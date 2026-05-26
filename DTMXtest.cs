using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
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
        private readonly string _logFilePath;
        private string _loadedPythonScriptPath;
        private string _pythonAutoLogFilePath;
        private string _pythonAutoStatusFilePath;
        private Timer _pythonAutoRetryTimer;
        private bool _pythonAutoRunActive;
        private bool _pythonAutoRunInProgress;
        private DateTime _pythonAutoScriptWriteTimeUtc;

        private TextBox _pythonCodeTextBox;
        private TextBox _pythonOutputTextBox;
        private Label _pythonAutoStatusLabel;
        private TextBox _objectIdsTextBox;
        private TextBox _objectSearchResultTextBox;
        private ComboBox _partTypeComboBox;
        private ComboBox _childComboBox;
        private ComboBox _parameterComboBox;
        private TextBox _searchValueTextBox;
        private TextBox _dataSearchResultTextBox;
        private TextBox _dataSearchLogTextBox;
        private bool _isLoadingDataSearch;
        private List<string> _partTypeCache;
        private readonly Dictionary<string, List<CLibObjectInfo>> _rootObjectsByPartTypeCache = new Dictionary<string, List<CLibObjectInfo>>(StringComparer.CurrentCultureIgnoreCase);
        private readonly Dictionary<string, List<string>> _childNamesByPartTypeCache = new Dictionary<string, List<string>>(StringComparer.CurrentCultureIgnoreCase);
        private readonly Dictionary<string, List<CLibObjectInfo>> _candidateObjectsCache = new Dictionary<string, List<CLibObjectInfo>>(StringComparer.CurrentCultureIgnoreCase);
        private readonly Dictionary<string, List<string>> _parameterNamesCache = new Dictionary<string, List<string>>(StringComparer.CurrentCultureIgnoreCase);

        public DTMXtestForm(CADLibrary library, IDatabaseBrowser browser)
        {
            _library = library;
            _browser = browser;
            _logFilePath = CreateLogFilePath();

            Text = "DTMXtest";
            Width = 1200;
            Height = 700;
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.Sizable;
            MaximizeBox = true;
            MinimizeBox = true;

            BuildUi();
            Load += (s, e) =>
            {
                LogDataSearch("Форма DTMXtest запущена. Лог: " + _logFilePath);
                LoadPartTypes();
            };
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            if (_pythonAutoRetryTimer != null)
            {
                _pythonAutoRetryTimer.Stop();
                _pythonAutoRetryTimer.Dispose();
                _pythonAutoRetryTimer = null;
            }

            base.OnFormClosed(e);
        }

        private void BuildUi()
        {
            var tabs = new TabControl
            {
                Dock = DockStyle.Fill
            };

            var tabSelection = new TabPage("Выделение CADLib");
            var tabDataSearch = new TabPage("Поиск данных");
            var tabPython = new TabPage("Python");

            BuildSelectionTab(tabSelection);
            BuildDataSearchTab(tabDataSearch);
            BuildPythonTab(tabPython);

            tabs.TabPages.Add(tabSelection);
            tabs.TabPages.Add(tabDataSearch);
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

        private void BuildDataSearchTab(TabPage tab)
        {
            var panel = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(16)
            };

            int labelTop = 22;
            int inputTop = 18;

            var lblPartType = CreateSearchLabel("Тип изделия", 20, labelTop, 65);
            _partTypeComboBox = CreateSearchComboBox(90, inputTop, 220);
            _partTypeComboBox.Name = "Тип изделия";
            _partTypeComboBox.Enter += (s, e) => LoadPartTypes();
            _partTypeComboBox.SelectedIndexChanged += (s, e) => LoadChildNames();

            var lblChild = CreateSearchLabel("Дочерний", 330, labelTop, 60);
            _childComboBox = CreateSearchComboBox(395, inputTop, 165);
            _childComboBox.Name = "Дочерний";
            _childComboBox.Enter += (s, e) => LoadChildNames();
            _childComboBox.SelectedIndexChanged += (s, e) => LoadParameterNames();

            var lblParam = CreateSearchLabel("Параметр", 580, labelTop, 60);
            _parameterComboBox = CreateSearchComboBox(645, inputTop, 280);
            _parameterComboBox.Name = "Параметр";
            _parameterComboBox.Enter += (s, e) => LoadParameterNames();

            var lblValue = CreateSearchLabel("Значение", 945, labelTop, 60);
            _searchValueTextBox = new TextBox
            {
                Left = 1010,
                Top = inputTop,
                Width = 115,
                Height = 24
            };

            var btnSearch = new Button
            {
                Text = "ПОИСК",
                Left = 20,
                Top = 62,
                Width = 140,
                Height = 36
            };
            btnSearch.Click += (s, e) => ExecuteDataSearch();

            _dataSearchResultTextBox = new TextBox
            {
                Left = 20,
                Top = 115,
                Width = 1085,
                Height = 340,
                Multiline = true,
                ScrollBars = ScrollBars.Both,
                WordWrap = false,
                Font = new Font("Consolas", 9),
                ReadOnly = true
            };

            _dataSearchLogTextBox = new TextBox
            {
                Left = 20,
                Top = 465,
                Width = 1085,
                Height = 150,
                Multiline = true,
                ScrollBars = ScrollBars.Both,
                WordWrap = false,
                Font = new Font("Consolas", 9),
                ReadOnly = true
            };

            panel.Controls.Add(lblPartType);
            panel.Controls.Add(_partTypeComboBox);
            panel.Controls.Add(lblChild);
            panel.Controls.Add(_childComboBox);
            panel.Controls.Add(lblParam);
            panel.Controls.Add(_parameterComboBox);
            panel.Controls.Add(lblValue);
            panel.Controls.Add(_searchValueTextBox);
            panel.Controls.Add(btnSearch);
            panel.Controls.Add(_dataSearchResultTextBox);
            panel.Controls.Add(_dataSearchLogTextBox);

            tab.Enter += (s, e) => LoadPartTypes();
            tab.VisibleChanged += (s, e) => LoadPartTypes();
            tab.Controls.Add(panel);
        }

        private static Label CreateSearchLabel(string text, int left, int top, int width)
        {
            return new Label
            {
                Text = text,
                Left = left,
                Top = top,
                Width = width,
                Height = 24
            };
        }

        private static ComboBox CreateSearchComboBox(int left, int top, int width)
        {
            return new ComboBox
            {
                Left = left,
                Top = top,
                Width = width,
                Height = 24,
                DropDownStyle = ComboBoxStyle.DropDownList,
                DropDownHeight = 360,
                IntegralHeight = false,
                MaxDropDownItems = 30,
                AutoCompleteMode = AutoCompleteMode.None,
                AutoCompleteSource = AutoCompleteSource.None
            };
        }

        private static string CreateLogFilePath()
        {
            string logDir = Path.Combine(GetProjectRoot(), "LOG");
            Directory.CreateDirectory(logDir);

            return Path.Combine(logDir, "DTMXtest_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".txt");
        }

        private static string CreatePythonAutoLogFilePath()
        {
            string logDir = Path.Combine(GetProjectRoot(), "LOG");
            Directory.CreateDirectory(logDir);

            return Path.Combine(logDir, "log_python_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".txt");
        }

        private static string GetProjectRoot()
        {
            string projectRoot = @"C:\pdf_ingest\DTMXtest";

            if (Directory.Exists(projectRoot))
                return projectRoot;

            return AppDomain.CurrentDomain.BaseDirectory;
        }

        private static string GetDefaultPythonDiagnosticsPath()
        {
            return Path.Combine(GetProjectRoot(), "Python", "diagnostics.py");
        }

        private static string GetPythonScriptsDir()
        {
            string dir = Path.Combine(GetProjectRoot(), "Python");
            Directory.CreateDirectory(dir);
            return dir;
        }

        private static string GetPythonAutoStatusFilePath()
        {
            return Path.Combine(GetPythonScriptsDir(), "autotest_status.json");
        }

        public string LogFilePath
        {
            get { return _logFilePath; }
        }

        public string PythonLogFilePath
        {
            get { return string.IsNullOrEmpty(_pythonAutoLogFilePath) ? _logFilePath : _pythonAutoLogFilePath; }
        }

        public string PythonAutoStatusFilePath
        {
            get { return string.IsNullOrEmpty(_pythonAutoStatusFilePath) ? GetPythonAutoStatusFilePath() : _pythonAutoStatusFilePath; }
        }

        public void WriteLog(string message)
        {
            LogDataSearch(message);
        }

        public void WritePythonLog(string message)
        {
            AppendPythonAutoLog(message);
        }

        public string[] GetPartTypesForPython()
        {
            return GetParameterValuesForPython("PART_TYPE");
        }

        public string[] GetParameterValuesForPython(string paramName)
        {
            if (_library == null || string.IsNullOrWhiteSpace(paramName))
                return new string[0];

            int paramDefId = _library.GetParamDefId(paramName);

            if (paramDefId <= 0)
                return new string[0];

            return GetParameterValueList(paramDefId).ToArray();
        }

        public CLibObjectInfo[] GetObjectsByPartTypeForPython(string partType)
        {
            if (_library == null || string.IsNullOrWhiteSpace(partType))
                return new CLibObjectInfo[0];

            int paramDefId = _library.GetParamDefId("PART_TYPE");

            if (paramDefId <= 0)
                return new CLibObjectInfo[0];

            var objects = _library.GetObjectParametersByValues(paramDefId, partType.Trim(), true, ';');
            var result = new List<CLibObjectInfo>();

            foreach (object item in SafeEnumerate(objects))
            {
                var obj = item as CLibObjectInfo;

                if (obj != null)
                    result.Add(obj);
            }

            return result.ToArray();
        }

        public Parameter[] GetObjectParametersForPython(int objectId)
        {
            if (_library == null || objectId <= 0)
                return new Parameter[0];

            var result = new List<Parameter>();

            foreach (Parameter parameter in _library.GetObjectParameters(objectId))
                result.Add(parameter);

            return result.ToArray();
        }

        public void RunPythonFile(string path)
        {
            LoadPythonScriptFromFile(path);
            ExecutePythonFromEditor();
        }

        private void LogDataSearch(string message)
        {
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " | " + message;

            try
            {
                File.AppendAllText(_logFilePath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch
            {
            }

            if (_dataSearchLogTextBox == null)
                return;

            try
            {
                if (_dataSearchLogTextBox.InvokeRequired)
                    _dataSearchLogTextBox.BeginInvoke(new Action(() => _dataSearchLogTextBox.AppendText(line + Environment.NewLine)));
                else
                    _dataSearchLogTextBox.AppendText(line + Environment.NewLine);
            }
            catch
            {
            }
        }

        private void AppendPythonAutoLog(string message)
        {
            string logPath = PythonLogFilePath;
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " | " + message;

            try
            {
                File.AppendAllText(logPath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch
            {
            }
        }

        private void WritePythonAutoStatus(string state, string note)
        {
            string path = PythonAutoStatusFilePath;

            try
            {
                string json =
                    "{" + Environment.NewLine +
                    "  \"state\": \"" + EscapeJson(state) + "\"," + Environment.NewLine +
                    "  \"script\": \"" + EscapeJson(_loadedPythonScriptPath ?? string.Empty) + "\"," + Environment.NewLine +
                    "  \"log\": \"" + EscapeJson(PythonLogFilePath) + "\"," + Environment.NewLine +
                    "  \"updated_at\": \"" + EscapeJson(DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss.fffzzz")) + "\"," + Environment.NewLine +
                    "  \"script_write_time_utc\": \"" + EscapeJson(_pythonAutoScriptWriteTimeUtc.ToString("O")) + "\"," + Environment.NewLine +
                    "  \"note\": \"" + EscapeJson(note ?? string.Empty) + "\"" + Environment.NewLine +
                    "}";

                File.WriteAllText(path, json, Encoding.UTF8);
            }
            catch (Exception ex)
            {
                AppendPythonAutoLog("Could not write protocol status file:\r\n" + ex);
            }
        }

        private string ReadPythonAutoStatusState()
        {
            try
            {
                string path = PythonAutoStatusFilePath;

                if (!File.Exists(path))
                    return "<missing>";

                string text = File.ReadAllText(path, Encoding.UTF8);
                return ExtractJsonString(text, "state") ?? "<unknown>";
            }
            catch (Exception ex)
            {
                AppendPythonAutoLog("Could not read protocol status file:\r\n" + ex);
                return "<read_error>";
            }
        }

        private static string ExtractJsonString(string text, string propertyName)
        {
            if (string.IsNullOrEmpty(text) || string.IsNullOrEmpty(propertyName))
                return null;

            string marker = "\"" + propertyName + "\"";
            int propertyIndex = text.IndexOf(marker, StringComparison.OrdinalIgnoreCase);

            if (propertyIndex < 0)
                return null;

            int colonIndex = text.IndexOf(':', propertyIndex + marker.Length);

            if (colonIndex < 0)
                return null;

            int quoteIndex = text.IndexOf('"', colonIndex + 1);

            if (quoteIndex < 0)
                return null;

            var sb = new StringBuilder();

            for (int i = quoteIndex + 1; i < text.Length; i++)
            {
                char ch = text[i];

                if (ch == '\\' && i + 1 < text.Length)
                {
                    i++;
                    char escaped = text[i];

                    if (escaped == '"' || escaped == '\\' || escaped == '/')
                        sb.Append(escaped);
                    else if (escaped == 'n')
                        sb.Append('\n');
                    else if (escaped == 'r')
                        sb.Append('\r');
                    else if (escaped == 't')
                        sb.Append('\t');
                    else
                        sb.Append(escaped);

                    continue;
                }

                if (ch == '"')
                    return sb.ToString();

                sb.Append(ch);
            }

            return null;
        }

        private static string EscapeJson(string value)
        {
            if (value == null)
                return string.Empty;

            return value
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n")
                .Replace("\t", "\\t");
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

            var btnLoadDiagnostics = new Button
            {
                Text = "Загрузить диагностику",
                Width = 170,
                Height = 30
            };
            btnLoadDiagnostics.Click += (s, e) => LoadPythonScriptFromFile(GetDefaultPythonDiagnosticsPath());

            var btnRunLatest = new Button
            {
                Text = "Запустить последний",
                Width = 170,
                Height = 30
            };
            btnRunLatest.Click += (s, e) => RunLatestPythonScript();

            var btnAutoRun = new Button
            {
                Text = "Автотест 1 мин",
                Width = 150,
                Height = 30
            };
            btnAutoRun.Click += async (s, e) => await StartPythonAutoRunAsync();

            var btnClearOutput = new Button
            {
                Text = "Очистить вывод",
                Width = 140,
                Height = 30
            };
            btnClearOutput.Click += (s, e) => _pythonOutputTextBox.Clear();

            toolbar.Controls.Add(btnRun);
            toolbar.Controls.Add(btnLoadSample);
            toolbar.Controls.Add(btnLoadDiagnostics);
            toolbar.Controls.Add(btnRunLatest);
            toolbar.Controls.Add(btnAutoRun);
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

            _pythonAutoStatusLabel = new Label
            {
                Text = "Автотест: ожидание",
                Dock = DockStyle.Top,
                Height = 20
            };

            topPanel.Controls.Add(_pythonCodeTextBox);
            topPanel.Controls.Add(lblCode);
            topPanel.Controls.Add(_pythonAutoStatusLabel);
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

            _pythonAutoRetryTimer = new Timer { Interval = 10000 };
            _pythonAutoRetryTimer.Tick += async (s, e) => await OnPythonAutoRetryTimerAsync();
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

        private void LoadPartTypes()
        {
            if (_isLoadingDataSearch || _library == null || _partTypeComboBox == null)
                return;

            if (_partTypeCache != null && _partTypeComboBox.Items.Count > 0)
                return;

            try
            {
                _isLoadingDataSearch = true;
                string current = GetComboText(_partTypeComboBox);

                if (_partTypeCache == null)
                {
                    LogDataSearch("Индексация PART_TYPE: старт.");
                    int partTypeParamId = _library.GetParamDefId("PART_TYPE");
                    _partTypeCache = GetParameterValueList(partTypeParamId);
                    LogDataSearch("Индексация PART_TYPE: найдено значений " + _partTypeCache.Count + ".");
                }

                FillComboBox(_partTypeComboBox, _partTypeCache, current, false);
                LogDataSearch("Список PART_TYPE загружен в UI: " + _partTypeComboBox.Items.Count + ".");
            }
            catch (Exception ex)
            {
                _dataSearchResultTextBox.Text = "Ошибка загрузки PART_TYPE:\r\n" + ex;
                LogDataSearch("Ошибка загрузки PART_TYPE: " + ex);
            }
            finally
            {
                _isLoadingDataSearch = false;
            }
        }

        private void LoadChildNames()
        {
            if (_isLoadingDataSearch || _library == null || _childComboBox == null)
                return;

            bool reloadParameters = false;

            try
            {
                _isLoadingDataSearch = true;
                string current = GetComboText(_childComboBox);
                string partType = GetComboText(_partTypeComboBox);
                LogDataSearch("Загрузка дочерних элементов для PART_TYPE='" + partType + "'.");
                List<string> childNames = GetCachedChildNames(partType);

                FillComboBox(_childComboBox, childNames, current, true);
                LogDataSearch("Список дочерних элементов загружен в UI: " + _childComboBox.Items.Count + ".");
                reloadParameters = true;
            }
            catch (Exception ex)
            {
                _dataSearchResultTextBox.Text = "Ошибка загрузки дочерних элементов:\r\n" + ex;
                LogDataSearch("Ошибка загрузки дочерних элементов: " + ex);
            }
            finally
            {
                _isLoadingDataSearch = false;
            }

            if (reloadParameters)
                LoadParameterNames();
        }

        private void LoadParameterNames()
        {
            if (_isLoadingDataSearch || _library == null || _parameterComboBox == null)
                return;

            try
            {
                _isLoadingDataSearch = true;
                string current = GetComboText(_parameterComboBox);
                string partType = GetComboText(_partTypeComboBox);
                string childName = GetComboText(_childComboBox);
                LogDataSearch("Загрузка параметров для PART_TYPE='" + partType + "', Дочерний='" + childName + "'.");
                List<string> paramNames = GetCachedParameterNames(partType, childName);

                FillComboBox(_parameterComboBox, paramNames, current, false);
                LogDataSearch("Список параметров загружен в UI: " + _parameterComboBox.Items.Count + ".");
            }
            catch (Exception ex)
            {
                _dataSearchResultTextBox.Text = "Ошибка загрузки параметров:\r\n" + ex;
                LogDataSearch("Ошибка загрузки параметров: " + ex);
            }
            finally
            {
                _isLoadingDataSearch = false;
            }
        }

        private void ExecuteDataSearch()
        {
            var lines = new List<string>();

            try
            {
                string partType = GetComboText(_partTypeComboBox);
                string childName = GetComboText(_childComboBox);
                string parameterName = ExtractParameterName(GetComboText(_parameterComboBox));
                string expectedValue = (_searchValueTextBox.Text ?? string.Empty).Trim();
                LogDataSearch("Поиск: PART_TYPE='" + partType + "', Дочерний='" + childName + "', Параметр='" + parameterName + "', Значение='" + expectedValue + "'.");

                if (string.IsNullOrWhiteSpace(partType))
                {
                    _dataSearchResultTextBox.Text = "Выберите тип изделия PART_TYPE.";
                    LogDataSearch("Поиск остановлен: не выбран PART_TYPE.");
                    return;
                }

                if (string.IsNullOrWhiteSpace(parameterName))
                {
                    _dataSearchResultTextBox.Text = "Выберите параметр.";
                    LogDataSearch("Поиск остановлен: не выбран параметр.");
                    return;
                }

                var matchedObjects = new List<CLibObjectInfo>();

                lines.Add("=== ПОИСК ДАННЫХ ===");
                lines.Add("");
                lines.Add("Тип изделия: " + partType);
                lines.Add("Дочерний: " + (string.IsNullOrWhiteSpace(childName) ? "<root>" : childName));
                lines.Add("Параметр: " + parameterName);
                lines.Add("Значение: " + (string.IsNullOrWhiteSpace(expectedValue) ? "<любое>" : expectedValue));
                lines.Add("");
                lines.Add("idObject | PART_TYPE | Name | " + parameterName);
                lines.Add(new string('-', 160));

                foreach (CLibObjectInfo obj in GetDataSearchCandidateObjects())
                {
                    string actualValue = ReadParam(obj, parameterName);

                    if (!IsValueMatch(actualValue, expectedValue))
                        continue;

                    matchedObjects.Add(obj);
                    lines.Add(
                        obj.idObject + " | " +
                        ReadParam(obj, "PART_TYPE") + " | " +
                        SafeToString(() => obj.Name) + " | " +
                        actualValue
                    );
                }

                lines.Add("");
                lines.Add("Найдено: " + matchedObjects.Count);
                LogDataSearch("Поиск завершен. Найдено объектов: " + matchedObjects.Count + ".");

            }
            catch (Exception ex)
            {
                lines.Add("ОШИБКА:");
                lines.Add(ex.ToString());
                LogDataSearch("Ошибка поиска: " + ex);
            }

            _dataSearchResultTextBox.Text = string.Join("\r\n", lines);
        }

        private List<CLibObjectInfo> GetDataSearchCandidateObjects()
        {
            string partType = GetComboText(_partTypeComboBox);
            string childName = GetComboText(_childComboBox);
            string key = MakeCandidateKey(partType, childName);
            List<CLibObjectInfo> cached;

            if (_candidateObjectsCache.TryGetValue(key, out cached))
                return cached;

            var result = new List<CLibObjectInfo>();

            foreach (CLibObjectInfo root in GetRootObjectsByPartType(partType))
            {
                if (string.IsNullOrWhiteSpace(childName))
                {
                    result.Add(root);
                    continue;
                }

                foreach (CLibObjectInfo child in GetChildObjects(root))
                {
                    if (string.Equals(SafeToString(() => child.Name), childName, StringComparison.CurrentCultureIgnoreCase))
                        result.Add(child);
                }
            }

            _candidateObjectsCache[key] = result;
            return result;
        }

        private List<CLibObjectInfo> GetRootObjectsByPartType(string partType)
        {
            partType = (partType ?? string.Empty).Trim();

            List<CLibObjectInfo> cached;

            if (_rootObjectsByPartTypeCache.TryGetValue(partType, out cached))
                return cached;

            var result = new List<CLibObjectInfo>();

            if (string.IsNullOrWhiteSpace(partType) || _library == null)
                return result;

            int partTypeParamId = _library.GetParamDefId("PART_TYPE");
            var objects = _library.GetObjectParametersByValues(partTypeParamId, partType.Trim(), true, ';');

            if (objects != null)
                result.AddRange(objects);

            result.Sort((a, b) => string.Compare(SafeToString(() => a.Name), SafeToString(() => b.Name), StringComparison.CurrentCultureIgnoreCase));

            _rootObjectsByPartTypeCache[partType] = result;
            return result;
        }

        private List<CLibObjectInfo> GetChildObjects(CLibObjectInfo root)
        {
            var result = new List<CLibObjectInfo>();

            if (root == null || _library == null)
                return result;

            var children = _library.GetChildObjects(root);

            if (children != null)
                result.AddRange(children);

            result.Sort((a, b) => string.Compare(SafeToString(() => a.Name), SafeToString(() => b.Name), StringComparison.CurrentCultureIgnoreCase));

            return result;
        }

        private List<string> GetCachedChildNames(string partType)
        {
            partType = (partType ?? string.Empty).Trim();

            List<string> cached;

            if (_childNamesByPartTypeCache.TryGetValue(partType, out cached))
            {
                LogDataSearch("Дочерние элементы взяты из кэша для PART_TYPE='" + partType + "': " + cached.Count + ".");
                return cached;
            }

            var childNames = new SortedDictionary<string, string>(StringComparer.CurrentCultureIgnoreCase);
            int rootCount = 0;

            foreach (CLibObjectInfo root in GetRootObjectsByPartType(partType))
            {
                rootCount++;

                foreach (CLibObjectInfo child in GetChildObjects(root))
                {
                    string name = SafeToString(() => child.Name);

                    if (!string.IsNullOrWhiteSpace(name) && !childNames.ContainsKey(name))
                        childNames.Add(name, name);
                }
            }

            cached = new List<string>(childNames.Values);
            _childNamesByPartTypeCache[partType] = cached;
            LogDataSearch("Дочерние элементы проиндексированы для PART_TYPE='" + partType + "': root=" + rootCount + ", childNames=" + cached.Count + ".");
            return cached;
        }

        private List<string> GetCachedParameterNames(string partType, string childName)
        {
            partType = (partType ?? string.Empty).Trim();
            childName = (childName ?? string.Empty).Trim();

            string key = MakeCandidateKey(partType, childName);
            List<string> cached;

            if (_parameterNamesCache.TryGetValue(key, out cached))
            {
                LogDataSearch("Параметры взяты из кэша для ключа '" + key + "': " + cached.Count + ".");
                return cached;
            }

            var paramNames = new SortedDictionary<string, string>(StringComparer.CurrentCultureIgnoreCase);
            int objectCount = 0;

            foreach (CLibObjectInfo obj in GetDataSearchCandidateObjects())
            {
                objectCount++;

                foreach (Parameter parameter in _library.GetObjectParameters(obj.idObject))
                {
                    string name = SafeToString(() => parameter.name);
                    string caption = SafeToString(() => parameter.caption);
                    string display = string.IsNullOrWhiteSpace(caption) || caption == name ? name : name + " / " + caption;

                    if (!string.IsNullOrWhiteSpace(name) && !paramNames.ContainsKey(display))
                        paramNames.Add(display, display);
                }
            }

            cached = new List<string>(paramNames.Values);
            _parameterNamesCache[key] = cached;
            LogDataSearch("Параметры проиндексированы для ключа '" + key + "': objects=" + objectCount + ", params=" + cached.Count + ".");
            return cached;
        }

        private static string MakeCandidateKey(string partType, string childName)
        {
            return (partType ?? string.Empty).Trim() + "\u001f" + (childName ?? string.Empty).Trim();
        }

        private List<string> GetParameterValueList(int paramDefId)
        {
            var values = new SortedDictionary<string, string>(StringComparer.CurrentCultureIgnoreCase);

            AddParameterValues(values, SafeEnumerate(_library.GetParamValuesList(paramDefId)));
            AddParameterValues(values, SafeEnumerate(InvokeMethod(_library, "GetParameterValues", paramDefId, false, false)));
            AddParameterValues(values, SafeEnumerate(InvokeMethod(_library, "GetParameterValues", paramDefId, false, true)));
            AddParameterValues(values, SafeEnumerate(InvokeMethod(_library, "GetParamDefValues", paramDefId)));
            AddParameterValues(values, SafeEnumerate(InvokeMethod(_library, "GetParamDefValuesExtended", paramDefId)));

            return new List<string>(values.Values);
        }

        private static IEnumerable<object> SafeEnumerate(object value)
        {
            var enumerable = value as System.Collections.IEnumerable;

            if (enumerable == null)
                yield break;

            foreach (object item in enumerable)
                yield return item;
        }

        private static void AddParameterValues(SortedDictionary<string, string> target, IEnumerable<object> values)
        {
            foreach (object value in values)
            {
                string text = ExtractValueText(value);

                if (!string.IsNullOrWhiteSpace(text) && !target.ContainsKey(text))
                    target.Add(text, text);
            }
        }

        private static string ExtractValueText(object value)
        {
            if (value == null)
                return string.Empty;

            if (value is string)
                return Convert.ToString(value);

            object propertyValue = ReadMemberValue(value, "Value");

            if (propertyValue == null)
                propertyValue = ReadMemberValue(value, "mValue");

            if (propertyValue == null)
                propertyValue = ReadMemberValue(value, "value");

            if (propertyValue == null)
                propertyValue = value;

            return Convert.ToString(propertyValue);
        }

        private static object ReadMemberValue(object target, string memberName)
        {
            if (target == null)
                return null;

            BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
            Type type = target.GetType();

            PropertyInfo property = type.GetProperty(memberName, flags);

            if (property != null && property.GetIndexParameters().Length == 0)
            {
                try
                {
                    return property.GetValue(target, null);
                }
                catch
                {
                }
            }

            FieldInfo field = type.GetField(memberName, flags);

            if (field != null)
            {
                try
                {
                    return field.GetValue(target);
                }
                catch
                {
                }
            }

            return null;
        }

        private static void FillComboBox(ComboBox comboBox, IList<string> values, string current, bool includeEmpty)
        {
            comboBox.BeginUpdate();
            comboBox.Items.Clear();

            if (includeEmpty)
                comboBox.Items.Add(string.Empty);

            foreach (string value in values)
            {
                if (!string.IsNullOrWhiteSpace(value))
                    comboBox.Items.Add(value);
            }

            int selectedIndex = -1;

            for (int i = 0; i < comboBox.Items.Count; i++)
            {
                if (string.Equals(Convert.ToString(comboBox.Items[i]), current, StringComparison.CurrentCultureIgnoreCase))
                {
                    selectedIndex = i;
                    break;
                }
            }

            comboBox.SelectedIndex = selectedIndex;
            comboBox.EndUpdate();
        }

        private static string GetComboText(ComboBox comboBox)
        {
            if (comboBox == null)
                return string.Empty;

            if (comboBox.SelectedItem != null)
                return Convert.ToString(comboBox.SelectedItem).Trim();

            return (comboBox.Text ?? string.Empty).Trim();
        }

        private static string ExtractParameterName(string displayText)
        {
            if (string.IsNullOrWhiteSpace(displayText))
                return string.Empty;

            int separator = displayText.IndexOf(" / ", StringComparison.Ordinal);

            if (separator >= 0)
                return displayText.Substring(0, separator).Trim();

            return displayText.Trim();
        }

        private static bool IsValueMatch(string actualValue, string expectedValue)
        {
            if (string.IsNullOrWhiteSpace(expectedValue))
                return true;

            return string.Equals(
                actualValue == null ? string.Empty : actualValue.Trim(),
                expectedValue.Trim(),
                StringComparison.CurrentCultureIgnoreCase
            );
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
                    HierarchySelectionResult hierarchySelection = SelectObjectsInHierarchy(foundIds);
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

        private HierarchySelectionResult SelectObjectsInHierarchy(IList<int> ids)
        {
            var selectionResult = new HierarchySelectionResult();

            if (_browser == null)
            {
                selectionResult.Message = "DBBrowser недоступен.";
                return selectionResult;
            }

            if (ids == null || ids.Count == 0)
            {
                selectionResult.Message = "Нет найденных объектов для перехода.";
                return selectionResult;
            }

            int idObject = ids[0];
            int[] path = BuildObjectPath(idObject);
            selectionResult.PathText = path.Length == 0 ? "<пустой>" : string.Join(" -> ", path);
            selectionResult.Message = "RootObject=" + SafeInvokeInt(_library, "GetRootObject", idObject) +
                                      "; ParentObject=" + SafeInvokeInt(_library, "GetParentObject", idObject);

            var candidates = GetHierarchySelectionTargets();
            int[] idsArray = ToArray(ids);

            foreach (object candidate in candidates)
            {
                MethodInvokeResult result = TryInvokeMethod(candidate, "ViewObjectsOnTree", ids);

                if (!result.Invoked)
                    result = TryInvokeMethod(candidate, "ViewObjectsOnTree", idsArray);

                if (result.Invoked)
                {
                    TryInvokeMethod(candidate, "HighlightObject", idObject);
                    TryInvokeMethod(candidate, "SelectObject", idObject);

                    selectionResult.Success = true;
                    selectionResult.TargetType = candidate.GetType().FullName;
                    selectionResult.Message = AppendDetail(selectionResult.Message, "ViewObjectsOnTree(ids) выполнен.");
                    return selectionResult;
                }
            }

            foreach (object candidate in candidates)
            {
                MethodInvokeResult result = TryInvokeMethod(candidate, "ViewObjects", ids);

                if (!result.Invoked)
                    result = TryInvokeMethod(candidate, "ViewObjects", idsArray);

                if (result.Invoked)
                {
                    TryInvokeMethod(candidate, "HighlightObject", idObject);
                    TryInvokeMethod(candidate, "SelectObject", idObject);

                    selectionResult.Success = true;
                    selectionResult.TargetType = candidate.GetType().FullName;
                    selectionResult.Message = AppendDetail(selectionResult.Message, "ViewObjects(ids) выполнен.");
                    return selectionResult;
                }
            }

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

        private sealed class MethodInvokeResult
        {
            public bool Invoked { get; set; }
            public object ReturnValue { get; set; }
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
            MethodInvokeResult result = TryInvokeMethod(target, methodName, args);
            return result.Invoked ? result.ReturnValue : null;
        }

        private static MethodInvokeResult TryInvokeMethod(object target, string methodName, params object[] args)
        {
            var result = new MethodInvokeResult();

            if (target == null)
                return result;

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
                    result.ReturnValue = method.Invoke(target, args);
                    result.Invoked = true;
                    return result;
                }
                catch
                {
                }
            }

            return result;
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
                LogDataSearch("Python: запуск скрипта.");

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
                LogDataSearch("Python: скрипт выполнен.");
                LogDataSearch("Python output:\r\n" + sb);
            }
            catch (Exception ex)
            {
                _pythonOutputTextBox.Text = "ОШИБКА ВЫПОЛНЕНИЯ PYTHON:\r\n" + ex;
                LogDataSearch("Python: ошибка выполнения:\r\n" + ex);
            }
        }

        private PythonExecutionResult ExecutePythonCode(string code, string scriptPath, string logPath)
        {
            var result = new PythonExecutionResult();

            try
            {
                var engine = Python.CreateEngine();
                var scope = engine.CreateScope();

                scope.SetVariable("Library", _library);
                scope.SetVariable("DBBrowser", _browser);
                scope.SetVariable("CLMainForm", this);
                scope.SetVariable("ScriptPath", scriptPath ?? string.Empty);
                scope.SetVariable("LogFilePath", logPath ?? string.Empty);
                scope.SetVariable("PythonLogFilePath", PythonLogFilePath);

                engine.Runtime.LoadAssembly(typeof(CADLibrary).Assembly);
                engine.Runtime.LoadAssembly(typeof(CLibObjectInfo).Assembly);
                engine.Runtime.LoadAssembly(typeof(Form).Assembly);
                engine.Runtime.LoadAssembly(typeof(Color).Assembly);

                using (var output = new MemoryStream())
                using (var error = new MemoryStream())
                {
                    engine.Runtime.IO.SetOutput(output, Encoding.UTF8);
                    engine.Runtime.IO.SetErrorOutput(error, Encoding.UTF8);

                    var source = engine.CreateScriptSourceFromString(code ?? string.Empty);
                    source.Execute(scope);

                    result.Stdout = Encoding.UTF8.GetString(output.ToArray());
                    result.Stderr = Encoding.UTF8.GetString(error.ToArray());
                }

                result.Success =
                    string.IsNullOrEmpty(result.Stderr) &&
                    !ContainsPythonErrorMarker(result.Stdout);
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.ExceptionText = ex.ToString();
            }

            result.DisplayText = BuildPythonDisplayText(result);

            try
            {
                File.AppendAllText(logPath, result.DisplayText + Environment.NewLine, Encoding.UTF8);
            }
            catch
            {
            }

            return result;
        }

        private static string BuildPythonDisplayText(PythonExecutionResult result)
        {
            var sb = new StringBuilder();

            if (!string.IsNullOrEmpty(result.Stdout))
            {
                sb.AppendLine("=== STDOUT ===");
                sb.AppendLine(result.Stdout);
            }

            if (!string.IsNullOrEmpty(result.Stderr))
            {
                sb.AppendLine("=== STDERR ===");
                sb.AppendLine(result.Stderr);
            }

            if (!string.IsNullOrEmpty(result.ExceptionText))
            {
                sb.AppendLine("=== EXCEPTION ===");
                sb.AppendLine(result.ExceptionText);
            }

            if (sb.Length == 0)
                sb.AppendLine("Script completed without text output.");

            return sb.ToString();
        }

        private static bool ContainsPythonErrorMarker(string text)
        {
            if (string.IsNullOrEmpty(text))
                return false;

            return text.IndexOf(" ERROR:", StringComparison.OrdinalIgnoreCase) >= 0 ||
                text.IndexOf("CRITICAL:", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private void LoadPythonScriptFromFile(string path)
        {
            try
            {
                if (!File.Exists(path))
                {
                    _pythonOutputTextBox.Text = "Файл Python-скрипта не найден:\r\n" + path;
                    LogDataSearch("Python: файл скрипта не найден: " + path);
                    return;
                }

                _loadedPythonScriptPath = Path.GetFullPath(path);
                _pythonCodeTextBox.Text = File.ReadAllText(path, Encoding.UTF8);
                _pythonOutputTextBox.Text = "Загружен Python-скрипт:\r\n" + path;
                LogDataSearch("Python: загружен скрипт " + path);
            }
            catch (Exception ex)
            {
                _pythonOutputTextBox.Text = "Ошибка загрузки Python-скрипта:\r\n" + ex;
                LogDataSearch("Python: ошибка загрузки скрипта:\r\n" + ex);
            }
        }

        private void RunLatestPythonScript()
        {
            try
            {
                string dir = GetPythonScriptsDir();
                string latestPath = null;
                DateTime latestWriteTime = DateTime.MinValue;

                foreach (string path in Directory.GetFiles(dir, "*.py"))
                {
                    DateTime writeTime = File.GetLastWriteTime(path);

                    if (latestPath == null || writeTime > latestWriteTime)
                    {
                        latestPath = path;
                        latestWriteTime = writeTime;
                    }
                }

                if (latestPath == null)
                {
                    _pythonOutputTextBox.Text = "В папке Python нет .py файлов:\r\n" + dir;
                    LogDataSearch("Python: в папке нет сценариев: " + dir);
                    return;
                }

                LogDataSearch("Python: запуск последнего сценария " + latestPath);
                RunPythonFile(latestPath);
            }
            catch (Exception ex)
            {
                _pythonOutputTextBox.Text = "Ошибка запуска последнего Python-сценария:\r\n" + ex;
                LogDataSearch("Python: ошибка запуска последнего сценария:\r\n" + ex);
            }
        }

        private async Task StartPythonAutoRunAsync()
        {
            if (_pythonAutoRunInProgress)
                return;

            string path = _loadedPythonScriptPath;

            if (string.IsNullOrEmpty(path) || !File.Exists(path))
                path = FindLatestPythonScriptPath();

            if (string.IsNullOrEmpty(path) || !File.Exists(path))
            {
                _pythonOutputTextBox.Text = "Auto retry: no Python script file found.";
                return;
            }

            _loadedPythonScriptPath = Path.GetFullPath(path);
            _pythonAutoLogFilePath = CreatePythonAutoLogFilePath();
            _pythonAutoStatusFilePath = GetPythonAutoStatusFilePath();
            _pythonAutoRunActive = true;

            AppendPythonAutoLog("Auto retry started. Script: " + _loadedPythonScriptPath);
            AppendPythonAutoLog("Protocol status file: " + _pythonAutoStatusFilePath);
            AppendPythonAutoLog("Auto test mode: after an error CADLib polls status/script changes every 10 seconds.");
            AppendPythonAutoLog("Log: " + _pythonAutoLogFilePath);
            WritePythonAutoStatus("running", "manual start");
            SetPythonAutoStatus("Autotest: running");

            await RunPythonAutoAttemptAsync("manual start");
        }

        private async Task OnPythonAutoRetryTimerAsync()
        {
            if (_pythonAutoRetryTimer != null)
                _pythonAutoRetryTimer.Stop();

            if (!_pythonAutoRunActive || _pythonAutoRunInProgress)
                return;

            if (string.IsNullOrEmpty(_loadedPythonScriptPath) || !File.Exists(_loadedPythonScriptPath))
            {
                AppendPythonAutoLog("Auto retry stopped: script file is missing.");
                WritePythonAutoStatus("stopped", "script file is missing");
                SetPythonAutoStatus("Autotest: stopped, script missing");
                _pythonAutoRunActive = false;
                return;
            }

            DateTime currentWriteTimeUtc = File.GetLastWriteTimeUtc(_loadedPythonScriptPath);
            string protocolState = ReadPythonAutoStatusState();

            if (currentWriteTimeUtc > _pythonAutoScriptWriteTimeUtc ||
                string.Equals(protocolState, "ready_to_run", StringComparison.OrdinalIgnoreCase))
            {
                AppendPythonAutoLog("Auto retry detected ready signal. State=" + protocolState + "; scriptChanged=" + (currentWriteTimeUtc > _pythonAutoScriptWriteTimeUtc));
                WritePythonAutoStatus("running", "ready signal received");
                await RunPythonAutoAttemptAsync("ready signal");
                return;
            }

            AppendPythonAutoLog("Auto retry heartbeat: waiting for ready_to_run or script change. State=" + protocolState);
            SetPythonAutoStatus("Autotest: waiting, polling 10 sec");

            if (_pythonAutoRetryTimer != null)
                _pythonAutoRetryTimer.Start();
        }

        private async Task RunPythonAutoAttemptAsync(string reason)
        {
            if (_pythonAutoRunInProgress)
                return;

            _pythonAutoRunInProgress = true;

            try
            {
                string path = _loadedPythonScriptPath;
                _pythonAutoScriptWriteTimeUtc = File.GetLastWriteTimeUtc(path);
                string code = File.ReadAllText(path, Encoding.UTF8);

                SetPythonAutoStatus("Автотест: выполнение (" + reason + ")");
                AppendPythonAutoLog("Attempt started: " + reason + ". Script write time UTC: " + _pythonAutoScriptWriteTimeUtc.ToString("O"));

                var result = await Task.Run(() => ExecutePythonCode(code, path, _pythonAutoLogFilePath));

                _pythonCodeTextBox.Text = code;
                _pythonOutputTextBox.Text = result.DisplayText;

                if (result.Success)
                {
                    AppendPythonAutoLog("Attempt completed successfully. Auto retry finished.");
                    AppendPythonAutoLog("Script completed successfully. Polling stopped.");
                    WritePythonAutoStatus("success", "script completed successfully");
                    _pythonOutputTextBox.Text = result.DisplayText + Environment.NewLine + "Autotest: script completed successfully. Polling stopped.";
                    SetPythonAutoStatus("Autotest: success");
                    _pythonAutoRunActive = false;

                    if (_pythonAutoRetryTimer != null)
                        _pythonAutoRetryTimer.Stop();
                }
                else
                {
                    AppendPythonAutoLog("Attempt failed. Polling every 10 seconds for ready_to_run or script changes.");
                    AppendPythonAutoLog("Status protocol: Codex may set state=codex_working, then state=ready_to_run.");
                    WritePythonAutoStatus("waiting_fix", "script failed; waiting for script change or ready_to_run");
                    _pythonOutputTextBox.Text = result.DisplayText + Environment.NewLine + "Autotest: error. Polling every 10 seconds.";
                    SetPythonAutoStatus("Autotest: error, polling 10 sec");

                    if (_pythonAutoRetryTimer != null)
                    {
                        _pythonAutoRetryTimer.Stop();
                        _pythonAutoRetryTimer.Start();
                    }
                }
            }
            catch (Exception ex)
            {
                AppendPythonAutoLog("Auto retry internal error:\r\n" + ex);
                AppendPythonAutoLog("Auto test internal error. Polling every 10 seconds.");
                WritePythonAutoStatus("waiting_fix", "internal auto test error");
                _pythonOutputTextBox.Text = "Auto retry internal error:\r\n" + ex + Environment.NewLine + "Autotest: error. Polling every 10 seconds.";
                SetPythonAutoStatus("Autotest: error, polling 10 sec");

                if (_pythonAutoRetryTimer != null)
                {
                    _pythonAutoRetryTimer.Stop();
                    _pythonAutoRetryTimer.Start();
                }
            }
            finally
            {
                _pythonAutoRunInProgress = false;
            }
        }

        private static string FindLatestPythonScriptPath()
        {
            string dir = GetPythonScriptsDir();
            string latestPath = null;
            DateTime latestWriteTime = DateTime.MinValue;

            foreach (string path in Directory.GetFiles(dir, "*.py"))
            {
                DateTime writeTime = File.GetLastWriteTime(path);

                if (latestPath == null || writeTime > latestWriteTime)
                {
                    latestPath = path;
                    latestWriteTime = writeTime;
                }
            }

            return latestPath;
        }

        private void SetPythonAutoStatus(string text)
        {
            if (_pythonAutoStatusLabel == null)
                return;

            try
            {
                if (_pythonAutoStatusLabel.InvokeRequired)
                    _pythonAutoStatusLabel.BeginInvoke(new Action(() => _pythonAutoStatusLabel.Text = text));
                else
                    _pythonAutoStatusLabel.Text = text;
            }
            catch
            {
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

        private sealed class PythonExecutionResult
        {
            public bool Success;
            public string Stdout;
            public string Stderr;
            public string ExceptionText;
            public string DisplayText;
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
