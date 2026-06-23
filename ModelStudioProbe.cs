using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
using CADLib;
using CADLibKernel;

namespace ModelStudioProbe
{
    public static class CADLibPluginEntryPoint
    {
        public static ICADLibPlugin RegisterPlugin(PluginsManager manager)
        {
            return new ModelStudioProbePlugin(
                manager.Library,
                manager.MainDBBrowser,
                manager.MainForm
            );
        }
    }

    public sealed class ModelStudioProbePlugin : ICADLibPlugin
    {
        private readonly CADLibrary _library;
        private readonly IDatabaseBrowser _browser;
        private readonly object _mainFormCandidate;
        private readonly string _logFilePath;
        private bool _startupProbeScheduled;

        public ModelStudioProbePlugin(CADLibrary library, IDatabaseBrowser browser, object mainFormCandidate)
        {
            _library = library;
            _browser = browser;
            _mainFormCandidate = mainFormCandidate;
            _logFilePath = LogPathFactory.Create("ModelStudioProbe");

            ProbeLogger.Write(_logFilePath, "Plugin constructed.");
            ProbeLogger.Write(_logFilePath, "Library type: " + SafeTypeName(_library));
            ProbeLogger.Write(_logFilePath, "Browser type: " + SafeTypeName(_browser));
            ProbeLogger.Write(_logFilePath, "Main form candidate type: " + SafeTypeName(_mainFormCandidate));

            ScheduleStartupProbe();
        }

        public MenuStrip GetMenu()
        {
            var menu = new MenuStrip();
            var toolsRoot = new ToolStripMenuItem("Инструменты");
            var probeRoot = new ToolStripMenuItem("DTMXtest ModelStudio Probe");
            var runProbeItem = new ToolStripMenuItem("Run probe + patch");
            var showPathItem = new ToolStripMenuItem("Show log path");

            runProbeItem.Click += delegate
            {
                RunProbeSuite("menu-click");
            };

            showPathItem.Click += delegate
            {
                MessageBox.Show(
                    _logFilePath,
                    "ModelStudioProbe log",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            };

            probeRoot.DropDownItems.Add(runProbeItem);
            probeRoot.DropDownItems.Add(showPathItem);
            toolsRoot.DropDownItems.Add(probeRoot);
            menu.Items.Add(toolsRoot);

            ProbeLogger.Write(_logFilePath, "GetMenu created menu entry.");
            return menu;
        }

        public ToolStripContainer GetToolbars()
        {
            var container = new ToolStripContainer();

            var dtmxToolStrip = new ToolStrip();
            dtmxToolStrip.Name = "DTMXtest";
            dtmxToolStrip.Text = "DTMXtest";
            dtmxToolStrip.Items.Add(CreateProbeButton("DMTX", "Dedicated DTMXtest toolbar button"));

            var miscToolStrip = new ToolStrip();
            miscToolStrip.Name = "Разное";
            miscToolStrip.Text = "Разное";
            miscToolStrip.Items.Add(CreateProbeButton("DMTX", "Attempted merge into 'Разное'"));

            container.TopToolStripPanel.Controls.Add(dtmxToolStrip);
            container.TopToolStripPanel.Controls.Add(miscToolStrip);

            ProbeLogger.Write(_logFilePath, "GetToolbars prepared toolbars: DTMXtest and Разное.");
            return container;
        }

        public void TrackInterfaceItems(InterfaceTracker tracker)
        {
            ProbeLogger.Write(_logFilePath, "TrackInterfaceItems invoked with tracker type: " + SafeTypeName(tracker));
        }

        private ToolStripButton CreateProbeButton(string text, string toolTipText)
        {
            var button = new ToolStripButton(text);
            button.DisplayStyle = ToolStripItemDisplayStyle.ImageAndText;
            button.Image = SystemIcons.Information.ToBitmap();
            button.ToolTipText = toolTipText;
            button.Click += delegate
            {
                RunProbeSuite("toolbar-button");
            };

            return button;
        }

        private void ScheduleStartupProbe()
        {
            if (_startupProbeScheduled)
            {
                return;
            }

            _startupProbeScheduled = true;
            var control = _mainFormCandidate as Control;
            if (control == null)
            {
                ProbeLogger.Write(_logFilePath, "Startup probe skipped: main form is not a Control.");
                return;
            }

            try
            {
                var timer = new Timer();
                timer.Interval = 2500;
                timer.Tick += delegate
                {
                    timer.Stop();
                    timer.Dispose();
                    RunProbeSuite("startup-timer");
                };
                timer.Start();
                ProbeLogger.Write(_logFilePath, "Startup probe timer scheduled.");
            }
            catch (Exception ex)
            {
                ProbeLogger.Write(_logFilePath, "Startup probe timer failed: " + ex);
            }
        }

        private void RunProbeSuite(string reason)
        {
            ProbeLogger.Write(_logFilePath, "========== Probe start: " + reason + " ==========");
            ProbeLogger.Write(_logFilePath, "Main form candidate: " + SafeTypeName(_mainFormCandidate));

            try
            {
                DumpRuntimeEnvironment();
                DumpMainFormSurface();
                TryInjectButtonIntoExistingMiscToolbar();
                TryAddDedicatedRuntimeToolbar();
                TryReflectRibbonLikeSurface();
            }
            catch (Exception ex)
            {
                ProbeLogger.Write(_logFilePath, "RunProbeSuite failed: " + ex);
            }

            ProbeLogger.Write(_logFilePath, "========== Probe end: " + reason + " ==========");
        }

        private void DumpRuntimeEnvironment()
        {
            ProbeLogger.Write(_logFilePath, "Environment.CurrentDirectory = " + Environment.CurrentDirectory);
            ProbeLogger.Write(_logFilePath, "AppDomain.FriendlyName = " + AppDomain.CurrentDomain.FriendlyName);

            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                string fullName;
                try
                {
                    fullName = assembly.FullName;
                }
                catch
                {
                    fullName = "<unavailable>";
                }

                ProbeLogger.Write(_logFilePath, "LoadedAssembly: " + fullName);
            }
        }

        private void DumpMainFormSurface()
        {
            if (_mainFormCandidate == null)
            {
                ProbeLogger.Write(_logFilePath, "Main form surface dump skipped: null.");
                return;
            }

            ProbeLogger.Write(_logFilePath, "Main form type: " + _mainFormCandidate.GetType().FullName);
            DumpMembers(_mainFormCandidate.GetType(), "MainFormMembers");

            var control = _mainFormCandidate as Control;
            if (control == null)
            {
                ProbeLogger.Write(_logFilePath, "Main form candidate is not a Control.");
                return;
            }

            var sb = new StringBuilder();
            DumpControlTree(control, 0, sb);
            ProbeLogger.Write(_logFilePath, sb.ToString());
        }

        private void TryInjectButtonIntoExistingMiscToolbar()
        {
            var control = _mainFormCandidate as Control;
            if (control == null)
            {
                ProbeLogger.Write(_logFilePath, "TryInjectButtonIntoExistingMiscToolbar skipped: main form is not a Control.");
                return;
            }

            foreach (ToolStrip toolStrip in FindControls<ToolStrip>(control))
            {
                var id = toolStrip.Name + " | " + toolStrip.Text;
                ProbeLogger.Write(_logFilePath, "ToolStrip found: " + id);

                if (!ContainsIgnoreCase(toolStrip.Name, "Разное") &&
                    !ContainsIgnoreCase(toolStrip.Text, "Разное") &&
                    !ContainsIgnoreCase(toolStrip.Name, "Misc") &&
                    !ContainsIgnoreCase(toolStrip.Text, "Misc"))
                {
                    continue;
                }

                if (ToolStripHasButton(toolStrip, "DMTX"))
                {
                    ProbeLogger.Write(_logFilePath, "ToolStrip already contains DMTX button: " + id);
                    return;
                }

                try
                {
                    toolStrip.Items.Add(CreateProbeButton("DMTX", "Injected into existing 'Разное'"));
                    ProbeLogger.Write(_logFilePath, "Injected DMTX button into existing ToolStrip: " + id);
                    return;
                }
                catch (Exception ex)
                {
                    ProbeLogger.Write(_logFilePath, "Failed injecting into ToolStrip '" + id + "': " + ex);
                }
            }

            ProbeLogger.Write(_logFilePath, "No existing 'Разное' or 'Misc' ToolStrip found.");
        }

        private void TryAddDedicatedRuntimeToolbar()
        {
            var control = _mainFormCandidate as Control;
            if (control == null)
            {
                ProbeLogger.Write(_logFilePath, "TryAddDedicatedRuntimeToolbar skipped: main form is not a Control.");
                return;
            }

            foreach (ToolStripContainer container in FindControls<ToolStripContainer>(control))
            {
                ProbeLogger.Write(_logFilePath, "ToolStripContainer found: " + container.Name);

                if (RuntimeToolbarExists(container, "DTMXtestRuntime"))
                {
                    ProbeLogger.Write(_logFilePath, "Runtime toolbar already exists.");
                    return;
                }

                try
                {
                    var strip = new ToolStrip();
                    strip.Name = "DTMXtestRuntime";
                    strip.Text = "DTMXtest";
                    strip.Items.Add(CreateProbeButton("DMTX", "Runtime-added toolbar"));
                    container.TopToolStripPanel.Controls.Add(strip);
                    ProbeLogger.Write(_logFilePath, "Runtime toolbar injected into ToolStripContainer.");
                    return;
                }
                catch (Exception ex)
                {
                    ProbeLogger.Write(_logFilePath, "Failed to inject runtime toolbar: " + ex);
                }
            }

            ProbeLogger.Write(_logFilePath, "No ToolStripContainer found on main form.");
        }

        private void TryReflectRibbonLikeSurface()
        {
            if (_mainFormCandidate == null)
            {
                ProbeLogger.Write(_logFilePath, "TryReflectRibbonLikeSurface skipped: null target.");
                return;
            }

            ProbeLogger.Write(_logFilePath, "Reflective ribbon probe started.");
            var visited = new HashSet<object>(ReferenceEqualityComparer.Instance);
            ExploreObject(_mainFormCandidate, "MainForm", 0, visited);
        }

        private void ExploreObject(object instance, string path, int depth, HashSet<object> visited)
        {
            if (instance == null || depth > 3 || visited.Contains(instance))
            {
                return;
            }

            visited.Add(instance);
            var type = instance.GetType();
            var typeName = type.FullName ?? type.Name;
            ProbeLogger.Write(_logFilePath, "ExploreObject: " + path + " => " + typeName);

            if (ContainsAny(typeName, "Ribbon", "Tab", "Tool", "Panel", "Menu"))
            {
                DumpMembers(type, "ReflectiveMatch:" + path);
            }

            PropertyInfo[] properties;
            try
            {
                properties = type.GetProperties(BindingFlags.Instance | BindingFlags.Public);
            }
            catch (Exception ex)
            {
                ProbeLogger.Write(_logFilePath, "Property enumeration failed for " + typeName + ": " + ex.Message);
                return;
            }

            foreach (var property in properties)
            {
                if (property.GetIndexParameters().Length > 0)
                {
                    continue;
                }

                object value = null;
                var valueLoaded = false;
                try
                {
                    value = property.GetValue(instance, null);
                    valueLoaded = true;
                }
                catch (Exception ex)
                {
                    ProbeLogger.Write(_logFilePath, "Property read failed: " + path + "." + property.Name + " => " + ex.Message);
                }

                if (!ContainsAny(property.Name, "Ribbon", "Tab", "Tool", "Panel", "Menu", "Button", "Command"))
                {
                    continue;
                }

                ProbeLogger.Write(
                    _logFilePath,
                    "Property probe: " + path + "." + property.Name + " : " + property.PropertyType.FullName +
                    " => " + (valueLoaded ? SafeTypeName(value) : "<read-failed>")
                );

                if (value != null)
                {
                    ExploreObject(value, path + "." + property.Name, depth + 1, visited);
                }
            }
        }

        private void DumpMembers(Type type, string title)
        {
            var sb = new StringBuilder();
            sb.AppendLine(title + " => " + type.FullName);

            foreach (var property in type.GetProperties(BindingFlags.Instance | BindingFlags.Public))
            {
                sb.AppendLine("  P " + property.PropertyType.Name + " " + property.Name);
            }

            foreach (var method in type.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.DeclaredOnly))
            {
                if (!ContainsAny(method.Name, "Ribbon", "Tab", "Tool", "Panel", "Menu", "Button", "Command", "Add", "Insert"))
                {
                    continue;
                }

                sb.Append("  M ");
                sb.Append(method.ReturnType.Name);
                sb.Append(" ");
                sb.Append(method.Name);
                sb.Append("(");

                var parameters = method.GetParameters();
                for (var i = 0; i < parameters.Length; i++)
                {
                    if (i > 0)
                    {
                        sb.Append(", ");
                    }

                    sb.Append(parameters[i].ParameterType.Name);
                    sb.Append(" ");
                    sb.Append(parameters[i].Name);
                }

                sb.AppendLine(")");
            }

            ProbeLogger.Write(_logFilePath, sb.ToString());
        }

        private static void DumpControlTree(Control control, int depth, StringBuilder sb)
        {
            if (control == null || depth > 6)
            {
                return;
            }

            sb.Append(' ', depth * 2);
            sb.Append(control.GetType().FullName);
            sb.Append(" | Name=");
            sb.Append(control.Name);
            sb.Append(" | Text=");
            sb.Append(control.Text);
            sb.Append(" | Visible=");
            sb.Append(control.Visible);
            sb.AppendLine();

            foreach (Control child in control.Controls)
            {
                DumpControlTree(child, depth + 1, sb);
            }
        }

        private static IEnumerable<T> FindControls<T>(Control root) where T : Control
        {
            var results = new List<T>();
            FindControlsRecursive(root, results);
            return results;
        }

        private static void FindControlsRecursive<T>(Control root, List<T> results) where T : Control
        {
            if (root == null)
            {
                return;
            }

            var directHit = root as T;
            if (directHit != null)
            {
                results.Add(directHit);
            }

            foreach (Control child in root.Controls)
            {
                FindControlsRecursive(child, results);
            }
        }

        private static bool RuntimeToolbarExists(ToolStripContainer container, string toolbarName)
        {
            foreach (Control child in container.TopToolStripPanel.Controls)
            {
                var toolStrip = child as ToolStrip;
                if (toolStrip != null && string.Equals(toolStrip.Name, toolbarName, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        private static bool ToolStripHasButton(ToolStrip toolStrip, string text)
        {
            foreach (ToolStripItem item in toolStrip.Items)
            {
                if (string.Equals(item.Text, text, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }

            return false;
        }

        private static bool ContainsIgnoreCase(string source, string value)
        {
            return !string.IsNullOrEmpty(source) &&
                   source.IndexOf(value, StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private static bool ContainsAny(string source, params string[] patterns)
        {
            if (string.IsNullOrEmpty(source))
            {
                return false;
            }

            foreach (var pattern in patterns)
            {
                if (source.IndexOf(pattern, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
            }

            return false;
        }

        private static string SafeTypeName(object value)
        {
            return value == null ? "<null>" : value.GetType().FullName;
        }
    }

    internal static class LogPathFactory
    {
        public static string Create(string prefix)
        {
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            var root = Path.Combine(appData, "CSoft", "Model Studio CS", "Library3D", "DTMXtestLogs");
            Directory.CreateDirectory(root);
            return Path.Combine(root, prefix + "_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".log");
        }
    }

    internal static class ProbeLogger
    {
        private static readonly object SyncRoot = new object();

        public static void Write(string path, string message)
        {
            lock (SyncRoot)
            {
                File.AppendAllText(
                    path,
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " | " + message + Environment.NewLine,
                    Encoding.UTF8
                );
            }
        }
    }

    internal sealed class ReferenceEqualityComparer : IEqualityComparer<object>
    {
        public static readonly ReferenceEqualityComparer Instance = new ReferenceEqualityComparer();

        public new bool Equals(object x, object y)
        {
            return ReferenceEquals(x, y);
        }

        public int GetHashCode(object obj)
        {
            return System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(obj);
        }
    }
}
