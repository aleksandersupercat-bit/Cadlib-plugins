# -*- coding: utf-8 -*-
import ctypes
import datetime
from pathlib import Path

import pythoncom
import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_live_bridge_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
TARGET_PARAMETER = "PART_TAGNUMBER"
ENTITY_NAMES = {"vcssubsegment"}
_PUNK_OFFSET = 16


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


def safe_call(fn, *args):
    try:
        return fn(*args)
    except Exception as ex:
        return f"<ERR:{ex}>"


def norm(v):
    return str(v).strip().lower() if v is not None else ""


def popup(message, title="DTMX live bridge probe"):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, title, 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


def get_app():
    for progid in [
        "nanoCADx64.Application.24.0",
        "nanoCADx64.Application",
        "nanoCAD.Application.24.0",
        "nanoCAD.Application",
    ]:
        try:
            app = win32com.client.GetActiveObject(progid)
            log(f"Connected: {progid}")
            return app
        except Exception:
            pass
    try:
        app = Application
        log("Connected: global Application")
        return app
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


def get_selected_entity(doc):
    for sel_attr in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            sel = list(getattr(doc, sel_attr))
            log(f"{sel_attr} count: {len(sel)}")
            for item in sel:
                if norm(safe_get(item, "ObjectName")) in ENTITY_NAMES or norm(safe_get(item, "EntityName")) in ENTITY_NAMES:
                    return item
        except Exception as ex:
            log(f"{sel_attr} error: {ex}")
    return None


def get_native_iunknown(pywin32_com_obj):
    try:
        py_iunknown = pywin32_com_obj._oleobj_.QueryInterface(pythoncom.IID_IUnknown)
        raw = ctypes.cast(
            id(py_iunknown) + _PUNK_OFFSET,
            ctypes.POINTER(ctypes.c_void_p)
        )[0]
        if not raw:
            log("get_native_iunknown: null pointer")
            return None, None
        return raw, py_iunknown
    except Exception as ex:
        log(f"get_native_iunknown error: {ex}")
        return None, None


reset_log()
log("=== probe_mstmanagedapi_live_bridge.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"MST DLL: {MST_DLL}")

app = get_app()
doc = get_doc(app)
if doc is None:
    log("No active document")
    popup(f"No active document\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

entity = get_selected_entity(doc)
if entity is None:
    log("No selected target entity")
    popup(f"No selected VCS entity\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

element = safe_get(entity, "Element")
if isinstance(element, str):
    log(f"entity.Element unavailable: {element}")
    popup(f"entity.Element unavailable\n{element}\n\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

log(f"Selected Handle = {safe_get(entity, 'Handle')}")
log(f"Selected ObjectName = {safe_get(entity, 'ObjectName')}")
log(f"COM Element.ObjectId = {safe_get(element, 'ObjectId')}")
log(f"COM Element.ElementId = {safe_get(element, 'ElementId')}")
log(f"COM GetValue({TARGET_PARAMETER!r}) = {safe_call(element.GetValue, TARGET_PARAMETER)!r}")

try:
    import clr
    import System
    import System.Reflection
    from System.Runtime.InteropServices import Marshal
    log("import clr/System/Marshal OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    popup(f"CLR import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

try:
    asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
    log(f"Assembly.LoadFrom OK: {asm.FullName}")
except Exception as ex:
    log(f"Assembly.LoadFrom FAILED: {ex}")
    popup(f"Assembly load failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

types = {t.FullName: t for t in asm.GetExportedTypes()}
c_element_type = types.get("mstManagedAPI.CElement")
if c_element_type is None:
    log("mstManagedAPI.CElement not found")
    popup(f"CElement not found\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

log(f"CElement type = {c_element_type}")

raw, keeper = get_native_iunknown(element)
if raw is None:
    popup(f"Could not get native IUnknown\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

dotnet_com = None
managed_element = None

try:
    dotnet_com = Marshal.GetObjectForIUnknown(System.IntPtr(raw))
    log(f"Marshal.GetObjectForIUnknown OK: {dotnet_com.GetType()}")
except Exception as ex:
    log(f"Marshal.GetObjectForIUnknown FAILED: {ex}")
    popup(f"GetObjectForIUnknown failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit
finally:
    keeper = None

constructors = list(c_element_type.GetConstructors())
log(f"CElement constructors count = {len(constructors)}")
for index, ctor in enumerate(constructors):
    log(f"  CTOR[{index}] {ctor}")

ctor_errors = []
for index, ctor in enumerate(constructors):
    params = list(ctor.GetParameters())
    try:
        if len(params) == 1:
            ptype = params[0].ParameterType.FullName or str(params[0].ParameterType)
            log(f"Trying CTOR[{index}] param type = {ptype}")
            managed_element = ctor.Invoke(System.Array[System.Object]([dotnet_com]))
            log(f"CTOR[{index}] invoke OK -> {managed_element}")
            break
    except Exception as ex:
        ctor_errors.append(f"CTOR[{index}] {ex}")
        log(f"CTOR[{index}] invoke FAILED: {ex}")

if managed_element is None:
    log("Could not construct mstManagedAPI.CElement from live COM element")
    for err in ctor_errors:
        log(f"  {err}")
    popup(f"CElement live bridge failed\nLog: {LOG_PATH}", "DTMX live bridge FAILED")
    raise SystemExit

try:
    log(f"Managed ElementId = {managed_element.ElementId}")
except Exception as ex:
    log(f"Managed ElementId FAILED: {ex}")
try:
    log(f"Managed ModelUID = {managed_element.ModelUID}")
except Exception as ex:
    log(f"Managed ModelUID FAILED: {ex}")
try:
    log(f"Managed Name = {managed_element.Name}")
except Exception as ex:
    log(f"Managed Name FAILED: {ex}")
try:
    log(f"Managed ParamsCount = {managed_element.ParamsCount}")
except Exception as ex:
    log(f"Managed ParamsCount FAILED: {ex}")

for probe_name in [TARGET_PARAMETER, "PART_TAG", "PART_NAME", "PART_TYPE"]:
    try:
        value = managed_element.GetParameterValue(probe_name, "")
        log(f"Managed GetParameterValue({probe_name!r}, '') = {value!r}")
    except Exception as ex:
        log(f"Managed GetParameterValue({probe_name!r}, '') FAILED: {ex}")

    try:
        param = managed_element.GetParameter(probe_name)
        log(f"Managed GetParameter({probe_name!r}) = {param}")
        if param is not None:
            for attr_name in ["Name", "Value", "Comment", "ValueComment"]:
                log(f"  CParam.{attr_name} = {safe_get(param, attr_name)}")
    except Exception as ex:
        log(f"Managed GetParameter({probe_name!r}) FAILED: {ex}")

try:
    iface = managed_element.GetElementInterface()
    log(f"Managed GetElementInterface() = {iface}")
except Exception as ex:
    log(f"Managed GetElementInterface FAILED: {ex}")

popup(f"Live bridge probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_live_bridge.py end ===")
