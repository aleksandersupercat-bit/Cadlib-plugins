from System import Array
from System.Collections.Generic import List
from System.IO import File
from System.Text import Encoding


LOG_LINES = []


def write_external_log():
    path = None
    try:
        path = PythonLogFilePath
    except Exception:
        path = None

    if not path:
        return

    try:
        File.AppendAllText(path, "\r\n".join(LOG_LINES) + "\r\n", Encoding.UTF8)
    except Exception:
        pass


def log(message):
    text = str(message)
    LOG_LINES.append(text)
    print(text)
    try:
        CLMainForm.WritePythonLog("[select_all_pipes_probe.py] " + text)
    except Exception:
        try:
            CLMainForm.WriteLog("[select_all_pipes_probe.py] " + text)
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
    markers = [
        u"\u0442\u0440\u0443\u0431",
        "pipe",
        "pipeline",
    ]

    for marker in markers:
        if marker in text:
            return True

    return False


def preview_sequence(label, values, limit):
    if values is None:
        log(label + ": <None>")
        return

    try:
        count = len(values)
    except Exception:
        count = None

    if count is not None:
        log(label + " count: " + str(count))

    index = 0
    for value in values:
        if index >= limit:
            log(label + " truncated at " + str(limit))
            break
        log(label + "[" + str(index) + "]=" + str(value))
        index += 1


def get_pipe_part_types():
    raw_values = safe_call("CLMainForm.GetPartTypesForPython", lambda: CLMainForm.GetPartTypesForPython())
    result = []

    if raw_values is not None:
        preview_sequence("PART_TYPE raw", raw_values, 30)
        for value in raw_values:
            if looks_like_pipe_part_type(value):
                result.append(str(value).strip())

    seen = set()
    distinct = []
    for value in result:
        key = normalize(value)
        if not key or key in seen:
            continue
        seen.add(key)
        distinct.append(value)

    if distinct:
        return distinct

    fallback = [
        u"\u0422\u0440\u0443\u0431\u0430",
        u"\u0422\u0440\u0443\u0431\u043e\u043f\u0440\u043e\u0432\u043e\u0434",
        "Pipe",
        "Pipeline",
    ]
    log("Auto-detect returned nothing; using fallback pipe PART_TYPE list.")
    return fallback


def get_objects_for_part_type(part_type):
    result = safe_call(
        "CLMainForm.GetObjectsByPartTypeForPython(" + str(part_type) + ")",
        lambda: CLMainForm.GetObjectsByPartTypeForPython(part_type)
    )

    if result is None:
        return []

    rows = []
    for obj in result:
        if obj is not None:
            rows.append(obj)

    log("Objects for PART_TYPE '" + str(part_type) + "': " + str(len(rows)))
    for index, obj in enumerate(rows[:10]):
        log("  obj[" + str(index) + "] id=" + str(obj.idObject) + "; name=" + str(obj.Name))

    if len(rows) > 10:
        log("  object preview truncated at 10")

    return rows


def collect_pipe_ids():
    pipe_types = get_pipe_part_types()
    log("Pipe-like PART_TYPE list: " + ", ".join(pipe_types))

    result_ids = []
    seen = set()

    for part_type in pipe_types:
        for obj in get_objects_for_part_type(part_type):
            object_id = int(obj.idObject)
            if object_id in seen:
                continue
            seen.add(object_id)
            result_ids.append(object_id)

    return result_ids


def read_selected_ids():
    selected = safe_call("DBBrowser.GetSelectedObjects(False)", lambda: DBBrowser.GetSelectedObjects(False))
    ids = []

    if selected is None:
        return ids

    for obj in selected:
        try:
            ids.append(int(obj.idObject))
        except Exception:
            pass

    log("Current selected ids: " + ",".join([str(x) for x in ids[:20]]) if ids else "Current selected ids: <empty>")
    if len(ids) > 20:
        log("Selected ids preview truncated at 20")

    return ids


def try_selection_methods(ids):
    methods = [
        ("SetEmptySelection", lambda: Library.SetEmptySelection()),
        ("SetSelectedObjects(List[int])", lambda: Library.SetSelectedObjects(build_net_list(ids))),
        ("SetSelectedObjects(Array[int])", lambda: Library.SetSelectedObjects(Array[int](ids))),
        ("AppendObjectsToSelection(List[int])", lambda: Library.AppendObjectsToSelection(build_net_list(ids))),
        ("AppendObjectsToSelection(Array[int])", lambda: Library.AppendObjectsToSelection(Array[int](ids))),
    ]

    if len(ids) == 1:
        methods.append(("SetSingleSelection", lambda: Library.SetSingleSelection(int(ids[0]))))

    for name, fn in methods:
        log("--- Trying " + name + " ---")
        result = safe_call(name, fn)
        selected_after = read_selected_ids()
        if selected_after:
            log(name + " appears to have changed selection.")
        else:
            log(name + " did not produce visible selection in DBBrowser.")
        log(name + " result object type: " + (str(type(result)) if result is not None else "<None>"))


def build_net_list(ids):
    net_list = List[int]()
    for object_id in ids:
        net_list.Add(int(object_id))
    return net_list


log("=== Select all pipes probe start ===")
safe_call("PythonLogFilePath", lambda: PythonLogFilePath)
safe_call("Library type", lambda: Library.GetType().FullName)
safe_call("DBBrowser type", lambda: DBBrowser.GetType().FullName)
safe_call("PART_TYPE id", lambda: Library.GetParamDefId("PART_TYPE"))

before_ids = read_selected_ids()
log("Selection count before: " + str(len(before_ids)))

pipe_ids = collect_pipe_ids()
log("Collected pipe ids count: " + str(len(pipe_ids)))
if pipe_ids:
    log("Pipe ids preview: " + ",".join([str(x) for x in pipe_ids[:30]]))
    if len(pipe_ids) > 30:
        log("Pipe ids preview truncated at 30")
else:
    log("No pipe ids collected.")

if pipe_ids:
    try_selection_methods(pipe_ids)

after_ids = read_selected_ids()
log("Selection count after: " + str(len(after_ids)))
log("=== Select all pipes probe end ===")
write_external_log()
