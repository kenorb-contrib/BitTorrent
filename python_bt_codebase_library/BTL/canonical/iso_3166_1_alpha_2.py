#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
ISO 3166-1 Alpha-2 Officially Assigned Code Elements list

excerpted from:
http://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
http://en.wikipedia.org/wiki/ISO_3166-3
'''

current = '''
AD Andorra
AE United Arab Emirates
AF Afghanistan
AG Antigua and Barbuda
AI Anguilla [AI previously represented French Territory of the Afars and the Issas]
AL Albania
AM Armenia
AN Netherlands Antilles
AO Angola
AQ Antarctica [defined as territory south of latitude 60°S]
AR Argentina
AS American Samoa
AT Austria
AU Australia [including Ashmore and Cartier Islands and Coral Sea Islands]
AW Aruba
AX Åland Islands
AZ Azerbaijan
BA Bosnia and Herzegovina
BB Barbados
BD Bangladesh
BE Belgium
BF Burkina Faso
BG Bulgaria
BH Bahrain
BI Burundi
BJ Benin
BM Bermuda
BN Brunei Darussalam
BO Bolivia
BR Brazil
BS Bahamas
BT Bhutan
BV Bouvet Island
BW Botswana
BY Belarus
BZ Belize
CA Canada
CC Cocos (Keeling) Islands
CD Congo, the Democratic Republic of the [formerly Zaire]
CF Central African Republic
CG Congo [officially the Republic of the Congo]
CH Switzerland [Latin: Confoederatio Helvetica]
CI Côte d\'Ivoire [also known as Ivory Coast]
CK Cook Islands
CL Chile
CM Cameroon
CN China [officially the People\'s Republic of China]
CO Colombia
CR Costa Rica
CU Cuba
CV Cape Verde
CX Christmas Island
CY Cyprus
CZ Czech Republic
DE Germany [German: Deutschland]
DJ Djibouti
DK Denmark
DM Dominica
DO Dominican Republic
DZ Algeria
EC Ecuador
EE Estonia
EG Egypt
EH Western Sahara [formerly Spanish Sahara]
ER Eritrea
ES Spain [including Canary Islands, Ceuta and Melilla - Spanish: España]
ET Ethiopia
FI Finland
FJ Fiji
FK Falkland Islands (Malvinas)
FM Micronesia, Federated States of
FO Faroe Islands
FR France
GA Gabon
GB United Kingdom [including Isle of Man and Channel Islands (Guernsey and Jersey)]
GD Grenada
GE Georgia [GE previously represented the Gilbert and Ellice Islands]
GF French Guiana
GH Ghana
GI Gibraltar
GL Greenland
GM Gambia
GN Guinea
GP Guadeloupe
GQ Equatorial Guinea
GR Greece
GS South Georgia and the South Sandwich Islands
GT Guatemala
GU Guam
GW Guinea-Bissau
GY Guyana
HK Hong Kong [officially the Hong Kong Special Administrative Region of the People\'s Republic of China]
HM Heard Island and McDonald Islands
HN Honduras
HR Croatia [Croat: Hrvatska]
HT Haiti
HU Hungary
ID Indonesia
IE Ireland
IL Israel
IN India
IO British Indian Ocean Territory [including Diego Garcia]
IQ Iraq
IR Iran, Islamic Republic of
IS Iceland
IT Italy
JM Jamaica
JO Jordan
JP Japan
KE Kenya
KG Kyrgyzstan
KH Cambodia
KI Kiribati
KM Comoros
KN Saint Kitts and Nevis
KP Korea, Democratic People\'s Republic of [i.e., North Korea]
KR Korea, Republic of [i.e., South Korea]
KW Kuwait
KY Cayman Islands
KZ Kazakhstan
LA Lao People\'s Democratic Republic
LB Lebanon
LC Saint Lucia
LI Liechtenstein
LK Sri Lanka
LR Liberia
LS Lesotho
LT Lithuania
LU Luxembourg
LV Latvia
LY Libyan Arab Jamahiriya
MA Morocco
MC Monaco
MD Moldova, Republic of
ME Montenegro, Republic of
MG Madagascar
MH Marshall Islands
MK Macedonia, the Former Yugoslav Republic of
ML Mali
MM Myanmar [formerly Burma]
MN Mongolia
MO Macao
MP Northern Mariana Islands
MQ Martinique
MR Mauritania
MS Montserrat
MT Malta
MU Mauritius
MV Maldives
MW Malawi
MX Mexico
MY Malaysia
MZ Mozambique
NA Namibia
NC New Caledonia
NE Niger
NF Norfolk Island
NG Nigeria
NI Nicaragua
NL Netherlands
NO Norway
NP Nepal
NR Nauru
NU Niue
NZ New Zealand
OM Oman
PA Panama
PE Peru
PF French Polynesia [including Clipperton Island]
PG Papua New Guinea
PH Philippines
PK Pakistan
PL Poland
PM Saint Pierre and Miquelon
PN Pitcairn
PR Puerto Rico
PS Palestinian Territory, Occupied [i.e., West Bank and Gaza Strip]
PT Portugal
PW Palau
PY Paraguay
QA Qatar
RE Réunion
RO Romania
RS Serbia, Republic of
RU Russian Federation
RW Rwanda
SA Saudi Arabia
SB Solomon Islands
SC Seychelles
SD Sudan
SE Sweden
SG Singapore
SH Saint Helena [including Ascension Island and Tristan da Cunha]
SI Slovenia
SJ Svalbard and Jan Mayen [consisting of Svalbard and Jan Mayen]
SK Slovakia [SK previously represented Sikkim]
SL Sierra Leone
SM San Marino
SN Senegal
SO Somalia
SR Suriname
ST Sao Tome and Principe
SV El Salvador
SY Syrian Arab Republic
SZ Swaziland
TC Turks and Caicos Islands
TD Chad [French: Tchad]
TF French Southern Territories
TG Togo
TH Thailand
TJ Tajikistan
TK Tokelau
TL Timor-Leste [also known as East Timor]
TM Turkmenistan
TN Tunisia
TO Tonga
TR Turkey
TT Trinidad and Tobago
TV Tuvalu
TW Taiwan, Province of China [administered by the Republic of China]
TZ Tanzania, United Republic of
UA Ukraine
UG Uganda
UM United States Minor Outlying Islands [consisting of Baker Island, Howland Island, Jarvis Island, Johnston Atoll, Kingman Reef, Midway Atoll, Navassa Island, Palmyra Atoll, Wake Island]
US United States
UY Uruguay
UZ Uzbekistan
VA Holy See (Vatican City State)
VC Saint Vincent and the Grenadines
VE Venezuela
VG Virgin Islands, British
VI Virgin Islands, U.S.
VN Viet Nam
VU Vanuatu
WF Wallis and Futuna
WS Samoa [formerly Western Samoa]
YE Yemen
YT Mayotte
ZA South Africa [Dutch: Zuid-Afrika]
ZM Zambia
ZW Zimbabwe
'''

private = '''
AA Reserved for private use
QM Reserved for private use
QN Reserved for private use
QO Reserved for private use
QP Reserved for private use
QQ Reserved for private use
QR Reserved for private use
QS Reserved for private use
QT Reserved for private use
QU Reserved for private use
QV Reserved for private use
QW Reserved for private use
QX Reserved for private use
QY Reserved for private use
QZ Reserved for private use
XA Reserved for private use
XB Reserved for private use
XC Reserved for private use
XD Reserved for private use
XE Reserved for private use
XF Reserved for private use
XG Reserved for private use
XH Reserved for private use
XI Reserved for private use
XJ Reserved for private use
XK Reserved for private use
XL Reserved for private use
XM Reserved for private use
XN Reserved for private use
XO Reserved for private use
XP Reserved for private use
XQ Reserved for private use
XR Reserved for private use
XS Reserved for private use
XT Reserved for private use
XU Reserved for private use
XV Reserved for private use
XW Reserved for private use
XX Reserved for private use
XY Reserved for private use
XZ Reserved for private use
ZZ Reserved for private use
'''

transitional_reservations = '''
BU Burma (now Myanmar, MM)
NT Neutral Zone, partitioned between Saudi Arabia and Iraq in 1983.
SF Finland (now FI)
SU Union of Soviet Socialist Republics (several successor codes; still used as ccTLD)
TP East Timor (now Timor-Leste, TL)
YU Yugoslavia (now Serbia and Montenegro, CS)
ZR Zaire (now Democratic Republic of the Congo, CD)
'''

indeterminate_reservations = '''
DY Benin [Code notified to United Nations Secretary-General under 1949 and/or 1968 Road Traffic Conventions]
EW Estonia [Code notified to United Nations Secretary-General under 1949 and/or 1968 Road Traffic Conventions]
FL Liechtenstein [Code in use for road transport purposes, but not notified to United Nations Secretary-General under 1949 Road Traffic Convention]
JA Jamaica [Code under 1949 Road Traffic Convention]
LF Libya Fezzan [Code in use for road transport purposes, but not notified to United Nations Secretary-General under 1949 Road Traffic Convention]
LT Libya Tripoli [Code in use for road transport purposes, but not notified to United Nations Secretary-General under 1949 Road Traffic Convention] (Note that LT has since been reassigned to Lithuania.)
ME Western Sahara [Code in use for road transport purposes, but not notified to United Nations Secretary-General under 1949 Road Traffic Convention]
PI Philippines [Code under 1949 Road Traffic Convention]
RA Argentina [Code under 1949 Road Traffic Convention]
RB This code is in use to refer to both Bolivia and Botswana: Bolivia [Code in use for road transport purposes, but not notified to United Nations Secretary-General under 1949 Road Traffic Convention]; Botswana [Code under 1949 Road Traffic Convention]
RC China (People\'s Republic of China) [Code under 1949 Road Traffic Convention]
RH Haiti [Code notified to United Nations Secretary-General under 1949 and/or 1968 Road Traffic Conventions]
RI Indonesia [Code under 1949 Road Traffic Convention]
RL Lebanon [Code under 1949 Road Traffic Convention]
RM Madagascar [Code under 1949 Road Traffic Convention]
RN Niger [Code under 1968 Road Traffic Convention]
RP Philippines [Code under 1968 Road Traffic Convention]
RU Burundi [Code in use for road transport purposes, but not notified to United Nations Secretary-General under 1949 Road Traffic Convention] (Note that RU has since been reassigned to the Russian Federation.)
WG Grenada [Code notified to United Nations Secretary-General under 1949 and/or 1968 Road Traffic Conventions]
WL Saint Lucia [Code notified to United Nations Secretary-General under 1949 and/or 1968 Road Traffic Conventions]
WV Saint Vincent [Code notified to United Nations Secretary-General under 1949 and/or 1968 Road Traffic Conventions]
YV Venezuela [Code notified to United Nations Secretary-General under 1949 and/or 1968 Road Traffic Conventions]
'''

exceptional_reservations = '''
AC Ascension Island — Reserved on request of UPU (also used as ccTLD)
CP Clipperton Island — Reserved on request of ITU
DG Diego Garcia — Reserved on request of ITU
EA Ceuta and Melilla — Reserved on request of WCO to represent area outside EU customs territory
EU European Union — Originally requested by ISO 4217 MA to provide country code for Euro; later extended for use in ISO 6166 International Securities Identification Numbering (ISIN) system; later extended by ISO 3166 MA for use for any purposes for which code EU required; also used as ccTLD
FX Metropolitan France — Reserved on request of France
GG Guernsey — Reserved on request of UPU; also used as ccTLD
IC Canary Islands — Reserved on request of WCO to represent area outside EU customs territory
IM Isle of Man — Reserved on request of UPU, also used as ccTLD
JE Jersey — Reserved on request of UPU, also used as ccTLD
TA Tristan da Cunha — Reserved on request of UPU
UK United Kingdom — Reserved on request of the United Kingdom, to prevent any other country from using code UK; also used as ccTLD
'''

wipo_reservations = '''
AP African Regional Intellectual Property Organization
BX Benelux Trademarks and Design Offices
EF Union of Countries under the European Community Patent Convention
EM European Trademark Office
EP European Patent Organisation
GC Patent Office of the Cooperation Council for the Arab States of the Gulf (GCC)
IB International Bureau of WIPO
OA Organisation Africaine de la Propriété Intellectuelle or African Intellectual Property Organization
WO World Intellectual Property Organization
'''

reserved = exceptional_reservations.strip() + '\n' + wipo_reservations.strip()

withdrawn = '''
AI Withdrawn 1977; formerly French Territory of the Afars and the Issas [Replaced by DJ (for Djibouti). Note that AI has since been reassigned to Anguilla.]
BQ Withdrawn 1979; formerly British Antarctic Territory [Now covered by AQ (Antarctica).]
BU Withdrawn 1989; formerly Burma [Replaced by MM (for Myanmar).]
CS Withdrawn 2006; formerly Serbia and Montenegro [formerly Yugoslavia - Serbian: Srbija i Crna Gora - CS previously represented Czechoslovakia which was withdrawn 1993 and replaced by CZ (Czech Republic) and SK (Slovakia)]
CT Withdrawn 1984; formerly Canton and Enderbury Islands [Now covered by KI (Kiribati).]
DD Withdrawn 1990; formerly East Germany [Now covered by DE (Germany).]
DY Withdrawn 1977; formerly Dahomey [Replaced by BJ (for Benin).]
FQ Withdrawn 1979; formerly French Southern and Antarctic Territories [Now covered by AQ (Antarctica) and TF (French Southern Territories).]
FX Withdrawn 1997; formerly Metropolitan France [Now covered by FR (France).]
GE Withdrawn 1979; formerly Gilbert and Ellice Islands [Now covered by KI (Kiribati) and TV (Tuvalu). Note that GE has since been reassigned to Georgia.]
HV Withdrawn 1984; formerly Upper Volta (Haute-Volta) [Replaced by BF (for Burkina Faso).]
JT Withdrawn 1986; formerly Johnston Island [Now covered by UM (United States Minor Outlying Islands).]
MI Withdrawn 1986; formerly Midway Atoll [Now covered by UM (United States Minor Outlying Islands).]
NH Withdrawn 1980; formerly New Hebrides [Replaced by VU (for Vanuatu).]
NQ Withdrawn 1983; formerly Queen Maud Land [Now covered by AQ (Antarctica).]
NT Withdrawn 1993; formerly Neutral Zone [Now covered by IQ (Iraq) and SA (Saudi Arabia).]
PC Withdrawn 1986; formerly Trust Territory of the Pacific Islands [Replaced by FM (Federated States of Micronesia), MH (Marshall Islands), MP (Northern Mariana Islands) and PW (Palau).]
PU Withdrawn 1986; formerly U.S. Miscellaneous Pacific Islands [Now covered by UM (United States Minor Outlying Islands).]
PZ Withdrawn 1980; formerly Panama Canal Zone [Now covered by PA (Panama).]
RH Withdrawn 1980; formerly Rhodesia [Replaced by ZW (for Zimbabwe).]
SK Withdrawn 1975; formerly Sikkim [Now covered by IN (India). Note that SK has since been reassigned to Slovakia.]
SU Withdrawn 1992; formerly Soviet Union [Replaced by AM (Armenia), AZ (Azerbaijan), BY (Belarus), EE (Estonia), GE (Georgia), KG (Kyrgyzstan), KZ (Kazakhstan), LT (Lithuania), LV (Latvia), MD (Moldova), RU (Russia), TJ (Tajikistan), TM (Turkmenistan), UA (Ukraine) and UZ (Uzbekistan), of which BY and UA already existed. SU is still in use as a top-level domain.]
TP Withdrawn 2002; formerly East Timor [Replaced by TL (for Timor-Leste) after becoming independent. TP is still in use as a top-level domain.]
VD Withdrawn 1977; formerly Democratic Republic of Vietnam, i.e. North Vietnam [Now covered by VN (Viet Nam).]
WK Withdrawn 1986; formerly Wake Island [Now covered by UM (United States Minor Outlying Islands).]
YD Withdrawn 1990; formerly South Yemen [Now covered by YE (Yemen).]
YU Withdrawn 2003; formerly Yugoslavia [Replaced by CS (for Serbia and Montenegro; Srbija i Crna Gora). YU is still in use as a top-level domain.]
ZR Withdrawn 1997; formerly Zaire [Replaced by CD (for Democratic Republic of the Congo).]
'''
