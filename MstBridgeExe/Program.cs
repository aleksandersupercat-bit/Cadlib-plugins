using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;

class Program
{
    private const string LogPath = @"C:\Users\atsarkov\Desktop\mst_bridge_exe_log.txt";

    static int Main()
    {
        File.WriteAllText(LogPath, string.Empty);
        Log("=== MstBridgeExe start ===");

        try
        {
            object app = Marshal.GetActiveObject("nanoCADx64.Application.24.0");
            object doc = Invoke(app, "ActiveDocument");
            Log("Document = " + Invoke(doc, "Name"));

            object sel = null;
            foreach (var name in new[] { "PickfirstSelectionSet", "ActiveSelectionSet" })
            {
                try
                {
                    sel = Invoke(doc, name);
                    var count = (int)Invoke(sel, "Count");
                    Log(name + " count = " + count);
                    if (count > 0)
                    {
                        break;
                    }
                }
                catch (Exception ex)
                {
                    Log(name + " error: " + ex.Message);
                }
            }

            if (sel == null)
            {
                Log("No selection");
                return 1;
            }

            object entity = null;
            var total = (int)Invoke(sel, "Count");
            for (var i = 0; i < total; i++)
            {
                var item = Invoke(sel, "Item", i);
                var objectName = Safe(() => Invoke(item, "ObjectName")?.ToString());
                if (string.Equals(objectName, "vCSSubSegment", StringComparison.OrdinalIgnoreCase))
                {
                    entity = item;
                    break;
                }
            }

            if (entity == null)
            {
                Log("No vCSSubSegment in selection");
                return 2;
            }

            Log("Handle = " + Safe(() => Invoke(entity, "Handle")?.ToString()));
            var element = Invoke(entity, "Element");
            Log("COM Before = " + Safe(() => Invoke(element, "GetValue", "PART_TAGNUMBER")?.ToString()));

            var asm = Assembly.LoadFrom(@"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll");
            var cElementType = asm.GetType("mstManagedAPI.CElement", true);
            var ctor = cElementType.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                .First(c => c.GetParameters().Length == 1 && c.GetParameters()[0].ParameterType.IsPointer);
            var pointerType = ctor.GetParameters()[0].ParameterType;
            Log("PointerType = " + pointerType.FullName);

            var punk = Marshal.GetIUnknownForObject(element);
            Log("IUnknown = 0x" + punk.ToInt64().ToString("X"));
            var iidElement = new Guid("{32D3F761-7B49-4D57-AC6C-0D0879AC9A75}");
            var hr = Marshal.QueryInterface(punk, ref iidElement, out var pElement);
            Log("QueryInterface(IElement) hr = 0x" + hr.ToString("X"));
            Log("IElement* = 0x" + pElement.ToInt64().ToString("X"));

            try
            {
                unsafe
                {
                    var ptrForCtor = pElement != IntPtr.Zero ? pElement : punk;
                    var boxed = Pointer.Box(ptrForCtor.ToPointer(), pointerType);
                    var cElement = ctor.Invoke(new object[] { boxed });
                    Log("CElement ctor OK");
                    Log("Managed Name = " + Safe(() => cElementType.InvokeMember("get_Name", BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance, null, cElement, null)?.ToString()));
                    Log("Managed ParamsCount = " + Safe(() => cElementType.InvokeMember("get_ParamsCount", BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance, null, cElement, null)?.ToString()));

                    foreach (var pname in new[] { "PART_TAGNUMBER", "PART_TAG", "PART_TYPE", "PART_NAME" })
                    {
                        try
                        {
                            var pObj = cElementType.InvokeMember(
                                "GetParameter",
                                BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                                null,
                                cElement,
                                new object[] { pname });
                            if (pObj == null)
                            {
                                Log($"Managed GetParameter({pname}) = null");
                            }
                            else
                            {
                                var pt = pObj.GetType();
                                Log($"Managed GetParameter({pname}) = {pt.FullName}");
                                Log($"  Name={Safe(() => pt.InvokeMember("get_Name", BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance, null, pObj, null)?.ToString())}");
                                Log($"  Value={Safe(() => pt.InvokeMember("get_Value", BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance, null, pObj, null)?.ToString())}");
                                Log($"  Comment={Safe(() => pt.InvokeMember("get_Comment", BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance, null, pObj, null)?.ToString())}");
                                Log($"  ValueComment={Safe(() => pt.InvokeMember("get_ValueComment", BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance, null, pObj, null)?.ToString())}");
                            }
                        }
                        catch (Exception ex)
                        {
                            Log($"Managed GetParameter({pname}) error: {ex.Message}");
                        }
                    }

                    var before = cElementType.InvokeMember(
                        "GetParameterValue",
                        BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                        null,
                        cElement,
                        new object[] { "PART_TAGNUMBER", string.Empty });
                    Log("Managed Before = " + (before ?? "<null>"));

                    cElementType.InvokeMember(
                        "SetParameter",
                        BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                        null,
                        cElement,
                        new object[] { "PART_TAGNUMBER", "DTMX_MST_EXE", string.Empty, string.Empty });
                    Log("Managed SetParameter invoked");

                    try
                    {
                        Invoke(entity, "Update");
                    }
                    catch (Exception ex)
                    {
                        Log("Update error: " + ex.Message);
                    }

                    var after = cElementType.InvokeMember(
                        "GetParameterValue",
                        BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                        null,
                        cElement,
                        new object[] { "PART_TAGNUMBER", string.Empty });
                    Log("Managed After = " + (after ?? "<null>"));
                    Log("COM After = " + Safe(() => Invoke(element, "GetValue", "PART_TAGNUMBER")?.ToString()));
                }
            }
            finally
            {
                if (pElement != IntPtr.Zero)
                {
                    Marshal.Release(pElement);
                }
                Marshal.Release(punk);
            }

            Log("=== MstBridgeExe done ===");
            return 0;
        }
        catch (Exception ex)
        {
            Log("Fatal: " + ex);
            return 10;
        }
    }

    static object Invoke(object obj, string name, params object[] args)
    {
        return obj.GetType().InvokeMember(
            name,
            BindingFlags.GetProperty | BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
            null,
            obj,
            args.Length == 0 ? null : args);
    }

    static string Safe(Func<string> getter)
    {
        try
        {
            return getter() ?? "<null>";
        }
        catch (Exception ex)
        {
            return "<error: " + ex.Message + ">";
        }
    }

    static void Log(string text)
    {
        File.AppendAllText(LogPath, DateTime.Now.ToString("HH:mm:ss") + " | " + text + Environment.NewLine);
    }
}
