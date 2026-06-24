# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstudio_interop_types_log.txt"
DLLS = [
    r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstudioData.dll",
    r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstudioDB.dll",
]
KEYWORDS = [
    "ielement",
    "element",
    "database",
    "idatabase",
    "project",
    "application",
    "active",
    "current",
    "objectid",
    "uid",
    "guid",
]
PREVIEW_LIMIT = 400


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def popup(message, title="DTMX interop type probe"):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, title, 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


def match_keywords(name):
    low = name.lower()
    return any(keyword in low for keyword in KEYWORDS)


def member_signature(method_base):
    parts = []
    try:
        params = list(method_base.GetParameters())
    except Exception:
        params = []
    for parameter in params:
        try:
            ptype = parameter.ParameterType.FullName or str(parameter.ParameterType)
        except Exception:
            ptype = "<unknown>"
        parts.append(f"{ptype} {parameter.Name}")
    try:
        ret = method_base.ReturnType.FullName
    except Exception:
        ret = "<unknown>"
    return f"{ret}({', '.join(parts)})"


def dump_type(t):
    log("")
    log(f"=== TYPE {t.FullName} ===")
    try:
        log(f"BaseType = {t.BaseType}")
    except Exception as ex:
        log(f"BaseType ERROR: {ex}")
    try:
        log(f"IsInterface = {t.IsInterface}; IsClass = {t.IsClass}; IsAbstract = {t.IsAbstract}")
    except Exception as ex:
        log(f"Flags ERROR: {ex}")
    try:
        guid_attrs = t.GetCustomAttributes(False)
        for attr in guid_attrs:
            attr_name = attr.GetType().FullName
            if "GuidAttribute" in attr_name:
                log(f"GUID = {attr.Value}")
    except Exception as ex:
        log(f"GUID scan ERROR: {ex}")
    try:
        props = sorted(list(t.GetProperties()), key=lambda x: x.Name)
        log(f"Properties count = {len(props)}")
        for prop in props[:PREVIEW_LIMIT]:
            try:
                ptype = prop.PropertyType.FullName
            except Exception:
                ptype = "<unknown>"
            flag = "KEY" if match_keywords(prop.Name) else "   "
            log(f"  {flag} PROP {prop.Name}: {ptype}")
    except Exception as ex:
        log(f"Properties ERROR: {ex}")
    try:
        methods = []
        for method in t.GetMethods():
            if method.IsSpecialName:
                continue
            if match_keywords(method.Name):
                methods.append(method)
        methods = sorted(methods, key=lambda x: x.Name)
        log(f"Interesting methods count = {len(methods)}")
        for method in methods[:PREVIEW_LIMIT]:
            prefix = "STATIC" if method.IsStatic else "INST"
            log(f"  {prefix} METHOD {method.Name}: {member_signature(method)}")
    except Exception as ex:
        log(f"Methods ERROR: {ex}")


reset_log()
log("=== probe_mstudio_interop_types.py start ===")
log(f"Log path: {LOG_PATH}")

try:
    import clr
    import System
    import System.Reflection
    log("import clr/System OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    popup(f"CLR import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX interop probe FAILED")
    raise SystemExit

for dll_path in DLLS:
    log("")
    log(f"=== ASSEMBLY {dll_path} ===")
    try:
        asm = System.Reflection.Assembly.LoadFrom(dll_path)
        log(f"Assembly.LoadFrom OK: {asm.FullName}")
    except Exception as ex:
        log(f"Assembly.LoadFrom FAILED: {ex}")
        continue

    try:
        exported = list(asm.GetExportedTypes())
    except Exception as ex:
        log(f"GetExportedTypes FAILED: {ex}")
        continue

    log(f"Exported types count = {len(exported)}")
    keyword_types = []
    for t in exported:
        full_name = t.FullName or ""
        if match_keywords(full_name):
            keyword_types.append(t)
    keyword_types = sorted(keyword_types, key=lambda x: x.FullName)
    log(f"Keyword types count = {len(keyword_types)}")
    for t in keyword_types[:PREVIEW_LIMIT]:
        log(f"  TYPE {t.FullName}")

    # deeper dump for especially interesting ones
    for t in keyword_types:
        full_name = t.FullName or ""
        if any(k in full_name.lower() for k in ["ielement", "idatabase", "element", "database"]):
            dump_type(t)

popup(f"Interop type probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstudio_interop_types.py end ===")
