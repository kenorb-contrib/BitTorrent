import sys
import os
from BitTorrent import version, app_name, languages, language_names
from BitTorrent.language import locale_sucks

NSIS_DIR = "C:\\Program Files\\NSIS"

if not os.path.exists(NSIS_DIR):
    raise Exception("Please set NSIS_DIR in winprepnsi.py!")

version_str = version
if int(version_str[2]) % 2:
    version_str = version_str + '-Beta'

nsis_language_names = {
    'af'    :'Afrikaans',
    'bg'    :'Bulgarian',
    'ca'    :'Catalan',
    'cs'    :'Czech',
    'da'    :'Danish',
    'de'    :'German',
    'en'    :'English',
    'es'    :'Spanish',
    'es_MX' :'SpanishMX',
    'fr'    :'French',
    'el'    :'Greek',
    'hu'    :'Hungarian',
    'he'    :'Hebrew',
    'it'    :'Italian',
    'is'    :'Icelandic',
    'ja'    :'Japanese',
    'ko'    :'Korean',
    'nb_NO' :'Norwegian',
    'nl'    :'Dutch',
    'pl'    :'Polish',
    'pt'    :'Portuguese',
    'pt_BR' :'PortugueseBR',
    'ro'    :'Romanian',
    'ru'    :'Russian',
    'sk'    :'Slovak',
    'sl'    :'Slovenian',
    'sv'    :'Swedish',
    'tr'    :'Turkish',
    'vi'    :'Vietnamese',
    'zh_CN' :'TradChinese',
    'zh_TW' :'SimpChinese',    
    }

    

f = open(sys.argv[1])
b = f.read()
f.close()
b = b.replace("%VERSION%", version_str)
b = b.replace("%APP_NAME%", app_name)

found_langs = {}
lang_macros = ""
for l in languages:
    lang = nsis_language_names[l]
    nlf = os.path.join(NSIS_DIR, "Contrib\\Language files\\%s.nlf" % lang)
    nsh = os.path.join(NSIS_DIR, "Contrib\\Modern UI\\Language files\\%s.nsh" % lang)
    if os.path.exists(nlf) and os.path.exists(nsh):
        lang_macros += ('  !insertmacro MUI_LANGUAGE "%s"\r\n' % lang)
        found_langs[l] = lang
    else:
        lcid = None
        for id, code in locale_sucks.iteritems():
            if code.lower() == l.lower():
                lcid = id
            
        print "Creating a template for", lang, lcid
        f = open(nlf, 'w')
        template = open("windows_installer\\template.nlf", 'r')
        template_str = template.read()
        template.close()
        t = (template_str % {'id':lcid})
        f.write(t)
        f.close()

        f = open(nsh, 'w')
        template = open("windows_installer\\template.nsh", 'r')
        template_str = template.read()
        template.close()
        t = (template_str % {'name':lang, 'id':lcid})
        f.write(t)
        f.close()
             

        lang_macros += ('  !insertmacro MUI_LANGUAGE "%s"\r\n' % lang)
        found_langs[l] = lang

b = b.replace("%LANG_MACROS%", lang_macros)

f = open(sys.argv[2], "w")
f.write(b)
f.close()

