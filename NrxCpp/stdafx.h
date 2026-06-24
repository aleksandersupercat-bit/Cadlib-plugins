#pragma once

#pragma pack(push, 8)
#pragma warning(disable: 4786 4996 4251)

#include <SDKDDKVer.h>
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX

// 1. Сначала Windows + COM вручную.
//    Это нужно сделать ДО NRX headers, так как мы используем HOST_NO_MFC.
//    (HOST_NO_MFC отключает #include <comdef.h> внутри SDK headers)
#include <windows.h>
#include <comdef.h>     // IDispatch, BSTR, VARIANT, _bstr_t, ...
#include <oaidl.h>      // IDispatch, ITypeInfo
#include <oleauto.h>    // SysAllocString, VariantInit, ...
#include <objbase.h>    // CoInitialize, CLSIDFromProgID, GetActiveObject
#include <unknwn.h>     // IUnknown

// 2. NRX SDK с HOST_NO_MFC — отключает CString и MFC зависимости в filer.h и др.
//    nc2ac.h (включается через arxHeaders.h) определит:
//      ads_name → nds_name
//      acedSSGet, acedSSLength, acedSSName, acedSSFree
//      acutPrintf
//      AcDb*, AcRx::, AcDbObjectId, AcDbHandle и т.д.
#define HOST_NO_MFC
#include "arxHeaders.h"

// 3. STL
#include <string>
#include <sstream>
#include <cstdio>

#pragma pack(pop)
