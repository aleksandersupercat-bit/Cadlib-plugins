#pragma once

#pragma pack(push, 8)
#pragma warning(disable: 4786 4996 4251)

#include <SDKDDKVer.h>
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX

// Windows + IUnknown (нужен для MAPI-интерфейсов)
#include <windows.h>
#include <unknwn.h>

// nanoCAD 24.1 MAPI headers may reference MFC types even with HOST_NO_MFC.
class CWnd;
class CString;
class CStringArray;

// NRX SDK с HOST_NO_MFC
#define HOST_NO_MFC
#include "arxHeaders.h"

// MAPI headers — после NRX, не зависят от MFC
#include "IMcNativeGate.h"     // IMcNativeGate, getMcsIdByNative, QueryObject, mcsWorkID
#include "IMcParametricEnt.h"  // IMcParametricEnt, mcsExValueArray, exValue, MCPAR_*

// STL
#include <string>
#include <cstdio>
#include <map>
#include <vector>
#include <cwctype>

#pragma pack(pop)
