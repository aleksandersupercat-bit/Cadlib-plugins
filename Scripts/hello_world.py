import win32com.client

shell = win32com.client.Dispatch("WScript.Shell")
shell.Popup("HELLO_FROM_PYTHON_COM", 0, "Python COM test", 64)
