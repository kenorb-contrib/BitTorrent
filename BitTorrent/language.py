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

# http://people.w3.org/rishida/names/languages.html

language_names = {
    'af'   :u'Afrikaans'            ,    'bg'   :u'Български'            ,
    'da'   :u'Dansk'                ,    'ca'   :u'Català'               ,
    'cs'   :u'Čeština'              ,    'de'   :u'Deutsch'              ,
    'en'   :u'English'              ,    'es'   :u'Español'              ,
    'es_MX':u'Español de Mexico '   ,    'fr'   :u'Français'             ,
    'el'   :u'Ελληνικά'             ,    'he'   :u'עברית'                ,
    'hu'   :u'Magyar'               ,    'it'   :u'Italiano'             ,
    'is'   :u'Íslenska'             ,    'ja'   :u'日本語'            ,
    'ko'   :u'한국어'            ,'nl'   :u'Nederlands'           ,
    'nb_NO':u'Norsk bokmål'         ,    'pl'   :u'Polski'               ,
    'pt'   :u'Português'            ,    'pt_BR':u'Português do Brasil'  ,
    'ro'   :u'Română'               ,    'ru'   :u'Русский'              ,
    'sk'   :u'Slovenský'            ,    'sl'   :u'Slovensko'            ,
    'sv'   :u'Svenska'              ,    'tr'   :u'Türkçe'               ,
    'vi'   :u'Tiê?ng Viê?t'           ,
    'zh_CN':u'简体中文'               , # Simplified
    'zh_TW':u'繁體中文'               , # Traditional
    }

unfinished_language_names = {
    'ar'   :u'العربية'       ,    'bs'   :u'Bosanski'             ,
    'eo'   :u'Esperanto'            ,    'eu'   :u'Euskara'              ,
    'et'   :u'Eesti'                ,    'fi'   :u'Suomi'                ,
    'fa'   :u'فارسی'                ,    'ga'   :u'Gaeilge'              ,
    'gl'   :u'Galego'               ,    'hr'   :u'Hrvatski'             ,
    'hy'   :u'Հայերեն'       ,    'in'   :u'Bahasa indonesia'     ,
    'ka'   :u'ქართული ენა',    'lt'   :u'Lietuvių'        ,
    'ms'   :u'Bahasa melayu'        ,    'ml'   :u'Malayalam'            ,
    'sq'   :u'Shqipe'                ,    'th'   :u'ภาษาไทย'              ,
    'tlh'  :u'tlhIngan-Hol'         ,    'uk'   :u'Українська'           ,
    'hi'   :u'हिंदी'  	                ,    'cy'   :u'Cymraeg'              ,
    'nn_NO':u'Norsk Nynorsk'        ,    'te'   :u'	తెలుగు'             ,
    }

#language_names.update(unfinished_language_names)
languages = language_names.keys()
languages.sort()

# windows codepage to locale mapping
locale_sucks = {
    0x0436: "af",       # Afrikaans
    0x3801: "ar_ae",    # Arabic - United Arab Emirates
    0x3C01: "ar_bh",    # Arabic - Bahrain
    0x1401: "ar_dz",    # Arabic - Algeria
    0x0C01: "ar_eg",    # Arabic - Egypt
    0x0801: "ar_iq",    # Arabic - Iraq
    0x2C01: "ar_jo",    # Arabic - Jordan
    0x3401: "ar_kw",    # Arabic - Kuwait
    0x3001: "ar_lb",    # Arabic - Lebanon
    0x1001: "ar_ly",    # Arabic - Libya
    0x1801: "ar_ma",    # Arabic - Morocco
    0x2001: "ar_om",    # Arabic - Oman
    0x4001: "ar_qa",    # Arabic - Qatar
    0x0401: "ar_sa",    # Arabic - Saudi Arabia
    0x2801: "ar_sy",    # Arabic - Syria
    0x1C01: "ar_tn",    # Arabic - Tunisia
    0x2401: "ar_ye",    # Arabic - Yemen
    0x082C: "az_az",    # Azeri - Cyrillic
    0x0423: "be",       # Belarusian
    0x0402: "bg",       # Bulgarian
    0x0403: "ca",       # Catalan
    0x0405: "cs",       # Czech
    0x0406: "da",       # Danish
    0x0007: "de",       # German
    0x0C07: "de_at",    # German - Austria
    0x0807: "de_ch",    # German - Switzerland
    0x0407: "de_de",    # German - Germany
    0x1407: "de_li",    # German - Liechtenstein
    0x1007: "de_lu",    # German - Luxembourg
    0x0408: "el",       # Greek
    0x0C09: "en_au",    # English - Australia
    0x2809: "en_bz",    # English - Belize
    0x1009: "en_ca",    # English - Canada
    0x2409: "en_cb",    # English - Carribbean
    0x0809: "en_gb",    # English - United Kingdom
    0x1809: "en_ie",    # English - Ireland
    0x2009: "en_jm",    # English - Jamaica
    0x1409: "en_nz",    # English - New Zealand
    0x3409: "en_ph",    # English - Phillippines
    0x2C09: "en_tt",    # English - Trinidad
    0x0409: "en_us",    # English - United States
    0x1C09: "en_za",    # English - South Africa
    0x000A: "es",       # Spanish (added)
    0x2C0A: "es_ar",    # Spanish - Argentina
    0x400A: "es_bo",    # Spanish - Bolivia
    0x340A: "es_cl",    # Spanish - Chile
    0x240A: "es_co",    # Spanish - Colombia
    0x140A: "es_cr",    # Spanish - Costa Rica
    0x1C0A: "es_do",    # Spanish - Dominican Republic
    0x300A: "es_ec",    # Spanish - Ecuador
    0x040a: "es_es",    # Spanish - Spain
    0x100A: "es_gt",    # Spanish - Guatemala
    0x480A: "es_hn",    # Spanish - Honduras
    0x080A: "es_mx",    # Spanish - Mexico
    0x4C0A: "es_ni",    # Spanish - Nicaragua
    0x180A: "es_pa",    # Spanish - Panama
    0x280A: "es_pe",    # Spanish - Peru
    0x500A: "es_pr",    # Spanish - Puerto Rico
    0x3C0A: "es_py",    # Spanish - Paraguay
    0x440A: "es_sv",    # Spanish - El Salvador
    0x380A: "es_uy",    # Spanish - Uruguay
    0x200A: "es_ve",    # Spanish - Venezuela
    0x0425: "et",       # Estonian
    0x0009: "en",       # English (added)
    0x042D: "eu",       # Basque
    0x0429: "fa",       # Farsi
    0x040B: "fi",       # Finnish
    0x0438: "fo",       # Faroese
    0x000C: "fr",       # French (added) 
    0x080C: "fr_be",    # French - Belgium
    0x0C0C: "fr_ca",    # French - Canada
    0x100C: "fr_ch",    # French - Switzerland
    0x040C: "fr_fr",    # French - France
    0x140C: "fr_lu",    # French - Luxembourg
    0x043C: "gd",       # Gaelic - Scotland
    0x083C: "gd_ie",    # Gaelic - Ireland
    0x040D: "he",       # Hebrew
    0x0439: "hi",       # Hindi
    0x041A: "hr",       # Croatian
    0x040E: "hu",       # Hungarian
    0x042B: "hy",       # Armenian
    0x0421: "id",       # Indonesian
    0x040F: "is",       # Icelandic
    0x0010: "it",       # Italian (added)
    0x0810: "it_ch",    # Italian - Switzerland
    0x0410: "it_it",    # Italian - Italy
    0x0411: "ja",       # Japanese
    0x0412: "ko",       # Korean
    0x0427: "lt",       # Lithuanian
    0x0426: "lv",       # Latvian
    0x042F: "mk",       # FYRO Macedonian
    0x044E: "mr",       # Marathi
    0x083E: "ms_bn",    # Malay - Brunei
    0x043E: "ms_my",    # Malay - Malaysia
    0x043A: "mt",       # Maltese
    0x0013: "nl",       # Dutch (added)
    0x0813: "nl_be",    # Dutch - Belgium
    0x0413: "nl_nl",    # Dutch - The Netherlands
    0x0814: "no_no",    # Norwegian - Nynorsk
    0x0414: "nb_no",    # Norwegian - Bokmal (?)
    0x0415: "pl",       # Polish
    0x0016: "pt",       # Portuguese (added)
    0x0416: "pt_br",    # Portuguese - Brazil
    0x0816: "pt_pt",    # Portuguese - Portugal
    0x0417: "rm",       # Raeto-Romance
    0x0418: "ro",       # Romanian - Romania
    0x0818: "ro_mo",    # Romanian - Moldova
    0x0419: "ru",       # Russian
    0x0819: "ru_mo",    # Russian - Moldova
    0x044F: "sa",       # Sanskrit
    0x042E: "sb",       # Sorbian
    0x041B: "sk",       # Slovak
    0x0424: "sl",       # Slovenian
    0x041C: "sq",       # Albanian
    0x081A: "sr_sp",    # Serbian - Latin
    0x001D: "sv",       # Swedish (added)
    0x081D: "sv_fi",    # Swedish - Finland
    0x041D: "sv_se",    # Swedish - Sweden
    0x0441: "sw",       # Swahili
    0x0430: "sx",       # Sutu
    0x0449: "ta",       # Tamil
    0x041E: "th",       # Thai
    0x0432: "tn",       # Setsuana
    0x041F: "tr",       # Turkish
    0x0431: "ts",       # Tsonga
    0X0444: "tt",       # Tatar
    0x0422: "uk",       # Ukrainian
    0x0420: "ur",       # Urdu
    0x0443: "uz_uz",    # Uzbek - Latin
    0x042A: "vi",       # Vietnamese
    0x0434: "xh",       # Xhosa
    0x043D: "yi",       # Yiddish
    0x0804: "zh_cn",    # Chinese - China
    0x0C04: "zh_hk",    # Chinese - Hong Kong S.A.R.
    0x1404: "zh_mo",    # Chinese - Macau S.A.R
    0x1004: "zh_sg",    # Chinese - Singapore
    0x0404: "zh_tw",    # Chinese - Taiwan
    0x0435: "zu",       # Zulu
}

if __name__ == '__main__':
    from sets import Set
    internal = Set([x.lower() for x in languages])
    windows = Set(locale_sucks.values())
    if not windows.issuperset(internal):
        diff = list(internal.difference(windows))
        diff.sort()
        print diff
