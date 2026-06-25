// DtmxNrx.cpp вЂ” NRX C++ plugin РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ РїР°СЂР°РјРµС‚СЂР°РјРё Model Studio
// v9: С‡РёСЃС‚С‹Р№ C++ Р±РµР· COM вЂ” MAPI (gpMcNativeGate в†’ IMcParametricEnt::setParams)

#include "stdafx.h"
#include <psapi.h>
#include "IContext.h"
#include "McsUtils.h"
#include "applicationDB.h"
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

struct UnitsCsApi
{
    HMODULE module = nullptr;
    PFN_getParametricInterface getParametricInterface = nullptr;
    PFN_getRootElementP getRootElementP = nullptr;
    PFN_setRootElementP setRootElementP = nullptr;
    PFN_setParameter4 setParameter4 = nullptr;
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

    Echo(L"[UnitsCS] getParametricInterface=" + Ptr((void*)api.getParametricInterface));
    Echo(L"[UnitsCS] getRootElementP=" + Ptr((void*)api.getRootElementP));
    Echo(L"[UnitsCS] setRootElementP=" + Ptr((void*)api.setRootElementP));
    Echo(L"[UnitsCS] setParameter4=" + Ptr((void*)api.setParameter4));

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
    bool isCustom = pGate->IsMCSCustomObject(id) ? true : false;
    Log(prefix + L" classId=" + GuidStr(clsid) +
        L" isMCSCustom=" + std::to_wstring(isCustom ? 1 : 0));
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
};

#define IDC_PARAM_COMBO  301
#define IDC_VALUE_EDIT   302

struct DlgCtx {
    std::vector<ParamState>* pParams = nullptr;
    std::wstring selectedName;
    std::wstring newValue;
    bool applied = false;
    bool done    = false;
    HFONT hFont  = nullptr;
};

static HINSTANCE g_hInst = nullptr;

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

        C(L"STATIC",   L"РџР°СЂР°РјРµС‚СЂ:", SS_LEFT,                                10, 14, 75, 16, 310);
        C(L"COMBOBOX", L"",          CBS_DROPDOWNLIST|WS_VSCROLL|WS_TABSTOP, 90, 11,325,200, IDC_PARAM_COMBO);
        C(L"STATIC",   L"Р—РЅР°С‡РµРЅРёРµ:", SS_LEFT,                                10, 42, 75, 16, 311);
        C(L"EDIT",     L"",          WS_BORDER|ES_AUTOHSCROLL|WS_TABSTOP,    90, 39,325, 22, IDC_VALUE_EDIT);
        C(L"BUTTON",   L"РџСЂРёРјРµРЅРёС‚СЊ", BS_DEFPUSHBUTTON|WS_TABSTOP,           205, 76,100, 28, IDOK);
        C(L"BUTTON",   L"РћС‚РјРµРЅР°",    BS_PUSHBUTTON|WS_TABSTOP,              315, 76,100, 28, IDCANCEL);

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

static bool ShowPickParamDlg(std::vector<ParamState>& params,
                              std::wstring& outName, std::wstring& outValue)
{
    static bool clsReg = false;
    if (!clsReg) {
        WNDCLASSEXW wc = {sizeof(wc)};
        wc.lpfnWndProc   = ParamDlgProc;
        wc.hInstance     = g_hInst;
        wc.hCursor       = ::LoadCursorW(nullptr, IDC_ARROW);
        wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE+1);
        wc.lpszClassName = L"DtmxNrxDlgCls";
        ::RegisterClassExW(&wc);
        clsReg = true;
    }

    DlgCtx ctx; ctx.pParams = &params;

    HWND hDlg = ::CreateWindowExW(
        WS_EX_DLGMODALFRAME | WS_EX_TOPMOST,
        L"DtmxNrxDlgCls",
        L"DTMXNRX вЂ” РџР°СЂР°РјРµС‚СЂС‹ СЌР»РµРјРµРЅС‚РѕРІ",
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

    Log(L"=== MAPI РґРёР°РіРЅРѕСЃС‚РёРєР° ===");
    ::acutPrintf(L"\n=== MAPI DLL РґРёР°РіРЅРѕСЃС‚РёРєР° ===\n");

    int found = 0;
    for (int i = 0; i < nDlls; ++i) {
        dlls[i].hMod = ::GetModuleHandleA(dlls[i].dllName);
        bool ok = (dlls[i].hMod != nullptr);
        if (ok) ++found;
        wchar_t wDll[64]; ::MultiByteToWideChar(CP_ACP, 0, dlls[i].dllName, -1, wDll, 64);
        std::wstring line = std::wstring(L"  ") + wDll;
        line.resize(22, L' ');
        line += ok ? L"Р—РђР“Р РЈР–Р•РќРђ " : L"РЅРµ РЅР°Р№РґРµРЅР°";
        if (ok) line += L" @ " + Ptr(dlls[i].hMod);
        Log(line); ::acutPrintf(L"%s\n", line.c_str());
    }

    IMcNativeGate* pGate = GetNativeGate();
    {
        std::wstring g = L"  gpMcNativeGate: " + Ptr(pGate);
        Log(g); ::acutPrintf(L"%s\n", g.c_str());
    }
    if (pGate) {
        Log(L"  >> IMcNativeGate OK: MAPI РїСѓС‚СЊ РґРѕСЃС‚СѓРїРµРЅ");
        ::acutPrintf(L"  >> IMcNativeGate OK: MAPI РїСѓС‚СЊ РґРѕСЃС‚СѓРїРµРЅ\n");
    }

    Log(std::wstring(L"  Р—Р°РіСЂСѓР¶РµРЅРѕ: ") + std::to_wstring(found) + L"/" + std::to_wstring(nDlls));
    ::acutPrintf(L"=== РіРѕС‚РѕРІРѕ ===\n");
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
        ::acutPrintf(L"\nDTMXNRX11PROBE: РІС‹Р±РµСЂРёС‚Рµ РѕР±СЉРµРєС‚С‹\n");
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
        ::acutPrintf(L"\nDTMXNRX: McTyp.dll РЅРµ Р·Р°РіСЂСѓР¶РµРЅ РёР»Рё MCS РЅРµ Р°РєС‚РёРІРµРЅ\n");
        Log(L"pGate == NULL");
        return;
    }
    Log(L"IMcNativeGate: " + Ptr(pGate));

    // 1. Р’С‹Р±РѕСЂ РѕР±СЉРµРєС‚РѕРІ
    ads_name ss = {};
    bool gotSS = (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) == RTNORM);
    if (!gotSS) {
        ::acutPrintf(L"\nDTMXNRX: РІС‹Р±РµСЂРёС‚Рµ РѕР±СЉРµРєС‚С‹:\n");
        gotSS = (::acedSSGet(nullptr, nullptr, nullptr, nullptr, ss) == RTNORM);
    }
    if (!gotSS) { Log(L"РќРµС‚ РІС‹РґРµР»РµРЅРёСЏ"); return; }

    long ssLen = 0;
    NCAD_SSLength(ss, &ssLen);
    if (ssLen == 0) { ::acedSSFree(ss); return; }
    Log(L"Р’С‹РґРµР»РµРЅРѕ: " + std::to_wstring(ssLen));

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
        ::acutPrintf(L"\nDTMXNRX: РЅРµС‚ РїРѕРґС…РѕРґСЏС‰РёС… РѕР±СЉРµРєС‚РѕРІ (IMcParametricEnt)\n");
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
        ps.dispValue = mixed ? L"<СЂР°Р·РЅС‹Рµ>" : kv.second;
        paramList.push_back(std::move(ps));
    }

    Log(L"РћР±С‰РёС… РїР°СЂР°РјРµС‚СЂРѕРІ: " + std::to_wstring(paramList.size()));
    if (paramList.empty()) {
        ::acutPrintf(L"\nDTMXNRX: РЅРµС‚ РѕР±С‰РёС… РїР°СЂР°РјРµС‚СЂРѕРІ Сѓ РІС‹РґРµР»РµРЅРЅС‹С… РѕР±СЉРµРєС‚РѕРІ\n");
        return;
    }

    // 4. Р”РёР°Р»РѕРі
    std::wstring pickedName, pickedValue;
    if (!ShowPickParamDlg(paramList, pickedName, pickedValue)) {
        Log(L"Р”РёР°Р»РѕРі РѕС‚РјРµРЅС‘РЅ"); return;
    }
    Log(L"РџСЂРёРјРµРЅСЏРµРј: " + pickedName + L" = " + pickedValue);

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
    ::acutPrintf(L"\nDTMXNRX: РіРѕС‚РѕРІРѕ вЂ” РѕР±РЅРѕРІР»РµРЅРѕ %d/%d РѕР±СЉРµРєС‚РѕРІ\n", ok, (int)objects.size());
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
        ::acutPrintf(L"\\nDTMXNRX loaded. Commands: DTMXNRX11PPING, DTMXNRX11PPROBE, DTMXNRX11PSET, DTMXNRX12UPROBE, DTMXNRX12USET, DTMXNRX12BUPROBE, DTMXNRX12BUSET, DTMXNRX12DUPROBE, DTMXNRX12DUSET, DTMXNRX12XSETP1, DTMXNRX12XSETP2, DTMXNRX12XSETP4\\n");
        break;
    case AcRx::kUnloadAppMsg:
        ::acedRegCmds->removeGroup(L"DTMXNRX11P_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12U_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12B_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12D_GROUP");
        ::acedRegCmds->removeGroup(L"DTMXNRX12X_GROUP");
        break;
    }
    return AcRx::kRetOK;
}

