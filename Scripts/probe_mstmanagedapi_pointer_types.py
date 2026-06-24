# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_pointer_types_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
TARGET_TYPES = [
    "mstManagedAPI.CElement",
    "mstManagedAPI.LibDatabase",
    "mstManagedAPI.ProjectDBUtils",
    "mstManagedAPI.LibObjectInfo",
]


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def popup(message, title="DTMX pointer type probe"):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, title, 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


def dump_type_info(t, prefix=""):
    if t is None:
        log(f"{prefix}<None>")
        return
    try:
        log(f"{prefix}FullName = {t.FullName}")
    except Exception as ex:
        log(f"{prefix}FullName ERROR: {ex}")
    for attr_name in ["Namespace", "Name", "AssemblyQualifiedName", "IsPointer", "IsInterface", "IsClass"]:
        try:
            log(f"{prefix}{attr_name} = {getattr(t, attr_name)!r}")
        except Exception as ex:
            log(f"{prefix}{attr_name} ERROR: {ex}")
    try:
        log(f"{prefix}GUID = {t.GUID}")
    except Exception as ex:
        log(f"{prefix}GUID ERROR: {ex}")
    try:
        log(f"{prefix}Assembly = {t.Assembly.FullName}")
    except Exception as ex:
        log(f"{prefix}Assembly ERROR: {ex}")


reset_log()
log("=== probe_mstmanagedapi_pointer_types.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"MST DLL: {MST_DLL}")

try:
    import clr
    import System
    import System.Reflection
    log("import clr/System OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    popup(f"CLR import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX pointer type FAILED")
    raise SystemExit

asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
log(f"Assembly.LoadFrom OK: {asm.FullName}")

types = {t.FullName: t for t in asm.GetExportedTypes()}

for name in TARGET_TYPES:
    t = types.get(name)
    log("")
    log(f"=== TYPE {name} ===")
    if t is None:
        log("Type not found")
        continue
    dump_type_info(t, "TYPE | ")
    try:
        ctors = list(t.GetConstructors())
        log(f"Constructors count = {len(ctors)}")
        for index, ctor in enumerate(ctors):
            log(f"  CTOR[{index}] {ctor}")
            params = list(ctor.GetParameters())
            for pindex, param in enumerate(params):
                log(f"    PARAM[{pindex}] name={param.Name}")
                ptype = param.ParameterType
                dump_type_info(ptype, "      PTYPE | ")
                try:
                    elem = ptype.GetElementType()
                    dump_type_info(elem, "      ELEM  | ")
                except Exception as ex:
                    log(f"      ELEM ERROR: {ex}")
    except Exception as ex:
        log(f"Constructor dump ERROR: {ex}")

popup(f"Pointer type probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_pointer_types.py end ===")
