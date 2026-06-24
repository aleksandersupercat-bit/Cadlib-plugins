import os
from pathlib import Path
import clr, System
root = Path(r"C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin")
for p in sorted(root.glob('*.dll')):
    try:
        an = System.Reflection.AssemblyName.GetAssemblyName(str(p))
        print(f"MANAGED|{p.name}|{an.FullName}")
    except Exception:
        pass
