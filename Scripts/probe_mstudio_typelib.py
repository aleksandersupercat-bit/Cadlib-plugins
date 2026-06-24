# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import pythoncom
import win32com.client


LOG_PATH = Path.home() / "Desktop" / "probe_mstudio_typelib_log.txt"
DLLS = [
    r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstudioData.dll",
    r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstudioDB.dll",
]
KEYWORDS = [
    "ielement",
    "element",
    "idatabase",
    "database",
    "project",
    "param",
    "object",
    "uid",
    "guid",
]
PREVIEW_LIMIT = 500


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def popup(message, title="DTMX typelib probe"):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, title, 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


def match_keywords(name):
    low = name.lower()
    return any(keyword in low for keyword in KEYWORDS)


def get_doc_string(ti, memid):
    try:
        return ti.GetDocumentation(memid)
    except Exception:
        return None


def dump_typelib(dll_path):
    log("")
    log(f"=== TYPELIB {dll_path} ===")
    try:
        tlb = pythoncom.LoadTypeLib(dll_path)
        log("LoadTypeLib OK")
    except Exception as ex:
        log(f"LoadTypeLib FAILED: {ex}")
        return

    try:
        attr = tlb.GetLibAttr()
        log(f"LibAttr = {attr}")
    except Exception as ex:
        log(f"GetLibAttr FAILED: {ex}")

    try:
        count = tlb.GetTypeInfoCount()
        log(f"TypeInfoCount = {count}")
    except Exception as ex:
        log(f"GetTypeInfoCount FAILED: {ex}")
        return

    interesting = []
    for index in range(count):
        try:
            ti = tlb.GetTypeInfo(index)
            ta = ti.GetTypeAttr()
            name = get_doc_string(ti, -1)[0]
            typekind = ta.typekind
            guid = str(ta.guid)
            if match_keywords(name):
                interesting.append((index, name, guid, typekind, ti, ta))
        except Exception as ex:
            log(f"TypeInfo[{index}] ERROR: {ex}")

    log(f"Interesting TypeInfos = {len(interesting)}")
    for index, name, guid, typekind, _, _ in interesting[:PREVIEW_LIMIT]:
        log(f"  TYPEINFO[{index}] name={name} guid={guid} typekind={typekind}")

    for index, name, guid, typekind, ti, ta in interesting[:PREVIEW_LIMIT]:
        log("")
        log(f"=== TYPEINFO[{index}] {name} ===")
        log(f"GUID = {guid}")
        log(f"typekind = {typekind}")
        try:
            log(f"cFuncs = {ta.cFuncs}; cVars = {ta.cVars}; cImplTypes = {ta.cImplTypes}")
        except Exception:
            pass

        # funcs
        try:
            for func_index in range(min(ta.cFuncs, PREVIEW_LIMIT)):
                fd = ti.GetFuncDesc(func_index)
                names = ti.GetNames(fd.memid)
                log(f"  FUNC[{func_index}] memid={fd.memid} names={names}")
        except Exception as ex:
            log(f"  FUNC dump ERROR: {ex}")

        # vars
        try:
            for var_index in range(min(ta.cVars, PREVIEW_LIMIT)):
                vd = ti.GetVarDesc(var_index)
                doc = get_doc_string(ti, vd.memid)
                log(f"  VAR[{var_index}] memid={vd.memid} doc={doc}")
        except Exception as ex:
            log(f"  VAR dump ERROR: {ex}")


reset_log()
log("=== probe_mstudio_typelib.py start ===")
log(f"Log path: {LOG_PATH}")

for dll in DLLS:
    dump_typelib(dll)

popup(f"Typelib probe finished.\nLog: {LOG_PATH}")
log("=== probe_mstudio_typelib.py end ===")
