import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_selected_ms_parameter_item_log.txt"
TARGET_PARAMETER = "PART_TAGNUMBER"
PREVIEW_LIMIT = 120


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def short_repr(value, limit=600):
    try:
        text = repr(value)
    except Exception as ex:
        text = f"<repr error: {ex}>"
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


def safe_get(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception as ex:
        return f"<GET_ERROR {ex}>"


def safe_call(func, *args):
    try:
        return func(*args)
    except Exception as ex:
        return f"<CALL_ERROR {ex}>"


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
            selection = getattr(doc, attr_name)
            rows = list(selection)
            log(f"{attr_name} count: {len(rows)}")
            if rows:
                return rows[0]
        except Exception as ex:
            log(f"{attr_name} read failed: {ex}")
    return None


def get_parameters_rows(parameters):
    count = safe_get(parameters, "Count")
    try:
        count = int(count)
    except Exception:
        count = 0

    rows = []
    for index in range(count):
        item = None
        for getter in [
            lambda: parameters.Item(index),
            lambda: parameters.Item(index + 1),
            lambda: parameters[index],
            lambda: parameters[index + 1],
        ]:
            result = safe_call(getter)
            if not (isinstance(result, str) and result.startswith("<CALL_ERROR")):
                item = result
                break
        rows.append((index, item))
    return rows


def dump_typeinfo(obj, prefix):
    try:
        typeinfo = obj._oleobj_.GetTypeInfo()
        attr = typeinfo.GetTypeAttr()
        func_count = attr[6]
        var_count = attr[7]
        log(f"{prefix}Function count = {func_count}")
        log(f"{prefix}Variable count = {var_count}")

        for index in range(min(func_count, PREVIEW_LIMIT)):
            try:
                funcdesc = typeinfo.GetFuncDesc(index)
                names = typeinfo.GetNames(funcdesc[0])
                log(f"{prefix}FUNC[{index}] dispid={funcdesc[0]} names={short_repr(names)}")
            except Exception as ex:
                log(f"{prefix}FUNC[{index}] ERROR: {ex}")
    except Exception as ex:
        log(f"{prefix}TYPEINFO ERROR: {ex}")


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, "DTMX parameter item probe", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== probe_selected_ms_parameter_item.py start ===")
log(f"Target parameter: {TARGET_PARAMETER}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available")
    popup("DTMX: no active document")
else:
    entity = get_selected_entity(doc)
    if entity is None:
        popup("DTMX: no selected object")
    else:
        element = safe_get(entity, "Element")
        parameters = safe_get(element, "Parameters")
        target_item = None
        target_index = None

        for index, item in get_parameters_rows(parameters):
            if item is None:
                continue
            if norm(safe_get(item, "Name")) == norm(TARGET_PARAMETER):
                target_item = item
                target_index = index
                break

        if target_item is None:
            log(f"{TARGET_PARAMETER} not found")
            popup(f"DTMX: {TARGET_PARAMETER} not found")
        else:
            log(f"Target index = {target_index}")
            log(f"Target repr = {short_repr(target_item)}")
            for attr_name in sorted(set(dir(target_item)))[:PREVIEW_LIMIT]:
                log(f"DIR = {attr_name}")
            for attr_name in ["Name", "Value", "Comment", "Caption", "Code", "Id", "ParameterId"]:
                log(f"{attr_name} = {short_repr(safe_get(target_item, attr_name))}")
            dump_typeinfo(target_item, "PARAM_ITEM | ")
            popup(f"DTMX: {TARGET_PARAMETER} probe done. Log: {LOG_PATH}")

log("=== probe_selected_ms_parameter_item.py end ===")
