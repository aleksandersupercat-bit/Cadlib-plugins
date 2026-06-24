using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using UnitsCSCom.Interop;

class Program
{
    private const string LogPath = @"C:\Users\atsarkov\Desktop\typed_units_com_exe_log.txt";

    static int Main()
    {
        File.WriteAllText(LogPath, string.Empty);
        Log("=== TypedUnitsComExe start ===");

        try
        {
            object app = Marshal.GetActiveObject("nanoCADx64.Application.24.0");
            object doc = Invoke(app, "ActiveDocument");
            object sel = Invoke(doc, "PickfirstSelectionSet");
            int count = (int)Invoke(sel, "Count");
            Log("PickfirstSelectionSet count = " + count);

            object entity = null;
            for (int i = 0; i < count; i++)
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

            object elementObj = Invoke(entity, "Element");
            object paramsObj = Invoke(elementObj, "Parameters");

            IntPtr pElement = Marshal.GetIUnknownForObject(elementObj);
            IntPtr pParams = Marshal.GetIUnknownForObject(paramsObj);

            try
            {
                var element = (IElement)Marshal.GetTypedObjectForIUnknown(pElement, typeof(IElement));
                var parameters = (IParameters)Marshal.GetTypedObjectForIUnknown(pParams, typeof(IParameters));

                Log("Typed IElement OK");
                Log("Typed IParameters OK");
                Log("IElement.GetValue(PART_TAGNUMBER) before = " + element.GetValue("PART_TAGNUMBER"));

                var existing = parameters.Item("PART_TAGNUMBER");
                if (existing != null)
                {
                    Log("Typed parameter item found");
                    Log("  Name = " + existing.Name);
                    Log("  Value = " + existing.Value);
                    Log("  Comment = " + existing.Comment);
                    Log("  ValueComment = " + existing.ValueComment);
                }

                parameters.SetParameter("PART_TAGNUMBER", "DTMX_TYPED_COM", "", "");
                Log("IParameters.SetParameter invoked");

                try
                {
                    Invoke(entity, "Update");
                }
                catch (Exception ex)
                {
                    Log("Update error: " + ex.Message);
                }

                Log("IElement.GetValue(PART_TAGNUMBER) after = " + element.GetValue("PART_TAGNUMBER"));
                Log("COM verify after = " + Safe(() => Invoke(elementObj, "GetValue", "PART_TAGNUMBER")?.ToString()));
            }
            finally
            {
                Marshal.Release(pElement);
                Marshal.Release(pParams);
            }

            Log("=== TypedUnitsComExe done ===");
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
