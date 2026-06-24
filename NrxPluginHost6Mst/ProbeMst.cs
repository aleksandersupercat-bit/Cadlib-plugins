using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;

using Teigha.DatabaseServices;
using Teigha.Runtime;

[assembly: CommandClass(typeof(DtmxHost6Mst.ProbeMst))]

namespace DtmxHost6Mst
{
    public class ProbeMst
    {
        private const string LogPath = @"C:\Users\atsarkov\Desktop\dtmx_host6_mst_log.txt";
        private const string MstManagedPath = @"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll";

        [CommandMethod("DTMXPINGMST", CommandFlags.UsePickSet | CommandFlags.Redraw)]
        public static void Ping()
        {
            File.WriteAllText(LogPath, DateTime.Now.ToString("HH:mm:ss") + " | PING" + Environment.NewLine);
        }

        [CommandMethod("DTMXMSTSET2", CommandFlags.UsePickSet | CommandFlags.Redraw)]
        public static unsafe void Set2()
        {
            File.WriteAllText(LogPath, string.Empty);
            Log("=== DTMXMSTSET2 start ===");

            try
            {
                var doc = HostMgd.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
                var implied = doc.Editor.SelectImplied();
                Log("SelectImplied.Status = " + implied.Status);
                if (implied.Value == null)
                {
                    Log("SelectImplied.Value = null");
                    return;
                }

                var ids = implied.Value.GetObjectIds();
                Log("SelectImplied.Count = " + ids.Length);
                if (ids.Length == 0)
                {
                    return;
                }

                var mstAsm = Assembly.LoadFrom(MstManagedPath);
                Log("mstManagedAPI loaded: " + mstAsm.FullName);

                var cElementType = mstAsm.GetType("mstManagedAPI.CElement", true);
                var iElementType = mstAsm.GetType("MStudioData.IElement", true);
                var elementPtrType = iElementType.MakePointerType();
                var ctor = cElementType.GetConstructor(
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance,
                    null,
                    new[] { elementPtrType },
                    null);
                Log("CtorFound = " + (ctor != null));

                object appCom = GetActiveComObject("nanoCADx64.Application.24.0");
                object docCom = InvokeMember(appCom, "ActiveDocument");

                using (var tr = doc.Database.TransactionManager.StartTransaction())
                {
                    var dbObj = tr.GetObject(ids[0], OpenMode.ForRead, false);
                    var handle = dbObj.Handle.ToString();
                    Log("Handle = " + handle);

                    var entCom = InvokeMember(docCom, "HandleToObject", handle);
                    var elementCom = InvokeMember(entCom, "Element");
                    var punk = Marshal.GetIUnknownForObject(elementCom);
                    Log("IUnknown = 0x" + punk.ToInt64().ToString("X"));

                    try
                    {
                        var boxedPtr = Pointer.Box(punk.ToPointer(), elementPtrType);
                        var cElement = ctor.Invoke(new[] { boxedPtr });
                        Log("CElement instance OK");

                        var before = cElementType.InvokeMember(
                            "GetParameterValue",
                            BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                            null,
                            cElement,
                            new object[] { "PART_TAGNUMBER", string.Empty });
                        Log("Before = " + (before ?? "<null>"));

                        cElementType.InvokeMember(
                            "SetParameter",
                            BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                            null,
                            cElement,
                            new object[] { "PART_TAGNUMBER", "DTMX_MST2", string.Empty, string.Empty });
                        Log("SetParameter invoked");

                        InvokeMember(entCom, "Update");
                        var after = cElementType.InvokeMember(
                            "GetParameterValue",
                            BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                            null,
                            cElement,
                            new object[] { "PART_TAGNUMBER", string.Empty });
                        Log("After = " + (after ?? "<null>"));
                    }
                    finally
                    {
                        Marshal.Release(punk);
                    }

                    tr.Commit();
                }

                Log("=== DTMXMSTSET2 done ===");
            }
            catch (System.Exception ex)
            {
                Log("Fatal: " + ex);
            }
        }

        private static object InvokeMember(object target, string name, params object[] args)
        {
            return target.GetType().InvokeMember(
                name,
                BindingFlags.Public | BindingFlags.Instance | BindingFlags.GetProperty | BindingFlags.InvokeMethod,
                null,
                target,
                args.Length == 0 ? null : args);
        }

        private static object GetActiveComObject(string progId)
        {
            var hresult = CLSIDFromProgIDEx(progId, out var clsid);
            if (hresult != 0)
            {
                hresult = CLSIDFromProgID(progId, out clsid);
            }

            if (hresult != 0)
            {
                Marshal.ThrowExceptionForHR(hresult);
            }

            hresult = GetActiveObject(ref clsid, IntPtr.Zero, out var obj);
            if (hresult != 0)
            {
                Marshal.ThrowExceptionForHR(hresult);
            }

            return obj;
        }

        private static void Log(string text)
        {
            File.AppendAllText(LogPath, DateTime.Now.ToString("HH:mm:ss") + " | " + text + Environment.NewLine);
        }

        [DllImport("ole32.dll", CharSet = CharSet.Unicode)]
        private static extern int CLSIDFromProgID(string progId, out Guid clsid);

        [DllImport("ole32.dll", CharSet = CharSet.Unicode)]
        private static extern int CLSIDFromProgIDEx(string progId, out Guid clsid);

        [DllImport("oleaut32.dll")]
        private static extern int GetActiveObject(ref Guid rclsid, IntPtr reserved, [MarshalAs(UnmanagedType.Interface)] out object ppunk);
    }
}
