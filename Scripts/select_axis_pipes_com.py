# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import pythoncom
import win32com.client
from win32com.client import VARIANT


LOG_PATH = Path.home() / "Desktop" / "select_axis_pipes_com_log.txt"
TARGET_ENTITY_NAMES = {"vcssubsegment"}


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


def norm(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX axis select", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


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


def get_first_selected_entity(doc):
    for attr_name in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            selection = list(getattr(doc, attr_name))
            log(f"{attr_name} count = {len(selection)}")
            if selection:
                return selection[0]
        except Exception as ex:
            log(f"{attr_name} failed: {ex}")
    return None


def add_to_active_selections(doc, entities):
    variant = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, tuple(entities))
    for attr_name in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            selection = getattr(doc, attr_name)
            try:
                selection.Clear()
            except Exception as ex:
                log(f"{attr_name}.Clear failed: {ex}")
            selection.AddItems(variant)
            log(f"{attr_name}.AddItems OK | count = {selection.Count}")
        except Exception as ex:
            log(f"{attr_name}.AddItems failed: {ex}")


reset_log()
log("=== select_axis_pipes_com.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_application()
doc = get_document(app)
if doc is None:
    log("ABORT: no active document")
    popup(f"No active document.\nLog: {LOG_PATH}")
    raise SystemExit

source_entity = get_first_selected_entity(doc)
if source_entity is None:
    log("ABORT: no selected source entity")
    popup(f"Select one pipe first.\nLog: {LOG_PATH}")
    raise SystemExit

log(f"Source entity ObjectName = {safe_get(source_entity, 'ObjectName')}")
log(f"Source entity Handle = {safe_get(source_entity, 'Handle')}")

element_axis = safe_get(source_entity, "ElementAxis")
if isinstance(element_axis, str) and element_axis.startswith("<GET_ERROR"):
    log(f"ABORT: ElementAxis unavailable: {element_axis}")
    popup(f"ElementAxis unavailable.\nLog: {LOG_PATH}")
    raise SystemExit

try:
    components = list(element_axis.Components)
except Exception as ex:
    log(f"ABORT: ElementAxis.Components failed: {ex}")
    popup(f"Components unavailable.\nLog: {LOG_PATH}")
    raise SystemExit

log(f"Axis components total = {len(components)}")

pipes = []
for index, component in enumerate(components):
    object_name = norm(safe_get(component, "ObjectName"))
    handle = safe_get(component, "Handle")
    log(f"COMP[{index}] ObjectName={object_name!r} Handle={handle!r}")
    if object_name in TARGET_ENTITY_NAMES:
        pipes.append(component)

log(f"Axis pipe subsegments = {len(pipes)}")

if not pipes:
    popup(f"No vCSSubSegment objects found.\nLog: {LOG_PATH}")
    raise SystemExit

add_to_active_selections(doc, pipes)

for component in pipes:
    try:
        component.Highlight(True)
    except Exception as ex:
        log(f"Highlight failed for {safe_get(component, 'Handle')}: {ex}")

popup(f"Selected axis pipes: {len(pipes)}\nLog: {LOG_PATH}")
log("=== select_axis_pipes_com.py end ===")
