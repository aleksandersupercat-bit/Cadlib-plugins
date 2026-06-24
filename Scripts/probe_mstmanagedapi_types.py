# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_types_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
TARGET_TYPE_NAMES = [
    "mstManagedAPI.MstudioCore",
    "mstManagedAPI.LibDatabase",
    "mstManagedAPI.CElement",
    "mstManagedAPI.CElementMngd",
    "mstManagedAPI.ProjectDBUtils",
    "mstManagedAPI.ProjectService",
    "mstManagedAPI.LibObjectInfo",
]
KEYWORDS = [
    "objectid",
    "element",
    "database",
    "current",
    "open",
    "find",
    "get",
    "handle",
    "uid",
    "guid",
    "project",
    "lib",
]
PREVIEW_LIMIT = 300


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


def popup(message, title="DTMX mstManagedAPI probe"):
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
            if sel:
                return sel[0]
        except Exception as ex:
            log(f"{sel_attr} error: {ex}")
    return None


def match_keywords(name):
    low = name.lower()
    return any(keyword in low for keyword in KEYWORDS)


def member_signature(method_base):
    parts = []
    try:
        params = list(method_base.GetParameters())
    except Exception:
        params = []
    for parameter in params:
        try:
            ptype = parameter.ParameterType.FullName or str(parameter.ParameterType)
        except Exception:
            ptype = "<unknown>"
        parts.append(f"{ptype} {parameter.Name}")
    try:
        ret = method_base.ReturnType.FullName
    except Exception:
        ret = "<unknown>"
    return f"{ret}({', '.join(parts)})"


def dump_type(t):
    log("")
    log(f"=== TYPE {t.FullName} ===")
    try:
        log(f"Assembly = {t.Assembly.FullName}")
    except Exception as ex:
        log(f"Assembly ERROR: {ex}")
    try:
        log(f"BaseType = {t.BaseType}")
    except Exception as ex:
        log(f"BaseType ERROR: {ex}")
    try:
        log(f"IsClass = {t.IsClass}; IsAbstract = {t.IsAbstract}; IsSealed = {t.IsSealed}")
    except Exception as ex:
        log(f"Flags ERROR: {ex}")

    # constructors
    try:
        ctors = list(t.GetConstructors())
        log(f"Constructors count = {len(ctors)}")
        for index, ctor in enumerate(ctors[:PREVIEW_LIMIT]):
            log(f"  CTOR[{index}] {ctor}")
    except Exception as ex:
        log(f"Constructors ERROR: {ex}")

    # properties
    try:
        props = list(t.GetProperties())
        props_sorted = sorted(props, key=lambda x: x.Name)
        log(f"Properties count = {len(props_sorted)}")
        for prop in props_sorted[:PREVIEW_LIMIT]:
            flag = "KEY" if match_keywords(prop.Name) else "   "
            try:
                ptype = prop.PropertyType.FullName
            except Exception:
                ptype = "<unknown>"
            log(f"  {flag} PROP {prop.Name}: {ptype}")
    except Exception as ex:
        log(f"Properties ERROR: {ex}")

    # methods
    try:
        methods = list(t.GetMethods())
        interesting = []
        for method in methods:
            if method.IsSpecialName:
                continue
            if match_keywords(method.Name):
                interesting.append(method)
        interesting = sorted(interesting, key=lambda x: x.Name)
        log(f"Interesting methods count = {len(interesting)}")
        for method in interesting[:PREVIEW_LIMIT]:
            prefix = "STATIC" if method.IsStatic else "INST"
            log(f"  {prefix} METHOD {method.Name}: {member_signature(method)}")
    except Exception as ex:
        log(f"Methods ERROR: {ex}")

    # fields
    try:
        fields = list(t.GetFields())
        interesting = []
        for field in fields:
            if match_keywords(field.Name):
                interesting.append(field)
        interesting = sorted(interesting, key=lambda x: x.Name)
        log(f"Interesting fields count = {len(interesting)}")
        for field in interesting[:PREVIEW_LIMIT]:
            prefix = "STATIC" if field.IsStatic else "INST"
            try:
                ftype = field.FieldType.FullName
            except Exception:
                ftype = "<unknown>"
            log(f"  {prefix} FIELD {field.Name}: {ftype}")
    except Exception as ex:
        log(f"Fields ERROR: {ex}")


reset_log()
log("=== probe_mstmanagedapi_types.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"MST DLL: {MST_DLL}")

app = get_app()
doc = get_doc(app)
entity = None
element = None

if doc is not None:
    entity = get_selected_entity(doc)
    if entity is not None:
        log(f"Selected ObjectName = {safe_get(entity, 'ObjectName')}")
        log(f"Selected Handle = {safe_get(entity, 'Handle')}")
        log(f"Selected EntityName = {safe_get(entity, 'EntityName')}")
        element = safe_get(entity, "Element")
        if not isinstance(element, str):
            log(f"Selected Element.ObjectId = {safe_get(element, 'ObjectId')}")
            log(f"Selected Element.ElementId = {safe_get(element, 'ElementId')}")
            log(f"Selected Element.Name = {safe_get(element, 'Name')}")

try:
    import clr
    import System
    import System.Reflection
    log("import clr/System OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    popup(f"CLR import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX mstManagedAPI probe FAILED")
    raise SystemExit

try:
    asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
    log(f"Assembly.LoadFrom OK: {asm.FullName}")
except Exception as ex:
    log(f"Assembly.LoadFrom FAILED: {ex}")
    popup(f"Assembly load failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX mstManagedAPI probe FAILED")
    raise SystemExit

all_types = list(asm.GetExportedTypes())
log(f"Exported types count = {len(all_types)}")

for type_name in TARGET_TYPE_NAMES:
    matching = [t for t in all_types if t.FullName == type_name]
    if not matching:
        log(f"TYPE NOT FOUND: {type_name}")
        continue
    dump_type(matching[0])

# extra scan: all types with keyword-ish names
log("")
log("=== KEYWORD TYPE SCAN ===")
keyword_types = []
for t in all_types:
    full_name = t.FullName or ""
    if match_keywords(full_name):
        keyword_types.append(full_name)
for name in sorted(keyword_types)[:PREVIEW_LIMIT]:
    log(f"  TYPE {name}")

popup(f"mstManagedAPI probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_types.py end ===")
