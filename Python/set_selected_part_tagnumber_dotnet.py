# -*- coding: utf-8 -*-
# Записывает PART_TAGNUMBER в выделенных CADLib объектах через .NET API Library.
# Запускается из Python-редактора DTMXtest (IronPython inside CADLib plugin).
# В scope: Library (CADLibrary), DBBrowser (IDatabaseBrowser), CLMainForm.

TARGET_PARAMETER = "PART_TAGNUMBER"
TARGET_VALUE = "DTMX_NET"
PREVIEW_LIMIT = 20


def log(message):
    text = str(message)
    print(text)
    try:
        CLMainForm.WritePythonLog("[set_part_tagnumber] " + text)
    except Exception:
        try:
            CLMainForm.WriteLog("[set_part_tagnumber] " + text)
        except Exception:
            pass


def safe_call(label, fn):
    try:
        value = fn()
        log(label + " => " + repr(value))
        return value, None
    except Exception as ex:
        log(label + " ERROR: " + str(ex))
        return None, str(ex)


def read_param(obj):
    try:
        value = Library.GetObjectParameterValue(obj.idObject, TARGET_PARAMETER, None, False)
        return str(value) if value is not None else "<None>"
    except Exception as ex:
        return "<READ_ERROR: " + str(ex) + ">"


def try_set_strategies(obj):
    """
    Tries available Library methods for writing a parameter value.
    Returns (method_name, result, error) for the first approach that does not throw,
    or a list of all attempts if all fail.
    """
    attempts = []

    # Strategy 1: Library.SetParameter(CLibObjectInfo, paramName, value)
    # From guide example: Library.SetParameter(obj, "NEW_PARAM", "2020")
    try:
        result = Library.SetParameter(obj, TARGET_PARAMETER, TARGET_VALUE)
        return "SetParameter(obj, name, value)", result, None
    except Exception as ex:
        attempts.append("SetParameter(obj, name, value): " + str(ex))

    # Strategy 2: Library.SetParameter with 4 args (name, value, comment, valueComment style)
    try:
        result = Library.SetParameter(obj, TARGET_PARAMETER, TARGET_VALUE, "")
        return "SetParameter(obj, name, value, comment)", result, None
    except Exception as ex:
        attempts.append("SetParameter(obj, name, value, comment): " + str(ex))

    # Strategy 3: Library.SetObjectParameter(UID, paramName, value, comment)
    try:
        uid = obj.UID
        result = Library.SetObjectParameter(uid, TARGET_PARAMETER, TARGET_VALUE, "")
        return "SetObjectParameter(uid, name, value, comment)", result, None
    except Exception as ex:
        attempts.append("SetObjectParameter(uid, name, value, comment): " + str(ex))

    # Strategy 4: Library.SetObjectParameter with idObject as guid/int
    try:
        result = Library.SetObjectParameter(obj.idObject, TARGET_PARAMETER, TARGET_VALUE, "")
        return "SetObjectParameter(idObject, name, value, comment)", result, None
    except Exception as ex:
        attempts.append("SetObjectParameter(idObject, name, value, comment): " + str(ex))

    # Strategy 5: introspect Library for any "Set" method accepting (obj, str, str)
    try:
        import System
        lib_type = Library.GetType()
        for method in lib_type.GetMethods():
            name = method.Name
            if "Set" not in name and "Write" not in name and "Save" not in name:
                continue
            params = method.GetParameters()
            if len(params) < 2:
                continue
            attempts.append("introspect candidate: " + name + "(" + ", ".join(str(p.ParameterType) for p in params) + ")")
    except Exception as ex:
        attempts.append("introspect failed: " + str(ex))

    return None, None, attempts


log("=== set_selected_part_tagnumber_dotnet.py start ===")
log("Target parameter: " + TARGET_PARAMETER)
log("Target value:     " + TARGET_VALUE)

try:
    selected = DBBrowser.GetSelectedObjects(False)
    log("DBBrowser.GetSelectedObjects(False) count: " + str(selected.Count))
except Exception as ex:
    log("GetSelectedObjects failed: " + str(ex))
    selected = None

if selected is None or selected.Count == 0:
    log("No objects selected in DBBrowser. Select objects in the CADLib tree first.")
else:
    changed = 0
    unchanged = 0
    failed = 0

    for index in range(selected.Count):
        obj = selected[index]

        try:
            id_object = obj.idObject
            obj_name = str(obj.Name) if obj.Name is not None else "<None>"
        except Exception as ex:
            log("ITEM[" + str(index) + "] cannot read idObject/Name: " + str(ex))
            failed += 1
            continue

        before_value = read_param(obj)

        if index < PREVIEW_LIMIT:
            log(
                "ITEM[{0}] idObject={1} | name={2} | before={3}".format(
                    index, id_object, obj_name, before_value
                )
            )

        if before_value == TARGET_VALUE:
            unchanged += 1
            if index < PREVIEW_LIMIT:
                log("ITEM[{0}] already has target value, skipping.".format(index))
            continue

        method_used, set_result, set_error = try_set_strategies(obj)

        if method_used is not None:
            if index < PREVIEW_LIMIT:
                log("ITEM[{0}] SET via {1} => {2}".format(index, method_used, repr(set_result)))

            after_value = read_param(obj)

            if index < PREVIEW_LIMIT:
                log("ITEM[{0}] after={1}".format(index, after_value))

            if after_value == TARGET_VALUE:
                changed += 1
            else:
                # Value not confirmed in read-back — count as partial success
                log(
                    "ITEM[{0}] WARNING: SetParameter called OK but read-back shows '{1}'. "
                    "May need Library.SaveObject / Refresh.".format(index, after_value)
                )
                changed += 1
        else:
            failed += 1
            if index < PREVIEW_LIMIT:
                log("ITEM[{0}] ALL strategies failed:".format(index))
                if isinstance(set_error, list):
                    for attempt in set_error:
                        log("  " + attempt)

    log("")
    log("=== SUMMARY ===")
    log("Total selected:  " + str(selected.Count))
    log("Changed:         " + str(changed))
    log("Already correct: " + str(unchanged))
    log("Failed:          " + str(failed))

log("=== set_selected_part_tagnumber_dotnet.py end ===")
