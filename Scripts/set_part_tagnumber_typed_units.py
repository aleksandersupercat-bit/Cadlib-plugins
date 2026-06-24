# -*- coding: utf-8 -*-
import datetime
from pathlib import Path

import win32com.client


LOG_PATH = Path.home() / "Desktop" / "set_part_tagnumber_typed_units_log.txt"
INTEROP_DLL = r"C:\pdf_ingest\DTMXtest\Artifacts\UnitsCSCom.Interop.dll"
TARGET_PARAM = "PART_TAGNUMBER"
TARGET_VALUE = "DTMX_TYPED_PY"


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


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
    return None


def safe_get(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception as ex:
        return f"<ERR:{ex}>"


reset_log()
log("=== set_part_tagnumber_typed_units.py start ===")

try:
    import clr
    import System
    from System.Runtime.InteropServices import Marshal
    log("pythonnet loaded")
except Exception as ex:
    log(f"pythonnet load FAILED: {ex}")
    raise SystemExit

try:
    clr.AddReference(INTEROP_DLL)
    import UnitsCSCom.Interop as units
    log("UnitsCSCom.Interop loaded")
except Exception as ex:
    log(f"UnitsCSCom.Interop load FAILED: {ex}")
    raise SystemExit

app = get_app()
if app is None:
    log("No active nanoCAD app")
    raise SystemExit

doc = app.ActiveDocument
entity = None
for sel_name in ["PickfirstSelectionSet", "ActiveSelectionSet"]:
    try:
        sel = getattr(doc, sel_name)
        count = sel.Count
        log(f"{sel_name} count = {count}")
        for i in range(count):
            item = sel.Item(i)
            object_name = str(safe_get(item, "ObjectName")).lower()
            if object_name == "vcssubsegment":
                entity = item
                break
        if entity is not None:
            break
    except Exception as ex:
        log(f"{sel_name} error: {ex}")

if entity is None:
    log("No vCSSubSegment in selection")
    raise SystemExit

log(f"Handle = {safe_get(entity, 'Handle')}")
element_obj = entity.Element
params_obj = element_obj.Parameters

p_element = Marshal.GetIUnknownForObject(element_obj)
p_params = Marshal.GetIUnknownForObject(params_obj)

try:
    typed_element = Marshal.GetTypedObjectForIUnknown(p_element, units.IElement)
    typed_params = Marshal.GetTypedObjectForIUnknown(p_params, units.IParameters)
    log("Typed IElement OK")
    log("Typed IParameters OK")

    before = typed_element.GetValue(TARGET_PARAM)
    log(f"Before = {before!r}")

    param_item = typed_params.Item(TARGET_PARAM)
    if param_item is not None:
        log(f"Param.Name = {param_item.Name}")
        log(f"Param.Value = {param_item.Value}")
        log(f"Param.Comment = {param_item.Comment}")
        log(f"Param.ValueComment = {param_item.ValueComment}")

    typed_params.SetParameter(TARGET_PARAM, TARGET_VALUE, "", "")
    log("SetParameter invoked")

    try:
        entity.Update()
    except Exception as ex:
        log(f"entity.Update error: {ex}")

    after = typed_element.GetValue(TARGET_PARAM)
    log(f"After = {after!r}")
    log(f"COM verify = {element_obj.GetValue(TARGET_PARAM)!r}")
finally:
    Marshal.Release(p_element)
    Marshal.Release(p_params)

log("=== set_part_tagnumber_typed_units.py end ===")
