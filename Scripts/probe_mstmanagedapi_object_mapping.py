# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_object_mapping_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
TARGET_OBJECT_ID = 1734958112
TARGET_PARAMETER = "PART_TAGNUMBER"
PREVIEW_LIMIT = 30


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def popup(message, title="DTMX object mapping probe"):
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


def dump_element(element, title):
    log("")
    log(f"=== {title} ===")
    log(f"repr = {safe_repr(element)}")
    for member in ["ElementId", "ModelUID", "Name", "ParamsCount", "ChildrenCount", "Level"]:
        try:
            log(f"{member} = {getattr(element, member)!r}")
        except Exception as ex:
            log(f"{member} ERROR: {ex}")

    for probe_name in [TARGET_PARAMETER, "PART_TAG", "PART_NAME", "PART_TYPE"]:
        try:
            value = element.GetParameterValue(probe_name, "")
            log(f"GetParameterValue({probe_name!r}, '') = {value!r}")
        except Exception as ex:
            log(f"GetParameterValue({probe_name!r}, '') ERROR: {ex}")


def dump_libobject(info, title):
    log("")
    log(f"=== {title} ===")
    log(f"repr = {safe_repr(info)}")
    for field in ["ObjectId", "ElementId", "ParentObjectId", "UID"]:
        try:
            log(f"{field} = {getattr(info, field)!r}")
        except Exception as ex:
            log(f"{field} ERROR: {ex}")


reset_log()
log("=== probe_mstmanagedapi_object_mapping.py start ===")
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
    popup(f"CLR import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX object mapping FAILED")
    raise SystemExit

asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
types = {t.FullName: t for t in asm.GetExportedTypes()}
LibDatabase = types["mstManagedAPI.LibDatabase"]

libdb = System.Activator.CreateInstance(LibDatabase)
download = libdb.DownloadElementsByObjectsIds(System.Array[System.Int32]([TARGET_OBJECT_ID]))
log(f"Download.Count = {download.Count}")

root = download.Root
dump_element(root, "Download.Root")

try:
    libobjects = download.LibObjects
    log(f"LibObjects = {safe_repr(libobjects)}")
except Exception as ex:
    log(f"LibObjects ERROR: {ex}")

try:
    info = download.GetObjectInfoByObjectId(TARGET_OBJECT_ID)
    dump_libobject(info, "GetObjectInfoByObjectId")
except Exception as ex:
    log(f"GetObjectInfoByObjectId ERROR: {ex}")
    info = None

try:
    element = download.GetElementByObjectId(TARGET_OBJECT_ID)
    dump_element(element, "GetElementByObjectId")
except Exception as ex:
    log(f"GetElementByObjectId ERROR: {ex}")
    element = None

if info is not None:
    try:
        root_by_id = root.GetElementById(info.ElementId)
        dump_element(root_by_id, "Root.GetElementById(info.ElementId)")
    except Exception as ex:
        log(f"Root.GetElementById(info.ElementId) ERROR: {ex}")

try:
    children_count = root.ChildrenCount
    log(f"Root.ChildrenCount = {children_count}")
    for index in range(min(int(children_count), PREVIEW_LIMIT)):
        try:
            child = root.GetChild(index)
            dump_element(child, f"Root.GetChild({index})")
        except Exception as ex:
            log(f"Root.GetChild({index}) ERROR: {ex}")
except Exception as ex:
    log(f"Root.ChildrenCount probe ERROR: {ex}")

popup(f"Object mapping probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_object_mapping.py end ===")
