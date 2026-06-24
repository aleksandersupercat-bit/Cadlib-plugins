using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Text;
using HostMgd.ApplicationServices;
using HostMgd.EditorInput;
using Multicad;
using Multicad.DatabaseServices;
using Multicad.Runtime;
using Teigha.DatabaseServices;

[assembly: CommandClass(typeof(NanoDwgProbe.DtmxMsCommands))]

namespace NanoDwgProbe
{
    [ContainsCommands]
    public sealed class DtmxMsCommands : IExtensionApplication
    {
        public void Initialize()
        {
            ProbeLog.Write("Initialize");
        }

        public void Terminate()
        {
            ProbeLog.Write("Terminate");
        }

        [CommandMethod("DTMX_MS_DWGINFO", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public void DumpActiveDocumentInfo()
        {
            var editor = GetEditor();
            ProbeLog.Write("===== DTMX_MS_DWGINFO =====");

            try
            {
                Document doc = Application.DocumentManager.MdiActiveDocument;
                if (doc == null)
                {
                    WriteBoth(editor, "Active document not found.");
                    return;
                }

                Database db = doc.Database;
                WriteBoth(editor, "Document: " + SafeToString(() => doc.Name));
                WriteBoth(editor, "Database.Filename: " + SafeToString(() => db.Filename));
                WriteBoth(editor, "CurrentSpaceId: " + SafeToString(() => db.CurrentSpaceId.ToString()));

                using (Transaction tr = db.TransactionManager.StartTransaction())
                {
                    var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                    var model = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);
                    int count = 0;
                    foreach (ObjectId ignored in model)
                    {
                        count++;
                    }

                    WriteBoth(editor, "ModelSpace entity count: " + count);
                    tr.Commit();
                }
            }
            catch (Exception ex)
            {
                WriteBoth(editor, "ERROR: " + ex);
            }
        }

        [CommandMethod("DTMX_MS_DUMPSEL", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public void DumpSelectedModelStudioObject()
        {
            var editor = GetEditor();
            ProbeLog.Write("===== DTMX_MS_DUMPSEL =====");

            try
            {
                McObjectId objectId = McObjectManager.SelectObject("Выберите объект Model Studio");
                if (objectId.IsNull)
                {
                    WriteBoth(editor, "Selection cancelled.");
                    return;
                }

                DumpMcObject(editor, objectId, "selected");
            }
            catch (Exception ex)
            {
                WriteBoth(editor, "ERROR: " + ex);
            }
        }

        [CommandMethod("DTMX_MS_SETTAGNUMBER", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public void SetSelectedPartTagNumber()
        {
            var editor = GetEditor();
            ProbeLog.Write("===== DTMX_MS_SETTAGNUMBER =====");

            try
            {
                McObjectId objectId = McObjectManager.SelectObject("Выберите объект Model Studio для записи PART_TAGNUMBER");
                if (objectId.IsNull)
                {
                    WriteBoth(editor, "Selection cancelled.");
                    return;
                }

                PromptStringOptions opts = new PromptStringOptions("\nВведите значение PART_TAGNUMBER");
                opts.AllowSpaces = true;
                opts.UseDefaultValue = true;
                opts.DefaultValue = "DTMX";
                PromptResult res = editor.GetString(opts);
                if (res.Status != PromptStatus.OK && res.Status != PromptStatus.None)
                {
                    WriteBoth(editor, "Input cancelled.");
                    return;
                }

                string newValue = string.IsNullOrWhiteSpace(res.StringResult) ? "DTMX" : res.StringResult.Trim();
                bool success = TrySetAnyStringProperty(
                    objectId,
                    newValue,
                    editor,
                    "Идентификатор",
                    "Параметры изделия.Идентификатор",
                    "PART_TAGNUMBER",
                    "PART_TAG",
                    "Параметры изделия.Обозначение / Модель",
                    "Обозначение / Модель");

                WriteBoth(editor, "Set tag-like property result: " + success);
                DumpNamedProperties(
                    objectId,
                    editor,
                    "PART_TYPE",
                    "PART_TAG",
                    "PART_TAGNUMBER",
                    "Идентификатор",
                    "Параметры изделия.Идентификатор",
                    "Дополнительные параметры.Тип изделий",
                    "Параметры изделия.Наименование изделия",
                    "Параметры изделия.Обозначение / Модель");
            }
            catch (Exception ex)
            {
                WriteBoth(editor, "ERROR: " + ex);
            }
        }

        [CommandMethod("DTMX_MS_SETMODEL", CommandFlags.NoCheck | CommandFlags.NoPrefix)]
        public void SetSelectedModelDesignation()
        {
            var editor = GetEditor();
            ProbeLog.Write("===== DTMX_MS_SETMODEL =====");

            try
            {
                McObjectId objectId = McObjectManager.SelectObject("Выберите объект Model Studio для записи в Обозначение / Модель");
                if (objectId.IsNull)
                {
                    WriteBoth(editor, "Selection cancelled.");
                    return;
                }

                PromptStringOptions opts = new PromptStringOptions("\nВведите значение для Обозначение / Модель");
                opts.AllowSpaces = true;
                opts.UseDefaultValue = true;
                opts.DefaultValue = "DTMX";
                PromptResult res = editor.GetString(opts);
                if (res.Status != PromptStatus.OK && res.Status != PromptStatus.None)
                {
                    WriteBoth(editor, "Input cancelled.");
                    return;
                }

                string newValue = string.IsNullOrWhiteSpace(res.StringResult) ? "DTMX" : res.StringResult.Trim();
                bool success = TrySetAnyStringProperty(
                    objectId,
                    newValue,
                    editor,
                    "Параметры изделия.Обозначение / Модель",
                    "Обозначение / Модель");

                WriteBoth(editor, "Set model/designation result: " + success);
                DumpNamedProperties(
                    objectId,
                    editor,
                    "Параметры изделия.Наименование изделия",
                    "Параметры изделия.Обозначение / Модель");
            }
            catch (Exception ex)
            {
                WriteBoth(editor, "ERROR: " + ex);
            }
        }

        private static void DumpMcObject(Editor editor, McObjectId objectId, string label)
        {
            WriteBoth(editor, "Dump object [" + label + "]");
            WriteBoth(editor, "McObjectId: " + SafeToString(() => objectId.ToString()));
            WriteBoth(editor, "IsNull: " + objectId.IsNull);

            McObject obj = null;
            try
            {
                obj = objectId.GetObject();
                WriteBoth(editor, "McObject type: " + SafeTypeName(obj));
            }
            catch (Exception ex)
            {
                WriteBoth(editor, "GetObject failed: " + ex.Message);
            }

            try
            {
                using (McDbEntity dbEntity = objectId.GetObjectOfType<McDbEntity>())
                {
                    if (dbEntity == null)
                    {
                        WriteBoth(editor, "GetObjectOfType<McDbEntity> returned null.");
                        return;
                    }

                    WriteBoth(editor, "McDbEntity type: " + dbEntity.GetType().FullName);
                    DumpAllProperties(dbEntity, editor);
                    DumpNamedProperties(
                        objectId,
                        editor,
                        "PART_TYPE",
                        "PART_TAG",
                        "PART_TAGNUMBER",
                        "Идентификатор",
                        "Параметры изделия.Идентификатор",
                        "Дополнительные параметры.Тип изделий",
                        "Параметры изделия.Наименование изделия",
                        "Параметры изделия.Обозначение / Модель");
                }
            }
            catch (Exception ex)
            {
                WriteBoth(editor, "GetObjectOfType<McDbEntity> failed: " + ex);
            }
        }

        private static void DumpAllProperties(McDbEntity dbEntity, Editor editor)
        {
            McProperties props = dbEntity.GetProperties(McProperties.PropertyType.Object);
            PropertyDescriptorCollection descriptors = props.GetProperties();
            WriteBoth(editor, "Object property count: " + descriptors.Count);

            foreach (PropertyDescriptor descriptor in descriptors)
            {
                object value = null;
                string valueText;

                try
                {
                    value = descriptor.GetValue(dbEntity);
                    valueText = FormatValue(value);
                }
                catch (Exception ex)
                {
                    valueText = "<ERROR: " + ex.Message + ">";
                }

                WriteBoth(
                    editor,
                    "PROP | Name=" + descriptor.Name +
                    " | DisplayName=" + descriptor.DisplayName +
                    " | Type=" + SafeTypeName(descriptor.PropertyType) +
                    " | ReadOnly=" + descriptor.IsReadOnly +
                    " | Value=" + valueText
                );
            }
        }

        private static void DumpNamedProperties(McObjectId objectId, Editor editor, params string[] names)
        {
            using (McDbEntity dbEntity = objectId.GetObjectOfType<McDbEntity>())
            {
                if (dbEntity == null)
                {
                    WriteBoth(editor, "Named property dump skipped: McDbEntity is null.");
                    return;
                }

                McProperties props = dbEntity.GetProperties(McProperties.PropertyType.Object);
                PropertyDescriptorCollection descriptors = props.GetProperties();

                foreach (string name in names)
                {
                    PropertyDescriptor descriptor = FindDescriptor(descriptors, name);
                    if (descriptor == null)
                    {
                        WriteBoth(editor, "NAMED | " + name + " | not found");
                        continue;
                    }

                    object value = null;
                    string valueText;
                    try
                    {
                        value = descriptor.GetValue(dbEntity);
                        valueText = FormatValue(value);
                    }
                    catch (Exception ex)
                    {
                        valueText = "<ERROR: " + ex.Message + ">";
                    }

                    WriteBoth(
                        editor,
                        "NAMED | " + name +
                        " | DisplayName=" + descriptor.DisplayName +
                        " | Type=" + SafeTypeName(descriptor.PropertyType) +
                        " | ReadOnly=" + descriptor.IsReadOnly +
                        " | Value=" + valueText
                    );
                }
            }
        }

        private static bool TrySetAnyStringProperty(McObjectId objectId, string newValue, Editor editor, params string[] propertyNames)
        {
            using (McDbEntity dbEntity = objectId.GetObjectOfType<McDbEntity>())
            {
                if (dbEntity == null)
                {
                    WriteBoth(editor, "Write skipped: McDbEntity is null.");
                    return false;
                }

                McProperties props = dbEntity.GetProperties(McProperties.PropertyType.Object);
                PropertyDescriptorCollection descriptors = props.GetProperties();

                foreach (string propertyName in propertyNames)
                {
                    PropertyDescriptor descriptor = FindDescriptor(descriptors, propertyName);
                    if (descriptor == null)
                    {
                        WriteBoth(editor, "Write probe: property not found: " + propertyName);
                        continue;
                    }

                    if (descriptor.IsReadOnly)
                    {
                        WriteBoth(editor, "Write probe: property is read-only: " + propertyName);
                        continue;
                    }

                    object beforeValue = null;
                    object afterValue = null;
                    object owner = null;

                    try
                    {
                        beforeValue = descriptor.GetValue(dbEntity);
                    }
                    catch
                    {
                    }

                    owner = TryGetPropertyOwner(dbEntity, descriptor);

                    try
                    {
                        descriptor.SetValue(dbEntity, newValue);
                    }
                    catch (Exception ex)
                    {
                        WriteBoth(editor, "Write on dbEntity failed: " + ex.Message);
                    }

                    if (owner != null && !ReferenceEquals(owner, dbEntity))
                    {
                        try
                        {
                            descriptor.SetValue(owner, newValue);
                        }
                        catch (Exception ex)
                        {
                            WriteBoth(editor, "Write on owner failed: " + ex.Message);
                        }
                    }

                    try
                    {
                        dbEntity.Update();
                    }
                    catch (Exception ex)
                    {
                        WriteBoth(editor, "dbEntity.Update failed: " + ex.Message);
                    }

                    try
                    {
                        McObjectManager.UpdateAll();
                    }
                    catch (Exception ex)
                    {
                        WriteBoth(editor, "McObjectManager.UpdateAll failed: " + ex.Message);
                    }

                    try
                    {
                        afterValue = descriptor.GetValue(dbEntity);
                    }
                    catch
                    {
                    }

                    WriteBoth(
                        editor,
                        "WRITE | Requested=" + propertyName +
                        " | Actual=" + descriptor.Name +
                        " | DisplayName=" + descriptor.DisplayName +
                        " | OwnerType=" + SafeTypeName(owner) +
                        " | Before=" + FormatValue(beforeValue) +
                        " | After=" + FormatValue(afterValue)
                    );
                    return true;
                }

                WriteBoth(editor, "Write skipped: no writable matching property found.");
                return false;
            }
        }

        private static PropertyDescriptor FindDescriptor(PropertyDescriptorCollection descriptors, string nameOrDisplayName)
        {
            if (descriptors == null || string.IsNullOrWhiteSpace(nameOrDisplayName))
            {
                return null;
            }

            PropertyDescriptor direct = descriptors.Find(nameOrDisplayName, true);
            if (direct != null)
            {
                return direct;
            }

            foreach (PropertyDescriptor descriptor in descriptors)
            {
                if (string.Equals(descriptor.DisplayName, nameOrDisplayName, StringComparison.OrdinalIgnoreCase))
                {
                    return descriptor;
                }

                if (string.Equals(descriptor.Name, nameOrDisplayName, StringComparison.OrdinalIgnoreCase))
                {
                    return descriptor;
                }
            }

            return null;
        }

        private static object TryGetPropertyOwner(object component, PropertyDescriptor descriptor)
        {
            if (component == null || descriptor == null)
            {
                return null;
            }

            try
            {
                ICustomTypeDescriptor typed = component as ICustomTypeDescriptor;
                if (typed != null)
                {
                    object owner = typed.GetPropertyOwner(descriptor);
                    if (owner != null)
                    {
                        return owner;
                    }
                }
            }
            catch
            {
            }

            return component;
        }

        private static Editor GetEditor()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            return doc == null ? null : doc.Editor;
        }

        private static void WriteBoth(Editor editor, string message)
        {
            ProbeLog.Write(message);
            if (editor != null)
            {
                try
                {
                    editor.WriteMessage("\n" + message);
                }
                catch
                {
                }
            }
        }

        private static string SafeTypeName(object value)
        {
            if (value == null)
            {
                return "<null>";
            }

            Type type = value as Type;
            return type != null ? type.FullName : value.GetType().FullName;
        }

        private static string SafeToString(Func<object> getter)
        {
            try
            {
                object value = getter();
                return FormatValue(value);
            }
            catch (Exception ex)
            {
                return "<ERROR: " + ex.Message + ">";
            }
        }

        private static string FormatValue(object value)
        {
            if (value == null)
            {
                return "<null>";
            }

            if (value is string)
            {
                return (string)value;
            }

            return Convert.ToString(value);
        }
    }

    internal static class ProbeLog
    {
        private static readonly object SyncRoot = new object();
        private static readonly string LogPath = CreateLogPath();

        public static void Write(string message)
        {
            lock (SyncRoot)
            {
                File.AppendAllText(
                    LogPath,
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " | " + message + Environment.NewLine,
                    Encoding.UTF8
                );
            }
        }

        private static string CreateLogPath()
        {
            string root = Path.Combine(@"C:\pdf_ingest\DTMXtest", "LOG");
            Directory.CreateDirectory(root);
            return Path.Combine(root, "NanoDwgProbe_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".txt");
        }
    }
}
