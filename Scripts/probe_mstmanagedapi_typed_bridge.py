# -*- coding: utf-8 -*-
import ctypes
import datetime
from pathlib import Path

import pythoncom
import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_typed_bridge_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
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


def norm(v):
    return str(v).strip().lower() if v is not None else ""


def popup(message, title="DTMX typed bridge probe"):
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
log("=== probe_mstmanagedapi_typed_bridge.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"MST DLL: {MST_DLL}")

app = get_app()
doc = get_doc(app)
if doc is None:
    log("No active document")
    raise SystemExit

entity = get_selected_entity(doc)
if entity is None:
    log("No selected target entity")
    raise SystemExit

element = safe_get(entity, "Element")
if isinstance(element, str):
    log(f"entity.Element unavailable: {element}")
    raise SystemExit

log(f"Selected Handle = {safe_get(entity, 'Handle')}")
log(f"Selected ObjectName = {safe_get(entity, 'ObjectName')}")
log(f"COM Element.ObjectId = {safe_get(element, 'ObjectId')}")

try:
    import clr
    import System
    import System.Reflection
    from System.Runtime.InteropServices import Marshal
    log("import clr/System/Marshal OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    raise SystemExit

asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
types = {t.FullName: t for t in asm.GetExportedTypes()}
c_element_type = types["mstManagedAPI.CElement"]

ctor0 = list(c_element_type.GetConstructors())[0]
param0 = list(ctor0.GetParameters())[0]
pointer_type = param0.ParameterType
elem_type = pointer_type.GetElementType()

log(f"Pointer type = {pointer_type}")
log(f"Element type = {elem_type}")
log(f"Element type GUID = {elem_type.GUID}")

raw, keeper = get_native_iunknown(element)
if raw is None:
    raise SystemExit

typed_obj = None
typed_qi = None

try:
    typed_obj = Marshal.GetTypedObjectForIUnknown(System.IntPtr(raw), elem_type)
    log(f"Marshal.GetTypedObjectForIUnknown OK: {typed_obj}")
    log(f"typed_obj.GetType() = {typed_obj.GetType()}")
except Exception as ex:
    log(f"Marshal.GetTypedObjectForIUnknown FAILED: {ex}")

try:
    iid = pythoncom.MakeIID(str(elem_type.GUID))
    typed_qi = element._oleobj_.QueryInterface(iid)
    log(f"pywin32 QueryInterface(typed GUID) OK: {typed_qi}")
except Exception as ex:
    log(f"pywin32 QueryInterface(typed GUID) FAILED: {ex}")

if typed_obj is not None:
    try:
        managed = ctor0.Invoke(System.Array[System.Object]([typed_obj]))
        log(f"CElement ctor(typed_obj) OK: {managed}")
        log(f"Managed Name = {managed.Name}")
        log(f"Managed ParamsCount = {managed.ParamsCount}")
    except Exception as ex:
        log(f"CElement ctor(typed_obj) FAILED: {ex}")

if typed_qi is not None:
    try:
        raw2, keeper2 = get_native_iunknown(typed_qi)
        log(f"typed_qi raw pointer = {raw2}")
        if raw2 is not None:
            typed_obj2 = Marshal.GetTypedObjectForIUnknown(System.IntPtr(raw2), elem_type)
            log(f"typed_obj2 = {typed_obj2}")
            managed2 = ctor0.Invoke(System.Array[System.Object]([typed_obj2]))
            log(f"CElement ctor(typed_qi->typed_obj2) OK: {managed2}")
            log(f"Managed2 Name = {managed2.Name}")
            log(f"Managed2 ParamsCount = {managed2.ParamsCount}")
    except Exception as ex:
        log(f"typed_qi bridge FAILED: {ex}")

popup(f"Typed bridge probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_typed_bridge.py end ===")
