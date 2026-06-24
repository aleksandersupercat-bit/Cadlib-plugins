# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_pipe_parameter_surface_log.txt"


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


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception as ex:
        text = f"<repr error: {ex}>"
    if len(text) > limit:
        text = text[:limit] + "...<truncated>"
    return text


def get_app():
    for progid in [
        "nanoCADx64.Application.24.0",
        "nanoCADx64.Application",
        "nanoCAD.Application.24.0",
        "nanoCAD.Application",
    ]:
        try:
            app = win32com.client.GetActiveObject(progid)
            log(f"Connected via {progid}")
            return app
        except Exception as ex:
            log(f"{progid} failed: {ex}")
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


def to_entity_property_name(parameter_name):
    if not parameter_name:
        return None
    tokens = parameter_name.split("_")
    upper_name = parameter_name.upper()
    special = {
        "PART_PIPE_DN": "PartPipe_DN",
        "PART_PIPE_DIAMETER": "PartPipe_Diam",
        "PIPE_THICKNESS": "PartPipe_Thickness",
    }
    if upper_name in special:
        return special[upper_name]
    if len(tokens) >= 2 and tokens[0].upper() == "PART":
        if len(tokens) >= 3 and tokens[1].upper() == "PIPE":
            return "PartPipe_" + "_".join(token.capitalize() for token in tokens[2:])
        return "Part_" + "_".join(token.capitalize() for token in tokens[1:])
    if len(tokens) >= 2 and tokens[0].upper() == "BOM":
        return "Bom_" + "_".join(token.capitalize() for token in tokens[1:])
    if len(tokens) >= 2 and tokens[0].upper() == "EXPLICATION":
        return "Explication_" + "_".join(token.capitalize() for token in tokens[1:])
    if len(tokens) >= 2 and tokens[0].upper() == "AXIS":
        return "Axis_" + "_".join(token.capitalize() for token in tokens[1:])
    return None


reset_log()
log("=== probe_pipe_parameter_surface.py start ===")
app = get_app()
if app is None:
    log("ABORT: application not found")
    raise SystemExit

doc = app.ActiveDocument
log(f"Document = {safe_repr(safe_get(doc, 'Name'))}")
entity = get_selected_entity(doc)
if entity is None:
    log("ABORT: no selected entity")
    raise SystemExit

element = entity.Element
parameters = element.Parameters

entity_dir = set(dir(entity))
rows = []
count = 0
for item in parameters:
    count += 1
    name = safe_get(item, "Name")
    value = safe_get(item, "Value")
    comment = safe_get(item, "Comment")
    value_comment = safe_get(item, "ValueComment")
    prop_name = to_entity_property_name(str(name))
    prop_exists = bool(prop_name and prop_name in entity_dir)
    prop_value = safe_get(entity, prop_name) if prop_exists else None
    rows.append(
        {
            "name": name,
            "value": value,
            "comment": comment,
            "value_comment": value_comment,
            "prop_name": prop_name,
            "prop_exists": prop_exists,
            "prop_value": prop_value,
        }
    )

log(f"Enumerated parameters count = {count}")
direct = [row for row in rows if row["prop_exists"]]
only_element = [row for row in rows if not row["prop_exists"]]
log(f"Direct entity property matches = {len(direct)}")
log(f"Element.Parameters only = {len(only_element)}")

for row in direct:
    log(
        "DIRECT | {0} -> {1} | param={2} | entity={3}".format(
            row["name"],
            row["prop_name"],
            safe_repr(row["value"]),
            safe_repr(row["prop_value"]),
        )
    )

for row in only_element:
    log(
        "ONLY_ELEMENT | {0} | value={1} | comment={2} | value_comment={3}".format(
            row["name"],
            safe_repr(row["value"]),
            safe_repr(row["comment"]),
            safe_repr(row["value_comment"]),
        )
    )

log("=== probe_pipe_parameter_surface.py end ===")
