# -*- coding: utf-8 -*-

def log(message):
    text = str(message)
    print(text)
    try:
        CLMainForm.WritePythonLog("[diagnostics.py] " + text)
    except Exception:
        try:
            CLMainForm.WriteLog("[diagnostics.py] " + text)
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


log("=== DTMX Python diagnostics start ===")
safe_call("LogFilePath", lambda: CLMainForm.LogFilePath)
safe_call("Library type", lambda: Library.GetType().FullName)
safe_call("DBBrowser type", lambda: DBBrowser.GetType().FullName)
safe_call("Current folder", lambda: DBBrowser.CurrentFolder)

selected = safe_call("Selected objects", lambda: DBBrowser.GetSelectedObjects(False))
if selected is not None:
    safe_call("Selected count", lambda: selected.Count)
    for i, obj in enumerate(selected):
        if i >= 10:
            log("Selected output truncated at 10 objects")
            break
        part_type = safe_call("PART_TYPE for " + str(obj.idObject), lambda obj=obj: Library.GetObjectParameterValue(obj.idObject, "PART_TYPE", None, False))
        log("selected[{0}] idObject={1}; category={2}; name={3}; PART_TYPE={4}".format(i, obj.idObject, obj.idObjectCategory, obj.Name, part_type))

part_type_id = safe_call("PART_TYPE id", lambda: Library.GetParamDefId("PART_TYPE"))
if part_type_id is not None:
    values = safe_call("PART_TYPE values", lambda: Library.GetParamValuesList(part_type_id))
    if values is not None:
        safe_call("PART_TYPE values count", lambda: values.Count)
        limit = min(values.Count, 20)
        for i in range(limit):
            log("PART_TYPE[{0}]={1}".format(i, values[i]))

form_values = safe_call("PART_TYPE values via CLMainForm", lambda: CLMainForm.GetPartTypesForPython())
if form_values is None:
    raise Exception("CRITICAL: CLMainForm.GetPartTypesForPython is unavailable. Reload the plugin DLL and run diagnostics again.")

if form_values is not None:
    safe_call("PART_TYPE values via CLMainForm count", lambda: form_values.Length)
    limit = min(form_values.Length, 20)
    for i in range(limit):
        log("FORM_PART_TYPE[{0}]={1}".format(i, form_values[i]))

log("=== DTMX Python diagnostics end ===")
