# -*- coding: utf-8 -*-
# Тест: проверяем GetTypedObjectForIUnknown в-process vs cross-process
# Логирует PID, пробует typed cast на первом доступном vcssubsegment

import ctypes, datetime, os
from pathlib import Path
import win32com.client, pythoncom

LOG_PATH = Path.home() / "Desktop" / "test_typed_cast_log.txt"
MIA = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin"
_PUNK_OFFSET = 16


def log(text=""):
    line = f"{datetime.datetime.now():%H:%M:%S.%f} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


LOG_PATH.write_text("", encoding="utf-8")
log("=== test_typed_cast.py start ===")
log(f"PID = {os.getpid()}")

# Проверяем глобальные переменные nanoCAD
for gvar in ["Application", "ThisDrawing", "doc", "app"]:
    try:
        val = eval(gvar)
        log(f"  global {gvar} доступен: {type(val)}")
    except Exception:
        log(f"  global {gvar} НЕ доступен")

# CLR
try:
    import clr
    import System
    import System.Reflection as Refl
    from System.Runtime.InteropServices import Marshal
    BF = Refl.BindingFlags
    log(f"CLR {System.Environment.Version}")
    log(f"AppDomain = {System.AppDomain.CurrentDomain.FriendlyName}")
except Exception as ex:
    log(f"CLR init error: {ex}"); raise SystemExit

# Загрузка Interop
try:
    scx_asm = Refl.Assembly.LoadFrom(f"{MIA}\\Interop.SCXComponentsLibLib.dll")
    IPEParameters_type = scx_asm.GetType("SCXComponentsLibLib.IPEParameters")
    log(f"Interop.SCXComponentsLibLib OK, IPEParameters: {IPEParameters_type is not None}")
    # Проверяем какой GUID у IPEParameters
    attrs = IPEParameters_type.GetCustomAttributes(True)
    for a in attrs:
        log(f"  attr: {a}")
except Exception as ex:
    log(f"Interop load error: {ex}"); IPEParameters_type = None

# Получаем entity
try:
    app_obj = win32com.client.GetActiveObject("nanoCADx64.Application.24.0")
    doc_obj = app_obj.ActiveDocument
    log(f"win32com app OK  doc={doc_obj.Name}")
except Exception as ex:
    log(f"win32com error: {ex}"); raise SystemExit

# Ищем первый vcssubsegment
entity = None
for attr in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
    try:
        for ent in getattr(doc_obj, attr):
            if str(getattr(ent, "ObjectName", "")).lower() == "vcssubsegment":
                entity = ent; break
    except Exception: pass
    if entity: break

if not entity:
    log("Нет vcssubsegment в выделении"); raise SystemExit

log(f"Entity Handle={entity.Handle}")

element = entity.Element
log(f"element type = {type(element)}")

# Извлекаем нативный IUnknown*
py_iunknown = element._oleobj_.QueryInterface(pythoncom.IID_IUnknown)
raw = ctypes.cast(id(py_iunknown) + _PUNK_OFFSET, ctypes.POINTER(ctypes.c_void_p))[0]
log(f"native IUnknown* = 0x{raw:016X}")

iunk_ptr = System.IntPtr(raw)
element_net = Marshal.GetObjectForIUnknown(iunk_ptr)
log(f"element_net type = {element_net.GetType().FullName}")

# Получаем Parameters
params_raw = element_net.GetType().InvokeMember(
    "Parameters", BF.GetProperty | BF.InvokeMethod | BF.Public | BF.Instance,
    None, element_net, None)
log(f"params_raw type = {params_raw.GetType().FullName}")

# Получаем IUnknown* от params
try:
    params_punk = Marshal.GetIUnknownForObject(params_raw)
    log(f"params IUnknown* = 0x{params_punk.ToInt64():016X}")
except Exception as ex:
    log(f"GetIUnknownForObject error: {ex}"); params_punk = System.IntPtr.Zero

# Пробуем GetTypedObjectForIUnknown
if IPEParameters_type is not None and params_punk != System.IntPtr.Zero:
    try:
        typed = Marshal.GetTypedObjectForIUnknown(params_punk, IPEParameters_type)
        log(f"GetTypedObjectForIUnknown SUCCESS: {typed.GetType()}")
        # Пробуем вызвать Set
        typed.Set("PART_TAGNUMBER", "DTMX_TYPED", "")
        log("IPEParameters.Set() вызван OK!")
        after = str(element.GetValue("PART_TAGNUMBER"))
        log(f"after = {after!r}  (ожидали DTMX_TYPED)")
    except Exception as ex:
        log(f"GetTypedObjectForIUnknown FAILED: {ex}")

# Проверяем IID интерфейса через QueryInterface
log("")
log("--- QueryInterface probe ---")
# IID IPEParameters из Interop: ищем через reflection
try:
    guid_attr = [a for a in IPEParameters_type.GetCustomAttributes(True)
                 if "Guid" in type(a).__name__]
    for a in guid_attr:
        log(f"  IPEParameters IID (from attr): {a}")
    # Попробуем через ComInterfaceType
    iface_type_attr = [a for a in IPEParameters_type.GetCustomAttributes(True)
                       if "Interface" in type(a).__name__]
    for a in iface_type_attr:
        log(f"  InterfaceType: {a}")
except Exception as ex:
    log(f"  attr probe error: {ex}")

# Считаем количество loaded assemblies в AppDomain
asm_names = [a.GetName().Name for a in System.AppDomain.CurrentDomain.GetAssemblies()]
scx_loaded = [n for n in asm_names if "SCX" in n or "CADLib" in n or "mst" in n]
log(f"")
log(f"Loaded SCX/CADLib/mst assemblies в AppDomain:")
for n in scx_loaded:
    log(f"  {n}")

log("")
log("=== test_typed_cast.py end ===")
