# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_download_data_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
TARGET_OBJECT_ID = 1734958112
PREVIEW_LIMIT = 80


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def popup(message, title="DTMX download data probe"):
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


def dump_object(obj, title):
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
log("=== probe_mstmanagedapi_download_data.py start ===")
log(f"Log path: {LOG_PATH}")
log(f"MST DLL: {MST_DLL}")
log(f"Target object id: {TARGET_OBJECT_ID}")

try:
    import clr
    import System
    import System.Reflection
    log("import clr/System OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    popup(f"CLR import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX download data FAILED")
    raise SystemExit

try:
    asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
    log(f"Assembly.LoadFrom OK: {asm.FullName}")
except Exception as ex:
    log(f"Assembly.LoadFrom FAILED: {ex}")
    popup(f"Assembly load failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX download data FAILED")
    raise SystemExit

types = {t.FullName: t for t in asm.GetExportedTypes()}
LibDatabase = types["mstManagedAPI.LibDatabase"]

libdb = System.Activator.CreateInstance(LibDatabase)
log(f"LibDatabase created. IsConnected = {libdb.IsConnected}")

arr = System.Array[System.Int32]([TARGET_OBJECT_ID])
download = libdb.DownloadElementsByObjectsIds(arr)
dump_object(download, "CElementDownloadData")

# Try common members by name
for member in [
    "Elements",
    "Count",
    "Items",
    "Root",
    "RootElement",
    "Element",
    "Result",
    "Data",
    "Status",
    "Message",
]:
    try:
        value = getattr(download, member)
        log(f"{member} = {safe_repr(value)}")
        if value is not None:
            dump_object(value, f"{member} object")
    except Exception as ex:
        log(f"{member} ERROR: {ex}")

# Try methods if present
for method_name, args in [
    ("GetType", ()),
    ("ToString", ()),
    ("GetRoot", ()),
    ("GetElementById", (0,)),
    ("GetChild", (0,)),
]:
    try:
        method = getattr(download, method_name)
        result = method(*args)
        log(f"{method_name}{args} -> {safe_repr(result)}")
        if result is not None and not isinstance(result, str):
            dump_object(result, f"{method_name} result")
    except Exception as ex:
        log(f"{method_name}{args} ERROR: {ex}")

popup(f"DownloadData probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_download_data.py end ===")
