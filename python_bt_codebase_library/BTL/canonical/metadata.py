#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a python module for identifying, extracting and canonicalizing
audiovisual content metadata stored in XHTML using a custom
microformat-like tagging system based on the XHTML class attribute.

See the accompanying metadata.html for documentation and
metadata_example.html for an example.
"""

# TODO: implement Creative Commons RDF Metadata support; see
# http://creativecommons.org/technology/metadata/implement

from __future__ import nested_scopes, generators, division
import os
import os.path
import sys
import xml.sax
import xml.sax.handler
import xml.sax.sax2exts
import xml.sax.saxutils
import xml.dom.minidom
import urlparse
import posixpath
import urllib
import urllib2
import re
import cgi
import BTL.canonical.gtin as gtin
import BTL.canonical.grid as grid
import BTL.canonical.isan as isan
import BTL.canonical.isrc as isrc
import BTL.canonical.iswc as iswc
import StringIO

def stringasxhtml(s, source = False, attribute = False):
    if not s:
        return s
    s = cgi.escape(s, quote = attribute)
    us = s.decode('UTF-8')
    usl = us.lstrip()
    if us != usl:
        ou = ord(us[0])
        us = '&#' + str(ou) + ';' + us[1:]
        pass
    usr = us.rstrip()
    if us != usr:
        ou = ord(us[-1])
        us = us[:-1] + '&#' + str(ou) + ';'
        pass
    s = us.encode('UTF-8')
    if attribute:
        s = '&#45;&#45;'.join(s.split('--'))
        pass
    for ordinal in range(0x1, 0x20) + range(0x7f, 0xa0):
        if ordinal in (0xa,) and not attribute:
            continue
        if unichr(ordinal).encode('UTF-8') in s:
            s = ('&#' + str(ordinal) + ';').join(s.split(unichr(ordinal).encode('UTF-8')))
            pass
        pass
    if not source: return s
    s = '<span class="entity-reference">&amp;<span class="entity-reference-value"><span class="entity-reference-name">gt</span>;</span></span>'.join('<span class="entity-reference">&amp;<span class="entity-reference-value"><span class="entity-reference-name">lt</span>;</span></span>'.join('<span class="entity-reference">&amp;<span class="entity-reference-value"><span class="entity-reference-name">quot</span>;</span></span>'.join('<span class="entity-reference">&amp;<span class="entity-reference-value"><span class="entity-reference-name">amp</span>;</span></span>'.join(s.split('&amp;')).split('&quot;')).split('&lt;')).split('&gt;'))
    for ordinal in range(0x1, 0x20) + range(0x7f, 0xa0):
        if ordinal == 0xa and not attribute:
            continue
        if '&#' + str(ordinal) + ';' in s:
            s = ('<span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">' + str(ordinal) + '</span>;</span></span>').join(s.split('&#' + str(ordinal) + ';'))
            pass
        pass
    return s

_namespacenames = {
    'http://purl.org/dc/elements/1.1/': 'dc',
    'http://relaxng.org/ns/compatibility/annotations/1.0': 'a',
    'http://relaxng.org/ns/structure/1.0': 'rng',
    'http://soapinterop.org/': 'sb',
    'http://web.resource.org/cc/': 'cc',
    'http://www.w3.org/1998/Math/MathML': 'm', # also 'math' or 'mml'
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
    'http://www.w3.org/1999/xhtml': 'xhtml', # also 'x', 'xh', 'html'
    'http://www.w3.org/1999/xlink': 'xlink',
    'http://www.w3.org/1999/XSL/Format': 'fo',
    'http://www.w3.org/1999/XSL/Transform': 'xsl',
    'http://www.w3.org/2000/01/rdf-schema#': 'rdfs',
    'http://www.w3.org/2000/svg': 'svg',
    'http://www.w3.org/2000/xmlns/': 'xmlns',
    'http://www.w3.org/2001/SMIL20/': 'smil20',
    'http://www.w3.org/2001/SMIL20/HostLanguage': 'HostLanguage',
    'http://www.w3.org/2001/SMIL20/IntegrationSet': 'IntegrationSet',
    'http://www.w3.org/2001/SMIL20/AccessKeyTiming': 'AccessKeyTiming',
    'http://www.w3.org/2001/SMIL20/AudioLayout': 'AudioLayout',
    'http://www.w3.org/2001/SMIL20/BasicAnimation': 'BasicAnimation',
    'http://www.w3.org/2001/SMIL20/BasicContentControl': 'BasicContentControl',
    'http://www.w3.org/2001/SMIL20/BasicInlineTiming': 'BasicInlineTiming',
    'http://www.w3.org/2001/SMIL20/BasicLayout': 'BasicLayout',
    'http://www.w3.org/2001/SMIL20/BasicLinking': 'BasicLinking',
    'http://www.w3.org/2001/SMIL20/BasicMedia': 'BasicMedia',
    'http://www.w3.org/2001/SMIL20/BasicTimeContainers': 'BasicTimeContainers',
    'http://www.w3.org/2001/SMIL20/BasicTransitions': 'BasicTransitions',
    'http://www.w3.org/2001/SMIL20/BrushMedia': 'BrushMedia',
    'http://www.w3.org/2001/SMIL20/CustomTestAttributes': 'CustomTestAttributes',
    'http://www.w3.org/2001/SMIL20/DeprecatedFeatures': 'smil10-deprecated-features',
    'http://www.w3.org/2001/SMIL20/EventTiming': 'EventTiming',
    'http://www.w3.org/2001/SMIL20/ExclTimeContainers': 'ExclTimeContainers',
    'http://www.w3.org/2001/SMIL20/FillDefault': 'FillDefault',
    'http://www.w3.org/2001/SMIL20/HierarchicalLayout': 'HierarchicalLayout',
    'http://www.w3.org/2001/SMIL20/InlineTransitions': 'InlineTransitions',
    'http://www.w3.org/2001/SMIL20/Language': 'smil20-language',
    'http://www.w3.org/2001/SMIL20/LinkingAttributes': 'LinkingAttributes',
    'http://www.w3.org/2001/SMIL20/MediaAccessibility': 'MediaAccessibility',
    'http://www.w3.org/2001/SMIL20/MediaClipMarkers': 'MediaClipMarkers',
    'http://www.w3.org/2001/SMIL20/MediaClipping': 'MediaClipping',
    'http://www.w3.org/2001/SMIL20/MediaDescription': 'MediaDescription',
    'http://www.w3.org/2001/SMIL20/MediaMarkerTiming': 'MediaMarkerTiming',
    'http://www.w3.org/2001/SMIL20/MediaParam': 'MediaParam',
    'http://www.w3.org/2001/SMIL20/Metainformation': 'Metainformation',
    'http://www.w3.org/2001/SMIL20/MinMaxTiming': 'MinMaxTiming',
    'http://www.w3.org/2001/SMIL20/MultiArcTiming': 'MultiArcTiming',
    'http://www.w3.org/2001/SMIL20/MultiWindowLayout': 'MultiWindowLayout',
    'http://www.w3.org/2001/SMIL20/NestedTimeContainers': 'NestedTimeContainers',
    'http://www.w3.org/2001/SMIL20/ObjectLinking': 'ObjectLinking',
    'http://www.w3.org/2001/SMIL20/PrefetchControl': 'PrefetchControl',
    'http://www.w3.org/2001/SMIL20/RepeatTiming': 'RepeatTiming',
    'http://www.w3.org/2001/SMIL20/RepeatValueTiming': 'RepeatValueTiming',
    'http://www.w3.org/2001/SMIL20/RestartDefault': 'RestartDefault',
    'http://www.w3.org/2001/SMIL20/RestartTiming': 'RestartTiming',
    'http://www.w3.org/2001/SMIL20/SkipContentControl': 'SkipContentControl',
    'http://www.w3.org/2001/SMIL20/SplineAnimation': 'SplineAnimation',
    'http://www.w3.org/2001/SMIL20/Structure': 'Structure',
    'http://www.w3.org/2001/SMIL20/SyncbaseTiming': 'SyncbaseTiming',
    'http://www.w3.org/2001/SMIL20/SyncBehavior': 'SyncBehavior',
    'http://www.w3.org/2001/SMIL20/SyncBehaviorDefault': 'SyncBehaviorDefault',
    'http://www.w3.org/2001/SMIL20/SyncMaster': 'SyncMaster',
    'http://www.w3.org/2001/SMIL20/TimeContainerAttributes': 'TimeContainerAttributes',
    'http://www.w3.org/2001/SMIL20/TimeManipulations': 'TimeManipulations',
    'http://www.w3.org/2001/SMIL20/TransitionModifiers': 'TransitionModifiers',
    'http://www.w3.org/2001/SMIL20/WallclockTiming': 'WallclockTiming',
    'http://www.w3.org/2001/vxml': 'vxml',
    'http://www.w3.org/2001/xml-events': 'ev',
    'http://www.w3.org/2001/XMLSchema#': 'xsd',
    'http://www.w3.org/2001/XMLSchema': 'xs',
    'http://www.w3.org/2001/XMLSchema-instance': 'xsi', # also 's'
    'http://www.w3.org/2002/06/hlink': 'hlink',
    'http://www.w3.org/2002/06/xframes/': 'x',
    'http://www.w3.org/2002/06/xhtml2/': 'xhtml2', # also 'html'
    'http://www.w3.org/2002/11/08-ccpp-client#': 'ccpp-client',
    'http://www.w3.org/2002/11/08-ccpp-schema#': 'ccpp',
    'http://www.w3.org/2002/Math/preference': 'pref',
    'http://www.w3.org/2002/xforms': 'xforms',
    'http://www.w3.org/2003/05/soap-encoding': 'enc',
    'http://www.w3.org/2003/05/soap-envelope': 'env', # also 'soap'
    'http://www.w3.org/2003/05/soap-envelope/role/next': 'role',
    'http://www.w3.org/2003/05/soap-rpc': 'rpc',
    'http://www.w3.org/2003/InkML': 'ink',
    'http://www.w3.org/2004/07/xpath-functions': 'fn',
    'http://www.w3.org/2004/08/representation': 'rep',
    'http://www.w3.org/2004/08/representation/http': 'htx',
    'http://www.w3.org/2004/08/xop/include': 'xop',
    'http://www.w3.org/2004/11/ttaf1#metadata': 'ttm',
    'http://www.w3.org/2004/11/ttaf1#metadata-extension': 'ttmx',
    'http://www.w3.org/2004/11/ttaf1#parameter': 'ttp',
    'http://www.w3.org/2004/11/ttaf1#style': 'tts',
    'http://www.w3.org/2004/11/ttaf1#style-extension': 'ttsx',
    'http://www.w3.org/2004/11/ttaf1': 'tt',
    'http://www.w3.org/2004/11/xmlmime': 'xmime',
    'http://www.w3.org/2004/xforms/': 'xforms',
    'http://www.w3.org/2005/SMIL21/': 'smil21',
    'http://www.w3.org/2005/SMIL21/AccessKeyTiming': 'AccessKeyTiming',
    'http://www.w3.org/2005/SMIL21/AlignmentLayout': 'align',
    'http://www.w3.org/2005/SMIL21/AudioLayout': 'AudioLayout',
    'http://www.w3.org/2005/SMIL21/BackgroundTilingLayout': 'BackgroundTilingLayout',
    'http://www.w3.org/2005/SMIL21/BasicAnimation': 'BasicAnimation',
    'http://www.w3.org/2005/SMIL21/BasicContentControl': 'BasicContentControl',
    'http://www.w3.org/2005/SMIL21/BasicExclTimeContainers': 'excl',
    'http://www.w3.org/2005/SMIL21/BasicInlineTiming': 'BasicInlineTiming',
    'http://www.w3.org/2005/SMIL21/BasicLayout': 'BasicLayout',
    'http://www.w3.org/2005/SMIL21/BasicLinking': 'BasicLinking',
    'http://www.w3.org/2005/SMIL21/BasicMedia': 'BasicMedia',
    'http://www.w3.org/2005/SMIL21/BasicPriorityClassContainers': 'BasicPriorityClassContainers',
    'http://www.w3.org/2005/SMIL21/BasicTimeContainers': 'BasicTimeContainers',
    'http://www.w3.org/2005/SMIL21/BasicTransitions': 'transition',
    'http://www.w3.org/2005/SMIL21/BrushMedia': 'BrushMedia',
    'http://www.w3.org/2005/SMIL21/CustomTestAttributes': 'CustomTestAttributes',
    'http://www.w3.org/2005/SMIL21/EventTiming': 'EventTiming',
    'http://www.w3.org/2005/SMIL21/ExtendedMobile': 'smil21-extended-mobile',
    'http://www.w3.org/2005/SMIL21/FillDefault': 'FillDefault',
    'http://www.w3.org/2005/SMIL21/FullScreenTransitionEffects': 'FullScreenTransitionEffects',
    'http://www.w3.org/2005/SMIL21/HostLanguage': 'HostLanguage',
    'http://www.w3.org/2005/SMIL21/InlineTransitions': 'InlineTransitions',
    'http://www.w3.org/2005/SMIL21/IntegrationSet': 'smil21-integration-set',
    'http://www.w3.org/2005/SMIL21/Language': 'smil21lang',
    'http://www.w3.org/2005/SMIL21/LinkingAttributes': 'LinkingAttributes',
    'http://www.w3.org/2005/SMIL21/MediaAccessibility': 'MediaAccessibility',
    'http://www.w3.org/2005/SMIL21/MediaClipMarkers': 'MediaClipMarkers',
    'http://www.w3.org/2005/SMIL21/MediaClipping': 'MediaClipping',
    'http://www.w3.org/2005/SMIL21/MediaDescription': 'MediaDescription',
    'http://www.w3.org/2005/SMIL21/MediaMarkerTiming': 'MediaMarkerTiming',
    'http://www.w3.org/2005/SMIL21/MediaParam': 'MediaParam',
    'http://www.w3.org/2005/SMIL21/Metainformation': 'Metainformation',
    'http://www.w3.org/2005/SMIL21/MinMaxTiming': 'MinMaxTiming',
    'http://www.w3.org/2005/SMIL21/Mobile': 'smil21-mobile',
    'http://www.w3.org/2005/SMIL21/MobileProfile': 'smp',
    'http://www.w3.org/2005/SMIL21/MultiArcTiming': 'MultiArcTiming',
    'http://www.w3.org/2005/SMIL21/MultiWindowLayout': 'MultiWindowLayout',
    'http://www.w3.org/2005/SMIL21/NestedTimeContainers': 'smil21-nested-time-containers',
    'http://www.w3.org/2005/SMIL21/ObjectLinking': 'ObjectLinking',
    'http://www.w3.org/2005/SMIL21/OverrideLayout': 'override',
    'http://www.w3.org/2005/SMIL21/PrefetchControl': 'PrefetchControl',
    'http://www.w3.org/2005/SMIL21/RepeatTiming': 'RepeatTiming',
    'http://www.w3.org/2005/SMIL21/RepeatValueTiming': 'RepeatValueTiming',
    'http://www.w3.org/2005/SMIL21/RestartDefault': 'RestartDefault',
    'http://www.w3.org/2005/SMIL21/RestartTiming': 'RestartTiming',
    'http://www.w3.org/2005/SMIL21/SkipContentControl': 'SkipContentControl',
    'http://www.w3.org/2005/SMIL21/SMIL10DeprecatedFeatures': 'smil10-deprecated-features',
    'http://www.w3.org/2005/SMIL21/SMIL20DeprecatedFeatures': 'smil20-deprecated-features',
    'http://www.w3.org/2005/SMIL21/SplineAnimation': 'SplineAnimation',
    'http://www.w3.org/2005/SMIL21/Structure': 'Structure',
    'http://www.w3.org/2005/SMIL21/SubRegionLayout': 'subregion',
    'http://www.w3.org/2005/SMIL21/SyncbaseTiming': 'SyncbaseTiming',
    'http://www.w3.org/2005/SMIL21/SyncBehavior': 'SyncBehavior',
    'http://www.w3.org/2005/SMIL21/SyncBehaviorDefault': 'SyncBehaviorDefault',
    'http://www.w3.org/2005/SMIL21/SyncMaster': 'SyncMaster',
    'http://www.w3.org/2005/SMIL21/TimeContainerAttributes': 'TimeContainerAttributes',
    'http://www.w3.org/2005/SMIL21/TimeManipulations': 'TimeManipulations',
    'http://www.w3.org/2005/SMIL21/TransitionModifiers': 'TransitionModifiers',
    'http://www.w3.org/2005/SMIL21/WallclockTiming': 'WallclockTiming',
    'http://www.w3.org/2005/sparql-results#': 'sparql',
    'http://www.w3.org/Graphics/SVG/svg-19990412.dtd': 'svg',
    'http://www.w3.org/TR/1999/REC-html-in-xml': 'xhtml', # non-standard
    'http://www.w3.org/TR/REC-html40': 'HTML', # non-standard
    'http://www.w3.org/TR/REC-smil': 'smil',
    'http://www.w3.org/TR/xhtml1/strict': 'xhtml', # non-standard
    'http://www.w3.org/XML/1998/namespace': 'xml',
    'http://www.wapforum.org/profiles/UAPROF/ccppschema-20010430#': 'prf',
    'urn:schemas-microsoft-com:office:office': 'o',
    'urn:schemas-microsoft-com:office:smarttags': 'st1',
    'urn:schemas-microsoft-com:office:word': 'w',
    'urn:schemas-microsoft-com:time': 't',
    'urn:schemas-microsoft-com:vml': 'v',
    }

_xhtmlEmptyElements = (
    (u'http://www.w3.org/1999/xhtml', u'area'),
    (u'http://www.w3.org/1999/xhtml', u'base'),
    (u'http://www.w3.org/1999/xhtml', u'br'),
    (u'http://www.w3.org/1999/xhtml', u'col'),
    (u'http://www.w3.org/1999/xhtml', u'hr'),
    (u'http://www.w3.org/1999/xhtml', u'img'),
    (u'http://www.w3.org/1999/xhtml', u'input'),
    (u'http://www.w3.org/1999/xhtml', u'link'),
    (u'http://www.w3.org/1999/xhtml', u'meta'),
    (u'http://www.w3.org/1999/xhtml', u'param'),
    (u'http://www.w3.org/TR/REC-html40', u'AREA'),
    (u'http://www.w3.org/TR/REC-html40', u'BASE'),
    (u'http://www.w3.org/TR/REC-html40', u'BR'),
    (u'http://www.w3.org/TR/REC-html40', u'COL'),
    (u'http://www.w3.org/TR/REC-html40', u'HR'),
    (u'http://www.w3.org/TR/REC-html40', u'IMG'),
    (u'http://www.w3.org/TR/REC-html40', u'INPUT'),
    (u'http://www.w3.org/TR/REC-html40', u'LINK'),
    (u'http://www.w3.org/TR/REC-html40', u'META'),
    (u'http://www.w3.org/TR/REC-html40', u'PARAM'),
    )

_noPrefixNamespaces = (
    u'http://www.w3.org/1998/Math/MathML',
    u'http://www.w3.org/1999/xhtml',
    u'http://www.w3.org/2001/SMIL20/Language',
    u'http://www.w3.org/2001/vxml',
    u'http://www.w3.org/2002/06/xframes/',
    u'http://www.w3.org/2002/06/xhtml2/',
    u'http://www.w3.org/2003/InkML',
    u'http://www.w3.org/2005/SMIL21/',
    u'http://www.w3.org/2005/SMIL21/ExtendedMobile',
    u'http://www.w3.org/2005/SMIL21/Language',
    u'http://www.w3.org/2005/SMIL21/Mobile',
    u'http://www.w3.org/2005/sparql-results#',
    u'http://www.w3.org/Graphics/SVG/svg-19990412.dtd',
    u'http://www.w3.org/TR/REC-html40',
    u'http://www.w3.org/TR/REC-smil',
    )

# FIXME: this should probably be somewhere else...
cache_root = reduce(os.path.join,
                    ( sys.prefix, 'BTL', 'canonical', 'metadata', 'cache', 'http' ))

_sysids = [
    'http://www.w3.org/2001/datatypes.dtd',
    'http://www.w3.org/2001/SMIL20/SMIL-anim.mod',
    'http://www.w3.org/2001/SMIL20/smil-attribs-1.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-control.mod',
    'http://www.w3.org/2001/SMIL20/smil-datatypes-1.mod',
    'http://www.w3.org/2001/SMIL20/smil-framework-1.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-layout.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-link.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-media.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-metainformation.mod',
    'http://www.w3.org/2001/SMIL20/smil-model-1.mod',
    'http://www.w3.org/2001/SMIL20/smil-qname-1.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-struct.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-timing.mod',
    'http://www.w3.org/2001/SMIL20/SMIL-transition.mod',
    'http://www.w3.org/2001/SMIL20/SMIL20.dtd',
    'http://www.w3.org/2001/XMLSchema.dtd',
    'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-20020430.dtd',
    'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-20020809.dtd',
    'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-flat-20020430.dtd',
    'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-flat-20020809.dtd',
    'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-flat.dtd',
    'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg.dtd',
    'http://www.w3.org/2002/06/hlink-qname.mod',
    'http://www.w3.org/2002/06/hlink.dtd',
    'http://www.w3.org/2005/SMIL21/SMIL-anim.mod',
    'http://www.w3.org/2005/SMIL21/smil-attribs-1.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-control.mod',
    'http://www.w3.org/2005/SMIL21/smil-datatypes-1.mod',
    'http://www.w3.org/2005/SMIL21/smil-extended-mobile-profile-model-1.mod',
    'http://www.w3.org/2005/SMIL21/smil-framework-1.mod',
    'http://www.w3.org/2005/SMIL21/smil-language-profile-model-1.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-layout.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-link.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-media.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-metainformation.mod',
    'http://www.w3.org/2005/SMIL21/smil-mobile-profile-model-1.mod',
    'http://www.w3.org/2005/SMIL21/smil-qname-1.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-struct.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-timing.mod',
    'http://www.w3.org/2005/SMIL21/SMIL-transition.mod',
    'http://www.w3.org/2005/SMIL21/SMIL21.dtd',
    'http://www.w3.org/2005/SMIL21/SMIL21ExtendedMobile.dtd',
    'http://www.w3.org/2005/SMIL21/SMIL21Mobile.dtd',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-animation.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-animevents-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-clip.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-filter.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-font.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-graphics-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-paint-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-structure.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-basic-text.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-clip.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-conditional.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-container-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-core-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-cursor.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-datatypes.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-docevents-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-extensibility.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-extresources-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-filter.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-font.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-framework.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-gradient.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-graphevents-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-graphics-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-hyperlink.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-image.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-marker.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-mask.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-opacity-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-paint-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-pattern.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-profile.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-qname.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-script.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-shape.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-structure.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-style.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-text.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-view.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-viewport-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg-xlink-attrib.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-attribs.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-basic-attribs.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-basic-model.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-basic.dtd',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-model.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny-attribs.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny-model.mod',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny.dtd',
    'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd',
    'http://www.w3.org/Graphics/SVG/svg-19990412.dtd',
    'http://www.w3.org/MarkUp/DTD/xframes-1.dtd',
    'http://www.w3.org/MarkUp/DTD/xframes-qname-1.mod',
    'http://www.w3.org/MarkUp/DTD/xhtml-lat1.ent',
    'http://www.w3.org/MarkUp/DTD/xhtml-special.ent',
    'http://www.w3.org/MarkUp/DTD/xhtml-symbol.ent',
    'http://www.w3.org/MarkUp/DTD/xhtml2.dtd',
    'http://www.w3.org/MarkUp/DTD/xml-events-1.mod',
    'http://www.w3.org/MarkUp/DTD/xml-events-qname-1.mod',
    'http://www.w3.org/Math/DTD/mathml1/isoamsa.ent',
    'http://www.w3.org/Math/DTD/mathml1/isoamsb.ent',
    'http://www.w3.org/Math/DTD/mathml1/isoamsc.ent',
    'http://www.w3.org/Math/DTD/mathml1/isoamsn.ent',
    'http://www.w3.org/Math/DTD/mathml1/isoamso.ent',
    'http://www.w3.org/Math/DTD/mathml1/isoamsr.ent',
    'http://www.w3.org/Math/DTD/mathml1/isobox.ent',
    'http://www.w3.org/Math/DTD/mathml1/isocyr1.ent',
    'http://www.w3.org/Math/DTD/mathml1/isocyr2.ent',
    'http://www.w3.org/Math/DTD/mathml1/isodia.ent',
    'http://www.w3.org/Math/DTD/mathml1/isogrk1.ent',
    'http://www.w3.org/Math/DTD/mathml1/isogrk2.ent',
    'http://www.w3.org/Math/DTD/mathml1/isogrk3.ent',
    'http://www.w3.org/Math/DTD/mathml1/isogrk4.ent',
    'http://www.w3.org/Math/DTD/mathml1/isolat1.ent',
    'http://www.w3.org/Math/DTD/mathml1/isolat2.ent',
    'http://www.w3.org/Math/DTD/mathml1/isomfrk.ent',
    'http://www.w3.org/Math/DTD/mathml1/isomopf.ent',
    'http://www.w3.org/Math/DTD/mathml1/isomscr.ent',
    'http://www.w3.org/Math/DTD/mathml1/isonum.ent',
    'http://www.w3.org/Math/DTD/mathml1/isopub.ent',
    'http://www.w3.org/Math/DTD/mathml1/isotech.ent',
    'http://www.w3.org/Math/DTD/mathml1/mathml.dtd',
    'http://www.w3.org/Math/DTD/mathml1/mmlalias.ent',
    'http://www.w3.org/Math/DTD/mathml1/mmlextra.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isobox.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isocyr1.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isocyr2.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isodia.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isolat1.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isolat2.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isonum.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso8879/isopub.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isoamsa.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isoamsb.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isoamsc.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isoamsn.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isoamso.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isoamsr.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isogrk3.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isogrk4.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isomfrk.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isomopf.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isomscr.ent',
    'http://www.w3.org/Math/DTD/mathml2/iso9573-13/isotech.ent',
    'http://www.w3.org/Math/DTD/mathml2/mathml/mmlalias.ent',
    'http://www.w3.org/Math/DTD/mathml2/mathml/mmlextra.ent',
    'http://www.w3.org/Math/DTD/mathml2/mathml2-a.dtd',
    'http://www.w3.org/Math/DTD/mathml2/mathml2-qname-1.mod',
    'http://www.w3.org/Math/DTD/mathml2/mathml2.dtd',
    'http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f-a.dtd',
    'http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f.dtd',
    'http://www.w3.org/TR/2000/REC-xhtml1-20000126/DTD/xhtml1-frameset.dtd',
    'http://www.w3.org/TR/2000/REC-xhtml1-20000126/DTD/xhtml1-strict.dtd',
    'http://www.w3.org/TR/2000/REC-xhtml1-20000126/DTD/xhtml1-transitional.dtd',
    'http://www.w3.org/TR/2001/REC-MathML2-20010221/dtd/xhtml-math11-f.dtd',
    'http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd',
    'http://www.w3.org/TR/2001/REC-xhtml11-20010531/DTD/xhtml11.dtd',
    'http://www.w3.org/TR/2004/CR-xhtml-print-20040120/DTD/xhtml-print10-model-1.mod',
    'http://www.w3.org/TR/2004/CR-xhtml-print-20040120/DTD/xhtml-print10.dtd',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-anim.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/smil-attribs-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-control.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/smil-datatypes-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/smil-DTD.dtd',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/smil-framework-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-layout.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-link.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-media.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-metainformation.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/smil-model-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/smil-qname-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-struct.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-timing.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL-transition.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/SMIL20.dtd',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-anim.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil-attribs-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-control.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil-datatypes-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil-extended-mobile-profile-model-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil-framework-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil-language-profile-model-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-layout.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-link.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-media.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-metainformation.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil-mobile-profile-model-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil-qname-1.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-struct.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-timing.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL-transition.mod',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL21.dtd',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil21.dtd',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL21ExtendedMobile.dtd',
    'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/SMIL21Mobile.dtd',
    'http://www.w3.org/TR/MathML2/dtd/mathml2.dtd',
    'http://www.w3.org/TR/MathML2/dtd/xhtml-math11-f.dtd',
    'http://www.w3.org/TR/ruby/xhtml-ruby-1.mod',
    'http://www.w3.org/TR/voicexml20/vxml.dtd',
    'http://www.w3.org/TR/voicexml21/vxml.dtd',
    'http://www.w3.org/TR/xhtml-basic/xhtml-arch-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-attribs-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-base-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-basic-form-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-basic-table-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-basic10-model-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-basic10.dtd',
    'http://www.w3.org/TR/xhtml-basic/xhtml-blkphras-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-blkstruct-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-charent-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-datatypes-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-framework-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-hypertext-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-image-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-inlphras-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-inlstruct-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-lat1.ent',
    'http://www.w3.org/TR/xhtml-basic/xhtml-link-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-list-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-meta-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-notations-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-object-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-param-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-qname-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-special.ent',
    'http://www.w3.org/TR/xhtml-basic/xhtml-struct-1.mod',
    'http://www.w3.org/TR/xhtml-basic/xhtml-symbol.ent',
    'http://www.w3.org/TR/xhtml-basic/xhtml-text-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-applet-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-arch-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-attribs-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-base-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-basic-form-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-basic-table-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-bdo-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-blkphras-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-blkpres-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-blkstruct-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-charent-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-csismap-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-datatypes-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-edit-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-events-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-form-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-frames-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-framework-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-hypertext-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-iframe-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-image-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-inlphras-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-inlpres-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-inlstruct-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-inlstyle-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-lat1.ent',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-legacy-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-legacy-redecl-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-link-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-list-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-meta-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-nameident-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-notations-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-object-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-param-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-pres-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-qname-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-script-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-special.ent',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-ssismap-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-struct-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-style-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-symbol.ent',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-table-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-target-1.mod',
    'http://www.w3.org/TR/xhtml-modularization/DTD/xhtml-text-1.mod',
    'http://www.w3.org/TR/xhtml1/DTD/xhtml-lat1.ent',
    'http://www.w3.org/TR/xhtml1/DTD/xhtml-special.ent',
    'http://www.w3.org/TR/xhtml1/DTD/xhtml-symbol.ent',
    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd',
    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd',
    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd',
    'http://www.w3.org/TR/xhtml11/DTD/xhtml11-model-1.mod',
    'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd',
    ]

# FIXME: commented-out DTDs use different default namespace prefices;
# theoretically we could re-serialize with different prefices to
# accomodate this...
_namespaceCatalog = {
    None:
    (
    (None, u'http://www.w3.org/Math/DTD/mathml1/mathml.dtd'),
    ),
    u'http://www.w3.org/2002/06/xframes/':
    (
    (u'-//W3C//DTD XFrames 1.0//EN', u'http://www.w3.org/MarkUp/DTD/xframes-1.dtd'),
    ),
    u'http://www.w3.org/1998/Math/MathML':
    (
    (u'-//W3C//DTD MathML 2.0//EN', u'http://www.w3.org/TR/MathML2/dtd/mathml2.dtd'),
    (u'-//W3C//DTD MathML 2.0//EN', u'http://www.w3.org/Math/DTD/mathml2/mathml2.dtd'),
    ),
    u'http://www.w3.org/2002/06/xhtml2/':
    (
    (u'-//W3C//DTD XHTML 2.0//EN', u'http://www.w3.org/MarkUp/DTD/xhtml2.dtd'),
    ),
    u'http://www.w3.org/2000/svg':
    (
    #(u'-//W3C//DTD SVG 1.1 Tiny//EN', u'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny.dtd'),
    #(u'-//W3C//DTD SVG 1.1 Basic//EN', u'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-basic.dtd'),
    #(u'-//W3C//DTD SVG 1.1//EN', u'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd'),
    (u'-//W3C//DTD XHTML 1.1 plus MathML 2.0 plus SVG 1.1//EN', u'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-flat.dtd'),
    #(u'-//W3C//DTD SVG 1.0//EN', u'http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd'),
    ),
    u'http://www.w3.org/Graphics/SVG/svg-19990412.dtd':
    (
    (u'-//W3C//DTD SVG April 1999//EN', u'http://www.w3.org/Graphics/SVG/svg-19990412.dtd'),
    ),
    u'http://www.w3.org/2002/06/hlink':
    (
    (u'-//W3C//DTD HLink 1.0//EN', u'http://www.w3.org/2002/06/hlink.dtd'),
    ),
    u'http://www.w3.org/1999/xhtml':
    (
    (u'-//W3C//DTD XHTML-Print 1.0//EN', u'http://www.w3.org/TR/2004/CR-xhtml-print-20040120/DTD/xhtml-print10.dtd'),
    (u'-//W3C//DTD XHTML Basic 1.0//EN', u'http://www.w3.org/TR/xhtml-basic/xhtml-basic10.dtd'),
    (u'-//W3C//DTD XHTML 1.1//EN', u'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd'),
    (u'-//W3C//DTD XHTML 1.1 plus MathML 2.0//EN', u'http://www.w3.org/Math/DTD/mathml2/xhtml-math11-f.dtd'),
    (u'-//W3C//DTD XHTML 1.1 plus MathML 2.0 plus SVG 1.1//EN', u'http://www.w3.org/2002/04/xhtml-math-svg/xhtml-math-svg-flat.dtd'),
    (u'-//W3C//DTD XHTML 1.0 Strict//EN', u'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'),
    (u'-//W3C//DTD XHTML 1.0 Frameset//EN', u'http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd'),
    (u'-//W3C//DTD XHTML 1.0 Transitional//EN', u'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'),
    ),
    u'http://www.w3.org/2001/XMLSchema':
    (
    (u'-//W3C//DTD XMLSCHEMA 200102//EN', u'http://www.w3.org/2001/XMLSchema.dtd'),
    ),
    u'http://www.w3.org/2001/SMIL20/Language':
    (
    (u'-//W3C//DTD SMIL 2.0//EN', u'http://www.w3.org/2001/SMIL20/SMIL20.dtd'),
    (u'-//W3C//DTD SMIL 2.0//EN', u'http://www.w3.org/TR/2005/REC-SMIL2-20050107/smil20DTD/smil-DTD.dtd'),
    ),
    u'http://www.w3.org/2005/SMIL21/Language':
    (
    (u'-//W3C//DTD SMIL 2.1//EN', u'http://www.w3.org/2005/SMIL21/SMIL21.dtd'),
    (u'-//W3C//DTD SMIL 2.1//EN', u'http://www.w3.org/TR/2005/REC-SMIL2-20051213/smil21DTD/smil21.dtd'),
    ),
    u'http://www.w3.org/2005/SMIL21/Mobile':
    (
    (u'-//W3C//DTD SMIL 2.1 Mobile//EN', u'http://www.w3.org/2005/SMIL21/SMIL21Mobile.dtd'),
    ),
    u'http://www.w3.org/2005/SMIL21/ExtendedMobile':
    (
    (u'-//W3C//DTD SMIL 2.1 Extended Mobile//EN', u'http://www.w3.org/2005/SMIL21/SMIL21ExtendedMobile.dtd'),
    ),
    u'http://www.w3.org/2001/vxml':
    (
    (u'-//W3C//DTD VOICEXML 2.1//EN', u'http://www.w3.org/TR/voicexml21/vxml.dtd'),
    (u'-//W3C//DTD VOICEXML 2.0//EN', u'http://www.w3.org/TR/voicexml20/vxml.dtd'),
    ),
    }

def domnodeinnertext(xmldomnode, allow_lookaside = False):
    '''

    Serialize a DOM node to text; when the optional flag
    allow_lookaside = True is provided, this supports some intelligent
    microformatting-style lookasides for XHTML 1.0 and 1.1:

    <abbr title="text">...</abbr> => "text"
    <abbr xhtml:title="text">...</abbr> => "text"
    <img alt="text" ... /> => "text"
    <img xhtml:alt="text" ... /> => "text"
    <br /> => "\n"

    and for VML:
    
    <v:... alt="text">...</v:...> => "text"
    <... v:alt="text">...</...> => "text"

    the HTML 4-based all-uppercase "XHTML" is supported too.
    '''
    o = []
    if xmldomnode.nodeType in (xmldomnode.TEXT_NODE, xmldomnode.CDATA_SECTION_NODE):
        o.append(xmldomnode.data.encode('UTF-8'))
        pass
    elif xmldomnode.nodeType in (xmldomnode.ELEMENT_NODE, xmldomnode.DOCUMENT_NODE, xmldomnode.DOCUMENT_FRAGMENT_NODE):
        nodeURI, nodeLocalName = (xmldomnode.namespaceURI, xmldomnode.localName)
        if allow_lookaside and xmldomnode.nodeType == xmldomnode.ELEMENT_NODE:
            if (nodeURI, nodeLocalName) in ((u'http://www.w3.org/1999/xhtml', u'abbr'),):
                if xmldomnode.hasAttributeNS(None, u'title'):
                    return xmldomnode.getAttributeNS(None,  u'title').encode('UTF-8')
                elif xmldomnode.hasAttributeNS(u'http://www.w3.org/1999/xhtml', u'title'):
                    return xmldomnode.getAttributeNS(u'http://www.w3.org/1999/xhtml', u'title').encode('UTF-8')
                pass
            elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/1999/xhtml', u'img'),):
                if xmldomnode.hasAttributeNS(None, u'alt'):
                    return xmldomnode.getAttributeNS(None,  u'alt').encode('UTF-8')
                elif xmldomnode.hasAttributeNS(u'http://www.w3.org/1999/xhtml', u'alt'):
                    return xmldomnode.getAttributeNS(u'http://www.w3.org/1999/xhtml', u'alt').encode('UTF-8')
                pass
            elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/1999/xhtml', u'br'),):
                return '\n'
            elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'ABBR'),):
                if xmldomnode.hasAttributeNS(None, u'TITLE'):
                    return xmldomnode.getAttributeNS(None,  u'TITLE').encode('UTF-8')
                elif xmldomnode.hasAttributeNS(u'http://www.w3.org/TR/REC-html40', u'TITLE'):
                    return xmldomnode.getAttributeNS(u'http://www.w3.org/TR/REC-html40', u'TITLE').encode('UTF-8')
                pass
            elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'IMG'),):
                if xmldomnode.hasAttributeNS(None, u'ALT'):
                    return xmldomnode.getAttributeNS(None,  u'ALT').encode('UTF-8')
                elif xmldomnode.hasAttributeNS(u'http://www.w3.org/TR/REC-html40', u'ALT'):
                    return xmldomnode.getAttributeNS(u'http://www.w3.org/TR/REC-html40', u'ALT').encode('UTF-8')
                pass
            elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'BR'),):
                return '\n'
            elif nodeURI == u'urn:schemas-microsoft-com:vml' and xmldomnode.hasAttributeNS(None, u'alt'):
                return xmldomnode.getAttributeNS(None, u'alt').encode('UTF-8')
                pass
            elif xmldomnode.hasAttributeNS(u'urn:schemas-microsoft-com:vml', u'alt'):
                return xmldomnode.getAttributeNS(u'urn:schemas-microsoft-com:vml', u'alt').encode('UTF-8')
                pass
            pass
        for childNode in xmldomnode.childNodes:
            o.append(domnodeinnertext(childNode, allow_lookaside = allow_lookaside))
            pass
        pass
    return ''.join(o)

def makePrefix(namespaceURI, namespaces, outputbuffer):
    namespaceURI = namespaceURI or u''
    namespaceURI = namespaceURI.strip()
    if namespaceURI == 'http://www.w3.org/XML/1998/namespace':
        return 'xml:'
    if namespaceURI == 'http://www.w3.org/2000/xmlns/':
        return 'xmlns:'
    if not namespaces.has_key(namespaceURI):
        prefix = None
        if _namespacenames.has_key(namespaceURI):
            prefix = _namespacenames[namespaceURI]
            pass
        disambiguation = 0
        while True:
            if prefix and prefix not in namespaces.itervalues():
                break
            prefix = 'ns%s' % disambiguation
            disambiguation += 1
            pass
        namespaces[namespaceURI] = prefix
        outputbuffer.append(' <span class="attribute"><span class="attribute-name">%s</span>=<span class="attribute-value">&quot;%s&quot;</span></span>' %
                     (stringasxhtml((u'xmlns:' + prefix).encode('UTF-8'), source = True),
                      stringasxhtml(namespaceURI.encode('UTF-8'), source = True, attribute = True)))
        pass
    return namespaces[namespaceURI] + u':'

def makeAttrPrefix(attrURI, namespaces, outputbuffer):
    attrPrefix = ''
    if attrURI is not None:
        attrPrefix = makePrefix(attrURI, namespaces, outputbuffer)
        pass
    return attrPrefix

def domnodesource(xmldomnode, xmlns = None, namespaces = None, format = 'xhtml', recursive = True, lang = '', space = None, classes = None, metadata = None, stderr = sys.stderr):
    '''
    Serializes a DOM node to XHTML (default) or text, altering
    namespace prefixes so that only namespace-free and XHTML names
    occur without a prefix, and regular prefices are used for all
    other namespaces. This also parses avcontent metadata.

    Also converts elements and attributes from the older HTML
    namespace to their equivalents in the newer XHTML namespace.

    Only empty elements found in _xhtmlEmptyElements will be emitted
    using the /> emtpy-element notation.

    Only elements from _noPrefixNamespaces and elements with no
    namespaceURI will be emitted without a namespace prefix.

    The optional flag recursive = False prevents serialization of
    child nodes.

    The optional argument lang provides the value for xml:lang in the
    serialization context; this is used to suppress duplicate xml:lang
    values in child nodes.

    The optional argument space provides the value for xml:space in
    the serialization context; this is used to suppress duplicate
    xml:space values in child nodes.

    The optional argument classes provides a dictionary of class names
    in effect at a given level, with the values being the number of
    levels of remove between this element and the given class name.

    The optional argument metadata provides a serialization context for
    avcontent metadata.
    '''
    assert format in ('xhtml', 'text')
    if format == 'text':
        return domnodeinnertext(xml.dom.minidom.parseString('<div xmlns="http://www.w3.org/1999/xhtml">%s</div>' % domnodesource(xmldomnode, xmlns = xmlns, namespaces = namespaces, format = 'xhtml', recursive = recursive, lang = lang, space = space, classes = classes, metadata = metadata, stderr = stderr)))
    namespaces = dict((namespaces or {}).items())
    classes = dict([ (className, level + 1) for className, level in (classes or {}).items() ])
    o = []
    if xmldomnode.nodeType == xmldomnode.ELEMENT_NODE:
        addns = []
        o.append('<span class="element">')
        o.append(stringasxhtml('<'))
        prefix = ''
        nodeURI, nodeLocalName = (xmldomnode.namespaceURI, xmldomnode.localName)
        if nodeURI and nodeURI not in _noPrefixNamespaces:
            prefix = makePrefix(nodeURI, namespaces, addns)
            pass
        elif xmlns != nodeURI:
            addns.append(' <span class="attribute"><span class="attribute-name">%s</span>=<span class="attribute-value">&quot;%s&quot;</span></span>' %
                         (stringasxhtml('xmlns', source = True),
                          stringasxhtml((nodeURI or u'').encode('UTF-8'), source = True, attribute = True)))
            xmlns = nodeURI
            pass
        o.append('<span class="element-name">%s</span>' % stringasxhtml((prefix + nodeLocalName).encode('UTF-8'), source = True))
        o += addns
        addattrs = []
        href = None
        rels = { }
        revs = { }
        if xmldomnode.hasAttributes():
            attrlist = [ i for i in xmldomnode.attributes.keysNS() ]
            attrlist.sort()
            for attrURI, attrLocalName in attrlist:
                attrNode = xmldomnode.getAttributeNodeNS(attrURI, attrLocalName)
                if attrURI == u'http://www.w3.org/2000/xmlns/':
                    # we generate our own xmlns attribute, so skip this
                    continue
                elif (attrURI == u'http://www.w3.org/XML/1998/namespace') and (attrLocalName == 'space'):
                    xml_space = xmldomnode.getAttributeNS(attrURI, attrLocalName).encode('UTF-8')
                    if xml_space == space:
                        continue
                    space = xml_space
                    pass
                elif (attrURI == u'http://www.w3.org/XML/1998/namespace') and (attrLocalName == 'lang'):
                    xml_lang = xmldomnode.getAttributeNS(attrURI, attrLocalName).encode('UTF-8')
                    if xml_lang == lang:
                        continue
                    lang = xml_lang
                    pass
                elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/1999/xhtml', u'a'), (u'http://www.w3.org/1999/xhtml', u'link')) and (attrURI and attrURI or nodeURI, attrLocalName) in ((u'http://www.w3.org/1999/xhtml', u'href'),):
                    href = xmldomnode.getAttributeNS(attrURI, attrLocalName).encode('UTF-8')
                    pass
                elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'A'), (u'http://www.w3.org/TR/REC-html40', u'LINK')) and (attrURI and attrURI or nodeURI, attrLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'HREF'),):
                    href = xmldomnode.getAttributeNS(attrURI, attrLocalName).encode('UTF-8')
                    pass
                elif (attrURI and attrURI or nodeURI, attrLocalName) in ((u'urn:schemas-microsoft-com:vml', u'href'),):
                    href = xmldomnode.getAttributeNS(attrURI, attrLocalName).encode('UTF-8')
                    pass
                elif (attrURI and attrURI or nodeURI, attrLocalName) in ((u'http://www.w3.org/1999/xhtml', u'class'), (u'http://www.w3.org/TR/REC-html40', u'CLASS'), (u'http://www.w3.org/2000/svg', u'class'), (u'http://www.w3.org/Graphics/SVG/svg-19990412.dtd', u'class'), (u'http://www.w3.org/1998/Math/MathML', u'class'), (u'urn:schemas-microsoft-com:vml', u'class')):
                    classNames = xmldomnode.getAttributeNS(attrURI, attrLocalName)
                    if (attrURI and attrURI or nodeURI) == u'http://www.w3.org/TR/REC-html40':
                        classNames = classNames.lower()
                        pass
                    for className in classNames.split():
                        classes[className.encode('UTF-8')] = 1
                        pass
                    pass
                elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/1999/xhtml', u'a'), (u'http://www.w3.org/1999/xhtml', u'link')) and (attrURI and attrURI or nodeURI, attrLocalName) in ((u'http://www.w3.org/1999/xhtml', u'rel'),):
                    relnames = xmldomnode.getAttributeNS(attrURI, attrLocalName)
                    for relname in relnames.split():
                        rels[relname.encode('UTF-8')] = 1
                        pass
                    pass
                elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/1999/xhtml', u'a'), (u'http://www.w3.org/1999/xhtml', u'link')) and (attrURI and attrURI or nodeURI, attrLocalName) in ((u'http://www.w3.org/1999/xhtml', u'rev'),):
                    revnames = xmldomnode.getAttributeNS(attrURI, attrLocalName)
                    for revname in revnames.split():
                        revs[revname.encode('UTF-8')] = 1
                        pass
                    pass
                elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'A'), (u'http://www.w3.org/TR/REC-html40', u'LINK')) and (attrURI and attrURI or nodeURI, attrLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'REL'),):
                    relnames = xmldomnode.getAttributeNS(attrURI, attrLocalName).lower()
                    for relname in relnames.split():
                        rels[relname.encode('UTF-8')] = 1
                        pass
                    pass
                elif (nodeURI, nodeLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'A'), (u'http://www.w3.org/TR/REC-html40', u'LINK')) and (attrURI and attrURI or nodeURI, attrLocalName) in ((u'http://www.w3.org/TR/REC-html40', u'REV'),):
                    revnames = xmldomnode.getAttributeNS(attrURI, attrLocalName).lower()
                    for revname in revnames.split():
                        revs[revname.encode('UTF-8')] = 1
                        pass
                    pass
                attrPrefix = makeAttrPrefix(attrURI, namespaces, o)
                addattrs.append(domnodesource(attrNode, xmlns = xmlns, namespaces = namespaces, format = format, recursive = recursive, lang = lang, space = space, classes = classes, metadata = metadata, stderr = stderr))
                pass
            pass
        if href is not None:
            href = normalize_uri(href)
            pass
        itext = None
        ixhtml = None
        if classes.has_key('avcontent') and metadata is not None:
            if ('avcontent', 1) in classes.iteritems():
                imetadata = { }
                metadata['avcontent'] = metadata.get('avcontent', []) + [ imetadata ]
                metadata = imetadata
                pass
            for className, level in classes.iteritems():
                if className.startswith('x-') and level == 1:
                    itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                    ixhtml = ixhtml or stringasxhtml(itext)
                    metadata[className] = metadata.get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                    pass
                pass
            for className in ('avcontent-title', 'avcontent-type', 'avcontent-keytitle', 'avcontent-date', 'avcontent-language', 'avcontent-subtitled', 'avcontent-summary', 'avcontent-description', 'avcontent-plot', 'avcontent-review', 'avcontent-grid', 'avcontent-gtin', 'avcontent-iswc', 'avcontent-isan', 'avcontent-isrc', 'avcontent-genre', 'avcontent-duration'):
                if (className, 1) in classes.iteritems():
                    itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                    ixhtml = ixhtml or stringasxhtml(itext)
                    metadata[className] = metadata.get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                    pass
                pass
            if classes.has_key('avcontent-tags') and classes['avcontent-tags'] <= classes['avcontent']:
                if ('avcontent-tags', 1) in classes.iteritems():
                    metadata['avcontent-tags'] = metadata.get('avcontent-tags', []) + [ { } ]
                    pass
                for relname in ('tag',):
                    if href is not None and (relname, 1) in rels.iteritems():
                        itext = urllib.unquote(posixpath.split(urlparse.urlsplit(href)[2])[1])
                        ixhtml = '<a href="%s" rel="nofollow %s">%s</a>' % (stringasxhtml(href, attribute = True), stringasxhtml(relname, attribute = True), stringasxhtml(itext))
                        metadata['avcontent-tags'][-1]['rel="' + stringasxhtml(relname, attribute = True) + '"'] = metadata['avcontent-tags'][-1].get('rel="' + stringasxhtml(relname, attribute = True) + '"', []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                pass
            if classes.has_key('avcontent-rating') and classes['avcontent-rating'] <= classes['avcontent']:
                if ('avcontent-rating', 1) in classes.iteritems():
                    metadata['avcontent-rating'] = metadata.get('avcontent-rating', []) + [ { } ]
                    pass
                for className in ('avcontent-rating-mpaa', 'avcontent-rating-esrb', 'avcontent-rating-riaa', 'avcontent-rating-producer'):
                    if (className, 1) in classes.iteritems():
                        itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                        ixhtml = ixhtml or stringasxhtml(itext)
                        metadata['avcontent-rating'][-1][className] = metadata['avcontent-rating'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                pass
            if classes.has_key('avcontent-wholesale') and classes['avcontent-wholesale'] <= classes['avcontent']:
                if ('avcontent-wholesale', 1) in classes.iteritems():
                    metadata['avcontent-wholesale'] = metadata.get('avcontent-wholesale', []) + [ { } ]
                    pass
                for className in ('avcontent-wholesale-country', 'avcontent-wholesale-currency', 'avcontent-wholesale-amount', 'avcontent-wholesale-token'):
                    if (className, 1) in classes.iteritems():
                        itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                        ixhtml = ixhtml or stringasxhtml(itext)
                        metadata['avcontent-wholesale'][-1][className] = metadata['avcontent-wholesale'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                pass
            if classes.has_key('avcontent-copyright') and classes['avcontent-copyright'] <= classes['avcontent']:
                if ('avcontent-copyright', 1) in classes.iteritems():
                    metadata['avcontent-copyright'] = metadata.get('avcontent-copyright', []) + [ { } ]
                    pass
                for className in ('avcontent-copyright-country', 'avcontent-copyright-date', 'avcontent-copyright-owner'):
                    if (className, 1) in classes.iteritems():
                        itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                        ixhtml = ixhtml or stringasxhtml(itext)
                        metadata['avcontent-copyright'][-1][className] = metadata['avcontent-copyright'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                pass
            if classes.has_key('avcontent-release') and classes['avcontent-release'] <= classes['avcontent']:
                if ('avcontent-release', 1) in classes.iteritems():
                    metadata['avcontent-release'] = metadata.get('avcontent-release', []) + [ { } ]
                    pass
                for className in ('avcontent-release-country', 'avcontent-release-date', 'avcontent-release-adult', 'avcontent-release-drm'):
                    if (className, 1) in classes.iteritems():
                        itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                        ixhtml = ixhtml or stringasxhtml(itext)
                        metadata['avcontent-release'][-1][className] = metadata['avcontent-release'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                if classes.has_key('avcontent-release-license') and classes['avcontent-release-license'] <= classes['avcontent']:
                    if ('avcontent-release-license', 1) in classes.iteritems():
                        metadata['avcontent-release'][-1]['avcontent-release-license'] = metadata['avcontent-release'][-1].get('avcontent-release-license', []) + [ { } ]
                        pass
                    for relname in ('license',):
                        if href is not None and (relname, 1) in rels.iteritems():
                            itext = href
                            ixhtml = '<a href="%s" rel="nofollow %s">%s</a>' % (stringasxhtml(href, attribute = True), stringasxhtml(relname, attribute = True), stringasxhtml(itext))
                            metadata['avcontent-release'][-1]['avcontent-release-license'][-1]['rel="' + stringasxhtml(relname, attribute = True) + '"'] = metadata['avcontent-release'][-1]['avcontent-release-license'][-1].get('rel="' + stringasxhtml(relname, attribute = True) + '"', []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                            pass
                        pass
                    pass
                pass
            if classes.has_key('avcontent-contributor') and classes['avcontent-contributor'] <= classes['avcontent']:
                if ('avcontent-contributor', 1) in classes.iteritems():
                    metadata['avcontent-contributor'] = metadata.get('avcontent-contributor', []) + [ { } ]
                    pass
                for className in ('avcontent-contributor-name', 'avcontent-contributor-role'):
                    if (className, 1) in classes.iteritems():
                        itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                        ixhtml = ixhtml or stringasxhtml(itext)
                        metadata['avcontent-contributor'][-1][className] = metadata['avcontent-contributor'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                pass
            if classes.has_key('avcontent-producer') and classes['avcontent-producer'] <= classes['avcontent']:
                if ('avcontent-producer', 1) in classes.iteritems():
                    metadata['avcontent-producer'] = metadata.get('avcontent-producer', []) + [ { } ]
                    pass
                for className in ('avcontent-producer-name', 'avcontent-producer-role'):
                    if (className, 1) in classes.iteritems():
                        itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                        ixhtml = ixhtml or stringasxhtml(itext)
                        metadata['avcontent-producer'][-1][className] = metadata['avcontent-producer'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                pass
            if classes.has_key('avcontent-file') and classes['avcontent-file'] <= classes['avcontent']:
                if ('avcontent-file', 1) in classes.iteritems():
                    metadata['avcontent-file'] = metadata.get('avcontent-file', []) + [ { } ]
                    pass
                for className in ('avcontent-file-uri', 'avcontent-file-type', 'avcontent-file-sha1', 'avcontent-file-md5', 'avcontent-file-size', 'avcontent-file-bitrate'):
                    if (className, 1) in classes.iteritems():
                        itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                        ixhtml = ixhtml or stringasxhtml(itext)
                        metadata['avcontent-file'][-1][className] = metadata['avcontent-file'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                        pass
                    pass
                if classes.has_key('avcontent-file-torrent') and classes['avcontent-file-torrent'] <= classes['avcontent-file']:
                    if ('avcontent-file-torrent', 1) in classes.iteritems():
                        metadata['avcontent-file'][-1]['avcontent-file-torrent'] = metadata['avcontent-file'][-1].get('avcontent-file-torrent', []) + [ { } ]
                        pass
                    for className in ('avcontent-file-torrent-uri', 'avcontent-file-torrent-infohash', 'avcontent-file-torrent-sha1', 'avcontent-file-torrent-md5', 'avcontent-file-torrent-size'):
                        if (className, 1) in classes.iteritems():
                            itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                            ixhtml = ixhtml or stringasxhtml(itext)
                            metadata['avcontent-file'][-1]['avcontent-file-torrent'][-1][className] = metadata['avcontent-file'][-1]['avcontent-file-torrent'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                            pass
                        pass
                    pass
                if classes.has_key('avcontent-file-visual') and classes['avcontent-file-visual'] <= classes['avcontent-file']:
                    if ('avcontent-file-visual', 1) in classes.iteritems():
                        metadata['avcontent-file'][-1]['avcontent-file-visual'] = metadata['avcontent-file'][-1].get('avcontent-file-visual', []) + [ { } ]
                        pass
                    for className in ('avcontent-file-visual-width', 'avcontent-file-visual-height', 'avcontent-file-visual-conversion'):
                        if (className, 1) in classes.iteritems():
                            itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                            ixhtml = ixhtml or stringasxhtml(itext)
                            metadata['avcontent-file'][-1]['avcontent-file-visual'][-1][className] = metadata['avcontent-file'][-1]['avcontent-file-visual'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                            pass
                        pass
                    pass
                if classes.has_key('avcontent-file-audio') and classes['avcontent-file-audio'] <= classes['avcontent-file']:
                    if ('avcontent-file-audio', 1) in classes.iteritems():
                        metadata['avcontent-file'][-1]['avcontent-file-audio'] = metadata['avcontent-file'][-1].get('avcontent-file-audio', []) + [ { } ]
                        pass
                    for className in ('avcontent-file-audio-channels',):
                        if (className, 1) in classes.iteritems():
                            itext = itext or domnodeinnertext(xmldomnode, allow_lookaside = True).decode('UTF-8').strip().encode('UTF-8')
                            ixhtml = ixhtml or stringasxhtml(itext)
                            metadata['avcontent-file'][-1]['avcontent-file-audio'][-1][className] = metadata['avcontent-file'][-1]['avcontent-file-audio'][-1].get(className, []) + [ { 'xhtml value': ixhtml, 'text value': itext, 'lang value': lang } ]
                            pass
                        pass
                    pass
                pass
            pass
        o += addattrs
        if xmldomnode.hasChildNodes() or (nodeURI, nodeLocalName) not in _xhtmlEmptyElements:
            o.append(stringasxhtml('>'))
            if xmldomnode.hasChildNodes():
                o.append('<span class="element-value">')
                for childNode in xmldomnode.childNodes:
                    o.append(domnodesource(childNode, xmlns = xmlns, namespaces = namespaces, format = format, recursive = recursive, lang = lang, space = space, classes = classes, metadata = metadata, stderr = stderr))
                    pass
                o.append('</span>')
                pass
            o.append(stringasxhtml('</'))
            o.append('<span class="element-name">%s</span>' % stringasxhtml((prefix + nodeLocalName).encode('UTF-8'), source = True))
            o.append(stringasxhtml('>'))
            pass
        else:
            o.append(stringasxhtml(' />'))
            pass
        o.append('</span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.ENTITY_REFERENCE_NODE:
        x = stringasxhtml(xmldomnode.toxml(encoding = 'UTF-8'))
        o.append('<span class="entity-reference">')
        o.append(stringasxhtml(x.rstrip(';')[:1]))
        o.append('<span class="entity-reference-value"><span class="entity-reference-name">')
        o.append(stringasxhtml(x.rstrip(';')[1:]))
        o.append('</span>')
        o.append(stringasxhtml(x[len(x)-len(x.rstrip(';')):]))
        o.append('</span></span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.CDATA_SECTION_NODE:
        o.append('<span class="cdata">&lt;![CDATA[')
        if xmldomnode.data:
            o.append('<span class="cdata-value">')
            o.append((
                '</span>' +
                ']]&gt;</span>' +
                '<span class="text">' +
                stringasxhtml(']]>', source = True) +
                '</span>' +
                '<span class="cdata">&lt;![CDATA[' +
                '<span class="cdata-value">'
                ).join(stringasxhtml(xmldomnode.data.encode('UTF-8')).split(stringasxhtml(']]>'))))
            o.append('</span>')
            pass
        o.append(']]&gt;</span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.TEXT_NODE:
        if xmldomnode.data:
            o.append('<span class="text">')
            o.append(stringasxhtml(xmldomnode.data.encode('UTF-8'), source = True))
            o.append('</span>')
            pass
        pass
    elif xmldomnode.nodeType == xmldomnode.COMMENT_NODE:
        o.append('<span class="comment">&lt;!--')
        if xmldomnode.data:
            o.append('<span class="comment-value">')
            o.append(stringasxhtml(xmldomnode.data.encode('UTF-8')))
            o.append('</span>')
            pass
        o.append('--&gt;</span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.DOCUMENT_TYPE_NODE:
        o.append('<span class="doctype">')
        o.append(stringasxhtml('<!DOCTYPE '))
        o.append('<span class="doctype-name">')
        o.append(stringasxhtml(xmldomnode.name.encode('UTF-8')))
        o.append('</span>')
        if xmldomnode.publicId:
            o.append(' PUBLIC <span class="doctype-public-id">&quot;%s&quot;</span> <span class="doctype-system-id">&quot;%s&quot;</span>'
                     % (stringasxhtml(xmldomnode.publicId.encode('UTF-8')),
                        stringasxhtml(xmldomnode.systemId.encode('UTF-8'))))
            pass
        elif xmldomnode.systemId:
            o.append(' SYSTEM <span class="doctype-system-id">&quot;%s&quot;</span>'
                     % stringasxhtml(xmldomnode.systemId.encode('UTF-8')))
            pass
        if xmldomnode.internalSubset is not None:
            o.append(' <span class="doctype-value">[')
            o.append(stringasxhtml(xmldomnode.internalSubset.encode('UTF-8')))
            o.append(']</span>')
        o.append(stringasxhtml('>'))
        o.append('</span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.ENTITY_NODE:
        o.append('<span class="entity">')
        o.append(stringasxhtml('<!ENTITY '))
        o.append('<span class="entity-name">')
        o.append(stringasxhtml(xmldomnode.nodeName.encode('UTF-8')))
        o.append('</span>')
        if xmldomnode.publicId:
            o.append(' PUBLIC <span class="entity-public-id">&quot;%s&quot;</span> <span class="entity-system-id">&quot;%s&quot;</span>'
                     % (stringasxhtml(xmldomnode.publicId.encode('UTF-8')),
                        stringasxhtml(xmldomnode.systemId.encode('UTF-8'))))
            pass
        elif xmldomnode.systemId:
            o.append(' SYSTEM <span class="entity-system-id">&quot;%s&quot;</span>'
                     % stringasxhtml(xmldomnode.systemId.encode('UTF-8')))
            pass
        if xmldomnode.notationName is not None:
            o.append(' NDATA <span class="entity-notation-name">')
            o.append(stringasxhtml(xmldomnode.notationName.encode('UTF-8')))
            o.append('</span>')
            pass
        if xmldomnode.hasChildNodes():
            o.append(' <span class="entity-value">&quot;')
            for childNode in xmldomnode.childNodes:
                o.append(childNode.toxml(encoding = 'UTF-8'))
                pass
            o.append('&quot;</span>')
            pass
        o.append(stringasxhtml('>'))
        o.append('</span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.NOTATION_NODE:
        o.append('<span class="notation">')
        o.append(stringasxhtml('<!NOTATION '))
        o.append('<span class="notation-name">')
        o.append(stringasxhtml(xmldomnode.nodeName.encode('UTF-8')))
        o.append('</span>')
        if xmldomnode.publicId:
            o.append(' PUBLIC <span class="notation-public-id">&quot;%s&quot;</span> <span class="notation-system-id">&quot;%s&quot;</span>'
                     % (stringasxhtml(xmldomnode.publicId.encode('UTF-8')),
                        stringasxhtml(xmldomnode.systemId.encode('UTF-8'))))
            pass
        elif xmldomnode.systemId:
            o.append(' SYSTEM <span class="notation-system-id">&quot;%s&quot;</span>'
                     % stringasxhtml(xmldomnode.systemId.encode('UTF-8')))
            pass
        o.append(stringasxhtml('>'))
        o.append('</span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.PROCESSING_INSTRUCTION_NODE:
        o.append('<span class="pi">&lt;?<span class="pi-name">')
        o.append(stringasxhtml(xmldomnode.target.encode('UTF-8')))
        o.append('</span>')
        if xmldomnode.data:
            o.append(' <span class="pi-value">')
            o.append(stringasxhtml(xmldomnode.data.encode('UTF-8')))
            o.append('</span>')
            pass
        o.append('?&gt;</span>')
        pass
    elif xmldomnode.nodeType == xmldomnode.ATTRIBUTE_NODE:
        attrURI, attrLocalName = (xmldomnode.namespaceURI, xmldomnode.localName)
        attrPrefix = makeAttrPrefix(attrURI, namespaces, o)
        attrName = attrPrefix + attrLocalName
        o.append(' <span class="attribute' + (xmldomnode.specified and ' attribute-specified' or '') + (xmldomnode.isId and ' attribute-id' or '') + '"><span class="attribute-name">')
        o.append(stringasxhtml(attrName.encode('UTF-8')))
        o.append('</span>=<span class="attribute-value">&quot;')
        for childNode in xmldomnode.childNodes:
            if childNode.nodeType in (xmldomnode.TEXT_NODE, xmldomnode.CDATA_SECTION_NODE):
                if childNode.data:
                    o.append('<span class="text">')
                    o.append(stringasxhtml(childNode.data.encode('UTF-8'), source = True, attribute = True))
                    o.append('</span>')
                    pass
                pass
            else:
                o.append(domnodesource(childNode, xmlns = xmlns, namespaces = namespaces, format = format, recursive = recursive, lang = lang, space = space, classes = classes, metadata = metadata, stderr = stderr))
                pass
            pass
        o.append('&quot;</span></span>')
        pass
    elif xmldomnode.nodeType in (xmldomnode.DOCUMENT_NODE, xmldomnode.DOCUMENT_FRAGMENT_NODE):
        for childNode in xmldomnode.childNodes:
            if o and xmldomnode.nodeType == xmldomnode.DOCUMENT_NODE:
                o.append('\n')
                pass
            o.append(domnodesource(childNode, xmlns = xmlns, namespaces = namespaces, format = format, recursive = recursive, lang = lang, space = space, classes = classes, metadata = metadata, stderr = stderr))
            pass
        pass
    else:
        o.append(stringasxhtml(xmldomnode.toxml(encoding = 'UTF-8')))
        pass
    return ''.join(o)

def normalize_country(lang):
    return lang.decode('UTF-8').upper().encode('UTF-8')

def normalize_uri(uri):
    '''
    normalize a URI; also converts IRIs to URIs
    '''
    uri = ''.join([ (ord(x) in xrange(33, 127)) and x or urllib.quote(x, safe='') for x in u''.join(uri.decode('UTF-8').split()).encode('UTF-8') ])
    try:
        scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)
        uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
        if scheme in urlparse.uses_netloc:
            if netloc is not None:
                user, hostport = urllib.splituser(netloc)
                if hostport is not None:
                    host, port = urllib.splitport(hostport)
                    if host is not None:
                        if host[:1] != '[':
                            # hostname segments get downcased and IDNA-encoded
                            ohost = []
                            for part in host.split('.'):
                                part = urllib.unquote(part)
                                try:
                                    part = part.decode('UTF-8').lower().encode('UTF-8')
                                    try:
                                        part = part.decode('UTF-8').encode('idna')
                                        pass
                                    except KeyboardInterrupt, k:
                                        raise
                                    except:
                                        pass
                                    pass
                                except KeyboardInterrupt, k:
                                    raise
                                except:
                                    pass
                                ohost.append(urllib.quote(part, safe=''))
                                pass
                            netloc = '.'.join(ohost)
                            if port is not None:
                                netloc += ':' + port
                                pass
                            if user is not None:
                                netloc = user + '@' + netloc
                                pass
                            uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
                            pass
                        pass
                    pass
                pass
            pass
        pass
    except KeyboardInterrupt, k:
        raise
    except:
        pass
    return uri

def normalize_currency(lang):
    return lang.decode('UTF-8').upper().encode('UTF-8')

def normalize_lang(lang):
    parts = lang.decode('UTF-8').lower().split(u'-')
    if len(parts) > 1 and len(parts[1]) in (2, 3):
        parts[1] = parts[1].upper()
        pass
    return u'-'.join(parts).encode('UTF-8')

_mime_token_re = re.compile(r'\A(?:\!|\#|\$|\%|\&|\'|\*|\+|\-|\.|0|1|2|3|4|5|6|7|8|9|A|B|C|D|E|F|G|H|I|J|K|L|M|N|O|P|Q|R|S|T|U|V|W|X|Y|Z|\^|\_|\`|a|b|c|d|e|f|g|h|i|j|k|l|m|n|o|p|q|r|s|t|u|v|w|x|y|z|\{|\||\}|\~)+\Z')

def normalize_content_type(content_type):

    # FIXME: cgi.parse_header does not handle semicolons in quoted
    # parameter values!

    # FIXME: this should handle RFC 2231 i18n features but does not, yet...
    
    base_type, params = cgi.parse_header(content_type)
    params_list = []
    for key, value in params.iteritems():
        key = key.lower()
        if key == 'charset':
            value = value.lower()
            pass
        if not _mime_token_re.match(value):
            value = '"' + '\\"'.join('\\\\'.join(value.split('\\')).split('"')) + '"'
            pass
        params_list.append(key + '=' + value)
        pass
    params_list.sort()
    return ';'.join([ base_type.lower() ] + params_list)

def fix_avcontent_metadata(metadata):
    metadata['text value'] = '%s %s containing %d sub-item(s).' % (metadata.get('avcontent-type', [ { 'xhtml value': 'audiovisual content' } ])[0]['xhtml value'], `metadata.get('avcontent-keytitle', metadata.get('avcontent-title', [ {'xhtml value': '(untitled)' } ]))[0]['xhtml value']`, len(metadata.get('avcontent', [])))
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_grid_metadata(metadata):
    metadata['text value'] = grid.GRid(metadata['text value']).__str__(short = True)
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_gtin_metadata(metadata):
    try:
        metadata['text value'] = gtin.GTIN(metadata['text value']).__str__(short = True)
        metadata['xhtml value'] = stringasxhtml(metadata['text value'])
        pass
    except ValueError, v:
        metadata['text value'] = gtin.GTIN(metadata['text value'], public = False).__str__(short = True)
        metadata['xhtml value'] = stringasxhtml(metadata['text value'])
        raise
    pass

def fix_isan_metadata(metadata):
    try:
        metadata['text value'] = isan.ISAN(metadata['text value']).__str__(short = True)
        metadata['xhtml value'] = stringasxhtml(metadata['text value'])
        pass
    except ValueError, v:
        metadata['text value'] = isan.ISAN(metadata['text value'], public = False).__str__(short = True)
        metadata['xhtml value'] = stringasxhtml(metadata['text value'])
        raise
    pass

def fix_isrc_metadata(metadata):
    metadata['text value'] = isrc.ISRC(metadata['text value']).__str__(short = True)
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_iswc_metadata(metadata):
    metadata['text value'] = iswc.ISWC(metadata['text value']).__str__(short = True)
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_sha1_metadata(metadata):
    metadata['text value'] = metadata['text value'].decode('UTF-8').lower().encode('UTF-8')
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    if len(metadata['text value'].decode('hex')) != 20:
        raise ValueError('Invalid SHA1 hex digest')
    pass

def fix_md5_metadata(metadata):
    metadata['text value'] = metadata['text value'].decode('UTF-8').lower().encode('UTF-8')
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    if len(metadata['text value'].decode('hex')) != 16:
        raise ValueError('Invalid MD5 hex digest')
    pass

def fix_lang_metadata(metadata):
    metadata['text value'] = normalize_lang(metadata['text value'])
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_country_metadata(metadata):
    metadata['text value'] = normalize_country(metadata['text value'])
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_currency_metadata(metadata):
    metadata['text value'] = normalize_currency(metadata['text value'])
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_content_type_metadata(metadata):
    metadata['text value'] = normalize_content_type(metadata['text value'])
    metadata['xhtml value'] = stringasxhtml(metadata['text value'])
    pass

def fix_visual_metadata(metadata):
    height = 0.0
    width = 0.0
    if metadata.has_key('avcontent-file-visual-width'):
        width = float(metadata['avcontent-file-visual-width'][0]['text value'])
        pass
    if metadata.has_key('avcontent-file-visual-height'):
        height = float(metadata['avcontent-file-visual-height'][0]['text value'])
        pass
    if not width:
        width = 1.0
        pass
    if not height:
        height = 1.0
        pass
    scale = 0.0125
    metadata['xhtml value'] = '<div style="width: %sem; height: 1em; line-height: 10px; font-size: 10px; font-family: sans; color: grey; border: 2px solid grey; background: silver; text-align: center; vertical-align: middle; padding: %sem 0; margin: 1em; ">%spx</div>' % (width * scale, (height * scale - 1.0) / 2, width * height)
    pass

def fix_copyright_metadata(metadata):
    if metadata.has_key('avcontent-copyright-date') and metadata.has_key('avcontent-copyright-owner'):
        metadata['text value'] = u'Copyright \u00a9 %s, %s'.encode('UTF-8') % (', '.join([ '-'.join(d['text value'].split('/')) for d in metadata['avcontent-copyright-date'] ]), ', '.join([ o['text value'] for o in metadata['avcontent-copyright-owner']]))
        metadata['xhtml value'] = stringasxhtml(metadata['text value'])
        pass
    pass

normal_forms = [
    ('avcontent/avcontent-file/avcontent-file-torrent/avcontent-file-torrent-md5', fix_md5_metadata),
    ('avcontent/avcontent-file/avcontent-file-torrent/avcontent-file-torrent-sha1', fix_sha1_metadata),
    ('avcontent/avcontent-file/avcontent-file-torrent/avcontent-file-torrent-infohash', fix_sha1_metadata),
    ('avcontent/avcontent-file/avcontent-file-md5', fix_md5_metadata),
    ('avcontent/avcontent-file/avcontent-file-sha1', fix_sha1_metadata),
    ('avcontent/avcontent-file/avcontent-file-visual', fix_visual_metadata),
    ('avcontent/avcontent-file/avcontent-file-type', fix_content_type_metadata),
    ('avcontent/avcontent-copyright/avcontent-copyright-country', fix_country_metadata),
    ('avcontent/avcontent-release/avcontent-release-country', fix_country_metadata),
    ('avcontent/avcontent-wholesale/avcontent-wholesale-country', fix_country_metadata),
    ('avcontent/avcontent-wholesale/avcontent-wholesale-currency', fix_currency_metadata),
    ('avcontent/avcontent-language', fix_lang_metadata),
    ('avcontent/avcontent-subtitled', fix_lang_metadata),
    ('avcontent/avcontent-grid', fix_grid_metadata),
    ('avcontent/avcontent-gtin', fix_gtin_metadata),
    ('avcontent/avcontent-isan', fix_isan_metadata),
    ('avcontent/avcontent-isrc', fix_isrc_metadata),
    ('avcontent/avcontent-iswc', fix_iswc_metadata),
    ('avcontent/avcontent-copyright', fix_copyright_metadata),
    ('avcontent', fix_avcontent_metadata),
    ]

def match_metadata(metadata, path):
    parts = path.split('/', 1)
    if metadata.has_key(parts[0]):
        for value in metadata[parts[0]]:
            if len(parts) == 1:
                yield value
                pass
            else:
                for subpath in match_metadata(value, parts[1]):
                    yield subpath
                    pass
                pass
            pass
        pass
    pass

def normalize_metadata(metadata, warning_handler = None, stderr = sys.stderr):
    metadata = dict(metadata.items())
    if metadata.has_key('avcontent'):
        metadata['avcontent'] = [ normalize_metadata(imetadata, warning_handler, stderr) for imetadata in metadata['avcontent'] ]
        pass
    for path, normalize in normal_forms:
        for container in match_metadata(metadata, path):
            try:
                normalize(container)
                pass
            except KeyboardInterrupt, k:
                raise
            except Exception, e:
                container['exception value'] = e
                if warning_handler is not None:
                    warning_handler(e)
                    pass
                else:
                    stderr.write(': warning: '.join(str(e).strip().split(': ', 1)) + '\n')
                    stderr.flush()
                    pass
                pass
            pass
        pass
    return metadata

def xoxoize(metadata):
    o = []
    if metadata.has_key('xhtml value'):
        o.append('<span class="comment-value-hyphen-hyphen"><abbr title="--" class="comment-value-hyphen-hyphen-value"><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span></abbr></span>'.join('<br />'.join(metadata['xhtml value'].split('\n')).split('--')))
        pass
    elif metadata.has_key('text value'):
        o.append('<span class="comment-value-hyphen-hyphen"><abbr title="--" class="comment-value-hyphen-hyphen-value"><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span></abbr></span>'.join('<br />'.join(stringasxhtml(metadata['text value']).split('\n')).split('--')))
        pass
    keylist = [ key for key in metadata.iterkeys() if key not in ('lang value', 'xhtml value', 'text value', 'exception value') ]
    if keylist:
        keylist.sort()
        o.append('<dl dir="ltr">')
        for key in keylist:
            for value in metadata[key]:
                etxt = ''
                eclass = ''
                if value.has_key('exception value'):
                    etxt = ' - <span class="exception"><span class="exception-type">' + '<span class="comment-value-hyphen-hyphen"><abbr title="--" class="comment-value-hyphen-hyphen-value"><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span></abbr>'.join(stringasxhtml(str(value['exception value'].__class__.__name__)).split('--')) + '</span>: <span class="exception-text">' + '<abbr title="--" class="comment-value-hyphen-hyphen-value" class="comment-value-hyphen-hyphen"><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span></abbr></span>'.join(stringasxhtml(str(value['exception value'])).split('--')) + '</span></span>'
                    eclass = ' exception-value'
                    pass
                o.append('<dt>%s%s</dt>' % ('<span class="comment-value-hyphen-hyphen"><abbr title="--" class="comment-value-hyphen-hyphen-value"><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span><span class="character-reference">&amp;#<span class="character-reference-value"><span class="character-reference-number">45</span>;</span></span></abbr></span>'.join(stringasxhtml(key).split('--')), etxt))
                attrs = ''
                if value.has_key('lang value'):
                    attrs = ' title="xml:lang=&quot;%s&quot;" xml:lang="%s"' % (stringasxhtml(stringasxhtml(normalize_lang(value['lang value']), attribute = True), attribute = True), stringasxhtml(normalize_lang(value['lang value']), attribute = True))
                    pass
                if value.has_key('xhtml value') or value.has_key('text value'):
                    attrs += ' dir="ltr"'
                    pass
                if [ key2 for key2 in value.iterkeys() if key2 != 'exception value' ]:
                    o.append('<dd class="%s"%s>' % (stringasxhtml(key + eclass, attribute = True), attrs))
                    o.append(xoxoize(value))
                    o.append('</dd>')
                    pass
                pass
            pass
        o.append('</dl>')
        pass
    return ''.join(o)

def domsource(xmldom, format = 'xhtml', style = 'pre', warnings = None, metadata = None, stderr = sys.stderr):
    warnings = [] + (warnings or [])
    assert format in ('xhtml', 'text')
    assert style in ('pre', 'div')
    if format == 'text':
        return domnodesource(xmldom, format = 'text', metadata = metadata, stderr = stderr)
    if metadata is None:
        metadata = {}
    s = domnodesource(xmldom, metadata = metadata, stderr = stderr)
    if _namespaceCatalog.has_key(xmldom.documentElement.namespaceURI):
        sxml = None
        dtd = None
        qname = None
        doctypes = _namespaceCatalog[xmldom.documentElement.namespaceURI]
        if xmldom.documentElement.hasAttributeNS(None, 'version'):
            docversion = xmldom.documentElement.getAttributeNS(None, 'version')
            doctypes = ([ (pubid, sysid) for (pubid, sysid) in doctypes if pubid == docversion ]
                        +
                        [ (pubid, sysid) for (pubid, sysid) in doctypes if pubid != docversion ])
            pass
        for pubid, sysid in doctypes:
            try:
                if sxml is None:
                    sxml = domnodeinnertext(xml.dom.minidom.parseString('<div xmlns="http://www.w3.org/1999/xhtml">%s</div>' % s))
                    pass
                if qname is None:
                    prefix = ''
                    xmldom = xml.dom.minidom.parseString(sxml)
                    if xmldom.documentElement.prefix:
                        prefix = xmldom.documentElement.prefix.encode('UTF-8') + ':'
                        pass
                    qname = prefix + xmldom.documentElement.localName.encode('UTF-8')
                    pass
                if pubid is not None:
                    dtd = (
                        '<!DOCTYPE %s PUBLIC "%s" "%s">\n' % (
                        qname,
                        stringasxhtml(pubid.encode('UTF-8'), attribute = True),
                        stringasxhtml(sysid.encode('UTF-8'), attribute = True)))
                    pass
                else:
                    dtd = (
                        '<!DOCTYPE %s SYSTEM "%s">\n' % (
                        qname,
                        stringasxhtml(sysid.encode('UTF-8'), attribute = True)))
                    pass
                vxmldom = parseString(dtd + sxml, user_warning_handler = lambda exc: None, validate = True, stderr = stderr)
                vs = domnodesource(vxmldom, format = 'text', stderr = stderr)
                if vs == sxml:
                    sxmldom = xml.dom.minidom.parseString(dtd + sxml)
                    s = domnodesource(sxmldom, stderr = stderr)
                    break
                pass
            except KeyboardInterrupt, k:
                raise
            except Exception, e:
                pass
            pass
        pass
    def inject_warning(exc):
        warnings.append(exc)
        stderr.write(': warning: '.join(str(exc).strip().split(': ', 1)) + '\n')
        stderr.flush()
        pass
    metadata = normalize_metadata(metadata, inject_warning, stderr)
    onload = None
    if warnings:
        onload = '(function(body){var messagePanel = (document.createElementNS ? document.createElementNS("http://www.w3.org/1999/xhtml", "pre") : null) || document.createElement("pre"); if (typeof (messagePanel.className) != "undefined") messagePanel.className = "message-panel"; else messagePanel.setAttribute("class", "message-panel"); if (typeof (messagePanel.onclick) != "undefined") messagePanel.onclick = (function () {messagePanel.parentNode.removeChild(messagePanel); return false;}); else messagePanel.setAttribute("onclick", "this.parentNode.removeChild(this); return false;"); messagePanel.appendChild(document.createTextNode(decodeURIComponent("%s") + "\\n(Click this message box to remove.)")); body.insertBefore(messagePanel, body.firstChild);})(((typeof(document.body) != "undefined") && (document.body != null)) ? document.body : document.getElementsByTagNameNS("http://www.w3.org/1999/xhtml", "body")[0]);' % urllib.quote('\n'.join([ (unicode(warning.__class__.__name__) + u': ' + unicode(warning).strip()).encode('UTF-8') for warning in warnings ]))
        pass
    o = []
    o.append(
'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" >
<head>
<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=%s" />
<meta http-equiv="Content-Language" content="en" />
<title>XML Source</title>
<style type="text/css">
/*<![CDATA[*/
body, th, td { color: black; background: white; font-family: sans; line-height: 10pt; font-size: 8pt; }
pre, samp { font-family: monospace; }
.element-name { font-weight: bold; color: purple; }
.attribute-value { color: blue; }
.attribute-name { font-weight: bold; }
.attribute-specified { border: 1px dotted grey; }
.attribute-id { text-decoration: underline; }
.entity-reference-value, .character-reference-value { color: #ff6000; }
.comment { color: green; font-style: italic; }
.cdata { color: #ff0080; font-weight: bold; }
.cdata-value { color: #800040; font-weight: normal; }
.doctype { font-style: italic; }
.doctype, .notation, .entity { color: #0080ff; }
.doctype-name, .notation-name, .entity-name, .entity-notation-name, .doctype-system-id, .notation-system-id, .entity-system-id, .doctype-public-id, .notation-public-id, .entity-public-id { font-weight: bold; font-style: normal; }
.pi { color: #ff80ff; font-style: italic; }
body { margin-top: 0px; padding-top: 0px; }
.message-panel { border: 1px solid #cc8888; text: black; background: #ffcccc; text-align: center; width: 80%%; border-top: none; margin-top: 0px; padding-top: 0px; position: relative; opacity: 0.70710678118654757; left: 10%%; font-size: smaller; font-family: sans; }
.xoxo dd dl { border-left: 1px dotted #88cc88; text: black; font-family: sans; padding: 0 0 1pt 1em; }
.xoxo dl dt { font-weight: bold; color: #006600; }
.xoxo dd { color: #664400; }
.exception { color: red; }
.exception-text { font-weight: normal; }
.exception-value { background: #ffcccc; border: 2px solid red; }
.comment-value-hyphen-hyphen-value { display: none; }
.comment-value-hyphen-hyphen:before { content: "--"; }
/*]]>*/
</style>
</head>
<body%s>
<%s%s class="samp">''' % (stringasxhtml('UTF-8', attribute = True), (onload is not None) and (' onload="%s"' % stringasxhtml(onload, attribute = True)) or '', style, ((style == 'pre') and ' xml:space="preserve"' or '')))
    if metadata:
        o.append('<div class="comment">&lt;!--<div class="comment-value xoxo">%s</div>--&gt;</div>' % xoxoize(metadata))
        pass
    if style == 'div':
        o.append('<samp>')
        s = '<br />\n'.join('&#10;'.join(s.split('\n')).split('&#10;'))
        pass
    o.append(s)
    if style == 'div':
        o.append('</samp>')
        pass
    o.append(
'''</%s>
</body>
</html>
''' % style
        )
    return ''.join(o)

_data_uri_re = re.compile(
    r'\Adata:[^,;]*(?:;[^,;=]+=[^,;]+)*(?P<base64>;base64)?,(?P<data>.*)\Z',
    re.IGNORECASE
    )

_safe_w3c_uri_re = re.compile(
    r'\Ahttp://(?P<host>www\.w3\.org)(?P<path>(?:/[-A-Za-z0-9_][-.A-Za-z0-9_]*)+[.](?:mod|dtd|ent))\Z',
    re.IGNORECASE
    )

def parseString(xmlstr, allow_network_access = False, parsers = None, user_warning_handler = None, validate = False, stderr = sys.stderr):
    '''
    Parses an XML string (xmlstr) and return the corresponding
    xml.dom.minidom tree.

    External entities are supported, but only data: URIs matching
    _data_uri_re and w3c external entities pre-cached on the local
    filesystem are allowed. the w3c external entities must have system
    identifiers that match _safe_w3c_uri_re and their filenames are
    based on match group "host" (downcased) + match group "path".

    If the optional flag allow_network_access = True is provided,
    external entities with system identifiers matching
    _safe_w3c_uri_re are fetched from the network if not found in the
    local cache. note that this does *not* populate the cache.

    If the optional list parsers is given, it contains a list of sax2
    parser modules in a format suitable for importing.

    If the optional user_warning_handler is given, it must be callable
    with an exception object parameter; it will be invoked once for
    each parsing warning.

    If the optional parameter validate = True is provided, this is a
    validating parse.
    '''
    if parsers is None:
        parsers = [
            'drv_libxml2',
            'xml.sax.drivers2.drv_pyexpat',
            'xml.sax.drivers2.drv_xmlproc']
        pass
    parser = None
    create_input_source_unsafe = None
    try:
        import xml.parsers.xmlproc.xmlapp
        create_input_source_unsafe = xml.parsers.xmlproc.xmlapp.InputSourceFactory.create_input_source
        pass
    except KeyboardInterrupt, k:
        raise
    except:
        pass
    skipped_entity_unsafe = xml.sax.handler.ContentHandler.skippedEntity
    def skipped_entity_wrapper(self, name):
        raise xml.sax.SAXParseException('Entity %r not defined' % (name.encode('UTF-8')), None, parser)
    xml.sax.handler.ContentHandler.skippedEntity = skipped_entity_wrapper
    processing_instruction_unsafe = xml.sax.handler.ContentHandler.processingInstruction
    def processing_instruction_wrapper(self, target, data):
        raise xml.sax.SAXParseException('<?%s %s>' % (target.encode('UTF-8'), (data or u'').encode('UTF-8')), None, parser)
    xml.sax.handler.ContentHandler.processingInstruction = processing_instruction_wrapper
    warning_handler_unsafe = xml.sax.handler.ErrorHandler.warning
    prepare_input_source_unsafe = xml.sax.saxutils.prepare_input_source
    warnings = []

    def warning_handler_wrapper(ignored, exception):
        if user_warning_handler is not None:
            user_warning_handler(exception)
            pass
        elif [ str(exception).strip() ] != warnings[-1:]:
            warnings.append(str(exception).strip())
            stderr.write(': warning: '.join(str(exception).strip().split(': ', 1)) + '\n')
            stderr.flush()
            pass
        return

    def create_input_source_wrapper(ignored, sysid):
        sysid = sysid.encode('UTF-8')
        match = _data_uri_re.match(sysid)
        if match:
            data = urllib.unquote_plus(match.group('data'))
            if match.group('base64'):
                data = ''.join(data.strip().split()).decode('base64')
                pass
            return StringIO.StringIO(data)
        match = _safe_w3c_uri_re.match(sysid)
        if match:
            filename = os.path.join(cache_root, match.group('host').lower() + match.group('path'))
            if os.path.isfile(filename):
                return file(filename, 'rb')
            if allow_network_access:
                return urllib2.urlopen(sysid)
            raise IOError('%s: network access not allowed' % sysid)
        raise IOError('%s: permission denied, does not match pattern %r or pattern %r' % (sysid, _safe_w3c_uri_re.pattern, _data_uri_re.pattern))

    def libxml2_entity_loader_wrapper(sysid, pubid, ctx):
        try:
            return create_input_source_wrapper(None, sysid.decode('UTF-8'))
        except KeyboardInterrupt, k:
            raise
        except Exception, entity_loader_exception:
            warning_handler_wrapper(None, entity_loader_exception)
            return StringIO.StringIO('')
        pass

    class PrepareInputSourceWrapper:
        def __call__(self, source, base = ''):
            import xml.sax.xmlreader
            if type(source) in (type(''), type(u'')):
                source = xml.sax.xmlreader.InputSource(source)
                pass
            elif hasattr(source, 'read'):
                f = source
                source = xml.sax.xmlreader.InputSource()
                source.setByteStream(f)
                if hasattr(f, 'name'):
                    source.setSystemId(f.name)
                    pass
                pass
            if source.getByteStream() is None:
                sysid = source.getSystemId()
                try:
                    f = create_input_source_wrapper(None, sysid)
                except KeyboardInterrupt, k:
                    raise
                except Exception, entity_loader_exception:
                    warning_handler_wrapper(None, entity_loader_exception)
                    raise
                source.setByteStream(f)
                pass
            return source
        pass
    prepare_input_source_wrapper = PrepareInputSourceWrapper()
    xml.sax.saxutils.prepare_input_source = prepare_input_source_wrapper
    try:
        import xml.parsers.xmlproc.xmlapp
        xml.parsers.xmlproc.xmlapp.InputSourceFactory.create_input_source = create_input_source_wrapper
        pass
    except KeyboardInterrupt, k:
        raise
    except:
        pass
    xml.sax.handler.ErrorHandler.warning = warning_handler_wrapper
    try:
        try:
            import libxml2
            libxml2.setEntityLoader(libxml2_entity_loader_wrapper)
            pass
        except KeyboardInterrupt, k:
            raise
        except:
            pass
        if validate:
            parser = xml.sax.sax2exts.ValidatingReaderFactory(parsers).make_parser(parsers)
            pass
        else:
            parser = xml.sax.sax2exts.XMLParserFactory.make_parser(parsers)
            pass
        if hasattr(parser, 'external_entity_ref'):
            external_entity_ref_unsafe = parser.external_entity_ref
            def external_entity_ref_wrapper(context, base, sysid, pubid):
                if base is not None and sysid is not None:
                    sysid = urlparse.urljoin(base, sysid)
                    pass
                return external_entity_ref_unsafe(context, base, sysid, pubid)
            parser.external_entity_ref = external_entity_ref_wrapper
            pass
        xmldom = xml.dom.minidom.parseString(xmlstr, parser = parser)
        pass
    finally:
        try:
            import xml.parsers.xmlproc.xmlapp
            xml.parsers.xmlproc.xmlapp.InputSourceFactory.create_input_source = create_input_source_unsafe
            xml.sax.saxutils.prepare_input_source = prepare_input_source_unsafe
            pass
        except KeyboardInterrupt, k:
            raise
        except:
            pass
        xml.sax.handler.ErrorHandler.warning = warning_handler_unsafe
        xml.sax.handler.ContentHandler.skippedEntity = skipped_entity_unsafe
        xml.sax.handler.ContentHandler.processingInstruction = processing_instruction_unsafe
        pass
    return xmldom

def main(args = sys.argv, environ = os.environ, stdin = sys.stdin, stdout = sys.stdout, stderr = sys.stderr, metadata = None):
    format = 'xhtml'
    style = 'pre'
    allow_network_access = False
    parsers = None
    while args[1:] and args[1][:1] == '-' and args[1] != '-':
        arg = args[1]
        args = args[:1] + args[2:]
        if arg == '--':
            break
        elif arg == '--help':
            print >> stdout, '''
Usage: %s [OPTION]... [ -- ]
Reformat XHTML for display and simple processing.
--help       print this message and exit
--text       output plain text
--xhtml      output XHTML "view source" text (default)
--div        output reflowable XHTML, whitespace not visually preserved
--pre        output preformatted XHTML, whitespace visually preserved (default)
--allow-network-access
             allow fetching DTDs and external entities from whitelisted HTTP URIs;
             NOTE: this may be a security hole when processing untrusted content!
--disallow-network-access
             disallow HTTP access, rely on local cache only (default)
--parser=module
             use specified SAX2 parser module
--default-parser
             use default XML parser
--fetch-dtds populate the DTD cache and exit
'''.strip() % (args[0])
            sys.exit(0)
            pass
        elif arg == '--default-parser':
            parsers = None
            pass
        elif arg == '--fetch-dtds':
            errors = 0
            for sysid in _sysids:
                match = _safe_w3c_uri_re.match(sysid)
                if match:
                    filename = os.path.join(cache_root, match.group('host').lower() + match.group('path'))
                    dirname = os.path.split(filename)[0]
                    if not os.path.isdir(dirname):
                        os.makedirs(dirname, mode = 0755)
                    if not os.path.isfile(filename):
                        try:
                            dtd = urllib2.urlopen(sysid).read()
                        except:
                            errors += 1
                            import traceback
                            print >> stderr, sysid + ': ' + traceback.format_exc()
                            continue
                        outfile = file(filename, 'wb')
                        try:
                            outfile.write(dtd)
                            outfile.close()
                        except:
                            try:
                                outfile.close()
                            except:
                                pass
                            try:
                                os.remove(filename)
                            except:
                                pass
                            errors += 1
                            import traceback
                            print >> stderr, filename + ': ' + traceback.format_exc()
                            pass
                        pass
                    pass
                pass
            if errors:
                raise Exception("Some system IDs could not be fetched.")
            return
        elif arg == '--parser':
            if len(args) < 2:
                raise IOError('%r: option %r requires an argument' % (args[0], arg))
            parsers = [ args[1] ]
            args = args[:1] + args[2:]
            pass
        elif arg[:len('--parser=')] == '--parser=':
            parsers = [ arg[len('--parser='):] ]
            pass
        elif arg == '--text':
            format = 'text'
            pass
        elif arg == '--xhtml':
            format = 'xhtml'
            pass
        elif arg == '--div':
            style = 'div'
            pass
        elif arg == '--pre':
            style = 'pre'
            pass
        elif arg == '--allow-network-access':
            allow_network_access = True
            pass
        elif arg == '--disallow-network-access':
            allow_network_access = False
            pass
        else:
            raise IOError('%r: argument %r not allowed' % (args[0], arg))
        pass
    assert args[1:] == []
    xmlstr = stdin.read()
    warnings = []
    def inject_warning(exc):
        warnings.append(exc)
        stderr.write(': warning: '.join(str(exc).strip().split(': ', 1)) + '\n')
        stderr.flush()
        pass
    xmldom = parseString(xmlstr, allow_network_access = allow_network_access, parsers = parsers, user_warning_handler = inject_warning, stderr = stderr)
    xmldom.normalize()
    src = domsource(xmldom, format = format, style = style, warnings = warnings, metadata = metadata, stderr = stderr)
    print >> stdout, src
    pass

def test():
    '''
    Someday this should be a quick smoke test.
    '''
    fake_stdin = StringIO.StringIO('''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8" />
<meta http-equiv="Content-Language" content="en" />
<title>Sample Metadata for Audiovisual Content</title>
</head>
<body class="avcontent avcontent-release avcontent-copyright">
<h1 class="avcontent-keytitle"><ruby><rb><abbr title="Fictional Item Three"><span class="avcontent-title">The Fictional Item, Part 3: Purely Fictional</span></abbr></rb><rp> (</rp><rt><abbr class="avcontent-date avcontent-release-date" title="2038">MMXXXVIII &#8212; <abbr title="NR" class="avcontent-rating avcontent-rating-mpaa">Unrated <span class="avcontent-genre">Sci Fi</span></abbr> &#8212; <abbr title="en-us" class="avcontent-language avcontent-subtitled">English</abbr> &#8212; <abbr title="4801.250" class="avcontent-duration">1h 20m 1&#188;s</abbr></abbr></rt><rp>)</rp></ruby></h1>
<h2 class="avcontent-type">Full-Length Movie</h2>
<h3>Copyright &#169; <abbr title="2034/2038" class="avcontent-copyright-date">2034-2038</abbr>, <span class="avcontent-copyright-owner avcontent-producer avcontent-producer-name">Fictional Pictures, Inc.</span></h3>
<p class="avcontent-summary">In this sequel to the brilliant but underappreciated <cite>Two Fictional Items &amp; I (2034)</cite>, <span class="avcontent-title">Fictional Item Three</span>, the <span class="avcontent-contributor"><b class="avcontent-contributor-role">Fictional Hero</b> (<span class="avcontent-contributor-name">Andy Actor</span>)</span> and <span class="avcontent-contributor"><span class="avcontent-contributor-role">Unlikely Heroine</span> (<span class="avcontent-contributor-name">Anna Actress</span>)</span> are back to save their planet from a takeover by the Brick-and-Mortar <span class="avcontent-contributor"><b class="avcontent-contributor-role">Behemoth</b> (<span class="avcontent-contributor-name">Ron Rote</span>)</span>. However, an unexpected <abbr title="Routine Plot Element">RPE</abbr> threatens to tear their fragile plot to shreds...</p>
<p class="avcontent-tags">Tags: <a rel="tag" href="http://tags.tempuri.org/tag/Dark%20Future">Dark Future</a></p>
<p class="avcontent-wholesale"><span class="avcontent-wholesale-currency"><span class="avcontent-wholesale-country avcontent-release-country avcontent-copyright-country">US</span>D</span> <span class="avcontent-wholesale-amount">4.25</span></p>
<p class="avcontent-gtin">UPC 0-01234-56789-5</p>
<p class="avcontent-file"><span class="avcontent-file-uri">fictional.mp4</span>: <span class="avcontent-file-size">530579456</span> bytes; type <span class="avcontent-file-type">video/x-ms-wmv</span>; SHA1 <span class="avcontent-file-sha1">6cb3aa27029e75ce93342837962188e239cd31fe</span>; MD5 <span class="avcontent-file-md5">05ae6f70652128ac7fd0070e01b3f6d9</span>; <span class="avcontent-file-visual"><span class="avcontent-file-visual-width">1920</span>x<span class="avcontent-file-visual-height">1080</span></span>; <abbr title="2" class="avcontent-file-audio avcontent-file-audio-channels">Stereo</abbr>; <abbr title="124531200" class="avcontent-file-bitrate">124 kbps</abbr></p>
<p class="avcontent"><span class="avcontent-type">Cover Art</span>: <span class="avcontent-file"><span class="avcontent-file-uri">fictional.png</span>: <span class="avcontent-file-size">35258</span> bytes; type <span class="avcontent-file-type">image/png</span>; SHA1 <span class="avcontent-file-sha1">b49ff30ce5fa03466289cbcccabf69cb0a7d1659</span>; <span class="avcontent-file-visual"><span class="avcontent-file-visual-width">512</span>x<span class="avcontent-file-visual-height">512</span></span></span> (this cover art is <span class="avcontent-release avcontent-release-license">licensed under a <a href="http://creativecommons.org/licenses/by/2.5/" rel="license">Creative Commons Attribution 2.5 License</a></span>)</p>
</body>
</html>
''')
    fake_stdout = StringIO.StringIO()
    fake_stderr = StringIO.StringIO()
    args = [ 'test', ]
    environ = { }
    metadata = { }
    main(args = args, environ = environ, stdin = fake_stdin, stdout = fake_stdout, stderr = fake_stderr, metadata = metadata)
    errors = fake_stderr.getvalue().splitlines()
    assert len(errors)
    assert 'non-public code in a public context for 00001234567895' in errors
    for error in errors:
        if error not in (
            'non-public code in a public context for 00001234567895',
            'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd:165:-1: warning: PEReference: %Common.attrib; not found',
            ):
            assert error.endswith(': warning: network access not allowed')
            pass
        pass
    def sortit(o):
        if type(o) is type(()):
            return '(' + ', '.join([ sortit(x) for x in o ]) + { False: '', True: ',' }[len(o) == 1] + ')'
        elif type(o) is type([]):
            return '[' + ', '.join([ sortit(x) for x in o ]) + ']'
        elif type(o) is type({}):
            return '{' + ', '.join([ sortit(k) + ': ' + sortit(v) for k, v in sorted(o.iteritems()) ]) + '}'
        elif isinstance(o, Exception):
            return o.__class__.__name__ + sortit(o.args)
        return `o`
    expected_metadata = {
        'avcontent':
        [{'avcontent-contributor':
          [{'avcontent-contributor-name':
            [{'text value':
              'Andy Actor',
              'lang value':
              'en',
              'xhtml value':
              'Andy Actor'}],
            'avcontent-contributor-role':
            [{'text value':
              'Fictional Hero',
              'lang value':
              'en',
              'xhtml value':
              'Fictional Hero'}]},
           {'avcontent-contributor-name':
            [{'text value':
              'Anna Actress',
              'lang value':
              'en',
              'xhtml value':
              'Anna Actress'}],
            'avcontent-contributor-role':
            [{'text value':
              'Unlikely Heroine',
              'lang value':
              'en',
              'xhtml value':
              'Unlikely Heroine'}]},
           {'avcontent-contributor-name':
            [{'text value':
              'Ron Rote',
              'lang value':
              'en',
              'xhtml value':
              'Ron Rote'}],
            'avcontent-contributor-role':
            [{'text value':
              'Behemoth',
              'lang value':
              'en',
              'xhtml value':
              'Behemoth'}]}],
          'avcontent-keytitle':
          [{'text value':
            'Fictional Item Three (2038)',
            'lang value':
            'en',
            'xhtml value':
            'Fictional Item Three (2038)'}],
          'avcontent-type':
          [{'text value':
            'Full-Length Movie',
            'lang value':
            'en',
            'xhtml value':
            'Full-Length Movie'}],
          'avcontent-date':
          [{'text value':
            '2038',
            'lang value':
            'en',
            'xhtml value':
            '2038'}],
          'avcontent-tags':
          [{'rel="tag"':
            [{'text value':
              'Dark Future',
              'lang value':
              'en',
              'xhtml value':
              '<a href="http://tags.tempuri.org/tag/Dark%20Future" rel="nofollow tag">Dark Future</a>'}]}],
          'avcontent-rating':
          [{'avcontent-rating-mpaa':
            [{'text value':
              'NR',
              'lang value':
              'en',
              'xhtml value':
              'NR'}]}],
          'avcontent-duration':
          [{'text value':
            '4801.250',
            'lang value':
            'en',
            'xhtml value':
            '4801.250'}],
          'avcontent-summary':
          [{'text value':
            'In this sequel to the brilliant but underappreciated Two Fictional Items & I (2034), Fictional Item Three, the Fictional Hero (Andy Actor) and Unlikely Heroine (Anna Actress) are back to save their planet from a takeover by the Brick-and-Mortar Behemoth (Ron Rote). However, an unexpected Routine Plot Element threatens to tear their fragile plot to shreds...',
            'lang value':
            'en',
            'xhtml value':
            'In this sequel to the brilliant but underappreciated Two Fictional Items &amp; I (2034), Fictional Item Three, the Fictional Hero (Andy Actor) and Unlikely Heroine (Anna Actress) are back to save their planet from a takeover by the Brick-and-Mortar Behemoth (Ron Rote). However, an unexpected Routine Plot Element threatens to tear their fragile plot to shreds...'}],
          'avcontent-copyright':
          [{'avcontent-copyright-country':
            [{'text value':
              'US',
              'lang value':
              'en',
              'xhtml value':
              'US'}],
            'avcontent-copyright-owner':
            [{'text value':
              'Fictional Pictures, Inc.',
              'lang value':
              'en',
              'xhtml value':
              'Fictional Pictures, Inc.'}],
            'text value':
            u'Copyright \N{COPYRIGHT SIGN} 2034-2038, Fictional Pictures, Inc.'.encode('utf-8'),
            'avcontent-copyright-date':
            [{'text value':
              '2034/2038',
              'lang value':
              'en',
              'xhtml value':
              '2034/2038'}],
            'xhtml value':
            u'Copyright \N{COPYRIGHT SIGN} 2034-2038, Fictional Pictures, Inc.'.encode('utf-8')}],
          'avcontent-genre':
          [{'text value':
            'Sci Fi',
            'lang value':
            'en',
            'xhtml value':
            'Sci Fi'}],
          'avcontent-title':
          [{'text value':
            'The Fictional Item, Part 3: Purely Fictional',
            'lang value':
            'en',
            'xhtml value':
            'The Fictional Item, Part 3: Purely Fictional'},
           {'text value':
            'Fictional Item Three',
            'lang value':
            'en',
            'xhtml value':
            'Fictional Item Three'}],
          'avcontent-producer':
          [{'avcontent-producer-name':
            [{'text value':
              'Fictional Pictures, Inc.',
              'lang value':
              'en',
              'xhtml value':
              'Fictional Pictures, Inc.'}]}],
          'avcontent-subtitled':
          [{'text value':
            'en-US',
            'lang value':
            'en',
            'xhtml value':
            'en-US'}],
          'avcontent-file':
          [{'avcontent-file-sha1':
            [{'text value':
              '6cb3aa27029e75ce93342837962188e239cd31fe',
              'lang value':
              'en',
              'xhtml value':
              '6cb3aa27029e75ce93342837962188e239cd31fe'}],
            'avcontent-file-bitrate':
            [{'text value':
              '124531200',
              'lang value':
              'en',
              'xhtml value':
              '124531200'}],
            'avcontent-file-type':
            [{'text value':
              'video/x-ms-wmv',
              'lang value':
              'en',
              'xhtml value':
              'video/x-ms-wmv'}],
            'avcontent-file-uri':
            [{'text value':
              'fictional.mp4',
              'lang value':
              'en',
              'xhtml value':
              'fictional.mp4'}],
            'avcontent-file-md5':
            [{'text value':
              '05ae6f70652128ac7fd0070e01b3f6d9',
              'lang value':
              'en',
              'xhtml value':
              '05ae6f70652128ac7fd0070e01b3f6d9'}],
            'avcontent-file-audio':
            [{'avcontent-file-audio-channels':
              [{'text value':
                '2',
                'lang value':
                'en',
                'xhtml value':
                '2'}]}],
            'avcontent-file-size':
            [{'text value':
              '530579456',
              'lang value':
              'en',
              'xhtml value':
              '530579456'}],
            'avcontent-file-visual':
            [{'avcontent-file-visual-width':
              [{'text value':
                '1920',
                'lang value':
                'en',
                'xhtml value':
                '1920'}],
              'avcontent-file-visual-height':
              [{'text value':
                '1080',
                'lang value':
                'en',
                'xhtml value':
                '1080'}],
              'xhtml value':
              '<div style="width: 24.0em; height: 1em; line-height: 10px; font-size: 10px; font-family: sans; color: grey; border: 2px solid grey; background: silver; text-align: center; vertical-align: middle; padding: 6.25em 0; margin: 1em; ">2073600.0px</div>'}]}],
          'avcontent-gtin':
          [{'exception value':
            ValueError('non-public code in a public context for 00001234567895',), 'text value':
            '00001234567895',
            'lang value':
            'en',
            'xhtml value':
            '00001234567895'}],
          'avcontent-wholesale':
          [{'avcontent-wholesale-currency':
            [{'text value':
              'USD',
              'lang value':
              'en',
              'xhtml value':
              'USD'}],
            'avcontent-wholesale-amount':
            [{'text value':
              '4.25',
              'lang value':
              'en',
              'xhtml value':
              '4.25'}],
            'avcontent-wholesale-country':
            [{'text value':
              'US',
              'lang value':
              'en',
              'xhtml value':
              'US'}]}],
          'avcontent-language':
          [{'text value':
            'en-US',
            'lang value':
            'en',
            'xhtml value':
            'en-US'}],
          'avcontent':
          [{'avcontent-type':
            [{'text value':
              'Cover Art',
              'lang value':
              'en',
              'xhtml value':
              'Cover Art'}],
            'avcontent-file':
            [{'avcontent-file-uri':
              [{'text value':
                'fictional.png',
                'lang value':
                'en',
                'xhtml value':
                'fictional.png'}],
              'avcontent-file-sha1':
              [{'text value':
                'b49ff30ce5fa03466289cbcccabf69cb0a7d1659',
                'lang value':
                'en',
                'xhtml value':
                'b49ff30ce5fa03466289cbcccabf69cb0a7d1659'}],
              'avcontent-file-size':
              [{'text value':
                '35258',
                'lang value':
                'en',
                'xhtml value':
                '35258'}],
              'avcontent-file-visual':
              [{'avcontent-file-visual-width':
                [{'text value':
                  '512',
                  'lang value':
                  'en',
                  'xhtml value':
                  '512'}],
                'avcontent-file-visual-height':
                [{'text value':
                  '512',
                  'lang value':
                  'en',
                  'xhtml value':
                  '512'}],
                'xhtml value':
                '<div style="width: 6.4em; height: 1em; line-height: 10px; font-size: 10px; font-family: sans; color: grey; border: 2px solid grey; background: silver; text-align: center; vertical-align: middle; padding: 2.7em 0; margin: 1em; ">262144.0px</div>'}],
              'avcontent-file-type':
              [{'text value':
                'image/png',
                'lang value':
                'en',
                'xhtml value':
                'image/png'}]}],
            'avcontent-release':
            [{'avcontent-release-license':
              [{'rel="license"':
                [{'text value':
                  'http://creativecommons.org/licenses/by/2.5/',
                  'lang value':
                  'en',
                  'xhtml value':
                  '<a href="http://creativecommons.org/licenses/by/2.5/" rel="nofollow license">http://creativecommons.org/licenses/by/2.5/</a>'}]}]}]}],
          'avcontent-release':
          [{'avcontent-release-country':
            [{'text value':
              'US',
              'lang value':
              'en',
              'xhtml value':
              'US'}],
            'avcontent-release-date':
            [{'text value':
              '2038',
              'lang value':
              'en',
              'xhtml value':
              '2038'}]}]}]}
    assert sortit(metadata) == sortit(expected_metadata)
    pass

test()

if __name__ == '__main__':
    main()
    pass
