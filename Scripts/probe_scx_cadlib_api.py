# -*- coding: utf-8 -*-
# Probe: reflects on CADLibControls / CADLibMain / CADLibPluginParameters /
# Interop.SCXComponentsLibLib to find the managed bridge from a selected
# entity to its ModelStudio parameters (IPEParameter / IPEParameters).
#
# Run from nanoCAD Python script editor with a VCS pipe entity selected.

import datetime
from pathlib import Path

LOG_PATH = Path.home() / "Desktop" / "probe_scx_cadlib_api_log.txt"

MIA = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin"

PROBE_DLLS = [
    f"{MIA}\\Interop.SCXComponentsLibLib.dll",
    f"{MIA}\\AxInterop.SCXComponentsLibLib.dll",
    f"{MIA}\\CADLibControls.dll",
    f"{MIA}\\CADLibMain.dll",
    f"{MIA}\\CADLibPluginParameters.dll",
    f"{MIA}\\mstManagedAPI.dll",
]

# Keywords in type/method names we care about
INTERESTING = {
    "parameter", "param", "scx", "property", "editor", "value",
    "element", "entity", "set", "get", "request", "object", "model",
    "bridge", "convert", "wrap", "util", "helper", "configurator",
}


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    ts = f"{datetime.datetime.now():%H:%M:%S}"
    line = f"{ts} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sig(method):
    """One-line signature string."""
    params = ", ".join(
        f"{p.ParameterType.Name} {p.Name}" for p in method.GetParameters()
    )
    return f"{method.ReturnType.Name} {method.Name}({params})"


def is_interesting(name):
    n = name.lower()
    return any(kw in n for kw in INTERESTING)


reset_log()
log("=== probe_scx_cadlib_api.py start ===")

try:
    import clr
    log("import clr OK")
except ImportError as ex:
    log(f"import clr FAILED: {ex}"); raise SystemExit

try:
    import System
except ImportError:
    for a in ("mscorlib", "System", "System.Core"):
        try: clr.AddReference(a)
        except Exception: pass
    import System

import System.Reflection as Refl
log(f"CLR {System.Environment.Version}")

# ─── Load DLLs and collect types ──────────────────────────────────────────────

loaded = {}  # dll_name -> Assembly

for dll_path in PROBE_DLLS:
    name = Path(dll_path).name
    try:
        asm = Refl.Assembly.LoadFrom(dll_path)
        loaded[name] = asm
        log(f"Loaded: {name} v{asm.GetName().Version}")
    except Exception as ex:
        log(f"FAILED to load {name}: {ex}")

log("")
log("=" * 60)
log("TYPE + METHOD DUMP (interesting types only)")
log("=" * 60)

for dll_name, asm in loaded.items():
    log("")
    log(f"─── {dll_name} ───")

    try:
        types = list(asm.GetExportedTypes())
    except Exception as ex:
        try:
            # ReflectionTypeLoadException — grab what loaded
            types = [t for t in ex.Types if t is not None]
        except Exception:
            types = []
        log(f"  GetExportedTypes partial: {ex}")

    for t in types:
        type_name = t.FullName or t.Name
        if not is_interesting(type_name):
            continue

        log(f"\n  TYPE: {type_name}")

        # Properties
        try:
            props = list(t.GetProperties())
            if props:
                log(f"    Properties ({len(props)}):")
                for p in props:
                    try:
                        rw = ("r" if p.CanRead else "-") + ("w" if p.CanWrite else "-")
                        log(f"      [{rw}] {p.PropertyType.Name} {p.Name}")
                    except Exception:
                        log(f"      {p.Name} (error)")
        except Exception as ex:
            log(f"    Properties error: {ex}")

        # Methods (exclude Object base methods)
        base_methods = {"GetType", "GetHashCode", "Equals", "ToString",
                        "MemberwiseClone", "Finalize", "ReferenceEquals"}
        try:
            methods = [m for m in t.GetMethods()
                       if m.Name not in base_methods
                       and not m.Name.startswith("add_")
                       and not m.Name.startswith("remove_")]
            if methods:
                log(f"    Methods ({len(methods)}):")
                for m in methods:
                    try:
                        log(f"      {sig(m)}")
                    except Exception:
                        log(f"      {m.Name} (sig error)")
        except Exception as ex:
            log(f"    Methods error: {ex}")

        # Events
        try:
            events = list(t.GetEvents())
            if events:
                log(f"    Events: {[e.Name for e in events]}")
        except Exception:
            pass

# ─── Search for methods that take int / long / ObjectId ────────────────────────

log("")
log("=" * 60)
log("METHODS ACCEPTING INT/INT64/OBJECTID (potential entity-ID bridge)")
log("=" * 60)

int_types = {"Int32", "Int64", "UInt32", "UInt64", "IntPtr", "ObjectId",
             "ObjectID", "long", "int"}

for dll_name, asm in loaded.items():
    try:
        types = list(asm.GetExportedTypes())
    except Exception:
        types = []

    for t in types:
        try:
            for m in t.GetMethods():
                param_types = [p.ParameterType.Name for p in m.GetParameters()]
                if any(pt in int_types for pt in param_types):
                    type_short = t.Name
                    log(f"  {type_short}.{sig(m)}")
        except Exception:
            pass

# ─── Try to access SCXUtils / AppScxPropertyEditor via win32com ───────────────

log("")
log("=" * 60)
log("LIVE PROBE: selected entity → IPEParameters")
log("=" * 60)

try:
    import win32com.client
    for progid in ["nanoCADx64.Application.24.0", "nanoCADx64.Application"]:
        try:
            app = win32com.client.GetActiveObject(progid)
            log(f"nanoCAD app: {progid}")
            break
        except Exception:
            app = None

    if app is None:
        try: app = Application
        except Exception: pass

    doc = None
    try: doc = app.ActiveDocument
    except Exception:
        try: doc = ThisDrawing
        except Exception: pass

    if doc:
        # Get first selected VCS entity
        entity = None
        for sel_attr in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
            try:
                for ent in getattr(doc, sel_attr):
                    if str(getattr(ent, "ObjectName", "")).lower() == "vcssubsegment":
                        entity = ent
                        break
            except Exception:
                pass
            if entity:
                break

        if entity:
            handle = getattr(entity, "Handle", "?")
            obj_id = getattr(entity, "ObjectID", None) or getattr(entity, "ObjectId", None)
            log(f"Entity: Handle={handle}  ObjectID={obj_id}")

            # Try CSCXUtils static methods
            for dll_name, asm in loaded.items():
                try:
                    types = list(asm.GetExportedTypes())
                except Exception:
                    types = []
                for t in types:
                    if "util" in t.Name.lower() or "scx" in t.Name.lower() or "bridge" in t.Name.lower():
                        log(f"\n  Trying {t.FullName}...")
                        for m in t.GetMethods():
                            if not m.IsStatic:
                                continue
                            params = m.GetParameters()
                            if len(params) == 0:
                                continue
                            param_types = [p.ParameterType.Name for p in params]
                            if any(pt in int_types for pt in param_types):
                                log(f"    static {sig(m)}")
                                # Try calling with ObjectID
                                if obj_id is not None:
                                    try:
                                        result = m.Invoke(None, System.Array[System.Object]([
                                            System.Convert.ChangeType(
                                                System.Int64(obj_id),
                                                params[0].ParameterType
                                            )
                                        ]))
                                        log(f"    → result type: {result.GetType() if result else None}")
                                        log(f"    → result: {result}")
                                    except Exception as ex:
                                        log(f"    → call error: {ex}")
        else:
            log("No VCS entity selected")
    else:
        log("No active document")

except Exception as ex:
    log(f"Live probe error: {ex}")

log("")
log("=== probe_scx_cadlib_api.py end ===")
log(f"Log: {LOG_PATH}")

try:
    import win32com.client
    win32com.client.Dispatch("WScript.Shell").Popup(
        f"SCX/CADLib probe done.\nLog: {LOG_PATH}", 5, "DTMX probe", 64)
except Exception:
    pass
