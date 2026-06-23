# -*- coding: utf-8 -*-

from System import Array
from System.Collections.Generic import List


def log(message):
    text = str(message)
    print(text)
    try:
        CLMainForm.WritePythonLog("[select_all_pipes.py] " + text)
    except Exception:
        try:
            CLMainForm.WriteLog("[select_all_pipes.py] " + text)
        except Exception:
            pass


def safe_call(label, fn):
    try:
        value = fn()
        log(label + ": " + str(value))
        return value
    except Exception as ex:
        log(label + " ERROR: " + str(ex))
        return None


def normalize(text):
    if text is None:
        return ""
    return str(text).strip().lower()


def looks_like_pipe_part_type(value):
    text = normalize(value)
    if not text:
        return False

    markers = [
        u"\u0442\u0440\u0443\u0431",
        u"\u0442\u0440\u0443\u0431\u0430",
        u"\u0442\u0440\u0443\u0431\u043e\u043f",
        "pipe",
        "pipeline",
    ]

    for marker in markers:
        if marker in text:
            return True

    return False


def distinct_part_types(values):
    result = []
    seen = set()

    if values is None:
        return result

    for value in values:
        text = str(value).strip()
        key = normalize(text)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(text)

    return result


def get_pipe_part_types():
    values = safe_call("PART_TYPE values via CLMainForm", lambda: CLMainForm.GetPartTypesForPython())
    result = []

    if values is not None:
        for value in values:
            if looks_like_pipe_part_type(value):
                result.append(str(value).strip())

    result = distinct_part_types(result)

    if result:
        return result

    fallback = [
        u"\u0422\u0440\u0443\u0431\u0430",
        u"\u0422\u0440\u0443\u0431\u043e\u043f\u0440\u043e\u0432\u043e\u0434",
        "Pipe",
        "Pipeline",
    ]

    log("Pipe-like PART_TYPE values were not auto-detected. Using fallback list.")
    return fallback


def get_objects_by_part_type(part_type):
    part_type_id = safe_call("PART_TYPE id", lambda: Library.GetParamDefId("PART_TYPE"))
    if part_type_id is None or int(part_type_id) <= 0:
        return []

    objects = safe_call(
        "GetObjectParametersByValues(" + str(part_type) + ")",
        lambda: Library.GetObjectParametersByValues(part_type_id, part_type, True, ';')
    )

    result = []
    if objects is None:
        return result

    for obj in objects:
        if obj is not None:
            result.append(obj)

    return result


def collect_pipe_objects():
    result = []
    seen_ids = set()
    used_types = []

    for part_type in get_pipe_part_types():
        objects = get_objects_by_part_type(part_type)
        if not objects:
            continue

        used_types.append(part_type)

        for obj in objects:
            object_id = int(obj.idObject)
            if object_id in seen_ids:
                continue
            seen_ids.add(object_id)
            result.append(obj)

    return used_types, result


def set_selection(ids):
    if not ids:
        return False

    net_list = List[int]()
    for object_id in ids:
        net_list.Add(int(object_id))

    result = safe_call("SetSelectedObjects(List[int])", lambda: Library.SetSelectedObjects(net_list))
    if isinstance(result, bool) and result:
        return True

    net_array = Array[int](ids)
    result = safe_call("SetSelectedObjects(Array[int])", lambda: Library.SetSelectedObjects(net_array))
    if isinstance(result, bool) and result:
        return True

    if len(ids) == 1:
        result = safe_call("SetSingleSelection", lambda: Library.SetSingleSelection(int(ids[0])))
        if isinstance(result, bool) and result:
            return True

    return result is not None


log("=== Select all pipes start ===")
safe_call("Library type", lambda: Library.GetType().FullName)
safe_call("DBBrowser type", lambda: DBBrowser.GetType().FullName)

part_types, objects = collect_pipe_objects()

if part_types:
    log("Pipe-like PART_TYPE values: " + ", ".join(part_types))
else:
    log("No pipe-like PART_TYPE values found.")

if not objects:
    log("No pipe objects found. Run diagnostics.py first and inspect actual PART_TYPE values.")
else:
    ids = [int(obj.idObject) for obj in objects]
    success = set_selection(ids)
    log("Selected object count: " + str(len(ids)))
    log("Selection API success: " + str(success))

    preview_count = min(len(objects), 15)
    for index in range(preview_count):
        obj = objects[index]
        log("selected[{0}] idObject={1}; name={2}".format(index, obj.idObject, obj.Name))

    if len(objects) > preview_count:
        log("Selected list truncated at " + str(preview_count) + " objects")

log("=== Select all pipes end ===")
