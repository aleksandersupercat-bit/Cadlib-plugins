import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "dump_selected_ms_parameters_log.txt"


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


def dump_parameter_like_properties(entity):
    names = sorted(set(dir(entity)))
    interesting = []

    prefixes = (
        "Part_",
        "PartPipe_",
        "Bom_",
        "Explication_",
        "Axis_",
    )
    exact_names = {
        "Insulation",
        "HasInsulation",
        "PipeLayer",
        "OwnerSegId",
        "OrderOnLine",
        "Position",
        "PointStart",
        "PointEnd",
        "Element",
        "ElementAxis",
        "LimitSlope",
    }

    for name in names:
        if name.startswith(prefixes) or name in exact_names:
            interesting.append(name)

    log(f"Interesting property count: {len(interesting)}")

    for name in interesting:
        value = safe_get(entity, name)
        log(f"{name} = {value}")


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX parameter dump", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== dump_selected_ms_parameters.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: no active document. Check dump_selected_ms_parameters_log.txt")
else:
    selected = get_selected_entities(doc)
    log(f"Selected entities total: {len(selected)}")

    if not selected:
        popup("DTMX: no selected entity. Select one pipe and rerun.")
    else:
        entity = selected[0]
        log(f"ObjectName = {safe_get(entity, 'ObjectName')}")
        log(f"EntityName = {safe_get(entity, 'EntityName')}")
        log(f"Handle = {safe_get(entity, 'Handle')}")
        dump_parameter_like_properties(entity)
        popup(f"DTMX parameter dump done. Log: {LOG_PATH}")

log("=== dump_selected_ms_parameters.py end ===")
