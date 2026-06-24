using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Multicad.Runtime;

[assembly: CommandClass(typeof(DtmxPureDotNet.ProbePureDotNet))]

namespace DtmxPureDotNet
{
    [ContainsCommands]
    public class ProbePureDotNet : IExtensionApplication
    {
        private const string LogPath = @"C:\Users\atsarkov\Desktop\dtmx_puredotnet_log.txt";
        private static bool _registered;

        public void Initialize()
        {
            if (_registered) return;
            _registered = true;

            File.AppendAllText(LogPath, $"{DateTime.Now:HH:mm:ss} Initialize{Environment.NewLine}");
            try
            {
                var asm = Assembly.GetExecutingAssembly();
                var mapimgd = typeof(CommandMethodAttribute).Assembly;
                var amType = mapimgd.GetType("Multicad.AssemblyManaging");
                var gpProp = amType?.GetProperty("gpNetLoader", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
                var loader = gpProp?.GetValue(null);
                var loadCmds = loader?.GetType().GetMethod("loadCommands", BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public);
                var result = loadCmds?.Invoke(loader, new object[] { typeof(ProbePureDotNet) });
                File.AppendAllText(LogPath, $"Assembly={asm.FullName}{Environment.NewLine}");
                File.AppendAllText(LogPath, $"loadCommands={result}{Environment.NewLine}");
                File.AppendAllText(LogPath, $"{DateTime.Now:HH:mm:ss} === AUTORUN start ==={Environment.NewLine}");
                LogLoadedAssemblies();
                ProbeProjectService();
                ProbeStaticFactories();
                File.AppendAllText(LogPath, $"{DateTime.Now:HH:mm:ss} === AUTORUN done ==={Environment.NewLine}");
            }
            catch (Exception ex)
            {
                File.AppendAllText(LogPath, $"Initialize EXCEPTION: {ex}{Environment.NewLine}");
            }
        }

        public void Terminate() { }

        [CommandMethod("DTMX", "DTMXPUREDOTNET", "DTMXPUREDOTNET", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public static void Run()
        {
            File.AppendAllText(LogPath, $"{DateTime.Now:HH:mm:ss} === DTMXPUREDOTNET start ==={Environment.NewLine}");
            try
            {
                LogLoadedAssemblies();
                ProbeProjectService();
                ProbeStaticFactories();
            }
            catch (Exception ex)
            {
                File.AppendAllText(LogPath, $"Run EXCEPTION: {ex}{Environment.NewLine}");
            }

            File.AppendAllText(LogPath, $"{DateTime.Now:HH:mm:ss} === DTMXPUREDOTNET done ==={Environment.NewLine}");
        }

        private static void LogLoadedAssemblies()
        {
            var loaded = AppDomain.CurrentDomain.GetAssemblies()
                .OrderBy(a => a.GetName().Name)
                .Where(a =>
                {
                    var n = a.GetName().Name ?? "";
                    return n.IndexOf("mst", StringComparison.OrdinalIgnoreCase) >= 0 ||
                           n.IndexOf("mstudio", StringComparison.OrdinalIgnoreCase) >= 0 ||
                           n.IndexOf("CS", StringComparison.OrdinalIgnoreCase) >= 0;
                });

            foreach (var asm in loaded)
            {
                File.AppendAllText(LogPath, $"LoadedAsm: {asm.FullName}{Environment.NewLine}");
            }
        }

        private static void ProbeProjectService()
        {
            File.AppendAllText(LogPath, "ProjectService probe..."+Environment.NewLine);
            try
            {
                try
                {
                    var pbhType = Type.GetType("mstManagedAPI.ProjectBuildingHierarchy, mstManagedAPI", throwOnError: true);
                    var collect = pbhType.GetMethod("CollectObjectsFactoryData", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
                    var collectResult = collect?.Invoke(null, null);
                    File.AppendAllText(LogPath, $"CollectObjectsFactoryData => {collectResult ?? "<null>"}{Environment.NewLine}");
                }
                catch (Exception ex)
                {
                    File.AppendAllText(LogPath, $"CollectObjectsFactoryData ERROR: {ex}{Environment.NewLine}");
                }

                var t = Type.GetType("mstManagedAPI.ProjectService, mstManagedAPI", throwOnError: true);
                var obj = Activator.CreateInstance(t);
                File.AppendAllText(LogPath, "ProjectService ctor OK"+Environment.NewLine);

                foreach (var name in new[] { "OpenWindowsSession", "ConnectionIsValid" })
                {
                    try
                    {
                        var method = t.GetMethod(name);
                        if (method == null)
                        {
                            File.AppendAllText(LogPath, $"ProjectService {name}: method not found{Environment.NewLine}");
                            continue;
                        }

                        object result;
                        if (name == "ConnectionIsValid")
                        {
                            var args = new object[] { "" };
                            result = method.Invoke(obj, args);
                            File.AppendAllText(LogPath, $"ProjectService {name} => {result}; out={args[0]}{Environment.NewLine}");
                        }
                        else
                        {
                            result = method.Invoke(obj, null);
                            File.AppendAllText(LogPath, $"ProjectService {name} => {result}{Environment.NewLine}");
                        }
                    }
                    catch (Exception ex)
                    {
                        File.AppendAllText(LogPath, $"ProjectService {name} ERROR: {ex}{Environment.NewLine}");
                    }
                }
            }
            catch (Exception ex)
            {
                File.AppendAllText(LogPath, $"ProjectService ctor ERROR: {ex}{Environment.NewLine}");
            }
        }

        private static void ProbeStaticFactories()
        {
            File.AppendAllText(LogPath, "Static factory probe..."+Environment.NewLine);
            try
            {
                var asm = AppDomain.CurrentDomain.GetAssemblies().FirstOrDefault(a => string.Equals(a.GetName().Name, "mstManagedAPI", StringComparison.OrdinalIgnoreCase));
                if (asm == null)
                {
                    asm = Assembly.Load("mstManagedAPI");
                }

                foreach (var type in asm.GetTypes().Where(t => t.FullName != null && (
                    t.FullName.IndexOf("Factory", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    t.FullName.IndexOf("Core", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    t.FullName.IndexOf("Service", StringComparison.OrdinalIgnoreCase) >= 0)))
                {
                    File.AppendAllText(LogPath, $"Type: {type.FullName}{Environment.NewLine}");
                    foreach (var m in type.GetMethods(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
                    {
                        if (m.IsSpecialName) continue;
                        if (m.Name.IndexOf("Get", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            m.Name.IndexOf("Open", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            m.Name.IndexOf("Current", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            m.Name.IndexOf("Main", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            m.Name.IndexOf("Factory", StringComparison.OrdinalIgnoreCase) >= 0)
                        {
                            File.AppendAllText(LogPath, $"  StaticMethod: {m}{Environment.NewLine}");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                File.AppendAllText(LogPath, $"Static factory probe ERROR: {ex}{Environment.NewLine}");
            }
        }
    }
}
