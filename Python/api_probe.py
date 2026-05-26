# -*- coding: utf-8 -*-


def log(message):
    text = str(message)
    print(text)
    try:
        CLMainForm.WriteLog("[api_probe.py] " + text)
    except Exception:
        pass


def safe(label, fn):
    try:
        value = fn()
        log(label + ": " + str(value))
        return value
    except Exception as ex:
        log(label + " ERROR: " + str(ex))
        return None


def sample_list(label, values, limit):
    if values is None:
        return
    count = safe(label + " count", lambda: values.Count)
    if count is None:
        return
    for i in range(min(count, limit)):
        log(label + "[" + str(i) + "]=" + str(values[i]))


log("=== API probe start ===")

part_type_id = safe("PART_TYPE id", lambda: Library.GetParamDefId("PART_TYPE"))
if part_type_id is not None:
    sample_list("GetParamValuesList(PART_TYPE)", safe("GetParamValuesList", lambda: Library.GetParamValuesList(part_type_id)), 30)

    objects = safe("GetObjectParametersByValues('Труба')", lambda: Library.GetObjectParametersByValues(part_type_id, "Труба", True, ';'))
    sample_list("Tube objects", objects, 10)

    if objects is not None and objects.Count > 0:
        first = objects[0]
        log("First tube idObject=" + str(first.idObject) + "; name=" + str(first.Name))
        children = safe("GetChildObjects(first)", lambda: Library.GetChildObjects(first))
        if children is not None:
            idx = 0
            for child in children:
                if idx >= 20:
                    break
                log("child[" + str(idx) + "] idObject=" + str(child.idObject) + "; name=" + str(child.Name))
                idx += 1
        params = safe("GetObjectParameters(first.idObject)", lambda: Library.GetObjectParameters(first.idObject))
        sample_list("First tube params", params, 20)

log("=== API probe end ===")
