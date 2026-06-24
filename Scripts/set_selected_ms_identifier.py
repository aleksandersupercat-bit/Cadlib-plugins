import datetime
import sys
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "set_selected_ms_identifier_log.txt"
TARGET_PARAMETER = "PART_TAGNUMBER"
TARGET_VALUE = sys.argv[1] if len(sys.argv) > 1 else "888"
ENTITY_NAMES = {"vcssubsegment"}
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


def is_target_entity(entity):
    object_name = norm(safe_get(entity, "ObjectName"))
    entity_name = norm(safe_get(entity, "EntityName"))
    return object_name in ENTITY_NAMES or entity_name in ENTITY_NAMES


def get_selected_entities(doc):
    for attr_name in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            selection = getattr(doc, attr_name)
            rows = list(selection)
            log(f"{attr_name} count: {len(rows)}")
            if rows:
                return rows
        except Exception as ex:
            log(f"{attr_name} read failed: {ex}")
    return []


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
        shell.Popup(message, 5, "DTMX identifier setter", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== set_selected_ms_identifier.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"Target parameter: {TARGET_PARAMETER}")
log(f"Target value: {TARGET_VALUE}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: no active document")
else:
    selected = get_selected_entities(doc)
    target_entities = [item for item in selected if is_target_entity(item)]

    log(f"Selected entities total: {len(selected)}")
    log(f"Selected target entities: {len(target_entities)}")

    changed = 0
    unchanged = 0
    failed = 0

    for index, entity in enumerate(target_entities):
        handle = safe_get(entity, "Handle")
        entity_name = safe_get(entity, "EntityName")
        element = safe_get(entity, "Element")

        if isinstance(element, str) and element.startswith("<GET_ERROR"):
            log(f"ITEM[{index}] Handle={handle} | EntityName={entity_name} | Element unavailable: {element}")
            failed += 1
            continue

        before_get = safe_call(element.GetValue, TARGET_PARAMETER)
        before_comment = safe_call(element.GetValueComment, TARGET_PARAMETER)
        param_item, param_index, parameters = find_parameter_item(element, TARGET_PARAMETER)

        if param_item is None:
            log(f"ITEM[{index}] Handle={handle} | EntityName={entity_name} | {TARGET_PARAMETER} not found")
            failed += 1
            continue

        before_value = safe_get(param_item, "Value")
        param_comment = safe_get(param_item, "Comment")
        before_value_comment = safe_get(param_item, "ValueComment")

        if index < PREVIEW_LIMIT:
            log(
                "ITEM[{0}] Handle={1} | EntityName={2} | param_index={3} | comment={4} | before_value={5} | before_get={6}".format(
                    index, handle, entity_name, param_index, param_comment, before_value, before_get
                )
            )
            log(f"ITEM[{index}] Handle={handle} | before_value_comment={before_value_comment!r} | before_comment={before_comment!r}")

        if str(before_get) == TARGET_VALUE or str(before_value) == TARGET_VALUE:
            unchanged += 1
            if index < PREVIEW_LIMIT:
                log(f"ITEM[{index}] Handle={handle} | already has target value")
            continue

        set_parameter_result = safe_call(
            parameters.SetParameter,
            TARGET_PARAMETER,
            TARGET_VALUE,
            param_comment,
            before_value_comment,
        )
        update_result = safe_call(entity.Update)
        regen_result = safe_call(doc.Regen, 1)

        try:
            if app is not None:
                safe_call(app.Update)
        except Exception:
            pass

        after_value = safe_get(param_item, "Value")
        after_get = safe_call(element.GetValue, TARGET_PARAMETER)
        after_comment = safe_call(element.GetValueComment, TARGET_PARAMETER)

        if index < PREVIEW_LIMIT:
            log(f"ITEM[{index}] Handle={handle} | SetParameter result = {set_parameter_result}")
            log(f"ITEM[{index}] Handle={handle} | entity.Update result = {update_result}")
            log(f"ITEM[{index}] Handle={handle} | doc.Regen result = {regen_result}")
            log(
                "ITEM[{0}] Handle={1} | after_value={2} | after_get={3} | after_comment={4}".format(
                    index, handle, after_value, after_get, after_comment
                )
            )

        if str(after_get) == TARGET_VALUE or str(after_value) == TARGET_VALUE:
            changed += 1
        else:
            failed += 1

    log(f"Summary | selected={len(selected)} | targets={len(target_entities)} | changed={changed} | unchanged={unchanged} | failed={failed}")

    popup(
        "DTMX: selected {0}\ntargets {1}\nupdated {2}\nalready set {3}\nfailed {4}\nLog: {5}".format(
            len(selected), len(target_entities), changed, unchanged, failed, LOG_PATH
        )
    )

log("=== set_selected_ms_identifier.py end ===")
