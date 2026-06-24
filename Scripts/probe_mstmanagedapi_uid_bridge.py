# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_uid_bridge_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
SERVER = r"(local)\IGA"
DATABASE = "PipeDB_Cadlib"
USER = ""
PASSWORD = ""
PORT = 5432
ENTITY_NAMES = {"vcssubsegment"}


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def safe_get(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception as ex:
        return f"<ERR:{ex}>"


def norm(v):
    return str(v).strip().lower() if v is not None else ""


def popup(message, title="DTMX UID bridge probe"):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, title, 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


def dump_element(element, title):
    log("")
    log(f"=== {title} ===")
    if element is None:
        log("None")
        return
    log(f"repr = {element!r}")
    for member in ["ElementId", "ModelUID", "Name", "ParamsCount", "ChildrenCount", "Level"]:
        try:
            log(f"{member} = {getattr(element, member)!r}")
        except Exception as ex:
            log(f"{member} ERROR: {ex}")
    for probe_name in ["SYS_DB_UID", "PART_TAGNUMBER", "PART_TAG", "PART_NAME", "PART_TYPE"]:
        try:
            value = element.GetParameterValue(probe_name, "")
            log(f"GetParameterValue({probe_name!r}, '') = {value!r}")
        except Exception as ex:
            log(f"GetParameterValue({probe_name!r}, '') ERROR: {ex}")


def dump_libobject(info, title):
    log("")
    log(f"=== {title} ===")
    if info is None:
        log("None")
        return
    log(f"repr = {info!r}")
    for field in ["ObjectId", "ElementId", "ParentObjectId", "UID"]:
        try:
            log(f"{field} = {getattr(info, field)!r}")
        except Exception as ex:
            log(f"{field} ERROR: {ex}")


def get_app():
    for progid in [
        "nanoCADx64.Application.24.0",
        "nanoCADx64.Application",
        "nanoCAD.Application.24.0",
        "nanoCAD.Application",
    ]:
        try:
            app = win32com.client.GetActiveObject(progid)
            log(f"Connected: {progid}")
            return app
        except Exception:
            pass
    try:
        return Application
    except Exception:
        return None


def get_doc(app):
    try:
        return ThisDrawing
    except Exception:
        pass
    if app:
        try:
            return app.ActiveDocument
        except Exception:
            pass
    return None


def get_selected_entity(doc):
    for sel_attr in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            sel = list(getattr(doc, sel_attr))
            log(f"{sel_attr} count: {len(sel)}")
            for item in sel:
                if norm(safe_get(item, "ObjectName")) in ENTITY_NAMES or norm(safe_get(item, "EntityName")) in ENTITY_NAMES:
                    return item
        except Exception as ex:
            log(f"{sel_attr} error: {ex}")
    return None


reset_log()
log("=== probe_mstmanagedapi_uid_bridge.py start ===")
log(f"Log path: {LOG_PATH}")

app = get_app()
doc = get_doc(app)
if doc is None:
    log("No active document")
    raise SystemExit

entity = get_selected_entity(doc)
if entity is None:
    log("No selected target entity")
    raise SystemExit

element_com = safe_get(entity, "Element")
if isinstance(element_com, str):
    log(f"entity.Element unavailable: {element_com}")
    raise SystemExit

sys_db_uid = ""
try:
    sys_db_uid = str(element_com.GetValue("SYS_DB_UID")).strip()
except Exception as ex:
    log(f"COM GetValue('SYS_DB_UID') ERROR: {ex}")

log(f"Selected Handle = {safe_get(entity, 'Handle')}")
log(f"Selected ObjectName = {safe_get(entity, 'ObjectName')}")
log(f"COM Element.ObjectId = {safe_get(element_com, 'ObjectId')}")
log(f"COM Element.ElementId = {safe_get(element_com, 'ElementId')}")
log(f"COM SYS_DB_UID = {sys_db_uid!r}")
log(f"COM PART_TAGNUMBER = {safe_get(element_com, 'GetValue')('PART_TAGNUMBER')!r}")

try:
    import clr
    import System
    import System.Reflection
    log("import clr/System OK")
except Exception as ex:
    log(f"CLR import FAILED: {ex}")
    raise SystemExit

asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
types = {t.FullName: t for t in asm.GetExportedTypes()}
LibDatabase = types["mstManagedAPI.LibDatabase"]

libdb = System.Activator.CreateInstance(LibDatabase)
platform = libdb.GetPlatform()
driver = libdb.GetDriver()
ok = libdb.Connect(SERVER, DATABASE, USER, PASSWORD, platform, driver, PORT, True)
log(f"LibDatabase.Connect(...) = {ok}")
log(f"LibDatabase.IsConnected = {libdb.IsConnected}")

if sys_db_uid:
    try:
        guid = System.Guid(sys_db_uid)
        log(f"System.Guid(sys_db_uid) = {guid}")
    except Exception as ex:
        log(f"Guid parse ERROR: {ex}")
        guid = None
else:
    guid = None

libinfo = None
if guid is not None:
    try:
        libinfo = libdb.GetLibraryObject(guid)
        dump_libobject(libinfo, "LibDatabase.GetLibraryObject(Guid)")
    except Exception as ex:
        log(f"GetLibraryObject(Guid) ERROR: {ex}")

if libinfo is not None:
    try:
        db_object_id = int(libinfo.ObjectId)
        log(f"DB ObjectId from LibObjectInfo = {db_object_id}")
        download = libdb.DownloadElementsByObjectsIds(System.Array[System.Int32]([db_object_id]))
        log(f"download.Count = {download.Count}")
        dump_element(download.Root, "download.Root")
        try:
            mapped = download.GetElementByObjectId(db_object_id)
            dump_element(mapped, "download.GetElementByObjectId(db_object_id)")
        except Exception as ex:
            log(f"download.GetElementByObjectId ERROR: {ex}")
    except Exception as ex:
        log(f"Download by DB ObjectId ERROR: {ex}")

try:
    libdb.Disconnect()
    log("Disconnect() OK")
except Exception as ex:
    log(f"Disconnect() ERROR: {ex}")

popup(f"UID bridge probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_uid_bridge.py end ===")
