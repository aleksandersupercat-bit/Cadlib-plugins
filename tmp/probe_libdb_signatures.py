from pathlib import Path
import clr, System
asm = System.Reflection.Assembly.LoadFrom(r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\mstManagedAPI.dll")
LibDatabase = [t for t in asm.GetExportedTypes() if t.FullName == 'mstManagedAPI.LibDatabase'][0]
for m in sorted(LibDatabase.GetMethods(), key=lambda x: x.Name):
    if m.Name in ('Connect','ConnectToDbUi','Disconnect','ShowModelStudioOptionsDlg','ShowModelStudioParametersDlg'):
        try:
            params = []
            for p in m.GetParameters():
                ptype = p.ParameterType.FullName or str(p.ParameterType)
                params.append(f"{ptype} {p.Name}")
            ret = m.ReturnType.FullName
            print(f"{m.Name} :: {ret}({', '.join(params)})")
        except Exception as ex:
            print('ERR', m.Name, ex)
