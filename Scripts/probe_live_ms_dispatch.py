# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import pythoncom
import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_live_ms_dispatch_log.txt"
MAX_TYPEINFO_FUNCS = 400
MAX_TYPEINFO_VARS = 200
MAX_DIR_ITEMS = 400

INVOKE_KIND_NAMES = {
    getattr(pythoncom, "INVOKE_FUNC", 1): "FUNC",
    getattr(pythoncom, "INVOKE_PROPERTYGET", 2): "PROPERTYGET",
    getattr(pythoncom, "INVOKE_PROPERTYPUT", 4): "PROPERTYPUT",
    getattr(pythoncom, "INVOKE_PROPERTYPUTREF", 8): "PROPERTYPUTREF",
}

VARTYPE_NAMES = {
    0: "EMPTY",
    1: "NULL",
    2: "I2",
    3: "I4",
    4: "R4",
    5: "R8",
    6: "CY",
    7: "DATE",
    8: "BSTR",
    9: "DISPATCH",
    10: "ERROR",
    11: "BOOL",
    12: "VARIANT",
    13: "UNKNOWN",
    14: "DECIMAL",
    16: "I1",
    17: "UI1",
    18: "UI2",
    19: "UI4",
    20: "I8",
    21: "UI8",
    22: "INT",
    23: "UINT",
    24: "VOID",
    25: "HRESULT",
    26: "PTR",
    27: "SAFEARRAY",
    28: "CARRAY",
    29: "USERDEFINED",
    30: "LPSTR",
    31: "LPWSTR",
    36: "RECORD",
    37: "INT_PTR",
    38: "UINT_PTR",
    64: "FILETIME",
    66: "STREAM",
    67: "STORAGE",
    68: "STREAMED_OBJECT",
    69: "STORED_OBJECT",
    70: "BLOB_OBJECT",
    71: "CF",
    72: "CLSID",
}


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def safe_repr(value, limit=800):
    try:
        text = repr(value)
    except Exception as ex:
        text = f"<repr error: {ex}>"
    if len(text) > limit:
        text = text[:limit] + "...<truncated>"
    return text


def safe_get(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception as ex:
        return f"<GET_ERROR {ex}>"


def norm(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def get_application():
    for progid in [
        "nanoCADx64.Application.24.0",
        "nanoCADx64.Application",
        "nanoCAD.Application.24.0",
        "nanoCAD.Application",
    ]:
        try:
            app = win32com.client.GetActiveObject(progid)
            log(f"Connected via GetActiveObject({progid})")
            return app
        except Exception as ex:
            log(f"GetActiveObject({progid}) failed: {ex}")
    return None


def get_document(app):
    if app is None:
        return None
    try:
        doc = app.ActiveDocument
        log("Using app.ActiveDocument")
        return doc
    except Exception as ex:
        log(f"app.ActiveDocument unavailable: {ex}")
        return None


def get_selected_entity(doc):
    for attr_name in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            selection = list(getattr(doc, attr_name))
            log(f"{attr_name} count = {len(selection)}")
            if selection:
                return selection[0]
        except Exception as ex:
            log(f"{attr_name} failed: {ex}")
    return None


def decode_vartype(vt):
    if isinstance(vt, tuple) and vt:
        base = vt[0]
        return f"{VARTYPE_NAMES.get(base, base)}:{safe_repr(vt)}"
    return VARTYPE_NAMES.get(vt, str(vt))


def dump_dir(obj, prefix):
    try:
        names = sorted(set(dir(obj)))
        log(f"{prefix}dir count = {len(names)}")
        for index, name in enumerate(names[:MAX_DIR_ITEMS]):
            log(f"{prefix}dir[{index}] = {name}")
        if len(names) > MAX_DIR_ITEMS:
            log(f"{prefix}dir truncated at {MAX_DIR_ITEMS}")
    except Exception as ex:
        log(f"{prefix}dir ERROR: {ex}")


def dump_maps(obj, prefix):
    for attr_name in ["_prop_map_get_", "_prop_map_put_", "_olerepr_"]:
        value = safe_get(obj, attr_name)
        log(f"{prefix}{attr_name} = {safe_repr(value)}")


def dump_typeinfo(obj, prefix):
    try:
        ti = obj._oleobj_.GetTypeInfo()
        ta = ti.GetTypeAttr()
        guid = ta[0]
        lcid = ta[1]
        func_count = ta[6]
        var_count = ta[7]
        typekind = ta[5]
        log(f"{prefix}TypeInfo GUID = {guid}")
        log(f"{prefix}TypeInfo LCID = {lcid}")
        log(f"{prefix}TypeInfo typekind = {typekind}")
        log(f"{prefix}TypeInfo func_count = {func_count}")
        log(f"{prefix}TypeInfo var_count = {var_count}")

        for index in range(min(func_count, MAX_TYPEINFO_FUNCS)):
            try:
                fd = ti.GetFuncDesc(index)
                memid = fd[0]
                invkind = fd[4]
                cparams = fd[6]
                cparams_opt = fd[7]
                vtable_offset = fd[1]
                names = ti.GetNames(memid)
                log(
                    f"{prefix}FUNC[{index}] memid={memid} "
                    f"invkind={INVOKE_KIND_NAMES.get(invkind, invkind)} "
                    f"cParams={cparams} cParamsOpt={cparams_opt} "
                    f"oVft={vtable_offset} names={safe_repr(names)}"
                )
                if len(fd) > 8:
                    arg_types = fd[2]
                    return_type = fd[8]
                    log(
                        f"{prefix}FUNC[{index}] "
                        f"arg_types={safe_repr(arg_types)} return={decode_vartype(return_type)}"
                    )
            except Exception as ex:
                log(f"{prefix}FUNC[{index}] ERROR: {ex}")
        if func_count > MAX_TYPEINFO_FUNCS:
            log(f"{prefix}FUNC truncated at {MAX_TYPEINFO_FUNCS}")

        for index in range(min(var_count, MAX_TYPEINFO_VARS)):
            try:
                vd = ti.GetVarDesc(index)
                memid = vd[0]
                varkind = vd[4]
                names = ti.GetNames(memid)
                vartype = vd[2]
                log(
                    f"{prefix}VAR[{index}] memid={memid} "
                    f"varkind={varkind} names={safe_repr(names)} vartype={decode_vartype(vartype)}"
                )
            except Exception as ex:
                log(f"{prefix}VAR[{index}] ERROR: {ex}")
        if var_count > MAX_TYPEINFO_VARS:
            log(f"{prefix}VAR truncated at {MAX_TYPEINFO_VARS}")
    except Exception as ex:
        log(f"{prefix}TYPEINFO ERROR: {ex}")


def dump_member_values(obj, prefix, names):
    for name in names:
        value = safe_get(obj, name)
        log(f"{prefix}{name} = {safe_repr(value)}")


def probe_com_object(obj, title):
    log(f"===== {title} =====")
    log(f"{title} repr = {safe_repr(obj)}")
    dump_maps(obj, f"{title} | ")
    dump_dir(obj, f"{title} | ")
    dump_typeinfo(obj, f"{title} | ")


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX dispatch probe", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== probe_live_ms_dispatch.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_application()
if app is None:
    log("ABORT: application not found")
    raise SystemExit

doc = get_document(app)
if doc is None:
    log("ABORT: no active document")
    raise SystemExit

log(f"Document.Name = {safe_repr(safe_get(doc, 'Name'))}")
entity = get_selected_entity(doc)
if entity is None:
    log("ABORT: no selected entity")
    popup(f"No selected object.\nLog: {LOG_PATH}")
    raise SystemExit

dump_member_values(
    entity,
    "ENTITY | ",
    ["ObjectName", "EntityName", "Handle", "Layer", "Color", "Linetype"],
)
probe_com_object(entity, "ENTITY")

element = safe_get(entity, "Element")
if not isinstance(element, str) or not element.startswith("<GET_ERROR"):
    dump_member_values(
        element,
        "ELEMENT | ",
        [
            "Name",
            "Description",
            "ElementId",
            "ObjectId",
            "PathFromRoot",
            "Level",
            "ModelUID",
        ],
    )
    probe_com_object(element, "ELEMENT")

    parameters = safe_get(element, "Parameters")
    if not isinstance(parameters, str) or not parameters.startswith("<GET_ERROR"):
        probe_com_object(parameters, "PARAMETERS")
        try:
            first_item = None
            count = 0
            for item in parameters:
                if first_item is None:
                    first_item = item
                count += 1
            log(f"PARAMETERS | enumerated count = {count}")
            if first_item is not None:
                dump_member_values(
                    first_item,
                    "PARAM_ITEM | ",
                    ["Name", "Value", "Comment", "ValueComment", "Category", "Caption"],
                )
                probe_com_object(first_item, "PARAM_ITEM")
        except Exception as ex:
            log(f"PARAMETERS enumeration failed: {ex}")

element_axis = safe_get(entity, "ElementAxis")
if not isinstance(element_axis, str) or not element_axis.startswith("<GET_ERROR"):
    dump_member_values(
        element_axis,
        "ELEMENT_AXIS | ",
        ["Name", "Description", "ElementId", "ObjectId", "PathFromRoot"],
    )
    probe_com_object(element_axis, "ELEMENT_AXIS")

popup(f"Dispatch probe done.\nLog: {LOG_PATH}")
log("=== probe_live_ms_dispatch.py end ===")
