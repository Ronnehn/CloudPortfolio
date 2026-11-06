# ==============================================================================
# RICHTSKILLS DATA
# ------------------------------------------------------------------------------
# Target skills anchored precisely at age 29 based on NT benchmarks.
# Youth and potential skills are mapped by interpolating linearly between
# age 17 (set at 35% of peak) up to the peak age of 29.
#
# Above age 29, skills keep evolving up to age 32 (then flatline). For several
# positions the age-30/31/32 progression differs by specialty (e.g. Unpredictable
# keepers/defenders trade a bit of DEF for extra passing; Q/H wingbacks & wingers
# lean into their natural skill while U/T variants lean into passing instead).
# Where no specialty split is given (SHWB, PDIM, NIM, OIM-Q, OIM-H, WTM, DFW,
# NFW, PNF) a single upward curve applies to everyone at that position.
# ==============================================================================

RICHTSKILLS_29 = {
    'K': {'GK': 21.0, 'DE': 12.0, 'PM': 1.0, 'WI': 1.0, 'Pas': 1.0, 'SC': 1.0, 'SH': 21.0},
    'NCD': {'GK': 1.0, 'DE': 18.5, 'PM': 15.0, 'WI': 1.0, 'Pas': 7.0, 'SC': 1.0, 'SH': 2.0},
    'OCD': {'GK': 1.0, 'DE': 17.6, 'PM': 17.3, 'WI': 1.0, 'Pas': 5.0, 'SC': 1.0, 'SH': 2.0},
    # Counter-attack defender (Onkruud, Oct 2026): high defending + high passing, playmaking minimal (optional:
    # more of it for a midfield counter). Passing as in the CA targets of Bangladesh / Zambia (PS 14 at ~29-30).
    'CAD': {'GK': 1.0, 'DE': 18.0, 'PM': 5.0, 'WI': 1.0, 'Pas': 14.5, 'SC': 1.0, 'SH': 3.0},
    'NWB': {'GK': 1.0, 'DE': 18.3, 'PM': 11.0, 'WI': 16.0, 'Pas': 5.0, 'SC': 1.0, 'SH': 2.0},
    'SHWB': {'GK': 1.0, 'DE': 18.0, 'PM': 8.0, 'WI': 14.0, 'Pas': 7.0, 'SC': 1.0, 'SH': 18.0},
    'PDIM': {'GK': 1.0, 'DE': 15.2, 'PM': 19.0, 'WI': 1.0, 'Pas': 7.0, 'SC': 1.0, 'SH': 2.0},
    'NIM': {'GK': 1.0, 'DE': 11.5, 'PM': 19.0, 'WI': 1.0, 'Pas': 12.8, 'SC': 7.0, 'SH': 2.0},
    'OIM-Q': {'GK': 1.0, 'DE': 7.0, 'PM': 19.0, 'WI': 1.0, 'Pas': 14.0, 'SC': 10.0, 'SH': 2.0},
    'OIM-H': {'GK': 1.0, 'DE': 7.0, 'PM': 19.0, 'WI': 1.0, 'Pas': 15.0, 'SC': 8.5, 'SH': 2.0},
    'NW': {'GK': 1.0, 'DE': 10.0, 'PM': 18.0, 'WI': 18.0, 'Pas': 7.0, 'SC': 4.0, 'SH': 2.0},
    'WTM': {'GK': 1.0, 'DE': 11.0, 'PM': 18.5, 'WI': 16.7, 'Pas': 6.0, 'SC': 4.0, 'SH': 2.0},
    # DFW and TDFW are one position (Onkruud, Oct 2026): the DFW table (spec preference Technical).
    # Defending 3.5: a left-over, as in Dutch senior TDFs (3-4.5).
    'DFW': {'GK': 1.0, 'DE': 3.5, 'PM': 16.0, 'WI': 7.0, 'Pas': 17.3, 'SC': 13.0, 'SH': 2.0},
    'NFW': {'GK': 1.0, 'DE': 3.0, 'PM': 13.0, 'WI': 12.0, 'Pas': 11.0, 'SC': 18.0, 'SH': 9.0},
    'PNF': {'GK': 1.0, 'DE': 3.5, 'PM': 15.0, 'WI': 8.0, 'Pas': 8.6, 'SC': 18.5, 'SH': 9.0},
}

RICHTSKILLS_DEFAULT = RICHTSKILLS_29.copy()

# Main (trained) skill per position, and its value at 17 years 0 days. Onkruud: straight from the youth
# academy at most ~8.2; 7.5 (middle of 'solid') is a typical promoted talent. (Was 6.2-10 per position.)
MAIN_SKILL = {'K': 'GK', 'NCD': 'DE', 'OCD': 'DE', 'CAD': 'DE', 'NWB': 'DE', 'SHWB': 'DE', 'PDIM': 'PM', 'NIM': 'PM',
              'OIM-Q': 'PM', 'OIM-H': 'PM', 'NW': 'WI', 'WTM': 'WI', 'DFW': 'Pas', 'NFW': 'SC', 'PNF': 'SC'}
MAIN_SKILL_AT_17 = 7.5
RICHTSKILLS_AGE_MIN, RICHTSKILLS_AGE_MAX = 17, 33

# ------------------------------------------------------------------------------
# Upward (29 -> 32) breakpoints per position. Each breakpoint only lists the
# skills that actually change at that age; anything omitted stays at its
# RICHTSKILLS_29 baseline value. Positions with a specialty split expose a
# 'spec_map' translating a SPECIALITY_OPTIONS value to a branch key; anything
# not in the map (including 'None') falls back to the 'default' branch.
# ------------------------------------------------------------------------------
RICHTSKILLS_UPWARD = {
    'K': {
        'spec_map': {'Unpredictable': 'U'},
        'branches': {
            'default': [(29, {}), (30, {'DE': 13.0}), (32, {'DE': 15.0})],
            'U': [(29, {}), (30, {'Pas': 8.0}), (32, {'DE': 14.0, 'Pas': 8.0})],
        },
    },
    'NCD': {
        'spec_map': {'Unpredictable': 'U'},
        'branches': {
            'default': [(29, {}), (30, {'Pas': 9.0, 'SH': 9.0}), (32, {'PM': 15.7, 'Pas': 10.0, 'SH': 10.0})],
            'U': [(29, {}), (30, {'Pas': 9.0, 'SH': 9.0}), (32, {'Pas': 12.0, 'SH': 9.0})],
        },
    },
    'OCD': {
        'spec_map': {'Unpredictable': 'U'},
        'branches': {
            'default': [(29, {}), (30, {'Pas': 7.0, 'SH': 9.0}), (32, {'Pas': 10.0, 'SH': 12.0})],
            'U': [(29, {}), (30, {'Pas': 7.0, 'SH': 9.0}), (32, {'DE': 17.5, 'PM': 17.1, 'Pas': 11.5, 'SH': 9.0})],
        },
    },
    'NWB': {
        'spec_map': {'Unpredictable': 'U'},
        'branches': {
            'default': [(29, {}), (30, {'DE': 18.4, 'Pas': 6.0, 'SH': 9.0}), (32, {'DE': 18.3, 'PM': 10.8, 'WI': 17.0, 'Pas': 9.0, 'SH': 9.0})],
            'U': [(29, {}), (30, {'Pas': 7.0, 'SH': 9.0}), (32, {'Pas': 10.8, 'SH': 9.0})],
        },
    },
    'SHWB': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'SH': 20.6}), (32, {'DE': 17.9, 'PM': 7.9, 'WI': 13.9, 'SH': 22.8})],
        },
    },
    'PDIM': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'PM': 19.3, 'SH': 9.0}), (31, {'DE': 15.6, 'PM': 19.3, 'SH': 9.0}), (32, {'DE': 15.6, 'PM': 19.2, 'Pas': 9.5, 'SH': 9.0})],
        },
    },
    'NIM': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'PM': 19.2, 'SC': 6.9, 'SH': 9.0}), (31, {'PM': 19.4, 'Pas': 12.7, 'SC': 6.8, 'SH': 9.0}), (32, {'DE': 11.4, 'PM': 19.3, 'Pas': 14.0, 'SC': 6.6, 'SH': 9.0})],
        },
    },
    'OIM-Q': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'PM': 19.2, 'SH': 9.0}), (31, {'PM': 19.3, 'Pas': 14.5, 'SC': 9.9, 'SH': 9.0}), (32, {'PM': 19.2, 'Pas': 15.0, 'SC': 10.6, 'SH': 9.0})],
        },
    },
    'OIM-H': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'PM': 19.2, 'SH': 9.0}), (31, {'PM': 19.3, 'Pas': 15.1, 'SC': 8.4, 'SH': 9.0}), (32, {'PM': 19.2, 'Pas': 16.2, 'SC': 8.1, 'SH': 9.0})],
        },
    },
    'NW': {
        'spec_map': {'Unpredictable': 'UT', 'Technical': 'UT'},
        'branches': {
            'default': [(29, {}), (30, {'PM': 18.2, 'WI': 18.4, 'SH': 8.0}), (32, {'WI': 18.2, 'Pas': 10.0, 'SC': 6.0, 'SH': 8.0})],
            'UT': [(29, {}), (30, {'WI': 18.2, 'Pas': 8.5, 'SH': 8.0}), (32, {'PM': 17.8, 'WI': 18.0, 'Pas': 11.0, 'SC': 6.0, 'SH': 8.0})],
        },
    },
    'WTM': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'WI': 17.6, 'SH': 8.0}), (32, {'DE': 10.9, 'PM': 18.3, 'WI': 17.4, 'Pas': 9.5, 'SC': 6.0, 'SH': 8.0})],
        },
    },
    'DFW': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'Pas': 17.8, 'SH': 8.0}), (32, {'PM': 15.7, 'Pas': 17.8, 'SC': 14.5, 'SH': 8.0})],
        },
    },
    'NFW': {
        'spec_map': {},
        'branches': {
            # 30: passing 14.0 (was 12.8). Dutch NT NFWs aged 30-32: passing 13.5-15.3 (avg 14.4),
            # PM 12.7-13.9, winger 11.8-12.8, scoring 17.8-18.4.
            'default': [(29, {}), (30, {'Pas': 14.0}), (32, {'Pas': 15.0, 'SC': 17.6})],
        },
    },
    'PNF': {
        'spec_map': {},
        'branches': {
            'default': [(29, {}), (30, {'Pas': 11.0, 'SC': 18.4}), (32, {'PM': 14.9, 'WI': 7.9, 'Pas': 13.9, 'SC': 18.1})],
        },
    },
}


def _resolve_breakpoint(base, override):
    merged = dict(base)
    merged.update(override)
    return merged


def _interp_full_dicts(d0, d1, t):
    return {k: round(v0 + (d1.get(k, v0) - v0) * t, 2) for k, v0 in d0.items()}


def _estimate_upward(pos, age, spec):
    base = RICHTSKILLS_29[pos]
    spec_table = RICHTSKILLS_UPWARD.get(pos)
    if not spec_table:
        return dict(base)

    branch_key = spec_table.get('spec_map', {}).get(spec, 'default') if spec else 'default'
    breakpoints = spec_table['branches'].get(branch_key, spec_table['branches']['default'])
    full_bp = [(a, _resolve_breakpoint(base, ov)) for a, ov in breakpoints]

    if age <= full_bp[0][0]:
        return full_bp[0][1]
    if age >= full_bp[-1][0]:
        return full_bp[-1][1]
    for i in range(len(full_bp) - 1):
        a0, d0 = full_bp[i]
        a1, d1 = full_bp[i + 1]
        if a0 <= age <= a1:
            t = (age - a0) / float(a1 - a0)
            return _interp_full_dicts(d0, d1, t)
    return full_bp[-1][1]


# Countries whose young wingers follow the Dutch curves (WTM PM 13 / WI 14, NW WI 14.5 / PM 11
# at 21). Everyone else trains wingers more as real wingers: WTM PM 12 / WI 15, NW WI 16 / PM 10.
DUTCH_PROFILE_COUNTRIES = {'netherlands', 'nederland', 'the netherlands', 'holland'}


# Country groups (Onkruud): the Netherlands on its own, then by ranking 12 countries per group (A, B, C);
# everyone else D. Fewer trainers and teams in lower groups -> slightly weaker players, so the profile is
# scaled down a little per group (skill above 1 x factor). Fill the lists from the ranking table.
COUNTRY_GROUPS = {
    'A': [],
    'B': [],
    'C': [],
}
COUNTRY_GROUP_FACTOR = {'NL': 1.0, 'A': 0.99, 'B': 0.975, 'C': 0.955, 'D': 0.93}


def country_group(country):
    """'NL', 'A', 'B', 'C' or 'D'. Unknown country -> NL (the built-in default). As long as the lists are
    empty every other country counts as A."""
    c = str(country or '').strip().lower()
    if uses_dutch_profile(c):
        return 'NL'
    if not any(COUNTRY_GROUPS.values()):
        return 'A'
    for g, names in COUNTRY_GROUPS.items():
        if c in {n.strip().lower() for n in names}:
            return g
    return 'D'


def uses_dutch_profile(country):
    """True for the Netherlands, and when no country is known (the built-in default)."""
    c = str(country or '').strip().lower()
    return c in ('', 'nan', 'none') or c in DUTCH_PROFILE_COUNTRIES


# Per-country targets at age 21, from a national coach's U21 training sheet. The built-in curve is
# shifted so it passes through these values at 21: the shift builds up from 17 (the youth-academy
# start stays the same) and fades out towards 29 (the age-29 benchmarks and the 29+ curve stay the
# same). Skills not listed keep the built-in curve.
# Argentina (Oct 2026): the sheet gives MINIMUM skills at 21 for U21/NT selection. Average players
# are above that, so each target is halfway between the Argentine minimum and the Dutch average at
# 21; where the minimum is already above the Dutch average, minimum + 0.5. Set pieces 4-5 for
# outfield players are left out (the solver keeps outfield set pieces at most 3 up to age 22).
COUNTRY_TARGETS_21 = {
    'argentina': {
        'K':    {'GK': 17.5, 'DE': 5.7, 'SH': 15.5},
        'NCD':  {'DE': 14.3, 'PM': 9.8, 'Pas': 6.5},
        'NWB':  {'DE': 14.5, 'PM': 4.9, 'WI': 10.8, 'Pas': 6.5},
        'SHWB': {'DE': 14.5, 'PM': 4.2, 'WI': 8.1, 'Pas': 6.5, 'SH': 16.5},
        'NIM':  {'DE': 7.5, 'PM': 15.7, 'Pas': 7.5, 'SC': 5.5},
        'PDIM': {'DE': 9.0, 'PM': 15.2, 'Pas': 5.5},
        'NW':   {'DE': 6.1, 'PM': 12.5, 'WI': 14.2, 'Pas': 6.5, 'SC': 4.5},
        'NFW':  {'PM': 8.5, 'WI': 8.5, 'Pas': 8.2, 'SC': 14.7},
        'DFW':  {'PM': 12.5, 'WI': 5.0, 'Pas': 12.4, 'SC': 9.0},
    },
}
COUNTRY_TARGET_ALIASES = {'argentinië': 'argentina', 'argentinie': 'argentina'}

# Minimum skills at 21 to be worth a U21 / NT place, per country (selection floor, not a profile).
# Argentina: U21 tab of the national team's training plan ("Habilidades Mínimas a los 21 AÑOS").
# '9+' and '14++' count as 9 and 14; '5/6' as 5.5. Set pieces 4-5 for outfield players are not checked
# (set pieces can't be read from TSI or wage). Extra minimums that only apply with a specialty go in
# COUNTRY_MINIMUMS_21_SPEC.
COUNTRY_MINIMUMS_21 = {
    'argentina': {
        'K':    {'GK': 17, 'DE': 5, 'SH': 15},
        'NCD':  {'DE': 14, 'PM': 9, 'Pas': 6},
        'NWB':  {'DE': 14, 'PM': 4, 'WI': 10, 'Pas': 6},
        'SHWB': {'DE': 14, 'PM': 4, 'WI': 6, 'Pas': 6, 'SH': 15},   # free-kick taker ("Pateador de TL")
        'NIM':  {'DE': 7, 'PM': 15, 'Pas': 7, 'SC': 5},
        'PDIM': {'DE': 8, 'PM': 15, 'Pas': 5},                      # defensive IM, ideally Powerful
        'NW':   {'DE': 6, 'PM': 12, 'WI': 14, 'Pas': 6, 'SC': 4},
        'NFW':  {'PM': 8, 'WI': 8, 'Pas': 8, 'SC': 14},
        'PNF':  {'PM': 9, 'WI': 8, 'Pas': 8, 'SC': 14},             # Powerful forward: playmaking 9-10
        'DFW':  {'PM': 12, 'WI': 4.5, 'Pas': 12, 'SC': 8},          # defensive technical forward
    },
}
COUNTRY_MINIMUMS_21_SPEC = {
    'argentina': {('K', 'Unpredictable'): {'Pas': 5.5}},            # only Unpredictable keepers pass
}

# Minimum skills at 29 for the NT, per country. Argentina: 'Mayor/NT' tab ("Habilidades Mínimas a los 29
# AÑOS"). '17,+' = 17, '6/7' = 6.5, '18,5' = 18.5; outfield set pieces '7/8 (Mínimo)' = 7.5 (checked in the
# Training Planner, not used for the solver's targets: set pieces can't be read from TSI or wage).
COUNTRY_MINIMUMS_29 = {
    'argentina': {
        'K':     {'GK': 20, 'DE': 15, 'SH': 20},
        'NCD':   {'DE': 17, 'PM': 17, 'Pas': 8, 'SH': 7.5},
        'NWB':   {'DE': 17, 'PM': 11, 'WI': 16, 'Pas': 8, 'SH': 7.5},
        'SHWB':  {'DE': 17, 'PM': 9, 'WI': 15, 'Pas': 8, 'SH': 20},     # free-kick taker
        'NIM':   {'DE': 12, 'PM': 18.5, 'Pas': 12, 'SC': 8, 'SH': 7.5},
        'OIM-Q': {'DE': 10, 'PM': 18.5, 'Pas': 14, 'SC': 9, 'SH': 7.5},
        'OIM-H': {'DE': 10, 'PM': 18.5, 'Pas': 14, 'SC': 9, 'SH': 7.5},
        'PDIM':  {'DE': 15, 'PM': 18.5, 'Pas': 9, 'SC': 6.5, 'SH': 7.5},
        'NW':    {'DE': 9, 'PM': 17.5, 'WI': 17.5, 'Pas': 9, 'SC': 6.5, 'SH': 7.5},
        'NFW':   {'PM': 13, 'WI': 13, 'Pas': 11, 'SC': 18, 'SH': 7.5},
        'PNF':   {'PM': 14, 'WI': 11, 'Pas': 11, 'SC': 18, 'SH': 7.5},    # Normal +Jugadas [Potente]
        'DFW':   {'PM': 17, 'WI': 7, 'Pas': 17, 'SC': 12, 'SH': 7.5},     # defensive technical forward
    },
}
COUNTRY_MINIMUMS_29_SPEC = {
    'argentina': {('K', 'Unpredictable'): {'Pas': 6}},
}


# NT guide targets per country at ~21 and ~29: what a good player can look like (a guide, not rules;
# training goes on after a target is reached). Per position code a list of roles:
# (role, specialties the role is meant for or None, targets at 21, targets at 29). A role missing in one
# table has None there.
# Zambia (Oct 2026): NT coach's tables "Skills expected at ~21.00 / ~29.00". W (t/mid) has no 21 row;
# its 21 value is phase 1 of Zambia's "Turbo Training Circuit" (PM 12, W 13, DE 5, PS 5).
# IM (offensive) is an NIM role (scoring/passing instead of defending), not OIM-Q/OIM-H.
COUNTRY_GUIDE_TARGETS = {
    'zambia': {
        'K': [('Goalkeeper', None, {'GK': 17, 'SH': 15}, {'GK': 20, 'DE': 15, 'SH': 20}),
              ('GK (w/defense)', None, {'GK': 16, 'DE': 8, 'SH': 15}, None),
              ('GK (unpredictable)', ('Unpredictable',), {'GK': 16, 'DE': 7, 'Pas': 6, 'SH': 15},
               {'GK': 20, 'DE': 14, 'Pas': 8, 'SH': 20})],
        'NCD': [('Central Defender', None, {'DE': 13, 'PM': 11, 'Pas': 6}, {'DE': 17, 'PM': 15, 'Pas': 10}),
                ('CD (counter-attacks)', ('Unpredictable', 'Technical'), {'DE': 14, 'PM': 5, 'Pas': 10},
                 {'DE': 18, 'PM': 10, 'Pas': 14}),
                ('CD (set pieces)', None, {'DE': 13, 'PM': 8, 'Pas': 6, 'SH': 15},
                 {'DE': 18, 'PM': 14, 'Pas': 8, 'SH': 20})],
        'OCD': [('CD (offensive)', None, {'DE': 11, 'PM': 13, 'Pas': 5}, {'DE': 17, 'PM': 17, 'Pas': 8})],
        'NWB': [('Wingback', None, {'DE': 13, 'PM': 6, 'WI': 11, 'Pas': 6}, {'DE': 18, 'PM': 9, 'WI': 15, 'Pas': 10}),
                ('WB (unpredictable)', ('Unpredictable',), {'DE': 13, 'WI': 10, 'Pas': 10},
                 {'DE': 17, 'WI': 14, 'Pas': 15})],
        'SHWB': [('WB (set pieces)', None, {'DE': 13, 'WI': 9, 'SH': 15},
                  {'DE': 18, 'PM': 7, 'WI': 15, 'Pas': 7, 'SH': 20})],
        'NIM': [('Inner Midfielder', None, {'DE': 5, 'PM': 16, 'Pas': 5, 'SC': 5}, {'DE': 11, 'PM': 18, 'Pas': 12, 'SC': 7}),
                ('IM (offensive)', None, {'PM': 14, 'Pas': 10, 'SC': 5}, {'PM': 18, 'Pas': 17, 'SC': 10}),
                ('IM (t/wing)', None, {'PM': 14, 'WI': 11}, {'DE': 10, 'PM': 17, 'WI': 14, 'Pas': 10})],
        'PDIM': [('IM (defensive)', ('Powerful',), {'DE': 11, 'PM': 13, 'Pas': 5}, {'DE': 15, 'PM': 18, 'Pas': 10})],
        'NW': [('Winger', None, {'DE': 5, 'PM': 11, 'WI': 15, 'Pas': 5}, {'DE': 8, 'PM': 15, 'WI': 18, 'Pas': 12}),
               ('W (counter-attacks)', ('Unpredictable', 'Quick'), {'WI': 15, 'Pas': 10},
                {'DE': 14, 'PM': 13, 'WI': 14, 'Pas': 14, 'SC': 7})],
        'WTM': [('W (t/mid)', None, {'DE': 5, 'PM': 12, 'WI': 13, 'Pas': 5}, {'DE': 10, 'PM': 17, 'WI': 14, 'Pas': 10})],
        'NFW': [('Forward', None, {'PM': 8, 'Pas': 8, 'SC': 14}, {'PM': 11, 'WI': 8, 'Pas': 15, 'SC': 18}),
                ('FW (t/wing)', None, {'PM': 6, 'WI': 12, 'Pas': 6, 'SC': 13}, {'PM': 8, 'WI': 17, 'Pas': 11, 'SC': 17})],
        'PNF': [('FW (PNF)', ('Powerful',), {'PM': 11, 'SC': 14}, {'PM': 16, 'Pas': 12, 'SC': 17})],
        'DFW': [('FW (defensive)', ('Technical',), {'PM': 11, 'Pas': 12, 'SC': 9}, {'PM': 15, 'Pas': 18, 'SC': 15})],
    },
}
_ALL = ('Quick', 'Unpredictable', 'Head', 'Technical', 'Powerful')
# Bangladesh (Oct 2026, CT's NT targets "achievable by the age of 30"; indicative). Only one table, so
# the second column is ~30 and there is no ~21. Specialties = the ones the CT lists for the role.
COUNTRY_GUIDE_TARGETS['bangladesh'] = {
    'K': [('Goalkeeper', ('Quick', 'Head', 'Unpredictable'), None, {'GK': 20, 'DE': 15, 'SH': 20}),
          ('Goalkeeper (U)', ('Unpredictable',), None, {'GK': 20, 'DE': 15, 'Pas': 8, 'SH': 20})],
    'NCD': [('Central Defender', ('Unpredictable', 'Head', 'Quick', 'Technical'), None, {'DE': 17, 'PM': 17, 'Pas': 8}),
            ('Central Defender (CA)', _ALL, None, {'DE': 18, 'PM': 10, 'Pas': 14})],
    'SHWB': [('Wing Back Shooter', ('Unpredictable', 'Quick', 'Technical'), None,
              {'DE': 17, 'PM': 8, 'WI': 17, 'Pas': 7, 'SH': 20})],
    'NWB': [('Wing Back', ('Unpredictable', 'Head', 'Quick', 'Technical'), None, {'DE': 17, 'PM': 10, 'WI': 17, 'Pas': 10})],
    'NIM': [('Inner Midfielder', ('Quick', 'Head', 'Unpredictable', 'Technical'), None, {'DE': 10, 'PM': 19, 'Pas': 13, 'SC': 7})],
    'PDIM': [('Defensive Inner Midfielder', ('Powerful',), None, {'DE': 15, 'PM': 19, 'Pas': 10})],
    'NW': [('Winger', ('Quick', 'Head', 'Unpredictable'), None, {'DE': 8, 'PM': 17, 'WI': 17, 'Pas': 11, 'SC': 8})],
    'NFW': [('Forward', ('Quick', 'Head', 'Unpredictable', 'Technical'), None, {'PM': 13, 'WI': 10, 'Pas': 13, 'SC': 18})],
    'PNF': [('Forward (PNF)', ('Powerful',), None, {'PM': 16, 'WI': 10, 'Pas': 12, 'SC': 17})],   # "17+"
}
# Sri Lanka (Oct 2026): "Target skills expected at 21.00 / 29.00". IM at 21 is "15.5 / 16+": 16 used.
# DE "11-12" at 29: 11.5. Roles only in one table have None in the other.
COUNTRY_GUIDE_TARGETS['sri lanka'] = {
    'K': [('Goalkeeper', None, {'GK': 17, 'SH': 15}, {'GK': 20, 'DE': 14, 'SH': 20})],
    'NCD': [('Centre-Defender', None, {'DE': 14, 'PM': 9, 'Pas': 6}, {'DE': 17.5, 'PM': 15, 'WI': 6, 'Pas': 10, 'SH': 8}),
            ('Centre-Defender CA', ('Unpredictable', 'Technical'), {'DE': 14, 'Pas': 9}, None),
            ('Centre-Defender (Set Pieces)', None, {'DE': 13.5, 'PM': 7, 'SH': 17}, None)],
    'NWB': [('Wingback', None, {'DE': 14, 'WI': 11, 'Pas': 6}, {'DE': 17, 'PM': 9, 'WI': 16, 'Pas': 10})],
    'SHWB': [('Wingback (Set Pieces)', None, {'DE': 13, 'WI': 8, 'SH': 17}, {'DE': 17, 'PM': 8, 'WI': 14, 'Pas': 10, 'SH': 21})],
    'NIM': [('Inner Midfielder', None, {'PM': 16, 'Pas': 7}, {'DE': 11.5, 'PM': 19, 'Pas': 12, 'SC': 8, 'SH': 8})],
    'PDIM': [('Inner Midfielder (Defensive)', ('Powerful',), None, {'DE': 15, 'PM': 18, 'Pas': 10})],
    'WTM': [('WTM (winger to the middle)', None, {'PM': 13, 'WI': 13}, {'DE': 10, 'PM': 18, 'WI': 16, 'Pas': 9, 'SC': 8, 'SH': 8})],
    'NW': [('Wing', None, {'PM': 10, 'WI': 15}, {'DE': 10, 'PM': 16, 'WI': 17, 'Pas': 9, 'SC': 8}),
           ('Wing CA', ('Unpredictable', 'Quick'), {'DE': 7, 'WI': 15, 'Pas': 7}, None)],
    'NFW': [('Forward', ('Head', 'Unpredictable', 'Quick', 'Technical'), {'Pas': 8, 'SC': 15},
             {'PM': 11, 'WI': 10, 'Pas': 14, 'SC': 17.5, 'SH': 8}),
            ('Forward (t/wing) #1', ('Quick',), {'WI': 13, 'SC': 13}, None),
            ('Forward (t/wing) #2', ('Quick',), {'WI': 11, 'SC': 14}, None)],
    'PNF': [('Forward (PNF)', ('Powerful',), {'PM': 10, 'SC': 14}, {'PM': 15, 'WI': 7, 'Pas': 10, 'SC': 18, 'SH': 8})],
    'DFW': [('Forward (Defensive)', ('Technical',), {'PM': 11, 'Pas': 13, 'SC': 9}, {'PM': 15, 'WI': 6, 'Pas': 17, 'SC': 13})],
}
# Ecuador (Oct 2026): NT targets, one table (no ~21), "after age 29" minimums. Two rows read as one column
# shifted in the sheet: GK UNP's 8 taken as passing (as Zambia/Bangladesh), WB Normal as DE 17 / PM 9 /
# WI 15 / PS 10 (sheet: WNG 9, PAS 15, SP 10).
_H, _U, _T, _Q, _P = 'Head', 'Unpredictable', 'Technical', 'Quick', 'Powerful'
COUNTRY_GUIDE_TARGETS['ecuador'] = {
    'K': [('GK', None, None, {'GK': 20, 'DE': 15, 'SH': 20}),
          ('GK UNP', (_U,), None, {'GK': 20, 'DE': 14, 'Pas': 8, 'SH': 20})],
    'NCD': [('CD Normal', (_H, _U, _T, _Q), None, {'DE': 17, 'PM': 14, 'Pas': 10}),
            ('CD SP', (_H, _U, _T, _Q, _P), None, {'DE': 17, 'PM': 8, 'Pas': 9, 'SH': 20})],
    'OCD': [('CD Offense', (_H, _U, _T, _Q, _P), None, {'DE': 16, 'PM': 16, 'Pas': 10})],
    'NWB': [('WB Normal', (_H, _U, _T, _Q), None, {'DE': 17, 'PM': 9, 'WI': 15, 'Pas': 10})],
    'SHWB': [('WB SP', (_H, _U, _T, _Q), None, {'DE': 17, 'PM': 6, 'WI': 13, 'Pas': 8, 'SH': 20})],
    'NIM': [('IM Normal', (_H, _U, _T, _Q), None, {'DE': 11, 'PM': 18.5, 'Pas': 13, 'SC': 9}),
            ('IM Offense', (_H, _Q, _T), None, {'PM': 18.5, 'Pas': 15, 'SC': 12}),
            ('IM TW', (_H, _Q, _U, _T), None, {'DE': 11, 'PM': 17, 'WI': 14, 'Pas': 9})],
    'OIM-Q': [('IM Offense', (_H, _Q, _T), None, {'PM': 18.5, 'Pas': 15, 'SC': 12})],
    'OIM-H': [('IM Offense', (_H, _Q, _T), None, {'PM': 18.5, 'Pas': 15, 'SC': 12})],
    'PDIM': [('IM Defense', (_P,), None, {'DE': 15, 'PM': 18, 'Pas': 10, 'SC': 6})],
    'WTM': [('WNG TM', (_H, _Q, _U, _T), None, {'DE': 11, 'PM': 17, 'WI': 14, 'Pas': 9})],
    'NW': [('WNG Normal', (_H, _Q, _U, _T), None, {'DE': 8, 'PM': 16, 'WI': 17, 'Pas': 10})],
    'NFW': [('FW Normal', (_H, _Q, _U), None, {'PM': 8, 'Pas': 10, 'SC': 17.5, 'SH': 10}),
            ('FW TW', (_H, _Q, _U), None, {'PM': 8, 'WI': 15, 'Pas': 11, 'SC': 17})],
    'PNF': [('FW Power', (_P,), None, {'PM': 15, 'Pas': 11, 'SC': 17.5})],
    'DFW': [('FW Def (TDF)', (_T,), None, {'PM': 15, 'Pas': 17, 'SC': 13})],
}
# Ages of the two target columns per country (default ~21 / ~29).
COUNTRY_GUIDE_AGES = {'bangladesh': (21, 30)}
COUNTRY_GUIDE_ALIASES = {'zambië': 'zambia', 'zambie': 'zambia', 'srilanka': 'sri lanka', 'sri-lanka': 'sri lanka'}


def _guide_country(country):
    c = str(country or '').strip().lower()
    return COUNTRY_GUIDE_ALIASES.get(c, COUNTRY_TARGET_ALIASES.get(c, c))


def country_guide_roles(country, pos):
    """NT guide roles for this country / position: list of (role, specs, t21, t29), or [].
    Dutch players: the target skills at 21 and 29 (skills from level 3, rounded to halves)."""
    c = _guide_country(country)
    if c in DUTCH_PROFILE_COUNTRIES and pos in RICHTSKILLS_29:
        def pick(age):
            prof = _estimate_age_richtskills_base(age)[pos]
            return {k: round(float(v) * 2) / 2 for k, v in prof.items()
                    if float(v) >= 3.0 and (k != 'GK' or pos == 'K') and (k != 'SH' or pos in ('K', 'SHWB'))}
        return [('Target skills', None, pick(21), pick(29))]
    return list(COUNTRY_GUIDE_TARGETS.get(c, {}).get(pos, []))


def country_guide_ages(country):
    """Ages of the two guide target columns for this country (e.g. (21, 29); Bangladesh (21, 30))."""
    return COUNTRY_GUIDE_AGES.get(_guide_country(country), (21, 29))


def country_minimums_21(country, pos, spec=None):
    """Minimum skills at 21 for this country / position (incl. specialty extras), or None."""
    c = str(country or '').strip().lower()
    c = COUNTRY_TARGET_ALIASES.get(c, c)
    base = COUNTRY_MINIMUMS_21.get(c, {}).get(pos)
    if base is None:
        return None
    out = dict(base)
    out.update(COUNTRY_MINIMUMS_21_SPEC.get(c, {}).get((pos, str(spec or '').strip()), {}))
    return out


def country_minimums_29(country, pos, spec=None):
    """Minimum skills at 29 for the NT for this country / position (incl. specialty extras), or None."""
    c = str(country or '').strip().lower()
    c = COUNTRY_TARGET_ALIASES.get(c, c)
    base = COUNTRY_MINIMUMS_29.get(c, {}).get(pos)
    if base is None:
        return None
    out = dict(base)
    out.update(COUNTRY_MINIMUMS_29_SPEC.get(c, {}).get((pos, str(spec or '').strip()), {}))
    return out


_TARGETS_29_CACHE = {}


def _country_targets_29(country):
    """Targets at 29 from the NT minimums, the same way as Argentina's age-21 targets: halfway between the
    minimum and the Dutch profile at 29, or minimum + 0.5 where the minimum is already above it. Set pieces
    of outfield players are left out."""
    c = str(country or '').strip().lower()
    c = COUNTRY_TARGET_ALIASES.get(c, c)
    mins = COUNTRY_MINIMUMS_29.get(c)
    if not mins:
        return None
    if c not in _TARGETS_29_CACHE:
        dutch = _estimate_age_richtskills_base(29)
        out = {}
        for pos, m in mins.items():
            if pos not in dutch:
                continue
            out[pos] = {}
            for sk, v in m.items():
                if sk == 'SH' and pos not in ('K', 'SHWB'):
                    continue
                d = float(dutch[pos].get(sk, 1.0))
                out[pos][sk] = round(float(v) + 0.5 if float(v) >= d else (float(v) + d) / 2.0, 2)
        _TARGETS_29_CACHE[c] = out
    return _TARGETS_29_CACHE[c]


def _country_targets(country):
    c = str(country or '').strip().lower()
    return COUNTRY_TARGETS_21.get(COUNTRY_TARGET_ALIASES.get(c, c))


def _target_fade(age):
    """Share of the age-21 shift applied at this age: 0 at 17, 1 at 21, back to 0 at 29."""
    if age <= 17 or age >= 29:
        return 0.0
    return (age - 17) / 4.0 if age < 21 else (29 - age) / 8.0


def estimate_age_richtskills(age, spec=None, country=None):
    """Age profile per position (see _estimate_age_richtskills_base), shifted towards the country's
    age-21 targets when COUNTRY_TARGETS_21 has them."""
    result = _estimate_age_richtskills_base(age, spec, country)
    targets = _country_targets(country)
    try:
        a = int(age)
    except (TypeError, ValueError):
        return result
    t29 = _country_targets_29(country)
    if (targets or t29) and a > 17:
        # through the age-21 target at 21 and the age-29 target at 29 (from 0 at 17); with only an
        # age-21 target the shift fades out again towards 29 (as before)
        at21 = _estimate_age_richtskills_base(21, spec, country)
        at29 = _estimate_age_richtskills_base(29, spec, country)
        for pos in set(targets or {}) | set(t29 or {}):
            if pos not in result:
                continue
            ta, tb = (targets or {}).get(pos, {}), (t29 or {}).get(pos, {})
            prof = dict(result[pos])
            for sk in set(ta) | set(tb):
                if sk not in prof:
                    continue
                da = float(ta[sk]) - at21[pos][sk] if sk in ta else None
                db = float(tb[sk]) - at29[pos][sk] if sk in tb else None
                prof[sk] = round(max(1.0, prof[sk] + _guide_shift(a, 21, 29, da, db)), 2)
            result[pos] = prof
    return _apply_guide_targets(result, a, spec, country)


def _guide_shift(age, ya, yb, da, db):
    """Shift at this age: 0 at 17, da at ya, db at yb (kept after yb); a missing point is skipped."""
    if age <= 17:
        return 0.0
    if da is None and db is None:
        return 0.0
    if da is None:                                   # only the later point (Bangladesh ~30)
        return db * min(1.0, (age - 17) / float(yb - 17))
    if age <= ya:
        return da * (age - 17) / float(ya - 17)
    if db is None:                                   # only ~21: fade out towards yb
        return da * max(0.0, (yb - age) / float(yb - ya))
    if age >= yb:
        return db
    return da + (db - da) * (age - ya) / float(yb - ya)


def _apply_guide_targets(result, age, spec, country):
    """Shift the profile towards the country's NT guide targets (main role per position): through the ~21
    target at 21 and the ~29 (Bangladesh ~30) target at 29, from 0 at 17. Skills a table leaves out keep the
    profile."""
    c = _guide_country(country)
    guide = COUNTRY_GUIDE_TARGETS.get(c)
    if not guide or age <= 17:
        return result
    ya, yb = COUNTRY_GUIDE_AGES.get(c, (21, 29))
    base_a = _estimate_age_richtskills_base(ya, spec, country)
    base_b = _estimate_age_richtskills_base(min(yb, RICHTSKILLS_AGE_MAX), spec, country)
    for pos, roles in guide.items():
        if pos not in result or not roles:
            continue
        _role, _specs, t21, t29 = roles[0]
        t21, t29 = t21 or {}, t29 or {}
        prof = dict(result[pos])
        for sk in set(t21) | set(t29):
            if sk not in prof:
                continue
            da = float(t21[sk]) - base_a[pos][sk] if sk in t21 else None
            db = float(t29[sk]) - base_b[pos][sk] if sk in t29 else None
            prof[sk] = round(max(1.0, prof[sk] + _guide_shift(age, ya, yb, da, db)), 2)
        result[pos] = prof
    return result


def _estimate_age_richtskills_base(age, spec=None, country=None):
    """Interpolates skills from age 17 up to the age 29 benchmarks, then
    continues the (optionally specialty-aware) upward curve to age 32+.
    country: the Netherlands (or None) uses the Dutch youth curves; other countries get
    the international winger curves (WTM / NW)."""
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 29

    # Position-specific youth curves (age -> value) that replace the default
    # "35% of peak at 17, linear to 29" rule, because young players are trained
    # main-skill-first and pick up secondaries later. Every curve ends at its
    # RICHTSKILLS_29 value so it joins the 29+ upward curve without a jump.
    # Skills not listed here still use the default linear rule.
    #
    # K: keepers train GK/SH much faster than the default assumption. Real data
    # shows U21 keepers at ~79% of peak GK, not 57%. Also real U21 SH is very low (1-4).
    K_CURVE = {
        # 17: 8.1 (was 10): a keeper promoted at 17 has at most ~8.1-8.2 (Onkruud); Reference DB keepers
        # aged 17: GK 8 in the first ~90 days, 9-10 only later in the season; at 19: GK 12-15 (avg 13.1).
        'GK': {17: 8.1, 19: 13.0, 21: 16.5, 25: 19.5, 29: 21.0},
        'DE': {17: 2.0,  21: 6.4,  25: 8.5,  29: 12.0},  # 8 Dutch U21 keepers: DEF 4-8, avg 6.4
        # Properly trained keepers have set pieces 14+ at 21 (the Dutch SH 6 keeper was a
        # training mistake). Without a real HTMS this is still a guess.
        'SH': {17: 5.0,  21: 14.5, 25: 17.0, 29: 21.0},
        'PM': {17: 1.0,  21: 2.5,  25: 5.0,  29: 1.0},   # PM low (avg 3-4)
        'WI': {17: 1.0,  21: 2.0,  25: 2.0,  29: 1.0},
        'Pas':{17: 1.0,  21: 2.5,  25: 3.0,  29: 1.0},   # PS avg=3.4
        'SC': {17: 1.0,  21: 2.0,  25: 2.0,  29: 1.0},
    }

    # NW: winging leads, PM follows a few levels behind; passing stays ~6-7 and
    # defending is barely trained while young (~15 WI / 11-12 PM / 6-7 Pas / 5 DE at 22).
    NW_CURVE = {
        'WI':  {17: 8.0, 21: 14.5, 23: 15.8, 26: 17.0, 29: 18.0},
        'PM':  {17: 5.0, 21: 11.0, 23: 12.5, 26: 15.0, 29: 18.0},
        'Pas': {17: 2.5, 21: 6.0,  23: 6.5,  29: 7.0},
        # Dutch U21 wingers: DE 6-7 (avg 6.2) and SC 3-7 (avg 5.2), left from before training.
        'DE':  {17: 4.0, 21: 6.2,  23: 6.6,  26: 7.8,  29: 10.0},
        'SC':  {17: 2.5, 21: 5.0,  26: 5.0,  29: 4.0},
    }
    # WTM: winging and PM trained almost evenly (~14.2 WI / 13.4 PM at 22).
    WTM_CURVE = {
        # Winger stays ahead of playmaking while young (13/14, 14/14, 15/13 at 21-23).
        'WI':  {17: 7.5, 21: 14.0, 23: 15.0, 26: 16.0, 29: 16.7},
        'PM':  {17: 6.0, 21: 13.0, 23: 14.0, 26: 15.5, 29: 18.5},
        'Pas': {17: 2.5, 21: 5.5,  23: 6.0,  29: 6.0},
        # Dutch U21 WTMs: DE 5-7 (avg 6.0), SC 4-5 (avg 4.8).
        'DE':  {17: 4.0, 21: 6.0,  23: 6.5,  26: 8.3,  29: 11.0},
        'SC':  {17: 2.5, 21: 4.8,  26: 4.8,  29: 4.0},
    }
    # NIM: playmaking first (~16.5 at 21, like the Dutch top IMs), secondaries still
    # modest while young: passing ~6.5-7, defending ~6.5-7, scoring ~3-4.
    NIM_CURVE = {
        'PM':  {17: 8.0, 21: 16.3, 23: 17.2, 26: 18.3, 29: 19.0},
        # Young: passing a little above defending (Dutch U21 NIMs: Pas 6.8 / DE 6.0 on average,
        # varies per player); defending catches up around 23 and leads from ~25.
        'Pas': {17: 3.0, 21: 6.8,  23: 7.5,  26: 9.0,  29: 12.8},
        'DE':  {17: 3.0, 21: 6.3,  23: 7.5,  26: 9.8,  29: 11.5},
        'SC':  {17: 2.0, 21: 3.8,  23: 4.5,  26: 6.0,  29: 7.0},
    }
    # PDIM (powerful defensive inner mid): playmaking like an inner mid, plus a lot of defending.
    # Dutch U21 PDIM Schraaven: DE 10.2 / PM 14.7 / Pas 7 / SC 4; Finnish Evikoski PM 16.0 on his
    # 21st birthday. (Before: no curve, 35% of the age-29 target -> PM only 10.8 at 21.)
    PDIM_CURVE = {
        'PM':  {17: 8.0, 21: 15.5, 23: 16.6, 26: 18.0, 29: 19.0},
        'DE':  {17: 4.5, 21: 10.0, 23: 11.3, 26: 13.4, 29: 15.2},
        'Pas': {17: 3.0, 21: 6.0,  23: 6.3,  26: 6.7,  29: 7.0},
        'SC':  {17: 2.0, 21: 2.0,  23: 1.8,  26: 1.4,  29: 1.0},
        'WI':  {17: 2.0, 21: 2.0,  29: 1.0},
    }
    # NFW / PNF: scoring first (~15.3 at 21, Dutch top U21 forwards 15.1-15.7), with
    # passing ~8-8.8 and PM / WI only ~7-8 while young.
    NFW_CURVE = {
        # Defending: a left-over from before training, kept (Dutch U21 NFWs: 2-4, avg 3.0).
        'DE':  {17: 3.0, 29: 3.0},
        'SC':  {17: 9.0, 21: 15.3, 23: 16.3, 26: 17.3, 29: 18.0},
        'PM':  {17: 3.5, 21: 7.3,  23: 8.3,  26: 10.5, 29: 13.0},
        'WI':  {17: 3.5, 21: 7.2,  23: 8.0,  26: 10.0, 29: 12.0},
        'Pas': {17: 4.0, 21: 8.4,  23: 9.0,  26: 10.0, 29: 11.0},
    }
    # PNF: scoring plus playmaking (Dutch U21 PNFs: SC 14.0-14.6, PM 10.4-11.0,
    # WI / passing 5-7). Defending isn't part of the ideal PNF profile; when a player
    # has it (from before his training), enter it under Known Subskills.
    PNF_CURVE = {
        # Defending: left-over from before training, typically 2-5.
        'DE':  {17: 3.5, 29: 3.5},
        'SC':  {17: 8.5, 21: 14.3, 23: 15.5, 26: 17.0, 29: 18.5},
        'PM':  {17: 5.0, 21: 10.6, 23: 11.8, 26: 13.5, 29: 15.0},
        'WI':  {17: 2.5, 21: 5.8,  23: 6.3,  26: 7.2,  29: 8.0},
        'Pas': {17: 2.5, 21: 6.0,  23: 6.8,  26: 7.8,  29: 8.6},
    }
    # NCD: defending first (Dutch U21 centre-backs: DE 14.2-15.9, PM 6-10.4, passing
    # 3-5.7). Winger/scoring 3-5 in that data are left-overs from before training,
    # not part of the profile.
    NCD_CURVE = {
        'DE':  {17: 7.5, 21: 14.6, 23: 15.8, 26: 17.3, 29: 18.5},
        # Playmaking trained alongside defending: ~15/10-11 at 21 (14/10 .. 14/12 also common).
        'PM':  {17: 4.5, 21: 10.5, 23: 11.5, 26: 13.0, 29: 15.0},
        'Pas': {17: 2.0, 21: 4.8,  23: 5.3,  26: 6.2,  29: 7.0},
    }
    # NWB: defending and winger trained together (Dutch U21 wing-backs: DE 13.3-14.3,
    # WI 10.6-13.0, PM 5-7, passing 4-6). Scoring 3-4 there is a left-over, not profile.
    NWB_CURVE = {
        'DE':  {17: 6.5, 21: 13.9, 23: 15.0, 26: 16.8, 29: 18.3},
        'WI':  {17: 5.0, 21: 11.7, 23: 12.8, 26: 14.6, 29: 16.0},
        'PM':  {17: 2.5, 21: 5.8,  23: 6.8,  26: 8.8,  29: 11.0},
        'Pas': {17: 2.5, 21: 5.0,  29: 5.0},
    }
    # SHWB: set pieces are trained first and are already at the adult level by 21
    # (Dutch U21 set-piece wing-backs: SP 17.3-19.0, DE 12.6-13.6, WI 8.7-12.2,
    # PM 2-6, passing 5-6). Scoring 2-5 in that data is a left-over, not profile.
    SHWB_CURVE = {
        'SH':  {17: 9.0, 21: 18.0, 29: 18.0},
        'DE':  {17: 6.5, 21: 13.0, 23: 14.2, 26: 16.3, 29: 18.0},
        'WI':  {17: 4.5, 21: 10.1, 23: 11.0, 26: 12.6, 29: 14.0},
        'PM':  {17: 2.0, 21: 4.5,  23: 5.2,  26: 6.6,  29: 8.0},
        'Pas': {17: 2.5, 21: 5.5,  29: 7.0},
    }
    # DFW (was TDFW): a very balanced player; at U21 about PM 11, passing 12.5-13, scoring 10 (Dutch
    # U21 TDFWs Zander and Weijermans), ending at the DFW table at 29.
    DFW_CURVE = {
        'DE':  {17: 3.0, 21: 3.5, 29: 3.5},
        'PM':  {17: 6.0, 21: 11.0, 23: 12.4, 26: 14.3, 29: 16.0},
        'Pas': {17: 7.0, 21: 12.75, 23: 13.9, 26: 15.7, 29: 17.3},
        'SC':  {17: 5.5, 21: 10.0, 23: 10.7, 26: 11.9, 29: 13.0},
        'WI':  {17: 3.5, 21: 5.5, 23: 6.0, 26: 6.5, 29: 7.0},
    }
    # Outside the Netherlands young wingers are trained more as pure wingers. Both curves end at
    # the same age-29 targets, so they join the 29+ curve without a jump.
    if not uses_dutch_profile(country):
        # WTM at 21-22: WI 15 / PM 13 (Dutch: PM 13 / WI 14; was PM 12 / WI 15 for other countries).
        WTM_CURVE = dict(WTM_CURVE,
                         WI={17: 8.0, 21: 15.0, 23: 15.8, 26: 16.4, 29: 16.7},
                         PM={17: 6.0, 21: 13.0, 23: 13.8, 26: 15.5, 29: 18.5})
        # NW at 21-22: WI 16 / PM 10 (Dutch: WI 14.5 / PM 11).
        NW_CURVE = dict(NW_CURVE,
                        WI={17: 8.5, 21: 16.0, 23: 16.8, 26: 17.4, 29: 18.0},
                        PM={17: 4.5, 21: 10.0, 23: 11.5, 26: 14.5, 29: 18.0})
    YOUTH_CURVES = {'SHWB': SHWB_CURVE, 'K': K_CURVE, 'NW': NW_CURVE, 'WTM': WTM_CURVE, 'NIM': NIM_CURVE, 'PDIM': PDIM_CURVE,
                    'NFW': NFW_CURVE, 'PNF': PNF_CURVE, 'NCD': NCD_CURVE, 'NWB': NWB_CURVE, 'DFW': DFW_CURVE}

    def _interp_curve(curve, age):
        ages = sorted(curve.keys())
        if age <= ages[0]: return curve[ages[0]]
        if age >= ages[-1]: return curve[ages[-1]]
        for i in range(len(ages)-1):
            a0, a1 = ages[i], ages[i+1]
            if a0 <= age <= a1:
                t = (age - a0) / (a1 - a0)
                return round(curve[a0] + (curve[a1] - curve[a0]) * t, 2)
        return curve[ages[-1]]

    result = {}
    for pos, bench_29 in RICHTSKILLS_29.items():
        if age <= 29:
            pos_result = {}
            for sk, v_29 in bench_29.items():
                if sk == MAIN_SKILL.get(pos) and MAIN_SKILL_AT_17:
                    # Main skill: a typical talent comes out of the youth academy with about 7.5 at 17
                    # (the academy maximum is ~8.2), then the position's curve / linear to 29.
                    curve = dict(YOUTH_CURVES.get(pos, {}).get(sk) or {29: v_29})
                    curve[17] = MAIN_SKILL_AT_17
                    pos_result[sk] = _interp_curve(curve, age)
                elif sk in YOUTH_CURVES.get(pos, {}):
                    # Position-specific curve, regardless of v_29 value
                    pos_result[sk] = _interp_curve(YOUTH_CURVES[pos][sk], age)
                elif v_29 <= 1.0:
                    pos_result[sk] = v_29
                else:
                    v_17 = max(1.0, v_29 * 0.35)
                    if age <= 17:
                        pos_result[sk] = round(v_17, 2)
                    else:
                        t = (age - 17) / 12.0
                        pos_result[sk] = round(v_17 + (v_29 - v_17) * t, 2)
            result[pos] = pos_result
        else:
            result[pos] = _estimate_upward(pos, age, spec)
    # Country group: other countries' players slightly weaker (A ~ Netherlands, D clearly lower).
    _f = COUNTRY_GROUP_FACTOR.get(country_group(country), 1.0)
    if _f != 1.0:
        result = {pos: {sk: (round(1.0 + (v - 1.0) * _f, 2) if v > 1.0 else v) for sk, v in prof.items()}
                  for pos, prof in result.items()}
    return result

RICHTSKILLS_U21_DEFAULT = estimate_age_richtskills(21)

# ── Log: which countries have their own target skills, and for which age group ─────────────────────
# One entry per change. 'u21' / 'nt' = which age group the data covers; 'used_in' = where the app uses it.
COUNTRY_TARGET_LOG = [
    dict(country='Netherlands', date='', u21=True, nt=True, richt=True, planner=True),
    dict(country='Argentina', date='Oct 2026', u21=True, nt=True, richt=True, planner=True),
    dict(country='Zambia', date='Oct 2026', u21=True, nt=True, richt=True, planner=True),
    dict(country='Bangladesh', date='Oct 2026', u21=False, nt=True, richt=True, planner=True),
    dict(country='Sri Lanka', date='Oct 2026', u21=True, nt=True, richt=True, planner=True),
    dict(country='Ecuador', date='Oct 2026', u21=False, nt=True, richt=True, planner=True),
]


def country_target_log():
    """The log, checked against the data actually in this file (a country listed in the data but not in
    the log still shows up)."""
    rows = [dict(r) for r in COUNTRY_TARGET_LOG]
    known = {r['country'].lower() for r in rows}
    for c in set(COUNTRY_TARGETS_21) | set(COUNTRY_MINIMUMS_21) | set(COUNTRY_GUIDE_TARGETS):
        if c not in known:
            g = COUNTRY_GUIDE_TARGETS.get(c, {})
            has21 = c in COUNTRY_TARGETS_21 or c in COUNTRY_MINIMUMS_21 or any(r[2] for v in g.values() for r in v)
            has29 = any(r[3] for v in g.values() for r in v)
            rows.append(dict(country=c.title(), date='?', u21=has21, nt=has29, richt=True,
                             planner=bool(g) or c in COUNTRY_MINIMUMS_21))
    return rows