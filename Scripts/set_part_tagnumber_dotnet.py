# -*- coding: utf-8 -*-
# Sets PART_TAGNUMBER on selected VCS entities via .NET COM interop.
#
# Strategy:
#   1. win32com enumerates selected entities (correct nanoCAD thread context).
#   2. ctypes extracts the real native IUnknown* from pywin32's PyIUnknown C struct
#      (offset 16 on x64: ob_refcnt=8 + ob_type=8 + punk=8).
#      Marshal.GetIUnknownForObject(pywin32_obj) returns a CCW wrapper — wrong.
#      Direct ctypes read gives the real COM pointer.
#   3. Marshal.GetObjectForIUnknown(IntPtr) creates a proper System.__ComObject
#      (.NET Runtime Callable Wrapper) from the native pointer.
#   4. Type.InvokeMember dispatches Parameters / SetParameter via IDispatch.
#      This is genuine .NET COM interop — not pywin32.
#
# CElement (mstManagedAPI) turns out to be a DTO (no persistence methods),
# so it cannot modify live drawing elements without a LibDatabase connection.

import ctypes
import datetime
from pathlib import Path

import win32com.client
import pythoncom

LOG_PATH = Path.home() / "Desktop" / "set_part_tagnumber_dotnet_log.txt"
TARGET_PARAMETER = "PART_TAGNUMBER"
TARGET_VALUE = "DTMX_NET"
ENTITY_NAMES = {"vcssubsegment"}


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def safe_get(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception as ex:
        return f"<ERR:{ex}>"


def norm(v):
    return str(v).strip().lower() if v is not None else ""


# ─── Log starts before CLR so failures appear in the file ─────────────────────

reset_log()
log("=== set_part_tagnumber_dotnet.py start ===")
log(f"Target: {TARGET_PARAMETER} = {TARGET_VALUE}")

# ─── Python.NET init ───────────────────────────────────────────────────────────

try:
    import clr
    log("import clr OK")
except ImportError as _ex:
    log(f"import clr FAILED: {_ex}"); raise SystemExit

try:
    import System
except ImportError:
    log("import System failed — trying clr.AddReference")
    for _a in ("mscorlib", "System", "System.Core"):
        try:
            clr.AddReference(_a); log(f"  clr.AddReference({_a}) OK")
        except Exception as _e:
            log(f"  clr.AddReference({_a}): {_e}")
    try:
        import System
    except ImportError as _ex2:
        log(f"import System FAILED: {_ex2}"); raise SystemExit

try:
    import System.Reflection as Refl
    import System.Runtime.InteropServices as interop
    from System.Runtime.InteropServices import Marshal
    BF = Refl.BindingFlags
    log(f"CLR {System.Environment.Version} | Reflection + Marshal OK")
except Exception as _ex:
    log(f"System.Reflection/Marshal FAILED: {_ex}"); raise SystemExit

# ─── ctypes bridge ────────────────────────────────────────────────────────────
#
# pywin32 PyIUnknown C struct layout (CPython x64):
#   offset  0: ob_refcnt  (8 bytes)
#   offset  8: ob_type    (8 bytes)
#   offset 16: IUnknown*  (8 bytes)   ← real native COM pointer

_PUNK_OFFSET = 16


def get_native_iunknown(pywin32_com_obj):
    """
    Returns (int_ptr, py_iunknown_keeper).
    py_iunknown_keeper must stay alive until Marshal.GetObjectForIUnknown is called.
    """
    try:
        py_iunknown = pywin32_com_obj._oleobj_.QueryInterface(pythoncom.IID_IUnknown)
        raw = ctypes.cast(
            id(py_iunknown) + _PUNK_OFFSET,
            ctypes.POINTER(ctypes.c_void_p)
        )[0]
        if not raw:
            log("  get_native_iunknown: null pointer")
            return None, None
        return raw, py_iunknown
    except Exception as ex:
        log(f"  get_native_iunknown error: {ex}")
        return None, None


# ─── .NET COM dispatch via Marshal.GetObjectForIUnknown ───────────────────────

def invoke_get(com_net_obj, name):
    """COM property getter via Type.InvokeMember on System.__ComObject."""
    return com_net_obj.GetType().InvokeMember(
        name,
        BF.GetProperty | BF.InvokeMethod | BF.Public | BF.Instance,
        None, com_net_obj, None
    )


def invoke_method(com_net_obj, name, *args):
    """COM method call via Type.InvokeMember on System.__ComObject."""
    net_args = System.Array[System.Object](list(args)) if args else None
    return com_net_obj.GetType().InvokeMember(
        name,
        BF.InvokeMethod | BF.Public | BF.Instance,
        None, com_net_obj, net_args
    )


def try_set_via_net_com(pywin32_element):
    """
    Primary .NET strategy: Marshal.GetObjectForIUnknown → System.__ComObject
    → Type.InvokeMember("Parameters") → Type.InvokeMember("SetParameter").
    Returns True on success (verified via COM readback).
    """
    raw, keeper = get_native_iunknown(pywin32_element)
    if raw is None:
        return False

    element_net = None
    try:
        iunk_ptr = System.IntPtr(raw)
        element_net = Marshal.GetObjectForIUnknown(iunk_ptr)
        log(f"  GetObjectForIUnknown OK  type={element_net.GetType()}")
    except Exception as ex:
        log(f"  GetObjectForIUnknown error: {ex}")
        return False
    finally:
        keeper = None  # RCW now holds its own COM ref

    try:
        # Get Parameters collection via .NET COM dispatch
        params_net = invoke_get(element_net, "Parameters")
        if params_net is None:
            log("  Parameters returned None")
            return False
        log(f"  Parameters OK  type={params_net.GetType()}")

        # Call SetParameter via .NET COM dispatch
        invoke_method(
            params_net, "SetParameter",
            TARGET_PARAMETER, TARGET_VALUE, "", ""
        )
        log("  SetParameter via .NET dispatch called OK")

        # Verify via COM (ground truth for what nanoCAD sees)
        after_com = str(pywin32_element.GetValue(TARGET_PARAMETER))
        log(f"  after (COM) = {after_com!r}")
        return after_com == TARGET_VALUE

    except Exception as ex:
        log(f"  try_set_via_net_com error: {ex}")
        return False
    finally:
        if element_net is not None:
            try:
                Marshal.ReleaseComObject(element_net)
            except Exception:
                pass


# ─── win32com entity access ───────────────────────────────────────────────────

def get_app():
    for progid in ["nanoCADx64.Application.24.0", "nanoCADx64.Application",
                   "nanoCAD.Application.24.0", "nanoCAD.Application"]:
        try:
            app = win32com.client.GetActiveObject(progid)
            log(f"win32com.GetActiveObject({progid}) OK")
            return app
        except Exception:
            pass
    try:
        log("using global Application")
        return Application
    except Exception:
        return None


def get_doc(app):
    try:
        return ThisDrawing
    except Exception:
        pass
    if app:
        try:
            return app.ActiveDocument
        except Exception:
            pass
    return None


def get_selected_vcs(doc):
    entities = []
    for attr in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            sel = list(getattr(doc, attr))
            log(f"{attr} count: {len(sel)}")
            for ent in sel:
                if norm(safe_get(ent, "ObjectName")) in ENTITY_NAMES:
                    entities.append(ent)
            if entities:
                break
        except Exception as ex:
            log(f"{attr} error: {ex}")
    return entities


# ─── Main ─────────────────────────────────────────────────────────────────────

app = get_app()
doc = get_doc(app)
if doc is None:
    log("ABORT: no active document"); raise SystemExit

entities = get_selected_vcs(doc)
log(f"VCS entities selected: {len(entities)}")

if not entities:
    log("No VCS pipe entities selected.")
    try:
        win32com.client.Dispatch("WScript.Shell").Popup(
            "No VCS entities selected.\nSelect pipe elements first.",
            5, "DTMX .NET setter", 64)
    except Exception:
        pass
    raise SystemExit

changed = 0
failed = 0

for idx, entity in enumerate(entities):
    handle = safe_get(entity, "Handle")
    log(f"--- [{idx}] Handle={handle} ---")

    element = safe_get(entity, "Element")
    if isinstance(element, str):
        log(f"  Element unavailable: {element}"); failed += 1; continue

    # Read current value via COM
    try:
        current = str(element.GetValue(TARGET_PARAMETER))
        log(f"  current = {current!r}")
        if current == TARGET_VALUE:
            log("  already set, skip"); changed += 1; continue
    except Exception as ex:
        log(f"  GetValue error: {ex}")

    # Set via .NET COM interop
    ok = try_set_via_net_com(element)

    if ok:
        try:
            entity.Update()
            doc.Regen(1)
        except Exception as ex:
            log(f"  Update/Regen: {ex}")
        changed += 1
        log("  SUCCESS")
    else:
        failed += 1
        log("  FAILED")

log("")
log("=== SUMMARY ===")
log(f"Total: {len(entities)} | Changed: {changed} | Failed: {failed}")
log(f"Log: {LOG_PATH}")

try:
    win32com.client.Dispatch("WScript.Shell").Popup(
        f"DTMX .NET setter\nTotal: {len(entities)}\nChanged: {changed}\nFailed: {failed}\nLog: {LOG_PATH}",
        8, "DTMX .NET setter", 64)
except Exception:
    pass

log("=== set_part_tagnumber_dotnet.py end ===")
