using System;
using System.Linq;
using System.Reflection;

var asm = Assembly.LoadFrom(@"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll");
string[] names = {
  "mstManagedAPI.CElement",
  "mstManagedAPI.CElementMngd",
  "mstManagedAPI.CMngdParam",
  "mstManagedAPI.CParam",
  "mstManagedAPI.LibDatabase",
  "mstManagedAPI.ProjectDBUtils",
  "MStudioData.IElement",
  "MStudioData.IParam",
  "MStudioData.IParamDefs",
  "MStudioDB.IDataBase",
  "MStudioDB.IElementData"
};
foreach (var name in names)
{
    var t = asm.GetType(name);
    Console.WriteLine($"=== {name} ===");
    if (t == null) { Console.WriteLine("TYPE NOT FOUND\n"); continue; }
    Console.WriteLine($"BaseType: {t.BaseType}");
    foreach (var iface in t.GetInterfaces()) Console.WriteLine($"IFACE {iface.FullName}");
    foreach (var ctor in t.GetConstructors(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance)) Console.WriteLine($"CTOR {ctor}");
    foreach (var prop in t.GetProperties(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static).OrderBy(p=>p.Name))
    {
        if (prop.Name.IndexOf("param", StringComparison.OrdinalIgnoreCase)>=0 || prop.Name.IndexOf("element", StringComparison.OrdinalIgnoreCase)>=0 || prop.Name.IndexOf("object", StringComparison.OrdinalIgnoreCase)>=0 || prop.Name.IndexOf("id", StringComparison.OrdinalIgnoreCase)>=0 || prop.Name.IndexOf("guid", StringComparison.OrdinalIgnoreCase)>=0 || prop.Name.IndexOf("uid", StringComparison.OrdinalIgnoreCase)>=0 || prop.Name.IndexOf("name", StringComparison.OrdinalIgnoreCase)>=0 || prop.Name.IndexOf("value", StringComparison.OrdinalIgnoreCase)>=0)
            Console.WriteLine($"PROP {prop.PropertyType.FullName} {prop.Name}");
    }
    foreach (var m in t.GetMethods(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static).OrderBy(m=>m.Name))
    {
        if (m.IsSpecialName) continue;
        var n=m.Name;
        if (new[]{"param","element","object","id","guid","uid","name","value","open","find","get","set","create","load","from","handle"}.Any(k=>n.IndexOf(k,StringComparison.OrdinalIgnoreCase)>=0))
        {
            var pars = string.Join(", ", m.GetParameters().Select(p => (p.ParameterType.FullName ?? p.ParameterType.Name)+" "+p.Name));
            Console.WriteLine($"METHOD {(m.IsStatic?"STATIC":"INST")} {(m.ReturnType.FullName ?? m.ReturnType.Name)} {m.Name}({pars})");
        }
    }
    Console.WriteLine();
}
