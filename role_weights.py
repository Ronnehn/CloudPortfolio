# ==============================================================================
# ROLE SECTOR WEIGHTS
# Relative rating contributions per position order. IMTW and FTW winger values follow
# the Dutch forum tables ("Relatieve Waarden Ratingbijdrage" / "HT contributions"):
# IMTW 59%, FTW 64% to his own wing + 21% to the other. Before: 40% / 48% / 26.25%
# (BLANCO_NT_HT_Predictor) -> see role_weights_backup_BLANCO.py.
# ==============================================================================

ROLE_SECTOR_WEIGHTS = {
    'K': {'CD': {'GK': 0.87, 'DE': 0.35}, 'RD': {'GK': 0.61, 'DE': 0.25}, 'LD': {'GK': 0.61, 'DE': 0.25}},
    'lCD': {'CD': {'DE': 1.0}, 'LD': {'DE': 0.52}, 'MID': {'PM': 0.25}},
    'lCDTW': {'CD': {'DE': 0.67}, 'LD': {'DE': 0.81}, 'MID': {'PM': 0.15}, 'LA': {'WI': 0.26}},
    'lDFW': {'MID': {'PM': 0.35}, 'CA': {'SC': 0.56, 'Pas': 0.53}, 'RA': {'SC': 0.13, 'Pas': 0.31, 'WI': 0.13}, 'LA': {'SC': 0.13, 'Pas': 0.31, 'WI': 0.13}},
    'lDIM': {'CD': {'DE': 0.58}, 'LD': {'DE': 0.27}, 'MID': {'PM': 0.95}, 'CA': {'SC': 0.13, 'Pas': 0.18}, 'LA': {'Pas': 0.14}},
    'lDW': {'CD': {'DE': 0.25}, 'LD': {'DE': 0.61}, 'MID': {'PM': 0.3}, 'CA': {'Pas': 0.05}, 'LA': {'Pas': 0.21, 'WI': 0.69}},
    'lDWB': {'CD': {'DE': 0.43}, 'LD': {'DE': 1.0}, 'MID': {'PM': 0.1}, 'LA': {'WI': 0.45}},
    'lFTW': {'MID': {'PM': 0.15}, 'CA': {'SC': 0.66, 'Pas': 0.23}, 'RA': {'SC': 0.19, 'Pas': 0.06, 'WI': 0.21}, 'LA': {'SC': 0.51, 'Pas': 0.21, 'WI': 0.64}},
    'lIMTW': {'CD': {'DE': 0.33}, 'LD': {'DE': 0.24}, 'MID': {'PM': 0.9}, 'CA': {'Pas': 0.23}, 'LA': {'Pas': 0.31, 'WI': 0.59}},
    'lNFW': {'MID': {'PM': 0.25}, 'CA': {'SC': 1.0, 'Pas': 0.33}, 'RA': {'SC': 0.27, 'Pas': 0.14, 'WI': 0.24}, 'LA': {'SC': 0.27, 'Pas': 0.14, 'WI': 0.24}},
    'lNIM': {'CD': {'DE': 0.4}, 'LD': {'DE': 0.19}, 'MID': {'PM': 1.0}, 'CA': {'SC': 0.22, 'Pas': 0.33}, 'LA': {'Pas': 0.26}},
    'lNW': {'CD': {'DE': 0.2}, 'LD': {'DE': 0.35}, 'MID': {'PM': 0.45}, 'CA': {'Pas': 0.11}, 'LA': {'Pas': 0.26, 'WI': 0.86}},
    'lNWB': {'CD': {'DE': 0.38}, 'LD': {'DE': 0.92}, 'MID': {'PM': 0.15}, 'LA': {'WI': 0.59}},
    'lOCD': {'CD': {'DE': 0.73}, 'LD': {'DE': 0.4}, 'MID': {'PM': 0.4}},
    'lOIM': {'CD': {'DE': 0.16}, 'LD': {'DE': 0.09}, 'MID': {'PM': 0.95}, 'CA': {'SC': 0.31, 'Pas': 0.49}, 'LA': {'Pas': 0.36}},
    'lOW': {'CD': {'DE': 0.13}, 'LD': {'DE': 0.22}, 'MID': {'PM': 0.3}, 'CA': {'Pas': 0.13}, 'LA': {'Pas': 0.29, 'WI': 1.0}},
    'lOWB': {'CD': {'DE': 0.35}, 'LD': {'DE': 0.74}, 'MID': {'PM': 0.2}, 'LA': {'WI': 0.69}},
    'lTDFW': {'MID': {'PM': 0.35}, 'CA': {'SC': 0.56, 'Pas': 0.53}, 'RA': {'SC': 0.13, 'Pas': 0.41, 'WI': 0.13}, 'LA': {'SC': 0.13, 'Pas': 0.41, 'WI': 0.13}},
    'lWBTM': {'CD': {'DE': 0.7}, 'LD': {'DE': 0.75}, 'MID': {'PM': 0.2}, 'LA': {'WI': 0.35}},
    'lWTM': {'CD': {'DE': 0.25}, 'LD': {'DE': 0.29}, 'MID': {'PM': 0.55}, 'CA': {'Pas': 0.16}, 'LA': {'Pas': 0.15, 'WI': 0.74}},
    'mCD': {'CD': {'DE': 1.0}, 'RD': {'DE': 0.26}, 'LD': {'DE': 0.26}, 'MID': {'PM': 0.25}},
    'mDFW': {'MID': {'PM': 0.35}, 'CA': {'SC': 0.56, 'Pas': 0.53}, 'RA': {'SC': 0.13, 'Pas': 0.31, 'WI': 0.13}, 'LA': {'SC': 0.13, 'Pas': 0.31, 'WI': 0.13}},
    'mDIM': {'CD': {'DE': 0.58}, 'RD': {'DE': 0.14}, 'LD': {'DE': 0.14}, 'MID': {'PM': 0.95}, 'CA': {'SC': 0.13, 'Pas': 0.18}, 'RA': {'Pas': 0.07}, 'LA': {'Pas': 0.07}},
    'mNFW': {'MID': {'PM': 0.25}, 'CA': {'SC': 1.0, 'Pas': 0.33}, 'RA': {'SC': 0.27, 'Pas': 0.14, 'WI': 0.24}, 'LA': {'SC': 0.27, 'Pas': 0.14, 'WI': 0.24}},
    'mNIM': {'CD': {'DE': 0.4}, 'RD': {'DE': 0.09}, 'LD': {'DE': 0.09}, 'MID': {'PM': 1.0}, 'CA': {'SC': 0.22, 'Pas': 0.33}, 'RA': {'Pas': 0.13}, 'LA': {'Pas': 0.13}},
    'mOCD': {'CD': {'DE': 0.73}, 'RD': {'DE': 0.2}, 'LD': {'DE': 0.2}, 'MID': {'PM': 0.4}},
    'mOIM': {'CD': {'DE': 0.16}, 'RD': {'DE': 0.04}, 'LD': {'DE': 0.04}, 'MID': {'PM': 0.95}, 'CA': {'SC': 0.31, 'Pas': 0.49}, 'RA': {'Pas': 0.18}, 'LA': {'Pas': 0.18}},
    'mTDFW': {'MID': {'PM': 0.35}, 'CA': {'SC': 0.56, 'Pas': 0.53}, 'RA': {'SC': 0.13, 'Pas': 0.41, 'WI': 0.13}, 'LA': {'SC': 0.13, 'Pas': 0.41, 'WI': 0.13}},
    'rCD': {'CD': {'DE': 1.0}, 'RD': {'DE': 0.52}, 'MID': {'PM': 0.25}},
    'rCDTW': {'CD': {'DE': 0.67}, 'RD': {'DE': 0.81}, 'MID': {'PM': 0.15}, 'RA': {'WI': 0.26}},
    'rDFW': {'MID': {'PM': 0.35}, 'CA': {'SC': 0.56, 'Pas': 0.53}, 'RA': {'SC': 0.13, 'Pas': 0.31, 'WI': 0.13}, 'LA': {'SC': 0.13, 'Pas': 0.31, 'WI': 0.13}},
    'rDIM': {'CD': {'DE': 0.58}, 'RD': {'DE': 0.27}, 'MID': {'PM': 0.95}, 'CA': {'SC': 0.13, 'Pas': 0.18}, 'RA': {'Pas': 0.14}},
    'rDW': {'CD': {'DE': 0.25}, 'RD': {'DE': 0.61}, 'MID': {'PM': 0.3}, 'CA': {'Pas': 0.05}, 'RA': {'Pas': 0.21, 'WI': 0.69}},
    'rDWB': {'CD': {'DE': 0.43}, 'RD': {'DE': 1.0}, 'MID': {'PM': 0.1}, 'RA': {'WI': 0.45}},
    'rFTW': {'MID': {'PM': 0.15}, 'CA': {'SC': 0.66, 'Pas': 0.23}, 'RA': {'SC': 0.51, 'Pas': 0.21, 'WI': 0.64}, 'LA': {'SC': 0.19, 'Pas': 0.06, 'WI': 0.21}},
    'rIMTW': {'CD': {'DE': 0.33}, 'RD': {'DE': 0.24}, 'MID': {'PM': 0.9}, 'CA': {'Pas': 0.23}, 'RA': {'Pas': 0.31, 'WI': 0.59}},
    'rNFW': {'MID': {'PM': 0.25}, 'CA': {'SC': 1.0, 'Pas': 0.33}, 'RA': {'SC': 0.27, 'Pas': 0.14, 'WI': 0.24}, 'LA': {'SC': 0.27, 'Pas': 0.14, 'WI': 0.24}},
    'rNIM': {'CD': {'DE': 0.4}, 'RD': {'DE': 0.19}, 'MID': {'PM': 1.0}, 'CA': {'SC': 0.22, 'Pas': 0.33}, 'RA': {'Pas': 0.26}},
    'rNW': {'CD': {'DE': 0.2}, 'RD': {'DE': 0.35}, 'MID': {'PM': 0.45}, 'CA': {'Pas': 0.11}, 'RA': {'Pas': 0.26, 'WI': 0.86}},
    'rNWB': {'CD': {'DE': 0.38}, 'RD': {'DE': 0.92}, 'MID': {'PM': 0.15}, 'RA': {'WI': 0.59}},
    'rOCD': {'CD': {'DE': 0.73}, 'RD': {'DE': 0.4}, 'MID': {'PM': 0.4}},
    'rOIM': {'CD': {'DE': 0.16}, 'RD': {'DE': 0.09}, 'MID': {'PM': 0.95}, 'CA': {'SC': 0.31, 'Pas': 0.49}, 'RA': {'Pas': 0.36}},
    'rOW': {'CD': {'DE': 0.13}, 'RD': {'DE': 0.22}, 'MID': {'PM': 0.3}, 'CA': {'Pas': 0.13}, 'RA': {'Pas': 0.29, 'WI': 1.0}},
    'rOWB': {'CD': {'DE': 0.35}, 'RD': {'DE': 0.74}, 'MID': {'PM': 0.2}, 'RA': {'WI': 0.69}},
    'rTDFW': {'MID': {'PM': 0.35}, 'CA': {'SC': 0.56, 'Pas': 0.53}, 'RA': {'SC': 0.13, 'Pas': 0.41, 'WI': 0.13}, 'LA': {'SC': 0.13, 'Pas': 0.41, 'WI': 0.13}},
    'rWBTM': {'CD': {'DE': 0.7}, 'RD': {'DE': 0.75}, 'MID': {'PM': 0.2}, 'RA': {'WI': 0.35}},
    'rWTM': {'CD': {'DE': 0.25}, 'RD': {'DE': 0.29}, 'MID': {'PM': 0.55}, 'CA': {'Pas': 0.16}, 'RA': {'Pas': 0.15, 'WI': 0.74}},
}

ROLE_FALLBACK = {
    'mCDTW': 'mCD', 'mIMTW': 'mNIM', 'mFTW': 'mNFW',
    'mNCD': 'mCD', 'lNCD': 'lCD', 'rNCD': 'rCD',
    'mOCD': 'mOCD', 'lOCD': 'lOCD', 'rOCD': 'rOCD',
    'lNWB': 'lNWB', 'rNWB': 'rNWB', 'mNWB': 'mCD',
    'lSHWB': 'lDWB', 'rSHWB': 'rDWB',
    'mPDIM': 'mDIM', 'lPDIM': 'lDIM', 'rPDIM': 'rDIM',
    'mOIM-Q': 'mOIM', 'lOIM-Q': 'lOIM', 'rOIM-Q': 'rOIM',
    'mOIM-H': 'mOIM', 'lOIM-H': 'lOIM', 'rOIM-H': 'rOIM',
    'mDFW': 'mDFW', 'lDFW': 'lDFW', 'rDFW': 'rDFW',
    'mPNF': 'mNFW', 'lPNF': 'lNFW', 'rPNF': 'rNFW',
    'mK': 'K', 'lK': 'K', 'rK': 'K', 'GK': 'K'
}

def get_role_weights(predictor_key):
    if predictor_key in ROLE_SECTOR_WEIGHTS:
        return ROLE_SECTOR_WEIGHTS[predictor_key]
    fallback_key = ROLE_FALLBACK.get(predictor_key)
    if fallback_key and fallback_key in ROLE_SECTOR_WEIGHTS:
        return ROLE_SECTOR_WEIGHTS[fallback_key]
    return {}