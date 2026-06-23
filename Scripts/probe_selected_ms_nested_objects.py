import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_selected_ms_nested_objects_log.txt"
PREVIEW_LIMIT = 250


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


def short_repr(value, limit=600):
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


def dump_dir(obj, prefix):
    try:
        names = sorted(set(dir(obj)))
        log(f"{prefix}dir count = {len(names)}")
        for index, name in enumerate(names[:PREVIEW_LIMIT]):
            log(f"{prefix}dir[{index}] = {name}")
        if len(names) > PREVIEW_LIMIT:
            log(f"{prefix}dir truncated at {PREVIEW_LIMIT}")
    except Exception as ex:
        log(f"{prefix}dir ERROR: {ex}")


def dump_interesting_properties(obj, prefix):
    names = sorted(set(dir(obj)))
    interesting = []

    prefixes = (
        "Part_",
        "PartPipe_",
        "Bom_",
        "Explication_",
        "Axis_",
    )

    exact_names = {
        "Tag",
        "TagNumber",
        "Part_Tag",
        "Part_Name",
        "Part_Type",
        "Name",
        "Description",
        "Number",
        "Code",
        "Model",
        "Designation",
        "Reference",
        "Comment",
        "Element",
        "ElementAxis",
        "OwnerSegId",
        "OrderOnLine",
        "PipeLayer",
        "Handle",
        "ObjectName",
        "EntityName",
        "GetAxisParamValue",
    }

    for name in names:
        if name.startswith(prefixes) or name in exact_names:
            interesting.append(name)

    log(f"{prefix}interesting count = {len(interesting)}")

    for name in interesting:
        value = safe_get(obj, name)
        log(f"{prefix}{name} = {short_repr(value)}")


def dump_typeinfo(obj, prefix):
    try:
        typeinfo = obj._oleobj_.GetTypeInfo()
        attr = typeinfo.GetTypeAttr()
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
    except Exception as ex:
        log(f"{prefix}TYPEINFO ERROR: {ex}")


def dump_getaxisparamvalue(obj, prefix):
    method = safe_get(obj, "GetAxisParamValue")
    if isinstance(method, str) and method.startswith("<GET_ERROR"):
        log(f"{prefix}GetAxisParamValue unavailable")
        return
    if not callable(method):
        log(f"{prefix}GetAxisParamValue is not callable")
        return

    for param_name in [
        "PART_TAGNUMBER",
        "PART_TAG",
        "PART_NAME",
        "PART_TYPE",
        "PART_REFERENCE",
    ]:
        try:
            value = method(param_name)
            log(f"{prefix}GetAxisParamValue({param_name!r}) = {short_repr(value)}")
        except Exception as ex:
            log(f"{prefix}GetAxisParamValue({param_name!r}) ERROR: {ex}")


def probe_object(obj, title):
    log(f"===== {title} =====")
    log(f"{title} repr = {short_repr(obj)}")
    dump_interesting_properties(obj, f"{title} | ")
    dump_getaxisparamvalue(obj, f"{title} | ")
    dump_dir(obj, f"{title} | ")
    dump_typeinfo(obj, f"{title} | ")


def popup(message):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 0, "DTMX nested probe", 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== probe_selected_ms_nested_objects.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_application()
doc = get_document(app)

if doc is None:
    log("No active document available.")
    popup("DTMX: no active document. Check probe_selected_ms_nested_objects_log.txt")
else:
    selected = get_selected_entities(doc)
    log(f"Selected count = {len(selected)}")

    if not selected:
        popup("DTMX: no selected object. Select one pipe and rerun.")
    else:
        entity = selected[0]
        probe_object(entity, "ENTITY")

        element = safe_get(entity, "Element")
        if isinstance(element, str) and element.startswith("<GET_ERROR"):
            log(f"ENTITY.Element unavailable: {element}")
        else:
            probe_object(element, "ELEMENT")

        element_axis = safe_get(entity, "ElementAxis")
        if isinstance(element_axis, str) and element_axis.startswith("<GET_ERROR"):
            log(f"ENTITY.ElementAxis unavailable: {element_axis}")
        else:
            probe_object(element_axis, "ELEMENT_AXIS")

        popup(f"DTMX nested probe done. Log: {LOG_PATH}")

log("=== probe_selected_ms_nested_objects.py end ===")
