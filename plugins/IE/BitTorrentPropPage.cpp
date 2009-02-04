// BitTorrentPropPage.cpp : Implementation of the CBitTorrentPropPage property page class.

#include "stdafx.h"
#include "BitTorrent.h"
#include "BitTorrentPropPage.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


IMPLEMENT_DYNCREATE(CBitTorrentPropPage, COlePropertyPage)



// Message map

BEGIN_MESSAGE_MAP(CBitTorrentPropPage, COlePropertyPage)
END_MESSAGE_MAP()



// Initialize class factory and guid

IMPLEMENT_OLECREATE_EX(CBitTorrentPropPage, "BitTorrent.BitTorrentPropPage.1",
	0x2e4ff6c2, 0x65ff, 0x4b2f, 0x84, 0x7f, 0xb1, 0x19, 0xc6, 0x5c, 0x81, 0x46)



// CBitTorrentPropPage::CBitTorrentPropPageFactory::UpdateRegistry -
// Adds or removes system registry entries for CBitTorrentPropPage

BOOL CBitTorrentPropPage::CBitTorrentPropPageFactory::UpdateRegistry(BOOL bRegister)
{
	if (bRegister)
		return AfxOleRegisterPropertyPageClass(AfxGetInstanceHandle(),
			m_clsid, IDS_BITTORRENT_PPG);
	else
		return AfxOleUnregisterClass(m_clsid, NULL);
}



// CBitTorrentPropPage::CBitTorrentPropPage - Constructor

CBitTorrentPropPage::CBitTorrentPropPage() :
	COlePropertyPage(IDD, IDS_BITTORRENT_PPG_CAPTION)
{
}



// CBitTorrentPropPage::DoDataExchange - Moves data between page and properties

void CBitTorrentPropPage::DoDataExchange(CDataExchange* pDX)
{
	DDP_PostProcessing(pDX);
}



// CBitTorrentPropPage message handlers
