# DTMXtest CADLib Plugin

DTMXtest is a C# CADLib plugin for Model Studio CS / CADLib. It adds a menu item:

```text
Инструменты -> DTMXtest
```

The plugin opens a small Windows Forms dialog with selection inspection and `PART_TYPE` summary tools.

## Build

The project targets .NET Framework 4.8 and expects CADLib / Model Studio CS assemblies to be installed locally.

The referenced assemblies are configured in `DTMXtest.csproj`, for example:

```xml
<HintPath>C:\Program Files\CSoft\Model Studio CS\3.1\MIA\bin\CADLibKernel.dll</HintPath>
```

Build:

```powershell
dotnet build .\DTMXtest.csproj -c Release
```

## Install

1. Build `DTMXtest.dll`.
2. Copy the DLL to the CADLib / Model Studio CS `MIA\bin` folder.
3. Add this line to `plugins_cadlib.xml` before `</Plugins>`:

```xml
<Plugin name="DTMXtest.dll"/>
```

4. Restart CADLib / Model Studio CS.
5. Open `Инструменты -> DTMXtest`.

## Files

- `DTMXtest.cs` - plugin source code.
- `DTMXtest.csproj` - .NET Framework project file.
- `plugins_cadlib_snippet.xml` - plugin registration snippet.
