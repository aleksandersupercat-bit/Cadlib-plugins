using System;
using System.Runtime.InteropServices;
using System.Reflection;
using SCXComponentsLibLib;

namespace DtmxSet
{
    class Program
    {
        const string TARGET_PARAM = "PART_TAGNUMBER";
        const string TARGET_VALUE = "DTMX_NET";

        static readonly BindingFlags GET = BindingFlags.GetProperty | BindingFlags.InvokeMethod
                                         | BindingFlags.Public | BindingFlags.Instance;
        static readonly BindingFlags CALL = BindingFlags.InvokeMethod
                                          | BindingFlags.Public | BindingFlags.Instance;

        static object Invoke(object obj, string name, params object[] args)
            => obj.GetType().InvokeMember(name, GET | CALL, null, obj, args.Length == 0 ? null : args);

        static int Main(string[] args)
        {
            string progId = "nanoCADx64.Application.24.0";
            object app = null;
            try
            {
                app = Marshal.GetActiveObject(progId);
            }
            catch (COMException ex)
            {
                Console.Error.WriteLine($"GetActiveObject({progId}) failed: {ex.Message}");
                return 1;
            }

            object doc = Invoke(app, "ActiveDocument");
            if (doc == null) { Console.Error.WriteLine("ActiveDocument is null"); return 1; }
            Console.WriteLine($"Document: {Invoke(doc, "Name")}");

            // Получаем выделение
            object sel = null;
            foreach (var selProp in new[] { "PickfirstSelectionSet", "ActiveSelectionSet" })
            {
                try
                {
                    sel = Invoke(doc, selProp);
                    int cnt = (int)Invoke(sel, "Count");
                    if (cnt > 0) { Console.WriteLine($"{selProp}: {cnt} objects"); break; }
                }
                catch { sel = null; }
            }
            if (sel == null) { Console.Error.WriteLine("No selection"); return 1; }

            int total = (int)Invoke(sel, "Count");
            int changed = 0, skipped = 0, failed = 0;

            // Загружаем тип IPEParameters для typed cast
            Type ipeType = typeof(IPEParameters);

            for (int i = 0; i < total; i++)
            {
                object ent = null;
                try { ent = Invoke(sel, "Item", i); }
                catch (Exception ex) { Console.Error.WriteLine($"  [{i}] Item error: {ex.Message}"); failed++; continue; }

                string objName = "";
                try { objName = Invoke(ent, "ObjectName")?.ToString() ?? ""; } catch { }
                if (!objName.Equals("vcssubsegment", StringComparison.OrdinalIgnoreCase))
                { skipped++; continue; }

                string handle = "";
                try { handle = Invoke(ent, "Handle")?.ToString() ?? ""; } catch { }

                try
                {
                    object element = Invoke(ent, "Element");
                    object paramsObj = Invoke(element, "Parameters");

                    // Читаем текущее значение
                    string current = null;
                    try { current = element.GetType().InvokeMember("GetValue", CALL, null, element,
                              new object[] { TARGET_PARAM })?.ToString(); }
                    catch { }

                    if (current == TARGET_VALUE)
                    {
                        Console.WriteLine($"  [{handle}] already {TARGET_VALUE} — skip");
                        skipped++;
                        continue;
                    }

                    // Путь 1: typed IPEParameters через GetTypedObjectForIUnknown
                    // (работает только in-process, но пробуем на случай будущего in-process запуска)
                    bool done = false;
                    IntPtr punk = Marshal.GetIUnknownForObject(paramsObj);
                    try
                    {
                        var typed = (IPEParameters)Marshal.GetTypedObjectForIUnknown(punk, ipeType);
                        typed.Set(TARGET_PARAM, TARGET_VALUE, "");
                        done = true;
                        Console.WriteLine($"  [{handle}] → {TARGET_VALUE}  [typed IPEParameters.Set]");
                    }
                    catch { }
                    finally { Marshal.Release(punk); }

                    // Путь 2: IDispatch SetParameter (рабочий путь)
                    if (!done)
                    {
                        paramsObj.GetType().InvokeMember("SetParameter", CALL, null, paramsObj,
                            new object[] { TARGET_PARAM, TARGET_VALUE, "", "" });
                        Console.WriteLine($"  [{handle}] → {TARGET_VALUE}  [IDispatch SetParameter]");
                    }

                    // Обновляем объект в чертеже
                    try { ent.GetType().InvokeMember("Update", CALL, null, ent, null); } catch { }

                    changed++;
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"  [{handle}] ERROR: {ex.Message}");
                    failed++;
                }
            }

            // Регенерация чертежа
            if (changed > 0)
            {
                try { doc.GetType().InvokeMember("Regen", CALL, null, doc, new object[] { 1 }); }
                catch { }
            }

            Console.WriteLine($"\nDone: changed={changed}, skipped={skipped}, failed={failed}");
            return failed > 0 ? 2 : 0;
        }
    }
}
