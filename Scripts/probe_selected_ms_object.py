import datetime
import inspect
from pathlib import Path

import pythoncom
import pywintypes
import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_selected_ms_object_log.txt"
PREVIEW_LIMIT = 200


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
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


def safe_call(label, fn):
    try:
        value = fn()
        log(f"{label}: {value}")
        return value
    except Exception as ex:
        log(f"{label} ERROR: {ex}")
        return None


def short_repr(value, limit=400):
    try:
        text = repr(value)
    except Exception as ex:
        text = f"<repr error: {ex}>"
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


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


def dump_basic_identity(entity, prefix):
    log(f"{prefix}--- BASIC IDENTITY ---")
    for attr_name in [
        "ObjectName",
        "EntityName",
        "Handle",
        "Layer",
        "Color",
        "Linetype",
        "LinetypeScale",
        "Lineweight",
        "ObjectID",
        "OwnerID",
        "Visible",
        "TrueColor",
        "Hyperlinks",
        "PlotStyleName",
        "HasExtensionDictionary",
    ]:
        value = safe_get(entity, attr_name)
        log(f"{prefix}{attr_name} = {short_repr(value)}")


def dump_dir(entity, prefix):
    log(f"{prefix}--- DIR ATTRIBUTES ---")
    try:
        names = sorted(set(dir(entity)))
        log(f"{prefix}dir count = {len(names)}")
        for index, name in enumerate(names[:PREVIEW_LIMIT]):
            log(f"{prefix}dir[{index}] = {name}")
        if len(names) > PREVIEW_LIMIT:
            log(f"{prefix}dir truncated at {PREVIEW_LIMIT}")
    except Exception as ex:
        log(f"{prefix}dir ERROR: {ex}")


def dump_prop_maps(entity, prefix):
    log(f"{prefix}--- PYWIN32 PROP MAPS ---")
    for map_name in ["_prop_map_get_", "_prop_map_put_", "_olerepr_"]:
        value = safe_get(entity, map_name)
        log(f"{prefix}{map_name} = {short_repr(value, 1200)}")


def dump_typeinfo(entity, prefix):
    log(f"{prefix}--- COM TYPEINFO ---")
    try:
        typeinfo = entity._oleobj_.GetTypeInfo()
        attr = typeinfo.GetTypeAttr()
        log(f"{prefix}TypeAttr = {short_repr(attr)}")

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

        if func_count > PREVIEW_LIMIT:
            log(f"{prefix}FUNC truncated at {PREVIEW_LIMIT}")

        for index in range(min(var_count, PREVIEW_LIMIT)):
            try:
                vardesc = typeinfo.GetVarDesc(index)
                names = typeinfo.GetNames(vardesc[0])
                log(f"{prefix}VAR[{index}] dispid={vardesc[0]} names={short_repr(names)}")
            except Exception as ex:
                log(f"{prefix}VAR[{index}] ERROR: {ex}")

        if var_count > PREVIEW_LIMIT:
            log(f"{prefix}VAR truncated at {PREVIEW_LIMIT}")
    except Exception as ex:
        log(f"{prefix}TYPEINFO ERROR: {ex}")


def dump_known_modelstudio_candidates(entity, prefix):
    log(f"{prefix}--- KNOWN MODEL STUDIO / NANO PROBES ---")
    candidate_names = [
        "PartType",
        "PART_TYPE",
        "PART_TAGNUMBER",
        "TagNumber",
        "Description",
        "Name",
        "Type",
        "ObjectType",
        "EffectiveName",
        "StyleName",
        "Material",
        "Application",
        "Document",
        "Database",
        "GetXData",
        "GetExtensionDictionary",
        "GetDynamicBlockProperties",
        "GetAttributes",
        "GetConstantAttributes",
        "GetBoundingBox",
        "Coordinates",
        "InsertionPoint",
        "Normal",
        "Rotation",
        "Area",
        "Length",
    ]

    for name in candidate_names:
        value = safe_get(entity, name)
        log(f"{prefix}{name} = {short_repr(value)}")


def dump_noarg_method_result(entity, method_name, prefix):
    value = safe_get(entity, method_name)
    if isinstance(value, str) and value.startswith("<GET_ERROR"):
        log(f"{prefix}{method_name} unavailable")
        return
    if not callable(value):
        log(f"{prefix}{method_name} is not callable")
        return

    try:
        result = value()
        log(f"{prefix}{method_name}() => {short_repr(result, 1200)}")
    except Exception as ex:
        log(f"{prefix}{method_name}() ERROR: {ex}")


def dump_common_method_calls(entity, prefix):
    log(f"{prefix}--- COMMON METHOD CALLS ---")
    for method_name in [
        "GetAttributes",
        "GetConstantAttributes",
        "GetDynamicBlockProperties",
        "GetExtensionDictionary",
    ]:
        dump_noarg_method_result(entity, method_name, prefix)

    try:
        if callable(safe_get(entity, "GetBoundingBox")):
            min_pt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0.0, 0.0, 0.0])
            max_pt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0.0, 0.0, 0.0])
            entity.GetBoundingBox(min_pt, max_pt)
            log(f"{prefix}GetBoundingBox() invoked")
        else:
            log(f"{prefix}GetBoundingBox unavailable")
    except Exception as ex:
        log(f"{prefix}GetBoundingBox ERROR: {ex}")


def dump_xdata(entity, prefix):
    log(f"{prefix}--- XDATA PROBE ---")
    method = safe_get(entity, "GetXData")
    if not callable(method):
        log(f"{prefix}GetXData unavailable")
        return

    for app_name in ["*", "MS", "MODELSTUDIO", "VCS", "NANOCAD", ""]:
        try:
            type_codes = []
            values = []
            method(app_name, type_codes, values)
            log(
                f"{prefix}GetXData({app_name!r}) => types={short_repr(type_codes, 800)} values={short_repr(values, 1200)}"
            )
        except Exception as ex:
            log(f"{prefix}GetXData({app_name!r}) ERROR: {ex}")


def dump_selected_overview(selected):
    log("--- SELECTED OVERVIEW ---")
    log(f"Selected count = {len(selected)}")
    for index, entity in enumerate(selected[:50]):
        log(
            "SELECTED[{0}] ObjectName={1}; EntityName={2}; Layer={3}; Handle={4}".format(
                index,
                safe_get(entity, "ObjectName"),
                safe_get(entity, "EntityName"),
                safe_get(entity, "Layer"),
                safe_get(entity, "Handle"),
            )
        )
    if len(selected) > 50:
        log("Selected overview truncated at 50")


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX object probe", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== probe_selected_ms_object.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: no active document. Check probe_selected_ms_object_log.txt")
else:
    safe_call("Document.Name", lambda: doc.Name)
    selected = get_selected_entities(doc)
    dump_selected_overview(selected)

    if not selected:
        popup("DTMX: no selected objects. Select one Model Studio element and rerun.")
    else:
        entity = selected[0]
        log("--- PROBING FIRST SELECTED ENTITY ONLY ---")
        dump_basic_identity(entity, "")
        dump_known_modelstudio_candidates(entity, "")
        dump_dir(entity, "")
        dump_prop_maps(entity, "")
        dump_typeinfo(entity, "")
        dump_common_method_calls(entity, "")
        dump_xdata(entity, "")
        popup(f"DTMX probe done. Selected count={len(selected)}. Log: {LOG_PATH}")

log("=== probe_selected_ms_object.py end ===")
