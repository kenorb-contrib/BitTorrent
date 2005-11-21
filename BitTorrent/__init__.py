# -*- coding: UTF-8 -*-
# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

app_name = 'BitTorrent'
version = '4.2.0'

URL = 'http://www.bittorrent.com/'
DONATE_URL = URL + 'donate.html'
FAQ_URL = URL + 'FAQ.html'
HELP_URL = URL + 'documentation.html'
SEARCH_URL = 'http://search.bittorrent.com/search.jsp?client=%(client)s&query=%(query)s'

import sys
assert sys.version_info >= (2, 2, 1), _("Python 2.2.1 or newer required")
import os
import time

branch = None
if os.access('.cdv', os.F_OK):
    branch = os.path.split(os.path.realpath(os.path.split(sys.argv[0])[0]))[1]

from BitTorrent.platform import get_home_dir, is_frozen_exe

# http://people.w3.org/rishida/names/languages.html
language_names = {
    'af'   :u'Afrikaans'            ,    'bg'   :u'Български'            ,
    'da'   :u'Dansk'                ,    'ca'   :u'Català'               ,
    'cs'   :u'Čeština'              ,    'de'   :u'Deutsch'              ,
    'en'   :u'English'              ,    'es'   :u'Español'              ,
    'es_MX':u'Español de Mexico '   ,    'fr'   :u'Français'             ,
    'gr'   :u'Ελληνικά'             ,    'hu'   :u'Magyar'               ,
    'it'   :u'Italiano'             ,    'nl'   :u'Nederlands'           ,
    'nb_NO':u'Norsk bokmål'         ,    'pl'   :u'Polski'               ,
    'pt'   :u'Português'            ,    'pt_BR':u'Português do Brasil'  ,
    'ro'   :u'Română'               ,    'ru'   :u'Русский'              ,
    'sk'   :u'Slovenský'            ,    'sl'   :u'Slovensko'            ,
    'sv'   :u'Svenska'              ,    'tr'   :u'Türkçe'               ,
    'vi'   :u'Tiếng Việt'           ,
    'zh_CN':u'简体中文'               , # Simplified
    'zh_TW':u'繁體中文'               , # Traditional
    }

unfinished_language_names = {
    'ar'   :u'العربية'       ,    'bs'   :u'Bosanski'             ,
    'eo'   :u'Esperanto'            ,    'eu'   :u'Euskara'              ,
    'et'   :u'Eesti'                ,    'fi'   :u'Suomi'                ,
    'ga'   :u'Gaeilge'              ,    'gl'   :u'Galego'               ,
    'he_IL':u'עברית'                ,    'hr'   :u'Hrvatski'             ,
    'hy'   :u'Հայերեն'       ,    'in'   :u'Bahasa indonesia'     ,
    'ja'   :u'日本語'            ,    'ka'   :u'ქართული ენა',
    'ko'   :u'한국어'            ,    'lt'   :u'Lietuvių'        ,
    'ms'   :u'Bahasa melayu'        ,    'ml'   :u'Malayalam'            ,
    'sq'   :u'Shqipe'                ,    'th'   :u'ภาษาไทย'              ,
    'tlh'  :u'tlhIngan-Hol'         ,    'uk'   :u'Українська'           ,
    'hi'   :u'हिन्दी'                  ,    'cy'   :u'Cymraeg'              ,
    'is'   :u'Íslenska'             ,    'nn_NO':u'Norsk Nynorsk'        ,
    'te'   :u'తెలుగు'             ,
    }

#language_names.update(unfinished_language_names)

languages = language_names.keys()
languages.sort()

if os.name == 'posix':
    if os.uname()[0] == "Darwin":
        from BitTorrent.platform import install_translation
        install_translation()

# hackery to get around bug in py2exe that tries to write log files to
# application directories, which may not be writable by non-admin users
if is_frozen_exe:
    baseclass = sys.stderr.__class__
    class Stderr(baseclass):
        logroot = get_home_dir()

        if logroot is None:
            logroot = os.path.splitdrive(sys.executable)[0]
            if logroot[-1] != os.sep:
                logroot += os.sep
        logname = os.path.splitext(os.path.split(sys.executable)[1])[0] + '_errors.log'
        logpath = os.path.join(logroot, logname)

        def __init__(self):        
            self.just_wrote_newline = True
        
        def write(self, text, alert=None, fname=logpath):
            output = text

            if self.just_wrote_newline and not text.startswith('[%s ' % version):
                output = '[%s %s] %s' % (version, time.strftime('%Y-%m-%d %H:%M:%S'), text)
                
            if 'GtkWarning' not in text:
                baseclass.write(self, output, fname=fname)

            if output[-1] == '\n':
                self.just_wrote_newline = True
            else:
                self.just_wrote_newline = False
                
    sys.stderr = Stderr()

del sys, get_home_dir, is_frozen_exe

INFO = 0
WARNING = 1
ERROR = 2
CRITICAL = 3

class BTFailure(Exception):
    pass
        
class BTShutdown(BTFailure):
    pass

