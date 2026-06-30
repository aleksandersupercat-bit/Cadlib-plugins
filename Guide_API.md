# CADLib / Model Studio / nanoCAD API — единый дедуплицированный справочник

Версия: `1.1-mapi-research`, дата сборки: `2026-06-25`.

## Назначение

Документ объединяет два ранее созданных справочника в один рабочий материал:

- архитектура расширения CADLib / Model Studio: плагины, события, интерфейсы, жизненный цикл, меню/кнопки, FolderPlugin;
- API-reference по `CSProject3D`, `CADLibControls`, `CADLibKernel`, `CSAppServices`;
- PythonPlugin-заготовки и практические проверки;
- ограничения анализа и перечень того, что нужно проверить на живой установке CADLib / Model Studio.

## Правила дедупликации

1. При конфликте приоритет выше у XML-комментариев `CSProject3D.XML` и `CADLibControls.xml`.
2. Для `CADLibKernel` и `CSAppServices` описания оставлены как восстановленные по DLL/сигнатурам, если XML-комментария нет.
3. Повторяющиеся вводные фрагменты, одинаковые описания слоёв и повторные практические выводы сведены к одному месту.
4. Не удалялись технические списки методов/событий/типов, даже если они частично пересекаются: для справочника это полезнее, чем агрессивное сокращение.
5. Широкие таблицы сохранены; при необходимости их лучше сокращать или разбивать точечно, а не оборачивать весь документ в HTML-блоки.

## Быстрая карта принятия решений

| Задача | Использовать в первую очередь | Комментарий |
|---|---|---|
| Быстрый скрипт внутри CADLib | PythonPlugin: `Library`, `DBBrowser`, `CLMainForm` | Подходит для диагностики, выборок, проверки API. |
| Кнопка/меню в CADLib | C# plugin layer: `ICADLibPlugin`, `PluginsManager`, `GetMenu`, `GetToolbars` | PythonPlugin не является полноценным UI-plugin контуром. |
| Работа с объектами/параметрами БД | `CADLibraryBase`, `CADLib.CADLibrary`, `CLibObjectInfo`, `CLibParamDefInfo`, `CLibFilterItem` | Ядро справочника для массовых операций. |
| 3D-выбор, текущий вид, mesh/shape | `CSProject3D.CAD3DLibrary`, `Viewer3DCtrl`, `ModelStudio.Graphics3D.*` | Для 3D-модели и графического представления. |
| Расширение дерева каталогов | `FolderPlugin`, `CreateFolderObject`, `ReportObjectPicked`, `GetObjectMenuItems` | Для специальных папок, контекстного меню и обработки double-click. | 
| Отчёты / публикация / сервисы | `CSAppServices.CHTMLReport`, `ObjectPublisher`, `XExchange`, `DbConnectParameters` | Требует проверки на конкретной версии. |
| Команды nanoCAD / Model Studio | nanoCAD .NET plugin: `CommandMethod`, HostMgd/Teigha | Это другой слой, не CADLib Plugin API. |

## Практические пометки по использованию

Ниже короткие примечания не как отдельный учебник, а как подсказки по тем методам, которые реально пригодились в рабочем плагине и скриптах.

- `ICADLibPlugin.GetMenu(...)` и `ICADLibPlugin.GetToolbars(...)` — базовые точки, если нужно добавить кнопку или пункт меню в интерфейс CADLib/Model Studio через C#-плагин. Для обычного PythonPlugin это не замена полноценному UI-контейнеру.
- `ICADLibMainPlugin.GetMainFormMenu(...)` и `ICADLibMainPlugin.GetMainFormToolBar(...)` — работают только у плагина с главной формой. Если вернуть `null`, то другие плагины не смогут встраивать свои пункты и кнопки в главное меню/панель.
- `IDatabaseBrowser.CurrentFolder`, `IDatabaseBrowser.GetSelectedObjects(...)`, `IDatabaseBrowser.GetSelectionPath(...)`, `IDatabaseBrowser.UpdateButtons(...)` — полезны для сценариев, где UI должен реагировать на текущую папку, выделение и состояние браузера БД.
- `CADLibraryBase.GetParamDefId(...)`, `CADLibraryBase.GetObjectParametersByValues(...)`, `CADLibraryBase.GetObjectParameters(...)` — рабочая связка для поиска и индексации по параметрам. Для `PART_TYPE` именно эта схема удобна для массовых выборок и построения списков значений.
- `SelectChildObjectByPath(...)` в дереве браузера может быть доступен не во всех контекстах и в живом хосте иногда возвращает `null`; на него лучше не опираться как на единственный путь навигации по иерархии.
- В PythonPlugin обычно доступны `Library`, `DBBrowser`, `CLMainForm`. Если нужен дополнительный мост для диагностики или записи логов, удобнее добавлять его в главную форму плагина и вызывать из Python через `CLMainForm`.

---

# Часть A. Архитектура расширения, плагины, события и UI

Версия: первичный технический справочник по `CSProject3D`, `CADLibControls`, `CADLibKernel`, `CSAppServices`.

Цель документа — не просто перечислить сигнатуры, а выделить точки расширения: события, интерфейсы, наследование, сервисные классы, жизненный цикл плагина и места подключения меню/кнопок. Верстка переработана: широкие таблицы заменены на карточки и списки, чтобы документ не уезжал за экран.

## 1. Что подтверждено фактически

Проверочный Python-скрипт в редакторе CADLib успешно получил активную БД, текущую папку и выполнил фильтр по объектам `PART_TYPE = Стена`. Это подтверждает, что встроенный Python имеет доступ к `Library`, `DBBrowser`, фильтрам и объектам БД через .NET API.

Из загруженных DLL и XML подтверждены следующие слои:

- `CADLibControls.dll` — UI, плагины, браузер БД, формы, меню, панели, редактор параметров. Найдено типов: 1539; методов: 10192; событий: 110; interface-implementations: 170.
- `CSProject3D.dll` — 3D-модель, 3D-просмотрщик, выделение, публикации, коллизии, графика. Найдено типов: 1465; методов: 12606; событий: 85; interface-implementations: 424.
- `CADLibKernel.dll` — ядро БД CADLib: объекты, параметры, фильтры, файлы, веб-сервис обновления. Найдено типов: 1375; методов: 6872; событий: 194; interface-implementations: 69.
- `CSAppServices.dll` — сервисный слой: подключение к БД, XML-обмен, отчеты, публикация/обновление БД. Найдено типов: 118; методов: 720; событий: 0; interface-implementations: 7.

## 2. Карта слоев API

```text
CADLib / Model Studio application
├─ CADLibControls
│  ├─ интерфейсы плагинов
│  ├─ главное окно / меню / панели инструментов
│  ├─ DBBrowser / DirectoryBrowser / FoldersBrowser
│  └─ FolderPlugin и расширение дерева каталогов
├─ CSProject3D
│  ├─ CAD3DLibrary
│  ├─ Viewer3DCtrl
│  ├─ события выбора объектов в 3D
│  ├─ публикации, виды, коллизии, 3D-графика
│  └─ CADLibPluginEntryPoint
├─ CADLibKernel
│  ├─ CADLibraryBase
│  ├─ CLibObjectInfo / CLibParamDefInfo / CLibFilterItem
│  ├─ файлы, связи, категории, параметры
│  └─ ObjectUpdateService / RouterService
└─ CSAppServices
   ├─ DbConnectParameters
   ├─ ObjectPublisher
   ├─ XExchange
   ├─ CHTMLReport
   └─ UpgradeDatabaseBuild / ParameterStorageBuild
```

## 3. Жизненный цикл плагина CADLib

По XML-описаниям и сигнатурам видно, что плагинный механизм строится вокруг интерфейсов `ICADLibPlugin`, `ICADLibMainPlugin`, `ICADLibStartPlugin`, менеджера `PluginsManager` и точки входа `CADLibPluginEntryPoint.RegisterPlugin(PluginsManager manager)`.

Ожидаемая схема:

```text
1. CADLib загружает plugin assembly
2. Ищет/вызывает CADLibPluginEntryPoint.RegisterPlugin(manager)
3. RegisterPlugin возвращает главный плагин или регистрирует плагины в PluginsManager
4. MainPlugin предоставляет главное окно, меню, панели и DBBrowser
5. Остальные плагины возвращают меню/панели через ICADLibPlugin
6. PluginsManager объединяет меню и панели с главным интерфейсом
7. При изменении состояния БД/папки/объекта вызывается TrackInterfaceItems / UpdateButtons
8. FolderPlugin расширяет дерево каталогов, контекстные меню и обработку double-click по 3D-объектам
```

Практический вывод: кнопки и меню нужно искать не в PythonPlugin, а в C#-плагинном контуре. PythonPlugin удобен для скриптов, но полноценная кнопка/панель/плагин вероятнее делается через `ICADLibPlugin` и `PluginsManager`.

## 4. Главные интерфейсы и точки расширения UI

### `CADLib.ICADLibPlugin`

- DLL: `CADLibControls.dll`
- Тип: `interface`
- XML-описание: Абстрактный класс, реализованный во всех плагинах. Извлекается вызовом метода CADLibPluginEntryPoint.RegisterPlugin(PluginsManager manager).
- Практический смысл: Базовый интерфейс обычного плагина. Через него плагин отдаёт меню, панели инструментов и реагирует на состояние интерфейса.
- Практическая пометка: если нужен элемент интерфейса в верхней панели или меню Model Studio, в первую очередь смотрят на `GetMenu(...)` и `GetToolbars(...)`.

Методы:
- `GetMenu(WinForms.MenuStrip())` — Метод для получения главного меню плагина, для последующего объединения элементов
- `GetToolbars(WinForms.ToolStripContainer())` — Метод для получения панели инструментов плагина, для последующего объединения контролов с неё
- `TrackInterfaceItems(void(CADLib.InterfaceTracker))` — Метод для реализации обработки состояния элементов управления в зависимости от состояния интерфейса

### `CADLib.ICADLibMainPlugin`

- DLL: `CADLibControls.dll`
- Тип: `interface`
- XML-описание: Абстрактный класс, реализованный в главных плагинах. Извлекается вызовом метода CADLibPluginEntryPoint.RegisterPlugin(PluginsManager manager).
- Практический смысл: Интерфейс главного плагина приложения: отдаёт главную форму, главное меню, главную панель инструментов и DBBrowser.

Свойства:
- `ApplicationTitle: string`
Методы:
- `GetDataBrowser(CADLib.IDatabaseBrowser())` — Используются только в плагинах с главной формой
- `GetMainForm(WinForms.Form())` — Используются только в плагинах с главной формой Возвращает главную форма, которая будет запущена как основная
- `GetMainFormToolBar(WinForms.ToolStripContainer())` — Используются только в плагинах с главной формой Возвращает главную панель инструментов, чтобы добавлять кнопки других плагинов Если не указана, то добавление кнопок с других плагинов не производится
- `GetMainFormMenu(WinForms.MenuStrip())` — Используются только в плагинах с главной формой Возвращает главное меню, чтобы другие плагины добавлять пункты других плагинов Если null, то добавление пунктов меню из плагинов не производится
- `GetInterfaceState(void(CADLib.LibConnectionState*, CADLib.LibFolderState*, CADLib.LibObjectState*, bool[]*))`
- `RefreshWindow(void())`
- `RegisterDocViewer(void(CADLib.DocumentViewer))`

### `CADLib.ICADLibStartPlugin`

- DLL: `CADLibControls.dll`
- Тип: `interface`
- Практический смысл: Стартовый плагин, который хранит ссылку на главный плагин. Используется на этапе запуска приложения.

Свойства:
- `MainPlugin: CADLib.ICADLibMainPlugin`

### `CADLib.IDatabaseBrowser`

- DLL: `CADLibControls.dll`
- Тип: `interface`
- XML-описание: Интерфейс, главного плагина, создающего окно Интерфес содержит методы типа GetCurrentSelection
- Практический смысл: Главный интерфейс браузера БД: активный объект, активный файл, текущая папка, выбранные объекты/файлы, обновление окна и каталога.
- Практическая пометка: для выборок и поисков чаще всего удобнее брать `CurrentFolder`, `GetSelectedObjects(...)` и `GetSelectionPath(...)`, а не пытаться сразу работать через визуальное дерево.

Свойства:
- `Library: CADLib.CADLibrary`
- `ActiveObject: CLibObjectInfo`
- `ActiveFile: CLibFileInfo`
- `ItemCount: int32`
- `CurrentFolder: CADLib.DbSettingsItem`
Методы:
- `UpdateButtons(void())`
- `GetSelectedObjects(ET_15(List`1))`
- `GetSelectedFiles(ET_15(List`1))`
- `GetSelection(ET_15(List`1))`
- `IsSingleSelection(bool())`
- `GetSelectionMode(CADLib.ESelectionState())`
- `RefreshActiveObject(void(bool))`
- `UpdateWindow(void())`
- `RefreshCurrentCatalog(void())`
- `GetSelectionPath(ET_15())`
- `GetClientState(CADLib.DirectoryBrowserClientState())`

### `CADLib.PluginsManager`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLib.PluginsManager` → `System.Object`
- XML-описание: Класс для управления плагинами
- Практический смысл: Менеджер загрузки и объединения плагинов: главное окно, меню, панели инструментов, DBBrowser, Library.
- Практическая пометка: если плагин должен встроиться в интерфейс, именно `PluginsManager` обычно склеивает меню и панели от разных расширений.
- Статические методы: `AreMenuItemsEqual`, `FindMenuItem`, `MergeInterfaceMenus`, `MergeInterfaceToolbars`, `ScanAndAddMenu`

Свойства:
- `MainForm: WinForms.Form` — Главная форма из главного плагина После загрузки всех плагинов она будет показана как основная
- `MainDBBrowser: CADLib.IDatabaseBrowser`
- `Library: CADLib.CADLibrary`
- `ShowSplash: bool` — Показывать ли сплэш картинку во время зугрузки
- `StartOrMainPlugin: CADLib.ICADLibMainPlugin`
Методы:
- `DbScripts(ET_15(IEnumerable`1))`
- `Load(void(string))` — Загружает главный плагин, имеющий главное окно Если загрузка не успешна, то программа прекращает свою работу
- `Application_Idle(void(object, System.EventArgs))`
- `UpdateButtons(void(CADLib.LibConnectionState, CADLib.LibFolderState, CADLib.LibObjectState, bool[]))` — Этот метод вызывается плагином во время изменения статуса
- `AreMenuItemsEqual(bool(WinForms.ToolStripItem, WinForms.ToolStripItem))`
- `FindMenuItem(WinForms.ToolStripMenuItem(WinForms.ToolStripItemCollection, WinForms.ToolStripMenuItem))`
- `MergeInterfaceMenus(void(WinForms.MenuStrip))` — Объединение меню плагина с главным меню приложения
- `MergeInterfaceToolbars(void(WinForms.ToolStripContainer))` — Объединение панелей инструментов плагина с главной формой
- `MergeInterfaceMenus(void(WinForms.MenuStrip, WinForms.MenuStrip, bool))` — Объединение меню плагина с главным меню приложения
- `ScanAndAddMenu(void(WinForms.ToolStripMenuItem, WinForms.ToolStripMenuItem, bool))` — Рекурсивная часть объединения меню
- `MergeInterfaceToolbars(void(WinForms.ToolStripContainer, WinForms.ToolStripContainer))` — Объединение панелей инструментов плагина с главной формой

### `CSProject3D.CADLibPluginEntryPoint`

- DLL: `CSProject3D.dll`
- Тип: `class`
- Наследование: `CSProject3D.CADLibPluginEntryPoint` → `System.Object`
- Практический смысл: Вероятная точка входа 3D-приложения CADLib. Метод `RegisterPlugin(manager)` возвращает `ICADLibMainPlugin`.
- Статические методы: `RegisterPlugin`

Методы:
- `RegisterPlugin(CADLib.ICADLibMainPlugin(CADLib.PluginsManager))`

## 5. FolderPlugin: расширение дерева, папок и контекстных меню

### `CADLibControls.FolderPlugin`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLibControls.FolderPlugin` → `System.Object`
- XML-описание: базовый класс для работы с папками категорий из плагинов
- Практический смысл: Базовый класс для работы с папками категорий из плагинов. Позволяет создавать папки/подпапки/классификаторы, обрабатывать double-click по 3D-объекту и добавлять меню объектов.

Методы:
- `CreateFolderObject(CLibCatalogFilterItem(CLibCatalogFilterItem, int32, string, string, int32, bool, eFolderFlags, EResultSetType, int32))` — Создаёт информацию о папке с использованием плагинов Вызывается для корневых каталогов
- `CreateVirtualFolderObject(CLibCatalogFilterItem(CLibCatalogFilterItem, int32))` — Создаёт информацию о папке с использованием плагинов(пиртуальная папка) Вызывается для корневых каталогов
- `CreateSubFolder(CLibCatalogFilterItem(CLibCatalogFilterItem, int32, string, string, string, int32, bool, eFolderFlags, int32))` — Вызывается при создании некорневых узлов папок (например в методе ExpandSubfolders)
- `CreateSubClassifier(CLibClassifierFilterItem(CLibCatalogFilterItem, int32, string, FilterInfoPair, CLibClassifier, bool))` — Вызывается при создании некорневых узлов классификаторов (например в методе ExpandSubfolders)
- `ReportObjectPicked(void(CLibObjectInfo, string, bool*))` — Вызывается при двойном клики по объекту в 3д - позволяет плагинам обработать клик и запретить форме менять папку
- `TryGetLibraryObject(CLibObjectInfo(CLibObjectInfo, string))` — Запрашивает у плагина объект
- `GetObjectMenuItems(ET_15(IEnumerable`1, void, WinForms.ToolStripMenuItem))` — Получение дополнительного меню для объектов
- `GetAdditionalCurrenViewObjects(ET_15())` — Получает дополнительные объекты из текущего вида Имеет значение для таких плагинов как "поверхности земли", которые показывают дополнительные объекты во вьювере, но они не отображаются в узле "Текущий вид". Тем не менее данные объекты должны быть обработаны во время выбора опции "Текущий вид" при экспорте или проверке коллизий.

Типовые сценарии `FolderPlugin`:

- создать виртуальную папку для собственной выборки, например “Объекты с ошибками параметров”;
- расширить классификатор дополнительными узлами;
- добавить контекстное меню для выбранных объектов;
- перехватить двойной клик по объекту в 3D через `ReportObjectPicked`;
- вернуть дополнительные объекты текущего вида через `GetAdditionalCurrenViewObjects`.

## 6. Библиотека БД и события ядра

### `CADLibKernel.CADLibraryBase`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CADLibraryBase` → `System.Object`
- Практический смысл: Базовый класс библиотеки CADLib. Здесь находятся события подключения, изменения имени объекта и обновления, а также основной объектный API.
- Статические методы: `ArchiveBlobToFile`, `ConvertDateValueToPgSql`, `ConvertDateValueToSql`, `ConvertDateValueToTSql`, `CreateDbCommand`, `Deserialize`, `DoUploadFile`, `DownloadFile`, `DownloadXmlParametric`, `ExtractZipFirstEntry`, `GetBmpBytes`, `GetEncoder`

События:
- `Connected`: `DConnected`
- `OnObjectNameChanged`: `ObjectNameChangedEventHandler`
- `OnRefresh`: `OnRefreshMethod`
Свойства:
- `Dbcp: CSAppServices.DbConnectParameters`
- `LibDirectory: string`
- `Is3DLibrary: bool`
- `IsConnected: bool`
- `Connection: LightweightDataAccess.DbConnectionInfo`
- `Transaction: LightweightDataAccess.DbTransactionInfo`
- `UserDisplayName: string`
- `CurrentUser: int32`
- `UserPermissions: bool[]`
- `IsCurrentUserAdministrator: bool`
- `IsCurrentUserInfoSec: bool`
- `ServerSpecificScriptsDir: System.IO.DirectoryInfo`
- `DatabaseDesc: string`
- `IsConnecting: bool`
- `CurrentDbContext: LightweightDataAccess.DbContext`
- `MiscCategoryId: int32`
- `StructureDataCategoryId: int32`
- `ObjectDataFileCategoryId: int32`
- `StructureDataGroupParamId: int32`
- `IsImporting: bool`
Методы:
- `IsInPredicate(bool(FLib.Str))`
- `IsInNotPredicate(bool(FLib.Str))`
- `IsExistsPredicate(bool(FLib.Str))`
- `IsNotExistsPredicate(bool(FLib.Str))`
- `IsExistencePredicate(bool(FLib.Str))`
- `Command(LightweightDataAccess.DbCommandInfo(string))`
- `AdaptedCommand(LightweightDataAccess.DbCommandInfo(string))`
- `Command(LightweightDataAccess.DbCommandInfo(string, ET_15))`
- `ExecuteDbCommand(void(string, bool, object[]))`
- `CreateDbCommand(LightweightDataAccess.DbCommandInfo(string, bool, object[]))`
- `CreateDbCommand(LightweightDataAccess.DbCommandInfo(LightweightDataAccess.DbConnectionInfo, System.Data.Common.DbTransaction, string, object[]))`
- `SP(object(int32))`
- `SPOut(object(int32))`
- `SP(object(ET_15, System.Func`2))`
- `FromTableParams(TypedReference(ET_00, ET_15))`
- `WithTableParams(void(System.Action, LightweightDataAccess.TableParam[]))`
- `WithTableParams(ET_15(List`1, void, TypedReference))`
- `RefreshUserPermissions(void())`
- `createConnection(void(bool))`
- `CreateNativeConnection(LightweightDataAccess.DbConnectionInfo())`
- `GetNotUsedFileName(string(string))`
- `mConnection_StateChange(void(object, System.Data.StateChangeEventArgs))`
- `GetFileName(string(int32))`
- `IsValidFile(bool(int32))`
- `GetFileIconId(int64(int32))`
- `GetFileObjects(ET_15(List`1, void))`
- `GetScriptsDir(string())`
- `GetFileCacheDir(string())`
- `BeginTransaction(void())`
- `BeginTransaction(void(System.Data.IsolationLevel))`
- … ещё 856 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CADLib.CADLibrary`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLib.CADLibrary` → `CADLibKernel.CADLibraryBase`
- Практический смысл: UI-наследник `CADLibraryBase`: добавляет работу с папками, деревьями, изображениями, скриптами, удалением/импортом объектов и плагинами папок.
- Статические методы: `AskForExportReport`, `ContainsNotEmptyString`, `ExploreFile`, `GetAppFolder`, `GetDirectory`, `GetFileDirectory`, `GetTempFolder`, `InitializeCSViewModels`, `MakeAppVersionInfo`, `RequestImportOptions`, `SetRowData`, `createImageList`

События:
- `BeforeDeleteObjects`: `BeforeDeleteObjectsEventHandler`
- `AfterDeleteObjects`: `AfterDeleteObjectsEventHandler`
- `AfterImportObjects`: `AfterImportObjectsEventHandler`
Свойства:
- `IsDocs: bool`
- `CalcNameOnDemand: bool`
- `AppVersion: string`
- `ExceptionMode: eExceptionMode`
- `ProgressWindow: CADLib.ProgressForm`
- `SmallImages: WinForms.ImageList`
- `LargeImages: WinForms.ImageList`
- `ScriptsDirectory: string`
- `CollisionCatId: int32`
- `FolderPlugins: ET_15` — Возвращает коллекцию плагинов каталогов
- `RootFilterWhere: string`
- `Rootfilters: ET_15` — Возвращает примененные корневые фильтры библиотеки
- `IsDBCreating: bool`
- `UserPermissions: bool[]`
- `IsAccessible: bool`
Методы:
- `MakeAppVersionInfo(string(string, string))`
- `InitializeCSViewModels(void())`
- `DeleteObjects(ET_15(List`1))`
- `DeleteObject(void(CLibObjectInfo))`
- `CADLibrary_OnRefresh(void(UpdatedSet))`
- `createImageList(WinForms.ImageList(int32))`
- `GetScriptsDir(string())`
- `GetFileCacheDir(string())`
- `SubRefresh(void())`
- `AddObjectNode(WinForms.TreeNode(WinForms.TreeView, WinForms.TreeNodeCollection, CLibObjectInfo, bool, bool, int32))`
- `FindNodeByNodesCollection(WinForms.TreeNode(WinForms.TreeNode, WinForms.TreeNodeCollection))`
- `FindNodeByNodesCollection(WinForms.TreeNode(WinForms.TreeView, WinForms.TreeNodeCollection))`
- `AddBaseObjectInfo(CLibObjectInfo(ET_15, List`1, void, ET_15))`
- `AddCustomObjectNode(CLibObjectInfo(WinForms.TreeView, WinForms.TreeNodeCollection, CLibObjectInfo, bool, bool, int32, bool, int32))`
- `AddObjectNode(CLibObjectInfo(WinForms.TreeView, WinForms.TreeNodeCollection, CLibObjectInfo, bool, int32, bool))`
- `AddObjectNode(CLibObjectInfo(WinForms.TreeView, WinForms.TreeNodeCollection, System.Data.IDataRecord, bool, int32, bool, CLibCatalogFilterItem))`
- `AddFileNode(WinForms.TreeNode(WinForms.TreeNodeCollection, CLibFileInfo, bool, bool))`
- `AddFileNode(void(WinForms.TreeNodeCollection, System.Data.Common.DbDataReader, bool, int32, bool))`
- `ExpandNode(void(WinForms.TreeNode))`
- `ExpandFileNode(void(WinForms.TreeNode, CLibFileInfo))`
- `ShowConnectDialog(CSAppServices.DbConnectParameters())`
- `GetSubObjects(CLibObjectInfo[](CLibObjectInfo))`
- `ExpandObjectNode(void(WinForms.TreeNode, CLibObjectInfo))`
- `ExpandFolderNode(void(WinForms.TreeView, WinForms.TreeNode, bool, bool, bool))`
- `ExpandFolderNode(void(WinForms.TreeView, WinForms.TreeNode))`
- `ExpandHierListClassifier(void(WinForms.TreeView, WinForms.TreeNode, HierListClassifier))`
- `ExpandClassifier(void(WinForms.TreeView, WinForms.TreeNode, CLibClassifierFilterItem))` — Раскрывает классификатор, извлекая подчинённые узлы (см. дерево каталогов - классификаторы)
- `ExpandClassifier(ET_15(List`1, void))` — Раскрывает классификатор, извлекая подчинённые узлы (см. дерево каталогов - классификаторы)
- `ExpandSubfolders(void(WinForms.TreeView, WinForms.TreeNode, CLibCatalogFilterItem, bool))`
- `doExpandFolder(void(object, WinForms.TreeView, WinForms.TreeNode, CLibCatalogFilterItem, bool))`
- … ещё 363 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CSProject3D.CAD3DLibrary`

- DLL: `CSProject3D.dll`
- Тип: `class`
- Наследование: `CSProject3D.CAD3DLibrary` → `CADLib.CADLibrary`
- XML-описание: Класс базы данных приложений CADLib, работающих с трёхмерной графикой объектов
- Практический смысл: 3D-наследник `CADLibrary`: выбор объектов в 3D, текущие виды, 3D-сессия, 3D-графика, mesh/shape, публикации.
- Статические методы: `CreateLibObjectFromUnmanaged`, `IsSelectionFolder`

События:
- `OnSelectionChanged`: `EventHandlerSelectionChanged`
Свойства:
- `CurrentSession: int32`
- `IsEmptySelection: bool`
- `SingleSelectedObjectId: int32`
- `SelectedObjects: ET_15`
- `IsSingleSelection: bool`
- `SelectedObjectsCount: int32`
- `bObjectJustPicked: bool` — true while in on axNWEViewerCtl1_OnObjectPicked methos
- `CurrentViewNode: WinForms.TreeNode`
- `Is3DLibrary: bool`
- `IsCurrentViewAllObjects: bool` — Показывает ли узел текущий вид все корневые объекты
- `UserTaggingNode: WinForms.TreeNode`
Методы:
- `onConnect(void())`
- `IsObjectSelected(bool(int32))`
- `IsSelectionSupersetOf(bool(ET_15))`
- `AnyObjectInSelection(bool(ET_15))`
- `RaiseOnSelChanged(void())`
- `InitSelFilterTable(bool())`
- `SetMultiselectionFilter(void())`
- `ResetSelection(bool())`
- `IsObjectSelectedTwice(bool(int32))`
- `AppendObjectToSelection(bool(int32))` — Add object to library 3D selection set
- `AppendObjectsToSelection(bool(ET_15))` — Add objects to library selection set
- `SetSelectedObjects(bool(ET_15))` — Set library selected objects to set
- `SelectObjectsWithSameGraphicsAsSelected(int32())` — Выделяет объекты, имеющие то же графическое представление, что и выбранные объекты Если у объекта несколько сеток, ты выбираются объекты, имеющие тот же набор сеток без учёта взаиморасположения
- `ApplyGraphicsToObjects(int32(int32, ET_15, IEnumerable`1))`
- `DoAppendObjectToSelection(bool(int32, bool))` — Add Object to selection
- `DoAppendObjectsToSelection(bool(ET_15))` — Smart appending objects and event raising
- `SetEmptySelection(bool())` — Clear selection
- `SetSingleSelection(bool(int32))` — Set selection to only one object
- `SetSingleSelectionFile(bool(int32))`
- `Connect3D(bool(AxInterop.CSAx3DViewerLib.AxCSAx3DViewer))`
- `Connect3D(bool(AxInterop.NWEViewerCompon<wbr>entLib.AxNWEViewerCtl))`
- `IsSelectionFolder(bool(CADLib.DbSettingsItem))`
- `GetCurrentViewNode(WinForms.TreeNode())`
- `GetCurrentViewObjects(ET_15())` — Возвращает идентификаторы объектов текущего вида Количество объектов может быть больше, чем количество объектов в фильтре "Текущий вид" т.к. в результат включены объекты текущего вида плагинов
- `CreateLibObjectFromUnmanaged(CLibObjectInfo(mstManagedAPI.LibObjectInfo))` — Преобразует неуправляемый объект библиотеки в управляемый
- `GetCurrentViewFilter(string(bool))`
- `GetFolderImageId(FLib.Str(CLibCatalogFilterItem))`
- `ShowRootFolders(void(WinForms.TreeView, WinForms.TreeNodeCollection, bool, bool, bool, bool))`
- `GetDirectoryPropertiesCaption(string(bool, int32))`
- `ShowViewFolders(void(CLibCatalogFilterItem, WinForms.TreeView, WinForms.TreeNodeCollection))`
- `DoShowFilterSource(void(string, string, string, int32, FilterGrid))`
- `ShowFilterSource(void(int32, bool, FilterGrid))`
- `SetCurrentViewContent(void(ET_15))`
- `SetCurrentViewContent(void(CADLib.DbSettingsItem))`
- `SwitchToUserDirectoryView(void())`
- `SetUserViewFilter(void(string))`
- `AddToCurrentViewContent(void(CADLib.DbSettingsItem))`
- `AppendUserViewFilter(void(string))`
- `IsUserView(bool(WinForms.TreeNode))`
- `UpdateCurrentViewNode(void())`
- … ещё 46 методов. В полном справочнике сигнатур они перечислены отдельно.

Цепочка наследования по ключевому контуру:

```text
System.Object
└─ CADLibKernel.CADLibraryBase
   └─ CADLib.CADLibrary
      └─ CSProject3D.CAD3DLibrary
```

## 7. 3D-просмотрщик и события выбора

### `CSProject3D.Viewer3DCtrl`

- DLL: `CSProject3D.dll`
- Тип: `class`
- Наследование: `CSProject3D.Viewer3DCtrl` → `System.Windows.Forms.UserControl`
- XML-описание: Компонент просмотра трёхмерной графики из базы данных
- Практический смысл: WinForms-компонент просмотра 3D-графики из БД. Содержит события выбора объектов/сущностей, загрузки 3D, контекстного меню, работы с поверхностями, заметками, измерениями и камерой.
- Статические методы: `GetKeyState`, `InputBox`, `SendMessage`

События:
- `OnObjectPicked`: `EventHandlerObject`
- `OnEntityPicked`: `EventHandlerEntity`
- `OnLandPicked`: `EventHandlerObject`
- `OnLandsHide`: `EventHandlerLands`
- `OnSelectCollision`: `EventHandlerCollisions`
- `PopupMenuOpening`: `EventHandlerPopupOpening`
- `On3DLoad`: `EventHandler3DLoad`
- `On3DPreLoad`: `EventHandler3DLoad`
- `On3DFatalError`: `System.EventHandler`
- `On3DInitialized`: `System.EventHandler`
- `OnContextMenuDown3D`: `System.EventHandler`
- `OnEntityClosedClick`: `EventHandlerEntity`
- `OnEntityInfoClick`: `EventHandlerEntity`
- `OnHotShapeChanged`: `EventHotShapeChanged`
- `OnSelectWithFrame`: `SelectWithFrame`
- `OnRequestEdit2dDrawing`: `TypeSpec`
Свойства:
- `PopupMenu: WinForms.ContextMenuStrip`
- `ContextMenuLastObject: CLibObjectInfo` — Объект БД (может быть кастомный) на котором было последний раз активированно контекстное меню
- `ContextMenuLastEntity: EntityPointer` — Сущность на которой последней раз было активированно контекстное меню
- `OnHyperlinkClicked: ET_15`
- `m_taggingCollection: UserTagging.UserTaggingCollection`
- `multiuserUI: CADLib.Dialogs.MultiuserForm` — Возвращает (если надо создаёт) окно многопользовательской работы
- `ShowAvatar: bool`
- `EnableGravity: bool`
- `AvatarCollisionCheck: bool`
- `EnableToolTip: bool`
- `Is3DInitialized: bool`
- `Library: CAD3DLibrary`
- `ShowViewerFormAction: System.Action`
- `CollisionCatId: int32`
- `IgnoreSelectionUpdate: bool`
- `HotObjectId: int32`
- `HotEntityId: EntityPointer`
- `LoadedFilter: string`
- `DontResetCorrections: bool`
- `Ax3DViewerVisible: bool`
- … ещё 6 свойств.
Методы:
- `SetVisibleLandSurfaces(void(int32[]))` — Устанавливает набор видимых поверхностей Загружает недостающие поверхности и удаляет пропавшие из списка видимости
- `SetSelectedLandSurfaces(void(int32[]))` — Устанавливает набор выделенных поверхностей Снимает выделение со всех остальных поверхностей
- `FocusOnLandSurfaces(void(int32[]))` — Фокусирует камеру на загруженных поверхностях земли из списка
- `toolStripMIInsertFromClipboard_Click(void(object, System.EventArgs))`
- `WndProc(void(WinForms.Message*))`
- `toolStripMIInsertSelectedObjLink_Click(void(object, System.EventArgs))`
- `AppendChatMessage(int32(string, int32))`
- `OnMessageSendEMailEvent(void(string, string, string))`
- `GetEMailServerParams(bool(string*, int32*, bool*, string*, string*, string*))`
- `TakeScreenshotForChat(void(string))`
- `UpdateChatMessages(int32(int32, ET_15))`
- `UpdateUsersList(bool(WinForms.ListView))`
- `GetCurrentUser(int32())`
- `mLibrary_AfterDeleteObjects(void(CADLibraryBase, int32[]))`
- `ShowViewer(void())`
- `SetUserTaggingCollection(void(UserTagging.UserTaggingCollection))`
- `Application_Idle(void(object, System.EventArgs))`
- `Parent_Enter(void(object, System.EventArgs))`
- `LoadLocalizetionFile(void(string, string))`
- `ForbidIfNotInitialized(bool())` — Проверяет инициализирован ли трёхмерный движок и выдайт сообщение если нет
- `axNWEViewerCtl1_OnObjectPicked(void(object, AxInterop.CSAx3DViewerLib<wbr>._ICSAx3DViewerEvents_OnO<wbr>bjectPickedEvent))`
- `AddSpecialSelectedShapes(void(ET_15, IEnumerable`1, void, int32))`
- `SetWorldUnselectedDecoration(void(ET_15, System.Nullable`1))` — Изменяет остальной мир на время выделения. Если указать A составляющую=0, то мир прорисовываться не будет (скрыть)
- `ReCalculateObjectParameters(void(int32))`
- `ax3DViewer_OnContextMenuUp(void(object, System.EventArgs))`
- `ax3DViewer_OnContextMenuDown(void(object, System.EventArgs))`
- `ax3DViewer_OnHelperViewTypeMenu(void(object, AxInterop.CSAx3DViewerLib<wbr>._ICSAx3DViewerEvents_OnH<wbr>elperViewTypeMenuEvent))`
- `ax3DViewer_OnAnnotationCreated(void(object, System.EventArgs))`
- `ax3DViewer_OnHelperVisualStyleMenu(void(object, System.EventArgs))`
- `ApplyUserTagging(void(UserTagging.Entities.UserTaggingBase))`
- `SetFirstPersonCamera(void())`
- `SetOrbitCamera(void())`
- `SuspendCameraChanges(void())`
- `SupressAutoOrbitForOperation(void())`
- `CommitCameraChanges(void())`
- … ещё 218 методов. В полном справочнике сигнатур они перечислены отдельно.

Для задач автоматизации важно различать:

- `CAD3DLibrary` — состояние 3D-библиотеки и выборки объектов;
- `Viewer3DCtrl` — визуальный компонент и события взаимодействия пользователя с 3D-окном;
- `IDatabaseBrowser` / `DBBrowser` — дерево/каталог/активный объект/выбор в интерфейсе БД.

## 8. Объекты, параметры, фильтры

### `CADLibKernel.CLibObjectInfo`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibObjectInfo` → `System.Object`
- Практический смысл: карточка объекта CADLib; используется в выборках, копировании, параметрах, активном объекте
- Статические методы: `StatusToString`, `op_Equality`, `op_Explicit`, `op_Implicit`, `op_Inequality`

Свойства:
- `Name: string`
- `StatusName: string`
- `IsRoot: bool`
- `LocalModifiedDate: System.DateTime`
Методы:
- `StatusToString(string(int32))`
- `GetHashCode(int32())`
- `Equals(bool(object))`
- `op_Equality(bool(CLibObjectInfo, CLibObjectInfo))`
- `op_Inequality(bool(CLibObjectInfo, CLibObjectInfo))`
- `op_Implicit(Models.ParametersDto(CLibObjectInfo))`
- `op_Explicit(CLibObjectInfo(Models.ParametersDto))`
- `ReloadData(void(System.Data.IDataRecord))`
- `ToString(string())`
- `Clone(CLibObjectInfo())`

### `CADLibKernel.CLibParamDefInfo`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibParamDefInfo` → `System.Object`
- Практический смысл: описание параметра: имя, заголовок, тип, категории; используется при создании новых параметров
- Статические методы: `AddParamDef`, `AddParamDefIfNotExists`, `MakeCorrectName`

Методы:
- `Equals(bool(object))`
- `MakeCorrectName(bool(string*))`
- `ToString(string())`
- `GetHashCode(int32())`
- `IsEqual(bool(CLibParamDefInfo))`
- `UpdateExtendedData(void(CADLibraryBase))`
- `AddParamDefIfNotExists(bool(ET_15, List`1, void, CLibParamDefInfo, string, string))`
- `AddParamDef(void(ET_15, List`1, void, CLibParamDefInfo, string, string))`

### `CADLibKernel.CLibParamCategoryInfo`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibParamCategoryInfo` → `System.Object`
- Практический смысл: категория параметров; нужна для группировки параметров в интерфейсе


### `CADLibKernel.CLibFilterItem`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibFilterItem` → `System.Object`
- Практический смысл: условие фильтра: параметр, оператор, значение; используется в `CreateFilter`
- Статические методы: `hasTimeComponent`

Методы:
- `GetHashCode(int32())`
- `Equals(bool(object))`
- `ToString(string())`
- `GetDateFilterExpression(string(LightweightDataAccess.EServerType, string, string))`
- `hasTimeComponent(ET_15(System.Nullable`1))`
- `UpdateObjectCondition(string(CLibFilterItem, string))`

### `CADLibKernel.CLibCatalogFilterItem`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibCatalogFilterItem` → `System.Object`
- Практический смысл: узел/папка каталога или выборки
- Статические методы: `GetFilterFolder`, `GetQueryForRelationType`

Свойства:
- `Parent: CLibCatalogFilterItem`
- `UseParentFilter: eUseParentFilter`
- `CoreFilter: string`
- `CoreParentFilter: string`
- `ResultSetType: EResultSetType`
- `IsRecursive: bool`
- `IsAllObjectsFolder: bool`
- `IsSearchFolder: bool`
- `IsStructureObjectsFolder: bool`
- `IsBuildingsHierarchyFolder: bool`
- `IsStructureHierarchyFolder: bool`
- `IsLinkedObjectParam: IsLinkedObjectParam`
- `PreferredFilterExpression: E`
- `IsCoreFilterEmpty: bool`
- `FullFilter: string`
- `FullFilterInfo: ET_15`
- `IsFileDir: bool`
- `FolderType: FolderType`
- `IsExpandable: bool`
Методы:
- `UpdateFilter(void(CADLibraryBase))`
- `GetQueryForRelationType(string(string))`
- `GetParamSetObjectList(ET_15())`
- `IsFilterEmpty(bool(string))`
- `GetFullFilter(string(E))`
- `GetPathParameters(object[]())`
- `GetPathValues(ET_15(IEnumerable`1))`
- `GetFolderType(FolderType())`
- `IsItemExpandable(bool())`
- `GetHashCode(int32())`
- `Equals(bool(object))`
- `IsSameFolder(bool(ET_15, System.Nullable`1))`
- `ContainsObjectCategoryFilter(bool(int32))`
- `GetSubfolders(void(CADLibraryBase, bool, ET_15))`
- `GetSubfolder(CLibCatalogFilterItem(FLib.Str, System.Data.IDataRecord, bool, int32))`
- `GetFilterFolder(CLibCatalogFilterItem(CADLibraryBase, string, bool, int32))`
- `GetFilterFolder(CLibCatalogFilterItem(CLibCatalogFilterItem, CADLibraryBase, string, bool, int32))`
- `GetBlockFolderEditMenu(bool())`
- `<get_FullFilterInfo>b__63_0(bool(FilterInfo))`

### `CADLibKernel.CLibClassifierFilterItem`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibClassifierFilterItem` → `CADLibKernel.CLibCatalogFilterItem`
- Практический смысл: узел классификатора
- Статические методы: `GetParent`

Свойства:
- `ParentClassifier: CLibClassifierFilterItem`
- `PreferredFilterExpression: E`
- `IsParamCoreFilterEmpty: bool`
- `FullFilter: string`
- `IsLinkedObjectParam: IsLinkedObjectParam`
- `FullFilterInfo: ET_15`
Методы:
- `GetParent(ET_15(FLib.Option`1))`
- `GetFullFilter(string(E))`
- `FullParamFilter(string(E))`
- `GetParamTableAlias(ET_15(FLib.Option`1))`
- `GetFolderType(FolderType())`
- `GetPathValues(ET_15(IEnumerable`1))`
- `Equals(bool(object))`
- `GetHashCode(int32())`
- `<get_FullFilterInfo>b__22_0(bool(FilterInfo))`

### `CADLibKernel.CLibFileInfo`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibFileInfo` → `System.Object`
- Практический смысл: информация о файле объекта/документа

Свойства:
- `CheckedFileName: string`
- `LocalModifiedDate: System.DateTime`
Методы:
- `ToString(string())`

### `CADLibKernel.CLibClassifier`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CLibClassifier` → `System.Object`
- Практический смысл: описание классификатора
- Статические методы: `RemoveNullClassifierValue`, `add`

Свойства:
- `Item: CLibParamDef[int32]`
- `Fields: ET_15`
- `IsFileMode: bool`
- `Name: string`
- `ClassifierId: int32`
- `MaxLevel: int32`
- `HasLinkedObjectParams: IsLinkedObjectParam`
Методы:
- `RemoveNullClassifierValue(ET_15(IEnumerable`1))`
- `ReloadFields(void(CADLibraryBase))`
- `add(void(string, ET_15, List`1, void))`
- `GetFilter(int32(ET_15, List`1, void, object, System.Text.StringBuilder, ET_15, List`1, void))`
- `makeValueCondition(string(string, string, string, bool, int32))`
- `makeValueCondition(string(string, string, int32, string, bool, int32))`
- `GetFilter(FilterInfoPair(ET_15, List`1, void, object))`
- `GetFilter(FilterInfo(ET_15, List`1, void, object, int32))`
- `GetLevelQuery(string(ET_15, List`1))`
- `GetFilterOthers(FilterInfoPair(ET_15, List`1, void))`
- `GetFilterOthers(FilterInfo(ET_15, List`1, void, object))`

Минимальная рабочая модель API, подтвержденная скриптом:

```python
conditions = List[CLibFilterItem]()
nIdPartName = Library.GetParamDefId("PART_TYPE")
conditions.Add(CLibFilterItem(nIdPartName, "=", "Стена"))
filter = Library.CreateFilter(conditions)
objects = Library.GetObjectsList(filter)
```

## 9. Service / singleton-like классы

В метаданных DLL не всегда можно доказать singleton-паттерн без анализа кода, но можно выделить классы, которые по назначению и имени являются сервисными точками. Для них в справочнике ставится статус “service-like”, а не “строго singleton”.

### `CADLibCommonUIPlugin.vmFolderManager`
- DLL: `CADLibControls.dll`
- Наследование: `CADLibCommonUIPlugin.vmFolderManager` → `CADLib.vmLibrary`

### `CADLibCommonUIPlugin.vmObjectManager`
- DLL: `CADLibControls.dll`
- Наследование: `CADLibCommonUIPlugin.vmObjectManager` → `CADLib.vmLibrary`

### `ViewModels.DataExchangeReportViewModel`
- DLL: `CADLibControls.dll`
- Наследование: `ViewModels.DataExchangeReportViewModel` → `NApp.ViewModel`

### `ObjectTemplates.ObjectTemplateManager`
- DLL: `CADLibControls.dll`
- Наследование: `ObjectTemplates.ObjectTemplateManager` → `System.Object`
- Признаки: static methods: LoadTemplate

### `CADLibControls.Data.DataExchangeDataSet`
- DLL: `CADLibControls.dll`
- Наследование: `CADLibControls.Data.DataExchangeDataSet` → `System.Data.DataSet`
- Описание: Represents a strongly typed in-memory cache of data.
- Признаки: static methods: GetTypedDataSetSchema

### `CADLibControls.ViewModels.vmDataExchange`
- DLL: `CADLibControls.dll`
- Наследование: `CADLibControls.ViewModels.vmDataExchange` → `CADLib.vmLibrary`

### `CADLibControls.Forms.DataExchangeReportForm`
- DLL: `CADLibControls.dll`
- Наследование: `CADLibControls.Forms.DataExchangeReportForm` → `NApp.WinForms.AppForm`

### `CADLibControls.Forms.Mana<wbr>geRecentDatabaseList`
- DLL: `CADLibControls.dll`
- Наследование: `CADLibControls.Forms.Mana<wbr>geRecentDatabaseList` → `NApp.WinForms.AppForm`

### `CADLibControls.Dialogs.Me<wbr>asurementsManagerDlg`
- DLL: `CADLibControls.dll`
- Наследование: `CADLibControls.Dialogs.Me<wbr>asurementsManagerDlg` → `System.Windows.Forms.Form`

### `CADLib.AppLoadBuild`
- DLL: `CADLibControls.dll`
- Наследование: `CADLib.AppLoadBuild` → `NBuild.Build`

### `CADLib.FormsManager`
- DLL: `CADLibControls.dll`
- Наследование: `CADLib.FormsManager` → `System.Windows.Forms.Form`

### `CADLib.PluginsManager`
- DLL: `CADLibControls.dll`
- Наследование: `CADLib.PluginsManager` → `System.Object`
- Описание: Класс для управления плагинами
- Признаки: static methods: AreMenuItemsEqual, FindMenuItem, MergeInterfaceMenus, MergeInterfaceToolbars, ScanAndAddMenu

### `CADLib.Forms.DataExchangeForm`
- DLL: `CADLibControls.dll`
- Наследование: `CADLib.Forms.DataExchangeForm` → `System.Windows.Forms.Form`

### `DataExchangeTableRowChangeEventHandler`
- DLL: `CADLibControls.dll`
- Наследование: `DataExchangeTableRowChangeEventHandler` → `System.MulticastDelegate`

### `DataExchangeTableDataTable`
- DLL: `CADLibControls.dll`
- Наследование: `DataExchangeTableDataTable` → `TypeSpec`
- Признаки: static methods: GetTypedTableSchema

### `DataExchangeTableRow`
- DLL: `CADLibControls.dll`
- Наследование: `DataExchangeTableRow` → `System.Data.DataRow`

### `DataExchangeTableRowChangeEvent`
- DLL: `CADLibControls.dll`
- Наследование: `DataExchangeTableRowChangeEvent` → `System.EventArgs`

### `TreeController`
- DLL: `CADLibControls.dll`
- Наследование: `TreeController` → `System.Object`

### `CustomComponentResourceManager`
- DLL: `CADLibControls.dll`
- Наследование: `CustomComponentResourceManager` → `System.ComponentModel.Com<wbr>ponentResourceManager`

### `SCHEMA__managerecentdatabaselist`
- DLL: `CADLibControls.dll`
- Наследование: `SCHEMA__managerecentdatabaselist` → `CoSql.Runtime.SchemaBase`

### `WorksLib2.WorksLib2Controller`
- DLL: `CSProject3D.dll`
- Наследование: `WorksLib2.WorksLib2Controller` → `System.Object`

### `CSProject3D.BuildingHierarchyLinksCollisions`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.BuildingHierarchyLinksCollisions` → `System.Windows.Forms.Form`

### `CSProject3D.EBuildingBranch`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.EBuildingBranch` → `System.Enum`

### `CSProject3D.CBuildingHierarchyLevelInfo`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.CBuildingHierarchyLevelInfo` → `System.Object`

### `CSProject3D.CAxisPipeManager`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.CAxisPipeManager` → `CADLibControls.FolderPlugin`

### `CSProject3D.CLPPublicationsManager`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.CLPPublicationsManager` → `CADLibControls.FolderPlugin`
- Признаки: static methods: GetPublicationFolder

### `CSProject3D.GridManager`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.GridManager` → `CADLibControls.FolderPlugin`
- Описание: Класс плагина менеджера координатных сеток: Создаёт (оборачивает) выборку координатных сеток с именем GridsFolderName Позволяет управлять видимостью координатных сеток и ограничивать по ним пространство +Добавляет пункт меню "Ограничить пространство" в контекстное меню 3D при клике по сетке
- Признаки: static methods: GetGridsFolder

### `CSProject3D.CLayerManager`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.CLayerManager` → `CADLibControls.FolderPlugin`

### `CSProject3D.BuildingsHierarchyPlugin`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.BuildingsHierarchyPlugin` → `CADLibControls.FolderPlugin`
- Признаки: static methods: GetHierarchyFolder, GetKeyState, PostMessage

### `CSProject3D.LayoutManager`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.LayoutManager` → `CADLibControls.FolderPlugin`
- Признаки: static methods: GetLayoutsFolder

### `CSProject3D.CADLibPluginEntryPoint`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.CADLibPluginEntryPoint` → `System.Object`
- Признаки: static methods: RegisterPlugin

### `CSProject3D.SurfaceManager`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.SurfaceManager` → `CADLibControls.FolderPlugin`
- Признаки: static methods: GetSurfacesFolder, LandSurfaceXPGImport

### `CSProject3D.UserTagging.U<wbr>serTaggingController`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.UserTagging.U<wbr>serTaggingController` → `System.Object`
- Признаки: static methods: GetRoot, GetUnboundRoot

### `CSProject3D.Scenario.CamScriptTreeController`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Scenario.CamScriptTreeController` → `System.Object`
- Признаки: static methods: AddSubItem

### `CSProject3D.Works.CBuildingHierarchyNode`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Works.CBuildingHierarchyNode` → `System.Object`

### `CSProject3D.Forms.ListPro<wbr>ject.BuildingHierarchyLev<wbr>elSelector`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Forms.ListPro<wbr>ject.BuildingHierarchyLev<wbr>elSelector` → `System.Windows.Forms.Form`

### `CSProject3D.Forms.ListPro<wbr>ject.PropertyBuildingFiel<wbr>d`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Forms.ListPro<wbr>ject.PropertyBuildingFiel<wbr>d` → `System.Object`

### `CSProject3D.Forms.ListPro<wbr>ject.PropertyGroupBuildin<wbr>gsField`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Forms.ListPro<wbr>ject.PropertyGroupBuildin<wbr>gsField` → `System.Object`

### `CSProject3D.Forms.ListPro<wbr>ject.PropertyBuildingBloc<wbr>kField`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Forms.ListPro<wbr>ject.PropertyBuildingBloc<wbr>kField` → `System.Object`

### `CSProject3D.Forms.ListPro<wbr>ject.PropertyMultiSection<wbr>BuildingField`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Forms.ListPro<wbr>ject.PropertyMultiSection<wbr>BuildingField` → `System.Object`

### `CSProject3D.Forms.ListPro<wbr>ject.PropertyBuildingSect<wbr>ionField`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Forms.ListPro<wbr>ject.PropertyBuildingSect<wbr>ionField` → `System.Object`

### `CSProject3D.Forms.ListPro<wbr>ject.PropertyServicesFiel<wbr>d`
- DLL: `CSProject3D.dll`
- Наследование: `CSProject3D.Forms.ListPro<wbr>ject.PropertyServicesFiel<wbr>d` → `System.Object`

### `CBuildingsHierachyFolder`
- DLL: `CSProject3D.dll`
- Наследование: `CBuildingsHierachyFolder` → `CCustomFilterItem`

### `TreeController`
- DLL: `CSProject3D.dll`
- Наследование: `TreeController` → `System.Object`

### `CustomComponentResourceManager`
- DLL: `CSProject3D.dll`
- Наследование: `CustomComponentResourceManager` → `System.ComponentModel.Com<wbr>ponentResourceManager`

### `X_building_number`
- DLL: `CSProject3D.dll`
- Наследование: `X_building_number` → `TypeSpec`
- Признаки: static methods: op_Implicit

### `CADLibKernel.ObjectUpdate<wbr>.ObjectUpdateService`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>.ObjectUpdateService` → `System.Web.Services.Proto<wbr>cols.SoapHttpClientProtoc<wbr>ol`

### `CADLibKernel.ObjectUpdate<wbr>.GetServiceVersionComplet<wbr>edEventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>.GetServiceVersionComplet<wbr>edEventHandler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>.GetServiceVersionComplet<wbr>edEventArgs`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>.GetServiceVersionComplet<wbr>edEventArgs` → `System.ComponentModel.Asy<wbr>ncCompletedEventArgs`

### `CADLibKernel.ObjectUpdate<wbr>Router.RouterService`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.RouterService` → `System.Web.Services.Proto<wbr>cols.SoapHttpClientProtoc<wbr>ol`

### `CADLibKernel.ObjectUpdate<wbr>Router.Authentication`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.Authentication` → `System.Web.Services.Protocols.SoapHeader`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetCatalogsAvailab<wbr>leToAuthenticatedUserComp<wbr>letedEventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetCatalogsAvailab<wbr>leToAuthenticatedUserComp<wbr>letedEventHandler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetCatalogsAvailab<wbr>leToAuthenticatedUserComp<wbr>letedEventArgs`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetCatalogsAvailab<wbr>leToAuthenticatedUserComp<wbr>letedEventArgs` → `System.ComponentModel.Asy<wbr>ncCompletedEventArgs`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesOfAuthenti<wbr>catedUserCompletedEventHa<wbr>ndler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesOfAuthenti<wbr>catedUserCompletedEventHa<wbr>ndler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesOfAuthenti<wbr>catedUserCompletedEventAr<wbr>gs`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesOfAuthenti<wbr>catedUserCompletedEventAr<wbr>gs` → `System.ComponentModel.Asy<wbr>ncCompletedEventArgs`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesCompletedE<wbr>ventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesCompletedE<wbr>ventHandler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesCompletedE<wbr>ventArgs`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesCompletedE<wbr>ventArgs` → `System.ComponentModel.Asy<wbr>ncCompletedEventArgs`

### `CADLibKernel.ObjectUpdate<wbr>Router.CreateRolesComplet<wbr>edEventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.CreateRolesComplet<wbr>edEventHandler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetUsersCompletedE<wbr>ventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetUsersCompletedE<wbr>ventHandler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>Router.GetUsersCompletedE<wbr>ventArgs`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.GetUsersCompletedE<wbr>ventArgs` → `System.ComponentModel.Asy<wbr>ncCompletedEventArgs`

### `CADLibKernel.ObjectUpdate<wbr>Router.CreateUsersComplet<wbr>edEventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.CreateUsersComplet<wbr>edEventHandler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>Router.UpdateUsersComplet<wbr>edEventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.UpdateUsersComplet<wbr>edEventHandler` → `System.MulticastDelegate`

### `CADLibKernel.ObjectUpdate<wbr>Router.DeleteUsersComplet<wbr>edEventHandler`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.ObjectUpdate<wbr>Router.DeleteUsersComplet<wbr>edEventHandler` → `System.MulticastDelegate`

### `CADLibKernel.DataExchangeUnit.eCsvImportMode`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchangeUnit.eCsvImportMode` → `System.Enum`

### `CADLibKernel.DataExchangeUnit.eHeaderLine`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchangeUnit.eHeaderLine` → `System.Enum`

### `CADLibKernel.DataExchangeUnit.DGetParamRefs`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchangeUnit.DGetParamRefs` → `System.MulticastDelegate`

### `CADLibKernel.DataExchange<wbr>Unit.DEvaluateFormula`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchange<wbr>Unit.DEvaluateFormula` → `System.MulticastDelegate`

### `CADLibKernel.DataExchangeUnit.CsvImport`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchangeUnit.CsvImport` → `System.Object`
- Признаки: static-like; static methods: ImportCsv, IsNodePath

### `CADLibKernel.DataExchangeUnit.CsvImportBuild`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchangeUnit.CsvImportBuild` → `NBuild.Build`
- Признаки: static methods: dump_table, normFileName

### `CADLibKernel.DataExchange<wbr>Unit.ParamDefsXmlImport`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchange<wbr>Unit.ParamDefsXmlImport` → `System.Object`
- Признаки: static methods: ExportParameters, ImportParameters, parseFloat

### `CADLibKernel.DataExchange<wbr>Unit.UserRegistryExchange`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchange<wbr>Unit.UserRegistryExchange` → `System.Object`
- Признаки: static methods: Export, Import, ImportCsv, postImport, resolveConflicts

### `CADLibKernel.DataExchange<wbr>Unit.ExportUserListToXML`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.DataExchange<wbr>Unit.ExportUserListToXML` → `System.Object`
- Признаки: static methods: Export, GetGroupsForUser, GetRolesForUser, GetUsersFromDB

### `CADLibKernel.CustomFolder<wbr>s.BuildingsHierarchy.CBui<wbr>ldingsHierarchyFolder`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.CustomFolder<wbr>s.BuildingsHierarchy.CBui<wbr>ldingsHierarchyFolder` → `CADLibKernel.CLibCatalogFilterItem`
- Признаки: static methods: Create, GetRelType

### `CADLibKernel.CustomFolder<wbr>s.BuildingsHierarchy.Hier<wbr>archyLevelType`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.CustomFolder<wbr>s.BuildingsHierarchy.Hier<wbr>archyLevelType` → `System.Enum`

### `CADLibKernel.CustomFolder<wbr>s.BuildingsHierarchy.CHie<wbr>rarchyObjectFolder`
- DLL: `CADLibKernel.dll`
- Наследование: `CADLibKernel.CustomFolder<wbr>s.BuildingsHierarchy.CHie<wbr>rarchyObjectFolder` → `CADLibKernel.CLibCatalogFilterItem`

### `CSAppServices.ChangeLog`
- DLL: `CSAppServices.dll`
- Наследование: `CSAppServices.ChangeLog` → `System.Object`
- Признаки: static methods: AddRecord, CreateTriggerEnabler, EnableChangeLog, FromDisabledChangeLog, WithDisabledChangeLog

### `CSAppServices.CHTMLReport`
- DLL: `CSAppServices.dll`
- Наследование: `CSAppServices.CHTMLReport` → `System.Object`

### `CSAppServices.CLWarningException`
- DLL: `CSAppServices.dll`
- Наследование: `CSAppServices.CLWarningException` → `LightweightDataAccess.ExceptionWithSeverity`

### `CSAppServices.DbConnectParameters`
- DLL: `CSAppServices.dll`
- Наследование: `CSAppServices.DbConnectParameters` → `System.Object`
- Признаки: static methods: Create, CreateWithDbmsAuth, CreateWithOSAuth, CreateWithOSAuth2, GetOdbcDriverNames

### `CSAppServices.dbcpOSAuthentication`
- DLL: `CSAppServices.dll`
- Наследование: `CSAppServices.dbcpOSAuthentication` → `CSAppServices.DbConnectParameters`

## 10. Важные сервисные классы CSAppServices

### `CSAppServices.DbConnectParameters`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.DbConnectParameters` → `System.Object`
- Практический смысл: параметры подключения к БД; базовый класс для OS/DBMS-аутентификации
- Статические методы: `Create`, `CreateWithDbmsAuth`, `CreateWithOSAuth`, `CreateWithOSAuth2`, `GetOdbcDriverNames`, `PreferredOdbcDrivers`, `SQLGetInstalledDriversW`, `SelectOdbcDriver`, `SelectOleDbProvider`, `ValidateDatabaseName`

Свойства:
- `convertUserNameToLowerCase: bool`
- `NormUserName: FLib.Str`
- `UseOdbc: bool`
- `IsOSAuthentication: bool`
- `IsAuthenticationDefined: bool`
Методы:
- `ValidateDatabaseName(bool(CSAppServices.DbName))`
- `LogParameters(void())`
- `Create(CSAppServices.DbConnectParameters(LightweightDataAccess.EServerType, FLib.Str, FLib.Str, FLib.Str, FLib.Str, string))`
- `CreateWithOSAuth(CSAppServices.DbConnectParameters(bool, LightweightDataAccess.EServerType, FLib.Str, FLib.Str, string, ET_15))`
- `CreateWithOSAuth2(CSAppServices.DbConnectParameters(bool, LightweightDataAccess.EServerType, FLib.Str, FLib.Str, CSAppServices.DbUser, string, ET_15))`
- `CreateWithDbmsAuth(CSAppServices.DbConnectParameters(bool, LightweightDataAccess.EServerType, FLib.Str, FLib.Str, FLib.Str, FLib.Str, string, ET_15))`
- `Create(CSAppServices.DbConnectParameters(FLib.Str, FLib.Str, FLib.Str))`
- `CreateConnection(LightweightDataAccess.DbConnectionInfo())`
- `MakeConnectionString(FLib.Str())`
- `MakeNativeConnectionString(FLib.Str())`
- `MakeOSAuthentication(CSAppServices.DbConnectParameters())`
- `MakeDbmsAuthentication(CSAppServices.DbConnectParameters(CSAppServices.DbUser, CSAppServices.DbPassword))`
- `MakeConnectionString(FLib.Str(CSAppServices.DbName))`
- `MakeNativeConnectionString(FLib.Str(CSAppServices.DbName))`
- `FromParameters(TypedReference(ET_00))`
- `WithParameters(void(ET_15))`
- `Copy(CSAppServices.DbConnectParameters(bool))`
- `SelectOdbcDriver(string(LightweightDataAccess.EServerType, bool))`
- `SelectOleDbProvider(string())`
- `SQLGetInstalledDriversW(bool(char[], uint16, uint16*))`
- `GetOdbcDriverNames(string[]())`
- `PreferredOdbcDrivers(string[](LightweightDataAccess.EServerType, bool))`

### `CSAppServices.dbcpOSAuthentication`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.dbcpOSAuthentication` → `CSAppServices.DbConnectParameters`
- Практический смысл: подключение с OS-аутентификацией

Свойства:
- `IsOSAuthentication: bool`
- `IsAuthenticationDefined: bool`
Методы:
- `MakeOSAuthentication(CSAppServices.DbConnectParameters())`
- `MakeDbmsAuthentication(CSAppServices.DbConnectParameters(CSAppServices.DbUser, CSAppServices.DbPassword))`
- `MakeConnectionString(FLib.Str(CSAppServices.DbName))`
- `MakeNativeConnectionString(FLib.Str(CSAppServices.DbName))`
- `FromParameters(TypedReference(ET_00))`
- `Copy(CSAppServices.DbConnectParameters(bool))`

### `CSAppServices.dbcpDBMSAuthentication`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.dbcpDBMSAuthentication` → `CSAppServices.DbConnectParameters`
- Практический смысл: подключение с DBMS-аутентификацией

### `CSAppServices.ObjectPublisher`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.ObjectPublisher` → `System.Object`
- Практический смысл: публикация/обработка объектов
- Статические методы: `GetObjectParamsSelQuery`, `GetObjectParamsSelQuery2`, `GetParamSrcTable`, `IsIntegerType`, `IsNumericType`, `IsRealType`, `PublishObjects`, `WriteObjectRows`

Методы:
- `GetParamSrcTable(string(int32))`
- `IsIntegerType(bool(int32))`
- `IsRealType(bool(int32))`
- `IsNumericType(bool(int32))`
- `PublishObjects(void(LightweightDataAccess.EServerType, LightweightDataAccess.DMakeDbCommandInfo, CSAppServices.CHTMLReport, ET_15))`
- `WriteObjectRows(int32(string, LightweightDataAccess.DMakeDbCommandInfo, CSAppServices.CHTMLReport))`
- `GetObjectParamsSelQuery2(string(LightweightDataAccess.EServerType, int32, ET_15, List`1, void))`
- `GetObjectParamsSelQuery(string(LightweightDataAccess.EServerType, int32, ET_15, List`1, void))`

### `CSAppServices.XExchange`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.XExchange` → `System.Object`
- Практический смысл: XML-обмен; вероятная точка импорта/экспорта структурированных данных
- Статические методы: `ActualColumns`, `CdeTableName`, `ColumnDefinitions`, `ColumnNames`, `DefinedColumns`, `DirectlyReferencedTables`, `DirectlyReferencingTables`, `ExplicitlyReferencedTables`, `ExplicitlyReferencingTables`, `GetDestinationHasDataSql`, `GetExcludedParameters`, `GetRecursiveHierarchy`

Методы:
- `StorageTableName(string(System.Xml.Linq.XElement))`
- `CdeTableName(string(System.Xml.Linq.XElement))`
- `StagingTableName(string(System.Xml.Linq.XElement))`
- `ReferencingPaths(ET_15(IEnumerable`1))`
- `ReferencedPaths(ET_15(IEnumerable`1))`
- `makeBoolAttr(ET_15(System.Func`2))`
- `name(string(System.Xml.Linq.XElement))`
- `nameAndPreviousNames(ET_15(IEnumerable`1))`
- `primary(bool(System.Xml.Linq.XElement))`
- `identity(bool(System.Xml.Linq.XElement))`
- `temporary(bool(System.Xml.Linq.XElement))`
- `extended(bool(System.Xml.Linq.XElement))`
- `primaveraName(string(System.Xml.Linq.XElement))`
- `primaveraProject(ET_15(IEnumerable`1))`
- `primaveraOrderBy(ET_15(FLib.Option`1))`
- `Table(ET_15(FLib.Option`1, void))`
- `Unit(ET_15(FLib.Option`1, void))`
- `ActualColumns(ET_15(IEnumerable`1))`
- `ActualColumns(ET_15(IEnumerable`1, void))`
- `IdentityColumns(ET_15(IEnumerable`1))`
- `IdentityColumns(ET_15(IEnumerable`1, void))`
- `HasHierarchicalIdentity(bool(System.Xml.Linq.XElement))`
- `IsParamValues(bool(System.Xml.Linq.XElement))`
- `PrimaryKeyColumns(ET_15(IEnumerable`1))`
- `PrimaryKeyColumns(ET_15(IEnumerable`1))`
- … ещё 28 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CSAppServices.CHTMLReport`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.CHTMLReport` → `System.Object`
- Практический смысл: формирование HTML-отчетов

Методы:
- `WriteStartTag(void(string, string))`
- `WriteEndTag(void(string))`
- `BeginTag(void(string))`
- `BeginTag(void(string, string))`
- `EndTag(void())`
- `EndLine(void())`
- `PrepareText(string(string))`
- `BeginTable(void(int32))`
- `BeginRow(void())`
- `BeginRow(void(string))`
- `EndTable(void())`
- `EndRow(void())`
- `WriteCell(void(string))`
- `WriteCell(void(string, string))`
- `WriteBoldCell(void(string))`
- `WriteText(void(string))`
- `WriteHeader(void(string, int32))`
- `Close(void())`

### `CSAppServices.UpgradeDatabaseBuild`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.UpgradeDatabaseBuild` → `NBuild.Build`
- Практический смысл: обновление структуры БД
- Статические методы: `getLocalMachineUsers`, `parseVersion`, `runSqlScripts`, `scriptsPath`, `scriptsUpgradePath`

Методы:
- `Upgrade(void())`
- `CheckDbConfig(void())`
- `ConfirmUpgrade(void())`
- `UpgradeDatabase(void())`
- `UpgradeDatabaseVersion(void())`
- `UpgradeDatabaseRevision(void())`
- `InitInternetSupport(void())`
- `GrantAccessToInternetUser(void())`
- `CreateInternetUserLogin(void())`
- `CheckInternetUserLoginExists(void())`
- `GetInternetUserName(void())`
- `GetInternetUserSecurityContext(void())`
- `CheckDatabaseUpToDate(void())`
- `Check3DSupport(void())`
- `CheckInternetSupport(void())`
- `GetDbInfo(void())`
- `LoadUpgradeInfo(void())`
- `GetAppDir(void())`
- `SelectUpgradeInfoScripts(void())`
- `parseVersion(int32(string))`
- `scriptsPath(string(string, LightweightDataAccess.EServerType, string))`
- `scriptsUpgradePath(string(string, LightweightDataAccess.EServerType, string))`
- `runSqlScripts(void(LightweightDataAccess.DbTransactionInfo, ET_15))`
- `getLocalMachineUsers(ET_15())`
- `<ConfirmUpgrade>b__19_0(bool())`
- … ещё 13 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CSAppServices.ParameterStorageBuild`

- DLL: `CSAppServices.dll`
- Тип: `class`
- Наследование: `CSAppServices.ParameterStorageBuild` → `NBuild.Build`
- Практический смысл: построение/обновление хранилища параметров

Методы:
- `Start(void())`
- `ReconfigureStorage(void())`
- `CreateParamTable(void())`
- `UpdateParamTable(void())`
- `UpdateLoggingTriggers(void())`
- `GetParamInfo(void())`
- `DropLoggingTriggers(void())`
- `ComposeLoggingTriggerI(void())`
- `ComposeLoggingTriggerD(void())`
- `ComposeLoggingTriggerU(void())`
- `<ReconfigureStorage>b__14_0(bool())`
- `<CreateParamTable>b__15_0(bool())`
- `<UpdateParamTable>b__16_0(bool())`
- `<UpdateLoggingTriggers>b__17_1(void(string))`

## 11. События: что можно подписывать

Ниже перечислены события, которые выглядят практически значимыми для автоматизации. В документе не используются широкие таблицы; каждый тип оформлен отдельной карточкой.

### `CADLib.CADLibrary`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLib.CADLibrary` → `CADLibKernel.CADLibraryBase`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.
- Статические методы: `AskForExportReport`, `ContainsNotEmptyString`, `ExploreFile`, `GetAppFolder`, `GetDirectory`, `GetFileDirectory`, `GetTempFolder`, `InitializeCSViewModels`, `MakeAppVersionInfo`, `RequestImportOptions`, `SetRowData`, `createImageList`

События:
- `BeforeDeleteObjects`: `BeforeDeleteObjectsEventHandler`
- `AfterDeleteObjects`: `AfterDeleteObjectsEventHandler`
- `AfterImportObjects`: `AfterImportObjectsEventHandler`
Свойства:
- `IsDocs: bool`
- `CalcNameOnDemand: bool`
- `AppVersion: string`
- `ExceptionMode: eExceptionMode`
- `ProgressWindow: CADLib.ProgressForm`
- `SmallImages: WinForms.ImageList`
- `LargeImages: WinForms.ImageList`
- `ScriptsDirectory: string`
- `CollisionCatId: int32`
- `FolderPlugins: ET_15` — Возвращает коллекцию плагинов каталогов
- `RootFilterWhere: string`
- `Rootfilters: ET_15` — Возвращает примененные корневые фильтры библиотеки
- `IsDBCreating: bool`
- `UserPermissions: bool[]`
- `IsAccessible: bool`
Методы:
- `MakeAppVersionInfo(string(string, string))`
- `InitializeCSViewModels(void())`
- `DeleteObjects(ET_15(List`1))`
- `DeleteObject(void(CLibObjectInfo))`
- `CADLibrary_OnRefresh(void(UpdatedSet))`
- `createImageList(WinForms.ImageList(int32))`
- `GetScriptsDir(string())`
- `GetFileCacheDir(string())`
- `SubRefresh(void())`
- `AddObjectNode(WinForms.TreeNode(WinForms.TreeView, WinForms.TreeNodeCollection, CLibObjectInfo, bool, bool, int32))`
- `FindNodeByNodesCollection(WinForms.TreeNode(WinForms.TreeNode, WinForms.TreeNodeCollection))`
- `FindNodeByNodesCollection(WinForms.TreeNode(WinForms.TreeView, WinForms.TreeNodeCollection))`
- … ещё 381 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CADLib.FoldersBrowser`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLib.FoldersBrowser` → `System.Windows.Forms.UserControl`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.
- Статические методы: `CanCreate`

События:
- `FolderChanged`: `FolderChangedAction`
- `FolderRefreshing`: `FolderRefreshAction`
- `FolderDragDrop`: `FolderDragDropAction`
- `FolderAdding`: `FolderNodeAddAction`
Свойства:
- `MainForm: CADLib.Forms.CadLibMainForm`
- `Library: CADLib.CADLibrary`
- `ImageList: WinForms.ImageList`
- `FoldersMenu: WinForms.ContextMenuStrip`
- `ModelRepresentationFlag: bool`
- `SelectedFolder: CLibCatalogFilterItem`
- `SelectedNode: WinForms.TreeNode`
Методы:
- `AddToInterfaceTracker(void(WinForms.ToolStripItem, CADLib.LibConnectionState, CADLib.LibFolderState, CADLib.LibObjectState, bool, CADLib.EClipboardState, CADLib.LibRequiredPermission))`
- `TrackInterfaceItems(void(CADLib.InterfaceTracker))`
- `Clear(void())`
- `PrepareProjectStructure(void(bool, bool, bool, bool))`
- `PrepareProjectStructure(void())`
- `foldersTree_AfterSelect(void(object, WinForms.TreeViewEventArgs))`
- `GetSelectedPath(string())`
- `GetDirectoryId(int32())`
- `AddFileFolderNode(void(int32, WinForms.TreeNode, CLibCatalogFilterItem))`
- `AddFolderNode(void(int32, WinForms.TreeNode, CLibCatalogFilterItem))`
- `CreateFolder(void())`
- `CreateClassifier(void())`
- … ещё 42 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CADLib.DirectoryBrowserCtrl`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLib.DirectoryBrowserCtrl` → `System.Windows.Forms.UserControl`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.
- Статические методы: `CanEditCoordinateGridObject`, `CheckUserAccessGroupsForObjects`, `HasAnyCoordinateGridObject`

События:
- `ObjectBeginDrag`: `CADLib.LibObjectEventHandler`
- `ObjectIconClick`: `WinForms.TreeNodeMouseClickEventHandler`
- `ObjectSelected`: `CADLib.LibObjectEventHandler`
- `ObjectClick`: `CADLib.LibObjectEventHandler`
- `ObjectDblClick`: `CADLib.LibObjectEventHandler`
- `FileBeginDrag`: `CADLib.LibFileEventHandler`
- `FileSelected`: `CADLib.LibFileEventHandler`
- `FileClick`: `CADLib.LibFileEventHandler`
- `FileDblClick`: `CADLib.LibFileEventHandler`
- `SelectionChanged`: `CADLib.DirectoryBrowserEventHandler`
- `PageViewStateChanged`: `CADLib.DirectoryBrowserEventHandler`
Свойства:
- `client: CADLib.DirectoryBrowserClient`
- `CurrentView: eView`
- `CurrentPage: CADLib.PageInfo`
- `mbHasNextPage: bool`
- `mbHasPrevPage: bool`
- `mnView: eView`
- `ObjectViewer: CADLib.Dialogs.ObjectViewerCtrl`
- `HasNextPage: bool`
- `HasPrevPage: bool`
- `PageSize: int32`
- `RecordsCount: int32`
- `CurrentFolder: CADLib.DbSettingsItem`
- `Library: CADLib.CADLibrary`
- `IsVisiblePageOnly: bool`
- `ActiveObject: CLibObjectInfo`
- `ActiveFile: CLibFileInfo`
- `CADLib.IDatabaseBrowser.ActiveObject: CLibObjectInfo`
- `CADLib.IDatabaseBrowser.ActiveFile: CLibFileInfo`
- `ItemCount: int32`
- `ItemCountText: string`
- … ещё 3 свойств.
Методы:
- `GetClient(CADLib.DirectoryBrowserClient())`
- `GetView(CADLib.DirectoryBrowserClient(eView))`
- `AddView(void(eView, ET_15))`
- `ForceUpdate(void())`
- `init(CADLib.DirectoryBrowserClient(CADLib.DirectoryBrowserClient))`
- `ResetPage(void())`
- `InvalidateClient(void())`
- `Value_ObjectNameChanged(void(CADLibraryBase, CLibObjectInfo))`
- `InitializeClient(void())`
- `SetTreeView(void())`
- `SetTableView(void())`
- `SetSketchView(void())`
- … ещё 112 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CADLib.DirectoryBrowserTreeBase`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLib.DirectoryBrowserTreeBase` → `CADLib.DirectoryBrowserClient`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.

События:
- `NoneSelected`: `SimpleEvent`
- `ObjectSelected`: `ObjectEvent`
- `ObjectClick`: `ObjectEvent`
- `ObjectDblClick`: `ObjectEvent`
- `FileSelected`: `FileEvent`
- `FileClick`: `FileEvent`
- `FileDblClick`: `FileEvent`
Свойства:
- `SelectedNodes: ET_15`
- `PageBounds: ET_15`
- `ItemCountText: string`
- `ObjectsTree: CADLib.ObjectsTreeView`
Методы:
- `OnVisibleItemsUpdated(void(int32))`
- `SetSelectedNode(void(WinForms.TreeNode))` — Устанавливает выбранный узел дерева
- `updateItems(void())`
- `tvObjects_QueryContinueDrag(void(object, WinForms.QueryContinueDragEventArgs))`
- `tvObjects_SizeChanged(void(object, System.EventArgs))`
- `ForEachNode(void(WinForms.TreeNodeCollection, TreeIteratorProc, bool, object, int32))`
- `ForEachNode(void(TreeIteratorProc, bool, object))`
- `GetSelectedNode(WinForms.TreeNode())`
- `ForEachChildNode(void(WinForms.TreeNodeCollection, TreeIteratorProc, bool, object))`
- `ForEachChildNodeByLevel(void(WinForms.TreeNodeCollection, TreeIteratorProc, bool, object, int32, bool))`
- `tvFolders_BeforeExpand(void(object, WinForms.TreeViewCancelEventArgs))`
- `tvObjects_BeforeExpand(void(object, WinForms.TreeViewCancelEventArgs))`
- … ещё 77 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CADLib.Dialogs.ObjectViewer`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLib.Dialogs.ObjectViewer` → `System.Windows.Forms.UserControl`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.

События:
- `OnFileAdd`: `CADLib.Dialogs.FileAddAction`
- `OnFilterByFile`: `CADLib.Dialogs.FileFilterAction`
- `OnRefreshInterface`: `CADLib.Dialogs.InterfaceAction`
- `OnPasteHyperlink`: `CADLib.Dialogs.InterfaceAction`
Свойства:
- `Library: CADLib.CADLibrary`
- `ActiveItem: object`
- `ActiveObject: object`
- `LargeImages: WinForms.ImageList`
- `SmallImages: WinForms.ImageList`
Методы:
- `TrackInterfaceItems(void(CADLib.InterfaceTracker))`
- `OnSetImagesLarge(void(WinForms.ImageList))`
- `OnSetImagesSmall(void(WinForms.ImageList))`
- `RaiseFileAdd(void(string[]))`
- `RaiseFilterByFile(void(string, int32))`
- `RaiseRefreshInterface(void())`
- `RaisePasteHyperlink(void())`
- `UpdateView(void(CLibObjectInfo))`
- `UpdateView(void(CLibFileInfo))`
- `DisableInterfaceTracking(void(CADLib.InterfaceTracker))`
- `ObjectViewer_Paint(void(object, WinForms.PaintEventArgs))`

### `CADLibControls.DesignerView`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `CADLibControls.DesignerView` → `System.Windows.Forms.UserControl`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.
- Статические методы: `GetModifiedEventParam`

События:
- `OnParamModified`: `OnParamModifiedEventHandler`
- `OnGetParamVariants`: `OnGetParamVariantsEventHandler`
Свойства:
- `Parameters: DesignerParameters`
- `OcxState: State`
Методы:
- `GetModifiedEventParam(DVParameter(object))`
- `AddParameter(DVParameter(string, string, object, string, DVParamType, bool, object, object))`
- `propEditor_OnParamModified(void(object, AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnParamModifiedEvent))`
- `propEditor_OnGetParamVariants(int32(object, AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnGetParamVariantsEven<wbr>t))`

### `AxInterop.SCXComponentsLi<wbr>bLib.AxPropertyEditor`

- DLL: `CADLibControls.dll`
- Тип: `class`
- Наследование: `AxInterop.SCXComponentsLi<wbr>bLib.AxPropertyEditor` → `System.Windows.Forms.AxHost`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.

События:
- `OnParamModified`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnParamModifiedEventHa<wbr>ndler`
- `OnSpecialEdit`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnSpecialEditEventHand<wbr>ler`
- `OnParameterSelchanged`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnParameterSelchangedE<wbr>ventHandler`
- `OnParameterIconClick`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnParameterIconClickEv<wbr>entHandler`
- `OnHyperlinkOpen`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnHyperlinkOpenEventHa<wbr>ndler`
- `OnHyperlinkEdit`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnHyperlinkEditEventHa<wbr>ndler`
- `OnGetParamVariants`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnGetParamVariantsEven<wbr>tHandler`
- `OnGetParamDetails`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnGetParamDetailsEvent<wbr>Handler`
- `OnParametersNeeded`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnParametersNeededEven<wbr>tHandler`
- `OnHierarchicalListDataCollect`: `AxInterop.SCXComponentsLi<wbr>bLib._IPropertyEditorEven<wbr>ts_OnHierarchicalListData<wbr>CollectEventHandler`
Свойства:
- `FillColor: System.Drawing.Color`
- `FillStyle: int32`
- `Font: System.Drawing.Font`
- `ForeColor: System.Drawing.Color`
- `Enabled: bool`
- `HWND: int64`
- `TabStop: bool`
- `Appearance: int16`
- `Valid: bool`
- `ViewType: Interop.SCXComponentsLibLib.EPropViewType`
- `Parameters: Interop.SCXComponentsLibLib.PEParameters`
- `SelectedParameter: Interop.SCXComponentsLibLib.PEParameter`
- `ShowCaptions: bool`
- `CurrentCategory: string`
- `ReadOnly: bool`
Методы:
- `CreateParameter(Interop.SCXComponentsLibLib.PEParameter(string, string, string, Interop.SCXComponentsLibLib.PEParamType))`
- `CreateParameter(Interop.SCXComponentsLibLib.PEParameter(string, string, string, Interop.SCXComponentsLibLib.PEParamType, object, object, object))`
- `Calculate(string(string))`
- `ExpandCategories(void(bool))`
- `MoveSelUpper(void())`
- `MoveSelLower(void())`
- `MoveSelTop(void())`
- `MoveSelBottom(void())`
- `SetCategoriesOrder(void(object))`
- `AddParameter(Interop.SCXComponentsLibLib.PEParameter(string, string, object, string, Interop.SCXComponentsLibLib.PEParamType, bool, object, object))`
- `AddMeasurement(Interop.SCXComponentsLibLib.PEMeasurement(string, string))`
- `UpdateHierListParameters(void(int32))`
- … ещё 13 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CSProject3D.CAD3DLibrary`

- DLL: `CSProject3D.dll`
- Тип: `class`
- Наследование: `CSProject3D.CAD3DLibrary` → `CADLib.CADLibrary`
- XML-описание: Класс базы данных приложений CADLib, работающих с трёхмерной графикой объектов
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.
- Статические методы: `CreateLibObjectFromUnmanaged`, `IsSelectionFolder`

События:
- `OnSelectionChanged`: `EventHandlerSelectionChanged`
Свойства:
- `CurrentSession: int32`
- `IsEmptySelection: bool`
- `SingleSelectedObjectId: int32`
- `SelectedObjects: ET_15`
- `IsSingleSelection: bool`
- `SelectedObjectsCount: int32`
- `bObjectJustPicked: bool` — true while in on axNWEViewerCtl1_OnObjectPicked methos
- `CurrentViewNode: WinForms.TreeNode`
- `Is3DLibrary: bool`
- `IsCurrentViewAllObjects: bool` — Показывает ли узел текущий вид все корневые объекты
- `UserTaggingNode: WinForms.TreeNode`
Методы:
- `onConnect(void())`
- `IsObjectSelected(bool(int32))`
- `IsSelectionSupersetOf(bool(ET_15))`
- `AnyObjectInSelection(bool(ET_15))`
- `RaiseOnSelChanged(void())`
- `InitSelFilterTable(bool())`
- `SetMultiselectionFilter(void())`
- `ResetSelection(bool())`
- `IsObjectSelectedTwice(bool(int32))`
- `AppendObjectToSelection(bool(int32))` — Add object to library 3D selection set
- `AppendObjectsToSelection(bool(ET_15))` — Add objects to library selection set
- `SetSelectedObjects(bool(ET_15))` — Set library selected objects to set
- … ещё 74 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CSProject3D.Viewer3DCtrl`

- DLL: `CSProject3D.dll`
- Тип: `class`
- Наследование: `CSProject3D.Viewer3DCtrl` → `System.Windows.Forms.UserControl`
- XML-описание: Компонент просмотра трёхмерной графики из базы данных
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.
- Статические методы: `GetKeyState`, `InputBox`, `SendMessage`

События:
- `OnObjectPicked`: `EventHandlerObject`
- `OnEntityPicked`: `EventHandlerEntity`
- `OnLandPicked`: `EventHandlerObject`
- `OnLandsHide`: `EventHandlerLands`
- `OnSelectCollision`: `EventHandlerCollisions`
- `PopupMenuOpening`: `EventHandlerPopupOpening`
- `On3DLoad`: `EventHandler3DLoad`
- `On3DPreLoad`: `EventHandler3DLoad`
- `On3DFatalError`: `System.EventHandler`
- `On3DInitialized`: `System.EventHandler`
- `OnContextMenuDown3D`: `System.EventHandler`
- `OnEntityClosedClick`: `EventHandlerEntity`
- `OnEntityInfoClick`: `EventHandlerEntity`
- `OnHotShapeChanged`: `EventHotShapeChanged`
- `OnSelectWithFrame`: `SelectWithFrame`
- `OnRequestEdit2dDrawing`: `TypeSpec`
Свойства:
- `PopupMenu: WinForms.ContextMenuStrip`
- `ContextMenuLastObject: CLibObjectInfo` — Объект БД (может быть кастомный) на котором было последний раз активированно контекстное меню
- `ContextMenuLastEntity: EntityPointer` — Сущность на которой последней раз было активированно контекстное меню
- `OnHyperlinkClicked: ET_15`
- `m_taggingCollection: UserTagging.UserTaggingCollection`
- `multiuserUI: CADLib.Dialogs.MultiuserForm` — Возвращает (если надо создаёт) окно многопользовательской работы
- `ShowAvatar: bool`
- `EnableGravity: bool`
- `AvatarCollisionCheck: bool`
- `EnableToolTip: bool`
- `Is3DInitialized: bool`
- `Library: CAD3DLibrary`
- `ShowViewerFormAction: System.Action`
- `CollisionCatId: int32`
- `IgnoreSelectionUpdate: bool`
- `HotObjectId: int32`
- `HotEntityId: EntityPointer`
- `LoadedFilter: string`
- `DontResetCorrections: bool`
- `Ax3DViewerVisible: bool`
- … ещё 6 свойств.
Методы:
- `SetVisibleLandSurfaces(void(int32[]))` — Устанавливает набор видимых поверхностей Загружает недостающие поверхности и удаляет пропавшие из списка видимости
- `SetSelectedLandSurfaces(void(int32[]))` — Устанавливает набор выделенных поверхностей Снимает выделение со всех остальных поверхностей
- `FocusOnLandSurfaces(void(int32[]))` — Фокусирует камеру на загруженных поверхностях земли из списка
- `toolStripMIInsertFromClipboard_Click(void(object, System.EventArgs))`
- `WndProc(void(WinForms.Message*))`
- `toolStripMIInsertSelectedObjLink_Click(void(object, System.EventArgs))`
- `AppendChatMessage(int32(string, int32))`
- `OnMessageSendEMailEvent(void(string, string, string))`
- `GetEMailServerParams(bool(string*, int32*, bool*, string*, string*, string*))`
- `TakeScreenshotForChat(void(string))`
- `UpdateChatMessages(int32(int32, ET_15))`
- `UpdateUsersList(bool(WinForms.ListView))`
- … ещё 241 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CSProject3D.Collisions.CollisionsTree`

- DLL: `CSProject3D.dll`
- Тип: `class`
- Наследование: `CSProject3D.Collisions.CollisionsTree` → `System.Object`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.

События:
- `SelectionChanged`: `System.EventHandler`
- `NodesChanged`: `TypeSpec`
- `NodesInserted`: `TypeSpec`
- `NodesRemoved`: `TypeSpec`
- `StructureChanged`: `TypeSpec`
Свойства:
- `AllItems: ET_15`
- `SelectedCollision: CollisionEngine.CollisionObject`
- `SelectedObjectId: int32`
- `IsMultiselection: bool`
- `FilterCollision: CollisionsFilter`
- `FilterObject1: CollisionsFilter`
- `FilterObject2: CollisionsFilter`
- `HasFilterCollision: bool`
- `HasFilterObject1: bool`
- `HasFilterObject2: bool`
- `HasFilterAny: bool`
Методы:
- `GetMultiselection(ET_15())`
- `SetFilterNoRefresh(void(CollisionsFilter, CollisionsFilter, CollisionsFilter))` — Устанавливает фильтр объектов без обновления дерева
- `AssignFilter(void(CollisionsFilter*, CollisionsFilter))` — Фильтр объектов коллизии Установка приводит к обновлению списка
- `GetHighlightObjectsSet(ET_15(IEnumerable`1, void))`
- `m_lib_OnObjectNameChanged(void(CADLibraryBase, CLibObjectInfo))`
- `m_lib_AfterDeleteObjects(void(CADLibraryBase, int32[]))`
- `treeView_SelectionChanged(void(object, System.EventArgs))`
- `RaiseSelectionChanged(void())`
- `GetPath(Aga.Controls.Tree.TreePath(object))`
- `MakeArgs(Aga.Controls.Tree.TreeModelEventArgs(object, bool))`
- `GetChildren(System.Collections.IEnumerable(Aga.Controls.Tree.TreePath))`
- `IsLeaf(bool(Aga.Controls.Tree.TreePath))`
- … ещё 20 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CSProject3D.Publications.PublicationsForm`

- DLL: `CSProject3D.dll`
- Тип: `class`
- Наследование: `CSProject3D.Publications.PublicationsForm` → `System.Windows.Forms.Form`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.

События:
- `CheckPublications`: `System.EventHandler`
Свойства:
- `AutoUpdate: bool`
Методы:
- `RefreshHandler(void(object, System.EventArgs))`
- `m_library_OnRefresh(void(UpdatedSet))`
- `OnLibraryDisconnected(void())`
- `m_library_Connected(void())`
- `InitUIProperties(void())`
- `BeginMonitoring(void())`
- `EndMonitoring(void())`
- `AddPublication(void(int32, string))`
- `RefreshData(void())` — Обновляет данные в окне публикаций
- `PublicationsForm_VisibleChanged(void(object, System.EventArgs))`
- `StartMonitor(void())`
- `PublicationsMonitor(void())`
- … ещё 18 методов. В полном справочнике сигнатур они перечислены отдельно.

### `CADLibKernel.CADLibraryBase`

- DLL: `CADLibKernel.dll`
- Тип: `class`
- Наследование: `CADLibKernel.CADLibraryBase` → `System.Object`
- Практический смысл: Событийная точка для UI/БД/3D/коллизий/публикаций.
- Статические методы: `ArchiveBlobToFile`, `ConvertDateValueToPgSql`, `ConvertDateValueToSql`, `ConvertDateValueToTSql`, `CreateDbCommand`, `Deserialize`, `DoUploadFile`, `DownloadFile`, `DownloadXmlParametric`, `ExtractZipFirstEntry`, `GetBmpBytes`, `GetEncoder`

События:
- `Connected`: `DConnected`
- `OnObjectNameChanged`: `ObjectNameChangedEventHandler`
- `OnRefresh`: `OnRefreshMethod`
Свойства:
- `Dbcp: CSAppServices.DbConnectParameters`
- `LibDirectory: string`
- `Is3DLibrary: bool`
- `IsConnected: bool`
- `Connection: LightweightDataAccess.DbConnectionInfo`
- `Transaction: LightweightDataAccess.DbTransactionInfo`
- `UserDisplayName: string`
- `CurrentUser: int32`
- `UserPermissions: bool[]`
- `IsCurrentUserAdministrator: bool`
- `IsCurrentUserInfoSec: bool`
- `ServerSpecificScriptsDir: System.IO.DirectoryInfo`
- `DatabaseDesc: string`
- `IsConnecting: bool`
- `CurrentDbContext: LightweightDataAccess.DbContext`
- `MiscCategoryId: int32`
- `StructureDataCategoryId: int32`
- `ObjectDataFileCategoryId: int32`
- `StructureDataGroupParamId: int32`
- `IsImporting: bool`
Методы:
- `IsInPredicate(bool(FLib.Str))`
- `IsInNotPredicate(bool(FLib.Str))`
- `IsExistsPredicate(bool(FLib.Str))`
- `IsNotExistsPredicate(bool(FLib.Str))`
- `IsExistencePredicate(bool(FLib.Str))`
- `Command(LightweightDataAccess.DbCommandInfo(string))`
- `AdaptedCommand(LightweightDataAccess.DbCommandInfo(string))`
- `Command(LightweightDataAccess.DbCommandInfo(string, ET_15))`
- `ExecuteDbCommand(void(string, bool, object[]))`
- `CreateDbCommand(LightweightDataAccess.DbCommandInfo(string, bool, object[]))`
- `CreateDbCommand(LightweightDataAccess.DbCommandInfo(LightweightDataAccess.DbConnectionInfo, System.Data.Common.DbTransaction, string, object[]))`
- `SP(object(int32))`
- … ещё 874 методов. В полном справочнике сигнатур они перечислены отдельно.

## 12. Все найденные интерфейсы

### `CADLibControls.dll`
- `Aga.Controls.Tree.IToolTipProvider`
- `Aga.Controls.Tree.ITreeModel`
- `CADLibControls.Forms.ICustomDestinationList`
- `CADLibControls.Forms.IObjectArray`
- `CADLibControls.Forms.IObjectCollection`
- `CADLibControls.Forms.ITaskbarList4`
- `CADLib.IDatabaseBrowser` — Интерфейс, главного плагина, создающего окно Интерфес содержит методы типа GetCurrentSelection
- `CADLib.ICADLibPlugin` — Абстрактный класс, реализованный во всех плагинах. Извлекается вызовом метода CADLibPluginEntryPoint.RegisterPlugin(PluginsManager manager).
- `CADLib.ICADLibMainPlugin` — Абстрактный класс, реализованный в главных плагинах. Извлекается вызовом метода CADLibPluginEntryPoint.RegisterPlugin(PluginsManager manager).
- `CADLib.ICADLibStartPlugin`
- `CADLib.IDocViewer`
- `CADLib.AccessControl.IAccessSubject`
- `Interop.SCXComponentsLibLib.IPECalculator`
- `Interop.SCXComponentsLibLib.IPECategories`
- `Interop.SCXComponentsLibL<wbr>ib.IPEHierarchicalListCon<wbr>text`
- `Interop.SCXComponentsLibLib.IPEMeasurement`
- `Interop.SCXComponentsLibLib.IPEObjectCsv`
- `Interop.SCXComponentsLibL<wbr>ib.IPEObjectHierarchyCsv`
- `Interop.SCXComponentsLibLib.IPEParamValue`
- `Interop.SCXComponentsLibLib.IPEParamValues`
- `Interop.SCXComponentsLibLib.IPEParameter`
- `Interop.SCXComponentsLibLib.IPEParameters`
- `Interop.SCXComponentsLibLib.IPEStringList`
- `Interop.SCXComponentsLibLib.IPEVariantsList`
- `Interop.SCXComponentsLibLib.IPropertyEditor`
- `Interop.SCXComponentsLibLib.ISCXUtils`
- `Interop.SCXComponentsLibLib.PECalculator`
- `Interop.SCXComponentsLibLib.PECategories`
- `Interop.SCXComponentsLibL<wbr>ib.PEHierarchicalListCont<wbr>ext`
- `Interop.SCXComponentsLibLib.PEMeasurement`
- `Interop.SCXComponentsLibLib.PEObjectCsv`
- `Interop.SCXComponentsLibL<wbr>ib.PEObjectHierarchyCsv`
- `Interop.SCXComponentsLibLib.PEParamValue`
- `Interop.SCXComponentsLibLib.PEParamValues`
- `Interop.SCXComponentsLibLib.PEParameter`
- `Interop.SCXComponentsLibLib.PEParameters`
- `Interop.SCXComponentsLibLib.PEVariantsList`
- `Interop.SCXComponentsLibLib.SCXUtils`
- `Interop.SCXComponentsLibL<wbr>ib._IPECalculatorEvents`
- `Interop.SCXComponentsLibL<wbr>ib._IPECalculatorEvents_E<wbr>vent`
- `Interop.SCXComponentsLibL<wbr>ib._IPropertyEditorEvents`
- `IRelationTypeIconProvider`
- `IView`
- `IUser`

### `CSProject3D.dll`
- `CSProject3D.IDockWindowOwner` — Интерфейс работы с палитрами
- `CSProject3D.I3DViewerOwner` — Интерфейс главного окна трёхмерной модели
- `CSProject3D.Properties3D.IPropertiesForm`
- `CSProject3D.Properties3D.<wbr>IPositionOrientation`
- `CSProject3D.Properties3D.IPosOrientClonable`
- `IView`
- `IView`

### `CADLibKernel.dll`
- `CollisionEngine.ICollisionCalcStarter`
- `CADLibKernel.IObjectTreeQuery`
- `CADLibKernel.ICadDataSource`
- `CADLibKernel.Models.ObjectUpdate.ICADLibItem`

### `CSAppServices.dll`
- Интерфейсы не найдены или не вынесены в публичные метаданные.

## 13. Все типы с событиями

### `CADLibControls.dll`
- `WizardFormLib.WizardFormBase`
  - base: `System.Windows.Forms.Form`
  - events: `WizardPageChangeEvent`, `WizardFormStartedEvent`
- `WizardFormLib.WizardPage`
  - base: `System.Windows.Forms.UserControl`
  - events: `WizardPageActivated`
- `FileDialogExtenders.FileDialogControlBase`
  - base: `System.Windows.Forms.UserControl`
  - events: `EventFileNameChanged`, `EventFolderNameChanged`, `EventFilterChanged`, `EventClosingDialog`
- `Aga.Controls.Tree.ITreeModel`
  - events: `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`
- `Aga.Controls.Tree.TreeModel`
  - base: `System.Object`
  - events: `NodesChanged`, `StructureChanged`, `NodesInserted`, `NodesRemoved`
- `Aga.Controls.Tree.TreeViewAdv`
  - base: `System.Windows.Forms.Control`
  - events: `ItemDrag`, `NodeMouseDoubleClick`, `ColumnWidthChanged`, `SelectionChanged`, `Collapsing`, `Collapsed`, `Expanding`, `Expanded`, `NodePropertyChanged`
- `Aga.Controls.Tree.NodeCon<wbr>trols.BindableControl`
  - base: `Aga.Controls.Tree.NodeControls.NodeControl`
  - events: `BeforeSetValue`, `AfterSetValue`
- `Aga.Controls.Tree.NodeCon<wbr>trols.EditableControl`
  - base: `Aga.Controls.Tree.NodeCon<wbr>trols.BindableControl`
  - events: `EditorShowing`, `EditorHided`
- `Aga.Controls.Tree.NodeControls.NodeCheckBox`
  - base: `Aga.Controls.Tree.NodeCon<wbr>trols.BindableControl`
  - events: `CheckStateChanged`
- `Aga.Controls.Tree.NodeControls.NodePushIcon`
  - base: `Aga.Controls.Tree.NodeCon<wbr>trols.BindableControl`
  - events: `OnIconClick`, `OnIconHover`
- `Aga.Controls.Tree.NodeControls.NodeTextBox`
  - base: `Aga.Controls.Tree.NodeCon<wbr>trols.BaseTextControl`
  - events: `LabelChanged`
- `ColorPicker.ColorSlider`
  - base: `ColorPicker.LabelRotate`
  - events: `SelectedValueChanged`
- `ColorPicker.ColorTable`
  - base: `ColorPicker.LabelRotate`
  - events: `SelectedIndexChanged`
- `ColorPicker.ColorWheel`
  - base: `System.Windows.Forms.Control`
  - events: `SelectedColorChanged`
- `ColorPicker.ColorWheelCtrl`
  - base: `System.Windows.Forms.UserControl`
  - events: `SelectedColorChanged`
- `ColorPicker.DropdownContainerControl`1`
  - base: `System.Windows.Forms.Control`
  - events: `SelectedItemChaged`
- `ColorPicker.EyedropColorPicker`
  - base: `System.Windows.Forms.Control`
  - events: `SelectedColorChanged`
- `AxInterop.SCXComponentsLi<wbr>bLib.AxPropertyEditor`
  - base: `System.Windows.Forms.AxHost`
  - events: `OnParamModified`, `OnSpecialEdit`, `OnParameterSelchanged`, `OnParameterIconClick`, `OnHyperlinkOpen`, `OnHyperlinkEdit`, `OnGetParamVariants`, `OnGetParamDetails`, `OnParametersNeeded`, `OnHierarchicalListDataCollect`
- `CADLibControls.CSStackPanelItem`
  - base: `System.Windows.Forms.UserControl`
  - events: `CloseButtonClick`
- `CADLibControls.DesignerView`
  - base: `System.Windows.Forms.UserControl`
  - events: `OnParamModified`, `OnGetParamVariants`
- `CADLibControls.BreadCrumbControl`
  - base: `System.Windows.Forms.UserControl`
  - events: `GetPath`, `SelectPath`
- `CADLibControls.Controls.ParametersSelectTree`
  - base: `System.Windows.Forms.UserControl`
  - events: `CheckStateChanged`, `SelectionChanged`
- `CADLib.ParamDefDlg`
  - base: `System.Windows.Forms.Form`
  - events: `OnValidateParameter`
- `CADLib.CADLibrary`
  - base: `CADLibKernel.CADLibraryBase`
  - events: `BeforeDeleteObjects`, `AfterDeleteObjects`, `AfterImportObjects`
- `CADLib.FoldersBrowser`
  - base: `System.Windows.Forms.UserControl`
  - events: `FolderChanged`, `FolderRefreshing`, `FolderDragDrop`, `FolderAdding`
- `CADLib.DirectoryBrowserClient`
  - base: `System.Windows.Forms.UserControl`
  - events: `VisibleItemsUpdated`
- `CADLib.DirectoryBrowserCtrl`
  - base: `System.Windows.Forms.UserControl`
  - events: `ObjectBeginDrag`, `ObjectIconClick`, `ObjectSelected`, `ObjectClick`, `ObjectDblClick`, `FileBeginDrag`, `FileSelected`, `FileClick`, `FileDblClick`, `SelectionChanged`, `PageViewStateChanged`
- `CADLib.DirectoryBrowserTreeBase`
  - base: `CADLib.DirectoryBrowserClient`
  - events: `NoneSelected`, `ObjectSelected`, `ObjectClick`, `ObjectDblClick`, `FileSelected`, `FileClick`, `FileDblClick`
- `CADLib.InterfaceTracker`
  - base: `System.Object`
  - events: `AfterTrackInterfaceState`
- `CADLib.ObjectsTreeView`
  - base: `System.Windows.Forms.TreeView`
  - events: `MouseDblClickEx`
- `CADLib.Dialogs.MultiuserForm`
  - base: `System.Windows.Forms.Form`
  - events: `OnLogOn`, `OnLogOff`, `OnPersonSelect`, `OnHyperlinkClicked`
- `CADLib.Dialogs.ObjectViewer`
  - base: `System.Windows.Forms.UserControl`
  - events: `OnFileAdd`, `OnFilterByFile`, `OnRefreshInterface`, `OnPasteHyperlink`
- `CADLib.Dialogs.ObjectViewerCtrl`
  - base: `System.Windows.Forms.UserControl`
  - events: `OnFileAdd`, `OnFilterByFile`, `OnRefreshInterface`, `OnPasteHyperlink`
- `CADLib.AccessControl.AccessControlModel`
  - base: `System.Object`
  - events: `Reloaded`
- `Interop.SCXComponentsLibL<wbr>ib._IPECalculatorEvents_E<wbr>vent`
  - events: `OnParametersNeeded`
- `ObjectCopyReportDataTableDataTable`
  - base: `TypeSpec`
  - events: `ObjectCopyReportDataTableRowChanging`, `ObjectCopyReportDataTableRowChanged`, `ObjectCopyReportDataTableRowDeleting`, `ObjectCopyReportDataTableRowDeleted`
- `DataExchangeTableDataTable`
  - base: `TypeSpec`
  - events: `DataExchangeTableRowChanging`, `DataExchangeTableRowChanged`, `DataExchangeTableRowDeleting`, `DataExchangeTableRowDeleted`
- `TreeController`
  - base: `System.Object`
  - events: `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`

### `CSProject3D.dll`
- `WorksLib2.WorksLib2Controller`
  - base: `System.Object`
  - events: `OnCurrentNodeChanged`, `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`
- `FileDialogExtendersOFD.Fi<wbr>leDialogControlBaseOFD`
  - base: `System.Windows.Forms.UserControl`
  - events: `EventFileNameChanged`, `EventFolderNameChanged`, `EventFilterChanged`, `EventClosingDialog`
- `CSProject3D.CAD3DLibrary`
  - base: `CADLib.CADLibrary`
  - описание: Класс базы данных приложений CADLib, работающих с трёхмерной графикой объектов
  - events: `OnSelectionChanged`
- `CSProject3D.Viewer3DCtrl`
  - base: `System.Windows.Forms.UserControl`
  - описание: Компонент просмотра трёхмерной графики из базы данных
  - events: `OnObjectPicked`, `OnEntityPicked`, `OnLandPicked`, `OnLandsHide`, `OnSelectCollision`, `PopupMenuOpening`, `On3DLoad`, `On3DPreLoad`, `On3DFatalError`, `On3DInitialized`, `OnContextMenuDown3D`, `OnEntityClosedClick`, `OnEntityInfoClick`, `OnHotShapeChanged`, `OnSelectWithFrame`, `OnRequestEdit2dDrawing`
- `CSProject3D.Properties3DForm`
  - base: `System.Windows.Forms.Form`
  - events: `OnUpdateProperties`
- `CSProject3D.UserTagging.U<wbr>serTaggingCollection`
  - base: `System.Object`
  - events: `OnTagNameChanged`, `OnTagPicked`
- `CSProject3D.UserTagging.U<wbr>serTaggingController`
  - base: `System.Object`
  - events: `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`, `SelectionChanged`
- `CSProject3D.UserTagging.V<wbr>ector2d.Vector2dCanvas`
  - base: `System.Object`
  - events: `OptionChanged`, `ObjectSelected`, `NeedRedraw`, `NeedChangeCursor`
- `CSProject3D.UserTagging.E<wbr>ntities.DrawingTag2d`
  - base: `CSProject3D.UserTagging.E<wbr>ntities.UserTaggingBase`
  - events: `OnNew2dDataApplied`
- `CSProject3D.Scenario.CamScriptTreeController`
  - base: `System.Object`
  - events: `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`
- `CSProject3D.Scenario.ScenarioView`
  - base: `System.Windows.Forms.UserControl`
  - events: `SelectedNodeChanged`, `NodeMouseDoubleClick`, `EditBegin`, `EditEnd`
- `CSProject3D.Publications.PublicationsForm`
  - base: `System.Windows.Forms.Form`
  - events: `CheckPublications`
- `CSProject3D.ModelRepresen<wbr>tation.ModelRepresentatio<wbr>nTree`
  - base: `System.Object`
  - events: `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`
- `CSProject3D.Works.WorkPro<wbr>perties.WorkProperty`
  - base: `System.Object`
  - events: `PropertyChanged`
- `CSProject3D.Forms.VideoRecorderControl`
  - base: `System.Windows.Forms.UserControl`
  - events: `RecordingStart`, `RecordingStop`
- `CSProject3D.Forms.Tools.Q<wbr>uestionBox.QuestionBoxCon<wbr>text`
  - base: `System.Object`
  - events: `PropertyChanged`
- `CSProject3D.Forms.Tools.H<wbr>ierarchyTableView.CLibObj<wbr>ectParameterView`
  - base: `System.Object`
  - описание: Класс для отображения параметра объекта CLibObjectInfo
  - events: `PropertyChanged`
- `CSProject3D.Forms.Tools.H<wbr>ierarchyTableView.CLibObj<wbr>ectView`
  - base: `System.Object`
  - описание: Класс для отображения параметров объекта CLibObjectInfo
  - events: `ParameterChanged`, `PropertyChanged`
- `CSProject3D.Forms.Expertise.NoteItem`
  - base: `System.Object`
  - events: `PropertyChanged`
- `CSProject3D.Forms.Expertise.CommentControl`
  - base: `System.Windows.Controls.UserControl`
  - описание: CommentControl
  - events: `FileSelected`, `RefSelected`
- `CSProject3D.Forms.Experti<wbr>se.CommentsListControl`
  - base: `System.Windows.Controls.UserControl`
  - описание: CommentsListControl
  - events: `NoteTitleClicked`, `StatusUpdated`
- `CSProject3D.Forms.Expertise.NotesListControl`
  - base: `System.Windows.Controls.UserControl`
  - описание: NotesListControl
  - events: `NoteSelected`, `NoteTitlePressed`, `NoteDeletePressed`
- `CSProject3D.Forms.Expertise.UploadControl`
  - base: `System.Windows.Controls.UserControl`
  - описание: UploadControl
  - events: `CloseClicked`
- `CSProject3D.Controls.Work<wbr>Mgmt.ColumnsEditor.DataCo<wbr>lumnEditorContext`
  - base: `System.Object`
  - events: `PropertyChanged`
- `CSProject3D.Controls.Work<wbr>Mgmt.ColumnsEditor.DataCo<wbr>lumnView`
  - base: `System.Object`
  - events: `PropertyChanged`
- `CSProject3D.Controls.Work<wbr>Mgmt.ColumnsEditor.RelayC<wbr>ommand`
  - base: `System.Object`
  - events: `CanExecuteChanged`
- `CSProject3D.Collisions.CollisionsTree`
  - base: `System.Object`
  - events: `SelectionChanged`, `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`
- `CSProject3D.Collisions.Wizard.ProfilesTree`
  - base: `System.Object`
  - events: `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`
- `TreeController`
  - base: `System.Object`
  - events: `NodesChanged`, `NodesInserted`, `NodesRemoved`, `StructureChanged`
- `CommentViewModel`
  - base: `System.Object`
  - events: `PropertyChanged`

### `CADLibKernel.dll`
- `CADLibKernel.CADLibraryBase`
  - base: `System.Object`
  - events: `Connected`, `OnObjectNameChanged`, `OnRefresh`
- `CADLibKernel.ObjectUpdate<wbr>.ObjectUpdateService`
  - base: `System.Web.Services.Proto<wbr>cols.SoapHttpClientProtoc<wbr>ol`
  - events: `IncreaseObjectVersionCompleted`, `LoadChildrenCompleted`, `GetFileCategoryCompleted`, `CreateFileCategoryCompleted`, `GetObjectRootParentCompleted`, `GetObjectParentCompleted`, `IsHaveEnouthEditingObject<wbr>PermissionsCompleted`, `GetTagByIdCompleted`, `GetTagsByKindCompleted`, `GetTagObjectsByIdCompleted`, `GetTagObjectsByKindCompleted`, `CreateObjectDocumentCompleted`, `GetParamsByCategoriesCompleted`, `GetModelRepresentationsCompleted`, `AddExpertiseItemCompleted`, `UpdateExpertiseItemCompleted`, `GetExpertiseItemsCompleted`, `LoadChildIdsHierarchyCompleted`, `LoadRecursiveChildGuidsCompleted`, `GetObjectIdInHierarchyCompleted`, `UploadObjectFileCompleted`, `UpdateDbTableFromKeyValueMapJSONCompleted`, `GetModelHasLowDetailMeshCompleted`, `GetModelExtentsCompleted`, `Count3DShapesSizeCompleted`, `SelectShapesExCompleted`, `SelectMeshesExCompleted`, `GetObject3DShapesInfoCompleted`, `GetSingleObject3DShapesInfoCompleted`, `GetGraphicsByIdsCompleted`, `GetObject3DShapesInfoByIdsCompleted`, `GetGraphicsByObjectsIdsCompleted`, `GetObject3DShapesInfoByParentIdCompleted`, `GetObject3DShapesInfoByPageCompleted`, `GetObjects3DCompleted`, `GetGraphicsCountCompleted`, `GetMeshesIdsByParentIdCompleted`, `Get3DGraphicsCompleted`, `Get3DGraphicsWithPtCompleted`, `Get3DGraphicsArrayCompleted`, `GetPersonsListCompleted`, `GetChatMessagesCompleted`, `AppendChatMessageCompleted`, `GetCurrentUserIdCompleted`, `GetPersonsInfoCompleted`, `UpdatePersonInfoCompleted`, `CreateDatabaseSnapshotCompleted`, `GetFileServerAddressCompleted`, `GetDocumentCachedFileIdsCompleted`, `GetLibraryDbmsTypeCompleted`, `GetObjectHierarchyChildrenCompleted`, `GetFolderHierarchyCompleted`, `GetObjectHierarchyFilterCompleted`, `GetObjectHierarchyFilterAllCompleted`, `AddObjectRelationTypeCompleted`, `LinkObjectsCompleted`, `LinkObjectsByUidCompleted`, `RemoveObjectLinksCompleted`, `RemoveObjectLinksByUidCompleted`, `GetLinkedObjectsCompleted`, `GetLinkedObjectsByUidCompleted`, `GetLandsByParentObjectByPageCompleted`, `GetLandsIdsByGroupCompleted`, `GetLandDataCompleted`, `GetLandArrayDataCompleted`, `GetObjectsListCountCompleted`, `GetObjectsCountCompleted`, `GetFilesCountCompleted`, `GetFilesInfoByTypeAndCategoryCompleted`, `GetTagsByObjectsIdsCompleted`, `GetDataByTagIdCompleted`, `GetObjectStatusCompleted`, `DeleteObjectCompleted`, `GetObjectFilesMSCompleted`, `GetObjectFilesDataCompleted`, `DownloadDefaultParametersCompleted`, `GetIconByObjectCategoryCompleted`, `GetObjectsInfoByIdCompleted`, `UploadObjectFilesCompleted`, `UploadFileCompleted`, `DeleteFileCompleted`, `RenameFileCompleted`, `GetParamDefsXmlCompleted`, `GetParamDefsCompleted`, `CreateObjectCategoryCompleted`, `GetObjectCategoriesCompleted`, `GetObjectCategoriesIdsCompleted`, `GetObjectCategoryNameByIdCompleted`, `GetObjectCategoryCaptionByIdCompleted`, `GetLibraryObjectInfoCompleted`, `GetLibraryObjectInfosCompleted`, `GetLibUIDsCompleted`, `GetLibraryObjectsInfoByCategoryCompleted`, `GetObjectsParametersCompleted`, `GetParamValueVariantsCompleted`, `GetCategoriesListCompleted`, `GetParamDefNameCompleted`, `GetIconsCompleted`, `GetFileCategoriesCompleted`, `GetFileCategoriesIdsCompleted`, `UploadParamDefsCompleted`, `UploadObjectCategoriesCompleted`, `UploadFileCategoriesCompleted`, `UploadIconsCompleted`, `UploadObjectExCompleted`, `GetFileCompleted`, `GetFileUnpackedCompleted`, `GetFileByIdCompleted`, `GetObjectFilesCompleted`, `GetObjectFilesJSONCompleted`, `GetObjectFilesExJSONCompleted`, `GetFileDataCompleted`, `GetFileData2Completed`, `GetObjectRelationTypeByNameCompleted`, `GetDocumentObjectsCompleted`, `GetObjectSystemPropertiesCompleted`, `GetPreviewFileNameCompleted`, `GetFolderFilesCompleted`, `GetFileFoldersCompleted`, `GetObjectXPGCompleted`, `SetObjectStructureCompleted`, `CreateElementFromXmlCompleted`, `CreateGraphicObjectFromXPGCompleted`, `CreateObjectFromXPGCompleted`, `DeleteObjectsCompleted`, `SetParentObjectCompleted`, `SetObjectCategoryCompleted`, `CopyFilesCompleted`, `GetServiceVersionCompleted`, `GetFoldersCompleted`, `GetClassifierParametersCompleted`, `GetObjectsCompleted`, `GetObjectsByIdCompleted`, `GetObjectsByParametersValueCompleted`, `GetObjectsForExpertiseCompleted`, `GetObjectsByParametersAndCategoryCompleted`, `GetObjectsByParametersAnd<wbr>CategoryByParentIdComplet<wbr>ed`, `GetObjectsByPageCompleted`, `GetObjectsTableCompleted`, `GetObjectHierarchyCompleted`, `SetObjectParentJSONCompleted`, `GetObjectUsersCompleted`, `GetObjectIdByUidCompleted`, `GetObjectUidByIdCompleted`, `GetFileIdByUidCompleted`, `GetObjectStringByIDCompleted`, `QueryObjectsCompleted`, `FindObjectsCompleted`, `FindObjectsSimpleCompleted`, `FindObjectsSimpleWithCountCompleted`, `FindObjectsPageCompleted`, `GetConnectionInfoCompleted`, `GetObjectParametersCompleted`, `GetObjectParametersAnyUserCompleted`, `GetObjectParameterValueCompleted`, `GetParameterValuesCompleted`, `GetObjectParameterValueByIdCompleted`, `GetObjectParameterValueAnyUserCompleted`, `GetParamCategoriesCompleted`, `SetObjectParameterCompleted`, `GetObjectsIdByParametersValueCompleted`, `GetObjectsUidByParametersValueCompleted`, `SetObjectParameterByIdCompleted`, `SetObjectCommentByIdCompleted`, `SetObjectNameCompleted`, `GetFileParametersCompleted`, `GetPreviewCompleted`, `GetObjectFileCompleted`, `GetObjectFileNCCompleted`, `GetObjectMSCompleted`, `GetObjectsMSCompleted`, `GetObjectMSByIdCompleted`, `GetObjectCompleted`, `GetObjectByIdCompleted`, `GetParamDefIdCompleted`, `GetObjectsIdByCategoryCompleted`, `GetObjectsIdByNameAndParentCompleted`, `GetObject2Completed`, `UploadObjectCompleted`
- `CADLibKernel.ObjectUpdate<wbr>Router.RouterService`
  - base: `System.Web.Services.Proto<wbr>cols.SoapHttpClientProtoc<wbr>ol`
  - events: `GetCatalogsAvailableToAut<wbr>henticatedUserCompleted`, `GetRolesOfAuthenticatedUserCompleted`, `GetRolesCompleted`, `CreateRolesCompleted`, `GetUsersCompleted`, `CreateUsersCompleted`, `UpdateUsersCompleted`, `DeleteUsersCompleted`
- `CADLibKernel.Collections.<wbr>ObservableCollectionEx`1`
  - base: `TypeSpec`
  - events: `PropertyChanged`, `CollectionChanged`, `System.ComponentModel.INo<wbr>tifyPropertyChanged.Prope<wbr>rtyChanged`, `System.Collections.Specia<wbr>lized.INotifyCollectionCh<wbr>anged.CollectionChanged`

### `CSAppServices.dll`

## 14. Практический вывод для разработки кнопок и команд

Для C#-плагина минимальный контур выглядит так:

```csharp
using CADLib;
using System.Windows.Forms;

public class MyPlugin : ICADLibPlugin
{
    public MenuStrip GetMenu()
    {
        var menu = new MenuStrip();
        var root = new ToolStripMenuItem("Мои проверки");
        root.DropDownItems.Add("Проверить параметры", null, (s, e) => MessageBox.Show("QC start"));
        menu.Items.Add(root);
        return menu;
    }

    public ToolStripContainer GetToolbars()
    {
        var c = new ToolStripContainer();
        var ts = new ToolStrip("My CADLib tools");
        ts.Items.Add(new ToolStripButton("QC", null, (s, e) => MessageBox.Show("QC start")));
        c.TopToolStripPanel.Controls.Add(ts);
        return c;
    }

    public void TrackInterfaceItems(InterfaceTracker tracker)
    {
        // Здесь обычно включают/выключают кнопки по состоянию БД, папки и выбранных объектов.
    }
}
```

Но для реального запуска нужно подтвердить формат регистрации плагина в конкретной поставке: путь загрузки DLL, имя класса entry point, наличие конфигурационного файла, требования к namespace и версиям зависимостей. Это следующий технический шаг.

## 15. Что проверять дальше

1. Найти в папке установки примеры C#-плагинов или конфигурационные файлы загрузки плагинов.
2. Проверить, какие DLL лежат рядом с `CSProject3D.dll` и `CADLibControls.dll`: версии должны совпадать.
3. Найти строки `RegisterPlugin`, `ICADLibPlugin`, `PluginsManager`, `FolderPlugin` в файлах установки.
4. Собрать минимальный C# plugin assembly и проверить, подхватывает ли его CADLib.
5. Отдельно сделать Python-скрипт “API explorer”: вывести методы объекта `Library`, `DBBrowser`, активного объекта и выделения.

## 16. Ограничения анализа

- Для `CSProject3D` и `CADLibControls` использованы XML-комментарии, поэтому назначение классов/методов достовернее.
- Для `CADLibKernel` и `CSAppServices` XML не было; назначение восстановлено по именам типов, сигнатурам, наследованию и уже проверенным Python-примерам.
- Без запуска внутри CADLib нельзя гарантировать, какие методы публичные, но не предназначены для внешнего использования.
- Для полноценного SDK нужны дополнительные проверки: сборка C#-плагина, запуск, подписка на события, создание меню/панели, проверка прав доступа.

---

# Часть B. Полный API-reference и PythonPlugin

## 1. Что это за контур API

Папка `PythonPlugin` показывает, что CADLib запускает Python-скрипты внутри приложения и передаёт им уже готовые глобальные объекты, например `Library`, `DBBrowser`, `CLMainForm`. Скрипты подключают .NET-сборки через `clr.AddReference(...)` и работают с классами CADLib как с .NET API.

Типовой импорт:

```python
import clr
clr.AddReference("CADLibKernel")
clr.AddReference("CSProject3D")
clr.AddReference("CSAppServices")
clr.AddReference("CADLibControls")
from CADLibKernel import *
```

Типовой доступ из примеров:

```python
Library.Dbcp.Database      # активная БД
CLMainForm.Text           # главное окно CADLib
DBBrowser.CurrentFolder   # текущая папка/узел браузера
```

## 2. Роли DLL в архитектуре

| DLL | Роль | Практическое значение | Уровень уверенности |
|---|---|---|---|
| `CADLibKernel.dll` | Ядро работы с БД CADLib: объекты, параметры, фильтры, категории, файлы, права, экспорт/импорт | Главный слой автоматизации через `Library` / `CADLibraryBase` | Высокий по сигнатурам и примерам | 
| `CSProject3D.dll` | 3D-проект, 3D-графика, выбор объектов, публикации, структуры проекта, mesh/shape | Работа с 3D-представлением объектов и CADLib-проектом | Высокий, есть XML |
| `CADLibControls.dll` | UI-слой: формы, диалоги, браузеры, редакторы параметров, фильтры интерфейса | Создание пользовательских интерфейсных надстроек, диалогов и команд | Высокий, есть XML | 
| `CSAppServices.dll` | Сервисный слой: подключение к БД, HTML-отчёты, публикация объектов, служебные DTO | Подключение, отчёты, SQL/DBMS-сервисные функции | Средний, XML нет |

## 3. Статистика разобранных сборок

| Сборка | Типов в DLL | XML members | Комментарии XML |
|---|---:|---:|---|
| `CSProject3D` | 1464 | 1449 | 1448 |
| `CADLibControls` | 1538 | 916 | 909 |
| `CADLibKernel` | 1374 | нет | назначение восстановлено по DLL |
| `CSAppServices` | 117 | нет | назначение восстановлено по DLL |

## 4. Основная карта API для практической автоматизации

| Задача | Основные классы / объекты | Что можно делать |
|---|---|---|
| Активная БД CADLib | `Library`, `CADLibKernel.CADLibraryBase`, `CSAppServices.DbConnectParameters` | Получать соединение, текущую БД, выполнять операции с объектами и параметрами | 
| Объекты БД | `CLibObjectInfo`, `ObjectData`, методы `CADLibraryBase` | Получать списки объектов, копировать, создавать дочерние объекты, удалять, менять имя/UID/положение |
| Фильтры и выборки | `CLibFilterItem`, `CreateFilter`, `GetObjectsList` | Создавать условия отбора по параметрам и категориям, получать наборы объектов |
| Параметры | `CLibParamDefInfo`, `CLibParamCategoryInfo`, `CLibParamValue`, `CreateParamDef`, `SetParameter` | Создавать определения параметров, категории, назначать значения объектам | 
| UI / браузер | `DBBrowser`, `CADLibControls`, формы `ParametersEditForm`, фильтр-диалоги | Обновлять активный объект, каталог, создавать диалоги и UI-команды |
| 3D-графика | `CSProject3D.CAD3DLibrary`, `CSMesh`, `MeshInfoEx`, `AddObject3DShape`, `Download3DMesh` | Выделять 3D-объекты, добавлять/удалять 3D-тела, читать/писать mesh |
| Отчёты и экспорт | `CSAppServices.CHTMLReport`, `ObjectPublisher`, `ExportParameters`, `ImportParameters` | Генерировать HTML-отчёты, экспортировать/импортировать параметры и объекты | 

## 5. Ключевые классы и назначение

### `CSProject3D.CAD3DLibrary`

**Сборка:** `CSProject3D`  
**Базовый тип:** `CADLib.CADLibrary`  
**Источник описания:** XML

**Назначение:** Класс базы данных приложений CADLib, работающих с трёхмерной графикой объектов
**Категории:** Library / ядро БД, 3D-графика / mesh, Публикации / проект

**Важные свойства:**
- `CurrentSession: int32`
- `IsEmptySelection: bool`
- `SingleSelectedObjectId: int32`
- `SelectedObjects: ET_15`
- `IsSingleSelection: bool`
- `SelectedObjectsCount: int32`
- `bObjectJustPicked: bool`
- `CurrentViewNode: System.Windows.Forms.TreeNode`
- `Is3DLibrary: bool`
- `IsCurrentViewAllObjects: bool`
- `UserTaggingNode: System.Windows.Forms.TreeNode`

**Практически важные методы:**
- `AppendObjectToSelectionbool(int32)` — Add object to library 3D selection set
- `AppendObjectsToSelectionbool(ET_15)` — Add objects to library selection set
- `SetSelectedObjectsbool(ET_15)` — Set library selected objects to set
- `SelectObjectsWithSameGraphicsAsSelectedint32()` — Выделяет объекты, имеющие то же графическое представление, что и выбранные объекты Если у объекта несколько сеток, ты выбираются объекты, имеющие тот же набор сеток без учёта взаиморасположения
- `GetCurrentViewObjectsET_15()` — Возвращает идентификаторы объектов текущего вида Количество объектов может быть больше, чем количество объектов в фильтре "Текущий вид" т.к. в результат включены объекты текущего вида плагинов
- `DeleteObject3DShapesint32(int32)` — Удаляет все трёхмерные тела, связанные с объектом БД
- `AddObject3DShapeint32(uint8[], ModelStudio.Graphics3D.CSVectorD3, uint8[], ModelStudio.Graphics3D.CSShapeInfo)` — Добавляет трёхмерное тело к объекту БД (объект указан в info.nShapeObjectId) Метод не ловит исключения. Добавление обёрнуто в транзакцию.
- `AddObject3DShapeint32(ModelStudio.Graphics3D.CSShapeInfo)` — Добавляет трёхмерное тело к объекту БД (объект указан в info.nShapeObjectId) Метод не ловит исключения. Добавление обёрнуто в транзакцию.
- `AddMeshUniqueint32(uint8[], float64, float64, float64, uint8[])` — Добавляет/находит в БД уникальную сетку
- `RetrieveMeshesByHashET_15(System.Collections.Generic.IEnumerable`1, void, MeshEntry, MeshEntry)` — Считывает сетку и информацию о ней, выбрав её по хэшу и экстентам

### `CSProject3D.Adapters.CADLibraryAdapter`

**Сборка:** `CSProject3D`  
**Базовый тип:** `System.Object`  
**Источник описания:** DLL / восстановлено по именам

**Назначение:** Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
**Категории:** Library / ядро БД, 3D-графика / mesh, Публикации / проект

**Методы для первичного изучения:**
- `GetSimpleParamDefsET_15()`
- `GetObjectParametersByValuesET_15(System.Collections.Generic.IEnumerable`1, void, CADLibKernel.CLibObjectInfo, int32)`

### `CADLib.ParametersEditForm`

**Сборка:** `CADLibControls`  
**Базовый тип:** `System.Windows.Forms.Form`  
**Источник описания:** DLL / восстановлено по именам

**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.
**Категории:** DBBrowser / UI, Параметры

**Важные свойства:**
- `Library: CADLib.CADLibrary`
- `ParamType: int32`
- `SelectedParameters: ET_15`
- `SingleSelectionMode: bool`
- `FileMode: bool`
- `CaptionMode: bool`
- `HasChanges: bool`
- `CategoryMode: bool`

**Методы для первичного изучения:**
- `CheckNewTypevoid(int32, string, string)`
- `OneSelParamET_15()`
- `UpdateToolbarvoid(bool)`
- `ShowParamsvoid()`
- `ParametersEditForm_Shownvoid(object, System.EventArgs)`
- `tbPropCat_Clickvoid(object, System.EventArgs)`
- `tbPropAlpha_Clickvoid(object, System.EventArgs)`
- `tbToggleExpand_Clickvoid(object, System.EventArgs)`
- `tbCaptions_Clickvoid(object, System.EventArgs)`
- `tbPropNew_Clickvoid(object, System.EventArgs)`
- `tbPropDel_Clickvoid(object, System.EventArgs)`
- `tbMoveTop_Clickvoid(object, System.EventArgs)`

### `CADLib.ListSelectDialog`1`

**Сборка:** `CADLibControls`  
**Базовый тип:** `System.Windows.Forms.Form`  
**Источник описания:** XML

**Назначение:** Общий диалог для выбора одного или нескольких элементов из списка
**Категории:** DBBrowser / UI

**Важные свойства:**
- `HasChanges: bool`
- `Prompt: string`
- `CheckBoxes: bool`
- `SelectedItems: ET_15`
- `Items: ET_15`
- `SelectedItem: !0`
- `CurrentItem: System.Windows.Forms.ListViewItem`

**Методы для первичного изучения:**
- `m_list_DrawItemvoid(object, System.Windows.Forms.Draw<wbr>ListViewItemEventArgs)`
- `HighlightItemvoid(System.Windows.Forms.ListViewItem, bool)`
- `m_list_ItemDragvoid(object, System.Windows.Forms.ItemDragEventArgs)`
- `m_list_DragOvervoid(object, System.Windows.Forms.DragEventArgs)`
- `m_list_DragEntervoid(object, System.Windows.Forms.DragEventArgs)`
- `m_list_DragDropvoid(object, System.Windows.Forms.DragEventArgs)`
- `AddItemsvoid(ET_15, System.Collections.Generic.IEnumerable`1)`
- `btnOK_Clickvoid(object, System.EventArgs)`
- `m_list_SizeChangedvoid(object, System.EventArgs)`
- `SwapItemsvoid(int32, int32)`
- `buttonMoveUp_Clickvoid(object, System.EventArgs)`
- `moveSelectedItemUpvoid()`

### `CADLib.CADLibrary`

**Сборка:** `CADLibControls`  
**Базовый тип:** `CADLibKernel.CADLibraryBase`  
**Источник описания:** DLL / восстановлено по именам

**Назначение:** Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
**Категории:** Library / ядро БД

**Важные свойства:**
- `IsDocs: bool`
- `CalcNameOnDemand: bool`
- `AppVersion: string`
- `ExceptionMode: eExceptionMode`
- `ProgressWindow: CADLib.ProgressForm`
- `SmallImages: System.Windows.Forms.ImageList`
- `LargeImages: System.Windows.Forms.ImageList`
- `ScriptsDirectory: string`
- `CollisionCatId: int32`
- `FolderPlugins: ET_15`
- `RootFilterWhere: string`
- `Rootfilters: ET_15`

**Методы для первичного изучения:**
- `MakeAppVersionInfostring(string, string)`
- `InitializeCSViewModelsvoid()`
- `DeleteObjectsET_15(System.Collections.Generic.List`1)`
- `DeleteObjectvoid(CADLibKernel.CLibObjectInfo)`
- `CADLibrary_OnRefreshvoid(UpdatedSet)`
- `createImageListSystem.Win<wbr>dows.Forms.ImageList(int32)`
- `GetScriptsDirstring()`
- `GetFileCacheDirstring()`
- `SubRefreshvoid()`
- `AddObjectNodeSystem.Windows.Forms.TreeNode(System.Windows.Forms.TreeView, System.Windows.Forms.TreeNodeCollection, CADLibKernel.CLibObjectInfo, bool, bool, int32)`
- `FindNodeByNodesCollection<wbr>System.Windows.Forms.Tree<wbr>Node(System.Windows.Forms.TreeNode, System.Windows.Forms.TreeNodeCollection)`
- `FindNodeByNodesCollection<wbr>System.Windows.Forms.Tree<wbr>Node(System.Windows.Forms.TreeView, System.Windows.Forms.TreeNodeCollection)`

### `CADLib.vmLibrary`

**Сборка:** `CADLibControls`  
**Базовый тип:** `NApp.ViewModel`  
**Источник описания:** DLL / восстановлено по именам

**Методы для первичного изучения:**
- `DB_ENABLEDvoid()`
- `DB_ENABLEDvoid(ET_15)`
- `OBJECT_ENABLEDvoid()`
- `initRecentDatabaseListvoid()`
- `initRecentDatabaseListvoid(object)`
- `openRecentDatabasevoid(DbConnectionEntry, bool)`

### `CADLibControls.Dialogs.Se<wbr>archingAndFiltering.frmFi<wbr>lter`

**Сборка:** `CADLibControls`  
**Базовый тип:** `NApp.WinForms.AppForm`  
**Источник описания:** DLL / восстановлено по именам

**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.
**Категории:** DBBrowser / UI, Фильтры / выборки

**Методы для первичного изучения:**
- `Disposevoid(bool)`
- `InitializeComponentvoid()`
- `initializeLocalizedPropertiesvoid()`

### `CADLibControls.Dialogs.Se<wbr>archingAndFiltering.frmMi<wbr>nidir`

### `CADLibKernel.CADLibraryBase`

**Сборка:** `CADLibKernel`  
**Базовый тип:** `System.Object`  
**Источник описания:** DLL / восстановлено по именам

**Важные свойства:**
- `Dbcp: CSAppServices.DbConnectParameters`
- `LibDirectory: string`
- `Is3DLibrary: bool`
- `IsConnected: bool`
- `Connection: LightweightDataAccess.DbConnectionInfo`
- `Transaction: LightweightDataAccess.DbTransactionInfo`
- `UserDisplayName: string`
- `CurrentUser: int32`
- `UserPermissions: bool[]`
- `IsCurrentUserAdministrator: bool`
- `IsCurrentUserInfoSec: bool`
- `ServerSpecificScriptsDir: System.IO.DirectoryInfo`

**Практически важные методы:**
- `CreateFilterCADLibKernel.<wbr>CLibCatalogFilterItem(string)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CreateFilterCADLibKernel.<wbr>CLibCatalogFilterItem(ET_15, System.Collections.Generic.List`1, void, CADLibKernel.CLibFilterItem, CADLibKernel.CLibCatalogFilterItem)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CreateFilterCADLibKernel.<wbr>CLibCatalogFilterItem(ET_15, System.Collections.Generic.List`1, void)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetObjectsListET_15(System.Collections.Generic.List`1, void)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetObjectsListET_15(System.Collections.Generic.List`1, void)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetObjectParameterValueobject(int32, string, ObjectQueryCache, bool)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `SetParameterint32(ET_15, System.Collections.Generic.List`1, void, CADLibKernel.CLibObjectInfo, string)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `SetObjectParametervoid(System.Guid, string, string, string)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CreateParamDefvoid(CADLibKernel.CLibParamDefInfo)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CreateParamDefint32()` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CopyObjectCADLibKernel.CLibObjectInfo(string, int32, int32, bool, bool)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CopyObjectCADLibKernel.CLibObjectInfo(string, int32, bool, int32, bool, bool, bool)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CopyObjectCADLibKernel.CLibObjectInfo(CADLibKernel.CLibObjectInfo, int32, bool)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CreateChildObjectCADLibKernel.CLibObjectInfo(CADLibKernel.CLibObjectInfo, string, int32)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `DeleteObjectvoid(int32)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `DeleteObjectvoid(CADLibKernel.CLibObjectInfo)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetParentObjectint32(int32, object)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetParentObjectint32(int32)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetRootObjectint32(int32)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetCategoriesListET_15()` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `GetCategoryInfoCADLibKern<wbr>el.CLibCategoryFullInfo(int32, bool, bool, bool)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `ExportParametersvoid(string)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `ExportParametersstring()` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `ImportParametersvoid(string, bool)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `ExportObjectsbool(ET_15, System.Collections.Generic.List`1, void, CADLibKernel.CLibObjectInfo, CADLibKernel.CADLibraryBase)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `Download3DMeshuint8[](int32, int32, ModelStudio.Graphics3D.CSVectorD3*)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `Download3DMeshvoid(int32, int32, System.IO.Stream, ModelStudio.Graphics3D.CSVectorD3*)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `Download3DMeshesBlobuint8[](int32[], int32, int32)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `CheckUserPermissionsvoid()` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.

### `CADLibKernel.CLibFilterItem`

**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.
**Категории:** Фильтры / выборки

**Практически важные методы:**
- `UpdateObjectConditionstring(CADLibKernel.CLibFilterItem, string)` — Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.
- `GetDateFilterExpressionstring(LightweightDataAccess.EServerType, string, string)` — Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

### `CADLibKernel.CLibParamDefInfo`

**Назначение:** Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
**Категории:** Параметры

**Практически важные методы:**
- `MakeCorrectNamebool(string*)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `UpdateExtendedDatavoid(CADLibKernel.CADLibraryBase)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `AddParamDefIfNotExistsbool(ET_15, System.Collections.Generic.List`1, void, CADLibKernel.CLibParamDefInfo, string, string)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `AddParamDefvoid(ET_15, System.Collections.Generic.List`1, void, CADLibKernel.CLibParamDefInfo, string, string)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.

### `CADLibKernel.CLibParamCategoryInfo`

### `CADLibKernel.CLibObjectInfo`

**Назначение:** Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура.
**Категории:** Объекты

**Важные свойства:**
- `Name: string`
- `StatusName: string`
- `IsRoot: bool`
- `LocalModifiedDate: System.DateTime`

**Практически важные методы:**
- `CloneCADLibKernel.CLibObjectInfo()` — Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура.
- `ReloadDatavoid(System.Data.IDataRecord)` — Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура.
- `StatusToStringstring(int32)` — Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура.

### `CADLibKernel.CLibParamValue`

**Важные свойства:**
- `Value: object`

**Методы для первичного изучения:**
- `ToStringstring()`

### `CADLibKernel.ObjectData`

### `ModelStudio.Graphics3D.CSMesh`

**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.
**Категории:** 3D-графика / mesh, Публикации / проект

**Важные свойства:**
- `VersionLoad: float32`
- `Vertices: ET_15`
- `Item: ModelStudio.Graphics3D.CSVertexCompressed[int32]`
- `Faces: int32`
- `Index: ET_15`
- `Materials: ET_15`
- `MaterialIndex: ET_15`
- `CurvesGraphics: ModelStudio.Graphics3D.CSCurves`
- `CurvesIsolines: ModelStudio.Graphics3D.CSCurves`
- `Name: string`
- `IntroString: string`
- `IsEmpty: bool`

**Методы для первичного изучения:**
- `SetCurrentMaterialvoid(ModelStudio.Graphics3D.CSMaterial)`
- `GetCurrentMaterialuint16()`
- `AddCurvevoid(ModelStudio.Graphics3D.CSCurve, bool)`
- `AddTriangleFacevoid(ModelStudio.Graphics3D.CSVector3, ModelStudio.Graphics3D.CSVector3, ModelStudio.Graphics3D.CSVector3, bool)`
- `NormalizeGraphicsModelStu<wbr>dio.Graphics3D.CSMatrixD(ModelStudio.Graphics3D.CSVector3*)`
- `NormalizeGraphicsModelStu<wbr>dio.Graphics3D.CSMatrixD()`
- `TransformByvoid(ModelStudio.Graphics3D.CSMatrixD)`
- `ReduceToNumVerticesbool(int32)`
- `CalculateBoundingBoxModel<wbr>Studio.Graphics3D.CSBox()`
- `CalculateExtentsModelStud<wbr>io.Graphics3D.CSExtents(ModelStudio.Graphics3D.CSMatrixD)`
- `IntersectBoxbool(ModelStudio.Graphics3D.CSBox)`
- `AddVertexint32(ModelStudio.Graphics3D.CSVertexCompressed)`

### `CADLibKernel.MeshInfoEx`

**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.
**Категории:** 3D-графика / mesh

### `CSAppServices.DbConnectParameters`

**Сборка:** `CSAppServices`  
**Базовый тип:** `System.Object`  
**Источник описания:** DLL / восстановлено по именам

**Назначение:** Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
**Категории:** Параметры, Подключение / сервисы

**Важные свойства:**
- `convertUserNameToLowerCase: bool`
- `NormUserName: FLib.Str`
- `UseOdbc: bool`
- `IsOSAuthentication: bool`
- `IsAuthenticationDefined: bool`

**Практически важные методы:**
- `CreateCSAppServices.DbConnectParameters(LightweightDataAccess.EServerType, FLib.Str, FLib.Str, FLib.Str, FLib.Str, string)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `CreateCSAppServices.DbConnectParameters(FLib.Str, FLib.Str, FLib.Str)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `CreateWithOSAuthCSAppServ<wbr>ices.DbConnectParameters(bool, LightweightDataAccess.EServerType, FLib.Str, FLib.Str, string, ET_15)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `CreateWithDbmsAuthCSAppSe<wbr>rvices.DbConnectParameter<wbr>s(bool, LightweightDataAccess.EServerType, FLib.Str, FLib.Str, FLib.Str, FLib.Str, string, ET_15)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `CreateConnectionLightweig<wbr>htDataAccess.DbConnection<wbr>Info()` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `MakeConnectionStringFLib.Str()` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `MakeConnectionStringFLib.Str(CSAppServices.DbName)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `MakeNativeConnectionStringFLib.Str()` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `MakeNativeConnectionStringFLib.Str(CSAppServices.DbName)` — Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.
- `MakeOSAuthenticationCSApp<wbr>Services.DbConnectParamet<wbr>ers()` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `MakeDbmsAuthenticationCSA<wbr>ppServices.DbConnectParam<wbr>eters(CSAppServices.DbUser, CSAppServices.DbPassword)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.

### `CSAppServices.ObjectPublisher`

**Назначение:** Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы.
**Категории:** Объекты, Подключение / сервисы

**Практически важные методы:**
- `PublishObjectsvoid(LightweightDataAccess.EServerType, LightweightDataAccess.DMakeDbCommandInfo, CSAppServices.CHTMLReport, ET_15)` — Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы.
- `WriteObjectRowsint32(string, LightweightDataAccess.DMakeDbCommandInfo, CSAppServices.CHTMLReport)` — Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы.
- `GetObjectParamsSelQuerystring(LightweightDataAccess.EServerType, int32, ET_15, System.Collections.Generic.List`1, void)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.
- `GetObjectParamsSelQuery2string(LightweightDataAccess.EServerType, int32, ET_15, System.Collections.Generic.List`1, void)` — Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.

### `CSAppServices.CHTMLReport`

**Назначение:** Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
**Категории:** Отчёты / HTML / экспорт, Подключение / сервисы

**Практически важные методы:**
- `BeginTablevoid(int32)` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `BeginRowvoid()` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `BeginRowvoid(string)` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `WriteCellvoid(string)` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `WriteCellvoid(string, string)` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `WriteBoldCellvoid(string)` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `WriteHeadervoid(string, int32)` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `WriteTextvoid(string)` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.
- `Closevoid()` — Формирование отчётов, экспорт/импорт данных и документирование содержимого БД.

### `CSAppServices.CLibParamDefInfo`

## 6. Подробные XML-описания `CSProject3D` и `CADLibControls`

В этом разделе приведены классы и члены, для которых поставка содержит XML-комментарии. Это наиболее надёжная часть справочника.

### 6.1. `CSProject3D`

#### `CSProject3D.Properties.Resources`
**Назначение:** A strongly-typed resource class, for looking up localized strings, etc.

| Член | Тип | Описание |
|---|---|---|
| `ResourceManager` | свойство | Returns the cached ResourceManager instance used by this class. |
| `Culture` | свойство | Overrides the current thread's CurrentUICulture property for all resource lookups using this strongly typed resource class. |
| `acad` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `accept` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `account_asm` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `account_obj` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Actions_mail_mark_task_icon` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Actions_view_calendar_timeline_icon` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `ActualSize` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `AddFilter` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `AddParams` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `addScript` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `alphaMode` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `AlphaSort` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `AngleDim` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `application_blue` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `applications_blue` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `applyLib` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `arrow_switch` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `arrowLeftGreen` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `basket_add` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `basket_pls` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Binoculars` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `bld_group` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `bld_section` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `bld_subgroup` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `bld_subsection` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `bld_subtype` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `bld_type` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `block` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_Back` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_Bottom` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_Front` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_Left` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_NEB` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_NEU` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_Right` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_SEB` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_SET` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_Top` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_WNB` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_WNU` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_WSB` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `box_WST` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `BuilderDialog_AddAll` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `BuilderDialog_RemoveAll` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `building` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `building1` | свойство | Looks up a localized resource of type System.Drawing.Icon similar to (Icon). |
| `BuildingBlock` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `BuildingSection` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `BuildingShow` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cable` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CableCore` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CADLib16` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cam` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cameraAdd` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cameraLoad` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cameraRemove` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cameraSave` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cameraScript` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| ... | ... | Ещё 281 членов класса опущены в основной таблице, см. полный машинный индекс ниже. |

#### `CSProject3D.BuildingsHier<wbr>archyPlugin.CHierarchyObj<wbr>ect.HierarchyLevelType`
**Назначение:** Поддерживаемые виды объектов иерархии

| Член | Тип | Описание |
|---|---|---|
| `UnknownLevel` | поле | Ошибка определения уровня |
| `Site` | поле | номер уровня иерархии площадки |
| `Building` | поле | номер уровня иерархии здания |
| `Floor` | поле | номер уровня иерархии этажа |
| `Room` | поле | номер уровня иерархии помещения |
| `Block` | поле | номер уровня иерархии блока |
| `Stage` | поле | номер уровня иерархии стадии |
| `Disciplines` | поле | номер уровня иерархии разделов |
| `Discipline` | поле | номер уровня иерархии раздела |
| `Chapter` | поле | номер уровня иерархии подраздела |
| `Part` | поле | номер уровня иерархии части |
| `GroupBuildings` | поле | номер уровня иерархии группа зданий |
| `System` | поле | номер уровня иерархии систем |
| `SubSystem` | поле | номер уровня иерархии подсистем |
| `Equipment` | поле | номер уровня иерархии оборудование |
| `Line` | поле | номер уровня иерархии линий |
| `GroupEquipment` | поле | номер уровня группы оборудования |
| `Union` | поле | номер уровня Штуцера |
| `TerminalBlock` | поле | номер уровня Клеммник |
| `Terminal` | поле | номер уровня Клемма |
| `Pipeline` | поле | номер уровня трубопровод |
| `PipelineAxis` | поле | номер уровня участка |
| `Cable` | поле | номер уровня кабеля |
| `CableCore` | поле | номер уровня жилы |
| `Connection` | поле | номер уровня подключения |
| `LinearEquipment` | поле | номер уровня подключения |
| `PiplineFitting` | поле | номер уровня подключения |
| `SituationFolder` | поле | номер уровня папки ситуация |
| `SystemsFolder` | поле | номер уровня папки система |
| `ConstructionsFolder` | поле | номер уровня папки конуструкции |
| `DifferentFolder` | поле | номер уровня папки разное |
| `EquipmentLink` | поле | номер уровня ссылка на оборудование |
| `FittingsLink` | поле | номер уровня ссылка на арматуру |
| `LinearEquipmentLink` | поле | номер уровня ссылка на линейное оборудование |
| `Control` | поле | номер уровня контроля |
| `Section` | поле | номер уровня раздел |
| `SubSection` | поле | номер уровня пождраздел |
| `Group` | поле | номер уровня группа |
| `SubGroup` | поле | номер уровня подгруппа |
| `Type` | поле | номер уровня тип |
| `SubType` | поле | номер уровня подтип |
| `AccountAsm` | поле | номер уровня Учетная сборка |
| `AccountObj` | поле | номер уровня Учетный объект |
| `Segment` | поле | номер уровня Сегмент |
| `Reducer` | поле | номер уровня Переход |
| `Cabinet` | поле | номер уровня Шкаф |
| `Device` | поле | номер уровня Прибор |
| `DeviceBlock` | поле | номер уровня Блок приборов |
| `SectionOfCabinets` | поле | номер уровня Секция |
| `Bus` | поле | номер уровня Шина |
| `RoomArea` | поле | номер уровня Зона помещения |
| `BuildingBlock` | поле | номер уровня Блок зданий/сооружений |
| `MultiSectionBuilding` | поле | номер уровня Многосекционное здание/сооружение |
| `BuildingSection` | поле | номер уровня Секция зданий/сооружений |
| `RoomGroup` | поле | номер уровня Группа помещений |
| `Elevation` | поле | номер уровня Уровень |

#### `CSProject3D.UserTagging.Vector2d.Shapes`
**Назначение:** Gestisce l'insieme degli oggetti vettoriali

| Член | Тип | Описание |
|---|---|---|
| `CopyMultiSelected(System.Single,System.Single)` | метод | Copy all selected Items |
| `CpSelected` | метод | returns a Copy of selected element |
| `CopySelected(System.Single,System.Single)` | метод | Copy selected Item |
| `RemoveSelectedShapes` | метод | Remove objects |
| `groupSelected` | метод | Grup selected objs |
| `deGroupSelected` | метод | Grup selected objs |
| `getSelectedArray` | метод | Returns an array with the selected item. Used for property grid. |
| `getSelectedList` | метод | Returns a m_shapes with the selected items. Used for SaveObj. |
| `setList(System.Collections.Generic.List{CSProject3D.UserTagging.V<wbr>ector2d.Element2dBase})` | метод | Returns a m_shapes with the selected items. Used for SaveObj. |
| `BringSelToFront` | метод | 2 front |
| `SendSelToBack` | метод | 2 back |
| `deSelect` | метод | Deselect |
| `Draw(System.Drawing.Graphics,System.Single,System.Single,System.Single)` | метод | Draw all shapes |
| `DrawUnselected(System.Drawing.Graphics,System.Single,System.Single,System.Single)` | метод | Draw all Unselected shapes |
| `DrawUnselected(System.Drawing.Graphics)` | метод | Draw all Unselected shapes |
| `DrawSelected(System.Drawing.Graphics,System.Single,System.Single,System.Single)` | метод | Draw all Selected shapes |
| `DrawSelected(System.Drawing.Graphics)` | метод | Draw all Selected shapes |
| `addPoly(System.Single,System.Single,S...` | метод | Adds Polygon | 
| `addGraph(System.Single,System.Single,...` | метод | Adds Graph | 
| `addColorPoinySet(System.Single,System...` | метод | Adds Polygon | 
| `addRect(System.Single,System.Single,System.Single,System.Single,System.Drawing.Color,System.Drawing.Color,System.Single,System.Boolean)` | метод | Adds Rect |
| `addLink(System.Single,System.Single,S...` | метод | Adds Link | 
| `addArc(System.Single,System.Single,System.Single,System.Single,System.Drawing.Color,System.Drawing.Color,System.Single,System.Boolean)` | метод | Adds Arc |
| `addLine(System.Single,System.Single,System.Single,System.Single,System.Drawing.Color,System.Single,System.Drawing.Drawing2D.LineCap)` | метод | Adds Line |
| `addVLine(System.Single,System.Single,System.Single,System.Single,System.Drawing.Color,System.Single)` | метод | Adds VLine |
| `addOLine(System.Single,System.Single,System.Single,System.Single,System.Drawing.Color,System.Single)` | метод | Adds OLine |
| `addTextBox(System.Single,System.Singl...` | метод | Adds TextBox | 
| `addSimpleTextBox(System.Single,System...` | метод | Adds SimpleTextBox | 
| `addRRect(System.Single,System.Single,System.Single,System.Single,System.Drawing.Color,System.Drawing.Color,System.Single,System.Boolean)` | метод | Adds RoundRect |
| `addImgBox(System.Single,System.Single,System.Single,System.Single,System.String,System.Drawing.Color,System.Single)` | метод | Adds ImageBox |
| `addEllipse(System.Single,System.Single,System.Single,System.Single,System.Drawing.Color,System.Drawing.Color,System.Single,System.Boolean)` | метод | Adds Ellipse |
| `click(System.Single,System.Single,System.Windows.Forms.RichTextBox)` | метод | Selects last shape containing x,y |
| `multiSelect(System.Single,System.Single,System.Single,System.Single,System.Windows.Forms.RichTextBox)` | метод | Selects all shapes in imput rectangle |

#### `CSProject3D.Viewer3DCtrl`
**Назначение:** Компонент просмотра трёхмерной графики из базы данных

| Член | Тип | Описание |
|---|---|---|
| `PopupMenuOpening` | событие | Событие, позволяющее изменить текст объекта вверху меню и вызывающиеся перед открытием меню, но после определения ContextMenuLastObject и ContextMenuLastEntity, что позволяет изменить меню в зависимости от выбранного объекта | 
| `ContextMenuLastObject` | свойство | Объект БД (может быть кастомный) на котором было последний раз активированно контекстное меню |
| `ContextMenuLastEntity` | свойство | Сущность на которой последней раз было активированно контекстное меню |
| `multiuserUI` | свойство | Возвращает (если надо создаёт) окно многопользовательской работы |
| `SetVisibleLandSurfaces(System.Int32[])` | метод | Устанавливает набор видимых поверхностей Загружает недостающие поверхности и удаляет пропавшие из списка видимости Параметры: arrLands — Массив идентификаторов поверхностей для показа idLand[] | 
| `SetSelectedLandSurfaces(System.Int32[])` | метод | Устанавливает набор выделенных поверхностей Снимает выделение со всех остальных поверхностей Параметры: arrLands — Массив идентификаторов поверхностей для выделения idLand[] | 
| `FocusOnLandSurfaces(System.Int32[])` | метод | Фокусирует камеру на загруженных поверхностях земли из списка Параметры: arrLands — Массив идентификаторов поверхностей для фокусировки idLand[] | 
| `ForbidIfNotInitialized` | метод | Проверяет инициализирован ли трёхмерный движок и выдайт сообщение если нет Возвращает: False усли нет |
| `SetWorldUnselectedDecoration(System.N...` | метод | Изменяет остальной мир на время выделения. Если указать A составляющую=0, то мир прорисовываться не будет (скрыть) Параметры: color — Цвет (опционально); bWireFrame — Выводить ли проволочную модель | 
| `SetObjectsCorrection(System.Collectio...` | метод | Добавляет правило коррекции объектов - степень прозрачности и управление видимостью Параметры: objectsIds — Объекты; complexColor — новый цвет (Empty - отменить коррекцию, прозрачность в цвете, Transparent - скрыть, Alpha,0,0,0 - полупрозрачный); bApplyToRender — сразу применится; bAddToCorrectionList — будет активно при последающих загрузках модели; bRedraw — перерисовывать ли 3D | 
| `SetObjectsCorrection(System.Collectio...` | метод | Добавляет правило коррекции объектов - степень прозрачности и управление видимостью Параметры: objectsIds — Объекты; fAlpha — степень прозрачности (0.0-скрыть 1.0-показать); bApplyToRender — сразу применится; bAddToCorrectionList — будет активно при последающих загрузках модели | 
| `ShowOnModel3D(System.Int32[])` | метод | Показ на модели набора объектов |
| `ShowClouds3D(System.Int32[])` | метод | Показ набора облаков |
| `HideClouds3D(System.Int32[])` | метод | Скрытие набора облаков |
| `SetCloudColor(System.Int32[],System.Drawing.Color,System.Boolean,System.Boolean)` | метод | Изменение цвета |
| `SetAllObjectsCorrection(System.Drawin...` | метод | Применяет корректировку материала ко всем загруженным объектам Параметры: newColor — новый цвет; fNewAlpha — прозрачность; bRedraw — перерисовывать ли модель | 
| `SetAllObjectsCorrection(System.Drawin...` | метод | Применяет корректировку материала ко всем загруженным объектам Параметры: complexColor — новый цвет (Empty - отменить коррекцию, прозрачность в цвете, Transparent - скрыть, Alpha,0,0,0 - полупрозрачный); bRedraw — перерисовывать ли модель | 
| `SetLoadObjectsCorrection(System.Collections.Generic.IEnumerable{System.Int32},System.String,System.Boolean,System.Boolean)` | метод | Will be applied after reload Параметры:  |
| `Clear` | метод | Clear 3D model representation |
| `Refresh3D` | метод | Reload previous request from DB |
| `AskObjectsPickStart(System.Object,Sys...` | метод | Запускает диалог выбора объектов, при выборе каждого объекта вызывается OnObjectPicked Обычно OnObjectPicked добавляет выбраный объект в выбор Library, т.о. можно использовать объект библиотеки для учёта выбранного Параметры: strMessage — Текст для показа в диалоге; bOneObject — Необходим ли один объект (диалог закроется автоматически после его выбора); onDialogClosed — Делегат, вызываемый после закрытия диалога; bOkButton — Наличие кнопки ОК в диалоге (используется, если необходимое число объектов для выбора заранее не известно) | 
| `OnRequestEdit2dDrawing` | событие | Действие, говорящее клиентам, что необходимо активировать редактирование/просмотр 2D Если object == null - деактивировать |
| `RequestEdit2dDrawing(System.Object)` | метод | Сам компонент ничего не делает, а лишь паредаёт вызов данного метода подписчикам OnRequestEdit2dDrawing Параметры: tag2d — Объект для рисования 2D | 
| `SetAdditionalFilter(System.String,Sys...` | метод | Добавляет/обновляет/удаляет дополнительный именованный фильтр объектов для загрузки (сделано для структурных объектов, т.к. фильтр не должен пересекаться с основным) Для удаления 3D объектов, загруженных по фильтру необходимо передать пустой фильтр. Также имеется возможность управлять разрешением на ограничения пространства для объектов, загруженных по фильтру. Параметры: strFilterName — Имя фильтра (идентификатор); strFilter — Фильтр или пустая строка; bForbidClipping — Запретить обрезать объекты данного фильтра ClipBox-ом | 
| `GetAdditionalFiltersStatus` | метод | Возвращает список активных дополнительных фильтров и их статус (загружены ли объекты) Возвращает: Список дополнительных фильтров |
| `CheckCalcCancel(System.String,System.Boolean)` | метод | Спросить, нужно ли остановить работу (например, если найдено очень много объектов для проверки) Параметры:  |

#### `CSProject3D.CAD3DLibrary`
**Назначение:** Класс базы данных приложений CADLib, работающих с трёхмерной графикой объектов

| Член | Тип | Описание |
|---|---|---|
| `bObjectJustPicked` | свойство | true while in on axNWEViewerCtl1_OnObjectPicked methos |
| `AppendObjectToSelection(System.Int32)` | метод | Add object to library 3D selection set Параметры: nObj — Object's ID Возвращает: true if selection have changed |
| `AppendObjectsToSelection(System.Colle...` | метод | Add objects to library selection set Параметры: arrObj — ids to add Возвращает: true if selection have changed | 
| `SetSelectedObjects(System.Collections...` | метод | Set library selected objects to set Параметры: arrObj — New selected objects set Возвращает: true if selection have changed | 
| `SelectObjectsWithSameGraphicsAsSelected` | метод | Выделяет объекты, имеющие то же графическое представление, что и выбранные объекты Если у объекта несколько сеток, ты выбираются объекты, имеющие тот же набор сеток без учёта взаиморасположения Возвращает: Количество добавленных к выделению объектв | 
| `DoAppendObjectToSelection(System.Int3...` | метод | Add Object to selection Параметры: nObj — ID; bRaiseEvent — Should this function rise event Возвращает: true if selection have changed | 
| `DoAppendObjectsToSelection(System.Col...` | метод | Smart appending objects and event raising Параметры: arrObj — objects set Возвращает: true if selection have changed | 
| `SetEmptySelection` | метод | Clear selection Возвращает: true if selection have changed |
| `SetSingleSelection(System.Int32)` | метод | Set selection to only one object Параметры: nObj — Selected object Возвращает: true if selection have changed |
| `GetCurrentViewObjects` | метод | Возвращает идентификаторы объектов текущего вида Количество объектов может быть больше, чем количество объектов в фильтре "Текущий вид" т.к. в результат включены объекты текущего вида плагинов | 
| `IsCurrentViewAllObjects` | свойство | Показывает ли узел текущий вид все корневые объекты |
| `CreateLibObjectFromUnmanaged(mstManag...` | метод | Преобразует неуправляемый объект библиотеки в управляемый Параметры: objInfo — Неуправляемый объект CLibObjectInfo Возвращает: Управляемый объект с теми же данными | 
| `DeleteObject3DShapes(System.Int32)` | метод | Удаляет все трёхмерные тела, связанные с объектом БД Параметры: nObjectId — Идентификатор объекта БД Возвращает: Количество удалённых тел | 
| `AddObject3DShape(System.Byte[],ModelS...` | метод | Добавляет трёхмерное тело к объекту БД (объект указан в info.nShapeObjectId) Метод не ловит исключения. Добавление обёрнуто в транзакцию. Параметры: graphicsData — Бинарные данные, содержащие трёхмерное тело/кривые в формате *.msm; ptBase — базовая точка сетки (вектор, обратный нормализации сетки), XPG графика приводится без нормализации, таким образом это вектор - разница между XPG и сеткой; xmlData — XPG графика сетки в ненормализованном виде (точка вставки - ноль графики); info — Информация о расположении тела в пространстве (nGrahicsId игнорируется, а после добавления актуализируется, дата модификации актуализируется) Возвращает: В случае успеха идентификатор тела, иначе 0 | 
| `AddMeshUnique(System.Byte[],System.Do...` | метод | Добавляет/находит в БД уникальную сетку Параметры: mesh — сетка для добавления/поиска; ptBaseX — базовая точка сетки (вектор, обратный нормализации сетки), XPG графика приводится без нормализации, таким образом это вектор - разница между XPG и сеткой; ptBaseY — базовая точка сетки (вектор, обратный нормализации сетки), XPG графика приводится без нормализации, таким образом это вектор - разница между XPG и сеткой; ptBaseZ — базовая точка сетки (вектор, обратный нормализации сетки), XPG графика приводится без нормализации, таким образом это вектор - разница между XPG и сеткой; xpg — xpg данные для добавления; connection — подключение Возвращает: idMesh новой или существующей сетки | 
| `RetrieveMeshesByHash(CSProject3D.CAD3...` | метод | Считывает сетку и информацию о ней, выбрав её по хэшу и экстентам Параметры: entryForSearch — информация о сетке, которую необходимо найти; fTol — точность с которой будут искаться похожие экстенты; bReadMesh — читать ли данные сетки; bReadXpg — читать ли данные XPG | 
| `AddMeshToDb(CSProject3D.CAD3DLibrary....` | метод | Добавляет сетку с информацией о ней в таблицу Mesh entry.nIdMesh должен содержать свободный ID для сетки Параметры: entry — информация о сетке с данными Возвращает: entry.nIdMesh | 
| `AddObject3DShape(ModelStudio.Graphics...` | метод | Добавляет ссылку на сетку к объекту БД (объект указан в info.nShapeObjectId) Идентификатор существующей сетки на которую необходимо ссылаться idMesh также указан в info Метод не ловит исключения Параметры: info — Информация о расположении тела в пространстве (nGrahicsId игнорируется, а после добавления актуализируется, дата модификации актуализируется) Возвращает: В случае успеха идентификатор тела, иначе 0 | 
| `UpdateObject3DShapeInfo(System.Collec...` | метод | Обновляет информацию об экземплярах трёхмерной графике объекта Параметры: arrInfo — Коллекция актуальной информации для применения к БД | 
| `SYS3D_X` | поле | Системные параметры для 3D Параметры: strParamName — Имя параметра Возвращает: идентификатор |

#### `CSProject3D.GridManager`
**Назначение:** Класс плагина менеджера координатных сеток: Создаёт (оборачивает) выборку координатных сеток с именем GridsFolderName Позволяет управлять видимостью координатных сеток и ограничивать по ним пространство +Добавляет пункт меню "Ограничить пространство" в контекстное меню 3D при клике по сетке

| Член | Тип | Описание |
|---|---|---|
| `GridsFolderName` | поле | Имя специальной выборки с осями |
| `GridsDataGroup` | поле | Категория координатных осей - имя группы структурных данных Значение параметра CADLibraryBase.SYS_CATEGORY_GROUP |
| `VISIBLE_GRIDS_PARAM` | поле | Имя параметра базы данных (пользовательского) для хранения включенных сеток |
| `Library` | свойство | Библиотека главной формы |
| `VisibleGrids` | поле | Список видимых координатных сеток (сохраняется в пользовательских настройках БД) |
| `MainForm3D` | свойство | Главная форма приложения |
| `#ctor(CSProject3D.MainForm)` | метод | Конструктор плагина с авторегистрацией Параметры: mainForm3D — Главная форма МиА |
| `LoadVisibleGrids` | метод | Загружает из пользовательских настроек БД список включенных сеток Сетки из списка показывает в 3D за счёт добавления именованных выборок |
| `GetGridsFolder(CSProject3D.CAD3DLibra...` | метод | Находит или создаёт специальную выборку для объектов осей. Выборке присваивается имя GridsFolderName, которое затем используется для особенной обработки данного каталога (рисование иконки, контекстное меню). Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Получение объекта координатной сетки CCoordinateGrid по объекту БД Параметры: libObject — Исходные объект бибилотеки; strStructGroup — Группа даных структурных объектов Возвращает: объект сетки CCoordinateGrid или null, в случае, если libObject-другой объект | 
| `SwitchGridsVisibility(System.Collecti...` | метод | Изменяет видимость указанных координатных сеток Параметры: grids — Список сеток; bVisible — Показать или скрыть | 
| `GetObjectMenuItems(CADLibKernel.CLibC...` | метод | Модифицирует контекстное меню объектов окна БД Параметры: folder — Активный каталог; selection — Выбранные объекты; menu — Меню для модификации Возвращает: Всегда пустое множество, т.к. изменяется само меню | 
| `GetAdditionalCurrenViewObjects` | метод | Получает дополнительные объекты из текущего вида Имеет значение для таких плагинов как "поверхности земли", которые показывают дополнительные объекты во вьювере, но они не отображаются в узле "Текущий вид". Тем не менее данные объекты должны быть обработаны во время выбора опции "Текущий вид" при экспорте или проверке коллизий. Возвращает: Идентификаторы дополнительных объектов, показанные плагином | 

#### `CSProject3D.ModelRepresen<wbr>tation.ModelRepresentatio<wbr>n`
**Назначение:** Класс представления модели. Умеет изменять внешний вид модели (раскраска) на основе заданных правил

| Член | Тип | Описание |
|---|---|---|
| `ModelRepresentationCatIcon` | поле | Имя иконки категории представления моделей |
| `Name` | свойство | Имя представления |
| `Comment` | свойство | Описание представления |
| `Library` | свойство | Объект библиотеки для работы с представлением |
| `SelectionType` | поле | Источник выборок для представления модели |
| `#ctor(System.String,CADLib.CADLibrary)` | метод | Создаёт пользовательское представление модели с указанием имени Параметры: strName — Имя представления модели |
| `#ctor(System.String,System.String,CAD...` | метод | Создаёт пользовательское представление модели с указанием имени и пути в дереве Параметры: strName — Имя представления модели | 
| `SaveToDB(CADLibKernel.CLibObjectInfo)` | метод | Сохраняет представление модели в БД Параметры: libObject — Объект БД (если необходимо обновить данные) Возвращает: Объект БД представления модели | 
| `LoadFromDB(CADLibKernel.CLibObjectInfo)` | метод | Загружает представление модели из объекта БД Параметры: libObject — Объект БД Возвращает: true, если данные успешно загружены | 
| `SaveToElement(CADLibKernel.CSElement)` | метод | Сериализация в CElement Параметры: dest — Элемент назначения |
| `LoadFrom(CADLibKernel.CSElement)` | метод | Десериализация из CElement Параметры: src — Исходный элемент |
| `Clear` | метод | Очистка представления |
| `m_сolors` | поле | Вхождения профиля представления модели |
| `CreateDefaultColorProfile` | метод | Создание и добавления строки "Прочие объекта" Данная строка всегда должна в профиле и применяется к объектам, не попавшим в выборки |

#### `CSProject3D.CCoordinateGrid`
**Назначение:** Объект координатной сетки (осей) Имеются методы сохранения/загрузки объекта (иерархическая запись) в БД с параметрами

| Член | Тип | Описание |
|---|---|---|
| `InitChildren(CADLib.CADLibrary)` | метод | Считывает подчинённые объекты типа CAxis Параметры: lib — Библиотека |
| `CLIP_BOX_LIMIT_PARAM` | поле | Имя параметра, в котором хранится конфигурация ограничения пространства |
| `ActivateSpaceClipping(CADLibKernel.CL...` | метод | Активирует режим ограничения пространства 3D Перед этим показывается диалог с настройками ограничения пространства (по каким осям...) Настройки, заданные в диалоге сохраняются либо непосредственно в объекте сетке (this), либо в исходном объекте (подразумевается, что с ним связана сетка, но настройки свои). Параметры: settingsSourceObject — Объект для ассоциации параметров обрезания или null, чтобы использовать параметры текущей сетки | 
| `Manager` | свойство | Управляющий объект |
| `Children` | свойство | Оси сетки (3: X,Y,Z) |
| `Node` | свойство | Информация об объекте в дереве объектов |
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный метод вызывается после применения объекта к узлу дерева (если было) Параметры: tree — Дерево объектов; node — Узел с которым ассоциирован данный объект | 
| `IsOn` | метод | Является ли координатная сетка видимой Возвращает: true, если поверхность (родитель или все подчинённые поверхности, если есть, видимы) |
| `SetOn(System.Boolean,System.Boolean)` | метод | Изменить видимость координатной сетки Параметры: bOn — видимость; bForbidClipping — запретить обрезать данную сетку ClipBox-ом |
| `TryExpandObjectNode(System.Windows.Fo...` | метод | Раскрывает узел объекта Параметры: treeNode — Узел дерева родительского объекта (вызываемого) Возвращает: возвращает true - если плагин заполнил дерево, иначе false - дерево заполняется стандартными средствами | 
| `UpdateTreeIcon` | метод | Обновляет иконку дерева после изменения видимости объекта |

#### `CSProject3D.Collisions.Co<wbr>llisionsTree.CollisionsFi<wbr>lter`
**Назначение:** Класс - обёртка над фильтром коллизий Может быть два режима: фильтр по условиям (Conditions) ИЛИ по каталогу БД (DbFilter) т.е. один из них д.б. null

| Член | Тип | Описание |
|---|---|---|
| `Conditions` | поле | Фильтр по условиям - кастомный. Если не null, То применяется он |
| `DbFilter` | поле | Фильтр по содержимому каталога БД |
| `DBFilterPath` | поле | Путь к каталогу БД, полученный с помощью CADLib.FoldersBrowser.GetFoldersPathString |
| `FilterType` | поле | Тип фильтра: по объекту1, по объекту2 либо по коллизии |
| `FilterName` | поле | Имя фильтра для вывода пользователю (всплывающая подсказка к кнопке) |
| `SaveToDbUserProperties(CADLibKernel.C...` | метод | Сохраняет фильтр в пользовательские настройки БД Параметры: filter — фильтр для сохранения или null для удаления настроек (значит, что фильтра нет) | 
| `LoadFromDbUserProperties(CADLibKernel...` | метод | Загружает фильтр из пользовательских настрое БД Параметры: lib — Библиотека; foldersTree — Дерева для восстановления внешнего фильтра по пути Возвращает: Фильтр, сохранённый в БД или null | 
| `SaveToDbSharedProperties(CADLibKernel...` | метод | Сохраняет фильтр в настройки БД Параметры: filter — фильтр для сохранения или null для удаления настроек (значит, что фильтра нет) | 
| `LoadFromDbSharedProperties(CADLibKern...` | метод | Загружает фильтр из настроек БД Параметры: lib — Библиотека; foldersTree — Дерево для восстановления внешнего фильтра по пути Возвращает: Фильтр, сохранённый в БД или null | 

#### `CSProject3D.Forms.Tools.H<wbr>ierarchyTableView.CLibObj<wbr>ectParameterView`
**Назначение:** Класс для отображения параметра объекта CLibObjectInfo

| Член | Тип | Описание |
|---|---|---|
| `Owner` | свойство | Объект, к которому принадлежит параметр |
| `ToolTip` | свойство | Подсказка о назначении параметра |
| `IsCalculated` | свойство | True если параметр вычисляемый |
| `IsModified` | свойство | True если значение параметра было изменено |
| `IsReadOnly` | свойство | True если значение параметра нельзя изменять |
| `Name` | свойство | Имя параметра |
| `NameDb` | свойство | Имя параметра |
| `Source` | свойство | Обозреваемый объект Parameter |
| `Value` | свойство | Значение параметра |

#### `CSProject3D.BuildingsHier<wbr>archyPlugin.CBuildingsHie<wbr>rachyFolder.CHierarchyObj<wbr>ectFolder`
**Назначение:** для каждого подобъекта

| Член | Тип | Описание |
|---|---|---|
| `HierarchyObject` | свойство | Объект иерархии, представляющий данную папку |
| `m_arrTableAliases` | поле | Используемые в запросе псевдонимы таблиц для метода GetFilterExpressions |
| `m_strFilterFrom` | поле | Информация о фильтре только этого узла |
| `m_strFilterWhere` | поле | Информация о фильтре только этого узла |
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `ShowObjectsTree(CADLibKernel.CLibCata...` | метод | Заполнение дерева объектов узлами с объектами (в tag узла необходимо записать наследников CLibObjectInfo) Параметры: folder — Каталог для которого необходимо показать объекты (может быть стандартным вложенным каталогом); tvObjects — Дерево объектов назначения; nPageSize — Размер страницы объектов; strMinName — Позиция начала страницы; strMaxName — Позиция конца страницы; bForward — Листание вперёд; bSelect — Выделять ли добавленные узлы дерева Возвращает: Если вернуть false, то будет использован стандартный механизм добавления объектов каталога | 

#### `CSProject3D.ModelRepresentation.MRPlugin`
**Назначение:** Плагин представлений модели Создаёт виртуальную папку в окне БД

| Член | Тип | Описание |
|---|---|---|
| `ModelRepresentationGroup` | поле | Имя группы данных структурного объекта (SYS_CATEGORY_GROUP) |
| `ModelRepresentationCatIcon` | поле | Имя иконки категории представления моделей |
| `Library` | свойство | Класс библиотеки |
| `m_mainForm` | поле | Форма приложения |
| `ActiveModelRepresentation` | поле | активное представление модели |
| `UpdateColorProfilesFromModelRepresent...` | метод | Обновления данных в таблице ModelRepresentations Параметры: mr — Представление модели; obj — CLibObjectInfo; isNew — True если представление создано вновь - для представлений из каталога применяются цвета по умолчанию | 
| `__CreateVirtualFolderObject(CADLibKer...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 

#### `CSProject3D.ProjectCustomHierarchyPlugin`
**Назначение:** Плагин иерархии разделов проекта

| Член | Тип | Описание |
|---|---|---|
| `GetPCHFolder(CSProject3D.CAD3DLibrary...` | метод | Находит или создаёт специальную выборку для объектов иерархии Разделов проекта Если каталог существует, но id категории не совпадает, то будет возвращено значение null, а создание bForceCreate=true обновит каталог. Если стоит bForceCreate, но категория не найдена - создаётся и возвращается не корректный каталог Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `PCHToObjectRelType` | свойство | Возвращает тип связи объекта иерархии с объектом модели или null (если нет типа) Значение кэшируется |
| `PCHObjToObjectRelType` | свойство | Возвращает тип связи ссылки на объект иерархии Значение кэшируется |
| `PCHObjToBldRelType` | свойство | Возвращает тип связи ссылки на ЗиС в иерархии Значение кэшируется |
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Запрашивает у плагина объект Параметры: libObject — стандартный объект; strStructGroup — Группа данных структурнуго объекта или null если не структурный Возвращает: Кастомный объект или null | 
| `MenuActiveObjects` | свойство | Объекты для которых действуют пункты меню |

#### `CSProject3D.ProjectCustom<wbr>HierarchyPlugin.CCustomHi<wbr>erachyFolder.CHierarchyOb<wbr>jectFolder`
**Назначение:** для каждого подобъекта

| Член | Тип | Описание |
|---|---|---|
| `PCHObject` | свойство | Объект иерархии, представляющий данную папку |
| `m_arrTableAliases` | поле | Используемые в запросе псевдонимы таблиц для метода GetFilterExpressions |
| `m_strFilterFrom` | поле | Информация о фильтре только этого узла |
| `m_strFilteWhere` | поле | Информация о фильтре только этого узла |
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `ShowObjectsTree(CADLibKernel.CLibCata...` | метод | Заполнение дерева объектов узлами с объектами (в tag узла необходимо записать наследников CLibObjectInfo) Параметры: folder — Каталог для которого необходимо показать объекты (может быть стандартным вложенным каталогом); tvObjects — Дерево объектов назначения; nPageSize — Размер страницы объектов; strMinName — Позиция начала страницы; strMaxName — Позиция конца страницы; bForward — Листание вперёд; bSelect — Выделять ли добавленные узлы дерева Возвращает: Если вернуть false, то будет использован стандартный механизм добавления объектов каталога | 

#### `CSProject3D.ProjectStruct<wbr>ureHierarchyPlugin.CStruc<wbr>tureHierachyFolder.CHiera<wbr>rchyObjectFolder`
**Назначение:** для каждого подобъекта

| Член | Тип | Описание |
|---|---|---|
| `PSHObject` | свойство | Объект иерархии, представляющий данную папку |
| `m_arrTableAliases` | поле | Используемые в запросе псевдонимы таблиц для метода GetFilterExpressions |
| `m_strFilterFrom` | поле | Информация о фильтре только этого узла |
| `m_strFilteWhere` | поле | Информация о фильтре только этого узла |
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `ShowObjectsTree(CADLibKernel.CLibCata...` | метод | Заполнение дерева объектов узлами с объектами (в tag узла необходимо записать наследников CLibObjectInfo) Параметры: folder — Каталог для которого необходимо показать объекты (может быть стандартным вложенным каталогом); tvObjects — Дерево объектов назначения; nPageSize — Размер страницы объектов; strMinName — Позиция начала страницы; strMaxName — Позиция конца страницы; bForward — Листание вперёд; bSelect — Выделять ли добавленные узлы дерева Возвращает: Если вернуть false, то будет использован стандартный механизм добавления объектов каталога | 

#### `CSProject3D.ProjectStructureHierarchyPlugin`
**Назначение:** Плагин иерархии разделов проекта

| Член | Тип | Описание |
|---|---|---|
| `StructureObjGroup` | поле | Значение параметра группа данных |
| `GetPSHFolder(CSProject3D.CAD3DLibrary...` | метод | Находит или создаёт специальную выборку для объектов иерархии Разделов проекта Если каталог существует, но id категории не совпадает, то будет возвращено значение null, а создание bForceCreate=true обновит каталог. Если стоит bForceCreate, но категория не найдена - создаётся и возвращается не корректный каталог Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `PSHToObjectRelType` | свойство | Возвращает тип связи объекта иерархии с объектом модели или null (если нет типа) Значение кэшируется |
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Запрашивает у плагина объект Параметры: libObject — стандартный объект; strStructGroup — Группа данных структурнуго объекта или null если не структурный Возвращает: Кастомный объект или null | 
| `MenuActiveObjects` | свойство | Объекты для которых действуют пункты меню |

#### `CSProject3D.SurfaceManage<wbr>r.CSurfaceObject.ESurface<wbr>Type`
**Назначение:** Тип поверхности (геогруппа)

| Член | Тип | Описание |
|---|---|---|
| `Unknown` | поле | Не известно (не задан) |
| `Surface` | поле | Линия поверхности |
| `Geo` | поле | Геология |
| `Others` | поле | Прочее |
| `Project` | поле | Проектная поверхность |
| `Ignore` | поле | игнорировать на профиле |

#### `CSProject3D.UserTagging.E<wbr>ntities.eActivationInvolv<wbr>ing`
**Назначение:** Объекты, задействованные при активации (флаги) Необходимы для устранения конфликтов atOnObjectSelect

| Член | Тип | Описание |
|---|---|---|
| `aiNothing` | поле | Активация ничего не меняет |
| `aiTagEnt` | поле | Активация изменяет сущность представления заметки (dynamic world entities) |
| `aiCamera` | поле | Активация изменяет положение/вид камеры |
| `aiOverlay` | поле | Активация задействует оверлей |
| `aiGeometric` | поле | Активация изменяет геометрию/вешний вид объектов |
| `aiObjectSelection` | поле | Активация изменяет состав выделенных объектов |

#### `CSProject3D.Works.WorksObjectsViewGenerator`
**Назначение:** Форма показа объектов, связанных с работами на 3D

| Член | Тип | Описание |
|---|---|---|
| `IsFactPeriods` | свойство | Рассматривать ли работы из группы "Факт" (выбирается в выпадающем списке План; Факт) |
| `m_arrObjectsToShow` | поле | Объекты, которые необходимо показать |
| `UpdateObjectsToShow` | метод | Вычисляется новый список m_arrObjectsToShow |

#### `CSProject3D.CAxis`
**Назначение:** Ось сетки

| Член | Тип | Описание |
|---|---|---|
| `InitChildren(CADLib.CADLibrary)` | метод | Считывает подчинённые объекты типа CAxisPoint Параметры: lib — Библиотека |
| `Parent` | свойство | Родительский объект |
| `TryExpandObjectNode(System.Windows.Fo...` | метод | Раскрывает узел объекта Параметры: treeNode — Узел дерева родительского объекта (вызываемого) Возвращает: возвращает true - если плагин заполнил дерево, иначе false - дерево заполняется стандартными средствами | 
| `LoadAxisData` | метод | Загружает информацию об оси из библиотеки |

#### `CSProject3D.Forms.Viewer3D.ClipBoxDlg`
**Назначение:** Диалог ограничения пространства по координатной сетке с сохранением параметров

| Член | Тип | Описание |
|---|---|---|
| `#ctor(CSProject3D.Forms.Viewer3D.Clip...` | метод | Конструктор диалога ограничения пространства по координатной сетке Параметры: settings — Параметры обрезки (будут обновлены при нажатии ОК); grid — Координатная сетка; activeObject — Объект - владелец настроек для вывода имени | 

#### `CSProject3D.IDockWindowOwner`
**Назначение:** Интерфейс работы с палитрами

| Член | Тип | Описание |
|---|---|---|
| `RegisterDockForm(System.Windows.Forms...` | метод | Регистрация палитры Необходимо проводить, чтобы указать положение по умолчанию Параметры: dockForm — Объект формы с заданым атрибутом DockableForm; defaultPos — Положение по умолчанию; mode — Распологать окно внутри основного (модель) или снаружи | 
| `UnregisterDockForm(System.Windows.Forms.Form)` | метод | Отменяет регистрацию формы Параметры: dockForm — Объект формы с заданым атрибутом DockableForm |
| `ShowDockForm(System.Windows.Forms.Form)` | метод | Показывает палитру или устанавливает фокус на открытой палитре Параметры: form — Объект формы с заданым атрибутом DockableForm | 
| `GetFormDockStyle(System.Windows.Forms...` | метод | Способ размещения палитры Параметры: form — Объект формы палитры Возвращает: Способ размещения палитры или None в случае ошибки | 

#### `CSProject3D.UserTagging.E<wbr>ntities.eVisibilityType`
**Назначение:** Видимость + Поведение видимости заметки при клике на связанном объекте

| Член | Тип | Описание |
|---|---|---|
| `vtInvisible` | поле | Не виден никогда |
| `vtVisible` | поле | Виден всегда |
| `vtRelated` | поле | Виден только если выбран связанный объект, либо тэг выбран в дереве (Highlighted) |
| `vtRelatedHot` | поле | Виден только если связанный объект выбран или выделен, либо тэг выбран в дереве (Highlighted) |

#### `CSProject3D.Forms.Tools.H<wbr>ierarchyTableView.CLibObj<wbr>ectView`
**Назначение:** Класс для отображения параметров объекта CLibObjectInfo

| Член | Тип | Описание |
|---|---|---|
| `UID` | свойство | UID объекта, параметры которого будут отображаться |
| `Parameters` | свойство | Словарь параметров : ключ - имя параметра (поле caption класса Parameter), значение - объект типа Paramater |
| `GetCalculatedParameters` | метод | Пересчитывает вычисляемые параметры (если они есть) Возвращает: True если есть вычисляемые параметры |

#### `CSProject3D.Forms.Tools.H<wbr>ierarchyTableView.Hierarc<wbr>hyTableView`
**Назначение:** Interaction logic for HierarchyTableView.xaml

| Член | Тип | Описание |
|---|---|---|
| `SaveChanges` | метод | Сохранение изменений в БД если были внесены |
| `GenerateDataGridColumns` | метод | Генерирует столбцы для DataGrid в зависимости от параметров объектов хранящихся в DataContext.Items |
| `InitializeComponent` | метод | InitializeComponent |

#### `CSProject3D.Forms.Tools.H<wbr>ierarchyTableView.Hierarc<wbr>hyTableViewContext`
**Назначение:** Контекст отображения таблицы свойств набора объектов типа CLibObjectInfo

| Член | Тип | Описание |
|---|---|---|
| `m_ParentWindow` | поле | Родительское окно для отображения коллекции объектов (нужен для опреций с окном - сворачивание, закрытие и т.д.) |
| `m_lib3d` | поле | Библиотека CAD3DLibrary (нужна для записи изменений в БД) |
| `Items` | свойство | Обозреваемая коллекция объектов типа CLibObjectInfo |

#### `CADLib.Controls.WorkMgmt.<wbr>WorkMgmtControl.Settings`
**Назначение:** Параметры вида элемента управления работ

| Член | Тип | Описание |
|---|---|---|
| `CurrentProject` | свойство | Проект выбранный в графике работ |
| `GetColumnsIdentities` | метод | Упорядоченный набор идентификаторов столбцов из пользовательского файла C:\Users\username\AppData\Roaming\CSoft\Model Studio CS\Library3D\settingsWorksManager.xml | 

#### `CSProject3D.BuildingsHier<wbr>archyPlugin.CBuildingsHie<wbr>rachyFolder.CUnboundObjec<wbr>tFolder`
**Назначение:** для объектов, не связанных с иерархией

| Член | Тип | Описание |
|---|---|---|
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `m_strFilterWhere` | поле | Информация о фильтре только этого узла |

#### `CSProject3D.CAxisPoint`
**Назначение:** Точка на оси сетки

| Член | Тип | Описание |
|---|---|---|
| `Parent` | свойство | Родительский объект |
| `LoadAxisPointData` | метод | Загружает информацию о точке из библиотеки |

#### `CSProject3D.Collisions.CollisionSign3d`
**Назначение:** Трёхмерный знак коллизии в виде треугольника со знаком восклицания Имеющий один статический экземпляр Для работы используется метод Inst.GenerateMesh

| Член | Тип | Описание |
|---|---|---|
| `Size` | свойство | Размер знака коллизии |
| `GenerateMesh(ModelStudio.Graphics3D.C...` | метод | Генерирует сетку в виде треугольника с (без) ножками в указанных точках Параметры: ptSign — Точка, где будет расположен знак; pt1 — Точка коллизии 1; pt2 — Точка коллизии 2; fSignScale — Масштаб знака; bTwoLegs — Добавлять ли линии к точкам коллизии; condition — Нарушенное условие коллизии или null; signInfo — Результирующая информация о сетке для добавления в БД; ptMeshBase — Базова точка сетки - вектор нормализации (используется для добавления сетки в БД) Возвращает: Бинарные данные сетки в формате msm для добавления в БД | 

#### `CSProject3D.Forms.Tools.H<wbr>ierarchyTableView.Hierarc<wbr>hyTableCellTemplateSelect<wbr>or`
**Назначение:** Класс селектора шаблона отображения ячейки таблицы в зависимости от типа отображаемого параметра

| Член | Тип | Описание |
|---|---|---|
| `GetTextBlockWithButtonTemplate` | метод | Шаблон для отображения только текстового поля и кнопки вызова диалога |
| `GetTextBlockTemplate` | метод | Шаблон для отображения только текстового поля |

#### `CSProject3D.Forms.Tools.Q<wbr>uestionBox.QuestionBox`
**Назначение:** Interaction logic for QuestionBox.xaml

| Член | Тип | Описание |
|---|---|---|
| `#ctor(System.String)` | метод | Конструктор нового окна с вопросом question и вариантами ответа "Да-Нет". Свойство Answer хранит вариант ответа после закрытия окна Параметры:  |
| `InitializeComponent` | метод | InitializeComponent |

#### `CSProject3D.ProjectCustom<wbr>HierarchyPlugin.CCustomHi<wbr>erachyFolder.CUnboundObje<wbr>ctFolder`
**Назначение:** для объектов, не связанных с иерархией

#### `CSProject3D.ProjectStruct<wbr>ureHierarchyPlugin.CStruc<wbr>tureHierachyFolder.CUnbou<wbr>ndObjectFolder`
**Назначение:** для объектов, не связанных с иерархией

#### `CSProject3D.UserTagging.Vector2d.SelGraph`
**Назначение:** Handle tool for redim/move/rotate Graphs

| Член | Тип | Описание |
|---|---|---|
| `setup(CSProject3D.UserTagging.Vector2d.Graph)` | метод | set ups handles |
| `reCreateCreationHandles(CSProject3D.UserTagging.Vector2d.Graph)` | метод | set ups handles |

#### `CSProject3D.UserTagging.Vector2d.SelPoly`
**Назначение:** Handle tool for redim/move/rotate Polygons

| Член | Тип | Описание |
|---|---|---|
| `setup(CSProject3D.UserTagging.Vector2d.PointSet)` | метод | set ups handles |
| `reCreateCreationHandles(CSProject3D.UserTagging.Vector2d.PointSet)` | метод | set ups handles |

#### `CSProject3D.CAxisPoint.AxisPointData`
**Назначение:** Класс данных оси сетки, загружаемый по запросу

| Член | Тип | Описание |
|---|---|---|
| `PointParam` | свойство | Параметр точки НЕ умноженный на масштаб |

#### `CSProject3D.Controls.Work<wbr>Mgmt.ColumnsEditor.DataCo<wbr>lumnEditor`
**Назначение:** Interaction logic for DataColumnEditor.xaml

| Член | Тип | Описание |
|---|---|---|
| `InitializeComponent` | метод | InitializeComponent |

#### `CSProject3D.Forms.Experti<wbr>se.AddNotesTagsControl`
**Назначение:** Interaction logic for NotesTags.xaml

#### `CSProject3D.Forms.Expertise.BCFExportForm`
**Назначение:** Interaction logic for BCFExportForm.xaml

#### `CSProject3D.Forms.Expertise.BCFImportForm`
**Назначение:** Interaction logic for BCFmportForm.xaml

#### `CSProject3D.Forms.Expertise.CollisionsDlg`
**Назначение:** Логика взаимодействия для CollisionsDlg.xaml

#### `CSProject3D.Forms.Expertise.CommentControl`
**Назначение:** CommentControl

#### `CSProject3D.Forms.Experti<wbr>se.CommentsListControl`
**Назначение:** CommentsListControl

#### `CSProject3D.Forms.Expertise.ExpertiseControl`
**Назначение:** Interaction logic for ExpertiseControl.xaml

#### `CSProject3D.Forms.Expertise.NoteWindow`
**Назначение:** NoteWindow

#### `CSProject3D.Forms.Expertise.NotesListControl`
**Назначение:** NotesListControl

#### `CSProject3D.Forms.Expertise.ProgressForm`
**Назначение:** Логика взаимодействия для ProgressForm.xaml

#### `CSProject3D.Forms.Expertise.RelationsObjForm`
**Назначение:** Interaction logic for RelationsForm.xaml

#### `CSProject3D.Forms.Expertise.TopicDlg`
**Назначение:** Логика взаимодействия для MainWindow.xaml

#### `CSProject3D.Forms.Expertise.UploadControl`
**Назначение:** UploadControl

#### `CSProject3D.I3DViewerOwner`
**Назначение:** Интерфейс главного окна трёхмерной модели

| Член | Тип | Описание |
|---|---|---|
| `Viewer3DControl` | свойство | Объект главного компонента просмотра трёхмерной модели |

#### `CSProject3D.LayoutManager<wbr>.CLayoutPluginFolderFilte<wbr>r.CLayoutFilter`
**Назначение:** для каждого листа

| Член | Тип | Описание |
|---|---|---|
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 

#### `CSProject3D.ModelRepresen<wbr>tation.ModelRepresentatio<wbr>nColor`
**Назначение:** Вхождение профиля: фильтр, имя, цвет, степень прозрачности

| Член | Тип | Описание |
|---|---|---|
| `IsDefault` | свойство | цвет по умолчанию |

#### `CSProject3D.Properties3D.EnumTypeConverterW`
**Назначение:** TypeConverter для Enum as CSPropertyWarapper[object], преобразовывающий Enum к строке с учетом атрибута Description

| Член | Тип | Описание |
|---|---|---|
| `#ctor(System.Type)` | метод | Инициализирует экземпляр Параметры: type — тип CSPropertyWarapper[Enum]> |

#### `CSProject3D.UserTagging.Vector2d.AbSel`
**Назначение:** Handle tool for redim/move/rotate shapes

| Член | Тип | Описание |
|---|---|---|
| `isOver(System.Single,System.Single)` | метод | Su quale maniglia cade il punto x,y? |

#### `CSProject3D.UserTagging.Vector2d.AbstractSel`
**Назначение:** Abstract Handle collection for redim/move/rotate shapes

| Член | Тип | Описание |
|---|---|---|
| `isOver(System.Single,System.Single)` | метод | On wich handle is point x,y |

#### `CSProject3D.UserTagging.Vector2d.Group`
**Назначение:** Group ( extends Element2dBase )

| Член | Тип | Описание |
|---|---|---|
| `#ctor(System.Collections.ArrayList)` | метод | .Ctor) |

#### `CSProject3D.UserTagging.Vector2d.SelRect`
**Назначение:** Handle tool for redim/move/rotate shapes

| Член | Тип | Описание |
|---|---|---|
| `setup` | метод | set ups handles |

#### `CSProject3D.UserTagging.Vector2d.SelRectBK`
**Назначение:** Handle tool for redim/move/rotate shapes

| Член | Тип | Описание |
|---|---|---|
| `isOver(System.Single,System.Single)` | метод | Which handle over the point |

#### `CSProject3D.Works.WorkPro<wbr>perties.WorkPropertiesVie<wbr>w`
**Назначение:** Interaction logic for WorkPropertiesView.xaml

#### `CSProject3D.CAxis.AxisData`
**Назначение:** Класс данных оси сетки, загружаемый по запросу


#### `CSProject3D.CCoordinateGrid.GridData`
**Назначение:** Класс данных сетки, загружаемый по запросу


#### `CSProject3D.Forms.ProjectDocumentListUpdater`
**Назначение:** Инициирует обновление дерева документов проекта в окне свойств


#### `CSProject3D.Forms.Relatio<wbr>nsControl.TreeController.<wbr>RelationsType`
**Назначение:** Какие типы связей показывать Все, Активные или конкретный тип


#### `CSProject3D.Forms.Relatio<wbr>nsControl.TreeNoCommonLin<wbr>ksNode`
**Назначение:** Узел показывает, что пересечение связей данного типа связи объектов является нулевым


#### `CSProject3D.Forms.Relatio<wbr>nsControl.TreeShowAllObje<wbr>ctsPagesItem`
**Назначение:** Узел показать остальные n (все страницы)


#### `CSProject3D.Forms.TypeWorkMode`
**Назначение:** Логика основана на 2-х параметрах WORK_COMPLETED_GROUP - группы WORK_COMPLETED_STATUS - статусы


#### `CSProject3D.Lib3DWorldClient`
**Назначение:** Класс для работы с объектом на сервере


#### `CSProject3D.Lib3DWorldProvider`
**Назначение:** Класс объекта расположенного на сервере


#### `CSProject3D.ModelRepresen<wbr>tation.ModelRepresentatio<wbr>n.ModelRepresentationSour<wbr>ce`
**Назначение:** Виды источников выборок для представления модели


#### `CSProject3D.ModelRepresen<wbr>tation.ModelRepresentatio<wbr>nCondition`
**Назначение:** Условие отбора объектов (как в диалоге коллизий или выборок): имя параметра, условие (=, !=, <, > ) и значение


#### `CSProject3D.Properties3D.<wbr>SimpleColorTypeConverter`
**Назначение:** there is no "not defined" and "Alpha"


#### `CSProject3D.UserTagging.P<wbr>roperties.UserTaggingText<wbr>Properties`
**Назначение:** Класс для настройки текст тэга


#### `CSProject3D.UserTagging.Vector2d.Arc`
**Назначение:** Arc


#### `CSProject3D.UserTagging.Vector2d.BoxTesto`
**Назначение:** Text Box ( estende Element2dBase )


#### `CSProject3D.UserTagging.V<wbr>ector2d.Ellipse2dElement`
**Назначение:** Ellipse


#### `CSProject3D.UserTagging.Vector2d.Graph`
**Назначение:** Graph ( extends Element2dBase )


#### `CSProject3D.UserTagging.V<wbr>ector2d.Image2dElement`
**Назначение:** Box Immagine ( estende Element2dBase )


#### `CSProject3D.UserTagging.Vector2d.Link`
**Назначение:** Rectangle ( extends Element2dBase )


#### `CSProject3D.UserTagging.Vector2d.OLine`
**Назначение:** OLinea //TEST!!!


#### `CSProject3D.UserTagging.V<wbr>ector2d.PointColorSet`
**Назначение:** A set of color point for Path Gradient Path management


#### `CSProject3D.UserTagging.Vector2d.PointSet`
**Назначение:** PointSet ( extends Element2dBase )


#### `CSProject3D.UserTagging.Vector2d.RRect`
**Назначение:** Rettangolo smussato ( estende Element2dBase )


#### `CSProject3D.UserTagging.Vector2d.Rect`
**Назначение:** Rectangle ( extends Element2dBase )


#### `CSProject3D.UserTagging.Vector2d.RedimHandle`
**Назначение:** Handle object for redim/move/rotate shapes


#### `CSProject3D.UserTagging.V<wbr>ector2d.Segment2dElement`
**Назначение:** Segment2dElement ( estende Element2dBase )


#### `CSProject3D.UserTagging.V<wbr>ector2d.SimpleText2dEleme<wbr>nt`
**Назначение:** Simple Text


#### `CSProject3D.UserTagging.Vector2d.UndoBuffer`
**Назначение:** Undo buffer. (Two Linked m_shapes)


#### `CSProject3D.UserTagging.Vector2d.VLine`
**Назначение:** VLine //TEST!!!


#### `CSProject3D.UserTagging.Vector2d.buffEle`
**Назначение:** Undo buffer Element2dBase element.


#### `CSProject3D.UserTagging.Vector2d.buffObj`
**Назначение:** Two Linked m_shapes Element


#### `CSProject3D.Works.WorkPro<wbr>perties.WorkPropertyMulti<wbr>Converter`
**Назначение:** Конвертер значения параметра работы в зависимости от типа данных 0 - True если DateTimeField 1 - True если TaskResourcesField 2 - True если ReadOnlyField 3 - Значение поля


#### `Win32Types.OPENFILENAME`
**Назначение:** See the documentation for OPENFILENAME


#### `Win32Types.OfnHookProc`
**Назначение:** Defines the shape of hook procedures that can be called by the OpenFileDialog


#### `WorksLib.ResourceGroup`
**Назначение:** Группа ресурсов, объединённых по ID и workTable


#### `WorksLib.ResourceList`
**Назначение:** Список ресурсов, относящийся к конкретной работе


#### `WorksLib.WorkItem`
**Назначение:** Базовые задачи (не нормируются) - WorkBasics/WorkItem


#### `WorksLib.Workcase`
**Назначение:** Разновидность работ - Workcases/Workcase


#### `CSProject3D.UserTagging.V<wbr>ector2d.Element2dBase`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `Draw(System.Drawing.Graphics,System.Single,System.Single,System.Single)` | метод | Draw this shape to a graphic ogj. |
| `AddGraphPath(System.Drawing.Drawing2D.GraphicsPath,System.Single,System.Single,System.Single)` | метод | Add this shape to a graphic path. |
| `AddGp(System.Drawing.Drawing2D.GraphicsPath,System.Single,System.Single,System.Single)` | метод | Add this shape to a graphic path. |
| `deGroup` | метод | Used to degroup a grouped shape. Returns a list of shapes. |
| `Select` | метод | Select this shape. |
| `Select(System.Windows.Forms.RichTextBox)` | метод | Select this shape. |
| `Select(System.Single,System.Single,System.Single,System.Single)` | метод | Select this shape. |
| `DeSelect` | метод | Deselct this shape. |
| `ShowEditor(CSProject3D.UserTagging.Vector2d.richForm2)` | метод | Used for RTF editor. |
| `AfterLoad` | метод | Used after the load from file. Manage here the creation of object not serialized. |
| `CopyFrom(CSProject3D.UserTagging.V<wbr>ector2d.Element2dBase)` | метод | Copy the properties from another shape |
| `Copy` | метод | Clone this shape |
| `copyGradprop(CSProject3D.UserTagging.V<wbr>ector2d.Element2dBase)` | метод | Copy the gradient properties. |
| `FillWithLines(System.Drawing.Graphics...` | метод | To fill a shape with parallel lines | 
| `scaledPenWidth(System.Single)` | метод | Used to define pen with. |
| `Fit2grid(System.Single)` | метод | Adapt the shape at the gridsize |
| `CommitRotate(System.Single,System.Single)` | метод | Confirm the rotation |
| `Rotate(System.Single,System.Single)` | метод | Rotate |
| `rotatePoint(System.Drawing.PointF,System.Single)` | метод | Return a point obtained rotating p by RotAng respect 0,0 |
| `_rotate(System.Single,System.Single)` | метод | Gets a rotation angle from a vertical line from the center of the shape and a line from the center to the point (x,y) |
| `getBrush(System.Single,System.Single,System.Single)` | метод | gets a brush from the properties of the shape |
| `copyStdProp(CSProject3D.UserTagging.V<wbr>ector2d.Element2dBase,CSProject3D.UserTagging.V<wbr>ector2d.Element2dBase)` | метод | Copy the properties common to all shapes. |
| `Dist(System.Single,System.Single,System.Single,System.Single)` | метод | 2 points distance |
| `dark(System.Drawing.Color,System.Int32,System.Int32)` | метод | Make a color darker or lighter |
| `Trasparency(System.Drawing.Color,System.Int32)` | метод | Make a color Tresparent/Solid |
| `contains(System.Single,System.Single)` | метод | true if the shape contains the point x,y |
| `move(System.Single,System.Single)` | метод | Moves the shape by x,y |
| `redim(System.Single,System.Single,System.String)` | метод | Redim the shape |
| `endMoveRedim` | метод | Called at the end of move/redim of the shape. Stores startX\|Y\|X1\|Y1 for a correct rendering during object move/redim |

#### `CSProject3D.MainForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `UnmanagedDB` | свойство | Экземпляр неуправляемой БД CLibDatabase |
| `SetStatusText(System.Int32,System.Str...` | метод | Задаёт состояние контролов загрузки в строке состояния главного окна Параметры: nLoadingPercent — Процент загрузки: если меньше нуля, то шкала загрузки скрыта если от 0 до 100, то значение загрузки если больше 100, то шкала загрузки в состоянии Marquee; strText — Текст состояния; bExclamation — Показывать ли знак восклицания перед текстом | 
| `InitControlMode` | метод | Вызывается при загрузке, если форма используется в качестве контрола Модифицирует меню и прочие функции |
| `CreateView` | метод | Create new view with dialog Возвращает: 0 if canceled or error otherwise new View's ID |
| `SaveUserState` | метод | Save to database: folderTree state etc... |
| `LoadUserState` | метод | Load from database: folderTree state etc... |
| `AppKey` | свойство | Используется для нахождения пути к настройкам (папка Settings или AppData) |
| `SelectObjects(System.Collections.Gene...` | метод | Выделяет список объектов Параметры: objectsIDs — Список объектов; bAddToView — Если да - вызывает добавляет выделение в текущий вид; bIsolate — Если да - вызывает опцию "Отобразить на модели" для выделенного списка | 
| `AttachObjectsToView(System.Collections.Generic.ICollection{System.Int32})` | метод | Добавляет объекты к текущему виду Параметры: objectsIDs — Список объектов |
| `RemoveObjectsFromView(System.Collections.Generic.ICollection{System.Int32})` | метод | Удаляет объект из текущего вида Параметры: objectsIDs — Список объектов |
| `TestCloneWholeModel` | метод | Метод для тестов Клонирует объекты всей трёхмерной модели со смещением вправо При клонировании используется эмуляция публикации новой модели (не используется информация о повторе сеток) | 
| `DEBUG_TEST_DbIntersections` | метод | Проверка работы ХП SPGetBoxIntersectedGraphics на клиенте |
| `DEBUGTEST_DbIntersectionsServerSide` | метод | Проверка работы ХП SPGetBoxIntersectedGraphics на сервере |
| `DEBUG_TEST_DbLandsGraphics` | метод | Проверка работы ХП SPGetLandsGraphics на клиенте |
| `DEBUG_TEST_DbLandsGraphics_Server` | метод | Проверка работы ХП SPGetLandsGraphics на сервере |
| `miLoadPointsCloud_Click(System.Object,System.EventArgs)` | метод | Загрузить облако точек из файла и поместить в БД Параметры:  |
| `miDeletePointsCloud_Click(System.Object,System.EventArgs)` | метод | Удалить объект облака точек и все ассоциированные файла из БД Параметры:  |

#### `CSProject3D.SurfaceManager`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `SurfacesFolderName` | поле | Имя специальной выборки для поверхностей |
| `SurfacesCat` | поле | Категория листов - системное имя |
| `SurfacesCatCaption` | поле | Категория поверхностей - Заголовок (русское имя) |
| `SurfacesDataGroup` | поле | имя параметра категории листов |
| `m_Library` | поле | Класс библиотеки |
| `VisibleLands` | свойство | idObject объектов, связанных с включёнными землями для текущего пользователя |
| `m_mainForm` | поле | Форма приложения |
| `GetVisibleLandsRecoursive(System.Coll...` | метод | Рекурсивно собираем включенные земли в VisibleLands останавливаясь на включённых | 
| `UpdateAndSaveVisibleLands` | метод | Считывает значения видимости из листов и записывает в настройки пользователя в БД |
| `SetSelectedNode(System.Windows.Forms.TreeNode)` | метод | Вызывается для обновления выделенной земли Параметры:  |
| `GetSurfacesFolder(CSProject3D.CAD3DLi...` | метод | Находит или создаёт специальную выборку для объектов поверхностей. Выборке присваивается имя SurfacesFolderName, которое затем используется для особенной обработки данного каталога (рисование иконки, контекстное меню). Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `GetAdditionalCurrenViewObjects` | метод | Получает дополнительные объекты из текущего вида Имеет значение для таких плагинов как "поверхности земли", которые показывают дополнительные объекты во вьювере, но они не отображаются в узле "Текущий вид". Тем не менее данные объекты должны быть обработаны во время выбора опции "Текущий вид" при экспорте или проверке коллизий. Возвращает: Идентификаторы дополнительных объектов, показанные плагином | 

#### `CSProject3D.Works.TaskInfo`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `TaskLevel` | свойство | Уровень вложения |
| `Id` | свойство | Обычный идентификатор задачи для работы логики |
| `TaskId` | свойство | Идентификатор задачи из файла *csv |
| `Start` | свойство | Дата начала (план.) |
| `StartA` | свойство | Дата начала (факт.) |
| `Finish` | свойство | Дата окончания (план.) |
| `FinishA` | свойство | Дата окончания (факт.) |
| `Duration` | свойство | Длительность (план.) |
| `DurationA` | свойство | Длительность (факт.) |
| `Composite` | свойство | Значения столбцов |
| `Type` | свойство | тип задаче в файле отличается, почему-то там не задаётся |
| `BudgetCode` | свойство | Сметный код |
| `PercentComplete` | свойство | Процент выполнения работ |

#### `CSProject3D.BuildingsHierarchyPlugin`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `HierarchyObjGroup` | поле | Значение параметра группа данных |
| `Library` | свойство | Класс библиотеки |
| `MainForm` | свойство | Форма приложения |
| `GetHierarchyFolder(CSProject3D.CAD3DL...` | метод | Находит или создаёт специальную выборку для объектов иерархии ЗиС Если каталог существует, но id категории не совпадает, то будет возвращено значение null, а создание bForceCreate=true обновит каталог. Если стоит bForceCreate, но категория не найдена - создаётся и возвращается не корректный каталог Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `m_coordGripRelationOld` | поле | Тип связи с сеткой для старых версий БД (обратная совместимость) |
| `HierarchyToObjectRelType` | свойство | Возвращает тип связи(ЗиС) объекта иерархии с объектом модели или null (если нет типа) Значение кэшируется |
| `HierarchySituationToObjectRelType` | свойство | Возвращает тип связи(Ситуация) объекта иерархии с объектом модели или null (если нет типа) Значение кэшируется |
| `HierarchySystemToObjectRelType` | свойство | Возвращает тип связи(Система) объекта иерархии с объектом модели или null (если нет типа) Значение кэшируется |
| `PSHToObjectRelType` | свойство | Возвращает тип связи объекта иерархии с объектом модели или null (если нет типа) Значение кэшируется |
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Запрашивает у плагина объект Параметры: libObject — стандартный объект; strStructGroup — Группа данных структурнуго объекта или null если не структурный Возвращает: Кастомный объект или null | 
| `MenuActiveObjects` | свойство | Объекты для которых действуют пункты меню |

#### `CSProject3D.CLPPublicationsManager`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `MainForm3D` | свойство | Главная форма приложения |
| `Library` | свойство | Библиотека главной формы |
| `PublicationFolderName` | поле | Имя специальной выборки с публикациями |
| `PublicationsCatGroup` | поле | Категория публикаций - имя группы структурных данных Значение параметра CADLibraryBase.SYS_CATEGORY_GROUP |
| `PublicationsDataGroup` | поле | Категория публикаций - имя группы структурных данных Значение параметра CADLibraryBase.SYS_CATEGORY_GROUP |
| `PublicationsActive` | поле | Активность публикации |
| `#ctor(CSProject3D.MainForm)` | метод | Конструктор плагина с авторегистрацией Параметры: mainForm3D — Главная форма МиА |
| `DeletePublish(CADLibKernel.CLibObjectInfo)` | метод | удаление публикации и всех связаных с ней объектов Параметры: publ — объект публикации |
| `GetPublicationFolder(CSProject3D.CAD3...` | метод | Находит или создаёт специальную выборку для объектов осей. Выборке присваивается имя GridsFolderName, которое затем используется для особенной обработки данного каталога (рисование иконки, контекстное меню). Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Получение объекта координатной сетки CCoordinateGrid по объекту БД Параметры: libObject — Исходные объект бибилотеки; strStructGroup — Группа даных структурных объектов Возвращает: объект сетки CCoordinateGrid или null, в случае, если libObject-другой объект | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 

#### `CSProject3D.Collisions.CollisionPlugin`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `CollisionCat` | поле | Категория коллизий - системное имя |
| `CollisionCatIcon` | поле | Имя иконки категории коллизий |
| `CollisionCatCaption` | поле | Категория коллизий - Заголовок (русское имя) |
| `CollisionsFolderName` | поле | Имя специальной выборки с коллизиями |
| `HierarchyLevelTypeBuilding` | поле | Для инициализации параметров Связь с первым объектом и Связь со вторым объектом |
| `m_Library` | поле | Класс библиотеки |
| `m_MainForm` | поле | Форма приложения |
| `GetCollisionsCatId(CSProject3D.CAD3DL...` | метод | Возвращает ID категории объектов коллизий с возможностью её создания Параметры: lib — Библиотека для работы; bCreateIfNone — Следует ли создавать категорию, если таковой нет; mainThreadControl — Элемент управления основного потока, для использования данного метода из фонового потока (необходим для загрузки иконки) Возвращает: ID категории объектов коллизий | 
| `GetCollisionsFolder(CSProject3D.CAD3D...` | метод | Находит или создаёт специальную выборку для объектов коллизий. Если каталог существует, но id категории не совпадает, то будет возвращено значение null, а создание bForceCreate=true обновит каталог. Выборке присваивается имя CollisionsFolderName, которое затем используется для особенной обработки данного каталога (рисование иконки, контекстное меню). Если стоит bForceCreate, но категория коллизий не найдена - создаётся и возвращается не корректный каталог Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 

#### `CSProject3D.SurfaceManager.CSurfaceObject`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `IsOn` | метод | Является ли поверхность видимой Возвращает: true, если поверхность (родитель или все подчинённые поверхности, если есть, видимы) |
| `SetOn(System.Boolean)` | метод | Изменить видимость поверхности (включая подчинённые) Параметры: bOn — видимость |
| `m_surfType` | поле | Тип поверхности (геогруппа) |
| `Manager` | свойство | Управляющий объект |
| `Parent` | свойство | Родительский объект |
| `ParentFolder` | свойство | Родительский каталог в случае, если Parent == null |
| `UpdateTreeIcon` | метод | Обновляет иконку дерева после изменения видимости объекта |
| `Node` | свойство | Информация об объекте в дереве объектов |
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный методы вызывается после применения объекта узлу дерева (если было) Параметры: tree — Дерево объектов; node — Узел с которым ассоциирован данный объект | 
| `TryExpandObjectNode(System.Windows.Fo...` | метод | Раскрывает узел объекта Параметры: treeNode — Узел дерева родительского объекта (вызываемого) Возвращает: возвращает true - если плагин заполнил дерево, иначе false - дерево заполняется стандартными средствами | 

#### `CSProject3D.Collisions.CollisionsForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `m_strToolTipSizeGenerator` | поле | Длина данной строки определит максимальный размер тултипа и соответственно размер картинки Другого способа не нашёл для задания размера, учитываемого в отступах от краёв экрана | 
| `HasCollisionPreview(Aga.Controls.Tree...` | метод | Для показа значка фотоаппарата на коллизиях, где есть скриншот Параметры: node — Узел дереве - коллизия Возвращает: Картинка для контрола | 
| `SaveCollisionToDb(CollisionEngine.CollisionObject)` | метод | Сохраняет или добавляет коллизию в БД, открытую в окне Параметры: collision — Объект коллизии |
| `RefreshData(System.Boolean)` | метод | Обновляет данные окна коллизий После смены библиотеки данный метод вызывается из LoadUserState(), и будет работать отлько после этого Параметры: | 
| `CollisionsFilterColl` | свойство | Позволяет установить или выявить наличие пользовательского фильтра Свойство может возвращать и принимать значение null - нет фильтра Изменение фильтра автоматически заставляет обновиться список коллизий | 
| `SaveUserState` | метод | Сохраняет настройки окна в пользовательские настройки БД (Загрузка настроек происходит в RefreshData при смене библиотеки) |

#### `CSProject3D.Collisions.Wizard.WizardForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `WizardPageActivated(System.Object,WizardFormLib.WizardPageActivateArgs)` | метод | Fired when a wizard page is activated (made visible) Параметры:  |
| `buttonBack_Click(System.Object,System.EventArgs)` | метод | Fired when the back button is clicked Параметры:  |
| `buttonNext_Click(System.Object,System.EventArgs)` | метод | Fired when the Next button is clicked Параметры:  |
| `buttonCancel_Click(System.Object,System.EventArgs)` | метод | Fired when the user clicks the Cancel button Параметры:  |
| `buttonHelp_Click(System.Object,System.EventArgs)` | метод | Fired when the user clicks the Help button Параметры:  |
| `buttonStart_Click(System.Object,System.EventArgs)` | метод | Fired when the user clicks the Start button (to return to the first wizard page). Параметры:  |

#### `CSProject3D.DocumentsFolderPlugin`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `Library` | свойство | Класс библиотеки |
| `MainForm` | свойство | Форма приложения |
| `ShowDocContentMI` | свойство | Пункт контекстного меню "Показать файл" |
| `Content2dAccessMI` | свойство | Пункт контекстного меню окна 3д "представления" |
| `GetFolderDocumentsQuery(CSProject3D.D...` | метод | Строит запрос на все карточки файлов или части файлов указанного каталога Параметры: folder — Каталог (родительский обхект файлов) Возвращает: Строку запроса для фильтра | 
| `GetObjectMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню для объектов Параметры: folder — Активный каталог (плагина или его подчинённый); selection — Выбранные в дереве объекты; menu — Меню в которое будут добавлены дополнительные пункты (для возможности заблокировать их видимость) Возвращает: Список дополнительных пунктов меню | 
| `GetPDHFolder(CSProject3D.CAD3DLibrary...` | метод | Находит или создаёт специальную выборку для объектов иерархии файлов проекта Если каталог существует, но id категории не совпадает, то будет возвращено значение null, а создание bForceCreate=true обновит каталог. Если стоит bForceCreate, но категория не найдена - создаётся и возвращается не корректный каталог Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Запрашивает у плагина объект Параметры: libObject — стандартный объект; strStructGroup — Группа данных структурнуго объекта или null если не структурный Возвращает: Кастомный объект или null | 

#### `CSProject3D.Forms.VideoRecorderControl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `RecordingStart` | событие | см. DefaultRecordingBehaviour |
| `RecordingStop` | событие | см. DefaultRecordingBehaviour |
| `DefaultRecordingBehaviour` | свойство | Если да, то нажатие кнопки запись запустит стандартную запись вьювера, иначе нажатие на запись вызовет событие RecordingStart, остановка записи вызовет RecordingStop | 
| `StartRecording(System.String)` | метод | Начинает запись видео В случае DefaultRecordingBehaviour==false просто переводит элемент управления в режим "Запись" Параметры: videoFileName — Файл назначения для DefaultRecordingBehaviour | 
| `StopRecording` | метод | Останавливает запись видео В случае DefaultRecordingBehaviour==false просто переводит элемент управления в режим "Остановлено" Возвращает: Да, если видео успешно создано | 
| `StartRecordInAutoFileName` | метод | Начинает запись видео по автоматически сгенерированному пути |

#### `CSProject3D.LayoutManager`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `LayoutsFolderName` | поле | Имя специальной выборки с листами |
| `LayoutsCat` | поле | Категория листов - системное имя |
| `LayoutsCatCaption` | поле | Категория листов - Заголовок (русское имя) |
| `LayoutsParamId` | поле | имя параметра категории листов |
| `LayoutsGroup` | поле | имя параметра категории листов |
| `m_Library` | поле | Класс библиотеки |
| `m_MainForm` | поле | Форма приложения |
| `GetLayoutsFolder(CSProject3D.CAD3DLib...` | метод | Находит или создаёт специальную выборку для объектов листов. Если каталог существует, но id категории не совпадает, то будет возвращено значение null, а создание bForceCreate=true обновит каталог. Если стоит bForceCreate, но категория не найдена - создаётся и возвращается не корректный каталог Параметры: lib — Библиотека; bForceCreate — Создавать ли выборку Возвращает: Объект выборки или null | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 

#### `CSProject3D.Forms.RelationsControl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `m_arrActiveObjects` | поле | Выбранные объекты для страницы |
| `m_nActiveOneObjectId` | поле | Выбранный конкретный объект для страницы (если 0, то обобщение для всех выбранных объектов) |
| `GetSelectedObjects` | метод | Возвращает все выделенные узлы объектов Возвращает: Список всех выбранных в дереве типов связи |
| `GetSelectedLinkTypes` | метод | Возвращает все выделенные узлы типов связи Возвращает: Список всех выбранных в дереве типов связи |
| `GetSelectedLinksObjects(System.Collec...` | метод | Поиск всех корневых и некорневых объектов, находящихся в выбранных связях Параметры: notRootItems — Сюда попадут выбранные не корневые объекты Возвращает: выбранные корневые объекты | 

#### `CADLibControls.FilterGrid`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `CustomGetParametersValue` | свойство | Предикат получения вариантов значения параметра (Для работы без библиотеки) |
| `CustomGetConditions` | свойство | Предикат получения списка операторов сравнения для фильтра по параметру (Для работы без библиотеки) |
| `EditValue(System.Windows.Forms.ListViewItem)` | метод | Редактирование колонки Значение параметра Параметры:  |
| `EditCondition(System.Windows.Forms.ListViewItem)` | метод | редактирование колонки Условие Параметры:  |

#### `CSProject3D.CGridsPluginFolderFilter`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `Node` | свойство | Информация об объекте в дереве объектов |
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `Manager` | свойство | Управляющий объект |
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `ExpandFolderNode(CADLib.CADLibrary,Sy...` | метод | Раскрытие каталога (вверху в окне БД) в TreeView Параметры: lib — Библиотека, выполняющая операцию; tree — Дерево, владеющее узлом; treeNode — Узел в который следует добавлять подузлы; bRecursive — Следует ли раскрывать всю иерархию; bUseClassifiers — Добавлять ли классификаторы в иерархию | 
| `ShowObjectsTree(CADLibKernel.CLibCata...` | метод | Заполнение узлами осуществляется стандартным механизмом Объекты преобразуются в CCoordinateGrid через вызов метода TryReadFolderObject Параметры: folder — Каталог для которого необходимо показать объекты (может быть стандартным вложенным каталогом); tvObjects — Дерево объектов назначения; nPageSize — Размер страницы объектов; strMinName — Позиция начала страницы; strMaxName — Позиция конца страницы; bForward — Листание вперёд; bSelect — Выделять ли добавленные узлы дерева Возвращает: Возвращает false, чтобы был использован стандартный механизм добавления объектов каталога | 
| `RootGrids` | свойство | Список загруженных координатных сеток каталога Список пополняется при преобразовании объекта БД в CCoordinateGrid при вызове метода TryReadFolderObject |

#### `CSProject3D.Forms.Relatio<wbr>nsControl.TreeRelationIte<wbr>m`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `CountTextL` | свойство | Текст количества объектов по связи слева |
| `CountTextR` | свойство | Текст количества объектов по связи справа |
| `RelObjectsCountL` | свойство | Имеются ли объекты, связанные данным типом связи с объектами контекста контроллера Устанавливается контроллером при вычислении узлов Связи, где связанный объект слева | 
| `RelObjectsCountR` | свойство | Имеются ли объекты, связанные данным типом связи с объектами контекста контроллера Устанавливается контроллером при вычислении узлов Связи, где связанный объект справа | 
| `m_linkedObjects` | поле | Связанные объекты (если null, то пока запроса небыло) |
| `EvaluateLinkedObjects` | метод | Получение связанных объектов при первом раскрытии узла типа связи |
| `IntersectLinkedObjectsByKeyId(mstMana...` | метод | Поиск общих связей для связанных объектов Параметры: arrLinked — Информацию о связи объектов, отсортированная по ключу; resSet — Результат пересечения всех множеств связей объектов; arrSortedKeys — Массив отсоритрованных запрашиваемых ключей, чтобы выявить объекты без связей | 

#### `CSProject3D.Forms.dbViewerModalDlg`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SelectedFolder` | свойство | Выделенный каталог |
| `SelectedObjects` | свойство | Список выделенных объектов, который следует использовать, если SelectedFolder == null |
| `FolderSelectionMode` | свойство | В данном режиме позволяется выбирать только папку кроме "Все объекты" |
| `GetUserSelection` | метод | Получение списка выбранных объектов (даже если был выбран каталог) Возвращает: Список информации о выбранных объектах |

#### `CSProject3D.SurfaceManage<wbr>r.CSurfacePluginFolderFil<wbr>ter`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `LoadLandsHierarchy` | метод | Загружает всю иерархию поверхностей в модель |
| `FolderOrder` | свойство | Поверхности идут после стандартных папок |
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный методы вызывается после применения каталога узлу дерева (если было) Параметры: node — Узел с которым ассоциирован данный каталог | 
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `Manager` | свойство | родительский каталог |
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `ShowObjectsTree(CADLibKernel.CLibCata...` | метод | Заполнение дерева объектов узлами с объектами (в tag узла необходимо записать наследников CLibObjectInfo) Параметры: folder — Каталог для которого необходимо показать объекты (может быть стандартным вложенным каталогом); tvObjects — Дерево объектов назначения; nPageSize — Размер страницы объектов; strMinName — Позиция начала страницы; strMaxName — Позиция конца страницы; bForward — Листание вперёд; bSelect — Выделять ли добавленные узлы дерева Возвращает: Если вернуть false, то будет использован стандартный механизм добавления объектов каталога | 

#### `CSProject3D.UserTagging.U<wbr>serTaggingCollection`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `ActivateTag(CSProject3D.UserTagging.E<wbr>ntities.UserTaggingBase)` | метод | Используется при клике по гиперссылки Параметры: tag — Тэг для активации |
| `AddTag(CSProject3D.UserTagging.UserTa...` | метод | Adding new tag with user dialog Параметры: taggingKind — Type of tag to be created; afterCreate — Will be called after creating new instance of Tag and before acquiring parameters | 
| `AddTagRet(CSProject3D.UserTagging.Use...` | метод | Adding new tag with user dialog. Return created tag Параметры: taggingKind — Type of tag to be created; afterCreate — Will be called after creating new instance of Tag and before acquiring parameters | 
| `AddTag(CSProject3D.UserTagging.Entiti...` | метод | Adding new tag with accepted parameters Also saving tag to DB Параметры: newTag — Tag to be added; bNotifyListeners — Should collection changed events be issued | 
| `ResolveActivationConflicts(CSProject3...` | метод | Разрешает конфликты автоматической активации, путём отключения её у других конфликтующих заметок Данный анализ производится, только если у обеих заметок одинаковый набор связанных объектов Параметры: predefinedTag — Заметка, оставляемая неизменной | 
| `TryGetElements(System.Xml.Linq.XEleme...` | метод | Возвращает подэлементы указанного XElement, с указанным именем Параметры: xElement — Исходный элемент; xElementName — Имя подэлемента; xElements — Подэлементы Возвращает: True если найден ходь один подэлемент | 
| `Import(System.Xml.Linq.XElement,CADLib.CADLibrary,CSProject3D.UserTagging.U<wbr>serTaggingCollection)` | метод | импорт заметок из XML-файла MALT |

#### `CSProject3D.WorkMgmtCtl3D`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `IsFactPeriods` | свойство | Рассматривать ли работы из группы "Факт" (выбирается в выпадающем списке) |
| `m_floatingForm` | поле | Окно в котором показывается диаграмма работ (чтобы была возможность разместить её на другом мониторе) Два режима: либо диаграмма в окне, либо на контроле | 
| `btnFloatWnd_Click(System.Object,System.EventArgs)` | метод | Кнопка активации/деактивации плавающего окна |
| `btnShowNonAssignedObjects_Click(System.Object,System.EventArgs)` | метод | Отобразить 3D-объекты, не связанные с работами Параметры:  |

#### `CSProject3D.Works.WorksVideoVisualizerForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SECONDS_IN_THE_END` | поле | Оставляем это время в конце видео ролика, чтобы успеть показать последнюю дату Данное время также добавлено, т.к. расчётная длительность скрипта немного не соответствует реальной | 
| `SECONDS_TO_FADE` | поле | Максимальное время перехода цвета состояния работ |
| `m_recState` | поле | Текущее состояние записи (устанавливается из потока 3D движка) |
| `timerTimeUpdater_Tick(System.Object,System.EventArgs)` | метод | Обновления состояния записи (время, процент) |

#### `CADLib.Controls.WorkMgmt.WorkMgmtControl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `WorkFilterDateTime(System.Collections...` | метод | Проверяет применимость списка работ по выбранному фильтру (для типов DateTime) Параметры: Compare — Тип сравнения (больше, меньше и пр.); ParamName — Наименование параметра, чьё значение сравниваем; FilterValue — Значение фильтра | 
| `WorkFilterString(System.Collections.G...` | метод | Проверяет применимость списка работ по выбранному фильтру (для типов String) Параметры: Compare — Тип сравнения (начинается, содержит и пр.); ParamName — Наименование параметра, чьё значение сравниваем; FilterValue — Значение фильтра | 
| `WorkFilterNumeric(System.Collections....` | метод | Проверяет применимость списка работ по выбранному фильтру (для типов int, double и пр.) Параметры: Compare — Тип сравнения (больше, меньше и пр.); ParamName — Наименование параметра, чьё значение сравниваем; FilterValue — Значение фильтра | 

#### `CADLibControls.FilterDialog`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SetOfflineMode(System.Action{CADLibCo...` | метод | Установка значений колбэков для использования без библиотеки Параметры: addParamsAction — Действие по нажатию на кнопку добавления параметров; getParametersValue — Предикат получения вариантов значения параметра; getConditions — Предикат получения списка операторов сравнения для фильтра по параметру, либо по умолчанию | 
| `AddOfflineConditions(System.Collectio...` | метод | Добавление условий фильтрации в таблицу (Для использования без библиотеки) Параметры: conditions — список строк таблицы | 
| `GetOfflineConditions` | метод | Возвращает условия фильтрации (Для использования без библиотеки) Возвращает: условия фильтрации |

#### `CSProject3D.Forms.Relatio<wbr>nsControl.TreeController`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `RelationTypes` | свойство | Виды связей устанавливаются извне при обновлении/подключении библиотеки |
| `ShowChildrenLinks` | свойство | Показывать ди связи с подчинёнными выбранным объектами |
| `ShowTypeMode` | свойство | Какие типы связей показывать Все, Активные или конкретный тип |
| `ShowParticularType` | свойство | Какой тип связи показывать, если выбран режим rtParticular |
| `RebuildTree` | метод | Перестраивает дерево |
| `MakeArgs(System.Collections.Generic.I...` | метод | Делает аргументы по узлам. У всех узлов ДОЛЖЕН БЫТЬ ОДИН РОДИТЕЛЬ Параметры: | 

#### `CSProject3D.Forms.WorkStatusesForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `LoadGroupValues` | метод | Загрузка всех групп WORK_COMPLETED_GROUP |
| `LoadGroupStatuses` | метод | Загрузка всех статусов WORK_COMPLETED_STATUS |
| `ValidateGroup(System.String)` | метод | Проверка группы Параметры: GroupName — Имя параметра группы |

#### `CSProject3D.Works.WorksImportWorksConnection`
**Назначение:** Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.

| Член | Тип | Описание |
|---|---|---|
| `GetArrFieldsConnection` | метод | Возвращает массив сапоставлений полей CadLib и CSV |
| `GetUserSelectedCustomFields` | метод | Возвращает массив сапоставлений выбранных дополнительных полей |
| `CheckXMLProfileName(System.String)` | метод | Проверяет существование профиля с заданным именем false - не существует, true - существует Параметры: ProfileName — Заданное имя профиля | 

#### `CSProject3D.BuildingsHier<wbr>archyPlugin.CBuildingsHie<wbr>rachyFolder`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `FolderOrder` | свойство | здания и сооружения сверху |
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `ExpandSubFolderNode(CADLib.CADLibrary...` | метод | Вызывается при раскрытии некастомных каталогов, вложенных в данный Параметры: lib — Библиотека, выполняющая операцию; expandingFolder — Раскрываемый каталог (подчинённый плагиновскому); tree — Дерево, владеющее узлом; treeNode — Узел в который следует добавлять подузлы; bRecursive — Следует ли раскрывать всю иерархию; bUseClassifiers — Добавлять ли классификаторы в иерархию | 
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный методы вызывается после применения каталога узлу дерева (если было) Параметры: node — Узел с которым ассоциирован данный каталог | 

#### `CSProject3D.CAD3DLibrary.<wbr>ShapesVersion15Updater`
**Назначение:** Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.

| Член | Тип | Описание |
|---|---|---|
| `UpdateShape(CSProject3D.CAD3DLibrary....` | метод | Производит обновление старой сетки из таблицы Shapes в новую в таблицах Mesh, Graphics Параметры: shape — старая фигура для преобразования; nWorker — номер работника для логирования ошибок; bOnServer — производить на сервере или не клиенте; sqlConnection — подключение | 
| `WorkerProc(System.Object)` | метод | Процедура для многопоточного обновления сетки Параметры: nWorkerNum — номер потока - отрицательный номер для обновления на сервере |
| `LogErrors(CADLibControls.Forms.AsyncP...` | метод | Выводит на форму ошибки, переданные работниками | 
| `GetOldShapesList` | метод | Возвращает список idShape фигур в таблице старой графики [Shapes] Возвращает: Список идентификаторов сеток |
| `CheckAndUpdateOldShapes` | метод | Проверяет имеются ли в библиотеки старая графика и если да, то преобразует её в новую (версии 1.5) |

#### `CSProject3D.CAxisPipeManager`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `MainForm3D` | свойство | Главная форма приложения |
| `Library` | свойство | Библиотека главной формы |
| `DATA_GROUP_AXIS_PIPE_CAPTION` | поле | Категория публикаций - имя группы структурных данных Значение параметра CADLibraryBase.SYS_CATEGORY_GROUP |
| `#ctor(CSProject3D.MainForm)` | метод | Конструктор плагина с авторегистрацией Параметры: mainForm3D — Главная форма МиА |
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Получение объекта по объекту БД Параметры: libObject — Исходные объект бибилотеки; strStructGroup — Группа даных структурных объектов Возвращает: объект сетки CCoordinateGrid или null, в случае, если libObject-другой объект | 

#### `CSProject3D.CLayerManager`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `MainForm3D` | свойство | Главная форма приложения |
| `Library` | свойство | Библиотека главной формы |
| `LayersCatGroup` | поле | Категория публикаций - имя группы структурных данных Значение параметра CADLibraryBase.SYS_CATEGORY_GROUP |
| `#ctor(CSProject3D.MainForm)` | метод | Конструктор плагина с авторегистрацией Параметры: mainForm3D — Главная форма МиА |
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Получение объекта по объекту БД Параметры: libObject — Исходные объект бибилотеки; strStructGroup — Группа даных структурных объектов Возвращает: объект сетки CCoordinateGrid или null, в случае, если libObject-другой объект | 

#### `CSProject3D.Collisions.Wizard.ProfilePage`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(WizardFormLib.WizardFormBase,CS...` | метод | Constructor that assumes the page type is "intermediate" Параметры: parent — The parent WizardFormBase-derived form | 
| `InitPage` | метод | This method serves as a common constructor initialization location, and serves mainly to set the desired size of the container panel in the wizard form (see WizardFormBase for more info). I didn't want to do this here but it was the only way I could get the form to resize itself appropriately - it needed to size itself according to the size of the largest wizard page. | 

#### `CSProject3D.DBViewerForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `HighlightSelection` | метод | Подсвечивает выбранные галочками объекты (с проверкой) |
| `foldersTreeMenu_Opening(System.Object...` | метод | Сложное определение видимости и активности пунктов контекстного меню каталогов Параметры: | 

#### `CSProject3D.Forms.Form2D`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(CSProject3D.CAD3DLibrary,CSProject3D.MainForm)` | метод | флаг сброса выбора связанного объекта |
| `ShowFiltered(System.String,System.Str...` | метод | Применяет новый фильтр к окну показа схемы Здесь же при первом вызове инициализируется компонент Параметры: | 

#### `CSProject3D.Forms.frmLinkToPropOrCode`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GetSelected3dParams` | метод | Возвращает выбранный пользователем параметр 3D объекта |
| `GetSelectedColumnParams` | метод | Возвращает выбранный пользователем столбец из диаграммы Гантта |

#### `CSProject3D.Forms.frmWorkFilterDlg`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GetResult` | метод | Результат применённых фильтров. Отсеиваются незаполненные фильтры |
| `HasResult` | свойство | результат применённых фильтров |

#### `CSProject3D.ModelRepresen<wbr>tation.ModelRepresentatio<wbr>nDlg`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `IsDefaultValue(Aga.Controls.Tree.Tree...` | метод | определения не редактируемого значения по умолчанию Параметры: node — Узел дереве - коллизия Возвращает: true если это значение по умолчанию и только для чтения | 
| `RefreshData(System.Boolean)` | метод | Обновляет данные окна коллизий После смены библиотеки данный метод вызывается из LoadUserState(), и будет работать отлько после этого Параметры: | 

#### `CSProject3D.ProjectCustom<wbr>HierarchyPlugin.CCustomHi<wbr>erachyFolder`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `FolderOrder` | свойство | ниже чем здания и сооружения сверху |
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `ExpandSubFolderNode(CADLib.CADLibrary...` | метод | Вызывается при раскрытии некастомных каталогов, вложенных в данный Параметры: lib — Библиотека, выполняющая операцию; expandingFolder — Раскрываемый каталог (подчинённый плагиновскому); tree — Дерево, владеющее узлом; treeNode — Узел в который следует добавлять подузлы; bRecursive — Следует ли раскрывать всю иерархию; bUseClassifiers — Добавлять ли классификаторы в иерархию | 
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный методы вызывается после применения каталога узлу дерева (если было) Параметры: node — Узел с которым ассоциирован данный каталог | 

#### `CSProject3D.ProjectStruct<wbr>ureHierarchyPlugin.CStruc<wbr>tureHierachyFolder`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

#### `CADLibWorkMgmt.DataColumnFilter`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `CheckedItems` | свойство | Результат фильтрации элементов |

#### `CSProject3D.Collisions.Wi<wbr>zard.ProfileSetupPage`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(WizardFormLib.WizardFormBase,CS...` | метод | Constructor that assumes the page type is "intermediate" Параметры: parent — The parent WizardFormBase-derived form | 
| `btnCreateSurface_Click(System.Object,...` | метод | Создать группу с названием Поверхность и сразу добавить в нее параметры для отбора объектов типа Поверхность Параметры: | 

#### `CSProject3D.Forms.Expertise.SendNotesForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `note` | поле | Ссылка на обозреваемый элемент списка замечаний |

#### `CSProject3D.Forms.ListProject.ProjOptions`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `CreateParamSet` | метод | Создание в БД набора общих параметров проекта. Вызывается автоматически при создании новой модели. Метод добавлен специально для доступа извне к необходимому функционалу ProjOptions для работы с БД (который, конечно, лучше вынести из класса диалога). Параметры: | 

#### `CSProject3D.Forms.ProjectDocumentsForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `UpdateDocTree` | метод | Загружает дерево документов проекта для выбранного объекта |

#### `CSProject3D.Forms.WorksLibForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GetSelectedSubroots(System.Collections.Generic.IEnumerable{WorksLib2.WorkItem})` | метод | Возвращает элементы верхнего уровня, полностью выбранные пользователем Параметры:  |

#### `CSProject3D.ModelRepresentation.MRObject`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `UpdateFromProfile` | метод | Актуализирует объект представления на основе данных из MRProfile |
| `m_treeNode` | свойство | Информация об объекте в дереве объектов |
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный методы вызывается после применения объекта узлу дерева (если было) Параметры: tree — Дерево объектов; node — Узел с которым ассоциирован данный объект | 
| `UpdateTreeIcon` | метод | Обновляет иконку дерева после изменения активности объекта |

#### `CSProject3D.ObjectPropertiesForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `ShowObjectProperties(CADLibKernel.CLi...` | метод | Показывает свойства объекта и переводит элемент управления свойств в режим одиночного показа Параметры: activeObject — Объект для показа Возвращает: Да, если что-то поменялось | 

#### `CSProject3D.Publications.PublicationsForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `RefreshData` | метод | Обновляет данные в окне публикаций |

#### `CSProject3D.UserTagging.D<wbr>ialogs.TagCommentDialog`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(CSProject3D.Viewer3DCtrl,CSProj...` | метод | Tag edit dialog constructor Параметры: viewer — Viewer to pick objects links; tagToEdit — Tag to be edited; onFinish — Callback to be executed when dialog is finished. If null - links are not enabled | 

#### `CSProject3D.UserTagging.D<wbr>ialogs.TagCommentDialogTy<wbr>pical`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(CSProject3D.Viewer3DCtrl,CSProj...` | метод | Tag edit dialog constructor Параметры: viewer — Viewer to pick objects links; tagToEdit — Tag to be edited; onFinish — Callback to be executed when dialog is finished. If null - links are not enabled | 

#### `CSProject3D.Works.MPJXWorkImporter`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `ImportUpdateTaskCSV(CADLibWorkMgmt.Pr...` | метод | Режим обновления задач для csv Параметры: prj — Проект в котором обновляем; task — Текущая обрабатываемая задача (из файла); idPar — Идентификатор ролителя; arrPWorks — Массив существующих работ | 
| `ImportUpdateTask(CADLibWorkMgmt.Proje...` | метод | Режим обновления задач для остальных форматов Параметры: prj — Проект в котором обновляем; task — Текущая обрабатываемая задача (из файла); arrPWorks — Массив существующих работ | 
| `ImportTaskSuccessor(CSProject3D.Works...` | метод | Связи между работами Связь является направленной и идёт от работы idPredecessor к работе idSuccessor Поля predDate и succDate определяют место подсоединения связи: 0 = начало работы, 1 = окончание работы | 

#### `CSProject3D.Works.WorkLibForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

#### `CSProject3D.Works.WorksVisualizer`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `EvaluateTransitions(System.Collection...` | метод | Точка входа расчётов Вычисляет сценарий раскраски сцены в виде временных точек с изменениями цветов Параметры: rootWorks — Список корневых работ; bFactPeriods — Факт или план; startDate — Дата начала расчётов (минимальная); endDate — Дата окончания расчётов (максимальная) | 
| `CollectDatesPoints(System.Collections...` | метод | Собирает все даты начал и окончаний работ, как точки в которые может меняться раскраска В список дат не включены дата начала и конца! Учитываются только работы со связанными объектами! Параметры: works — Список корневых работ; resDates — Массив для складывания результата; bFactPeriods — Факт или план; startDate — Минимальная валидная дата; endDate — Максимальная валидная дата | 
| `EvaluateSnapshot(System.Collections.G...` | метод | На основе предыдущих состояний и текущей даты вычисляет новые переходы цветов | 
| `CollectAllWorksObjects(System.Func{CA...` | метод | Рекурсивно собирает все объекты, связанные с работами, удовлетворяющими условию fnIsWorkToInclude Параметры: fnIsWorkToInclude — Функция, принимающая работу или задание и возвращающая ДА, если работу следует учитывать при сборе объектов; subworks — Набор корневыз работ по которым осуществляется сбор; arrResObjectsIds — Коллекция, куда будут помещены объекты - результат | 

#### `CADLibControls.CLibLinkedFilterDialog`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `components` | поле | Требуется переменная конструктора. |
| `Dispose(System.Boolean)` | метод | Освободить все используемые ресурсы. Параметры: disposing — истинно, если управляемый ресурс должен быть удален; иначе ложно. |
| `InitializeComponent` | метод | Обязательный метод для поддержки конструктора - не изменяйте содержимое данного метода при помощи редактора кода. |

#### `CADLibControls.FilterDialogTab`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

#### `CSProject3D.BuildingsHier<wbr>archyPlugin.CHierarchyObj<wbr>ect`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `ApplyToModelObjects(CSProject3D.CAD3D...` | метод | Связывает данный объект иерархии с объектами модели Старые связи с иерархией удаляются Параметры: destObjects — Список объектов модели | 
| `m_hierarchyLevel` | поле | Уровень иерархии |
| `CoordinateGridId` | свойство | Идентификатор связанной координатной сетки |

#### `CSProject3D.CPublicationsPluginFolderFilter`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `Node` | свойство | Информация об объекте в дереве объектов |
| `Manager` | свойство | Управляющий объект |
| `GetBlockFolderEditMenu` | метод | Возвращает признак, нужно ли блокировать пункты меню Создать копию/Очистить/Вырезать/Вставить |

#### `CSProject3D.Collisions.Co<wbr>llisionPlugin.CCollisionP<wbr>luginFolderFilter.CIntern<wbr>alFolder`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `SelectInModel_Click(System.Object,Sys...` | метод | Выбрать в 3D-модели все коллизии, относящиеся к текущему узлу раздела Коллизии Отличие в том, что выбирать сами коллизии для этого не нужно Параметры: | 
| `RemoveFromView_Click(System.Object,System.EventArgs)` | метод | Удалить из текущего вида Параметры:  |
| `HideFromView_Click(System.Object,System.EventArgs)` | метод | Скрыть из вида Параметры:  |

#### `CSProject3D.Collisions.Wi<wbr>zard.CollisionsSetupPage`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(WizardFormLib.WizardFormBase,CS...` | метод | Constructor that assumes the page type is "intermediate" Параметры: parent — The parent WizardFormBase-derived form | 

#### `CSProject3D.Collisions.Wizard.ExecutingPage`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(WizardFormLib.WizardFormBase,CS...` | метод | Constructor that assumes the page type is "intermediate" Параметры: parent — The parent WizardFormBase-derived form | 

#### `CSProject3D.Collisions.Wi<wbr>zard.ProfileSetupPage2`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(WizardFormLib.WizardFormBase,CS...` | метод | Constructor that assumes the page type is "intermediate" Параметры: parent — The parent WizardFormBase-derived form | 

#### `CSProject3D.Controls.Work<wbr>Mgmt.ColumnsEditor.DataCo<wbr>lumnEditorContext`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SelectedIndex` | свойство | Индекс текущего элемента |
| `SelectedItem` | свойство | Текущий элемент |
| `Move(CSProject3D.Controls.WorkMgmt.Co...` | метод | Меняет местами элементы списка Параметры: source — Список значений; sourceIndex — Индекс источника; targetIndex — Индекс назначения Возвращает: True если перемещение удалось | 

#### `CSProject3D.DocumentsFold<wbr>erPlugin.CRootFolder`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `FolderOrder` | свойство | ниже чем РП |
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный методы вызывается после применения каталога узлу дерева (если было) Параметры: node — Узел с которым ассоциирован данный каталог | 
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 

#### `CSProject3D.Forms.EncodingOpenFileDialog`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `components` | поле | Обязательная переменная конструктора. |
| `Dispose(System.Boolean)` | метод | Освободить все используемые ресурсы. Параметры: disposing — истинно, если управляемый ресурс должен быть удален; иначе ложно. |
| `InitializeComponent` | метод | Требуемый метод для поддержки конструктора — не изменяйте содержимое этого метода с помощью редактора кода. |

#### `CSProject3D.LayoutManager<wbr>.CLayoutPluginFolderFilte<wbr>r`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `OwnerPlugin` | свойство | родительский плагин |
| `ExpandSubFolderNode(CADLib.CADLibrary...` | метод | Вызывается при раскрытии некастомных каталогов, вложенных в данный Параметры: lib — Библиотека, выполняющая операцию; expandingFolder — Раскрываемый каталог (подчинённый плагиновскому); tree — Дерево, владеющее узлом; treeNode — Узел в который следует добавлять подузлы; bRecursive — Следует ли раскрывать всю иерархию; bUseClassifiers — Добавлять ли классификаторы в иерархию | 
| `FolderOrder` | свойство | Листы идут после коллизий |

#### `CSProject3D.Properties3D.ColorTypeConverter`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `GetStandardValuesSupported(System.ComponentModel.ITypeDescriptorContext)` | метод | Будем предоставлять выбор из списка |
| `GetStandardValuesExclusive(System.ComponentModel.ITypeDescriptorContext)` | метод | ... и только из списка |
| `GetStandardValues(System.ComponentModel.ITypeDescriptorContext)` | метод | А вот и список |

#### `CSProject3D.TrackBarStringConverter`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `CanConvertTo(System.ComponentModel.ITypeDescriptorContext,System.Type)` | метод | True if the destination type is a string |
| `ConvertFrom(System.ComponentModel.ITypeDescriptorContext,System.Globalization.CultureInfo,System.Object)` | метод | Convert from a string to a CMinMaxNumValue. |
| `ConvertTo(System.ComponentModel.ITypeDescriptorContext,System.Globalization.CultureInfo,System.Object,System.Type)` | метод | Converts from a CMinMaxNumValue to a string |

#### `CSProject3D.UserTagging.E<wbr>ntities.UserTaggingBase`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `IsSingleActivation` | свойство | If true it is restricted to activate more then one this kind of Tag simultaneously (at one object selection) |
| `IsSingleInstance` | свойство | Is true we can't add more then one this kind of Tag to object |
| `ApplyToViewer` | метод | Synchronize with 3D viewer |

#### `CSProject3D.Works.CSVProjectFile`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `StandartFields` | свойство | Стандартные поля |
| `UserSelectedFields` | свойство | Выбранные стандартные пользователем поля |
| `UserSelectedCustomFields` | свойство | Выбранные дополнительные пользователем поля |

#### `CSProject3D.Works.WorksVi<wbr>deoVisualizerForm.RecordS<wbr>tate`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `m_fRecTime` | поле | Прошедшее время записи |
| `m_bJustFinishedRecord` | поле | Устанавливается в true (из потока 3D движка) в момент окончания записи сценария |
| `m_currentRecordingDate` | поле | Текущая дата календаря по которой записывается кадр |

#### `CSProject3D.CatParamPickerStringConverter`
**Назначение:** Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.

| Член | Тип | Описание |
|---|---|---|
| `CanConvertFrom(System.ComponentModel.ITypeDescriptorContext,System.Type)` | метод | True if the source type is a string |
| `CanConvertTo(System.ComponentModel.ITypeDescriptorContext,System.Type)` | метод | True if the destination type is a string |

#### `CSProject3D.Collisions.Co<wbr>llisionPlugin.CCollisionP<wbr>luginFolderFilter`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `FolderOrder` | свойство | Коллизии идут после поверхностей |
| `GetBlockFolderEditMenu` | метод | Возвращает список пунктов меню Создать копию/Очистить/Вырезать/Вставить, которые надо блокировать |

#### `CSProject3D.Collisions.CollisionsTree`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `SetFilterNoRefresh(CSProject3D.Collis...` | метод | Устанавливает фильтр объектов без обновления дерева Параметры: | 
| `AssignFilter(CSProject3D.Collisions.C...` | метод | Фильтр объектов коллизии Установка приводит к обновлению списка | 

#### `CSProject3D.DocumentsFolderPlugin.CSubFolder`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `FolderObject` | свойство | Объект на основе которого сделан данный каталог |
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 

#### `CSProject3D.Forms.RelationsControl.TreeItem`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `IsObjectNode` | свойство | Является ли узлом объекта |
| `GetLibObjects` | метод | Получение объектов библиотеки, входящих в данный узел и его подузлы |

#### `CSProject3D.Forms.Relatio<wbr>nsControl.TreeObjectItem`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `IsLeftLink` | свойство | Находится ли данный связанный объект в таблице связей слева |
| `SelectObject(CADLib.DirectoryBrowserC...` | метод | Выбирает объект в МиА Параметры: browser — Окно БД для выбора подчинённого объекта; viewer — Вьювер для эмуляции клика по объекту или null | 

#### `CSProject3D.ModelRepresen<wbr>tation.MRFolderFilter`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

| Член | Тип | Описание |
|---|---|---|
| `FolderOrder` | свойство | порядок следования идет после коллизий |
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 

#### `CSProject3D.ModelRepresen<wbr>tation.MRPlugin.MRFolderF<wbr>ilter`
**Назначение:** Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам.

#### `CSProject3D.ProjectCustom<wbr>HierarchyPlugin.CPCHObjec<wbr>t`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `ApplyToModelObjects(CSProject3D.CAD3D...` | метод | Связывает данный объект иерархии с объектами модели Старые связи с иерархией удаляются Параметры: destObjects — Список объектов модели | 
| `m_hierarchyLevel` | поле | Уровень иерархии |

#### `CSProject3D.ProjectStruct<wbr>ureHierarchyPlugin.CPSHOb<wbr>ject`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

#### `CSProject3D.Properties3D.PointEditor`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `EditValue(System.ComponentModel.ITypeDescriptorContext,System.IServiceProvider,System.Object)` | метод | Реализация метода редактирования |
| `GetEditStyle(System.ComponentModel.ITypeDescriptorContext)` | метод | Возвращаем стиль редактора - модальное окно |

#### `CSProject3D.UserTagging.E<wbr>ntities.SelectionTrigger`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `TriggeringObjects` | свойство | UIDs of related objects to be triggers Empty list - all related |
| `ObjectsToSelect` | свойство | UIDs of additional objects to be selected Empty list - all related |

#### `CSProject3D.UserTagging.P<wbr>roperties.DrawingTag2dPro<wbr>perites.SubObjectsListEdi<wbr>tor`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

#### `CSProject3D.UserTagging.P<wbr>roperties.SelectionTrigge<wbr>rProperties.SubObjectsLis<wbr>tEditor`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

#### `CSProject3D.UserTagging.P<wbr>roperties.TagCommentPrope<wbr>rites.TagInfoEditor`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

#### `CSProject3D.UserTagging.P<wbr>roperties.TagCommentPrope<wbr>ritesTypical.TagInfoEdito<wbr>r`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

#### `CSProject3D.UserTagging.P<wbr>roperties.VariantEditor`
**Назначение:** Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.

#### `CSProject3D.UserTagging.V<wbr>ector2d.Vector2dCanvas`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `NeedRedraw` | событие | need to ReportRedrawNeeded shapes All=true : ReportRedrawNeeded all graphic All=false : ReportRedrawNeeded only selected objects |
| `ReportRedrawNeeded(System.Boolean)` | метод | redraws this.m_shapes on this control All=true : ReportRedrawNeeded all graphic All=false : ReportRedrawNeeded only selected objects | 

#### `CSProject3D.WorkMaterialO<wbr>verrideSettings.MaterialO<wbr>verrideTypeConverter`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `GetStandardValuesSupported(System.ComponentModel.ITypeDescriptorContext)` | метод | Будем предоставлять выбор из списка |
| `GetStandardValues(System.ComponentModel.ITypeDescriptorContext)` | метод | А вот и список |

#### `CADLibControls.CLibLinked<wbr>FilterDialog.LinkedObject<wbr>sTab`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GetTabControlImageIndexByKey(System.S...` | метод | По каким-то причинам не получается показать картинку на вкладке по ImageKey Этот метод получает индекс картинки по ключу Параметры: strImageKey — ключ Возвращает: индекс картинки | 

#### `CSProject3D.CSSettings3D`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `MainForm` | свойство | Главная форма приложения (устанавливается при создании формы) |

#### `CSProject3D.Forms.CVideoR<wbr>ecorderCodecSettings`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GetEditStyle(System.ComponentModel.ITypeDescriptorContext)` | метод | Возвращаем стиль редактора - модальное окно |

#### `CSProject3D.Forms.Viewer3D.ClipBoxSettings`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `XMinAxis` | свойство | 0 == INF, далее индекc точки на оси |

#### `CSProject3D.Properties3D.<wbr>IPositionOrientation`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `GetIsDifferent(CSProject3D.Properties...` | метод | For multi select | 

#### `CSProject3D.UserTagging.E<wbr>ntities.DrawingTag2d`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `OnNew2dDataApplied` | событие | Вызывается при применении нового чертежа (нажатии кнопки "Сохранить" на панели редактора) |

#### `CSProject3D.UserTagging.U<wbr>serTaggingController`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `RelatedObjectsIds` | свойство | Задаёт объекты для показа в дереве |

#### `CSProject3D.Viewer3DCtrl.FastInteroperation`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `Invoke3DSynchronously(System.Action)` | метод | Выполняет работу синхронно в потоке движка Если данный метод уже выполняется из потока движка, то работа выполняется напрямую, иначе происходит ожидание с определённым timeout Параметры: task — Работа для выполнения | 

#### `CSProject3D.Works.CSVReader`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

| Член | Тип | Описание |
|---|---|---|
| `SearchParent(System.Int32@,CSProject3D.Works.TaskInfo)` | метод | Поиск родителя путём рекурсии для варианта с сепаратором ; |

#### `CSProject3D.Works.ExcelReader`
**Назначение:** Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление.

### 6.2. `CADLibControls`

#### `CADLibControls.Properties.Resources`
**Назначение:** A strongly-typed resource class, for looking up localized strings, etc.

| Член | Тип | Описание |
|---|---|---|
| `ResourceManager` | свойство | Returns the cached ResourceManager instance used by this class. |
| `Culture` | свойство | Overrides the current thread's CurrentUICulture property for all resource lookups using this strongly typed resource class. |
| `_041_Sort_16x16_72` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `acad` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `ActualSize` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `addobjects` | свойство | Looks up a localized resource of type System.Drawing.Icon similar to (Icon). |
| `AddParams` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `AlphaSort` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `AngelSmile` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `AngrySmile` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `base_cog_32` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `basket` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `basket_add` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `basket_pls` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Beer` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `BrokenHeart` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `BuilderDialog_AddAll` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `BuilderDialog_RemoveAll` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `building` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CADLib` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CADLib1` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CADLib16` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `catProps` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CatSort` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cb_checked` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cb_unchecked` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `chain` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `chainR` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `chainWithArrow` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `changepass` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `check` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `childTreeItem` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `classifier_new` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `ClearParams` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `ClearValues` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `clipboard` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `clpPublication` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Collapsed` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `colorbarIndicators` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Comment` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `ConfusedSmile` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Copy` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CopyHS` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `CrySmile` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `cut` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `delete` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `DelMultiParam` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `DelParam` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `DevilSmile` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `dockLeft` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `dropdown` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `dropdown_separator` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Edit_UndoHS` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `EditInformation` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `EmbarassedSmile` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `erase` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `exclcmction` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `exportCSV` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `eyedropper` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| `Find` | свойство | Looks up a localized resource of type System.Drawing.Bitmap. |
| ... | ... | Ещё 87 членов класса опущены в основной таблице, см. полный машинный индекс ниже. |

#### `CADLibControls.ExRichTextBox`
**Назначение:** This class adds the following functionality to RichTextBox: 1. Allows plain text to be inserted or appended programmatically to RTF content. 2. Allows the font, text color, and highlight color of plain text to be specified when inserting or appending text as RTF. 3. Allows images to be inserted programmatically, or with interaction from the user.

| Член | Тип | Описание |
|---|---|---|
| `#ctor` | метод | Initializes the text colors, creates dictionaries for RTF colors and font families, and stores the horizontal and vertical resolution of the RichTextBox's graphics context. | 
| `#ctor(CADLibControls.RtfColor)` | метод | Calls the default constructor then sets the text color. Параметры:  |
| `#ctor(CADLibControls.RtfColor,CADLibControls.RtfColor)` | метод | Calls the default constructor then sets te text and highlight colors. Параметры:  |
| `AppendRtf(System.String)` | метод | Assumes the string passed as a paramter is valid RTF text and attempts to append it as RTF to the content of the control. Параметры:  |
| `InsertRtf(System.String)` | метод | Assumes that the string passed as a parameter is valid RTF text and attempts to insert it as RTF into the content of the control. Параметры: | 
| `AppendTextAsRtf(System.String)` | метод | Appends the text using the current font, text, and highlight colors. Параметры:  |
| `AppendTextAsRtf(System.String,System.Drawing.Font)` | метод | Appends the text using the given font, and current text and highlight colors. Параметры:  |
| `AppendTextAsRtf(System.String,System....` | метод | Appends the text using the given font and text color, and the current highlight color. Параметры: | 
| `AppendTextAsRtf(System.String,System....` | метод | Appends the text using the given font, text, and highlight colors. Simply moves the caret to the end of the RichTextBox's text and makes a call to insert. Параметры: | 
| `InsertTextAsRtf(System.String)` | метод | Inserts the text using the current font, text, and highlight colors. Параметры:  |
| `InsertTextAsRtf(System.String,System.Drawing.Font)` | метод | Inserts the text using the given font, and current text and highlight colors. Параметры:  |
| `InsertTextAsRtf(System.String,System....` | метод | Inserts the text using the given font and text color, and the current highlight color. Параметры: | 
| `InsertTextAsRtf(System.String,System....` | метод | Inserts the text using the given font, text, and highlight colors. The text is wrapped in RTF codes so that the specified formatting is kept. You can only assign valid RTF to the RichTextBox.Rtf property, else an exception is thrown. The RTF string should follow this format ... {\rtf1\ansi\ansicpg1252\deff0\deflang1033{\fonttbl{[FONTS]}{\colortbl ;[COLORS]}} \viewkind4\uc1\pard\cf1\f0\fs20 [DOCUMENT AREA] } Параметры: | 
| `GetDocumentArea(System.String,System....` | метод | Creates the Document Area of the RTF being inserted. The document area (in this case) consists of the text being added as RTF and all the formatting specified in the Font object passed in. This should have the form ... \viewkind4\uc1\pard\cf1\f0\fs20 [DOCUMENT AREA] } Параметры: Возвращает: The document area as a string. | 
| `InsertImage(System.Drawing.Image,Syst...` | метод | Inserts an image into the RichTextBox. The image is wrapped in a Windows Format Metafile, because although Microsoft discourages the use of a WMF, the RichTextBox (and even MS Word), wraps an image in a WMF before inserting the image into a document. The WMF is attached in HEX format (a string of HEX numbers). The RTF Specification v1.6 says that you should be able to insert bitmaps, .jpegs, .gifs, .pngs, and Enhanced Metafiles (.emf) directly into an RTF document without the WMF wrapper. This works fine with MS Word, however, when you don't wrap images in a WMF, WordPad and RichTextBoxes simply ignore them. Both use the riched20.dll or msfted.dll. Параметры: | 
| `GetRtfImage(System.Drawing.Image,Syst...` | метод | Creates the RTF control string that describes the image being inserted. This description (in this case) specifies that the image is an MM_ANISOTROPIC metafile, meaning that both X and Y axes can be scaled independently. The control string also gives the images current dimensions, and its target dimensions, so if you want to control the size of the image being inserted, this would be the place to do it. The prefix should have the form ... {\pict\wmetafile8\picw[A]\pich[B]\picwgoal[C]\pichgoal[D] where ... A = current width of the metafile in hundredths of millimeters (0.01mm) = Image Width in Inches * Number of (0.01mm) per inch = (Image Width in Pixels / Graphics Context's Horizontal Resolution) * 2540 = (Image Width in Pixels / Graphics.DpiX) * 2540 B = current height of the metafile in hundredths of millimeters (0.01mm) = Image Height in Inches * Number of (0.01mm) per inch = (Image Height in Pixels / Graphics Context's Vertical Resolution) * 2540 = (Image Height in Pixels / Graphics.DpiX) * 2540 C = target width of the metafile in twips = Image Width in Inches * Number of twips per inch = (Image Width in Pixels / Graphics Context's Horizontal Resolution) * 1440 = (Image Width in Pixels / Graphics.DpiX) * 1440 D = target height of the metafile in twips = Image Height in Inches * Number of twips per inch = (Image Height in Pixels / Graphics Context's Horizontal Resolution) * 1440 = (Image Height in Pixels / Graphics.DpiX) * 1440 Wraps the image in an Enhanced Metafile by drawing the image onto the graphics context, then converts the Enhanced Metafile to a Windows Metafile, and finally appends the bits of the Windows Metafile in HEX to a string and returns the string. Возвращает: A string containing the bits of a Windows Metafile in HEX | 
| `GetFontTable(System.Drawing.Font)` | метод | Creates a font table from a font object. When an Insert or Append operation is performed a font is either specified or the default font is used. In any case, on any Insert or Append, only one font is used, thus the font table will always contain a single font. The font table should have the form ... {\fonttbl{\f0\[FAMILY]\fcharset0 [FONT_NAME];} Параметры: | 
| `GetColorTable(CADLibControls.RtfColor...` | метод | Creates a font table from the RtfColor structure. When an Insert or Append operation is performed, _textColor and _backColor are either specified or the default is used. In any case, on any Insert or Append, only three colors are used. The default color of the RichTextBox (signified by a semicolon (;) without a definition), is always the first color (index 0) in the color table. The second color is always the text color, and the third is always the highlight color (color behind the text). The color table should have the form ... {\colortbl ;[TEXT_COLOR];[HIGHLIGHT_COLOR];} Параметры: | 
| `RemoveBadChars(System.String)` | метод | Called by overrided RichTextBox.Rtf accessor. Removes the null character from the RTF. This is residue from developing the control for a specific instant messaging protocol and can be ommitted. Параметры: Возвращает: RTF without null character | 
| `InsertLink(System.String)` | метод | Insert a given text as a link into the RichTextBox at the current insert position. Параметры: text — Text to be inserted |
| `InsertLink(System.String,System.Int32)` | метод | Insert a given text at a given position as a link. Параметры: text — Text to be inserted; position — Insert position |
| `InsertLink(System.String,System.String)` | метод | Insert a given text at at the current input position as a link. The link text is followed by a hash (#) and the given hyperlink text, both of them invisible. When clicked on, the whole link text and hyperlink string are given in the LinkClickedEventArgs. Параметры: text — Text to be inserted; hyperlink — Invisible hyperlink string to be inserted | 
| `InsertLink(System.String,System.Strin...` | метод | Insert a given text at a given position as a link. The link text is followed by a hash (#) and the given hyperlink text, both of them invisible. When clicked on, the whole link text and hyperlink string are given in the LinkClickedEventArgs. Параметры: text — Text to be inserted; hyperlink — Invisible hyperlink string to be inserted; position — Insert position | 
| `SetSelectionLink(System.Boolean)` | метод | Set the current selection's link style Параметры: link — true: set link style, false: clear link style |
| `GetSelectionLink` | метод | Get the link style for the current selection Возвращает: 0: link style not set, 1: link style set, -1: mixed |

#### `CADLibControls.Forms.AsyncProgressForm`
**Назначение:** Форма и менеджер выполнения операции в фоновом потоке с поддержкой отмены, показа процента выполнения и лога

| Член | Тип | Описание |
|---|---|---|
| `IsActive` | свойство | Показывается ли сейчас форма выполнения фоновой операции Приложение не выполняет UpdateButtons в Application_Idle, если это свойство true Метод set временно активен в свойстве, т.к. это единственный способ запретить обновление кнопок извне | 
| `OperationText` | свойство | Текст текущей операции в окне |
| `IsAborted` | свойство | Да, если была нажата или вызвана отмена |
| `IsCriticalError` | свойство | Да, если процесс завершился ошибкой |
| `ShowAbortButton` | свойство | Управление видимостью кнопки "Отмена" |
| `AbortButtonEnabled` | свойство | Управление активностью кнопки "Отмена" |
| `AutoClose` | свойство | Состояние галочки автоматического закрытия окна |
| `MaxProgress` | свойство | Максимальное (конечное) число прогресса |
| `ShowDetailButton` | свойство | Показывать ли кнопку "Детали" |
| `ShowDetails` | свойство | Управление состоянием диалога - показывать или нет детали (да - активирует кнопку "Детали") |
| `WorkerThread` | свойство | Рабочий поток создаётся автоматически при использовании PerformAsyncWork, либо задаётся при внешнем использовании диалога для возможности принудительной отмены операции | 
| `CurrentProgress` | свойство | Текущий прогресс |
| `PerformAsyncWork(System.Windows.Forms...` | метод | Статический метод показа формы во время выполнения длительной операции work. Выполняет работу в фоновом потоке с ловлей исключений в качестве критических ошибок и автоматическим вызовом FinishProgress по завершении. Для показа формы использовается метод ShowDialogDelayed. Параметры: parentForm — Родительское окно; work — Работа для выполнения, подразумевается, что она сообщает свой процент выполнения и ведёт логгирование (но не обязательно); strWorkTitle — Название работы на русском языке для заголовка (например Импорт объетов); bSupportAbort — Определяет показывать ли кнопку "Прервать" (см. IsAborted); bSupportReporting — Определяет показывать ли кнопку "Детали" (см. UpdateProgress); nShowProgressDelay — Задержка показа формы в миллисекундах Возвращает: True в случае успешного завершения операции (работы) | 
| `PerformAsyncWork(System.Action{CADLib...` | метод | Выполняет работу в фоновом потоке с ловлей исключений в качестве критических ошибок и автоматическим вызовом FinishProgress по завершении. Для показа формы использовается метод ShowDialogDelayed. Параметры: work — Работа для выполнения, подразумевается, что она сообщает свой процент выполнения и ведёт логгирование (но не обязательно); strWorkTitle — Название работы на русском языке для заголовка (например Импорт объетов); nShowProgressDelay — Задержка показа формы в миллисекундах Возвращает: True в случае успешного завершения операции (работы) | 
| `ShowDialogDelayed(System.Int32)` | метод | Показывает диалог с задержкой времени, необходимой для устранения мелькания диалога в случае, если выполнение операции длится меньше, чем указанная задержка. Диалог нельзя будет закрыть до вызова FinishProgress или CriticalError. Параметры: nDelay — Задержка в миллисекундах | 
| `UpdateProgress(System.Int32,System.St...` | метод | Позволяющий выводить сообщения, процент завершения операции. Может вызываться из любого потока (создан для вызова из потока-работника). Вызов данного метода не обновляет окно сразу, а кэшируется, что позволяет вызывать его с любой частотой. Параметры: nProgress — Процент выполнения, если [0..MAX], Значение "-1", означает только вывод сообщения strMsg (если задано) Значения больше MAX позволяет не показывать процент выполнения (бегунок); strMsg — Сообщение для добавления в лог (без завершающего Enter) Если сообщение начинается со строки "[MSG_BOX]", то оно будет показано в MessageBox | 
| `FinishProgress` | метод | Вызывается для завершения диалога по окончании операции Данный метод может закрыть диалог, либо оставит его открытым в случае снятой галочки "Закрывать окно по завершении" Вызов данного метода обязателен (при нормальной работе) и производится из потока-работника При возникновении критической ошибки вместо него вызывается CriticalError | 
| `CriticalError(System.Exception)` | метод | Вызывается в случае критической ошибки из-за который импорт невозможен Параметры: exception — Исключение для логгирования подробностей | 
| `RunningOnWin7` | свойство | Determines if the application is running on Windows 7 |

#### `CADLib.CADLibrary.CCustomFilterItem`
**Назначение:** Каталог для поддержания плагинами Содержимое каталога и подкаталоги запрашиваются у данной папки

| Член | Тип | Описание |
|---|---|---|
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный метод вызывается после применения каталога узлу дерева (если было) Параметры: node — Узел с которым ассоциирован данный каталог | 
| `ExpandFolderNode(CADLib.CADLibrary,Sy...` | метод | Раскрытие каталога (вверху в окне БД) в TreeView Параметры: lib — Библиотека, выполняющая операцию; tree — Дерево, владеющее узлом; treeNode — Узел в который следует добавлять подузлы; bRecursive — Следует ли раскрывать всю иерархию; bUseClassifiers — Добавлять ли классификаторы в иерархию | 
| `ExpandSubFolderNode(CADLib.CADLibrary...` | метод | Вызывается при раскрытии некастомных каталогов, вложенных в данный Параметры: lib — Библиотека, выполняющая операцию; expandingFolder — Раскрываемый каталог (подчинённый плагиновскому); tree — Дерево, владеющее узлом; treeNode — Узел в который следует добавлять подузлы; bRecursive — Следует ли раскрывать всю иерархию; bUseClassifiers — Добавлять ли классификаторы в иерархию | 
| `GetFolderMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню, для каталога организованного плагином и его подкаталогов | 
| `GetBlockSubfolderEditMenu(CADLibKerne...` | метод | Следует ли блокировать показ стандартных пунктов меню создания подкаталогов "создать выборку" и т.д. для каталога или подкаталога плагина | 
| `GetFolderIconKey(System.Windows.Forms.ImageList)` | метод | Получение иконки для каталога Параметры:  |
| `IsFolderVisible` | метод | Если необходимо скрыть каталог из дереве, то метод должен вернуть false Проверяется в момент добавления в дерево Возвращает: Видимость каталога |
| `FolderOrder` | свойство | Возвращает порядок следования каталога в дереве 0 - естественный порядок как в БД меньше нуля 0 - каталог добавляется в дереве выше естественного порядка, сортируясь среди других пользовательских каталогов больше нуля - каталог добавляется ниже, сортируясь среди других пользовательских каталогов, у которых FolderOrder > 0 | 
| `TryReadFolderObject(System.Data.IData...` | метод | Считывание корневого объекта данного каталога Метод может быть использован для добавления объектов-наследников CCustomLibObjectInfo Параметры: reader — считанные данные; idx — номер объекта Возвращает: возвращает null если необходимо использовать стандартный механизм чтения объектов | 
| `ShowObjectsTree(CADLibKernel.CLibCata...` | метод | Заполнение дерева объектов узлами с объектами (в tag узла необходимо записать наследников CLibObjectInfo) Параметры: folder — Каталог для которого необходимо показать объекты (может быть стандартным вложенным каталогом); tvObjects — Дерево объектов назначения; nPageSize — Размер страницы объектов; strMinName — Позиция начала страницы; strMaxName — Позиция конца страницы; bForward — Листание вперёд; bSelect — Выделять ли добавленные узлы дерева Возвращает: Если вернуть false, то будет использован стандартный механизм добавления объектов каталога | 
| `GetFilterExpressions(System.String@,S...` | метод | Получение выражений для запроса выборки данной папки из БД Используется для формирования корневых фильтров у кастомных папок ", Parameters_STR PT0 where (PT0.idObject = O.idObject) AND (PT0.idParamDef = 1) AND (PT0.Value='Координатные сетки')" strFrom = ", Parameters_STR PT0" strWhere = "(PT0.idObject = O.idObject) AND (PT0.idParamDef = 1) AND (PT0.Value='Координатные сетки')" По умолчанию части запроса извлекаются из CoreFilter, что не желательно, т.к. не используется nTableIndex Параметры: strFrom — Результируюющая строка с дополнительными тиблицами выборки (перед where); strWhere — Результирующая строка с условиями выборки (после where); nTableIndex — Дополнительный номер к псевдонимам таблиц, чтобы избежать их дублирования | 
| `FindParentCustomItem(CADLibKernel.CLi...` | метод | Поиск плагина, владеющего данным каталогом (текущий или его родители вверх по дереву) Параметры: catalog — Где искать Возвращает: Папку плагина или null | 

#### `CADLibControls.Forms.HRESULT`
**Назначение:** HRESULT Wrapper This is intended for Library Internal use only.

| Член | Тип | Описание |
|---|---|---|
| `S_FALSE` | поле | S_FALSE |
| `S_OK` | поле | S_OK |
| `E_INVALIDARG` | поле | E_INVALIDARG |
| `E_OUTOFMEMORY` | поле | E_OUTOFMEMORY |
| `E_NOINTERFACE` | поле | E_NOINTERFACE |
| `E_FAIL` | поле | E_FAIL |
| `E_ELEMENTNOTFOUND` | поле | E_ELEMENTNOTFOUND |
| `TYPE_E_ELEMENTNOTFOUND` | поле | TYPE_E_ELEMENTNOTFOUND |
| `NO_OBJECT` | поле | NO_OBJECT |
| `ERROR_CANCELLED` | поле | Win32 Error code: ERROR_CANCELLED |
| `E_ERROR_CANCELLED` | поле | ERROR_CANCELLED |
| `RESOURCE_IN_USE` | поле | The requested resource is in use |

#### `CADLibControls.FolderPlugin`
**Назначение:** базовый класс для работы с папками категорий из плагинов

| Член | Тип | Описание |
|---|---|---|
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Вызывается для корневых каталогов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `CreateVirtualFolderObject(CADLibKerne...` | метод | Создаёт информацию о папке с использованием плагинов(пиртуальная папка) Вызывается для корневых каталогов Возвращает: элемент дерева каталогов-категорий | 
| `CreateSubFolder(CADLibKernel.CLibCata...` | метод | Вызывается при создании некорневых узлов папок (например в методе ExpandSubfolders) Параметры: | 
| `CreateSubClassifier(CADLibKernel.CLib...` | метод | Вызывается при создании некорневых узлов классификаторов (например в методе ExpandSubfolders) Параметры: | 
| `ReportObjectPicked(CADLibKernel.CLibO...` | метод | Вызывается при двойном клики по объекту в 3д - позволяет плагинам обработать клик и запретить форме менять папку Параметры: libObject — Объект по которуму ткнули; strStructGroup — Группа данных структурнуго объекта или null если не структурный; bSupressSelectionFolderHighlighting — Устанавливается в Да, если необходимо запретить выделать папку "выбранные объекты" | 
| `TryGetLibraryObject(CADLibKernel.CLib...` | метод | Запрашивает у плагина объект Параметры: libObject — стандартный объект; strStructGroup — Группа данных структурнуго объекта или null если не структурный Возвращает: Кастомный объект или null | 
| `GetObjectMenuItems(CADLibKernel.CLibC...` | метод | Получение дополнительного меню для объектов Параметры: folder — Активный каталог (плагина или его подчинённый); selection — Выбранные в дереве объекты; menu — Меню в которое будут добавлены дополнительные пункты (для возможности заблокировать их видимость) Возвращает: Список дополнительных пунктов меню | 
| `GetAdditionalCurrenViewObjects` | метод | Получает дополнительные объекты из текущего вида Имеет значение для таких плагинов как "поверхности земли", которые показывают дополнительные объекты во вьювере, но они не отображаются в узле "Текущий вид". Тем не менее данные объекты должны быть обработаны во время выбора опции "Текущий вид" при экспорте или проверке коллизий. Возвращает: Идентификаторы дополнительных объектов, показанные плагином | 

#### `WizardFormLib.WizardPageChain`
**Назначение:** This class maintains a list of visited wizard pages, and manages visibility of those pages. If a page has been visited on the way to the stop page, it will be in this list.

| Член | Тип | Описание |
|---|---|---|
| `Count` | свойство | Get the number of pages currently in the list |
| `PageChain` | свойство | Get the wizard page chain list |
| `#ctor(WizardFormLib.WizardFormBase)` | метод | Constructor Параметры: parent — The WizardFormBase that conatins this chain |
| `GetCurrentPage` | метод | Get the current page (the last page in the list). |
| `GoFirst` | метод | Moves to the first wizard page. All pages except the first page are also removed from the page chain list, and the remaining page is shown. Возвращает: The new current wizard page | 
| `GoBack` | метод | Moves backwards through the chain of viewed property pages. It removes the last page from the list, and shows the new last page in the list. Возвращает: The new current wizard page | 
| `GoNext(WizardFormLib.WizardPage)` | метод | Adds the specified page to the list, hides the old current page, and shows the newly added page. Параметры: nextPage — The wizard page to add to the list Возвращает: The new current wizard page | 
| `SaveData` | метод | Cycles through each page in the list (starting with the first one), and calls the SaveData function in that page. If a page returns false, this method will return the page that faulted. Возвращает: The WizardPage object that failed during the save data process | 

#### `CADLib.CADLibrary.CCustomLibObjectInfo`
**Назначение:** объект поддерживаемый плагинами

| Член | Тип | Описание |
|---|---|---|
| `OwnerPlugin` | свойство | плагин, владеющий объектом |
| `GetObjectIconIndex(System.Windows.Forms.ImageList)` | метод | Получение иконки для объекта Параметры:  |
| `GetObjectIconKey(System.Windows.Forms.ImageList)` | метод | Получение иконки для объекта Параметры:  |
| `TryExpandObjectNode(System.Windows.Fo...` | метод | Раскрывает узел объекта Параметры: treeNode — Узел дерева родительского объекта (вызываемого) Возвращает: возвращает true - если плагин заполнил дерево, иначе false - дерево заполняется стандартными средствами | 
| `SetTreeNode(System.Windows.Forms.Tree...` | метод | Данный методы вызывается после применения объекта узлу дерева (если было) Параметры: node — Узел с которым ассоциирован данный объект | 
| `Need3DFocus` | метод | Позволяет отменить выделение на объекте при двойном клике Возвращает: false, если необходимо отменить стандартное поведение по выделению 3d родителя этого объекта | 
| `OnMouseDoubleClick(System.Windows.Forms.TreeNode)` | метод | Вызывается при двойно клике по объекту в дереве объектов Параметры:  |

#### `CADLib.PluginsManager`
**Назначение:** Класс для управления плагинами

| Член | Тип | Описание |
|---|---|---|
| `MainForm` | свойство | Главная форма из главного плагина После загрузки всех плагинов она будет показана как основная |
| `ShowSplash` | свойство | Показывать ли сплэш картинку во время зугрузки |
| `Load(System.String)` | метод | Загружает главный плагин, имеющий главное окно Если загрузка не успешна, то программа прекращает свою работу Параметры: strPluginsConfigPath — путь xml-документа с описанием плагинов | 
| `UpdateButtons(CADLib.LibConnectionState,CADLib.LibFolderState,CADLib.LibObjectState,System.Boolean[])` | метод | Этот метод вызывается плагином во время изменения статуса |
| `MergeInterfaceMenus(System.Windows.Forms.MenuStrip)` | метод | Объединение меню плагина с главным меню приложения Параметры: menu — Меню плагина |
| `MergeInterfaceToolbars(System.Windows...` | метод | Объединение панелей инструментов плагина с главной формой Параметры: pluginContainer — Панели инструментво плагина | 
| `ScanAndAddMenu(System.Windows.Forms.T...` | метод | Рекурсивная часть объединения меню Параметры: curInLevel — Текущее подменю, куда добавлять подпункты; menu — Текущее подменю с подпунктами | 

#### `NCI.Windows.Controls.PromptedTextBox`
**Назначение:** Draws a textbox with a prompt inside of it, similar to the "Quick Search" box in Outlook 2007, IE7 or the Firefox 2.0 search box. The prompt will disappear when the focus is placed in the textbox, and will not display again if the Text property contains any value. If the Text property is empty, then the prompt will display again when the textbox loses the focus.

| Член | Тип | Описание |
|---|---|---|
| `#ctor` | метод | Public constructor |
| `OnEnter(System.EventArgs)` | метод | When the textbox receives an OnEnter event, select all the text if any text is present Параметры:  |
| `OnTextAlignChanged(System.EventArgs)` | метод | Redraw the control when the text alignment changes Параметры:  |
| `OnPaint(System.Windows.Forms.PaintEventArgs)` | метод | Redraw the control with the prompt Параметры:  |
| `WndProc(System.Windows.Forms.Message@)` | метод | Overrides the default WndProc for the control Параметры: m — The Windows message structure |
| `DrawTextPrompt` | метод | Overload to automatically create the Graphics region before drawing the text prompt |
| `DrawTextPrompt(System.Drawing.Graphics)` | метод | Draws the PromptText in the TextBox.ClientRectangle using the PromptFont and PromptForeColor Параметры: g — The Graphics region to draw the prompt on | 

#### `CADLib.InterfaceItemState.TrackerSupressor`
**Назначение:** Класс, необходимый для приостановки синхронизации элемента управления Присвойте экземпляр данного класса полю Tag элемента управления и он не будет участвовать в синхронизации Т.о. появляется возможность использовать сложное поведение в обработчике события Opening меню для безопасности в начале обработчика Opening рекомендуется установить Tag=null

| Член | Тип | Описание |
|---|---|---|
| `SupressInterfaceTracking(System.Windo...` | метод | Приостанавливает синхронизацию пункта меню трэкером Параметры: item — Пунк меню, видимость которого необходимо фиксировать; reason — Причина блокировки для отладки (любая строка) Возвращает: Объект блокировки | 
| `ResumeInterfaceTracking(System.Window...` | метод | Восстанавливает трэкинг пункта меню, возвращает ему исходные параметры Если трэкинг был остановлен много раз, то снимаются все блокировки Параметры: item — Пункт меню для восстановления исходного состояния Возвращает: Да, если был приостановлен трэкинг пункта меню | 
| `MenuItemVisible` | свойство | Используется для хранения исходной видимости пункта меню |
| `MenuItemEnabled` | свойство | Используется для хранения исходной активности пункта меню |
| `Tag` | свойство | Используется для хранения исходного тэга пункта меню |
| `Reason` | свойство | Причина блокировки для отладки |

#### `CADLib.ICADLibMainPlugin`
**Назначение:** Абстрактный класс, реализованный в главных плагинах. Извлекается вызовом метода CADLibPluginEntryPoint.RegisterPlugin(PluginsManager manager).

| Член | Тип | Описание |
|---|---|---|
| `GetDataBrowser` | метод | Используются только в плагинах с главной формой Возвращает: Интерфейс объекта работы с базой данных |
| `GetMainForm` | метод | Используются только в плагинах с главной формой Возвращает главную форма, которая будет запущена как основная Возвращает: Главная форма приложения |
| `GetMainFormToolBar` | метод | Используются только в плагинах с главной формой Возвращает главную панель инструментов, чтобы добавлять кнопки других плагинов Если не указана, то добавление кнопок с других плагинов не производится Возвращает: Панель инструментов главной формы приложения или null | 
| `GetMainFormMenu` | метод | Используются только в плагинах с главной формой Возвращает главное меню, чтобы другие плагины добавлять пункты других плагинов Если null, то добавление пунктов меню из плагинов не производится Возвращает: Главное меню главной формы приложения или null | 

#### `CADLib.CADLibrary.CLinkedObjectsLnkTypesNode`
**Назначение:** Класс кастомного объекта для узла "Связи" в дереве объектов При раскрытии объект данного класса показывает доступные типы связей в виде узлов CLinkedObjectsNode

| Член | Тип | Описание |
|---|---|---|
| `m_arrRelTypes` | поле | Доступные типы связей CLibObjectInfo с другими объектами (получаются из GetLinkedObjectLinksTypes перед вызовом конструктора) |
| `Need3DFocus` | метод | Блокирует фокус на 3D |
| `TryExpandObjectNode(System.Windows.Fo...` | метод | Раскрывает узел объекта - выводит по подчинённому узлу CLinkedObjectsNode для каждого доступного типа связи Параметры: treeNode — Узел дерева родительского объекта (вызываемого) Возвращает: true | 

#### `CADLib.DynamicPropertyFilterAttribute`
**Назначение:** Атрибут для поддержки динамически показываемых свойств

| Член | Тип | Описание |
|---|---|---|
| `PropertyName` | свойство | Название свойства, от которого будет зависить видимость |
| `ShowOn` | свойство | Значения свойства, от которого зависит видимость (через запятую, если несколько), при котором свойство, к которому применен атрибут, будет видимо. |
| `#ctor(System.String,System.String)` | метод | Конструктор Параметры: propertyName — Название свойства, от которого будет зависеть видимость; value — Значения свойства (через запятую, если несколько), при котором свойство, к которому применен атрибут, будет видимо. | 

#### `CADLib.ICADLibPlugin`
**Назначение:** Абстрактный класс, реализованный во всех плагинах. Извлекается вызовом метода CADLibPluginEntryPoint.RegisterPlugin(PluginsManager manager).

| Член | Тип | Описание |
|---|---|---|
| `GetMenu` | метод | Метод для получения главного меню плагина, для последующего объединения элементов Возвращает: Главное меню плагина или null |
| `GetToolbars` | метод | Метод для получения панели инструментов плагина, для последующего объединения контролов с неё Возвращает: Панель инструментов плагина или null |
| `TrackInterfaceItems(CADLib.InterfaceT...` | метод | Метод для реализации обработки состояния элементов управления в зависимости от состояния интерфейса Возвращает: Массив InterfaceItemState со списком контролов и их поведением или null в случае его отсутствия | 

#### `CADLib.ListSelectDialog`1`
**Назначение:** Общий диалог для выбора одного или нескольких элементов из списка


#### `CADLib.CADLibrary.CLinkedObjectsNode`
**Назначение:** Класс кастомного объекта для узла "Связи" в дереве объектов При раскрытии объект данного класса показывает связанные объекты заданного типа

| Член | Тип | Описание |
|---|---|---|
| `Need3DFocus` | метод | Блокирует фокус на 3D |

#### `CADLib.PropertyOrderPair`
**Назначение:** Пара имя/номер п/п с сортировкой по номеру

| Член | Тип | Описание |
|---|---|---|
| `CompareTo(System.Object)` | метод | Собственно метод сравнения |

#### `Aga.Controls.Tree.TreeVie<wbr>wAdv.CustomToolTipForNode`
**Назначение:** Обработка сложных тултипов. Вызывается перед применением тултипа.


#### `CADLib.CADLibrary.IRelationTypeIconProvider`
**Назначение:** Интерфейс, позволяющий плагину выдавать кастомное икноки для своих типов связи Это необходимо, т.к. в библиотеке поддерживается только bmp формат иконок


#### `CADLib.CADLibrary.LibExceptionWrapper`
**Назначение:** Класс исключения, выбрасываемого из ReportError при активном режиме ThrowExceptions


#### `CADLib.CADLibrary.ParamEditMode`
**Назначение:** Для принудительной смены режима редактирования Readonly или EnableEdit - устанавливает соответствующий признак, Ignore - оставляет, как было


#### `CADLib.EnumTypeConverter`1`
**Назначение:** TypeConverter для Enum, преобразовывающий Enum к строке с учетом атрибута Description


#### `CADLib.FilterablePropertyBase`
**Назначение:** Базовый класс для объектов, поддерживающих динамическое отображение свойств в PropertyGrid


#### `CADLib.IDatabaseBrowser`
**Назначение:** Интерфейс, главного плагина, создающего окно Интерфес содержит методы типа GetCurrentSelection


#### `CADLib.LibFolderState`
**Назначение:** Что выбрано в дереве каталогов Конвертирует значение, возвращаемое CADLib.DbSettingsItem.GetSelStatus() Для МиА следующие значения: Текущий вид: Special Выбранные объекты: Special Все объекты: System Все документы: System Каталог (выборка): Folder Миникаталог (куда просто можно помещать объекты): Directory Классификатор (имя классификатора, где показываются все объекты): ClassifierRoot Ветвь классификатора (где отфильтрованные объекты): Classifier Виды: Special Вид из видов: Directory Заметки: Special Результаты поиска (Редактирование - Поиск): Search


#### `CADLib.PropertyOrderAttribute`
**Назначение:** Атрибут для задания сортировки


#### `CADLibControls.Data.DataExchangeDataSet`
**Назначение:** Represents a strongly typed in-memory cache of data.


#### `CADLibControls.Data.DataE<wbr>xchangeDataSet.DataExchan<wbr>geTableDataTable`
**Назначение:** Represents the strongly named DataTable class.


#### `CADLibControls.Data.DataE<wbr>xchangeDataSet.DataExchan<wbr>geTableRow`
**Назначение:** Represents strongly named DataRow class.


#### `CADLibControls.Data.DataE<wbr>xchangeDataSet.DataExchan<wbr>geTableRowChangeEvent`
**Назначение:** Row event argument class


#### `CADLibControls.Data.ObjectCopyReportDataSet`
**Назначение:** Represents a strongly typed in-memory cache of data.


#### `CADLibControls.Data.Objec<wbr>tCopyReportDataSet.Object<wbr>CopyReportDataTableDataTa<wbr>ble`
**Назначение:** Represents the strongly named DataTable class.


#### `CADLibControls.Data.Objec<wbr>tCopyReportDataSet.Object<wbr>CopyReportDataTableRow`
**Назначение:** Represents strongly named DataRow class.


#### `CADLibControls.Data.Objec<wbr>tCopyReportDataSet.Object<wbr>CopyReportDataTableRowCha<wbr>ngeEvent`
**Назначение:** Row event argument class


#### `CADLibControls.EmoticonMenuItem`
**Назначение:** Summary description for EmoticonMenuItem.


#### `ObjectTemplates.ObjectTemplate`
**Назначение:** Шаблон проверки объектов


#### `WizardFormLib.WizardFormException`
**Назначение:** This class exists to satisfy FXCop rules about not manually instantiating System.Exceptions in code


#### `CADLib.CADLibrary`
**Назначение:** Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.

| Член | Тип | Описание |
|---|---|---|
| `ExpandClassifier(CADLibKernel.CLibCla...` | метод | Раскрывает классификатор, извлекая подчинённые узлы (см. дерево каталогов - классификаторы) Параметры: parentClassifier — Родительский классификатор; bIncludeNulls — Включать узлы, не имеющие объектов Возвращает: Список подчинённых узлов родительского классификатора | 
| `CreateFolderObject(CADLibKernel.CLibC...` | метод | Создаёт информацию о папке с использованием плагинов Параметры: nID — Идентификатор каталога в БД; strName — Имя папки; strFilter — Фильтр папки; dir — Идентификатор миникаталога БД ([Directories]), если это миникаталог (иначе 0); flags — Флаги папки (столбец в БД) Возвращает: элемент дерева каталогов-категорий | 
| `doShowClassifiers(System.Func{System....` | метод | Раскрывает классификатор в дерево в коллекцию treeNodes Параметры: query — Запрос из таблицы классификаторов уже с фильтром по родительскому каталогу; bIsFile — Создаются ли классификаторы файлов; tree — Дерево - владелец узлов; treeNode — Узел для добавления классификаторов; parentFolder — Родительский каталог для информации плагинам; bCollapsed — Если да, то в каждый новый узел добавится фиктивный пустой узел | 
| `GetRelationTypeIcon(CADLibKernel.CADL...` | метод | Возвращает картинку для типа связи, предоставленную подключенным плагином Это необходимо, т.к. в библиотеке поддерживается только bmp формат иконок Параметры: relationType — тип связи Возвращает: Иконка (кастомная из библиотеки или по умолчанию) | 
| `FolderPlugins` | свойство | Возвращает коллекцию плагинов каталогов |
| `RegisterFolderPlugin(CADLibControls.F...` | метод | Регистрация плагинов для работы с папками-категориями для работы плагин должен быть унаследован от FolderPlugin Плагин также может реализовывать IRelationTypeIconProvider Параметры: | 
| `RemoveFolderPlugin(CADLibControls.FolderPlugin)` | метод | разрегистрация плагина для работы с папками-категориями Параметры:  |
| `ReportObjectPicked(CADLibKernel.CLibO...` | метод | Вызывается при двойном клики по объекту в 3д - позволяет плагинам обработать клик и запретить форме менять папку Параметры: libObject — Объект по которуму ткнули; strStructGroup — Группа данных структурнуго объекта или null если не структурный; bSupressSelectionFolderHighlighting — Устанавливается в Да, если необходимо запретить выделать папку "выбранные объекты" | 
| `GetStructureObjectGroup(CADLibKernel....` | метод | Получение группы объекта структурных данных Параметры: nObjectId — Идентификатор объекта из категории структурных данных Возвращает: Группа данных (значение параметра SYS_CATEGORY_GROUP) или null | 
| `GetLibraryCustomObject(System.Int32)` | метод | Получение кастомного объекта библиотеки по идентификатору Кастомные объекты создаются плагинами В случае, если этот объект не является объектом плагинов - возвращается обычный CLibObjectInfo Параметры: nId — Идентификатор запрашиваемого объекта Возвращает: Кастомный объект или обычный объект или null (если не найден) или исключение | 
| `GetLibraryCustomObject(CADLibKernel.C...` | метод | Получение кастомного объекта библиотеки по CLibObjectInfo Кастомные объекты создаются плагинами В случае, если этот объект не является объектом плагинов - возвращается обычный CLibObjectInfo Параметры: nId — Идентификатор запрашиваемого объекта Возвращает: Кастомный объект или обычный объект или null (если не найден) или исключение | 
| `AddRootFiltersToFilter(System.String)` | метод | Добавляет корневые фильтры к строке фильтрации вида , Parameters_STR PT0 where (PT0.idObject = O.idObject) AND (PT0.idParamDef = 1) AND (PT0.Value='Координатные сетки') Параметры: strFilter — Исходный фильтр Возвращает: Исходный фильтр + корневые фильтры + Фильтр на ИСКЛЮЧЕНИЕ ИЗ ВЫБОРКИ структурных объектов, если в исходном фильтре не указано обратного | 
| `AddStructureObjectsExclude(System.Str...` | метод | Добавляет фильтр на исключение из выборки структурных объектов, если в исходном фильтре не указано обратного Параметры: strBaseQuery — Исходный фильтр с where или без Возвращает: Изменённый фильтр | 
| `Rootfilters` | свойство | Возвращает примененные корневые фильтры библиотеки |
| `SetRootFilters(System.Collections.Gen...` | метод | Устанавливает набор корневых фильтров библиотеки, которые будут применены дополнительно к результатам методов ShowFolders и doShowClassifiers, DoCreateClassifier и везде, где используется AddRootFiltersToFilter Параметры: | 
| `GetSimpleParamDefs(System.Boolean,Sys...` | метод | Возвращает определения параметров в простом виде из видимых категорий Определение содержит имя, заголовок, идентификатор и список категорий Параметры: bSysParams — Включать ли в выборку системные параметры (включая имя); bSysName — Включать ли в выборку системный параметр имя (только имя, если bSysParams==false); bHideUnused — Не включать в выборку неиспользуемые параметры; bExtendedOnly — Включать только параметры из расширенных таблиц; bIndependentOnly — Включать только независемые параметры; bFileSysParams — Возвращать параметры файлов; bReadCategories — Возвращать категории (если нет, то ускоряется чтение, а списки категорий будут установлены в null) | 
| `UpdatePreviewFile(CADLibKernel.CLibFi...` | метод | Retrieves file graphics and try to load it to the preview PictureBox. If file format is not graphical shows file category icon from largeImages ImageList Written by Zapevalov. Параметры: file — File to retrieve data from; preview — PictureBox to load to; largeImages — ImageList with catigories icons | 
| `GetFileAssociatedIcon(System.String,S...` | метод | Retrieve windows Registered File Associated Icon Параметры: strFileTypeCaption — Type extension like "DWG"; cloneIcon — The callback that receives associated icon. The callback must clone the icon because it will be destroyed when the method returns. | 
| `ShowObjectsTree(System.Windows.Forms....` | метод | Заполняет дерево объектами из указанного каталога Параметры: bSelect — Выделяет галочками добавленные узлы-объекты; tvFolders — Если не NULL то хранит папки | 
| `UpdateCategory(CADLibKernel.CLibCateg...` | метод | Обновляет информацию о категории, либо создаёт новую Необходимые определения параметров должны быть созданы заранее, либо параметры не добавятся При добавлении обновляется поле idCategory Параметры: category — Категория для создания/обновления; guiControl — Элемент управления основного потока для создания иконок из рабочего потока. При вызове из основного потока может быть null | 
| `UploadIcons(System.Drawing.Image,Syst...` | метод | Добавляет иконки в базу данных Если ImageList используется в элементах управления, то метод должен запускаться в потоке, владеющим ими Параметры: ico16 — Объект маленькой иконки; ico32 — Объект большой икноки; strName — Имя иконки Возвращает: Идентификатор новой иконки, либо Exception | 
| `UpdateObjectParameterValuesAndComment...` | метод | UpdateObjectParameterValuesAndComments: метод является центральным механизмом обновления параметров объектов и все таковые обновления (кроме добавления/удаления параметров) должгы выполнятся через этот метод. Помимо параметров, указанных в аргументе newData, метод может изменить и другие параметры, а именно параметры-формулы, если таковые имеются у указанного объекта(-ов). При этом параметры-формулы могут быть изменены у объектов поимио указанных в аргументе objects, а именно у объектов, входящих в иерархию(-и) указанного объекта(-ов). То есть: для всех объектов, входящих в иерархию, пересчитываются все параметры-формулы, зависящие прямо или косвенно от указаных в аргументе newData параметров. Параметры: objects — Множество объектов, параметры которых изменились; newData — Новые значения, которые необходимо присвоить параметрам всех объектов из множества objects | 
| `ShowFileParameters(System.Windows.For...` | метод | Retrieves file parameters into ListView. Written by Zapevalov. Параметры: props — ListView to retrieve info to; file — File to retrieve params from | 
| `m_nThrowExceptions` | поле | Если значение больше нуля, то вместо показа диалога с ошибкой будут выданы исключения |
| `PushThrowExceptions` | метод | Включает режим, при котором вместо показа диалога с ошибкой будут выданы исключения обёрнутые в LibExceptionWrapper |
| `PopThrowExceptions` | метод | Отключает режим, при котором вместо показа диалога с ошибкой будут выданы исключения |
| `ReportError(System.Exception)` | метод | Логирует ошибку Параметры: e — Исключение |
| `ReportError(System.String)` | метод | Обработка ошибок. Если нет окна прогресса - показывает MessageBox с текстом ошибки Параметры: msg — Текст ошибки |
| `GetUserGroupBySysName(System.String)` | метод | Поиск группы пользователей по системному имени Параметры: strSysName — Системное имя группы ("ALL" - стандартная группа "Все пользователи") Возвращает: id группы или 0, если такой нет | 
| `ShowDependencies(System.Windows.Forms.TreeView)` | метод | Заполняет дерево для формы Настройка зависимостей параметров Параметры:  |
| `ShowDependentParameters(System.Windows.Forms.TreeNode)` | метод | Заполняет указанный узел дерева для формы Настройка зависимостей параметров Параметры:  |
| `FillClassifierObjectsTree(System.Wind...` | метод | Заполняет дерево объектами-ссылками - вложенными в классификатор Параметры: tvObjects — Дерево для добавления объектов; classifierRoot — Классификатор, который будет раскрыт; destBrowser — Контрол для смены каталога в случае двойного клика по объекту | 

#### `WizardFormLib.WizardFormBase`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GraphicPanelBackgroundColor` | свойство | Get/set the graphic panel background color |
| `GraphicPanelGradientColor` | свойство | Get/set the graphic panel gradient color |
| `GraphicPanelImage` | свойство | Get/set the image used on the graphic panel |
| `GraphicPanelImagePosition` | свойство | Set the position of the image. If middle or center, title and subtitle text will be ignored. |
| `GraphicPanelImageIsTransparent` | свойство | Image has a transparent background - affects the way the gradient is painted |
| `GraphicPanelTitleFont` | свойство | Get/set the font used for the title string in the graphic panel |
| `GraphicPanelSubtitleFont` | свойство | Get/set the font used for the subtitle string in the graphic panel |
| `GraphicPanelTitleColor` | свойство | Get/set title color |
| `GraphicPanelSubtitleColor` | свойство | Get/set subtitle color |
| `StartPage` | свойство | Get the start page for this wizard form |
| `StopPage` | свойство | Get set stop page for this wizard form |
| `PageCount` | свойство | Get the number of pages that have been added to this wizard form |
| `ButtonStartHide` | свойство | Get/set the value that represents the show/hide state of the Back button |
| `ButtonBackHide` | свойство | Get/set the value that represents the show/hide state of the Back button |
| `ButtonNextHide` | свойство | Get/set the value that represents the show/hide state of the Next button |
| `ButtonCancelHide` | свойство | Get/set the value that represents the show/hide state of the Cancel button |
| `ButtonHelpHide` | свойство | Get/set the value that represents the show/hide state of the Help button |
| `#ctor` | метод | Constructor |
| `Raise_WizardPageChangeEvent(WizardFormLib.WizardPageChangeArgs)` | метод | Fires the WizardPageCreatedEvent event. Параметры:  |
| `Raise_WizardFormStartedEvent(WizardFormLib.WizardFormStartedArgs)` | метод | Fires the WizardFormStartedEvent event. Параметры:  |
| `graphicPanelTop_Paint(System.Object,S...` | метод | Fired when the graphic panel is painted 0- this should only happen the first time the wizard form is shown. Параметры: | 
| `PaintTitle` | метод | Paint the title and subtitle text. This should happen whenever the current page is changed. Параметры:  |
| `PageCreated(WizardFormLib.WizardPage)` | метод | This method allows this object to add the wizard page to the pagePanel container. While we're here, we establish the start and stop page if possible. Параметры: | 
| `DiscoverPagePanelSize(System.Drawing....` | метод | Called by the wizard page when it's created to allow this object to resize itself. The desired panel size is increased on whatever axis is larger than the current value. Параметры: | 
| `StartWizard` | метод | Seeds the page chain, resizes the form to be large enough to contain the desired size of the pagePanel container, and finally, shows the start page. |
| `PageIsVisible(WizardFormLib.WizardBut...` | метод | Determines if the specified state has the Visible flag turned on Параметры: state — The state to be checked Возвращает: True if the Visible flag is turned on | 
| `PageIsEnabled(WizardFormLib.WizardBut...` | метод | Determines if the specified state has the Enabled flag turned on Параметры: state — The state to be checked Возвращает: True if the Enabled flag is turned on | 
| `UpdateWizardForm(WizardFormLib.Wizard...` | метод | Updates the state of the buttons on the form base on the specified page settings. Параметры: page — The page controlling the button state | 

#### `WizardFormLib.WizardPage`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `Title` | свойство | Get/set the title text displayed in the graphic panel |
| `Subtitle` | свойство | Get/set the sub-title text displayed in the graphic panel |
| `WizardPageType` | свойство | Get/set the title page type (start, intermediate, or stop) |
| `ParentWizardForm` | свойство | Get/set the parent wizard form |
| `ButtonStateStart` | свойство | The button state (visible/enabled) for the Back button |
| `ButtonStateBack` | свойство | The button state (visible/enabled) for the Back button |
| `ButtonStateNext` | свойство | The button state (visible/enabled) for the Next button |
| `ButtonStateCancel` | свойство | The button state (visible/enabled) for the Cancel button |
| `ButtonStateHelp` | свойство | The button state (visible/enabled) for the Help button |
| `NextPages` | свойство | Get the list of "next" pages |
| `#ctor(WizardFormLib.WizardFormBase)` | метод | Default constructor - creates an Intermediate wizard page. To create a start or stop page, use the overloaded constructor |
| `#ctor(WizardFormLib.WizardFormBase,Wi...` | метод | Creates a wizard page of the specified type. You can optionally call the other constructor if you're adding anintermediate page. Параметры: parent — The parent wizard form; pageType — The type of page being created (see WizardPageType enum) | 
| `Init(WizardFormLib.WizardFormBase,WizardFormLib.WizardPageType)` | метод | This is a common initialization function called by all of the constructors. Параметры:  |
| `AddNextPage(WizardFormLib.WizardPage)` | метод | Adds a "next page" item to the list of possible next pages. The derived Wizard page can then decide on its own which page is next based on the values of one/more controls in the derived page. Параметры: nextPage — The page to add as a possible "next" page | 
| `Raise_WizardPageActivated(WizardFormLib.WizardPageActivateArgs)` | метод | Allows the derived Wizard form to raise the WizardPageActivated event. Параметры:  |
| `SaveData` | метод | Base method used to save data for all visited wizard pages. This copy of the method always returns true. Возвращает: True if the data was succesfully saved |
| `GetNextPage` | метод | Get the next page to be shown. This is virtual so that you can override it in order to provide a programmatically determined "next" page. Возвращает: The page that will be displayed next | 
| `parentForm_WizardPageChange(System.Ob...` | метод | Allows the base class to handle a page change event. Right now, there's nothing to do, but you could add some apppropriate functionalty that suits your application. Параметры: | 
| `WizardPage_VisibleChanged(System.Object,System.EventArgs)` | метод | Fired when a page is made visible. Параметры:  |

#### `CADLibControls.Controls.ParametersSelectTree`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `Parameters` | свойство | Список параметров для отображения элементом |
| `SelectedParameter` | свойство | Выделенный параметр (на котором подсветка) |
| `CurrentCategory` | свойство | Текущая категория - либо выделенная подсветкой, либо та, к котороый относится текущий выделенный параметр |
| `GetSelectedParameter``1` | метод | Привязанный пользовательский объект выделенного параметра с приведением типа Возвращает: Приведённый тэг выделенного объекта или null |
| `ShowCheckBoxes` | свойство | Показывать или нет галочки справа от параметров При изменении во время показа необходима перерисовка |
| `ShowCategories` | свойство | Показывать параметры по категориям либо в алфавитном порядке |
| `ShowParametersCaption` | свойство | Показывать заголовки параметров или системные имена |
| `CheckStateChanged` | событие | Происходит при изменении галочек, изменившиеся параметры не передаются |
| `SelectionChanged` | событие | Происходит при изменении выделенного параметра |

#### `Aga.Controls.Tree.TreeViewAdv`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `ExpandedNodes` | свойство | returns all nodes, which parent is expanded |
| `PageRowCount` | свойство | Number of rows fits to the screen |
| `RowCount` | свойство | Number of all visible nodes (which parent is expanded) |
| `EnsureVisible(Aga.Controls.Tree.TreeNodeAdv)` | метод | Expand all parent nodes, andd scroll to the specified node |
| `ScrollTo(Aga.Controls.Tree.TreeNodeAdv)` | метод | Make node visible, scroll if needed. All parent nodes of the specified node must be expanded Параметры:  |
| `CustomToolTip` | свойство | Позволяет указать функцию обработки сложных тултипов |
| `BoldFont` | свойство | Возвращает шрифт данного элемента управления с установленным флагом "жирный" |
| `SetRowFontPredicate(System.Func{Aga.C...` | метод | Позволяет задать колбэк для указания шрифта каждой строки дерева Параметры: objectToFont — Функция, преобразующая узел дерева в шрифт | 
| `SetRowBackgroundColorPredicate(System...` | метод | Позволяет задать колбэк для указания кисти(цвета) фона каждой строки дерева Параметры: objectToRowColor — Функция, преобразующая узел дерева в кисть | 

#### `CADLib.DirectoryBrowserTreeBase`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SetSelectedNode(System.Windows.Forms.TreeNode)` | метод | Устанавливает выбранный узел дерева Параметры:  |
| `ShowProps(System.Windows.Forms.TreeNode)` | метод | Вызов события показа свойств объекта Параметры:  |
| `tvFolders_KeyDown(System.Object,Syste...` | метод | Обработка нажатия клавиш в дереве объектов. Нужно для навигации по дереву в помощью клавиатуры Параметры: | 
| `tvObjects_KeyDown(System.Object,Syste...` | метод | Обработка нажатия клавиш в дереве объектов. Нужно для навигации по дереву в помощью клавиатуры Параметры: | 
| `tvObjects_MouseDown(System.Object,System.Windows.Forms.MouseEventArgs)` | метод | Обработка события нужно для определения нажатия на область чекбокса Параметры:  |
| `SelectChildObjectByPath(System.Int32[])` | метод | Выделяет подчинённый объект по указанному пути Параметры: arrPathObjectsIds — Путь к объекту, начиная с корневого (idObject). Возвращает: Ссылку на выбранный объект (как хранится в дереве) или null, если не удалось произвести выбор | 

#### `CADLib.ParametersEditForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SelectedParameters` | свойство | Возвращает выделенные параметры |
| `OnSetupCategories` | метод | Настройка сортировки категорий |
| `cbValType_SelectedIndexChanged(System.Object,System.EventArgs)` | метод | Изменение типа параметра в комбобоксе Параметры:  |
| `SetTopIndexCurrentCategory(System.String)` | метод | Отобразить текущую категорию первой в списке категорий Параметры:  |

#### `CADLib.TreeViewNodeSelector`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

| Член | Тип | Описание |
|---|---|---|
| `IsSingle` | свойство | Выделен только один узел |
| `Nodes` | свойство | Выделенные узлы |
| `IsEmpty` | свойство | True если нет выделенных узлов |
| `Clear` | метод | Очистка списка выделения |
| `Contains(System.Windows.Forms.TreeNode)` | метод | Определяет содержится ли узел в выделенных Параметры:  Возвращает: True если узел выделен |
| `Begin(System.Windows.Forms.TreeNode,S...` | метод | Начало множественного выделения Параметры: treeNode — Узел, с которого начинается выделение; keys — Нажатые клавиши (Shift, Ctrl, ...); button — Нажатая кнопка мыши Возвращает: False если узел был выбран повторно и удалён из выделенных | 
| `End(System.Windows.Forms.TreeNode,Sys...` | метод | Завершение множественного выделения Параметры: treeNode — Последний узел в выделении; keys — Нажатые клавиши (Shift, Ctrl, ...) | 

#### `CADLib.DirectoryBrowserCtrl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `RefreshCurrentCatalog(System.Boolean,...` | метод | Обновляет каталог объектов в окне БД Параметры: bKeepSelection — Запоминать выбранные объекты; bKeepPage — Запоминать страницу на которой находились; bShowAll — Показывать все объекты; bResetView — ХЗ; bSelectContents — Выделять галочками все объекты | 
| `SelectChildObjectByPath(System.Int32[])` | метод | Выделяет подчинённый объект по указанному пути Параметры: arrPathObjectsIds — Путь к объекту, начиная с корневого (idObject). Возвращает: Ссылку на выбранный объект (как хранится в дереве) или null, если не удалось произвести выбор | 
| `ObjectSelected` | событие | Собтыие происходит при смене выбранного объекта. Возвращаемое значение не используется. |

#### `CADLibControls.CSStackPanelItem`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `Text` | свойство | Текст элемента |
| `Icon` | свойство | Иконка элемента |
| `CloseButtonClick` | событие | Событие нажатия на крестик |

#### `CADLibControls.Controls.FunctionEditCtl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `populateListBox(System.String)` | метод | Called when a "." is pressed - the previous word is found, and if matched in the treeview, the members listbox is populated with items from the tree, which are first sorted. Возвращает: Whether an items are found for the word | 
| `getLastWord(System.Boolean)` | метод | Searches backwards from the current caret position, until a space or newline is found. Возвращает: The previous word from the carret position | 
| `selectItem` | метод | Autofills the selected item in the member listbox, by taking everything before and after the "." in the richtextbox, and appending the word in the middle. | 

#### `ObjectTemplates.ObjectTemplateListForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `tbTemplateCreate_Click(System.Object,System.EventArgs)` | метод | Создать новый шаблон Параметры:  |
| `tbTemplateAdd_Click(System.Object,System.EventArgs)` | метод | Добавить дочерний шаблон Параметры:  |
| `AddTemplateParameters(CADLibKernel.CL...` | метод | Добавить к объекту все параметры из шаблона Параметры: | 

#### `CADLib.AddParamsDlgBase`
**Назначение:** Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями.

| Член | Тип | Описание |
|---|---|---|
| `SelectedParameters` | свойство | Возвращает выделенные параметры |
| `UpdateTreeParameters` | метод | Данный метод необходимо переопределить так, чтобы здесь присваивались параметры дереву |

#### `CADLib.CSSettingsBase`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

| Член | Тип | Описание |
|---|---|---|
| `GetFileName` | метод | Имя файла для настроек (например settings.xml), если не задано, то настройки не сохраняются |
| `GetName` | метод | Имя настроек для их идентификации |
| `GetTreePath` | метод | Путь в дуреве настроек в диалоге настроек, если не задан - настройки не добавляются в диалог Узлы дерева в пути разделены символом \| |
| `HasSaveImplementation` | свойство | Возвращает, да, если для класса реализованы собственные методы SaveSettings и LoadSettings В противном случае будет использован стандартный механизм сохранения и загрузки | 
| `ParentGrid` | свойство | Таблица свойств, которая показывает данные настройки должна установить это поле перед показом необходимо для возможности вызова модальных диалогов из настроек | 

#### `CADLib.DirectoryBrowserClient`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `VisibleItemsUpdated` | событие | Событие обновления дерева объектов |
| `SelectChildObjectByPath(System.Int32[])` | метод | Выделяет подчинённый объект по указанному пути Параметры: arrPathObjectsIds — Путь к объекту, начиная с корневого (idObject). Возвращает: Ссылку на выбранный объект (как хранится в дереве) или null, если не удалось произвести выбор | 

#### `CADLib.FoldersBrowser`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GetFolderByPath(System.String)` | метод | Пытается загрузить каталог по указанному пути в дереве Работает также как RestoreFoldersPath, но не меняет выделенный узел и статус свёрнутости узлов Параметры: foldersText — Путь, полученный с помощью GetFoldersPathString() (разделител "\ | \ | \ | ") Возвращает: Каталог БД или null, в случае неудачного поиска. Если целиком путь восстановить не удаётся, то будет возвращена существующая часть пути. | 
| `GetNodeByPath(System.String,System.Bo...` | метод | Пытается загрузить каталог по указанному пути в дереве Работает также как RestoreFoldersPath, но не меняет выделенный узел и статус свёрнутости узлов Параметры: foldersText — Путь, полученный с помощью GetFoldersPathString() (разделител "\ | \ | \ | ") Возвращает: Каталог или null, в случае неудачного поиска. bFindFullPath - флаг поиска полного соответствия пути если путь целиком не существует, true - если путь целиком не существует возвращенно будет null false - Если целиком путь восстановить не удаётся, то будет возвращена существующая часть пути. | 

#### `CADLib.Dialogs.MultiuserForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `ResizeImage(System.Drawing.Image,Syst...` | метод | Resize the image to the specified width and height. Параметры: image — The image to resize.; width — The width to resize to.; height — The height to resize to. Возвращает: The resized image. | 

#### `CADLib.ObjectPropertiesDlg`
**Назначение:** Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура.

| Член | Тип | Описание |
|---|---|---|
| `BlockButtons(System.Boolean)` | метод | Заблокировать часть кнопок редактирования параметров. Необходимо при отображении списка Параметров проекта Параметры:  |

#### `CADLib.ObjectViewerForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `ShowObjectProperties(CADLibKernel.CLi...` | метод | Показывает свойства объекта и переводит элемент управления свойств в режим одиночного показа Параметры: activeObject — Объект для показа; forceShow — Принудительно показать окно общих свойств Возвращает: Да, если что-то поменялось | 

#### `CADLib.ParametersDialog`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(System.String)` | метод | Конструктор диалога Параметры: strParamToHighlight — Есди задан, то при открытии диалога будет выбран параметр с этим именем |

#### `CADLibControls.Forms.TaskProgressBarForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(System.Int32)` | метод | Позволяет визуализировать ход выполнения чего-либо Параметры: TaskCount — Максимальное кол-во чего-либо |
| `components` | поле | Обязательная переменная конструктора. |
| `Dispose(System.Boolean)` | метод | Освободить все используемые ресурсы. Параметры: disposing — истинно, если управляемый ресурс должен быть удален; иначе ложно. |
| `InitializeComponent` | метод | Требуемый метод для поддержки конструктора — не изменяйте содержимое этого метода с помощью редактора кода. |

#### `CADLibControls.Transliteration`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `Front(System.String)` | метод | Транслитирует строку русских символов (по умолчанию стандарт ISO) Параметры: text — Строка с русским текстом |
| `Front(System.String,CADLibControls.Tr...` | метод | Транслитирует строку русских символов (по умолчанию стандарт ISO) Параметры: text — Строка с русским текстом; type — Вариант ГОСТа | 
| `Back(System.String)` | метод | Транслитирует строку обратно в русский текст (по умолчанию стандарт ISO) Параметры: text — Транслитируемая строка |
| `Back(System.String,CADLibControls.Tra...` | метод | Транслитирует строку обратно в русский текст (по умолчанию стандарт ISO) Параметры: text — Транслитируемая строка; type — Вариант ГОСТа | 

#### `ObjectTemplates.CheckTemplateForm`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SelectItem(System.Windows.Forms.TreeNode)` | метод | Выделить указанный объект в главном дереве объектов Параметры:  |

#### `CADLib.CADLibrary.eExceptionMode`
**Назначение:** Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта.

| Член | Тип | Описание |
|---|---|---|
| `Free` | поле | Exception can be reported using default mechanism |
| `NonInteractiveSkip` | поле | Reporter should not show modal dialogs |
| `NonInteractiveThrow` | поле | Reporter should not show modal dialogs, but rethrows exceptions |

#### `Aga.Controls.Tree.NodeCon<wbr>trols.BaseTextControl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `BackgroundCirclePen` | свойство | Позволяет рисовать фоновый скруглённый прямоугольник на фоне поля Если задано, то он рисуется и обводится указанной кистью |
| `BackgroundCircleBrush` | свойство | Позволяет рисовать фоновый скруглённый прямоугольник на фоне поля Если задано, то он рисуется и закрашивается указанной кистью |

#### `CADLib.CSFileEditor`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

#### `CADLib.CSFolderEditor`
**Назначение:** Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура.

#### `CADLib.Dialogs.CadLibDockWindowBase`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(System.Windows.Forms.Form,Syste...` | метод | Cad lib dock window base constructor This window automatically docks in Panel2 of the given DockSplitContainer Параметры: MainForm — can be null before first FhowForm; DockSplitContainer — can be null before first FhowForm | 
| `#ctor` | метод | Default constructor FOR DISIGNER ONLY |

#### `CADLib.PdfFileEditor`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

#### `NExtensions.DrawingExtensions`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

| Член | Тип | Описание |
|---|---|---|
| `MakeMonochrome(System.String)` | метод | Creates a monochrome version of an image Параметры: sourceImageFile — The path to the image to convert to monochrome. The source image is not altered in any way. Возвращает: The monochrome image | 
| `MakeMonochrome(System.Drawing.Image)` | метод | Creates a monochrome version of an image Параметры: source — The image to convert to monochrome. The source image is not altered in any way. Возвращает: The monochrome image | 

#### `ObjectTemplates.ObjectTemplateManager`
**Назначение:** Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура.

| Член | Тип | Описание |
|---|---|---|
| `CheckTemplateObject(CADLibKernel.CLibObjectInfo,System.Collections.Generic.List{CADLibKernel.CLibObjectInfo})` | метод | Pfuhep Параметры:  |
| `CheckObject(CADLibKernel.CLibObjectIn...` | метод | Основной метод проверки объекта Выполняет последовательную проверку условий указанного шаблона Параметры: | 

#### `Aga.Controls.Tree.InputState`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `MouseMove(System.Windows.Forms.MouseEventArgs)` | метод | handle OnMouseMove event Параметры:  Возвращает: true if event was handled and should be dispatched |

#### `Aga.Controls.Tree.NodeCon<wbr>trols.BindableControl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SetValuePredicate(System.Func{Aga.Con...` | метод | Позволяет задать колбэк для получения значения поля объекта по узлу дерева Если она задана, то она используется вместо получения значения по имени поля (DataPropertyName) Параметры: getValuePredicate — Функция, преобразующая узел дерева в значение для данного NodeControl | 

#### `Aga.Controls.Tree.NodeCon<wbr>trols.EditableControl`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `SetReadOnlyCallback(System.Func{Aga.C...` | метод | Позволяет задать колбэк для получения значения поля объекта по узлу дерева Если она задана, то она используется вместо получения значения по имени поля (DataPropertyName) Параметры: readOnlyCallback — Функция, преобразующая узел дерева в значение для данного NodeControl | 

#### `CADLib.CSSettings`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

| Член | Тип | Описание |
|---|---|---|
| `ApplicationFolderName` | свойство | Имя каталога приложения в AppData - необходимо установить в первую очередь |

#### `CADLib.DbSettingsItem`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

| Член | Тип | Описание |
|---|---|---|
| `GetSelStatus` | метод | Тип данного каталога Для DbSettingsItemType.itSpecialFolder: Special Для DbSettingsItemType.itFolder или DbSettingsItemType.itFileFolder смотрит тип каталога (Folder): в МиА следующие значения: Текущий вид: Special Выбранные объекты: Special Все объекты: System Все файлы: System Каталог (выборка): Folder Миникаталог (куда просто можно помещать объекты): Directory Классификатор (имя классификатора, где показываются все объекты): ClassifierRoot Ветвь классификатора (где отфильтрованные объекты): Classifier Виды: Special Вид из видов: Directory Заметки: Special Результаты поиска (Редактирование - Поиск): Search Для остальных типов возвращает LibFolderState.System | 

#### `CADLib.EnumTypeConverter`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

| Член | Тип | Описание |
|---|---|---|
| `#ctor(System.Type)` | метод | Инициализирует экземпляр Параметры: type — тип Enum |

#### `CADLib.Forms.CadLibMainForm.DockFormInfo`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `InitPosition` | поле | Will be invoked in case of DockStyle is DockStyle.None |

#### `CADLib.PropertySorter`
**Назначение:** Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL.

| Член | Тип | Описание |
|---|---|---|
| `GetProperties(System.ComponentModel.ITypeDescriptorContext,System.Object,System.Attribute[])` | метод | Возвращает упорядоченный список свойств |

#### `CADLibControls.Controls.P<wbr>arametersSelectTree.Param<wbr>eter`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `Tag` | свойство | Привязанный пользовательский объект |

#### `CADLibControls.Forms.THUMBBUTTON`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `THBN_CLICKED` | поле | WPARAM value for a THUMBBUTTON being clicked. |

#### `CADLibControls.GdiNativeMethods`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `GdipEmfToWmfBits(System.IntPtr,System...` | метод | Use the EmfToWmfBits function in the GDI+ specification to convert a Enhanced Metafile to a Windows Metafile Параметры: _hEmf — A handle to the Enhanced Metafile to be converted; _bufferSize — The size of the buffer used to store the Windows Metafile bits returned; _buffer — An array of bytes used to hold the Windows Metafile bits returned; _mappingMode — The mapping mode of the image. This control uses MM_ANISOTROPIC.; _flags — Flags used to specify the format of the Windows Metafile returned | 

#### `WizardFormLib.WizardUtility`
**Назначение:** UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса.

| Член | Тип | Описание |
|---|---|---|
| `IsDesignTime` | метод | Determines if the programmer is using the designer to modify this control (or controls derived from this class). Возвращает: True if the designer is displaying this control | 

## 7. DLL без XML: `CADLibKernel` и `CSAppServices`

Здесь перечислены публичные типы и наиболее заметные методы. Описания восстановлены по именам типов/методов и по связям с примерами PythonPlugin; их нужно проверять на тестовой БД CADLib.

### `CADLibKernel` — типы по функциональным зонам

#### 3D-графика / mesh

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `ModelStudio.Graphics3D.CSMesh` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 71 |
| `ModelStudio.Graphics3D.CSVectorD3` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 50 |
| `ModelStudio.Graphics3D.CSVector3` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 43 |
| `ModelStudio.Graphics3D.CSMatrixD` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 40 |
| `ModelStudio.Graphics3D.CSVertexCompressed` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 17 |
| `ModelStudio.Graphics3D.CSBox` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 37 |
| `ModelStudio.Graphics3D.CSExtents` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 29 |
| `ModelStudio.Graphics3D.MeshProcessor` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 15 |
| `ModelStudio.Graphics3D.CSMaterial` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 18 |
| `ModelStudio.Graphics3D.CSCurves` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 19 |
| `ModelStudio.Graphics3D.CSCurve` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 15 |
| `ModelStudio.Graphics3D.CSPolyline` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 15 |
| `ModelStudio.Graphics3D.CSCylinder` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 17 |
| `ModelStudio.Graphics3D.CSShapeInfo` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 17 |
| `ModelStudio.Graphics3D.CSCircle` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 17 |
| `ModelStudio.Graphics3D.CSCircleArc` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 18 |
| `ModelStudio.Graphics3D.CS<wbr>AttributeTableRecord` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 9 |
| `ModelStudio.Graphics3D.CC<wbr>SRealFloatExtensions` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 5 |
| `CSVertexIndex` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 |
| `CS3DHeader14` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 19 |
| `CS3DHeader15` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 15 |
| `CS3DHeader20` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 18 |
| `CADLibKernel.MeshInfoEx` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 5 |
| `CADLibKernel.ShapeInfoEx` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 23 |

#### DBBrowser / UI

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.eUserNameFormat` | UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса. | 3 |
| `CADLibKernel.DataExchange<wbr>Unit.DEvaluateFormula` | UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса. | 4 |

#### Library / ядро БД

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.CADLibraryBase` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 1094 |
| `CADLibKernel.ObjectUpdate.GetConnecti...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryO...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetConnecti...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryO...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryD...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryO...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryO...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryD...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryO...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 
| `CADLibKernel.ObjectUpdate.GetLibraryO...` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 4 | 

#### Коллизии / замечания

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CollisionEngine.ICollisionCalcStarter` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 6 |

#### Объекты

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.ObjectUpdate<wbr>.ObjectUpdateService` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 1446 |
| `CADLibKernel.ObjectUpdate.ShapeInfoEx` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 89 |
| `CADLibKernel.ObjectUpdate<wbr>Router.RouterService` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 78 |
| `CADLibKernel.ObjectTreeQuery` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 89 |
| `CADLibKernel.Models.ObjectUpdate.Catalog` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 52 |
| `CADLibKernel.ObjectUpdate.ParamDef` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 45 |
| `CADLibKernel.Models.ObjectUpdate.LibObject` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 39 |
| `CADLibKernel.ObjectUpdate.CSShapeInfo` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 53 |
| `CADLibKernel.Models.ObjectUpdate.Folder` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 35 |
| `CADLibKernel.ObjectUpdate.ParamDefCategory` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 13 |
| `CADLibKernel.Models.Objec<wbr>tUpdate.SelectedObjectsFo<wbr>lder` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 22 |
| `CADLibKernel.ObjectUpdate.ParamDefVariant` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 9 |
| `CADLibKernel.ObjectUpdate.Parameter` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 21 |
| `CADLibKernel.CLibObjectInfo` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 34 |
| `CADLibKernel.ObjectUpdate.GetClassifi...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsB...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsB...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetParamDef...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetClassifi...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsB...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsB...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>.GetParamDefsXmlCompleted<wbr>EventArgs` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `CADLibKernel.ObjectUpdate.ObjectCategory` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 29 |
| `CADLibKernel.CLibCSVExportObject` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 17 |
| `CADLibKernel.ObjectUpdate.CSVectorD3` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 13 |
| `CADLibKernel.ObjectUpdate.ParameterDefault` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 13 |
| `CADLibKernel.CLibClassifier` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 34 |
| `ObjectRelationType` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 33 |
| `CADLibKernel.CLibObjectParamsMap` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 11 |
| `CADLibKernel.Models.Objec<wbr>tUpdate.SearchResults` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 22 |
| `CADLibKernel.ObjectUpdate.FileCategory` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 21 |
| `CADLibKernel.Models.ObjectUpdate.SearchRoot` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 16 |
| `CADLibKernel.ObjectUpdate<wbr>.Count3DShapesSizeComplet<wbr>edEventArgs` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 6 |
| `CADLibKernel.ObjectUpdate.ExpertiseItem` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 33 |
| `CADLibKernel.ObjectUpdate<wbr>.Get3DGraphicsArrayComple<wbr>tedEventArgs` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 6 |
| `CADLibKernel.ObjectUpdate<wbr>.Get3DGraphicsWithPtCompl<wbr>etedEventArgs` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 6 |
| `CADLibKernel.ObjectUpdate.GetObject3D...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 6 | 
| `CADLibKernel.ObjectUpdate<wbr>.Count3DShapesSizeComplet<wbr>edEventHandler` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 |
| `CADLibKernel.ObjectUpdate.DownloadDef...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>.Get3DGraphicsArrayComple<wbr>tedEventHandler` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 |
| `CADLibKernel.ObjectUpdate<wbr>.Get3DGraphicsCompletedEv<wbr>entHandler` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 |
| `CADLibKernel.ObjectUpdate<wbr>.Get3DGraphicsWithPtCompl<wbr>etedEventHandler` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 |
| `CADLibKernel.ObjectUpdate.GetFilePara...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetModelHas...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObject3D...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObject3D...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObject3D...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObject3D...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsB...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsI...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsP...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectsU...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>.GetParamDefIdCompletedEv<wbr>entHandler` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `CADLibKernel.ObjectUpdate.GetParamDef...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>.GetParamDefsCompletedEve<wbr>ntHandler` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `CADLibKernel.ObjectUpdate.GetParamVal...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetParamete...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.GetSingleOb...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| `CADLibKernel.ObjectUpdate.SetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.SetObjectPa...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate.UploadParam...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdateRouter.GetCa...` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>Router.GetRolesOfAuthenti<wbr>catedUserCompletedEventHa<wbr>ndler` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 4 |
| `CADLibKernel.IsLinkedObjectParam` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 16 |
| `CADLibKernel.Models.ObjectUpdate.Empty` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 13 |
| `CADLibKernel.Models.ObjectUpdate.Error` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 14 |
| `CADLibKernel.Models.Objec<wbr>tUpdate.FilesCollection` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 15 |
| `CADLibKernel.ObjectUpdate.DownloadDef...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>.Get3DGraphicsCompletedEv<wbr>entArgs` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 |
| `CADLibKernel.ObjectUpdate.GetFilePara...` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>.GetModelExtentsCompleted<wbr>EventArgs` | Объекты CADLib: данные объекта, иерархия, копирование, создание, удаление, связи и структура. | 14 |
| `CADLibKernel.ObjectUpdate.GetModelHas...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObject3D...` | Работа с 3D-графикой объектов: формы, сетки, меши, вершины, материалы, геометрическое представление. | 4 | 
| ... | В категории ещё 353 типов; для полного машинного индекса требуется отдельная выгрузка CSV/JSON. | |

#### Отчёты / HTML / экспорт

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.DataExchangeUnit.CsvImportBuild` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 77 |
| `CADLibKernel.DataExchange<wbr>Unit.ExportUserListToXML` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 5 |
| `CADLib.XmlExtension.XmlExtension` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 18 |
| `CADLibKernel.DataExchangeUnit.CsvImport` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 3 |
| `CADLibKernel.DataExchangeUnit.eCsvImportMode` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 4 |

#### Параметры

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.Models.ExtendedParameter` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 29 |
| `CADLibKernel.Models.FastParameter` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 29 |
| `CADLibKernel.Models.Parameter` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 29 |
| `CADLibKernel.Models.SystemParameter` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 25 |
| `CADLibKernel.CParamsOwner` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 39 |
| `CADLibKernel.DataExchange<wbr>Unit.ParamDefsXmlImport` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 6 |
| `CADLibKernel.Models.ParametersDto` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 19 |
| `CADLibKernel.DataModels.dmParamDefs` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 17 |
| `CADLibKernel.XmlWrappers.X_PARAMETERS` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 13 |
| `CADLibKernel.Parameter` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 23 |
| `CADLibKernel.CLibParamDefInfo` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 30 |
| `CADLibKernel.ParamDefCategory` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 5 |
| `CADLibKernel.ParamDefVariant` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `CADLibKernel.SystemParameters` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 17 |
| `CADLibKernel.idParamDef` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 12 |
| `CADLibKernel.ParamDefIdEx` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 9 |
| `ParamDef` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 15 |
| `CADLibKernel.CLibParamCategoryInfo` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 10 |
| `CADLibKernel.CLibParametersQueryData` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 7 |
| `ParamCategory` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 8 |
| `CADLibKernel.CSParameter` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 8 |
| `ParamDef2` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 7 |
| `ParamValue` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 21 |
| `CADLibKernel.CLibCategoryFullInfo` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 17 |
| `CADLibKernel.ParamDef` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 13 |
| `CADLibKernel.ParameterDefault` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 5 |
| `CADLibKernel.SysParamDef` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 12 |
| `CADLibKernel.idFileCategory` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 14 |
| `CADLibKernel.idParamTable` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 14 |
| `CADLibKernel.idParamType` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 13 |
| `CLibParamDef` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 8 |
| `CsvParamRow` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 10 |
| `CExportParamContext` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `ParamDef` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 2 |
| `StructParamDefs` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `CADLibKernel.CLibCategoryInfo` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 14 |
| `CADLibKernel.CLibParamValue` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 10 |
| `CLibParamsMapItem` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 15 |
| `CADLibKernel.CMeasureUnit` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 13 |
| `CADLibKernel.DataExchangeUnit.DGetParamRefs` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `ParamKey` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 6 |
| `CADLibKernel.CLibParamValueExtended` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |
| `CADLibKernel.FileCategory` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 7 |
| `Common.LocalizedCategoryAttribute` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 2 |
| `ParamHeader` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 13 |
| `ParamType` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 5 |
| `ParamValue` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 5 |
| `ParamValueEx` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |
| `ClsParam`1` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |
| `ParamInfo` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |
| `ParamTable` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `eMissingParamValueTranslation` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |
| `eNullParamsPolicy` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 4 |
| `eParamData` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |

#### Пользователи / права

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `UserItem` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 41 |
| `CADLibKernel.DataExchange<wbr>Unit.UserRegistryExchange` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 8 |
| `GroupItem` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 9 |
| `RoleItem` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 9 |
| `CADLibKernel.CLibUserMRUItem` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 5 |
| `UserTagging.Common.eActivationType` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 4 |
| `UserTagging.Common.eTextVisibleBehaviour` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 4 |

#### Прочее / служебное

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.CSElement` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 77 |
| `CADLibKernel.Collections.<wbr>ObservableCollectionEx`1` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 40 |
| `CADLibKernel.CLibFilePropertySet` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 31 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 26 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 23 |
| `NotificationInfo` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 25 |
| `LandSurface` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 21 |
| `CADLibKernel.nElementOrder` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 15 |
| `CADLibKernel.Uploader` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 16 |
| `CADLibKernel.idFile` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 14 |
| `Vector` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 15 |
| `CADLibKernel.CdeStreamVersion` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 12 |
| `CADLibKernel.FileUID` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 12 |
| `CADLibKernel.CLibFileInfo` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 20 |
| `Common.LocalizedStringMap` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 11 |
| `CADLibKernel.CLibUpgradeInfoFile` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `CADLibKernel.Properties.Settings` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `CADLibKernel.ReentryMonitor` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 10 |
| `CADLibKernel.ModuleActivationContext` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 11 |
| `CADLibKernel.Transliteration` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 10 |
| `Common.Lang` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `CADLibKernel.Resource` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `PageData` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 11 |
| `QueryString` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 7 |
| `CADLib.ColorExtension` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 7 |
| `ReentryMonitor` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 6 |
| `Triangle` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `ValueData` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 7 |
| `CADLibKernel.FileTableInfo` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `CADLibKernel.GetFileReplaceAction` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `CADLibKernel.ICadDataSource` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `CADLibKernel.MainTableInfo` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 12 |
| `CADLibKernel.ProgressAction` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `DConnected` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `OnRefreshMethod` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `PageBoundary` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 7 |
| `State` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 10 |
| `CADLibKernel.CMeasurement` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 7 |
| `CSBlockHeader` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 7 |
| `Common.LocalizedDescriptionAttribute` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `Common.LocalizedDisplayNameAttribute` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `EqByName` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `TableData` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `Vertex` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 10 |
| `CADLibKernel.IconData` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `CADLibKernel.UpgradeInfoElement` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `Interop` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `Interop` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `ParseError` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `UniquePositionsComaparer` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 2 |
| `CADLib.CSColorList` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 2 |
| `CADLibKernel.AssemblyInfoEx` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `CADLibKernel.DataFile` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `CADLibKernel.DataFileWithId` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `CADLibKernel.Element` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `CADLibKernel.ElementMS` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `CADLibKernel.ExpertiseItem` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `CADLibKernel.LibOperationResult` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 7 |
| `CADLibKernel.UnassignedModifiedDate` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 2 |
| `CSColor` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `CopyMap` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `ImageInfo` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `LandSurfaceEx` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 13 |
| `Options` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `PageInfo` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `Result` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `tridata` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 2 |
| `ACTCTX` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 9 |
| `CADLibKernel.DataExchangeUnit.eHeaderLine` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `CADLibKernel.EFileReplaceAction` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 6 |
| `CADLibKernel.EFileReplaceContext` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `CADLibKernel.EPageDir` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `CADLibKernel.ERecursiveType` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `CADLibKernel.EResultSetType` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 6 |
| `CADLibKernel.EUpgradeInfo` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 6 |
| `CADLibKernel.eAddFileMode` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `CADLibKernel.eAlgorithmType` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `CADLibKernel.eWorksCodeSeparator` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| ... | В категории ещё 12 типов; для полного машинного индекса требуется отдельная выгрузка CSV/JSON. | |

#### Публикации / проект

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.CLibUserFavoritesItem` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 5 |
| `CADLibKernel.CLibAllUsersItem` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 3 |
| `CADLibKernel.CLibTableViewColumn` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 10 |

#### Фильтры / выборки

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CADLibKernel.CLibCatalogFilterItem` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 85 |
| `CADLibKernel.CLibClassifierFilterItem` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 29 |
| `LinkedObjectConditions` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 19 |
| `CADLibKernel.ObjectUpdate.CFilterItem` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 13 |
| `CADLibKernel.CLibFilterItemCollision` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 7 |
| `CADLibKernel.CLibUserFilterItem` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 6 |
| `CADLibKernel.ObjectUpdate.GetObjectHi...` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectHi...` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 4 | 
| `CADLibKernel.ObjectUpdate.GetObjectHi...` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 4 | 
| `CADLibKernel.ObjectUpdate<wbr>.GetObjectHierarchyFilter<wbr>CompletedEventArgs` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 4 |
| `CADLibKernel.CLibFilterItem` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 14 |
| `FilterInfo` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 7 |
| `HierarchyFilter` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 4 |
| `ConditionInfo` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 8 |
| `FilterInfoPair` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 3 |
| `CADLibKernel.eConditionTarget` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 3 |
| `CADLibKernel.eUseParentFilter` | Описание условия фильтрации/выборки объектов или файлов по параметрам, категориям, классификаторам. | 3 |

### `CSAppServices` — типы по функциональным зонам

#### DBBrowser / UI

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `DomainControllerInfo` | UI-слой CADLib: формы, диалоги, браузер БД, панели и команды интерфейса. | 10 |

#### Library / ядро БД

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CSAppServices.dbcpDBMSAuthentication` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 14 |
| `CSAppServices.dbcpOSAuthentication` | Центральный объект доступа к БД/библиотеке CADLib: соединение, объекты, параметры, структуры, операции импорта/экспорта. | 13 |

#### Объекты

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CSAppServices.ObjectPublisher` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 9 |

#### Отчёты / HTML / экспорт

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CSAppServices.CHTMLReport` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 24 |
| `CSAppServices.XmlWrappers.X_exchange` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 16 |
| `CSAppServices.ReportingEnumerable` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 10 |
| `CSAppServices.ReportingEnumerator`1` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 13 |
| `CSAppServices.ReportingEnumerable`1` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 7 |
| `CSAppServices.ReportingEnumerator` | Формирование отчётов, экспорт/импорт данных и документирование содержимого БД. | 1 |

#### Параметры

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CSAppServices.DbConnectParameters` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 57 |
| `CSAppServices.ParameterStorageBuild` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 26 |
| `CSAppServices.CLibParamDefInfo` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 18 |
| `CSAppServices.HParam` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |
| `Common.LocalizedCategoryAttribute` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 2 |
| `ParamInfo` | Работа с определениями параметров, категориями параметров, значениями, единицами измерения и зависимостями. | 3 |

#### Подключение / сервисы

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CSAppServices.XExchange` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 53 |
| `CSAppServices.UpgradeDatabaseBuild` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 55 |
| `CSAppServices.DbServerPort` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 14 |
| `CSAppServices.DbName` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 12 |
| `CSAppServices.DbPassword` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 12 |
| `CSAppServices.DbServerHost` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 12 |
| `CSAppServices.ChangeLog` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 11 |
| `CSAppServices.Mailbox`2` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 7 |
| `CSAppServices.DProcessReply` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 4 |
| `CSAppServices.DcName` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 5 |
| `CSAppServices.TableColumnPair` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 6 |
| `CSAppServices.CLWarningException` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 2 |
| `CSAppServices.Module` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 2 |
| `CSAppServices.Msg`2` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 3 |
| `CSAppServices.EDbInfo` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 15 |
| `CSAppServices.eProgress` | Сервисный слой: подключение к СУБД, строки подключения, публикация объектов, вспомогательные сервисы. | 10 |

#### Пользователи / права

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `CSAppServices.DbUser` | Пользователи, группы, роли, права доступа и интеграция с доменной инфраструктурой. | 12 |

#### Прочее / служебное

| Тип | Назначение / гипотеза | Публичные члены |
|---|---|---:|
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 68 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 62 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 14 |
| `Common.LocalizedStringMap` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 11 |
| `Common.Lang` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 8 |
| `DMakeCascadeSelectSqlAddWhere` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `attributes` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `Common.LocalizedDescriptionAttribute` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `Common.LocalizedDisplayNameAttribute` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `Eq` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `ParseError` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 5 |
| `CascadeSelect` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 3 |
| `CurrentVars` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 1 |
| `DSGETDCNAME_FLAGS` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 18 |
| `EChangeType` | Назначение явно не описано в XML; восстановлено только по имени типа и публичным членам DLL. | 4 |

## 8. Практические заготовки PythonPlugin

### 8.1 Получить текущую БД, окно и активную папку

```python
import System.Windows.Forms as wf
wf.MessageBox.Show(Library.Dbcp.Database.ToString())
wf.MessageBox.Show(CLMainForm.Text)
wf.MessageBox.Show(DBBrowser.CurrentFolder.Folder.mStrName)
```

### 8.2 Создать параметр и записать значение объектам по фильтру

```python
from System.Collections.Generic import List
from CADLibKernel import *

param = CLibParamDefInfo()
param.mstrName = "NEW_PARAM"
param.mstrCaption = "Новый параметр"
param.midType = 1
param.mCategories = List[CLibParamCategoryInfo]()
param.mCategories.Add(CLibParamCategoryInfo("Новые параметры"))
Library.CreateParamDef(param)

conditions = List[CLibFilterItem]()
conditions.Add(CLibFilterItem(Library.GetParamDefId("PART_TYPE"), "=", "Стена"))
filter = Library.CreateFilter(conditions)
objects = Library.GetObjectsList(filter)
for obj in objects:
    Library.SetParameter(obj, "NEW_PARAM", "2020")
```

### 8.3 3D-графика MSM/OBJ

Скрипт `MsmObjConverter.py` показывает, что 3D-сетка доступна через `ModelStudio.Graphics3D.CSMesh`, `CSVector3`, `CSMaterial`, `CSVertexCompressed`. Это полезно для конвертации геометрии, диагностики mesh и внешних пайплайнов визуализации.

## 9. Что нужно проверить на живой CADLib

1. Какие глобальные объекты реально доступны в PythonPlugin: `Library`, `DBBrowser`, `CLMainForm`, возможно другие.
2. Какие методы `CADLibraryBase` разрешены текущей ролью пользователя.
3. Какие типы параметров соответствуют `midType`: строка, число, список, вычисляемый параметр и т.д.
4. Какой объектный тип возвращает `Library.GetObjectsList(filter)` в конкретной версии CADLib.
5. Какие методы требуют транзакции `BeginTransaction / CommitTransaction / RollbackTransaction`.
6. Какие операции меняют БД необратимо: создание параметров, удаление объектов, копирование, импорт.

---

# Часть C. Практические заметки по кастомизации интерфейса Model Studio

Ниже собраны практические выводы из реальной настройки модуля `NANOWATER` в `Model Studio CS`. Это не общая теория по API, а рабочая памятка по тому, как на практике добавлять вкладки/кнопки и как диагностировать ситуацию, когда интерфейс модуля перестаёт загружаться.

## 1. Как в Model Studio устроена загрузка интерфейса модуля

Для модуля Water фактическая цепочка загрузки интерфейса оказалась такой:

1. В `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\cfg.ini` секция `[\Configuration\Water]` должна указывать на `CfgFile=sWater.cfg`.
2. Файл `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\Water.cfg` подключает модульный корневой конфиг:
   - `#include "C:\Program Files\CSoft\Model Studio CS\NANOWATER\water.cfg"`
3. Корневой `C:\Program Files\CSoft\Model Studio CS\NANOWATER\water.cfg` подключает:
   - `Support\WATER\ms_main.cfg`
   - `Support\WATER\water.cfg`
   - `Support\WATER\msestimate.cfg`
4. В этом же корневом `water.cfg` задаются ribbon-пакеты:
   - `Support\WATER\MSMAIN.cuix`
   - `Support\WATER\water.cuix`
   - `Support\WATER\msestimate.cuix`

Практический вывод: если нужно вернуть или исправить интерфейс модуля, проверять нужно не только `CUIX`, но и всю цепочку `cfg.ini -> user Water.cfg -> module water.cfg -> *.cuix`.

## 2. Главная причина, почему могут пропасть кнопки и вкладки

В реальной диагностике проблема оказалась не в `RibbonRoot.cui`, а в неверной привязке модуля Water в пользовательском конфиге.

Критический симптом:

- в `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\cfg.ini`
- в секции `[\Configuration\Water]`
- вместо `CfgFile=sWater.cfg` оказался указан чужой конфиг, например путь к `heatvent.cfg`

Из-за этого модуль Water начинал загружать не свой интерфейс, а конфигурацию другого модуля. Внешне это проявлялось так:

- не появлялись нужные вкладки и кнопки;
- менялись названия меню;
- могли подгружаться чужие разделы;
- создавалось впечатление, что «сломался ribbon», хотя корневая проблема была в неправильном `CfgFile`.

Рабочее решение:

- проверить `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\cfg.ini`;
- убедиться, что для `[\Configuration\Water]` стоит именно `CfgFile=sWater.cfg`;
- после правки полностью перезапустить `nanoCAD` / `Model Studio`.

## 3. Проблема кодировки и иероглифов

Для `Support\WATER\water.cfg` важно учитывать кодировку.

Практически подтверждено:

- `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\water.cfg` в битом состоянии читался как `cp1251`;
- после перекодирования в `UTF-8 BOM` кириллица стала отображаться корректно;
- для сравнения полезно смотреть на рабочие cfg-файлы других модулей, например `C:\Program Files\CSoft\Model Studio CS\NANOHEATVENT\Support\HEATVENT\heatvent.cfg`.

Практический вывод:

- если названия групп, меню или статусы в интерфейсе показываются «иероглифами», сначала нужно проверить кодировку `water.cfg`;
- безопасный рабочий формат для этого файла в нашем кейсе — `UTF-8 BOM`.

## 4. Интерфейсы: устройство `CUIX` и `RibbonRoot.cui`

Этот блок нужно считать рабочим журналом по структуре интерфейсов Model Studio. Его можно и нужно дополнять по мере накопления новых наблюдений.

### 4.1 Что такое `CUIX` в нашем кейсе

Практически подтверждено, что `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\water.cuix` — это контейнер-архив с XML-файлами интерфейса и набором картинок/иконок.

При распаковке в `water.cuix` были обнаружены:

- интерфейсные XML-файлы (`*.cui`);
- служебные файлы пакета, включая `Menu_Package_Info.xml`, `[Content_Types].xml`, `_rels\.rels`;
- встроенные иконки и изображения команд (`*.png`, `*.ico`, и др.).

Практический вывод:

- `CUIX` можно анализировать как zip-контейнер;
- для кастомизации ribbon полезнее всего изучать не бинарный контейнер целиком, а содержимое конкретных `*.cui` внутри него.

### 4.2 Какие файлы внутри `water.cuix` уже известны

Ниже перечислены файлы, наличие которых подтверждено распаковкой `water.cuix`:

- `MenuGroup.cui`
- `RibbonRoot.cui`
- `ToolbarRoot.cui`
- `AcceleratorRoot.cui`
- `Header.cui`
- `ImageMenuRoot.cui`
- `DigitizerButtonRoot.cui`
- `DoubleClickRoot.cui`
- `MouseButtonRoot.cui`
- `OverrideRoot.cui`
- `PanelSetRoot.cui`
- `PopMenuRoot.cui`
- `QuickAccessToolbarRoot.cui`
- `QuickPropertiesRoot.cui`
- `RolloverTooltipRoot.cui`
- `ScreenMenuRoot.cui`
- `TabletMenuRoot.cui`
- `ToolPanelRoot.cui`
- `WorkspaceRoot.cui`
- `LSPFiles.cui`

Также внутри присутствует большой набор иконок, например:

- `PipeDrawPipeline.png`
- `MStudioInlineAdd.png`
- `MS_PIPE32.png`
- `MStudioSupportAdd.png`
- `MStudioCopyPipeline.png`
- и другие штатные ресурсы команд.

### 4.3 Назначение основных файлов `CUIX`

Ниже — то, что уже подтверждено или достаточно надёжно выведено из структуры.

**Подтверждено**

- `MenuGroup.cui` — хранит определения макросов (`MenuMacro`), команды, `HelpString`, `SmallImage`, `LargeImage`.
- `RibbonRoot.cui` — хранит ribbon-вкладки, панели, группы, кнопки и привязки панелей к вкладкам.
- `ToolbarRoot.cui` — хранит классические панели инструментов (`Toolbar`, `ToolbarButton`, `MacroRef`).

**Пока считается вероятным, но ещё не разбиралось глубоко**

- `AcceleratorRoot.cui` — горячие клавиши / accelerators.
- `PopMenuRoot.cui` — контекстные меню.
- `QuickAccessToolbarRoot.cui` — панель быстрого доступа.
- `WorkspaceRoot.cui` — рабочие пространства.
- `RolloverTooltipRoot.cui` — расширенные всплывающие подсказки.
- `DoubleClickRoot.cui` — действия по двойному щелчку.
- `MouseButtonRoot.cui`, `TabletMenuRoot.cui`, `DigitizerButtonRoot.cui` — привязки кнопок мыши/планшета/вводных устройств.
- `PanelSetRoot.cui`, `ToolPanelRoot.cui` — наборы панелей и инструментальных панелей.
- `ImageMenuRoot.cui` — image-menu / меню с графическими элементами.
- `Header.cui` — служебная информация о пакете интерфейса.
- `OverrideRoot.cui` — переопределения / overrides.
- `LSPFiles.cui` — связанные LSP-описания или ссылки на Lisp-ресурсы.

Важно: эти роли нужно считать рабочими гипотезами, пока не проведён отдельный разбор каждого файла.

### 4.4 Что именно делает `MenuGroup.cui`

Практически подтверждено на `water.cuix`:

- каждая команда ribbon/toolbar в конечном итоге ссылается на `MenuMacroID`;
- сам `MenuMacroID` должен существовать в `MenuGroup.cui`;
- внутри `MenuMacro` лежат:
  - `Name`
  - `Command`
  - `HelpString`
  - `SmallImage`
  - `LargeImage`

Пример рабочего встроенного макроса:

- `UID="pipe_draw_pipeline"`
- `Command=^C^C_pipe_draw_pipeline`
- `SmallImage=PipeDrawPipeline.png`
- `LargeImage=MS_PIPE32.png`

Практический вывод:

- если кнопка видна, но не работает, нужно проверять не только `RibbonRoot.cui`, но и наличие/корректность соответствующего `MenuMacro` в `MenuGroup.cui`.

### 4.5 Что именно делает `RibbonRoot.cui`

Практически подтверждено на `water.cuix`:

- `RibbonPanelSource` описывает отдельную панель/группу ribbon;
- `RibbonTabSource` описывает вкладку;
- `RibbonPanelSourceReference` подключает панель к вкладке;
- `RibbonCommandButton` описывает кнопку ribbon;
- `RibbonSplitButton` описывает выпадающую кнопку-группу.

Из этого следует важная практическая разница:

- если добавить `RibbonCommandButton` внутрь `RibbonSplitButton`, команда попадёт в выпадающий список;
- если нужна отдельная видимая группа на вкладке, надо создавать отдельный `RibbonPanelSource` и затем привязывать его к `RibbonTabSource` через `RibbonPanelSourceReference`.

Это как раз было подтверждено на примере `DMTX`:

- первый вариант добавил кнопку внутрь split `Разное`, и она оказалась в выпадающем меню;
- финальный рабочий вариант — отдельная панель `DTMXtestPanel` на вкладке `Водоснабжение и канализация`.

### 4.5.1 Почему ribbon-кнопка может быть видна, но не работать

Отдельно подтверждена важная ловушка nanoCAD / Model Studio:

- одной правки `water.cuix` недостаточно;
- вид кнопки может приходить из `RibbonRoot.cui` / `MenuGroup.cui`, но исполнение ribbon-команды в пользовательском профиле опирается ещё и на кэш-файлы:
  - `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\RibbonCmds.xml`
  - `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\RibbonTabsAndPanels.xml`
- если кастомная кнопка видна, но по нажатию не происходит вообще ничего и в консоли нет следов запуска команды, нужно проверять именно `RibbonCmds.xml`.

Практически подтверждено:

- встроенные кнопки вроде `SCRIPTED` и `pipe_draw_pipeline` отрабатывают через свой ribbon-слой;
- наши `MenuMacro` в `MenuGroup.cui` существовали и были корректны;
- те же строки команд работали через `SendCommand(...)`;
- но кнопки `DTMX_CMD_*` молчали, пока в пользовательском `RibbonCmds.xml` не появились записи:
  - `UID="DTMX_CMD_EDIT"`
  - `UID="DTMX_CMD_EXPLORE"`
  - `UID="DTMX_CMD_PATHS"`

Практический вывод:

- для новых ribbon-кнопок нужно синхронно править:
  - `MenuGroup.cui`
  - `RibbonRoot.cui`
  - `Support\WATER\water.cfg` → блоки `[\configman\commands\DTMX_CMD_*]`
  - при необходимости пользовательский `RibbonCmds.xml`
  - и, если в профиле уже есть кэш кнопок, пользовательский `RibbonTabsAndPanels.xml`
- если кнопка уже есть на экране, но не исполняется, это очень сильный признак, что проблема не в NRX и не в самой команде, а именно в ribbon-кэше профиля.

Дополнительное подтверждение по Water:

- одного `UID` в `RibbonRoot.cui` недостаточно;
- для кастомных команд `DTMX_CMD_*` нужны реальные записи в `Support\WATER\water.cfg` в ветке:
  - `[\configman\commands\DTMX_CMD_EDIT]`
  - `[\configman\commands\DTMX_CMD_EXPLORE]`
  - `[\configman\commands\DTMX_CMD_PATHS]`
  - `[\configman\commands\DTMX_CMD_PING]`
- именно после появления этих блоков ribbon-кнопки начали стабильно исполнять наши NRX-команды.

### 4.6 Что именно делает `ToolbarRoot.cui`

Практически подтверждено, что `ToolbarRoot.cui` описывает классические панели инструментов и кнопки на них.

Внутри встречаются:

- `Toolbar`
- `Alias`
- `Name`
- `Description`
- `ToolbarButton`
- `ToolbarFlyout`
- `MacroRef MenuMacroID="..."`

Практический вывод:

- `ToolbarRoot.cui` полезен, если нужно понять старые toolbars модуля;
- но для задачи с вкладками/панелями ribbon в первую очередь нужно править `RibbonRoot.cui`.

### 4.7 Подтверждённая финальная схема `DMTX`

На текущем этапе рабочая схема для Water такая:

- на вкладке `Водоснабжение и канализация` есть отдельная панель `DTMXtestPanel`;
- в панели `DTMXtestPanel` есть кнопка `DMTX`;
- отдельно существует вкладка `DTMXtest` со своей кнопкой `DMTX`;
- в выпадающем списке `Разное` кнопки `DMTX` больше быть не должно;
- в группе `Трубопровод` кнопка `DMTX` больше не должна жить как отдельный элемент строки;
- обе рабочие кнопки должны использовать `MenuMacroID="pipe_draw_pipeline"`.

### 4.7.1 Иконки для кастомных DTMX-кнопок

Что подтверждено по факту:

- для кастомных команд `DTMX_CMD_*` в Water кнопка реально регистрируется через `Support\WATER\water.cfg`;
- визуальная иконка для этих команд берётся из блока `[\configman\commands\DTMX_CMD_*]` через:
  - `BitmapDll=s...`
  - `Icon=s...`
  - либо `BitmapId=s...`
- эта схема полностью совпадает с примерами из `NC_SDK_RU_24.1\samples\Menu\NCadSDK.cfg`.

Практический итог:

- `water.cfg` нужен не только для регистрации команды, но и является реальным источником иконки для `DTMX_CMD_*`;
- попытка опираться только на `MenuGroup.cui -> SmallImage/LargeImage` для этих кастомных DTMX-кнопок у нас не дала результата;
- даже когда PNG были встроены в `water.cuix`, кнопки оставались пустыми;
- даже подмена на уже существующие штатные `SmallImage/LargeImage` из `water.cuix` не оживила картинки.

Отсюда следует:

- для DTMX-кнопок в Water надёжный путь — собственный ресурсный DLL;
- рабочая схема:
  - `DtmxMenuRes.dll` — ресурсный DLL с `ICON`-ресурсами;
  - `water.cfg` — ссылка `BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_...`;
  - `RibbonRoot.cui` / `MenuGroup.cui` — структура вкладки, панели и макросов, но не основной источник картинки.

Дополнительно подготовлен собственный набор bitmap-иконок DTMX в проекте:

- каталог:
  - `Assets\Icons\DTMX`
- исходники на chroma-key фоне:
  - `dtmx_edit_source.png`
  - `dtmx_properties_source.png`
  - `dtmx_connections_source.png`
  - `dtmx_test_source.png`
- прозрачные PNG:
  - `dtmx_edit.png`
  - `dtmx_properties.png`
  - `dtmx_connections.png`
  - `dtmx_test.png`
- уменьшенные версии под ribbon / toolbar:
  - `dtmx_edit_16.png`, `dtmx_edit_32.png`, `dtmx_edit_64.png`
  - `dtmx_properties_16.png`, `dtmx_properties_32.png`, `dtmx_properties_64.png`
  - `dtmx_connections_16.png`, `dtmx_connections_32.png`, `dtmx_connections_64.png`
  - `dtmx_test_16.png`, `dtmx_test_32.png`, `dtmx_test_64.png`

Практика генерации:

- иконки генерируются в едином стиле как отдельные raster-assets;
- фон делается однотонным chroma-key (`#00ff00`);
- после этого фон локально вырезается в alpha PNG;
- для встраивания в ribbon удобнее держать сразу набор размеров `16/32/64`.

### 4.7.2 Почему PNG внутри `water.cuix` не сработали

Мы отдельно проверили гипотезу, что кастомные DTMX-кнопки можно заставить брать картинку напрямую из `water.cuix`.

Что именно было сделано:

1. Подготовлены свои PNG в `Assets\Icons\DTMX`.
2. PNG были встроены в `water.cuix`.
3. В `MenuGroup.cui` у `DTMX_CMD_*` были проставлены `SmallImage` / `LargeImage`.
4. В `._rels\.rels` были добавлены `Relationship Type="Image"`.
5. В `[Content_Types].xml` были добавлены `ContentType="image/png"`.
6. В `Menu_Package_Info.xml` были добавлены `PartData` для новых картинок.
7. Для контроля выполнялась даже замена на уже существующие штатные картинки из самого `water.cuix`.

Результат проверки:

- `CUIX` действительно является контейнером с картинками;
- структура упаковки PNG была приведена к корректному виду;
- но для `DTMX_CMD_EDIT`, `DTMX_CMD_EXPLORE`, `DTMX_CMD_PATHS`, `DTMX_CMD_PING` кнопки всё равно оставались пустыми.

Практический вывод:

- сама идея встраивать PNG в `water.cuix` не бесполезна для анализа структуры `CUIX`;
- но для наших кастомных DTMX-команд в Water это не дало рабочего отображения;
- поэтому этот путь помечаем как исследованный, но нерабочий для текущего кейса.

### 4.7.3 Финальный рабочий путь: ресурсный DLL

Финально рабочим оказался классический путь из SDK:

1. Создать отдельный ресурсный DLL без кода:
   - `DtmxMenuRes\DtmxMenuRes.vcxproj`
   - `DtmxMenuRes\DtmxMenuRes.rc`
2. Подготовить `ICO`-файлы:
   - `DtmxMenuRes\res\dtmx_edit.ico`
   - `DtmxMenuRes\res\dtmx_explore.ico`
   - `DtmxMenuRes\res\dtmx_paths.ico`
   - `DtmxMenuRes\res\dtmx_ping.ico`
3. В `DtmxMenuRes.rc` объявить ресурсы:
   - `DTMX_EDIT ICON "res\\dtmx_edit.ico"`
   - `DTMX_EXPLORE ICON "res\\dtmx_explore.ico"`
   - `DTMX_PATHS ICON "res\\dtmx_paths.ico"`
   - `DTMX_PING ICON "res\\dtmx_ping.ico"`
4. Собрать `DtmxMenuRes.dll`.
5. Положить DLL рядом с `water.cfg`:
   - `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\DtmxMenuRes.dll`
6. В `water.cfg` для каждой DTMX-команды указать:
   - `BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_EDIT`
   - `BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_EXPLORE`
   - `BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_PATHS`
   - `BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_PING`

Итог:

- кнопка остаётся зарегистрированной через `DTMX_CMD_*`;
- иконка берётся из ресурсного DLL;
- `RibbonRoot.cui` и `MenuGroup.cui` продолжают отвечать за структуру вкладки и команды;
- `water.cfg` становится точкой привязки иконки к кнопке.

Практический вывод:

- если кнопка DTMX видна, но иконка пустая, первым делом проверять `[\configman\commands\DTMX_CMD_*]` в `water.cfg`;
- если там нет `BitmapDll/Icon`, для нашего кейса это уже признак проблемы;
- для DTMX-кнопок Water безопаснее считать `resource DLL + water.cfg` основным рабочим решением.

### 4.7.4 Что дополнительно выяснили по формату иконок `resource DLL`

Ниже — уже более поздние и важные результаты по состоянию на `2026-06-30`.

#### Что подтвердилось

- для кастомных DTMX-кнопок механизм `BitmapDll=s... |Icon=s...` действительно работает;
- иконки из `DtmxMenuRes.dll` реально подхватываются интерфейсом;
- проблема была уже не в отсутствии иконки, а в качестве и корректности рендера:
  - мыло;
  - чёрные пиксели;
  - ощущение сломанной прозрачности.

#### Что оказалось ошибочным путём

Мы последовательно проверили несколько подходов:

1. **`PNG-compressed ICO`**
   - иконка собиралась как `ICO`, внутри которого лежали PNG-frame'ы;
   - результат: рендер в Water ломался сильнее всего.

2. **Многокадровый `ICO` (`16/24/32`)**
   - даже при `DIB/BMP`-frame'ах были артефакты;
   - поведение было хуже, чем у штатных SDK-примеров.

3. **Отрисовка своих иконок поверх уменьшенных/увеличенных raster-исходников**
   - особенно плохо выглядело при попытке рисовать “мини-иллюстрации” поверх маленькой кнопки;
   - появлялись грязные контуры и мусор на прозрачном фоне.

#### Что проверили программно у штатных иконок

Подтверждённые свойства штатных иконок:

- маленькие штатные иконки (`SmallImage`):
  - размер `16x16`;
  - часто режим `P` / palette-like;
  - alpha только `0/255`;
  - очень мало цветов.

- большие штатные иконки (`LargeImage`):
  - размер `32x32`;
  - режим `RGBA`;
  - alpha не обязательно строго бинарный, но значения очень ограничены;
  - пример:
    - `MS_EDITPIPE32.png` → alpha values `[0, 6, 243, 255]`
    - `MS_EDITVALV32.png` → alpha values `[0, 6, 255]`
    - `MS_PIPE_ROUTE32.png` → alpha values `[0, 6, 243, 255]`
    - `MS_WARNING32.png` → alpha values `[0, 255]`

Отдельно проверяли типичную маленькую системную иконку:

- `CommandBlue16.png`
  - `16x16`
  - `P`
  - alpha only `0/255`
  - всего `3` цвета

#### Что проверили у resource-иконок SDK

На примере:

- `NC_SDK_RU_24.1\samples\Menu\MenuRes\res\c_cap.ico`

подтверждено:

- это `ICO` с **одним** frame;
- размер frame — `16x16`;
- внутри лежит `DIB`, а не PNG;
- прозрачный фон читается корректно.

Это стало важным эталоном для сравнения с нашими кастомными иконками.

#### Самый важный практический вывод

Для `configman` / `BitmapDll | Icon` в Model Studio / nanoCAD:

- нельзя считать, что любой корректный Windows `ICO` будет одинаково хорошо рендериться;
- есть высокая вероятность, что загрузчик иконок ведёт себя “узко” и лучше всего работает с форматом, близким к SDK-образцу:
  - single-frame `ICO`;
  - `DIB/BMP` внутри;
  - особенно надёжно для `16x16`.

#### Нерешённый вопрос

Остаётся открытым вопрос по **большим ribbon-кнопкам**:

- наши кнопки на вкладке `DTMXtest` визуально относятся к большому типу;
- логично ожидать, что основная иконка там должна быть `32x32`;
- однако при использовании кастомного `resource DLL` даже точные копии больших штатных `32x32` иконок в некоторых тестах всё равно давали визуальные артефакты прозрачности.

Из этого следует:

- либо `configman`-иконка для этих кнопок фактически рендерится через путь, который лучше совместим только с “малой” resource-иконкой;
- либо внутри ribbon есть дополнительная логика выбора small/large representation, которую мы пока не нашли;
- либо для больших кнопок штатные команды используют не тот же путь рендера, что и кастомные `DTMX_CMD_*`.

#### Что уже можно утверждать уверенно

1. `water.cfg + BitmapDll/Icon` — рабочая точка подключения кастомной иконки.
2. `PNG` внутри `water.cuix` для `DTMX_CMD_*` — не решение нашей задачи.
3. `PNG-compressed ICO` — плохой путь для этого кейса.
4. `DIB ICO` ближе к правильному формату, чем `PNG ICO`.
5. Простое “нарисовать что-то красивое и сохранить в ICO” недостаточно — нужно повторять технику штатных иконок почти буквально.

#### Что стоит исследовать дальше

Если продолжать поиск решения уже с внешней помощью / другим агентом, полезно искать ответы на такие вопросы:

- как именно ribbon в nanoCAD / Model Studio выбирает изображение для `configman`-команды на большой кнопке;
- поддерживает ли этот путь отдельные `16x16` и `32x32` resources в одном DLL;
- использует ли `Icon=` только `HICON 16x16`, а large-version подтягивает откуда-то ещё;
- есть ли у `configman` альтернативный синтаксис для large bitmap:
  - `BitmapId=...`
  - отдельные large/small resource identifiers;
- можно ли использовать resource `BITMAP`, а не `ICON`, для больших ribbon-элементов;
- как именно сделаны large-иконки у штатных команд Model Studio, если команда задана через `configman`.

#### Краткое состояние на момент передачи

- пустые иконки — победили;
- неправильную кодировку и лишние DTMX-блоки — чистили;
- точка привязки `BitmapDll/Icon` — подтверждена;
- основная текущая проблема — **не сам механизм подключения, а корректный формат/тип большой кастомной иконки для ribbon**.

### 4.8 Скрипты `SCRIPTED`: что реально подтвердилось по языкам

Этот блок относится именно к встроенному редактору `SCRIPTED` в nanoCAD / Model Studio, а не к `PythonPlugin` из CADLib.

Подтверждённые факты по состоянию на `2026-06-23`:

- `VBScript (.vbs)` запускается штатно из `SCRIPTED`; простой `MsgBox` отрабатывает без дополнительной настройки.
- `JScript (.js)` запускается штатно из `SCRIPTED`; рабочий минимальный smoke-test лучше делать через `ActiveXObject("WScript.Shell").Popup(...)`, а не через `print(...)`.
- `Python (.py)` в `SCRIPTED` использует не `IronPython`, а Windows Active Scripting engine `Python.AXScript.2`.
- Ошибка `Unable to create scripting engine for "Python.AXScript.2"` означает, что сам движок Python Active Scripting не зарегистрирован в Windows.

Практически подтверждённый рабочий сценарий для `Python`:

1. Использовать установленный `Python 3.11`, а не пытаться сразу опираться на основной `Python 3.14`.
2. Убедиться, что для `Python 3.11` установлен `pywin32`.
3. Зарегистрировать Active Scripting engine командой:
   - `py -3.11 "C:\Users\atsarkov\AppData\Local\Programs\Python\Python311\Lib\site-packages\win32comext\axscript\client\pyscript.py"`
4. После регистрации в реестре должен появиться ключ:
   - `HKEY_CLASSES_ROOT\Python.AXScript.2`

Практический вывод по отладке:

- если `VBScript` и `JScript` работают, а `Python` пишет ошибку про `Python.AXScript.2`, сначала нужно чинить регистрацию Active Scripting, а не сам скрипт;
- если ошибка уже не показывается, но `print(...)` ничего не выводит, это ещё не значит, что Python не работает: для smoke-test надёжнее использовать popup через COM / WinAPI или запись в файл;
- для `JScript` и `VBScript` в `SCRIPTED` нужно мыслить категориями ActiveX Automation;
- для `Python` в `SCRIPTED` нельзя автоматически переносить предположения из `PythonPlugin`: это другой хост и другой способ передачи контекста.

Подтверждённые COM ProgID, видимые в системе:

- `nanoCAD.Application`
- `nanoCAD.Application.24.0`
- `nanoCADx64.Application`
- `nanoCADx64.Application.24.0`
- `nanoCAD.Drawing.24.1`

Практическая разница между двумя Python-контурами:

- `PythonPlugin` внутри CADLib даёт готовые объекты `Library`, `DBBrowser`, `CLMainForm`;
- `SCRIPTED -> Python` даёт именно Active Scripting / COM-контур и требует отдельно получать `Application` / `ActiveDocument`.

### 4.9 Практика по свойствам элементов Model Studio внутри DWG

Подтверждённые факты по состоянию на `2026-06-23` при пробе выбранной трубы `vCSSubSegment`:

- для пользовательской трубы в модели основной рабочий COM-тип сейчас — `vCSSubSegment`;
- часть свойств элемента доступна прямо на сущности как обычные COM-свойства, например `Part_Name`, `Part_Tag`, `Part_Type`, `Part_Comment`, `Part_Material`, `Part_Standard`, `PartPipe_DN`;
- запись в `entity.Part_Tag` реально меняет значение, но это поле соответствует не `PART_TAGNUMBER`, а другому свойству интерфейса;
- вызов `entity.GetAxisParamValue("PART_TAGNUMBER")` на проверенном объекте вернул пустую строку, то есть это не тот канал, через который читается нужный параметр.

Что обнаружено по вложенным объектам:

- `entity.Element` даёт отдельный COM-объект элемента Model Studio;
- у `entity.Element` подтверждены методы `GetValue(parameter)`, `GetValueComment(parameter)`, свойство `Parameters` и метод `SetParameters(pSrc)`;
- `entity.ElementAxis` даёт осевой объект с методами `GetFromObjParamVal(ParamName)` и `GetToObjParamVal(ParamName)`;
- значит, если параметр не виден как прямое свойство `Part_*`, следующая правильная точка поиска — именно `Element.GetValue(...)`, коллекция `Element.Parameters` и методы осевого объекта.

Дополнительная практическая проверка по `PART_TAGNUMBER`:

- `PART_TAGNUMBER` реально найден в `entity.Element.Parameters`;
- в проверенном объекте это был элемент коллекции с индексом `25` из `31`;
- у самого item подтверждены свойства `Name`, `Value`, `Comment`, `ValueComment`;
- `item.Name = "PART_TAGNUMBER"`, `item.Comment = "Идентификатор"`;
- прямое присваивание `item.Value = "DTMX"` само по себе не является надёжным commit-механизмом;
- вызов `entity.Element.SetParameters(entity.Element.Parameters)` в таком виде дал COM-ошибку `Несовпадение типов`, то есть метод принимает не просто коллекцию параметров как есть;
- у самой коллекции `entity.Element.Parameters` подтверждён метод:
  - `SetParameter(Name, Value, Comment, ValueComment)`
- именно `Parameters.SetParameter("PART_TAGNUMBER", "DTMX", comment, valueComment)` оказался рабочим способом записи;
- после `Parameters.SetParameter(...)` и `entity.Update()` повторная проверка показала:
  - `entity.Element.GetValue("PART_TAGNUMBER") = "DTMX"`
  - `PARAM[25].Value = "DTMX"`

Рабочие диагностические скрипты:

- `Scripts/probe_selected_ms_nested_objects.py` — базовая разведка по `entity`, `entity.Element`, `entity.ElementAxis`;
- `Scripts/probe_selected_ms_element_parameters.py` — точечная проверка `Element.GetValue(...)`, `Element.GetValueComment(...)`, `Element.Parameters`, `ElementAxis.GetFromObjParamVal(...)`, `ElementAxis.GetToObjParamVal(...)`.
- `Scripts/probe_selected_ms_parameter_item.py` — probe самого item внутри `Element.Parameters`;
- `Scripts/probe_selected_ms_commit_channels.py` — probe коллекции `Parameters`, её методов и каналов commit;
- `Scripts/set_selected_pipes_part_tagnumber.py` — боевой скрипт записи `PART_TAGNUMBER` для всех выделенных труб через `Element.Parameters.SetParameter(...)`.
- `Scripts/set_selected_ms_parameter.py` — универсальный боевой шаблон записи произвольного параметра Model Studio для выделенных объектов.

Минимальный рабочий рецепт записи `PART_TAGNUMBER`:

1. Взять выделенные `vCSSubSegment`.
2. Для каждой трубы получить `entity.Element.Parameters`.
3. Вызвать:
   - `Parameters.SetParameter("PART_TAGNUMBER", "DTMX", comment, valueComment)`
4. Затем выполнить `entity.Update()`.
5. Для проверки читать назад через:
   - `entity.Element.GetValue("PART_TAGNUMBER")`

Универсальный шаблон для дальнейшей работы:

- в `Scripts/set_selected_ms_parameter.py` меняются только верхние константы:
  - `TARGET_PARAMETER`
  - `TARGET_VALUE`
  - `ENTITY_NAMES`
- для труб текущий рабочий набор:
  - `ENTITY_NAMES = {"vcssubsegment"}`
- если позже будем писать параметры арматуры, оборудования или других объектов, можно оставить тот же скрипт и только расширить `ENTITY_NAMES`.

Практический вывод:

- для чтения/записи “обычных” свойств nanoCAD / части свойств Model Studio можно работать напрямую с COM-сущностью;
- для полного доступа к параметрам именно элемента Model Studio нужно исследовать не только сам объект чертежа, но и вложенный объект `Element`.
- для `PART_TAGNUMBER` рабочий commit-механизм через Python/COM уже подтверждён: нужно писать не в `item.Value`, а через `entity.Element.Parameters.SetParameter(...)`.

### 4.10 Как правильно называть два подхода

Чтобы дальше не путаться, полезно разделять два слоя:

- `SCRIPTED Python / COM / Automation` — это скриптовый слой, в котором мы сейчас работаем;
- `.NET plugin API` или `внутренний .NET API nanoCAD / Model Studio` — это плагинный слой на `C#` / `VB.NET`, который загружается в хост как `.dll`.

Практически в разговоре лучше использовать такие формулировки:

- “через `Python/COM`” — когда речь про текущие скрипты в `SCRIPTED`;
- “через `.NET API`” или “через `.NET-плагин`” — когда речь про собственную сборку `.dll`.

### 4.11 Насколько решение будет другим в `.NET`

Короткий практический ответ: не кардинально по логике, но заметно по способу реализации.

Что, скорее всего, останется тем же:

- нужно будет найти выделенные объекты;
- нужно будет понять тип объекта, например `vCSSubSegment`;
- нужно будет обратиться к параметрам именно элемента Model Studio, а не только к “обычным” свойствам графического объекта;
- нужно будет записать значение параметра и обновить объект.

Что, скорее всего, изменится:

- вместо `COM`-объектов и вызовов `GetActiveObject(...)` / `Dispatch(...)` будет использоваться плагинный контур `HostMgd` / `.NET API`;
- вместо проб через `dir(...)`, `GetTypeInfo(...)` и `COM`-методы работа пойдёт через типы, методы и свойства `.NET`;
- код будет более строгим: меньше “угадывания” имён на лету, больше явных типов и ссылок на сборки;
- интеграция с интерфейсом, командами и кнопками будет удобнее и чище в `.dll`.

Практический вывод для нашей задачи:

- бизнес-логика не меняется: “найти трубы → найти параметр элемента → записать значение → обновить объект”;
- меняется именно технический слой доступа;
- поэтому текущая разведка через `Python/COM` не пропадает: она уже дала нам карту объектов, имён параметров и рабочую последовательность действий.

Когда есть смысл оставаться в `Python/COM`:

- быстрые пробы;
- массовые одноразовые сценарии;
- диагностика, логирование, исследование неизвестного API;
- простые инструменты без сложной UI-интеграции.

Когда есть смысл идти в `.NET API`:

- нужен стабильный production-инструмент;
- нужна нормальная команда/кнопка/диалог;
- нужна более глубокая интеграция с nanoCAD / Model Studio;
- нужно меньше зависеть от ограничений `SCRIPTED` и `COM`.

### 4.12 Проба `Python -> .NET` внутри контура `Python 3.11`

На `2026-06-23` дополнительно проверен отдельный экспериментальный мост:

- в `Python 3.11`, который используется для `Python.AXScript.2`, был установлен пакет `pythonnet`;
- внешний probe подтвердил:
  - `import clr` — работает;
  - `import System` — работает;
  - `System.Environment.Version` читается;
  - `clr.AddReference("System.Windows.Forms")` — работает.

Рабочий probe:

- `Scripts/probe_scripted_python_dotnet.py`

Что это означает practically:

- гипотеза “из Python-контурa можно попробовать поднять .NET-библиотеки” подтверждена как минимум на уровне самого `Python 3.11`;
- это ещё не доказывает, что тот же код будет на 100% так же работать именно внутри окна `SCRIPTED`, но направление уже выглядит реальным, а не чисто теоретическим;
- если `SCRIPTED` увидит тот же `pythonnet`, мы сможем попробовать гибридный подход: `Python` как сценарный слой + `.NET` как библиотечный мост.

### 4.13 Гибридный путь `Python -> .NET COM interop` и пределы live-bridge

На `2026-06-24` подтверждён ещё один важный результат:

- скрипт `Scripts/set_part_tagnumber_dotnet.py` успешно записывает `PART_TAGNUMBER` через `.NET COM interop`;
- рабочая схема:
  1. взять live COM-объект через `win32com`;
  2. получить его нативный `IUnknown*`;
  3. превратить его в `System.__ComObject` через `Marshal.GetObjectForIUnknown(...)`;
  4. вызвать `Parameters.SetParameter(...)` уже через `.NET reflection dispatch`.

Практический вывод:

- это уже не чистый `pywin32`, а рабочий гибридный мост `Python + pythonnet + .NET COM interop`;
- для live-редактирования текущего элемента в DWG этот путь подтверждён как рабочий.

Отдельная проба прямого моста в `mstManagedAPI.CElement` показала ограничение:

- `mstManagedAPI.CElement` имеет конструктор от `MStudioData.IElement*`;
- прямое создание `CElement` из `System.__ComObject`, полученного от live COM-элемента, не удалось;
- runtime сообщил, что не может преобразовать `System.__ComObject` в `MStudioData.IElement*`.

Что это означает practically:

- прямой путь `live COM element -> mstManagedAPI.CElement` пока не найден;
- значит, `mstManagedAPI` нельзя считать автоматически “прямой обёрткой” над текущим выбранным COM-объектом;
- следующий поиск нужно вести либо через `LibDatabase`, либо через другие интерфейсные типы/базы `MStudioData`, а не через наивный конструктор `CElement`.

### 4.14 Локальный runtime Model Studio внутри DWG: что удалось подтвердить

Важное уточнение по слою задачи:

- пока элемент живёт только в `DWG`, его нужно рассматривать как локальный runtime-объект Model Studio внутри nanoCAD;
- в этот момент не нужно опираться на `CadLib`, `LibDatabase` и синхронизацию в БД;
- основной практический контур для таких операций сейчас — `COM / Automation` по живому открытому чертежу.

Подтверждённый способ внешней диагностики без `SCRIPTED`:

- внешний `Python 3.11 + pywin32` может подключаться к уже открытому nanoCAD через `GetActiveObject("nanoCADx64.Application.24.0")`;
- далее доступны `app.ActiveDocument`, `ActiveSelectionSet`, `PickfirstSelectionSet` и live COM-объекты выбранных элементов;
- это позволяет исследовать и даже менять объекты `Model Studio` из отдельного процесса, пока открыт нужный `DWG`.

Практически подтверждённая COM-поверхность live объекта трубы `vCSSubSegment`:

- у графического объекта доступны прямые свойства nanoCAD / Model Studio, например `Part_Name`, `Part_Tag`, `Part_Type`, `PartPipe_DN`, `PartPipe_Diam`, `PartPipe_Thickness`, `Bom_*`, `Explication_*`;
- у объекта есть вложенные точки входа `Element` и `ElementAxis`;
- у самого `Element` подтверждены:
  - свойства `Name`, `Description`, `ElementId`, `ObjectId`, `Parameters`, `Parent`, `Root`, `SubElements`, `SubElementsAll`, `PathFromRoot`;
  - методы `GetValue(parameter)`, `GetValueComment(parameter)`, `GetPath(divider)`, `GetParentByLevel(level)`, `GetById(id)`, `AddChild(Name)`, `SetParameters(pSrc)`, `CopyFrom(pSrc)`;
- у `Element.Parameters` подтверждены:
  - `Count`;
  - `Item(indexOrName)`;
  - `Has(indexOrName)`;
  - `SetParameter(Name, Value, Comment, ValueComment)`;
  - `DeleteParameter(Name)`;
  - `DeleteAll()`.

Практический вывод по параметрам трубы:

- на тестовой трубе было перечислено `29` параметров `Element.Parameters`;
- из них `19` имеют прямое соответствие в свойствах графического объекта (`entity.Part_*`, `entity.PartPipe_*`, `entity.Bom_*`);
- ещё `10` доступны только через `Element.Parameters`.

Что оказалось прямыми свойствами объекта:

- `PART_NAME -> Part_Name`;
- `PART_TAG -> Part_Tag`;
- `PART_TYPE -> Part_Type`;
- `PART_MATERIAL -> Part_Material`;
- `PART_STANDARD -> Part_Standard`;
- `PART_PIPE_DN -> PartPipe_DN`;
- `PART_PIPE_DIAMETER -> PartPipe_Diam`;
- `PIPE_THICKNESS -> PartPipe_Thickness` (но значение оказалось не полностью эквивалентно параметру, это нужно учитывать отдельно).

Что на текущем тесте оказалось только в `Element.Parameters`:

- `PART_TAGNUMBER`;
- `PART_PIPE_PN`;
- `PART_PIPE_CLASS`;
- `PART_SPECIALITY`;
- `SYS_DB_UID`;
- `START_COMPID`;
- служебные `BOM_*` поля вроде `BOM_GROUP_ID`, `BOM_PART_QTY`, `BOM_SORT_ID`.

Отсюда рабочее правило:

- если параметр уже вынесен в прямое свойство `entity.Part_*` / `entity.PartPipe_*`, для чтения и простых правок можно идти через сам графический объект;
- если параметр не вынесен напрямую, основной безопасный путь — `entity.Element.Parameters.SetParameter(...)`;
- `PART_TAGNUMBER` относится именно ко второй группе: он подтверждён как parameter-only и штатно пишется через `Parameters.SetParameter(...)`.

### 4.15 `ElementAxis` как локальный обход модели внутри DWG

Самая сильная находка по локальному обходу модели:

- `entity.ElementAxis.Components` возвращает не один объект, а всю связанную трассу / ось как набор live COM-объектов;
- на текущем тестовом участке было получено `33` компонента, из них `16` объектов типа `vCSSubSegment`, плюс `vCSNode` и `vCSInLine`;
- это значит, что для задач “обойти все трубы связанной ветки” не нужно искать их по всему чертежу и не нужен `LISP`.

Дополнительно по `ElementAxis` подтверждены:

- `Components`;
- `GetFirstComponent()`;
- `GetLastComponent()`;
- `GetPrevComponent(component)`;
- `GetNextComponent(component)`;
- `GetFromObjParamVal(paramName)`;
- `GetToObjParamVal(paramName)`;
- `CountItems(bTerminators, bElbows, bPipes, bInlines, bSupports)`;
- свойства `StartTee`, `EndTee`, `StartPipe`, `EndPipe`, `HasStartPipe`, `HasEndPipe`, `Length`.

Отдельно по иерархии `Element`:

- `SubElements` у тестовой трубы вернул 1 дочерний элемент;
- `SubElementsAll` вернул 4 элемента для одного `ObjectId` (`ElementId = 0, 1, 2, 3`);
- `PathFromRoot` вернул цепочку от корня до текущего элемента;
- это подтверждает, что внутренняя структура Model Studio внутри `DWG` уже существует как отдельная иерархия, даже без БД.

### 4.16 Практический итог по COM-выделению без LISP

Удалось подтвердить ещё один важный сценарий:

- из `ElementAxis.Components` можно собрать список pipe-объектов `vCSSubSegment`;
- этот список можно передать в `SelectionSet.AddItems(...)` через обычный `COM`;
- внутри одного COM-сеанса `ActiveSelectionSet` и `PickfirstSelectionSet` действительно показывали `Count = 16` для найденных труб трассы.

Но есть важная оговорка:

- при внешнем запуске из отдельного Python-процесса это выделение не было надёжно подтверждено как устойчивое UI-выделение после завершения процесса;
- то есть для операций обработки объектов лучше не завязываться на визуальное выделение как на единственный commit-механизм.

Практический вывод:

- для массовых операций над трубами связанной трассы лучше работать напрямую по коллекции `ElementAxis.Components`;
- UI-выделение можно считать вспомогательным инструментом, но не основным каналом изменения модели.

### 4.17 Новые служебные скрипты по локальному DWG runtime

Для этого слоя были добавлены отдельные probes:

- `Scripts/probe_live_ms_dispatch.py` — глубокий дамп `IDispatch`/`TypeInfo` для `entity`, `Element`, `ElementAxis`, `Parameters` и первого parameter item;
- `Scripts/probe_pipe_parameter_surface.py` — карта соответствия между `Element.Parameters` и прямыми свойствами `entity.Part_*` / `entity.PartPipe_*`;
- `Scripts/select_axis_pipes_com.py` — обход `ElementAxis.Components` с фильтрацией `vCSSubSegment` и попыткой переноса найденных труб в активные selection sets через `COM`.

### 4.18 .NET runtime для локального DWG: nanoCAD SDK, `HostMgd` и `Multicad`

Отдельно был проверен локальный nanoCAD SDK:

- `C:\pdf_ingest\DTMXtest\NC_SDK_RU_26.0.7228.4926.8429`

Ключевой практический вывод:

- managed API nanoCAD SDK в этой поставке уже работает не на старом `.NET Framework`, а на `.NET 6`;
- это подтверждается тем, что `hostmgd.dll` и `mapimgd.dll` требуют `System.Runtime, Version=6.0.0.0`;
- поэтому новый probe под локальный `DWG`/`Model Studio` нужно собирать как `net6.0-windows`, а не как `.NET Framework 4.8`.

Что удалось подтвердить по слоям API:

- `HostMgd + Teigha` — слой для доступа к активному документу, editor, transaction, `ModelSpace`, `ObjectId`;
- `Multicad` — более высокий слой для работы с `McObjectId`, `McDbEntity`, `McProperties`, то есть ближе к реальным объектам nanoCAD / Model Studio внутри `DWG`.

Практически полезные точки входа из SDK:

- `HostMgd.ApplicationServices.Application.DocumentManager.MdiActiveDocument`
- `Document.Editor`
- `Database.TransactionManager.StartTransaction()`
- `Multicad.McObjectManager.SelectObject(...)`
- `McObjectId.GetObject()`
- `McObjectId.GetObjectOfType<McDbEntity>()`
- `McDbEntity.GetProperties(McProperties.PropertyType.Object)`

Для проверки этого слоя добавлен отдельный проект:

- `NanoDwgProbe.csproj`
- `NanoDwgProbe.cs`

Сборка проекта:

- `dotnet restore NanoDwgProbe.csproj`
- `dotnet build NanoDwgProbe.csproj -c Debug -p:Platform=x64`
- `dotnet build NanoDwgProbe.csproj -c Release -p:Platform=x64`

Результат сборки:

- `bin\NanoDwgProbe\Debug\NanoDwgProbe.dll`
- `bin\NanoDwgProbe\Release\NanoDwgProbe.dll`

Команды, которые сейчас реализованы в этой DLL:

- `DTMX_MS_DWGINFO` — пишет в командную строку и лог базовую информацию о текущем документе и количестве сущностей в `ModelSpace`;
- `DTMX_MS_DUMPSEL` — просит выбрать объект через `Multicad`, затем пытается выгрузить тип `McObject`, тип `McDbEntity` и весь набор object-properties;
- `DTMX_MS_SETTAGNUMBER` — просит выбрать объект, затем пытается записать значение в `PART_TAGNUMBER` через `McProperties` / `PropertyDescriptor`.

Куда пишет лог:

- `C:\pdf_ingest\DTMXtest\LOG\NanoDwgProbe_*.txt`

Отдельный важный вывод по исследованию:

- на первом проходе не нужно искать мост `Teigha.ObjectId -> McObjectId`, потому что для прикладного исследования объектов Model Studio проще и надёжнее сразу работать через `McObjectManager.SelectObject(...)`;
- мост между low-level `HostMgd` и high-level `Multicad` может понадобиться позже, но он не обязателен для первого рабочего runtime-probe.

Текущее направление исследования:

- сначала проверить, какие свойства реально видны через `McDbEntity.GetProperties(McProperties.PropertyType.Object)` у выбранной трубы `Model Studio`;
- затем сравнить, попадают ли туда `PART_TYPE`, `PART_TAG`, `PART_TAGNUMBER`;
- если запись `PART_TAGNUMBER` сработает через `.NET`, это будет первый подтверждённый путь изменения свойств объекта `Model Studio` внутри `DWG` без `COM`.

Практический результат первой живой проверки команды `DTMX_MS_DUMPSEL`:

- команда `DTMX_MS_DWGINFO` успешно получила активный `DWG`, путь к базе и количество сущностей в `ModelSpace`;
- команда `DTMX_MS_DUMPSEL` успешно выбрала объект `Model Studio` через `Multicad`;
- выбранная труба была прочитана как:
  - `McObject type = Multicad.DatabaseServices.McEntity`
  - `McDbEntity type = Multicad.DatabaseServices.McDbEntity`
- через `McDbEntity.GetProperties(McProperties.PropertyType.Object)` было получено `45` свойств.

Ключевой вывод по свойствам:

- в `.NET` property surface не нашлись прямые имена `PART_TYPE`, `PART_TAG`, `PART_TAGNUMBER`;
- вместо этого видны человеко-читаемые свойства на русском языке, например:
  - `Дополнительные параметры.Тип изделий`
  - `Параметры изделия.Наименование изделия`
  - `Параметры изделия.Обозначение / Модель`
- это означает, что для `.NET`-слоя `Model Studio` внутри `DWG` свойства могут быть доступны не по внутренним `PART_*` alias, а по локализованным display/property names.

Из этого следует следующая рабочая стратегия:

- искать и писать свойства не только по `PART_*`, но и по русским именам, которые реально возвращает `McProperties`;
- первым кандидатом на запись сейчас является:
  - `Параметры изделия.Обозначение / Модель`
- именно это поле раньше уже проявлялось как связанное с `PART_TAG` / `PART_TAGNUMBER` в предыдущих COM-пробах.

Отдельное замечание по использованию команды `DTMX_MS_SETTAGNUMBER`:

- сначала команда ждёт именно выбор объекта;
- только после выбора объекта появляется запрос на ввод нового значения;
- если в этот момент вводить текст до выбора объекта, nanoCAD воспринимает это как неверное выражение/ввод в фазе выбора.

После этого probe был доработан:

- команда `DTMX_MS_SETTAGNUMBER` теперь пытается искать несколько вариантов имён свойства:
  - `PART_TAGNUMBER`
  - `PART_TAG`
  - `Параметры изделия.Обозначение / Модель`
  - `Обозначение / Модель`
- добавлена отдельная команда:
  - `DTMX_MS_SETMODEL`
- она пишет значение напрямую в:
  - `Параметры изделия.Обозначение / Модель`

Практический результат первой записи через `DTMX_MS_SETMODEL`:

- свойство `Параметры изделия.Обозначение / Модель` находится корректно;
- `PropertyDescriptor` сообщает `ReadOnly=False`;
- вызов `SetValue(...)` проходит без исключения;
- но значение `Before` и `After` остаётся одинаковым.

Текущий вывод:

- в этом месте `.NET` уже точно видит property surface объекта `Model Studio`;
- но обычного `PropertyDescriptor.SetValue(...)` пока недостаточно для фактической записи в подложку модели;
- это очень похоже на `no-op setter`, UI-wrapper setter или необходимость писать через другой owner / другой API-слой.

Практическое замечание по разработке DLL:

- после `NETLOAD` nanoCAD удерживает загруженную DLL открытой;
- поэтому повторная сборка в тот же `bin` может упираться в блокировку файла;
- удобный рабочий приём: собирать новую версию во второй output path, например:
  - `bin\NanoDwgProbe\Debug2\NanoDwgProbe.dll`

Практический результат успешной записи `PART_TAGNUMBER` уже через `COM`:

- для выбранной трубы `Model Studio` прямой `.NET`-setter пока не дал фактической записи;
- при этом через живой `COM`-объект выбранного элемента удалось получить реальный список параметров `element.Parameters`;
- у выбранной трубы подтверждено:
  - `ObjectName = vCSSubSegment`
  - параметр `PART_TAGNUMBER` существует в коллекции параметров элемента;
  - его человеко-читаемое имя / comment:
    - `Идентификатор`
- рабочий канал записи оказался таким:
  - `entity.Element.Parameters.SetParameter("PART_TAGNUMBER", value, param_comment, valueComment)`
  - затем `entity.Update()`
  - затем `doc.Regen(1)`
- проверка после записи показала:
  - `element.GetValue("PART_TAGNUMBER")` возвращает новое значение;
  - повторная выгрузка `element.Parameters` тоже показывает новое значение.

Из этого следует важный вывод по слоям API:

- `.NET`-слой nanoCAD / Multicad уже полезен для исследования `DWG`, выбора объекта и просмотра object-properties;
- но для изменения именно параметров элемента `Model Studio` внутри `DWG` на текущем этапе подтверждённо работает именно `COM`-канал `Element.Parameters.SetParameter(...)`;
- внутреннее имя `PART_TAGNUMBER` и отображаемое имя `Идентификатор` — это один и тот же параметр, просто в разных представлениях.

Рабочий скрипт для этой операции:

- `Scripts\set_selected_ms_identifier.py`

Что делает этот скрипт:

- берёт уже выбранные объекты из `ActiveSelectionSet` / `PickfirstSelectionSet`;
- оставляет только `vCSSubSegment`;
- ищет у элемента параметр `PART_TAGNUMBER`;
- записывает новое значение;
- пишет лог в:
  - `C:\Users\atsarkov\Desktop\set_selected_ms_identifier_log.txt`

## 5. Фича 1. Как добавить вкладку `DTMXtest`, группу и кнопку

Ниже — рабочая схема, которая была проверена на модуле `NANOWATER`.

### 5.1 Что именно редактируется

Основной файл ленты для Water:

- `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\water.cuix`

Дополнительно может использоваться:

- `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\MSMAIN.cuix`

Практически оказалось достаточно правки `water.cuix` для финальной схемы:

- новой вкладки `DTMXtest`;
- кнопки `DMTX` на вкладке `DTMXtest`;
- отдельной панели `DTMXtestPanel` на вкладке `Водоснабжение и канализация`;
- кнопки `DMTX` внутри панели `DTMXtestPanel`.

### 5.2 Какую команду лучше использовать

Для кнопки `DMTX` сначала был создан отдельный макрос-дубликат, но наиболее надёжный вариант оказался другим:

- привязывать кнопку напрямую к штатному `MenuMacroID="pipe_draw_pipeline"`

Почему так лучше:

- штатный макрос уже существует внутри `water.cuix`;
- у него уже корректно настроены команда, подсказка и изображения;
- привязка к встроенному `MenuMacroID` срабатывает надёжнее, чем ссылка на самодельный дублирующий макрос.

Рабочая привязка кнопки:

- `MenuMacroID="pipe_draw_pipeline"`

Команда встроенного макроса:

- `^C^C_pipe_draw_pipeline`

### 5.3 Пошаговый алгоритм

1. Сделать бэкап `water.cuix`.
2. Распаковать `water.cuix` как zip-архив во временную папку.
3. В `RibbonRoot.cui`:
   - создать отдельный `RibbonPanelSource` для вкладки `DTMXtest`;
   - создать отдельный `RibbonTabSource` для `DTMXtest`;
   - добавить в эту вкладку кнопку `DMTX` с `MenuMacroID="pipe_draw_pipeline"`;
   - создать отдельный `RibbonPanelSource` с именем `DTMXtestPanel`;
   - привязать `DTMXtestPanel` к вкладке `Водоснабжение и канализация` через `RibbonPanelSourceReference`;
   - добавить в `DTMXtestPanel` кнопку `DMTX` с `MenuMacroID="pipe_draw_pipeline"`;
   - не добавлять `DMTX` внутрь split-кнопки `Разное`, если нужна именно отдельная группа.
4. Сохранить XML в `UTF-8 BOM`.
5. Собрать `water.cuix` обратно.
6. Полностью перезапустить `Model Studio`.

### 5.4 Минимум, который должен появиться после патча

После успешной модификации в интерфейсе должны быть видны:

- новая вкладка `DTMXtest`;
- кнопка `DMTX` на вкладке `DTMXtest`;
- отдельная панель `DTMXtestPanel` на вкладке `Водоснабжение и канализация`;
- кнопка `DMTX` внутри панели `DTMXtestPanel`;
- по нажатию должен запускаться штатный сценарий `Отрисовать трубопровод`.

## 6. Что проверять, если после патча кнопок нет

Если после изменения `CUIX` кнопки не появились, идти нужно в таком порядке:

1. Проверить `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\cfg.ini`
   - секция `[\Configuration\Water]`
   - строка `CfgFile=sWater.cfg`
2. Проверить `C:\Users\atsarkov\AppData\Roaming\Nanosoft\nanoCAD x64 24.1\Config\Water.cfg`
   - должен быть include на `C:\Program Files\CSoft\Model Studio CS\NANOWATER\water.cfg`
3. Проверить `C:\Program Files\CSoft\Model Studio CS\NANOWATER\water.cfg`
   - должны быть подключены `MSMAIN.cuix` и `water.cuix`
4. Проверить кодировку `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\water.cfg`
   - если текст битый, сначала исправить кодировку
5. Проверить, что кнопка в `RibbonRoot.cui` привязана именно к рабочему `MenuMacroID`
   - в нашем кейсе это `pipe_draw_pipeline`
6. Проверить, что отдельная панель действительно подключена к вкладке Water через `RibbonPanelSourceReference`
   - одной правки `RibbonPanelSource` недостаточно, если ссылка на панель не добавлена в `RibbonTabSource`
7. После любых правок полностью закрыть и заново открыть приложение

## 7. Что проверять, если кнопка видна, но ничего не делает

Если кнопка в ribbon отображается, но по нажатию ничего не происходит, нужно проверять не только наличие кнопки, но и её привязку:

- кнопка может ссылаться на пользовательский макрос, который визуально существует, но обрабатывается хостом не так, как штатный;
- в таком случае лучше не дублировать команду, а использовать уже существующий встроенный `MenuMacroID`.

Практически подтверждённое решение для нашего кейса:

- заменить `MenuMacroID="DTMX_WATER_BUTTON"` на `MenuMacroID="pipe_draw_pipeline"`

После этого кнопка `DMTX` начала корректно запускать действие.

## 8. Практический итог по Model Studio

На текущем этапе можно считать подтверждёнными следующие выводы:

- для задач по ribbon в Model Studio критична не только правка `CUIX`, но и корректная цепочка `cfg`;
- отсутствие кнопок в интерфейсе чаще всего нужно начинать диагностировать с `cfg.ini`, а не с ribbon XML;
- для Water важна корректная кодировка `Support\WATER\water.cfg`;
- новые кнопки в ribbon безопаснее привязывать к уже существующим штатным `MenuMacroID`, если такие есть;
- если нужна отдельная видимая группа на вкладке, нужно создавать `RibbonPanelSource` и подключать его через `RibbonPanelSourceReference`, а не добавлять кнопку внутрь split-кнопки;
- для модуля `NANOWATER` рабочая точка кастомизации ribbon — `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\water.cuix`.

Дополнительно подтверждено для текущего патчера `Patch-NanoWaterCuix.ps1`:

- по умолчанию он должен держать кастомные команды именно на вкладке `DTMXtest`;
- по умолчанию он не должен возвращать `DMTX` в split `Разное`;
- по умолчанию он не должен возвращать `DMTX` в строку панели `Трубопровод`;
- если такие старые вхождения есть, патчер их удаляет;
- на вкладке `DTMXtest` поддерживаются отдельные кнопки:
  - `DTMXEDIT`
  - `DTMXNRX22EXPLORE`
  - `DTMXNRX23PATHS`

## 9. In-process `.NET` в nanoCAD / Model Studio

Ниже — важный практический результат по исследованию доступа к объектам `Model Studio` внутри `DWG` уже из загруженной `.NET`-команды.

### 9.1 Что подтвердилось

- отдельная сборка под `HostMgd` и `hostdbmgd` на `net6.0-windows` успешно загружается в открытый `nanoCAD`;
- рабочий проект-проба находится в:
  - `NrxPluginHost6\DtmxHost6Probe.csproj`
  - `NrxPluginHost6\Host6Probe.cs`
- команда `DTMXHOSTPROBE` через `HostMgd.Editor.SelectImplied()` корректно видит текущее выделение;
- на живой проверке были получены:
  - `SelectImplied.Status = OK`
  - `SelectImplied.Count = 2`
  - оба объекта определились как `Rx = vCSSubSegment`
  - handles: `8A2`, `94C`

Это важный вывод, потому что прежний путь через `Multicad.DatabaseServices.McObjectManager.SelectionSet` в autorun-режиме возвращал `null`.

### 9.2 Что это означает practically

- проблема была не в том, что выделения в `DWG` нет;
- проблема была в неправильной точке входа;
- для работы с текущим выделением нужно заходить не через autorun/`McObjectManager.SelectionSet`, а через нормальную пользовательскую команду `HostMgd` и `Editor.SelectImplied()`.

То есть первый реальный рабочий `.NET`-слой для `Model Studio` внутри `DWG` уже подтверждён.

### 9.3 Команда записи `PART_TAGNUMBER` из in-process `.NET`

Добавлена вторая команда:

- `DTMXHOSTSETTAG`

Что она делает:

1. берёт выделение через `Editor.SelectImplied()`;
2. получает `Handle` выбранных `vCSSubSegment`;
3. по этим handle находит live COM-объекты через `ActiveDocument.HandleToObject(...)`;
4. пишет `PART_TAGNUMBER` в значение `DTMX_HOST6`;
5. вызывает `Update()` и `Regen(1)`;
6. пишет подробный лог в:
   - `C:\Users\atsarkov\Desktop\dtmx_host6_probe_log.txt`

### 9.4 Результат проверки `typed IPEParameters.Set()`

На живом запуске получен такой результат:

- `typed IPEParameters.Set()` из in-process `.NET` **не сработал**;
- ошибка:
  - `Unable to cast object of type 'System.__ComObject' to type 'SCXComponentsLibLib.IPEParameters'`
- fallback через late-bound:
  - `Parameters.SetParameter("PART_TAGNUMBER", value, "", "")`
  - **сработал**
- после записи:
  - `After=DTMX_HOST6`

Практический вывод:

- даже внутри загруженной `.NET`-команды доступ к параметрам `Model Studio` пока подтверждён именно через COM-объект `Element.Parameters`;
- но ключевой прогресс в том, что теперь этот доступ можно вызывать из нормальной in-process команды, а не только из внешнего `exe` или Python;
- текущий блокер для полностью типизированного варианта — не выделение и не команда, а именно приведение `System.__ComObject` к `SCXComponentsLibLib.IPEParameters`.

### 9.5 Текущее состояние исследования

На сейчас можно считать подтверждённым:

- `.NET`-команда внутри `nanoCAD` / `Model Studio` — рабочий путь;
- выбор текущих объектов `Model Studio` через `HostMgd` — рабочий путь;
- доступ к live-объектам `vCSSubSegment` по `Handle` — рабочий путь;
- изменение `PART_TAGNUMBER` из in-process команды — рабочий путь;
- полностью типизированный вызов `IPEParameters.Set()` — **ещё не подтверждён**.

Следующий этап исследования:

- понять, можно ли получить правильный typed RCW для `IPEParameters`;
- либо найти уже не `COM`, а собственный `.NET` API-слой `Model Studio` для параметров элемента внутри `DWG`.

### 9.6 Typed `.NET COM` через реальный `TypeLib` — подтверждённый успех

После дальнейшего исследования был найден более правильный путь, чем старый `Interop.SCXComponentsLibLib.dll`.

#### Откуда брать типы

В реестре у `IElement` зарегистрировано:

- `IID IElement = {32D3F761-7B49-4D57-AC6C-0D0879AC9A75}`
- `TypeLib = {1AE1985C-5D87-4E89-8E67-068628FC3CD6}`

Этот `TypeLib` указывает на:

- `C:\Program Files\CSoft\Model Studio CS\NANOWATER\bin\nanoCAD241\UnitsCSCom.nrx`

Из него была успешно сгенерирована interop-сборка командой:

- `C:\Program Files (x86)\Microsoft SDKs\Windows\v10.0A\bin\NETFX 4.8 Tools\x64\TlbImp.exe`
- команда:
  - `TlbImp.exe "C:\Program Files\CSoft\Model Studio CS\NANOWATER\bin\nanoCAD241\UnitsCSCom.nrx" /out:"C:\pdf_ingest\DTMXtest\Artifacts\UnitsCSCom.Interop.dll"`

Результат:

- `Artifacts\UnitsCSCom.Interop.dll`

#### Какие typed интерфейсы подтвердились

В этой interop-сборке найдены и проверены:

- `UnitsCSCom.Interop.IElement`
  - `GUID = 32D3F761-7B49-4D57-AC6C-0D0879AC9A75`
  - методы:
    - `GetValue(parameter)`
    - `GetValueComment(parameter)`
    - `SetParameters(pSrc)`
    - `GetPath(divider)`
    - `GetById(...)`
    - `GetParentByLevel(...)`
- `UnitsCSCom.Interop.IParameters`
  - `GUID = 8A6EB6C1-813B-4B17-941C-2B05D5D1C499`
  - методы:
    - `Item(index)`
    - `Has(index)`
    - `SetParameter(Name, Value, Comment, ValueComment)`
    - `DeleteParameter(...)`
    - `DeleteAll()`
- `UnitsCSCom.Interop.IParameter`
  - `GUID = D353DEF9-2B51-4F21-BEA3-6B666F4BA568`

#### Практический результат

Собран и проверен внешний typed `.NET` exe:

- `TypedUnitsComExe\TypedUnitsComExe.csproj`
- `TypedUnitsComExe\Program.cs`

Что он делает:

1. подключается к уже открытому `nanoCAD` через `Marshal.GetActiveObject(...)`;
2. берёт `PickfirstSelectionSet`;
3. находит первый `vCSSubSegment`;
4. получает `entity.Element` и `entity.Element.Parameters`;
5. приводит их через:
   - `Marshal.GetTypedObjectForIUnknown(..., typeof(UnitsCSCom.Interop.IElement))`
   - `Marshal.GetTypedObjectForIUnknown(..., typeof(UnitsCSCom.Interop.IParameters))`
6. вызывает:
   - `IParameters.SetParameter("PART_TAGNUMBER", "DTMX_TYPED_COM", "", "")`
7. вызывает `entity.Update()`;
8. проверяет новое значение через:
   - `IElement.GetValue("PART_TAGNUMBER")`
   - обычную COM-проверку `element.GetValue("PART_TAGNUMBER")`

Живой подтверждённый результат:

- `IElement.GetValue(PART_TAGNUMBER) before = DTMX_HOST6`
- `IParameters.SetParameter invoked`
- `IElement.GetValue(PART_TAGNUMBER) after = DTMX_TYPED_COM`
- `COM verify after = DTMX_TYPED_COM`

Практический вывод:

- typed `.NET COM` путь для `Model Studio` **реально работает**;
- это уже не late-bound `InvokeMember("SetParameter", ...)`, а нормальный typed interop;
- на текущем этапе это самый чистый и подтверждённый `.NET`-маршрут для изменения `PART_TAGNUMBER` в live `DWG`.

#### Дополнительный скрипт

Под этот же путь подготовлен Python-скрипт:

- `Scripts\set_part_tagnumber_typed_units.py`

Он использует:

- `python + clr`
- `Artifacts\UnitsCSCom.Interop.dll`
- `Marshal.GetTypedObjectForIUnknown(...)`

На момент последней проверки сам typed путь в скрипте собран корректно, но конкретный запуск завершился без записи только потому, что текущее выделение уже отсутствовало:

- `PickfirstSelectionSet count = 0`

То есть проблема была не в typed interop, а в отсутствии выбранных объектов в момент прогона.

## 10. Ошибочные и тупиковые направления

Ниже — список веток, которые уже были проверены и которые не стоит повторять без новой зацепки.

### 10.1 `McObjectManager.SelectionSet` в autorun

Проверено:

- in-process DLL через `mapimgd`
- autorun после `LoadModule`
- чтение `Multicad.DatabaseServices.McObjectManager.SelectionSet`

Результат:

- `SelectionSet is null`

Вывод:

- для работы с текущим выделением этот путь не подходит;
- правильная точка входа — обычная пользовательская команда + `HostMgd.Editor.SelectImplied()`.

### 10.2 Повторная hot-load загрузка одной и той же `HostMgd`-сборки

Проверено:

- последовательные сборки `HostMgd` DLL в новые каталоги;
- та же логика, но с новыми файлами;
- затем даже новые имена команд.

Практическая проблема:

- `nanoCAD` продолжал держать в памяти старую уже загруженную сборку;
- новые команды не появлялись предсказуемо в том же сеансе.

Вывод:

- для быстрых итераций по `HostMgd` нельзя рассчитывать на бесконечный hot-reload в одном сеансе;
- либо нужен новый сеанс `nanoCAD`, либо нужно выносить эксперимент в отдельный внешний процесс/скрипт.

### 10.3 `Interop.SCXComponentsLibLib.IPEParameters` typed cast

Проверено:

- `Marshal.GetTypedObjectForIUnknown(..., typeof(IPEParameters))`
- in-process и cross-process пробы

Результат:

- типизированное приведение не подтвердилось;
- ошибка вида:
  - `Unable to cast object of type 'System.__ComObject' to type 'SCXComponentsLibLib.IPEParameters'`

Но:

- fallback через `SetParameter(Name, Value, Comment, ValueComment)` работает.

Вывод:

- старый `Interop.SCXComponentsLibLib.dll` не дал надёжного typed-приведения для нашей live-поверхности;
- более правильный маршрут — `UnitsCSCom.nrx` → `TlbImp` → `UnitsCSCom.Interop.dll`.

### 10.4 `mstManagedAPI.CElement` от `IUnknown`

Проверено:

- `mstManagedAPI.CElement` создаётся через конструктор `.ctor(MStudioData.IElement*)`;
- если подать туда просто `IUnknown*`, конструктор может создаться, но чтение значений даёт:
  - `AccessViolationException`

Вывод:

- `IUnknown*` недостаточен;
- нужен корректный interface pointer.

### 10.5 `mstManagedAPI.CElement` от правильного `IElement*`

Проверено:

- `QueryInterface(IElement)` на IID:
  - `{32D3F761-7B49-4D57-AC6C-0D0879AC9A75}`
- `CElement` после этого создаётся корректно и уже не падает сразу.

Но:

- `GetParameterValue("PART_TAGNUMBER", "")` возвращал пустую строку;
- `SetParameter(...)` вызывался, но live `COM`-объект не менялся;
- `COM verify after` оставался со старым значением.

Вывод:

- `mstManagedAPI` уже близко к нужной поверхности и pointer-мост на `IElement` подтверждён;
- но на текущем этапе этот путь **не подтвердил запись обратно в live `DWG`**;
- значит, пока он не является боевым решением для изменения параметров выбранной трубы.

### 10.6 Прямой конструктор `mstManagedAPI.CElement` от `System.__ComObject`

Проверено:

- попытка передать `System.__ComObject` прямо в `CElement` через reflection

Результат:

- ошибка преобразования:
  - объект типа `System.__ComObject` не приводится к `MStudioData.IElement*`

Вывод:

- без pointer bridge этот путь нерабочий.

### 10.7 `Teigha.DatabaseServices.ImpEntity` не раскрывает `Model Studio` managed-поверхность

Проверено:

- in-process команда `DTMXHOSTPROBE2` на реальном объекте `Rx=vCSSubSegment`;
- fallback-скан `ModelSpace`, чтобы убрать зависимость от текущего выделения;
- reflection по runtime-типу `Teigha.DatabaseServices.ImpEntity`.

Результат:

- у live-объекта не нашлось прямых managed-свойств/методов вида `Element`, `Parameters`, `PartType`, `ModelStudio...`;
- из релевантного найдены только общие платформенные поверхности:
  - `AcadObject`
  - `UnmanagedObject`
  - `ObjectId`
  - `ExtensionDictionary`
  - `GetImpObj()`
- type dump не показал встроенного `.NET` API уровня `Model Studio` поверх `ImpEntity`.

Практический вывод:

- чистый путь `HostMgd/Teigha -> готовые managed свойства Model Studio` на текущем этапе **не подтверждён**;
- сам объект `DWG` в runtime выглядит как обычный `ImpEntity`, а не как специализированный `.NET`-класс с параметрами `Model Studio`;
- это сильно сужает дальнейший поиск: если чистый `.NET` путь существует, он лежит не в открытых свойствах `ImpEntity`, а либо в:
  - `UnmanagedObject` / внутренних указателях,
  - `mstManagedAPI`,
  - отдельной нативной фабрике/обвязке `Model Studio`.

### 10.8 `mstManagedAPI.ProjectService` без скрытой фабрики

Проверено:

- `Activator.CreateInstance(mstManagedAPI.ProjectService)`;
- отдельно — inside `nanoCAD` через `NrxPluginPureDotNet`;
- отдельно — после `mstManagedAPI.MstudioCore.LoadCoreFromPath(...)` с путями:
  - `C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin`
  - `...\mstCoreLoader.dll`
  - `C:\Program Files\CSoft\Model Studio CS\NANOWATER\bin\nanoCAD241`
  - `...\mstCoreLoader.dll`
- дополнительно вызвано:
  - `mstManagedAPI.ProjectBuildingHierarchy.CollectObjectsFactoryData()`

Результат:

- `ProjectService` стабильно падает на конструкторе:
  - `Error: pFactory can't be NULL. Disposed object using possible.`
- `LoadCoreFromPath(...)` не устранил проблему;
- `CollectObjectsFactoryData()` вернул `null` и тоже не устранил проблему.

Вывод:

- одного присутствия `mstManagedAPI.dll` в процессе недостаточно;
- даже в процессе `nanoCAD` фабрика, требуемая `ProjectService`, не инициализируется автоматически через найденные публичные managed entry points;
- на текущем этапе `ProjectService` нельзя считать рабочей точкой входа для чистого `.NET` доступа к live-данным `Model Studio` внутри `DWG`.

### 10.9 Практический статус на текущий момент

Подтверждено:

- `COM` путь работает;
- typed `.NET COM` путь через `UnitsCSCom.Interop.dll` работает.

Не подтверждено:

- чистая запись параметров `Model Studio` в live `DWG` через только managed `.NET` API без `COM`.

Самый важный практический вывод:

- сейчас у нас **нет подтверждённого чистого `.NET` маршрута без `COM`** для изменения `PART_TAGNUMBER` у live-объекта `Model Studio` в открытом `DWG`;
- все реальные успехи записи пока идут либо через:
  - `IDispatch/COM`,
  - либо через typed `.NET COM interop`.

---

## 11. NRX C++ vtable — подтверждённый нативный путь (2026-06-24)

### 11.1 Обзор подхода

NRX (nanoCAD Runtime Extension) — это C++ DLL, аналог ObjectARX в AutoCAD. Загружается командой `APPLOAD` в nanoCAD, работает in-process в том же адресном пространстве. Файл имеет расширение `.nrx`.

В отличие от COM IDispatch, vtable-вызовы работают напрямую через C++ virtual dispatch — без `Invoke`, без `GetIDsOfNames`, без boxing VARIANT. Это самый быстрый и прямой способ работы с `IElement`/`IParameters`.

### 11.2 Три подтверждённых способа записи параметров

| Способ | Механизм | Статус |
|---|---|---|
| Python/COM через `entity.Element.Parameters.SetParameter(...)` | IDispatch, late-bound | ✅ работает |
| C# + `UnitsCSCom.Interop.dll` (TlbImp) | Typed .NET COM interop | ✅ работает |
| **NRX C++ vtable** | Прямой C++ virtual call | ✅ **подтверждено** |

### 11.3 Объявление интерфейсов (вручную из TypeLib)

TypeLib находится в `UnitsCSCom.nrx`:

```
C:\Program Files\CSoft\Model Studio CS\NANOWATER\bin\nanoCAD241\UnitsCSCom.nrx
```

Объявления без `#import` (избегает зависимости от OdaX/IAcadEntity):

```cpp
struct __declspec(uuid("8A6EB6C1-813B-4B17-941C-2B05D5D1C499"))
IParameters : IDispatch
{
    virtual HRESULT __stdcall get__NewEnum(IUnknown** ppEnumVariant)        = 0;
    virtual HRESULT __stdcall Item(VARIANT Index, IUnknown** pVal)           = 0;
    virtual HRESULT __stdcall get_Count(long* pVal)                          = 0;
    virtual HRESULT __stdcall SetParameter(BSTR Name, BSTR Value,
                                           VARIANT Comment,
                                           VARIANT ValueComment)             = 0;
    virtual HRESULT __stdcall DeleteParameter(BSTR Name)                     = 0;
    virtual HRESULT __stdcall DeleteAll()                                    = 0;
    virtual HRESULT __stdcall Has(VARIANT Index, VARIANT_BOOL* pResult)      = 0;
};

struct __declspec(uuid("32D3F761-7B49-4D57-AC6C-0D0879AC9A75"))
IElement : IDispatch
{
    virtual HRESULT __stdcall get_Name(BSTR* pVal)                           = 0;
    virtual HRESULT __stdcall put_Name(BSTR pVal)                            = 0;
    virtual HRESULT __stdcall get_Parameters(IParameters** pVal)             = 0;
    // ... (GetValue, GetParentByLevel, AddChild, SetParameters — см. DtmxNrx.cpp)
    virtual HRESULT __stdcall GetValue(BSTR parameter, BSTR* pResult)        = 0;
};
```

### 11.4 Ключевые IID

```
IID IElement    = {32D3F761-7B49-4D57-AC6C-0D0879AC9A75}
IID IParameters = {8A6EB6C1-813B-4B17-941C-2B05D5D1C499}
```

### 11.5 Полный нативный путь (чистый C++, без COM)

COM не нужен: все MAPI DLL уже загружены в процессе nanoCAD когда активен Model Studio CS.  
Доступ только через `gpMcNativeGate` из `McTyp.dll` + NRX-функции для выбора объектов.

```
acedSSGet()                              NRX — выбор объектов
  → ads_name → AcDbObjectId             NRX — oid объекта

  → GetModuleHandleA("McTyp.dll")        MAPI — получить DLL
  → GetProcAddress(..., "gpMcNativeGate") → IMcNativeGate*

  → getMcsIdByNative(mcid, *(int64_t*)&oid)  → mcsWorkID
  → QueryObject(mcid)                        → IMcObjectPtr

  → pObj->isKindOf(IMcParametricEnt::...)    → IMcParametricEnt*

  → getParams(arr)                      читаем все параметры
  → arr: найти / добавить exValue       изменяем нужный
  → setParams(arr)                      записываем обратно
```

**Создание / изменение параметра:**

```cpp
// Добавить или перезаписать PART_TAGNUMBER:
mcsExValueArray params;
pParamEnt->getParams(params);         // получить текущие

exValue ev;
ev.strParName = _T("PART_TAGNUMBER");
ev.setValue(_T("новое_значение"));    // → MCSSTR
ev.lFlag = MCPAR_PUBLIC;
params.AddDistinctByName(ev, true);   // true = перезаписать если есть

pParamEnt->setParams(params);
```

**Динамическое получение IMcNativeGate (без линковки McTyp.lib):**

```cpp
static IMcNativeGate* GetNativeGate() {
    HMODULE h = GetModuleHandleA("McTyp.dll");
    if (!h) return nullptr;
    auto** pp = (IMcNativeGate**)GetProcAddress(h, "gpMcNativeGate");
    return pp ? *pp : nullptr;
}
```

> **Устаревший COM-путь** (оставлен для справки, больше не используется):
> `GetActiveObject("nanoCADx64.Application.24.0") → ActiveDocument → HandleToObject → .Element → QI IElement`

### 11.6 vtMissing для опциональных VARIANT-параметров

`SetParameter(BSTR Name, BSTR Value, VARIANT Comment, VARIANT ValueComment)` —  
последние два параметра опциональные. Передача `VT_EMPTY` возвращает `DISP_E_TYPEMISMATCH (0x80020005)`.

Правильный способ — `VT_ERROR | DISP_E_PARAMNOTFOUND` (эквивалент `vtMissing` в VBA):

```cpp
static VARIANT MissingVar()
{
    VARIANT v; VariantInit(&v);
    V_VT(&v)    = VT_ERROR;
    V_ERROR(&v) = DISP_E_PARAMNOTFOUND;
    return v;
}
```

### 11.7 ABI mismatch: SDK 26.0 vs nanoCAD 24.1

SDK 26.0 изменил тип параметров `acedSSLength`/`acedSSName` с `long` на `int`. Это меняет mangled name:

- SDK 26.0 импортирует: `?ncedSSLength@@YAHQEB_JPEAH@Z` (`PEAH` = `int*`)
- nanoCAD 24.1 экспортирует: `?ncedSSLength@@YAHQEB_JPEAJ@Z` (`PEAJ` = `long*`)

Windows loader не находит `PEAH` в `NrxHostGate.dll` → `ERROR_PROC_NOT_FOUND (127)` при APPLOAD.

**Решение:** GetProcAddress-обёртки с правильными именами 24.1:

```cpp
static int NCAD_SSLength(ads_name ss, long* pLen)
{
    typedef int(*PFN)(ads_name, long*);
    static PFN fn = nullptr;
    if (!fn) {
        HMODULE h = GetModuleHandleW(L"NrxHostGate.dll");
        fn = h ? (PFN)GetProcAddress(h, "?ncedSSLength@@YAHQEB_JPEAJ@Z") : nullptr;
    }
    return fn ? fn(ss, pLen) : RTERROR;
}
```

Аналогично для `NCAD_SSName` (имя: `?ncedSSName@@YAHQEB_JJQEA_J@Z`).

### 11.8 Подключение COM-заголовков при HOST_NO_MFC

`HOST_NO_MFC` отключает CString-зависимости в `filer.h` и других NRX headers.  
Но COM-заголовки (`comdef.h`, `oaidl.h`, `oleauto.h`) нужно подключить **до** `#define HOST_NO_MFC`:

```cpp
// stdafx.h — порядок критичен:
#include <windows.h>
#include <comdef.h>       // IDispatch, BSTR, VARIANT
#include <oaidl.h>        // IDispatch, IEnumVARIANT
#include <oleauto.h>      // SysAllocString, VariantInit
#include <objbase.h>      // CoInitialize, GetActiveObject
#include <unknwn.h>       // IUnknown

#define HOST_NO_MFC
#include "arxHeaders.h"   // NRX SDK
```

### 11.9 Перечисление параметров через IEnumVARIANT

`IParameters::get__NewEnum()` возвращает `IEnumVARIANT`. Каждый item — объект с IDispatch-свойствами `Name` и `Value`:

```cpp
IUnknown* pEnumUnk = nullptr;
pParams->get__NewEnum(&pEnumUnk);
IEnumVARIANT* pEV = nullptr;
pEnumUnk->QueryInterface(IID_IEnumVARIANT, (void**)&pEV);

VARIANT vi = {}; ULONG got = 0;
while (pEV->Next(1, &vi, &got) == S_OK && got > 0) {
    IDispatch* pd = (vi.vt == VT_DISPATCH) ? vi.pdispVal : nullptr;
    if (pd) {
        VARIANT vN={}, vV={};
        DispGet(pd, L"Name", &vN);   // имя параметра
        DispGet(pd, L"Value", &vV);  // текущее значение
        // ...
        VariantClear(&vN); VariantClear(&vV);
    }
    VariantClear(&vi); got = 0;
}
```

`IID_IEnumVARIANT = {00020404-0000-0000-C000-000000000046}`

### 11.10 Win32 GUI диалог из NRX (без MFC)

При `HOST_NO_MFC` MFC недоступен. GUI строится через Win32 API напрямую.  
Для корректного отображения кириллицы нужен системный шрифт:

```cpp
NONCLIENTMETRICSW ncm = {sizeof(ncm)};
SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, sizeof(ncm), &ncm, 0);
HFONT hFnt = CreateFontIndirectW(&ncm.lfMessageFont);
// → "Segoe UI" 9pt на Windows 10/11, полная поддержка Unicode/кириллицы
```

`GetStockObject(DEFAULT_GUI_FONT)` не подходит — возвращает устаревший шрифт без гарантии поддержки кириллицы.

Модальный message loop **без `PostQuitMessage`** (иначе хост завершится):

```cpp
bool done = false;
MSG msg;
while (!done) {
    BOOL got = GetMessageW(&msg, nullptr, 0, 0);
    if (got == 0) { PostQuitMessage((int)msg.wParam); break; } // WM_QUIT — репост хосту
    if (got < 0) break;
    if (!IsDialogMessageW(hDlg, &msg)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
}
// done = true выставляется в WM_DESTROY окна диалога
```

### 11.11 Сборка NRX-проекта (VS 2022, SDK 26.0, nanoCAD 24.1)

- `PlatformToolset`: в vcxproj `v145`, при сборке переопределять: `/p:PlatformToolset=v143`
- Подключить: `$(NCadSDK)\include\arxgate\rxsdk_releasecfg.props`
- Переопределить `OutputFile` вручную: `$(OutDir)DtmxNrx7.nrx` (SDK props перезаписывает это)
- Дополнительные библиотеки: `Gdi32.lib`, `User32.lib` (через `#pragma comment(lib, ...)`)

**Кириллица в исходнике — обязательный флаг:**

```xml
<!-- vcxproj → ItemDefinitionGroup → ClCompile -->
<AdditionalOptions>/utf-8 /wd4828 %(AdditionalOptions)</AdditionalOptions>
```

Причина: инструменты создают `.cpp` в UTF-8 без BOM. MSVC без `/utf-8` читает файл как Windows-1251 и компилирует `L"Параметр:"` в неверные codepoints — кириллица ломается и в консоли nanoCAD, и в Win32-диалоге. `/wd4828` подавляет предупреждение C4828 о "неверных UTF-8 байтах" в SDK-заголовках (они сами написаны в Windows-1251).

**Полный `stdafx.h`:**

```cpp
#pragma once
#pragma pack(push, 8)
#pragma warning(disable: 4786 4996 4251)
#include <SDKDDKVer.h>
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
// COM-заголовки ОБЯЗАТЕЛЬНО до HOST_NO_MFC:
#include <windows.h>
#include <comdef.h>
#include <oaidl.h>
#include <oleauto.h>
#include <objbase.h>
#include <unknwn.h>
#define HOST_NO_MFC
#include "arxHeaders.h"
#include <string>
#include <map>
#include <vector>
#pragma pack(pop)
```

### 11.12 Логирование из NRX — UTF-8 с BOM

Писать лог-файл нужно в UTF-8 (не UTF-16), иначе Notepad/VSCode не читают кириллицу без ручной смены кодировки:

```cpp
static void LogClear()
{
    HANDLE hf = CreateFileW(LOG_PATH, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, 0, nullptr);
    if (hf != INVALID_HANDLE_VALUE) {
        const unsigned char bom[] = {0xEF, 0xBB, 0xBF};   // UTF-8 BOM
        DWORD w; WriteFile(hf, bom, 3, &w, nullptr);
        CloseHandle(hf);
    }
}

static void Log(const wchar_t* msg)
{
    SYSTEMTIME st; GetLocalTime(&st);
    wchar_t wbuf[4096];
    int wn = swprintf_s(wbuf, L"%02d:%02d:%02d %s\n", st.wHour, st.wMinute, st.wSecond, msg);
    char utf8[8192];
    int un = WideCharToMultiByte(CP_UTF8, 0, wbuf, wn, utf8, sizeof(utf8)-1, nullptr, nullptr);
    if (un <= 0) return;
    HANDLE hf = CreateFileW(LOG_PATH, GENERIC_WRITE, FILE_SHARE_READ,
                             nullptr, OPEN_ALWAYS, 0, nullptr);
    if (hf != INVALID_HANDLE_VALUE) {
        SetFilePointer(hf, 0, nullptr, FILE_END);
        DWORD w; WriteFile(hf, utf8, (DWORD)un, &w, nullptr);
        CloseHandle(hf);
    }
}
```

### 11.13 MAPI — нативный C++ путь к параметрам (исследование 2026-06-25)

MAPI (Model Studio CS API) — это отдельная C++ объектная модель, параллельная NRX/ObjectARX. Заголовки находятся в `$(NCadSDK)\include\MAPI\`.

#### Ключевые глобальные переменные (McTyp.dll)

```cpp
// IMcs.h:72
extern MCTYP_API IMcNativeGate *gpMcNativeGate;  // мост NcDb ↔ MAPI
extern MCTYP_API IMcContext    *gpMcContext;       // контекст приложения MAPI
```

#### Динамическое получение без статической линковки

```cpp
// Аналог MCS_GetContextDyn() из IContext.h
static IMcNativeGate* GetMcNativeGate()
{
    HMODULE h = GetModuleHandleA("McTyp.dll");
    if (!h) return nullptr;
    void** pp = (void**)GetProcAddress(h, "gpMcNativeGate");
    return pp ? (IMcNativeGate*)*pp : nullptr;
}

static void* MCS_GetContextDyn()
{
    FARPROC fn = GetProcAddress(GetModuleHandleA("MechCtl.dll"), "MCS_GetContext");
    return fn ? ((void*(*)())fn)() : nullptr;
}
```

#### Интерфейс параметров (IMcParametricEnt.h)

```cpp
// GUID: "0000000F-0001-AAAA-AAAA-050B00000000"
struct IMcParametricEnt : public virtual IMcObject {
    virtual HRESULT getParams(OUT mcsExValueArray& params,
                              IN OPTIONAL uint32_t dwFlags = MCPAR_ALL) = 0;
    virtual HRESULT setParams(IN const mcsExValueArray& params,
                              IN OPTIONAL uint32_t dwFlags = MCPAR_ALL) = 0;
};
```

Стандартные имена параметров (MCSParams.h):
```cpp
#define MCPAR_STD_NAME        _T("strTheName")
#define MCPAR_STD_TYPE        _T("strTheType")
#define MCPAR_PART_DESC       _T("strPartDescription")
#define MCPAR_PART_PARTITION  _T("SpecPartition")
```

#### Полный нативный путь (без COM)

```
gpMcNativeGate (McTyp.dll)
  → getMcsIdByNative(mcsWorkID&, int64_t nativeObjectId)
  → mcsWorkID
  → QueryObject(mcsWorkID)
  → IMcObjectPtr
  → QI → IMcParametricEnt*   (прямо ИЛИ через getParentID — см. §11.15)
  → setParams(mcsExValueArray)   ← чистый C++, без IDispatch
```

Использование `NcDbObjectId` как `int64_t` (из McFlattenInterface.h:129):
```cpp
mcsWorkID mcid;
gpMcNativeGate->getMcsIdByNative(mcid, *(int64_t*)&oid);
```

> **Важно**: `getMcsIdByNative` имеет параметр `bAddPairIfNotExist = true` по умолчанию.
> Это означает, что вызов ВСЕГДА возвращает S_OK для любого NcDb-объекта,
> создавая MAPI-обёртку при необходимости. Факт успешного вызова **не доказывает**,
> что объект является параметрическим MCS-элементом.

#### Статус MAPI DLL в nanoCAD 24.1 + MCS (подтверждено 2026-06-25)

| DLL | Статус |
|---|---|
| McTyp.dll | ✅ загружена |
| MechCtl.dll | ✅ загружена |
| MT.dll | ✅ загружена |
| McGeL.dll | ✅ загружена |
| gpMcNativeGate | ✅ не NULL (MAPI активен) |
| gpMcContext | ✅ не NULL |
| MCS_GetContext() | ✅ возвращает тот же адрес что gpMcContext |

> Вывод: при активном Model Studio CS все MAPI DLL уже загружены в процессе nanoCAD. Можно вызывать `getMcsIdByNative` → `setParams` без COM-слоя.

#### Риск ABI

SDK версии 26.0 — nanoCAD 24.1 может использовать более старую MAPI. Перед использованием `setParams` рекомендуется проверить, что `gpMcNativeGate != NULL` и вызов `getMcsIdByNative` не падает. MAPI Import libs для статической линковки (`McTyp.lib`, `MechCtl.lib`) есть в `$(NCadSDK)\lib-x64\`.

### 11.14 Актуальный практический статус (DtmxNrx10, 2026-06-25)

Подтверждено на nanoCAD 24.1 + Model Studio CS:

| Возможность | Статус |
|---|---|
| `IParameters::SetParameter` через vtable (COM) | ✅ работает (DtmxNrx7) |
| Параметр персистирует в DWG | ✅ сохраняется после Ctrl+S + reload |
| GUI диалог Win32 (без MFC) | ✅ работает |
| Кириллица в диалоге и консоли | ✅ флаг `/utf-8 /wd4828` в vcxproj |
| Лог-файл UTF-8 BOM | ✅ читается в Notepad/VSCode |
| MAPI DLL загружены в процессе | ✅ McTyp + MechCtl + MT + McGeL |
| gpMcNativeGate != NULL | ✅ MAPI путь доступен |
| Сборка без COM (чистый MAPI) | ✅ DtmxNrx8-10 компилируются без ошибок |
| getMcsIdByNative → QueryObject | ✅ работает для любого NcDb-объекта |
| QI к IMcEntity / IMcDbEntity | ✅ подтверждено для выбранных объектов |
| QI к IMcParametricEnt напрямую | ⚠️ **не работает** для graphical entities (см. §11.15) |
| getParentID → IMcParametricEnt | 🔲 тестируется в DtmxNrx10 |

Текущий файл плагина: `c:\pdf_ingest\DTMXtest\Scripts\DtmxNrx10.nrx`

### 11.15 MAPI: иерархия объектов и путь к IMcParametricEnt (2026-06-25)

#### Иерархия интерфейсов MAPI

```
IMcObject  (IID: 00000001-0001-AAAA-AAAA-050B00000000)
├── IMcDbObject  (00000002-...)
│   └── IMcDbEntity  (00000003-...)
│       └── IMcEntity  (00000005-...)
│           └── IMcCdEntity  (00000006-...)
│               └── IMcReferenceEntity  ← наследует и IMcEntity, и IMcParametricEnt
│                   (IID закомментирован в SDK: //00000007-...)
└── IMcParametricEnt  (0000000F-0001-AAAA-AAAA-050B00000000)
    └── (реализуется конкретными MCS-объектами)
```

`IMcParametricEnt` — **отдельная ветка**, не часть цепочки `IMcEntity`. Графические примитивы (`IMcEntity`) не QI-руются в `IMcParametricEnt` напрямую.

#### Ключевые IID (из MCSTypes.h, стабильны между версиями SDK)

| Интерфейс | IID |
|---|---|
| `IMcObject` | `00000001-0001-AAAA-AAAA-050B00000000` |
| `IMcDbObject` | `00000002-0001-AAAA-AAAA-050B00000000` |
| `IMcDbEntity` | `00000003-0001-AAAA-AAAA-050B00000000` |
| `IMcEntity` | `00000005-0001-AAAA-AAAA-050B00000000` |
| `IMcCdEntity` | `00000006-0001-AAAA-AAAA-050B00000000` |
| `IMcParametricEnt` | `0000000F-0001-AAAA-AAAA-050B00000000` |
| `IMcReferenceEntity` | закомментирован (`//00000007-...`) — не используй QI |

#### Почему прямой QI к IMcParametricEnt не работает

`IMCS_QI_METHOD_DEFINITION(IMcReferenceEntity, IMcEntity)` генерирует `QueryInterface`, который проверяет только `IID_IMcReferenceEntity` и делегирует `IMcEntity::QueryInterface`. `IID_IMcParametricEnt` в цепочке не проверяется. Итог: даже у объектов `IMcReferenceEntity` (которые наследуют `IMcParametricEnt`) QI по `IID_IMcParametricEnt` возвращает `E_FAIL`.

#### Обходной путь: навигация через родителя

В Model Studio CS **параметрический объект является РОДИТЕЛЕМ** графических примитивов. Алгоритм:

```cpp
// 1. Получить MAPI-объект для выбранного NcDb-entity
mcsWorkID mcid;
pGate->getMcsIdByNative(mcid, *(int64_t*)&oid);
IMcObjectPtr pObj = pGate->QueryObject(mcid);

// 2. Попытаться QI к IMcParametricEnt напрямую
IMcParametricEntPtr pPE = pObj;

// 3. Если не вышло — подняться к родителю
if (!pPE) {
    IMcDbObjectPtr pDbObj = pObj;
    if (pDbObj) {
        const mcsWorkID& parentID = pDbObj->getParentID();
        if (parentID != WID_NULL) {
            IMcObjectPtr pParent = pGate->QueryObject(parentID);
            if (pParent) pPE = pParent;   // QI к IMcParametricEnt
        }
    }
}
```

> Статус на 2026-06-25: алгоритм реализован в DtmxNrx10, тестирование продолжается.

#### Поведение getMcsIdByNative

```cpp
// Подпись:
virtual HRESULT getMcsIdByNative(
    OUT mcsWorkID& id,
    IN int64_t SomeId,
    bool bAddPairIfNotExist = true   // ← создаёт MAPI-обёртку если нет
);
```

`bAddPairIfNotExist = true` → вызов всегда возвращает `S_OK` для любого NcDb-объекта. Факт успешного вызова **не означает** что объект является параметрическим MCS-элементом. Надо проверять QI к `IMcParametricEnt`.

#### Отсутствующие заголовки SDK 26.0 (созданы вручную)

При сборке NRX-плагина с MAPI-заголовками SDK 26.0 ряд файлов отсутствует. Перечень stub-файлов, которые нужно создать в `$(NCadSDK)\include\MAPI\`:

| Файл | Содержимое заглушки |
|---|---|
| `EntityGeometryTypeEnum.h` | `enum EntityGeometryTypeEnum { kMcEntGeomLine, ... }` |
| `McGeomOverlapStatusEnum.h` | `enum McGeomOverlapStatusEnum { kMcGeomOverlap_Unknown, ... }` |
| `mcsGeomEntArray.h` | `class mcsGeomEntArray : public McsArray<McsEntityGeometry> {}` |
| `McsEntityGeometry.h` | `struct McsEntityGeometry { unsigned int color; void transformBy(const mcsMatrix&){}; void setNull(){}; }` |
| `mcsText.h` | `enum McsHorizTextAlignEnum {...}; enum McsVertTextAlignEnum {...}` |
| `mcsHatch.h` | `struct mcsHatch { enum PatternType { kPreDefined, ... }; }` |
| `mcsArrow.h` | `struct mcsArrow {}` |
| `mcsObjGeomRef.h` | `struct mcsObjGeomRef {}` |
| `mcOfsCrvHolder.h` | `struct mcOfsCrvHolder {}` |
| `mcsRepeatedShape.h` | `struct mcsRepeatedShape {}` |
| `mcsMesh.h` | `struct mcsMesh {}` |
| `McGe/mcsSphere.h` | `struct mcsSphere {}` |
| `McGe/mcsCylinder.h` | `struct mcsCylinder {}` |
| `McGe/mcsCone.h` | `struct mcsCone {}` |
| `McGe/mcsTorus.h` | `struct mcsTorus {}` |
| `McGe/mcsTriangle.h` | `struct mcsTriangle {}` |
| `pugixml/pugixml.hpp` | `namespace pugi { struct xml_node {}; struct xml_document {}; }` |

> `mcsGeomEntArray` должен быть именованным классом (не typedef), т.к. `McGe/mcsBoundBlock.h` делает forward-declaration `class mcsGeomEntArray;`.

### 11.16 DtmxNrx11 — углублённый probe для чистого MAPI (2026-06-25)

Следующий эксперимент переведён в отдельную сборку `v11`, чтобы исключить путаницу с уже загруженными NRX-модулями и кешем команд.

Файлы:

- `NrxCpp/DtmxNrx.cpp`
- `NrxCpp/DtmxNrx.vcxproj`
- выходной модуль: `Scripts/DtmxNrx11.nrx`

Команды `v11`:

- `DTMXNRX11PING`
- `DTMXNRX11PROBE`
- `DTMXNRX11SET`

Что добавлено в `DTMXNRX11PROBE`:

- лог `getMcsIdByNative` для каждого выбранного объекта;
- лог `QueryObject(mcid)`;
- проверка интерфейсов на каждом уровне:
  - `IMcDbObject`
  - `IMcDbEntity`
  - `IMcEntity`
  - `IMcParametricEnt` через обычный QI;
- дополнительная проверка `IMcObject::getSpecificKindPtr(__uuidof(IMcParametricEnt))`;
- подъём по цепочке родителей до 6 уровней;
- лог `getParentID()` и `getParent()`;
- лог числа параметров, если найден рабочий `IMcParametricEnt`.

Почему это важно:

- обычный QI к `IMcParametricEnt` у графического MCS-объекта может не сработать из-за множественного/виртуального наследования;
- `getSpecificKindPtr()` — отдельный механизм MAPI для получения корректного адреса нужной ветки объекта без обычного `QueryInterface`;
- если `IMcReferenceEntity` реально сидит в цепочке, то именно `getSpecificKindPtr()` или один из родителей должен дать положительный результат раньше, чем COM-маршрут.

Практический статус `v11`:

- проект успешно собран локально через MSBuild;
- итоговый файл: `Scripts/DtmxNrx11.nrx`;
- следующий шаг тестирования — загрузить `DtmxNrx11.nrx` в nanoCAD/Model Studio и выполнить:
  1. `NETLOAD` / загрузку NRX;
  2. `DTMXNRX11PING`;
  3. выделить один объект `Model Studio`;
  4. `DTMXNRX11PROBE`;
  5. изучить лог `C:\Users\atsarkov\Desktop\dtmx_nrx_log.txt`.

Промежуточный вывод:

- это всё ещё **чистый C++ / MAPI путь без COM**;
- если `DTMXNRX11PROBE` найдёт `IMcParametricEnt` через `getSpecificKindPtr()` или через одного из родителей, тогда `DTMXNRX11SET` сможет перейти к реальной записи параметров тем же чистым маршрутом.

#### Важная совместимость runtime/SDK

При первой сборке `v11` модуль мог не загружаться с ошибкой:

- `Не удается загрузить модуль ... ошибка: Не найдена указанная процедура`

Причина:

- код случайно подтянул импорт `operator==` / `operator!=` для `mcsWorkID` из `mt.dll`;
- в runtime-версии MAPI у пользователя эти экспорты могут отсутствовать;
- из-за этого NRX собирался, но не загружался в nanoCAD.

Практическое правило:

- для `mcsWorkID` в совместимом NRX лучше не использовать ни `== WID_NULL`, ни `!= WID_NULL`;
- safest-вариант — проверять GUID структуры вручную:

```cpp
static bool WidIsNull(const mcsWorkID& wid)
{
    if (wid.ID.Data1 != 0) return false;
    if (wid.ID.Data2 != 0) return false;
    if (wid.ID.Data3 != 0) return false;
    for (int i = 0; i < 8; ++i) {
        if (wid.ID.Data4[i] != 0) return false;
    }
    return true;
}
```

Статус:

- `DtmxNrx11.nrx` пересобран после устранения этого импорта.
- дополнительно выяснено, что `v10` ломался уже на `operator!=` для `mcsWorkID`, то есть проблема началась раньше `v11`.

#### Что оказалось ложным путём

При следующем углублении probe был опробован путь через `IMcObjectsManager` / `gpMcObjManager`, чтобы вытянуть subentity → parent на стороне MAPI.

Практический итог:

- в текущем сочетании SDK/headers этот путь оказался ненадёжным;
- попытка опереться на `isSubent`, `GetParentId`, `kNullSubentType` привела к поломке сборки;
- этот маршрут пока считается **ложным для быстрого исследования** и не должен быть базовым.

Рабочая коррекция:

- не использовать `IMcObjectsManager` как опорный механизм для первого probe;
- использовать только:
  - `gpMcNativeGate`,
  - `getMcsIdByNative`,
  - `QueryObject`,
  - `QueryObjectClassID`,
  - `IsMCSCustomObject`,
  - подъём по **native owner chain** через `AcDbObject::ownerId()`.

#### Почему теперь probe идёт через native owner chain

Реальное наблюдение по логу `DTMXNRX11PROBE`:

- выбранная труба даёт валидный `mcsWorkID`;
- `QueryObject(mcid)` возвращает MAPI-объект;
- объект определяется как:
  - `IMcDbObject`,
  - `IMcDbEntity`,
  - `IMcEntity`,
  - но **не** `IMcParametricEnt`;
- `getParentID()` у него может быть `NULL`.

Вывод:

- пользователь выделяет не обязательно корневой параметрический объект;
- часто это графическое представление / drawable / дочерняя геометрия;
- поэтому для поиска реального параметрического владельца нужно подниматься не только по MAPI-родителю, но и по **цепочке владельцев DWG-объекта**.

Текущий probe теперь делает именно это:

1. берёт выбранный `AcDbObjectId`;
2. открывает `AcDbObject`;
3. логирует `class name`;
4. берёт `ownerId()`;
5. для каждого уровня снова вызывает `getMcsIdByNative`;
6. проверяет:
   - `QueryObjectClassID`,
   - `IsMCSCustomObject`,
   - `ResolveParametric(...)`.

Это сейчас основной правильный вектор для чистого `C++/MAPI` доступа без COM.

#### Что показал реальный лог по `vCSSubSegment`

На реальном запуске `DTMXNRX11PPROBE` по выбранной трубе получено:

- `class=VCSSUBSEGMENT`;
- `QueryObjectClassID = {53534376-6275-6553-676D-656E74000000}`;
- `isMCSCustom=1`;
- на MAPI-стороне объект виден как:
  - `IMcDbObject`,
  - `IMcDbEntity`,
  - `IMcEntity`,
  - но **не** `IMcParametricEnt`;
- `parentID = NULL`.

Подъём по native owner chain дал:

- `nativeDepth=0` → `VCSSUBSEGMENT`;
- `nativeDepth=1` → `BLOCK_RECORD`;
- `nativeDepth=2` → `TABLE`;
- параметрический владелец через owner chain **не найден**.

Практический вывод:

- `vCSSubSegment` в DWG действительно является кастомным MCS-объектом;
- но прямой путь
  - `selected entity -> getMcsIdByNative -> QueryObject -> IMcParametricEnt`
  не срабатывает;
- и путь через `ownerId()` тоже не приводит к параметрическому интерфейсу;
- значит, следующий этап исследования — искать **класс-специфичный интерфейс/адаптер для `vCSSubSegment`**, а не просто ещё глубже идти по generic parent chain.

Это важное отрицательное знание: generic MAPI-подъём по `QueryObject/parent/ownerId` для выбранной трубы пока **не даёт** доступ к `setParams`.

#### Практическая правка по сборке, когда NRX уже загружен

Если `DtmxNrx11.nrx` уже загружен в nanoCAD, linker не может перезаписать файл и падает с `LNK1104`.

Чтобы не упираться в блокировку модуля, в `NrxCpp/DtmxNrx.vcxproj` выходной путь переведён на шаблон:

```xml
<OutputFile>$(OutDir)$(TargetName).nrx</OutputFile>
```

Это позволяет собирать соседние test/probe-варианты, не выгружая основной модуль:

```powershell
MSBuild NrxCpp\DtmxNrx.vcxproj /t:Build `
  /p:Configuration="Release NCAD" `
  /p:Platform=x64 `
  /p:TargetName=DtmxNrx11_probe
```

Результат:

- основной `Scripts/DtmxNrx11.nrx` можно оставить загруженным;
- тестовая сборка уходит, например, в `Scripts/DtmxNrx11_probe.nrx`.

### 11.17 DtmxNrx12 — новый чистый C++ путь через `UnitsCS.nrx` (2026-06-25)

После тупика на generic `MAPI`-цепочке найден следующий, более сильный вектор:

- не искать `IMcParametricEnt` у выбранного `vCSSubSegment`;
- брать **product-native API** из `UnitsCS.nrx`;
- входить в parametric layer через:
  - `linCSParametricWrapper::getParametricInterface(NcDbObject*)`;
- дальше работать с:
  - `linCSParametricSolidBase::getRootElementP()`;
  - `linCSParametricSolidBase::setParameter(wchar_t const*, wchar_t const*, wchar_t const*, wchar_t const*)`;
  - `linCSParametricSolidBase::setRootElementP(CElement*)`.

Подтверждённые native-экспорты:

- `?getParametricInterface@linCSParametricWrapper@@SAPEAVlinCSParametricSolidBase@@PEAVNcDbObject@@@Z`
- `?getRootElementP@linCSParametricSolidBase@@QEAAPEAVCElement@@XZ`
- `?setRootElementP@linCSParametricSolidBase@@QEAAXPEAVCElement@@@Z`
- `?setParameter@linCSParametricSolidBase@@QEAAXPEB_W000@Z`
- дополнительно:
  - `?ursGetObjectParameters@@YAHPEBVNcDbObject@@AEAVCElement@@I@Z`
  - `?ursSetObjectParameters@@YAHPEAVNcDbObject@@AEAVCElement@@_N@Z`
  - `?GetCelementFromIdWritable@@YAPEAVCElement@@AEBVNcDbObjectId@@AEAV?$CSCPtr@VNcDbObject@@@@_N@Z`

Практический смысл:

- это уже не `COM` и не `COM + .NET`;
- это **in-process native C++ путь внутри DWG / Model Studio runtime**;
- он опирается не на SDK-обёртки верхнего уровня, а на экспортируемые функции продуктовых модулей.

Что собрано в `v12`:

- файл проекта: `NrxCpp/DtmxNrx.vcxproj`
- исходник: `NrxCpp/DtmxNrx.cpp`
- выходной модуль: `Scripts/DtmxNrx12.nrx`

Новые команды:

- `DTMXNRX12UPROBE`
- `DTMXNRX12USET`

Что делает `DTMXNRX12UPROBE`:

1. загружает `UnitsCS.nrx`;
2. резолвит native-экспорты через `GetProcAddress`;
3. просит выбрать один объект Model Studio;
4. открывает `NcDbObject` на запись;
5. вызывает `getParametricInterface(...)`;
6. логирует указатель на `linCSParametricSolidBase`;
7. логирует указатель на `root element`.

Что делает `DTMXNRX12USET`:

1. загружает тот же native API;
2. просит выбрать один объект Model Studio;
3. просит ввести значение для `PART_TAGNUMBER` (по умолчанию `DTMX`);
4. вызывает:
   - `setParameter("PART_TAGNUMBER", "", value, "")`;
5. затем повторно вызывает `setRootElementP(...)` для текущего root;
6. делает `REGEN`.

Почему это важно:

- это первый реально собранный маршрут, который пытается писать `PART_TAGNUMBER` **чисто через native C++**;
- он полностью обходит:
  - `IDispatch`,
  - `UnitsCSCom.Interop.dll`,
  - внешние `exe`,
  - cross-process `COM`.

Статус на текущий момент:

- `Scripts/DtmxNrx12.nrx` успешно собран;
- проект переведён на доступный toolset `v143`;
- `TargetName` изменён на `DtmxNrx12`, чтобы не перетирать старые `v11`-сборки;
- запись через `v12` **ещё нужно подтвердить живым запуском внутри nanoCAD/Model Studio**.

Важный практический вывод:

- после `11.16` правильный следующий шаг — не углублять generic `MAPI`;
- правильный шаг — идти в **class-specific / product-specific native API** (`UnitsCS.nrx`, `msPipeNetworks.nrx`, `linCSParametric...`).

Что пока не доказано:

- что именно четверка аргументов `setParameter(name, a2, a3, a4)` использована в идеальном порядке для `PART_TAGNUMBER`;
- что одного `setRootElementP(currentRoot)` достаточно для commit внутрь DWG;
- что для `vCSSubSegment` не нужен ещё один class-specific wrapper поверх `linCSParametricSolidBase`.

Поэтому `v12` надо считать не финальным решением, а **правильным чистым C++ probe следующего поколения**.

#### Уточнение по состоянию `v12` после живых запусков

По результатам последующих запусков внутри nanoCAD/Model Studio уточнено следующее:

- `UnitsCS.nrx` **реально загружается**;
- native-экспорты успешно резолвятся;
- критичный экспорт записи найден именно как:
  - `?SetParameter@linCSParametricSolidBase@@QEAAXPEB_W000@Z`
- вариант с `?setParameter...` был ложным следом и давал `nullptr`;
- `getParametricInterface(...)` и `getRootElementP(...)` работают;
- проблема сейчас не в загрузке API, а в **безопасном commit native-записи**.

Подтверждённый диагностический вывод для рабочей probe-версии:

- `getParametricInterface` — адрес найден;
- `getRootElementP` — адрес найден;
- `setRootElementP` — адрес найден;
- `SetParameter` — адрес найден.

Практический вывод:

- гипотеза `UnitsCS API not available` больше не актуальна для актуальной `D`-ветки;
- чистый native путь **подтверждён на уровне входа в parametric layer**;
- текущий риск сосредоточен в шаге записи/фиксации изменений в DWG.

#### Почему падал `DTMXNRX12DUSET`

Отдельно подтверждено:

- прямой вызов native `SetParameter(...)` в текущей реализации может валить nanoCAD;
- интерактивный выбор через `acedEntSel(...)` тоже является подозрительной точкой и на части запусков валит хост ещё на этапе выбора объекта;
- значит проблема не в самом экспорте, а в одном из пунктов:
  - неверный контекст объекта;
  - неверная семантика аргументов;
  - нужен другой commit-маршрут после изменения параметра;
  - для `vCSSubSegment` нужен не только `linCSParametricSolidBase`, а более специфический wrapper.

Из-за этого команда `DTMXNRX12DUSET` временно переведена в **safe mode**:

- ручной клик-выбор убран;
- команда работает только по заранее выделенному объекту (`PICKFIRST`);
- в следующей safe-итерации selection-цепочка расширена до `I` → `P` → `ssget prompt`, так как на части запусков implied selection не передавался в custom-команду;
- объект открывается;
- `parametric interface` и `root element` получаются;
- запись **не выполняется**;
- команда завершает работу без native write-call, чтобы не провоцировать падение.

Актуальная безопасная сборка для этой стадии:

- `Scripts/DtmxNrx12g.nrx`
- `Scripts/DtmxNrx12h.nrx` — safer variant без `acedEntSel`, только `PICKFIRST`
- `Scripts/DtmxNrx12i.nrx` — safer variant с fallback `Previous` и `ssget`

Поведение safe-версии:

- `DTMXNRX12DUPROBE` — рабочая диагностическая команда;
- `DTMXNRX12DUSET` — no-op проверка тракта, без реальной записи.

#### Правильный следующий шаг по чистому C++

Чтобы добить путь без `COM`, дальше нужно исследовать уже **не загрузку `UnitsCS`**, а именно механизм commit:

- `ursGetObjectParameters(...)`;
- `ursSetObjectParameters(...)`;
- возможный copy/clone сценарий через `CElement`;
- class-specific API поверх `vCSSubSegment`;
- соседние product-модули, например `msPipeNetworks.nrx`, если именно они содержат write-safe слой для трубопроводных элементов.

То есть на текущем этапе:

- `COM`-путь — уже рабочий;
- `.NET + COM`-путь — уже рабочий;
- `pure C++ native` — **частично подтверждён**, вход найден, безопасная запись ещё не доведена до результата.

#### Новые подтверждённые факты по live-отладке через COM + NRX

Во время следующей серии прогонов удалось автоматизировать NRX-команды через уже открытый `nanoCAD`:

- подключение к живому хосту через `GetActiveObject("nanoCAD.Application")` работает;
- у `ActiveDocument` доступен `SendCommand(...)`;
- selection для NRX надёжнее всего передавать не через COM `PickfirstSelectionSet`, а через:
  - `LISP handent + ssadd + sssetfirst`;
- перед автоматическим запуском команд нужно проверять, не висит ли уже активная команда:
  - `CMDACTIVE`
  - `CMDNAMES`

Практически подтверждено:

- если в `CMDNAMES` висит чужая команда (например `LENGTHEN`), новые `SendCommand(...)` могут тихо не отрабатывать;
- двойной `Esc` (`char(3), char(3)`) снимает зависшую команду и возвращает `CMDACTIVE = 0`.

#### Подтверждённый результат по `SetParameter(...)`

Команда экспериментального класса `DTMXNRX12XSETP1` была успешно доведена до реального вызова:

- объект выбирается автоматически;
- `getParametricInterface(...)` возвращает валидный указатель;
- `getRootElementP(...)` возвращает валидный `root`;
- `SetParameter(...)` **возвращается без падения**.

Подтверждённый лог:

- `calling SetParameter(PART_TAGNUMBER, '', 'DTMX', '')`
- `SetParameter returned`

После этого COM-проверка выбранного объекта показала:

- `Name = PART_TAGNUMBER`
- `Value = ''`
- `Comment = 'DTMX'`

Практический вывод:

- третий строковый аргумент `SetParameter(name, arg2, arg3, arg4)` для `PART_TAGNUMBER` попадает не в `Value`, а в `Comment`;
- значит основной барьер уже не в падении native-вызова, а в **раскладке аргументов и/или в commit-механике**.

#### Как вернуть кириллицу в NRX-исходниках и логах

Если вместо русских строк появляются `Р...`, `С...`, `вЂ...`, причина почти всегда в перекодировке исходника при сохранении.

Надёжные правила:

1. Исходники `.cpp/.h/.vcxproj` держать в **UTF-8**.
2. В проекте оставлять флаг компилятора:

```xml
<AdditionalOptions>/utf-8 /wd4828 %(AdditionalOptions)</AdditionalOptions>
```

3. Не переписывать C++-файлы командами/инструментами, которые могут молча сменить кодировку.
4. Для автоматических правок prefer:
   - `apply_patch`,
   - редактор с явным сохранением `UTF-8`.
5. Для диагностических NRX-строк безопаснее использовать ASCII, если русские сообщения не критичны.
6. Логи писать в `UTF-8 BOM`, чтобы Notepad корректно открывал кириллицу.

Практический симптом:

- если комментарии/литералы в самом `NrxCpp/DtmxNrx.cpp` уже выглядят как `РџС...`, значит текст в файле уже был сохранён в неверной кодировке, и один только `/utf-8` это не исправит — нужно перезаписать испорченные строки корректным текстом в UTF-8.

#### Двойная перекодировка UTF-8→cp1251→UTF-8 (AI-артефакт)

**Симптом:** в файле визуально всё выглядит нормально (Read-тул и некоторые терминалы показывают читаемые буквы), но в диалоге nanoCAD видны иероглифы `РџР°СЂ...` вместо `Параметр`. Проверка raw-байтов показывает `d0 a0 d1 9f` вместо правильных `d0 9f` для `П`.

**Причина:** AI-инструмент (или редактор) читал файл как Windows-1251, брал его байты как есть и сохранял их в UTF-8. Каждый байт оригинального UTF-8 записался как отдельный Windows-1251-символ с повторным UTF-8-кодированием. Байт `D0` (Р в cp1251) → `D0 A0`; байт `9F` (џ в cp1251) → `D1 9F`. Итого один символ П = `D0 9F` превратился в два символа `Р` + `џ` = `D0 A0 D1 9F`.

**Диагностика:** запустить Python — если `Match: False`, файл повреждён:

```python
with open("DtmxNrx.cpp", "rb") as f:
    raw = f.read()
correct = "Параметр:".encode("utf-8")   # d0 9f d0 b0 d1 80 ...
idx = raw.find(b'L"', raw.find(b"STATIC"))
chunk = raw[idx+2:idx+2+len(correct)]
print(f"Match: {chunk == correct}")     # False = повреждён
```

**Быстрый фикс (Python, обратная перекодировка через cp1251):**

```python
import re

def fix_double_encoded(s):
    """Восстановить: cp1251-байты были записаны как UTF-8 символы.
    Закодировать в cp1251 → расшифровать как UTF-8 → оригинал."""
    try:
        return s.encode("cp1251").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None   # строка не повреждена, пропустить

with open("DtmxNrx.cpp", encoding="utf-8") as f:
    text = f.read()

for m in re.finditer(r'L"([^"\\]*(?:\\.[^"\\]*)*)"', text):
    fixed = fix_double_encoded(m.group(1))
    if fixed and fixed != m.group(1):
        text = text.replace(m.group(1), fixed, 1)

with open("DtmxNrx.cpp", "w", encoding="utf-8") as f:
    f.write(text)
```

Скрипт безопасен: `fix_double_encoded` возвращает `None` для строк без повреждений (корректный UTF-8 не может быть закодирован в cp1251 и расшифрован обратно без ошибки).

**Профилактика:** при автоматической правке C++-файлов всегда открывать с явным `encoding="utf-8"` и писать обратно с тем же `encoding="utf-8"`. Не использовать PowerShell `Set-Content` (по умолчанию UTF-16 LE).

---

### 11.18 UnitsCS vtable — единственный рабочий путь для объектов Model Studio CS (DtmxNrx18, 2026-06-25)

#### Ключевой вывод

Объекты Model Studio CS в DWG (`vCSSubSegment`, `vCSNode` и подобные) **не реализуют `IMcParametricEnt`** через MAPI:

```
depth=0 | peQI=0 peKind=0 parentID=NULL  → ResolveParametric=null
```

Это значит:
- `getMcsIdByNative` → S_OK (MAPI знает об объекте)
- `QueryObject` → валидный `IMcObjectPtr`
- Но `QI(IMcParametricEnt)` = null, `getSpecificKindPtr` = null, `parentID` = null
- `setParams/getParams` через MAPI **недоступны** для этих объектов

Единственный путь — vtable `linCSParametricSolidBase` из `UnitsCS.nrx`.

#### Экспортированные функции UnitsCS.nrx (x64, подтверждены)

```cpp
// Factory: AcDbObject* → linCSParametricSolidBase*
"?getParametricInterface@linCSParametricWrapper@@SAPEAVlinCSParametricSolidBase@@PEAVNcDbObject@@@Z"

// Корневой элемент (нужен для чтения значений)
"?getRootElementP@linCSParametricSolidBase@@QEAAPEAVCElement@@XZ"              // → CElement*

// Перечисление
"?GetParamsCount@linCSParametricSolidBase@@QEAAHXZ"                            // → int
"?GetParameter@linCSParametricSolidBase@@QEBAPEAVCParam@@H@Z"                  // (pIface, int i) → CParam*

// Чтение значения по имени
"?SubEnt_ParameterLPCSTR@linCSParametricSolidBase@@SAPEB_WPEBVCElement@@PEB_W_N1@Z"
//   (CElement* pRoot, const wchar_t* name, bool isExpr, bool isTemplate) → const wchar_t*

// Запись параметра
"?SetParameter@linCSParametricSolidBase@@QEAAXPEB_W000@Z"
//   (pIface, name, value, comment, group) — все wchar_t*
```

#### Структура CParam (определено через VirtualQuery-зондирование)

```
CParam (x64, layout подтверждён для UnitsCS.nrx из nanoCAD 24.1 + MCS):

  offset  0:  vtable-указатель (8 байт)
              → при чтении как wchar_t* → иероглифы (байты указателя на .text)
  offset  8:  CStringW m_strName  → имя параметра (русский текст)
  offset 16:  CStringW m_strValue → текущее значение
  offset 24+: прочие поля
```

**Причина иероглифов**: `*(wchar_t**)pCParam` (offset 0) читает vtable-адрес как указатель на строку. В памяти по vtable-адресу лежат 8-байтные указатели на виртуальные функции; первые 2 байта каждого — как правило, `32 хх` (младшие байты адреса .text секции DLL), что даёт символы вроде `㈐`. Правильное смещение имени — **8**.

#### SafeWcharPtrAt — безопасное чтение через VirtualQuery

```cpp
static const wchar_t* SafeWcharPtrAt(const void* pBase, int byteOffset)
{
    const void* pField = (const char*)pBase + byteOffset;
    MEMORY_BASIC_INFORMATION mbi = {};
    if (!::VirtualQuery(pField, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT) return nullptr;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return nullptr;
    const wchar_t* p = *(const wchar_t* const*)pField;
    if (!p) return nullptr;
    if (!::VirtualQuery(p, &mbi, sizeof(mbi)) || mbi.State != MEM_COMMIT) return nullptr;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return nullptr;
    return p;
}
```

Никакого `__try/__except` — `VirtualQuery` безопасно работает на любом указателе, не вызывает AV.

#### ProbeCParamNameOffset — автоопределение смещения имени

```cpp
static int ProbeCParamNameOffset(void* pCParam)
{
    for (int off : {0, 8, 16, 24}) {        // первый проход: ищем кириллицу
        const wchar_t* p = SafeWcharPtrAt(pCParam, off);
        if (!p) continue;
        bool hasCyr = false, allOk = true; int len = 0;
        for (; len < 200 && p[len]; ++len) {
            wchar_t c = p[len];
            if (c < 0x20 || c == 0xFFFE) { allOk = false; break; }
            if (c >= 0x0400 && c <= 0x04FF) hasCyr = true;
        }
        if (allOk && hasCyr && len > 0) return off;
    }
    return 8; // fallback: vtable@0, name@8
}
```

Вызывается один раз для первого `CParam` текущего объекта, результат используется для всех остальных (все `CParam` одного класса имеют одинаковый layout).

#### Полный цикл: чтение параметров

```cpp
AcDbObject* pDbObj = nullptr;
acdbOpenAcDbObject(pDbObj, oid, AcDb::kForRead);
void* pIface = api.getParametricInterface((void*)pDbObj);
int count    = api.getParamsCount(pIface);       // например 29
CElement* pRoot = api.getRootElementP(pIface);

void* pC0  = api.getParameterByIndex(pIface, 0);
int nameOff = ProbeCParamNameOffset(pC0);        // обычно 8

for (int i = 0; i < count; ++i) {
    void* pCParam = api.getParameterByIndex(pIface, i);
    const wchar_t* name = SafeWcharPtrAt(pCParam, nameOff);
    if (!name || !name[0]) continue;

    const wchar_t* val = api.subEntParameterStr(pRoot, name, false, false);
    // name = L"Диаметр условный", val = L"500"
}
pDbObj->close();
```

#### Полный цикл: запись параметра

```cpp
AcDbObject* pDbObj = nullptr;
acdbOpenAcDbObject(pDbObj, oid, AcDb::kForWrite);
void* pIface = api.getParametricInterface((void*)pDbObj);
api.setParameter4(pIface, L"Диаметр условный", L"600", L"", L"");
pDbObj->close();
// параметр персистирует в DWG (сохраняется через Ctrl+S)
```

#### Итоговый статус (DtmxNrx18, 2026-06-25)

| Возможность | Статус |
|---|---|
| Перечисление всех параметров MCS-объекта | ✅ `EnumParamsViaNative` → 29 пар. |
| Чтение текущего значения | ✅ `subEntParameterStr(pRoot, name)` |
| Запись / обновление параметра | ✅ `setParameter4(pIface, name, val, "", "")` |
| Множественное выделение (общие параметры) | ✅ пересечение `std::map`, `<разные>` |
| Win32 GUI: combo + edit + Apply / Cancel | ✅ кириллица, системный шрифт |
| MAPI `IMcParametricEnt` для этих объектов | ❌ недоступен (см. диагностику выше) |
| Безопасное чтение CParam без SEH | ✅ `VirtualQuery` вместо `__try` |

---

### 11.19 Перспективы работы с объектами Model Studio CS из NRX (2026-06-25)

После того как установлен полный цикл чтения/записи параметров через `linCSParametricSolidBase`, открывается широкий спектр автоматизации непосредственно в DWG без внешних инструментов.

#### Что уже работает (базовый слой)

```
AcDbObject* (любой MCS-элемент в DWG)
    │
    └─ getParametricInterface()  ──→  linCSParametricSolidBase*
            │
            ├─ GetParamsCount()          → количество параметров
            ├─ GetParameter(i) + offset8 → имя параметра (CStringW)
            ├─ SubEnt_ParameterLPCSTR()  → текущее значение
            └─ SetParameter()            → запись нового значения
```

#### Ближайшие задачи (легко реализовать поверх базового слоя)

| Задача | Механизм |
|--------|----------|
| Пакетное изменение параметра на группе объектов | выборка `acedSSGet` → цикл `SetParameter` |
| Поиск элементов по значению параметра | цикл по всем объектам чертежа `AcDbBlockTableRecord` → `getParametricInterface` → `SubEnt_ParameterLPCSTR` |
| Выделение найденных элементов | `acedSSAdd` → `acedRedraw` |
| Экспорт всех параметров в CSV | цикл по выборке → `fwprintf` |
| Импорт параметров из CSV | построчный разбор → `SetParameter` для каждого объекта |
| Проверка/валидация (аудит параметров) | сравнение значений с эталонным списком |
| Синхронизация параметров между двумя элементами | читаем из источника → пишем в приёмник |

#### Более сложные задачи

- **Работа с иерархией** — у Model Studio CS есть родительские/дочерние объекты (трубопровод → фитинги → опоры). Через `SubEnt_ParameterLPCSTR` с `isExpr=true` можно читать выражения вместо вычисленных значений. Это позволяет понять зависимости между параметрами.

- **Обращение к БД через параметры** — объекты MCS хранят `idObject` (или аналог) — идентификатор в базе данных проекта. Получив его через параметр, можно запрашивать ссылочные данные (PDM, PLM, реестр трубопроводов).

- **Создание новых параметров** — `SetParameter(name, value, comment, group)` с новым именем создаёт пользовательский параметр. Можно добавлять расчётные или справочные атрибуты прямо в DWG без изменения шаблона MCS.

- **Интеграция с внешними системами** — NRX работает in-process в nanoCAD. Команда может читать данные из файла, REST API, ODBC и массово обновлять параметры объектов по результату запроса.

- **Мониторинг изменений** — через NRX-реакторы (`AcDbDatabaseReactor`, `AcEditorReactor`) можно перехватывать изменения объектов и автоматически обновлять зависимые параметры.

#### Ограничения, которые нужно учитывать

- `setParameter4` всегда получает строки (`wchar_t*`). Числа нужно форматировать самостоятельно (`swprintf_s`).
- Layout `CParam` (vtable@0, name@8) установлен для UnitsCS.nrx из nanoCAD 24.1. При обновлении MCS нужно повторно проверить `ProbeCParamNameOffset`.
- Открытие объекта `kForWrite` блокирует его на время операции — для пакетной записи на сотнях объектов нужен транзакционный подход или минимизация времени удержания блокировки.
- `SubEnt_ParameterLPCSTR` возвращает указатель, управляемый объектом pRoot. Если pRoot закрыт, указатель невалиден — копировать в `std::wstring` немедленно.

---

### 11.20 Текущая задача: исследование иерархии параметров (DtmxNrx19–20)

#### Задача

Убедиться в точности чтения параметров через vtable `linCSParametricSolidBase` для реальных объектов Model Studio CS. Для этого нужно:

- видеть **все параметры** выбранного элемента с актуальными значениями;
- видеть параметры **родительского объекта** (если есть по MAPI);
- видеть параметры **других MCS-объектов в том же NcDb-блоке** (потенциальные дочерние / смежные элементы).

#### Что сделано (DtmxNrx19–20)

**Кнопка "Лог →файл" в диалоге** (`IDC_DUMP_BTN`):
- Появляется слева от "Применить" в существующем диалоге `DTMXNRX18SET`.
- При нажатии: пишет в `dtmx_nrx_log.txt` все параметры и значения, показанные в диалоге (общие параметры выделенных объектов). Диалог не закрывается.

**Команда `DTMXNRX19DUMP`** — автономный полный дамп:
```
Для каждого выбранного объекта:
  1. Прямые параметры (vtable EnumParamsViaNative)
  2. MAPI-родитель: getMcsIdByNative → getParentID → если не NULL → дампить его параметры
  3. Блок-скан: пробежать по всем сущностям owner-блока (до 50),
     найти те что имеют getParametricInterface → дампить их параметры
```

**Вспомогательная функция `DumpMcsObjectById(api, oid, prefix)`**:
```cpp
AcDbObject* pObj = nullptr;
acdbOpenAcDbObject(pObj, oid, kForRead);
void* pIface = api.getParametricInterface(pObj);
if (!pIface) { pObj->close(); return 0; }
auto ps = EnumParamsViaNative(api, pIface);  // ← pObj должен быть открыт!
pObj->close();                                // ← закрыть ПОСЛЕ энумерации
```

#### Критический баг (исправлен в DtmxNrx20)

`pObj->close()` вызывался **до** `EnumParamsViaNative`. В результате:
- `getParametricInterface(pObj)` возвращает `pIface` корректно;
- `getRootElementP(pIface)` после `close()` возвращает невалидный `pRoot` (или null);
- `subEntParameterStr(pRoot, name, ...)` возвращает null → `dispValue = ""`.

**Симптом:** в логе видны имена параметров, но все значения пустые.

**Правило:** `pObj` обязан оставаться открытым всё время пока используется `pIface` или любой результат vtable-вызова на нём. Закрывать только после завершения всех vtable-операций.

#### Текущий статус (DtmxNrx20)

| Что | Статус |
|-----|--------|
| Параметры выбранного объекта | ✅ имена + значения |
| MAPI-родитель | ✅ проверяется; для root-элементов = NULL |
| Блок-скан (до 50 соседних объектов) | ✅ имена + значения |
| Пустые значения в дампе | ✅ исправлено в DtmxNrx20 |

#### Новое рабочее направление: дерево `CElement` через `mstudioData.dll` (2026-06-25)

Ключевое уточнение:

- `UnitsCS.nrx` **не** экспортирует методы `CElement` / `CParamsOwner` / `CParam`;
- `UnitsCS.nrx` экспортирует только мост в параметрику:
  - `getParametricInterface`
  - `getRootElementP`
  - `SubEnt_ParameterLPCSTR`
- методы дерева и параметров берутся из `mstudioData.dll`.

Подтверждённые экспорты `mstudioData.dll`:

- `CElement::GetChildCount`
- `CElement::GetChild(index)`
- `CElement::GetName`
- `CElement::GetId`
- `CElement::GetLevel`
- `CParamsOwner::GetParamsCount`
- `CParamsOwner::GetParameter(index)`
- `CParam::getName`
- `CParam::getValue`
- `CParam::getComment`

Это дало первый **чистый C++** положительный результат по дереву геометрии Model Studio в DWG.

#### Команда `DTMXNRX20TREE`

Новая команда в `NrxCpp/DtmxNrx.cpp`:

1. Берёт выбранный объект nanoCAD/Model Studio.
2. Через `UnitsCS.nrx` получает `pIface` и `CElement* root`.
3. Через `mstudioData.dll` обходит дерево `CElement`.
4. Для каждого узла пишет:
   - `ptr`
   - `id`
   - `level`
   - `childCount`
   - `name`
5. Для каждого узла читает параметры через `CParamsOwner`.

Практический результат на выбранной трубе (`VCSSUBSEGMENT`):

- корневой узел: `name=3D`, `childCount=2`
- дочерние узлы: два `CONE`
- на дочерних узлах успешно прочитаны геометрические параметры:
  - `Height`
  - `Radius`
  - `Radius2`
  - `DirectionX/Y/Z`
  - `OrientationX/Y/Z`
  - `StartPointX/Y/Z`
  - `Visible`
  - `WallThickness`
  - и др.

Пример вывода:

```text
[NODE] ptr=... id=0 level=0 childCount=2 name=3D
  [P] MIRROR_ELEMENTS = 0
  [CHILD] index=0 ...
  [NODE] ... name=CONE
    [P] Height = 4805.699999999998
    [P] Radius = 10
    [P] Visible = 1
```

#### Важный вывод

Теперь у нас есть **два разных слоя данных** в DWG:

1. **Параметры интерфейса Model Studio / Part-параметры**  
   Путь: `UnitsCS.nrx` → `linCSParametricSolidBase`  
   Примеры: `PART_TAGNUMBER`, `PART_TYPE`, `PART_NAME`.

2. **Внутреннее дерево геометрии / children**  
   Путь: `UnitsCS.nrx` → `getRootElementP()` → `mstudioData.dll::CElement`  
   Примеры: `CONE`, `Height`, `Radius`, `Visible`.

Это не одно и то же.  
`PART_*` живут не в дочерних `CONE`, а в другом слое параметрики объекта.

#### Что это значит для следующего шага

Рабочая гипотеза теперь такая:

- если цель — **собрать всё о выделенном MS-элементе**, нужен объединённый дамп:
  1. `UnitsCS`-параметры верхнего уровня;
  2. `CElement`-дерево и параметры всех children.

- если цель — **менять геометрию children**, путь уже найден: `CElement/CParamsOwner`;
- если цель — **менять `PART_*`**, надо дальше добивать именно слой `linCSParametricSolidBase`, а не children.

#### DtmxNrx20: подтверждённый доступ к правой панели свойств Model Studio через MAPI (2026-06-25)

Новый подтверждённый рабочий путь:

- `gpMcNativeGate`
- `getMcsIdByNative(...)`
- `QueryObject(mcsWorkID)`
- приведение к `IMcDbObject`
- далее:
  - `getProperties(...)`
  - `getProperty(...)`
  - `getPropertyInfo(...)`

Это дало **реальные значения**, совпадающие с правой частью окна `Параметры объекта`.

Ключевой вывод:

- `IMcDbObject` в MAPI реально является `IMcPropertySource`;
- именно этот путь даёт не только имена, но и пользовательские значения из UI;
- это **другой слой**, не совпадающий с `CElement`-геометрией и не совпадающий с прямым `PART_*`-дампом через `UnitsCS`.

Примеры реально прочитанных значений:

- `Параметры изделия.Наименование изделия = Труба полипропиленовая`
- `Параметры изделия.Обозначение / Модель = PP-R SDR 6/S 2.5 - 20x3.4 PN 20`
- `Параметры изделия.Нормативный документ = ГОСТ 32415-2013`
- `Параметры изделия.Материал = Полипропилен`
- `Спецификация.Группа по спецификации = Трубы`
- `Дополнительные параметры.Тип изделий = Труба`

Это первый подтверждённый **чистый C++** путь, который возвращает именно значения из UI, а не пустой список имён.

#### Три слоя данных, которые нельзя смешивать

По состоянию на сейчас в DWG у объекта Model Studio подтверждены три разных слоя:

1. **`UnitsCS` / `linCSParametricSolidBase`**  
   Даёт `PART_*`, `BOM_*`, `PIPE_*` и т.п.  
   Проблема: для многих параметров имя видно, но значение пустое.

2. **`MAPI / IMcPropertySource`**  
   Даёт то, что реально видно справа в `Параметры объекта`.  
   Пример: `Наименование изделия`, `Материал`, `Группа по спецификации`.

3. **`CElement` / `mstudioData.dll`**  
   Даёт геометрическое дерево `3D -> CONE -> ...` и параметры `Height`, `Radius`, `Visible`.

Это принципиально важно:  
если задача — вывести **все поля справа**, нужно идти через `IMcPropertySource`;  
если задача — пройти **геометрию children**, нужно идти через `CElement`;  
если задача — работать с `PART_*`, это отдельный слой.

#### Что НЕ сработало для иерархии UI

Подтверждённо не сработали следующие пути:

- `ownerId()` native DWG-цепочки  
  Даёт только:
  - `VCSSUBSEGMENT -> BLOCK_RECORD -> TABLE`
  - это **не** дерево UI слева.

- `IMcDbObject::getChildrenIDs()` на raw `VCSSUBSEGMENT`  
  На выбранной трубе падает с:
  - `seh=0xC0000005`
  - значит левое дерево свойств не лежит напрямую в обычных `children` этого MAPI-объекта.

- путь только через `CElement`
  Даёт только геометрию (`3D`, `CONE`, ...), но **не** ловит узлы UI вроде:
  - `Параметризация`
  - `Порт1`
  - `Порт2`
  - `Список работ`

#### Новые зацепки для следующего исследования

После чтения SDK зафиксированы самые перспективные направления:

1. **`McPropertyInfo`**
   - смотреть `ctrlType`
   - смотреть `propType`
   - смотреть `pCustomDialog`
   - смотреть `values`

   Особенно интересны свойства-заглушки:
   - `Трубопровод.Параметры трубопровода = <Свойства Осевой>`
   - `Компонент.Параметры компонента = <Свойства объекта>`
   - `Изоляция.Изоляция = <Свойства Изоляции>`

   Гипотеза: именно они могут быть входом в подчинённые наборы свойств / вложенные редакторы.

2. **`IMcReferenceExtension`**
   - в SDK есть отдельный интерфейс зависимостей/ссылок;
   - нужно проверить, не сидят ли `Порт1/Порт2/изоляция/список работ` в ссылочной модели, а не в `children`.

3. **`getChildrenIDsEx(...)`**
   - в SDK есть расширенный вариант с фильтрами:
     - `kChildrenSysFilter_All`
     - `kChildrenSysFilter_AllDeep`
     - `kChildrenSysFilter_UseGetObject`
   - нужно отдельно проверить, не даст ли он другой результат, чем `getChildrenIDs()`.

#### Техническая заметка по тестированию NRX

На этом этапе было важно разделить две вещи:

- **сборка NRX** — проходит успешно;
- **горячая перезагрузка в nanoCAD через COM** — нестабильна.

Практический вывод:

- `DtmxNrx20.nrx` собирается нормально;
- но автоматическая загрузка/перезагрузка через COM (`LoadArx`, `LoadModule`) может вернуть `E_FAIL`, даже когда сам файл корректен;
- для отладки лучше опираться на:
  - успешную сборку,
  - лог `dtmx_nrx_log.txt`,
  - и ручную/командную загрузку NRX внутри nanoCAD, если COM начинает вести себя нестабильно.

#### COM → native: что удалось доказать по `UnitsCSCom.nrx` (ветка `research/com-native-path`, 2026-06-25)

Новый отдельный вектор исследования:

- не идти “вслепую” только через MAPI/NRX;
- а разбирать **рабочий COM-слой**, который уже умеет писать `PART_TAGNUMBER`;
- от него восстанавливать внутренний native-маршрут.

##### 1. `UnitsCSCom.nrx` — это реальная ATL COM-обёртка, а не просто typelib

Подтверждено через `dumpbin /exports`:

- `UnitsCSCom.nrx` экспортирует:
  - `DllGetClassObject`
  - `DllRegisterServer`
  - `DllUnregisterServer`
- внутри есть реальные COM-классы:
  - `CoElement`
  - `CoElementStandalone`
  - `CoElementStandaloneEx`
  - `CoElementPersistent`
  - `CoElementTemporary`
  - `CoElementAdapter`
  - `CoElementAdapterT<linCSDataObject>`
  - `CoElementAdapterT<linCSNode>`
  - `CoElementAdapterT<linCSCollision>`

Практический вывод:

- `COM`-слой не является внешним “скриптовым костылём”;
- это **родная in-process обёртка продукта**, сидящая прямо поверх внутренних классов Model Studio.

##### 2. Подтверждённые coclass / typelib регистрации

Из реестра подтверждено:

- `TypeLib = {1AE1985C-5D87-4E89-8E67-068628FC3CD6}`
  - `Model Studio Objects 1.0 Type Library`
- `CLSID Element Class = {45ABD4AA-0795-42DF-92CC-592C757A8443}`
  - `ProgID = MDSUnits.Element.1`
  - `VersionIndependentProgID = MDSUnits.Element`
  - `InprocServer32 = ...\UnitsCSCom.nrx`
- `CLSID Parameters Class = {8AFB3213-BB2E-447E-8B85-A12F02C0FD67}`
  - `ProgID = MDSUnits.Parameters.1`
  - `VersionIndependentProgID = MDSUnits.Parameters`
  - `InprocServer32 = ...\UnitsCSCom.nrx`

То есть:

- `IElement` и `IParameters` реально живут в `UnitsCSCom.nrx`;
- это **in-process COM**, а не внешняя служба и не cross-process automation.

##### 3. DISPIDs typed COM-слоя уже известны

Через reflection по `Artifacts\UnitsCSCom.Interop.dll` подтверждено:

- `IElement`
  - `DISPID 2` → `Parameters`
  - `DISPID 13` → `GetValue`
  - `DISPID 14` → `GetValueComment`
  - `DISPID 21` → `SetParameters`
  - `DISPID 9` → `Implementation`
- `IParameters`
  - `DISPID 0` → `Item(index)`
  - `DISPID 1` → `Count`
  - `DISPID 2` → `SetParameter(Name, Value, Comment, ValueComment)`
  - `DISPID 3` → `DeleteParameter`
  - `DISPID 4` → `DeleteAll`
  - `DISPID 5` → `Has(index)`
- `IParameter`
  - `DISPID 1` → `Name`
  - `DISPID 0` → `Value`
  - `DISPID 3` → `Comment`
  - `DISPID 4` → `ValueComment`

Это важно, потому что теперь можно:

- трассировать late-bound вызовы не “по имени”, а уже по точным `DISPID`;
- сопоставлять их с нативными методами COM-классов.

##### 4. Что `UnitsCSCom.nrx` реально оборачивает внутри

По `dumpbin /imports` и `dumpbin /exports` подтверждено:

- `UnitsCSCom.nrx` импортирует:
  - `mstudioData.dll`
  - `mstudioUI.dll`
  - `UnitsCS.nrx`
- внутри `mstudioData.dll` экспортированы:
  - `CElement`
  - `CParamsOwner`
  - `CParam`
  - `CIElementImpl@MStudioData`
  - `CIParamsOwnerImpl@MStudioData`
  - `CIParamImpl@MStudioData`

Особенно важные экспорты `mstudioData.dll`:

- `CIElementImpl@MStudioData::SetParameter(...)`
- `CIParamsOwnerImpl@MStudioData::SetParameter(...)`
- `CParamsOwner::SetParameter(...)`
- `CParam::setValue(...)`
- `CParam::setComment(...)`
- `CParam::setValueComment(...)`
- `CElement::QueryParameter(...)`
- `CElement::ApplyParameter(...)`
- `CParamsOwner::ApplyParameters(...)`

Практический вывод:

- рабочий COM-вызов `Parameters.SetParameter(...)` почти наверняка в итоге приходит не в abstract API, а в:
  - `CIParamsOwnerImpl@MStudioData::SetParameter(...)`
  - либо прямо в `CParamsOwner::SetParameter(...)`
- то есть **нативная точка записи уже фактически найдена по именам классов**.

##### 5. Что оборачивает `CoElement`

Из экспортов `UnitsCSCom.nrx` подтверждены методы:

- `CoElement::get_Parameters`
- `CoElement::GetValue`
- `CoElement::GetValueComment`
- `CoElement::SetParameters`
- `CoElement::get_Implementation`
- `CoElement::GetParentByLevel`
- `CoElement::GetById`
- `CoElement::AddChild`

Также подтверждены фабричные методы:

- `CreateElement`
- `CreateRootObject`
- `CreateParentObject`
- `CreateSubelementsCollection`
- `CreateSubelementsAllCollection`
- `CreateSubelementsPathCollection`

И отдельная сильная зацепка:

- `CoElementAdapterT<linCSDataObject>`
- `CoElementAdapterT<linCSNode>`
- `CoElementAdapterT<linCSCollision>`

Это означает:

- COM-объект `Element` в Model Studio не абстрактен;
- он адаптирует конкретные нативные классы продукта `linCS...`;
- то есть путь “разобрать COM и собрать эквивалент в C++” **правильный по сути**.

##### 6. Текущая рабочая гипотеза native-маршрута

На текущем этапе самая правдоподобная цепочка выглядит так:

1. live `vCSSubSegment` из nanoCAD / OdaX
2. COM-свойство `entity.Element`
3. `UnitsCSCom.nrx::CoElement`
4. адаптер `CoElementAdapterT<linCSDataObject>` или `CoElementPersistent/Standalone`
5. `mstudioData.dll::CIElementImpl / CIParamsOwnerImpl`
6. `mstudioData.dll::CParamsOwner::SetParameter(...)`
7. `mstudioData.dll::CParam::setValue / setComment / setValueComment`

Это уже гораздо конкретнее, чем общий поиск по памяти.

##### 7. Почему этот путь лучше “искать байты в памяти”

Потому что здесь мы идём:

- не от случайного layout;
- а от **рабочей продуктовой обёртки**;
- не от guessed offsets;
- а от:
- `TypeLib`
- `DISPID`
- `CLSID`
- реальных экспортированных имён классов и методов.

То есть следующая цель — не “угадывать 8 байт туда-сюда”, а:

- восстановить соответствие
- `IParameters.SetParameter(...)`
- `CIParamsOwnerImpl::SetParameter(...)`
- `CParamsOwner::SetParameter(...)`
- и уже потом вызвать это из чистого C++ без COM.

##### 8. Дополнительная live-проверка typed COM на реальном `vCSSubSegment`

Через `ModelSpace` была найдена реальная труба:

- `ObjectName = vCSSubSegment`
- `Handle = 84F`

По ней подтверждено:

- `element.Parameters.Count = 31`
- это совпадает с количеством параметров, которое раньше возвращал наш native-дамп `UnitsCS`
- `element.Parameters.Item("PART_TAGNUMBER")` существует
  - `Name = PART_TAGNUMBER`
  - `Value = ""`
  - `Comment = ""`
- `element.Parameters.Item("PART_TAG")` существует и даёт заполненное значение

Отдельно проверено:

- `element.Implementation` для этой live-трубы вернулся как `System.Int64`
- значение: `0`

Практический вывод:

- `Implementation` нельзя пока считать готовым мостом на полезный managed/native объект;
- зато `Parameters.Count = 31` ещё раз подтверждает, что typed COM и native `UnitsCS` смотрят в один и тот же param-layer.

##### 9. Новый pure C++ owner-path probe (`DTMXNRX21OPROBE` / `DTMXNRX21OSET`)

В `NrxCpp/DtmxNrx.cpp` добавлен отдельный экспериментальный путь поверх `mstudioData.dll`, без COM:

- `DTMXNRX21OPROBE`
  - берёт preselected объект;
  - открывает его через `AcDbObject`;
  - получает:
    - `pIface = getParametricInterface(...)`
    - `pRoot = getRootElementP(pIface)`
  - затем пробует смотреть на:
    - `pIface` как на `CParamsOwner`
    - `pRoot` как на `CParamsOwner`
  - логирует:
    - `ifaceCount`
    - `ownerCount` на `pIface`
    - `ownerCount` на `pRoot`
    - список параметров через:
      - `CParamsOwner::GetParamsCount`
      - `CParamsOwner::GetParameter(index)`
      - `CParam::getName`
      - `CParam::getValue`
      - `CParam::getComment`
  - отдельно снимает snapshot по:
    - `PART_TAG`
    - `PART_TAGNUMBER`
    - и одновременно сравнивает с `SubEnt_ParameterLPCSTR(...)`.

- `DTMXNRX21OSET`
  - использует тот же path;
  - сначала пытается писать через:
    - `CParamsOwner::SetParameter(...)` на `pIface`
  - если это не срабатывает, пробует fallback:
    - найти `CParam*` для `PART_TAGNUMBER` на `pRoot`
    - вызвать `CParam::setValue(...)`
  - после этого снимает `AFTER`-snapshot по `PART_TAGNUMBER`.

Текущее тестовое значение:

- `PART_TAGNUMBER = DTMX_CPP_OWNER`

Это не финальный production-путь, а именно controlled probe:

- совпадает ли layout `pIface` с `CParamsOwner`;
- живой ли путь записи через `mstudioData.dll`;
- где именно находится writable owner-слой.

##### 10. Важное техническое ограничение по SEH в VC++

При реализации owner-path выяснилось:

- `__try / __except` нельзя использовать в функциях, где есть C++-объекты с unwind/destructor (`std::wstring`, `std::vector` и т.д.);
- компилятор выдаёт:
  - `C2712: Невозможно использовать __try в функциях, требующих уничтожения объектов`

Рабочее решение:

- все потенциально “падающие” вызовы вынесены в отдельные leaf-wrapper функции без STL:
  - `SehOwnerCount(...)`
  - `SehIfaceCount(...)`
  - `SehOwnerGetParamAt(...)`
  - `SehParamGetName(...)`
  - `SehParamGetValue(...)`
  - `SehParamGetComment(...)`
  - `SehSubEntParameterStr(...)`
  - `SehOwnerSetParameter4(...)`
  - `SehParamSetValue(...)`
- а уже поверх них сделаны обычные логирующие helper’ы:
  - `SafeOwnerCount(...)`
  - `SafeIfaceCount(...)`
  - `LogOwnerParams(...)`
  - `LogNamedParamSnapshot(...)`

Практический вывод:

- для crash-prone reverse/probe-кода в nanoCAD/MCS лучше держать двухслойную схему:
  - **низкий слой** = только POD + `__try`
  - **верхний слой** = STL, логика, логирование

##### 11. Статус сборки NRX после owner-path изменений

После добавления `DTMXNRX21...` проект снова успешно собирается:

- проект: `NrxCpp/DtmxNrx.vcxproj`
- output: `Scripts/DtmxNrx20.nrx`

Проверка `dumpbin /exports` показала:

- экспорт присутствует:
  - `ncrxEntryPoint`

Проверка `dumpbin /dependents` показала стандартные зависимости:

- `McTyp.dll`
- `mt.dll`
- `NrxDbGate.dll`
- `NrxHostGate.dll`
- `McGeL.dll`
- runtime CRT DLL

Это важно, потому что:

- успешная сборка и наличие `ncrxEntryPoint` подтверждают, что текущий бинарь как минимум формально валиден как NRX-модуль;
- если `APPLOAD` снова скажет `Не найдена указанная процедура`, следующая проверка должна идти уже не в код команды, а в:
  - несовпадение SDK/runtime;
  - сторонние импортируемые DLL;
  - или конкретный экспорт/ABI одной из зависимостей на живой машине.

##### 12. Реальная причина `APPLOAD -> Не найдена указанная процедура` для `DtmxNrx20.nrx`

Причина была найдена через прямое сравнение import/export:

- runtime:
  - `nanoCAD x64 24.1`
- SDK сборки:
  - `NC_SDK_RU_26.0.7228.4926.8429`

Это уже само по себе риск ABI-расхождения:

- старые/простые NRX могли загружаться;
- более новые сборки начинали импортировать дополнительные символы из SDK 26;
- часть таких символов в runtime 24.1 уже отсутствует.

Конкретно у `DtmxNrx20.nrx` был найден прямой несовместимый импорт:

- DLL: `mt.dll`
- отсутствующий в runtime-24.1 символ:
  - `??0mcsWorkIDArray@@QEAA@XZ`
  - это `mcsWorkIDArray::mcsWorkIDArray()`

Практически это и вызывало:

- `APPLOAD, ЗАГПРИЛ`
- `Не удается загрузить модуль "...DtmxNrx20.nrx", ошибка: Не найдена указанная процедура`

##### 13. Как именно был найден несовместимый импорт

Сравнение показало:

- `DtmxNrx19.nrx` импортировал из `mt.dll` 9 символов
- `DtmxNrx20.nrx` импортировал из `mt.dll` 11 символов
- новый импорт в `20`, которого не было в `19`:
  - `??0mcsWorkIDArray@@QEAA@XZ`

Далее была сделана проверка экспортов live-runtime DLL:

- `McTyp.dll` (из `bin_nPlat`) — все прямые импорты `DtmxNrx20.nrx` присутствуют
- `NrxDbGate.dll` — все прямые импорты присутствуют
- `NrxHostGate.dll` — все прямые импорты присутствуют
- `mt.dll` — отсутствовал именно:
  - `??0mcsWorkIDArray@@QEAA@XZ`

Итог:

- проблема была не в `ncrxEntryPoint`
- не в `mstudioData.dll`
- не в `CParamsOwner`
- а именно в несовместимом **прямом импорте** `mt.dll`.

##### 14. Что в коде вызывало этот импорт

Источник несовместимого импорта был найден в MAPI-diagnostic коде:

- `LogMapiChildrenExProbes(...)`
- обращение к:
  - `mcsWorkIDArray children;`
- и дополнительный рискованный путь:
  - `MCSVariant::WorkIDArray()`

Для совместимости с runtime `24.1` было сделано:

1. отключён `getChildrenIDsEx(...)` probe, который требовал default-construction `mcsWorkIDArray`
2. ветка форматирования
   - `MCSVariant::kWorkIDArray`
   упрощена до текстового маркера без вызова `WorkIDArray()`

После этого:

- прямой импорт `??0mcsWorkIDArray@@QEAA@XZ` исчез из `DtmxNrx20.nrx`
- повторная проверка показала:
  - `McTyp.dll` — missing `0`
  - `mt.dll` — missing `0`
  - `NrxDbGate.dll` — missing `0`
  - `NrxHostGate.dll` — missing `0`

Практический вывод:

- для `nanoCAD 24.1` нельзя бездумно тянуть новые container/variant helper-и из SDK 26;
- даже если заголовки компилируются и линковка проходит, `APPLOAD` может упасть на отсутствующем runtime-export;
- при reverse/probe-разработке нужно регулярно проверять не только build, но и import-table итогового `.nrx`.

##### 15. Улучшение `DTMXNRX20TREE`: плоские строки пути

Чтобы удобнее изучать именно **иерархию объекта + свойства как строки**, в `DTMXNRX20TREE` добавлен второй формат лога поверх обычных `[NODE]` / `[P]`:

- `[PATH] <полный путь узла>`
- `[FLAT] <полный путь узла> -> <параметр> = <значение>`
- `[FLAT-NODE] <полный путь узла> -> <no-owner-params>`

Логика:

- путь собирается рекурсивно от корня через `CElement::GetName()`;
- для пустых имён используется fallback:
  - `<unnamed>`
- для каждого `CElement` теперь есть:
  1. старый структурный лог
  2. новый плоский лог, пригодный для grep / анализа / сопоставления

Пример целевого формата:

```text
[PATH] 3D/CONE
[FLAT] 3D/CONE -> Height = 4805.699999999998
[FLAT] 3D/CONE -> Radius = 10
[FLAT] 3D/CONE -> Visible = 1
```

Практический смысл:

- стало проще видеть дерево как набор строк;
- проще искать дублирующиеся узлы;
- проще сравнивать логи между итерациями;
- это ближе к задаче “получить иерархию объекта и его свойства в виде строк”.

##### 16. Переключение проекта на `NC_SDK_RU_24.1`

На 2026-06-26 выяснилось:

- путь на `NC_SDK_RU_26.0.7228.4926.8429` в рабочем окружении отсутствовал;
- реально доступен локальный SDK:
  - `C:\pdf_ingest\DTMXtest\NC_SDK_RU_24.1`

Проект `NrxCpp/DtmxNrx.vcxproj` переключён на этот SDK.

Дополнительно для совместимости понадобилось:

1. явно вернуть define:
   - `_MCS_CORE_ONLY`
2. в `stdafx.h` добавить forward declarations:
   - `class CWnd;`
   - `class CString;`
   - `class CStringArray;`
3. убрать прямую зависимость от метода:
   - `IMcNativeGate::IsMCSCustomObject(...)`
   которого нет в API `24.1`

После этого проект снова успешно собирается в:

- `Scripts/DtmxNrx20.nrx`

Важно:

- при сборке с `SDK 24.1` остаются многочисленные предупреждения `C4005` по MAPI/NRX-макросам;
- на текущем этапе это не блокирует сборку;
- warnings не равны проблеме загрузки, если итоговый `.nrx` создаётся и import-table совместима с runtime `24.1`.

### 11.21 `DTMXNRX20TREE` — текущий рабочий диагностический срез по объекту

По состоянию на `2026-06-26` наиболее полезная C++-команда для исследования live-объекта `Model Studio` в `DWG`:

- команда: `DTMXNRX20TREE`;
- актуальная сборка: `Scripts\DtmxNrx26.nrx`;
- загрузка в открытую сессию nanoCAD успешно автоматизируется через COM `LoadModule(...)`, но сама диагностика остаётся **чисто in-process C++**.

Что сейчас реально выдаёт команда:

1. **`MAPI-VIS` / `MAPI-FLAT`**
   - даёт человекочитаемую категорию, локальное название и значение;
   - формат:
     - `UI/<категория> -> <локальное имя> [<имя MAPI-свойства>] = <значение>`;
   - это самый полный и стабильный источник **видимых пользователю значений**.

2. **`DIRECT`**
   - перечисляет внутренние ключи параметров `Model Studio` (`PART_TAGNUMBER`, `PART_NAME`, `PART_TYPE`, `SYS_DB_UID` и т.д.);
   - теперь читает не только имя, но и `CParam::getValue()` / `CParam::getComment()`;
   - это подтвердило, что для многих параметров можно получить именно внутреннюю пару:
     - `внутреннее_имя -> значение`,
     - а иногда ещё и `comment`, который совпадает с пользовательской подписью.

3. **`TREE` / `FLAT`**
   - строит нативное дерево `CElement`;
   - пути теперь уникализируются через `id`, например:
     - `3D[0]/CONE[1]`
     - `3D[0]/CONE[2]`
   - это устранило проблему, когда одинаковые дочерние узлы с именем `CONE` невозможно было различить.

4. **`JOIN`**
   - новый слой склейки `DIRECT` и `MAPI-VIS`;
   - формат:
     - `UI/<категория> -> <локальное имя> [<внутренний PART_*>] = <значение>`;
   - нужен для практической задачи `описание атрибута + внутренний ключ + значение` в одном месте.

Пример уже подтверждённых `DIRECT`-строк:

- `PART_NAME = Труба полипропиленовая`
- `PART_TAG = PP-R SDR 6/S 2.5 - 20x3.4 PN 20`
- `PART_TAGNUMBER = DTMX_NRX_CPP`
- `PART_TYPE = Труба | comment=Тип изделия`
- `PART_GROUP = Детали трубопроводные | comment=Группа изделий`
- `PART_SPECIALITY = Водоснабжение и канализация | comment=Специализация`
- `SYS_DB_UID = {GUID}`

Практический вывод:

- связка `DIRECT + MAPI-FLAT` уже даёт то, что нужно для большинства задач исследования:
  - **внутренний ключ**;
  - **человекочитаемое имя / описание**;
  - **значение**.
- связка `JOIN` даёт уже готовые строки соответствия, например:
  - `UI/Параметры изделия -> Наименование изделия [PART_NAME] = ...`
  - `UI/Параметры изделия -> Обозначение / Модель [PART_TAG] = ...`
  - `UI/Параметры изделия -> Нормативный документ [PART_STANDARD] = ...`
  - `UI/Дополнительные параметры -> Группа изделий [PART_GROUP] = ...`
  - `UI/Дополнительные параметры -> Тип изделий [PART_TYPE] = ...`
  - `UI/? -> Идентификатор [PART_TAGNUMBER] = DTMX_NRX_CPP`

### 11.21.1 Актуальные публичные команды NRX

- `DTMXEDIT`
  - чистая пользовательская команда для массового редактирования параметра;
  - работает только по уже выделенным объектам (`PickFirst` / implied selection);
  - если ничего не выделено заранее, команда не должна переводить пользователя в режим ручного выбора, а должна завершаться сообщением:
    - `DTMXEDIT: сначала выделите объекты, затем запускайте команду`
  - строит список общих параметров по выделенным объектам;
  - пишет подробный лог **по каждому объекту отдельно**:
    - `--- OBJECT [0] params=N ---`
    - `ключ = значение`
  - после этого отдельно считает `common params`, которые можно редактировать пачкой.

- `DTMXLOG`
  - чистая диагностическая команда;
  - запускает текущий `DTMXNRX20TREE`;
  - в начале лога теперь пишет краткую легенду по системным тегам.

- `DTMXSUBELEMENTS`
  - отдельная диагностическая команда только для `sub-elements`;
  - берёт выбранный `Model Studio`-объект, получает `root CElement`;
  - рекурсивно пишет в лог:
    - индекс узла;
    - `depth`;
    - `level`;
    - `id`;
    - `childCount`;
    - `name`;
    - полный `path`;
  - в конце пишет сводку:
    - `totalNodesIncludingRoot`;
    - `subElementsWithoutRoot`;
    - `uniqueNames`;
    - количество каждого имени.

### 11.21.2 Легенда по системным тегам лога

- `[UnitsCS]`
  - найденные функции и адреса из `UnitsCS.nrx`;
  - для каждой строки теперь добавляется короткое пояснение, что делает указатель:
    - `getParametricInterface` — вход в параметрический интерфейс объекта;
    - `getRootElementP` — получить корневой `CElement`;
    - `setParameter4` — запись параметра по имени;
    - `CParam::getName/getValue/getComment` — имя, значение и подпись параметра;
    - `CParam::setValue/setComment/setValueComment` — возможные точки записи.

- `[SELECTED]`
  - выбранный DWG-объект;
  - показывает, удалось ли открыть объект и снять прямой snapshot его интерфейса.

- `[MAPI]`
  - слой Model Studio API через `IMcNativeGate`;
  - используется для связи native DWG-объекта с объектом MCS.

- `[DIRECT]`
  - внутренние параметры `PART_*` и их значения;
  - это основной источник для внутренних ключей.

- `[JOIN]`
  - склейка UI-подписи и внутреннего `PART_*`;
  - удобный слой вида:
    - `UI/<категория> -> <подпись> [PART_*] = <значение>`.

- `[NODE]`, `[PATH]`, `[FLAT]`
  - нативное дерево `CElement`;
  - помогает понять иерархию, даже когда UI-дерево ещё не полностью восстановлено.

- `[OWNER-IFACE]`, `[OWNER-ROOT]`
  - owner-параметры на разных уровнях;
  - это отдельный слой по отношению к `DIRECT` и UI-свойствам.

### 11.21.3 Иерархическое дерево: как мы пришли к параметрам

Ниже — практическая карта слоёв, файлов и точек входа, по которой сейчас идёт исследование параметров Model Studio внутри `DWG`.

```text
Выбранный объект в nanoCAD / Model Studio
└─ DWG entity
   ├─ пример runtime-класса:
   │  ├─ vCSSubSegment
   │  └─ vCSSegment2 / другие MCS custom objects
   ├─ открытие из C++:
   │  ├─ acedSSGet(...)
   │  ├─ acdbGetObjectId(...)
   │  └─ acdbOpenAcDbObject(...)
   └─ наш код:
      └─ NrxCpp/DtmxNrx.cpp

1. Слой nanoCAD / NRX host
└─ отвечает за загрузку нашего модуля и доступ к DWG-объекту
   ├─ файл проекта:
   │  └─ NrxCpp/DtmxNrx.vcxproj
   ├─ исходники:
   │  ├─ NrxCpp/DtmxNrx.cpp
   │  ├─ NrxCpp/stdafx.h
   │  └─ NrxCpp/stdafx.cpp
   ├─ результат сборки:
   │  └─ Scripts/DtmxNrx26.nrx
   └─ базовые host/API headers:
      ├─ $(NCadSDK)\include\arxgate\...
      ├─ $(NCadSDK)\include\nrxgate\...
      ├─ $(NCadSDK)\include\nrxdbgate\...
      └─ $(NCadSDK)\include\nrxhostgate\...

2. Слой MAPI (общий Model Studio API)
└─ отвечает за связь DWG ↔ MCS object
   ├─ DLL/runtime:
   │  ├─ McTyp.dll
   │  ├─ MechCtl.dll
   │  ├─ MT.dll
   │  └─ McGeL.dll
   ├─ ключевой глобальный мост:
   │  └─ gpMcNativeGate
   ├─ точка входа в нашем коде:
   │  └─ GetNativeGate()
   ├─ основные интерфейсы:
   │  ├─ IMcNativeGate
   │  ├─ IMcObject
   │  ├─ IMcDbObject
   │  ├─ IMcPropertySource
   │  └─ IMcParametricEnt
   ├─ основные действия:
   │  ├─ getMcsIdByNative(...)
   │  ├─ QueryObject(...)
   │  ├─ getParentID()
   │  └─ перечисление UI-свойств через property source
   └─ headers:
      ├─ $(NCadSDK)\include\MAPI\IContext.h
      ├─ $(NCadSDK)\include\MAPI\...
      └─ локально подключаемые:
         ├─ NrxCpp/IContext.h
         └─ NrxCpp/McsUtils.h

3. Product-native слой WATER / UnitsCS
└─ это главный подтверждённый путь к внутренним параметрам Model Studio
   ├─ runtime-модуль:
   │  └─ C:\Program Files\CSoft\Model Studio CS\NANOWATER\bin\nanoCAD241\UnitsCS.nrx
   ├─ в нашем коде:
   │  ├─ struct UnitsCsApi
   │  └─ LoadUnitsCsApi(...)
   ├─ factory / bridge:
   │  └─ getParametricInterface(AcDbObject*) -> linCSParametricSolidBase*
   ├─ основной объект:
   │  └─ linCSParametricSolidBase
   ├─ подтверждённые операции:
   │  ├─ GetParamsCount()
   │  ├─ GetParameter(index)
   │  ├─ SetParameter(...)
   │  ├─ getRootElementP()
   │  └─ SubEnt_ParameterLPCSTR(...)
   └─ назначение:
      ├─ читать внутренние `PART_*`
      ├─ писать `PART_*`
      └─ получать root `CElement`

4. Внутренний параметрический слой
└─ это уже не generic MAPI, а внутренние параметры конкретного объекта
   ├─ ключевой тип:
   │  └─ CParam
   ├─ подтверждённые методы:
   │  ├─ CParam::getName()
   │  ├─ CParam::getValue()
   │  ├─ CParam::getComment()
   │  ├─ CParam::setValue()
   │  ├─ CParam::setComment()
   │  └─ CParam::setValueComment()
   ├─ типовые внутренние ключи:
   │  ├─ PART_NAME
   │  ├─ PART_TAG
   │  ├─ PART_TAGNUMBER
   │  ├─ PART_TYPE
   │  ├─ PART_GROUP
   │  └─ PART_SPECIALITY
   └─ что даёт:
      ├─ внутренний ключ
      ├─ значение
      └─ подпись/comment параметра

5. Дерево children / sub-elements
└─ это путь в структуру объекта, а не только в его верхние PART_*
   ├─ root берётся из:
   │  └─ linCSParametricSolidBase::getRootElementP()
   ├─ основной тип:
   │  └─ CElement
   ├─ подтверждённые методы:
   │  ├─ CElement::GetChildCount()
   │  ├─ CElement::GetChild(index)
   │  ├─ CElement::GetName()
   │  ├─ CElement::GetId()
   │  └─ CElement::GetLevel()
   ├─ owner-параметры children:
   │  └─ CParamsOwner::{GetParamsCount, GetParameter, SetParameter4}
   └─ назначение:
      ├─ строить нативную иерархию
      ├─ искать sub-element
      └─ в перспективе выходить на дочерние параметры

6. UI-слой окна "Параметры объекта"
└─ это то, что видит пользователь справа в свойствах
   ├─ MAPI-VIS
   │  └─ видимые свойства с категориями и значениями
   ├─ MAPI-FLAT
   │  └─ плоские строки: категория / локальное имя / значение
   ├─ DIRECT
   │  └─ внутренние `PART_*`
   └─ JOIN
      └─ склейка:
         UI-подпись -> внутренний ключ -> значение

7. COM-слой (не основной, но важный как эталон)
└─ нужен как контрольный рабочий путь и как источник знания о native-слое
   ├─ runtime:
   │  └─ C:\Program Files\CSoft\Model Studio CS\NANOWATER\bin\nanoCAD241\UnitsCSCom.nrx
   ├─ interop:
   │  └─ Artifacts/UnitsCSCom.Interop.dll
   ├─ подтверждённые интерфейсы:
   │  ├─ UnitsCSCom.Interop.IElement
   │  ├─ UnitsCSCom.Interop.IParameters
   │  └─ UnitsCSCom.Interop.IParameter
   └─ роль в исследовании:
      ├─ доказал, что запись параметров реально работает
      ├─ помог понять внутренний param-layer
      └─ служит эталоном, но не целевым финальным решением

8. Что сейчас считается "правильным маршрутом"
└─ текущая рабочая цепочка
   ├─ DWG object
   ├─ UnitsCS.nrx
   ├─ linCSParametricSolidBase
   ├─ CParam / PART_*
   ├─ CElement root / children
   └─ JOIN с MAPI-VIS для человекочитаемого отображения
```

Краткий смысл дерева:

- если нужно **менять атрибуты типа `PART_TAGNUMBER`**, основной путь идёт через:
  - `DWG object -> UnitsCS -> linCSParametricSolidBase -> CParam`.
- если нужно **восстанавливать иерархию объекта**, основной путь идёт через:
  - `DWG object -> UnitsCS -> getRootElementP() -> CElement tree`.
- если нужно **понять, как это выглядит для пользователя в окне свойств**, нужен мост:
  - `DIRECT + MAPI-VIS + JOIN`.
- generic `MAPI` полезен как слой навигации и UI-свойств, но не доказан как основной путь записи `PART_*` для `vCSSubSegment`.

### 11.21.4 Что реально показала команда `DTMXSUBELEMENTS` на трубе

Live-проверка на выбранной трубе (`vCSSubSegment`) в `nanoCAD 24.1 + Model Studio CS` показала:

- команда успешно отрабатывает на реальном объекте;
- `selected class = vCSSubSegment`;
- `root CElement` существует;
- для исследованной трубы дерево `sub-elements` сейчас выглядит так:

```text
3D[0]
├─ CONE[1]
└─ CONE[2]
```

Сводка из лога:

- `totalNodesIncludingRoot = 3`
- `subElementsWithoutRoot = 2`
- `uniqueNames = 2`
- `3D = 1`
- `CONE = 2`

Практический вывод:

- на текущем найденном `CElement`-маршруте для трубы видна **геометрическая подструктура**;
- это полезно для исследования native-иерархии;
- но это **ещё не** левое UI-дерево окна `Параметры объекта` (`Порт1`, `Порт2`, `Список работ`, `Изоляция` и т.д.);
- значит, для UI-иерархии нужен либо другой контейнер, либо дополнительный слой поверх уже найденного `root CElement`.

### 11.21.5 Что показал `DTMXCONTAINERPROBE` по выбранной трубе

Команда `DTMXCONTAINERPROBE` была прогнана на live-выборке трубы (`vCSSubSegment`) в `nanoCAD 24.1 + Model Studio CS`.

Что подтвердилось:

- выбранный объект:
  - `class = vCSSubSegment`
  - `rootName = 3D`
  - `rootChildCount = 2`
- `MAPI parentID = NULL`
- `MAPI references`:
  - `IMcReferenceExtension` для выбранного объекта не дал полезного дерева;
  - `MAPI-REF hr = 0x80004002`, `count = 0`

Особенно важный результат по `MAPI-VIS / MAPI-OBJ`:

- в свойствах уже видны **контейнерные узлы**, которые очень похожи на UI-группы, а не на отдельные native-классы:
  - `Трубопровод.Параметры трубопровода = <Свойства Осевой>`
  - `Компонент.Параметры компонента = <Свойства объекта>`
  - `Изоляция.Изоляция = <Свойства Изоляции>`
  - `Поведение компонента.OwnerSegId = ...`
- это сильный сигнал, что часть левого дерева окна свойств может быть:
  - не `CElement`-children,
  - не `MAPI getChildrenIDs()`,
  - а именно **UI/property containers**, собранные внутри property-layer.

Что найдено в owner-блоке рядом с выбранной трубой:

- рядом живут разные runtime-классы:
  - `vCSSubSegment`
  - `vCSNode`
  - `vCSInLine`
  - `vCSSegment2`
  - `vCSAxis`

Практически важное наблюдение:

- `vCSInLine` и `vCSNode` — реальные соседние parametric-объекты, которые стоят рядом с трубой в одном owner-блоке;
- у них тоже есть собственные `PART_*` параметры;
- у `vCSInLine` встречается:
  - `PART_PIPE_PARAM_STATE`
  - `PART_INSULATION_THICKNESS`
  - `PART_INSULATION_DISABLEVIEW`
- это делает `vCSInLine` и `vCSNode` главными кандидатами для следующего исследования на предмет:
  - портов,
  - компонентных узлов,
  - осевой/стыковой логики.

Промежуточный вывод:

- `Параметризация`, `Порт1`, `Порт2`, `Список работ` пока **не подтверждены** как отдельные `CElement` sub-elements;
- `Изоляция` уже подтверждена как property-container в `MAPI`;
- next best direction:
  - исследовать отношения между выбранным `vCSSubSegment` и соседними `vCSNode` / `vCSInLine`;
  - отдельно искать, не прячутся ли `Порт1/Порт2` в свойствах этих соседних классов, а не в самой трубе.

### 11.21.6 Что показал `DTMXRELPROBE` по owner-блоку выбранной трубы

Команда `DTMXRELPROBE` была расширена и прогнана на live-модели. Она:

- проходит по owner-блоку выбранного `vCSSubSegment`;
- фильтрует соседние runtime-классы;
- пишет `DIRECT` + `MAPI` свойства;
- дополнительно показывает имена детей `root CElement`;
- для нетиповых веток (`GROUP`, `ARRAY_*`, `REVOLVE`, `NOZZLE`) автоматически делает углублённый `tree dump`.

Что подтверждено по составу owner-блока:

- `vCSSubSegment` — `95` объектов;
- `vCSNode` — `83` объектов;
- `vCSSegment2` — `69` объектов;
- `vCSInLine` — `32` объектов;
- `vCSAxis` — `14` объектов.

Что важно по деревьям `root CElement`:

- выбранная труба `vCSSubSegment` почти всегда даёт только геометрию:
  - `3D -> CONE, CONE`
- `vCSNode` бывает двух характерных типов:
  - `3D -> NOZZLE`
  - `3D -> TORUS_ARC / CYLINDER / ...`
- `vCSInLine` оказался самым интересным классом:
  - `3D -> CONE / CYLINDER / ...`
  - `3D -> CYLINDER / REVOLVE(9) / BOX`
  - `3D -> GROUP(3) / ARRAY_CIRC(1) / ARRAY_CIRC(1) / CYLINDER`

Практический смысл:

- `vCSSubSegment` остаётся в первую очередь телом трубы;
- `vCSNode` похож на узлы/стыки/концы, в том числе с дочерним `NOZZLE`;
- `vCSInLine` очень похож на врезанные/линейные компоненты арматуры и фитингов.

Что показал углублённый `tree dump`:

- у `vCSNode -> NOZZLE` идут чисто конструктивные параметры:
  - `Radius`
  - `Radius2`
  - `WallThickness`
  - `Direction*`
  - `Orientation*`
- у нетипового `vCSInLine -> CYLINDER / REVOLVE / BOX` тоже пока видны именно геометрические и связочные поля:
  - `DestElement`
  - `DestObjectType`
  - `DestRelation`
  - `Radius`
  - `Height`
  - `Visible`
- то есть даже там найденный `CElement`-маршрут пока раскрывает в основном **нативную геометрию**, а не готовое UI-дерево окна свойств.

Что подтвердилось по `MAPI`:

- `vCSInLine` даёт уже полезные product-данные, например:
  - `Дополнительные параметры.Тип изделий = Кран шаровой`
  - `Дополнительные параметры.Группа изделий = Арматура трубопроводная`
  - `Параметры изделия.Обозначение / Модель = PP-R, DN20`
- значит, `vCSInLine` — это важный carrier-класс для встроенных компонентов в трубопроводе.

Что пока не найдено:

- прямых узлов `Порт1`, `Порт2`, `Список работ`, `Параметризация` в уже найденных `CElement`-деревьях;
- явных `MAPI`-полей с текстами `порт` / `работ` на текущем owner-блоке.

Промежуточный вывод:

- левое UI-дерево окна `Параметры объекта` пока **не совпадает** с найденным `root CElement`-деревом;
- `CElement` даёт геометрию и внутренние подузлы;
- `MAPI` даёт правую панель свойств;
- `vCSInLine` и `vCSNode` — подтверждённые соседние carrier-классы, которые нужно исследовать дальше как возможные носители логики оси, стыков, портов и встроенных компонентов.

### 11.22 Что уже подтверждено и что пока не подтверждено по дереву

Подтверждено:

- `MAPI-VIS` стабильно возвращает значения пользовательских свойств выбранного объекта;
- `DIRECT` после чтения `CParam::getValue()` стал возвращать реальные значения многих внутренних `PART_*` параметров;
- `JOIN` уже автоматически связывает значительную часть `PART_*` параметров с пользовательскими подписями справа в окне свойств;
- нативное дерево `CElement` для выбранной трубы сейчас показывает геометрическую часть (`3D -> CONE -> ...`) и owner-параметры дочерних геометрических узлов;
- автоматический запуск диагностики в открытом nanoCAD можно делать через:
  - `GetActiveObject("nanoCADx64.Application.24.0")`
  - `UnloadModule(...)`
  - `LoadModule(...)`
  - `ActiveDocument.SendCommand("DTMXNRX20TREE ")`

Пока не подтверждено:

- что нативное дерево `CElement` полностью совпадает с левым деревом окна `Параметры объекта` (`Параметризация`, `Порт1`, `Порт2`, `Список работ`, `Изоляция` и т.п.);
- что все дочерние UI-элементы окна свойств доступны через уже найденные `CElement::GetChild*` без дополнительного обхода других контейнеров;
- что `MAPI childCount` в runtime `nanoCAD 24.1` можно получить штатно: экспорт `mcsWorkIDArray()` в этой конфигурации отсутствует, поэтому ветка `MAPI-CHILDEX` сейчас пропускается;
- что `LogOwnerParams(pIface)` безопасно отрабатывает до конца на всех объектах — для части сценариев эта ветка зависает/обрывается после `ownerCount`.
- что `PART_TAGNUMBER -> Идентификатор` присутствует в `MAPI-VIS` как обычное видимое свойство: сейчас оно подтверждено через `DIRECT`, но в текущем наборе `MAPI-VIS` явно не поймано и потому помечается как `UI/?`.

Рекомендуемый практический маршрут на текущем этапе:

1. для **значений и подписей** опираться на `MAPI-FLAT`;
2. для **внутренних ключей** опираться на `DIRECT`;
3. для **геометрической/нативной иерархии** опираться на `TREE/FLAT`;
4. дальше искать мост между:
   - UI-деревом окна свойств,
   - и нативным `CElement`-деревом,
   чтобы получить полное соответствие `родитель/дочерний узел -> внутренние параметры -> пользовательские подписи`.

---

### 11.23 Глобальный реестр CParamDef, Explorer, Порты и Параметры оси (DtmxNrx41–44)

#### Глобальный реестр определений параметров (`mstudioData.dll`)

Рядом с инстанс-уровнем CParam (`getName`, `getValue`) находится **глобальный реестр схемы** — 4597 определений для всех возможных параметров Model Studio CS.

Подтверждённые экспорты `mstudioData.dll`:

```
?GetGlobalParamDefs@@YAXPEAPEAVF_CParamDefs@@_N@Z
    — free function, сигнатура: void(CParamDefs** ppOut, bool includeHidden)
    — возвращает глобальный CParamDefs*, содержит все 4597 определений схемы

?GetParam@CParamDefs@@QEBAPEAVCParamDef@@PEB_W@Z
    — CParamDef* CParamDefs::GetParam(const wchar_t* name)
    — поиск определения по внутреннему имени (PART_NAME, BOM_GROUP, ...)

?GetCount@CParamDefs@@QEBA_JXZ
    — long long CParamDefs::GetCount()
    — возвращает 4597

?GetComment@CParamDef@@QEBAPEB_WXZ
    — const wchar_t* CParamDef::GetComment()
    — канонический UI-лейбл (например «Наименование», «Диаметр условный (Ду)»)

?GetCategoryCount@CParamDef@@QEBA_JXZ
    — long long CParamDef::GetCategoryCount()
    — число категорий у определения (обычно 1–2)

?GetCategory@CParamDef@@QEBAPEB_W_J@Z
    — const wchar_t* CParamDef::GetCategory(long long idx)
    — реальная MCS-категория по индексу: «Изделие», «Трубопровод», «Спецификация», ...

?IsHidden@CParamDef@@QEBA_NXZ
    — bool CParamDef::IsHidden()
    — true для системных/внутренних параметров (SYS_*)

?GetName@CParamDef@@QEBAPEB_WXZ
    — const wchar_t* CParamDef::GetName()
    — внутреннее имя (PART_NAME, BOM_GROUP, ...)
```

Подтверждённые примеры из живого запуска (команда `DTMXNRX21PARAMDEF`):

| Имя | GetComment | GetCategory(0) | Hidden |
|-----|-----------|----------------|--------|
| `PART_NAME` | «Наименование» | «Изделие» | false |
| `BOM_GROUP` | «Группа по спецификации» | «Документ Спецификация» (cat[0]), «Спецификация» (cat[1]) | false |
| `BOM_COMMENT` | «Примечания» | «Документ Спецификация» | false |
| `PART_PIPE_DN` | «Диаметр условный (Ду)» | «Трубопровод» | false |
| `SYS_DB_UID` | «» (пустой — так и должно быть) | — | false |

Практическое применение:

- Заполнять `ParamState::comment` из `CParamDef::GetComment()`, если инстанс-уровень `CParam::getComment()` вернул пустую строку.
- Заполнять `ParamState::category` из `CParamDef::GetCategory(0)` — это реальная MCS-категория для группировки в UI.
- Кешировать `CParamDefs*` один раз (вызов `GetGlobalParamDefs` дорогой), переиспользовать для всех объектов сессии.

Типичные категории MCS (подтверждены на живых данных):

```
«Изделие»                «Классификация»       «Изоляция»
«Трубопровод»            «Документ Спецификация» «Спецификация»
«Программа СТАРТ»        «Системные»            «Прочие»
```

#### Путь `cpoGetParameterComment` — мёртвый конец

`CParamsOwner::GetParameterComment(name, default)` — **не работает** для получения лейблов.  
На всех реальных объектах возвращает пустую строку.  
Правильный маршрут: `CParamDefs::GetParam(name)` → `CParamDef::GetComment()`.

#### SEH-правило в NRX C++

**Ограничение компилятора**: функция, содержащая `__try/__except`, не может содержать объекты C++ с нетривиальным деструктором (`std::wstring`, `std::vector`, любые RAII).

Ошибка: `C2712: Cannot use __try in functions that require object unwinding`.

**Решение**: выделять SEH-вызовы в отдельные статические функции с только POD-локальными переменными:

```cpp
// Только POD-локали, никаких std::wstring, vector, RAII:
static const wchar_t* SehCpdGetComment(PFN_cpdGetComment fn, void* pDef)
{
    if (!fn || !pDef) return nullptr;
    __try { return fn(pDef); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return nullptr; }
}

static int SehSbGetCountNodes(PFN_sbGetCountNodes fn, const void* pThis)
{
    if (!fn || !pThis) return 0;
    __try { return fn(pThis); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 0; }
}
```

Вызывающий код с `std::wstring` и RAII вызывает эти функции безопасно.

#### DTMXNRX22EXPLORE — интерактивный проводник объекта

Win32 TreeView-окно, открываемое командой `DTMXNRX22EXPLORE`. Показывает для выбранного MCS-объекта:

| Секция | Источник | Содержимое |
|--------|----------|------------|
| `CElement дерево` | `mstudioData.dll CElement` | геометрическая иерархия + owner-параметры |
| `Параметры (N)` | `linCSParametricSolidBase::GetParameter(i)` | все vtable-параметры, группировка по `CParamDef::GetCategory` |
| `Параметры оси (N)` | `linCSNode::GetParamsCount / GetParameter(i)` | параметры оси, только для `linCSNode` |
| `Порты (N)` | `linCSParametricSolidBase::GetCountNodes / GetNodeID(i)` | только OID + класс подключённого объекта |
| `Связи и соседи` | MAPI + блок-скан | IMcCtrDriver-связи, блочные соседи |

Архитектурный принцип: **Порты ≠ Параметры оси**.  
«Порты» — топологический срез (что к чему подключено). «Параметры оси» — отдельная секция только для `linCSNode`-объектов (труб).

#### DTMXNRX23PATHS — визуализация маршрутов доступа к данным

Отдельное Win32 TreeView-окно, открываемое командой `DTMXNRX23PATHS`.  
Его задача не просто показать параметры, а показать **как именно программист до них добирается**: через какой слой, какой интерфейс и какую точку перехода.

Команда особенно полезна для выбранных объектов типа `vCSNode` / `vCSInLine`, когда нужно понять:

- где начинается путь от `AcDbObjectId`;
- как перейти к нативному `AcDbObject*`;
- как выйти на in-process `UnitsCS` / `CElement`;
- как получить те же данные через `COM`;
- где участвует `MAPI`;
- как попасть к соседям через `ownerId -> BlockTableRecord`.

Текущее дерево `DTMXNRX23PATHS` строится по слоям:

| Секция | Что показывает |
|--------|----------------|
| `1. DWG / Native` | `AcDbObjectId`, `AcDbObject*`, native class, handle, `ownerId` |
| `2. C++ / UnitsCS` | переход `AcDbObject* -> getParametricInterface() -> getRootElementP() -> CElement`, плюс примеры owner-параметров |
| `3. COM` | маршрут `ActiveDocument.Database.HandleToObject(handle) -> entity -> Element / ElementAxis` |
| `4. MAPI` | маршрут `getMcsIdByNative -> QueryObject -> IMcObject / IMcDbObject` |
| `5. Соседи / owner-block` | обход содержимого owner-блока и статистику соседних native-классов |
| `6. Быстрые маршруты` | короткие «шпаргалки», какой API использовать для нужного семейства данных |

Ключевая идея команды: **показывать не только “что нашли”, но и “через какой интерфейс и узел перехода мы к этому пришли”**.

Текущее состояние:

- команда зарегистрирована и открывает отдельное окно;
- окно подтверждено в runtime (`MCS Paths — vCSInLine`);
- для `COM` уже показывается маршрут к `entity.Element.Parameters.Item(i)` и `entity.ElementAxis.Element.Parameters.Item(i)`;
- дополнительно подтверждён COM-путь к топологии осевой через `entity.ElementAxis`: `Components`, `GetPrevComponent(...)`, `GetNextComponent(...)`, `GetFirstComponent()`, `GetLastComponent()`;
- для `C++ / UnitsCS` уже показывается маршрут к `pIface`, `pRoot` и owner-параметрам;
- секция `Соседи / owner-block` теперь не только считает классы, но и даёт ленивое раскрытие:
  - сначала `vCSNode = 83`;
  - затем список конкретных объектов этого класса;
  - у каждого объекта есть свой `handle` и собственные подузлы путей;
- у каждого раскрытого объекта доступны как минимум:
  - `DWG / Native`;
  - `C++ / UnitsCS`;
  - `MAPI direct connections (N)`;
  - `owner-block classes`;
- если у раскрытого объекта есть параметры (`getParamsCount > 0` / `Parameters.Count > 0`), они теперь тоже выводятся внутри его узла:
  - `C++ / UnitsCS -> Параметры (N)` — owner/vtable параметры;
  - `COM -> entity.Element (N)` — COM-параметры элемента;
  - `COM -> entity.ElementAxis (N)` — COM-параметры осевой, если доступны;
- важная деталь реализации: даже для корневого выбранного объекта параметры лучше грузить **лениво по раскрытию узла**, а не строить весь список сразу в `WM_CREATE`; иначе окно `MCS Paths` может не доживать до показа;
- таким образом дерево начинает работать как рекурсивный навигатор по объектам и их связям, а не только как статический отчёт по текущему выбору;
- прямой нативный C++ путь к вкладке `Параметры осевой` пока **не подтверждён**, поэтому в дереве он помечается как исследуемый.

Практическое назначение:

- использовать как «карту переходов» перед написанием рабочего кода;
- быстро понимать, какой слой реально отдаёт нужные данные;
- сравнивать пути `C++`, `COM`, `MAPI` для одного и того же выбранного элемента;
- фиксировать, где путь уже рабочий, а где пока только гипотеза.

#### COM-топология осевой: что можно добавить в «Связи»

Проверено отдельным read-only скриптом:

- `Scripts\probe_selected_ms_com_relations.py`
- лог:
  - `C:\Users\atsarkov\Desktop\probe_selected_ms_com_relations_log.txt`

На выбранном объекте `vCSInLOffset` (`Handle=90DE`) COM дал не только параметры, но и полноценный срез связей по осевой:

- `entity.ElementAxis` возвращает объект оси `vCSAxis`;
- `entity.ElementAxis.Components` возвращает всю цепочку компонентов оси;
- `GetPrevComponent(entity)` возвращает предыдущий компонент относительно выбранного;
- `GetNextComponent(entity)` возвращает следующий компонент относительно выбранного;
- `GetFirstComponent()` / `GetLastComponent()` дают начало и конец цепочки;
- `StartTee` / `EndTee`, `StartPipe` / `EndPipe`, `EquipmentNodeStart` / `EquipmentNodeEnd` дают специальные концевые подключения, если они есть;
- `CountItems(bTerminators, bElbows, bPipes, bInlines, bSupports)` считает компоненты по типам;
- `GetFromObjParamVal(name)` / `GetToObjParamVal(name)` позволяют читать параметры объектов на концах оси.

Фактический результат на тестовой осевой:

- `Components.Count = 27`;
- в цепочке найдены:
  - `vCSNode`;
  - `vCSSubSegment`;
  - `vCSInLine`;
  - `vCSInLOffset`;
  - `vCSSupport`;
- для выбранного `vCSInLOffset #90DE`:
  - `GetPrevComponent` → `vCSSubSegment #90DF`;
  - `GetNextComponent` → `vCSSubSegment #90E0`;
  - `GetFirstComponent` → `vCSNode #853`;
  - `GetLastComponent` → `vCSNode #884`;
  - `EndTee` → `vCSInLine #887`;
  - `Length = 9853.800873085213`;
  - `CountItems(all) = 28`;
  - `CountItems(pipes) = 13`;
  - `CountItems(elbows+inlines) = 12`;
  - `CountItems(supports) = 1`.

Практический вывод:

- `MAPI direct connections` и `owner-block classes` показывают низкоуровневые соседства;
- `COM ElementAxis` показывает **осмысленную технологическую цепочку трубопровода**;
- в окно `DTMXNRX23PATHS` стоит добавлять отдельную ветку:
  - `COM -> entity.ElementAxis topology`;
  - внутри: endpoints, prev/next, first/last, counts, full `Components`;
- это read-only использование COM, не связано с уже решённым COM-путём записи `PART_TAGNUMBER`.

Важное ограничение по стабильности:

- полную ветку `entity.ElementAxis topology` нельзя строить при раскрытии каждого дочернего объекта в lazy-иерархии;
- на соседних/дочерних объектах могут попадаться классы без стабильного `ElementAxis`, и nanoCAD может аварийно закрыться;
- безопасное правило: полную COM-топологию осевой строить только для корневого выбранного объекта;
- для дочерних `OidRef` оставлять параметры `entity.Element` / `entity.ElementAxis.Element` и MAPI/owner-block связи, но не запускать полный обход `Components`;
- fallback `ElementAxis -> entity` допустим только если сам объект имеет `ObjectName = vCSAxis`.

Отдельное ограничение по `Proxy`-объектам:

- соседние `Proxy` / `AcDbProxyEntity` элементы нельзя раскрывать как полноценные Model Studio объекты;
- при попытке открыть proxy через общий путь `BuildOidSections -> getParametricInterface / COM / MAPI` nanoCAD может аварийно закрыться;
- правильное поведение в `DTMXNRX23PATHS`:
  - оставлять раскрываемый `+` у proxy-узла;
  - при раскрытии показывать безопасный паспорт `DWG / Native safe proxy view`;
  - выводить `NativeClassName`, `Handle`, `ObjectId(old)`, `ownerId`;
  - не запускать для proxy только опасные ветки `COM / MAPI / UnitsCS`;
- для всех обычных Model Studio / DWG объектов раскрытие должно сохраняться максимально полным;
- цель `DTMXNRX23PATHS` — потрошитель выбранного элемента: собирать все доступные связи и параметры, а не скрывать проблемные ветки.

#### Подтверждённые экспорты `UnitsCS.nrx` — порты и параметры оси

```
?GetCountNodes@linCSParametricSolidBase@@QEBAHXZ
    — int GetCountNodes() const
    — число подключённых осей/компонентов (портов)
    — работает на ЛЮБОМ linCSParametricSolidBase (и компонент, и труба)

?GetNodeID@linCSParametricSolidBase@@QEBA?AVNcDbObjectId@@H@Z
    — NcDbObjectId GetNodeID(int portIdx) const
    — OID объекта, подключённого к порту portIdx
    — !! ВНИМАНИЕ: возвращает NcDbObjectId по значению через hidden pointer !!

?GetParamsCount@linCSNode@@QEAAHXZ
    — int GetParamsCount()   (non-const — QEAA, не QEBA)
    — число параметров оси linCSNode

?GetParameter@linCSNode@@QEBAPEAVCParam@@H@Z
    — const CParam* GetParameter(int idx) const
    — параметр оси по индексу, тот же CParam что в mstudioData.dll
```

#### ABI-ловушка: NcDbObjectId возвращается через hidden pointer

`NcDbObjectId` имеет user-defined `operator=` → по правилам MSVC x64 ABI **не является trivially copyable** → возвращается через скрытый первый аргумент (hidden pointer), **не через RAX**.

Правильный typedef для `GetNodeID`:
```cpp
// НЕПРАВИЛЬНО (возвращает NcDbObjectId в RAX — undefined behaviour):
// typedef NcDbObjectId (__cdecl* PFN_sbGetNodeID)(const void* pThis, int idx);

// ПРАВИЛЬНО (hidden pointer convention):
typedef void (__cdecl* PFN_sbGetNodeID)(AcDbObjectId* outOid, const void* pThis, int portIdx);
```

SEH-обёртка:
```cpp
static void SehSbGetNodeID(PFN_sbGetNodeID fn, AcDbObjectId* outOid,
                           const void* pThis, int idx)
{
    if (!fn || !outOid || !pThis) return;
    __try { fn(outOid, pThis, idx); }
    __except(EXCEPTION_EXECUTE_HANDLER) {}
}
```

Использование в init:
```cpp
AcDbObjectId nodeOid;
nodeOid.setNull();
SehSbGetNodeID(api.sbGetNodeID, &nodeOid, pIface, portIndex);
// nodeOid теперь корректен
```

#### Определение типа объекта (linCSNode vs компонент)

Для выбора между чтением через `linCSNode::GetParamsCount` (труба) и обычным vtable-путём (компонент):

```cpp
std::wstring cls = NativeClassName(pObj);  // pObj->isA()->name()
bool isLinCSNode = (cls.find(L"linCSNode") != std::wstring::npos);
```

Только при `isLinCSNode == true` вызывать `?GetParamsCount@linCSNode@@QEAAHXZ` и `?GetParameter@linCSNode@@QEBAPEAVCParam@@H@Z`. Вызов этих методов на не-`linCSNode` объекте приведёт к краше (неверная vtable).

#### Резервный путь для портов на трубе

Когда `pIface` (из `getParametricInterface`) null или отличается от `pObj`:

```cpp
const void* portBase = ctx->pIface ? ctx->pIface : (const void*)ctx->pObj;
int nPorts = SehSbGetCountNodes(api.sbGetCountNodes, portBase);
```

`linCSNode` является `linCSParametricSolidBase` (наследование), поэтому `GetCountNodes`/`GetNodeID` применимы и к трубе, и к компоненту.

#### Что пока не подтверждено

- Что именно возвращает `GetNodeID` для трубы (`linCSNode`): OID двух подключённых компонентов, или что-то иное — нужен живой тест.
- Что `GetCountNodes` на `linCSNode` возвращает 2 (оба конца трубы).
- Параметры оси через `linCSNode::GetParamsCount` — нужно подтвердить, что они совпадают с тем, что показывает вкладка «Параметры осей» в UI Model Studio.
- Работает ли `DTMXNRX22EXPLORE` на объектах типа `linCSNode` (выбор самой трубы, не компонента).

---

## Иконки для ribbon-кнопок плагина

### Механизм регистрации иконок в nanoCAD

Иконки для ribbon-кнопок задаются **не** через атрибуты `SmallImage`/`LargeImage` в CUIX-файле, а через секции `[\configman\commands\...]` в файле `water.cfg`. Ключом секции является значение атрибута `MenuMacroID` ribbon-кнопки (Macro UID), а не имя команды.

**Файл:** `C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\water.cfg` (кодировка CP1251)

```ini
[\configman\commands\DTMX_CMD_EDIT]
weight=i10 |cmdtype=i1
intername=sDTMXEDIT
DispName=sПравка
ToolTipText=sПравка
StatusText=sПравка параметров
BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_EDIT

[\configman\commands\DTMX_CMD_EXPLORE]
weight=i10 |cmdtype=i1
intername=sDTMXNRX22EXPLORE
DispName=sСвойства
ToolTipText=sСвойства
StatusText=sПроводник свойств элемента
BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_EXPLORE

[\configman\commands\DTMX_CMD_PATHS]
weight=i10 |cmdtype=i1
intername=sDTMXNRX23PATHS
DispName=sСвязи
ToolTipText=sСвязи
StatusText=sМаршруты и связи объекта
BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_PATHS

[\configman\commands\DTMX_CMD_PING]
weight=i10 |cmdtype=i1
intername=sDTMXPING
DispName=sТест
ToolTipText=sТест
StatusText=sДиагностика ribbon-кнопки
BitmapDll=sDtmxMenuRes.dll |Icon=sDTMX_PING
```

Формат строки `BitmapDll`: `s<имя_dll> |Icon=s<имя_ресурса>` — префикс `s` означает строковый тип значения.

`BitmapDll` задаёт имя DLL (без пути, ищется рядом с `CommonRes.dll`) и имя именованного ресурса типа `RT_GROUP_ICON` внутри DLL. nanoCAD загружает иконку через `LoadImage(hDll, "DTMX_EDIT", IMAGE_ICON, cx, cy, 0)`.

Рабочий пример из стандартной поставки:

```ini
[\configman\commands\pipe_draw_pipeline]
weight=i10 |cmdtype=i1
intername=spipe_draw_pipeline
BitmapDll=sCommonRes.dll |Icon=sIDI_MS_PIPE32
```

### Ресурсная DLL (DtmxMenuRes.dll)

Иконки для DTMX-команд хранятся в отдельной DLL-ресурсе `DtmxMenuRes.dll`, расположенной в том же каталоге, что и `CommonRes.dll`:

```
C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\DtmxMenuRes.dll
```

Проект DLL: `c:\pdf_ingest\DTMXtest\DtmxMenuRes\DtmxMenuRes.vcxproj` (x64, Release)

Файл ресурсов `DtmxMenuRes.rc`:

```rc
DTMX_EDIT               ICON   "res\\dtmx_edit.ico"
DTMX_EXPLORE            ICON   "res\\dtmx_explore.ico"
DTMX_PATHS              ICON   "res\\dtmx_paths.ico"
DTMX_PING               ICON   "res\\dtmx_ping.ico"
DTMX_EDIT_DARK          ICON   "res\\dtmx_edit.ico"
DTMX_EXPLORE_DARK       ICON   "res\\dtmx_explore.ico"
DTMX_PATHS_DARK         ICON   "res\\dtmx_paths.ico"
DTMX_PING_DARK          ICON   "res\\dtmx_ping.ico"
```

После изменения `.ico` файлов — пересобрать и задеплоить:

```powershell
$msbuild = "C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe"
& $msbuild "c:\pdf_ingest\DTMXtest\DtmxMenuRes\DtmxMenuRes.vcxproj" /p:Configuration=Release /p:Platform=x64 /t:Rebuild /v:minimal
Copy-Item "c:\pdf_ingest\DTMXtest\DtmxMenuRes\bin\x64\Release\DtmxMenuRes.dll" `
          "C:\Program Files\CSoft\Model Studio CS\NANOWATER\Support\WATER\DtmxMenuRes.dll"
```

### Формат ICO-файлов для нормального отображения

**Обязательно:**
- Несколько размеров в одном файле: 16×16, 32×32, 48×48, 64×64
- 32bpp BGRA (Format32bppArgb)
- 1bpp AND-маска (бит=1 → прозрачный пиксель) — обязательна, иначе GDI/`LoadIcon` игнорирует alpha-channel и рисует прозрачные пиксели чёрными

Без AND-маски: пиксели с A=0 отображаются как чёрный фон — иконка без прозрачности.

Источники иконок: `c:\pdf_ingest\DTMXtest\Assets\Icons\DTMX\`
- `dtmx_edit_16.png`, `dtmx_edit_32.png`, `dtmx_edit_64.png` — Edit (Правка)
- `dtmx_properties_16.png`, `dtmx_properties_32.png`, `dtmx_properties_64.png` — Explore (Свойства)
- `dtmx_connections_16.png`, `dtmx_connections_32.png`, `dtmx_connections_64.png` — Paths (Связи)
- `dtmx_test_16.png`, `dtmx_test_32.png`, `dtmx_test_64.png` — Ping (Тест)
- `dtmx_*_source.png` — исходники 1254×1254 с зелёным хромакей-фоном

Скрипт для пересборки ICO: `Make-Ico3.ps1` (в scratchpad сессии) — C#-класс `IcoBuilder2`, создаёт ICO с 4 размерами (16, 32, 48 из 64, 64) с правильной AND-маской.

### Критическая ошибка ZIP при патче CUIX

При перепаковке `.cuix` (ZIP-файл) через `ZipFile::CreateFromDirectory()` на Windows пути записываются с обратным слешем (`_rels\.rels`), тогда как nanoCAD требует прямой слеш (`_rels/.rels`). Результат — все иконки интерфейса исчезают.

**Правильный способ** — открыть ZIP в режиме Update и перезаписывать содержимое существующих записей, не изменяя имена путей:

```powershell
$archive = [System.IO.Compression.ZipFile]::Open($cuixPath, [System.IO.Compression.ZipArchiveMode]::Update)
# Перезаписывать через $entry.Open() + SetLength(0) + Write(), не через CreateFromDirectory
```

