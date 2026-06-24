# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstmanagedapi_connect_log.txt"
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
SERVER = r"(local)\IGA"
DATABASE = "PipeDB_Cadlib"
USER = ""
PASSWORD = ""
PORT = 5432
TARGET_OBJECT_ID = 1734958112


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def popup(message, title="DTMX connect probe"):
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


reset_log()
log("=== probe_mstmanagedapi_connect.py start ===")
log(f"Log path: {LOG_PATH}")

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

log(f"Default platform = {platform}")
log(f"Default driver = {driver!r}")
log(f"Before connect IsConnected = {libdb.IsConnected}")

try:
    ok = libdb.Connect(SERVER, DATABASE, USER, PASSWORD, platform, driver, PORT, True)
    log(f"Connect(...) -> {ok}")
except Exception as ex:
    log(f"Connect(...) ERROR: {ex}")
    ok = False

log(f"After connect IsConnected = {libdb.IsConnected}")
log(f"DatabaseName = {safe_repr(libdb.DatabaseName)}")
log(f"Server = {safe_repr(libdb.Server)}")
log(f"UserName = {safe_repr(libdb.UserName)}")

try:
    download = libdb.DownloadElementsByObjectsIds(System.Array[System.Int32]([TARGET_OBJECT_ID]))
    log(f"DownloadElementsByObjectsIds -> {safe_repr(download)}")
    if download is not None:
        try:
            log(f"download.Count = {download.Count}")
        except Exception as ex:
            log(f"download.Count ERROR: {ex}")
        try:
            root = download.Root
            log(f"download.Root = {safe_repr(root)}")
            if root is not None:
                for member in ["ElementId", "Name", "ParamsCount", "ChildrenCount"]:
                    try:
                        log(f"root.{member} = {getattr(root, member)!r}")
                    except Exception as ex:
                        log(f"root.{member} ERROR: {ex}")
        except Exception as ex:
            log(f"download.Root ERROR: {ex}")
except Exception as ex:
    log(f"DownloadElementsByObjectsIds ERROR: {ex}")

try:
    libdb.Disconnect()
    log("Disconnect() OK")
except Exception as ex:
    log(f"Disconnect() ERROR: {ex}")

popup(f"Connect probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstmanagedapi_connect.py end ===")
