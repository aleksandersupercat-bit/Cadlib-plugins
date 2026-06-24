# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_runtime_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
PREVIEW_LIMIT = 50


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def popup(message, title="DTMX mstManagedAPI runtime probe"):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, title, 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


def safe_repr(value, limit=800):
    try:
        text = repr(value)
    except Exception as ex:
        text = f"<repr error: {ex}>"
    if len(text) > limit:
        return text[:limit] + "...<truncated>"
    return text


def safe_call(fn, *args):
    try:
        return fn(*args)
    except Exception as ex:
        return f"<ERR:{ex}>"


def dump_members(obj, title):
    log("")
    log(f"=== {title} ===")
    log(f"repr = {safe_repr(obj)}")
    try:
        names = sorted(set(dir(obj)))
        log(f"dir count = {len(names)}")
        for index, name in enumerate(names[:PREVIEW_LIMIT]):
            log(f"  dir[{index}] = {name}")
    except Exception as ex:
        log(f"dir ERROR: {ex}")


reset_log()
log("=== probe_mstmanagedapi_runtime.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"MST DLL: {MST_DLL}")

try:
    import clr
    import System
    import System.Reflection
    log("import clr/System OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    popup(f"CLR import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX runtime probe FAILED")
    raise SystemExit

try:
    asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
    log(f"Assembly.LoadFrom OK: {asm.FullName}")
except Exception as ex:
    log(f"Assembly.LoadFrom FAILED: {ex}")
    popup(f"Assembly load failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX runtime probe FAILED")
    raise SystemExit

types = {t.FullName: t for t in asm.GetExportedTypes()}
MstudioCore = types["mstManagedAPI.MstudioCore"]
LibDatabase = types["mstManagedAPI.LibDatabase"]
ProjectService = types["mstManagedAPI.ProjectService"]

# MstudioCore
log("")
log("=== MstudioCore ===")
try:
    value = MstudioCore.GetMethod("GetMainAppKey").Invoke(None, None)
    log(f"MstudioCore.GetMainAppKey() = {value!r}")
except Exception as ex:
    log(f"MstudioCore.GetMainAppKey FAILED: {ex}")

# LibDatabase
log("")
log("=== LibDatabase default ctor ===")
try:
    libdb = System.Activator.CreateInstance(LibDatabase)
    log("LibDatabase() OK")
    dump_members(libdb, "LibDatabase instance")
    for member in [
        "IsConnected",
        "DatabaseName",
        "Server",
        "UserName",
        "Port",
        "UsernameFormat",
        "UsernameLowercase",
    ]:
        try:
            log(f"  {member} = {getattr(libdb, member)!r}")
        except Exception as ex:
            log(f"  {member} ERROR: {ex}")

    for call_name, args in [
        ("GetPlatform", ()),
        ("GetDriver", ()),
        ("LoadProjectSettings", ()),
        ("SetStandartParamDefsLib", ()),
        ("GetObjectCategoryId", ("Труба", False)),
        ("GetLibraryObject", (1734958112,)),
        ("DownloadElementsByObjectsIds", (System.Array[System.Int32]([1734958112]),)),
    ]:
        try:
            result = getattr(libdb, call_name)(*args)
            log(f"  {call_name}{args} -> {safe_repr(result)}")
        except Exception as ex:
            log(f"  {call_name}{args} ERROR: {ex}")
except Exception as ex:
    log(f"LibDatabase() FAILED: {ex}")

# ProjectService
log("")
log("=== ProjectService default ctor ===")
try:
    service = System.Activator.CreateInstance(ProjectService)
    log("ProjectService() OK")
    dump_members(service, "ProjectService instance")
    for call_name, args in [
        ("OpenWindowsSession", ()),
        ("OpenConnection", ("",)),
    ]:
        try:
            result = getattr(service, call_name)(*args)
            log(f"  {call_name}{args} -> {safe_repr(result)}")
        except Exception as ex:
            log(f"  {call_name}{args} ERROR: {ex}")
except Exception as ex:
    log(f"ProjectService() FAILED: {ex}")

popup(f"mstManagedAPI runtime probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_runtime.py end ===")
