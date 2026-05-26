# -*- coding: utf-8 -*-


def log(message):
    text = str(message)
    print(text)
    try:
        CLMainForm.WriteLog("[introspect.py] " + text)
    except Exception:
        pass


def dump_methods(label, obj, contains):
    log("--- " + label + " methods containing '" + contains + "' ---")
    methods = obj.GetType().GetMethods()
    rows = []
    for method in methods:
        name = method.Name
        if contains.lower() in name.lower():
            rows.append(name)
    rows.sort()
    for name in rows[:100]:
        log(name)
    log("count=" + str(len(rows)))


log("=== Introspection start ===")
log("Library type: " + Library.GetType().FullName)
log("DBBrowser type: " + DBBrowser.GetType().FullName)
dump_methods("Library", Library, "Object")
dump_methods("Library", Library, "Param")
dump_methods("DBBrowser", DBBrowser, "Select")
dump_methods("DBBrowser", DBBrowser, "View")
log("=== Introspection end ===")
