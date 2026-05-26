using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
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
        private TextBox _objectIdsTextBox;
        private TextBox _objectSearchResultTextBox;

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

            var lblObjectIds = new Label
            {
                Left = 20,
                Top = 235,
                Width = 800,
                Height = 22,
                Text = "idObject для поиска (через пробел, перенос строки, запятую или точку с запятой):"
            };

            _objectIdsTextBox = new TextBox
            {
                Left = 20,
                Top = 260,
                Width = 620,
                Height = 80,
                Multiline = true,
                ScrollBars = ScrollBars.Vertical,
                WordWrap = true,
                Font = new Font("Consolas", 10),
                Text = "6826836 6826837 6826838"
            };

            var btnFindByIds = new Button
            {
                Text = "3. Найти и выделить по idObject",
                Left = 660,
                Top = 260,
                Width = 240,
                Height = 40
            };
            btnFindByIds.Click += (s, e) => FindAndSelectObjectsByIds();

            _objectSearchResultTextBox = new TextBox
            {
                Left = 20,
                Top = 360,
                Width = 880,
                Height = 210,
                Multiline = true,
                ScrollBars = ScrollBars.Both,
                WordWrap = false,
                Font = new Font("Consolas", 9),
                ReadOnly = true
            };

            panel.Controls.Add(btnInspect);
            panel.Controls.Add(btnSummary);
            panel.Controls.Add(note);
            panel.Controls.Add(lblObjectIds);
            panel.Controls.Add(_objectIdsTextBox);
            panel.Controls.Add(btnFindByIds);
            panel.Controls.Add(_objectSearchResultTextBox);
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

        private void FindAndSelectObjectsByIds()
        {
            var lines = new List<string>();

            try
            {
                if (_library == null)
                {
                    _objectSearchResultTextBox.Text = "CADLibrary недоступна.";
                    return;
                }

                var ids = ParseObjectIds(_objectIdsTextBox.Text);

                if (ids.Count == 0)
                {
                    _objectSearchResultTextBox.Text = "Введите один или несколько idObject, например: 6826836 6826837 6826838";
                    return;
                }

                var foundObjects = new List<CLibObjectInfo>();
                var foundIds = new List<int>();
                var notFound = new List<int>();

                lines.Add("=== ПОИСК ПО idObject ===");
                lines.Add("");
                lines.Add("Запрошено idObject: " + ids.Count);
                lines.Add("");
                lines.Add("idObject | Category | PART_TYPE | Name");
                lines.Add(new string('-', 140));

                foreach (int id in ids)
                {
                    CLibObjectInfo obj = FindObjectById(id);

                    if (obj == null)
                    {
                        notFound.Add(id);
                        lines.Add(id + " | <не найден>");
                        continue;
                    }

                    foundObjects.Add(obj);
                    foundIds.Add(obj.idObject);

                    lines.Add(
                        obj.idObject + " | " +
                        SafeToString(() => obj.idObjectCategory) + " | " +
                        ReadParam(obj, "PART_TYPE") + " | " +
                        SafeToString(() => obj.Name)
                    );
                }

                lines.Add("");
                lines.Add("Найдено: " + foundObjects.Count);
                lines.Add("Не найдено: " + notFound.Count);

                if (notFound.Count > 0)
                    lines.Add("Не найдены idObject: " + string.Join(" ", notFound));

                bool selectionChanged = SetLibrarySelectedObjects(foundIds);
                lines.Add("Массовое выделение найденных объектов: " + (selectionChanged ? "выполнено" : "без изменений или недоступно"));

                if (foundIds.Count > 0)
                {
                    HierarchySelectionResult hierarchySelection = SelectObjectInHierarchy(foundIds[0]);
                    lines.Add("Переход в иерархии к первому найденному объекту (" + foundIds[0] + "): " + (hierarchySelection.Success ? "выполнен" : "недоступен"));
                    lines.Add("Путь idObject для иерархии: " + hierarchySelection.PathText);

                    if (!string.IsNullOrEmpty(hierarchySelection.TargetType))
                        lines.Add("Контрол иерархии: " + hierarchySelection.TargetType);

                    if (!string.IsNullOrEmpty(hierarchySelection.Message))
                        lines.Add("Детали перехода: " + hierarchySelection.Message);

                    TryInvokeNoArg(_browser, "RefreshActiveObject", true);
                    TryInvokeNoArg(_browser, "UpdateWindow");
                    TryInvokeNoArg(_browser, "UpdateButtons");
                }
            }
            catch (Exception ex)
            {
                lines.Add("ОШИБКА:");
                lines.Add(ex.ToString());
            }

            _objectSearchResultTextBox.Text = string.Join("\r\n", lines);
        }

        private static List<int> ParseObjectIds(string text)
        {
            var ids = new List<int>();
            var seen = new HashSet<int>();

            if (string.IsNullOrWhiteSpace(text))
                return ids;

            string[] tokens = text.Split(new[] { ' ', '\t', '\r', '\n', ',', ';' }, StringSplitOptions.RemoveEmptyEntries);

            foreach (string token in tokens)
            {
                int id;

                if (!int.TryParse(token.Trim(), out id))
                    continue;

                if (seen.Add(id))
                    ids.Add(id);
            }

            return ids;
        }

        private CLibObjectInfo FindObjectById(int idObject)
        {
            try
            {
                return _library.GetLibraryCustomObject(idObject);
            }
            catch
            {
                return null;
            }
        }

        private bool SetLibrarySelectedObjects(IList<int> ids)
        {
            if (ids == null || ids.Count == 0)
                return false;

            object result = InvokeMethod(_library, "SetSelectedObjects", ids);

            if (result is bool)
                return (bool)result;

            result = InvokeMethod(_library, "SetSelectedObjects", ToArray(ids));

            if (result is bool)
                return (bool)result;

            if (ids.Count == 1)
            {
                result = InvokeMethod(_library, "SetSingleSelection", ids[0]);

                if (result is bool)
                    return (bool)result;
            }

            return result != null;
        }

        private static int[] ToArray(IList<int> ids)
        {
            var result = new int[ids.Count];

            for (int i = 0; i < ids.Count; i++)
                result[i] = ids[i];

            return result;
        }

        private HierarchySelectionResult SelectObjectInHierarchy(int idObject)
        {
            var selectionResult = new HierarchySelectionResult();

            if (_browser == null)
            {
                selectionResult.Message = "DBBrowser недоступен.";
                return selectionResult;
            }

            int[] path = BuildObjectPath(idObject);
            selectionResult.PathText = path.Length == 0 ? "<пустой>" : string.Join(" -> ", path);
            selectionResult.Message = "RootObject=" + SafeInvokeInt(_library, "GetRootObject", idObject) +
                                      "; ParentObject=" + SafeInvokeInt(_library, "GetParentObject", idObject);

            var candidates = GetHierarchySelectionTargets();

            foreach (object candidate in candidates)
            {
                if (!HasMethod(candidate, "SelectChildObjectByPath"))
                    continue;

                object result = InvokeMethod(candidate, "SelectChildObjectByPath", path);

                if (result != null)
                {
                    TrySelectReturnedNode(candidate, result);

                    selectionResult.Success = true;
                    selectionResult.TargetType = candidate.GetType().FullName;
                    selectionResult.Message = AppendDetail(selectionResult.Message, "SelectChildObjectByPath(path) вернул " + result.GetType().FullName + ".");
                    return selectionResult;
                }

                result = InvokeMethod(candidate, "SelectChildObjectByPath", new[] { idObject });

                if (result != null)
                {
                    TrySelectReturnedNode(candidate, result);

                    selectionResult.Success = true;
                    selectionResult.TargetType = candidate.GetType().FullName;
                    selectionResult.Message = AppendDetail(selectionResult.Message, "SelectChildObjectByPath(idObject) вернул " + result.GetType().FullName + ".");
                    return selectionResult;
                }

                if (string.IsNullOrEmpty(selectionResult.TargetType))
                    selectionResult.TargetType = candidate.GetType().FullName;
            }

            selectionResult.Message = AppendDetail(selectionResult.Message, "Метод SelectChildObjectByPath найден не был или вернул null.");

            return selectionResult;
        }

        private List<object> GetHierarchySelectionTargets()
        {
            var targets = new List<object>();

            AddUniqueTarget(targets, _browser);
            AddNestedSelectionTargets(targets, _browser);

            var browserControl = _browser as Control;

            if (browserControl != null)
                AddControlTargets(targets, browserControl);

            return targets;
        }

        private static void AddNestedSelectionTargets(List<object> targets, object source)
        {
            if (source == null)
                return;

            Type type = source.GetType();
            BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

            foreach (PropertyInfo property in type.GetProperties(flags))
            {
                if (property.GetIndexParameters().Length > 0)
                    continue;

                TryAddMemberTarget(targets, source, property);
            }

            foreach (FieldInfo field in type.GetFields(flags))
                TryAddMemberTarget(targets, source, field);
        }

        private static void TryAddMemberTarget(List<object> targets, object source, MemberInfo member)
        {
            try
            {
                object value = null;

                var property = member as PropertyInfo;

                if (property != null)
                    value = property.GetValue(source, null);

                var field = member as FieldInfo;

                if (field != null)
                    value = field.GetValue(source);

                if (value == null || value is string)
                    return;

                Type valueType = value.GetType();

                if (valueType.IsValueType)
                    return;

                if (HasMethod(value, "SelectChildObjectByPath") || value is Control)
                    AddUniqueTarget(targets, value);

                var control = value as Control;

                if (control != null)
                    AddControlTargets(targets, control);
            }
            catch
            {
            }
        }

        private static void AddControlTargets(List<object> targets, Control root)
        {
            if (root == null)
                return;

            AddUniqueTarget(targets, root);

            foreach (Control child in root.Controls)
                AddControlTargets(targets, child);
        }

        private static void AddUniqueTarget(List<object> targets, object target)
        {
            if (target == null)
                return;

            foreach (object existing in targets)
            {
                if (ReferenceEquals(existing, target))
                    return;
            }

            targets.Add(target);
        }

        private static void TrySelectReturnedNode(object target, object result)
        {
            var node = result as TreeNode;

            if (node != null)
            {
                InvokeMethod(target, "SetSelectedNode", node);
                node.EnsureVisible();
            }
        }

        private int[] BuildObjectPath(int idObject)
        {
            var path = new List<int>();
            var seen = new HashSet<int>();
            int current = idObject;

            while (current > 0 && seen.Add(current))
            {
                path.Insert(0, current);

                object parent = InvokeMethod(_library, "GetParentObject", current);

                if (parent == null)
                {
                    CLibObjectInfo currentObject = FindObjectById(current);
                    parent = ReadIntMember(currentObject, "idParentObject");

                    if (parent == null)
                        parent = ReadIntMember(currentObject, "idParent");

                    if (parent == null)
                        parent = ReadIntMember(currentObject, "ParentObjectId");

                    if (parent == null)
                        break;
                }

                int parentId;

                try
                {
                    parentId = Convert.ToInt32(parent);
                }
                catch
                {
                    break;
                }

                if (parentId <= 0 || parentId == current)
                    break;

                current = parentId;
            }

            return path.ToArray();
        }

        private static object ReadIntMember(object target, string memberName)
        {
            if (target == null)
                return null;

            BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
            Type type = target.GetType();

            FieldInfo field = type.GetField(memberName, flags);

            if (field != null)
                return field.GetValue(target);

            PropertyInfo property = type.GetProperty(memberName, flags);

            if (property != null && property.GetIndexParameters().Length == 0)
                return property.GetValue(target, null);

            return null;
        }

        private static string SafeInvokeInt(object target, string methodName, int value)
        {
            object result = InvokeMethod(target, methodName, value);

            if (result == null)
                return "<null>";

            return Convert.ToString(result);
        }

        private static string AppendDetail(string current, string detail)
        {
            if (string.IsNullOrEmpty(current))
                return detail;

            if (string.IsNullOrEmpty(detail))
                return current;

            return current + " " + detail;
        }

        private sealed class HierarchySelectionResult
        {
            public bool Success { get; set; }
            public string PathText { get; set; }
            public string TargetType { get; set; }
            public string Message { get; set; }
        }

        private static bool HasMethod(object target, string methodName)
        {
            if (target == null)
                return false;

            MethodInfo[] methods = target.GetType().GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);

            foreach (MethodInfo method in methods)
            {
                if (method.Name == methodName)
                    return true;
            }

            return false;
        }

        private static object InvokeMethod(object target, string methodName, params object[] args)
        {
            if (target == null)
                return null;

            Type type = target.GetType();
            MethodInfo[] methods = type.GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);

            foreach (MethodInfo method in methods)
            {
                if (method.Name != methodName)
                    continue;

                ParameterInfo[] parameters = method.GetParameters();

                if (parameters.Length != args.Length)
                    continue;

                try
                {
                    return method.Invoke(target, args);
                }
                catch
                {
                }
            }

            return null;
        }

        private static void TryInvokeNoArg(object target, string methodName, params object[] args)
        {
            InvokeMethod(target, methodName, args);
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
