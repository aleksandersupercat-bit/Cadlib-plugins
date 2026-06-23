import datetime
from pathlib import Path


LOG_PATH = Path.home() / "Desktop" / "probe_scripted_python_dotnet_log.txt"


def reset_log():
    LOG_PATH.write_text("", encoding="utf-8")


def log(text=""):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {text}"
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def popup(message, title="DTMX .NET probe"):
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        shell.Popup(message, 5, title, 64)
    except Exception as ex:
        log(f"Popup failed: {ex}")


reset_log()
log("=== probe_scripted_python_dotnet.py start ===")
log(f"Log path: {LOG_PATH}")

try:
    import sys

    log(f"Python version = {sys.version}")
except Exception as ex:
    log(f"sys import failed: {ex}")

try:
    import clr

    log("import clr = OK")
except Exception as ex:
    log(f"import clr FAILED: {ex}")
    popup(f"clr import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX .NET probe FAILED")
    log("=== probe_scripted_python_dotnet.py end ===")
    raise SystemExit

try:
    import System

    log("import System = OK")
    log(f"System.String = {System.String}")
    log(f"Environment.Version = {System.Environment.Version}")
except Exception as ex:
    log(f"import System FAILED: {ex}")
    popup(f"System import failed\n{ex}\n\nLog: {LOG_PATH}", "DTMX .NET probe FAILED")
    log("=== probe_scripted_python_dotnet.py end ===")
    raise SystemExit

try:
    clr.AddReference("System.Windows.Forms")
    log("clr.AddReference(System.Windows.Forms) = OK")
    from System.Windows.Forms import MessageBox

    result = MessageBox.Show(
        "Python -> clr -> System.Windows.Forms works",
        "DTMX .NET probe",
    )
    log(f"MessageBox.Show result = {result}")
except Exception as ex:
    log(f"System.Windows.Forms FAILED: {ex}")

popup(f".NET probe finished.\nLog: {LOG_PATH}", "DTMX .NET probe OK")
log("=== probe_scripted_python_dotnet.py end ===")
