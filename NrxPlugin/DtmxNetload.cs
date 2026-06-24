using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using Multicad.Runtime;
using SCXComponentsLibLib;

[assembly: CommandClass(typeof(DtmxNetload.DtmxApp))]

namespace DtmxNetload
{
    internal static class AutoRun
    {
        internal const string LogPath = @"C:\Users\atsarkov\Desktop\dtmx_set_inproc_log8.txt";
        internal const string TriggerPath = @"C:\Users\atsarkov\Desktop\dtmx_autorun.flag";
        internal static bool IsAutoRun;
        internal static System.Windows.Forms.Timer Timer;
    }

    [ContainsCommands]
    public class DtmxApp : IExtensionApplication
    {
        public void Initialize()
        {
            try
            {
                File.AppendAllText(AutoRun.LogPath, $"{DateTime.Now:HH:mm:ss} | Initialize{Environment.NewLine}");
                var mapimgd = typeof(CommandMethodAttribute).Assembly;
                var amType = mapimgd.GetType("Multicad.AssemblyManaging");
                if (amType == null)
                {
                    File.AppendAllText(AutoRun.LogPath, "AssemblyManaging NOT FOUND" + Environment.NewLine);
                    return;
                }

                var gpProp = amType.GetProperty("gpNetLoader",
                    BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
                if (gpProp == null)
                {
                    File.AppendAllText(AutoRun.LogPath, "gpNetLoader NOT FOUND" + Environment.NewLine);
                    return;
                }

                var loader = gpProp.GetValue(null);
                if (loader == null)
                {
                    File.AppendAllText(AutoRun.LogPath, "gpNetLoader is NULL" + Environment.NewLine);
                    return;
                }

                var loadCmds = loader.GetType().GetMethod("loadCommands",
                    BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public);
                if (loadCmds == null)
                {
                    File.AppendAllText(AutoRun.LogPath, "loadCommands NOT FOUND" + Environment.NewLine);
                    return;
                }

                var processAssembly = loader.GetType().GetMethod("ProcessAssembly",
                    BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public);
                if (processAssembly != null)
                {
                    var processResult = processAssembly.Invoke(loader, new object[] { Assembly.GetExecutingAssembly() });
                    File.AppendAllText(AutoRun.LogPath, $"ProcessAssembly returned: {processResult}{Environment.NewLine}");
                }

                var result = loadCmds.Invoke(loader, new object[] { typeof(DtmxApp) });
                File.AppendAllText(AutoRun.LogPath, $"loadCommands returned: {result}{Environment.NewLine}");
                foreach (var method in typeof(DtmxApp).GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance))
                {
                    foreach (var attr in method.GetCustomAttributes(typeof(CommandMethodAttribute), false))
                    {
                        var cmdAttr = (CommandMethodAttribute)attr;
                        File.AppendAllText(AutoRun.LogPath,
                            $"CommandMethod found: method={method.Name}, global={cmdAttr.GlobalName}, group={cmdAttr.GroupName}, flags={cmdAttr.Flags}{Environment.NewLine}");
                    }
                }

                if (File.Exists(AutoRun.TriggerPath))
                {
                    File.AppendAllText(AutoRun.LogPath, "AUTORUN trigger found" + Environment.NewLine);
                    AutoRun.IsAutoRun = true;
                    AutoRun.Timer = new System.Windows.Forms.Timer();
                    AutoRun.Timer.Interval = 2000;
                    AutoRun.Timer.Tick += (sender, args) =>
                    {
                        AutoRun.Timer.Stop();
                        File.AppendAllText(AutoRun.LogPath, $"{DateTime.Now:HH:mm:ss} | AUTORUN tick" + Environment.NewLine);
                        DtmxCommandsCore.SetPartTagNumber();
                    };
                    AutoRun.Timer.Start();
                }
            }
            catch (Exception ex)
            {
                File.AppendAllText(AutoRun.LogPath, $"Initialize ERROR: {ex}{Environment.NewLine}");
            }
        }
        public void Terminate() { }
        
        [CommandMethod("DTMX", "DTMXSET6", "DTMXSET6", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public static void SetPartTagNumber()
        {
            DtmxCommandsCore.SetPartTagNumber();
        }

        [CommandMethod("DTMX", "DTMXPING7", "DTMXPING7", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public static void Ping()
        {
            File.AppendAllText(AutoRun.LogPath, $"{DateTime.Now:HH:mm:ss} | DTMXPING7 OK{Environment.NewLine}");
        }
    }

    public class DtmxCommandsCore
    {
        private const string TargetParam = "PART_TAGNUMBER";
        private const string TargetValue = "DTMX_NET";
        private static readonly string LogPath = AutoRun.LogPath;

        private static readonly BindingFlags InstanceFlags =
            BindingFlags.Public | BindingFlags.Instance | BindingFlags.GetProperty | BindingFlags.GetField | BindingFlags.InvokeMethod;

        private static readonly BindingFlags StaticFlags =
            BindingFlags.Public | BindingFlags.Static | BindingFlags.GetProperty | BindingFlags.GetField | BindingFlags.InvokeMethod;

        private static void ResetLog()
        {
            File.WriteAllText(LogPath, string.Empty);
        }

        private static void Log(string text)
        {
            File.AppendAllText(LogPath, $"{DateTime.Now:HH:mm:ss} | {text}{Environment.NewLine}");
        }

        private static void ShowMessage(string msg)
        {
            if (AutoRun.IsAutoRun)
            {
                Log("Message suppressed in autorun: " + msg);
                return;
            }

            System.Windows.Forms.MessageBox.Show(msg, "DTMXSET");
        }

        private static object TryGetMember(object obj, string name)
        {
            if (obj == null)
                return null;

            try
            {
                return obj.GetType().InvokeMember(name, InstanceFlags, null, obj, null);
            }
            catch
            {
                return null;
            }
        }

        private static object TryInvoke(object obj, string name, params object[] args)
        {
            if (obj == null)
                return null;

            try
            {
                return obj.GetType().InvokeMember(name, InstanceFlags, null, obj, args);
            }
            catch
            {
                return null;
            }
        }

        private static string SafeToString(object value)
        {
            return value == null ? string.Empty : value.ToString();
        }

        private static object TryGetActiveAppCom()
        {
            var progIds = new[]
            {
                "nanoCADx64.Application.24.0",
                "nanoCAD.Application.24.0"
            };

            foreach (var progId in progIds)
            {
                try
                {
                    var app = Marshal.GetActiveObject(progId);
                    Log($"COM app OK via {progId}");
                    return app;
                }
                catch (Exception ex)
                {
                    Log($"COM app failed via {progId}: {ex.Message}");
                }
            }

            return null;
        }

        private static int ProcessComPickfirstSelection()
        {
            var app = TryGetActiveAppCom();
            if (app == null)
            {
                Log("COM fallback: app is null");
                return -1;
            }

            object doc;
            try
            {
                doc = TryGetMember(app, "ActiveDocument");
            }
            catch (Exception ex)
            {
                Log($"COM fallback: ActiveDocument failed: {ex.Message}");
                return -1;
            }

            if (doc == null)
            {
                Log("COM fallback: ActiveDocument is null");
                return -1;
            }

            var pickfirst = TryGetMember(doc, "PickfirstSelectionSet");
            if (pickfirst == null)
            {
                Log("COM fallback: PickfirstSelectionSet is null");
                return -1;
            }

            int count;
            try
            {
                count = Convert.ToInt32(TryGetMember(pickfirst, "Count"));
            }
            catch (Exception ex)
            {
                Log($"COM fallback: Count failed: {ex.Message}");
                return -1;
            }

            Log($"COM fallback: PickfirstSelectionSet count = {count}");
            if (count <= 0)
                return 0;

            var changed = 0;
            foreach (var entity in (System.Collections.IEnumerable)pickfirst)
            {
                try
                {
                    var objectName = SafeToString(TryGetMember(entity, "ObjectName"));
                    var entityName = SafeToString(TryGetMember(entity, "EntityName"));
                    var handle = SafeToString(TryGetMember(entity, "Handle"));
                    Log($"COM item ObjectName={objectName} EntityName={entityName} Handle={handle}");

                    if (!objectName.Equals("vcssubsegment", StringComparison.OrdinalIgnoreCase) &&
                        !entityName.Equals("vcssubsegment", StringComparison.OrdinalIgnoreCase))
                    {
                        Log("COM item skipped: not vcssubsegment");
                        continue;
                    }

                    var element = TryGetMember(entity, "Element");
                    if (element == null)
                    {
                        Log("COM item: Element is null");
                        continue;
                    }

                    var paramsObj = TryGetMember(element, "Parameters");
                    if (paramsObj == null)
                    {
                        Log("COM item: Parameters is null");
                        continue;
                    }

                    var before = SafeToString(TryInvoke(element, "GetValue", TargetParam));
                    Log($"COM before = {(string.IsNullOrEmpty(before) ? "<empty>" : before)}");

                    IntPtr punk = IntPtr.Zero;
                    try
                    {
                        punk = Marshal.GetIUnknownForObject(paramsObj);
                        var typed = (IPEParameters)Marshal.GetTypedObjectForIUnknown(punk, typeof(IPEParameters));
                        typed.Set(TargetParam, TargetValue, string.Empty);
                        Log("COM typed IPEParameters.Set() invoked");
                    }
                    catch (Exception ex)
                    {
                        Log($"COM typed path failed: {ex}");
                        TryInvoke(paramsObj, "SetParameter", TargetParam, TargetValue, string.Empty, string.Empty);
                        Log("COM fallback SetParameter(4) invoked");
                    }
                    finally
                    {
                        if (punk != IntPtr.Zero)
                            Marshal.Release(punk);
                    }

                    TryInvoke(entity, "Update");
                    TryInvoke(doc, "Regen", 1);

                    var after = SafeToString(TryInvoke(element, "GetValue", TargetParam));
                    Log($"COM after = {(string.IsNullOrEmpty(after) ? "<empty>" : after)}");
                    if (after == TargetValue)
                        changed++;
                }
                catch (Exception ex)
                {
                    Log($"COM item error: {ex}");
                }
            }

            Log($"COM fallback changed = {changed}");
            return changed;
        }

        private static Type FindType(string fullName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                try
                {
                    var type = asm.GetType(fullName, false);
                    if (type != null)
                        return type;
                }
                catch { }
            }

            return null;
        }

        private static object GetStaticMember(Type type, string name)
        {
            if (type == null)
                return null;

            try
            {
                return type.InvokeMember(name, StaticFlags, null, null, null);
            }
            catch
            {
                return null;
            }
        }

        private static object InvokeStatic(Type type, string name, params object[] args)
        {
            if (type == null)
                return null;

            try
            {
                return type.InvokeMember(name, StaticFlags, null, null, args);
            }
            catch
            {
                return null;
            }
        }

        public static void SetPartTagNumber()
        {
            ResetLog();
            Log("=== DTMXSET start ===");

            var mcObjectManagerType = FindType("Multicad.DatabaseServices.McObjectManager");
            if (mcObjectManagerType == null)
            {
                Log("McObjectManager type not found");
                var changedViaCom = ProcessComPickfirstSelection();
                ShowMessage("DTMXSET: McObjectManager type not found; changed=" + changedViaCom);
                return;
            }

            Log($"McObjectManager type = {mcObjectManagerType.AssemblyQualifiedName}");

            var currentCommandMode = GetStaticMember(mcObjectManagerType, "CurrentCommandMode");
            Log($"CurrentCommandMode = {SafeToString(currentCommandMode)}");

            var selectionSetObj = GetStaticMember(mcObjectManagerType, "SelectionSet");
            if (selectionSetObj == null)
            {
                Log("SelectionSet is null");
                var changedViaCom = ProcessComPickfirstSelection();
                ShowMessage("DTMXSET: SelectionSet is null; changed=" + changedViaCom);
                return;
            }

            Log($"SelectionSet type = {selectionSetObj.GetType().FullName}");

            var currentSelection = TryGetMember(selectionSetObj, "CurrentSelection");
            if (currentSelection == null)
            {
                Log("CurrentSelection is null");
                var changedViaCom = ProcessComPickfirstSelection();
                ShowMessage("DTMXSET: CurrentSelection is null; changed=" + changedViaCom);
                return;
            }

            Log($"CurrentSelection type = {currentSelection.GetType().FullName}");

            var selectionItems = currentSelection as System.Collections.IEnumerable;
            if (selectionItems == null)
            {
                Log("CurrentSelection is not enumerable");
                var changedViaCom = ProcessComPickfirstSelection();
                ShowMessage("DTMXSET: CurrentSelection not enumerable; changed=" + changedViaCom);
                return;
            }

            var changed = 0;
            var skipped = 0;
            var failed = 0;
            var typedSuccess = 0;
            var fallbackSuccess = 0;
            var selectionCount = 0;

            foreach (var objectId in selectionItems)
            {
                selectionCount++;
                object managedObj = null;
                try
                {
                    managedObj = InvokeStatic(mcObjectManagerType, "GetObject", objectId);
                }
                catch (Exception ex)
                {
                    Log($"GetObject failed: {ex}");
                }

                if (managedObj == null)
                {
                    Log($"Object {SafeToString(objectId)} resolved to null");
                    failed++;
                    continue;
                }

                Log($"--- Selected object {SafeToString(objectId)} type={managedObj.GetType().FullName} ---");

                var dbEntityObj = TryGetMember(managedObj, "DbEntity") ?? managedObj;
                Log($"DbEntity candidate type = {dbEntityObj.GetType().FullName}");

                var objectName = SafeToString(TryGetMember(dbEntityObj, "ObjectName"));
                var entityName = SafeToString(TryGetMember(dbEntityObj, "EntityName"));
                var handle = SafeToString(TryGetMember(dbEntityObj, "Handle"));
                Log($"ObjectName={objectName} EntityName={entityName} Handle={handle}");

                if (!objectName.Equals("vcssubsegment", StringComparison.OrdinalIgnoreCase) &&
                    !entityName.Equals("vcssubsegment", StringComparison.OrdinalIgnoreCase))
                {
                    Log("Skipped: not vcssubsegment");
                    skipped++;
                    continue;
                }

                try
                {
                    var element = TryGetMember(dbEntityObj, "Element") ?? TryGetMember(managedObj, "Element");
                    if (element == null)
                    {
                        Log("Element member not found on managed object");
                        failed++;
                        continue;
                    }

                    var paramsObj = TryGetMember(element, "Parameters") ?? TryInvoke(element, "Parameters");
                    if (paramsObj == null)
                    {
                        Log("Parameters object not found");
                        failed++;
                        continue;
                    }

                    Log($"element type = {element.GetType().FullName}");
                    Log($"params type = {paramsObj.GetType().FullName}");

                    string before;
                    try
                    {
                        before = SafeToString(TryInvoke(element, "GetValue", TargetParam));
                    }
                    catch (Exception ex)
                    {
                        Log($"GetValue(before) failed: {ex.Message}");
                        before = string.Empty;
                    }

                    Log($"before = {(string.IsNullOrEmpty(before) ? "<empty>" : before)}");
                    if (before == TargetValue)
                    {
                        Log("already has target value");
                        skipped++;
                        continue;
                    }

                    var done = false;
                    var usedTyped = false;
                    IntPtr punk = IntPtr.Zero;
                    try
                    {
                        punk = Marshal.GetIUnknownForObject(paramsObj);
                        var typed = (IPEParameters)Marshal.GetTypedObjectForIUnknown(punk, typeof(IPEParameters));
                        Log($"typed cast OK: {typed.GetType().FullName}");
                        typed.Set(TargetParam, TargetValue, string.Empty);
                        done = true;
                        usedTyped = true;
                        Log("IPEParameters.Set() invoked");
                    }
                    catch (Exception ex)
                    {
                        Log($"typed path failed: {ex}");
                    }
                    finally
                    {
                        if (punk != IntPtr.Zero)
                            Marshal.Release(punk);
                    }

                    if (!done)
                    {
                        Log("fallback: SetParameter(4)");
                        TryInvoke(paramsObj, "SetParameter", TargetParam, TargetValue, string.Empty, string.Empty);
                    }

                    var updateResult = TryInvoke(dbEntityObj, "Update");
                    Log($"Update result = {SafeToString(updateResult)}");

                    InvokeStatic(mcObjectManagerType, "UpdateAll");
                    Log("McObjectManager.UpdateAll invoked");

                    string after;
                    try
                    {
                        after = SafeToString(TryInvoke(element, "GetValue", TargetParam));
                    }
                    catch (Exception ex)
                    {
                        Log($"GetValue(after) failed: {ex.Message}");
                        after = string.Empty;
                    }

                    Log($"after = {(string.IsNullOrEmpty(after) ? "<empty>" : after)}");
                    if (after == TargetValue)
                    {
                        changed++;
                        if (usedTyped)
                        {
                            typedSuccess++;
                            Log("SUCCESS via typed IPEParameters.Set");
                        }
                        else
                        {
                            fallbackSuccess++;
                            Log("SUCCESS via fallback SetParameter");
                        }
                    }
                    else
                    {
                        failed++;
                        Log("FAILED: value not changed");
                    }
                }
                catch (Exception ex)
                {
                    Log($"[{handle}] ERROR: {ex}");
                    failed++;
                }
            }

            Log($"selectionCount={selectionCount}");
            Log($"Summary changed={changed} skipped={skipped} failed={failed} typedSuccess={typedSuccess} fallbackSuccess={fallbackSuccess}");
            Log($"Log file: {LogPath}");
            ShowMessage($"DTMXSET готово: изменено={changed}, пропущено={skipped}, ошибок={failed}");
        }
    }
}
