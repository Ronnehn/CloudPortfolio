import math
import re
import numpy as np
import pandas as pd
import scipy.optimize as opt
import configparser
from richtskills_data import RICHTSKILLS_DEFAULT, RICHTSKILLS_29, estimate_age_richtskills

# ==============================================================================
# 1. CORE CONSTANTS & DICTIONARIES
# ==============================================================================
FLAG_MAP = {
    'Netherlands': '🇳🇱', 'Nederland': '🇳🇱', 'Belgium': '🇧🇪', 'België': '🇧🇪',
    'Germany': '🇩🇪', 'Deutschland': '🇩🇪', 'France': '🇫🇷', 'Italy': '🇮🇹', 'Italia': '🇮🇹',
    'Spain': '🇪🇸', 'España': '🇪🇸', 'Portugal': '🇵🇹', 'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
    'Wales': '🏴󠁧󠁢󠁷󠁬󠁳󠁿', 'Ireland': '🇮🇪', 'Northern Ireland': '🇬🇧', 'Sweden': '🇸🇪', 'Sverige': '🇸🇪',
    'Norway': '🇳🇴', 'Norge': '🇳🇴', 'Denmark': '🇩🇰', 'Danmark': '🇩🇰', 'Finland': '🇫🇮', 'Suomi': '🇫🇮',
    'Iceland': '🇮🇸', 'Ísland': '🇮🇸', 'Poland': '🇵🇱', 'Polska': '🇵🇱', 'Turkey': '🇹🇷', 'Türkiye': '🇹🇷',
    'Brazil': '🇧🇷', 'Brasil': '🇧🇷', 'Argentina': '🇦🇷', 'Zambia': '🇿🇲', 'Zambië': '🇿🇲', 'Bangladesh': '🇧🇩', 'Sri Lanka': '🇱🇰', 'Ecuador': '🇪🇨', 'Uruguay': '🇺🇾', 'Chile': '🇨🇱',
    'Colombia': '🇨🇴', 'Peru': '🇵🇪', 'Mexico': '🇲🇽', 'USA': '🇺🇸', 'United States': '🇺🇸',
    'Canada': '🇨🇦', 'Australia': '🇦🇺', 'Switzerland': '🇨🇭', 'Schweiz': '🇨🇭', 'Austria': '🇦🇹',
    'Österreich': '🇦🇹', 'Czech Republic': '🇨🇿', 'Česká republika': '🇨🇿', 'Croatia': '🇭🇷',
    'Hrvatska': '🇭🇷', 'Serbia': '🇷🇸', 'Srbija': '🇷🇸', 'Romania': '🇷🇴', 'România': '🇷🇴',
    'Bulgaria': '🇧🇬', 'Greece': '🇬🇷', 'Hellas': '🇬🇷', 'Russia': '🇷🇺', 'Rossiya': '🇷🇺',
    'Ukraine': '🇺🇦', 'Ukraina': '🇺🇦', 'South Africa': '🇿🇦', 'Japan': '🇯🇵',
    'Nippon': '🇯🇵', 'South Korea': '🇰🇷', 'China': '🇨🇳'
}
# Every other Hattrick country: name -> ISO code (the flag is built from the code). Oceania has no flag of its own.
_ISO_FLAGS = {
    'Albania': 'AL', 'Algeria': 'DZ', 'Andorra': 'AD', 'Angola': 'AO', 'Armenia': 'AM', 'Azerbaijan': 'AZ', 'Bahrain': 'BH',
    'Barbados': 'BB', 'Belarus': 'BY', 'Belgium': 'BE', 'België': 'BE', 'Belize': 'BZ', 'Benin': 'BJ', 'Bolivia': 'BO',
    'Bosnia & Herzegovina': 'BA', 'Bosnia and Herzegovina': 'BA', 'Botswana': 'BW', 'Brunei': 'BN', 'Burkina Faso': 'BF',
    'Cambodia': 'KH', 'Cameroon': 'CM', 'Cape Verde': 'CV', 'Comoros': 'KM', 'Costa Rica': 'CR', "Côte d'Ivoire": 'CI',
    'Ivory Coast': 'CI', 'Cuba': 'CU', 'Curaçao': 'CW', 'Curacao': 'CW', 'Cyprus': 'CY', 'Czechia': 'CZ', 'DR Congo': 'CD',
    'Congo': 'CG', 'Dominican Republic': 'DO', 'Egypt': 'EG', 'El Salvador': 'SV', 'Equatorial Guinea': 'GQ', 'Estonia': 'EE',
    'Ethiopia': 'ET', 'Faroe Islands': 'FO', 'Georgia': 'GE', 'Ghana': 'GH', 'Grenada': 'GD', 'Guam': 'GU', 'Guatemala': 'GT',
    'Guinea': 'GN', 'Haiti': 'HT', 'Honduras': 'HN', 'Hong Kong': 'HK', 'Hungary': 'HU', 'Magyarország': 'HU', 'India': 'IN',
    'Indonesia': 'ID', 'Iran': 'IR', 'Iraq': 'IQ', 'Israel': 'IL', 'Jamaica': 'JM', 'Jordan': 'JO', 'Kazakhstan': 'KZ',
    'Kenya': 'KE', 'Kosovo': 'XK', 'Kuwait': 'KW', 'Kyrgyzstan': 'KG', 'Latvia': 'LV', 'Lebanon': 'LB', 'Liechtenstein': 'LI',
    'Lithuania': 'LT', 'Luxembourg': 'LU', 'Madagascar': 'MG', 'Malaysia': 'MY', 'Maldives': 'MV', 'Malta': 'MT',
    'Moldova': 'MD', 'Mongolia': 'MN', 'Montenegro': 'ME', 'Morocco': 'MA', 'Mozambique': 'MZ', 'Myanmar': 'MM', 'Nepal': 'NP',
    'Nicaragua': 'NI', 'Nigeria': 'NG', 'North Macedonia': 'MK', 'Macedonia': 'MK', 'Oman': 'OM', 'Pakistan': 'PK',
    'Palestine': 'PS', 'Panama': 'PA', 'Paraguay': 'PY', 'Philippines': 'PH', 'Puerto Rico': 'PR', 'Qatar': 'QA', 'Rwanda': 'RW',
    'Saint Vincent and the Grenadines': 'VC', 'San Marino': 'SM', 'São Tomé e Príncipe': 'ST', 'Sao Tome and Principe': 'ST',
    'Saudi Arabia': 'SA', 'Senegal': 'SN', 'Singapore': 'SG', 'Slovakia': 'SK', 'Slovensko': 'SK', 'Slovenia': 'SI',
    'Slovenija': 'SI', 'Suriname': 'SR', 'Syria': 'SY', 'Tahiti': 'PF', 'Taiwan': 'TW', 'Chinese Taipei': 'TW', 'Tanzania': 'TZ',
    'Thailand': 'TH', 'Trinidad & Tobago': 'TT', 'Trinidad and Tobago': 'TT', 'Tunisia': 'TN', 'Uganda': 'UG', 'United Arab Emirates': 'AE',
    'Uzbekistan': 'UZ', 'Venezuela': 'VE', 'Vietnam': 'VN', 'Yemen': 'YE', 'Zimbabwe': 'ZW', 'Libya': 'LY', 'Sudan': 'SD',
    'Mali': 'ML', 'Gabon': 'GA', 'Namibia': 'NA', 'Malawi': 'MW', 'Afghanistan': 'AF', 'Laos': 'LA', 'Bhutan': 'BT', 'Fiji': 'FJ',
    'New Zealand': 'NZ', 'Belgium ': 'BE', 'Germany': 'DE', 'Deutschland': 'DE', 'Netherlands': 'NL', 'Nederland': 'NL',
    'France': 'FR', 'Italy': 'IT', 'Italia': 'IT', 'Gibraltar': 'GI', 'Aruba': 'AW', 'Bermuda': 'BM', 'Antigua and Barbuda': 'AG',
    'Saint Lucia': 'LC', 'Dominica': 'DM', 'Bahamas': 'BS', 'Guyana': 'GY', 'Sierra Leone': 'SL', 'Liberia': 'LR', 'Togo': 'TG',
    'Niger': 'NE', 'Chad': 'TD', 'Mauritius': 'MU', 'Seychelles': 'SC', 'Eswatini': 'SZ', 'Lesotho': 'LS', 'Gambia': 'GM',
    'Mauritania': 'MR', 'Somalia': 'SO', 'Eritrea': 'ER', 'Djibouti': 'DJ', 'Burundi': 'BI', 'Central African Republic': 'CF',
    'South Sudan': 'SS', 'Tajikistan': 'TJ', 'Turkmenistan': 'TM', 'North Korea': 'KP', 'Korea': 'KR', 'Macau': 'MO',
    'Papua New Guinea': 'PG', 'Samoa': 'WS', 'Tonga': 'TO', 'Solomon Islands': 'SB', 'Vanuatu': 'VU', 'New Caledonia': 'NC',
    'Monaco': 'MC', 'Vatican': 'VA', 'Timor-Leste': 'TL',
}
for _n, _c in _ISO_FLAGS.items():
    FLAG_MAP.setdefault(_n.strip(), ''.join(chr(0x1F1E6 + ord(ch) - 65) for ch in _c))
FLAG_MAP.setdefault('Oceania', '🌏')
COUNTRY_LIST = sorted(list(set(FLAG_MAP.keys())))

# Maps local-language nationality strings to canonical English name
# so 'Nederland' and 'Netherlands' show as one entry in dropdowns
NATIONALITY_CANONICAL = {
    'Nederland': 'Netherlands', 'België': 'Belgium', 'Deutschland': 'Germany',
    'Italia': 'Italy', 'España': 'Spain', 'Sverige': 'Sweden', 'Norge': 'Norway',
    'Danmark': 'Denmark', 'Suomi': 'Finland', 'Ísland': 'Iceland', 'Polska': 'Poland',
    'Türkiye': 'Turkey', 'Brasil': 'Brazil', 'Hrvatska': 'Croatia', 'Srbija': 'Serbia',
    'România': 'Romania', 'Hellas': 'Greece', 'Rossiya': 'Russia', 'Ukraina': 'Ukraine',
    'Nippon': 'Japan', 'Schweiz': 'Switzerland', 'Österreich': 'Austria',
    'Česká republika': 'Czech Republic',
}

def normalize_nationality(nat: str) -> str:
    """Return canonical English country name for display."""
    if not nat or str(nat).lower() in ('nan', 'none', ''):
        return 'Unknown'
    return NATIONALITY_CANONICAL.get(str(nat).strip(), str(nat).strip())

HTMS_ABILITY_TABLE = {
    0: {'GK': 0, 'DE': 0, 'PM': 0, 'WI': 0, 'Pas': 0, 'SC': 0, 'SH': 0},
    1: {'GK': 2, 'DE': 4, 'PM': 4, 'WI': 2, 'Pas': 3, 'SC': 4, 'SH': 1},
    2: {'GK': 12, 'DE': 18, 'PM': 17, 'WI': 12, 'Pas': 14, 'SC': 17, 'SH': 2},
    3: {'GK': 23, 'DE': 39, 'PM': 34, 'WI': 25, 'Pas': 31, 'SC': 36, 'SH': 5},
    4: {'GK': 39, 'DE': 65, 'PM': 57, 'WI': 41, 'Pas': 51, 'SC': 59, 'SH': 9},
    5: {'GK': 56, 'DE': 98, 'PM': 84, 'WI': 60, 'Pas': 75, 'SC': 88, 'SH': 15},
    6: {'GK': 76, 'DE': 134, 'PM': 114, 'WI': 81, 'Pas': 104, 'SC': 119, 'SH': 21},
    7: {'GK': 99, 'DE': 175, 'PM': 150, 'WI': 105, 'Pas': 137, 'SC': 156, 'SH': 28},
    8: {'GK': 123, 'DE': 221, 'PM': 190, 'WI': 132, 'Pas': 173, 'SC': 197, 'SH': 37},
    9: {'GK': 150, 'DE': 271, 'PM': 231, 'WI': 161, 'Pas': 213, 'SC': 240, 'SH': 46},
    10: {'GK': 183, 'DE': 330, 'PM': 281, 'WI': 195, 'Pas': 259, 'SC': 291, 'SH': 56},
    11: {'GK': 222, 'DE': 401, 'PM': 341, 'WI': 238, 'Pas': 315, 'SC': 354, 'SH': 68},
    12: {'GK': 268, 'DE': 484, 'PM': 412, 'WI': 287, 'Pas': 381, 'SC': 427, 'SH': 81},
    13: {'GK': 321, 'DE': 580, 'PM': 493, 'WI': 344, 'Pas': 457, 'SC': 511, 'SH': 95},
    14: {'GK': 380, 'DE': 689, 'PM': 584, 'WI': 407, 'Pas': 540, 'SC': 607, 'SH': 112},
    15: {'GK': 446, 'DE': 809, 'PM': 685, 'WI': 478, 'Pas': 634, 'SC': 713, 'SH': 131},
    16: {'GK': 519, 'DE': 942, 'PM': 798, 'WI': 555, 'Pas': 738, 'SC': 830, 'SH': 153},
    17: {'GK': 600, 'DE': 1092, 'PM': 924, 'WI': 642, 'Pas': 854, 'SC': 961, 'SH': 179},
    18: {'GK': 691, 'DE': 1268, 'PM': 1070, 'WI': 741, 'Pas': 988, 'SC': 1114, 'SH': 210},
    19: {'GK': 797, 'DE': 1487, 'PM': 1247, 'WI': 855, 'Pas': 1148, 'SC': 1300, 'SH': 246},
    20: {'GK': 924, 'DE': 1791, 'PM': 1480, 'WI': 995, 'Pas': 1355, 'SC': 1547, 'SH': 287},
    21: {'GK': 1074, 'DE': 1791, 'PM': 1791, 'WI': 1172, 'Pas': 1355, 'SC': 1547, 'SH': 334},
    22: {'GK': 1278, 'DE': 1791, 'PM': 1791, 'WI': 1360, 'Pas': 1355, 'SC': 1547, 'SH': 388},
    23: {'GK': 1278, 'DE': 1791, 'PM': 1791, 'WI': 1360, 'Pas': 1355, 'SC': 1547, 'SH': 450}
}

# SC column: Dutch wage table (bigpapy / ciscouf, season-50 update). Levels 20+ from the
# fitted formula a*(s-1)^b (a=0.0009136982, b=6.4090063683, compression 0.7984 above
# 20000), scaled to match level 19. Before this, SC was a copy of the GK column.
WAGE_TABLE = {
    0: {'GK': 250.0, 'DE': 250.0, 'PM': 250.0, 'WI': 250.0, 'Pas': 250.0, 'SC': 250.0},
    1: {'GK': 250.0, 'DE': 250.0, 'PM': 250.0, 'WI': 250.0, 'Pas': 250.0, 'SC': 250.0},
    2: {'GK': 270.0, 'DE': 250.0, 'PM': 250.0, 'WI': 250.0, 'Pas': 250.0, 'SC': 250.0},
    3: {'GK': 330.0, 'DE': 250.0, 'PM': 250.0, 'WI': 250.0, 'Pas': 250.0, 'SC': 250.0},
    4: {'GK': 450.0, 'DE': 250.0, 'PM': 250.0, 'WI': 250.0, 'Pas': 250.0, 'SC': 250.0},
    5: {'GK': 610.0, 'DE': 250.0, 'PM': 250.0, 'WI': 250.0, 'Pas': 250.0, 'SC': 250.0},
    6: {'GK': 830.0, 'DE': 270.0, 'PM': 270.0, 'WI': 250.0, 'Pas': 250.0, 'SC': 270.0},
    7: {'GK': 1150.0, 'DE': 310.0, 'PM': 330.0, 'WI': 290.0, 'Pas': 290.0, 'SC': 330.0},
    8: {'GK': 1590.0, 'DE': 450.0, 'PM': 510.0, 'WI': 370.0, 'Pas': 390.0, 'SC': 470.0},
    9: {'GK': 2250.0, 'DE': 730.0, 'PM': 850.0, 'WI': 550.0, 'Pas': 590.0, 'SC': 790.0},
    10: {'GK': 3170.0, 'DE': 1290.0, 'PM': 1550.0, 'WI': 890.0, 'Pas': 970.0, 'SC': 1430.0},
    11: {'GK': 4530.0, 'DE': 2310.0, 'PM': 2830.0, 'WI': 1530.0, 'Pas': 1690.0, 'SC': 2570.0},
    12: {'GK': 6450.0, 'DE': 4070.0, 'PM': 5030.0, 'WI': 2630.0, 'Pas': 2930.0, 'SC': 4550.0},
    13: {'GK': 9150.0, 'DE': 6930.0, 'PM': 8610.0, 'WI': 4430.0, 'Pas': 4930.0, 'SC': 7770.0},
    14: {'GK': 12910.0, 'DE': 11450.0, 'PM': 14250.0, 'WI': 7250.0, 'Pas': 8090.0, 'SC': 12830.0},
    15: {'GK': 18050.0, 'DE': 18270.0, 'PM': 22370.0, 'WI': 11510.0, 'Pas': 12870.0, 'SC': 20490.0},
    16: {'GK': 24150.0, 'DE': 26840.0, 'PM': 32450.0, 'WI': 17810.0, 'Pas': 19910.0, 'SC': 29650.0},
    17: {'GK': 31480.0, 'DE': 38310.0, 'PM': 46640.0, 'WI': 25650.0, 'Pas': 28200.0, 'SC': 42480.0},
    18: {'GK': 40930.0, 'DE': 54160.0, 'PM': 66330.0, 'WI': 35720.0, 'Pas': 39440.0, 'SC': 60240.0},
    19: {'GK': 52990.0, 'DE': 75730.0, 'PM': 93180.0, 'WI': 49380.0, 'Pas': 54680.0, 'SC': 84470.0},
    20: {'GK': 68210.0, 'DE': 105085.0, 'PM': 129150.0, 'WI': 67660.0, 'Pas': 75100.0, 'SC': 117694.0},
    21: {'GK': 87280.0, 'DE': 145035.0, 'PM': 177338.0, 'WI': 91800.0, 'Pas': 102461.0, 'SC': 161850.0},
    22: {'GK': 111174.0, 'DE': 199405.0, 'PM': 241895.0, 'WI': 123679.0, 'Pas': 139123.0, 'SC': 219708.0},
    23: {'GK': 141113.0, 'DE': 273400.0, 'PM': 328382.0, 'WI': 165779.0, 'Pas': 188248.0, 'SC': 294551.0},
    24: {'GK': 178627.0, 'DE': 374104.0, 'PM': 444249.0, 'WI': 221378.0, 'Pas': 254073.0, 'SC': 390241.0},
    25: {'GK': 225633.0, 'DE': 511158.0, 'PM': 599477.0, 'WI': 294805.0, 'Pas': 342276.0, 'SC': 511285.0},
}

# HTMS training points per week at each age: Foxtrick htms-points.js (WEEK_PTS_PER_AGE), incl. 29-45.
HTMS_POTENTIAL_GAINS = {17: 10, 18: 9.92, 19: 9.81, 20: 9.69, 21: 9.54, 22: 9.39, 23: 9.22, 24: 9.04, 25: 8.85,
                        26: 8.66, 27: 8.47, 28: 8.27, 29: 8.07, 30: 7.87, 31: 7.67, 32: 7.47, 33: 7.27, 34: 7.07,
                        35: 6.87, 36: 6.67, 37: 6.47, 38: 6.26, 39: 6.06, 40: 5.86, 41: 5.65, 42: 6.45, 43: 6.24,
                        44: 6.04, 45: 5.83}
SPECIALITY_OPTIONS = ['None', 'Quick', 'Unpredictable', 'Technical', 'Powerful', 'Head', 'Resilient', 'Support']
DUTCH_SPEC_MAP = {'Q': 'Quick', 'T': 'Technical', 'U': 'Unpredictable', 'P': 'Powerful', 'H': 'Head', 'R': 'Resilient', 'S': 'Support'}
HRF_SPECIALTY_ID_MAP = {'0': 'None', '1': 'Technical', '2': 'Quick', '3': 'Powerful', '4': 'Unpredictable', '5': 'Head', '8': 'Resilient'}
DEFAULT_EXAMPLE_PLAYER = {'PlayerID': 485123456, 'Speler': 'Jan Jansen', 'Positie': 'NFW', 'Leeftijd': 20, 'dag(en)': 15, 'Specialiteit': 'Quick', 'Vorm': 6.0, 'Conditie': 6.0, 'Ervaring': 4.0, 'TSI': 15000, 'Loon': 2100, 'HTMS': 500, 'HTMS28': 1900, 'GK': 1.0, 'DE': 5.0, 'PM': 5.0, 'WI': 5.0, 'Pas': 4.0, 'SC': 5.0, 'SH': 1.0, 'Nationality': 'Netherlands'}

POSITIONS_LIST = [
    ('Keeper', 'K', ['K', 'GK']), 
    ('Left Wingback', 'LWB', ['NWB', 'SHWB', 'DWB', 'OWB', 'WBTM', 'WB']), 
    ('Central Defender (Left)', 'CD (LI)', ['CD', 'NCD', 'OCD', 'CAD', 'CDTW']), 
    ('Central Defender (Center)', 'CD (CNT)', ['CD', 'NCD', 'OCD', 'CAD']), 
    ('Central Defender (Right)', 'CD (RE)', ['CD', 'NCD', 'OCD', 'CAD', 'CDTW']), 
    ('Right Wingback', 'RWB', ['NWB', 'SHWB', 'DWB', 'OWB', 'WBTM', 'WB']), 
    ('Left Winger', 'LW', ['NW', 'DW', 'OW', 'WTM']), 
    ('Inner Midfielder (Left)', 'IM (LI)', ['NIM', 'DIM', 'PDIM', 'OIM', 'OIM-Q', 'OIM-H', 'IMTW']), 
    ('Inner Midfielder (Center)', 'IM (CNT)', ['NIM', 'DIM', 'PDIM', 'OIM', 'OIM-Q', 'OIM-H']), 
    ('Inner Midfielder (Right)', 'IM (RE)', ['NIM', 'DIM', 'PDIM', 'OIM', 'OIM-Q', 'OIM-H', 'IMTW']), 
    ('Right Winger', 'RW', ['NW', 'DW', 'OW', 'WTM']), 
    ('Forward (Left)', 'FW (LI)', ['NFW', 'DFW', 'FTW', 'TDFW', 'PNF']), 
    ('Forward (Center)', 'FW (CNT)', ['NFW', 'DFW', 'TDFW', 'PNF']), 
    ('Forward (Right)', 'FW (RE)', ['NFW', 'DFW', 'FTW', 'TDFW', 'PNF'])
]

PITCH_LAYOUT = [
    [('LFW', 'FW (LI)', ['NFW', 'DFW', 'FTW', 'TDFW', 'PNF']), ('CFW', 'FW (CNT)', ['NFW', 'DFW', 'TDFW', 'PNF']), ('RFW', 'FW (RE)', ['NFW', 'DFW', 'FTW', 'TDFW', 'PNF'])], 
    [('LW', 'LW', ['NW', 'DW', 'OW', 'WTM']), ('LIM', 'IM (LI)', ['NIM', 'DIM', 'PDIM', 'OIM', 'OIM-Q', 'OIM-H', 'IMTW']), ('CM', 'IM (CNT)', ['NIM', 'DIM', 'PDIM', 'OIM', 'OIM-Q', 'OIM-H']), ('RIM', 'IM (RE)', ['NIM', 'DIM', 'PDIM', 'OIM', 'OIM-Q', 'OIM-H', 'IMTW']), ('RW', 'RW', ['NW', 'DW', 'OW', 'WTM'])], 
    [('LWB', 'LWB', ['NWB', 'SHWB', 'DWB', 'OWB', 'WBTM']), ('LCD', 'CD (LI)', ['CD', 'NCD', 'OCD', 'CAD', 'CDTW']), ('CD', 'CD (CNT)', ['CD', 'NCD', 'OCD', 'CAD']), ('RCD', 'CD (RE)', ['CD', 'NCD', 'OCD', 'CDTW']), ('RWB', 'RWB', ['NWB', 'SHWB', 'DWB', 'OWB', 'WBTM'])], 
    [('K', 'K', ['K', 'GK'])]
]

COACH_MULTIPLIERS = {
    '100% DEF': (1.125, 0.884), '90% DEF': (1.1125, 0.8956), '80% DEF': (1.1, 0.9072), '70% DEF': (1.0875, 0.9188), '60% DEF': (1.075, 0.9304), '50% DEF': (1.0625, 0.9420), '40% DEF': (1.05, 0.9536), '30% DEF': (1.0375, 0.9652), '20% DEF': (1.025, 0.9768), '10% DEF': (1.0125, 0.9884), 
    'Neutral Coach': (1.0, 1.0), 
    '10% ATT': (0.9884, 1.0079), '20% ATT': (0.9768, 1.0158), '30% ATT': (0.9652, 1.0237), '40% ATT': (0.9536, 1.0316), '50% ATT': (0.9420, 1.0395), '60% ATT': (0.9304, 1.0474), '70% ATT': (0.9188, 1.0553), '80% ATT': (0.9072, 1.0632), '90% ATT': (0.8956, 1.0711), '100% ATT': (0.884, 1.079)
}

WEATHER_SPECIALTY_MULT = {'Sunny': {'Technical': 1.05, 'Powerful': 0.95, 'Quick': 0.95}, 'Rain':  {'Technical': 0.95, 'Powerful': 1.05, 'Quick': 0.95}, 'Normal / Overcast': {}}
# A 2nd/3rd powerful forward or PDIM used to lose 4% / 7.5% of every contribution. That penalty is
# not in the Unwritten Manual, Hattrick Organizer or the BLANCO sheets (only the crowding penalties
# for 2-3 central defenders / inner mids / forwards are), so it's switched off: factor 1 for all.
STACK_PENALTY_MULT = {1: 1.0, 2: 1.0, 3: 1.0}
TACTIC_AIM_MULT, TACTIC_AOW_MULT, TACTIC_COUNTER_MULT, TACTIC_CREATIVE_MULT, TACTIC_LS_MID_MULT = 0.86, 0.858029, 0.93, 0.94, 0.950323

CATEGORY_TO_POSITION = {
    'Goalkeeper': 'K', 'Wing back': 'NWB', 'Central Defender': 'NCD',
    'Inner Midfielder': 'NIM', 'Winger': 'NW', 'Forward': 'NFW',
    'GK': 'K', 'CB': 'NCD', 'CD': 'NCD', 'WB': 'NWB', 'IM': 'NIM', 'W': 'NW', 'WI': 'NW', 'FW': 'NFW',
    'Extra2': 'Not Assigned', 'Substitute': 'Not Assigned', 'Reserve': 'Not Assigned',
    'Reserved': 'Not Assigned', 'Not Assigned': 'Not Assigned',
}

# Midfield factors from the Unwritten Manual ('The influence on midfield rating'). Derby: only the
# away team gets 1.11493; the home team gets the normal home factor. Before: HO/BLANCO values
# (home 1.199529, derby 1.113699, MOTS 1.10965, PIC 0.839949).
LOCATION_MULTIPLIERS = {'Home': 1.19892, 'Derby': 1.11493, 'Away': 1.0}
ATTITUDE_MULTIPLIERS = {'MOTS (Match of the Season)': 1.1149, 'Normal': 1.0, 'PIC (Play It Cool)': 0.83945}

# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================
def get_flag(country):
    if pd.isna(country) or not str(country).strip() or str(country).lower() == 'nan': return ''
    return FLAG_MAP.get(str(country).strip(), '🏳️')

def clean_spec(val):
    if pd.isna(val): return 'None'
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    if s in HRF_SPECIALTY_ID_MAP: return HRF_SPECIALTY_ID_MAP[s]
    for option in SPECIALITY_OPTIONS:
        if s.lower() == option.lower(): return option
    return DUTCH_SPEC_MAP.get(s.upper(), 'None')

def is_player_u21(age, days):
    try:
        if int(age) < 21: return True
        return int(age) == 21 and int(days) <= 111
    except: return False

def sh_fallback_for(pos_code, age, days=0, spec=None):
    """Age-appropriate set-pieces (SH) target for this position."""
    bench = estimate_age_richtskills(int(age), spec)
    pos_bench = bench.get(pos_code, bench.get('NFW', {}))
    return float(pos_bench.get('SH', 6.0))

FILENAME_POSITION_TAGS = {
    'GK': 'K', 'K': 'K', 'WB': 'NWB', 'NWB': 'NWB', 'SHWB': 'SHWB',
    'CD': 'NCD', 'NCD': 'NCD', 'OCD': 'OCD', 'CB': 'NCD', 'CAD': 'CAD', 'CADEF': 'CAD',
    'IM': 'NIM', 'NIM': 'NIM', 'PDIM': 'PDIM', 'OIM': 'OIM-Q',
    'WI': 'NW', 'NW': 'NW', 'W': 'NW', 'WTM': 'WTM',
    'FW': 'NFW', 'NFW': 'NFW', 'DFW': 'DFW', 'TDFW': 'DFW', 'PNF': 'PNF',
}

def _extract_filename_position_hint(filename):
    if not filename: return None
    base = str(filename).rsplit('.', 1)[0]
    tokens = [t for t in re.split(r'[_\-\s]+', base) if t]
    for t in reversed(tokens):
        if t in FILENAME_POSITION_TAGS: return FILENAME_POSITION_TAGS[t]
    return None

IM_FAMILY = ('NIM', 'OIM-Q', 'OIM-H')


SHWB_MIN_SH = 8.0  # a wing back needs at least this much set pieces to count as SHWB


def infer_position_from_skills(gk, de, pm, wi, pas, sc, spec=None, sh=None):
    """Closest position by skill shape (vs the age-29 targets), with an explicit
    inner-midfield rule on top:
      • NIM = balanced, defending is the stronger secondary (DE >= SC)
      • OIM = more scoring than defending (SC > DE)
        – Head -> OIM-H, Quick -> OIM-Q; other specialties: more scoring than
          passing -> OIM-Q, else OIM-H (as the two target profiles differ).
    PDIM (defending-heavy) and all other positions come from the shape match.
    sh: set pieces, when known. A wing back with set pieces under SHWB_MIN_SH is a normal wing
    back (NWB): the shape match ignores set pieces, so it labelled 163 plain wing backs in the
    Reference DB as SHWB (set pieces 1-7, while the SHWB profile has 18)."""
    outfield_vals = [de, pm, wi, pas, sc]
    if gk >= 2 * max(outfield_vals) and gk >= 8.0: return 'K'
    best_pos, best_score = 'NFW', -1e18
    for pos, bench in RICHTSKILLS_29.items():
        if pos == 'K': continue
        b = [bench['DE'], bench['PM'], bench['WI'], bench['Pas'], bench['SC']]
        v = [de, pm, wi, pas, sc]
        norm_v = sum(a * a for a in v) ** 0.5
        norm_b = sum(c * c for c in b) ** 0.5
        if norm_v <= 0 or norm_b <= 0: continue
        score = sum(a * c for a, c in zip(v, b)) / (norm_v * norm_b)
        if score > best_score: best_score, best_pos = score, pos
    # A technical defensive forward needs the Technical specialty (and a Technical DFW is a TDFW).
    if best_pos == 'SHWB' and sh is not None and float(sh) < SHWB_MIN_SH:
        return 'NWB'
    # Counter-attack defender: defending first, passing clearly the second skill (at least 55% of defending)
    # and more than playmaking. Playmaking stays low (optional: some for a midfield counter).
    if best_pos in ('NCD', 'OCD') and de >= max(pm, pas, wi, sc) and pas >= 0.55 * de and pas > pm:
        return 'CAD'
    # Wingers: more playmaking than winger = winger towards middle (WTM), otherwise a normal winger. The shape match
    # alone called a PM 17 / WI 16 player with little defending NW (the WTM profile has defending 11).
    if best_pos in ('NW', 'WTM'):
        return 'WTM' if pm > wi else 'NW'
    if best_pos in ('DFW', 'TDFW'):
        return 'DFW'      # DFW and TDFW are one position (the lineup still uses Technical for TDF ratings)
    if best_pos in IM_FAMILY:
        if de >= sc:
            return 'NIM'
        spec_s = str(spec or '').strip()
        if spec_s == 'Head':
            return 'OIM-H'
        if spec_s == 'Quick':
            return 'OIM-Q'
        return 'OIM-Q' if sc / max(pas, 1.0) > 10.0 / 14.5 else 'OIM-H'
    return best_pos

def _hrf_get_first(config, section, keys):
    for k in keys:
        if config.has_option(section, k):
            v = config.get(section, k, fallback=None)
            if v is not None and str(v).strip() != '': return str(v).strip()
    return None

def _hrf_resolve_specialty(config, section):
    raw = _hrf_get_first(config, section, ['specialityLabel', 'specialtyLabel', 'SpecialityLabel', 'SpecialtyLabel', 'speciality', 'specialty', 'Speciality', 'Specialty'])
    if raw is None: return 'None'
    if raw in HRF_SPECIALTY_ID_MAP: return HRF_SPECIALTY_ID_MAP[raw]
    return clean_spec(raw)

def _hrf_resolve_position(config, section, filename_hint=None, skills=None):
    raw = _hrf_get_first(config, section, ['category', 'Category', 'playerCategory', 'PlayerCategory', 'CategoryID', 'PlayerCategoryID'])
    if raw is not None:
        mapped = CATEGORY_TO_POSITION.get(raw)
        if mapped and mapped != 'Not Assigned': return mapped
        if raw in RICHTSKILLS_DEFAULT: return raw
    if filename_hint: return filename_hint
    if skills: return infer_position_from_skills(*skills)
    return 'NFW'

def parse_hrf_to_dataframe(file_path_or_buffer, username):
    config = configparser.ConfigParser(strict=False)
    if isinstance(file_path_or_buffer, str):
        config.read(file_path_or_buffer, encoding='latin1')
        filename = file_path_or_buffer
    else:
        content = file_path_or_buffer.getvalue().decode('latin1', errors='ignore')
        config.read_string(content)
        filename = getattr(file_path_or_buffer, 'name', None)

    filename_hint = _extract_filename_position_hint(filename)
    players_data = []
    for section in config.sections():
        if section.lower().startswith('player') and section.lower() != 'player1':
            def get_skill_with_sub(base_key, sub_key, default):
                base = config.getfloat(section, base_key, fallback=default)
                sub = config.getfloat(section, sub_key, fallback=0.0)
                return round(base + sub, 3)   # HO sublevels have many decimals: keep 3

            gk = get_skill_with_sub('mlv', 'mlvSub', 1.0)
            de = get_skill_with_sub('bac', 'bacSub', 5.0)
            pm = get_skill_with_sub('spe', 'speSub', 5.0)
            wi = get_skill_with_sub('ytt', 'yttSub', 5.0)
            pas = get_skill_with_sub('fra', 'fraSub', 4.0)
            sc = get_skill_with_sub('mal', 'malSub', 5.0)
            sh = get_skill_with_sub('fas', 'fasSub', 1.0)
            
            age = config.getint(section, 'ald', fallback=20)
            days = config.getint(section, 'agedays', fallback=0)
            htms_val = calculate_htms_ability(gk, de, pm, wi, pas, sc, sh)
            htms28_val = calculate_htms_potential(age, days, htms_val)

            p_dict = {
                'username': username,
                'PlayerID': config.getint(section, 'PlayerID', fallback=int(section.replace('player', ''))),
                'Speler': config.get(section, 'name', fallback='Unknown'),
                'Positie': _hrf_resolve_position(config, section, filename_hint=filename_hint, skills=(gk, de, pm, wi, pas, sc)),
                'Leeftijd': age,
                'dag(en)': days,
                'Specialiteit': _hrf_resolve_specialty(config, section),
                'Vorm': config.getfloat(section, 'for', fallback=6.0),
                'Conditie': config.getfloat(section, 'uth', fallback=7.0),
                'Ervaring': config.getfloat(section, 'rut', fallback=4.0),
                'TSI': config.getfloat(section, 'mkt', fallback=1000),
                'Loon': config.getfloat(section, 'sal', fallback=1000),
                'GK': gk, 'DE': de, 'PM': pm, 'WI': wi, 'Pas': pas, 'SC': sc, 'SH': sh,
                'Nationality': 'Netherlands',
                'Leiderschap': config.getfloat(section, 'led', fallback=5.0),
                'Injuries': 0.0, 'Transfer-listed': '',
                'Matches for the national team': config.getint(section, 'Caps', fallback=0),
                'Matches for the national U21 team': config.getint(section, 'CapsU20', fallback=0),
                'National team player': 1 if config.getint(section, 'NationalTeamID', fallback=0) > 0 else 0,
                'HTMS': htms_val,
                'HTMS28': htms28_val if isinstance(htms28_val, (int, float)) else 0.0
            }
            players_data.append(p_dict)
    return pd.DataFrame(players_data)

# Hattrick's level names (whole numbers; TS 6.0-6.99 is 'content', 4.5 = composed at the season start)
TS_LEVELS = ['like the Cold War', 'murderous', 'furious', 'irritated', 'composed', 'calm', 'content', 'satisfied',
             'delirious', 'walking on clouds', 'Paradise on Earth!']
TC_LEVELS = ['non-existent', 'disastrous', 'wretched', 'poor', 'decent', 'strong', 'wonderful', 'slightly exaggerated',
             'exaggerated', 'completely exaggerated']


def level_name(value, names):
    """The Hattrick name for a team spirit / confidence value (4.5 -> composed)."""
    try:
        i = int(float(value))
    except (TypeError, ValueError):
        return ''
    return names[max(0, min(i, len(names) - 1))]


def get_team_spirit_multiplier(ts_val):
    """Midfield factor for team spirit, from the table 'invloed van teamgeest en motivatie op je
    middenveld' (Dutch Hattrick guide): +7% per team-spirit level around composed (4.5 = 100%),
    with a steeper drop at murderous (1.5 = 72%). Normalised to 1.00 at TS 7.2, where the midfield
    ratings were calibrated (BLANCO). Before: sqrt(TS / 7.2), up to ~11% too steep at both ends.
    The factor works on the players' strength before the 1.2 power of the sector formula, so it is
    raised to 1.2 here: Hattrick's own lineup simulator (stage, Nov 2026: composed -> delirious with a
    fixed team) moved midfield 8-10% per level, the table's 7% alone only 6% (0.37 too low at delirious)."""
    ts = max(float(ts_val or 0), 0.0)
    if ts >= 2.5:
        rel = 1.0 + 0.07 * (ts - 4.5)
    else:   # below furious: 86% at 2.5, 72% at 1.5, then on with that slope
        rel = max(0.40, 0.86 - 0.14 * (2.5 - ts))
    return float((rel / (1.0 + 0.07 * (7.2 - 4.5))) ** 1.2)

def get_team_confidence_multiplier(tc_val): 
    return float(1.05 ** (tc_val - 4.5))

def get_weather_multiplier(weather, specialty): 
    return WEATHER_SPECIALTY_MULT.get(weather, {}).get(specialty, 1.0)

def get_tactic_mults(tactiek):
    mid = rd = cd = ld = ra = ca = la = 1.0
    if tactiek == 'AIM': rd = ld = TACTIC_AIM_MULT
    elif tactiek == 'AOW': cd = TACTIC_AOW_MULT
    elif tactiek == 'Counter': mid = TACTIC_COUNTER_MULT
    elif tactiek == 'Creative': rd = cd = ld = TACTIC_CREATIVE_MULT
    elif tactiek == 'Long Shots': 
        mid, ra, ca, la = TACTIC_LS_MID_MULT, TACTIC_LS_MID_MULT * 1.022998, TACTIC_LS_MID_MULT * 1.022998, TACTIC_LS_MID_MULT * 1.022998
    return mid, rd, cd, ld, ra, ca, la

def get_stack_combo_type(role_code, specialty):
    if role_code in ('NFW', 'PNF') and specialty == 'Powerful': return 'PNF'
    if role_code in ('TDFW', 'DFW') and specialty == 'Technical': return 'TDF'
    if role_code in ('DIM', 'PDIM') and specialty == 'Powerful': return 'PDIM'
    return None

def get_player_status(vorm, cond, exp, with_experience=True):
    """Form x stamina (x experience, BLANCO). The Lineup Simulator uses with_experience=False and
    adds experience as a small rating bonus instead (experience_rating_bonus, WesselV1)."""
    form_val = min(max(vorm - 0.5, 0.0), 7.5)
    f_part = (form_val ** 0.45) / (7.5 ** 0.45) if form_val > 0 else 0.1
    cond_val = min(max(cond + 6.5, 7.0), 15.25)
    c_part = (cond_val ** 0.6) / (15.25 ** 0.6)
    if not with_experience:
        return f_part * c_part
    exp_val = max(((exp / 15.0) ** (2.0 / 3.0)) * 15.0 - 0.5, 0.0)
    e_part = (exp_val ** 0.375 + 12.5) / 12.5
    return f_part * c_part * e_part


# Experience adds to the ratings, not to the skills (WesselV1, forum 17371940.86; Tasos 17445499.339:
# through each player's contribution to the sector). Rating levels: 0.36 x (1 - 0.85^XP), times
# 1 for midfield and side defence, 7/8 for central defence and side attack, 4/5 for central attack.
# Midfield experience: share of BLANCO's experience factor; the rest is WesselV1's rating bonus.
# 0.5 fits Finland's real-match ratings (Pernaug) at team spirit 9.5: PIC 10.75 vs 10.90, MOTS 13.92
# vs 13.60. (1.0 = BLANCO only: 11.50 / 14.94; 0.0 = WesselV1 only: 10.01 / 12.92.)
MID_EXPERIENCE_BLANCO_SHARE = 0.5
EXPERIENCE_SECTOR_COEF = {'MID': 1.0, 'RD': 1.0, 'LD': 1.0, 'CD': 7.0 / 8.0, 'RA': 7.0 / 8.0, 'LA': 7.0 / 8.0, 'CA': 4.0 / 5.0}


def experience_rating_bonus(sector, xp):
    """Rating levels experience adds to a sector, for a player with this experience level."""
    try:
        return EXPERIENCE_SECTOR_COEF.get(sector, 1.0) * 0.36 * (1.0 - 0.85 ** max(float(xp or 0), 0.0))
    except (TypeError, ValueError):
        return 0.0

def get_predictor_key(pos_code, role_code):
    if pos_code == 'K': return 'K'
    return ('l' if pos_code in ['LWB', 'CD (LI)', 'LW', 'IM (LI)', 'FW (LI)'] else ('r' if pos_code in ['RWB', 'CD (RE)', 'RW', 'IM (RE)', 'FW (RE)'] else 'm')) + role_code

# ==============================================================================
# 3. MATH ENGINE (HTMS, WAGE, TSI)
# ==============================================================================
def lookup_htms_ability(s_name, val):
    if pd.isna(val) or val <= 0: return 0.0
    val = float(val)
    fl_idx = max(0, min(int(np.floor(val)), 23))
    return float(HTMS_ABILITY_TABLE[fl_idx][s_name])

def calculate_htms_ability(gk, de, pm, wi, pas, sc, sh):
    skills = {'GK': gk, 'DE': de, 'PM': pm, 'WI': wi, 'Pas': pas, 'SC': sc, 'SH': sh}
    return round(sum(lookup_htms_ability(s, v) for s, v in skills.items()))

def calculate_htms_potential(age, days, ability_points):
    """HTMS28 exactly as Foxtrick (htms-points.js): under 28, add the training points of the
    weeks left in this age year plus 16 weeks for every following year up to 28; from 28 on,
    subtract the weeks since the birthday and 16 weeks for every year back to 28."""
    try:
        years = int(age)
        d = max(0, min(int(days), 111))
        cur = float(ability_points)
        wk = HTMS_POTENTIAL_GAINS
        if years < 28:
            diff = (112 - d) / 7.0 * wk.get(years, 10.0) + sum(16 * wk[i] for i in range(years + 1, 28))
        elif years <= 45:
            diff = -(d / 7.0 * wk[years] + sum(16 * wk[i] for i in range(years, 28, -1)))
        else:
            diff = -cur
        return int(round(cur + diff))
    except Exception:
        return round(ability_points)

# How the wage rises within one skill level: wage = wage(level) x (wage(next) / wage(level)) ^ (sub-level ^ WAGE_SUB_P).
# 1.0 = evenly in % (as before); above 1 = slower at the start of a level, faster near the end.
# Tested (1.0 / 1.5 / 2.0): 36 players with real skills 0.704 / 0.685 / 0.704 levels off; 214 Reference DB forwards
# like Acim: main skill 0.225 / 0.176 / 0.118, second skill 1.665 / 1.534 / 1.472; NT options about the same at 1.5,
# second skill a bit worse at 2.0. Real seniors' wages sat in the lower third of their level's range at 1.0.
WAGE_SUB_P = 1.5


def lookup_wage(skill_val, skill_name):
    if pd.isna(skill_val) or float(skill_val) < 0: skill_val = 0.0
    val, fl = float(skill_val), int(np.floor(float(skill_val)))
    idx, n_idx = max(0, min(fl, 25)), max(0, min(fl + 1, 25))
    w_base, w_next = WAGE_TABLE[idx][skill_name], WAGE_TABLE[n_idx][skill_name]
    if w_base <= 0: return 0.0
    calc_wage = w_base * ((w_next / w_base) ** ((val - fl) ** WAGE_SUB_P)) if w_next > w_base else w_base
    return calc_wage - 250.0

# Pre-flattened wage table arrays for fast solver access (avoids dict lookups)
_WAGE_GK  = [WAGE_TABLE[i]['GK']  for i in range(26)]
_WAGE_DE  = [WAGE_TABLE[i]['DE']  for i in range(26)]
_WAGE_PM  = [WAGE_TABLE[i]['PM']  for i in range(26)]
_WAGE_WI  = [WAGE_TABLE[i]['WI']  for i in range(26)]
_WAGE_PAS = [WAGE_TABLE[i]['Pas'] for i in range(26)]
_WAGE_SC  = [WAGE_TABLE[i]['SC']  for i in range(26)]
_HTMS_GK  = [HTMS_ABILITY_TABLE[i]['GK']  for i in range(24)]
_HTMS_DE  = [HTMS_ABILITY_TABLE[i]['DE']  for i in range(24)]
_HTMS_PM  = [HTMS_ABILITY_TABLE[i]['PM']  for i in range(24)]
_HTMS_WI  = [HTMS_ABILITY_TABLE[i]['WI']  for i in range(24)]
_HTMS_PAS = [HTMS_ABILITY_TABLE[i]['Pas'] for i in range(24)]
_HTMS_SC  = [HTMS_ABILITY_TABLE[i]['SC']  for i in range(24)]
_HTMS_SH  = [HTMS_ABILITY_TABLE[i]['SH']  for i in range(24)]

def _lw(v, tbl):
    """Fast wage lookup — no dict, no pd.isna, minimal branching."""
    if v < 0: v = 0.0
    fl = int(v)
    if fl >= 25: return tbl[25] - 250.0
    wb, wn = tbl[fl], tbl[min(fl+1,25)]
    if wb <= 0: return 0.0
    return (wb * ((wn/wb)**((v-fl)**WAGE_SUB_P)) if wn > wb else wb) - 250.0

def _lh(v, tbl):
    """Fast HTMS lookup — floor index into pre-built list."""
    fl = max(0, min(int(v), 23))
    return float(tbl[fl])

def _solver_eval(age, age_tsi_f, spec_m, age_wage_f, sh_mul,
                 gk, de, pm, wi, pas, sc, sh, form, cond):
    """Fast combined TSI+Wage+HTMS evaluation for the solver inner loop.
    Pre-computed constants (age_tsi_f, spec_m, age_wage_f, sh_mul) are
    passed in so the solver closure captures them once, not per call.
    Returns (tsi, wage, htms).
    """
    # TSI
    sf = (1.034*(de-1)**3 + 1.031*(pm-1)**3 +
          1.038*(sc-1)**3 + 1.035*(pas-1)**3 + 0.826*(wi-1)**3
          ) if de>1 or pm>1 or sc>1 or pas>1 or wi>1 else 0.0
    tsi = sf*sf*(cond-1)**0.5*(form-1)**0.5/1000*age_tsi_f if sf>0 and cond>1 and form>1 else 0.0
    # Wage
    w0=_lw(gk,_WAGE_GK); w1=_lw(de,_WAGE_DE); w2=_lw(pm,_WAGE_PM)
    w3=_lw(wi,_WAGE_WI); w4=_lw(pas,_WAGE_PAS); w5=_lw(sc,_WAGE_SC)
    mx=max(w0,w1,w2,w3,w4,w5)
    m=0.40 if mx>20300 else 0.50
    bb=(w0 if w0==mx else m*w0)+(w1 if w1==mx else m*w1)+(w2 if w2==mx else m*w2)+(w3 if w3==mx else m*w3)+(w4 if w4==mx else m*w4)+(w5 if w5==mx else m*w5)
    wage=(250+bb*sh_mul)*spec_m*age_wage_f
    # HTMS
    htms=(_lh(gk,_HTMS_GK)+_lh(de,_HTMS_DE)+_lh(pm,_HTMS_PM)+
          _lh(wi,_HTMS_WI)+_lh(pas,_HTMS_PAS)+_lh(sc,_HTMS_SC)+_lh(sh,_HTMS_SH))
    return tsi, wage, round(htms)

def _solver_eval_keeper(age_tsi_f, spec_m, age_wage_f, sh_mul,
                        gk, de, pm, wi, pas, sc, sh, form, cond):
    """Fast evaluation specifically for Keeper position.
    TSI is based on GK only (not outfield skills).
    Returns (tsi, wage, htms).
    """
    # TSI — keeper: 3*(GK-1)^3.359 * (form-1)^0.5  (NO cond term!)
    tsi = (3.0 * max(gk - 1, 0.0) ** 3.359
           * max(form - 1, 0.0) ** 0.5
           * age_tsi_f) if gk > 1 and form > 1 else 0.0
    # Wage (same formula as outfield)
    w0=_lw(gk,_WAGE_GK); w1=_lw(de,_WAGE_DE); w2=_lw(pm,_WAGE_PM)
    w3=_lw(wi,_WAGE_WI); w4=_lw(pas,_WAGE_PAS); w5=_lw(sc,_WAGE_SC)
    mx=max(w0,w1,w2,w3,w4,w5)
    m=0.40 if mx>20300 else 0.50
    bb=(w0 if w0==mx else m*w0)+(w1 if w1==mx else m*w1)+(w2 if w2==mx else m*w2)+(w3 if w3==mx else m*w3)+(w4 if w4==mx else m*w4)+(w5 if w5==mx else m*w5)
    wage=(250+bb*sh_mul)*spec_m*age_wage_f
    # HTMS
    htms=(_lh(gk,_HTMS_GK)+_lh(de,_HTMS_DE)+_lh(pm,_HTMS_PM)+
          _lh(wi,_HTMS_WI)+_lh(pas,_HTMS_PAS)+_lh(sc,_HTMS_SC)+_lh(sh,_HTMS_SH))
    return tsi, wage, round(htms)


def calculate_tsi_for_form(age, form, cond, gk, de, pm, wi, pas, sc):
    tsi_gk = (3 * max(gk - 1, 0.0) ** 3.359 * max(form - 1, 0.0) ** 0.5 if (gk > 1 and form > 1) else 0.0)
    sum_field = (
        1.034 * max(de - 1, 0) ** 3 + 1.031 * max(pm - 1, 0) ** 3 + 
        1.038 * max(sc - 1, 0) ** 3 + 1.035 * max(pas - 1, 0) ** 3 + 0.826 * max(wi - 1, 0) ** 3
    )
    tsi_field = ((sum_field ** 2 * max(cond - 1, 0) ** 0.5 * max(form - 1, 0) ** 0.5) / 1000 if (cond > 1 and form > 1) else 0.0)
    tsi27 = max(tsi_gk, tsi_field)
    if tsi27 == tsi_gk and tsi_gk > 0:
        return max(0.1, 1 - 0.1 * (age - 30)) * tsi27 if age > 30 else tsi27
    return max(0.125, 1 - 0.125 * (age - 27)) * tsi27 if age > 27 else tsi27

def calculate_exact(age, days, spec, vorm, cond, gk, de, pm, wi, pas, sc, sh):
    form_floor = float(int(vorm))  # e.g. form=4.37 → 4.0
    calc_tsi_low  = calculate_tsi_for_form(age, form_floor,        cond, gk, de, pm, wi, pas, sc)
    calc_tsi_curr = calculate_tsi_for_form(age, vorm,              cond, gk, de, pm, wi, pas, sc)
    calc_tsi_high = calculate_tsi_for_form(age, form_floor + 0.99, cond, gk, de, pm, wi, pas, sc)
    
    subskill_wages = [lookup_wage(gk,'GK'), lookup_wage(de,'DE'), lookup_wage(pm,'PM'), lookup_wage(wi,'WI'), lookup_wage(pas,'Pas'), lookup_wage(sc,'SC')]
    max_w = max(subskill_wages)
    bb_bg_sum = sum(w if w == max_w else (0.40 if max_w > 20300 else 0.50) * w for w in subskill_wages)
    calc_wage_28 = max((250 + bb_bg_sum * (1 + 0.25 * sh / 100.0)) * (1.10 if (spec and str(spec).strip() not in ('Geen', 'None', '', 'nan')) else 1.00), 250.0)
    calc_wage_curr = max((max(0.1, 1 - 0.1 * (age - 28)) if age > 28 else 1.0) * calc_wage_28, 250.0)

    ability_pts = calculate_htms_ability(gk, de, pm, wi, pas, sc, sh)
    return (calc_tsi_low, calc_tsi_curr, calc_tsi_high, calc_wage_curr, calc_wage_28, ability_pts, calculate_htms_potential(age, days, ability_pts))

# ==============================================================================
# 4. PREDICTOR ENGINE
# ==============================================================================
def long_shot_goal_prob(shooter_sc, shooter_sp, keeper_gk, keeper_sp):
    """Chance a long shot is scored (Unwritten Manual 16741488.108):
    attack = 0.0643·SC^2.3808·SP^2.7720, defence = 1977.45·GK^0.9 + 31.48·SP^2.3262."""
    att = 0.0643 * max(float(shooter_sc), 0.0) ** 2.3808 * max(float(shooter_sp), 0.0) ** 2.7720
    dfn = 1977.4524 * max(float(keeper_gk), 0.0) ** 0.9 + 31.4827 * max(float(keeper_sp), 0.0) ** 2.3262
    return att / (att + dfn) if (att + dfn) > 0 else 0.0


def aim_aow_redirect(level):
    """Share of attacks an AIM/AOW team redirects, by tactic level:
    0.474·(1 − e^(−0.0762·level)) — ~15% at level 5, ~30% at 13, ~37% at 20
    (Hattrick wiki: AIM/AOW move 15–40% depending on tactic level)."""
    try:
        lv = max(0.0, float(level))
    except (TypeError, ValueError):
        return None
    return 0.474 * (1.0 - math.exp(-0.0762 * lv))


def _attack_split(tac):
    """(each wing, centre) share of a team's normal attacks. Normal: 25/35.
    AIM/AOW use the tactic level ('REDIR') when given, otherwise the BLANCO
    sheet's fixed split (AIM 17.5/50, AOW 32.5/20)."""
    p = tac.get('REDIR')
    if tac.get('AIM') == 1:
        return (0.175, 0.5) if p is None else (0.25 * (1 - p), 0.35 + 0.5 * p)
    if tac.get('AOW') == 1:
        return (0.325, 0.2) if p is None else (0.25 + 0.175 * p, 0.35 * (1 - p))
    return 0.25, 0.35


def _with_long_shots(tac, open_play_rate, open_play_share):
    """Long Shots: a share of the centre/wing chances (tac['LS_CONV'], by tactic level)
    becomes a long shot, scored with tac['LS_GOAL'] instead of via the sector ratings."""
    conv, goal = tac.get('LS_CONV'), tac.get('LS_GOAL')
    if conv is None or goal is None:
        return open_play_rate
    return (1 - conv) * open_play_rate + conv * open_play_share * goal


def indirect_set_piece_ratings(players, keeper=None, taker=None):
    """Indirect set-piece ratings of a lineup (Hattrick Organizer, module/lineup/Lineup.java):
    attack  = 0.5 x avg scoring + 0.3 x avg set pieces + 0.09 x set-piece taker's set pieces
    defence = 0.4 x avg defending + 0.3 x avg set pieces + 0.1 x keeper's set pieces + 0.08 x keeper's keeping
    players: skill dicts (GK..SH) of everyone on the pitch, keeper included; taker: one of them
    (default: highest set pieces among the outfield players)."""
    ps = [p for p in players if p]
    if not ps:
        return 0.0, 0.0
    f = lambda p, k: float(p.get(k) or 0.0)
    n = len(ps)
    avg = lambda k: sum(f(p, k) for p in ps) / n
    if taker is None:
        outfield = [p for p in ps if p is not keeper] or ps
        taker = max(outfield, key=lambda p: f(p, 'SH'))
    att = 0.5 * avg('SC') + 0.3 * avg('SH') + 0.09 * f(taker, 'SH')
    dfn = 0.4 * avg('DE') + 0.3 * avg('SH') + (0.1 * f(keeper, 'SH') + 0.08 * f(keeper, 'GK') if keeper else 0.0)
    return att, dfn


def special_event_counts(lineup_players):
    """#PNF, #CD, #PDIM of a lineup {slot: player dict with 'Positie' = role, 'Specialiteit'}.
    PNF = Powerful normal forward, CD = central defenders (no wing-backs), PDIM = Powerful
    defensive inner midfielder (Pernaug's match simulator inputs)."""
    pw = lambda p: str(p.get('Specialiteit', '')).strip() == 'Powerful'
    n_cd = sum(1 for s in ('LCD', 'CD', 'RCD') if s in lineup_players)
    n_pnf = sum(1 for s in ('LFW', 'CFW', 'RFW') if s in lineup_players
                and lineup_players[s].get('Positie') in ('NFW', 'PNF') and pw(lineup_players[s]))
    n_pdim = sum(1 for s in ('LIM', 'CM', 'RIM') if s in lineup_players
                 and lineup_players[s].get('Positie') in ('DIM', 'PDIM') and pw(lineup_players[s]))
    return {'PNF': n_pnf, 'CD': n_cd, 'PDIM': n_pdim}


# Special events (Pernaug's match simulator, from forum / Unwritten Manual data):
PDIM_CUT = {0: 0.0, 1: 0.063, 2: 0.10, 3: 0.125}            # share of the opponent's normal chances cancelled
PNF_BASE_BY_CD = {0: 0.080, 1: 0.055, 2: 0.022, 3: 0.008}   # PNF goal per missed chance, by opponent CDs
PNF_MULT = {0: 0.0, 1: 1.0, 2: 1.6, 3: 2.0}                 # more PNFs


def _pnf_chance(n_pnf, opp_cd):
    n_pnf, opp_cd = int(n_pnf or 0), int(opp_cd or 0)
    return PNF_BASE_BY_CD[min(max(opp_cd, 0), 3)] * PNF_MULT[min(max(n_pnf, 0), 3)]


# Hattrick shows a rating 0.75 above the value the match engine uses (Unwritten Manual ch.5: attack 12 vs
# defence 13.5 goes into the goal-chance formula as 11.25 vs 12.75). Every attack/defence matchup uses
# the same gap. Before: three of the six matchups used +1.0 instead (our left attack, their central and
# left attack), so two identical teams got different scores (0.74 vs 0.79).
RATING_GAP = -0.75


def calculate_expected_score(nl, other, nl_tac, other_tac):
    def pwr(base, a, d, off): return base * 0.92 * max(a+off, 0.0001)**3.5 / (max(a+off, 0.0001)**3.5 + max(d+off, 0.0001)**3.5)
    def sp(dir, a, d): return 0.1*dir + 0.05 * max(a-0.75, 0.0001)**3.5 / (max(a-0.75, 0.0001)**3.5 + max(d-0.75, 0.0001)**3.5)
    pool = max(10.0 - nl_tac['PRESS'] - other_tac['PRESS'], 0.0)
    nc_nl = pool * max(nl['MID'], 0.0001)**3 / (max(nl['MID'], 0.0001)**3 + max(other['MID'], 0.0001)**3)
    nc_o = pool * max(other['MID'], 0.0001)**3 / (max(other['MID'], 0.0001)**3 + max(nl['MID'], 0.0001)**3)
    s_nl, c_nl_base = _attack_split(nl_tac)
    s_o, c_o_base = _attack_split(other_tac)
    rate_nl = _with_long_shots(nl_tac, pwr(s_nl, nl['RA'], other['LD'], RATING_GAP) + pwr(c_nl_base, nl['CA'], other['CD'], RATING_GAP) + pwr(s_nl, nl['LA'], other['RD'], RATING_GAP), 2 * s_nl + c_nl_base) + sp(nl['DIRSP'], nl['ISPOFF'], other['ISPDEF'])
    # Opponent attacks are played against OUR defence (was: against their own CD/RD).
    rate_o = _with_long_shots(other_tac, pwr(s_o, other['RA'], nl['LD'], RATING_GAP) + pwr(c_o_base, other['CA'], nl['CD'], RATING_GAP) + pwr(s_o, other['LA'], nl['RD'], RATING_GAP), 2 * s_o + c_o_base) + sp(other['DIRSP'], other['ISPOFF'], nl['ISPDEF'])
    # PDIM: a share of the opponent's normal chances is cancelled before it is played.
    nc_nl *= 1.0 - PDIM_CUT[min(max(int(other.get('N_PDIM', 0) or 0), 0), 3)]
    nc_o *= 1.0 - PDIM_CUT[min(max(int(nl.get('N_PDIM', 0) or 0), 0), 3)]
    n_nl, n_o = nc_nl * rate_nl, nc_o * rate_o
    # PNF: each missed normal chance can still become a goal (fewer against more CDs).
    pnf_nl = max(nc_nl - n_nl, 0.0) * _pnf_chance(nl.get('N_PNF', 0), other.get('N_CD', 0))
    pnf_o = max(nc_o - n_o, 0.0) * _pnf_chance(other.get('N_PNF', 0), nl.get('N_CD', 0))
    c_nl = (nc_o - n_o - pnf_o) * nl_tac['CAPCT'] * rate_nl if nc_nl < nc_o else 0.0
    c_o = (nc_nl - n_nl - pnf_nl) * other_tac['CAPCT'] * rate_o if nc_o < nc_nl else 0.0
    return {'goals_nl': n_nl+c_nl+pnf_nl, 'goals_o': n_o+c_o+pnf_o, 'pnf_nl': pnf_nl, 'pnf_o': pnf_o, 'possession_nl': max(nl['MID'],0.0001)/(max(nl['MID'],0.0001)+max(other['MID'],0.0001)), 'possession_o': max(other['MID'],0.0001)/(max(nl['MID'],0.0001)+max(other['MID'],0.0001))}

# Share of the opponent's missed normal chances that a Counter-tactic team turns
# into counter chances, by counter-attack tactic level. Live data by nickarana
# (forum 17493341.6): ~200k missed chances, matches with both teams 400+ HatStats.
# Levels 6–9 (few matches, noisy) smoothed; ceiling ~45% from level 29 up.
COUNTER_PCT_BY_LEVEL = {6: 0.05, 7: 0.07, 8: 0.09, 9: 0.11, 10: 0.13, 11: 0.16, 12: 0.19,
                        13: 0.22, 14: 0.25, 15: 0.29, 16: 0.32, 17: 0.34, 18: 0.35, 19: 0.37,
                        20: 0.38, 21: 0.39, 22: 0.41, 23: 0.42, 24: 0.43, 25: 0.43, 26: 0.43,
                        27: 0.44, 28: 0.44, 29: 0.45}


# BLANCO Score Predictor ('CAs' tab), levels 10-17: per level the average of what was measured
# ('Real': counters / stopped chances) and the sheet's own estimate. Level 17: (30.8% + 39%) / 2 = 34.9%.
# Small samples (level 17: 26 chances), so level 16 (39.1%) comes out above level 17.
_BLANCO_REAL = {10: 0.2533, 11: 0.2543, 12: 0.3041, 13: 0.3186, 14: 0.3721, 15: 0.3543, 16: 0.4029, 17: 0.3077}
_BLANCO_EST = {10: 0.25, 11: 0.27, 12: 0.30, 13: 0.32, 14: 0.35, 15: 0.37, 16: 0.38, 17: 0.39}
COUNTER_PCT_SCPRED = {lv: (_BLANCO_REAL[lv] + _BLANCO_EST[lv]) / 2 for lv in _BLANCO_REAL}
# The two ways to use nickarana's live data in the Score Predictor:
COUNTER_SOURCES = {'nick_table': 'CA-Original', 'nick': 'CA-Nick'}
# nickarana's live data by CA rating (rows) and average match rating (columns) (forum 17493341.115).
COUNTER_GRID_RATINGS = (10, 11, 12, 13, 14)
COUNTER_GRID = {16: (0.33, 0.33, 0.32, 0.31, 0.30), 17: (0.34, 0.35, 0.34, 0.33, 0.32), 18: (0.36, 0.36, 0.35, 0.35, 0.34),
                19: (0.35, 0.37, 0.37, 0.36, 0.36), 20: (0.39, 0.39, 0.38, 0.37, 0.36)}
# Outside that grid: the per-level table (v2, all matches) with ~0.6 points less per rating level above 12.
COUNTER_RATING_SLOPE = 0.006
COUNTER_RATING_CENTRE = 12.0


def _interp_table(table, lv):
    keys = sorted(table)
    if lv <= keys[0]:
        return table[keys[0]]
    if lv >= keys[-1]:
        return table[keys[-1]]
    lo = max(k for k in keys if k <= lv)
    hi = min(k for k in keys if k >= lv)
    if lo == hi:
        return table[lo]
    t = (lv - lo) / (hi - lo)
    return table[lo] + (table[hi] - table[lo]) * t


def _grid_row(lv, r):
    """nickarana's grid at CA rating lv (16-20, interpolated) and match rating r (10-14, interpolated)."""
    r = min(max(float(r), COUNTER_GRID_RATINGS[0]), COUNTER_GRID_RATINGS[-1])
    def row_at(level):
        vals = COUNTER_GRID[level]
        i = min(int(r) - COUNTER_GRID_RATINGS[0], len(vals) - 2)
        t = r - COUNTER_GRID_RATINGS[i]
        return vals[i] + (vals[i + 1] - vals[i]) * t
    lo = int(min(max(lv, 16), 20))
    hi = min(lo + 1, 20)
    t = min(max(lv - lo, 0.0), 1.0)
    return row_at(lo) + (row_at(hi) - row_at(lo)) * t


def counter_pct_from_level(level, source='nick', match_rating=None):
    """Share of the opponent's missed normal chances that a Counter team turns into counters.
    source 'nick': nickarana's live data - for CA 16-20 his grid by match rating (both teams'
    average rating), elsewhere his per-level table corrected for the match rating.
    source 'scpred': BLANCO sheet, average of its measured and estimated values (levels 10-17),
    continued outside that range with nickarana's steps."""
    try:
        lv = float(level)
    except (TypeError, ValueError):
        return 0.0
    if source == 'nick_table':      # nickarana's original per-level table, the same for every match
        return _interp_table(COUNTER_PCT_BY_LEVEL, lv)
    if source == 'scpred':
        keys = sorted(COUNTER_PCT_SCPRED)
        if lv < keys[0]:
            return max(COUNTER_PCT_SCPRED[keys[0]] + _interp_table(COUNTER_PCT_BY_LEVEL, lv)
                       - COUNTER_PCT_BY_LEVEL[keys[0]], 0.0)
        if lv > keys[-1]:
            return min(COUNTER_PCT_SCPRED[keys[-1]] + _interp_table(COUNTER_PCT_BY_LEVEL, lv)
                       - COUNTER_PCT_BY_LEVEL[keys[-1]], 0.60)
        return _interp_table(COUNTER_PCT_SCPRED, lv)
    if match_rating:
        try:
            r = float(match_rating)
            if 16 <= lv <= 20:
                return _grid_row(lv, r)
            base = _interp_table(COUNTER_PCT_BY_LEVEL, lv)
            return max(base - COUNTER_RATING_SLOPE * (min(max(r, 10.0), 14.0) - COUNTER_RATING_CENTRE), 0.0)
        except (TypeError, ValueError):
            pass
    return _interp_table(COUNTER_PCT_BY_LEVEL, lv)


def attitude_factor(seen_as, play_as):
    """Midfield factor to convert ratings seen with one attitude to another
    (e.g. opponent's Normal-match ratings -> expected MOTS: ×1.1149)."""
    return ATTITUDE_MULTIPLIERS.get(play_as, 1.0) / ATTITUDE_MULTIPLIERS.get(seen_as, 1.0)


def goal_distribution(nl, other, nl_tac, other_tac, slots=10):
    """Exact score distribution from the same chance model as calculate_expected_score:
    10 chance moments; each is played (pool/10), goes to a team by midfield, may be cancelled by PDIMs,
    is scored, or becomes a PNF goal, or (if missed) a counter for the other team. Returns P[a, b]."""
    pwr = lambda base, a, d, off: base * 0.92 * max(a+off, 1e-4)**3.5 / (max(a+off, 1e-4)**3.5 + max(d+off, 1e-4)**3.5)
    sp = lambda dr, a, d: 0.1*dr + 0.05 * max(a-0.75, 1e-4)**3.5 / (max(a-0.75, 1e-4)**3.5 + max(d-0.75, 1e-4)**3.5)
    G = RATING_GAP
    pool = max(10.0 - nl_tac['PRESS'] - other_tac['PRESS'], 0.0)
    m1, m2 = max(nl['MID'], 1e-4)**3, max(other['MID'], 1e-4)**3
    sh1 = m1 / (m1 + m2)
    s1, c1 = _attack_split(nl_tac); s2, c2 = _attack_split(other_tac)
    r1 = _with_long_shots(nl_tac, pwr(s1, nl['RA'], other['LD'], G) + pwr(c1, nl['CA'], other['CD'], G) + pwr(s1, nl['LA'], other['RD'], G), 2*s1 + c1) + sp(nl['DIRSP'], nl['ISPOFF'], other['ISPDEF'])
    r2 = _with_long_shots(other_tac, pwr(s2, other['RA'], nl['LD'], G) + pwr(c2, other['CA'], nl['CD'], G) + pwr(s2, other['LA'], nl['RD'], G), 2*s2 + c2) + sp(other['DIRSP'], other['ISPOFF'], nl['ISPDEF'])
    k1 = 1 - PDIM_CUT[min(max(int(other.get('N_PDIM', 0) or 0), 0), 3)]
    k2 = 1 - PDIM_CUT[min(max(int(nl.get('N_PDIM', 0) or 0), 0), 3)]
    q1 = _pnf_chance(nl.get('N_PNF', 0), other.get('N_CD', 0)); q2 = _pnf_chance(other.get('N_PNF', 0), nl.get('N_CD', 0))
    nc1, nc2 = pool * sh1 * k1, pool * (1 - sh1) * k2
    ca1 = nl_tac['CAPCT'] if nc1 < nc2 else 0.0          # same rule as the expected score: only the team with fewer chances counters
    ca2 = other_tac['CAPCT'] if nc2 < nc1 else 0.0
    live = pool / slots
    # one chance moment: P(us +1), P(them +1) (never both)
    pa = live * (sh1 * k1 * (r1 + (1 - r1) * q1) + (1 - sh1) * k2 * (1 - r2) * (1 - q2) * ca1 * r1)
    pb = live * ((1 - sh1) * k2 * (r2 + (1 - r2) * q2) + sh1 * k1 * (1 - r1) * (1 - q1) * ca2 * r2)
    import numpy as _np
    P = _np.zeros((slots + 1, slots + 1)); P[0, 0] = 1.0
    for _ in range(slots):
        N = P * (1 - pa - pb)
        N[1:, :] += P[:-1, :] * pa
        N[:, 1:] += P[:, :-1] * pb
        P = N
    return P


def poisson_win_draw_loss(lambda_nl, lambda_o, max_goals=10):
    def pois_pmf(k, lam):
        lam = max(float(lam), 1e-6)
        return math.exp(-lam) * lam ** k / math.factorial(k)
    p_win = p_draw = p_loss = 0.0
    for h in range(max_goals + 1):
        ph = pois_pmf(h, lambda_nl)
        for a in range(max_goals + 1):
            p = ph * pois_pmf(a, lambda_o)
            if h > a: p_win += p
            elif h == a: p_draw += p
            else: p_loss += p
    total = p_win + p_draw + p_loss
    if total > 0: p_win, p_draw, p_loss = p_win / total, p_draw / total, p_loss / total
    return p_win, p_draw, p_loss

# ==============================================================================
# 5. AUTO-SOLVER & REVERSE-ENGINEERING ENGINE
# ==============================================================================
def hattrick_skill_band(displayed_level, floor=1.0):
    n = int(round(displayed_level))
    return (max(floor, float(n)), max(max(floor, float(n)), float(n) + 0.99))

HATTRICK_SKILL_WORDS = ['Non-existent', 'Disastrous', 'Wretched', 'Poor', 'Weak', 'Inadequate', 'Passable', 'Solid',
                         'Excellent', 'Formidable', 'Outstanding', 'Brilliant', 'Magnificent', 'World Class',
                         'Supernatural', 'Titanic', 'Extra-terrestrial', 'Mythical', 'Magical', 'Utopian', 'Divine']
HATTRICK_SKILL_WORD_OPTIONS = [f'{i} - {w}' for i, w in enumerate(HATTRICK_SKILL_WORDS)]

def skill_level_label(value):
    n = max(0, min(20, int(math.floor(float(value)))))
    return f'{n} - {HATTRICK_SKILL_WORDS[n]}'

_TSI_W = {'DE': 1.034, 'PM': 1.031, 'WI': 0.826, 'Pas': 1.035, 'SC': 1.038}


KEEPER_SH_PER_GK = 0.5   # set-pieces levels per goalkeeping level ahead of the age profile


def wage_main_skill(pos_code, age, spec=None, skills=None):
    """The skill that sets the wage: the one with the highest wage component, not
    simply the 'main' skill of the position. Playmaking pays far more per level than
    defending, winger, passing or scoring, so for OCD (DE≈PM), DFW (PM vs passing),
    WTM and experienced wingers the wage comes from PM. Uses the given skills, or the
    age profile of the position. Returns (skill, ambiguous): ambiguous when the
    runner-up is within 15% of the wage, so the profile can't tell them apart."""
    if pos_code == 'K':
        return 'GK', False
    if skills is None:
        prof = estimate_age_richtskills(int(age), spec)
        skills = prof.get(pos_code, prof.get('NFW', {}))
    comps = sorted(((lookup_wage(float(skills.get(k, 1.0) or 1.0), k), k)
                    for k in ('DE', 'PM', 'WI', 'Pas', 'SC')), reverse=True)
    (w1, k1), (w2, _) = comps[0], comps[1]
    return k1, (w1 > 0 and w2 >= 0.85 * w1)



def _ref_playing_age(ref_df, age):
    """Reference players of 36 and older mostly stopped playing (coaches, retired): their skills wear down, so they make
    a 34-35 year old look weaker than he is. Leave them out as peers, unless the player himself is that old."""
    try:
        if ref_df is None or getattr(ref_df, 'empty', True) or int(age) >= 36:
            return ref_df
        import pandas as _pd
        return ref_df[_pd.to_numeric(ref_df['Leeftijd'], errors='coerce').fillna(0) < 36]
    except Exception:
        return ref_df


def _ref_base_wage(ref_df):
    """Reference players marked abroad: their stored wage includes Hattrick's +20% bonus, so
    compare peers on the base wage (wage / 1.2)."""
    if ref_df is None or getattr(ref_df, 'empty', True) or 'Foreign' not in ref_df.columns:
        return ref_df
    try:
        import pandas as _pd
        d = ref_df.copy()
        ab = _pd.to_numeric(d['Foreign'], errors='coerce').fillna(0).astype(int) == 1
        d.loc[ab, 'Loon'] = _pd.to_numeric(d.loc[ab, 'Loon'], errors='coerce') / 1.2
        return d
    except Exception:
        return ref_df


def _without_player(ref_df, exclude_player):
    """Reference players minus the player being calculated (by PlayerID or name), so a player
    is never his own peer (an earlier result synced to the Reference DB would pull him back)."""
    if ref_df is None or getattr(ref_df, 'empty', True) or not exclude_player:
        return ref_df
    pid, name = (list(exclude_player) + [None, None])[:2]
    try:
        import pandas as _pd
        mask = _pd.Series(False, index=ref_df.index)
        if pid and 'PlayerID' in ref_df.columns and int(float(pid)) > 0:
            mask |= _pd.to_numeric(ref_df['PlayerID'], errors='coerce').fillna(0).astype(int) == int(float(pid))
        if name and 'Speler' in ref_df.columns:
            mask |= ref_df['Speler'].astype(str).str.strip().str.lower() == str(name).strip().lower()
        return ref_df[~mask].reset_index(drop=True)
    except Exception:
        return ref_df


def stamina_max(age=None):
    """Highest possible stamina (Schum, 'Stamina 2.0'): 9.4 up to 27; from 28 to 33 7/30 of a level
    less per year, from 34 on 14/30 per year (calculation scale 252/30 = 8.4 -> 9.4 on the normal scale)."""
    try:
        a = int(age)
    except (TypeError, ValueError):
        return 9.4
    calc = 252.0 / 30.0 - 7.0 / 30.0 * max(0, min(a, 33) - 27) - 14.0 / 30.0 * max(0, a - 33)
    return round(calc + 1.0, 3)


def stamina_middle(cond, age=None):
    """Middle of the displayed stamina level, within what's possible at this age:
    8 -> 8.5; formidable (9) runs 9.0-9.4 up to 27 -> 9.2. A value with decimals is used as it is."""
    c = float(cond)
    top = stamina_max(age)
    if c != int(c):
        return min(c, top)
    hi = min(c + 0.99, top)
    return round((c + max(hi, c)) / 2.0, 3) if c >= 9 or hi < c + 0.99 else c + 0.5

def estimate_htms_from_profile(age, days, tsi, wage, form, cond, is_foreign=False, spec='None', pos_code='NFW', fixed_sh=None, pre_ref_df=None, exclude_player=None, wage_skill=None, profile=None):
    """profile: this position's target skills for the player's country and age (e.g. from
    get_richtskills_for_age). Without it the built-in (Dutch) profile is used."""
    pos_code = normalize_position(pos_code)
    if not (isinstance(profile, dict) and profile):
        profile = None
    base_wage = (wage / 1.20) if is_foreign else float(wage)
    # A specialty adds 10% to the wage; without removing it the main skill comes out too high.
    if spec and str(spec).strip() not in ('Geen', 'None', '', 'nan'):
        base_wage /= 1.10
    age_wage_factor = max(0.10, 1.0 - 0.10 * (age - 28)) if age > 28 else 1.00
    norm_wage_28 = max(250.0, base_wage / age_wage_factor)

    if pos_code == 'K':
        classic_col = 'GK'
    elif 'CD' in pos_code:           classic_col = 'DE'
    elif pos_code == 'SHWB':         classic_col = 'DE'
    elif 'WB' in pos_code:           classic_col = 'DE'
    elif 'FW' in pos_code or pos_code == 'PNF': classic_col = 'SC'
    elif pos_code in ('NW', 'W', 'WTM', 'OW', 'DW', 'LW', 'RW'): classic_col = 'WI'
    else:                            classic_col = 'PM'
    # The wage follows the best-paid skill, which is PM for e.g. OCD, DFW and WTM.
    primary_col, main_ambiguous = wage_main_skill(
        pos_code, age, spec, skills={k: profile[k] for k in ('DE', 'PM', 'WI', 'Pas', 'SC') if k in profile} if profile else None)
    if wage_skill in ('DE', 'PM', 'WI', 'Pas', 'SC'):      # forced (TDFW: tried both ways)
        primary_col, main_ambiguous = wage_skill, False

    primary_skill = 5.0
    if pos_code == 'K':
        # Keeper: GK from TSI = 3·(GK−1)^3.359·√(form−1)
        try:
            # Hattrick shows form as a whole number: use the middle of that level
            # (the bottom, e.g. 6.00, would give the highest possible GK).
            form_mid = min(form + 0.5, 8.0) if float(form) == int(form) else float(form)  # 8 = max form
            form_f = max(form_mid - 1.0, 0.1) ** 0.5
            age_tsi_f_k = max(0.1, 1 - 0.1 * (age - 30)) if age > 30 else 1.0
            gk_from_tsi = 1.0 + (tsi / (3.0 * form_f * age_tsi_f_k)) ** (1.0 / 3.359)
            primary_skill = round(min(25.0, max(1.0, gk_from_tsi)), 2)
        except Exception:
            pass
    else:
        for level in range(5, 25):
            w_base = WAGE_TABLE[level].get(primary_col, 350.0)
            w_next = WAGE_TABLE[min(level + 1, 25)].get(primary_col, 350.0)
            if norm_wage_28 >= w_base and norm_wage_28 < w_next:
                try:
                    decimal = (math.log(norm_wage_28 / w_base) / math.log(w_next / w_base)) ** (1.0 / WAGE_SUB_P)
                    primary_skill = float(level) + max(0.0, min(0.99, decimal))
                except Exception: primary_skill = float(level)
                break
            elif level == 24 and norm_wage_28 >= w_next: primary_skill = 25.0

    # Shown in the diagnostics as "inferred primary at birthday": the wage is 250 + (main skill +
    # 50% (40% above 20,300) of the other skills) x the set-pieces bonus, so the other skills and
    # set pieces (from the age profile) come off first. Dutch U21 test: error 0.17 -> 0.08.
    # The solver keeps steering with primary_skill above: its old overestimate happens to offset
    # training since the birthday, and switching made late-in-the-year results worse.
    primary_at_birthday = primary_skill
    if pos_code != 'K':
        try:
            _prof = profile or estimate_age_richtskills(int(age), spec).get(pos_code, {}) or {}
            _sec = sum(lookup_wage(float(_prof[k]), k) for k in ('DE', 'PM', 'WI', 'Pas', 'SC')
                       if k != primary_col and k in _prof)
            _sh_mul = 1.0 + 0.25 * float(_prof.get('SH', 1.0)) / 100.0
            _raw = max(0.0, norm_wage_28 - 250.0) / _sh_mul
            _m = 0.40 if (_raw - 0.5 * _sec) > 20300 else 0.50
            _w = max(0.0, _raw - _m * _sec) + 250.0
            for level in range(5, 25):
                w_base = WAGE_TABLE[level].get(primary_col, 350.0)
                w_next = WAGE_TABLE[min(level + 1, 25)].get(primary_col, 350.0)
                if w_base <= _w < w_next:
                    primary_at_birthday = level + max(0.0, min(0.99, (math.log(_w / w_base) / math.log(w_next / w_base)) ** (1.0 / WAGE_SUB_P)))
                    break
        except Exception:
            pass

    est_form = min(form + 0.5, 8.0) if form == float(int(form)) else form  # 8 = max form
    est_cond = stamina_middle(cond, age)
    form_factor = max(est_form - 1.0, 0.1) ** 0.5
    cond_factor = max(est_cond - 1.0, 0.1) ** 0.5
    age_tsi_factor = (max(0.1, 1 - 0.1 * (age - 30)) if age > 30 else 1.0) if pos_code == 'K' else (max(0.125, 1 - 0.125 * (age - 27)) if age > 27 else 1.0)

    sum_field = ((tsi * 1000.0) / max(0.001, (cond_factor * form_factor * age_tsi_factor))) ** 0.5
    primary_weight = (3.0 * max(primary_skill - 1.0, 0.0) ** 3.359) if pos_code == 'K' else (1.031 * (max(primary_skill - 1.0, 0.0) ** 3.0))
    residual_linear = max(0.0, sum_field - primary_weight)
    n_secondaries = 4.0
    avg_secondary_weight = 0.975

    if pos_code == 'K':
        # Keeper secondaries (SH, DE, Pas) are invisible in TSI: use the age profile.
        _kb = estimate_age_richtskills(age).get('K', {})
        secondary_avg = round(
            (_kb.get('SH', 13.0) * 0.4 + _kb.get('DE', 5.0) * 0.4 + _kb.get('Pas', 2.5) * 0.2), 2
        )
    else:
        secondary_avg = (residual_linear / (n_secondaries * avg_secondary_weight)) ** (1.0 / 3.0) + 1.0 if residual_linear > 0 else 3.0

    age_bench = estimate_age_richtskills(age)
    pos_bench = profile or age_bench.get(pos_code, age_bench.get('NFW', {}))
    bench_sh = float(pos_bench.get('SH', 5.0))

    if pos_code in ('K', 'SHWB'):
        if fixed_sh is not None and fixed_sh > bench_sh * 0.7:
            est_sh = fixed_sh
        else:
            est_sh = bench_sh
    else:
        if fixed_sh is not None and fixed_sh > 1.0:
            est_sh = fixed_sh
        else:
            est_sh = bench_sh

    # Wingers too: the classic formula left out their defending/scoring left-overs
    # (Dutch U21 wingers: DE 6-7, SC 3-7), so their HTMS came out ~190 too low.
    if pos_code != 'K' and (primary_col != classic_col or pos_code in ('NW', 'WTM')):
        # Age profile with the wage skill set, the other skills scaled to fit TSI.
        prof = {k: float(pos_bench.get(k, 1.0)) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']}
        prof[primary_col] = primary_skill
        others = [k for k in prof if k != primary_col and prof[k] > 1.5]
        base = sum(_TSI_W[k] * (prof[k] - 1.0) ** 3 for k in others)
        resid = sum_field - _TSI_W[primary_col] * max(primary_skill - 1.0, 0.0) ** 3
        f = min(1.6, max(0.3, (max(resid, 0.0) / base) ** (1.0 / 3.0))) if base > 0 else 1.0
        for k in others:
            prof[k] = 1.0 + (prof[k] - 1.0) * f
        calc_htms = calculate_htms_ability(1.0, prof['DE'], prof['PM'], prof['WI'], prof['Pas'], prof['SC'], est_sh)
    elif pos_code == 'K':
        bench_de = float(pos_bench.get('DE', 12.0))
        bench_gk = float(pos_bench.get('GK', 21.0))
        # A keeper further ahead in goalkeeping for his age has usually had more keeper
        # training, so his set pieces are a bit further along too (half a level per GK level).
        proportional_sh = max(1.0, est_sh + KEEPER_SH_PER_GK * (primary_skill - bench_gk))
        # Include the profile's small left-overs (PM/WI/Pas/SC ~2-2.5): the solver gives keepers
        # those too, and leaving them out made the HTMS guess ~60 too low, which then pushed
        # set pieces down to their lower limit (e.g. 12.5 for a 21-year-old).
        calc_htms = calculate_htms_ability(primary_skill, bench_de,
                                           float(pos_bench.get('PM', 1.0)), float(pos_bench.get('WI', 1.0)),
                                           float(pos_bench.get('Pas', 1.0)), float(pos_bench.get('SC', 1.0)),
                                           proportional_sh)
    elif 'FW' in pos_code or pos_code == 'PNF':
        calc_htms = calculate_htms_ability(1.0, secondary_avg * 0.5, secondary_avg * 0.9, secondary_avg, secondary_avg, primary_skill, est_sh)
    elif pos_code == 'SHWB':
        # SHWB: DE from wage, SH and WI from the age profile.
        bench_wi = float(pos_bench.get('WI', 14.0))
        calc_htms = calculate_htms_ability(1.0, primary_skill, secondary_avg * 0.4, bench_wi, secondary_avg * 0.3, 1.0, est_sh)
    elif 'CD' in pos_code or 'WB' in pos_code:
        calc_htms = calculate_htms_ability(1.0, primary_skill, secondary_avg, secondary_avg * 0.8, secondary_avg * 0.8, 2.0, est_sh)
    elif pos_code in ('NW', 'W', 'WTM', 'OW', 'DW', 'LW', 'RW'):
        calc_htms = calculate_htms_ability(1.0, secondary_avg * 0.8, secondary_avg, primary_skill, secondary_avg * 0.9, 2.0, est_sh)
    elif pos_code in ('DFW', 'TDFW'):
        calc_htms = calculate_htms_ability(1.0, secondary_avg * 0.4, secondary_avg * 0.7, secondary_avg * 0.8, primary_skill, secondary_avg * 0.7, est_sh)
    else:
        calc_htms = calculate_htms_ability(1.0, secondary_avg, primary_skill, secondary_avg * 0.8, secondary_avg * 0.9, 2.0, est_sh)

    # The profile-based estimate already has the right shape: no calibration.
    HTMS_CALIBRATION = 1.00 if (pos_code == 'K' or primary_col != classic_col or pos_code in ('NW', 'WTM')) else 1.13
    est_htms = round(calc_htms * HTMS_CALIBRATION)
    est_htms28 = calculate_htms_potential(age, days, est_htms)

    # Blend with Reference DB peers of similar TSI/wage/age (70% peers, 30% formula).
    # Not for SHWB/K: their SH is invisible in TSI/wage, so peers differ too much.
    # Not from KNN_HTMS_MAX_AGE on: for seniors TSI and wage are scaled down by age, and peers with
    # the same TSI/wage are weaker players. Tested on 21 Dutch NT seniors (30-33): peers pulled the
    # HTMS estimate ~600 too low (e.g. 1732 vs real 2426), and the solver then wiped out the secondaries.
    knn_htms = None
    knn_count = 0
    if pos_code not in ('SHWB', 'K') and int(age) < KNN_HTMS_MAX_AGE:
        try:
            ref_df = pre_ref_df if pre_ref_df is not None else None
            if ref_df is None:
                from data_layer import get_reference_players_df
                ref_df = get_reference_players_df()
            ref_df = _ref_playing_age(_ref_base_wage(_without_player(ref_df, exclude_player)), age)
            if ref_df is not None and not ref_df.empty:
                same_pos = ref_df[ref_df['Positie'] == pos_code].copy()
                if len(same_pos) < 5:
                    same_pos = ref_df.copy()
                if len(same_pos) >= 3:
                    tsi_s  = max(ref_df['TSI'].std(), 1)
                    wage_s = max(ref_df['Loon'].std(), 1)
                    age_s  = max(ref_df['Leeftijd'].std(), 1)
                    same_pos = same_pos.copy()
                    same_pos['_dist'] = (
                        ((same_pos['TSI']      - tsi)  / tsi_s)  ** 2 +
                        ((same_pos['Loon']     - wage) / wage_s) ** 2 +
                        ((same_pos['Leeftijd'] - age)  / age_s)  ** 2
                    ) ** 0.5
                    nearest = same_pos.nsmallest(7, '_dist')
                    if len(nearest) >= 3:
                        knn_htms  = nearest['HTMS'].mean()
                        knn_count = len(nearest)
        except Exception:
            pass

    if knn_htms is not None and knn_htms > 0:
        est_htms  = round(0.30 * est_htms + 0.70 * knn_htms)
        est_htms28 = calculate_htms_potential(age, days, est_htms)

    diagnostics = {
        'base_wage': base_wage, 'age_wage_factor': age_wage_factor, 'norm_wage_28': norm_wage_28,
        'primary_col': primary_col, 'primary_ambiguous': main_ambiguous, 'inferred_primary': primary_skill,
        'inferred_primary_birthday': primary_at_birthday, 'form_factor': form_factor,
        'cond_factor': cond_factor, 'age_tsi_factor': age_tsi_factor, 'residual_secondary_avg': secondary_avg,
        'est_sh': est_sh,
        'est_htms': int(est_htms), 'est_htms28': int(est_htms28) if isinstance(est_htms28, (int, float)) else 0,
        'active_target_htms': int(est_htms), 'active_target_htms28': int(est_htms28) if isinstance(est_htms28, (int, float)) else 0,
        'knn_ref_count': knn_count,
    }
    return int(est_htms), int(est_htms28), diagnostics

def profile_shape_solution(pos_code, age, days, spec, form, cond, target_tsi, target_wage,
                           is_foreign, bench, current_skills=None, skill_bands=None, main_now=None):
    """Option 4: the position's age profile kept in shape. The skill that sets the wage is
    scaled to fit the wage; all other skills share one scale factor fitted to TSI. Form and
    stamina use the middle of their displayed level. Keepers: one factor fitted to TSI."""
    pos_code = normalize_position(pos_code)
    keys = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
    f = min(float(form) + 0.5, 8.0) if float(form) == int(form) else float(form)
    c = stamina_middle(cond, age)
    base_w = float(target_wage or 0) / (1.20 if is_foreign else 1.0)
    b = {k: float((bench or {}).get(k, 1.0) or 1.0) for k in keys}
    known = {k: float(v) for k, v in (current_skills or {}).items() if v is not None and float(v) > 0}
    bands = skill_bands or {}

    def make(km, ks, main):
        out = {}
        for k in keys:
            if k in known:
                out[k] = known[k]
                continue
            v = 1.0 + (b[k] - 1.0) * (km if k == main else ks)
            if bands.get(k) is not None:
                v = min(max(v, bands[k][0]), bands[k][1])
            out[k] = min(25.0, max(1.0, v))
        if pos_code == 'K' and 'SH' not in known and bands.get('SH') is None and int(age) >= 21:
            out['SH'] = max(out['SH'], 14.0)   # same keeper rule as the solver
        return out

    def tsi_of(sk):
        return calculate_tsi_for_form(age, f, c, *[sk[k] for k in keys[:6]])

    def wage_of(sk):
        return calculate_exact(age, days, spec, f, c, *[sk[k] for k in keys])[3]

    def solve(fn, target, lo=0.2, hi=3.0, it=40):
        if fn(lo) >= target:
            return lo
        if fn(hi) <= target:
            return hi
        for _ in range(it):
            mid = (lo + hi) / 2
            if fn(mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    if pos_code == 'K' or base_w <= 0 or target_tsi <= 0:
        fit_tsi = target_tsi > 0
        k = solve(lambda k: (tsi_of if fit_tsi else wage_of)(make(k, k, None)),
                  target_tsi if fit_tsi else base_w)
        sk = make(k, k, None)
    else:
        main = wage_main_skill(pos_code, age, spec, skills=b)[0]

        def km_for(ks):
            return solve(lambda km: wage_of(make(km, ks, main)), base_w, it=30)

        def miss(ks):
            cand = make(km_for(ks), ks, main)
            return (abs(tsi_of(cand) - target_tsi) / max(target_tsi, 1.0)
                    + abs(wage_of(cand) - base_w) / max(base_w, 1.0))

        # TSI isn't monotone in the shared factor once the wage is held fixed (more from the
        # others means less from the wage skill), so scan, then refine around the best.
        grid = [0.25 + 0.025 * i for i in range(111)]          # 0.25 .. 3.0
        scored = [miss(k) for k in grid]

        def refine(k0):
            lo_k, hi_k = max(0.2, k0 - 0.025), min(3.0, k0 + 0.025)
            for _ in range(25):
                m1, m2 = lo_k + (hi_k - lo_k) / 3, hi_k - (hi_k - lo_k) / 3
                if miss(m1) < miss(m2):
                    hi_k = m2
                else:
                    lo_k = m1
            k = (lo_k + hi_k) / 2
            return miss(k), k

        # Every local dip of the scan is refined: several factors can fit TSI and wage
        # (e.g. a winger whose playmaking grows until it becomes the wage skill).
        dips = [grid[i] for i in range(len(grid))
                if scored[i] <= (scored[i - 1] if i > 0 else 9e9) and scored[i] <= (scored[i + 1] if i + 1 < len(grid) else 9e9)]
        fits = [refine(k) for k in dips] or [refine(grid[scored.index(min(scored))])]
        floor_miss = min(m for m, _ in fits)
        good = [k for m, k in fits if m <= floor_miss + 0.004]

        def keeps_main(k):
            cand = make(km_for(k), k, main)
            return wage_main_skill(pos_code, age, spec,
                                   skills={x: cand[x] for x in ('DE', 'PM', 'WI', 'Pas', 'SC')})[0] == main
        # Prefer fits where the wage skill is still the best-paid one, then the one closest
        # to the pure profile shape (both factors alike).
        good = [k for k in good if keeps_main(k)] or good
        ks = min(good, key=lambda k: abs(km_for(k) - k))
        sk = make(km_for(ks), ks, main)

        # The wage only fits the skills of the birthday. If today's TSI is higher than any
        # birthday shape can reach (training since then), grow every skill by the same factor
        # until TSI matches: the profile shape stays, the extra is training since the birthday.
        if target_tsi > 0 and tsi_of(sk) < target_tsi * 0.995:
            base_sk = dict(sk)

            def grown(g):
                return {k: (base_sk[k] if (k in known or bands.get(k) is not None)
                            else min(25.0, 1.0 + (base_sk[k] - 1.0) * g)) for k in keys}
            lo_g, hi_g = 1.0, 2.0
            for _ in range(40):
                mg = (lo_g + hi_g) / 2
                if tsi_of(grown(mg)) < target_tsi:
                    lo_g = mg
                else:
                    hi_g = mg
            sk = grown((lo_g + hi_g) / 2)

    # Trained since the birthday: the wage skill gets its birthday value + typical training
    # (main_now); the other skills keep the profile shape and are refitted to today's TSI.
    if main_now is not None and pos_code != 'K' and target_tsi > 0:
        _main = wage_main_skill(pos_code, age, spec, skills=b)[0]
        if _main not in known:
            _fixed = max(float(sk[_main]), float(main_now))

            def _with(ks):
                d = make(1.0, ks, None)
                d[_main] = _fixed
                return d
            # If TSI can't hold the full trained value (other skills already at their lowest
            # shape), step the main skill down to the highest value TSI allows.
            _start = float(sk[_main])
            _min_k = 0.8   # keep the profile shape: other skills at least 80% of the profile
            while _fixed > _start and tsi_of(_with(_min_k)) > target_tsi:
                _fixed = max(_start, _fixed - 0.02)
            lo_k, hi_k = _min_k, 3.0
            if tsi_of(_with(lo_k)) <= target_tsi <= tsi_of(_with(hi_k)):
                for _ in range(40):
                    mk = (lo_k + hi_k) / 2
                    if tsi_of(_with(mk)) < target_tsi:
                        lo_k = mk
                    else:
                        hi_k = mk
                sk = _with((lo_k + hi_k) / 2)

    _, c_tsi, _, c_wage, _, c_htms, c_htms28 = calculate_exact(age, days, spec, f, c, *[sk[k] for k in keys])
    return dict(sk, Vorm=f, Cond=c, Calc_TSI=c_tsi, Calc_Wage=c_wage * (1.20 if is_foreign else 1.0),
                Calc_HTMS=c_htms, Calc_HTMS28=c_htms28)



KNN_HTMS_MAX_AGE = 28     # from this age on, the HTMS estimate uses the formula only (no Reference DB peers)
SENIOR_SH_MIN_AGE = 28    # from this age on, set pieces stay near the profile (outside SHWB/K)
SENIOR_SH_BELOW = 3.0     # ... at most this many levels below the profile
# Seniors with HTMS unknown: pull of set pieces towards the profile (0 = off). Tested on 10 Dutch NT
# senior wingers: set pieces error 3.6 -> 2.6 (1e6), but the other skills got worse (0.80 -> 0.96,
# scoring 1.8 -> 2.4): set pieces balance the HTMS estimate and the wage. A lower cap
# (SENIOR_SH_ABOVE 2 or 1 instead of 4) was worse too (0.99-1.12). So off.
SENIOR_SH_PULL = 0.0
SENIOR_HTMS_EST_WEIGHT = 1e8  # 28+, HTMS unknown: weight of the HTMS estimate (None = 1e9 as younger players). 35 Dutch NT seniors: error 1.13 -> 0.85 (NIM 1.70 -> 0.84, NFW 0.47 -> 0.36, NW 1.14 -> 1.06)
# Contribution shape, seniors, HTMS unknown: the HTMS estimate comes from the (Dutch) profile; for a weaker
# senior it can't be reached and it dragged the leftover TSI into whatever skill gives most HTMS per TSI.
# 36 weak test seniors (12 positions): skill error 1.33 -> 1.18 at 1e7 (keepers 1.79 -> 0.67); 1e6 was a bit
# better on average (1.14) but dropped NIM defending to ~3 (Hodzic).
CONTRIB_SENIOR_HTMS_EST_WEIGHT = 1e7
SENIOR_WAGE_CEIL_AGE = 30      # from this age today's skills may earn at most SENIOR_WAGE_CEIL x the wage
SENIOR_WAGE_CEIL = 1.005
SENIOR_WAGE_LIMIT_WEIGHT = 1e11   # as strong as TSI: the wage is a hard fact
SENIOR_WAGE_DROP_PER_WEEK = 0.003  # 28+: today's skills may earn at most 0.3%/week since the birthday less than the wage
SENIOR_SH_ABOVE_POS = {'NW': 1.0, 'WTM': 1.0, 'NCD': 1.0}  # senior wingers: set pieces at most 1 above the profile (Onkruud)
SENIOR_SH_ABOVE = 1.0     # ... and this many above. Was 4.0: set pieces are invisible in TSI and only
                          # 0.25%/level in the wage, so with HTMS unknown the solver filled its HTMS estimate
                          # with set pieces and they drifted to the top (NFW 33 / PDIM 30 / PNF 29: 12.3-12.5
                          # against a profile of 9). NW/WTM/NCD already had 1.0 (SENIOR_SH_ABOVE_POS).
# Senior wingers (NW/WTM from SENIOR_WING_MIN_AGE):
#  - winger minus playmaking stays within SENIOR_WING_GAP_TOL of the profile's gap (skills decline
#    together; before, the whole decline came out of winger: Bouderbala 32 as NW, WI 15.75);
#  - defending and passing stay near the profile (SENIOR_WING_BOUNDS): defending went up to 12 and
#    took spare TSI (+1.5 too high), passing had no floor (dropped to 2.9).
# Test on 10 Dutch NT senior wingers (29-33, real skills, simulated TSI/wage), option 1, solved as NW:
# error per skill 1.55 -> 1.30; without set pieces 1.15 -> 0.79 (mono 1.26 -> 0.76);
# defending error 1.45 -> 0.37 (bias +1.38 -> +0.10), passing 1.62 -> 0.86, winger 0.66 -> 0.47.
# A wider defending floor (1.5 below) gave 0.92; gap rule alone 1.13.
SENIOR_WING_MIN_AGE = 28
# Seniors: per position, (levels below, levels above) the profile a skill may go. Fitted on Dutch NT
# seniors (PNF Esch/Lepolder, NWB Tamaela, 6 NFW).
SENIOR_POS_MIN_AGE = 28
SENIOR_MAIN_FROM_BIRTHDAY_AGE = 28  # from this age the main skill is read from the wage minus the other skills
SENIOR_MAIN_FROM_BIRTHDAY_SKIP = {'NFW'}  # tested: NFW better with the whole-wage value (0.36 vs 0.45)
# Senior targets (the solver aims at min(profile, value)) and soft floors (levels below the profile).
# NWB: TSI can't tell winger from passing, and the U profile's passing 10.8 at 32 took winger's TSI
# (Tamaela U, 32: WI 16.4 / Pas 9.0 vs real 17.2 / 7.5).
# NWB winger: soft floor 1 above the profile, at most 17 (U profile 16 at 32; Tamaela U real 17.23);
# playmaking at most 0.5 above the profile. Tamaela (32, actual data): DE 18.39 / PM 10.92 / WI 16.88 ->
# DE 18.28 / PM 11.23 / WI 16.97 (real at 31: 18.25 / 11.12 / 17.23).
# NCD: Dutch NT seniors (30-31) have PM 16.7-17.3 and passing 7.3-8.4 (profile: PM 15-15.7, passing 9-12),
# and defending 18.2-18.5. Without this, playmaking came out ~0.9 low, passing ~2.5 high, and defending
# ~0.25 high to make up the wage (Duco Heming: DE 18.56 / PM 16.08 / Pas 11.30, real 18.24 / 17.23 / 7.27).
SENIOR_POS_TARGETS = {'NWB': {'Pas': 8.0}, 'NCD': {'Pas': 8.0, 'DE': 18.25}}
SENIOR_POS_SET = {'NCD': {'PM': 16.9}}   # seniors: the solver aims at exactly this (also used to read the wage)
SENIOR_POS_SOFT_FLOOR = {'NWB': {'WI': -1.0}, 'NCD': {'PM': -1.5}}       # levels below the profile (negative = above)
SENIOR_POS_SOFT_FLOOR_MAX = {'NWB': {'WI': 17.0}, 'NCD': {'PM': 17.0}}
SENIOR_POS_BOUNDS = {
    'PNF': {'PM': (1.0, 1.0), 'WI': (2.0, 3.0), 'Pas': (3.0, 2.0)},
    'NFW': {'PM': (1.0, 1.5), 'WI': (1.5, 1.0)},
    'NWB': {'PM': (1.0, 0.5), 'WI': (1.0, 1.5)},
    'NCD': {'PM': (1.0, 1.0), 'Pas': (2.0, 0.5)},
    # NIM: TSI can't tell defending from passing; Dutch NT seniors: DE 10.1-13.0, passing 12.7-14.9, SC 6.9-9.1.
    'NIM': {'DE': (1.5, 1.5), 'Pas': (1.5, 2.0), 'SC': (1.5, 2.5)},
    # DFW (incl. former TDFW): winger and defending are left-overs (Dutch senior TDFs: WI 6.4-7.3, DE 3-4.5);
    # without limits spare TSI went there (WI 10.5, DE 5.5 on profile-like test players).
    'DFW': {'PM': (1.0, 1.0), 'WI': (1.5, 1.0), 'DE': (1.0, 1.0), 'Pas': (1.0, 1.5)},
}
SENIOR_WING_GAP_TOL = 1.0
SENIOR_WING_GAP_WEIGHT = 1e7  # 0 = off
# How far winger may drop below the profile's gap. NW: a normal winger never has winger below
# playmaking + the profile's gap (0 at 29, +0.2 from 30), held firmly (1e9). 10 Dutch NT seniors
# (winger - playmaking -0.12 to +1.22): winger error 0.47 -> 0.33, playmaking 0.18 -> 0.11, all skills
# without set pieces 0.79 -> 0.83 (same within noise); before, winger came out up to 0.7 below PM.
SENIOR_WING_GAP_BELOW = {'NW': 0.0, 'WTM': 1.0}
SENIOR_WING_BELOW_WEIGHT = {'NW': 1e9}  # per position: weight of that lower limit (default SENIOR_WING_GAP_WEIGHT)
SENIOR_WING_PASS_CAP = False  # senior wingers: passing cap = profile + 2 instead of 9 (tested: worse, 0.92 -> 1.19)
# Senior NW/WTM passing: fixed range (None = profile -2 / +3.5). 6-9.5 (Onkruud): 10 Dutch NT seniors
# all skills without set pieces 0.83 -> 0.80, defending 0.72 -> 0.49, passing 1.08 -> 1.23
# (7 of the 10 have real passing 10.2-12.0). 6-9 was worse (1.11).
# Senior NW/WTM passing: target 7.5 and range 6-8 (was profile 10-11 and range 6-9). Bouderbala (32, healthy
# TSI 289,790): DE 9.28 / Pas 9.00 / SC 7.50 -> DE 10.00 / Pas 7.88 / SC 7.48 (real at 30: 10.44 / 7.73 / 7.07).
# Current Dutch NT wingers (11): error 0.96 -> 0.90; older ones with passing 10-12 come out lower (1.15 -> 1.53).
SENIOR_WING_PAS_TARGET = 7.5   # None = profile
SENIOR_WING_PAS_RANGE = (6.0, 8.0)
SENIOR_WING_BOUNDS = {'DE': (2.5, 0.5), 'Pas': (2.0, 3.5)}  # hard limits: levels below / above the profile ({} = off)
# Soft floors (levels below the profile) for senior NW/WTM: defending/scoring normally stay above these,
# but may go lower when TSI is too low for winger >= playmaking (that rule weighs 1e9, these 1e7).
# DE soft floor at the profile itself (was 1 below): Kromdijk (32) DE 9.06 -> 10.00 (real at 31: 10.12),
# 17 Dutch senior wingers: defending error 0.74 -> 0.54, all skills 1.12 -> 1.10.
SENIOR_WING_SOFT_FLOOR = {'DE': 0.0, 'SC': 3.0}
SENIOR_WING_SOFT_WEIGHT = 1e7
SENIOR_WING_SEC_BELOW = 5.0   # senior NW/WTM: DE/Pas/SC hard floor this far below the profile (soft floor above)
SENIOR_PASS_MIN_AGE = 28  # from this age on, the passing cap of forwards follows the profile
FORM_MID_WEIGHT = 1e5     # pull of form/stamina towards the middle of their displayed level
STAMINA_MID_WEIGHT = 1e8  # stamina: middle of its level unless TSI/wage clearly say otherwise (neutral on accuracy, realistic stamina)
# PDIM: a stronger pull (1e8) gave the most realistic builds and better accuracy on simulated PDIMs;
# for inner mids and WTMs it made results worse, so only for PDIM.
FORM_MID_WEIGHT_POS = {'PDIM': 1e8}
SENIOR_WAGE_FLOOR_WEIGHT = 1e11
SENIOR_WAGE_DROP_PER_WEEK = 0.005  # 28+: today's skills may earn at most 0.5% less per week since the birthday (None = no limit)
WAGE_LIMIT_WEIGHT = 1e9    # wage for today's skills: above the training ceiling / below the actual wage
# Tested on 132 young Reference DB players (Oct 2026); kept at the values that tested best:
# MAIN_TARGET_WEIGHT 1e11: main skill inside its level 55% -> 59%, but the other skills ~0.03 worse.
# MULTI_MAIN_FACTOR 0.5 (multi option: half the training into the main skill): option 2 worse.
# HTMS_STRAT_SCALE {'2': 1.06, '3': 0.92} (more/less total skill for multi/mono): both worse.
# TSI + wage alone can't tell a mono from a multi; these per-option pushes only add error.
MAIN_TARGET_WEIGHT = 1e10  # pull of the main skill towards its training target
MONO_MAIN_WEIGHT = 1e11    # option 3 (mono): pull of the main skill to the top of its allowed range (0 = off)
# Mono's pull to the top of the range is as strong as TSI, so it beat the wage ceiling (1e9): a 29-year-old
# NIM came out at PM 18.7 with today's skills earning 15% over his wage. The wage ceilings are this much
# stronger (all options; options 1/2 and the non-target estimate rarely touch them), so the main skill
# stops where the wage stops it. Test (35 players): mono wage overshoot 5.7% (max 29%) -> 0.02%,
# mono main-skill error 0.44 -> 0.27; options 1 and 2 unchanged.
MONO_WAGE_CEIL_MULT = 1e3
# Lowest build (all secondary skills at their lower limits) above this x target TSI: lower the limits
# so that the lowest build lands at FEASIBLE_TSI_AIM x target TSI (room left for the solver).
FEASIBLE_TSI_MARGIN = 1.01
FEASIBLE_TSI_AIM = 0.97
MONO_MAIN_PUSH = 0.0       # option 3 (mono): reward per level of main skill (0 = off)
MULTI_MAIN_PULL = 0.0      # option 2 (multi): penalty per level of main skill (0 = off)
WIDEN_FOR_TSI = True      # raise capped secondaries when TSI can't be reached next to a wage-fitting main skill
WAGE_EXPECT_WEIGHT = 1e10   # options 1/2, under 28: pull today's wage to the expected one (0 = off)
RETRY_WAGE_MULT = 1e3        # ...and holds the wage limits this much harder (the wage is a hard fact)
RETRY_PROFILE_MULT = 1e4     # ...and follows that lifted profile this much more firmly (else HTMS-estimate pull wins)
RETRY_LIFT = True           # that re-solve aims the secondaries at the profile lifted evenly to fit TSI
RELAX_CAPS_ON_WAGE = True   # re-solve with left-over caps lifted when every option breaks the wage ceiling
MULTI_LOW_SHARE = 0.0     # option 2 (multi): share of the way down to the lowest main skill the wage allows. 0.5 tested:
#   own multi-skilled club players main error 0.56 -> 0.49, but 108 NT players from 6 countries 0.39 -> 0.62. Off;
#   the range itself is still worked out and shown ("Possible: x - y").
MULTI_MAIN_FACTOR = 0.0    # option 2 (multi): share of option 1's training gain that goes to the main skill.
                           # 0.0 (was 1.0, Oct 2026): multi is the LOW end for the main skill (about its birthday
                           # value from the wage, others higher), option 1 / mono the high end TSI allows. Only for
                           # players under 28 who are past their birthday; seniors have no training range.
HTMS_STRAT_SCALE = {}      # per option ('1','2','3'): scale on the estimated HTMS (only when HTMS is unknown)
TRAINED_SHARE = 0.96  # players train every week; only a few weeks lost to injury over 5 seasons (~4%)
# The skill that gets the training once the main skill can't reach its next level before 22.
SECONDARY_TRAINED = {'PDIM': {'DE': 0.35, 'Pas': 0.65}, 'NCD': 'PM', 'OCD': 'PM', 'CAD': 'Pas', 'NIM': 'Pas', 'OIM-Q': 'Pas', 'OIM-H': 'Pas',
                     'NW': 'PM', 'NFW': 'PM', 'PNF': 'PM', 'DFW': 'Pas', 'TDFW': 'Pas', 'NWB': 'WI', 'SHWB': 'WI'}
# Positions that switch training to their secondary skill once the next whole level of the
# main skill is out of reach before 22 (PDIM: PM 16 at 21 -> trains defending). A player close
# to a whole level still reaches it when training allows. Keepers keep training goalkeeping.
REACHABLE_LEVEL_RULE = {'NCD', 'OCD', 'CAD', 'NWB', 'SHWB', 'NW', 'NIM', 'OIM-Q', 'OIM-H', 'PDIM', 'NFW', 'PNF', 'DFW', 'TDFW'}
# The skill each position is trained in. When that isn't the skill that sets the wage (a WTM is
# paid for PM but trained in winger), the wage skill stays near its birthday value instead.
# Share of the training weeks that goes to that skill (the rest trains the second skill: a CD
# alternates defending with playmaking, a WB defending with winger, ...). Mono option = 100%.
# Calibrated on the Reference DB (Oct 2026, ~200 players aged 17-23 with whole-level skills): the
# wage gives the main skill on the birthday, the DB gives today's level, and the share below puts
# the most players inside their real level. Was a hand-typed 0.85 / 0.6 for most positions:
#   NIM 0.85 -> 1.0, NFW 0.85 -> 0.95, NCD 0.6 -> 0.9, NWB 0.6 -> 0.95.
#   Held-out check (fit on half the players, scored on the other half, 200 random splits):
#   inside the real level 54% -> 64% (NIM 60 -> 70%, NWB 27 -> 71%, NCD 30 -> 46%, NFW 59 -> 60%).
#   Kept: OIM-Q/H 0.85, NW 0.8, PNF 0.85, PDIM 0.65 (a new value did not hold up on the other half);
#   WTM, OCD, SHWB (no data: WTM is paid for PM but trained in WI; the DB's "SHWBs" were plain WBs).
#   Ceiling: 93% of players fit SOME share between 0.5 and 1.2, so one number per position can't
#   get much past ~65-70%: players simply differ in how much they trained.
# Solver test (132 young players, option 1): main skill inside its real level 52% -> 55%,
# the other skills unchanged.
TRAINED_WEEK_SHARE = {'K': 1.0, 'WTM': 0.75, 'NCD': 0.9, 'OCD': 0.6, 'CAD': 0.8, 'NWB': 0.95, 'SHWB': 0.6, 'NW': 0.8,
                      'NIM': 1.0, 'OIM-Q': 0.85, 'OIM-H': 0.85, 'PDIM': 0.65, 'NFW': 0.95, 'PNF': 0.85}
TRAINED_SKILL = {'K': 'GK', 'NCD': 'DE', 'OCD': 'DE', 'CAD': 'DE', 'NWB': 'DE', 'SHWB': 'DE', 'NW': 'WI', 'WTM': 'WI',
                 'NIM': 'PM', 'OIM-Q': 'PM', 'OIM-H': 'PM', 'PDIM': 'PM', 'NFW': 'SC', 'PNF': 'SC'}


# Hattrick lowers the TSI of an injured player. Fitted on two Dutch NT players (healthy TSI just before
# the injury vs the injured TSI, same age/form/stamina): shown TSI = healthy / (1 + 0.15 x weeks).
#   Bouderbala, 2 weeks: 289,790 -> 221,590 (x0.765; formula x0.769, healthy estimate -0.6%)
#   Frijters,   3 weeks: 357,650 -> 248,590 (x0.695; formula x0.690, healthy estimate +0.8%)
INJURY_TSI_PER_WEEK = 0.15


def tsi_age_factor(age, pos_code='NFW'):
    """Hattrick's TSI age factor (same as in the solver): keepers from 31, others from 28."""
    age = int(age)
    if pos_code == 'K':
        return max(0.1, 1 - 0.1 * (age - 30)) if age > 30 else 1.0
    return max(0.125, 1 - 0.125 * (age - 27)) if age > 27 else 1.0


def tsi_after_birthday(tsi, age, pos_code='NFW'):
    """Hattrick applies the new age to TSI only at the first weekly update after the birthday
    (Bouderbala: 393,190 at 31y111d and 32y2d, 289,790 at 32y4d). A TSI from before that update
    still carries last year's age factor: convert it to this year's."""
    prev = tsi_age_factor(int(age) - 1, pos_code)
    return float(tsi) * tsi_age_factor(age, pos_code) / prev if prev > 0 else float(tsi)


def healthy_tsi(tsi, injury_weeks):
    """TSI the player would show when healthy, from the injured TSI and the weeks of injury left."""
    try:
        w = float(injury_weeks or 0)
    except (TypeError, ValueError):
        w = 0.0
    return float(tsi) * (1.0 + INJURY_TSI_PER_WEEK * w) if w > 0 else float(tsi)


def full_training_gain(skill, start, age, weeks):
    """Levels a skill gains with full training for `weeks` (Foxtrick HTMS training speed:
    training points per week at this age / HTMS points the next level costs)."""
    v, left = float(start), max(0.0, float(weeks))
    ppw = float(HTMS_POTENTIAL_GAINS.get(int(age), 8.0))
    while left > 1e-9 and v < 23.0:
        step = min(left, 0.1)
        lv = int(v)
        cost = HTMS_ABILITY_TABLE[min(lv + 1, 23)][skill] - HTMS_ABILITY_TABLE[min(lv, 23)][skill]
        v += ppw * step / max(cost, 1.0)
        left -= step
    return v - float(start)



# Lineup roles / short names that ended up as roster positions (the old "Save lineup" button
# wrote the lineup role into the roster). The solver only knows the position codes below, so
# translate before use; an unknown code made e.g. a CD solve as a forward (scoring as main skill).
POSITION_ALIASES = {
    'CD': 'NCD', 'NCD': 'NCD', 'OCD': 'OCD', 'CDTW': 'NCD', 'DEF': 'NCD',
    'CAD': 'CAD', 'CADEF': 'CAD', 'CA DEF': 'CAD', 'CA-DEF': 'CAD', 'CA_DEF': 'CAD', 'CA CD': 'CAD', 'COUNTER CD': 'CAD',
    'WB': 'NWB', 'NWB': 'NWB', 'DWB': 'NWB', 'OWB': 'NWB', 'WBTM': 'NWB', 'SHWB': 'SHWB',
    'W': 'NW', 'NW': 'NW', 'OW': 'NW', 'DW': 'NW', 'WTM': 'WTM', 'WING': 'NW',
    'IM': 'NIM', 'NIM': 'NIM', 'IMTW': 'NIM', 'OIM': 'OIM-Q', 'OIM-Q': 'OIM-Q', 'OIM-H': 'OIM-H',
    'DIM': 'PDIM', 'PDIM': 'PDIM', 'MID': 'NIM',
    'FW': 'NFW', 'NFW': 'NFW', 'FTW': 'NFW', 'PNF': 'PNF', 'DFW': 'DFW', 'TDFW': 'DFW', 'ATT': 'NFW',   # DFW/TDFW: one position for the solver
    'K': 'K', 'GK': 'K', 'KEEPER': 'K',
}


def normalize_position(pos):
    """Roster/lineup position text -> one of the solver's position codes (unknown stays as is)."""
    if pos is None:
        return pos
    p = str(pos).strip()
    return POSITION_ALIASES.get(p.upper(), POSITION_ALIASES.get(p, p))


# ── Last match position (Hattrick CSV "Last match position", HTP "PositionCode") ──────────────
# The slot a player was last fielded in, grouped into lines. A player can legitimately play out of
# his position (an NWB at CD, a WTM on the wing), so a difference is shown as a hint, not an error.
MATCH_SLOT_POSITIONS = {
    'GK': ('K',), 'CD': ('NCD', 'OCD', 'CAD'), 'WB': ('NWB', 'SHWB'),
    'IM': ('NIM', 'OIM-Q', 'OIM-H', 'PDIM'), 'W': ('NW', 'WTM'), 'FW': ('NFW', 'PNF', 'DFW', 'TDFW'),
}
MATCH_SLOT_DEFAULT = {'GK': 'K', 'CD': 'NCD', 'WB': 'NWB', 'IM': 'NIM', 'W': 'NW', 'FW': 'NFW'}
# Hattrick match role IDs (HTP PositionCode): 100 keeper, 101-105 defence (right to left),
# 106-110 midfield, 111-113 forwards. 114+ are substitutes / set-piece taker etc.
HT_ROLE_ID_SLOT = {100: 'GK', 101: 'WB', 102: 'CD', 103: 'CD', 104: 'CD', 105: 'WB',
                   106: 'W', 107: 'IM', 108: 'IM', 109: 'IM', 110: 'W', 111: 'FW', 112: 'FW', 113: 'FW'}
_SLOT_TEXT = {'GK': 'GK', 'K': 'GK', 'KEEPER': 'GK',
              'CD': 'CD', 'CB': 'CD', 'LCD': 'CD', 'RCD': 'CD', 'MCD': 'CD',
              'WB': 'WB', 'LB': 'WB', 'RB': 'WB', 'LWB': 'WB', 'RWB': 'WB',
              'IM': 'IM', 'CM': 'IM', 'LIM': 'IM', 'RIM': 'IM', 'MIM': 'IM',
              'W': 'W', 'WI': 'W', 'LW': 'W', 'RW': 'W',
              'FW': 'FW', 'CF': 'FW', 'LF': 'FW', 'RF': 'FW', 'LFW': 'FW', 'RFW': 'FW', 'ST': 'FW'}
LAST_MATCH_MAX_AGE_DAYS = 60   # older ratings are shown, but not used for the position hint


def match_slot(value):
    """'IM', 'LB', 'FW' (Hattrick CSV) or 107 (HTP role ID) -> line 'GK'/'CD'/'WB'/'IM'/'W'/'FW', else None."""
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s or s in ('NAN', 'NONE'):
        return None
    try:
        return HT_ROLE_ID_SLOT.get(int(float(s)))
    except ValueError:
        return _SLOT_TEXT.get(s)


def slot_fits_position(slot, pos_code):
    """True when the stored position is one that's normally played in this slot."""
    return normalize_position(pos_code) in MATCH_SLOT_POSITIONS.get(slot, ())


MULTI_SEC_EVEN = 3000.0   # option 2: pull the top 3 secondaries together (0 = off). Tested on 83 Dutch NT seniors:
                          # 0 / 1000 / 3000 / 8000 -> 0.795 / 0.789 / 0.763 / 0.769 levels off, spread 3.41 / 3.28 / 3.12 / 2.90 (real 3.25)
MULTI_TOP_PULL = 1.0   # option 2: pull of the main skill toward the 2nd and 3rd highest skill (1 = as before)


def auto_solve_subskills(
    target_tsi,
    target_wage,
    target_htms,
    target_htms28,
    age,
    days,
    spec,
    vorm,
    cond,
    pos_code,
    country_richtskills=None,
    htms_unknown=False,
    htms28_unknown=False,
    current_skills=None,
    is_foreign=False,
    skill_bands=None,
    pre_ref_df=None,  # pre-loaded reference DataFrame to avoid Turso round-trips
    training_plan=None,  # option 5: {skill: share} trained since the birthday (None = position default)
    weeks_missed=0.0,    # option 5: weeks without training (injury, no minutes)
    default_only=False,  # only option 1 (fast; used by the import)
    exclude_player=None,  # (PlayerID, name): never use the player himself as a reference peer
    form_stamina_case=None,  # 'A' low / 'B' middle / 'C' high within the displayed levels (None = solver decides)
    _relaxed_caps=False,     # internal: second try with the left-over skill caps lifted (see the end)
    wage_skill=None,         # force the wage skill (used for TDFW, see below)
    shape='target',          # 'target' = target skills profile; 'contribution' = reshaped by the contribution table
    order=None,              # contribution shape: the order (NCD, CDTW, OW, ...); None = position default
    accent=None,             # contribution shape: None / 'counter' / 'longshot'
    untrained=False,         # True: not trained since the birthday, so today's skills = the birthday skills
):
    pos_code = normalize_position(pos_code)
    _contrib = shape == 'contribution'
    # TDFW: playmaking and passing are both main skills, and either can be the wage skill
    # (playmaking pays more per level). TSI and wage often fit both - e.g. a Swiss TDFW fits
    # passing 16.5 / playmaking 8.5 as well as playmaking 15 / passing 10. Solve both ways and keep
    # the one closest to the (balanced) TDFW profile.
    if (wage_skill is None and pos_code == 'DFW'
            and not (current_skills and any(float(current_skills.get(k) or 0) > 0 for k in ('PM', 'Pas')))
            and not (skill_bands and any(skill_bands.get(k) is not None for k in ('PM', 'Pas')))):
        _args = dict(target_tsi=target_tsi, target_wage=target_wage, target_htms=target_htms, target_htms28=target_htms28,
                     age=age, days=days, spec=spec, vorm=vorm, cond=cond, pos_code=pos_code,
                     country_richtskills=country_richtskills, htms_unknown=htms_unknown, htms28_unknown=htms28_unknown,
                     current_skills=current_skills, is_foreign=is_foreign, skill_bands=skill_bands, pre_ref_df=pre_ref_df,
                     training_plan=training_plan, weeks_missed=weeks_missed, default_only=default_only,
                     exclude_player=exclude_player, form_stamina_case=form_stamina_case,
                     shape=shape, order=order, accent=accent, untrained=untrained)
        _prof = (country_richtskills or {}).get(pos_code) if isinstance(country_richtskills, dict) else None
        _prof = _prof or estimate_age_richtskills(age, spec).get(pos_code, {})
        _best = None
        for _ws in ('Pas', 'PM'):
            try:
                _r, _d = auto_solve_subskills(wage_skill=_ws, **_args)
            except Exception:
                continue
            if not _r:
                continue
            _x = _r[0]
            _score = sum(((float(_x[k]) - float(_prof.get(k, 1.0))) / max(float(_prof.get(k, 1.0)), 1.0)) ** 2
                         for k in ('PM', 'Pas', 'SC'))
            if _best is None or _score < _best[0]:
                _best = (_score, _r, _d)
        if _best is not None:
            return _best[1], _best[2]

    results = []
    _skill_keys = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
    
    richt_bench = None
    if isinstance(country_richtskills, dict) and country_richtskills:
        richt_bench = country_richtskills.get(pos_code)
    if not richt_bench:
        richt_bench = estimate_age_richtskills(age, spec).get(pos_code)
    if not richt_bench:
        richt_bench = RICHTSKILLS_29.get(pos_code, RICHTSKILLS_29.get('NFW'))
    # Contribution shape: the profile reshaped by the contribution table (+ tactic accent). The Dutch senior
    # adjustments below are skipped: they encode the Dutch training shape this option replaces.
    if _contrib and richt_bench and CONTRIB_PURE:
        richt_bench = pure_contribution_profile(richt_bench, pos_code, order, accent, age, days, spec, vorm, cond,
                                                target_tsi, target_wage, is_foreign)
    elif _contrib and richt_bench:
        richt_bench = contribution_profile(richt_bench, pos_code, order, accent)
        # Set pieces have no rating contribution: for outfield players (not set-piece WBs, not long shots)
        # they are a left-over, about their value at 21 (+1.5): ~2.8, forwards ~6.6. The senior profile's 9-10
        # (Dutch NT seniors / forwards who trained them along the way) otherwise came back in every
        # contribution solve (Borbola, Hodzic, Cvijetic, Lorca: SP 9.5-9.9).
        _p21 = estimate_age_richtskills(21, spec).get(pos_code, {}) if int(age) > 21 else {}
        if pos_code not in ('K', 'SHWB') and accent != 'longshot' and _p21:
            # same left-over for every outfield position (forwards too: their Dutch profile has SP 5 at 21
            # from youth training, which still left a PNF at SP 7)
            _sh21 = min(float(_p21.get('SH', 1.3)), 1.5)
            richt_bench = dict(richt_bench, SH=min(float(richt_bench.get('SH', 2.0)), _sh21 + 1.5))
        # The same for skills without a contribution for this order (e.g. CD passing): a left-over near its
        # value at 21, not the Dutch senior value (CD passing 10-12). Otherwise a weak senior CD came out
        # with passing 11 and playmaking 7 (Borbola, 33).
        if pos_code != 'K' and _p21:
            _c, _ = order_contributions(order or (POSITION_ORDERS.get(pos_code) or ['NFW'])[0], accent)
            _rb = dict(richt_bench)
            for _k in ('DE', 'PM', 'WI', 'Pas', 'SC'):
                if _c.get(_k, 0) <= 0:
                    _rb[_k] = min(float(_rb.get(_k, 1.0)), max(1.0, float(_p21.get(_k, 1.0)) + 1.5))
            richt_bench = _rb
    # Senior wingers: the solver's target for passing (the profile's 10-11 at 32 put passing at its cap
    # and took the TSI from defending).
    if not _contrib and pos_code in ('NW', 'WTM') and int(age) >= SENIOR_WING_MIN_AGE and richt_bench and SENIOR_WING_PAS_TARGET:
        richt_bench = dict(richt_bench, Pas=min(float(richt_bench.get('Pas', 8.0)), SENIOR_WING_PAS_TARGET))
    if not _contrib and int(age) >= SENIOR_POS_MIN_AGE and richt_bench and SENIOR_POS_TARGETS.get(pos_code):
        richt_bench = dict(richt_bench, **{k: min(float(richt_bench.get(k, v)), v) for k, v in SENIOR_POS_TARGETS[pos_code].items()})
    if not _contrib and int(age) >= SENIOR_POS_MIN_AGE and richt_bench and SENIOR_POS_SET.get(pos_code):
        richt_bench = dict(richt_bench, **SENIOR_POS_SET[pos_code])

    ref_bench = None
    ref_count = 0
    ref_percentiles = {}  # P10/P90 of Reference DB peers per skill
    try:
        import numpy as _np
        ref_df = pre_ref_df if pre_ref_df is not None else None
        if ref_df is None:
            from data_layer import get_reference_players_df
            ref_df = get_reference_players_df()
        ref_df = _ref_playing_age(_ref_base_wage(_without_player(ref_df, exclude_player)), age)
        if ref_df is not None and not ref_df.empty:
            same_pos = ref_df[(ref_df['Positie'] == pos_code) & (ref_df['Leeftijd'].between(age - 3, age + 3))]
            if same_pos.empty:
                same_pos = ref_df[ref_df['Positie'] == pos_code]
            if not same_pos.empty:
                ref_bench = {sk: same_pos[sk].mean() for sk in _skill_keys}
                ref_count = len(same_pos)
                if len(same_pos) >= 10:
                    for sk in _skill_keys:
                        vals = same_pos[sk].dropna().astype(float)
                        if len(vals) >= 5:
                            ref_percentiles[sk] = (
                                float(_np.percentile(vals, 10)),
                                float(_np.percentile(vals, 90)),
                            )
    except Exception:
        pass

    fixed_sh = current_skills.get('SH') if current_skills else None

    rev_htms, rev_htms28, diagnostics = estimate_htms_from_profile(
        age=age,
        days=days,
        tsi=target_tsi,
        wage=target_wage,
        form=vorm,
        cond=cond,
        is_foreign=is_foreign,
        spec=spec,
        pos_code=pos_code,
        fixed_sh=fixed_sh,
        pre_ref_df=pre_ref_df, exclude_player=exclude_player, wage_skill=wage_skill,
        profile=richt_bench,
    )

    # Keeper, HTMS and SH unknown: aim set pieces at the profile, shifted by how far his
    # goalkeeping (from TSI) is ahead of or behind the profile for his age. Otherwise every
    # keeper of the same age got the same set pieces, whatever his goalkeeping.
    if pos_code == 'K' and htms_unknown and fixed_sh is None and richt_bench:
        _gk = float(diagnostics.get('inferred_primary') or 0)
        _bgk = float(richt_bench.get('GK', 0) or 0)
        if _gk > 1.0 and _bgk > 1.0:
            richt_bench = dict(richt_bench)
            richt_bench['SH'] = max(1.0, float(richt_bench.get('SH', 14.5)) + KEEPER_SH_PER_GK * (_gk - _bgk))

    use_exact_htms = (not htms_unknown) and (target_htms > 0)
    use_exact_htms28 = (not htms28_unknown) and (target_htms28 > 0)

    htms_penalty_weight = 1e11 if use_exact_htms else 1e9
    effective_target_htms   = target_htms if use_exact_htms else rev_htms
    effective_target_htms28 = target_htms28 if use_exact_htms28 else rev_htms28

    # HTMS unknown but skills known: all 7 known -> exact HTMS; some known -> estimate.
    if current_skills and not use_exact_htms:
        known_vals = {}
        for k, v in current_skills.items():
            try:
                fv = float(v)
                if fv > 0.0:
                    known_vals[k] = fv
            except (TypeError, ValueError):
                pass
        if len(known_vals) >= 7:
            calc_htms = calculate_htms_ability(
                known_vals.get('GK', 1.0), known_vals.get('DE', 1.0),
                known_vals.get('PM', 1.0), known_vals.get('WI', 1.0),
                known_vals.get('Pas', 1.0), known_vals.get('SC', 1.0),
                known_vals.get('SH', 1.0)
            )
            if calc_htms > 0:
                calc_htms28 = calculate_htms_potential(age, days, calc_htms)
                effective_target_htms   = calc_htms
                effective_target_htms28 = calc_htms28
                htms_penalty_weight = 5e10
                diagnostics['htms_mode'] = 'Calculated from Known Skills'
                diagnostics['active_target_htms']   = int(calc_htms)
                diagnostics['active_target_htms28'] = int(calc_htms28) if isinstance(calc_htms28, (int, float)) else 0
        elif len(known_vals) >= 1 and not use_exact_htms and pos_code not in ('SHWB', 'K'):
            # Known skills exactly + wage-inferred primary + position-aware fills.
            bench_for_htms = richt_bench or {}
            bench_sh = 1.0  # SH is rarely trained outside SHWB/K
            primary_col  = diagnostics.get('primary_col', 'SC')
            inferred_pri = diagnostics.get('inferred_primary', 5.0)
            sec_avg      = max(1.0, diagnostics.get('residual_secondary_avg', 5.0))
            _sec_weights = {'GK':0.0,'DE':1.0,'PM':1.0,'WI':0.8,'Pas':0.9,'SC':1.0,'SH':0.0}
            _htms_tbls = {'GK':_HTMS_GK,'DE':_HTMS_DE,'PM':_HTMS_PM,
                          'WI':_HTMS_WI,'Pas':_HTMS_PAS,'SC':_HTMS_SC,'SH':_HTMS_SH}

            exact_known_htms = sum(
                _lh(v, _htms_tbls[k]) for k, v in known_vals.items() if k in _htms_tbls
            )
            estimated_unknown_htms = 0.0
            for k in _skill_keys:
                if k in known_vals:
                    continue
                if k == primary_col:
                    estimated_unknown_htms += _lh(max(1.0, inferred_pri), _htms_tbls[k])
                elif k == 'SH':
                    estimated_unknown_htms += _lh(bench_sh, _HTMS_SH)
                elif k == 'GK':
                    estimated_unknown_htms += _lh(1.0, _HTMS_GK)
                else:
                    w = _sec_weights.get(k, 1.0)
                    # Skills the position hardly trains keep their (low) profile value.
                    bench_val = max(1.0, float(bench_for_htms.get(k, 1.0)))
                    sec_val   = max(1.0, sec_avg * w)
                    use_val   = bench_val if bench_val < sec_val * 0.6 else sec_val
                    estimated_unknown_htms += _lh(use_val, _htms_tbls.get(k, _HTMS_PM))

            better_htms = round(exact_known_htms + estimated_unknown_htms)
            better_htms = max(round(rev_htms * 0.6), min(round(rev_htms * 1.4), better_htms))

            if better_htms > 0:
                n_known = len(known_vals)
                calc_htms28 = calculate_htms_potential(age, days, better_htms)
                effective_target_htms   = better_htms
                effective_target_htms28 = calc_htms28
                # Estimated anchor: gentle, TSI (1e11) dominates.
                htms_penalty_weight = 1e7
                diagnostics['htms_mode'] = f'Partial Known Skills ({n_known}/7 exact + rev-eng unknown)'
                diagnostics['active_target_htms']   = int(better_htms)
                diagnostics['active_target_htms28'] = int(calc_htms28) if isinstance(calc_htms28, (int, float)) else 0
                if 'SH' not in known_vals:
                    diagnostics['_bench_sh_pin'] = bench_sh

    # Exact HTMS + some known skills: HTMS points left for the unknown skills.
    htms_budget_for_unknown = None
    unknown_skills = []
    wage_bounds_for_unknown = {}

    if use_exact_htms and current_skills and target_htms > 0:
        known_htms_pts = 0.0
        unknown_skills = []
        for k in _skill_keys:
            v = current_skills.get(k) if current_skills else None
            try:
                fv = float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                fv = 0.0
            if fv > 0.0:
                tbl = {'GK':_HTMS_GK,'DE':_HTMS_DE,'PM':_HTMS_PM,
                       'WI':_HTMS_WI,'Pas':_HTMS_PAS,'SC':_HTMS_SC,'SH':_HTMS_SH}.get(k)
                if tbl:
                    known_htms_pts += _lh(fv, tbl)
            else:
                unknown_skills.append(k)
        if unknown_skills and known_htms_pts > 0:
            htms_budget_for_unknown = max(0, target_htms - known_htms_pts)
            diagnostics['htms_budget_unknown'] = f"{htms_budget_for_unknown:.0f} pts for {unknown_skills}"

    # Wage budget left for unknown skills -> upper bound per unknown skill.
    if current_skills and target_wage > 0:
        try:
            _spec_m_w = 1.10 if (spec and str(spec).strip() not in ('Geen','None','','nan')) else 1.00
            _age_wage_f_w = max(0.1, 1 - 0.1*(age-28)) if age > 28 else 1.0
            sh_val = float((current_skills or {}).get('SH') or 0) or 1.0
            sh_m_w = 1 + 0.25 * sh_val / 100.0
            total_budget = target_wage / (_spec_m_w * _age_wage_f_w * sh_m_w) - 250

            wage_tbls = {'GK':_WAGE_GK,'DE':_WAGE_DE,'PM':_WAGE_PM,
                         'WI':_WAGE_WI,'Pas':_WAGE_PAS,'SC':_WAGE_SC}
            known_wage_comps = {}
            for k, tbl in wage_tbls.items():
                v = current_skills.get(k) if current_skills else None
                try:
                    fv = float(v) if v is not None else 0.0
                except (TypeError, ValueError):
                    fv = 0.0
                if fv > 0.0:
                    known_wage_comps[k] = _lw(fv, tbl)

            if known_wage_comps:
                primary_known = max(known_wage_comps.values())
                secondary_mult = 0.40 if primary_known > 20300 else 0.50
                known_sum = sum(
                    (v if v == primary_known else secondary_mult * v)
                    for v in known_wage_comps.values()
                )
                remaining = max(0, total_budget - known_sum)
                max_comp = remaining / secondary_mult if secondary_mult > 0 else remaining

                unk_skls = [k for k in _skill_keys
                            if current_skills.get(k) is None
                            or float(current_skills.get(k) or 0) <= 0]
                for k in unk_skls:
                    if k in wage_tbls:
                        tbl = wage_tbls[k]
                        for lvl in range(1, 25):
                            if _lw(float(lvl), tbl) > max_comp:
                                wage_bounds_for_unknown[k] = min(float(lvl) + 0.99, 25.0)
                                break
        except Exception as _wage_err:
            diagnostics['wage_bounds_error'] = str(_wage_err)

    if wage_bounds_for_unknown:
        diagnostics['wage_bounds'] = {k: f'≤{v:.1f}' for k,v in wage_bounds_for_unknown.items()}

    if 'htms_mode' not in diagnostics:
        diagnostics['htms_mode'] = (
            'Exact Target (1e11)'
            if use_exact_htms
            else 'Reverse-Engineered Soft Anchor (1e9)'
        )
        diagnostics['active_target_htms']   = effective_target_htms
        diagnostics['active_target_htms28'] = effective_target_htms28
    diagnostics['ref_players_found'] = ref_count

    def is_known(k):
        if current_skills is None: return False
        v = current_skills.get(k)
        return v is not None and float(v) > 0.0

    def is_bounded(k):
        return is_known(k) or (
            skill_bands is not None and skill_bands.get(k) is not None
        )

    def get_pos_bounds():
        bounds = []
        for k in _skill_keys:
            if is_known(k):
                v = float(current_skills[k])
                bounds.append((max(1.0, v - 0.02), min(25.0, v + 0.02)))
            elif skill_bands and skill_bands.get(k) is not None:
                bounds.append(skill_bands[k])
            elif k == 'GK' and pos_code != 'K':
                bounds.append((1.0, 1.0))
            elif k == 'GK' and pos_code == 'K':
                # Keeper GK floor at 75% of the age target.
                bench_gk_k = float((richt_bench or {}).get('GK', 16.5))
                lo_gk = max(1.0, bench_gk_k * 0.75)
                bounds.append((lo_gk, 25.0))
            elif pos_code == 'K' and k == 'SH':
                bench_sh_k = float((richt_bench or {}).get('SH', 13.0))
                if htms_unknown and age <= 22:
                    lo_sh = max(9.0, bench_sh_k * 0.90)
                    hi_sh = min(25.0, bench_sh_k * 1.15)
                elif htms_unknown and age <= 26:
                    lo_sh = max(10.0, bench_sh_k * 0.90)
                    hi_sh = min(25.0, bench_sh_k * 1.20)
                if htms_unknown and age >= 21:
                    # Properly trained keepers have set pieces 14+ from 21 on; lower values
                    # (like SH 6) are training mistakes, which a real HTMS still finds (below).
                    lo_sh = max(lo_sh if age <= 26 else 10.0, 14.0)
                    hi_sh = max(hi_sh if age <= 26 else 25.0, lo_sh + 1.5)
                elif htms_unknown and age > 26:
                    lo_sh, hi_sh = 10.0, 25.0
                if not htms_unknown:
                    # HTMS known: HTMS decides SH (keeper TSI and wage barely see it). No floor:
                    # real Dutch U21 keepers range from SH 6 to 16.
                    lo_sh = 3.0
                    hi_sh = 25.0
                bounds.append((lo_sh, hi_sh))
            elif pos_code == 'K' and k == 'DE':
                bench_de_k = float((richt_bench or {}).get('DE', 5.5))
                lo_de = max(2.0, bench_de_k * 0.60)
                bounds.append((lo_de, min(25.0, bench_de_k * 1.5)))
            elif pos_code == 'K' and k in ('PM', 'WI', 'SC'):
                # Left-overs from before keeper training: real U21 keepers have 1-5 here.
                bounds.append((1.0, 5.0))
            elif pos_code == 'K' and k == 'Pas':
                bench_pas_k = float((richt_bench or {}).get('Pas', 2.5))
                bounds.append((1.0, min(8.0, max(bench_pas_k * 2.0, 7.0))))
            elif pos_code == 'SHWB' and k == 'SH':
                # SH is a main skill for a set-pieces WB; bounds tighten with age.
                bench_sh_shwb = float((richt_bench or {}).get('SH', 18.0))
                if htms_unknown and age >= 28:
                    lo_sh = max(8.0, bench_sh_shwb * 0.80)
                    hi_sh = min(25.0, bench_sh_shwb * 1.25)
                elif htms_unknown and age >= 23:
                    lo_sh = max(5.0, bench_sh_shwb * 0.70)
                    hi_sh = min(25.0, bench_sh_shwb * 1.40)
                elif htms_unknown:
                    lo_sh = max(5.0, bench_sh_shwb * 0.85)
                    hi_sh = min(25.0, bench_sh_shwb * 1.30)
                else:
                    lo_sh = max(3.0, bench_sh_shwb * 0.40)
                    hi_sh = 25.0
                bounds.append((lo_sh, hi_sh))
            elif pos_code == 'SHWB' and k == 'SC':
                bounds.append((1.0, max(4.0, float((richt_bench or {}).get('SC', 1.0)) + 2.0) if _contrib else 4.0))
            elif pos_code == 'SHWB' and k == 'Pas':
                # Passing is the least-trained secondary of a set-piece WB (Dutch U21: 5-6
                # against a profile of 5.5). Without a cap TSI went into passing (highest TSI
                # weight per level) instead of winger.
                bench_pas = float((richt_bench or {}).get('Pas', 5.0))
                bounds.append((1.0, min(25.0, max(bench_pas * 1.5, 7.0))))
            elif pos_code == 'SHWB' and k == 'WI':
                bench_wi = float((richt_bench or {}).get('WI', 8.0))
                bounds.append((max(1.0, bench_wi * 0.75), 25.0))
            elif (pos_code in ('NW', 'WTM') and k in ('DE', 'Pas') and int(age) >= SENIOR_WING_MIN_AGE
                  and SENIOR_WING_BOUNDS.get(k)):
                # Senior wingers: defending and passing were trained along the way and stay near
                # the profile. Before: defending up to 12 (NW) / profile+1 (WTM), so spare TSI landed
                # there (~0.6-1.2 too high), and passing had no floor (dropped to 2.9).
                _b_w = float((richt_bench or {}).get(k, 8.0))
                _below, _above = SENIOR_WING_BOUNDS[k]
                _lo_w, _hi_w = max(1.0, _b_w - _below), min(25.0, _b_w + _above)
                if k == 'Pas' and SENIOR_WING_PAS_RANGE:
                    _lo_w, _hi_w = SENIOR_WING_PAS_RANGE
                bounds.append((_lo_w, _hi_w))
            elif pos_code == 'WTM' and k in ('DE', 'Pas', 'SC'):
                # WTM trains winger (paid for PM): untrained left-overs stay near the profile so
                # spare TSI goes to winger (simulated WTMs: winger 0.2-1.2 too low otherwise).
                _b_w = float((richt_bench or {}).get(k, 4.0))
                bounds.append((1.0, min(25.0, _b_w + (1.5 if k == 'SC' else 1.0))))
            elif pos_code in ('NW', 'WTM') and k == 'SC':
                bounds.append((1.0, max(7.5, float((richt_bench or {}).get('SC', 1.0)) + 2.0) if _contrib else 7.5))
            elif pos_code in ('NW', 'WTM') and k == 'WI':
                bench_wi_nw = float((richt_bench or {}).get('WI', 10.0))
                lo_wi = max(1.0, bench_wi_nw * 0.5)
                bounds.append((lo_wi, 25.0))
            elif pos_code in ('NFW', 'PNF') and k == 'SC':
                bench_sc_nfw = float((richt_bench or {}).get('SC', 18.0))
                lo_sc = max(1.0, bench_sc_nfw * 0.8)
                bounds.append((lo_sc, 25.0))
            elif pos_code in ('NFW', 'PNF') and k == 'DE':
                # Left-over defending: real forwards have 2-5 (was capped at 3).
                hi_de = 5.0
                bounds.append((1.0, hi_de))
            elif pos_code in ('NW', 'WTM') and k == 'DE':
                bench_de_nw = float((richt_bench or {}).get('DE', 5.0))
                hi_de = min(12.0, max(bench_de_nw * 1.5, 5.0))
                bounds.append((1.0, hi_de))
            elif pos_code == 'NWB' and k == 'PM':
                bench_pm = float((richt_bench or {}).get('PM', 3.0))
                bounds.append((1.0, min(25.0, max(bench_pm * 2.5, 6.0))))
            elif pos_code == 'NWB' and k == 'Pas':
                bench_pas = float((richt_bench or {}).get('Pas', 3.0))
                bounds.append((1.0, min(25.0, max(bench_pas * 2.5, 6.0))))
            elif pos_code == 'SHWB' and k == 'PM':
                bench_pm = float((richt_bench or {}).get('PM', 4.5))
                bounds.append((1.0, min(25.0, max(bench_pm * 2.0, 8.0))))
            elif pos_code in ('NIM', 'OIM-H', 'OIM-Q') and k == 'WI':
                bench_wi = float((richt_bench or {}).get('WI', 1.0))
                bounds.append((1.0, min(25.0, max(bench_wi * 3.0, 4.0))))
            elif pos_code in ('NWB', 'NCD', 'SHWB') and k == 'SC':
                bench_sc = float((richt_bench or {}).get('SC', 1.0))
                # contribution shape (long shots): at most 2 above its profile, else spare TSI lands here
                bounds.append((1.0, min(25.0, max(bench_sc * 3.0, 4.0), bench_sc + 2.0 if _contrib and bench_sc > 2.0 else 25.0)))
            elif pos_code == 'NCD' and k == 'Pas':
                bench_pas = float((richt_bench or {}).get('Pas', 4.0))
                bounds.append((1.0, min(25.0, bench_pas * 1.3)))
            elif pos_code == 'PDIM' and k == 'SC':
                # left-over, little or no training: at most ~2x the profile (Dutch PDIM: 4)
                bench_sc = float((richt_bench or {}).get('SC', 2.0))
                bounds.append((1.0, max(bench_sc * 2.0, 4.0)))
            elif pos_code == 'PDIM' and k == 'DE':
                # trained alongside playmaking: never a left-over (Dutch PDIM DE 10.2)
                bench_de = float((richt_bench or {}).get('DE', 10.0))
                bounds.append((max(1.0, bench_de * 0.6), min(25.0, bench_de + 5.0)))
            elif pos_code == 'PDIM' and k == 'Pas':
                # passing is part of the PDIM's play (Dutch PDIM: 7): at least ~80% of the profile
                bench_pas = float((richt_bench or {}).get('Pas', 6.0))
                bounds.append((max(1.0, bench_pas * 0.8), min(25.0, bench_pas + 3.5)))
            elif pos_code in ('NCD', 'PDIM') and k == 'WI':
                # Not trained: a left-over (else spare TSI piles up here, e.g. PDIM winger 5.5).
                bounds.append((1.0, 3.0))
            elif pos_code in ('NIM', 'OIM-H', 'OIM-Q', 'PDIM') and k == 'GK':
                bounds.append((1.0, 2.0))
            elif pos_code in ('NIM', 'OIM-H', 'OIM-Q') and k == 'SC' and age > 24:
                # Older inner mids: scoring at most ~4 above the profile, otherwise TSI
                # gets dumped into scoring (highest TSI weight) instead of DE/passing.
                bench_sc_im = float((richt_bench or {}).get('SC', 7.0))
                bounds.append((1.0, min(25.0, bench_sc_im + 4.0)))
            elif pos_code == 'OCD' and k in ('DE', 'PM'):
                # Offensive CD: defending and playmaking are both main skills.
                bounds.append((max(1.0, float((richt_bench or {}).get(k, 5.0)) * 0.6), 25.0))
            elif pos_code == 'DFW' and k == 'DE':
                # a left-over for a TDFW (Dutch TDFWs: 3-4.5); without a limit spare TSI lands here
                bounds.append((1.0, min(25.0, float((richt_bench or {}).get('DE', 3.5)) + 1.0)))
            elif pos_code == 'DFW' and k == 'SC':
                # a real, trained skill for a TDFW (seniors ~13.8): keep it near the profile
                _b_sc = float((richt_bench or {}).get('SC', 10.0))
                bounds.append((max(1.0, _b_sc * 0.6), min(25.0, _b_sc + 3.0)))
            elif pos_code in ('DFW', 'TDFW') and k in ('PM', 'Pas'):
                # Defensive FW: playmaking and passing are both main skills.
                bounds.append((max(1.0, float((richt_bench or {}).get(k, 5.0)) * 0.6), 25.0))
            elif pos_code in ('DFW', 'TDFW') and k == 'WI':
                # a left-over for a DFW: at most 1.5 above the profile (was 1.5 x profile, up to 10.5)
                bench_k = float((richt_bench or {}).get(k, 4.0))
                bounds.append((1.0, min(25.0, bench_k + 1.5)))
            elif pos_code == 'OCD' and k == 'Pas':
                bench_k = float((richt_bench or {}).get(k, 4.0))
                bounds.append((1.0, min(25.0, max(bench_k * 1.5, 6.0))))
            else:
                lo, hi = 1.0, 25.0
                # A skill the position doesn't train (1 in its profile) is at most a
                # left-over from before: without this, TSI lets e.g. an OCD's defending
                # be swapped for scoring (almost the same TSI weight).
                if (k not in ('GK', 'SH') and pos_code in RICHTSKILLS_29
                        and float(RICHTSKILLS_29[pos_code].get(k, 1.0)) <= 1.0):
                    hi = 5.0
                    # contribution shape (e.g. long shots): the reshaped profile may give this skill a real value
                    if _contrib and float((richt_bench or {}).get(k, 1.0)) > 4.0:
                        hi = min(25.0, float(richt_bench[k]) + 2.0)

                # SH is invisible in TSI/wage, so cap it outside SHWB/K (by age).
                if k == 'SH' and pos_code not in ('SHWB', 'K'):
                    bench_sh_pos = float((richt_bench or {}).get('SH', 5.0))
                    if age <= 22:
                        hi = 3.0
                    elif age <= 26:
                        hi = min(25.0, max(4.0, bench_sh_pos))
                    elif age < SENIOR_SH_MIN_AGE:
                        hi = min(25.0, max(5.0, bench_sh_pos))
                    else:
                        # Seniors: set pieces were trained along the way (Dutch NT seniors 30-33:
                        # SP 4-13). Invisible in TSI and only 0.25%/level in the wage, so without a
                        # floor the solver dropped it to 1-2. Keep it around the profile.
                        lo = max(1.0, bench_sh_pos - SENIOR_SH_BELOW)
                        hi = min(25.0, bench_sh_pos + SENIOR_SH_ABOVE_POS.get(pos_code, SENIOR_SH_ABOVE))
                    if _contrib and accent == 'longshot':
                        # long-shot player: set pieces are trained too, so they follow the reshaped profile
                        lo, hi = max(1.0, bench_sh_pos - 1.5), min(25.0, bench_sh_pos + 1.5)

                if k in wage_bounds_for_unknown:
                    hi = min(hi, wage_bounds_for_unknown[k])

                # HTMS budget: only decisive when exactly 1 skill is unknown.
                if (htms_budget_for_unknown is not None
                        and k in unknown_skills
                        and len(unknown_skills) == 1):
                    budget_tbl = {'GK':_HTMS_GK,'DE':_HTMS_DE,'PM':_HTMS_PM,
                                  'WI':_HTMS_WI,'Pas':_HTMS_PAS,'SC':_HTMS_SC,'SH':_HTMS_SH}.get(k)
                    if budget_tbl:
                        for lvl in range(1, 25):
                            if _lh(float(lvl), budget_tbl) >= htms_budget_for_unknown:
                                hi = min(hi, float(lvl) + 0.99)
                                break
                bounds.append((lo, hi))
        # Seniors (SENIOR_POS_MIN_AGE+): per position, skills stay within (below, above) levels of the
        # profile. TSI can't tell the secondaries apart and winger is the cheapest skill in TSI, so
        # without limits the left-over TSI piled up in winger (PNF Lepolder WI 14.0 vs real 10.5,
        # NFW Baaijens 15.5 vs 12.5, NWB Tamaela PM 12.6 vs real 11.1 / WI 15.7 vs 17.2).
        # Contribution shape: only the upper limits. The lower ones, around a reshaped (stronger) profile,
        # could exclude the TSI (PNF Lorca, 33: PM >= 15 -> TSI +67%); without the upper ones TSI piles
        # up in winger again (PNF Arens: WI 15.4 vs real 5).
        if int(age) >= SENIOR_POS_MIN_AGE and richt_bench and pos_code in SENIOR_POS_BOUNDS:
            for i, k in enumerate(_skill_keys):
                lim = SENIOR_POS_BOUNDS[pos_code].get(k)
                if not lim or is_known(k) or (skill_bands and skill_bands.get(k) is not None):
                    continue
                b = float(richt_bench.get(k, 1.0))
                lo_k, hi_k = (1.0 if _contrib else max(1.0, b - lim[0])), min(25.0, b + lim[1])
                if k == diagnostics.get('primary_col'):   # wage skill: keep the wage-based range, only clip
                    lo_k, hi_k = max(bounds[i][0], lo_k), min(bounds[i][1], max(hi_k, bounds[i][0] + 0.05))
                    if lo_k >= hi_k:
                        continue
                bounds[i] = (lo_k, hi_k)
        # Senior wingers: defending, passing and scoring were trained along the way and decline
        # slowly after 30, so they stay within SENIOR_WING_SEC_BELOW levels of the profile.
        # Without a floor the senior gap rule pushed Bouderbala (32) to passing 2.9 (was 7.7 at 30).
        if pos_code in ('NW', 'WTM') and int(age) >= SENIOR_WING_MIN_AGE and richt_bench:
            for i, k in enumerate(_skill_keys):
                if k in ('DE', 'Pas', 'SC') and not is_known(k) and not (skill_bands and skill_bands.get(k) is not None):
                    lo, hi = bounds[i]
                    floor = float(richt_bench.get(k, 1.0)) - SENIOR_WING_SEC_BELOW
                    if floor > lo:
                        bounds[i] = (min(floor, hi - 0.5), hi)
        if _relaxed_caps:
            # Second try: the caps on left-over skills (CD winger <= 3, scoring <= 4, passing <= 1.3 x profile,
            # ...) fit NT-trained players. A player trained otherwise (pressing / long shots: CD with winger 6,
            # scoring 8) then had nowhere to put his TSI but the main skill's partner, and the wage went 15-40%
            # over what it can be. Lift them to just under the main skill; TSI and wage decide.
            _mi = _skill_keys.index(diagnostics.get('primary_col')) if diagnostics.get('primary_col') in _skill_keys else -1
            _cap = max(5.0, float(diagnostics.get('inferred_primary') or 10.0) - 0.5)
            for i, k in enumerate(_skill_keys[:6]):
                if i == _mi or k == 'GK' or is_known(k) or (skill_bands and skill_bands.get(k) is not None):
                    continue
                lo, hi = bounds[i]
                if hi < _cap:
                    bounds[i] = (lo, _cap)
        return bounds

    bnds = get_pos_bounds()
    v_fl, c_fl = int(np.floor(vorm)), int(np.floor(cond))
    form_hi = min(float(v_fl) + 0.99, 8.0)
    # Stamina: at most 9.4 up to 27, lower from 28 (Schum, 'Stamina 2.0').
    cond_hi = max(float(c_fl), min(float(c_fl) + 0.99, stamina_max(age)))
    if form_stamina_case in ('A', 'B', 'C'):
        # A / B / C: form and stamina at the bottom, middle or top of the level Hattrick shows.
        _pos = {'A': 0.05, 'B': 0.50, 'C': 0.95}[form_stamina_case]
        # position within the real width of the level (form 8 has no room; stamina 9 runs to 9.4)
        _f = float(v_fl) + _pos * (form_hi - float(v_fl)) / 0.99 if form_hi - float(v_fl) < 0.99 else float(v_fl) + _pos
        _c = float(c_fl) + _pos * (cond_hi - float(c_fl)) / 0.99 if cond_hi - float(c_fl) < 0.99 else float(c_fl) + _pos
        _f, _c = min(_f, form_hi), min(_c, cond_hi)
        bnds.append((max(float(v_fl), _f - 0.01), min(form_hi, _f + 0.01)))
        bnds.append((max(float(c_fl), _c - 0.01), min(cond_hi, _c + 0.01)))
    else:
        bnds.append((float(v_fl), form_hi))
        bnds.append((float(c_fl), cond_hi))
    primary_idx = (
        _skill_keys.index(diagnostics['primary_col'])
        if diagnostics['primary_col'] in _skill_keys
        else -1
    )

    _age_tsi_f = (max(0.1, 1 - 0.1*(age-30)) if age > 30 else 1.0) if pos_code == 'K' else (max(0.125, 1 - 0.125*(age-27)) if age > 27 else 1.0)
    _spec_m    = 1.10 if (spec and str(spec).strip() not in ('Geen','None','','nan')) else 1.00
    _age_wage_f= max(0.1, 1 - 0.1*(age-28)) if age > 28 else 1.0

    # Pin the dominant skill around its wage-inferred level (unless known or banded).
    primary_col = diagnostics['primary_col']
    inferred_primary = diagnostics['inferred_primary']
    # Seniors: read the main skill from the wage with the other skills taken off (the birthday value).
    # The whole-wage value overestimates it, which for young players happens to make up for training
    # since the birthday, but seniors hardly train: it put a floor under the main skill that was too
    # high (Duco Heming NCD 31: DE floor 18.5 from 19.2, while the wage gives 18.36; real 18.24).
    if (int(age) >= SENIOR_MAIN_FROM_BIRTHDAY_AGE and pos_code not in SENIOR_MAIN_FROM_BIRTHDAY_SKIP
            and float(diagnostics.get('inferred_primary_birthday') or 0) > 1.0):
        inferred_primary = float(diagnostics['inferred_primary_birthday'])
    _inferred_primary_solve = inferred_primary
    dominant_pinned = False

    if (primary_idx >= 0
            and not is_known(primary_col)
            and not (skill_bands and skill_bands.get(primary_col) is not None)
            and inferred_primary > 1.0
            and not diagnostics.get('primary_ambiguous')):
        primary_floor = float(int(inferred_primary))
        old_bnd = bnds[primary_idx]
        if old_bnd[0] <= primary_floor + 0.5 <= old_bnd[1]:
            bnds[primary_idx] = (max(old_bnd[0], primary_floor - 0.5),
                                  min(old_bnd[1], primary_floor + 1.49))
            dominant_pinned = True

    # Players are trained (NT/U21 candidates): today's main skill lies between its birthday value
    # (from the wage) and that value plus full training since, and is pulled towards ~96% of it.
    main_target = None
    main_cap = None
    sec_target = None
    if (primary_idx >= 0 and pos_code != 'K' and not is_known(primary_col)
            and not (skill_bands and skill_bands.get(primary_col) is not None)
            and int(days) > 0 and int(age) < 28):
        _b = float(diagnostics.get('inferred_primary_birthday') or 0.0)
        if _b > 1.0 and untrained:
            # Not trained since the birthday: today's main skill is its birthday value.
            main_cap = _b + 0.05
            main_target = _b
            _lo, _hi = bnds[primary_idx]
            _new_lo, _new_hi = max(_lo, _b - 0.05), min(_hi, main_cap)
            if _new_lo >= _new_hi:
                _new_lo, _new_hi = _b - 0.05, main_cap
            bnds[primary_idx] = (_new_lo, _new_hi)
        elif _b > 1.0:
            _trained = TRAINED_SKILL.get(pos_code, primary_col)
            if _trained == primary_col:
                _gain = full_training_gain(primary_col, _b, age, int(days) / 7.0)
                main_cap = _b + _gain + 0.05
                main_target = _b + TRAINED_SHARE * TRAINED_WEEK_SHARE.get(pos_code, 1.0) * _gain
                # Trained only up to the highest whole level still reachable before 22: after
                # that the training goes to the secondary skill (e.g. PDIM PM 16.0 at 21 -> 17 is
                # out of reach, so he trains defending). The main skill then stops just above
                # that level instead of growing on.
                if int(age) < 22 and pos_code in REACHABLE_LEVEL_RULE:
                    # with the position's usual split (a PDIM trains PM ~65% of the weeks)
                    _to22 = TRAINED_WEEK_SHARE.get(pos_code, 1.0) * full_training_gain(
                        primary_col, _b, age, (22 - int(age)) * 16.0)
                    _top = float(int(_b + _to22))          # highest whole level reachable by 22
                    if _top <= int(_b):                    # no new level possible: not trained
                        main_target = _b
                        _weeks_main = 0.0
                    else:
                        main_target = min(main_target, _top + 0.05)
                        # weeks the main skill needed to reach that level (with its usual split)
                        _share = TRAINED_WEEK_SHARE.get(pos_code, 1.0)
                        _lo_w, _hi_w = 0.0, (22 - int(age)) * 16.0
                        for _ in range(30):
                            _mw = (_lo_w + _hi_w) / 2
                            if _b + _share * full_training_gain(primary_col, _b, age, _mw) < _top + 0.05:
                                _lo_w = _mw
                            else:
                                _hi_w = _mw
                        _weeks_main = _hi_w
                    # After the switch the secondary skill gets the training: pull it to its
                    # profile value plus that training (PDIM: defending ~10 -> ~10.8 at 21).
                    _secs = SECONDARY_TRAINED.get(pos_code)
                    if isinstance(_secs, str):
                        _secs = {_secs: 1.0}
                    _weeks_sec = max(0.0, int(days) / 7.0 - _weeks_main)
                    sec_target = []
                    for _sec, _part in (_secs or {}).items():
                        if (_weeks_sec > 0 and not is_known(_sec)
                                and not (skill_bands and skill_bands.get(_sec) is not None)):
                            _sec_base = float((richt_bench or {}).get(_sec, 0.0))
                            if _sec_base > 1.0:
                                sec_target.append((['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH'].index(_sec),
                                                   _sec_base + TRAINED_SHARE * full_training_gain(
                                                       _sec, _sec_base, age, _weeks_sec * _part)))
                    if sec_target:
                        diagnostics['secondary_training'] = [(['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH'][i], round(t, 2))
                                                             for i, t in sec_target] + [round(_weeks_sec, 1)]
                    else:
                        sec_target = None
            else:
                # Wage skill isn't trained (e.g. WTM: wage from PM, training on winger):
                # it stays about at its birthday value, and the trained skill gets the training:
                # its profile value plus the training since the birthday.
                main_cap = _b + 0.30
                main_target = _b
                if not is_known(_trained) and not (skill_bands and skill_bands.get(_trained) is not None):
                    _tb = float((richt_bench or {}).get(_trained, 0.0))
                    if _tb > 1.0:
                        _tshare = TRAINED_SHARE * TRAINED_WEEK_SHARE.get(pos_code, 0.75)
                        sec_target = [(['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH'].index(_trained),
                                       _tb + _tshare * full_training_gain(_trained, _tb, age, int(days) / 7.0))]
            _lo, _hi = bnds[primary_idx]
            # The wage decides the range: from the birthday value (skills don't drop before 28) up to
            # full training since then - also when that's below the position profile's minimum
            # (a weaker player than the national-team profile, e.g. a forward with scoring 8).
            _new_lo, _new_hi = max(_lo, _b), min(_hi, main_cap)
            if _new_lo >= _new_hi:
                _new_lo, _new_hi = _b, max(main_cap, _b + 0.05)
            bnds[primary_idx] = (_new_lo, _new_hi)
    diagnostics['main_training'] = (main_target, main_cap)

    # Lowest main skill the wage allows: Hattrick pays the best-paid skill in full and the others half, so a
    # secondary as high as the main skill (DE 12 + PM 12: PM pays more per level) explains part of the wage and
    # the main skill is lower than the wage alone suggests (Ciezkowski NCD: wage-only DE 13.4, real 12.x).
    # Range [main_low, wage-only value] = what TSI + wage allow; option 2 (multiskill) aims in its middle.
    main_low = None
    try:
        if (primary_idx >= 0 and primary_col in ('DE', 'PM', 'WI', 'Pas', 'SC') and not is_known(primary_col)
                and not (skill_bands and skill_bands.get(primary_col) is not None) and target_wage > 0):
            _bw = float(diagnostics.get('inferred_primary_birthday') or diagnostics.get('inferred_primary') or 0)
            _others = [k for k in ('DE', 'PM', 'WI', 'Pas', 'SC') if k != primary_col
                       and not is_known(k) and not (skill_bands and skill_bands.get(k) is not None)]
            if _bw > 2.0 and _others:
                _j = max(_others, key=lambda k: lookup_wage(_bw, k))
                _prof = {k: float((richt_bench or {}).get(k, 1.0)) for k in _skill_keys}
                for k, v in (current_skills or {}).items():
                    if v is not None and float(v) > 0:
                        _prof[k] = float(v)

                def _w_at(xv):
                    d = dict(_prof); d[primary_col] = xv; d[_j] = xv
                    w = calculate_exact(age, 0, spec, 6, 6, *[d[k] for k in _skill_keys])[3]
                    return w * (1.20 if is_foreign else 1.0)
                lo_x, hi_x = 1.0, _bw
                if _w_at(hi_x) >= target_wage:
                    for _ in range(40):
                        mx = (lo_x + hi_x) / 2
                        if _w_at(mx) < target_wage:
                            lo_x = mx
                        else:
                            hi_x = mx
                    main_low = round(min(_bw, (lo_x + hi_x) / 2), 3)
                    diagnostics['main_range'] = (main_low, round(_bw, 3), _j)
    except Exception:
        main_low = None
    if _contrib:
        diagnostics['shape'] = (order or (POSITION_ORDERS.get(pos_code) or ['NFW'])[0], accent)
        diagnostics['shape_profile'] = {k: round(float(v), 1) for k, v in (richt_bench or {}).items()}
    # Feasibility: the profile-based lower limits can need more TSI than the player has. A weaker or older
    # player than the profile (e.g. a 33-year-old foreign PNF: TSI 63k, scoring 18 from the wage, but PNF
    # senior limits PM >= 13.9 / passing >= 10.9 asked for ~100k TSI) then got all options stuck on the
    # limits, far off the TSI. Lower the secondary limits towards 1 until the lowest build fits the TSI.
    try:
        def _tsi_at(lows):
            _x = [float(v) for v in lows]
            _shm = 1 + 0.25 * _x[6] / 100.0
            if pos_code == 'K':
                return _solver_eval_keeper(_age_tsi_f, _spec_m, _age_wage_f, _shm, *_x)[0]
            return _solver_eval(age, _age_tsi_f, _spec_m, _age_wage_f, _shm, *_x)[0]
        _free = [i for i, k in enumerate(_skill_keys[:6]) if i != primary_idx and not is_known(k)
                 and not (skill_bands and skill_bands.get(k) is not None) and not (k == 'GK' and pos_code != 'K')]
        _lows = [b[0] for b in bnds]
        # the lowest build as the solver will see it: main skill at its wage value, form / stamina in the
        # middle of their displayed level (that is where the solver puts them)
        if 0 <= primary_idx < 6:
            _pm_v = float(diagnostics.get('inferred_primary_birthday') or diagnostics.get('inferred_primary') or _lows[primary_idx])
            # the main skill where the solver will really put it: with the training since the birthday (<28),
            # or still earning the wage today (28+). With the birthday value the lowest build looked like it
            # fitted the TSI, but the wage then lifted the main skill and every option missed the TSI
            # (NCD Borbola, 33: DE 17.55 assumed, 18.07 needed for the wage -> TSI +7%).
            _mt = (diagnostics.get('main_training') or (None, None))[0]
            if _mt:
                _pm_v = max(_pm_v, float(_mt))
            if int(age) >= 28 and diagnostics.get('inferred_primary'):
                _pm_v = max(_pm_v, float(diagnostics['inferred_primary']))
            _lows[primary_idx] = min(max(_lows[primary_idx], _pm_v), bnds[primary_idx][1])
        for _j, _v in ((7, vorm), (8, cond)):
            if len(_lows) > _j:
                _mid = float(_v) + 0.5 if float(_v) == int(float(_v)) else float(_v)
                _lows[_j] = min(max(_lows[_j], _mid), bnds[_j][1])
        if _free and target_tsi > 0 and _tsi_at(_lows) > target_tsi * FEASIBLE_TSI_MARGIN:
            def _scaled(f):
                return [1.0 + (lo - 1.0) * f if i in _free else lo for i, lo in enumerate(_lows)]
            if _tsi_at(_scaled(0.0)) <= target_tsi * FEASIBLE_TSI_AIM:
                f_lo, f_hi = 0.0, 1.0
                for _ in range(30):
                    f_mid = (f_lo + f_hi) / 2.0
                    if _tsi_at(_scaled(f_mid)) > target_tsi * FEASIBLE_TSI_AIM:
                        f_hi = f_mid
                    else:
                        f_lo = f_mid
                _new = _scaled(f_lo)
            else:
                _new = _scaled(0.0)
            for i in _free:
                bnds[i] = (round(_new[i], 3), bnds[i][1])
            diagnostics['bounds_relaxed'] = True
        # Still too much TSI with every free skill at its lowest: the main skill's lower limit is too high
        # (keepers: GK >= 75% of the age target; Feddersen, 32: GK 15.6 vs 15.4 from TSI -> TSI +171).
        # TSI is today's value and can't be exceeded, so lower that limit until the lowest build fits.
        if 0 <= primary_idx < 6 and target_tsi > 0:
            _base = [1.0 + (lo - 1.0) * 0.0 if i in _free else lo for i, lo in enumerate(_lows)]
            _base[primary_idx] = bnds[primary_idx][0]
            for _j in (7, 8):   # form / stamina at their lowest: only when nothing at all fits
                if len(_base) > _j:
                    _base[_j] = bnds[_j][0]
            if _tsi_at(_base) > target_tsi * 1.0005:
                p_lo, p_hi = 1.0, bnds[primary_idx][0]
                for _ in range(30):
                    p_mid = (p_lo + p_hi) / 2.0
                    _base[primary_idx] = p_mid
                    if _tsi_at(_base) > target_tsi * 0.999:
                        p_hi = p_mid
                    else:
                        p_lo = p_mid
                bnds[primary_idx] = (round(p_lo, 3), max(bnds[primary_idx][1], p_lo + 0.05))
                diagnostics['bounds_relaxed'] = True
        # The other way round: too LITTLE TSI room. The secondaries' upper limits come from the (Dutch) profile
        # (young CD: winger <= 3, scoring <= 4, passing <= 6.5). A multi-skilled player (Ciezkowski NCD 22:
        # DE 12 / PM 12 / WI 6 / PS 5 / SC 8) has more TSI than those limits allow next to a wage-fitting
        # main skill, so every option pushed the TSI into DE / PM and today's skills earned 24-41% more than
        # his wage. If even the highest build can't reach the TSI with the main skill where the wage allows,
        # let the main skill go down to the lowest value the wage allows and raise the secondaries' limits.
        if (WIDEN_FOR_TSI and 0 <= primary_idx < 6 and target_tsi > 0 and main_low is not None and _free
                and pos_code != 'K'):
            def _wage_x(v):
                _xv = [float(t) for t in v]
                _shm = 1 + 0.25 * _xv[6] / 100.0
                w_ = _solver_eval(age, _age_tsi_f, _spec_m, _age_wage_f, _shm, *_xv)[1]
                return w_ * (1.20 if is_foreign else 1.0)
            _hiv = [b[1] for b in bnds]
            _hiv[primary_idx] = bnds[primary_idx][0]          # main skill as low as allowed now
            _lov = [b[0] for b in bnds]
            if _tsi_at(_hiv) < target_tsi * 0.995 and _wage_x(_lov) > target_wage * 1.05:
                _m = min(bnds[primary_idx][0], float(main_low))
                bnds[primary_idx] = (round(_m, 3), max(bnds[primary_idx][1], _m + 0.05))
                _hiv[primary_idx] = _m

                def _widened(f):
                    out = list(_hiv)
                    for i in _free:
                        out[i] = min(_m, max(bnds[i][1], 1.0 + (bnds[i][1] - 1.0) * f))
                    return out
                f_lo, f_hi = 1.0, 6.0
                if _tsi_at(_widened(f_hi)) >= target_tsi * 1.01:
                    for _ in range(30):
                        fm = (f_lo + f_hi) / 2.0
                        if _tsi_at(_widened(fm)) < target_tsi * 1.01:
                            f_lo = fm
                        else:
                            f_hi = fm
                    _wd = _widened(f_hi)
                else:
                    _wd = _widened(f_hi)
                for i in _free:
                    bnds[i] = (bnds[i][0], round(max(bnds[i][1], _wd[i]), 3))
                diagnostics['bounds_widened'] = True
    except Exception:
        pass
    diagnostics['bounds'] = [tuple(round(float(v), 2) for v in b) for b in bnds]

    # Young wingers (NW/WTM) are trained main-skill-first: passing, defending and scoring
    # stay close to their age benchmark (≈6 at 21-22) instead of soaking up the
    # HTMS/TSI budget, and a normal winger's WI leads his PM by ~3 levels (15/12, 16/11).
    # Applied to every strategy, with per-strategy slack so the options still differ:
    #   strategy -> (secondary cap = benchmark + slack, minimum NW WI-PM gap)
    _WING_W = 1e7
    _WING_RULES = {
        '1. Default Profile (Target Skills Benchmark)': (1.0, 2.5),
        '2. Multiskill Profile (Balanced Secondaries)': (2.0, 1.5),
        '3. Maximize Primary Skill (Mono-skill)':       (0.5, 3.0),
    }
    # Young NIM: the same secondary limits apply (passing/defending/scoring stay near
    # the age benchmark while playmaking is trained first).
    # Young forwards (NFW/PNF): scoring first, so PM / WI / passing stay near their age
    # target instead of soaking up TSI that belongs to scoring.
    _YOUNG_SECONDARIES = {'NW': (('DE', 1), ('Pas', 4), ('SC', 5)), 'WTM': (('DE', 1), ('Pas', 4), ('SC', 5)),
                          'NIM': (('DE', 1), ('Pas', 4), ('SC', 5)),
                          'NFW': (('PM', 2), ('WI', 3), ('Pas', 4)), 'PNF': (('PM', 2), ('WI', 3), ('Pas', 4)),
                          'NCD': (('PM', 2), ('Pas', 4)), 'NWB': (('PM', 2), ('Pas', 4))}
    _young_wing = pos_code in _YOUNG_SECONDARIES and age <= 24 and bool(richt_bench)
    _wing_skills = [(_i, float(richt_bench.get(_k, 6.0))) for _k, _i in _YOUNG_SECONDARIES.get(pos_code, ())
                    if _young_wing and not is_bounded(_k)]
    _nw_gap_on = _young_wing and pos_code == 'NW' and not is_bounded('PM') and not is_bounded('WI')
    _senior_wage_floor = 0.995 - SENIOR_WAGE_DROP_PER_WEEK * max(0, min(int(days), 111)) / 7.0
    _senior_soft_floor = []
    _soft = (SENIOR_WING_SOFT_FLOOR if pos_code in ('NW', 'WTM') else SENIOR_POS_SOFT_FLOOR.get(pos_code, {}))
    # Not for the contribution shape: these floors are Dutch senior habits (NCD playmaking 1.5 above the
    # profile, NWB winger...). With a weak senior they pushed all TSI into one skill (Borbola: PM 12.2, PS 1).
    if (not _contrib and int(age) >= SENIOR_WING_MIN_AGE and richt_bench and _soft):
        for _k, _below in _soft.items():
            if not is_bounded(_k):
                _fl = float(richt_bench.get(_k, 1.0)) - _below
                _cap = SENIOR_POS_SOFT_FLOOR_MAX.get(pos_code, {}).get(_k)
                _senior_soft_floor.append((_skill_keys.index(_k), min(_fl, _cap) if _cap else _fl))
    _senior_sh_target = (float(richt_bench.get('SH', 5.0))
                         if (SENIOR_SH_PULL > 0 and int(age) >= SENIOR_SH_MIN_AGE and htms_unknown and richt_bench
                             and pos_code not in ('SHWB', 'K') and not is_bounded('SH'))
                         else None)
    _senior_wing_gap = (float(richt_bench.get('WI', 0)) - float(richt_bench.get('PM', 0))
                        if (pos_code in ('NW', 'WTM') and int(age) >= SENIOR_WING_MIN_AGE and richt_bench
                            and SENIOR_WING_GAP_WEIGHT > 0 and not is_bounded('PM') and not is_bounded('WI'))
                        else None)
    # Young NWB: defending leads winger (Dutch U21 wing-backs: DE 0.4-3.6 above WI, ~2.1
    # on average). Per strategy: minimum DE-WI gap.
    _NWB_GAP = {'1. Default Profile (Target Skills Benchmark)': 1.5,
                '2. Multiskill Profile (Balanced Secondaries)': 1.0,
                '3. Maximize Primary Skill (Mono-skill)':       2.0}
    _nwb_gap_on = _young_wing and pos_code == 'NWB' and not is_bounded('DE') and not is_bounded('WI')

    def _young_wing_cap_penalty(x, strat):
        if not _young_wing or strat not in _WING_RULES:
            return 0.0
        slack, gap = _WING_RULES[strat]
        p = sum(max(0.0, x[i] - (bench + slack)) ** 2 * _WING_W for i, bench in _wing_skills)
        if _nw_gap_on:
            p += max(0.0, x[2] - (x[3] - gap)) ** 2 * _WING_W
        if _nwb_gap_on:
            p += max(0.0, x[3] - (x[1] - _NWB_GAP[strat])) ** 2 * _WING_W
        return p

    # Hattrick shows form/condition as whole levels: aim for the middle of the level, not
    # its bottom (the bottom needs extra skill for the same TSI and pushes skills up).
    _form_target = min(float(vorm) + 0.5, 8.0) if float(vorm) == int(vorm) else float(vorm)
    _cond_target = stamina_middle(cond, age)

    # The wage was set on the birthday, so it may sit below the current skills by what
    # training since then explains (at most ~0.2 main-skill levels a week), but not more.
    # Before: any wage overshoot was only weakly penalised, even at 0 days, which let the
    # main skill jump to the next level (e.g. an NCD with DE 14.39 came out at 15.09).
    # Wage ceiling: the wage was set on the birthday, so the wage for TODAY's skills can be at most
    # what full training of the wage skill since then adds (the steepest possible rise; training
    # another skill raises the wage less). Real training speed instead of the old 0.2 levels/week.
    _pc = diagnostics.get('primary_col')
    _ip = float(diagnostics.get('inferred_primary_birthday') or diagnostics.get('inferred_primary', 0) or 0)
    _wk = max(0, min(int(days), 111)) / 7.0
    if _pc in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC') and _ip > 1.0 and int(age) < 28:
        # birthday skills: the wage skill from the wage, the others from the profile; then the
        # biggest wage rise full training could give (wage skill, or the skill really trained, e.g. WTM winger)
        _K7 = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
        _bs = {k: max(1.0, float((richt_bench or {}).get(k, 1.0))) for k in _K7}
        _bs[_pc] = _ip
        _w0 = calculate_exact(age, 0, spec, 6, 6, *[_bs[k] for k in _K7])[3]
        _ratios = []
        for _sk in {_pc, TRAINED_SKILL.get(pos_code, _pc)}:
            _d = dict(_bs)
            _d[_sk] = min(25.0, _d[_sk] + full_training_gain(_sk, _d[_sk], age, _wk))
            _ratios.append(calculate_exact(age, 0, spec, 6, 6, *[_d[k] for k in _K7])[3] / max(_w0, 1.0))
        _wage_tol = max(_ratios)
        # Expected wage today (option 1's assumption: the main skill trained ~96% since the birthday, the
        # rest as on the birthday): the wage for today's skills should be about this, not anywhere up to the
        # ceiling. Steers TSI that the main skill doesn't need into skills that pay little (the wage then
        # tells the secondaries apart: playmaking pays ~2x winger per level).
        if main_target is not None and float(main_target) > _ip:
            _d = dict(_bs); _d[_pc] = float(main_target)
            diagnostics['wage_expected_ratio'] = calculate_exact(age, 0, spec, 6, 6, *[_d[k] for k in _K7])[3] / max(_w0, 1.0)
    elif int(age) < 28:
        _wage_tol = 1.44 ** (_wk * 0.10)
    else:
        _wage_tol = 1.0
    if untrained and int(age) < 28:
        _wage_tol = 1.0   # not trained since the birthday: today's skills earn the birthday wage
    # + 2% for the rounding of the displayed wage; 28+: + 0.5% only (skills only drop after the birthday)
    _wage_tol = max(_wage_tol, 1.0) * (1.005 if int(age) >= 28 else 1.02)
    diagnostics['wage_ceiling'] = target_wage * _wage_tol

    # Seniors with HTMS unknown: the HTMS estimate is a rough guess (35 Dutch NT seniors: 0.90-1.11 x the
    # real HTMS), and at full weight it pushed builds towards it (Tamaela NWB: winger 16.6 instead of 17.2).
    if int(age) >= 28 and not use_exact_htms and SENIOR_HTMS_EST_WEIGHT is not None:
        htms_penalty_weight = min(htms_penalty_weight, CONTRIB_SENIOR_HTMS_EST_WEIGHT if _contrib else SENIOR_HTMS_EST_WEIGHT)

    def make_objective(strat):
        wage_confidence = max(
            0.35, 1.0 - (max(0, min(int(days), 111)) / 111.0) * 0.65
        )
        # Exact HTMS + known skills: wage decides the composition, so weigh it heavily.
        has_known_skills = bool(current_skills and any(
            float(v) > 0 for v in current_skills.values()
            if v is not None
        ))
        # Overshooting the (birthday) wage: firm right after the birthday, when the skills
        # can't have grown yet, back to the old looseness later in the age year. Tested on
        # Dutch U21s: main-skill error 0.29 -> 0.12 at 30 days, unchanged at 84 days.
        _fresh = max(0.0, 1.0 - max(0, min(int(days), 111)) / 111.0)
        wage_base_weight = (1e10 if (use_exact_htms and has_known_skills)
                            else 2e7 + (4e8 * _fresh ** 5 if pos_code in ('NCD', 'NFW', 'WTM', 'NW') else 0.0))

        _ceil_mult = MONO_WAGE_CEIL_MULT * (RETRY_WAGE_MULT if _relaxed_caps else 1.0)   # all options
        _w_exp = diagnostics.get('wage_expected_ratio') if WAGE_EXPECT_WEIGHT > 0 else None

        def objective(x):
            sh_mul = 1 + 0.25 * x[6] / 100.0
            if pos_code == 'K':
                c_tsi, c_wage_curr, c_htms_curr = _solver_eval_keeper(
                    _age_tsi_f, _spec_m, _age_wage_f, sh_mul,
                    x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8]
                )
            else:
                c_tsi, c_wage_curr, c_htms_curr = _solver_eval(
                    age, _age_tsi_f, _spec_m, _age_wage_f, sh_mul,
                    x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8]
                )
            if is_foreign:
                c_wage_curr *= 1.20

            err_tsi = ((c_tsi - target_tsi) / max(target_tsi, 1.0)) ** 2 * 1e11
            # TSI is today's value: never above it (a keeper with known levels came out +102 because the
            # wage asked for more goalkeeping than his TSI allows; the wage gives way, not the TSI)
            if c_tsi > target_tsi + 0.4:
                err_tsi += ((c_tsi - target_tsi) / max(target_tsi, 1.0)) ** 2 * 1e14
            err_wage = (
                ((c_wage_curr - target_wage) / max(target_wage, 1.0)) ** 2
                * (wage_base_weight if c_wage_curr >= target_wage else 1e9)
                * wage_confidence
            )
            if _w_exp is not None and strat[0] in ('1', '2'):
                err_wage += ((c_wage_curr / (target_wage * _w_exp)) - 1.0) ** 2 * WAGE_EXPECT_WEIGHT
            if c_wage_curr > target_wage * _wage_tol:      # hard ceiling: more than training allows
                err_wage += ((c_wage_curr - target_wage * _wage_tol) / max(target_wage, 1.0)) ** 2 * WAGE_LIMIT_WEIGHT * _ceil_mult
            if int(age) < 28 and c_wage_curr < target_wage * 0.995:   # skills don't drop before 28 (0.5% = rounding)
                err_wage += ((target_wage * 0.995 - c_wage_curr) / max(target_wage, 1.0)) ** 2 * WAGE_LIMIT_WEIGHT
            # 28+: skills can drop after the birthday, so today's skills may earn a bit less than the
            # wage - but only by what decline since the birthday explains. Before, any shortfall was
            # cheap for seniors: Bouderbala (32, 6 days) came out 2.8% under his wage.
            # 30+: no net growth since the birthday (training barely beats the decline), so today's skills
            # may not earn more than the wage either. Before, up to +2% was allowed and only weakly held,
            # so the main skill sat at the top of its range (Tamaela NWB 32: DE 18.4-18.5 vs real 18.25,
            # wage +2.9%) and took TSI away from the secondaries.
            if int(age) >= SENIOR_WAGE_CEIL_AGE and c_wage_curr > target_wage * SENIOR_WAGE_CEIL:
                err_wage += ((c_wage_curr - target_wage * SENIOR_WAGE_CEIL) / max(target_wage, 1.0)) ** 2 * SENIOR_WAGE_LIMIT_WEIGHT * _ceil_mult
            if int(age) >= 28 and c_wage_curr < target_wage * _senior_wage_floor:
                err_wage += ((target_wage * _senior_wage_floor - c_wage_curr) / max(target_wage, 1.0)) ** 2 * SENIOR_WAGE_LIMIT_WEIGHT * _ceil_mult
            # From 28 skills can drop, but only since the birthday (when the wage was set): today's
            # skills may earn less than the actual wage by at most what that time allows.
            # Before, there was no lower limit at all from 28 (Bouderbala, 6 days after his
            # birthday: solved skills earned 2.8% less than his actual wage).
            elif int(age) >= 28 and SENIOR_WAGE_DROP_PER_WEEK is not None:
                _wfloor = max(0.80, 0.995 - SENIOR_WAGE_DROP_PER_WEEK * max(0, int(days)) / 7.0)
                if c_wage_curr < target_wage * _wfloor:
                    err_wage += ((target_wage * _wfloor - c_wage_curr) / max(target_wage, 1.0)) ** 2 * SENIOR_WAGE_FLOOR_WEIGHT * _ceil_mult
            _htms_t = effective_target_htms * (1.0 if use_exact_htms else HTMS_STRAT_SCALE.get(strat[0], 1.0))
            err_htms = (
                ((c_htms_curr - _htms_t) / max(_htms_t, 1.0))
                ** 2
            ) * htms_penalty_weight

            anchor_primary = 0.0
            if (htms_unknown and primary_idx >= 0 and not diagnostics.get('primary_ambiguous') and not _relaxed_caps
                    and not (strat[0] == '2' and main_low is not None and MULTI_LOW_SHARE > 0)):
                p_val = x[primary_idx]
                inf_p = _inferred_primary_solve
                anchor_primary = ((p_val - inf_p) ** 2) * (5e6 if p_val < inf_p else 5e4)

            err_form = ((x[7] - _form_target) ** 2) * FORM_MID_WEIGHT_POS.get(pos_code, FORM_MID_WEIGHT)
            err_cond = ((x[8] - _cond_target) ** 2) * max(FORM_MID_WEIGHT_POS.get(pos_code, FORM_MID_WEIGHT), STAMINA_MID_WEIGHT)

            p_richt = sum(
                (
                    (x[i] - max(float(
                        (3.0 if (k == 'SH' and pos_code not in ('SHWB','K') and age <= 22 and accent != 'longshot')
                         else (float(richt_bench.get(k, 1.0)) * 1.2 if (k == 'SH' and pos_code not in ('SHWB','K') and age <= 26)
                         else richt_bench.get(k, 1.0)))
                    ), 1.0))
                    / max(float(
                        3.0 if (k == 'SH' and pos_code not in ('SHWB','K') and age <= 22 and accent != 'longshot')
                        else (float(richt_bench.get(k, 1.0)) * 1.2 if (k == 'SH' and pos_code not in ('SHWB','K') and age <= 26)
                        else richt_bench.get(k, 1.0))
                    ), 1.0)
                ) ** 2
                * (
                    # Prior strength: SHWB/K SH strongest, then keeper DE, known-skill runs, default.
                    (1e8 if (k == 'SH' and pos_code == 'SHWB')
                     else (1e7 if (k == 'SH' and pos_code == 'K')
                     else (5e5 if (pos_code == 'K' and k == 'DE')
                     # Forwards' left-over defending: hold it near the profile (~3), or TSI
                     # gets parked there (every forward came out at DE 4-4.6).
                     else (5e6 if (pos_code in ('NFW', 'PNF') and k == 'DE')
                     else (1e4 if (pos_code == 'K' and k != 'SH')
                     else (1e8 if (has_known_skills and not is_bounded(k)
                                   and k not in (diagnostics.get('primary_col','SC'),))
                     else (1e4 if strat == '1. Default Profile (Target Skills Benchmark)' else 1e3)))))))
                    * (RETRY_PROFILE_MULT if _relaxed_caps else 1.0)
                )
                for i, k in enumerate(_skill_keys)
                if richt_bench and not is_bounded(k)
            )

            p_ref = 0.0
            if ref_bench:
                p_ref = sum(
                    (
                        (x[i] - max(float(ref_bench.get(k, 1.0)), 1.0))
                        / max(float(ref_bench.get(k, 1.0)), 1.0)
                    ) ** 2
                    * (5e6 if (k == 'SH' and pos_code in ('SHWB', 'K')) else 1.5e4)
                    for i, k in enumerate(_skill_keys)
                    if not is_bounded(k)
                    # Keeper / set-piece WB with HTMS unknown: peers' set pieces can't be measured
                    # either, and pulling towards their average dragged set pieces down (every
                    # keeper on the same lower limit, SHWBs ~1 level low). Profile decides instead.
                    and not (pos_code in ('K', 'SHWB') and k == 'SH' and htms_unknown)
                )

            pas_val = x[4]
            # Passing above 9 is penalised, except for DFW and inner midfielders, whose
            # profile has 13-17 passing at 29: there the cap follows the profile.
            # (Not for young forwards: tested, it moved their scoring by up to a level.)
            # Senior forwards (SENIOR_PASS_MIN_AGE+): also the profile. Dutch NT NFWs aged 30-32 have
            # passing 13.5-15.3; a cap at 9 pushed their passing ~4 levels too low and moved that TSI
            # into winger. (Tried for senior wingers too: winger got worse, so not for NW.)
            pass_cap = (max(9.0, float((richt_bench or {}).get('Pas', 1.0)) + 2.0)
                        if (_contrib or pos_code in ('DFW', 'TDFW', 'NIM', 'OIM-Q', 'OIM-H') or (pos_code in ('NFW', 'PNF') and int(age) >= SENIOR_PASS_MIN_AGE)
                            or (SENIOR_WING_PASS_CAP and pos_code in ('NW', 'WTM') and int(age) >= SENIOR_WING_MIN_AGE))
                        else 9.0)
            pass_bias = (
                max(0.0, pas_val - pass_cap) ** 2 * 2e5
                if pos_code not in ('CADEF', 'OCD', 'CDTW')
                else 0.0
            )
            pass_bias += _young_wing_cap_penalty(x, strat)
            # Seniors, HTMS unknown: set pieces are invisible in TSI and only 0.25%/level in the
            # wage, so the solver used them to top up the HTMS estimate and they drifted to the top
            # of their range (Bouderbala, 32: 12.0 against a profile of 8). Hold them at the profile.
            # Senior wingers: soft floors under the hard bounds. When TSI is too low for a normal
            # winger shape, defending/scoring give way before winger drops below playmaking.
            if _senior_soft_floor:
                for _i, _fl in _senior_soft_floor:
                    pass_bias += max(0.0, _fl - x[_i]) ** 2 * SENIOR_WING_SOFT_WEIGHT
            if _senior_sh_target is not None:
                pass_bias += (x[6] - _senior_sh_target) ** 2 * SENIOR_SH_PULL
            # Senior wingers (NW/WTM 28+): winger and playmaking keep about the profile's gap.
            # Skills decline together after 30, but TSI drops least per lost winger level, so the
            # solver took the whole decline out of winger (Bouderbala, 32: PM 18.2 / WI 15.3).
            if _senior_wing_gap is not None:
                _g = (x[3] - x[2]) - _senior_wing_gap
                _below = SENIOR_WING_GAP_BELOW.get(pos_code, SENIOR_WING_GAP_TOL)
                pass_bias += (max(0.0, -_g - _below) ** 2 * SENIOR_WING_BELOW_WEIGHT.get(pos_code, SENIOR_WING_GAP_WEIGHT)
                              + max(0.0, _g - SENIOR_WING_GAP_TOL) ** 2 * SENIOR_WING_GAP_WEIGHT)
            
            base_err = (
                err_tsi
                + err_wage
                + err_htms
                + anchor_primary
                + err_form
                + err_cond
                + pass_bias
                + (10000.0 * (x[0] - 1.0) ** 2 if pos_code != 'K' else 0.0)
                # SHWB / NWB: WI must stay above PM
                + (1e8 * max(0, x[2] - x[3]) ** 2 if pos_code == 'SHWB' and not is_bounded('PM') and not is_bounded('WI') else 0.0)
                + (1e8 * max(0, x[2] - x[3]) ** 2 if pos_code == 'NWB' and not is_bounded('PM') and not is_bounded('WI') else 0.0)
                + p_richt
                + p_ref
            )

            var_mod = 0.0
            if strat == '2. Multiskill Profile (Balanced Secondaries)':
                outfield = sorted([x[1], x[2], x[3], x[4], x[5]], reverse=True)
                var_mod += MULTI_TOP_PULL * ((outfield[0] - outfield[1]) ** 2 * 1000.0 + (
                    outfield[0] - outfield[2]
                ) ** 2 * 500.0)
                if MULTI_SEC_EVEN > 0 and primary_idx >= 0:
                    # balanced secondaries: the 3 highest skills after the main one close together
                    _secs = sorted((x[_i] for _i in range(1, 6) if _i != primary_idx), reverse=True)[:3]
                    var_mod += MULTI_SEC_EVEN * ((_secs[0] - _secs[1]) ** 2 + (_secs[0] - _secs[2]) ** 2)

            return base_err + var_mod

        if sec_target:
            _base_obj2 = objective

            def objective(x, _targets=tuple(sec_target)):
                return _base_obj2(x) + sum(1e9 * ((x[_si] - _st) / _st) ** 2 for _si, _st in _targets)
        if strat[0] == '3' and primary_idx >= 0 and MONO_MAIN_PUSH > 0:
            _base_mono = objective

            def objective(x):
                # mono: main skill as high as TSI / wage / HTMS allow, the others lower to keep TSI exact
                return _base_mono(x) - MONO_MAIN_PUSH * x[primary_idx]
        if strat[0] == '2' and primary_idx >= 0 and MULTI_MAIN_PULL > 0:
            _base_multi = objective

            def objective(x):
                # multi: main skill as low as the wage allows, the others higher to keep TSI exact
                return _base_multi(x) + MULTI_MAIN_PULL * x[primary_idx]
        if (strat[0] == '2' and main_low is not None and MULTI_LOW_SHARE > 0 and diagnostics.get('main_range')
                and not (main_target is not None and main_cap is not None)):
            # no training range (28+ or birthday today): aim the multiskill option inside the wage range directly
            _hi_w = float(diagnostics['main_range'][1])
            _tgt_m = _hi_w - MULTI_LOW_SHARE * (_hi_w - main_low)
            _base_m = objective

            def objective(x, _tgt_m=_tgt_m):
                return _base_m(x) + MAIN_TARGET_WEIGHT * ((x[primary_idx] - _tgt_m) / _tgt_m) ** 2
        if main_target is not None and main_cap is not None and not _relaxed_caps:
            # All options assume the player trained every week since the birthday (~96% of full
            # training: only a little lost to injuries); mono = exactly full training.
            _b = diagnostics.get('inferred_primary_birthday', 0.0)
            _full = main_cap - 0.05 - _b
            if strat[0] == '3':
                _tgt = _b + _full
            elif strat[0] == '2':
                _tgt = _b + MULTI_MAIN_FACTOR * (main_target - _b)
                if main_low is not None and MULTI_LOW_SHARE > 0:
                    _tgt = _b - MULTI_LOW_SHARE * (_b - main_low)
            else:
                _tgt = main_target
            _base_obj = objective

            def objective(x, _tgt=_tgt):
                return _base_obj(x) + MAIN_TARGET_WEIGHT * ((x[primary_idx] - _tgt) / _tgt) ** 2
        # Mono: the main skill as high as its allowed range goes (wage + training since the birthday, or the
        # senior wage limits), the other skills lower so TSI stays exact. A what-if for a player trained
        # in his main skill only; option 1 stays the best guess.
        if (strat[0] == '3' and MONO_MAIN_WEIGHT > 0 and primary_idx >= 0
                and not is_known(primary_col) and not (skill_bands and skill_bands.get(primary_col) is not None)):
            _top = float(bnds[primary_idx][1])
            _mono_base = objective

            def objective(x, _top=_top):
                return _mono_base(x) + MONO_MAIN_WEIGHT * ((x[primary_idx] - _top) / _top) ** 2
        return objective

    # ── Unstick whole numbers ────────────────────────────────────────────────
    # HTMS counts whole levels and the (birthday) wage pulls skills down, so a skill that
    # HTMS needs at level N often lands on exactly N.00. Only when that happens: keep
    # every level (HTMS unchanged), move the stuck skill into its level, and let the
    # other skills shift as little as possible to keep TSI exact. The birthday wage may
    # rise by what training since then explains (≈0.2 main-skill levels/week).
    _bday_tol = 1.44 ** min(max(0, min(int(days), 111)) / 7.0 * 0.20, 3.0)

    def _unstick(x0):
        x0 = np.array(x0, dtype=float)
        cand_idx = [i for i, k in enumerate(_skill_keys)
                    if not is_bounded(k) and (k != 'GK' or pos_code == 'K') and x0[i] >= 2.0]
        stuck = [i for i in cand_idx if (x0[i] - math.floor(x0[i])) < 0.04]
        if not stuck:
            return x0
        lvl = {i: math.floor(x0[i]) for i in cand_idx}
        pb = [(x0[i], x0[i]) for i in range(len(_skill_keys))] + [bnds[7], bnds[8]]
        for i in cand_idx:
            pb[i] = (max(bnds[i][0], lvl[i] + 0.01), min(bnds[i][1], lvl[i] + 0.99))
            if pb[i][0] > pb[i][1]:
                pb[i] = (x0[i], x0[i])

        def ev(v):
            sh_mul = 1 + 0.25 * v[6] / 100.0
            if pos_code == 'K':
                return _solver_eval_keeper(_age_tsi_f, _spec_m, _age_wage_f, sh_mul, *v[:9])
            return _solver_eval(age, _age_tsi_f, _spec_m, _age_wage_f, sh_mul, *v[:9])

        def obj(v):
            t, w, _ = ev(v)
            if is_foreign:
                w *= 1.20
            e = ((t - target_tsi) / max(target_tsi, 1.0)) ** 2 * 1e14
            if target_wage > 0:
                tw = float(target_wage)
                if w < tw:
                    e += ((w - tw) / tw) ** 2 * 1e9
                elif w > tw * _bday_tol:
                    e += ((w - tw * _bday_tol) / tw) ** 2 * 2e7
            e += ((v[7] - x0[7]) ** 2 + (v[8] - x0[8]) ** 2) * 1e5
            if _senior_wing_gap is not None:   # keep senior wingers' winger >= playmaking here too
                _lim = v[2] + _senior_wing_gap - SENIOR_WING_GAP_BELOW.get(pos_code, SENIOR_WING_GAP_TOL)
                e += max(0.0, _lim - v[3]) ** 2 * 1e12
            for i in cand_idx:
                if i in stuck:
                    f = v[i] - lvl[i]
                    if i == primary_idx:
                        # main skill: TSI decides, just not on the edge of the level
                        e += (max(0.0, 0.12 - f) ** 2 + max(0.0, f - 0.95) ** 2) * 1e8
                    else:
                        e += (f - 0.5) ** 2 * 1e6
                else:
                    e += (v[i] - x0[i]) ** 2 * 1e6       # everything else: stay put
            return e

        start = x0.copy()
        for i in stuck:
            start[i] = min(max(lvl[i] + 0.3, pb[i][0]), pb[i][1])
        try:
            cand = opt.minimize(obj, start, method='L-BFGS-B', bounds=pb,
                                options={'ftol': 1e-12, 'maxiter': 500}).x
        except Exception:
            return x0
        (ta, _, ha), (tb, _, hb) = ev(x0), ev(cand)
        ok = (abs(tb - target_tsi) <= abs(ta - target_tsi) + target_tsi * 1e-4) and hb == ha
        return cand if ok else x0

    def _tsi_x(x_):
        return calculate_exact(age, days, spec, x_[7], x_[8], *x_[:7])[1]

    def _fine(x_):
        """Best form/stamina pair (0.001 steps, within bounds) for TSI: (miss, form, stamina)."""
        best = (abs(_tsi_x(x_) - target_tsi), x_[7], x_[8])
        for df in range(-30, 31):
            f_ = round(x_[7] + df * 0.001, 3)
            if not (bnds[7][0] - 1e-9 <= f_ <= bnds[7][1] + 1e-9):
                continue
            y = np.array(x_); y[7] = f_
            t_ = _tsi_x(y)
            if t_ <= 0:
                continue
            c_exact = 1.0 + (x_[8] - 1.0) * (target_tsi / t_) ** 2
            for c_ in (round(c_exact, 3) + d for d in (-0.001, 0.0, 0.001)):
                c_ = round(c_, 3)
                if not (bnds[8][0] - 1e-9 <= c_ <= bnds[8][1] + 1e-9):
                    continue
                y[8] = c_
                m_ = abs(_tsi_x(y) - target_tsi)
                if m_ < best[0] - 1e-9:
                    best = (m_, f_, c_)
        return best

    def _exact_clean(x0):
        x_ = np.array(x0, dtype=float)
        for i in range(7):
            x_[i] = round(float(min(max(x_[i], bnds[i][0]), bnds[i][1])), 3)
        x_[7], x_[8] = round(x_[7], 3), round(x_[8], 3)
        m_, f_, c_ = _fine(x_)
        if m_ < 0.5:
            x_[7], x_[8] = f_, c_
            return x_
        # coarse step on a free skill (0.01), then fine again
        # skills with a known level (band) may move too, within their level: with every level known (imported
        # own players) nothing was free and TSI stayed 1 off
        free = [i for i, k in enumerate(_skill_keys[:7])
                if k in ('DE', 'PM', 'WI', 'Pas', 'SC') and i != primary_idx and not is_known(k)]
        if pos_code == 'K' and not is_known('GK'):
            # keeper TSI hangs on goalkeeping only: the other skills can't close the last points
            # (Feddersen: 47,729 instead of 47,730)
            free = [0] + free
        best = (m_, x_.copy(), f_, c_)
        # smallest change first: +-0.001 on every free skill, then +-0.002, ... (first exact hit wins)
        for step in range(1, 61):
            for i in free:
                for k in (step, -step):
                    y = np.array(x_); y[i] = round(y[i] + k * 0.001, 3)
                    if not (bnds[i][0] - 1e-9 <= y[i] <= bnds[i][1] + 1e-9):
                        continue
                    if abs(_tsi_x(y) - target_tsi) > 150:      # only close candidates get the fine search
                        continue
                    m2, f2, c2 = _fine(y)
                    if m2 < best[0] - 1e-9:
                        best = (m2, y, f2, c2)
                    if best[0] < 0.5:
                        break
                if best[0] < 0.5:
                    break
            if best[0] < 0.5:
                break
        x_ = best[1]; x_[7], x_[8] = best[2], best[3]
        return x_

    strats = [
        '1. Default Profile (Target Skills Benchmark)',
        '2. Multiskill Profile (Balanced Secondaries)',
        '3. Maximize Primary Skill (Mono-skill)',
    ]
    if default_only:
        strats = strats[:1]
    if _relaxed_caps and main_low is not None:
        # second try (non-standard player): the main skill may also sit as low as the wage allows
        bnds[primary_idx] = (min(bnds[primary_idx][0], main_low), bnds[primary_idx][1])
    _bnds_all = list(bnds)
    for strat in strats:
        # option 2 (multi) may go down to the lowest main skill the wage allows; the others keep the
        # wage-only floor (lowering it for option 1 made Dutch-shaped players worse: main 0.33 -> 0.37)
        bnds = list(_bnds_all)
        if strat[0] == '2' and main_low is not None and MULTI_LOW_SHARE > 0:
            bnds[primary_idx] = (min(bnds[primary_idx][0], main_low), bnds[primary_idx][1])
        try:
            res_de = opt.differential_evolution(
                make_objective(strat),
                bounds=bnds,
                popsize=20 if dominant_pinned else 25,
                maxiter=120 if dominant_pinned else 150,
                tol=1e-7,
                seed=42,
                polish=False,
            )
            final_x = opt.minimize(
                make_objective(strat),
                res_de.x,
                method='L-BFGS-B',
                bounds=bnds,
                options={'ftol': 1e-10, 'maxiter': 300},
            ).x
        except Exception:
            final_x = res_de.x

        # Senior wingers: the winger >= playmaking rule makes a narrow valley the search often misses
        # (Bouderbala, 32: it stopped at WI 17.4 / PM 17.9 with a 25x worse score than WI 18.0 / PM 17.8).
        # Also start from the best build with winger lifted to its gap (and the left-overs lowered).
        if _senior_wing_gap is not None:
            _obj = make_objective(strat)
            _best_f, _best_x = _obj(final_x), final_x
            for _drop in (0.0, 1.0, 2.0):
                _y = np.array(final_x, dtype=float)
                _y[3] = _y[2] + _senior_wing_gap + 0.05
                for _i in (1, 4, 5):                       # DE, Pas, SC
                    _y[_i] -= _drop
                _y = np.array([min(max(v, lo), hi) for v, (lo, hi) in zip(_y, bnds)])
                try:
                    _cand = opt.minimize(_obj, _y, method='L-BFGS-B', bounds=bnds,
                                         options={'ftol': 1e-10, 'maxiter': 300}).x
                except Exception:
                    continue
                _f = _obj(_cand)
                if _f < _best_f:
                    _best_f, _best_x = _f, _cand
            final_x = _best_x

        final_x = _unstick(final_x)

        # Keeper with a known HTMS: set pieces don't count in keeper TSI and barely in the
        # wage, and HTMS moves in whole-level steps where the optimiser gets stuck. So pick
        # SH directly: the value that hits the HTMS, closest to where the solver put it.
        if (pos_code == 'K' and use_exact_htms and not is_bounded('SH')):
            _lo, _hi = bnds[6]
            _base = [final_x[i] for i in range(6)]
            _best = None
            for _sh in np.arange(max(1.0, _lo), min(25.0, _hi) + 1e-9, 0.01):
                _h = calculate_htms_ability(*_base, float(_sh))
                _key = (abs(_h - target_htms), abs(_sh - final_x[6]))
                if _best is None or _key < _best[0]:
                    _best = (_key, float(_sh))
            if _best is not None:
                final_x = np.array(final_x, dtype=float)
                # middle of the matching band, not its edge
                _cands = [v for v in np.arange(max(1.0, _lo), min(25.0, _hi) + 1e-9, 0.01)
                          if calculate_htms_ability(*_base, float(v)) == calculate_htms_ability(*_base, _best[1])
                          and math.floor(v) == math.floor(_best[1])]
                final_x[6] = round(float(np.mean(_cands)), 2) if _cands else _best[1]

        # TSI must be exact. TSI grows with sqrt(form - 1) and sqrt(stamina - 1), so if the solver
        # ended a little off (it balances many wishes), move form - then stamina - within the
        # level Hattrick shows until TSI matches exactly.
        if target_tsi > 0:
            final_x = np.array(final_x, dtype=float)
            for _idx in (7, 8):
                _t = calculate_exact(age, days, spec, final_x[7], final_x[8], *final_x[:7])[1]
                if _t <= 0 or abs(_t - target_tsi) < 0.5:
                    break
                _lo_b, _hi_b = bnds[_idx]
                _new = 1.0 + (final_x[_idx] - 1.0) * (target_tsi / _t) ** 2
                final_x[_idx] = float(min(max(_new, _lo_b), _hi_b))
            # Still off (form/stamina fixed by A/B/C, or at the edge of their level): scale the
            # other skills (never the wage skill or known/banded skills) until TSI is exact.
            _t = calculate_exact(age, days, spec, final_x[7], final_x[8], *final_x[:7])[1]
            if _t > 0 and abs(_t - target_tsi) >= 0.5:
                _free = [i for i, k in enumerate(_skill_keys[:7])
                         if k in ('DE', 'PM', 'WI', 'Pas', 'SC') and i != primary_idx
                         and not is_known(k) and not (skill_bands and skill_bands.get(k) is not None)
                         # senior wingers: never scale winger here - it dropped Bouderbala's winger
                         # from 17.88 to 17.55, below playmaking 17.69
                         and not (k == 'WI' and _senior_wing_gap is not None)]
                if _free:
                    _base_x = np.array(final_x, dtype=float)

                    def _scaled(f):
                        x_ = np.array(_base_x)
                        for i in _free:
                            x_[i] = float(min(max(1.0 + (_base_x[i] - 1.0) * f, bnds[i][0]), bnds[i][1]))
                        return x_
                    _tsi_of = lambda f: calculate_exact(age, days, spec, _base_x[7], _base_x[8], *_scaled(f)[:7])[1]
                    _lo_f, _hi_f = 0.8, 1.2
                    if (_tsi_of(_lo_f) - target_tsi) * (_tsi_of(_hi_f) - target_tsi) <= 0:
                        for _ in range(40):
                            _mf = (_lo_f + _hi_f) / 2
                            if (_tsi_of(_mf) - target_tsi) * (_tsi_of(_lo_f) - target_tsi) > 0:
                                _lo_f = _mf
                            else:
                                _hi_f = _mf
                        final_x = _scaled((_lo_f + _hi_f) / 2)
            # last fine adjustment: form, then stamina (within their bounds) for the final few points
            for _ in range(2):
                for _idx in (7, 8):
                    _t = calculate_exact(age, days, spec, final_x[7], final_x[8], *final_x[:7])[1]
                    if _t <= 0 or abs(_t - target_tsi) < 0.5:
                        break
                    _lo_b, _hi_b = bnds[_idx]
                    _new = 1.0 + (final_x[_idx] - 1.0) * (target_tsi / _t) ** 2
                    final_x[_idx] = float(min(max(_new, _lo_b), _hi_b))

        # Clean numbers: skills and form/stamina to 3 decimals, TSI still exact.
        #  1. coarse: move one free skill (never the wage skill / known ones) in 0.001 steps
        #  2. fine:   search form and stamina in 0.001 steps within their levels
        if target_tsi > 0:
            final_x = _exact_clean(final_x)

        _, c_tsi, _, c_wage, _, c_htms, c_htms28 = calculate_exact(
            age, days, spec, final_x[7], final_x[8], final_x[0], final_x[1], final_x[2], final_x[3], final_x[4], final_x[5], final_x[6]
        )
        results.append({
            'Strategy': strat,
            'GK': final_x[0],
            'DE': final_x[1],
            'PM': final_x[2],
            'WI': final_x[3],
            'Pas': final_x[4],
            'SC': final_x[5],
            'SH': final_x[6],
            'Vorm': final_x[7],
            'Cond': final_x[8],
            'Calc_TSI': c_tsi,
            'Calc_Wage': c_wage * (1.20 if is_foreign else 1.0),
            'Calc_HTMS': c_htms,
            'Calc_HTMS28': (
                float(effective_target_htms28)
                if (isinstance(c_htms28, (int, float)) and age >= 28 and target_htms28 > 0)
                else c_htms28
            ),
            'Target_HTMS': effective_target_htms,
            'Target_HTMS28': effective_target_htms28,
            'Loss': 0,
        })

    # (A 4th "profile shape" option was removed: forcing the age profile's shape on a player kept
    #  skills the profile has at 1 exactly at 1 and squeezed the rest. The import still uses
    #  profile_shape_solution for its quick estimate of new players.)

    # The wage is a hard fact: when every option's skills earn clearly more than the wage allows (the left-over
    # caps forced TSI into a well-paid skill), solve again with those caps lifted.
    _ceil = float(diagnostics.get('wage_ceiling') or 0)
    if (not _relaxed_caps and RELAX_CAPS_ON_WAGE and _ceil > 0 and results and pos_code != 'K'
            and min(float(r.get('Calc_Wage') or 0) for r in results) > _ceil * 1.03):
        try:
            _cr = country_richtskills
            if RETRY_LIFT and richt_bench and diagnostics.get('main_range'):
                # Secondary skills: the player has more of them than the profile (that's why the caps broke).
                # Lift every outfield secondary by the same amount, so that with the main skill in the middle of
                # what the wage allows the TSI fits, instead of letting one skill (often winger: cheap in TSI
                # and wage) take all of it (Ciezkowski: WI 11.2, real 6).
                _ml, _mh, _ = diagnostics['main_range']
                _mv = (_ml + _mh) / 2.0
                _secs = [k for k in ('DE', 'PM', 'WI', 'Pas', 'SC') if k != primary_col
                         and not is_known(k) and not (skill_bands and skill_bands.get(k) is not None)]
                _fv, _cv = (min(float(vorm) + 0.5, 8.0) if float(vorm) == int(vorm) else float(vorm)), stamina_middle(cond, age)

                def _tsi_l(L):
                    d = {k: float(richt_bench.get(k, 1.0)) for k in _skill_keys}
                    for k, v in (current_skills or {}).items():
                        if v is not None and float(v) > 0:
                            d[k] = float(v)
                    d[primary_col] = _mv
                    for k in _secs:
                        d[k] = min(_mv - 0.5, max(1.0, d[k] + L))
                    return calculate_tsi_for_form(age, _fv, _cv, *[d[k] for k in _skill_keys[:6]]), d
                lo_l, hi_l = -3.0, 12.0
                if _secs and _tsi_l(lo_l)[0] <= target_tsi <= _tsi_l(hi_l)[0]:
                    for _ in range(40):
                        ml = (lo_l + hi_l) / 2
                        if _tsi_l(ml)[0] < target_tsi:
                            lo_l = ml
                        else:
                            hi_l = ml
                    _lifted = _tsi_l((lo_l + hi_l) / 2)[1]
                    _cr = dict(country_richtskills or {})
                    _cr[pos_code] = dict(richt_bench, **{k: round(_lifted[k], 2) for k in _secs})
                    diagnostics['retry_lift'] = round((lo_l + hi_l) / 2, 2)
            _r2, _d2 = auto_solve_subskills(
                target_tsi, target_wage, target_htms, target_htms28, age, days, spec, vorm, cond, pos_code,
                _cr, htms_unknown, htms28_unknown, current_skills, is_foreign, skill_bands,
                pre_ref_df, training_plan=training_plan, weeks_missed=weeks_missed, default_only=default_only,
                exclude_player=exclude_player, form_stamina_case=form_stamina_case, wage_skill=wage_skill,
                # contribution shape: the retry aims at the lifted profile itself (the pure contribution
                # shape would put the non-contributing skills back at 1 and push TSI into the wage skill again)
                shape=('target' if _contrib else shape), order=order, accent=accent, _relaxed_caps=True,
                untrained=untrained)
            if _r2:
                _d2['caps_relaxed'] = True
                _d2['retry_profile'] = (_cr or {}).get(pos_code) if isinstance(_cr, dict) else None
                return _r2, _d2
        except Exception:
            pass
    return results, diagnostics

# ==============================================================================
# 6. BIRTHDAY WAGE (display helper — does not affect the solver)
# ==============================================================================
def primary_skill_for(pos_code):
    """Main (wage-driving) skill for a position code."""
    if pos_code == 'K':
        return 'GK'
    if 'CD' in pos_code or 'WB' in pos_code:
        return 'DE'
    if 'FW' in pos_code or pos_code == 'PNF':
        return 'SC' if pos_code not in ('DFW', 'TDFW') else 'Pas'
    if pos_code in ('NW', 'W', 'WTM', 'OW', 'DW'):
        return 'WI'
    return 'PM'


def birthday_wage_range(skills, pos_code, age, days, spec, is_foreign=False):
    """Hattrick sets the wage on the birthday, so the actual wage belongs to the skills
    of `days` ago. Returns (low, typical, high, weeks):
      high    = wage of today's skills (no training since the birthday)
      typical = main skill lowered by 0.10 level/week of training
      low     = main skill lowered by the maximum (0.20/week, keepers 0.30/week)."""
    weeks = max(0, min(int(days), 111)) / 7.0
    main = wage_main_skill(pos_code, age, spec,
                           skills={k: float(skills.get(k, 1.0) or 1.0) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']})[0] \
        if pos_code != 'K' else 'GK'
    max_rate = 0.30 if pos_code == 'K' else 0.20

    def wage_with(gain):
        s = {k: float(skills.get(k, 1.0) or 1.0) for k in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']}
        s[main] = max(1.0, s[main] - gain)
        w = calculate_exact(age, days, spec, 6.0, 6.0, s['GK'], s['DE'], s['PM'], s['WI'],
                            s['Pas'], s['SC'], s['SH'])[3]
        return w * (1.20 if is_foreign else 1.0)

    return (wage_with(min(weeks * max_rate, 3.0)), wage_with(weeks * 0.10), wage_with(0.0), weeks)

# ==============================================================================
# Player links + forum markup (Hattrick / Hattrick Portal), as in Hattline's "Copy Player"
# ==============================================================================
POSITION_NAMES = {
    'K': 'Keeper', 'NCD': 'Central Defender', 'OCD': 'Central Defender (offensive)', 'CAD': 'Central Defender (counter-attack)',
    'NWB': 'Wing Back', 'SHWB': 'Wing Back (set pieces)', 'NIM': 'Inner Midfielder',
    'OIM-Q': 'Inner Midfielder (offensive)', 'OIM-H': 'Inner Midfielder (offensive)',
    'PDIM': 'Inner Midfielder (defensive)', 'NW': 'Winger', 'WTM': 'Winger (towards middle)',
    'NFW': 'Forward', 'PNF': 'Forward (powerful)', 'DFW': 'Forward (defensive)', 'TDFW': 'Forward (defensive, technical)',
}


def player_links(player_id):
    """(Hattrick URL, Hattrick Portal URL) for a player ID, or (None, None)."""
    try:
        pid = int(float(player_id))
    except (TypeError, ValueError):
        return None, None
    if pid <= 0:
        return None, None
    return (f'https://www.hattrick.org/Club/Players/Player.aspx?playerId={pid}',
            f'https://hattrickportal.online/Tracker/Player.aspx?playerID={pid}')


def _num_txt(v, decimals=2):
    """7.5 -> '7.5', 3.0 -> '3', 14.234 -> '14.23'."""
    v = round(float(v), decimals)
    return str(int(v)) if v == int(v) else f'{v:.{decimals}f}'.rstrip('0').rstrip('.')


def _level_txt(v):
    """'solid (7.5)': the Hattrick word for the whole level, plus the value."""
    lv = int(max(0, min(float(v), len(HATTRICK_SKILL_WORDS) - 1)))
    return f'{HATTRICK_SKILL_WORDS[lv].lower()} ({_num_txt(v)})'


FORUM_STAMINA_MAX = 9.0   # Hattrick's maximum: formidable (9) is shown as 9


def forum_stamina(v):
    """Stamina for forum copies: as stored, never above formidable (9), Hattrick's maximum."""
    try:
        return min(float(v), FORUM_STAMINA_MAX)
    except (TypeError, ValueError):
        return v


def player_forum_markup(name, player_id=None, age=None, days=None, experience=None, leadership=None,
                        tsi=None, position=None, wage=None, specialty=None, injury=None,
                        form=None, stamina=None, skills=None):
    """Hattrick forum markup for one player, in the Hattline 'Copy Player' layout."""
    def ok(v):
        try:
            return v is not None and str(v).lower() not in ('', 'nan', 'none') and float(v) == float(v)
        except (TypeError, ValueError):
            return False

    pid = None
    try:
        pid = int(float(player_id)) if ok(player_id) and float(player_id) > 0 else None
    except (TypeError, ValueError):
        pid = None
    head = f'[b]{name}' + (f' [playerid={pid}]' if pid else '') + '[/b]'
    lines = [f'[q]{head}']
    if ok(age):
        lines.append(f'{int(float(age))} years' + (f' and {int(float(days))} days' if ok(days) else ''))
    lines.append('')
    xp_ls = []
    if ok(experience):
        xp_ls.append(f'{_level_txt(experience)} experience')
    if ok(leadership):
        xp_ls.append(f'{_level_txt(leadership)} leadership')
    if xp_ls:
        lines.append('Has ' + ' and '.join(xp_ls) + '.')
    if ok(tsi):
        lines.append('TSI: ' + f'{int(round(float(tsi))):,}'.replace(',', ' '))
    if position:
        lines.append(f'Best position: {POSITION_NAMES.get(position, position)}')
    if ok(wage):
        w = int(round(float(wage)))
        lines.append(f'Wage: [money]{w}[/money]/week ([money]{w * 16}[/money]/season)')
    spec = clean_spec(specialty) if specialty else 'None'
    lines.append(f'Specialty: [b]{spec if spec != "None" else "-"}[/b]')
    inj = float(injury) if ok(injury) else -1
    lines.append('Injuries : ' + ('Healthy' if inj <= 0 else f'Injured ({_num_txt(inj, 0)} weeks)'))
    lines.append('')
    fs = ''
    if ok(form):
        fs += f'[tr][th]Form[/th][td]{_level_txt(form)}[/td][/tr]'
    if ok(stamina):
        fs += f'[tr][th]Stamina[/th][td]{_level_txt(forum_stamina(stamina))}[/td][/tr]'
    if fs:
        lines.append(f'[table]{fs}[/table]')
    names = [('GK', 'Keeper'), ('DE', 'Defending'), ('PM', 'Playmaking'), ('WI', 'Winger'),
             ('Pas', 'Passing'), ('SC', 'Scoring'), ('SH', 'Set Pieces')]
    sk = ''.join(f'[tr][th]{label}[/th][td]{_level_txt((skills or {}).get(key))}[/td][/tr]'
                 for key, label in names if ok((skills or {}).get(key)))
    out = '\n'.join(lines) + (f'\n[table]{sk}[/table]' if sk else '') + '[/q]'
    return out


def hatstats_value(rating):
    """HatStats points of one sector rating: disastrous very low (1.00) = 1, wretched very
    low (2.00) = 5, ... divine very high (20.75) = 80, i.e. 4 x rating - 3."""
    return max(0.0, 4.0 * float(rating or 0) - 3.0)


def hatstats(ratings):
    """HatStats = 3 x midfield + the three defence + the three attack values."""
    r = ratings or {}
    return (3 * hatstats_value(r.get('MID', 0)) +
            sum(hatstats_value(r.get(s, 0)) for s in ('RD', 'CD', 'LD', 'RA', 'CA', 'LA')))

# ==============================================================================
# 7. TRAINING SPEED (training planner)
# Port of the HT-Tools training formula (Ventouris Anastasios, github.com/ventouris/hattricktools,
# static/js/training.js, GPL v3; also used by ht.8ic.ro). Training "points" needed per level grow
# with the level; the points per week depend on the training type, coach, assistants, intensity,
# stamina share and age (an effective-weeks table per age year), with a skill drop above 15.
# Checked against Tooltrick's own HTMS-based speed (full training from 7.5 at 17, to 21): within
# 0.1-0.4 of a level, except defending, which HT-Tools trains ~0.7 faster.
# ==============================================================================
TRAINING_TYPES = {   # label -> (code, base speed)
    'Goalkeeping': ('GK', 0.335), 'Defending': ('Def', 0.206), 'Defensive positions': ('DefPos', 0.094),
    'Winger (crossing)': ('Cross', 0.315), 'Winger 50% (crossing)': ('Cross 50%', 0.1575),
    'Wing attacks': ('WingAtt', 0.219), 'Playmaking': ('PM', 0.22), 'Playmaking 50%': ('PM 50%', 0.11),
    'Scoring': ('Sco', 0.218), 'Shooting': ('Shoot', 0.097), 'Passing': ('Pass', 0.237),
    'Through passes': ('ThPass', 0.178), 'Set pieces': ('SP', 0.941), 'Set pieces 25%': ('SP 25%', 1.183),
}
# Tooltrick skill -> the full training for it
SKILL_TRAINING = {'GK': 'Goalkeeping', 'DE': 'Defending', 'PM': 'Playmaking', 'WI': 'Winger (crossing)',
                  'Pas': 'Passing', 'SC': 'Scoring', 'SH': 'Set pieces'}
TRAINING_SKILL = {'Goalkeeping': 'GK', 'Defending': 'DE', 'Defensive positions': 'DE', 'Winger (crossing)': 'WI',
                  'Winger 50% (crossing)': 'WI', 'Wing attacks': 'WI', 'Playmaking': 'PM', 'Playmaking 50%': 'PM',
                  'Scoring': 'SC', 'Shooting': 'SC', 'Passing': 'Pas', 'Through passes': 'Pas',
                  'Set pieces': 'SH', 'Set pieces 25%': 'SH'}
TRAINING_AGE_TABLE = [0.000, 16.000, 31.704, 47.117, 62.246, 77.094, 91.668, 105.972, 120.012, 133.791,
                      147.316, 160.591, 173.620, 186.408, 198.960, 211.279, 223.370, 235.238]   # age 17 .. 34
TRAINING_ASSIST_FACTOR = [0.66, 0.692, 0.724, 0.756, 0.788, 0.82, 0.852, 0.884, 0.916, 0.948, 0.98,
                          1.012, 1.044, 1.076, 1.108, 1.14]                                       # 0 .. 15 levels
TRAINING_COACH_FACTOR = {4: 0.774, 5: 0.867, 6: 0.943, 7: 1.0, 8: 1.045}                      # weak .. excellent
TRAINING_MAX_AGE = 33
# Slow-down above level 15, relative to HT-Tools (1.0). HT-Tools trained levels 16-19 too slowly:
# winger 50% from 7.0 at 17y0d took 211 weeks to 19 (18->19: 65 weeks) against 179 (42) in a
# hattrickportal record (xflygame analysis, Oct 2026). 0.72 fits that record: 179 weeks, 18->19 41.
# One record at one age, so re-fit when more real level-ups above 15 are known.
TRAINING_DROP_SCALE = 0.72


def _training_points(v):
    v = float(v)
    return (v ** 1.72 - 1) / (6.0896 * 1.72) if v < 9 else 2.45426 + (v - 5) ** 1.96 / (4.7371 * 1.96)


def training_speed(training, coach=7, assistants=10, intensity=100, stamina=10, share=1.0):
    """Training points per effective week (HT-Tools 'totalK'). share: part of the weeks this
    training is given (e.g. 0.5 when it alternates with another training)."""
    base = TRAINING_TYPES.get(training, (None, 0.0))[1]
    a = int(min(max(int(assistants), 0), len(TRAINING_ASSIST_FACTOR) - 1))
    c = TRAINING_COACH_FACTOR.get(int(coach), 1.0)
    return c * TRAINING_ASSIST_FACTOR[a] * float(intensity) / 100.0 * (100.0 - float(stamina)) / 100.0 * base * float(share)


def training_schedule(years, days, value, training, coach=7, assistants=10, intensity=100, stamina=10, share=1.0):
    """Ages at which each next whole level is reached (HT-Tools trainingcalc).
    Returns [(level, years, days, weeks since the previous level)], at most up to TRAINING_MAX_AGE."""
    k = training_speed(training, coach, assistants, intensity, stamina, share)
    years, days = int(years), int(min(max(int(days), 0), 111))
    if k <= 0 or years < 17 or years > TRAINING_MAX_AGE:
        return []
    T = TRAINING_AGE_TABLE
    level, sub = int(float(value)), float(value) - int(float(value))
    a0 = (days / 112.0) * (T[years - 16] - T[years - 17]) + T[years - 17]
    start = years + days / 112.0
    out, shtraf, ageee, age1, oldweek = [], 0.0, start, start, years * 112 + days
    for lev in range(level + 1, 21):
        xxx = (_training_points(lev) - _training_points(level + sub)) / k + a0
        i = next((i for i in range(17, 35) if xxx <= T[i - 17]), None)
        if i is None or i - 1 < 17:
            break
        agge = i - 1
        old = ageee
        ageee = agge + (xxx - T[agge - 17]) / (T[agge - 16] - T[agge - 17])
        if lev > level + sub + 1:
            s = 1.0 / 16 - ageee + old
        else:
            s = (1.0 / 16 - ageee + start) * (lev - (level + sub))
        shtraf += max(s, 0.0)
        drop = TRAINING_DROP_SCALE * lev ** 7.5 * 8 / 1e12 if lev > 15 else 0.0
        age1 = ageee if lev <= 15 else age1 + (ageee - old) / (1 - drop * (ageee - old) * 16)
        ry = int(age1 + shtraf + 0.0089)
        rd = int((age1 + shtraf - ry + 0.0089) * 112)
        if ry > TRAINING_MAX_AGE:
            break
        weeks = ((ry * 112 + rd) - oldweek) / 7.0
        oldweek = ry * 112 + rd
        out.append((lev, ry, rd, weeks))
    return out


def skill_at_age(target_years, target_days, years, days, value, training, **kw):
    """Projected skill value at an age (linear between the levels training_schedule gives)."""
    pts = [(int(years) + int(days) / 112.0, float(value))] + \
          [(y + d / 112.0, float(lev)) for lev, y, d, _ in training_schedule(years, days, value, training, **kw)]
    t = int(target_years) + int(target_days) / 112.0
    if t <= pts[0][0]:
        return float(value)
    for (a0, v0), (a1, v1) in zip(pts, pts[1:]):
        if a0 <= t <= a1:
            return v0 + (v1 - v0) * (t - a0) / max(a1 - a0, 1e-9)
    if len(pts) == 1:
        return float(value)
    # past the last level within the age range: no further level (stays just below the next)
    return min(pts[-1][1] + 0.99, pts[-1][1] + (t - pts[-1][0]) * (pts[-1][1] - pts[-2][1]) / max(pts[-1][0] - pts[-2][0], 1e-9))


# ==============================================================================
# 8. NON-TARGET ESTIMATE (Auto-Solver extra option)
# ==============================================================================
NON_TARGET_MIN_PEERS = 5


def non_target_profile(ref_df, pos_code, age, spec=None, min_peers=NON_TARGET_MIN_PEERS):
    """Skill shape for a solve without country / custom target skills: the average of Reference DB
    players at the same position and a similar age (+-1, then +-2, +-3 years), when there are at least
    min_peers; otherwise the plain built-in age profile (no country targets). Returns (profile, source)."""
    pos = normalize_position(pos_code)
    keys = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
    try:
        if ref_df is not None and not ref_df.empty and 'Positie' in ref_df.columns:
            d = ref_df[ref_df['Positie'] == pos]
            ages = pd.to_numeric(d['Leeftijd'], errors='coerce')
            for w in (1, 2, 3):
                peers = d[(ages - int(age)).abs() <= w]
                if len(peers) >= min_peers:
                    prof = {k: float(pd.to_numeric(peers[k], errors='coerce').mean()) for k in keys}
                    if all(pd.notna(v) for v in prof.values()):
                        return prof, f'{len(peers)} Reference DB peers, age {int(age) - w}-{int(age) + w}'
    except Exception:
        pass
    prof = estimate_age_richtskills(int(age), spec).get(pos) or RICHTSKILLS_29.get(pos, RICHTSKILLS_29['NFW'])
    return dict(prof), 'built-in profile (too few Reference DB peers)'


# ==============================================================================
# 9. CONTRIBUTION SHAPE (Auto-Solver: "Contribution table" instead of the target skills)
# ==============================================================================
# Absolute rating contributions per order (Dutch NT staff sheet, from Hattrick Organizer): the relative
# sector values of role_weights.py x line weights (central defence 33.0, wing defence 40.0 per side,
# midfield 90.0, central attack 41.2, wing attack 38.2 per side; reproduces all 63 values within 0.4).
# The NL U22 sheet's position scores = these weights' average of the skills + 1.335 x log10(experience).
CONTRIB_SKILLS = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC']
CONTRIBUTIONS = {o: dict(zip(CONTRIB_SKILLS, v)) for o, v in {
    'K': (77.5, 31.5, 0, 0, 0, 0), 'NCD': (0, 53.7, 22.5, 0, 0, 0), 'OCD': (0, 40.0, 36.0, 0, 0, 0),
    'CDTW': (0, 54.5, 13.5, 9.9, 0, 0), 'NWB': (0, 49.3, 13.5, 22.6, 0, 0), 'DWB': (0, 54.2, 9.0, 17.2, 0, 0),
    'OWB': (0, 41.1, 18.0, 26.4, 0, 0), 'WBTM': (0, 53.1, 18.0, 13.4, 0, 0),
    'NW': (0, 20.6, 40.5, 32.9, 14.5, 0), 'DW': (0, 32.6, 27.0, 26.4, 10.1, 0), 'OW': (0, 13.1, 27.0, 38.2, 16.4, 0),
    'WTM': (0, 19.8, 49.5, 28.3, 12.3, 0), 'NIM': (0, 20.4, 90.0, 0, 23.5, 9.1), 'DIM': (0, 30.3, 85.5, 0, 12.8, 5.4),
    'OIM': (0, 8.5, 85.5, 0, 33.9, 12.8), 'IMTW': (0, 20.5, 81.0, 22.6, 21.3, 0),
    'NFW': (0, 0, 22.5, 18.4, 24.3, 61.8), 'TDFW': (0, 0, 31.5, 9.9, 53.2, 33.0), 'FTW': (0, 0, 13.5, 32.5, 19.8, 53.9),
    # PNF is not in the sheet: NFW scaled per skill by how the Dutch PNF profile differs from the Dutch NFW
    # profile at 29 (implied weight ~ ((skill - 1) / (scoring - 1))^2).
    'PNF': (0, 0, 28.9, 7.0, 13.2, 61.8),
}.items()}
CONTRIB_TSI_W = {'GK': 1.0, 'DE': 1.034, 'PM': 1.031, 'WI': 0.826, 'Pas': 1.035, 'SC': 1.038}
# Orders that can be chosen per solver position (first = default).
POSITION_ORDERS = {
    'K': ['K'], 'NCD': ['NCD', 'CDTW'], 'OCD': ['OCD'], 'CAD': ['NCD', 'CDTW'], 'NWB': ['NWB', 'DWB', 'OWB', 'WBTM'],
    'SHWB': ['NWB', 'DWB', 'OWB', 'WBTM'], 'NW': ['NW', 'DW', 'OW'], 'WTM': ['WTM'],
    'NIM': ['NIM', 'OIM', 'IMTW'], 'OIM-Q': ['OIM'], 'OIM-H': ['OIM'], 'PDIM': ['DIM'],
    'NFW': ['NFW', 'FTW'], 'PNF': ['PNF'], 'DFW': ['TDFW'], 'TDFW': ['TDFW'],
}
DEFENDER_ORDERS = {'NCD', 'OCD', 'CDTW', 'NWB', 'DWB', 'OWB', 'WBTM'}
# Counter-attack tactic: only defenders count, passing twice as much as defending (Hattrick wiki).
# Size fitted on the counter-attack CD targets of Bangladesh and Zambia (DE 18, PM 10, PS 14 at ~29-30):
# with +22.8 defending / +45.6 passing the ideal NCD shape is DE 18 / PM 10.2 / PS 14.4.
ACCENT_COUNTER_DE = 22.8
ACCENT_COUNTER_PAS = 45.6
# Long shots tactic level = 1.66 x average scoring + 0.55 x average set pieces of the outfield players
# (Unwritten Manual). No country targets to fit on, so a judgement: scoring +20 for every outfield
# player (a 29-year-old NIM: SC 7 -> ~11, CD SC 1 -> ~11), set pieces at the same 0.55 / 1.66 ratio.
ACCENT_LONGSHOT_SC = 20.0
ACCENT_LONGSHOT_SH = ACCENT_LONGSHOT_SC * 0.55 / 1.66
ACCENTS = {'none': 'None', 'counter': 'Counter-attack', 'longshot': 'Long shots'}


def order_contributions(order, accent=None):
    """Contribution weights of an order, with a tactic accent added. Returns ({skill: weight}, set-pieces weight)."""
    c = dict(CONTRIBUTIONS.get(order) or CONTRIBUTIONS['NFW'])
    sh = 0.0
    if accent == 'counter' and order in DEFENDER_ORDERS:
        c['DE'] += ACCENT_COUNTER_DE
        c['Pas'] += ACCENT_COUNTER_PAS
    elif accent == 'longshot' and order != 'K':
        c['SC'] += ACCENT_LONGSHOT_SC
        sh = ACCENT_LONGSHOT_SH
    return c, sh


def contribution_profile(base, pos_code, order=None, accent=None):
    """The profile `base` (target skills for this age) reshaped by the contribution table: the main skill
    stays, and the TSI of the contributing secondary skills is spread in the order's ideal shape
    (skill - 1 ~ sqrt(contribution / TSI weight)). Skills without a contribution keep the profile value
    (most players still have some passing etc.). Long shots also raises set pieces."""
    pos = normalize_position(pos_code)
    order = order or (POSITION_ORDERS.get(pos) or ['NFW'])[0]
    prof = {k: float(v) for k, v in dict(base or {}).items()}
    for k in CONTRIB_SKILLS + ['SH']:
        prof.setdefault(k, 1.0)
    c, sh_w = order_contributions(order, accent)
    outf = ['GK'] if pos == 'K' else [k for k in CONTRIB_SKILLS if k != 'GK']
    top = max(prof[k] for k in outf)
    pref = {'NW': 'WI', 'NWB': 'DE', 'SHWB': 'DE', 'NCD': 'DE', 'OCD': 'DE', 'CAD': 'DE'}.get(pos)
    main = pref if pref and prof[pref] >= top - 0.5 else max(outf, key=lambda k: prof[k])
    sec = [k for k in CONTRIB_SKILLS if k != main and c[k] > 0 and (k != 'GK' or pos == 'K')]
    if sec:
        tw = CONTRIB_TSI_W
        budget = sum(tw[k] * max(prof[k] - 1.0, 0.0) ** 3 for k in sec)
        unit = sum(tw[k] * (c[k] / tw[k]) ** 1.5 for k in sec)
        if budget > 0 and unit > 0:
            x = (budget / unit) ** (1.0 / 3.0)
            for k in sec:
                prof[k] = round(min(prof[main], 1.0 + x * (c[k] / tw[k]) ** 0.5), 2)
    if sh_w > 0 and c[main] > 0:
        prof['SH'] = round(max(prof['SH'], 1.0 + (prof[main] - 1.0) * (sh_w / (c[main] / CONTRIB_TSI_W[main])) ** 0.5), 2)
    return prof


def contribution_rating(skills, order, xp=None):
    """Contribution-weighted average of the skills for an order (the NL sheet's position score),
    plus 1.335 x log10(experience) when xp is given."""
    import math
    c = CONTRIBUTIONS[order]
    r = sum(c[k] * float(skills.get(k, 1.0) or 1.0) for k in CONTRIB_SKILLS) / sum(c.values())
    return r + (1.335 * math.log10(xp) if xp and xp > 0 else 0.0)


def order_fit(skills, order):
    """How well the skills suit an order (%): his contribution / the best contribution the same skill TSI
    could give in that order's ideal shape. Independent of how strong the player is."""
    c, tw = CONTRIBUTIONS[order], CONTRIB_TSI_W
    s = {k: float(skills.get(k, 1.0) or 1.0) for k in CONTRIB_SKILLS}
    budget = sum(tw[k] * max(s[k] - 1.0, 0.0) ** 3 for k in CONTRIB_SKILLS)
    unit = sum(tw[k] * (c[k] / tw[k]) ** 1.5 for k in CONTRIB_SKILLS if c[k] > 0)
    best = sum(c.values()) + budget ** (1.0 / 3.0) * unit ** (2.0 / 3.0)
    return 100.0 * sum(c[k] * s[k] for k in CONTRIB_SKILLS) / best if best > 0 else 0.0


def best_orders(skills, n=3, keeper=None):
    """[(order, fit %)] best first. Keepers only fit K; outfield players not K (unless keeper=None and GK leads)."""
    s = {k: float(skills.get(k, 1.0) or 1.0) for k in CONTRIB_SKILLS}
    if keeper is None:
        keeper = s['GK'] >= max(s[k] for k in CONTRIB_SKILLS if k != 'GK')
    orders = ['K'] if keeper else [o for o in CONTRIBUTIONS if o != 'K']
    fits = sorted(((o, order_fit(s, o)) for o in orders), key=lambda t: -t[1])
    return fits[:n]


# Pure contribution shape: no Dutch skill levels at all. The secondaries follow the order's ideal shape
# relative to the main skill (skill - 1 ~ sqrt(contribution / TSI weight)), skills without a contribution
# stay at 1 (set pieces 2), and the whole shape is fitted to this player's TSI and wage. Only the wage skill's
# position (which skill is main) comes from the profile.
CONTRIB_PURE = True


def pure_contribution_profile(base, pos_code, order, accent, age, days, spec, vorm, cond, tsi, wage, is_foreign):
    pos = normalize_position(pos_code)
    order = order or (POSITION_ORDERS.get(pos) or ['NFW'])[0]
    c, sh_w = order_contributions(order, accent)
    prof = {k: float(v) for k, v in dict(base or {}).items()}
    outf = ['GK'] if pos == 'K' else [k for k in CONTRIB_SKILLS if k != 'GK']
    top = max(prof.get(k, 1.0) for k in outf)
    pref = {'NW': 'WI', 'NWB': 'DE', 'SHWB': 'DE', 'NCD': 'DE', 'OCD': 'DE', 'CAD': 'DE'}.get(pos)
    main = pref if pref and prof.get(pref, 1.0) >= top - 0.5 else max(outf, key=lambda k: prof.get(k, 1.0))
    m = float(prof.get(main, 10.0))
    tw = CONTRIB_TSI_W
    cm = c.get(main, 0.0) / tw[main] if c.get(main, 0.0) > 0 else max(c[k] / tw[k] for k in CONTRIB_SKILLS) or 1.0
    shape = {'GK': 1.0, 'DE': 1.0, 'PM': 1.0, 'WI': 1.0, 'Pas': 1.0, 'SC': 1.0, 'SH': 2.0}
    for k in CONTRIB_SKILLS:
        if k == main:
            shape[k] = m
        elif c.get(k, 0) > 0 and (k != 'GK' or pos == 'K'):
            shape[k] = min(m, 1.0 + (m - 1.0) * ((c[k] / tw[k]) / cm) ** 0.5)
    if pos in ('K', 'SHWB'):
        shape['SH'] = float(prof.get('SH', 2.0))
    elif sh_w > 0:
        shape['SH'] = 1.0 + (m - 1.0) * (sh_w / cm) ** 0.5
    try:
        fit = profile_shape_solution(pos, age, days, spec, vorm, cond, tsi, wage, is_foreign, shape)
        return {k: round(float(fit.get(k, shape[k])), 2) for k in shape}
    except Exception:
        return shape


# ==============================================================================
# 10. ALL OUTCOMES (Auto-Solver beta): every whole-level skill combination that fits TSI + wage, ranked by a prior
# ==============================================================================
# TSI and wage give two equations for five unknown outfield skills, so many combinations fit (often 30,000-90,000
# whole-level combos). Instead of one optimiser answer, list them all and average them, weighted by how close each
# is to a prior (the target profile, or the user's own players at this position). Tested Oct 2026 on 33 real Dutch
# U22 players: main skill error 0.38 -> 0.17, other skills 0.94 -> 0.70 (Auto-Solver option 1 -> this); with the
# user's own players as prior (leave-one-out): AFRN centre-backs' other skills ~2.0 -> ~1.0.
OUTCOME_SKILLS = ['DE', 'PM', 'WI', 'Pas', 'SC']
OUTCOME_TSI_W = np.array([1.034, 1.031, 0.826, 1.035, 1.038])
OUTCOME_PRIOR_SD = 2.0
_OUTCOME_WGRID = None


# How real Dutch NT seniors (83 players, exact skills, ages 29-33) differ from the target profile, per position.
# E.g. real NT centre backs have ~2 more PM and ~1.6 less Passing than the profile. Applied to the NT template
# only, faded in by age (none at 22 or younger, full from 28), because it was measured on seniors.
NT_REAL_OFFSET = {
    'NCD':  {'DE': -0.3, 'PM': 1.9, 'Pas': -1.6},
    'NWB':  {'DE': -0.1, 'PM': 0.4, 'WI': 0.9, 'Pas': -0.4},
    'SHWB': {'DE': -0.1, 'PM': 0.3, 'WI': 1.4, 'Pas': 1.4},
    'NIM':  {'DE': -0.1, 'Pas': 0.8, 'SC': 1.3},
    'PDIM': {'PM': 0.2, 'Pas': 0.5},
    'NW':   {'DE': 0.4, 'PM': -0.3, 'Pas': 0.7},
    'NFW':  {'PM': 0.1, 'WI': 0.2, 'Pas': -0.1, 'SC': 0.2},
    'PNF':  {'WI': 0.6, 'Pas': 0.1, 'SC': -0.4},
    'DFW':  {'PM': 0.7, 'Pas': -0.3, 'SC': -0.4},
}


def nt_outcome_prior(profile, pos_code, age):
    """The NT target profile, moved toward what real NT players at this position have (see NT_REAL_OFFSET)."""
    pos = normalize_position(pos_code)
    pos = {'OCD': 'NCD', 'ADEF': 'NCD', 'CAD': 'NCD', 'WTM': 'NW'}.get(pos, pos)
    f = min(1.0, max(0.0, (int(age) - 22) / 6.0))
    off = NT_REAL_OFFSET.get(pos, {})
    return {k: float(profile.get(k, 1.0)) + f * off.get(k, 0.0) for k in OUTCOME_SKILLS}


def training_outcome_prior(trained, profile, pos_code, age, own=None):
    """Template for players outside the NT/U22 mould. trained = [main, second, third training] (2-3 skills): the main
    one at the profile's top level (at least 10), the second halfway between that and the leftovers, the third halfway
    between the second and the leftovers; trained skills loosely known, every other skill a leftover around 4.5,
    tightly known. With own (the user's own players' average skills at this position) the trained skills take those
    levels instead. Returns (prior, per-skill sd) for enumerate_outcomes. Tested on AFRN + a Dutch club (real TSI,
    wage, skills): a third skill took the secondaries from 0.85 to 0.67 (AFRN) and 0.35 to 0.34 levels."""
    trained = list(dict.fromkeys(t for t in (trained or []) if t in OUTCOME_SKILLS))[:3]
    hi = max(max(float(profile.get(k, 1.0)) for k in OUTCOME_SKILLS), 10.0)
    mid = (hi + 4.5) / 2
    levels, sds = [hi, mid, (mid + 4.5) / 2], [4.0, 4.0, 3.0]
    lv = {t: levels[i] for i, t in enumerate(trained)}
    prior = {k: ((float(own[k]) if own and k in own else lv[k]) if k in trained else 4.5) for k in OUTCOME_SKILLS}
    sd = {k: (sds[trained.index(k)] if k in trained else 1.5) for k in OUTCOME_SKILLS}
    return prior, sd


# Usual training per position: the default answer to "current training" for Other players.
POS_TRAINING = {'NCD': ('DE', 'PM'), 'OCD': ('DE', 'PM'), 'CAD': ('DE', 'Pas'), 'ADEF': ('DE', 'PM'), 'NWB': ('DE', 'WI'), 'SHWB': ('DE', 'WI'),
                'NIM': ('PM', 'Pas'), 'OIM-Q': ('PM', 'Pas'), 'OIM-H': ('PM', 'Pas'), 'PDIM': ('PM', 'DE'),
                'NW': ('WI', 'PM'), 'WTM': ('PM', 'WI'), 'NFW': ('SC', 'Pas'), 'PNF': ('SC', 'PM'), 'DFW': ('SC', 'Pas'),
                'TDFW': ('SC', 'Pas')}
REF_FORM_RANGE, REF_STAM_RANGE = (5, 8), (6, 8)   # form / stamina not stored in the Reference DB


def reestimate_reference_row(row, mode='auto'):
    """All-outcomes estimate for one Reference DB row (form and stamina unknown). mode 'auto': U22 template up to
    21, NT template from 22; 'other': training template with the usual training for the position.
    Returns ({skill: value}, note) or (None, reason)."""
    try:
        pos = normalize_position(str(row.get('Positie') or ''))
        age, days = int(float(row.get('Leeftijd'))), int(float(row.get('dag(en)') or 0))
        tsi, wage = float(row.get('TSI') or 0), float(row.get('Loon') or 0)
    except (TypeError, ValueError):
        return None, 'missing age / TSI / wage'
    if pos == 'K' or not pos:
        return None, 'keeper'
    if tsi <= 0 or wage <= 0:
        return None, 'no TSI or wage'
    spec = str(row.get('Specialiteit') or 'None')
    nat = str(row.get('Nationality') or 'Netherlands')
    foreign = bool(int(float(row.get('Foreign') or 0)))
    gk = float(row.get('GK') or 1.0) or 1.0
    sh = float(row.get('SH') or 3.0) or 3.0
    try:
        from richtskills_data import estimate_age_richtskills as _est
        prof = _est(age, spec, nat).get(pos) or _est(age, spec).get(pos) or {}
    except Exception:
        prof = {}
    if not prof:
        return None, 'no profile for this position'
    sd, train = None, None
    if mode == 'other':
        t = POS_TRAINING.get(pos, ('SC', 'Pas'))
        prior, sd = training_outcome_prior(list(t), prof, pos, age)
        train, src = t[0], f'training {t[0]} + {t[1]}'
    elif age <= 21:
        prior, src = {k: float(prof.get(k, 1.0)) for k in OUTCOME_SKILLS}, 'U22 template'
    else:
        prior, src = nt_outcome_prior(prof, pos, age), 'NT template'
    fl, fh = REF_FORM_RANGE
    cl, ch = REF_STAM_RANGE
    oc = enumerate_outcomes(tsi, wage, age, days, spec, fl, cl, pos, foreign, prior, sd, sh, None, train, fh, ch)
    if not oc:
        return None, 'no combination fits TSI + wage'
    b = outcome_build(oc, tsi, age, days, spec, (fl + fh + 0.99) / 2, (cl + ch + 0.99) / 2, pos, gk=gk, sh=sh, is_foreign=foreign)
    out = {k: round(float(b[k]), 3) for k in OUTCOME_SKILLS}
    out.update(GK=gk, SH=sh)
    rng = ' · '.join(f"{k} {oc['lo'][k]}" + (f"-{oc['hi'][k]}" if oc['hi'][k] != oc['lo'][k] else '') for k in OUTCOME_SKILLS)
    return out, f"{src}; likely {rng}"


def _outcome_wage_base(levels):
    """Base wage (no age / specialty / foreign / set pieces) for an (N,5) array of skill values."""
    global _OUTCOME_WGRID
    if _OUTCOME_WGRID is None:
        _OUTCOME_WGRID = {k: np.array([lookup_wage(v, k) for v in np.arange(0, 26, 0.001)]) for k in OUTCOME_SKILLS}
    w = np.stack([_OUTCOME_WGRID[k][np.clip((levels[:, i] * 1000).astype(int), 0, 25999)]
                  for i, k in enumerate(OUTCOME_SKILLS)], 1)
    mx = w.max(1)
    m = np.where(mx > 20300, 0.40, 0.50)
    return 250 + mx + m * (w.sum(1) - mx)


# Skill drops with age (Schum, "Drops 2.0", forum 17404127): every Monday a player loses a little of each skill from
# the age it starts dropping; how much depends only on his age. AgeNoDrop per skill, and the drop per week by Age+.
SKILL_NO_DROP_AGE = {'GK': 29, 'DE': 28, 'PM': 27, 'WI': 27, 'Pas': 27, 'SC': 26, 'SH': 30}
SKILL_DROP_PER_WEEK = [0, 0.0003, 0.0014, 0.0037, 0.0074, 0.0127, 0.0197, 0.0285, 0.0393, 0.0522, 0.0673, 0.0846]


def weekly_skill_drop(skill, age):
    """Levels of `skill` a player of this age loses every Monday (0 until the skill starts dropping)."""
    k = int(age) - SKILL_NO_DROP_AGE.get(skill, 27)
    return SKILL_DROP_PER_WEEK[min(max(k, 0), len(SKILL_DROP_PER_WEEK) - 1)]


ENUM_EXACT_DROPS = True


def enumerate_outcomes(tsi, wage, age, days, spec, form, stam, pos_code, is_foreign, prior, prior_sd=None, sh=3.0, levels=None,
                       train_skill=None, form_hi=None, stam_hi=None, prior_cov=None, extra_filter=None, logw_fn=None,
                       form_range=None, w_lo_frac=None):
    """Outfield players only. prior: {skill: expected value}. Returns None, or a dict with
    n (combinations that fit), est {skill: weighted mean}, lo/hi {skill: 10th / 90th percentile whole level}."""
    pos = normalize_position(pos_code)
    if pos == 'K' or not tsi or not wage:
        return None
    sd = OUTCOME_PRIOR_SD if (not prior_sd or isinstance(prior_sd, dict)) else float(prior_sd)
    age = int(age)
    agef = (max(0.125, 1 - 0.125 * (age - 27)) if age > 27 else 1.0)
    # form / stamina: one known level (its decimals unknown), or a range of levels when not known (form_hi / stam_hi)
    f0, c0 = float(int(float(form))), float(int(float(stam)))
    f1 = float(int(float(form_hi))) + 0.99 if form_hi is not None else f0 + 0.99
    c1 = float(int(float(stam_hi))) + 0.99 if stam_hi is not None else c0 + 0.99
    c1 = min(c1, stamina_max(age)) if 'stamina_max' in globals() else c1
    if form_range is not None:   # hidden form narrowed down by his TSI history (ht_extras.hidden_form)
        f0, f1 = float(form_range[0]), float(form_range[1])
    # largest level any one skill can have: alone it may not exceed the TSI
    sf_max = (float(tsi) * 1000.0 / (np.sqrt(max((c0 - 1) * (f0 - 1), 1e-6)) * agef)) ** 0.5   # lowest form/stamina
    top = [int(min(22, 1 + (sf_max / w) ** (1 / 3))) for w in OUTCOME_TSI_W]
    grids = np.meshgrid(*[np.arange(1, t + 1, dtype=np.float32) for t in top], indexing='ij')
    lv = np.stack([g.ravel() for g in grids], 1)

    def tsi_of(x, f, c):
        return (((x - 1) ** 3) @ OUTCOME_TSI_W) ** 2 * np.sqrt((c - 1) * (f - 1)) / 1000 * agef
    n_grid = int(len(lv))
    ok = (tsi_of(lv, f0, c0) <= tsi) & (tsi_of(lv + 0.999, f1, c1) >= tsi)
    n_tsi = int(ok.sum())
    for i, s in enumerate(OUTCOME_SKILLS):   # known levels (or a level range) narrow it down
        if levels and levels.get(s) is not None:
            a, b = levels[s]
            ok &= (lv[:, i] >= int(a)) & (lv[:, i] <= int(b))
    lv = lv[ok]
    n_lvl = int(len(lv))
    if not len(lv):
        return None
    specm = 1.10 if (spec and str(spec).strip() not in ('Geen', 'None', '', 'nan')) else 1.0
    agew = max(0.1, 1 - 0.1 * (age - 28)) if age > 28 else 1.0
    k = (1 + 0.0025 * sh) * specm * agew * (1.2 if is_foreign else 1.0)
    weeks = max(0, min(int(days), 111)) / 7.0
    # train_skill: skill(s) trained since the birthday - one name, a list of up to 2 (the weeks split evenly),
    # 'none' / [] = not trained (today's skills earn the birthday wage), None = the position's wage skill.
    gains = {}
    if age < 28:
        # The wage was set on the birthday; since then only the trained skill(s) grew (by at most full training).
        # So today's skills earn at least the wage, and today's skills minus that growth at most the wage.
        if train_skill is None:
            tr = [wage_main_skill(pos, age, spec)[0] if pos else 'SC']
        elif isinstance(train_skill, str):
            tr = [] if train_skill == 'none' else [train_skill]
        else:
            tr = list(train_skill)
        tr = [t for t in dict.fromkeys(tr) if t in OUTCOME_SKILLS][:2]
        for t in tr:
            m0 = float((prior or {}).get(t, 12.0))
            g = full_training_gain(t, m0, age, weeks / len(tr)) if weeks > 0 else 0.0
            if g > 0:
                gains[OUTCOME_SKILLS.index(t)] = g
        w_lo, w_hi = float(wage) * 0.995, float(wage) * 1.02
    else:
        # 28+: skills only drop after the birthday (ageing), so today's skills earn at most the birthday wage
        # (no margin above it; was +2%). Tested on 14 seniors: same accuracy.
        w_lo, w_hi = float(wage) * max(0.80, 0.995 - 0.005 * weeks), float(wage) * 1.0
        if w_lo_frac is not None:   # his TSI history shows how much (little) he lost since the birthday
            w_lo = float(wage) * max(float(w_lo_frac), 0.80)
        if ENUM_EXACT_DROPS:
            # Exact: on his birthday each skill was higher by the Mondays since then x the weekly drop at his age, and
            # those birthday skills earned the wage (Schum's drop table; replaces the 0.5%-a-week guess).
            for ti, s_ in enumerate(OUTCOME_SKILLS):
                d_ = weekly_skill_drop(s_, age) * weeks
                if d_ > 0:
                    gains[ti] = -d_
            w_lo, w_hi = float(wage) * 0.995, float(wage) * 1.005
    lv_b = lv.copy()
    for ti, g in gains.items():
        lv_b[:, ti] = np.maximum(lv_b[:, ti] - g, 1.0)
    lv_hi = lv + 0.999
    for ti, g in gains.items():
        if g < 0:   # ageing: the birthday skills were higher
            lv_hi[:, ti] = lv_hi[:, ti] - g
    wmin, wmax = _outcome_wage_base(lv_b) * k, _outcome_wage_base(lv_hi) * k
    ok = (wmax >= w_lo) & (wmin <= w_hi)
    n_wage = int(ok.sum())
    if extra_filter is not None:   # e.g. an earlier TSI (performance history) the skills must also fit
        ok &= np.asarray(extra_filter(lv), dtype=bool)
    lv = lv[ok]
    if not len(lv):
        return None
    p = np.array([float((prior or {}).get(s, 1.0)) for s in OUTCOME_SKILLS]) - 0.5
    if isinstance(prior_sd, dict):   # per-skill certainty (e.g. trained skills loose, the rest tight)
        sd = np.array([float(prior_sd.get(s, OUTCOME_PRIOR_SD)) for s in OUTCOME_SKILLS])
    if prior_cov is not None:   # skills that go together (5x5 covariance around the template)
        icov = np.linalg.inv(np.asarray(prior_cov, dtype=float))
        dd = lv - p
        logw = -0.5 * np.einsum('ij,jk,ik->i', dd, icov, dd)
    else:
        logw = -0.5 * (((lv - p) / sd) ** 2).sum(1)
    if logw_fn is not None:   # extra knowledge on the whole combination (training order, team shape, match ratings)
        logw = logw + np.asarray(logw_fn(lv + 0.5), dtype=float)
    w = np.exp(logw - logw.max()); w /= w.sum()
    est = (w[:, None] * (lv + 0.5)).sum(0)
    def _ranges(lv_, w_):
        w_ = w_ / w_.sum()
        lo_, hi_ = {}, {}
        for i, s in enumerate(OUTCOME_SKILLS):
            order = np.argsort(lv_[:, i]); cw = np.cumsum(w_[order])
            lo_[s] = int(lv_[order][np.searchsorted(cw, 0.10)][i])
            hi_[s] = int(lv_[order][min(np.searchsorted(cw, 0.90), len(cw) - 1)][i])
        return lo_, hi_
    lo, hi = _ranges(lv, w)
    # Two builds instead of one average: split the combinations along the direction in which they differ most
    # (e.g. more passing + less scoring vs the other way round) and average each side.
    alts = []
    try:
        d = lv + 0.5 - est
        cov = (w[:, None] * d).T @ d
        vals, vecs = np.linalg.eigh(cov)
        v = vecs[:, -1]
        side = (d @ v) > 0
        for msk in (side, ~side):
            ws = w[msk]
            if ws.sum() < 0.05:
                continue
            e_ = (ws[:, None] * (lv[msk] + 0.5)).sum(0) / ws.sum()
            l_, h_ = _ranges(lv[msk], ws)
            alts.append(dict(share=float(ws.sum()), est={s: float(e_[i]) for i, s in enumerate(OUTCOME_SKILLS)}, lo=l_, hi=h_))
        alts.sort(key=lambda a_: -a_['share'])
    except Exception:
        alts = []
    return dict(counts=dict(grid=n_grid, tsi=n_tsi, levels=n_lvl, wage=n_wage, final=int(len(lv))),
                n=int(len(lv)), est={s: float(est[i]) for i, s in enumerate(OUTCOME_SKILLS)}, lo=lo, hi=hi, alts=alts,
                w_lo=float(w_lo), w_hi=float(w_hi), sh=float(sh), gains={int(i): float(g) for i, g in gains.items()},
                lv_min={s: int(lv[:, i].min()) for i, s in enumerate(OUTCOME_SKILLS)},
                lv_max={s: int(lv[:, i].max()) for i, s in enumerate(OUTCOME_SKILLS)},
                _lv=lv.astype(np.int8), _w=w.astype(np.float32),
                logz=float(logw.max() + np.log(np.exp(logw - logw.max()).sum())))   # how well this template explains TSI + wage


def outcome_split(oc, metric, k=3):
    """Split enumerate_outcomes' combinations into k groups along metric(levels) (weighted equal shares, low to high).
    -> [dict(share, n, est, lo, hi)] to build with outcome_build(dict(oc, est=.., lo=.., hi=..))."""
    lv, w = oc.get('_lv'), oc.get('_w')
    if lv is None or not len(lv):
        return []
    lv = lv.astype(float)
    w = w.astype(float) / w.sum()
    m = np.asarray(metric(lv), dtype=float)
    order = np.argsort(m, kind='stable')
    cw = np.cumsum(w[order])
    out = []
    for g in range(k):
        sel = order[(cw > g / k) & (cw <= (g + 1) / k + 1e-12)] if g else order[cw <= 1 / k + 1e-12]
        if not len(sel):
            continue
        ws = w[sel]
        e_ = (ws[:, None] * (lv[sel] + 0.5)).sum(0) / ws.sum()
        lo_, hi_ = {}, {}
        for i, s in enumerate(OUTCOME_SKILLS):
            o2 = np.argsort(lv[sel][:, i]); c2 = np.cumsum(ws[o2]) / ws.sum()
            lo_[s] = int(lv[sel][o2][np.searchsorted(c2, 0.10)][i])
            hi_[s] = int(lv[sel][o2][min(np.searchsorted(c2, 0.90), len(c2) - 1)][i])
        out.append(dict(share=float(ws.sum()), n=int(len(sel)), est={s: float(e_[i]) for i, s in enumerate(OUTCOME_SKILLS)},
                        lo=lo_, hi=hi_))
    return out


def outcome_build(res, tsi, age, days, spec, form, stam, pos_code, gk=1.0, sh=None, is_foreign=False):
    """Turn enumerate_outcomes' estimate into one consistent build: as close as possible to the averaged
    estimate, hitting the TSI exactly and keeping the wage inside the window the enumeration used. Every
    skill stays within its likely range (p10-p90 whole levels, widened to the levels that fit if needed)."""
    from scipy.optimize import minimize
    est = np.array([res['est'][s] for s in OUTCOME_SKILLS], dtype=float)
    f = min(float(form) + 0.5, 8.0) if float(form) == int(float(form)) else float(form)
    c = stamina_middle(stam, age)
    shv = float(sh if sh is not None else res.get('sh', 3.0))
    fx = 1.20 if is_foreign else 1.0
    w_lo, w_hi = res.get('w_lo'), res.get('w_hi')

    def calc(x):
        d = dict(zip(OUTCOME_SKILLS, x))
        r = calculate_exact(age, days, spec, f, c, gk, d['DE'], d['PM'], d['WI'], d['Pas'], d['SC'], shv)
        return r[1], r[3] * fx, r

    gains = res.get('gains') or {}

    def w_today_max(x):
        # today's wage may exceed the birthday ceiling by what the training since then added to the trained skill(s)
        if not w_hi or not gains:
            return w_hi
        xb = np.array(x, dtype=float)
        for ti, g in gains.items():
            xb[int(ti)] = max(1.0, xb[int(ti)] - g)
        return w_hi * calc(x)[1] / max(calc(xb)[1], 1.0)

    def fit(bnds):
        x0 = np.clip(est, [b[0] for b in bnds], [b[1] for b in bnds])
        def obj(x):
            t, w, _ = calc(x)
            w_hi_x = w_today_max(x)
            pen = ((t / tsi - 1) * 1e3) ** 2
            if w_lo and w < w_lo:
                pen += ((w_lo - w) / w_lo * 1e2) ** 2
            if w_hi_x and w > w_hi_x:
                # 28+: a hard ceiling (skills only drop after the birthday, so never above the actual wage)
                pen += ((w - w_hi_x) / w_hi_x * (1e3 if int(age) >= 28 else 1e2)) ** 2
            return pen + ((x - est) ** 2).sum()
        r = minimize(obj, x0, method='L-BFGS-B', bounds=bnds, options=dict(maxiter=500))
        return r.x
    tight = [(float(res['lo'][s]), float(res['hi'][s]) + 0.99) for s in OUTCOME_SKILLS]
    x = fit(tight)
    t, w, _ = calc(x)
    if abs(t / tsi - 1) > 0.002 or (w_lo and w < w_lo * 0.995) or (w_hi and w > w_today_max(x) * 1.005):
        wide = [(float(res.get('lv_min', res['lo'])[s]), float(res.get('lv_max', res['hi'])[s]) + 0.99) for s in OUTCOME_SKILLS]
        x = fit(wide)
    x = np.maximum(x, 1.0)
    # TSI exactly as Hattrick shows it (whole number): scale the non-main skills (direct formula, exact)
    if tsi and abs(calc(x)[0] - tsi) >= 0.3:
        mi = int(np.argmax(x))
        nb = fast_rebalance(dict(zip(OUTCOME_SKILLS, x), GK=gk, SH=shv), {OUTCOME_SKILLS[mi]: float(x[mi])},
                            tsi, age, days, spec, f, c, is_foreign)
        if nb is not None:
            x = np.array([nb[k] for k in OUTCOME_SKILLS], dtype=float)
    d = dict(zip(OUTCOME_SKILLS, (float(v) for v in x)))
    _, c_tsi, _, c_wage, _, c_htms, c_htms28 = calc(x)[2]
    return dict(GK=gk, SH=shv, Vorm=f, Cond=c, Calc_TSI=c_tsi, Calc_Wage=c_wage * fx, Calc_HTMS=c_htms, Calc_HTMS28=c_htms28, **d)


# ==============================================================================
# 11. POSITION FIT, POSITION SCORE AND TRAINING ADVICE (from the contribution table)
# ==============================================================================
# Position score: contribution-weighted average of the skills + 0.3 x log10(experience). Tested on the Dutch NT
# staff sheet (83 senior players): same ranking per position (rank agreement 0.93, same #1 in 7 of 9 positions);
# the U22 sheet's 1.335 x log10(xp) counted experience far too much for seniors (centre backs: 0.14).
POSITION_SCORE_XP = 0.3
ORDER_LABELS = {'K': 'Keeper', 'NCD': 'Normal CD', 'CDTW': 'CD towards wing', 'OCD': 'Offensive CD',
                'NWB': 'Normal WB', 'DWB': 'Defensive WB', 'OWB': 'Offensive WB', 'WBTM': 'WB towards middle',
                'NW': 'Normal winger', 'DW': 'Defensive winger', 'OW': 'Offensive winger', 'WTM': 'Winger towards middle',
                'NIM': 'Normal IM', 'DIM': 'Defensive IM', 'OIM': 'Offensive IM', 'IMTW': 'IM towards wing',
                'NFW': 'Normal FW', 'TDFW': 'Technical defensive FW', 'FTW': 'FW towards wing', 'PNF': 'Powerful FW'}


def position_score(skills, order, xp=None):
    """How good he is in this order (skill-level scale), like the NT staff sheet's position score."""
    import math
    c = CONTRIBUTIONS[order]
    s = {k: float(skills.get(k, 1.0) or 1.0) for k in CONTRIB_SKILLS}
    r = sum(c[k] * s[k] for k in CONTRIB_SKILLS) / sum(c.values())
    try:
        x = float(xp or 0)
    except (TypeError, ValueError):
        x = 0.0
    return r + (POSITION_SCORE_XP * math.log10(x) if x > 0 else 0.0)


def best_positions(skills, spec=None, n=3):
    """[(order, fit %)] best first: how well his skills suit each order. Powerful FW only for Powerful players.
    Tested on 83 Dutch NT players: best fit in the listed line for 82, listed position in the top 3 for all 83."""
    powerful = str(spec or '').strip().lower() in ('powerful', 'krachtig', 'p')
    out = [(o, f) for o, f in best_orders(skills, n=len(CONTRIBUTIONS))
           if o != 'PNF' or powerful]
    return out[:n]


def training_advice(skills, order, years, days, **kw):
    """Rating gained in this order by one season (16 weeks) of training each contributing skill, with the
    Training planner's speed model (kw: coach, assistants, intensity, stamina, share).
    Returns [dict(skill, now, after, gain_levels, gain_score)] best first, or [] when past the training age."""
    if int(years) + 1 > TRAINING_MAX_AGE:
        return []
    c = CONTRIBUTIONS[order]
    tot = sum(c.values())
    out = []
    for k in CONTRIB_SKILLS:
        if c[k] <= 0 or (k == 'GK') != (order == 'K'):
            continue
        now = float(skills.get(k, 1.0) or 1.0)
        try:
            after = float(skill_at_age(int(years) + 1, int(days), int(years), int(days), now, SKILL_TRAINING[k], **kw))
        except Exception:
            continue
        g = max(0.0, after - now)
        out.append(dict(skill=k, now=now, after=after, gain_levels=g, gain_score=c[k] * g / tot))
    return sorted(out, key=lambda d: -d['gain_score'])


def rebalance_build(build, fixed, tsi, age, days, spec, form, cond, is_foreign=False, with_wage=True):
    """Slider helper: keep the skills in `fixed` ({skill: value}) and scale the other outfield skills together
    (their part above 1) so the build hits the TSI exactly. Direct formula (TSI grows with the square of the
    weighted sum of (skill - 1)^3), so it is instant. Returns (new build dict, wage) or (None, None) when the
    fixed skills alone already exceed the TSI."""
    sk = ['DE', 'PM', 'WI', 'Pas', 'SC']
    w = {'DE': 1.034, 'PM': 1.031, 'WI': 0.826, 'Pas': 1.035, 'SC': 1.038}
    gk, sh = float(build.get('GK', 1.0)), float(build.get('SH', 3.0))
    free = [k for k in sk if k not in fixed]
    a = sum(w[k] * max(float(fixed[k]) - 1.0, 0.0) ** 3 for k in fixed if k in w)
    b = sum(w[k] * max(float(build[k]) - 1.0, 0.0) ** 3 for k in free)
    # TSI = K x S^2 for this age / form / stamina: K from one evaluation
    ref = {k: float(build[k]) for k in sk}
    s_ref = sum(w[k] * max(ref[k] - 1.0, 0.0) ** 3 for k in sk)
    t_ref = calculate_tsi_for_form(age, form, cond, gk, *[ref[k] for k in sk])
    if s_ref <= 0 or t_ref <= 0:
        return None, None
    s_need = (float(tsi) * s_ref ** 2 / t_ref) ** 0.5
    if s_need < a:
        return None, None
    g = ((s_need - a) / b) ** (1.0 / 3.0) if b > 0 else 0.0
    d = {k: float(fixed[k]) for k in fixed}
    d.update({k: 1.0 + max(float(build[k]) - 1.0, 0.0) * g for k in free})
    out = dict(build); out.update(d)
    if with_wage:
        r = calculate_exact(age, days, spec, form, cond, gk, d['DE'], d['PM'], d['WI'], d['Pas'], d['SC'], sh)
        out['Calc_TSI'], out['Calc_Wage'] = r[1], r[3] * (1.2 if is_foreign else 1.0)
        out['Calc_HTMS'], out['Calc_HTMS28'] = r[5], r[6]
        return out, out['Calc_Wage']
    out['Calc_TSI'] = calculate_tsi_for_form(age, form, cond, gk, d['DE'], d['PM'], d['WI'], d['Pas'], d['SC'])
    return out, None


def edge_safe(build, tsi, age, days, spec, form, cond, fixed=None, is_foreign=False, top=0.99):
    """A skill a hair under the next level (e.g. playmaking 6.99998) is shown and saved as 7.00 and then counts as
    level 7: TSI and HTMS jump (Aćim: +176 TSI, +36 HTMS in the Estimator). Such skills go to level + 0.99 and the
    other free skills follow so the TSI stays exact. Returns the build unchanged when nothing is on the edge."""
    sk = ['DE', 'PM', 'WI', 'Pas', 'SC']
    try:
        b = dict(build)
        fx = {k: float(v) for k, v in (fixed or {}).items() if k in sk}
        changed = False
        for _ in range(4):
            edged = {k: float(int(float(b[k]))) + top for k in sk if float(b[k]) - int(float(b[k])) > top}
            if not edged:
                break
            changed = True
            b.update(edged)
            fx.update(edged)
            main = max(sk, key=lambda k: float(b[k]))
            fx.setdefault(main, float(b[main]))
            nb = fast_rebalance(b, fx, tsi, age, days, spec, form, cond, is_foreign) if tsi and len(fx) < len(sk) else None
            if nb is not None:
                b = nb
        if not changed:
            return build
        r = calculate_exact(age, days, spec, form, cond, float(b.get('GK', 1.0)), *[float(b[k]) for k in sk],
                            float(b.get('SH', 3.0)))
        b['Calc_TSI'], b['Calc_Wage'] = r[1], r[3] * (1.2 if is_foreign else 1.0)
        b['Calc_HTMS'], b['Calc_HTMS28'] = r[5], r[6]
        return b
    except Exception:
        return build


def snap_tsi(build, tsi, age, days, spec, form, cond, fixed=None, is_foreign=False):
    """Any build -> the same build with TSI exactly `tsi` as Hattrick shows it (whole number): the skills not in
    `fixed` (plus the main skill) are scaled together. Returns the build unchanged when it already fits or
    when it can't be done (keepers, or the fixed skills alone are more than the TSI)."""
    sk = ['DE', 'PM', 'WI', 'Pas', 'SC']
    try:
        if not tsi or round(float(build['Calc_TSI'])) == round(float(tsi)):
            return build
        if float(build.get('GK', 1.0) or 1.0) > max(float(build[k]) for k in sk):
            return build
        fx = {k: float(build[k]) for k in (fixed or {}) if k in sk}
        main = max(sk, key=lambda k: float(build[k]))
        fx.setdefault(main, float(build[main]))
        if len(fx) >= len(sk):
            return build
        nb = fast_rebalance(build, fx, tsi, age, days, spec, form, cond, is_foreign)
        if nb is None or round(float(nb['Calc_TSI'])) != round(float(tsi)):
            return build
        return nb
    except Exception:
        return build


def fast_rebalance(build, fixed, tsi, age, days, spec, form, cond, is_foreign=False):
    """Fast version of rebalance_build for sliders: TSI grows with the square of S = sum of w*(skill-1)^3, so
    the free skills' scale follows in one step instead of a search. Returns the new build dict or None when
    the fixed skills alone already exceed the TSI."""
    sk = ['DE', 'PM', 'WI', 'Pas', 'SC']
    w = {'DE': 1.034, 'PM': 1.031, 'WI': 0.826, 'Pas': 1.035, 'SC': 1.038}
    gk, sh = float(build.get('GK', 1.0)), float(build.get('SH', 3.0))
    b = {k: float(build[k]) for k in sk}
    t0 = calculate_tsi_for_form(age, form, cond, gk, *[b[k] for k in sk])
    s0 = sum(w[k] * max(b[k] - 1.0, 0.0) ** 3 for k in sk)
    if t0 <= 0 or s0 <= 0:
        return None
    s_target = s0 * (float(tsi) / t0) ** 0.5
    free = [k for k in sk if k not in fixed]
    s_fixed = sum(w[k] * max(float(fixed[k]) - 1.0, 0.0) ** 3 for k in fixed)
    s_free0 = sum(w[k] * max(b[k] - 1.0, 0.0) ** 3 for k in free)
    rem = s_target - s_fixed
    if rem < 0:
        return None
    d = {k: float(fixed[k]) for k in fixed}
    if s_free0 > 1e-9:
        g = (rem / s_free0) ** (1.0 / 3.0)
        d.update({k: 1.0 + max(b[k] - 1.0, 0.0) * g for k in free})
    elif free:   # the free skill(s) sit at 1.0: share what is left equally
        d.update({k: 1.0 + (rem / len(free) / w[k]) ** (1.0 / 3.0) for k in free})
    r = calculate_exact(age, days, spec, form, cond, gk, d['DE'], d['PM'], d['WI'], d['Pas'], d['SC'], sh)
    out = dict(build); out.update(d)
    out['Vorm'], out['Cond'] = float(form), float(cond)
    out['Calc_TSI'], out['Calc_Wage'] = r[1], r[3] * (1.2 if is_foreign else 1.0)
    out['Calc_HTMS'], out['Calc_HTMS28'] = r[5], r[6]
    return out


# ==============================================================================
# Wage fit for the solver options (NT / U22): the same check the result card makes
# ==============================================================================
def wage_status(skills, actual_wage, pos_code, age, days, spec, is_foreign=False, ceiling=0.0, margin=0.0):
    """'ok', 'low' (skills too low for the wage), 'high' (a senior whose skills pay more than his wage: after
    the birthday a senior only loses skill) or 'ceil' (more growth since the birthday than training allows).
    Same thresholds as the wage line on the Auto-Solver cards."""
    actual_wage = float(actual_wage or 0); days = int(days or 0)
    if days <= 0 or actual_wage <= 0:
        return 'ok'
    _lo, _typ, hi, _wks = birthday_wage_range(skills, pos_code, int(age), days, spec, is_foreign)
    drop = min(0.20, 0.005 * max(0, min(days, 111)) / 7.0) if int(age) >= 28 else 0.0
    if actual_wage > hi * (1.02 - margin) / max(1.0 - drop, 0.8):
        return 'low'
    if drop > 0 and actual_wage > hi * 1.02:
        return 'ok'
    if int(age) >= 28 and hi > actual_wage * (1.005 - margin):
        return 'high'
    if ceiling and hi > float(ceiling) * (1.10 - margin):
        return 'ceil'
    return 'ok'


def wage_fit_build(build, actual_wage, tsi, pos_code, age, days, spec, form, cond, fixed=None, is_foreign=False,
                   ceiling=0.0, max_move=2.0, step=0.02, margin=0.003):
    """A solver build whose wage does not fit: move the skill that sets the wage the smallest amount that makes
    it fit (down when the wage comes out too high, up when too low). The other free skills follow so TSI stays
    exact; skills in `fixed` stay where they are. Returns (new build, moved skill, change) or (build, None, 0)
    when it already fits or can't be fitted within `max_move` levels."""
    sk = ['DE', 'PM', 'WI', 'Pas', 'SC']
    try:
        if pos_code == 'K':
            return build, None, 0.0
        skills = lambda b: {k: float(b.get(k, 1.0) or 1.0) for k in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']}
        st0 = wage_status(skills(build), actual_wage, pos_code, age, days, spec, is_foreign, ceiling, margin)
        if st0 == 'ok':
            return build, None, 0.0
        main = wage_main_skill(pos_code, int(age), spec, skills={k: float(build[k]) for k in sk})[0]
        fx = {k: float(v) for k, v in (fixed or {}).items() if k in sk}
        if main not in sk or main in fx:
            return build, None, 0.0
        sign = 1.0 if st0 == 'low' else -1.0
        # Wage too high: every skill that pays almost as much as the main one goes down with it (an NCD with
        # DE 18 and PM 17: lowering DE alone pushes PM up and the wage with it); the cheap skills keep TSI.
        move = [main]
        if sign < 0:
            w1 = lookup_wage(float(build[main]), main)
            move += [k for k in sk if k != main and k not in fx and lookup_wage(float(build[k]), k) >= 0.6 * w1]
        if len([k for k in sk if k not in fx and k not in move]) == 0:
            return build, None, 0.0

        def at(d):
            nb = fast_rebalance(build, dict(fx, **{k: float(build[k]) + d for k in move}), tsi, age, days, spec,
                                form, cond, is_foreign)
            if nb is None or any(float(nb[k]) > 20.99 or float(nb[k]) < 1.0 for k in sk):
                return None
            return nb
        n = int(round(max_move / step))
        for i in range(1, n + 1):
            d = sign * step * i
            nb = at(d)
            if nb is None:
                continue
            if wage_status(skills(nb), actual_wage, pos_code, age, days, spec, is_foreign, ceiling, margin) == 'ok':
                nb2 = at(d + sign * step)   # one step more, so it does not sit right on the edge
                if nb2 is not None and wage_status(skills(nb2), actual_wage, pos_code, age, days, spec,
                                                   is_foreign, ceiling, margin) == 'ok':
                    nb, d = nb2, d + sign * step
                return nb, '+'.join(move), d
        return build, None, 0.0
    except Exception:
        return build, None, 0.0