#pragma once

// BitTorrentCtrl.h : Declaration of the CBitTorrentCtrl ActiveX Control class.


// CBitTorrentCtrl : See BitTorrentCtrl.cpp for implementation.

class CBitTorrentCtrl : public COleControl
{
	DECLARE_DYNCREATE(CBitTorrentCtrl)

// Constructor
public:
	CBitTorrentCtrl();

// Overrides
public:
	virtual void OnDraw(CDC* pdc, const CRect& rcBounds, const CRect& rcInvalid);
	virtual void DoPropExchange(CPropExchange* pPX);
	virtual void OnResetState();
	virtual DWORD GetControlFlags();

// Implementation
protected:
	~CBitTorrentCtrl();

	DECLARE_OLECREATE_EX(CBitTorrentCtrl)    // Class factory and guid
	DECLARE_OLETYPELIB(CBitTorrentCtrl)      // GetTypeInfo
	DECLARE_PROPPAGEIDS(CBitTorrentCtrl)     // Property page IDs
	DECLARE_OLECTLTYPE(CBitTorrentCtrl)		// Type name and misc status

// Message maps
	DECLARE_MESSAGE_MAP()

// Dispatch maps
	DECLARE_DISPATCH_MAP()

// Event maps
	DECLARE_EVENT_MAP()

// Dispatch and event IDs
public:
	enum {
	};
};

