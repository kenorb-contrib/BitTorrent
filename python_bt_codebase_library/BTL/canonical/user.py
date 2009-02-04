#!/usr/bin/env python
# -*- coding: utf-8 -*-
from BTL.obsoletepythonsupport import set
from BTL.canonical.unicode import unichr, unichars, to_utf8, to_unicode
from BTL.canonical.xidmodifications import xidmodifications_restricted_pat, xidmodifications_not_IICore_pat
from BTL.canonical.idnchars import idnchars_output_pat, idnchars_input_lenient_pat, idnchars_nonstarting_pat, idnchars_input_pat
from BTL.canonical.saslprep import saslprep
from rfc822 import parseaddr
import os
import time
import urllib
# for URI sanitizer
import re
import urlparse
import unicodedata
import cgi

# adapted from RFC3986 (a.k.a. STD66)
non_uri_re = re.compile(r'(?:[-\[\]@!$&\'()*+,;=._~A-Za-z0-9:/?#]|%[0-9a-fA-F][0-9a-fA-F])+|(.)', re.DOTALL)
denormalized_escape_re = re.compile(r'((?:%(?:2[deDE]|3[0-9]|[46][1-9a-fA-F]|[57][0-9aA]|5[fF]|7[eE]))+)|[^%]+|.', re.DOTALL)
valid_uri_re = re.compile(r'\A(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?\Z')
# no need to pass through harmful URIs here
safe_uri_re = re.compile(r'\A(?:https?|ftp)://.*\Z')
def escape_non_uri(uri):
    '''
    Perform URI escaping on non-ASCII bytes
    '''
    o = []
    for match in non_uri_re.finditer(uri):
        if match.group(1): o.append(urllib.quote(match.group(1)))
        else: o.append(match.group(0))
        pass
    return ''.join(o)
def normalize_uri_escapes(uri):
    '''
    Return a URI with unneccessary quoting removed
    '''
    o = []
    for match in denormalized_escape_re.finditer(uri):
        if match.group(1): o.append(urllib.unquote(match.group(1)))
        else: o.append(match.group(0))
        pass
    return ''.join(o)
def encode_idna(hostname):
    hostname = to_utf8(hostname)
    segments = []
    for segment in hostname.split('.'):
        try:
            usegment = segment.decode('utf-8')
            idna = usegment.encode('idna')
            if idna[:len('xn--')] != 'xn--':
                raise TypeError('not idna')
            if usegment == usegment.lower():
                segment = idna.lower()
            elif usegment == usegment.upper():
                segment = idna.upper()
            elif usegment == usegment.capitalize():
                segment = idna.capitalize()
            elif usegment == usegment.title():
                segment = idna.title()
            else:
                segment = idna
        except:
            pass
        segments.append(segment)
    return '.'.join(segments)
def decode_idna(hostname):
    hostname = to_utf8(hostname)
    segments = []
    for segment in hostname.split('.'):
        try:
            if segment[:len('xn--')].lower() != 'xn--'.lower():
                raise TypeError('not idna')
            usegment = segment.lower().decode('idna')
            if unicode(segment) == unicode(segment).lower():
                usegment = usegment.lower()
            elif unicode(segment) == unicode(segment).upper():
                usegment = usegment.upper()
            elif unicode(segment) == unicode(segment).capitalize():
                usegment = usegment.capitalize()
            elif unicode(segment) == unicode(segment).title():
                usegment = usegment.title()
            segment = usegment.encode('utf-8')
        except:
            pass
        segments.append(segment)
    return '.'.join(segments)
def uri_encode_idna(uri):
    '''
    Do IDNA encoding for hostnames, if possible
    '''
    scheme, netloc, path, query, fragment  = urlparse.urlsplit(uri)
    if scheme.lower() in urlparse.uses_netloc and netloc is not None:
        user_password, host_port = urllib.splituser(netloc)
        if host_port is not None:
            host, port = urllib.splitport(host_port)
            if host is not None and host[:1] + host[-1:] != '[]':
                # NOTE: this works around a bug in the urlparse cache w.r.t. unicode strings
                host = ''.join([ chr(ord(ch)) for ch in host ])
                try:
                    host = urllib.quote(unicodedata.normalize('NFKC', urllib.unquote(host).decode('utf-8')).encode('utf-8'))
                except:
                    pass
                try:
                    host = urllib.quote(encode_idna(urllib.unquote(host)))
                except:
                    pass
                host_port = host + (port is not None and (':' + port) or '')
                netloc = (user_password is not None and (user_password + '@') or '') + host_port
        pass
    uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
    # NOTE: this works around a bug in the urlparse cache w.r.t. unicode strings
    uri = ''.join([ chr(ord(ch)) for ch in uri ])
    return uri
def uri_decode_idna(uri):
    '''
    Do IDNA decoding for hostnames, if possible
    '''
    scheme, netloc, path, query, fragment  = urlparse.urlsplit(uri)
    if scheme.lower() in urlparse.uses_netloc and netloc is not None:
        user_password, host_port = urllib.splituser(netloc)
        if host_port is not None:
            host, port = urllib.splitport(host_port)
            if host is not None and host[:1] + host[-1:] != '[]':
                # NOTE: this works around a bug in the urlparse cache w.r.t. unicode strings
                host = ''.join([ chr(ord(ch)) for ch in host ])
                try:
                    host = urllib.quote(decode_idna(urllib.unquote(host)))
                except:
                    pass
                try:
                    host = urllib.quote(unicodedata.normalize('NFKC', urllib.unquote(host).decode('utf-8')).encode('utf-8'))
                except:
                    pass
                host_port = host + (port is not None and (':' + port) or '')
                netloc = (user_password is not None and (user_password + '@') or '') + host_port
        pass
    uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
    # NOTE: this works around a bug in the urlparse cache w.r.t. unicode strings
    uri = ''.join([ chr(ord(ch)) for ch in uri ])
    return uri
def fix_query_string_spaces(uri):
    '''
    Replace %20 with + in the query string part of the URI
    '''
    scheme, netloc, path, query, fragment  = urlparse.urlsplit(uri)
    query = query.replace('%20', '+')
    uri = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
    # NOTE: this works around a bug in the urlparse cache w.r.t. unicode strings
    uri = ''.join([ chr(ord(ch)) for ch in uri ])
    return uri
def canon_uri(uri, unsafe = False):
    '''
    Canonicalize a URI and return it. Unless the optional
    parameter unsafe = True is given, None is returned if the URI
    is not a valid, "safe" FTP, HTTP or HTTPS URI.
    '''
    uri = to_utf8(uri)
    if urlparse.urlparse(uri)[0] == '': uri = 'http://' + uri
    uri = escape_non_uri(uri)
    uri = normalize_uri_escapes(uri)
    uri = uri_encode_idna(uri)
    uri = fix_query_string_spaces(uri)
    if unsafe or (safe_uri_re.match(uri) and valid_uri_re.match(uri) and uri == uri.decode('us-ascii', 'replace').encode('us-ascii', 'replace')):
        return uri
bidi_controls = u'\N{LEFT-TO-RIGHT MARK}\N{RIGHT-TO-LEFT MARK}\N{LEFT-TO-RIGHT EMBEDDING}\N{RIGHT-TO-LEFT EMBEDDING}\N{LEFT-TO-RIGHT OVERRIDE}\N{RIGHT-TO-LEFT OVERRIDE}\N{POP DIRECTIONAL FORMATTING}'
iri_nonascii_pctencoded_re = re.compile(r'((?:%[89a-fA-F][0-9a-fA-F])+)|.', re.DOTALL)
iri_nonascii_re = re.compile(r'((?:(?:\xe1[\x80-\xbf][\x80-\xbf]|\xe0[\xa0-\xbf][\x80-\xbf]|[\xc3-\xda][\x80-\xbf]|\xc2[\xa0-\xbf]|[\xe2-\xec][\x80-\xbf][\x80-\xbf]|[\xdb-\xdf][\x80-\xbf]|\xed[\x80-\x9f][\x80-\xbf]|\xef(?:\xb7[\x80-\x8f\xb0-\xbf]|[\xa4-\xb6\xb8-\xbe][\x80-\xbf]|\xbf[\x80-\xaf])|\xf1(?:[\x8f\x9f\xaf\xbf](?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd])|[\x80-\x8e\x90-\x9e\xa0-\xae\xb0-\xbd][\x80-\xbf][\x80-\xbf]|\xbe[\x80-\xbf][\x80-\xbf])|\xf0(?:[\x9f\xaf\xbf](?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd])|[\x90-\x9e\xa0-\xae\xb0-\xbd][\x80-\xbf][\x80-\xbf]|\xbe[\x80-\xbf][\x80-\xbf])|\xf3(?:[\x80-\x8e\x90-\x9e\xa1-\xae][\x80-\xbf][\x80-\xbf]|[\x8f\x9f\xaf](?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd]))|\xf2(?:[\x8f\x9f\xaf\xbf](?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd])|[\x80-\x8e\x90-\x9e\xa0-\xae\xb0-\xbd][\x80-\xbf][\x80-\xbf]|\xbe[\x80-\xbf][\x80-\xbf]))|(?:\xf3(?:[\xb0-\xbe][\x80-\xbf][\x80-\xbf]|\xbf(?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd]))|\xf4(?:[\x80-\x8e][\x80-\xbf][\x80-\xbf]|\x8f(?:[\x80-\xbe][\x80-\xbf]|\xbf[\x80-\xbd]))|\xef[\x80-\xa3][\x80-\xbf]|\xee[\x80-\xbf][\x80-\xbf]))+)|.', re.DOTALL)
def iri_unquote(iri):
    '''
    Unquote safe percent-encoded non-ASCII parts of an IRI
    '''
    o = []
    for match2 in iri_nonascii_pctencoded_re.finditer(iri):
        if match2.group(1):
            for match in iri_nonascii_re.finditer(urllib.unquote(match2.group(1))):
                if match.group(1):
                    o.append(match.group(1))
                else:
                    o.append(urllib.quote(match.group(0)))
        else:
            o.append(match2.group(0))
    iri = ''.join(o)
    for forbidden in bidi_controls:
        forbidden = forbidden.encode('utf-8')
        iri = urllib.quote(forbidden).join(iri.split(forbidden))
    return iri
def canon_idn(idn):
    '''
    Canonicalize an internationalized domain name
    '''
    idn = to_utf8(idn)
    idn = escape_non_uri(idn)
    if idn[:1] + idn[-1:] != '[]':
        try:
            idn = urllib.quote(decode_idna(urllib.unquote(idn)))
        except:
            pass
    return iri_unquote(idn)

def canon_iri(iri, unsafe = False):
    '''
    Canonicalize an IRI
    '''
    iri = canon_uri(uri = iri, unsafe = unsafe)
    if iri is not None:
        iri = uri_decode_idna(iri)
        iri = iri_unquote(iri)
    return iri

xmlentities = {
    'lt': '<',
    'gt': '>',
    'amp': '&',
    'quot': '"',
    'apos': "'",
    }
xmlchars_re = (lambda: re.compile(r'(?:&(?:(%s)|#[xX]0*([1-9a-fA-F][0-9a-fA-F]*)|#0*([1-9][0-9]*))(?:;|\b)|.)' % r'|'.join([ re.escape(x) for x in xmlentities ]), re.DOTALL))()

c1_re = re.compile(r'(\xc2[\x80-\x9f])|(?:[^\xc2]|\xc2[^\x80-\x9f\xc2]){1,1024}|.', re.DOTALL)
def demoronize(chars):
    '''
    Transform Unicode C1 codepoints to non-C1 codepoints as if
    Unicode were a windows-1252 superset rather than an ISO-8859-1
    superset. C1 characters not mapped in windows-1252 are mapped
    according to macroman.
    '''
    chars = to_utf8(chars)
    o = []
    for match in c1_re.finditer(chars):
        if match.group(1):
            byteval = match.group(0).decode('utf-8').encode('iso-8859-1')
            o.append((byteval.decode('windows-1252', 'ignore') or byteval.decode('macroman')).encode('utf-8'))
        else:
            o.append(match.group(0))
    return ''.join(o)
def decode_xmlchars(chars):
    chars = to_utf8(chars)
    o = []
    for match in xmlchars_re.finditer(chars):
        if match.group(1):
            o.append(xmlentities[match.group(1)])
        elif match.group(2):
            try:
                o.append(unichr(int(match.group(2), 16)).encode('utf-8', 'replace'))
            except:
                o.append(u'\N{REPLACEMENT CHARACTER}')
        elif match.group(3):
            try:
                o.append(unichr(int(match.group(3), 10)).encode('utf-8', 'replace'))
            except:
                o.append(u'\N{REPLACEMENT CHARACTER}')
        else:
            o.append(match.group(0))
    return ''.join(o)

idn_re = re.compile(r'\b((?:[a-zA-Z0-9](?:[-a-zA-Z0-9]*[a-zA-Z0-9])?\.)*[xX][nN]--[-a-zA-Z0-9]*[a-zA-Z0-9](?:\.[a-zA-Z0-9](?:[-a-zA-Z0-9]*[a-zA-Z0-9])?)*\.?)\b|\b\w+\b|.', re.DOTALL)
def demoronize_idna(chars):
    '''
    Decode IDNA tokens and ensure that decoded hostnames have the
    correct directionality using Unicode bidirectional embedding
    control characters. Note that such control characters are not
    valid in IRIs or IDNs.
    '''
    chars = to_utf8(chars)
    o = []
    for match in idn_re.finditer(chars):
        if match.group(1):
            try:
                o.append(u'\N{LEFT-TO-RIGHT EMBEDDING}'.encode('utf-8') +
                         canon_idn(match.group(0)) +
                         u'\N{POP DIRECTIONAL FORMATTING}'.encode('utf-8'))
            except:
                o.append(match.group(0))
        else:
            o.append(match.group(0))
    return ''.join(o)

# this really needs work...
_valid_email_re = re.compile(r'\A[-a-zA-Z0-9_+.]+[@](?:[1-9][0-9]{0,2}[.](?:[1-9][0-9]{0,2}|0)[.](?:[1-9][0-9]{0,2}|0)[.][1-9][0-9]{0,2}|(?:[a-zA-Z0-9][-a-zA-Z0-9]{0,62}[.])+[a-zA-Z][-a-zA-Z0-9]{0,61}[a-zA-Z0-9])\Z')

def canon_email(address):
    address = to_utf8(address)
    address = parseaddr(address)[1]
    if not address:
        raise ValueError("email address must be non-empty")
    if '@' not in address:
        raise ValueError("email address does not contain the required '@' character")
    localpart, hostname = address.split('@')
    hostname = hostname.rstrip('.')
    if not hostname:
        raise ValueError("email address hostname must be non-empty")
    if '.' not in hostname:
        raise ValueError("email address hostname must contain the '.' character and a domain name")
    if not localpart:
        raise ValueError("email address local part must be non-empty")
#   if '+' in localpart:
#       raise ValueError("email address local part must not contain the '+' character.")
    hostname = encode_idna(hostname)
    hostname = hostname.decode('utf-8').lower().encode('utf-8')
    address = '%s@%s' % (localpart, hostname)
    if not _valid_email_re.match(address):
        raise ValueError("email address does not match the permitted pattern")
    return address

_valid_language_code_re = re.compile(r'\A([a-z]{2,3}|([ix]|[a-z]{2,3})-([A-Z]{2,3}|[a-z0-9]{4,}))(-[a-z0-9]+)*\Z')

def canon_lang(lang):
    '''
    Returns an RFC 3066 language value in normalized form; language
    codes from ISO 639 are lower case, while country
    codes from ISO 3166 are upper case; IANA-assigned
    and private subtags are assumed to be lower-case:
    en
    en-US
    en-scouse
    en-US-tx
    sgn-US-ma
    i-tsolyani
    x-37334
    '''
    lang = to_utf8(lang)
    lang = lang.decode('UTF-8')
    lang = lang.lower()
    # replace underscores sometimes found in locale names
    lang = '-'.join(lang.split('_'))
    lang_parts = lang.split('-')
    if len(lang_parts) > 1 and (len(lang_parts[1]) in (2, 3)):
        lang_parts[1] = lang_parts[1].upper()
    lang = '-'.join(lang_parts)
    if not _valid_language_code_re.match(lang):
        raise ValueError("RFC 3066 language value must be in normalized form; language codes from ISO 639 are lower case, while country codes from ISO 3166 are upper case; IANA-assigned and private subtags are lower case (ASCII only)")
    return lang.encode('UTF-8')

# extension of remapping from appendix a of utr # 36, with a bugfix
username_premap = {
    u'_': u'-',
    u'.': u'-',
    u'/': u'-',
    u':': u'-',
    u'\\': u'-',
    u'\'': u'\u02bc',
    u'\u2018': u'\u02bb',
    u'\u2019': u'\u02bc',
    u'\u309b': u'\u3099',
    u'\u309c': u'\u309a',
    }
username_premap_re = (lambda: re.compile(ur'|'.join([ ur'(?:%s)' % re.escape(i) for i in username_premap ]), re.UNICODE))()

# \A means match only from the start of string.
# \Z means match up to the end of the string.  Specifying both \A and \Z means
# match the entire string.

_restrictive_valid_user_name_re = re.compile(r'\A[a-z][-a-z0-9]{1,61}[a-z0-9]\Z')
# The following regex allows all user names from 2 to 64 characters starting
# with any lowercase letter or digit.
_valid_user_name_re = re.compile(r'\A[a-z0-9][-a-z0-9]{0,61}[a-z0-9]\Z')
#_valid_user_name_re = re.compile(r'\A[a-z][-a-z0-9]{1,61}[a-z0-9]\Z')
##_valid_user_name_re = re.compile(r'\A[a-z][-a-z0-9]{4,61}[a-z0-9]\Z')

_username_nonstarting_utf8_re = re.compile(r'\A(?:%s)' % idnchars_nonstarting_pat)
_invalid_username_utf8_re = (lambda: re.compile(r'|'.join([ r'(?:%s)' % pat for pat in (xidmodifications_not_IICore_pat, xidmodifications_restricted_pat) ])))()
_valid_input_username_utf8_re = (lambda: re.compile(r'\A(?:%s)+\Z' % (r'|'.join([ r'(?:%s)' % pat for pat in (idnchars_output_pat, idnchars_input_pat, idnchars_input_lenient_pat, idnchars_nonstarting_pat) ]))))()
_valid_output_username_utf8_re = (lambda: re.compile(r'\A(?:%s)+\Z' % (r'|'.join([ r'(?:%s)' % pat for pat in (idnchars_output_pat, idnchars_nonstarting_pat) ]))))()

class DisplayedValueError(ValueError):
    def __init__(self, error, displayed_error):
        self.error = error
        self.displayed_error = displayed_error

    def __str__(self):
        return self.displayed_error

    def internal_error(self):
        return self.error

def canon_person(name):
    name = to_utf8(name)
    name = demoronize(name)
    name = name.decode('utf-8')
    name = name.lower()
    name = unicodedata.normalize('NFKC', name)
    name = name.strip()
    if not name:
        raise ValueError("name must be non-empty")
    name = '-'.join(name.split())
    name = username_premap_re.sub(lambda m: username_premap[m.group(0)], name)
    return name


def canon_username(username, allow_reserved = True ):
    username = to_utf8(username)
    username = demoronize(username)
    username = username.decode('utf-8')
    username = username.lower()
    username = unicodedata.normalize('NFKC', username)
    username = username.strip()
    if not username:
        raise ValueError("user name must be non-empty")
    username = '-'.join(username.split())
    username = username_premap_re.sub(lambda m: username_premap[m.group(0)], username)
    if allow_reserved:
        if _valid_user_name_re.match(to_utf8(username)) and username[:len('xn--')] == 'xn--':
            username = to_utf8(username).decode('idna')
    elif _restrictive_valid_user_name_re.match(to_utf8(username)) and username[:len('xn--')] == 'xn--':
        username = to_utf8(username).decode('idna')
    if _username_nonstarting_utf8_re.match(username.encode('utf-8')):
        raise ValueError("user name begins with a character not permitted in that position")
    if _invalid_username_utf8_re.search(username.encode('utf-8')):
        raise DisplayedValueError("user name contains characters that are not permitted (reason code: XID-in)", "user name contains characters that are not permitted")
    if not _valid_input_username_utf8_re.match(username.encode('utf-8')):
        raise DisplayedValueError("user name contains characters that are not permitted (reason code: IDN-in) FOO FOO FOO ", "user name contains characters that are not permitted")
    try:
        username = username.encode('idna')
    except:
        raise DisplayedValueError("user name contains characters that are not permitted (reason code: IDN)", "user name contains characters that are not permitted")
    if not _valid_output_username_utf8_re.match(username.decode('idna').encode('utf-8')):
        raise DisplayedValueError("user name contains characters that are not permitted (reason code: IDN-out)", "user name contains characters that are not permitted" )
    if allow_reserved and len(username) < 2:
        raise ValueError("user name is too short (must contain at least two characters)")
    elif not allow_reserved and len(username) < 3:
        raise ValueError("user name is too short (must contain at least three characters)")
    if len(username) > 63:
        raise ValueError("user name is too long (must contain at most sixty-three characters)")
    if not allow_reserved and not _valid_user_name_re.match(username):
        raise ValueError("user name must start with a letter or digit, end with a letter or digit, and contain only letters, digits and hyphens")
    # allow_reserved is ignored for now
    return username

def canon_password(username, password, allow_weak):
    '''
    N.B. allow_weak = True should be used for lookup but not storage
    as it allows unassigned codepoints.
    '''
    username = to_utf8(username)
    password = to_utf8(password)
    password = demoronize(password)
    password = password.decode('utf-8')
    password = saslprep(password, allow_unassigned = allow_weak)
    if not allow_weak:
        if len(password) < 6:
            # FIXME: This error message is wrong -- there is no actual maximum length.
            raise ValueError('Please enter a password of between 6 and 20 characters')
        try:
            cpassword = canon_username(password, allow_reserved = True).decode('idna')
        except:
            cpassword = password.decode('utf-8')
        try:
            username = canon_username(username, allow_reserved = True).decode('idna')
        except:
            try:
                username = username.decode('idna')
            except:
                username = username.decode('utf-8')
        # import here because this is a big, slow module
        from BTL.canonical.identifier import confuse
        password_letters = list(set([ ch for ch in confuse(cpassword) ]))
        password_letters.sort()
        username_letters = list(set([ ch for ch in confuse(username) ]))
        username_letters.sort()
        if cpassword in username or u''.join(password_letters) == u''.join(username_letters):
            raise ValueError('password is too similar to user name')
        # TODO: password re-use prevention (password history)
        # TODO: complexity checks (dictionary?)
        # TODO: lockout (temporary and permanent) after failed login attempts
    return password

_account_name_graphic_premap, _account_name_graphic_premap_re = [ None ] * 2

def account_name_graphic(value, prefix_reserved = [ u'xn--' ], full_name_reserved = []):
    '''
    Transform an acocunt name for graphic form collation.
    '''
    if value is not None:
        from BTL.canonical.identifier import confuse
        value = to_unicode(value)
        value = unicodedata.normalize('NFC', value)
        value = value.strip()
        value = u'-'.join(value.split())
        value = username_premap_re.sub(lambda m: username_premap[m.group(0)], value)
        global _account_name_graphic_premap, _account_name_graphic_premap_re
        value = value.strip()
        value = confuse(u'-').join(value.split())
        if _account_name_graphic_premap is None:
            _account_name_graphic_premap = dict([ (confuse(k), confuse(v)) for k, v in username_premap.iteritems() ])
        if _account_name_graphic_premap_re is None:
            _account_name_graphic_premap_re = re.compile(ur'|'.join([ ur'(?:%s)' % re.escape(i) for i in _account_name_graphic_premap ]), re.UNICODE)
        value = _account_name_graphic_premap_re.sub(lambda m: _account_name_graphic_premap[m.group(0)], value)
        value = confuse(value)
        for prefix in prefix_reserved:
            if value.startswith(confuse(prefix)):
                raise ValueError('The requested user name is reserved.  It starts with something a lot like ' + prefix)
        for full_name in full_name_reserved:
            if value == confuse(full_name):
                raise ValueError('The requested user name is reserved.  It is too much like ' + full_name)
    return value

def urlify_username(username):
    '''
    Escape a username for use in a URI.
    '''
    return urllib.quote(to_utf8(canon_username(username, True).decode('idna')),
                        safe='')

def test():
    '''
    Run a quick smoke test to make sure this module still works.
    '''
    for unsafe, uri_in, uri_out, iri_out in (
        (False,
         'http://www.example.org',
         'http://www.example.org',
         'http://www.example.org',
         ),
        (True,
         'http://www.example.org',
         'http://www.example.org',
         'http://www.example.org',
         ),
        (False,
         'javascript:alert("0wn3d!")',
         None,
         None,
         ),
        (True,
         'javascript:alert("0wn3d!")',
         'javascript:alert(%220wn3d!%22)',
         'javascript:alert(%220wn3d!%22)',
         ),
        (False,
         'http://www.example.org/?q=monkey%20rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (True,
         'http://www.example.org/?q=monkey%20rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (False,
         'http://www.example.org/?q=monkey rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (True,
         'http://www.example.org/?q=monkey rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (True,
         'http://www.example.org/',
         'http://www.example.org/',
         'http://www.example.org/',
         ),
        (True,
         u'http://www.example.org/',
         'http://www.example.org/',
         'http://www.example.org/',
         ),
        (True,
         u'http://\N{LEFT-TO-RIGHT MARK}\N{RIGHT-TO-LEFT MARK}\N{LEFT-TO-RIGHT EMBEDDING}\N{RIGHT-TO-LEFT EMBEDDING}\N{LEFT-TO-RIGHT OVERRIDE}\N{RIGHT-TO-LEFT OVERRIDE}\N{POP DIRECTIONAL FORMATTING}/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         ),
        (True,
         'http://\xe2\x80\x8e\xe2\x80\x8f\xe2\x80\xaa\xe2\x80\xab\xe2\x80\xad\xe2\x80\xae\xe2\x80\xac/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         ),
        (True,
         'http://xn--fiqz9szqa.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         u'http://\u4e2d\u570b\u57ce.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         'http://%E4%B8%AD%E5%9C%8B%E5%9F%8E.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         'http://xn--afiqz9szqa.net/',
         'http://xn--afiqz9szqa.net/',
         'http://xn--afiqz9szqa.net/',
         ),
        (False,
         'www.example.org',
         'http://www.example.org',
         'http://www.example.org',
         ),
        (True,
         'www.example.org',
         'http://www.example.org',
         'http://www.example.org',
         ),
        (False,
         'www.example.org/?q=monkey%20rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (True,
         'www.example.org/?q=monkey%20rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (False,
         'www.example.org/?q=monkey rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (True,
         'www.example.org/?q=monkey rockets',
         'http://www.example.org/?q=monkey+rockets',
         'http://www.example.org/?q=monkey+rockets',
         ),
        (True,
         'www.example.org/',
         'http://www.example.org/',
         'http://www.example.org/',
         ),
        (True,
         u'www.example.org/',
         'http://www.example.org/',
         'http://www.example.org/',
         ),
        (True,
         u'\N{LEFT-TO-RIGHT MARK}\N{RIGHT-TO-LEFT MARK}\N{LEFT-TO-RIGHT EMBEDDING}\N{RIGHT-TO-LEFT EMBEDDING}\N{LEFT-TO-RIGHT OVERRIDE}\N{RIGHT-TO-LEFT OVERRIDE}\N{POP DIRECTIONAL FORMATTING}/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         ),
        (True,
         '\xe2\x80\x8e\xe2\x80\x8f\xe2\x80\xaa\xe2\x80\xab\xe2\x80\xad\xe2\x80\xae\xe2\x80\xac/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         'http://%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC/',
         ),
        (True,
         'xn--fiqz9szqa.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         '\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         u'\u4e2d\u570b\u57ce.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         '%E4%B8%AD%E5%9C%8B%E5%9F%8E.net/',
         'http://xn--fiqz9szqa.net/',
         'http://\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net/',
         ),
        (True,
         'xn--afiqz9szqa.net/',
         'http://xn--afiqz9szqa.net/',
         'http://xn--afiqz9szqa.net/',
         ),
        (True,
         'xn--afiqz9szqa.net/',
         'http://xn--afiqz9szqa.net/',
         'http://xn--afiqz9szqa.net/',
         ),
        ):
        # NOTE: please fix canon_uri/canon_iri rather than commenting these out if the tests fail on your system
        assert canon_uri(uri = uri_in, unsafe = unsafe) == uri_out
        assert canon_iri(iri = uri_in, unsafe = unsafe) == iri_out
        pass
    for idn_in, idn_out in (
        ('www.example.org',
         'www.example.org',
         ),
        (u'www.example.org',
         'www.example.org',
         ),
        (u'\N{LEFT-TO-RIGHT MARK}\N{RIGHT-TO-LEFT MARK}\N{LEFT-TO-RIGHT EMBEDDING}\N{RIGHT-TO-LEFT EMBEDDING}\N{LEFT-TO-RIGHT OVERRIDE}\N{RIGHT-TO-LEFT OVERRIDE}\N{POP DIRECTIONAL FORMATTING}',
         '%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC',
         ),
        ('\xe2\x80\x8e\xe2\x80\x8f\xe2\x80\xaa\xe2\x80\xab\xe2\x80\xad\xe2\x80\xae\xe2\x80\xac',
         '%E2%80%8E%E2%80%8F%E2%80%AA%E2%80%AB%E2%80%AD%E2%80%AE%E2%80%AC',
         ),
        ('xn--fiqz9szqa.net',
         '\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net',
         ),
        ('\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net',
         '\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net',
         ),
        (u'\u4e2d\u570b\u57ce.net',
         '\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net',
         ),
        ('%E4%B8%AD%E5%9C%8B%E5%9F%8E.net',
         '\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net',
         ),
        ('xn--afiqz9szqa.net',
         'xn--afiqz9szqa.net',
         ),
        ):
        assert canon_idn(idn = idn_in) == idn_out
    for xmlchars, chars in (
        ('This is a simple test.',
         'This is a simple test.',
         ),
        ('< &lt &lt&lt; > &gt &gt&gt; & &amp &amp&amp; " &quot &quot&quot; \' &apos &apos&apos;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#60 &#60&#60; > &#62 &#62&#62; & &#38 &#38&#38; " &#34 &#34&#34; \' &#39 &#39&#39;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#x3C &#x3C&#x3C; > &#x3E &#x3E&#x3E; & &#x26 &#x26&#x26; " &#x22 &#x22&#x22; \' &#x27 &#x27&#x27;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#x3c &#x3c&#x3c; > &#x3e &#x3e&#x3e; & &#x26 &#x26&#x26; " &#x22 &#x22&#x22; \' &#x27 &#x27&#x27;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#X3C &#X3C&#X3C; > &#X3E &#X3E&#X3E; & &#X26 &#X26&#X26; " &#X22 &#X22&#X22; \' &#X27 &#X27&#X27;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#060 &#060&#060; > &#062 &#062&#062; & &#038 &#038&#038; " &#034 &#034&#034; \' &#039 &#039&#039;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#x03C &#x03C&#x03C; > &#x03E &#x03E&#x03E; & &#x026 &#x026&#x026; " &#x022 &#x022&#x022; \' &#x027 &#x027&#x027;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#x03c &#x03c&#x03c; > &#x03e &#x03e&#x03e; & &#x026 &#x026&#x026; " &#x022 &#x022&#x022; \' &#x027 &#x027&#x027;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ('< &#x03C &#x03C&#x03C; > &#x03E &#x03E&#x03E; & &#x026 &#x026&#x026; " &#x022 &#x022&#x022; \' &#x027 &#x027&#x027;',
         '< < << > > >> & & && " " "" \' \' \'\'',
         ),
        ):
        assert decode_xmlchars(xmlchars) == chars
    for i, o in (
        (u'root@example.org',    u'root@example.org'),
        (u'root@Example.ORG',    u'root@example.org'),
        (u'Root@example.org',    u'Root@example.org'),
        (u'Root@Example.ORG',    u'Root@example.org'),
        (u'root@127.0.0.1',      u'root@127.0.0.1'),
        (u'Root@127.0.0.1',      u'Root@127.0.0.1'),
        ('Shrubbery@www.example.org',
         'Shrubbery@www.example.org',
         ),
        (u'Shrubbery@www.example.org',
         'Shrubbery@www.example.org',
         ),
        ('Shrubbery@xn--fiqz9szqa.net',
         'Shrubbery@xn--fiqz9szqa.net',
         ),
        ('Shrubbery@XN--FIQZ9SZQA.NET',
         'Shrubbery@xn--fiqz9szqa.net',
         ),
        ('Shrubbery@\xe4\xb8\xad\xe5\x9c\x8b\xe5\x9f\x8e.net',
         'Shrubbery@xn--fiqz9szqa.net',
         ),
        (u'Shrubbery@\u4e2d\u570b\u57ce.net',
         'Shrubbery@xn--fiqz9szqa.net',
         ),
        ('Shrubbery@xn--afiqz9szqa.net',
         'Shrubbery@xn--afiqz9szqa.net',
         ),
        ('Shrubbery@XN--AFIQZ9SZQA.NET',
         'Shrubbery@xn--afiqz9szqa.net',
         ),
        ):
        assert to_utf8(canon_email(i)) == to_utf8(o)
    for i in (
        '', # must be non-empty
        'root', # missing '@'
        '@', # empty hostname and local part
        'root@', # empty hostname
        '@127.0.0.1', # empty local part
        'root@localhost', # hostname missing required '.'
        ):
        try:
            canon_email(i)
        except:
            pass
        else:
            assert "canon_email should have generated an exception" [:0]
    for i, o in (
        ('x' * 6, 'x' * 6),
        ('x' * 63, 'x' * 63),
        ('short1', 'short1'),
        ('    strip this    ', 'strip-this'),
        (u'zo\N{LATIN SMALL LETTER E WITH DIAERESIS}hep', 'xn--zohep-osa'),
        ('xn--zohep-osa', 'xn--zohep-osa'),
        ):
        assert to_utf8(canon_username(i)) == to_utf8(o)
    for i in (
        '', # must be non-empty
        'x', # too short
        'x' * 64, # too long
        'way too long' * 256,
        'xn--foo', # characters not allowed
        ):
        try:
            canon_username(i)
        except:
            pass
        else:
            assert "canon_username should have generated an exception" [:0]
    for i in (
        '', # must be non-empty
        'xx', # too short
        'x' * 64, # too long
        'sh',
        'way too long' * 256,
        'xn--foo', # characters not allowed
        ):
        try:
            canon_username(i, allow_reserved = False)
        except:
            pass
        else:
            assert "canon_username should have generated an exception" [:0]
    for i, o in (
        ('x' * 6, 'x' * 6),
        ('x' * 63, 'x' * 63),
        ('short1', 'short1'),
        ('    strip this    ', 'strip-this'),
        (u'zo\N{LATIN SMALL LETTER E WITH DIAERESIS}hep', 'zo%C3%ABhep'),
        ('xn--zohep-osa', 'zo%C3%ABhep'),
        ):
        assert urlify_username(i) == to_utf8(o)
    for i in (
        '', # must be non-empty
        'x', # too short
        'x' * 64, # too long
        'way too long' * 256,
        'xn--foo', # characters not allowed
        ):
        try:
            urlify_username(i)
        except:
            pass
        else:
            assert "urlify_username should have generated an exception" [:0]
    for i, o in (
        ('', ''),
        ('x' * 6, u'x' * 6),
        ('x' * 63, u'x' * 63),
        ('short1', u'short1'),
        ('    strip this    ', u'strip-this'),
        (u'zo\N{LATIN SMALL LETTER E WITH DIAERESIS}hep', 'zo\xC3\xABhep'),
        (u'zo\N{LATIN SMALL LETTER E WITH DIAERESIS}hep', 'z0\xC3\xABhep'),
        (u'zo\N{LATIN SMALL LETTER E WITH DIAERESIS}hep', 'zO\xC3\xABhep'),
        ('x' * 5, 'x' * 5),
        ('x' * 64, 'x' * 64),
        ('short', 'short'),
        ('way too long' * 256, 'way too long' * 256),
        ):
        assert account_name_graphic(i) == account_name_graphic(o)
    for i in (
        'xn--foo', # characters not allowed
        'xn--zohep-osa',
        ):
        try:
            account_name_graphic(i)
        except:
            pass
        else:
            assert "account_name_graphic should have generated an exception" [:0]
    for i, o in (
        (u'', u''),
        ('Hello, world!', u'Hello, world!'),
        (u'Hello, world!', u'Hello, world!'),
        (u'\x00', u'\x00'),
        (u'\x7f', u'\x7f'),
        (u'\xa0', u'\xa0'),
        (u'\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f',
         u'\u20ac\xc5\u201a\u0192\u201e\u2026\u2020\u2021\u02c6\u2030\u0160\u2039\u0152\xe7\u017d\xe8\xea\u2018\u2019\u201c\u201d\u2022\u2013\u2014\u02dc\u2122\u0161\u203a\u0153\xf9\u017e\u0178'),
        ):
        assert demoronize(i) == to_utf8(o)
    for i in (
        'en',
        'en-US',
        'en-scouse',
        'en-US-tx',
        'sgn-US-ma',
        'i-tsolyani',
        'x-37334',
        ):
        assert canon_lang(i) == i
        assert canon_lang('_'.join(i.split('-'))) == i
        assert canon_lang(i.lower()) == i
        assert canon_lang(i.upper()) == i
        assert canon_lang(i.title()) == i
    pass
test()
