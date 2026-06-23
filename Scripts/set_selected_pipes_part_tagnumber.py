import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "set_selected_pipes_part_tagnumber_log.txt"
TARGET_PARAMETER = "PART_TAGNUMBER"
TARGET_VALUE = "DTMX"
PREVIEW_LIMIT = 20


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


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


def is_pipe_entity(entity):
    object_name = norm(safe_get(entity, "ObjectName"))
    entity_name = norm(safe_get(entity, "EntityName"))
    return object_name == "vcssubsegment" or entity_name == "vcssubsegment"


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


def get_parameters_rows(parameters):
    count = None
    count_value = safe_get(parameters, "Count")
    if not (isinstance(count_value, str) and count_value.startswith("<GET_ERROR")):
        try:
            count = int(count_value)
        except Exception:
            count = None

    rows = []
    if count is None:
        try:
            for index, item in enumerate(parameters):
                rows.append((index, item))
        except Exception as ex:
            log(f"Parameters enumeration failed: {ex}")
        return rows

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


def find_parameter_item(element, target_name):
    parameters = safe_get(element, "Parameters")
    if isinstance(parameters, str) and parameters.startswith("<GET_ERROR"):
        log(f"Element.Parameters unavailable: {parameters}")
        return None, None, None

    for index, item in get_parameters_rows(parameters):
        if item is None:
            continue
        param_name = safe_get(item, "Name")
        if norm(param_name) == norm(target_name):
            return item, index, parameters
    return None, None, parameters


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, "DTMX PART_TAGNUMBER writer", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== set_selected_pipes_part_tagnumber.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"Target parameter: {TARGET_PARAMETER}")
log(f"Target value: {TARGET_VALUE}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: no active document. Check set_selected_pipes_part_tagnumber_log.txt")
else:
    selected = get_selected_entities(doc)
    pipe_entities = [item for item in selected if is_pipe_entity(item)]

    log(f"Selected entities total: {len(selected)}")
    log(f"Selected pipe entities: {len(pipe_entities)}")

    changed = 0
    unchanged = 0
    failed = 0

    for index, entity in enumerate(pipe_entities):
        handle = safe_get(entity, "Handle")
        element = safe_get(entity, "Element")
        if isinstance(element, str) and element.startswith("<GET_ERROR"):
            log(f"PIPE[{index}] Handle={handle} | Element unavailable: {element}")
            failed += 1
            continue

        before_get = safe_call(element.GetValue, TARGET_PARAMETER)
        param_item, param_index, parameters = find_parameter_item(element, TARGET_PARAMETER)

        if param_item is None:
            log(f"PIPE[{index}] Handle={handle} | {TARGET_PARAMETER} not found")
            failed += 1
            continue

        before_value = safe_get(param_item, "Value")
        before_comment = safe_get(param_item, "Comment")
        before_value_comment = safe_get(param_item, "ValueComment")
        if index < PREVIEW_LIMIT:
            log(
                "PIPE[{0}] Handle={1} | param_index={2} | before_value={3} | before_get={4}".format(
                    index, handle, param_index, before_value, before_get
                )
            )

        if str(before_get) == TARGET_VALUE or str(before_value) == TARGET_VALUE:
            unchanged += 1
            if index < PREVIEW_LIMIT:
                log(f"PIPE[{index}] Handle={handle} | already has target value")
            continue

        set_parameter_result = safe_call(
            parameters.SetParameter,
            TARGET_PARAMETER,
            TARGET_VALUE,
            before_comment,
            before_value_comment,
        )
        if index < PREVIEW_LIMIT:
            log(f"PIPE[{index}] Handle={handle} | Parameters.SetParameter result = {set_parameter_result}")

        update_result = safe_call(entity.Update)
        if index < PREVIEW_LIMIT:
            log(f"PIPE[{index}] Handle={handle} | entity.Update result = {update_result}")

        regen_result = safe_call(doc.Regen, 1)
        if index < PREVIEW_LIMIT:
            log(f"PIPE[{index}] Handle={handle} | doc.Regen result = {regen_result}")

        after_value = safe_get(param_item, "Value")
        after_get = safe_call(element.GetValue, TARGET_PARAMETER)
        if index < PREVIEW_LIMIT:
            log(
                "PIPE[{0}] Handle={1} | after_value={2} | after_get={3}".format(
                    index, handle, after_value, after_get
                )
            )

        if str(after_get) == TARGET_VALUE or str(after_value) == TARGET_VALUE:
            changed += 1
        else:
            failed += 1

    log(f"Summary | selected_pipes={len(pipe_entities)} | changed={changed} | unchanged={unchanged} | failed={failed}")

    popup(
        "DTMX: selected pipes {0}\nupdated {1}\nalready set {2}\nfailed {3}\nLog: {4}".format(
            len(pipe_entities), changed, unchanged, failed, LOG_PATH
        )
    )

log("=== set_selected_pipes_part_tagnumber.py end ===")
