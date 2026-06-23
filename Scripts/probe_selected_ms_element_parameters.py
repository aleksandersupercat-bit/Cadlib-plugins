import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_selected_ms_element_parameters_log.txt"
PREVIEW_LIMIT = 80
PARAM_KEYS = [
    "PART_TAGNUMBER",
    "PART_TAG",
    "PART_NAME",
    "PART_TYPE",
    "PART_REFERENCE",
    "PART_COMMENT",
    "PART_GROUP",
    "PART_MATERIAL",
    "Part_Tag",
    "Part_Name",
    "Part_Type",
    "TagNumber",
    "Tag",
    "Name",
    "Description",
]


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


def normalize_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)

    text = value
    try:
        repaired = text.encode("cp1251").decode("utf-8")
        if repaired != text:
            return repaired
    except Exception:
        pass
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

    try:
        app = Application
        log("Connected via global Application")
        return app
    except Exception as ex:
        log(f"Global Application unavailable: {ex}")

    return None


def get_document(app):
    try:
        doc = ThisDrawing
        log("Using global ThisDrawing")
        return doc
    except Exception as ex:
        log(f"Global ThisDrawing unavailable: {ex}")

    if app is None:
        return None

    try:
        doc = app.ActiveDocument
        log("Using app.ActiveDocument")
        return doc
    except Exception as ex:
        log(f"app.ActiveDocument unavailable: {ex}")
        return None


def get_selected_entities(doc):
    for attr_name in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            selection = getattr(doc, attr_name)
            rows = []
            for item in selection:
                rows.append(item)
            log(f"{attr_name} count: {len(rows)}")
            if rows:
                return rows
        except Exception as ex:
            log(f"{attr_name} read failed: {ex}")
    return []


def dump_basic_entity(entity):
    log("===== ENTITY =====")
    for attr_name in [
        "Handle",
        "ObjectName",
        "EntityName",
        "Part_Name",
        "Part_Tag",
        "Part_Type",
        "Part_Comment",
    ]:
        value = safe_get(entity, attr_name)
        log(f"ENTITY | {attr_name} = {short_repr(normalize_text(value))}")


def try_iter_collection(collection):
    count = None

    for attr_name in ["Count", "Length"]:
        attr_value = safe_get(collection, attr_name)
        if not isinstance(attr_value, str) or not attr_value.startswith("<GET_ERROR"):
            try:
                count = int(attr_value)
                break
            except Exception:
                pass

    rows = []

    if count is not None:
        for index in range(min(count, PREVIEW_LIMIT)):
            item = None
            for getter in [
                lambda: collection.Item(index),
                lambda: collection.Item(index + 1),
                lambda: collection[index],
                lambda: collection[index + 1],
            ]:
                result = safe_call(getter)
                if not (isinstance(result, str) and result.startswith("<CALL_ERROR")):
                    item = result
                    break
            rows.append((index, item))
        return rows, count

    try:
        for index, item in enumerate(collection):
            rows.append((index, item))
            if index + 1 >= PREVIEW_LIMIT:
                break
        return rows, None
    except Exception:
        return rows, count


def dump_parameter_item(item, index):
    log(f"PARAM[{index}] repr = {short_repr(item)}")
    for attr_name in [
        "Name",
        "Caption",
        "Description",
        "Value",
        "Comment",
        "Code",
        "Id",
        "ParameterId",
    ]:
        value = safe_get(item, attr_name)
        if isinstance(value, str) and value.startswith("<GET_ERROR"):
            continue
        log(f"PARAM[{index}] {attr_name} = {short_repr(normalize_text(value))}")


def dump_element_parameters(element):
    log("===== ELEMENT =====")
    for attr_name in ["Name", "Description", "ElementId", "ObjectId", "PathFromRoot"]:
        value = safe_get(element, attr_name)
        log(f"ELEMENT | {attr_name} = {short_repr(normalize_text(value))}")

    get_value = safe_get(element, "GetValue")
    get_comment = safe_get(element, "GetValueComment")

    for key in PARAM_KEYS:
        if callable(get_value):
            value = safe_call(get_value, key)
            log(f"ELEMENT | GetValue({key!r}) = {short_repr(normalize_text(value))}")
        if callable(get_comment):
            comment = safe_call(get_comment, key)
            log(f"ELEMENT | GetValueComment({key!r}) = {short_repr(normalize_text(comment))}")

    parameters = safe_get(element, "Parameters")
    log(f"ELEMENT | Parameters repr = {short_repr(parameters)}")

    if isinstance(parameters, str) and parameters.startswith("<GET_ERROR"):
        return

    rows, count = try_iter_collection(parameters)
    if count is not None:
        log(f"ELEMENT | Parameters count = {count}")
    else:
        log("ELEMENT | Parameters count = <unknown>")

    if not rows:
        log("ELEMENT | Parameters enumeration returned no items")
        return

    for index, item in rows[:PREVIEW_LIMIT]:
        if item is None:
            log(f"PARAM[{index}] = <unavailable>")
            continue
        dump_parameter_item(item, index)


def dump_axis_values(element_axis):
    log("===== ELEMENT_AXIS =====")

    for attr_name in ["Handle", "ObjectName", "EntityName", "Length"]:
        value = safe_get(element_axis, attr_name)
        log(f"ELEMENT_AXIS | {attr_name} = {short_repr(normalize_text(value))}")

    for method_name in ["GetFromObjParamVal", "GetToObjParamVal"]:
        method = safe_get(element_axis, method_name)
        if not callable(method):
            log(f"ELEMENT_AXIS | {method_name} unavailable")
            continue
        for key in PARAM_KEYS:
            value = safe_call(method, key)
            log(f"ELEMENT_AXIS | {method_name}({key!r}) = {short_repr(normalize_text(value))}")


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, "DTMX element probe", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== probe_selected_ms_element_parameters.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: no active document. Check probe_selected_ms_element_parameters_log.txt")
else:
    selected = get_selected_entities(doc)
    log(f"Selected count = {len(selected)}")

    if not selected:
        popup("DTMX: no selected object. Select one pipe and rerun.")
    else:
        entity = selected[0]
        dump_basic_entity(entity)

        element = safe_get(entity, "Element")
        if isinstance(element, str) and element.startswith("<GET_ERROR"):
            log(f"ENTITY.Element unavailable: {element}")
        else:
            dump_element_parameters(element)

        element_axis = safe_get(entity, "ElementAxis")
        if isinstance(element_axis, str) and element_axis.startswith("<GET_ERROR"):
            log(f"ENTITY.ElementAxis unavailable: {element_axis}")
        else:
            dump_axis_values(element_axis)

        popup(f"DTMX element probe done. Log: {LOG_PATH}")

log("=== probe_selected_ms_element_parameters.py end ===")
