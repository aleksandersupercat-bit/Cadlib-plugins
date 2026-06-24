// DtmxNrx.cpp — NRX C++ plugin для записи PART_TAGNUMBER через Model Studio COM
//
// Стратегия:
//   1. IDispatch навигация: COM app → doc → HandleToObject → entity → Element
//   2. QueryInterface для типизированных IElement / IParameters (C++ vtable)
//   3. SetParameter() вызывается через vtable — без IDispatch overhead
//
// IElement и IParameters определены вручную из анализа TypeLib (.tlh)
// чтобы не тянуть #import и зависимость от OdaX/IAcadEntity.

#include "stdafx.h"
#include <fstream>

// ─────────────────────────────────────────────────────────────────
// Типизированные интерфейсы Model Studio (из анализа UnitsCSCom.nrx TypeLib)
// Vtable layout точно соответствует .tlh, сгенерированному #import
// ─────────────────────────────────────────────────────────────────

// IID из TypeLib UnitsCSCom.nrx:
//   IElement    = {32D3F761-7B49-4D57-AC6C-0D0879AC9A75}
//   IParameters = {8A6EB6C1-813B-4B17-941C-2B05D5D1C499}

struct IElement;
struct IParameters;
struct IElements;

struct __declspec(uuid("8A6EB6C1-813B-4B17-941C-2B05D5D1C499"))
IParameters : IDispatch
{
    // vtable после IDispatch slots (QueryInterface, AddRef, Release,
    //   GetTypeInfoCount, GetTypeInfo, GetIDsOfNames, Invoke):
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
    // vtable после IDispatch slots:
    virtual HRESULT __stdcall get_Name(BSTR* pVal)                           = 0;
    virtual HRESULT __stdcall put_Name(BSTR pVal)                            = 0;
    virtual HRESULT __stdcall get_Parameters(IParameters** pVal)             = 0;
    virtual HRESULT __stdcall get_Parent(IElement** pVal)                    = 0;
    virtual HRESULT __stdcall put_Parent(IElement* pVal)                     = 0;
    virtual HRESULT __stdcall get_SubElements(IUnknown** pVal)               = 0;
    virtual HRESULT __stdcall get_Description(BSTR* pVal)                    = 0;
    virtual HRESULT __stdcall get_IsValid(VARIANT_BOOL* pVal)                = 0;
    virtual HRESULT __stdcall get_ElementId(long* pVal)                      = 0;
    virtual HRESULT __stdcall get_ObjectId(long* pVal)                       = 0;
    virtual HRESULT __stdcall get_Implementation(VARIANT* pVal)              = 0;
    virtual HRESULT __stdcall CopyFrom(IElement* pSrc)                      = 0;
    virtual HRESULT __stdcall GetPath(BSTR divider, BSTR* pResult)           = 0;
    virtual HRESULT __stdcall GetParentByLevel(long level, IElement** pVal)  = 0;
    virtual HRESULT __stdcall GetValue(BSTR parameter, BSTR* pResult)        = 0;
    virtual HRESULT __stdcall GetValueComment(BSTR parameter, BSTR* pResult) = 0;
    virtual HRESULT __stdcall AddChild(BSTR Name, IElement** pSrc)           = 0;
    virtual HRESULT __stdcall get_HasParent(VARIANT_BOOL* pVal)              = 0;
    virtual HRESULT __stdcall GetById(long nElementId, IElement** pRes)      = 0;
    virtual HRESULT __stdcall get_Root(IElement** pVal)                      = 0;
    virtual HRESULT __stdcall get_SubElementsAll(IUnknown** pVal)            = 0;
    virtual HRESULT __stdcall get_PathFromRoot(IUnknown** pVal)              = 0;
    virtual HRESULT __stdcall SetParameters(IElement* pSrc)                  = 0;
};

// ─────────────────────────────────────────────────────────────────
// Logging
// ─────────────────────────────────────────────────────────────────

static const wchar_t LOG_PATH[] = L"C:\\Users\\atsarkov\\Desktop\\dtmx_nrx_log.txt";

static void LogClear()
{
    ::DeleteFileW(LOG_PATH);
}

static void Log(const wchar_t* msg)
{
    SYSTEMTIME st; ::GetLocalTime(&st);
    wchar_t ts[24];
    ::swprintf_s(ts, L"%02d:%02d:%02d ", st.wHour, st.wMinute, st.wSecond);
    HANDLE hFile = ::CreateFileW(LOG_PATH, GENERIC_WRITE, FILE_SHARE_READ,
                                 nullptr, OPEN_ALWAYS, 0, nullptr);
    if (hFile != INVALID_HANDLE_VALUE)
    {
        ::SetFilePointer(hFile, 0, nullptr, FILE_END);
        wchar_t buf[4096];
        int n = ::swprintf_s(buf, L"%s%s\n", ts, msg);
        DWORD written;
        ::WriteFile(hFile, buf, n * sizeof(wchar_t), &written, nullptr);
        ::CloseHandle(hFile);
    }
}

static void Log(const std::wstring& msg) { Log(msg.c_str()); }

static std::wstring Hex(HRESULT hr)
{
    wchar_t b[16]; ::swprintf_s(b, L"0x%08X", (unsigned)hr); return b;
}

static std::wstring BstrW(BSTR b)
{
    return (b && b[0]) ? std::wstring(b) : std::wstring(L"<empty>");
}

// ─────────────────────────────────────────────────────────────────
// IDispatch helpers (навигация: app → doc → entity → element)
// ─────────────────────────────────────────────────────────────────

static HRESULT DispGet(IDispatch* p, LPCWSTR name, VARIANT* out)
{
    if (!p) return E_POINTER;
    ::VariantInit(out);
    DISPID id; LPOLESTR n = const_cast<LPOLESTR>(name);
    HRESULT hr = p->GetIDsOfNames(IID_NULL, &n, 1, LOCALE_USER_DEFAULT, &id);
    if (FAILED(hr)) return hr;
    DISPPARAMS dp = {};
    return p->Invoke(id, IID_NULL, LOCALE_USER_DEFAULT,
                     DISPATCH_PROPERTYGET, &dp, out, nullptr, nullptr);
}

static HRESULT DispCall1(IDispatch* p, LPCWSTR name, VARIANT* arg, VARIANT* out)
{
    if (!p) return E_POINTER;
    ::VariantInit(out);
    DISPID id; LPOLESTR n = const_cast<LPOLESTR>(name);
    HRESULT hr = p->GetIDsOfNames(IID_NULL, &n, 1, LOCALE_USER_DEFAULT, &id);
    if (FAILED(hr)) return hr;
    DISPPARAMS dp = { arg, nullptr, 1, 0 };
    return p->Invoke(id, IID_NULL, LOCALE_USER_DEFAULT,
                     DISPATCH_METHOD, &dp, out, nullptr, nullptr);
}

// ─────────────────────────────────────────────────────────────────
// COM app helper
// ─────────────────────────────────────────────────────────────────

static HRESULT GetNanoApp(IDispatch** ppApp)
{
    *ppApp = nullptr;
    static const wchar_t* IDS[] = {
        L"nanoCADx64.Application.24.0",
        L"nanoCADx64.Application.23.0",
        L"nanoCADx64.Application",
    };
    for (auto pid : IDS)
    {
        CLSID cls = {};
        if (FAILED(::CLSIDFromProgID(pid, &cls))) continue;
        IUnknown* pUnk = nullptr;
        if (FAILED(::GetActiveObject(cls, nullptr, &pUnk))) continue;
        HRESULT hr = pUnk->QueryInterface(IID_IDispatch,
                                          reinterpret_cast<void**>(ppApp));
        pUnk->Release();
        if (SUCCEEDED(hr)) return S_OK;
    }
    return E_FAIL;
}

// ─────────────────────────────────────────────────────────────────
// Команды
// ─────────────────────────────────────────────────────────────────

static const wchar_t TARGET_PARAM[] = L"PART_TAGNUMBER";
static const wchar_t TARGET_VALUE[] = L"DTMX_NRX_CPP";

// Пустой VARIANT для необязательных параметров (эквивалент vtMissing)
static VARIANT EmptyVar()
{
    VARIANT v; ::VariantInit(&v); V_VT(&v) = VT_EMPTY; return v;
}

static void dtmxNrxSetCmd()
{
    LogClear();
    Log(L"=== DTMXNRXSET start ===");

    // 1. Implied selection
    ads_name ss;
    if (::acedSSGet(L":I", nullptr, nullptr, nullptr, ss) != RTNORM)
    {
        Log(L"acedSSGet(:I) failed — выделите объекты перед вызовом команды");
        ::acutPrintf(L"\nDTMXNRX: сначала выделите объекты\n");
        return;
    }
    Adesk::Int32 ssLen = 0;
    ::acedSSLength(ss, &ssLen);
    Log(L"Выделено объектов: " + std::to_wstring(ssLen));

    if (ssLen == 0) { ::acedSSFree(ss); return; }

    // 2. COM app
    IDispatch* pApp = nullptr;
    HRESULT hr = GetNanoApp(&pApp);
    Log(L"GetNanoApp hr=" + Hex(hr));
    if (FAILED(hr))
    {
        ::acedSSFree(ss);
        ::acutPrintf(L"\nDTMXNRX: не удалось получить COM объект приложения\n");
        return;
    }

    VARIANT vDoc; ::VariantInit(&vDoc);
    DispGet(pApp, L"ActiveDocument", &vDoc);
    IDispatch* pDoc = (vDoc.vt == VT_DISPATCH) ? vDoc.pdispVal : nullptr;
    Log(L"ActiveDocument vt=" + std::to_wstring(vDoc.vt)
        + L" ptr=" + std::to_wstring((UINT_PTR)pDoc));

    // 3. Цикл по объектам
    for (Adesk::Int32 i = 0; i < ssLen; ++i)
    {
        ads_name ename = {};
        ::acedSSName(ss, i, ename);

        AcDbObjectId objId;
        if (::acdbGetObjectId(objId, ename) != Acad::eOk)
        {
            Log(L"  [" + std::to_wstring(i) + L"] acdbGetObjectId failed");
            continue;
        }

        // Читаем handle для COM навигации
        AcDbObject* pObj = nullptr;
        if (::acdbOpenObject(pObj, objId, AcDb::kForRead) != Acad::eOk)
        {
            Log(L"  [" + std::to_wstring(i) + L"] acdbOpenObject failed");
            continue;
        }
        AcDbHandle hdl;
        pObj->getNcDbHandle(hdl);      // NcDbObject::getNcDbHandle (не getDbHandle)
        wchar_t hBuf[32] = {};
        hdl.getIntoAsciiBuffer(hBuf, 32);
        std::wstring typeName;
        {
            AcRxObject* rxObj = pObj;
            if (rxObj && rxObj->isA())
                typeName = rxObj->isA()->name();
        }
        pObj->close();
        Log(L"  [" + std::to_wstring(i) + L"] handle=" + hBuf
            + L" type=" + typeName);

        if (!pDoc) { Log(L"  pDoc == null, пропуск"); continue; }

        // 3a. HandleToObject через IDispatch
        VARIANT vHnd; ::VariantInit(&vHnd);
        V_VT(&vHnd) = VT_BSTR; V_BSTR(&vHnd) = ::SysAllocString(hBuf);
        VARIANT vEnt; ::VariantInit(&vEnt);
        hr = DispCall1(pDoc, L"HandleToObject", &vHnd, &vEnt);
        ::VariantClear(&vHnd);
        Log(L"    HandleToObject hr=" + Hex(hr) + L" vt=" + std::to_wstring(vEnt.vt));

        if (FAILED(hr) || vEnt.vt != VT_DISPATCH || !vEnt.pdispVal)
        {
            ::VariantClear(&vEnt); continue;
        }
        IDispatch* pEnt = vEnt.pdispVal;

        // 3b. .Element property
        VARIANT vElem; ::VariantInit(&vElem);
        hr = DispGet(pEnt, L"Element", &vElem);
        Log(L"    Element hr=" + Hex(hr) + L" vt=" + std::to_wstring(vElem.vt));

        if (FAILED(hr) || !vElem.pdispVal)
        {
            ::VariantClear(&vEnt); ::VariantClear(&vElem); continue;
        }

        // 3c. QI для типизированного IElement (vtable — без IDispatch)
        IElement* pElem = nullptr;
        static const IID IID_IElement =
            {0x32D3F761,0x7B49,0x4D57,{0xAC,0x6C,0x0D,0x08,0x79,0xAC,0x9A,0x75}};
        hr = vElem.pdispVal->QueryInterface(IID_IElement,
                                            reinterpret_cast<void**>(&pElem));
        Log(L"    QI IElement hr=" + Hex(hr));

        if (SUCCEEDED(hr) && pElem)
        {
            // 3d. GetValue — прямой vtable вызов (NO IDispatch)
            BSTR bsBefore = nullptr;
            pElem->GetValue(::SysAllocString(TARGET_PARAM), &bsBefore);
            Log(L"    Before (vtable GetValue) = " + BstrW(bsBefore));
            ::SysFreeString(bsBefore);

            // 3e. get_Parameters — vtable getter
            IParameters* pParams = nullptr;
            static const IID IID_IParameters =
                {0x8A6EB6C1,0x813B,0x4B17,{0x94,0x1C,0x2B,0x05,0xD5,0xD1,0xC4,0x99}};
            hr = pElem->get_Parameters(&pParams);
            Log(L"    get_Parameters hr=" + Hex(hr));

            // Проверяем: является ли *pParams тем же объектом (QI по IID_IParameters)
            if (SUCCEEDED(hr) && pParams)
            {
                // 3f. SetParameter — ПРЯМОЙ VTABLE ВЫЗОВ, NO IDispatch!
                VARIANT varEmpty1 = EmptyVar();
                VARIANT varEmpty2 = EmptyVar();
                hr = pParams->SetParameter(
                    ::SysAllocString(TARGET_PARAM),
                    ::SysAllocString(TARGET_VALUE),
                    varEmpty1,
                    varEmpty2);
                ::VariantClear(&varEmpty1);
                ::VariantClear(&varEmpty2);
                Log(L"    SetParameter (vtable) hr=" + Hex(hr));

                // Читаем обратно для проверки
                BSTR bsAfter = nullptr;
                pElem->GetValue(::SysAllocString(TARGET_PARAM), &bsAfter);
                Log(L"    After (vtable GetValue) = " + BstrW(bsAfter));
                ::SysFreeString(bsAfter);

                pParams->Release();
            }
            pElem->Release();
        }
        else
        {
            // QI не удался — fallback через IDispatch (для диагностики)
            Log(L"    WARN: QI IElement FAILED — fallback IDispatch SetParameter");
            VARIANT vParams; ::VariantInit(&vParams);
            DispGet(vElem.pdispVal, L"Parameters", &vParams);
            if (vParams.vt == VT_DISPATCH && vParams.pdispVal)
            {
                // 4 аргумента в обратном порядке (rgvarg[0] = последний аргумент)
                VARIANT args[4] = {};
                ::VariantInit(&args[0]); V_VT(&args[0])=VT_BSTR; V_BSTR(&args[0])=::SysAllocString(L"");
                ::VariantInit(&args[1]); V_VT(&args[1])=VT_BSTR; V_BSTR(&args[1])=::SysAllocString(L"");
                ::VariantInit(&args[2]); V_VT(&args[2])=VT_BSTR; V_BSTR(&args[2])=::SysAllocString(TARGET_VALUE);
                ::VariantInit(&args[3]); V_VT(&args[3])=VT_BSTR; V_BSTR(&args[3])=::SysAllocString(TARGET_PARAM);
                DISPID id; LPOLESTR mn = const_cast<LPOLESTR>(L"SetParameter");
                vParams.pdispVal->GetIDsOfNames(IID_NULL,&mn,1,LOCALE_USER_DEFAULT,&id);
                DISPPARAMS dp = {args,nullptr,4,0};
                VARIANT vRes; ::VariantInit(&vRes);
                HRESULT hrFb = vParams.pdispVal->Invoke(id,IID_NULL,LOCALE_USER_DEFAULT,
                                                        DISPATCH_METHOD,&dp,&vRes,nullptr,nullptr);
                Log(L"    Fallback IDispatch SetParameter hr=" + Hex(hrFb));
                for (int k=0;k<4;k++) ::VariantClear(&args[k]);
                ::VariantClear(&vRes);
            }
            ::VariantClear(&vParams);
        }

        ::VariantClear(&vElem);
        ::VariantClear(&vEnt);
    }

    if (pDoc) { /* pDoc AddRef not called separately, owned by vDoc */ }
    ::VariantClear(&vDoc);
    if (pApp) pApp->Release();
    ::acedSSFree(ss);

    Log(L"=== DTMXNRXSET done ===");
    ::acutPrintf(L"\nDTMXNRX: готово — лог: %ls\n", LOG_PATH);
}

static void dtmxNrxPingCmd()
{
    Log(L"DTMXNRXPING — alive");
    ::acutPrintf(L"\nDTMXNRXPING: OK\n");
}

// ─────────────────────────────────────────────────────────────────
// DllMain — диагностика: если этот файл появляется, LoadLibrary прошёл.
// Если файл НЕ появляется при ошибке APPLOAD — значит LoadLibrary не вызывает DllMain.
BOOL WINAPI DllMain(HINSTANCE hInst, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        ::DisableThreadLibraryCalls(hInst);
        // Пишем маркер загрузки до вызова ncrxEntryPoint
        HANDLE hf = ::CreateFileW(L"C:\\Users\\atsarkov\\Desktop\\dtmx_dllmain.txt",
                                  GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, 0, nullptr);
        if (hf != INVALID_HANDLE_VALUE) {
            const char msg[] = "DllMain DLL_PROCESS_ATTACH\r\n";
            DWORD w; ::WriteFile(hf, msg, (DWORD)(sizeof(msg)-1), &w, nullptr);
            ::CloseHandle(hf);
        }
    }
    return TRUE;
}

// ─────────────────────────────────────────────────────────────────
// NRX entry point
// ─────────────────────────────────────────────────────────────────

#ifdef DTMXNRX_MODULE
  #define DLLEXP __declspec(dllexport)
#else
  #define DLLEXP
#endif

extern "C" DLLEXP AcRx::AppRetCode
acrxEntryPoint(AcRx::AppMsgCode msg, void* appId)
{
    switch (msg)
    {
    case AcRx::kInitAppMsg:
        ::acrxDynamicLinker->unlockApplication(appId);
        ::acrxDynamicLinker->registerAppMDIAware(appId);
        ::acedRegCmds->addCommand(L"DTMXNRX_GROUP", L"DTMXNRXPING", L"DTMXNRXPING",
                                  ACRX_CMD_TRANSPARENT, dtmxNrxPingCmd);
        ::acedRegCmds->addCommand(L"DTMXNRX_GROUP", L"DTMXNRXSET", L"DTMXNRXSET",
                                  ACRX_CMD_MODAL | ACRX_CMD_USEPICKSET, dtmxNrxSetCmd);
        ::acutPrintf(L"\nDTMXNRX загружен. Команды: DTMXNRXPING, DTMXNRXSET\n");
        break;

    case AcRx::kUnloadAppMsg:
        ::acedRegCmds->removeGroup(L"DTMXNRX_GROUP");
        break;
    }
    return AcRx::kRetOK;
}
