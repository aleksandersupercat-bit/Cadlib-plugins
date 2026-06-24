# -*- coding: utf-8 -*-
# Устанавливает PART_TAGNUMBER через typed managed IPEParameters.Set()
# Два пути (пробуются по порядку):
#   1. Typed: загружаем Interop.SCXComponentsLibLib → приводим params к IPEParameters → Set()
#   2. Fallback IDispatch: Type.InvokeMember("SetParameter", 4 аргумента) — как в старом скрипте

import ctypes
import datetime
from pathlib import Path

import win32com.client
import pythoncom

LOG_PATH = Path.home() / "Desktop" / "set_part_tagnumber_typed_log.txt"
TARGET_PARAMETER = "PART_TAGNUMBER"
TARGET_VALUE = "DTMX_NET"
ENTITY_NAMES = {"vcssubsegment"}
MIA = r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin"

_PUNK_OFFSET = 16  # CPython x64: ob_refcnt(8) + ob_type(8) + IUnknown*(8)


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


# ─── Log starts before CLR so failures appear in the file ─────────────────────
reset_log()
log("=== set_part_tagnumber_typed.py start ===")
log(f"Target: {TARGET_PARAMETER} = {TARGET_VALUE}")

# ─── Python.NET init ───────────────────────────────────────────────────────────
try:
    import clr
    log("import clr OK")
except ImportError as ex:
    log(f"import clr FAILED: {ex}"); raise SystemExit

try:
    import System
except ImportError:
    for _a in ("mscorlib", "System", "System.Core"):
        try: clr.AddReference(_a)
        except Exception: pass
    import System

import System.Reflection as Refl
from System.Runtime.InteropServices import Marshal
BF = Refl.BindingFlags
log(f"CLR {System.Environment.Version}")

# ─── Загрузка Interop.SCXComponentsLibLib ─────────────────────────────────────
IPEParameters_type = None

try:
    interop_path = f"{MIA}\\Interop.SCXComponentsLibLib.dll"
    scx_asm = Refl.Assembly.LoadFrom(interop_path)
    log(f"Загружен Interop.SCXComponentsLibLib v{scx_asm.GetName().Version}")

    # Ищем интерфейс IPEParameters
    IPEParameters_type = scx_asm.GetType("SCXComponentsLibLib.IPEParameters")
    if IPEParameters_type:
        log(f"IPEParameters тип найден: {IPEParameters_type.FullName}")
    else:
        log("IPEParameters тип НЕ найден в Interop.SCXComponentsLibLib!")

except Exception as ex:
    log(f"Загрузка Interop.SCXComponentsLibLib FAILED: {ex}")


# ─── ctypes bridge ────────────────────────────────────────────────────────────

def get_native_iunknown(pywin32_com_obj):
    try:
        py_iunknown = pywin32_com_obj._oleobj_.QueryInterface(pythoncom.IID_IUnknown)
        raw = ctypes.cast(
            id(py_iunknown) + _PUNK_OFFSET,
            ctypes.POINTER(ctypes.c_void_p)
        )[0]
        if not raw:
            log("  get_native_iunknown: null pointer")
            return None, None
        return raw, py_iunknown
    except Exception as ex:
        log(f"  get_native_iunknown error: {ex}")
        return None, None


# ─── Typed cast helper ────────────────────────────────────────────────────────

def try_cast_to_interface(com_net_obj, iface_type):
    """Пробует привести System.__ComObject к управляемому интерфейсу через Marshal."""
    if iface_type is None:
        return None
    try:
        # Вариант A: Marshal.GetTypedObjectForIUnknown
        ptr = Marshal.GetIUnknownForObject(com_net_obj)
        typed = Marshal.GetTypedObjectForIUnknown(ptr, iface_type)
        if typed is not None:
            log(f"  Marshal.GetTypedObjectForIUnknown → {typed.GetType()}")
            return typed
    except Exception as ex:
        log(f"  GetTypedObjectForIUnknown error: {ex}")
    try:
        # Вариант B: явный cast через clr
        typed = System.Runtime.InteropServices.Marshal.GetTypedObjectForIUnknown(
            Marshal.GetIUnknownForObject(com_net_obj), iface_type)
        return typed
    except Exception:
        pass
    return None


# ─── IDispatch helpers ────────────────────────────────────────────────────────

def invoke_get(com_net_obj, name):
    return com_net_obj.GetType().InvokeMember(
        name,
        BF.GetProperty | BF.InvokeMethod | BF.Public | BF.Instance,
        None, com_net_obj, None)


def invoke_method(com_net_obj, name, *args):
    net_args = System.Array[System.Object](list(args)) if args else None
    return com_net_obj.GetType().InvokeMember(
        name,
        BF.InvokeMethod | BF.Public | BF.Instance,
        None, com_net_obj, net_args)


# ─── Основная стратегия ───────────────────────────────────────────────────────

def try_set_param(pywin32_element):
    """
    Пробует установить TARGET_PARAMETER через managed typed IPEParameters.Set
    или через IDispatch fallback.
    Возвращает True если успешно.
    """
    raw, keeper = get_native_iunknown(pywin32_element)
    if raw is None:
        return False

    element_net = None
    try:
        iunk_ptr = System.IntPtr(raw)
        element_net = Marshal.GetObjectForIUnknown(iunk_ptr)
        log(f"  GetObjectForIUnknown OK  type={element_net.GetType()}")
    except Exception as ex:
        log(f"  GetObjectForIUnknown error: {ex}")
        return False
    finally:
        keeper = None  # RCW теперь держит свою ссылку

    try:
        params_raw = invoke_get(element_net, "Parameters")
        if params_raw is None:
            log("  Parameters вернул None")
            return False
        log(f"  Parameters OK  type={params_raw.GetType()}")

        # ── Путь 1: типизированный IPEParameters через Interop ────────────────
        if IPEParameters_type is not None:
            typed_params = try_cast_to_interface(params_raw, IPEParameters_type)
            if typed_params is not None:
                try:
                    # IPEParameters.Set(Object Param, Object ParamValue, Object Comment)
                    typed_params.Set(TARGET_PARAMETER, TARGET_VALUE, "")
                    log("  IPEParameters.Set() typed path — вызван OK")
                    after = str(pywin32_element.GetValue(TARGET_PARAMETER))
                    log(f"  after (COM verify) = {after!r}")
                    if after == TARGET_VALUE:
                        log("  ✓ Typed path SUCCESS")
                        return True
                    log("  Typed path: значение не сохранилось, пробуем IDispatch fallback")
                except Exception as ex:
                    log(f"  IPEParameters.Set typed error: {ex}")

        # ── Путь 2: IDispatch Set(3 аргумента) ───────────────────────────────
        try:
            invoke_method(params_raw, "Set", TARGET_PARAMETER, TARGET_VALUE, "")
            log("  IDispatch Set(3) вызван OK")
            after = str(pywin32_element.GetValue(TARGET_PARAMETER))
            log(f"  after (COM verify) = {after!r}")
            if after == TARGET_VALUE:
                log("  ✓ IDispatch Set(3) SUCCESS")
                return True
        except Exception as ex:
            log(f"  IDispatch Set(3) error: {ex}")

        # ── Путь 3: IDispatch SetParameter(4 аргумента) ──────────────────────
        invoke_method(params_raw, "SetParameter",
                      TARGET_PARAMETER, TARGET_VALUE, "", "")
        log("  IDispatch SetParameter(4) вызван OK")
        after = str(pywin32_element.GetValue(TARGET_PARAMETER))
        log(f"  after (COM verify) = {after!r}")
        if after == TARGET_VALUE:
            log("  ✓ IDispatch SetParameter(4) SUCCESS")
            return True
        log(f"  FAILED — значение осталось '{after}'")
        return False

    except Exception as ex:
        log(f"  try_set_param error: {ex}")
        return False
    finally:
        if element_net is not None:
            try:
                Marshal.ReleaseComObject(element_net)
            except Exception:
                pass


# ─── win32com entity access ───────────────────────────────────────────────────

def get_app():
    for progid in ["nanoCADx64.Application.24.0", "nanoCADx64.Application",
                   "nanoCAD.Application.24.0", "nanoCAD.Application"]:
        try:
            app = win32com.client.GetActiveObject(progid)
            log(f"win32com.GetActiveObject({progid}) OK")
            return app
        except Exception:
            pass
    try:
        log("using global Application")
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


def get_selected_vcs(doc):
    entities = []
    for attr in ["ActiveSelectionSet", "PickfirstSelectionSet"]:
        try:
            sel = list(getattr(doc, attr))
            log(f"{attr} count: {len(sel)}")
            for ent in sel:
                if norm(safe_get(ent, "ObjectName")) in ENTITY_NAMES:
                    entities.append(ent)
            if entities:
                break
        except Exception as ex:
            log(f"{attr} error: {ex}")
    return entities


# ─── Main ─────────────────────────────────────────────────────────────────────

app = get_app()
doc = get_doc(app)
if doc is None:
    log("ABORT: no active document"); raise SystemExit

entities = get_selected_vcs(doc)
log(f"VCS entities selected: {len(entities)}")

if not entities:
    log("Нет выбранных VCS элементов.")
    try:
        win32com.client.Dispatch("WScript.Shell").Popup(
            "Нет выбранных VCS элементов.\nВыберите элементы трубопровода.",
            5, "DTMX typed setter", 64)
    except Exception:
        pass
    raise SystemExit

changed = 0
failed = 0

for idx, entity in enumerate(entities):
    handle = safe_get(entity, "Handle")
    log(f"--- [{idx}] Handle={handle} ---")

    element = safe_get(entity, "Element")
    if isinstance(element, str):
        log(f"  Element недоступен: {element}"); failed += 1; continue

    try:
        current = str(element.GetValue(TARGET_PARAMETER))
        log(f"  current = {current!r}")
        if current == TARGET_VALUE:
            log("  already set, skip"); changed += 1; continue
    except Exception as ex:
        log(f"  GetValue error: {ex}")

    ok = try_set_param(element)

    if ok:
        try:
            entity.Update()
            doc.Regen(1)
        except Exception as ex:
            log(f"  Update/Regen: {ex}")
        changed += 1
        log("  SUCCESS")
    else:
        failed += 1
        log("  FAILED")

log("")
log("=== ИТОГ ===")
log(f"Всего: {len(entities)} | Изменено: {changed} | Ошибок: {failed}")
log(f"Log: {LOG_PATH}")

try:
    win32com.client.Dispatch("WScript.Shell").Popup(
        f"DTMX typed setter\nВсего: {len(entities)}\nИзменено: {changed}\nОшибок: {failed}\nLog: {LOG_PATH}",
        8, "DTMX typed setter", 64)
except Exception:
    pass

log("=== set_part_tagnumber_typed.py end ===")
