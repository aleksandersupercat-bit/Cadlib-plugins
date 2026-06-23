# ModelStudioProbe

`ModelStudioProbe` is a separate experimental CADLib / Model Studio plugin DLL for trial-and-error UI probing.

What it does:

- adds menu item `Инструменты -> DTMXtest ModelStudio Probe`
- publishes two toolbar strategies through `GetToolbars()`
- tries to add a `DMTX` button into an existing `Разное` / `Misc` block at runtime
- writes a verbose log of discovered controls, properties, methods, and injection attempts

Build:

```powershell
dotnet build .\ModelStudioProbe.csproj -c Release
```

Install:

1. Copy `ModelStudioProbe.dll` into `C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin`.
2. Add `plugins_modelstudio_probe_snippet.xml` entry into `plugins.xml`.
3. Restart Model Studio CS / CADLib.
4. Run `Инструменты -> DTMXtest ModelStudio Probe -> Run probe + patch`.

Log location at runtime:

```text
%AppData%\CSoft\Model Studio CS\Library3D\DTMXtestLogs
```

Additional `NANOWATER` ribbon inspection script:

```powershell
.\Inspect-NanoWaterRibbon.ps1
```

It reads `Support\WATER\MSMAIN.cuix` and `Support\WATER\water.cuix`, then logs discovered tabs, panels, and command macros.

`NANOWATER` patcher:

```powershell
.\Patch-NanoWaterCuix.ps1 -DryRun
.\Patch-NanoWaterCuix.ps1
```

Default behavior:

- adds button `DMTX` into toolbar `MS_OTHER` in `MSMAIN.cuix`
- adds button `DMTX` into ribbon split `Разное` in `water.cuix`
- adds a new ribbon tab `DTMXtest` in `water.cuix`
- points the button to `PIPE_DUMP` until a custom command is implemented

Encoding repair for already corrupted `CUIX` labels:

```powershell
.\Repair-NanoWaterCuixEncoding.ps1 -DryRun
.\Repair-NanoWaterCuixEncoding.ps1
```
