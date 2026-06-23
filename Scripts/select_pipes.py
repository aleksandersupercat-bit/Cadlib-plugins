import datetime
from pathlib import Path

import pythoncom
import win32com.client


LOG_PATH = Path.home() / "Desktop" / "select_pipes_log.txt"


def log(text):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    current = ""
    if LOG_PATH.exists():
        current = LOG_PATH.read_text(encoding="utf-8", errors="ignore")
    LOG_PATH.write_text(current + line + "\n", encoding="utf-8")


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


def safe_get(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception:
        return None


def is_pipe_entity(entity):
    object_name = norm(safe_get(entity, "ObjectName"))
    entity_name = norm(safe_get(entity, "EntityName"))
    return object_name == "vcssubsegment" or entity_name == "vcssubsegment"


def collect_pipes(doc):
    total = 0
    result = []

    for entity in doc.ModelSpace:
        total += 1

        if not is_pipe_entity(entity):
            continue

        result.append(entity)

        if len(result) <= 30:
            log(
                "PIPE ObjectName={0}; EntityName={1}; Layer={2}; Handle={3}".format(
                    safe_get(entity, "ObjectName"),
                    safe_get(entity, "EntityName"),
                    safe_get(entity, "Layer"),
                    safe_get(entity, "Handle"),
                )
            )

    log(f"Scanned ModelSpace entities: {total}")
    log(f"Pipe objects found: {len(result)}")
    return total, result


def clear_selection_set(doc, name):
    try:
        for selection_set in doc.SelectionSets:
            if norm(selection_set.Name) == norm(name):
                selection_set.Delete()
                log(f"Deleted previous selection set {name}")
                return
    except Exception as ex:
        log(f"SelectionSets cleanup failed: {ex}")


def fill_selection_set(doc, name, items):
    if not items:
        return False

    try:
        clear_selection_set(doc, name)
        selection_set = doc.SelectionSets.Add(name)
        payload = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, items)
        selection_set.AddItems(payload)
        log(f"Selection set {name} created and filled")
        return True
    except Exception as ex:
        log(f"Selection set {name} failed: {ex}")
        return False


def fill_active_selection(doc, items):
    if not items:
        return False

    payload = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, items)

    for attr_name in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            selection = getattr(doc, attr_name)
            try:
                selection.Clear()
            except Exception:
                pass

            selection.AddItems(payload)
            log(f"{attr_name}.AddItems executed")
            return True
        except Exception as ex:
            log(f"{attr_name}.AddItems failed: {ex}")

    return False


def highlight_items(items):
    count = 0
    for item in items:
        try:
            item.Highlight(True)
            count += 1
        except Exception as ex:
            log(f"Highlight failed: {ex}")
    log(f"Highlighted items: {count}")
    return count


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX pipe selection", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


log("=== select_pipes.py start ===")
log(f"Log path: {LOG_PATH}")
log("Mode: pure Python, vCSSubSegment only")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: active document not found. Check select_pipes_log.txt on Desktop.")
else:
    total_entities, pipes = collect_pipes(doc)
    selection_ok = fill_selection_set(doc, "DTMX_PIPES", pipes)
    active_ok = fill_active_selection(doc, pipes)
    highlighted = highlight_items(pipes)

    popup(
        "DTMX: total objects {0}\nPipes {1}\nSelectionSet: {2}\nActiveSelection: {3}\nHighlight: {4}\nLog: {5}".format(
            total_entities,
            len(pipes),
            "OK" if selection_ok else "FAIL",
            "OK" if active_ok else "FAIL",
            highlighted,
            LOG_PATH,
        )
    )

log("=== select_pipes.py end ===")
