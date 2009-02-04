// BitTorrent.cpp : Implementation of CBitTorrentApp and DLL registration.

#include "stdafx.h"
#include "BitTorrent.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif
#include "comcat.h"
#include "strsafe.h"
#include "objsafe.h"
 
// CLSID_SafeItem - Necessary for safe ActiveX control
// Id taken from IMPLEMENT_OLECREATE_EX function in xxxCtrl.cpp
// This if for SafeForInitializing/SafeForScripting auto-registration -- 
// see http://www.codeproject.com/com/CompleteActiveX.asp
 
const CATID CLSID_SafeItem =
{0x21c4e4b2, 0x40f7, 0x4e77, {0xbf, 0x19, 0x8b, 0xed, 0x71, 0x87, 0xbb, 0x55}};
 
// HRESULT CreateComponentCategory - Used to register ActiveX control as safe
 
HRESULT CreateComponentCategory(CATID catid, WCHAR *catDescription)
{
    ICatRegister *pcr = NULL ;
    HRESULT hr = S_OK ;
 
    hr = CoCreateInstance(CLSID_StdComponentCategoriesMgr, 
            NULL, CLSCTX_INPROC_SERVER, IID_ICatRegister, (void**)&pcr);
    if (FAILED(hr))
        return hr;
 
    // Make sure the HKCR\Component Categories\{..catid...}
    // key is registered.
    CATEGORYINFO catinfo;
    catinfo.catid = catid;
    catinfo.lcid = 0x0409 ; // english
    size_t len;
    // Make sure the provided description is not too long.
    // Only copy the first 127 characters if it is.
    // The second parameter of StringCchLength is the maximum
    // number of characters that may be read into catDescription.
    // There must be room for a NULL-terminator. The third parameter
    // contains the number of characters excluding the NULL-terminator.
    hr = StringCchLength((const char *)catDescription, STRSAFE_MAX_CCH, &len);
    if (SUCCEEDED(hr))
        {
        if (len>127)
          {
            len = 127;
          }
        }   
    else
        {
          // TODO: Write an error handler;
        }
    // The second parameter of StringCchCopy is 128 because you need 
    // room for a NULL-terminator.
    hr = StringCchCopy((char *)catinfo.szDescription, len + 1, (const char *)catDescription);
    // Make sure the description is null terminated.
    catinfo.szDescription[len + 1] = '\0';
 
    hr = pcr->RegisterCategories(1, &catinfo);
    pcr->Release();
 
    return hr;
}
 
// HRESULT RegisterCLSIDInCategory -
//      Register your component categories information
 
HRESULT RegisterCLSIDInCategory(REFCLSID clsid, CATID catid)
{
// Register your component categories information.
    ICatRegister *pcr = NULL ;
    HRESULT hr = S_OK ;
    hr = CoCreateInstance(CLSID_StdComponentCategoriesMgr, 
                NULL, CLSCTX_INPROC_SERVER, IID_ICatRegister, (void**)&pcr);
    if (SUCCEEDED(hr))
    {
       // Register this category as being "implemented" by the class.
       CATID rgcatid[1] ;
       rgcatid[0] = catid;
       hr = pcr->RegisterClassImplCategories(clsid, 1, rgcatid);
    }
 
    if (pcr != NULL)
        pcr->Release();
            
    return hr;
}

CBitTorrentApp NEAR theApp;

const GUID CDECL BASED_CODE _tlid =
		{ 0x9F2ED8F3, 0x441F, 0x482D, { 0x98, 0x5D, 0x7E, 0x5B, 0xA0, 0xDF, 0x27, 0x47 } };
const WORD _wVerMajor = 1;
const WORD _wVerMinor = 0;



// CBitTorrentApp::InitInstance - DLL initialization

BOOL CBitTorrentApp::InitInstance()
{
	BOOL bInit = COleControlModule::InitInstance();

	if (bInit)
	{
		// TODO: Add your own module initialization code here.
	}

	return bInit;
}



// CBitTorrentApp::ExitInstance - DLL termination

int CBitTorrentApp::ExitInstance()
{
	// TODO: Add your own module termination code here.

	return COleControlModule::ExitInstance();
}



// DllRegisterServer - Adds entries to the system registry

STDAPI DllRegisterServer(void)
{
    HRESULT hr;    // HResult used by Safety Functions
 
    AFX_MANAGE_STATE(_afxModuleAddrThis);
 
    if (!AfxOleRegisterTypeLib(AfxGetInstanceHandle(), _tlid))
      return ResultFromScode(SELFREG_E_TYPELIB);
 
    if (!COleObjectFactoryEx::UpdateRegistryAll(TRUE))
      return ResultFromScode(SELFREG_E_CLASS);
 
    // Mark the control as safe for initializing.
                                             
    hr = CreateComponentCategory(CATID_SafeForInitializing, 
         L"Controls safely initializable from persistent data!");
    if (FAILED(hr))
      return hr;
 
    hr = RegisterCLSIDInCategory(CLSID_SafeItem, 
         CATID_SafeForInitializing);
    if (FAILED(hr))
        return hr;
 
    // Mark the control as safe for scripting.
 
    hr = CreateComponentCategory(CATID_SafeForScripting, 
                                 L"Controls safely  scriptable!");
    if (FAILED(hr))
        return hr;
 
    hr = RegisterCLSIDInCategory(CLSID_SafeItem, 
                        CATID_SafeForScripting);
    if (FAILED(hr))
        return hr;
 
    return NOERROR;
}



// DllUnregisterServer - Removes entries from the system registry

STDAPI DllUnregisterServer(void)
{
	AFX_MANAGE_STATE(_afxModuleAddrThis);
 
    if (!AfxOleUnregisterTypeLib(_tlid, _wVerMajor, _wVerMinor))
      return ResultFromScode(SELFREG_E_TYPELIB);
 
    if (!COleObjectFactoryEx::UpdateRegistryAll(FALSE))
      return ResultFromScode(SELFREG_E_CLASS);
  
    return NOERROR;
}
