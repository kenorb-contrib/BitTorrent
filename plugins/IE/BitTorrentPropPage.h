#pragma once

// BitTorrentPropPage.h : Declaration of the CBitTorrentPropPage property page class.


// CBitTorrentPropPage : See BitTorrentPropPage.cpp for implementation.

class CBitTorrentPropPage : public COlePropertyPage
{
	DECLARE_DYNCREATE(CBitTorrentPropPage)
	DECLARE_OLECREATE_EX(CBitTorrentPropPage)

// Constructor
public:
	CBitTorrentPropPage();

// Dialog Data
	enum { IDD = IDD_PROPPAGE_BITTORRENT };

// Implementation
protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV support

// Message maps
protected:
	DECLARE_MESSAGE_MAP()
};

