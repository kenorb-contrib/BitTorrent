// BitTorrentCtrl.cpp : Implementation of the CBitTorrentCtrl ActiveX Control class.

#include "stdafx.h"
#include "BitTorrent.h"
#include "BitTorrentCtrl.h"
#include "BitTorrentPropPage.h"


#ifdef _DEBUG
#define new DEBUG_NEW
#endif


IMPLEMENT_DYNCREATE(CBitTorrentCtrl, COleControl)



// Message map

BEGIN_MESSAGE_MAP(CBitTorrentCtrl, COleControl)
	ON_OLEVERB(AFX_IDS_VERB_PROPERTIES, OnProperties)
END_MESSAGE_MAP()



// Dispatch map

BEGIN_DISPATCH_MAP(CBitTorrentCtrl, COleControl)
END_DISPATCH_MAP()



// Event map

BEGIN_EVENT_MAP(CBitTorrentCtrl, COleControl)
END_EVENT_MAP()



// Property pages

// TODO: Add more property pages as needed.  Remember to increase the count!
BEGIN_PROPPAGEIDS(CBitTorrentCtrl, 1)
	PROPPAGEID(CBitTorrentPropPage::guid)
END_PROPPAGEIDS(CBitTorrentCtrl)



// Initialize class factory and guid

IMPLEMENT_OLECREATE_EX(CBitTorrentCtrl, "BitTorrent.BitTorrentCtrl.1",
	0x21c4e4b2, 0x40f7, 0x4e77, 0xbf, 0x19, 0x8b, 0xed, 0x71, 0x87, 0xbb, 0x55)



// Type library ID and version

IMPLEMENT_OLETYPELIB(CBitTorrentCtrl, _tlid, _wVerMajor, _wVerMinor)



// Interface IDs

const IID BASED_CODE IID_DBitTorrent =
		{ 0x128CBD7F, 0xBF9, 0x45BC, { 0x96, 0x1A, 0xF8, 0x2B, 0x83, 0xBE, 0x1F, 0x3E } };
const IID BASED_CODE IID_DBitTorrentEvents =
		{ 0xA6D2FDB2, 0x9F28, 0x4574, { 0x83, 0x49, 0xD4, 0xCD, 0x6, 0xE3, 0x2D, 0x86 } };



// Control type information

static const DWORD BASED_CODE _dwBitTorrentOleMisc =
	OLEMISC_INVISIBLEATRUNTIME |
	OLEMISC_ACTIVATEWHENVISIBLE |
	OLEMISC_SETCLIENTSITEFIRST |
	OLEMISC_INSIDEOUT |
	OLEMISC_CANTLINKINSIDE |
	OLEMISC_RECOMPOSEONRESIZE;

IMPLEMENT_OLECTLTYPE(CBitTorrentCtrl, IDS_BITTORRENT, _dwBitTorrentOleMisc)



// CBitTorrentCtrl::CBitTorrentCtrlFactory::UpdateRegistry -
// Adds or removes system registry entries for CBitTorrentCtrl

BOOL CBitTorrentCtrl::CBitTorrentCtrlFactory::UpdateRegistry(BOOL bRegister)
{
	// TODO: Verify that your control follows apartment-model threading rules.
	// Refer to MFC TechNote 64 for more information.
	// If your control does not conform to the apartment-model rules, then
	// you must modify the code below, changing the 6th parameter from
	// afxRegApartmentThreading to 0.

	if (bRegister)
		return AfxOleRegisterControlClass(
			AfxGetInstanceHandle(),
			m_clsid,
			m_lpszProgID,
			IDS_BITTORRENT,
			IDB_BITTORRENT,
			afxRegApartmentThreading,
			_dwBitTorrentOleMisc,
			_tlid,
			_wVerMajor,
			_wVerMinor);
	else
		return AfxOleUnregisterClass(m_clsid, m_lpszProgID);
}



// CBitTorrentCtrl::CBitTorrentCtrl - Constructor

CBitTorrentCtrl::CBitTorrentCtrl()
{
	InitializeIIDs(&IID_DBitTorrent, &IID_DBitTorrentEvents);
	// TODO: Initialize your control's instance data here.
}



// CBitTorrentCtrl::~CBitTorrentCtrl - Destructor

CBitTorrentCtrl::~CBitTorrentCtrl()
{
	// TODO: Cleanup your control's instance data here.
}



// CBitTorrentCtrl::OnDraw - Drawing function

void CBitTorrentCtrl::OnDraw(
			CDC* pdc, const CRect& rcBounds, const CRect& rcInvalid)
{
	if (!pdc)
		return;

	// TODO: Replace the following code with your own drawing code.
	pdc->FillRect(rcBounds, CBrush::FromHandle((HBRUSH)GetStockObject(WHITE_BRUSH)));
	pdc->Ellipse(rcBounds);
}



// CBitTorrentCtrl::DoPropExchange - Persistence support

void CBitTorrentCtrl::DoPropExchange(CPropExchange* pPX)
{
	ExchangeVersion(pPX, MAKELONG(_wVerMinor, _wVerMajor));
	COleControl::DoPropExchange(pPX);

	// TODO: Call PX_ functions for each persistent custom property.
}



// CBitTorrentCtrl::GetControlFlags -
// Flags to customize MFC's implementation of ActiveX controls.
//
DWORD CBitTorrentCtrl::GetControlFlags()
{
	DWORD dwFlags = COleControl::GetControlFlags();


	// The control can activate without creating a window.
	// TODO: when writing the control's message handlers, avoid using
	//		the m_hWnd member variable without first checking that its
	//		value is non-NULL.
	dwFlags |= windowlessActivate;
	return dwFlags;
}



// CBitTorrentCtrl::OnResetState - Reset control to default state

void CBitTorrentCtrl::OnResetState()
{
	COleControl::OnResetState();  // Resets defaults found in DoPropExchange

	// TODO: Reset any other control state here.
}



// CBitTorrentCtrl message handlers
