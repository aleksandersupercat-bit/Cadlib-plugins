// DtmxNrx.cpp вЂ” NRX C++ plugin РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ РїР°СЂР°РјРµС‚СЂР°РјРё Model Studio
// v9: С‡РёСЃС‚С‹Р№ C++ Р±РµР· COM вЂ” MAPI (gpMcNativeGate в†’ IMcParametricEnt::setParams)

#include "stdafx.h"
#include <psapi.h>
#include "IContext.h"
#include "McsUtils.h"
#include "applicationDB.h"
#include <set>
#pragma comment(lib, "Gdi32.lib")
#pragma comment(lib, "Psapi.lib")
#pragma comment(lib, "User32.lib")

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// Р›РѕРіРёСЂРѕРІР°РЅРёРµ (UTF-8 СЃ BOM)
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

static const wchar_t LOG_PATH[] = L"C:\\Users\\atsarkov\\Desktop\\dtmx_nrx_log.txt";

static void LogClear()
{
    HANDLE hf = ::CreateFileW(LOG_PATH, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, 0, nullptr);
    if (hf != INVALID_HANDLE_VALUE) {
        const unsigned char bom[] = {0xEF, 0xBB, 0xBF};
        DWORD w; ::WriteFile(hf, bom, 3, &w, nullptr);
        ::CloseHandle(hf);
    }
}

static void Log(const wchar_t* msg)
{
    SYSTEMTIME st; ::GetLocalTime(&st);
    wchar_t wbuf[4096];
    int wn = ::swprintf_s(wbuf, L"%02d:%02d:%02d %s\n", st.wHour, st.wMinute, st.wSecond, msg);
    char utf8[8192];
    int un = ::WideCharToMultiByte(CP_UTF8, 0, wbuf, wn, utf8, (int)sizeof(utf8)-1, nullptr, nullptr);
    if (un <= 0) return;
    HANDLE hf = ::CreateFileW(LOG_PATH, GENERIC_WRITE, FILE_SHARE_READ,
                               nullptr, OPEN_ALWAYS, 0, nullptr);
    if (hf != INVALID_HANDLE_VALUE) {
        ::SetFilePointer(hf, 0, nullptr, FILE_END);
        DWORD w; ::WriteFile(hf, utf8, (DWORD)un, &w, nullptr);
        ::CloseHandle(hf);
    }
}
static void Log(const std::wstring& s) { Log(s.c_str()); }
static void Echo(const std::wstring& s)
{
    Log(s);
    ::acutPrintf(L"\n%ls", s.c_str());
}
static std::wstring Ptr(const void* p);
static void EchoApiPtr(const wchar_t* owner, const wchar_t* name, const void* ptr, const wchar_t* note)
{
    std::wstring line = L"[";
    line += owner;
    line += L"] ";
    line += name;
    line += L"=";
    line += Ptr((void*)ptr);
    if (note && note[0]) {
        line += L" | ";
        line += note;
    }
    Echo(line);
}
static std::wstring Hex(HRESULT hr) { wchar_t b[16]; ::swprintf_s(b,L"0x%08X",(unsigned)hr); return b; }
static std::wstring Dec(DWORD value) { wchar_t b[32]; ::swprintf_s(b, L"%lu", (unsigned long)value); return b; }
static std::wstring Ptr(const void* p) {
    wchar_t b[32]; ::swprintf_s(b, L"0x%016llX", (unsigned long long)(uintptr_t)p); return b;
}
static std::wstring GuidStr(REFGUID guid)
{
    wchar_t b[64] = {};
    ::swprintf_s(
        b,
        L"{%08lX-%04hX-%04hX-%02hhX%02hhX-%02hhX%02hhX%02hhX%02hhX%02hhX%02hhX}",
        guid.Data1, guid.Data2, guid.Data3,
        guid.Data4[0], guid.Data4[1], guid.Data4[2], guid.Data4[3],
        guid.Data4[4], guid.Data4[5], guid.Data4[6], guid.Data4[7]);
    return b;
}
static std::wstring WidStr(const mcsWorkID& wid)
{
    return GuidStr(wid.ID);
}
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

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// GetProcAddress-РѕР±С‘СЂС‚РєРё (SDK 26.0 vs nanoCAD 24.1 ABI mismatch)
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

static int NCAD_SSLength(ads_name ss, long* pLen)
{
    typedef int(*PFN)(ads_name,long*);
    static PFN fn = nullptr;
    if (!fn) {
        HMODULE h = ::GetModuleHandleW(L"NrxHostGate.dll");
        fn = h ? (PFN)::GetProcAddress(h,"?ncedSSLength@@YAHQEB_JPEAJ@Z") : nullptr;
    }
    return fn ? fn(ss,pLen) : RTERROR;
}

static int NCAD_SSName(ads_name ss, long i, ads_name result)
{
    typedef int(*PFN)(ads_name,long,ads_name);
    static PFN fn = nullptr;
    if (!fn) {
        HMODULE h = ::GetModuleHandleW(L"NrxHostGate.dll");
        fn = h ? (PFN)::GetProcAddress(h,"?ncedSSName@@YAHQEB_JJQEA_J@Z") : nullptr;
    }
    return fn ? fn(ss,i,result) : RTERROR;
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// MAPI вЂ” РїРѕР»СѓС‡РёС‚СЊ IMcNativeGate
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

static IMcNativeGate* GetNativeGate()
{
    HMODULE h = ::GetModuleHandleA("McTyp.dll");
    if (!h) return nullptr;
    auto** pp = (IMcNativeGate**)::GetProcAddress(h, "gpMcNativeGate");
    return pp ? *pp : nullptr;
}

class CElement;
class linCSParametricSolidBase;

typedef linCSParametricSolidBase* (__cdecl* PFN_getParametricInterface)(void* pDbObject);
typedef CElement* (__cdecl* PFN_getRootElementP)(void* pThis);
typedef void (__cdecl* PFN_setRootElementP)(void* pThis, CElement* pElement);
typedef void (__cdecl* PFN_setParameter4)(void* pThis,
    const wchar_t* p1, const wchar_t* p2, const wchar_t* p3, const wchar_t* p4);
typedef int  (__cdecl* PFN_getParamsCount)(void* pThis);
typedef void*(__cdecl* PFN_getParameterByIndex)(void* pThis, int index);
typedef const wchar_t* (__cdecl* PFN_subEntParameterStr)(
    const void* pElement, const wchar_t* name, bool bDefault, bool bFormula);
typedef long long (__cdecl* PFN_ceGetChildCount)(const void* pThis);
typedef CElement* (__cdecl* PFN_ceGetChildByIndex)(const void* pThis, long long index);
typedef const wchar_t* (__cdecl* PFN_ceGetName)(const void* pThis);
typedef int (__cdecl* PFN_ceGetId)(const void* pThis);
typedef int (__cdecl* PFN_ceGetLevel)(const void* pThis);
typedef long long (__cdecl* PFN_cpoGetParamsCount)(const void* pThis);
typedef void* (__cdecl* PFN_cpoGetParameterByIndex)(const void* pThis, long long index);
typedef void (__cdecl* PFN_cpoSetParameter4)(void* pThis,
    const wchar_t* p1, const wchar_t* p2, const wchar_t* p3, const wchar_t* p4);
typedef const wchar_t* (__cdecl* PFN_cpGetName)(const void* pThis);
typedef const wchar_t* (__cdecl* PFN_cpGetValue)(const void* pThis);
typedef const wchar_t* (__cdecl* PFN_cpGetComment)(const void* pThis);
typedef void (__cdecl* PFN_cpSetValue)(void* pThis, const wchar_t* value);
typedef void (__cdecl* PFN_cpSetComment)(void* pThis, const wchar_t* value);
typedef void (__cdecl* PFN_cpSetValueComment)(void* pThis, const wchar_t* value);

struct UnitsCsApi
{
    HMODULE module = nullptr;
    PFN_getParametricInterface getParametricInterface = nullptr;
    PFN_getRootElementP getRootElementP = nullptr;
    PFN_setRootElementP setRootElementP = nullptr;
    PFN_setParameter4 setParameter4 = nullptr;
    PFN_getParamsCount getParamsCount = nullptr;
    PFN_getParameterByIndex getParameterByIndex = nullptr;
    PFN_subEntParameterStr subEntParameterStr = nullptr;
    PFN_ceGetChildCount ceGetChildCount = nullptr;
    PFN_ceGetChildByIndex ceGetChildByIndex = nullptr;
    PFN_ceGetName ceGetName = nullptr;
    PFN_ceGetId ceGetId = nullptr;
    PFN_ceGetLevel ceGetLevel = nullptr;
    PFN_cpoGetParamsCount cpoGetParamsCount = nullptr;
    PFN_cpoGetParameterByIndex cpoGetParameterByIndex = nullptr;
    PFN_cpoSetParameter4 cpoSetParameter4 = nullptr;
    PFN_cpGetName cpGetName = nullptr;
    PFN_cpGetValue cpGetValue = nullptr;
    PFN_cpGetComment cpGetComment = nullptr;
    PFN_cpSetValue cpSetValue = nullptr;
    PFN_cpSetComment cpSetComment = nullptr;
    PFN_cpSetValueComment cpSetValueComment = nullptr;
};

static HMODULE FindLoadedModuleLike(const wchar_t* token)
{
    HMODULE modules[1024] = {};
    DWORD needed = 0;
    if (!::EnumProcessModules(::GetCurrentProcess(), modules, sizeof(modules), &needed))
        return nullptr;

    const DWORD count = needed / sizeof(HMODULE);
    for (DWORD i = 0; i < count; ++i) {
        wchar_t path[MAX_PATH] = {};
        if (!::GetModuleFileNameExW(::GetCurrentProcess(), modules[i], path, MAX_PATH))
            continue;
        if (_wcsicmp(path, token) == 0) return modules[i];
        const wchar_t* fileName = wcsrchr(path, L'\\');
        fileName = fileName ? fileName + 1 : path;
        if (_wcsicmp(fileName, token) == 0) return modules[i];
        if (wcsstr(path, token) != nullptr) return modules[i];
    }
    return nullptr;
}

static bool LoadUnitsCsApi(UnitsCsApi& api)
{
    api = UnitsCsApi{};
    const wchar_t* unitsPath =
        L"C:\\Program Files\\CSoft\\Model Studio CS\\NANOWATER\\bin\\nanoCAD241\\UnitsCS.nrx";

    api.module = ::GetModuleHandleW(L"UnitsCS.nrx");
    if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS.nrx");
    if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS");
    Echo(L"[UnitsCS] preloaded handle=" + Ptr(api.module));
    if (!api.module) {
        IMcContext* pContext = MCS_GetContextDyn();
        Echo(L"[UnitsCS] MCS_GetContextDyn()=" + Ptr(pContext));
        if (pContext) {
            HRESULT hrLoad = pContext->LoadModule(unitsPath);
            Echo(L"[UnitsCS] IMcContext::LoadModule(path) hr=" + Hex(hrLoad));
            if (!api.module) {
                hrLoad = pContext->LoadModule(L"UnitsCS.nrx");
                Echo(L"[UnitsCS] IMcContext::LoadModule(short) hr=" + Hex(hrLoad));
            }
        }
        api.module = ::GetModuleHandleW(L"UnitsCS.nrx");
        if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS.nrx");
        if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS");
        Echo(L"[UnitsCS] after IMcContext handle=" + Ptr(api.module));
    }
    if (!api.module) {
        mcsModuleInfo mi = {};
        mi.csModuleName = unitsPath;
        mi.iForceUnload = 0;
        mi.fDisableAlienInstanceCheck = true;
        mcsModuleInfoArray arr;
        arr.Add(mi);
        DWORD_PTR ldrHandle = 0;
        HRESULT hrMods = mcsLoadModules(ldrHandle, arr, nullptr, nullptr, true);
        Echo(L"[UnitsCS] mcsLoadModules(path) hr=" + Hex(hrMods) + L" handle=" + Ptr((void*)ldrHandle));
        if (arr.GetSize() > 0) {
            Echo(L"[UnitsCS] mcsLoadModules result hModule=" + Ptr(arr[0].hModule) +
                L" dwSize=" + Dec(arr[0].dwSize));
        }
        api.module = ::GetModuleHandleW(L"UnitsCS.nrx");
        if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS.nrx");
        if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS");
        Echo(L"[UnitsCS] after mcsLoadModules handle=" + Ptr(api.module));
    }
    if (!api.module) {
        NcRxDynamicLinker* pLdr = GetDynamicLinker();
        Echo(L"[UnitsCS] GetDynamicLinker()=" + Ptr(pLdr));
        if (pLdr) {
            bool ok = pLdr->loadModule(unitsPath, true, false);
            Echo(L"[UnitsCS] NcRxDynamicLinker::loadModule(path)=" + std::to_wstring(ok ? 1 : 0));
            if (!ok) {
                ok = pLdr->loadModule(L"UnitsCS.nrx", true, false);
                Echo(L"[UnitsCS] NcRxDynamicLinker::loadModule(short)=" + std::to_wstring(ok ? 1 : 0));
            }
        }
        api.module = ::GetModuleHandleW(L"UnitsCS.nrx");
        if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS.nrx");
        if (!api.module) api.module = FindLoadedModuleLike(L"UnitsCS");
        Echo(L"[UnitsCS] after dynamic linker handle=" + Ptr(api.module));
    }
    if (!api.module) {
        ::SetLastError(0);
        api.module = ::LoadLibraryExW(unitsPath, nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
        DWORD gle = ::GetLastError();
        Echo(L"[UnitsCS] LoadLibraryExW(path)=" + Ptr(api.module) + L" gle=" + Dec(gle));
    }
    if (!api.module) {
        Echo(L"[UnitsCS] module not found/loaded");
        return false;
    }

    Echo(L"[UnitsCS] module handle=" + Ptr(api.module));
    HMODULE hMstudioData = ::GetModuleHandleW(L"mstudioData.dll");
    if (!hMstudioData) hMstudioData = FindLoadedModuleLike(L"mstudioData.dll");
    Echo(L"[mstudioData] module handle=" + Ptr(hMstudioData));

    api.getParametricInterface =
        (PFN_getParametricInterface)::GetProcAddress(
            api.module,
            "?getParametricInterface@linCSParametricWrapper@@SAPEAVlinCSParametricSolidBase@@PEAVNcDbObject@@@Z");
    api.getRootElementP =
        (PFN_getRootElementP)::GetProcAddress(
            api.module,
            "?getRootElementP@linCSParametricSolidBase@@QEAAPEAVCElement@@XZ");
    api.setRootElementP =
        (PFN_setRootElementP)::GetProcAddress(
            api.module,
            "?setRootElementP@linCSParametricSolidBase@@QEAAXPEAVCElement@@@Z");
    api.setParameter4 =
        (PFN_setParameter4)::GetProcAddress(
            api.module,
            "?SetParameter@linCSParametricSolidBase@@QEAAXPEB_W000@Z");
    api.getParamsCount =
        (PFN_getParamsCount)::GetProcAddress(
            api.module,
            "?GetParamsCount@linCSParametricSolidBase@@QEAAHXZ");
    api.getParameterByIndex =
        (PFN_getParameterByIndex)::GetProcAddress(
            api.module,
            "?GetParameter@linCSParametricSolidBase@@QEBAPEAVCParam@@H@Z");
    api.subEntParameterStr =
        (PFN_subEntParameterStr)::GetProcAddress(
            api.module,
            "?SubEnt_ParameterLPCSTR@linCSParametricSolidBase@@SAPEB_WPEBVCElement@@PEB_W_N1@Z");
    api.ceGetChildCount =
        (PFN_ceGetChildCount)::GetProcAddress(
            hMstudioData,
            "?GetChildCount@CElement@@QEBA_JXZ");
    api.ceGetChildByIndex =
        (PFN_ceGetChildByIndex)::GetProcAddress(
            hMstudioData,
            "?GetChild@CElement@@QEBAPEAV1@_J@Z");
    api.ceGetName =
        (PFN_ceGetName)::GetProcAddress(
            hMstudioData,
            "?GetName@CElement@@QEBAPEB_WXZ");
    api.ceGetId =
        (PFN_ceGetId)::GetProcAddress(
            hMstudioData,
            "?GetId@CElement@@QEBAHXZ");
    api.ceGetLevel =
        (PFN_ceGetLevel)::GetProcAddress(
            hMstudioData,
            "?GetLevel@CElement@@QEBAHXZ");
    api.cpoGetParamsCount =
        (PFN_cpoGetParamsCount)::GetProcAddress(
            hMstudioData,
            "?GetParamsCount@CParamsOwner@@QEBA_JXZ");
    api.cpoGetParameterByIndex =
        (PFN_cpoGetParameterByIndex)::GetProcAddress(
            hMstudioData,
            "?GetParameter@CParamsOwner@@QEBAPEAVCParam@@_J@Z");
    api.cpoSetParameter4 =
        (PFN_cpoSetParameter4)::GetProcAddress(
            hMstudioData,
            "?SetParameter@CParamsOwner@@QEAAXPEB_W000@Z");
    api.cpGetName =
        (PFN_cpGetName)::GetProcAddress(
            hMstudioData,
            "?getName@CParam@@QEBAPEB_WXZ");
    api.cpGetValue =
        (PFN_cpGetValue)::GetProcAddress(
            hMstudioData,
            "?getValue@CParam@@QEBAPEB_WXZ");
    api.cpGetComment =
        (PFN_cpGetComment)::GetProcAddress(
            hMstudioData,
            "?getComment@CParam@@QEBAPEB_WXZ");
    api.cpSetValue =
        (PFN_cpSetValue)::GetProcAddress(
            hMstudioData,
            "?setValue@CParam@@QEAAXPEB_W@Z");
    api.cpSetComment =
        (PFN_cpSetComment)::GetProcAddress(
            hMstudioData,
            "?setComment@CParam@@QEAAXPEB_W@Z");
    api.cpSetValueComment =
        (PFN_cpSetValueComment)::GetProcAddress(
            hMstudioData,
            "?setValueComment@CParam@@QEAAXPEB_W@Z");

    EchoApiPtr(L"UnitsCS", L"getParametricInterface", api.getParametricInterface, L"получить параметрический интерфейс из выбранного DWG-объекта");
    EchoApiPtr(L"UnitsCS", L"getRootElementP", api.getRootElementP, L"получить корневой CElement текущего элемента Model Studio");
    EchoApiPtr(L"UnitsCS", L"setRootElementP", api.setRootElementP, L"назначить другой корневой CElement; служебная операция");
    EchoApiPtr(L"UnitsCS", L"setParameter4", api.setParameter4, L"записать параметр по имени: значение + 2 текстовых комментария");
    EchoApiPtr(L"UnitsCS", L"getParamsCount", api.getParamsCount, L"сколько параметров у параметрического интерфейса");
    EchoApiPtr(L"UnitsCS", L"getParameterByIndex", api.getParameterByIndex, L"получить параметр интерфейса по индексу");
    EchoApiPtr(L"UnitsCS", L"subEntParameterStr", api.subEntParameterStr, L"прочитать строковое значение параметра у sub-element / CElement");
    EchoApiPtr(L"UnitsCS", L"CElement::GetChildCount", api.ceGetChildCount, L"количество дочерних узлов CElement");
    EchoApiPtr(L"UnitsCS", L"CElement::GetChild(index)", api.ceGetChildByIndex, L"получить дочерний узел CElement по индексу");
    EchoApiPtr(L"UnitsCS", L"CElement::GetName", api.ceGetName, L"имя узла CElement, например 3D или CONE");
    EchoApiPtr(L"UnitsCS", L"CElement::GetId", api.ceGetId, L"внутренний id узла CElement");
    EchoApiPtr(L"UnitsCS", L"CElement::GetLevel", api.ceGetLevel, L"уровень узла в нативном дереве CElement");
    EchoApiPtr(L"UnitsCS", L"CParamsOwner::GetParamsCount", api.cpoGetParamsCount, L"сколько owner-параметров у узла/интерфейса");
    EchoApiPtr(L"UnitsCS", L"CParamsOwner::GetParameter(index)", api.cpoGetParameterByIndex, L"получить owner-параметр по индексу");
    EchoApiPtr(L"UnitsCS", L"CParamsOwner::SetParameter4", api.cpoSetParameter4, L"записать owner-параметр по имени через CParamsOwner");
    EchoApiPtr(L"UnitsCS", L"CParam::getName", api.cpGetName, L"внутреннее имя параметра, например PART_TAGNUMBER");
    EchoApiPtr(L"UnitsCS", L"CParam::getValue", api.cpGetValue, L"текущее значение параметра");
    EchoApiPtr(L"UnitsCS", L"CParam::getComment", api.cpGetComment, L"человекочитаемая подпись/комментарий параметра");
    EchoApiPtr(L"UnitsCS", L"CParam::setValue", api.cpSetValue, L"записать новое значение параметра");
    EchoApiPtr(L"UnitsCS", L"CParam::setComment", api.cpSetComment, L"записать общий комментарий/подпись параметра");
    EchoApiPtr(L"UnitsCS", L"CParam::setValueComment", api.cpSetValueComment, L"записать комментарий именно к значению параметра");

    return api.getParametricInterface &&
           api.getRootElementP &&
           api.setRootElementP &&
           api.setParameter4;
}

static bool GetSingleSelectedObject(AcDbObjectId& oid)
{
    oid.setNull();
    ads_name ss = {};
    bool gotSS = (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) {
        gotSS = (::acedSSGet(L"I", nullptr, nullptr, nullptr, ss) == RTNORM);
    }
    if (!gotSS) {
        gotSS = (::acedSSGet(L"P", nullptr, nullptr, nullptr, ss) == RTNORM);
        if (gotSS) Echo(L"[SELECT] Using previous selection set.");
    }
    if (!gotSS) {
        Echo(L"[SELECT] No implied selection found; falling back to ssget prompt.");
        gotSS = (::acedSSGet(nullptr, nullptr, nullptr, nullptr, ss) == RTNORM);
    }
    if (!gotSS) {
        Echo(L"[SELECT] No selection acquired.");
        ::acutPrintf(L"\nNo selection acquired.\n");
        return false;
    }

    long len = 0;
    if (NCAD_SSLength(ss, &len) != RTNORM || len <= 0) {
        Echo(L"[SELECT] PICKFIRST exists but selection length is zero.");
        return false;
    }

    if (len > 1) {
        Echo(L"[SELECT] More than one object selected; command will use the first one.");
    }

    ads_name en = {};
    if (NCAD_SSName(ss, 0, en) != RTNORM) {
        Echo(L"[SELECT] Failed to read first entity from PICKFIRST.");
        return false;
    }

    Acad::ErrorStatus es = ::acdbGetObjectId(oid, en);
    Echo(L"[SELECT] acdbGetObjectId status=" + std::to_wstring((int)es));
    return (es == Acad::eOk);
}

static std::vector<AcDbObjectId> GetSelectedObjects()
{
    std::vector<AcDbObjectId> result;
    ads_name ss = {};
    bool gotSS = (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) gotSS = (::acedSSGet(L"I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) {
        gotSS = (::acedSSGet(L"P", nullptr, nullptr, nullptr, ss) == RTNORM);
        if (gotSS) Echo(L"[SELECT] Using previous selection set.");
    }
    if (!gotSS) return result;

    long len = 0;
    if (NCAD_SSLength(ss, &len) != RTNORM || len <= 0) {
        ::acedSSFree(ss);
        return result;
    }

    for (long i = 0; i < len; ++i) {
        ads_name en = {};
        if (NCAD_SSName(ss, i, en) != RTNORM) continue;
        AcDbObjectId oid;
        if (::acdbGetObjectId(oid, en) == Acad::eOk) result.push_back(oid);
    }
    ::acedSSFree(ss);
    return result;
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// MAPI вЂ” РїРµСЂРµС‡РёСЃР»РёС‚СЊ РїР°СЂР°РјРµС‚СЂС‹ в†’ std::map
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

static void MapiEnumParams(IMcParametricEnt* pPE,
                            std::map<std::wstring, std::wstring>& out)
{
    mcsExValueArray params;
    if (FAILED(pPE->getParams(params))) return;
    for (int i = 0; i < params.GetSize(); ++i) {
        const exValue& ev = params[i];
        if (ev.strParName.IsEmpty()) continue;
        std::wstring name((LPCTSTR)ev.strParName);
        std::wstring val;
        if (ev.val.m_ValType == MCSSTR) {
            LPCTSTR s = ev.val.getStr();
            if (s) val = s;
        } else if (ev.val.m_ValType == MCSNUM) {
            wchar_t buf[64]; ::swprintf_s(buf, L"%g", ev.val.m_num);
            val = buf;
        }
        if (!name.empty()) out[name] = val;
    }
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// MAPI вЂ” СѓСЃС‚Р°РЅРѕРІРёС‚СЊ РѕРґРёРЅ РїР°СЂР°РјРµС‚СЂ
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

static HRESULT MapiSetParam(IMcParametricEnt* pPE,
                             LPCTSTR paramName, LPCTSTR paramValue)
{
    mcsExValueArray params;
    HRESULT hr = pPE->getParams(params);
    if (FAILED(hr)) return hr;

    exValue ev;
    ev.strParName = paramName;
    ev.setValue(paramValue);    // в†’ m_ValType = MCSSTR
    ev.lFlag = MCPAR_PUBLIC;
    params.AddDistinctByName(ev, true); // РґРѕР±Р°РІРёС‚СЊ РёР»Рё РїРµСЂРµР·Р°РїРёСЃР°С‚СЊ

    return pPE->setParams(params);
}

static IMcParametricEnt* GetSpecificParametric(IMcObject* pObj)
{
    if (!pObj) return nullptr;
    void* raw = pObj->getSpecificKindPtr(__uuidof(IMcParametricEnt));
    return reinterpret_cast<IMcParametricEnt*>(raw);
}

static void LogKindSnapshot(IMcObject* pObj, const std::wstring& prefix)
{
    if (!pObj) {
        Log(prefix + L" obj=null");
        return;
    }

    IMcDbObjectPtr pDbObj = pObj;
    IMcDbEntityPtr pDbEnt = pObj;
    IMcEntityPtr pEnt = pObj;
    IMcParametricEntPtr pPeQi = pObj;
    IMcParametricEnt* pPeKind = GetSpecificParametric(pObj);

    Log(prefix + L" obj=" + Ptr((IMcObject*)pObj) +
        L" dbObj=" + std::to_wstring(pDbObj ? 1 : 0) +
        L" dbEnt=" + std::to_wstring(pDbEnt ? 1 : 0) +
        L" ent=" + std::to_wstring(pEnt ? 1 : 0) +
        L" peQI=" + std::to_wstring(pPeQi ? 1 : 0) +
        L" peKind=" + std::to_wstring(pPeKind ? 1 : 0));

    if (pDbObj) {
        const mcsWorkID& pid = pDbObj->getParentID();
        Log(prefix + L" parentID=" + WidStr(pid));
    }
}

static IMcParametricEnt* ResolveParametric(IMcNativeGate* pGate, IMcObject* pStart, int maxDepth, bool logWalk)
{
    if (!pGate || !pStart) return nullptr;

    IMcObjectPtr current = pStart;
    for (int depth = 0; current && depth <= maxDepth; ++depth) {
        std::wstring prefix = L"depth=" + std::to_wstring(depth) + L" |";
        if (logWalk) LogKindSnapshot(current, prefix);

        IMcParametricEntPtr pPeQi = current;
        if (pPeQi) {
            if (logWalk) Log(prefix + L" resolved=QI");
            return pPeQi;
        }

        IMcParametricEnt* pPeKind = GetSpecificParametric(current);
        if (pPeKind) {
            if (logWalk) Log(prefix + L" resolved=getSpecificKindPtr");
            return pPeKind;
        }

        IMcDbObjectPtr pDbObj = current;
        if (!pDbObj) {
            if (logWalk) Log(prefix + L" stop=no IMcDbObject");
            break;
        }

        const mcsWorkID& pid = pDbObj->getParentID();
        if (WidIsNull(pid)) {
            if (logWalk) Log(prefix + L" stop=parentID NULL");
            break;
        }

        IMcDbObjectPtr pParentDb = pDbObj->getParent();
        if (logWalk) {
            Log(prefix + L" getParent()=" + Ptr((IMcDbObject*)pParentDb));
            Log(prefix + L" QueryObject(" + WidStr(pid) + L")");
        }

        IMcObjectPtr next = pParentDb ? IMcObjectPtr(pParentDb) : pGate->QueryObject(pid);
        if (!next) {
            if (logWalk) Log(prefix + L" stop=parent query null");
            break;
        }
        current = next;
    }
    return nullptr;
}

static std::wstring NativeClassName(AcDbObject* pObj)
{
    if (!pObj || !pObj->isA() || !pObj->isA()->name())
        return L"<null>";
    const ACHAR* name = pObj->isA()->name();
    return name ? std::wstring(name) : L"<noname>";
}

static void LogMapiInfoForId(IMcNativeGate* pGate, const mcsWorkID& id, const std::wstring& prefix)
{
    if (!pGate) {
        Log(prefix + L" gate=NULL");
        return;
    }

    GUID clsid = pGate->QueryObjectClassID(id, nullptr);
    Log(prefix + L" classId=" + GuidStr(clsid) +
        L" isMCSCustom=<sdk24-unknown>");
}

static void LogDiagLegend()
{
    Log(L"[LEGEND] UnitsCS = найденные in-process функции из UnitsCS.nrx");
    Log(L"[LEGEND] SELECTED = выбранный DWG-объект и его прямой интерфейс");
    Log(L"[LEGEND] MAPI = Model Studio API-объекты, полученные через IMcNativeGate");
    Log(L"[LEGEND] DIRECT = внутренние PART_* параметры и их значения");
    Log(L"[LEGEND] JOIN = сопоставление UI-параметра с внутренним PART_*");
    Log(L"[LEGEND] NODE/PATH = узлы нативного дерева CElement");
    Log(L"[LEGEND] OWNER-IFACE / OWNER-ROOT = параметры владельца на разных уровнях");
}

static void LogNativeOwnerChain(IMcNativeGate* pGate, const AcDbObjectId& startOid, int maxDepth)
{
    AcDbObjectId current = startOid;
    for (int depth = 0; !current.isNull() && depth <= maxDepth; ++depth) {
        AcDbObject* pDbObj = nullptr;
        Acad::ErrorStatus es = ::acdbOpenAcDbObject(pDbObj, current, AcDb::kForRead);
        if (es != Acad::eOk || !pDbObj) {
            Log(L"nativeDepth=" + std::to_wstring(depth) +
                L" open failed es=" + std::to_wstring((int)es));
            break;
        }

        const AcDbObjectId owner = pDbObj->ownerId();
        Log(L"nativeDepth=" + std::to_wstring(depth) +
            L" oid=" + std::to_wstring((long long)current.asOldId()) +
            L" class=" + NativeClassName(pDbObj) +
            L" ownerOldId=" + std::to_wstring((long long)owner.asOldId()));

        if (pGate) {
            mcsWorkID wid;
            HRESULT hr = pGate->getMcsIdByNative(wid, *(int64_t*)&current);
            Log(L"nativeDepth=" + std::to_wstring(depth) +
                L" getMcsIdByNative hr=" + Hex(hr) +
                L" mcid=" + WidStr(wid));
            if (SUCCEEDED(hr)) {
                LogMapiInfoForId(pGate, wid, L"nativeDepth=" + std::to_wstring(depth));
                IMcObjectPtr pObj = pGate->QueryObject(wid);
                Log(L"nativeDepth=" + std::to_wstring(depth) +
                    L" QueryObject=" + Ptr((IMcObject*)pObj));
                IMcParametricEnt* pResolved = ResolveParametric(pGate, pObj, 6, true);
                if (pResolved) {
                    mcsExValueArray params;
                    HRESULT hrParams = pResolved->getParams(params);
                    Log(L"nativeDepth=" + std::to_wstring(depth) +
                        L" resolved params hr=" + Hex(hrParams) +
                        L" count=" + std::to_wstring(params.GetSize()));
                }
            }
        }

        pDbObj->close();
        current = owner;
    }
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// Win32 РґРёР°Р»РѕРі
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

struct ParamState {
    std::wstring name;
    std::wstring dispValue;  // С‚РµРєСѓС‰РµРµ Р·РЅР°С‡РµРЅРёРµ РёР»Рё "<СЂР°Р·РЅС‹Рµ>"
    std::wstring comment;
};

struct UiPropState {
    std::wstring internal;
    std::wstring local;
    std::wstring category;
    std::wstring value;
};

#define IDC_PARAM_COMBO  301
#define IDC_VALUE_EDIT   302
#define IDC_DUMP_BTN     303

struct DlgCtx {
    std::vector<ParamState>* pParams = nullptr;
    std::wstring selectedName;
    std::wstring newValue;
    bool applied = false;
    bool done    = false;
    HFONT hFont  = nullptr;
};

static HINSTANCE g_hInst = nullptr;

static void dtmxNrx18SetCmd();
static void dtmxNrx20TreeCmd();

static LRESULT CALLBACK ParamDlgProc(HWND hWnd, UINT msg, WPARAM wp, LPARAM lp)
{
    DlgCtx* pCtx = (DlgCtx*)::GetWindowLongPtrW(hWnd, GWLP_USERDATA);

    switch (msg) {
    case WM_CREATE: {
        auto* cs = (CREATESTRUCTW*)lp;
        pCtx = (DlgCtx*)cs->lpCreateParams;
        ::SetWindowLongPtrW(hWnd, GWLP_USERDATA, (LONG_PTR)pCtx);

        NONCLIENTMETRICSW ncm = {sizeof(ncm)};
        ::SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, sizeof(ncm), &ncm, 0);
        pCtx->hFont = ::CreateFontIndirectW(&ncm.lfMessageFont);
        HFONT hFnt = pCtx->hFont ? pCtx->hFont : (HFONT)::GetStockObject(DEFAULT_GUI_FONT);
        auto C = [&](LPCWSTR cls, LPCWSTR txt, DWORD sty,
                     int x, int y, int w, int h, WORD id) {
            HWND hw = ::CreateWindowExW(0,cls,txt,WS_CHILD|WS_VISIBLE|sty,
                x,y,w,h, hWnd,(HMENU)(UINT_PTR)id, g_hInst, nullptr);
            ::SendMessageW(hw, WM_SETFONT, (WPARAM)hFnt, FALSE);
            return hw;
        };

        C(L"STATIC",   L"Параметр:", SS_LEFT,                                10, 14, 75, 16, 310);
        C(L"COMBOBOX", L"",          CBS_DROPDOWNLIST|WS_VSCROLL|WS_TABSTOP, 90, 11,325,200, IDC_PARAM_COMBO);
        C(L"STATIC",   L"Значение:", SS_LEFT,                                10, 42, 75, 16, 311);
        C(L"EDIT",     L"",          WS_BORDER|ES_AUTOHSCROLL|WS_TABSTOP,    90, 39,325, 22, IDC_VALUE_EDIT);
        C(L"BUTTON",   L"Лог →файл",  BS_PUSHBUTTON|WS_TABSTOP,              10,  76,105, 28, IDC_DUMP_BTN);
        C(L"BUTTON",   L"Применить", BS_DEFPUSHBUTTON|WS_TABSTOP,           175, 76,120, 28, IDOK);
        C(L"BUTTON",   L"Отмена",    BS_PUSHBUTTON|WS_TABSTOP,              305, 76,120, 28, IDCANCEL);

        HWND hCb = ::GetDlgItem(hWnd, IDC_PARAM_COMBO);
        for (auto& p : *pCtx->pParams)
            ::SendMessageW(hCb, CB_ADDSTRING, 0, (LPARAM)p.name.c_str());
        if (!pCtx->pParams->empty()) {
            ::SendMessageW(hCb, CB_SETCURSEL, 0, 0);
            ::SetDlgItemTextW(hWnd, IDC_VALUE_EDIT, (*pCtx->pParams)[0].dispValue.c_str());
        }

        RECT rc; ::GetWindowRect(hWnd, &rc);
        int W = rc.right-rc.left, H = rc.bottom-rc.top;
        ::MoveWindow(hWnd,
            (::GetSystemMetrics(SM_CXSCREEN)-W)/2,
            (::GetSystemMetrics(SM_CYSCREEN)-H)/2,
            W, H, FALSE);
        return 0;
    }
    case WM_COMMAND: {
        if (!pCtx) return 0;
        WORD id = LOWORD(wp), notif = HIWORD(wp);
        if (id == IDC_PARAM_COMBO && notif == CBN_SELCHANGE) {
            int sel = (int)::SendDlgItemMessageW(hWnd, IDC_PARAM_COMBO, CB_GETCURSEL, 0, 0);
            if (sel >= 0 && sel < (int)pCtx->pParams->size())
                ::SetDlgItemTextW(hWnd, IDC_VALUE_EDIT,
                                  (*pCtx->pParams)[sel].dispValue.c_str());
        }
        else if (id == IDOK) {
            int sel = (int)::SendDlgItemMessageW(hWnd, IDC_PARAM_COMBO, CB_GETCURSEL, 0, 0);
            if (sel >= 0 && sel < (int)pCtx->pParams->size()) {
                pCtx->selectedName = (*pCtx->pParams)[sel].name;
                wchar_t buf[2048] = {};
                ::GetDlgItemTextW(hWnd, IDC_VALUE_EDIT, buf, 2048);
                pCtx->newValue = buf;
                pCtx->applied  = true;
            }
            ::DestroyWindow(hWnd);
        }
        else if (id == IDC_DUMP_BTN) {
            Log(L"=== Лог параметров из диалога ===");
            for (auto& p : *pCtx->pParams)
                Log(L"  " + p.name + L" = " + p.dispValue);
            Log(L"=== итого: " + std::to_wstring(pCtx->pParams->size()) + L" параметров ===");
            ::MessageBeep(MB_ICONINFORMATION);
        }
        else if (id == IDCANCEL)
            ::DestroyWindow(hWnd);
        return 0;
    }
    case WM_CLOSE:
        ::DestroyWindow(hWnd);
        return 0;
    case WM_DESTROY:
        if (pCtx) {
            if (pCtx->hFont) { ::DeleteObject(pCtx->hFont); pCtx->hFont = nullptr; }
            pCtx->done = true;
        }
        return 0;
    }
    return ::DefWindowProcW(hWnd, msg, wp, lp);
}

static void RegisterDlgClass()
{
    WNDCLASSEXW wc = {sizeof(wc)};
    wc.cbSize        = sizeof(wc);
    wc.lpfnWndProc   = ParamDlgProc;
    wc.hInstance     = g_hInst;
    wc.hCursor       = ::LoadCursorW(nullptr, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE+1);
    wc.lpszClassName = L"DtmxNrxDlg13";
    ::RegisterClassExW(&wc);
}
static void UnregisterDlgClass()
{
    ::UnregisterClassW(L"DtmxNrxDlg13", g_hInst);
}

static bool ShowPickParamDlg(std::vector<ParamState>& params,
                              std::wstring& outName, std::wstring& outValue)
{

    DlgCtx ctx; ctx.pParams = &params;

    HWND hDlg = ::CreateWindowExW(
        WS_EX_DLGMODALFRAME | WS_EX_TOPMOST,
        L"DtmxNrxDlg13",
        L"DTMXNRX — Параметры элементов",
        WS_POPUP | WS_CAPTION | WS_SYSMENU,
        0, 0, 440, 160,
        nullptr, nullptr, g_hInst, &ctx);
    if (!hDlg) {
        Log(L"CreateWindowExW failed err=" + std::to_wstring(::GetLastError()));
        return false;
    }
    ::ShowWindow(hDlg, SW_SHOW);
    ::SetForegroundWindow(hDlg);

    MSG wMsg;
    while (!ctx.done) {
        BOOL got = ::GetMessageW(&wMsg, nullptr, 0, 0);
        if (got == 0) { ::PostQuitMessage((int)wMsg.wParam); break; }
        if (got < 0) break;
        if (!::IsDialogMessageW(hDlg, &wMsg)) {
            ::TranslateMessage(&wMsg);
            ::DispatchMessageW(&wMsg);
        }
    }

    outName  = ctx.selectedName;
    outValue = ctx.newValue;
    return ctx.applied;
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// MAPI РґРёР°РіРЅРѕСЃС‚РёРєР° (РєРѕРјР°РЅРґР° DTMXNRX10PING)
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

struct MapiDllInfo { const char* dllName; HMODULE hMod; };

static void RunMapiDiagnostic()
{
    MapiDllInfo dlls[] = {
        { "McTyp.dll",   nullptr },
        { "MechCtl.dll", nullptr },
        { "MT.dll",      nullptr },
        { "McGeL.dll",   nullptr },
    };
    const int nDlls = (int)(sizeof(dlls)/sizeof(dlls[0]));

    Log(L"=== MAPI диагностика ===");
    ::acutPrintf(L"\n=== MAPI DLL диагностика ===\n");

    int found = 0;
    for (int i = 0; i < nDlls; ++i) {
        dlls[i].hMod = ::GetModuleHandleA(dlls[i].dllName);
        bool ok = (dlls[i].hMod != nullptr);
        if (ok) ++found;
        wchar_t wDll[64]; ::MultiByteToWideChar(CP_ACP, 0, dlls[i].dllName, -1, wDll, 64);
        std::wstring line = std::wstring(L"  ") + wDll;
        line.resize(22, L' ');
        line += ok ? L"ЗАГРУЖЕНА " : L"не найдена";
        if (ok) line += L" @ " + Ptr(dlls[i].hMod);
        Log(line); ::acutPrintf(L"%s\n", line.c_str());
    }

    IMcNativeGate* pGate = GetNativeGate();
    {
        std::wstring g = L"  gpMcNativeGate: " + Ptr(pGate);
        Log(g); ::acutPrintf(L"%s\n", g.c_str());
    }
    if (pGate) {
        Log(L"  >> IMcNativeGate OK: MAPI путь доступен");
        ::acutPrintf(L"  >> IMcNativeGate OK: MAPI путь доступен\n");
    }

    Log(std::wstring(L"  Загружено: ") + std::to_wstring(found) + L"/" + std::to_wstring(nDlls));
    ::acutPrintf(L"=== готово ===\n");
}

static void dtmxNrxPingCmd()
{
    Log(L"DTMXNRX11PING");
    ::acutPrintf(L"\nDTMXNRX11PING: OK\n");
    RunMapiDiagnostic();
}

static void dtmxNrxProbeCmd()
{
    LogClear();
    Log(L"=== DTMXNRX11PROBE start ===");

    IMcNativeGate* pGate = GetNativeGate();
    if (!pGate) {
        Log(L"pGate == NULL");
        ::acutPrintf(L"\nDTMXNRX11PROBE: MAPI not available\n");
        return;
    }

    ads_name ss = {};
    bool gotSS = (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) {
        ::acutPrintf(L"\nDTMXNRX11PROBE: выберите объекты\n");
        gotSS = (::acedSSGet(nullptr, nullptr, nullptr, nullptr, ss) == RTNORM);
    }
    if (!gotSS) {
        Log(L"probe: no selection");
        return;
    }

    long ssLen = 0;
    NCAD_SSLength(ss, &ssLen);
    Log(L"probe: selected=" + std::to_wstring(ssLen));

    for (long i = 0; i < ssLen; ++i) {
        ads_name en = {};
        NCAD_SSName(ss, i, en);
        AcDbObjectId oid;
        if (::acdbGetObjectId(oid, en) != Acad::eOk) continue;

        mcsWorkID mcid;
        HRESULT hr = pGate->getMcsIdByNative(mcid, *(int64_t*)&oid);
        Log(L"obj[" + std::to_wstring(i) + L"] getMcsIdByNative hr=" + Hex(hr) + L" mcid=" + WidStr(mcid));
        if (FAILED(hr)) continue;

        LogMapiInfoForId(pGate, mcid, L"obj[" + std::to_wstring(i) + L"]");
        LogNativeOwnerChain(pGate, oid, 8);

        IMcObjectPtr pObj = pGate->QueryObject(mcid);
        Log(L"obj[" + std::to_wstring(i) + L"] QueryObject=" + Ptr((IMcObject*)pObj));
        IMcParametricEnt* pResolved = ResolveParametric(pGate, pObj, 6, true);
        if (pResolved) {
            mcsExValueArray params;
            HRESULT hrParams = pResolved->getParams(params);
            Log(L"obj[" + std::to_wstring(i) + L"] resolved params hr=" + Hex(hrParams) +
                L" count=" + std::to_wstring(params.GetSize()));
        } else {
            Log(L"obj[" + std::to_wstring(i) + L"] resolved NONE");
        }
    }

    ::acedSSFree(ss);
    Log(L"=== DTMXNRX11PROBE done ===");
    ::acutPrintf(L"\nDTMXNRX11PROBE: done, log = %ls\n", LOG_PATH);
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// РљРѕРјР°РЅРґР° SET вЂ” С‡РёСЃС‚С‹Р№ MAPI, Р±РµР· COM
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

static void dtmxNrxSetCmd()
{
    LogClear();
    Log(L"=== DTMXNRX11SET start ===");

    IMcNativeGate* pGate = GetNativeGate();
    if (!pGate) {
        ::acutPrintf(L"\nDTMXNRX: McTyp.dll не загружен или MCS не активен\n");
        Log(L"pGate == NULL");
        return;
    }
    Log(L"IMcNativeGate: " + Ptr(pGate));

    // 1. Р’С‹Р±РѕСЂ РѕР±СЉРµРєС‚РѕРІ
    ads_name ss = {};
    bool gotSS = (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) {
        ::acutPrintf(L"\nDTMXNRX: выберите объекты:\n");
        gotSS = (::acedSSGet(nullptr, nullptr, nullptr, nullptr, ss) == RTNORM);
    }
    if (!gotSS) { Log(L"Нет выделения"); return; }

    long ssLen = 0;
    NCAD_SSLength(ss, &ssLen);
    if (ssLen == 0) { ::acedSSFree(ss); return; }
    Log(L"Выделено: " + std::to_wstring(ssLen));

    // 2. РЎРѕР±СЂР°С‚СЊ РѕР±СЉРµРєС‚С‹ + РїР°СЂР°РјРµС‚СЂС‹ С‡РµСЂРµР· MAPI
    struct ObjInfo {
        AcDbObjectId oid;
        std::map<std::wstring, std::wstring> params;
    };
    std::vector<ObjInfo> objects;

    for (long i = 0; i < ssLen; ++i) {
        ads_name en = {};
        NCAD_SSName(ss, i, en);
        AcDbObjectId oid;
        if (::acdbGetObjectId(oid, en) != Acad::eOk) continue;

        mcsWorkID mcid;
        HRESULT hr = pGate->getMcsIdByNative(mcid, *(int64_t*)&oid);
        if (FAILED(hr)) {
            Log(L"  getMcsIdByNative hr=" + Hex(hr)); continue;
        }

        IMcObjectPtr pObj = pGate->QueryObject(mcid);
        if (!pObj) { Log(L"  QueryObject = null"); continue; }

        IMcParametricEnt* pPE = ResolveParametric(pGate, pObj, 6, true);
        if (!pPE) continue;

        ObjInfo obj; obj.oid = oid;
        MapiEnumParams(pPE, obj.params);
        Log(L"  params=" + std::to_wstring(obj.params.size()));
        objects.push_back(std::move(obj));
    }
    ::acedSSFree(ss);

    if (objects.empty()) {
        ::acutPrintf(L"\nDTMXNRX: нет подходящих объектов (IMcParametricEnt)\n");
        return;
    }

    // 3. РћР±С‰РёРµ РїР°СЂР°РјРµС‚СЂС‹
    std::map<std::wstring, std::wstring> common = objects[0].params;
    for (size_t oi = 1; oi < objects.size(); ++oi) {
        for (auto it = common.begin(); it != common.end(); ) {
            it = (objects[oi].params.find(it->first) == objects[oi].params.end())
                 ? common.erase(it) : ++it;
        }
    }

    std::vector<ParamState> paramList;
    for (auto& kv : common) {
        ParamState ps; ps.name = kv.first;
        bool mixed = false;
        for (size_t oi = 1; oi < objects.size() && !mixed; ++oi) {
            auto it = objects[oi].params.find(kv.first);
            if (it == objects[oi].params.end() || it->second != kv.second)
                mixed = true;
        }
        ps.dispValue = mixed ? L"<разные>" : kv.second;
        paramList.push_back(std::move(ps));
    }

    Log(L"Общих параметров: " + std::to_wstring(paramList.size()));
    if (paramList.empty()) {
        ::acutPrintf(L"\nDTMXNRX: нет общих параметров у выделенных объектов\n");
        return;
    }

    // 4. Р”РёР°Р»РѕРі
    std::wstring pickedName, pickedValue;
    if (!ShowPickParamDlg(paramList, pickedName, pickedValue)) {
        Log(L"Диалог отменён"); return;
    }
    Log(L"Применяем: " + pickedName + L" = " + pickedValue);

    // 5. РџСЂРёРјРµРЅРёС‚СЊ С‡РµСЂРµР· MAPI setParams
    int ok = 0;
    for (auto& obj : objects) {
        mcsWorkID mcid;
        if (FAILED(pGate->getMcsIdByNative(mcid, *(int64_t*)&obj.oid))) continue;

        IMcObjectPtr pObj = pGate->QueryObject(mcid);
        if (!pObj) continue;

        IMcParametricEnt* pPE = ResolveParametric(pGate, pObj, 6, true);
        if (!pPE) continue;

        HRESULT hr = MapiSetParam(pPE, pickedName.c_str(), pickedValue.c_str());
        if (SUCCEEDED(hr)) ++ok;
        Log(L"  setParams hr=" + Hex(hr));
    }

    Log(L"=== DTMXNRX11SET done: " + std::to_wstring(ok) + L"/" + std::to_wstring(objects.size()) + L" ===");
    ::acutPrintf(L"\nDTMXNRX: готово — обновлено %d/%d объектов\n", ok, (int)objects.size());
}

static void dtmxNrx12UnitsProbeCmd()
{
    LogClear();
    Log(L"=== DTMXNRX12UPROBE start ===");

    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) {
        Log(L"LoadUnitsCsApi failed");
        ::acutPrintf(L"\nDTMXNRX12UPROBE: UnitsCS API not available\n");
        return;
    }

    Log(L"UnitsCS module=" + Ptr(api.module));
    Log(L" getParametricInterface=" + Ptr((void*)api.getParametricInterface));
    Log(L" getRootElementP=" + Ptr((void*)api.getRootElementP));
    Log(L" setRootElementP=" + Ptr((void*)api.setRootElementP));
    Log(L" setParameter4=" + Ptr((void*)api.setParameter4));

    AcDbObjectId oid;
    if (!GetSingleSelectedObject(oid)) {
        Log(L"no object selected");
        return;
    }

    AcDbObject* pObj = nullptr;
    Acad::ErrorStatus es = ::acdbOpenAcDbObject(pObj, oid, AcDb::kForWrite);
    Log(L"open status=" + std::to_wstring((int)es) + L" obj=" + Ptr(pObj));
    if (es != Acad::eOk || !pObj) {
        ::acutPrintf(L"\nDTMXNRX12UPROBE: open failed\n");
        return;
    }

    auto* pIface = api.getParametricInterface((void*)pObj);
    Log(L"iface=" + Ptr(pIface));
    if (pIface) {
        CElement* pRoot = api.getRootElementP((void*)pIface);
        Log(L"root=" + Ptr(pRoot));
    }

    pObj->close();
    Log(L"=== DTMXNRX12UPROBE done ===");
    ::acutPrintf(L"\nDTMXNRX12UPROBE: done, log = %ls\n", LOG_PATH);
}

static void dtmxNrx12UnitsSetCmd()
{
    LogClear();
    Log(L"=== DTMXNRX12USET start ===");

    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) {
        Log(L"LoadUnitsCsApi failed");
        ::acutPrintf(L"\nDTMXNRX12USET: UnitsCS API not available\n");
        return;
    }

    AcDbObjectId oid;
    if (!GetSingleSelectedObject(oid)) {
        Log(L"no object selected");
        return;
    }

    wchar_t rawValue[512] = L"";
    std::wstring value = L"DTMX";
    int rcStr = ::acedGetString(0, L"\nEnter PART_TAGNUMBER value <DTMX>: ", rawValue);
    if (rcStr == RTNORM && rawValue[0] != 0) {
        value = rawValue;
    }
    Log(L"value=" + value);

    AcDbObject* pObj = nullptr;
    Acad::ErrorStatus es = ::acdbOpenAcDbObject(pObj, oid, AcDb::kForWrite);
    Log(L"open status=" + std::to_wstring((int)es) + L" obj=" + Ptr(pObj));
    if (es != Acad::eOk || !pObj) {
        ::acutPrintf(L"\nDTMXNRX12USET: open failed\n");
        return;
    }

    auto* pIface = api.getParametricInterface((void*)pObj);
    Log(L"iface=" + Ptr(pIface));
    if (!pIface) {
        pObj->close();
        ::acutPrintf(L"\nDTMXNRX12USET: no parametric interface\n");
        return;
    }

    CElement* pRootBefore = api.getRootElementP((void*)pIface);
    Log(L"root before=" + Ptr(pRootBefore));
    Echo(L"[SAFE] Native SetParameter is temporarily disabled to avoid nanoCAD crash.");
    Echo(L"[SAFE] Resolved interface and root successfully; write path needs a safer commit strategy.");

    pObj->close();

    Log(L"=== DTMXNRX12USET done ===");
    ::acutPrintf(L"\nDTMXNRX12USET: safe mode, no write executed. Log = %ls\n", LOG_PATH);
}

static void dtmxNrx12bUnitsProbeCmd()
{
    dtmxNrx12UnitsProbeCmd();
}

static void dtmxNrx12bUnitsSetCmd()
{
    dtmxNrx12UnitsSetCmd();
}

static void dtmxNrx12dUnitsProbeCmd()
{
    Echo(L"=== DTMXNRX12DUPROBE wrapper ===");
    dtmxNrx12UnitsProbeCmd();
}

static void dtmxNrx12dUnitsSetCmd()
{
    Echo(L"=== DTMXNRX12DUSET wrapper ===");
    dtmxNrx12UnitsSetCmd();
}

static void dtmxNrx12xSetParamOnlyCmd()
{
    LogClear();
    Log(L"=== DTMXNRX12XSETP1 start ===");

    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) {
        Log(L"LoadUnitsCsApi failed");
        ::acutPrintf(L"\nDTMXNRX12XSETP1: UnitsCS API not available\n");
        return;
    }

    AcDbObjectId oid;
    if (!GetSingleSelectedObject(oid)) {
        Log(L"no object selected");
        return;
    }

    AcDbObject* pObj = nullptr;
    Acad::ErrorStatus es = ::acdbOpenAcDbObject(pObj, oid, AcDb::kForWrite);
    Log(L"open status=" + std::to_wstring((int)es) + L" obj=" + Ptr(pObj));
    if (es != Acad::eOk || !pObj) {
        ::acutPrintf(L"\nDTMXNRX12XSETP1: open failed\n");
        return;
    }

    auto* pIface = api.getParametricInterface((void*)pObj);
    Log(L"iface=" + Ptr(pIface));
    if (!pIface) {
        pObj->close();
        ::acutPrintf(L"\nDTMXNRX12XSETP1: no parametric interface\n");
        return;
    }

    CElement* pRootBefore = api.getRootElementP((void*)pIface);
    Log(L"root before=" + Ptr(pRootBefore));
    Log(L"calling SetParameter(PART_TAGNUMBER, '', 'DTMX', '')");
    api.setParameter4((void*)pIface, L"PART_TAGNUMBER", L"", L"DTMX", L"");
    Log(L"SetParameter returned");
    CElement* pRootAfter = api.getRootElementP((void*)pIface);
    Log(L"root after=" + Ptr(pRootAfter));

    pObj->close();
    Log(L"=== DTMXNRX12XSETP1 done ===");
    ::acutPrintf(L"\nDTMXNRX12XSETP1: done, log = %ls\n", LOG_PATH);
}

static void dtmxNrx12xSetParamArg2Cmd()
{
    LogClear();
    Log(L"=== DTMXNRX12XSETP2 start ===");
    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) return;
    AcDbObjectId oid;
    if (!GetSingleSelectedObject(oid)) return;
    AcDbObject* pObj = nullptr;
    Acad::ErrorStatus es = ::acdbOpenAcDbObject(pObj, oid, AcDb::kForWrite);
    Log(L"open status=" + std::to_wstring((int)es) + L" obj=" + Ptr(pObj));
    if (es != Acad::eOk || !pObj) return;
    auto* pIface = api.getParametricInterface((void*)pObj);
    Log(L"iface=" + Ptr(pIface));
    if (pIface) {
        Log(L"calling SetParameter(PART_TAGNUMBER, 'DTMX_A2', '', '')");
        api.setParameter4((void*)pIface, L"PART_TAGNUMBER", L"DTMX_A2", L"", L"");
        Log(L"SetParameter returned");
    }
    pObj->close();
    Log(L"=== DTMXNRX12XSETP2 done ===");
}

static void dtmxNrx12xSetParamArg4Cmd()
{
    LogClear();
    Log(L"=== DTMXNRX12XSETP4 start ===");
    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) return;
    AcDbObjectId oid;
    if (!GetSingleSelectedObject(oid)) return;
    AcDbObject* pObj = nullptr;
    Acad::ErrorStatus es = ::acdbOpenAcDbObject(pObj, oid, AcDb::kForWrite);
    Log(L"open status=" + std::to_wstring((int)es) + L" obj=" + Ptr(pObj));
    if (es != Acad::eOk || !pObj) return;
    auto* pIface = api.getParametricInterface((void*)pObj);
    Log(L"iface=" + Ptr(pIface));
    if (pIface) {
        Log(L"calling SetParameter(PART_TAGNUMBER, '', '', 'DTMX_A4')");
        api.setParameter4((void*)pIface, L"PART_TAGNUMBER", L"", L"", L"DTMX_A4");
        Log(L"SetParameter returned");
    }
    pObj->close();
    Log(L"=== DTMXNRX12XSETP4 done ===");
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// DllMain
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ


// Safely dereferences *(wchar_t**)((char*)pBase + byteOffset) via VirtualQuery.
// Returns nullptr if either the field or the pointed-to string is inaccessible.
static const wchar_t* SafeWcharPtrAt(const void* pBase, int byteOffset)
{
    if (!pBase) return nullptr;
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

// Returns the byte offset within pCParam that holds the CStringW parameter name.
// Prefers an offset whose string contains Cyrillic; falls back to any printable string.
static int ProbeCParamNameOffset(void* pCParam)
{
    // First pass: look for Cyrillic (Russian parameter names)
    for (int off : {0, 8, 16, 24}) {
        const wchar_t* p = SafeWcharPtrAt(pCParam, off);
        if (!p) continue;
        bool hasCyr = false, allOk = true;
        int len = 0;
        for (; len < 200 && p[len]; ++len) {
            wchar_t c = p[len];
            if (c < 0x0020 || c == 0xFFFE || c == 0xFFFF) { allOk = false; break; }
            if (c >= 0x0400 && c <= 0x04FF) hasCyr = true;
        }
        if (allOk && hasCyr && len > 0) return off;
    }
    // Second pass: any short printable string (non-Cyrillic param names)
    for (int off : {8, 0, 16, 24}) {
        const wchar_t* p = SafeWcharPtrAt(pCParam, off);
        if (!p || !p[0]) continue;
        bool allOk = true; int len = 0;
        for (; len < 200 && p[len]; ++len) {
            wchar_t c = p[len];
            if (c < 0x0020 || c == 0xFFFE || c == 0xFFFF) { allOk = false; break; }
        }
        if (allOk && len > 0 && len < 100) return off;
    }
    return -1;
}

static std::vector<ParamState> EnumParamsViaNative(UnitsCsApi& api, void* pIface)
{
    std::vector<ParamState> result;
    if (!api.getParamsCount || !api.getParameterByIndex) return result;

    int count = api.getParamsCount(pIface);
    Log(L"EnumParamsViaNative: count=" + std::to_wstring(count));
    if (count <= 0 || count > 2000) return result;

    CElement* pRoot = api.getRootElementP ? api.getRootElementP(pIface) : nullptr;

    // Probe name offset from first CParam with hex dump
    int nameOff = 8; // default: vtable-ptr at 0, CStringW name at 8
    void* pC0 = api.getParameterByIndex(pIface, 0);
    if (pC0) {
        MEMORY_BASIC_INFORMATION mbi = {};
        if (::VirtualQuery(pC0, &mbi, sizeof(mbi)) && mbi.State == MEM_COMMIT) {
            std::wstring hex = L"CParam0 hex:";
            const uint8_t* b = (const uint8_t*)pC0;
            for (int j = 0; j < 48; ++j) {
                wchar_t h[4]; ::swprintf_s(h, L"%02X", b[j]);
                hex += h;
                hex += (j % 8 == 7) ? L"| " : L" ";
            }
            Log(hex);
        }
        int probed = ProbeCParamNameOffset(pC0);
        if (probed >= 0) nameOff = probed;
        Log(L"CParam nameOff=" + std::to_wstring(nameOff));
    }

    for (int i = 0; i < count; ++i) {
        void* pCParam = api.getParameterByIndex(pIface, i);
        if (!pCParam) continue;
        const wchar_t* pName = SafeWcharPtrAt(pCParam, nameOff);
        if (!pName || !pName[0]) continue;
        ParamState ps;
        ps.name = pName;
        {
            const wchar_t* rawValue = api.cpGetValue ? api.cpGetValue((const void*)pCParam) : nullptr;
            const wchar_t* rawComment = api.cpGetComment ? api.cpGetComment((const void*)pCParam) : nullptr;
            if (rawValue) ps.dispValue = rawValue;
            if (rawComment) ps.comment = rawComment;
        }
        if (api.subEntParameterStr && pRoot) {
            const wchar_t* val = api.subEntParameterStr(pRoot, pName, false, false);
            if (val && (!val[0] ? false : true)) ps.dispValue = val;
        }
        result.push_back(std::move(ps));
    }
    Log(L"EnumParamsViaNative: found=" + std::to_wstring(result.size()));
    return result;
}

static std::wstring SafeWs(const wchar_t* p)
{
    return p ? std::wstring(p) : std::wstring();
}

static std::wstring NormalizeNodeName(const std::wstring& s, const wchar_t* fallback)
{
    if (!s.empty()) return s;
    return fallback ? std::wstring(fallback) : std::wstring(L"<unnamed>");
}

static std::wstring JoinNodePath(const std::wstring& basePath, const std::wstring& nodeName)
{
    const std::wstring normalized = NormalizeNodeName(nodeName, L"<unnamed>");
    if (basePath.empty()) return normalized;
    return basePath + L"/" + normalized;
}

static std::wstring WithNodeIdSuffix(const std::wstring& nodeName, int id)
{
    return NormalizeNodeName(nodeName, L"<unnamed>") + L"[" + std::to_wstring(id) + L"]";
}

static std::wstring SafeMcsStr(const McsString& s)
{
    return s.IsEmpty() ? std::wstring() : std::wstring((LPCTSTR)s);
}

static std::wstring VariantToString(const MCSVariant& v);

static std::wstring NormalizeMatchText(const std::wstring& s)
{
    std::wstring out;
    out.reserve(s.size());
    for (wchar_t ch : s) {
        if (ch == L' ' || ch == L'\t' || ch == L'\r' || ch == L'\n' ||
            ch == L'/' || ch == L'_' || ch == L'-' || ch == L'.' ||
            ch == L'(' || ch == L')')
            continue;
        out.push_back((wchar_t)::towlower(ch));
    }
    return out;
}

static bool ContainsNormalized(const std::wstring& haystack, const std::wstring& needle)
{
    const std::wstring h = NormalizeMatchText(haystack);
    const std::wstring n = NormalizeMatchText(needle);
    return !n.empty() && h.find(n) != std::wstring::npos;
}

static std::wstring ExpectedUiLabelForDirect(const std::wstring& directName)
{
    if (directName == L"PART_NAME") return L"Наименование изделия";
    if (directName == L"PART_TAG") return L"Обозначение / Модель";
    if (directName == L"PART_TAGNUMBER") return L"Идентификатор";
    if (directName == L"PART_STANDARD") return L"Нормативный документ";
    if (directName == L"PART_MATERIAL") return L"Материал";
    if (directName == L"PART_GROUP") return L"Группа изделий";
    if (directName == L"PART_TYPE" || directName == L"PART_PIPE_CLASS") return L"Тип изделий";
    if (directName == L"PART_SPECIALITY") return L"Специализация";
    if (directName == L"PART_WEIGHT") return L"Вес";
    if (directName == L"PART_COMMENT") return L"Примечания";
    if (directName == L"PART_MANUFACTURER") return L"Производитель";
    if (directName == L"PART_REFDRAWING") return L"Ссылочный чертеж";
    if (directName == L"PART_PIPE_DN") return L"Диаметр условный / DN";
    if (directName == L"PART_PIPE_DIAMETER") return L"Диаметр наружный / Dext.";
    if (directName == L"PIPE_THICKNESS") return L"Толщина стенки трубы";
    return L"";
}

static std::vector<UiPropState> CollectMapiProperties(IMcDbObject* pDbObj, mcsPropertyType eType)
{
    std::vector<UiPropState> props;
    if (!pDbObj) return props;
    mcsStringArray names;
    if (FAILED(pDbObj->getProperties(names, eType))) return props;

    for (int i = 0; i < names.GetSize(); ++i) {
        const McsString& name = names[i];
        MCSVariant value;
        McPropertyInfo info;
        HRESULT hrVal = pDbObj->getProperty(name, eType, value);
        HRESULT hrInfo = pDbObj->getPropertyInfo(name, info, eType);
        UiPropState p;
        p.internal = SafeMcsStr(name);
        p.value = SUCCEEDED(hrVal) ? VariantToString(value) : std::wstring();
        if (SUCCEEDED(hrInfo)) {
            p.local = SafeMcsStr(info.stLocalName);
            p.category = SafeMcsStr(info.stCategory);
        }
        props.push_back(std::move(p));
    }
    return props;
}

static void LogDirectMapiJoin(const std::vector<ParamState>& direct, const std::vector<UiPropState>& uiProps)
{
    for (const auto& p : direct) {
        const UiPropState* best = nullptr;
        int bestScore = -1;
        const std::wstring expected = ExpectedUiLabelForDirect(p.name);
        for (const auto& ui : uiProps) {
            int score = 0;
            if (!expected.empty() && ContainsNormalized(ui.local, expected)) score += 100;
            if (!p.comment.empty() && ContainsNormalized(ui.local, p.comment)) score += 90;
            if (!p.dispValue.empty() && !ui.value.empty() && p.dispValue == ui.value) score += 20;
            if ((p.name == L"PART_TAGNUMBER") && ContainsNormalized(ui.local, L"Идентификатор")) score += 120;
            if ((p.name == L"PART_NAME") && ContainsNormalized(ui.local, L"Наименование")) score += 70;
            if ((p.name == L"PART_TAG") && ContainsNormalized(ui.local, L"Обозначение")) score += 70;
            if ((p.name == L"PART_STANDARD") && ContainsNormalized(ui.local, L"Нормативный документ")) score += 70;
            if (score > bestScore) {
                bestScore = score;
                best = &ui;
            }
        }

        std::wstring line = L"[JOIN] ";
        if (best && bestScore >= 70) {
            line += L"UI/" + (best->category.empty() ? L"<no-category>" : best->category);
            line += L" -> " + (best->local.empty() ? L"<no-local>" : best->local);
        } else if (!p.comment.empty()) {
            line += L"UI/? -> " + p.comment;
        } else if (!expected.empty()) {
            line += L"UI/? -> " + expected;
        } else {
            line += L"UI/? -> <unmapped>";
        }
        line += L" [" + p.name + L"] = " + p.dispValue;
        Log(line);
    }
}

static std::vector<ParamState> EnumElementParamsViaOwner(UnitsCsApi& api, CElement* pElement)
{
    std::vector<ParamState> result;
    if (!pElement || !api.cpoGetParamsCount || !api.cpoGetParameterByIndex || !api.cpGetName) {
        return result;
    }

    const long long count = api.cpoGetParamsCount((const void*)pElement);
    Log(L"EnumElementParamsViaOwner: elem=" + Ptr(pElement) + L" count=" + std::to_wstring(count));
    if (count < 0 || count > 2000) return result;

    for (long long i = 0; i < count; ++i) {
        void* pParam = api.cpoGetParameterByIndex((const void*)pElement, i);
        if (!pParam) continue;

        ParamState ps;
        ps.name = SafeWs(api.cpGetName ? api.cpGetName((const void*)pParam) : nullptr);
        if (ps.name.empty()) continue;
        ps.dispValue = SafeWs(api.cpGetValue ? api.cpGetValue((const void*)pParam) : nullptr);
        ps.comment = SafeWs(api.cpGetComment ? api.cpGetComment((const void*)pParam) : nullptr);
        if (ps.dispValue.empty() && api.subEntParameterStr) {
            const wchar_t* val = api.subEntParameterStr(pElement, ps.name.c_str(), false, false);
            if (val) ps.dispValue = val;
        }
        result.push_back(std::move(ps));
    }

    Log(L"EnumElementParamsViaOwner: elem=" + Ptr(pElement) + L" found=" + std::to_wstring(result.size()));
    return result;
}

static bool SehOwnerCount(const UnitsCsApi* api, const void* pOwner, long long* pOutCount)
{
    if (!api || !pOwner || !pOutCount || !api->cpoGetParamsCount) return false;
    __try {
        *pOutCount = api->cpoGetParamsCount(pOwner);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehIfaceCount(const UnitsCsApi* api, void* pIface, int* pOutCount)
{
    if (!api || !pIface || !pOutCount || !api->getParamsCount) return false;
    __try {
        *pOutCount = api->getParamsCount(pIface);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehOwnerGetParamAt(const UnitsCsApi* api, const void* pOwner, long long index, void** ppParam)
{
    if (!api || !pOwner || !ppParam || !api->cpoGetParameterByIndex) return false;
    __try {
        *ppParam = api->cpoGetParameterByIndex(pOwner, index);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehParamGetName(const UnitsCsApi* api, const void* pParam, const wchar_t** ppValue)
{
    if (!api || !pParam || !ppValue || !api->cpGetName) return false;
    __try {
        *ppValue = api->cpGetName(pParam);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehParamGetValue(const UnitsCsApi* api, const void* pParam, const wchar_t** ppValue)
{
    if (!api || !pParam || !ppValue || !api->cpGetValue) return false;
    __try {
        *ppValue = api->cpGetValue(pParam);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehCeGetChildCount(const UnitsCsApi* api, const void* pEl, long long* pOut)
{
    if (!api || !pEl || !pOut || !api->ceGetChildCount) return false;
    __try { *pOut = api->ceGetChildCount(pEl); return true; }
    __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}

static bool SehCeGetChild(const UnitsCsApi* api, const void* pEl, long long index, CElement** ppChild)
{
    if (!api || !pEl || !ppChild || !api->ceGetChildByIndex) return false;
    __try { *ppChild = api->ceGetChildByIndex(pEl, index); return true; }
    __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}

static bool SehCeGetName(const UnitsCsApi* api, const void* pEl, const wchar_t** ppName)
{
    if (!api || !pEl || !ppName || !api->ceGetName) return false;
    __try { *ppName = api->ceGetName(pEl); return true; }
    __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}

// Recursive CElement subtree dump — returns total element count visited
static int LogElementSubtree(const UnitsCsApi& api, CElement* pEl, int depth, int maxDepth)
{
    if (!pEl || depth > maxDepth) return 0;
    std::wstring pad(depth * 2, L' ');

    const wchar_t* elName = nullptr;
    SehCeGetName(&api, pEl, &elName);

    long long paramCount = -1;
    bool pcOk = SehOwnerCount(&api, pEl, &paramCount);

    Log(pad + L"[" + std::to_wstring(depth) + L"] " + SafeWs(elName) +
        L"  params=" + (pcOk ? std::to_wstring(paramCount) : L"err"));

    if (pcOk && paramCount > 0 && paramCount < 500) {
        for (long long i = 0; i < paramCount && i < 64; ++i) {
            void* pParam = nullptr;
            if (!SehOwnerGetParamAt(&api, pEl, i, &pParam) || !pParam) {
                Log(pad + L"  [P] i=" + std::to_wstring(i) + L" crashed");
                continue;
            }
            const wchar_t* pName = nullptr;
            const wchar_t* pValue = nullptr;
            SehParamGetName(&api, pParam, &pName);
            SehParamGetValue(&api, pParam, &pValue);
            Log(pad + L"  [P] " + SafeWs(pName) + L" = " + SafeWs(pValue));
        }
    }

    long long childCount = 0;
    if (!SehCeGetChildCount(&api, pEl, &childCount)) {
        Log(pad + L"  children: GetChildCount crashed");
        return 1;
    }
    Log(pad + L"  children: " + std::to_wstring(childCount));

    int total = 1;
    for (long long ci = 0; ci < childCount && ci < 200; ++ci) {
        CElement* pChild = nullptr;
        if (!SehCeGetChild(&api, pEl, ci, &pChild) || !pChild) {
            Log(pad + L"  child[" + std::to_wstring(ci) + L"] null/crash");
            continue;
        }
        total += LogElementSubtree(api, pChild, depth + 1, maxDepth);
    }
    return total;
}

static bool SehParamGetComment(const UnitsCsApi* api, const void* pParam, const wchar_t** ppValue)
{
    if (!api || !pParam || !ppValue || !api->cpGetComment) return false;
    __try {
        *ppValue = api->cpGetComment(pParam);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehSubEntParameterStr(
    const UnitsCsApi* api,
    const void* pElement,
    const wchar_t* name,
    const wchar_t** ppValue)
{
    if (!api || !pElement || !name || !ppValue || !api->subEntParameterStr) return false;
    __try {
        *ppValue = api->subEntParameterStr(pElement, name, false, false);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehOwnerSetParameter4(
    const UnitsCsApi* api,
    void* pOwner,
    const wchar_t* name,
    const wchar_t* value,
    const wchar_t* comment,
    const wchar_t* valueComment)
{
    if (!api || !pOwner || !api->cpoSetParameter4) return false;
    __try {
        api->cpoSetParameter4(pOwner, name, value, comment, valueComment);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static bool SehParamSetValue(const UnitsCsApi* api, void* pParam, const wchar_t* value)
{
    if (!api || !pParam || !value || !api->cpSetValue) return false;
    __try {
        api->cpSetValue(pParam, value);
        return true;
    }
    __except(EXCEPTION_EXECUTE_HANDLER) {
        return false;
    }
}

static long long SafeOwnerCount(const UnitsCsApi& api, const void* pOwner, const wchar_t* tag)
{
    long long count = -1;
    if (SehOwnerCount(&api, pOwner, &count)) {
        Log(std::wstring(tag) + L" ownerCount=" + std::to_wstring(count));
        return count;
    }
    Log(std::wstring(tag) + L" ownerCount crashed");
    return -1;
}

static int SafeIfaceCount(const UnitsCsApi& api, void* pIface, const wchar_t* tag)
{
    int count = -1;
    if (SehIfaceCount(&api, pIface, &count)) {
        Log(std::wstring(tag) + L" ifaceCount=" + std::to_wstring(count));
        return count;
    }
    Log(std::wstring(tag) + L" ifaceCount crashed");
    return -1;
}

static void* FindOwnerParamByName(const UnitsCsApi& api, const void* pOwner, const wchar_t* wantedName)
{
    if (!pOwner || !wantedName || !api.cpoGetParamsCount || !api.cpoGetParameterByIndex || !api.cpGetName) {
        return nullptr;
    }

    const long long count = SafeOwnerCount(api, pOwner, L"[OWNER-FIND]");
    if (count <= 0 || count > 2000) return nullptr;

    for (long long i = 0; i < count; ++i) {
        void* pParam = nullptr;
        if (!SehOwnerGetParamAt(&api, pOwner, i, &pParam)) {
            Log(L"[OWNER-FIND] getParameterByIndex crashed at " + std::to_wstring(i));
            return nullptr;
        }
        if (!pParam) continue;

        const wchar_t* pName = nullptr;
        if (!SehParamGetName(&api, pParam, &pName)) {
            Log(L"[OWNER-FIND] cpGetName crashed at " + std::to_wstring(i));
            return nullptr;
        }
        if (pName && _wcsicmp(pName, wantedName) == 0) {
            Log(L"[OWNER-FIND] found " + std::wstring(wantedName) + L" at index=" + std::to_wstring(i) +
                L" ptr=" + Ptr(pParam));
            return pParam;
        }
    }
    Log(L"[OWNER-FIND] not found: " + std::wstring(wantedName));
    return nullptr;
}

static void LogOwnerParams(const UnitsCsApi& api, const void* pOwner, const wchar_t* tag, int maxItems)
{
    if (!pOwner || !tag) return;
    if (!api.cpoGetParamsCount || !api.cpoGetParameterByIndex || !api.cpGetName) {
        Log(std::wstring(tag) + L" owner API incomplete");
        return;
    }

    const long long count = SafeOwnerCount(api, pOwner, tag);
    if (count <= 0 || count > 2000) return;

    const long long limit = (count < maxItems) ? count : maxItems;
    for (long long i = 0; i < limit; ++i) {
        void* pParam = nullptr;
        const wchar_t* pName = nullptr;
        const wchar_t* pValue = nullptr;
        const wchar_t* pComment = nullptr;
        if (!SehOwnerGetParamAt(&api, pOwner, i, &pParam)) {
            Log(std::wstring(tag) + L" index=" + std::to_wstring(i) + L" crashed");
            continue;
        }
        if (pParam) {
            SehParamGetName(&api, pParam, &pName);
            SehParamGetValue(&api, pParam, &pValue);
            SehParamGetComment(&api, pParam, &pComment);
        }
        if (!pParam || !pName || !pName[0]) continue;

        std::wstring line = std::wstring(tag) + L" [" + std::to_wstring(i) + L"] " + pName +
            L" = " + SafeWs(pValue);
        if (pComment && pComment[0]) line += L" | comment=" + SafeWs(pComment);
        Log(line);
    }
    if (count > limit) {
        Log(std::wstring(tag) + L" ... truncated, total=" + std::to_wstring(count));
    }
}

static void LogNamedParamSnapshot(
    const UnitsCsApi& api,
    void* pIface,
    CElement* pRoot,
    const wchar_t* paramName,
    const wchar_t* tag)
{
    std::wstring line = std::wstring(tag) + L" " + paramName;

    if (api.subEntParameterStr && pRoot) {
        const wchar_t* pDisp = nullptr;
        if (!SehSubEntParameterStr(&api, pRoot, paramName, &pDisp)) {
            Log(line + L" | subEntParameterStr crashed");
            return;
        }
        line += L" | rootDisp=" + SafeWs(pDisp);
    }

    void* pParamIface = FindOwnerParamByName(api, pIface, paramName);
    if (pParamIface) {
        const wchar_t* pVal = nullptr;
        const wchar_t* pComment = nullptr;
        if (!SehParamGetValue(&api, pParamIface, &pVal) ||
            !SehParamGetComment(&api, pParamIface, &pComment)) {
            line += L" | ifaceParam crashed";
            Log(line);
            return;
        }
        line += L" | ifaceVal=" + SafeWs(pVal);
        if (pComment && pComment[0]) line += L" | ifaceComment=" + SafeWs(pComment);
    } else {
        line += L" | ifaceVal=<not-found>";
    }

    void* pParamRoot = FindOwnerParamByName(api, pRoot, paramName);
    if (pParamRoot) {
        const wchar_t* pVal = nullptr;
        const wchar_t* pComment = nullptr;
        if (!SehParamGetValue(&api, pParamRoot, &pVal) ||
            !SehParamGetComment(&api, pParamRoot, &pComment)) {
            line += L" | rootParam crashed";
            Log(line);
            return;
        }
        line += L" | rootVal=" + SafeWs(pVal);
        if (pComment && pComment[0]) line += L" | rootComment=" + SafeWs(pComment);
    } else {
        line += L" | rootVal=<not-found>";
    }

    Log(line);
}

static bool TryOwnerSetParameter4(
    const UnitsCsApi& api,
    void* pOwner,
    const wchar_t* name,
    const wchar_t* value,
    const wchar_t* comment,
    const wchar_t* valueComment,
    const wchar_t* tag)
{
    if (!pOwner || !api.cpoSetParameter4) {
        Log(std::wstring(tag) + L" setParameter4 unavailable");
        return false;
    }
    if (SehOwnerSetParameter4(&api, pOwner, name, value, comment, valueComment)) {
        Log(std::wstring(tag) + L" setParameter4 called ok");
        return true;
    }
    Log(std::wstring(tag) + L" setParameter4 crashed");
    return false;
}

static bool TryParamSetValue(
    const UnitsCsApi& api,
    void* pParam,
    const wchar_t* value,
    const wchar_t* tag)
{
    if (!pParam || !api.cpSetValue) {
        Log(std::wstring(tag) + L" cpSetValue unavailable");
        return false;
    }
    if (SehParamSetValue(&api, pParam, value)) {
        Log(std::wstring(tag) + L" cpSetValue called ok");
        return true;
    }
    Log(std::wstring(tag) + L" cpSetValue crashed");
    return false;
}

static int DumpElementTreeRecursive(
    UnitsCsApi& api,
    CElement* pElement,
    const std::wstring& parentPath,
    int depth,
    int maxDepth,
    int maxNodes,
    std::set<const void*>& visited)
{
    if (!pElement) return 0;
    if (depth > maxDepth) {
        Log(L"[TREE] depth limit reached at " + Ptr(pElement));
        return 0;
    }
    if ((int)visited.size() >= maxNodes) {
        Log(L"[TREE] node limit reached at " + Ptr(pElement));
        return 0;
    }
    if (!visited.insert((const void*)pElement).second) {
        Log(L"[TREE] cycle detected at " + Ptr(pElement));
        return 0;
    }

    const std::wstring indent(depth * 2, L' ');
    const int id = api.ceGetId ? api.ceGetId((const void*)pElement) : -1;
    const std::wstring name = NormalizeNodeName(
        SafeWs(api.ceGetName ? api.ceGetName((const void*)pElement) : nullptr),
        L"<unnamed>");
    const std::wstring path = JoinNodePath(parentPath, WithNodeIdSuffix(name, id));
    const int level = api.ceGetLevel ? api.ceGetLevel((const void*)pElement) : -1;
    const long long childCount = api.ceGetChildCount ? api.ceGetChildCount((const void*)pElement) : -1;

    Log(indent + L"[NODE] ptr=" + Ptr(pElement) +
        L" id=" + std::to_wstring(id) +
        L" level=" + std::to_wstring(level) +
        L" childCount=" + std::to_wstring(childCount) +
        L" name=" + name);
    Log(indent + L"[PATH] " + path);

    int total = 1;
    std::vector<ParamState> ps = EnumElementParamsViaOwner(api, pElement);
    for (const auto& p : ps) {
        std::wstring line = indent + L"  [P] " + p.name + L" = " + p.dispValue;
        if (!p.comment.empty()) line += L" | comment=" + p.comment;
        Log(line);
        std::wstring flatLine = L"[FLAT] " + path + L" -> " + p.name + L" = " + p.dispValue;
        if (!p.comment.empty()) flatLine += L" | comment=" + p.comment;
        Log(flatLine);
        ++total;
    }

    if (ps.empty()) Log(L"[FLAT-NODE] " + path + L" -> <no-owner-params>");

    if (childCount <= 0 || !api.ceGetChildByIndex) return total;

    for (long long i = 0; i < childCount; ++i) {
        CElement* pChild = api.ceGetChildByIndex((const void*)pElement, i);
        if (!pChild) {
            Log(indent + L"  [CHILD] index=" + std::to_wstring(i) + L" ptr=<null>");
            continue;
        }
        Log(indent + L"  [CHILD] index=" + std::to_wstring(i) + L" ptr=" + Ptr(pChild));
        total += DumpElementTreeRecursive(api, pChild, path, depth + 1, maxDepth, maxNodes, visited);
    }
    return total;
}

static void LogIfaceSnapshot(UnitsCsApi& api, AcDbObject* pObj, const std::wstring& prefix)
{
    if (!pObj) return;
    void* pIface = api.getParametricInterface ? api.getParametricInterface((void*)pObj) : nullptr;
    Log(prefix + L" class=" + NativeClassName(pObj) + L" iface=" + Ptr(pIface));
    if (!pIface) return;

    CElement* pRoot = api.getRootElementP ? api.getRootElementP(pIface) : nullptr;
    Log(prefix + L" root=" + Ptr(pRoot));
    if (pRoot && api.ceGetName && api.ceGetChildCount) {
        std::wstring name = SafeWs(api.ceGetName((const void*)pRoot));
        long long childCount = api.ceGetChildCount((const void*)pRoot);
        int level = api.ceGetLevel ? api.ceGetLevel((const void*)pRoot) : -1;
        int id = api.ceGetId ? api.ceGetId((const void*)pRoot) : -1;
        Log(prefix + L" rootName=" + (name.empty() ? L"<empty>" : name) +
            L" rootId=" + std::to_wstring(id) +
            L" rootLevel=" + std::to_wstring(level) +
            L" rootChildCount=" + std::to_wstring(childCount));
    }

    std::vector<ParamState> direct = EnumParamsViaNative(api, pIface);
    Log(prefix + L" directParamCount=" + std::to_wstring((int)direct.size()));
    for (const auto& p : direct) {
        if (!p.dispValue.empty())
            Log(prefix + L"   " + p.name + L" = " + p.dispValue);
    }
}

static void LogOwnerChainSnapshots(UnitsCsApi& api, const AcDbObjectId& startId)
{
    Log(L"[OWNERCHAIN] start");
    AcDbObjectId current = startId;
    for (int depth = 0; depth < 8 && !current.isNull(); ++depth) {
        AcDbObject* pObj = nullptr;
        Acad::ErrorStatus es = ::acdbOpenAcDbObject(pObj, current, AcDb::kForRead);
        Log(L"[OWNERCHAIN] depth=" + std::to_wstring(depth) +
            L" open=" + std::to_wstring((int)es) +
            L" idValid=" + std::to_wstring(current.isValid() ? 1 : 0));
        if (es != Acad::eOk || !pObj) break;

        LogIfaceSnapshot(api, pObj, L"[OWNERCHAIN] depth=" + std::to_wstring(depth));
        AcDbObjectId owner = pObj->ownerId();
        pObj->close();
        current = owner;
    }
    Log(L"[OWNERCHAIN] done");
}

static bool SafeGetMapiChildren(IMcDbObject* pDbObj, const mcsWorkIDArray*& pChildren, int& childCount, HRESULT& sehCode)
{
    pChildren = nullptr;
    childCount = -1;
    sehCode = S_OK;
    __try {
        pChildren = &pDbObj->getChildrenIDs();
        childCount = pChildren ? pChildren->GetSize() : -1;
        return true;
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        sehCode = (HRESULT)GetExceptionCode();
        return false;
    }
}

static std::wstring VariantToString(const MCSVariant& v)
{
    switch (v.GetType()) {
    case MCSVariant::kUndefined: return L"<undefined>";
    case MCSVariant::kString: {
        LPCTSTR s = (LPCTSTR)v;
        return s ? std::wstring(s) : L"";
    }
    case MCSVariant::kInt: return std::to_wstring((int)v);
    case MCSVariant::kInt64: return std::to_wstring((long long)(__int64)v);
    case MCSVariant::kDouble: {
        wchar_t buf[128] = {};
        ::swprintf_s(buf, L"%.15g", (double)v);
        return buf;
    }
    case MCSVariant::kBool: return ((bool)v) ? L"True" : L"False";
    case MCSVariant::kMCSWorkID: return WidStr((const mcsWorkID)v);
    case MCSVariant::kIntArray: return L"<int-array:" + std::to_wstring(v.IntArray().GetSize()) + L">";
    case MCSVariant::kDoubleArray: return L"<double-array:" + std::to_wstring(v.DoubleArray().GetSize()) + L">";
    case MCSVariant::kStringArray: return L"<string-array:" + std::to_wstring(v.StringArray().GetSize()) + L">";
    case MCSVariant::kWorkIDArray: return L"<wid-array>";
    default:
        return L"<type:" + std::to_wstring((int)v.GetType()) + L">";
    }
}

static std::wstring CtrlTypeName(int ctrlType)
{
    switch (ctrlType) {
    case MC_NONE: return L"MC_NONE";
    case MC_EDIT_INT: return L"MC_EDIT_INT";
    case MC_EDIT_DOUBLE: return L"MC_EDIT_DOUBLE";
    case MC_EDIT_STRING: return L"MC_EDIT_STRING";
    case MC_BOOL_COMBOBOX: return L"MC_BOOL_COMBOBOX";
    case MC_COLOR_COMBOBOX: return L"MC_COLOR_COMBOBOX";
    case MC_LAYER_COMBOBOX: return L"MC_LAYER_COMBOBOX";
    case MC_COMBOBOX_STRING: return L"MC_COMBOBOX_STRING";
    case MC_COMBOBOX_INT: return L"MC_COMBOBOX_INT";
    case MC_COMBOBOX_DOUBLE: return L"MC_COMBOBOX_DOUBLE";
    case MC_OPEN_FILE_DIALOG: return L"MC_OPEN_FILE_DIALOG";
    case MC_STRING_ARRAY: return L"MC_STRING_ARRAY";
    case MC_EDIT_STRING_ARRAY: return L"MC_EDIT_STRING_ARRAY";
    case MC_CUSTOM_DIALOG: return L"MC_CUSTOM_DIALOG";
    default:
        return L"CTRL#" + std::to_wstring(ctrlType);
    }
}

static std::wstring PropFlagsString(int flags)
{
    std::wstring s = std::to_wstring(flags);
    if (flags == 0) return s + L"[mcPropsNone]";
    std::vector<std::wstring> parts;
    if (flags & mcPropsReadOnly) parts.push_back(L"ReadOnly");
    if (flags & mcPropsInternal) parts.push_back(L"Internal");
    if (flags & mcPropsDisabled) parts.push_back(L"Disabled");
    if (flags & mcPropsInconstantInfo) parts.push_back(L"InconstantInfo");
    if (flags & mcPropsNeedUpdateSet) parts.push_back(L"NeedUpdateSet");
    if (flags & mcPropsNormaCS) parts.push_back(L"NormaCS");
    if (flags & mcPropsSpecSymbols) parts.push_back(L"SpecSymbols");
    if (flags & mcPropsDisablePreview) parts.push_back(L"DisablePreview");
    if (flags & mcPropsNeedUpdate) parts.push_back(L"NeedUpdate");
    s += L"[";
    for (size_t i = 0; i < parts.size(); ++i) {
        if (i) s += L"|";
        s += parts[i];
    }
    s += L"]";
    return s;
}

static void LogMapiPropertySource(IMcDbObject* pDbObj, mcsPropertyType eType, const std::wstring& label)
{
    if (!pDbObj) return;
    mcsStringArray names;
    HRESULT hr = pDbObj->getProperties(names, eType);
    Log(label + L" getProperties hr=" + Hex(hr) + L" count=" + std::to_wstring(names.GetSize()));
    if (FAILED(hr)) return;

    for (int i = 0; i < names.GetSize(); ++i) {
        const McsString& name = names[i];
        MCSVariant value;
        HRESULT hrVal = pDbObj->getProperty(name, eType, value);
        McPropertyInfo info;
        HRESULT hrInfo = pDbObj->getPropertyInfo(name, info, eType);
        std::wstring line = label + L" [" + std::to_wstring(i) + L"] " + (LPCTSTR)name;
        line += L" | hrVal=" + Hex(hrVal);
        line += L" | value=" + VariantToString(value);
        if (SUCCEEDED(hrInfo)) {
            if (!info.stLocalName.IsEmpty()) line += L" | local=" + std::wstring((LPCTSTR)info.stLocalName);
            if (!info.stCategory.IsEmpty()) line += L" | cat=" + std::wstring((LPCTSTR)info.stCategory);
            line += L" | ctrl=" + CtrlTypeName((int)info.ctrlType);
            line += L" | flags=" + PropFlagsString(info.propType);
            if (info.values.GetType() != MCSVariant::kUndefined) line += L" | variantsData=" + VariantToString(info.values);
            if (info.iGsMarker >= 0) line += L" | gs=" + std::to_wstring(info.iGsMarker);
            if (info.pCustomDialog) line += L" | customDlg=" + Ptr((void*)info.pCustomDialog);
        } else {
            line += L" | hrInfo=" + Hex(hrInfo);
        }
        Log(line);

        std::wstring cat = SUCCEEDED(hrInfo) ? SafeMcsStr(info.stCategory) : std::wstring();
        std::wstring local = SUCCEEDED(hrInfo) ? SafeMcsStr(info.stLocalName) : std::wstring();
        const std::wstring internal = std::wstring((LPCTSTR)name);
        if (cat.empty()) cat = L"<no-category>";
        if (local.empty()) local = internal;
        Log(L"[MAPI-FLAT] UI/" + cat + L" -> " + local + L" [" + internal + L"] = " + VariantToString(value));
    }
}

static bool SafeGetReferenceItems(
    IMcObject* pObj,
    IMcReferenceItems& refs,
    HRESULT& hrCall,
    HRESULT& sehCode)
{
    hrCall = E_FAIL;
    sehCode = S_OK;
    __try {
        if (!pObj) {
            hrCall = E_POINTER;
            return true;
        }
        void* raw = pObj->getSpecificKindPtr(__uuidof(IMcReferenceExtension));
        IMcReferenceExtension* pRefExt = reinterpret_cast<IMcReferenceExtension*>(raw);
        if (!pRefExt) {
            hrCall = E_NOINTERFACE;
            return true;
        }
        hrCall = pRefExt->GetReferenceItems(refs);
        return true;
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        sehCode = (HRESULT)GetExceptionCode();
        return false;
    }
}

static void LogMapiChildrenExProbes(IMcDbObject* pDbObj, int depth)
{
    if (!pDbObj) return;
    const std::wstring prefix(depth * 2, L' ');
    Log(prefix + L"[MAPI-CHILDEX] skipped: nanoCAD 24.1 runtime lacks mcsWorkIDArray() export");
}

static void LogMapiReferenceProbes(IMcObject* pObj, int depth)
{
    if (!pObj) return;
    const std::wstring prefix(depth * 2, L' ');
    IMcReferenceItems refs;
    HRESULT hrCall = E_FAIL, sehCode = S_OK;
    if (!SafeGetReferenceItems(pObj, refs, hrCall, sehCode)) {
        Log(prefix + L"[MAPI-REF] crashed seh=" + Hex(sehCode));
        return;
    }
    Log(prefix + L"[MAPI-REF] hr=" + Hex(hrCall) + L" count=" + std::to_wstring(refs.GetSize()));
    const int limit = refs.GetSize() < 16 ? refs.GetSize() : 16;
    for (int i = 0; i < limit; ++i) {
        IMcReferenceItemPtr ref = refs[i];
        if (!ref) {
            Log(prefix + L"  [REF] index=" + std::to_wstring(i) + L" ptr=NULL");
            continue;
        }
        std::wstring line = prefix + L"  [REF] index=" + std::to_wstring(i);
        line += L" src=" + WidStr(ref->getSource());
        line += L" dst=" + WidStr(ref->getTarget());
        line += L" dir=" + std::to_wstring((int)ref->getDirection());
        McsString expr = ref->getExpression();
        if (!expr.IsEmpty()) line += L" expr=" + std::wstring((LPCTSTR)expr);
        Log(line);
    }
}

static void DumpMapiChildrenRecursive(
    IMcNativeGate* pGate,
    IMcObject* pObj,
    const mcsWorkID& selfId,
    int depth,
    int maxDepth,
    std::set<std::wstring>& visited)
{
    if (!pGate || !pObj || depth > maxDepth) return;

    IMcDbObjectPtr pDbObj = pObj;
    if (!pDbObj) {
        Log(std::wstring(depth * 2, L' ') + L"[MAPI] no IMcDbObject");
        return;
    }

    std::wstring key = WidStr(selfId);
    if (!visited.insert(key).second) {
        Log(std::wstring(depth * 2, L' ') + L"[MAPI] cycle " + key);
        return;
    }

    GUID clsid = pGate->QueryObjectClassID(selfId, nullptr);
    Log(std::wstring(depth * 2, L' ') + L"[MAPI] id=" + key +
        L" classId=" + GuidStr(clsid));

    LogMapiPropertySource(pDbObj, mcPropsObject, std::wstring(depth * 2, L' ') + L"[MAPI-OBJ]");
    LogMapiPropertySource(pDbObj, mcPropsUser, std::wstring(depth * 2, L' ') + L"[MAPI-USER]");
    LogMapiPropertySource(pDbObj, mcPropsSystem, std::wstring(depth * 2, L' ') + L"[MAPI-SYS]");
    LogMapiPropertySource(pDbObj, mcPropsVisible2, std::wstring(depth * 2, L' ') + L"[MAPI-VIS]");
    LogMapiChildrenExProbes(pDbObj, depth);
    LogMapiReferenceProbes(pObj, depth);

    int childCount = -1;
    const mcsWorkIDArray* pChildren = nullptr;
    HRESULT sehCode = S_OK;
    if (!SafeGetMapiChildren(pDbObj, pChildren, childCount, sehCode)) {
        Log(std::wstring(depth * 2, L' ') + L"[MAPI] getChildrenIDs crashed seh=" + Hex(sehCode));
        return;
    }
    Log(std::wstring(depth * 2, L' ') + L"[MAPI] childCount=" + std::to_wstring(childCount));

    IMcParametricEnt* pPE = ResolveParametric(pGate, pObj, 3, false);
    if (pPE) {
        std::map<std::wstring, std::wstring> pm;
        MapiEnumParams(pPE, pm);
        Log(std::wstring(depth * 2, L' ') + L"  [MAPI-PARAMS] count=" + std::to_wstring((int)pm.size()));
        for (const auto& kv : pm) {
            if (!kv.second.empty()) {
                Log(std::wstring(depth * 2, L' ') + L"    " + kv.first + L" = " + kv.second);
            }
        }
    }

    for (int i = 0; pChildren && i < pChildren->GetSize(); ++i) {
        const mcsWorkID& childId = (*pChildren)[i];
        IMcObjectPtr pChild = pGate->QueryObject(childId);
        Log(std::wstring(depth * 2, L' ') + L"  [MAPI-CHILD] index=" + std::to_wstring(i) +
            L" id=" + WidStr(childId) +
            L" ptr=" + Ptr((IMcObject*)pChild));
        if (pChild) DumpMapiChildrenRecursive(pGate, pChild, childId, depth + 1, maxDepth, visited);
    }
}

// Opens oid for read, dumps all MCS params to log. Returns param count (0 = not MCS).
// pObj must stay open during EnumParamsViaNative — pIface/pRoot reference its internal state.
static int DumpMcsObjectById(UnitsCsApi& api, AcDbObjectId oid, const std::wstring& prefix)
{
    AcDbObject* pObj = nullptr;
    if (::acdbOpenAcDbObject(pObj, oid, AcDb::kForRead) != Acad::eOk) return 0;
    std::wstring cn = NativeClassName(pObj);
    void* pIface = api.getParametricInterface((void*)pObj);
    if (!pIface) { pObj->close(); return 0; }
    std::vector<ParamState> ps = EnumParamsViaNative(api, pIface);  // needs pObj open
    pObj->close();
    if (ps.empty()) return 0;
    Log(prefix + L"[" + cn + L"] " + std::to_wstring(ps.size()) + L" параметров:");
    for (auto& p : ps) Log(prefix + L"  " + p.name + L" = " + p.dispValue);
    return (int)ps.size();
}

static void dtmxNrx19DumpCmd()
{
    LogClear();
    Log(L"=== DTMXNRX19DUMP start ===");

    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) {
        ::acutPrintf(L"\nDTMXNRX19DUMP: UnitsCS not available\n");
        return;
    }
    IMcNativeGate* pGate = GetNativeGate();

    ads_name ss = {};
    bool gotSS = (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) gotSS = (::acedSSGet(nullptr, nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) { Log(L"no selection"); return; }
    long ssLen = 0; NCAD_SSLength(ss, &ssLen);
    Log(L"selected: " + std::to_wstring(ssLen));

    int total = 0;
    std::vector<AcDbObjectId> selectedOids;

    // 1. Selected objects — direct params
    for (long i = 0; i < ssLen; ++i) {
        ads_name en = {}; NCAD_SSName(ss, i, en);
        AcDbObjectId oid;
        if (::acdbGetObjectId(oid, en) != Acad::eOk) continue;
        selectedOids.push_back(oid);
        Log(L"--- Выбранный [" + std::to_wstring(i) + L"] ---");
        total += DumpMcsObjectById(api, oid, L"");

        // MAPI: check for parent
        if (pGate) {
            mcsWorkID mcid;
            if (SUCCEEDED(pGate->getMcsIdByNative(mcid, *(int64_t*)&oid))) {
                IMcObjectPtr pMcObj = pGate->QueryObject(mcid);
                IMcDbObjectPtr pDbObj = pMcObj;
                if (pDbObj) {
                    const mcsWorkID& pid = pDbObj->getParentID();
                    if (!WidIsNull(pid)) {
                        Log(L"  → MAPI родитель:");
                        IMcObjectPtr pPar = pGate->QueryObject(pid);
                        if (pPar) {
                            IMcParametricEnt* pPE = ResolveParametric(pGate, pPar, 4, false);
                            if (pPE) {
                                std::map<std::wstring,std::wstring> pm;
                                MapiEnumParams(pPE, pm);
                                for (auto& kv : pm) { Log(L"    " + kv.first + L" = " + kv.second); ++total; }
                            }
                        }
                    } else {
                        Log(L"  (MAPI parentID=NULL — корневой элемент)");
                    }
                }
            }
        }
    }
    ::acedSSFree(ss);

    // 2. Owner block scan — other MCS-parametric objects in the same block
    if (!selectedOids.empty()) {
        AcDbObject* pFirst = nullptr;
        if (::acdbOpenAcDbObject(pFirst, selectedOids[0], AcDb::kForRead) == Acad::eOk) {
            AcDbObjectId ownerId = pFirst->ownerId();
            pFirst->close();

            AcDbObject* pBTRObj = nullptr;
            if (::acdbOpenAcDbObject(pBTRObj, ownerId, AcDb::kForRead) == Acad::eOk) {
                AcDbBlockTableRecord* pBTR = AcDbBlockTableRecord::cast(pBTRObj);
                if (pBTR) {
                    Log(L"--- Другие MCS-объекты в блоке (до 50) ---");
                    AcDbBlockTableRecordIterator* pIt = nullptr;
                    pBTR->newIterator(pIt);
                    int found = 0;
                    for (; pIt && !pIt->done() && found < 50; pIt->step()) {
                        AcDbObjectId entId;
                        if (pIt->getEntityId(entId) != Acad::eOk) continue;
                        bool isSel = false;
                        for (auto& s : selectedOids) if (s == entId) { isSel = true; break; }
                        if (isSel) continue;
                        int n = DumpMcsObjectById(api, entId, L"  ");
                        if (n > 0) { total += n; ++found; }
                    }
                    delete pIt;
                    Log(L"  Найдено: " + std::to_wstring(found));
                }
                pBTRObj->close();
            }
        }
    }

    Log(L"=== DTMXNRX19DUMP done: total=" + std::to_wstring(total) + L" ===");
    ::acutPrintf(L"\nDTMXNRX19DUMP: %d параметров — см. лог\n", total);
}

static void dtmxNrx20TreeCmd()
{
    LogClear();
    Log(L"=== DTMXNRX20TREE start ===");
    LogDiagLegend();

    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) {
        ::acutPrintf(L"\nDTMXNRX20TREE: UnitsCS not available\n");
        return;
    }
    IMcNativeGate* pGate = GetNativeGate();
    if (!api.ceGetChildCount || !api.ceGetChildByIndex || !api.ceGetName ||
        !api.cpoGetParamsCount || !api.cpoGetParameterByIndex || !api.cpGetName) {
        Log(L"DTMXNRX20TREE: CElement/CParamsOwner API is incomplete");
        ::acutPrintf(L"\nDTMXNRX20TREE: CElement API is incomplete\n");
        return;
    }

    std::vector<AcDbObjectId> selected = GetSelectedObjects();
    Log(L"selectedCount=" + std::to_wstring((int)selected.size()));
    if (selected.empty()) {
        Log(L"DTMXNRX20TREE: no selected object");
        return;
    }
    AcDbObjectId oid = selected.front();

    for (size_t i = 0; i < selected.size(); ++i) {
        AcDbObject* pSelObj = nullptr;
        Acad::ErrorStatus esOpen = ::acdbOpenAcDbObject(pSelObj, selected[i], AcDb::kForRead);
        Log(L"[SELECTED] index=" + std::to_wstring((int)i) + L" open=" + std::to_wstring((int)esOpen));
        if (esOpen == Acad::eOk && pSelObj) {
            LogIfaceSnapshot(api, pSelObj, L"[SELECTED] index=" + std::to_wstring((int)i));
            pSelObj->close();
        }
    }
    LogOwnerChainSnapshots(api, oid);
    IMcDbObjectPtr pSelectedDbObj;
    if (pGate) {
        mcsWorkID wid;
        HRESULT hr = pGate->getMcsIdByNative(wid, *(int64_t*)&oid);
        Log(L"[MAPI] getMcsIdByNative hr=" + Hex(hr) + L" id=" + WidStr(wid));
        if (SUCCEEDED(hr)) {
            IMcObjectPtr pRootObj = pGate->QueryObject(wid);
            Log(L"[MAPI] QueryObject(root)=" + Ptr((IMcObject*)pRootObj));
            pSelectedDbObj = pRootObj;
            if (pRootObj) {
                std::set<std::wstring> visitedMapi;
                DumpMapiChildrenRecursive(pGate, pRootObj, wid, 0, 6, visitedMapi);
            }
        }
    }

    AcDbObject* pObj = nullptr;
    Acad::ErrorStatus es = ::acdbOpenAcDbObject(pObj, oid, AcDb::kForRead);
    Log(L"selected open status=" + std::to_wstring((int)es));
    if (es != Acad::eOk || !pObj) {
        ::acutPrintf(L"\nDTMXNRX20TREE: failed to open selected object\n");
        return;
    }

    Log(L"selected class=" + NativeClassName(pObj));
    void* pIface = api.getParametricInterface((void*)pObj);
    Log(L"selected iface=" + Ptr(pIface));
    if (!pIface) {
        pObj->close();
        ::acutPrintf(L"\nDTMXNRX20TREE: selected object is not parametric\n");
        return;
    }

    CElement* pRoot = api.getRootElementP ? api.getRootElementP(pIface) : nullptr;
    Log(L"selected root=" + Ptr(pRoot));
    if (!pRoot) {
        pObj->close();
        ::acutPrintf(L"\nDTMXNRX20TREE: root element not found\n");
        return;
    }

    std::vector<UiPropState> uiVisible = CollectMapiProperties(pSelectedDbObj, mcPropsVisible2);
    std::vector<ParamState> direct = EnumParamsViaNative(api, pIface);
    Log(L"[DIRECT] selected interface params=" + std::to_wstring(direct.size()));
    for (const auto& p : direct) {
        std::wstring line = L"  [DIRECT] " + p.name + L" = " + p.dispValue;
        if (!p.comment.empty()) line += L" | comment=" + p.comment;
        Log(line);
    }
    LogDirectMapiJoin(direct, uiVisible);

    std::set<const void*> visited;
    const int total = DumpElementTreeRecursive(api, pRoot, L"", 0, 16, 500, visited);
    pObj->close();

    Log(L"=== DTMXNRX20TREE done: visited=" + std::to_wstring((int)visited.size()) +
        L" totalLines=" + std::to_wstring(total) + L" ===");
    ::acutPrintf(L"\nDTMXNRX20TREE: nodes=%d — см. лог\n", (int)visited.size());
}

static void RunDtmxNrx21OwnerCmd(bool doWrite)
{
    LogClear();
    Log(std::wstring(L"=== ") + (doWrite ? L"DTMXNRX21OSET" : L"DTMXNRX21OPROBE") + L" start ===");

    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) {
        ::acutPrintf(doWrite
            ? L"\nDTMXNRX21OSET: UnitsCS not available\n"
            : L"\nDTMXNRX21OPROBE: UnitsCS not available\n");
        return;
    }
    if (!api.getParametricInterface || !api.getRootElementP ||
        !api.getParamsCount || !api.getParameterByIndex ||
        !api.cpoGetParamsCount || !api.cpoGetParameterByIndex ||
        !api.cpGetName || !api.cpGetValue) {
        Log(L"DTMXNRX21: required owner API is incomplete");
        ::acutPrintf(doWrite
            ? L"\nDTMXNRX21OSET: owner API incomplete\n"
            : L"\nDTMXNRX21OPROBE: owner API incomplete\n");
        return;
    }

    std::vector<AcDbObjectId> selected = GetSelectedObjects();
    Log(L"selectedCount=" + std::to_wstring((int)selected.size()));
    if (selected.empty()) {
        ::acutPrintf(doWrite
            ? L"\nDTMXNRX21OSET: preselect one Model Studio object first\n"
            : L"\nDTMXNRX21OPROBE: preselect one Model Studio object first\n");
        return;
    }

    AcDbObject* pObj = nullptr;
    Acad::ErrorStatus es = ::acdbOpenAcDbObject(
        pObj,
        selected.front(),
        doWrite ? AcDb::kForWrite : AcDb::kForRead);
    Log(L"selected open status=" + std::to_wstring((int)es));
    if (es != Acad::eOk || !pObj) {
        ::acutPrintf(doWrite
            ? L"\nDTMXNRX21OSET: failed to open selected object\n"
            : L"\nDTMXNRX21OPROBE: failed to open selected object\n");
        return;
    }

    Log(L"selected class=" + NativeClassName(pObj));
    void* pIface = api.getParametricInterface((void*)pObj);
    Log(L"selected iface=" + Ptr(pIface));
    CElement* pRoot = pIface && api.getRootElementP ? api.getRootElementP(pIface) : nullptr;
    Log(L"selected root=" + Ptr(pRoot));

    if (!pIface || !pRoot) {
        pObj->close();
        ::acutPrintf(doWrite
            ? L"\nDTMXNRX21OSET: selected object is not parametric\n"
            : L"\nDTMXNRX21OPROBE: selected object is not parametric\n");
        return;
    }

    SafeIfaceCount(api, pIface, L"[IFACE]");
    SafeOwnerCount(api, pIface, L"[OWNER-IFACE]");
    SafeOwnerCount(api, pRoot, L"[OWNER-ROOT]");

    Log(L"--- owner params on pIface ---");
    LogOwnerParams(api, pIface, L"[OWNER-IFACE]", 64);
    Log(L"--- owner params on root element ---");
    LogOwnerParams(api, pRoot, L"[OWNER-ROOT]", 64);

    LogNamedParamSnapshot(api, pIface, pRoot, L"PART_TAG", L"[BEFORE]");
    LogNamedParamSnapshot(api, pIface, pRoot, L"PART_TAGNUMBER", L"[BEFORE]");

    if (doWrite) {
        const wchar_t* kValue = L"DTMX_CPP_OWNER";
        bool changed = false;

        const long long ifaceOwnerCount = SafeOwnerCount(api, pIface, L"[WRITE-OWNER-IFACE]");
        if (ifaceOwnerCount > 0 && ifaceOwnerCount < 2000) {
            changed = TryOwnerSetParameter4(
                api, pIface, L"PART_TAGNUMBER", kValue, L"", L"", L"[WRITE-OWNER-IFACE]");
        }

        if (!changed) {
            void* pRootParam = FindOwnerParamByName(api, pRoot, L"PART_TAGNUMBER");
            if (pRootParam) {
                changed = TryParamSetValue(api, pRootParam, kValue, L"[WRITE-ROOT-PARAM]");
            }
        }

        LogNamedParamSnapshot(api, pIface, pRoot, L"PART_TAGNUMBER", L"[AFTER]");
        ::acutPrintf(changed
            ? L"\nDTMXNRX21OSET: write path executed — check log and properties\n"
            : L"\nDTMXNRX21OSET: no safe write path succeeded — check log\n");
    } else {
        ::acutPrintf(L"\nDTMXNRX21OPROBE: owner snapshot written to log\n");
    }

    pObj->close();
    Log(std::wstring(L"=== ") + (doWrite ? L"DTMXNRX21OSET" : L"DTMXNRX21OPROBE") + L" done ===");
}

static void dtmxNrx21OwnerProbeCmd()
{
    RunDtmxNrx21OwnerCmd(false);
}

static void dtmxNrx21OwnerSetCmd()
{
    RunDtmxNrx21OwnerCmd(true);
}

static void dtmxEditCmd()
{
    dtmxNrx18SetCmd();
}

static void dtmxLogCmd()
{
    dtmxNrx20TreeCmd();
}

static void dtmxNrx18SetCmd()
{
    LogClear();
    Log(L"=== DTMXNRX18SET start ===");

    IMcNativeGate* pGate = GetNativeGate();
    if (!pGate) {
        ::acutPrintf(L"\nDTMXNRX18SET: McTyp not loaded or MCS not active\n");
        return;
    }
    UnitsCsApi api;
    if (!LoadUnitsCsApi(api)) {
        ::acutPrintf(L"\nDTMXNRX18SET: UnitsCS vtable API not available\n");
        return;
    }

    // 1. Selection
    ads_name ss = {};
    bool gotSS = (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) gotSS = (::acedSSGet(nullptr, nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) { Log(L"no selection"); return; }
    long ssLen = 0;
    NCAD_SSLength(ss, &ssLen);
    if (ssLen == 0) { ::acedSSFree(ss); return; }
    Log(L"selected: " + std::to_wstring(ssLen));

    // 2. Enumerate params — MAPI first, vtable fallback
    Log(L"sizeof(AcDbObjectId)=" + std::to_wstring(sizeof(AcDbObjectId)));
    struct ObjEntry { AcDbObjectId oid; std::map<std::wstring,std::wstring> params; };
    std::vector<ObjEntry> objects;
    for (long i = 0; i < ssLen; ++i) {
        ads_name en = {};
        NCAD_SSName(ss, i, en);
        AcDbObjectId oid;
        Acad::ErrorStatus es = ::acdbGetObjectId(oid, en);
        if (es != Acad::eOk) { Log(L"  [" + std::to_wstring(i) + L"] getObjectId es=" + std::to_wstring((int)es)); continue; }

        // --- MAPI path ---
        bool mapiOk = false;
        mcsWorkID mcid;
        HRESULT hr = pGate->getMcsIdByNative(mcid, *(int64_t*)&oid);
        if (SUCCEEDED(hr)) {
            IMcObjectPtr pMcObj = pGate->QueryObject(mcid);
            if (pMcObj) {
                IMcParametricEnt* pPE = ResolveParametric(pGate, pMcObj, 6, false);
                if (pPE) {
                    ObjEntry oe; oe.oid = oid;
                    MapiEnumParams(pPE, oe.params);
                    Log(L"  [" + std::to_wstring(i) + L"] MAPI params=" + std::to_wstring(oe.params.size()));
                    objects.push_back(std::move(oe));
                    mapiOk = true;
                }
            }
        } else {
            Log(L"  [" + std::to_wstring(i) + L"] getMcsId hr=" + Hex(hr));
        }
        if (mapiOk) continue;

        // --- Vtable fallback (linCSParametricSolidBase) ---
        AcDbObject* pDbObjR = nullptr;
        if (::acdbOpenAcDbObject(pDbObjR, oid, AcDb::kForRead) != Acad::eOk) {
            Log(L"  [" + std::to_wstring(i) + L"] vtable: open failed");
            continue;
        }
        void* pIface2 = api.getParametricInterface((void*)pDbObjR);
        if (!pIface2) {
            pDbObjR->close();
            Log(L"  [" + std::to_wstring(i) + L"] vtable: no iface");
            continue;
        }
        std::vector<ParamState> ps = EnumParamsViaNative(api, pIface2);
        pDbObjR->close();
        Log(L"  [" + std::to_wstring(i) + L"] vtable params=" + std::to_wstring(ps.size()));
        ObjEntry oe; oe.oid = oid;
        for (auto& p : ps) oe.params[p.name] = p.dispValue;
        objects.push_back(std::move(oe));
    }
    ::acedSSFree(ss);

    if (objects.empty()) {
        ::acutPrintf(L"\nDTMXNRX18SET: no parametric objects found — see log\n");
        return;
    }
    Log(L"objects total: " + std::to_wstring(objects.size()));

    // 3. Per-object dump in log
    for (size_t oi = 0; oi < objects.size(); ++oi) {
        const ObjEntry& oe = objects[oi];
        Log(L"--- OBJECT [" + std::to_wstring((int)oi) + L"] params=" +
            std::to_wstring(oe.params.size()) + L" ---");
        for (const auto& kv : oe.params) {
            Log(L"  " + kv.first + L" = " + kv.second);
        }
    }

    // 4. Common parameters across all selected objects
    std::map<std::wstring,std::wstring> common = objects[0].params;
    for (size_t oi = 1; oi < objects.size(); ++oi) {
        for (auto it = common.begin(); it != common.end(); ) {
            it = (objects[oi].params.find(it->first) == objects[oi].params.end())
                 ? common.erase(it) : ++it;
        }
    }
    std::vector<ParamState> paramList;
    for (auto& kv : common) {
        ParamState ps; ps.name = kv.first;
        bool mixed = false;
        for (size_t oi = 1; oi < objects.size() && !mixed; ++oi) {
            auto it = objects[oi].params.find(kv.first);
            if (it == objects[oi].params.end() || it->second != kv.second) mixed = true;
        }
        ps.dispValue = mixed ? L"<разные>" : kv.second;
        paramList.push_back(std::move(ps));
    }
    Log(L"common params: " + std::to_wstring(paramList.size()));
    if (paramList.empty()) {
        ::acutPrintf(L"\nDTMXNRX18SET: no common parameters\n");
        return;
    }

    // 5. Dialog
    std::wstring pickedName, pickedValue;
    if (!ShowPickParamDlg(paramList, pickedName, pickedValue)) {
        Log(L"dialog cancelled"); return;
    }
    Log(L"writing: " + pickedName + L" = " + pickedValue);

    // 6. Write via UnitsCS vtable setParameter4
    int ok = 0;
    for (auto& oe : objects) {
        AcDbObject* pDbObj = nullptr;
        if (::acdbOpenAcDbObject(pDbObj, oe.oid, AcDb::kForWrite) != Acad::eOk) continue;
        auto* pIface = api.getParametricInterface((void*)pDbObj);
        if (pIface) {
            api.setParameter4((void*)pIface, pickedName.c_str(), pickedValue.c_str(), L"", L"");
            ++ok;
        }
        pDbObj->close();
    }
    Log(L"=== DTMXNRX18SET done: " + std::to_wstring(ok) + L"/" + std::to_wstring(objects.size()) + L" ===");
    ::acutPrintf(L"\nDTMXNRX18SET: done %d/%zu  %ls = %ls\n",
                 ok, objects.size(), pickedName.c_str(), pickedValue.c_str());
}

BOOL WINAPI DllMain(HINSTANCE hInst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH) {
        g_hInst = hInst;
        ::DisableThreadLibraryCalls(hInst);
        HANDLE hf = ::CreateFileW(L"C:\\Users\\atsarkov\\Desktop\\dtmx_dllmain.txt",
                                  GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, 0, nullptr);
        if (hf != INVALID_HANDLE_VALUE) {
            const char msg[] = "DllMain DLL_PROCESS_ATTACH v11-MAPI-probe\r\n";
            DWORD w; ::WriteFile(hf, msg, (DWORD)(sizeof(msg)-1), &w, nullptr);
            ::CloseHandle(hf);
        }
    }
    return TRUE;
}

// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
// NRX entry point
// в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

#ifdef DTMXNRX_MODULE
  #define DLLEXP __declspec(dllexport)
#else
  #define DLLEXP
#endif

extern "C" DLLEXP AcRx::AppRetCode
acrxEntryPoint(AcRx::AppMsgCode msg, void* appId)
{
    switch (msg) {
    case AcRx::kInitAppMsg:
        ::acrxDynamicLinker->unlockApplication(appId);
        ::acrxDynamicLinker->registerAppMDIAware(appId);
        RegisterDlgClass();
        ::acedRegCmds->addCommand(L"DTMXNRX11P_GROUP", L"DTMXNRX11PPING", L"DTMXNRX11PPING",
                                  ACRX_CMD_TRANSPARENT, dtmxNrxPingCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX11P_GROUP", L"DTMXNRX11PPROBE",  L"DTMXNRX11PPROBE",
                                  ACRX_CMD_MODAL, dtmxNrxProbeCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX11P_GROUP", L"DTMXNRX11PSET",  L"DTMXNRX11PSET",
                                  ACRX_CMD_MODAL, dtmxNrxSetCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12U_GROUP", L"DTMXNRX12UPROBE", L"DTMXNRX12UPROBE",
                                  ACRX_CMD_MODAL, dtmxNrx12UnitsProbeCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12U_GROUP", L"DTMXNRX12USET", L"DTMXNRX12USET",
                                  ACRX_CMD_MODAL, dtmxNrx12UnitsSetCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12B_GROUP", L"DTMXNRX12BUPROBE", L"DTMXNRX12BUPROBE",
                                  ACRX_CMD_MODAL, dtmxNrx12bUnitsProbeCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12B_GROUP", L"DTMXNRX12BUSET", L"DTMXNRX12BUSET",
                                  ACRX_CMD_MODAL, dtmxNrx12bUnitsSetCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12D_GROUP", L"DTMXNRX12DUPROBE", L"DTMXNRX12DUPROBE",
                                  ACRX_CMD_MODAL, dtmxNrx12dUnitsProbeCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12D_GROUP", L"DTMXNRX12DUSET", L"DTMXNRX12DUSET",
                                  ACRX_CMD_MODAL, dtmxNrx12dUnitsSetCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12X_GROUP", L"DTMXNRX12XSETP1", L"DTMXNRX12XSETP1",
                                  ACRX_CMD_MODAL, dtmxNrx12xSetParamOnlyCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12X_GROUP", L"DTMXNRX12XSETP2", L"DTMXNRX12XSETP2",
                                  ACRX_CMD_MODAL, dtmxNrx12xSetParamArg2Cmd);
        ::acedRegCmds->addCommand(L"DTMXNRX12X_GROUP", L"DTMXNRX12XSETP4", L"DTMXNRX12XSETP4",
                                  ACRX_CMD_MODAL, dtmxNrx12xSetParamArg4Cmd);
        ::acedRegCmds->addCommand(L"DTMX_PUBLIC_GROUP", L"DTMXEDIT",  L"DTMXEDIT",
                                  ACRX_CMD_MODAL, dtmxEditCmd);
        ::acedRegCmds->addCommand(L"DTMX_PUBLIC_GROUP", L"DTMXLOG",  L"DTMXLOG",
                                  ACRX_CMD_MODAL, dtmxLogCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX18_GROUP", L"DTMXNRX18SET",  L"DTMXNRX18SET",
                                  ACRX_CMD_MODAL, dtmxNrx18SetCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX19_GROUP", L"DTMXNRX19DUMP", L"DTMXNRX19DUMP",
                                  ACRX_CMD_MODAL, dtmxNrx19DumpCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX20_GROUP", L"DTMXNRX20TREE", L"DTMXNRX20TREE",
                                  ACRX_CMD_MODAL, dtmxNrx20TreeCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX21_GROUP", L"DTMXNRX21OPROBE", L"DTMXNRX21OPROBE",
                                  ACRX_CMD_MODAL, dtmxNrx21OwnerProbeCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX21_GROUP", L"DTMXNRX21OSET", L"DTMXNRX21OSET",
                                  ACRX_CMD_MODAL, dtmxNrx21OwnerSetCmd);
        ::acutPrintf(L"\nDTMXNRX loaded. Main: DTMXEDIT  DTMXLOG\n");
        break;
    case AcRx::kUnloadAppMsg:
        ::acedRegCmds->removeGroup(L"DTMX_PUBLIC_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX11P_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12U_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12B_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12D_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12X_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX18_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX19_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX20_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX21_GROUP");
        UnregisterDlgClass();
        break;
    }
    return AcRx::kRetOK;
}

