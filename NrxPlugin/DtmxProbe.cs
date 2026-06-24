using System;
using System.IO;
using System.Reflection;
using Multicad.Runtime;

[assembly: CommandClass(typeof(DtmxProbe.ProbeApp))]

namespace DtmxProbe
{
    [ContainsCommands]
    public class ProbeApp : IExtensionApplication
    {
        static readonly string LOG = @"C:\Users\atsarkov\Desktop\dtmx_probe_log.txt";
        static bool _registered = false;

        public void Initialize()
        {
            if (_registered) return;
            _registered = true;

            File.AppendAllText(LOG, $"{DateTime.Now:HH:mm:ss} Initialize\n");
            try
            {
                var asm = Assembly.GetExecutingAssembly();
                var mapimgd = typeof(CommandMethodAttribute).Assembly;
                File.AppendAllText(LOG, $"Assembly: {asm.FullName}\n");
                foreach (var attr in asm.GetCustomAttributes(false))
                    File.AppendAllText(LOG, $"AssemblyAttr: {attr.GetType().FullName}\n");

                foreach (var method in typeof(ProbeApp).GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance))
                {
                    foreach (var attr in method.GetCustomAttributes(typeof(CommandMethodAttribute), false))
                    {
                        var cmdAttr = (CommandMethodAttribute)attr;
                        File.AppendAllText(LOG,
                            $"CommandMethod found: method={method.Name}, global={cmdAttr.GlobalName}, group={cmdAttr.GroupName}, flags={cmdAttr.Flags}\n");
                    }
                }

                var amType = mapimgd.GetType("Multicad.AssemblyManaging");
                if (amType == null) { File.AppendAllText(LOG, "AssemblyManaging NOT FOUND\n"); return; }

                var gpProp = amType.GetProperty("gpNetLoader",
                    BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
                if (gpProp == null) { File.AppendAllText(LOG, "gpNetLoader prop NOT FOUND\n"); return; }

                var loader = gpProp.GetValue(null);
                if (loader == null) { File.AppendAllText(LOG, "gpNetLoader is NULL\n"); return; }

                // Вызываем loadCommands напрямую для нашего типа
                var loadCmds = loader.GetType().GetMethod("loadCommands",
                    BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public);
                if (loadCmds == null)
                {
                    // Ищем через все методы
                    File.AppendAllText(LOG, "loadCommands NOT FOUND by name, listing all methods:\n");
                    foreach (var m in loader.GetType().GetMethods(BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public))
                        if (m.Name.IndexOf("ommand", StringComparison.OrdinalIgnoreCase) >= 0 ||
                            m.Name.IndexOf("Load", StringComparison.OrdinalIgnoreCase) >= 0)
                            File.AppendAllText(LOG, $"  {m.Name}({string.Join(", ", Array.ConvertAll(m.GetParameters(), p => p.ParameterType.Name))})\n");
                    return;
                }

                File.AppendAllText(LOG, $"loadCommands found: {loadCmds.Name}\n");
                var result = loadCmds.Invoke(loader, new object[] { typeof(ProbeApp) });
                File.AppendAllText(LOG, $"loadCommands returned: {result}\n");
            }
            catch (Exception ex)
            {
                File.AppendAllText(LOG, $"EXCEPTION: {ex.Message}\n{ex.InnerException?.Message}\n");
            }
        }

        public void Terminate() { }

        [CommandMethod("DTMX", "DTMXPROBE", "DTMXPROBE", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public static void Probe()
        {
            File.AppendAllText(LOG, $"{DateTime.Now:HH:mm:ss} DTMXPROBE OK!\n");
        }
    }
}
