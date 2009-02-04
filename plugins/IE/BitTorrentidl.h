

/* this ALWAYS GENERATED file contains the definitions for the interfaces */


 /* File created by MIDL compiler version 6.00.0361 */
/* at Wed Feb 07 22:05:37 2007
 */
/* Compiler settings for .\BitTorrent.idl:
    Oicf, W1, Zp8, env=Win32 (32b run)
    protocol : dce , ms_ext, c_ext, robust
    error checks: allocation ref bounds_check enum stub_data 
    VC __declspec() decoration level: 
         __declspec(uuid()), __declspec(selectany), __declspec(novtable)
         DECLSPEC_UUID(), MIDL_INTERFACE()
*/
//@@MIDL_FILE_HEADING(  )

#pragma warning( disable: 4049 )  /* more than 64k source lines */


/* verify that the <rpcndr.h> version is high enough to compile this file*/
#ifndef __REQUIRED_RPCNDR_H_VERSION__
#define __REQUIRED_RPCNDR_H_VERSION__ 475
#endif

#include "rpc.h"
#include "rpcndr.h"

#ifndef __RPCNDR_H_VERSION__
#error this stub requires an updated version of <rpcndr.h>
#endif // __RPCNDR_H_VERSION__


#ifndef __BitTorrentidl_h__
#define __BitTorrentidl_h__

#if defined(_MSC_VER) && (_MSC_VER >= 1020)
#pragma once
#endif

/* Forward Declarations */ 

#ifndef ___DBitTorrent_FWD_DEFINED__
#define ___DBitTorrent_FWD_DEFINED__
typedef interface _DBitTorrent _DBitTorrent;
#endif 	/* ___DBitTorrent_FWD_DEFINED__ */


#ifndef ___DBitTorrentEvents_FWD_DEFINED__
#define ___DBitTorrentEvents_FWD_DEFINED__
typedef interface _DBitTorrentEvents _DBitTorrentEvents;
#endif 	/* ___DBitTorrentEvents_FWD_DEFINED__ */


#ifndef __BitTorrent_FWD_DEFINED__
#define __BitTorrent_FWD_DEFINED__

#ifdef __cplusplus
typedef class BitTorrent BitTorrent;
#else
typedef struct BitTorrent BitTorrent;
#endif /* __cplusplus */

#endif 	/* __BitTorrent_FWD_DEFINED__ */


#ifdef __cplusplus
extern "C"{
#endif 

void * __RPC_USER MIDL_user_allocate(size_t);
void __RPC_USER MIDL_user_free( void * ); 


#ifndef __BitTorrentLib_LIBRARY_DEFINED__
#define __BitTorrentLib_LIBRARY_DEFINED__

/* library BitTorrentLib */
/* [control][helpstring][helpfile][version][uuid] */ 


EXTERN_C const IID LIBID_BitTorrentLib;

#ifndef ___DBitTorrent_DISPINTERFACE_DEFINED__
#define ___DBitTorrent_DISPINTERFACE_DEFINED__

/* dispinterface _DBitTorrent */
/* [helpstring][uuid] */ 


EXTERN_C const IID DIID__DBitTorrent;

#if defined(__cplusplus) && !defined(CINTERFACE)

    MIDL_INTERFACE("128CBD7F-0BF9-45BC-961A-F82B83BE1F3E")
    _DBitTorrent : public IDispatch
    {
    };
    
#else 	/* C style interface */

    typedef struct _DBitTorrentVtbl
    {
        BEGIN_INTERFACE
        
        HRESULT ( STDMETHODCALLTYPE *QueryInterface )( 
            _DBitTorrent * This,
            /* [in] */ REFIID riid,
            /* [iid_is][out] */ void **ppvObject);
        
        ULONG ( STDMETHODCALLTYPE *AddRef )( 
            _DBitTorrent * This);
        
        ULONG ( STDMETHODCALLTYPE *Release )( 
            _DBitTorrent * This);
        
        HRESULT ( STDMETHODCALLTYPE *GetTypeInfoCount )( 
            _DBitTorrent * This,
            /* [out] */ UINT *pctinfo);
        
        HRESULT ( STDMETHODCALLTYPE *GetTypeInfo )( 
            _DBitTorrent * This,
            /* [in] */ UINT iTInfo,
            /* [in] */ LCID lcid,
            /* [out] */ ITypeInfo **ppTInfo);
        
        HRESULT ( STDMETHODCALLTYPE *GetIDsOfNames )( 
            _DBitTorrent * This,
            /* [in] */ REFIID riid,
            /* [size_is][in] */ LPOLESTR *rgszNames,
            /* [in] */ UINT cNames,
            /* [in] */ LCID lcid,
            /* [size_is][out] */ DISPID *rgDispId);
        
        /* [local] */ HRESULT ( STDMETHODCALLTYPE *Invoke )( 
            _DBitTorrent * This,
            /* [in] */ DISPID dispIdMember,
            /* [in] */ REFIID riid,
            /* [in] */ LCID lcid,
            /* [in] */ WORD wFlags,
            /* [out][in] */ DISPPARAMS *pDispParams,
            /* [out] */ VARIANT *pVarResult,
            /* [out] */ EXCEPINFO *pExcepInfo,
            /* [out] */ UINT *puArgErr);
        
        END_INTERFACE
    } _DBitTorrentVtbl;

    interface _DBitTorrent
    {
        CONST_VTBL struct _DBitTorrentVtbl *lpVtbl;
    };

    

#ifdef COBJMACROS


#define _DBitTorrent_QueryInterface(This,riid,ppvObject)	\
    (This)->lpVtbl -> QueryInterface(This,riid,ppvObject)

#define _DBitTorrent_AddRef(This)	\
    (This)->lpVtbl -> AddRef(This)

#define _DBitTorrent_Release(This)	\
    (This)->lpVtbl -> Release(This)


#define _DBitTorrent_GetTypeInfoCount(This,pctinfo)	\
    (This)->lpVtbl -> GetTypeInfoCount(This,pctinfo)

#define _DBitTorrent_GetTypeInfo(This,iTInfo,lcid,ppTInfo)	\
    (This)->lpVtbl -> GetTypeInfo(This,iTInfo,lcid,ppTInfo)

#define _DBitTorrent_GetIDsOfNames(This,riid,rgszNames,cNames,lcid,rgDispId)	\
    (This)->lpVtbl -> GetIDsOfNames(This,riid,rgszNames,cNames,lcid,rgDispId)

#define _DBitTorrent_Invoke(This,dispIdMember,riid,lcid,wFlags,pDispParams,pVarResult,pExcepInfo,puArgErr)	\
    (This)->lpVtbl -> Invoke(This,dispIdMember,riid,lcid,wFlags,pDispParams,pVarResult,pExcepInfo,puArgErr)

#endif /* COBJMACROS */


#endif 	/* C style interface */


#endif 	/* ___DBitTorrent_DISPINTERFACE_DEFINED__ */


#ifndef ___DBitTorrentEvents_DISPINTERFACE_DEFINED__
#define ___DBitTorrentEvents_DISPINTERFACE_DEFINED__

/* dispinterface _DBitTorrentEvents */
/* [helpstring][uuid] */ 


EXTERN_C const IID DIID__DBitTorrentEvents;

#if defined(__cplusplus) && !defined(CINTERFACE)

    MIDL_INTERFACE("A6D2FDB2-9F28-4574-8349-D4CD06E32D86")
    _DBitTorrentEvents : public IDispatch
    {
    };
    
#else 	/* C style interface */

    typedef struct _DBitTorrentEventsVtbl
    {
        BEGIN_INTERFACE
        
        HRESULT ( STDMETHODCALLTYPE *QueryInterface )( 
            _DBitTorrentEvents * This,
            /* [in] */ REFIID riid,
            /* [iid_is][out] */ void **ppvObject);
        
        ULONG ( STDMETHODCALLTYPE *AddRef )( 
            _DBitTorrentEvents * This);
        
        ULONG ( STDMETHODCALLTYPE *Release )( 
            _DBitTorrentEvents * This);
        
        HRESULT ( STDMETHODCALLTYPE *GetTypeInfoCount )( 
            _DBitTorrentEvents * This,
            /* [out] */ UINT *pctinfo);
        
        HRESULT ( STDMETHODCALLTYPE *GetTypeInfo )( 
            _DBitTorrentEvents * This,
            /* [in] */ UINT iTInfo,
            /* [in] */ LCID lcid,
            /* [out] */ ITypeInfo **ppTInfo);
        
        HRESULT ( STDMETHODCALLTYPE *GetIDsOfNames )( 
            _DBitTorrentEvents * This,
            /* [in] */ REFIID riid,
            /* [size_is][in] */ LPOLESTR *rgszNames,
            /* [in] */ UINT cNames,
            /* [in] */ LCID lcid,
            /* [size_is][out] */ DISPID *rgDispId);
        
        /* [local] */ HRESULT ( STDMETHODCALLTYPE *Invoke )( 
            _DBitTorrentEvents * This,
            /* [in] */ DISPID dispIdMember,
            /* [in] */ REFIID riid,
            /* [in] */ LCID lcid,
            /* [in] */ WORD wFlags,
            /* [out][in] */ DISPPARAMS *pDispParams,
            /* [out] */ VARIANT *pVarResult,
            /* [out] */ EXCEPINFO *pExcepInfo,
            /* [out] */ UINT *puArgErr);
        
        END_INTERFACE
    } _DBitTorrentEventsVtbl;

    interface _DBitTorrentEvents
    {
        CONST_VTBL struct _DBitTorrentEventsVtbl *lpVtbl;
    };

    

#ifdef COBJMACROS


#define _DBitTorrentEvents_QueryInterface(This,riid,ppvObject)	\
    (This)->lpVtbl -> QueryInterface(This,riid,ppvObject)

#define _DBitTorrentEvents_AddRef(This)	\
    (This)->lpVtbl -> AddRef(This)

#define _DBitTorrentEvents_Release(This)	\
    (This)->lpVtbl -> Release(This)


#define _DBitTorrentEvents_GetTypeInfoCount(This,pctinfo)	\
    (This)->lpVtbl -> GetTypeInfoCount(This,pctinfo)

#define _DBitTorrentEvents_GetTypeInfo(This,iTInfo,lcid,ppTInfo)	\
    (This)->lpVtbl -> GetTypeInfo(This,iTInfo,lcid,ppTInfo)

#define _DBitTorrentEvents_GetIDsOfNames(This,riid,rgszNames,cNames,lcid,rgDispId)	\
    (This)->lpVtbl -> GetIDsOfNames(This,riid,rgszNames,cNames,lcid,rgDispId)

#define _DBitTorrentEvents_Invoke(This,dispIdMember,riid,lcid,wFlags,pDispParams,pVarResult,pExcepInfo,puArgErr)	\
    (This)->lpVtbl -> Invoke(This,dispIdMember,riid,lcid,wFlags,pDispParams,pVarResult,pExcepInfo,puArgErr)

#endif /* COBJMACROS */


#endif 	/* C style interface */


#endif 	/* ___DBitTorrentEvents_DISPINTERFACE_DEFINED__ */


EXTERN_C const CLSID CLSID_BitTorrent;

#ifdef __cplusplus

class DECLSPEC_UUID("21C4E4B2-40F7-4E77-BF19-8BED7187BB55")
BitTorrent;
#endif
#endif /* __BitTorrentLib_LIBRARY_DEFINED__ */

/* Additional Prototypes for ALL interfaces */

/* end of Additional Prototypes */

#ifdef __cplusplus
}
#endif

#endif


