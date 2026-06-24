using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using SCXComponentsLibLib;

#if NCAD
using Teigha.DatabaseServices;
using Teigha.Runtime;
using HostMgd.ApplicationServices;
using HostMgd.EditorInput;
#else
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Runtime;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.ApplicationServices;
#endif

[assembly: CommandClass(typeof(DtmxHost6Probe.Host6Probe))]

namespace DtmxHost6Probe
{
    public class Host6Probe
    {
        private const string LogPath = @"C:\Users\atsarkov\Desktop\dtmx_host6_probe_log.txt";
        private const string TargetParam = "PART_TAGNUMBER";
        private const string TargetValue = "DTMX_HOST6";
        private const string MstManagedPath = @"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll";
        private static readonly string[] ReflectionKeywords = new[]
        {
            "element", "param", "part", "model", "studio", "pipe", "segment", "subsegment", "property", "object"
        };

        [CommandMethod("DTMXHOSTPROBE2", CommandFlags.UsePickSet | CommandFlags.Redraw)]
        public static void ProbeSelection()
        {
            ResetLog();
            Log("=== DTMXHOSTPROBE start ===");
            Log("Assembly = " + Assembly.GetExecutingAssembly().Location);

            try
            {
                var doc = HostMgd.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
                if (doc == null)
                {
                    Log("ActiveDocument = null");
                    return;
                }

                var db = doc.Database;
                var ed = doc.Editor;
                object appCom = GetActiveComObject("nanoCADx64.Application.24.0");
                object docCom = InvokeMember(appCom, "ActiveDocument");

                Log("Document = " + Safe(() => doc.Name));
                Log("Database = " + (db == null ? "null" : db.GetType().FullName));

                var ids = ResolveTargetIds(doc, db, ed, docCom);
                Log("Resolved.Count = " + ids.Length);

                using (var tr = db.TransactionManager.StartTransaction())
                {
                    for (var index = 0; index < ids.Length; index++)
                    {
                        var id = ids[index];
                        try
                        {
                            var obj = tr.GetObject(id, OpenMode.ForRead, false);
                            Log($"[{index}] ObjectId={id} Handle={Safe(() => obj.Handle.ToString())} Type={obj.GetType().FullName} Rx={Safe(() => obj.GetRXClass().Name)}");
                            DumpInterestingProperties(obj, index);
                        }
                        catch (System.Exception ex)
                        {
                            Log($"[{index}] Open error: {ex}");
                        }
                    }

                    tr.Commit();
                }

                Log("=== DTMXHOSTPROBE done ===");
            }
            catch (System.Exception ex)
            {
                Log("Fatal: " + ex);
            }
        }

        [CommandMethod("DTMXHOSTSETTAG2", CommandFlags.UsePickSet | CommandFlags.Redraw)]
        public static void SetTagViaInprocCom()
        {
            ResetLog();
            Log("=== DTMXHOSTSETTAG start ===");

            try
            {
                var doc = HostMgd.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
                if (doc == null)
                {
                    Log("ActiveDocument = null");
                    return;
                }

                object appCom = GetActiveComObject("nanoCADx64.Application.24.0");
                object docCom = InvokeMember(appCom, "ActiveDocument");
                var ids = ResolveTargetIds(doc, doc.Database, doc.Editor, docCom);
                Log("Resolved.Count = " + ids.Length);
                if (ids.Length == 0)
                {
                    return;
                }
                Log("COM ActiveDocument.Name = " + Safe(() => InvokeMember(docCom, "Name")?.ToString()));

                int changed = 0;
                int typedOk = 0;
                int fallbackOk = 0;

                using (var tr = doc.Database.TransactionManager.StartTransaction())
                {
                    for (var index = 0; index < ids.Length; index++)
                    {
                        var dbObj = tr.GetObject(ids[index], OpenMode.ForRead, false);
                        var handle = dbObj.Handle.ToString();
                        var rx = Safe(() => dbObj.GetRXClass().Name);
                        Log($"[{index}] Handle={handle} Rx={rx}");

                        object entCom = null;
                        try
                        {
                            entCom = InvokeMember(docCom, "HandleToObject", handle);
                        }
                        catch (System.Exception ex)
                        {
                            Log($"[{index}] HandleToObject error: {ex.Message}");
                            continue;
                        }

                        if (entCom == null)
                        {
                            Log($"[{index}] HandleToObject returned null");
                            continue;
                        }

                        var objectName = Safe(() => InvokeMember(entCom, "ObjectName")?.ToString());
                        Log($"[{index}] COM ObjectName={objectName}");
                        if (!string.Equals(objectName, "vCSSubSegment", StringComparison.OrdinalIgnoreCase))
                        {
                            Log($"[{index}] skipped by ObjectName");
                            continue;
                        }

                        var element = InvokeMember(entCom, "Element");
                        var paramsObj = InvokeMember(element, "Parameters");
                        var before = Safe(() => InvokeMember(element, "GetValue", TargetParam)?.ToString());
                        Log($"[{index}] Before={before}");

                        bool done = false;
                        IntPtr punk = IntPtr.Zero;
                        try
                        {
                            punk = Marshal.GetIUnknownForObject(paramsObj);
                            var typed = (IPEParameters)Marshal.GetTypedObjectForIUnknown(punk, typeof(IPEParameters));
                            typed.Set(TargetParam, TargetValue, "");
                            done = true;
                            typedOk++;
                            Log($"[{index}] typed IPEParameters.Set OK");
                        }
                        catch (System.Exception ex)
                        {
                            Log($"[{index}] typed IPEParameters.Set error: {ex.Message}");
                        }
                        finally
                        {
                            if (punk != IntPtr.Zero)
                            {
                                Marshal.Release(punk);
                            }
                        }

                        if (!done)
                        {
                            try
                            {
                                InvokeMember(paramsObj, "SetParameter", TargetParam, TargetValue, "", "");
                                fallbackOk++;
                                done = true;
                                Log($"[{index}] fallback SetParameter(4) OK");
                            }
                            catch (System.Exception ex)
                            {
                                Log($"[{index}] fallback SetParameter(4) error: {ex.Message}");
                            }
                        }

                        try
                        {
                            InvokeMember(entCom, "Update");
                        }
                        catch (System.Exception ex)
                        {
                            Log($"[{index}] Update error: {ex.Message}");
                        }

                        var after = Safe(() => InvokeMember(element, "GetValue", TargetParam)?.ToString());
                        Log($"[{index}] After={after}");

                        if (done)
                        {
                            changed++;
                        }
                    }

                    tr.Commit();
                }

                try
                {
                    InvokeMember(docCom, "Regen", 1);
                }
                catch (System.Exception ex)
                {
                    Log("Regen error: " + ex.Message);
                }

                Log($"RESULT changed={changed} typedOk={typedOk} fallbackOk={fallbackOk}");
                Log("=== DTMXHOSTSETTAG done ===");
            }
            catch (System.Exception ex)
            {
                Log("Fatal: " + ex);
            }
        }

        [CommandMethod("DTMXMSTSET2", CommandFlags.UsePickSet | CommandFlags.Redraw)]
        public static unsafe void SetTagViaMstManagedApi()
        {
            ResetLog();
            Log("=== DTMXMSTSET start ===");

            try
            {
                var doc = HostMgd.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
                if (doc == null)
                {
                    Log("ActiveDocument = null");
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

                Log("CElement type = " + cElementType.FullName);
                Log("IElement native type = " + iElementType.FullName);
                Log("Pointer ctor found = " + (ctor != null));

                object appCom = GetActiveComObject("nanoCADx64.Application.24.0");
                object docCom = InvokeMember(appCom, "ActiveDocument");
                var ids = ResolveTargetIds(doc, doc.Database, doc.Editor, docCom);
                Log("Resolved.Count = " + ids.Length);
                if (ids.Length == 0)
                {
                    return;
                }

                int changed = 0;

                using (var tr = doc.Database.TransactionManager.StartTransaction())
                {
                    for (var index = 0; index < ids.Length; index++)
                    {
                        var dbObj = tr.GetObject(ids[index], OpenMode.ForRead, false);
                        var handle = dbObj.Handle.ToString();
                        Log($"[{index}] Handle={handle} Rx={Safe(() => dbObj.GetRXClass().Name)}");

                        object entCom;
                        object elementCom;
                        IntPtr punk = IntPtr.Zero;
                        IntPtr pElement = IntPtr.Zero;

                        try
                        {
                            entCom = InvokeMember(docCom, "HandleToObject", handle);
                            elementCom = InvokeMember(entCom, "Element");

                            punk = Marshal.GetIUnknownForObject(elementCom);
                            Log($"[{index}] element IUnknown = 0x{punk.ToInt64():X}");
                            var iidElement = new Guid("{32D3F761-7B49-4D57-AC6C-0D0879AC9A75}");
                            var hr = Marshal.QueryInterface(punk, ref iidElement, out pElement);
                            Log($"[{index}] QueryInterface(IElement) hr = 0x{hr:X}");
                            if (hr != 0 || pElement == IntPtr.Zero)
                            {
                                throw new COMException("QueryInterface(IElement) failed", hr);
                            }

                            var boxedPtr = Pointer.Box(pElement.ToPointer(), elementPtrType);
                            var cElement = ctor.Invoke(new[] { boxedPtr });
                            Log($"[{index}] CElement instance = {cElement.GetType().FullName}");

                            var before = cElementType.InvokeMember(
                                "GetParameterValue",
                                BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                                null,
                                cElement,
                                new object[] { TargetParam, string.Empty });
                            Log($"[{index}] mstManagedAPI before = {FormatValue(before)}");

                            cElementType.InvokeMember(
                                "SetParameter",
                                BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                                null,
                                cElement,
                                new object[] { TargetParam, "DTMX_MSTAPI", string.Empty, string.Empty });
                            Log($"[{index}] mstManagedAPI SetParameter invoked");

                            try
                            {
                                InvokeMember(entCom, "Update");
                            }
                            catch (System.Exception ex)
                            {
                                Log($"[{index}] COM Update error: {ex.Message}");
                            }

                            var after = cElementType.InvokeMember(
                                "GetParameterValue",
                                BindingFlags.InvokeMethod | BindingFlags.Public | BindingFlags.Instance,
                                null,
                                cElement,
                                new object[] { TargetParam, string.Empty });
                            Log($"[{index}] mstManagedAPI after = {FormatValue(after)}");

                            var comAfter = Safe(() => InvokeMember(elementCom, "GetValue", TargetParam)?.ToString());
                            Log($"[{index}] COM verify after = {comAfter}");
                            changed++;
                        }
                        catch (System.Exception ex)
                        {
                            Log($"[{index}] ERROR: {ex}");
                        }
                        finally
                        {
                            if (pElement != IntPtr.Zero)
                            {
                                Marshal.Release(pElement);
                            }
                            if (punk != IntPtr.Zero)
                            {
                                Marshal.Release(punk);
                            }
                        }
                    }

                    tr.Commit();
                }

                try
                {
                    InvokeMember(docCom, "Regen", 1);
                }
                catch (System.Exception ex)
                {
                    Log("Regen error: " + ex.Message);
                }

                Log($"RESULT changed={changed}");
                Log("=== DTMXMSTSET done ===");
            }
            catch (System.Exception ex)
            {
                Log("Fatal: " + ex);
            }
        }

        private static void DumpInterestingProperties(DBObject obj, int index)
        {
            var type = obj.GetType();
            foreach (var name in new[] { "Element", "Parameters", "PartType", "PartTypeName", "Name" })
            {
                try
                {
                    var prop = type.GetProperty(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                    if (prop == null)
                    {
                        continue;
                    }

                    object value;
                    try
                    {
                        value = prop.GetValue(obj, null);
                    }
                    catch (System.Exception ex)
                    {
                        Log($"[{index}] PROP {name} read error: {ex.GetType().FullName}: {ex.Message}");
                        continue;
                    }

                    Log($"[{index}] PROP {name} Type={prop.PropertyType.FullName} Value={FormatValue(value)}");
                }
                catch (System.Exception ex)
                {
                    Log($"[{index}] PROP {name} lookup error: {ex.GetType().FullName}: {ex.Message}");
                }
            }

            DumpReflectiveMembers(type, index);
        }

        private static ObjectId[] ResolveTargetIds(Document doc, Database db, Editor ed, object docCom)
        {
            var implied = ed.SelectImplied();
            Log("SelectImplied.Status = " + implied.Status);
            if (implied.Value != null)
            {
                var selected = implied.Value.GetObjectIds();
                Log("SelectImplied.Count = " + selected.Length);
                if (selected.Length > 0)
                {
                    return selected;
                }
            }
            else
            {
                Log("SelectImplied.Value = null");
            }

            Log("Fallback scan for first vCSSubSegment...");

            using (var tr = db.TransactionManager.StartTransaction())
            {
                var blockTable = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                var modelSpace = (BlockTableRecord)tr.GetObject(blockTable[BlockTableRecord.ModelSpace], OpenMode.ForRead);

                foreach (ObjectId id in modelSpace)
                {
                    try
                    {
                        var obj = tr.GetObject(id, OpenMode.ForRead, false);
                        var handle = obj.Handle.ToString();
                        var entCom = InvokeMember(docCom, "HandleToObject", handle);
                        var objectName = Safe(() => InvokeMember(entCom, "ObjectName")?.ToString());
                        if (string.Equals(objectName, "vCSSubSegment", StringComparison.OrdinalIgnoreCase))
                        {
                            Log("Fallback found handle = " + handle);
                            tr.Commit();
                            return new[] { id };
                        }
                    }
                    catch (System.Exception ex)
                    {
                        Log("Fallback scan item error: " + ex.Message);
                    }
                }

                tr.Commit();
            }

            Log("Fallback found nothing");
            return Array.Empty<ObjectId>();
        }

        private static void DumpReflectiveMembers(Type type, int index)
        {
            try
            {
                Log($"[{index}] TYPE FullName={type.FullName}");

                foreach (var prop in type.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
                {
                    if (!IsInteresting(prop.Name) && !IsInteresting(prop.PropertyType.FullName))
                    {
                        continue;
                    }

                    Log($"[{index}] REF PROP {prop.PropertyType.FullName} {prop.Name}");
                }

                foreach (var field in type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
                {
                    if (!IsInteresting(field.Name) && !IsInteresting(field.FieldType.FullName))
                    {
                        continue;
                    }

                    Log($"[{index}] REF FIELD {field.FieldType.FullName} {field.Name}");
                }

                foreach (var method in type.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
                {
                    if (method.IsSpecialName)
                    {
                        continue;
                    }

                    if (!IsInteresting(method.Name) && !IsInteresting(method.ReturnType.FullName))
                    {
                        var hit = false;
                        foreach (var p in method.GetParameters())
                        {
                            if (IsInteresting(p.Name) || IsInteresting(p.ParameterType.FullName))
                            {
                                hit = true;
                                break;
                            }
                        }

                        if (!hit)
                        {
                            continue;
                        }
                    }

                    Log($"[{index}] REF METHOD {method}");
                }
            }
            catch (System.Exception ex)
            {
                Log($"[{index}] Reflection dump error: {ex}");
            }
        }

        private static string FormatValue(object value)
        {
            if (value == null)
            {
                return "<null>";
            }

            return value + " [" + value.GetType().FullName + "]";
        }

        private static string Safe(Func<string> getter)
        {
            try
            {
                return getter() ?? "<null>";
            }
            catch (System.Exception ex)
            {
                return "<error: " + ex.GetType().Name + ": " + ex.Message + ">";
            }
        }

        private static bool IsInteresting(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            foreach (var keyword in ReflectionKeywords)
            {
                if (text.IndexOf(keyword, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
            }

            return false;
        }

        private static void ResetLog()
        {
            File.WriteAllText(LogPath, string.Empty);
        }

        private static void Log(string text)
        {
            File.AppendAllText(LogPath, DateTime.Now.ToString("HH:mm:ss") + " | " + text + Environment.NewLine);
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

        private static object InvokeMember(object target, string name, params object[] args)
        {
            return target.GetType().InvokeMember(
                name,
                BindingFlags.Public | BindingFlags.Instance | BindingFlags.GetProperty | BindingFlags.InvokeMethod,
                null,
                target,
                args.Length == 0 ? null : args);
        }

        [DllImport("ole32.dll", CharSet = CharSet.Unicode)]
        private static extern int CLSIDFromProgID(string progId, out Guid clsid);

        [DllImport("ole32.dll", CharSet = CharSet.Unicode)]
        private static extern int CLSIDFromProgIDEx(string progId, out Guid clsid);

        [DllImport("oleaut32.dll")]
        private static extern int GetActiveObject(ref Guid rclsid, IntPtr reserved, [MarshalAs(UnmanagedType.Interface)] out object ppunk);
    }
}
