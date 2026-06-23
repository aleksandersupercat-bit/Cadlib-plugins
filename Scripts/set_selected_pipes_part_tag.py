import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "set_selected_pipes_part_tag_log.txt"
TAG_VALUE = "DTMX"


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def norm(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def safe_get(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception as ex:
        return f"<GET_ERROR {ex}>"


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


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX Part_Tag writer", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== set_selected_pipes_part_tag.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"Target Part_Tag value: {TAG_VALUE}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: no active document. Check set_selected_pipes_part_tag_log.txt")
else:
    selected = get_selected_entities(doc)
    pipe_entities = [item for item in selected if is_pipe_entity(item)]

    log(f"Selected entities total: {len(selected)}")
    log(f"Selected pipe entities: {len(pipe_entities)}")

    changed = 0

    for index, entity in enumerate(pipe_entities):
        handle = safe_get(entity, "Handle")
        before_tag = safe_get(entity, "Part_Tag")
        before_name = safe_get(entity, "Part_Name")
        before_type = safe_get(entity, "Part_Type")

        if index < 30:
            log(
                "PIPE[{0}] Handle={1}; Part_Name={2}; Part_Type={3}; Part_Tag(before)={4}".format(
                    index, handle, before_name, before_type, before_tag
                )
            )

        try:
            entity.Part_Tag = TAG_VALUE
            after_tag = safe_get(entity, "Part_Tag")
            log(
                "SET_OK Handle={0}; Part_Tag(before)={1}; Part_Tag(after)={2}".format(
                    handle, before_tag, after_tag
                )
            )
            changed += 1
        except Exception as ex:
            log(
                "SET_FAIL Handle={0}; Part_Tag(before)={1}; Error={2}".format(
                    handle, before_tag, ex
                )
            )

    popup(
        "DTMX: selected pipes {0}\nPart_Tag updated {1}\nLog: {2}".format(
            len(pipe_entities), changed, LOG_PATH
        )
    )

log("=== set_selected_pipes_part_tag.py end ===")
