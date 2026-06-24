# -*- coding: utf-8 -*-
# Probe: dumps all COM properties of entity.Element to find ID/UID bridge to mstManagedAPI.
# Run from nanoCAD Python script editor with at least one entity selected.

import datetime
from pathlib import Path

import win32com.client

LOG_PATH = Path.home() / "Desktop" / "probe_element_properties_log.txt"
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


def safe_call(fn, *args):
    try:
        return fn(*args)
    except Exception as ex:
        return f"<ERR:{ex}>"


def norm(v):
    return str(v).strip().lower() if v is not None else ""


def get_app():
    for progid in ["nanoCADx64.Application.24.0", "nanoCADx64.Application",
                   "nanoCAD.Application.24.0", "nanoCAD.Application"]:
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


reset_log()
log("=== probe_element_properties.py start ===")

app = get_app()
if not app:
    log("ERROR: no nanoCAD application found")
    raise SystemExit

try:
    doc = app.ActiveDocument
except Exception:
    try:
        doc = ThisDrawing
    except Exception:
        doc = None

if not doc:
    log("ERROR: no active document")
    raise SystemExit

# Get first selected VCS entity
entity = None
for sel_attr in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
    try:
        sel = getattr(doc, sel_attr)
        for item in sel:
            obj_name = norm(safe_get(item, "ObjectName"))
            ent_name = norm(safe_get(item, "EntityName"))
            if obj_name in ENTITY_NAMES or ent_name in ENTITY_NAMES:
                entity = item
                break
    except Exception:
        pass
    if entity:
        break

if not entity:
    log("No VCS entity selected. Select a pipe element first.")
    raise SystemExit

log(f"Entity ObjectName={safe_get(entity, 'ObjectName')}")
log(f"Entity Handle={safe_get(entity, 'Handle')}")
log(f"Entity EntityName={safe_get(entity, 'EntityName')}")
log("")

# Dump entity top-level ID-like properties
log("=== ENTITY ID PROPERTIES ===")
for prop in ["Handle", "ObjectID", "ObjectId", "Id", "UID", "UniqueID",
             "GuidId", "FullSubentPath", "LayerId", "OwnerId"]:
    val = safe_get(entity, prop)
    log(f"  entity.{prop} = {val}")
log("")

# Get element
log("=== ENTITY.ELEMENT ===")
element = safe_get(entity, "Element")
if isinstance(element, str) and element.startswith("<ERR"):
    log(f"entity.Element unavailable: {element}")
    raise SystemExit

log(f"element type = {type(element)}")
log("")

# Dump element ID-like properties
log("=== ELEMENT ID PROPERTIES ===")
id_props = [
    "ElementId", "ObjectId", "ObjectID", "Id", "UID", "UniqueID", "GUID",
    "GuidId", "Tag", "TagNumber", "Handle", "Name", "TypeName", "ClassName",
    "VcsId", "LibObjectId", "CatalogId", "TypeCode", "Code",
]
for prop in id_props:
    val = safe_get(element, prop)
    log(f"  element.{prop} = {val}")
log("")

# Dump all via dir()
log("=== ALL element ATTRIBUTES (dir) ===")
try:
    attrs = [a for a in dir(element) if not a.startswith("_")]
    log(f"Count: {len(attrs)}")
    for attr in attrs:
        val = safe_get(element, attr)
        if callable(val) and not isinstance(val, str):
            log(f"  [method] {attr}")
        else:
            log(f"  {attr} = {val}")
except Exception as ex:
    log(f"dir(element) failed: {ex}")
log("")

# Try element.Parameters — dump first parameter item in detail
log("=== ELEMENT.PARAMETERS FIRST ITEM ===")
try:
    params = element.Parameters
    log(f"parameters type = {type(params)}")
    count = safe_get(params, "Count")
    log(f"parameters Count = {count}")

    # Get first item
    first = None
    for getter in [lambda: params.Item(0), lambda: params.Item(1), lambda: params[0]]:
        r = safe_call(getter)
        if not (isinstance(r, str) and r.startswith("<ERR")):
            first = r
            break

    if first:
        log(f"first param type = {type(first)}")
        log("first param attrs:")
        for attr in [a for a in dir(first) if not a.startswith("_")]:
            val = safe_get(first, attr)
            log(f"  {attr} = {val}")
except Exception as ex:
    log(f"parameters probe failed: {ex}")
log("")

# Try mstManagedAPI.dll loading
log("=== mstManagedAPI.dll LOAD TEST ===")
MST_DLL = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll"
try:
    import clr
    import System.Reflection
    asm = System.Reflection.Assembly.LoadFrom(MST_DLL)
    log(f"Assembly.LoadFrom OK: {asm.FullName}")
    types = [t.FullName for t in asm.GetExportedTypes()]
    log(f"Exported types ({len(types)}): {types}")
except Exception as ex:
    log(f"LoadFrom failed: {ex}")
log("")

log("=== probe_element_properties.py end ===")
log(f"Log: {LOG_PATH}")

try:
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.Popup(f"Probe done.\nLog: {LOG_PATH}", 5, "DTMX element probe", 64)
except Exception:
    pass
