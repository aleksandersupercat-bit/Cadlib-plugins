# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import pythoncom
import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_selected_ms_com_relations_log.txt"
MAX_ITEMS = 300
SHOW_POPUP = False


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def popup(message):
    if not SHOW_POPUP:
        log(f"Popup skipped: {message}")
        return
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX COM relations probe", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


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


def is_error(value):
    return isinstance(value, str) and (value.startswith("<GET_ERROR") or value.startswith("<CALL_ERROR"))


def describe_obj(obj):
    fields = [
        "ObjectName",
        "EntityName",
        "Handle",
        "Name",
        "Description",
        "ElementId",
        "ObjectId",
        "PathFromRoot",
        "Level",
        "ModelUID",
    ]
    parts = []
    for field in fields:
        value = safe_get(obj, field)
        if not is_error(value) and value not in (None, ""):
            parts.append(f"{field}={value!r}")
    return " | ".join(parts) if parts else repr(obj)


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
    result = []
    seen = set()
    for attr_name in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            selection = getattr(doc, attr_name)
            log(f"{attr_name}.Count = {safe_get(selection, 'Count')}")
            for entity in selection:
                key = str(safe_get(entity, "Handle"))
                if key not in seen:
                    seen.add(key)
                    result.append(entity)
        except Exception as ex:
            log(f"{attr_name} failed: {ex}")
    return result


def enum_collection(obj, attr, max_items=MAX_ITEMS):
    collection = safe_get(obj, attr)
    if is_error(collection) or collection is None:
        log(f"  {attr}: unavailable: {collection}")
        return []

    count = safe_get(collection, "Count")
    log(f"  {attr}: collection={describe_obj(collection)} Count={count!r}")

    items = []
    try:
        for index, item in enumerate(collection):
            if index >= max_items:
                log(f"    {attr}[...] truncated at {max_items}")
                break
            items.append(item)
            log(f"    {attr}[{index}] {describe_obj(item)}")
    except Exception as ex:
        log(f"    {attr} enumeration failed: {ex}")
    return items


def dump_named_object(obj, prefix, attr):
    value = safe_get(obj, attr)
    if is_error(value) or value is None:
        log(f"{prefix}{attr}: {value}")
        return None
    log(f"{prefix}{attr}: {describe_obj(value)}")
    return value


def dump_axis_call(axis, prefix, name, *args):
    func = safe_get(axis, name)
    if is_error(func):
        log(f"{prefix}{name}: unavailable: {func}")
        return None
    value = safe_call(func, *args)
    if is_error(value) or value is None:
        log(f"{prefix}{name}: {value}")
        return None
    log(f"{prefix}{name}: {describe_obj(value)}")
    return value


def dump_axis_scalar_call(axis, prefix, name, *args):
    func = safe_get(axis, name)
    if is_error(func):
        log(f"{prefix}{name}: unavailable: {func}")
        return
    value = safe_call(func, *args)
    log(f"{prefix}{name}: {value!r}")


def dump_element_tree(element, prefix, depth=0, max_depth=4):
    if depth > max_depth or element is None or is_error(element):
        return
    log(f"{prefix}TREE depth={depth} {describe_obj(element)}")
    dump_parameters(element, f"{prefix}  ", limit=12)
    for attr in ["SubElements", "SubElementsAll", "Root", "Parent", "PathFromRoot"]:
        value = safe_get(element, attr)
        if is_error(value) or value is None:
            log(f"{prefix}  {attr}: {value}")
            continue
        if attr in ["SubElements", "SubElementsAll", "PathFromRoot"]:
            items = []
            try:
                count = safe_get(value, "Count")
                log(f"{prefix}  {attr}.Count = {count!r}")
                for index, item in enumerate(value):
                    if index >= 30:
                        log(f"{prefix}    {attr} truncated at 30")
                        break
                    items.append(item)
                    log(f"{prefix}    {attr}[{index}] {describe_obj(item)}")
            except Exception as ex:
                log(f"{prefix}  {attr} enumeration failed: {ex}")
            if attr == "SubElements":
                for item in items:
                    dump_element_tree(item, prefix + "    ", depth + 1, max_depth)
        else:
            log(f"{prefix}  {attr}: {describe_obj(value)}")


def dump_parameters(obj, prefix, limit=20):
    parameters = safe_get(obj, "Parameters")
    if is_error(parameters) or parameters is None:
        log(f"{prefix}Parameters unavailable: {parameters}")
        return
    count = safe_get(parameters, "Count")
    log(f"{prefix}Parameters.Count = {count!r}")
    try:
        for index, param in enumerate(parameters):
            if index >= limit:
                log(f"{prefix}Parameters truncated at {limit}")
                break
            name = safe_get(param, "Name")
            value = safe_get(param, "Value")
            comment = safe_get(param, "Comment")
            value_comment = safe_get(param, "ValueComment")
            log(f"{prefix}PARAM[{index}] Name={name!r} Value={value!r} Comment={comment!r} ValueComment={value_comment!r}")
    except Exception as ex:
        log(f"{prefix}Parameters enumeration failed: {ex}")


def dump_typeinfo(obj, prefix):
    ole = getattr(obj, "_oleobj_", None)
    if ole is None:
        log(f"{prefix}No _oleobj_")
        return
    try:
        typeinfo = ole.GetTypeInfo()
        attr = typeinfo.GetTypeAttr()
        log(f"{prefix}TYPEINFO funcs={attr.cFuncs} vars={attr.cVars}")
        for index in range(min(attr.cFuncs, 80)):
            try:
                desc = typeinfo.GetFuncDesc(index)
                names = typeinfo.GetNames(desc.memid)
                log(f"{prefix}FUNC memid={desc.memid} invkind={desc.invkind} names={names}")
            except Exception as ex:
                log(f"{prefix}FUNC[{index}] failed: {ex}")
    except Exception as ex:
        log(f"{prefix}TypeInfo failed: {ex}")


def dump_entity_relations(entity, index):
    log("")
    log(f"=== SELECTED[{index}] ENTITY ===")
    log(describe_obj(entity))
    dump_typeinfo(entity, "ENTITY | ")

    element = safe_get(entity, "Element")
    if not is_error(element) and element is not None:
        log("ENTITY.Element:")
        log(f"  {describe_obj(element)}")
        dump_typeinfo(element, "ELEMENT | ")
        dump_parameters(element, "  Element.")
        dump_element_tree(element, "  ElementTree.", max_depth=5)
        for attr in ["Children", "SubElements", "Subelements", "AllSubelements", "Parents", "Path", "Links", "LinkedObjects"]:
            enum_collection(element, attr, max_items=40)
    else:
        log(f"ENTITY.Element unavailable: {element}")

    axis = safe_get(entity, "ElementAxis")
    if not is_error(axis) and axis is not None:
        log("ENTITY.ElementAxis:")
        log(f"  {describe_obj(axis)}")
        dump_typeinfo(axis, "AXIS | ")
        log("  Axis scalar properties:")
        for attr in [
            "Length",
            "LimitSlope",
            "HasEquipmentNodeStart",
            "HasEquipmentNodeEnd",
            "HasStartTee",
            "HasEndTee",
            "HasStartPipe",
            "HasEndPipe",
        ]:
            value = safe_get(axis, attr)
            log(f"    {attr} = {value!r}")

        log("  Axis endpoint objects:")
        for attr in [
            "EquipmentNodeStart",
            "EquipmentNodeEnd",
            "StartTee",
            "EndTee",
            "StartPipe",
            "EndPipe",
        ]:
            dump_named_object(axis, "    ", attr)

        log("  Axis method links:")
        dump_axis_call(axis, "    ", "GetFirstComponent")
        dump_axis_call(axis, "    ", "GetLastComponent")
        dump_axis_call(axis, "    ", "GetPrevComponent", entity)
        dump_axis_call(axis, "    ", "GetNextComponent", entity)
        for flags in [
            (True, True, True, True, True),
            (False, False, True, False, False),
            (False, True, False, True, False),
            (False, False, False, False, True),
        ]:
            dump_axis_scalar_call(axis, "    ", "CountItems", *flags)
        for param_name in ["PART_NAME", "PART_TAG", "PART_TAGNUMBER", "LINE_SYSTEM_TAG", "LINE_SYSTEM_TYPE"]:
            dump_axis_scalar_call(axis, "    ", "GetFromObjParamVal", param_name)
            dump_axis_scalar_call(axis, "    ", "GetToObjParamVal", param_name)

        axis_element = safe_get(axis, "Element")
        if not is_error(axis_element) and axis_element is not None:
            log("  ElementAxis.Element:")
            log(f"    {describe_obj(axis_element)}")
            dump_parameters(axis_element, "    Axis.Element.")
        components = enum_collection(axis, "Components", max_items=MAX_ITEMS)
        log(f"  Components usable count = {len(components)}")
        for component_index, component in enumerate(components[:80]):
            component_element = safe_get(component, "Element")
            tag = ""
            if not is_error(component_element) and component_element is not None:
                part_name = safe_call(component_element.GetValue, "PART_NAME") if hasattr(component_element, "GetValue") else ""
                part_tag = safe_call(component_element.GetValue, "PART_TAG") if hasattr(component_element, "GetValue") else ""
                part_tagnumber = safe_call(component_element.GetValue, "PART_TAGNUMBER") if hasattr(component_element, "GetValue") else ""
                tag = f" | PART_NAME={part_name!r} PART_TAG={part_tag!r} PART_TAGNUMBER={part_tagnumber!r}"
            log(f"    COMPONENT_SUMMARY[{component_index}] {describe_obj(component)}{tag}")
    else:
        log(f"ENTITY.ElementAxis unavailable: {axis}")


reset_log()
log("=== probe_selected_ms_com_relations.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_application()
doc = get_document(app)
if doc is None:
    log("ABORT: no active document")
    popup(f"No active document.\nLog: {LOG_PATH}")
    raise SystemExit

log(f"Document.Name = {safe_get(doc, 'Name')!r}")
entities = get_selected_entities(doc)
log(f"Selected unique entities = {len(entities)}")
if not entities:
    popup(f"Select one Model Studio object first.\nLog: {LOG_PATH}")
    raise SystemExit

for entity_index, entity in enumerate(entities[:5]):
    dump_entity_relations(entity, entity_index)

popup(f"DTMX COM relations probe done.\nSelected: {len(entities)}\nLog: {LOG_PATH}")
log("=== probe_selected_ms_com_relations.py end ===")
