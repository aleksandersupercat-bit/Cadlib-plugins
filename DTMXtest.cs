using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;
using CADLib;
using CADLibKernel;
using IronPython.Hosting;
using Microsoft.Scripting.Hosting;

namespace DTMXtest
{
    /// <summary>
    /// Entry point CADLib calls when the DLL is loaded from plugins_cadlib.xml.
    /// Pattern is the same as CADLibPluginSample.dll.
    /// </summary>
    public static class CADLibPluginEntryPoint
    {
        public static ICADLibPlugin RegisterPlugin(PluginsManager manager)
        {
            // For stable production use this message can be removed after first successful test.
            // MessageBox.Show("DTMXtest PLUGIN LOADED");

            return new DTMXtestPlugin(
                manager.Library,
                manager.MainDBBrowser
            );
        }
    }

    /// <summary>
    /// CADLib plugin that adds menu item: Инструменты -> DTMXtest.
    /// </summary>
    public sealed class DTMXtestPlugin : ICADLibPlugin
    {
        private readonly CADLibrary _library;
        private readonly IDatabaseBrowser _browser;

        public DTMXtestPlugin(CADLibrary library, IDatabaseBrowser browser)
        {
            _library = library;
            _browser = browser;
        }

        public MenuStrip GetMenu()
        {
            var menu = new MenuStrip();

            // Important: use the same root text as the existing CADLib menu.
            // PluginsManager.MergeInterfaceMenus should merge equal top-level items.
            var toolsRoot = new ToolStripMenuItem("Инструменты");
            var runItem = new ToolStripMenuItem("DTMXtest");

            runItem.Click += (sender, args) => ShowMainForm();

            toolsRoot.DropDownItems.Add(runItem);
            menu.Items.Add(toolsRoot);

            return menu;
        }

        public ToolStripContainer GetToolbars()
        {
            // No toolbar. Only menu item is added.
            return null;
        }

        public void TrackInterfaceItems(InterfaceTracker tracker)
        {
            // Later this can be used to enable/disable menu items depending on DB state and selection.
        }

        private void ShowMainForm()
        {
            try
            {
                using (var form = new DTMXtestForm(_library, _browser))
                {
                    form.ShowDialog();
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    ex.ToString(),
                    "DTMXtest: ошибка запуска",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }
    }

    public sealed class DTMXtestForm : Form
    {
        private readonly CADLibrary _library;
        private readonly IDatabaseBrowser _browser;

        private TextBox _pythonCodeTextBox;
        private TextBox _pythonOutputTextBox;

        public DTMXtestForm(CADLibrary library, IDatabaseBrowser browser)
        {
            _library = library;
            _browser = browser;

            Text = "DTMXtest";
            Width = 950;
            Height = 700;
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.Sizable;
            MaximizeBox = true;
            MinimizeBox = true;

            BuildUi();
        }

        private void BuildUi()
        {
            var tabs = new TabControl
            {
                Dock = DockStyle.Fill
            };

            var tabSelection = new TabPage("Выделение CADLib");
            var tabPython = new TabPage("Python");

            BuildSelectionTab(tabSelection);
            BuildPythonTab(tabPython);

            tabs.TabPages.Add(tabSelection);
            tabs.TabPages.Add(tabPython);

            Controls.Add(tabs);
        }

        private void BuildSelectionTab(TabPage tab)
        {
            var panel = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(20)
            };

            var btnInspect = new Button
            {
                Text = "1. Инспектор выделения",
                Left = 20,
                Top = 20,
                Width = 420,
                Height = 40
            };
            btnInspect.Click += (s, e) => InspectSelection();

            var btnSummary = new Button
            {
                Text = "2. Сводка PART_TYPE",
                Left = 20,
                Top = 80,
                Width = 420,
                Height = 40
            };
            btnSummary.Click += (s, e) => ShowPartTypeSummary();

            var note = new Label
            {
                Left = 20,
                Top = 145,
                Width = 800,
                Height = 80,
                Text = "Используется подтверждённый вызов DBBrowser.GetSelectedObjects(false). " +
                       "Выделять объекты нужно в дереве CADLib.",
                AutoSize = false
            };

            panel.Controls.Add(btnInspect);
            panel.Controls.Add(btnSummary);
            panel.Controls.Add(note);
            tab.Controls.Add(panel);
        }

        private void BuildPythonTab(TabPage tab)
        {
            var root = new SplitContainer
            {
                Dock = DockStyle.Fill,
                Orientation = Orientation.Horizontal,
                SplitterDistance = 430
            };

            var topPanel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(8) };
            var bottomPanel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(8) };

            var toolbar = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 42,
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = false
            };

            var btnRun = new Button
            {
                Text = "Выполнить",
                Width = 120,
                Height = 30
            };
            btnRun.Click += (s, e) => ExecutePythonFromEditor();

            var btnLoadSample = new Button
            {
                Text = "Вставить пример",
                Width = 140,
                Height = 30
            };
            btnLoadSample.Click += (s, e) => _pythonCodeTextBox.Text = GetDefaultPythonScript();

            var btnClearOutput = new Button
            {
                Text = "Очистить вывод",
                Width = 140,
                Height = 30
            };
            btnClearOutput.Click += (s, e) => _pythonOutputTextBox.Clear();

            toolbar.Controls.Add(btnRun);
            toolbar.Controls.Add(btnLoadSample);
            toolbar.Controls.Add(btnClearOutput);

            _pythonCodeTextBox = new TextBox
            {
                Multiline = true,
                ScrollBars = ScrollBars.Both,
                WordWrap = false,
                AcceptsTab = true,
                Font = new Font("Consolas", 10),
                Dock = DockStyle.Fill,
                Text = GetDefaultPythonScript()
            };

            var lblCode = new Label
            {
                Text = "Python-код. В scope уже переданы: Library, DBBrowser, CLMainForm.",
                Dock = DockStyle.Top,
                Height = 24
            };

            topPanel.Controls.Add(_pythonCodeTextBox);
            topPanel.Controls.Add(lblCode);
            topPanel.Controls.Add(toolbar);

            _pythonOutputTextBox = new TextBox
            {
                Multiline = true,
                ScrollBars = ScrollBars.Both,
                WordWrap = false,
                Font = new Font("Consolas", 9),
                Dock = DockStyle.Fill,
                ReadOnly = true
            };

            var lblOutput = new Label
            {
                Text = "Вывод / ошибки",
                Dock = DockStyle.Top,
                Height = 24
            };

            bottomPanel.Controls.Add(_pythonOutputTextBox);
            bottomPanel.Controls.Add(lblOutput);

            root.Panel1.Controls.Add(topPanel);
            root.Panel2.Controls.Add(bottomPanel);

            tab.Controls.Add(root);
        }

        private IList<CLibObjectInfo> GetSelectedObjects()
        {
            if (_browser == null)
                return new List<CLibObjectInfo>();

            // Confirmed correct CADLib API pattern:
            // GetSelectedObjects(false) returns List<CLibObjectInfo>.
            // Do not pass a List<T> into this method as an out-like argument.
            var selected = _browser.GetSelectedObjects(false);

            if (selected == null)
                return new List<CLibObjectInfo>();

            return selected;
        }

        private string ReadParam(CLibObjectInfo obj, string paramName)
        {
            try
            {
                if (_library == null || obj == null)
                    return "<None>";

                object value = _library.GetObjectParameterValue(
                    obj.idObject,
                    paramName,
                    null,
                    false
                );

                return value == null ? "<None>" : Convert.ToString(value);
            }
            catch (Exception ex)
            {
                return "ERROR: " + ex.Message;
            }
        }

        private void InspectSelection()
        {
            var lines = new List<string>();

            try
            {
                var selected = GetSelectedObjects();

                lines.Add("=== ВЫДЕЛЕНИЕ CADLib ===");
                lines.Add("");
                lines.Add("Количество объектов: " + selected.Count);
                lines.Add("");
                lines.Add("№ | idObject | Category | PART_TYPE | Name");
                lines.Add(new string('-', 140));

                for (int i = 0; i < selected.Count; i++)
                {
                    CLibObjectInfo obj = selected[i];

                    string idObject = SafeToString(() => obj.idObject);
                    string category = SafeToString(() => obj.idObjectCategory);
                    string name = SafeToString(() => obj.Name);
                    string partType = ReadParam(obj, "PART_TYPE");

                    lines.Add(
                        (i + 1) + " | " +
                        idObject + " | " +
                        category + " | " +
                        partType + " | " +
                        name
                    );
                }
            }
            catch (Exception ex)
            {
                lines.Add("ОШИБКА:");
                lines.Add(ex.ToString());
            }

            ShowTextWindow("CADLib Selection Inspector", lines, 1200, 800);
        }

        private void ShowPartTypeSummary()
        {
            var lines = new List<string>();

            try
            {
                var selected = GetSelectedObjects();
                var counts = new SortedDictionary<string, int>(StringComparer.CurrentCultureIgnoreCase);

                foreach (CLibObjectInfo obj in selected)
                {
                    string partType = ReadParam(obj, "PART_TYPE");

                    if (!counts.ContainsKey(partType))
                        counts[partType] = 0;

                    counts[partType]++;
                }

                lines.Add("=== СВОДКА PART_TYPE ===");
                lines.Add("");
                lines.Add("Всего объектов: " + selected.Count);
                lines.Add("");

                foreach (var pair in counts)
                    lines.Add(pair.Key + ": " + pair.Value);
            }
            catch (Exception ex)
            {
                lines.Add("ОШИБКА:");
                lines.Add(ex.ToString());
            }

            ShowTextWindow("CADLib PART_TYPE Summary", lines, 700, 500);
        }

        private void ExecutePythonFromEditor()
        {
            try
            {
                _pythonOutputTextBox.Clear();

                var engine = Python.CreateEngine();
                var scope = engine.CreateScope();

                // Give Python access to CADLib context.
                scope.SetVariable("Library", _library);
                scope.SetVariable("DBBrowser", _browser);
                scope.SetVariable("CLMainForm", this);

                // Make CADLib assemblies available for import/clr usage.
                engine.Runtime.LoadAssembly(typeof(CADLibrary).Assembly);
                engine.Runtime.LoadAssembly(typeof(CLibObjectInfo).Assembly);
                engine.Runtime.LoadAssembly(typeof(Form).Assembly);
                engine.Runtime.LoadAssembly(typeof(Color).Assembly);

                var output = new MemoryStream();
                var error = new MemoryStream();

                engine.Runtime.IO.SetOutput(output, Encoding.UTF8);
                engine.Runtime.IO.SetErrorOutput(error, Encoding.UTF8);

                var source = engine.CreateScriptSourceFromString(_pythonCodeTextBox.Text);
                source.Execute(scope);

                string stdout = Encoding.UTF8.GetString(output.ToArray());
                string stderr = Encoding.UTF8.GetString(error.ToArray());

                var sb = new StringBuilder();

                if (!string.IsNullOrEmpty(stdout))
                {
                    sb.AppendLine("=== STDOUT ===");
                    sb.AppendLine(stdout);
                }

                if (!string.IsNullOrEmpty(stderr))
                {
                    sb.AppendLine("=== STDERR ===");
                    sb.AppendLine(stderr);
                }

                if (sb.Length == 0)
                    sb.AppendLine("Скрипт выполнен без текстового вывода.");

                _pythonOutputTextBox.Text = sb.ToString();
            }
            catch (Exception ex)
            {
                _pythonOutputTextBox.Text = "ОШИБКА ВЫПОЛНЕНИЯ PYTHON:\r\n" + ex;
            }
        }

        private static string SafeToString<T>(Func<T> getter)
        {
            try
            {
                object value = getter();
                return value == null ? "<None>" : Convert.ToString(value);
            }
            catch
            {
                return "<None>";
            }
        }

        private static void ShowTextWindow(string title, IList<string> lines, int width, int height)
        {
            using (var form = new Form())
            {
                form.Text = title;
                form.Width = width;
                form.Height = height;
                form.StartPosition = FormStartPosition.CenterScreen;

                var tb = new TextBox
                {
                    Multiline = true,
                    ScrollBars = ScrollBars.Both,
                    WordWrap = false,
                    Font = new Font("Consolas", 9),
                    Dock = DockStyle.Fill,
                    Text = string.Join("\r\n", lines)
                };

                form.Controls.Add(tb);
                form.ShowDialog();
            }
        }

        private static string GetDefaultPythonScript()
        {
            return
@"# -*- coding: utf-8 -*-
# В scope уже есть: Library, DBBrowser, CLMainForm

selected = DBBrowser.GetSelectedObjects(False)
print('Количество выделенных объектов:', selected.Count)

for i, obj in enumerate(selected):
    val = Library.GetObjectParameterValue(obj.idObject, 'PART_TYPE', None, False)
    print(str(i + 1) + ' | ' + str(obj.idObject) + ' | ' + str(val) + ' | ' + str(obj.Name))
";
        }
    }
}
