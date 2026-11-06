# ==============================================================================
# Extra knowledge for All Combos (enumerate_outcomes' logw_fn / extra_filter):
#   1. trained skills in the order you pick them (up to 4), as a strong preference
#   2. "spare levels" options: one build per skill you did not pick
#   3. team shape: how your known players are built, for a player whose training is unknown
#   4. match ratings (pasted from Hattrick): which builds explain his star ratings
# Tested on AFRN (12), a Dutch club (8) and a senior team (14) with real skills (other-skill error, levels):
#   order picked (3-4 skills)     0.66/0.34/0.55 -> 0.46/0.28/0.39  (vs the 'halfway' training template)
#   right spare option (3 picked) 0.58/0.28/0.48 -> 0.33/0.14/0.40
#   team shape, training unknown  2.43/2.12/2.08 -> 1.45/0.35/0.85  (vs the NT / age template)
#   match history, main skill only (10 players, held out)       1.99 -> 1.29
# ==============================================================================
import numpy as np

SKILLS = ['DE', 'PM', 'WI', 'Pas', 'SC']           # = ht_engine.OUTCOME_SKILLS
_TSI_W = np.array([1.034, 1.031, 0.826, 1.035, 1.038])

# ---------------------------------------------------------------- 1. picked training order
ORDER_SLACK = 0.5     # how hard 'second <= main' etc. is kept (levels); 0.5 = strong preference, not a hard rule


def training_prior4(trained, profile, pos_code, age, own=None):
    """training_outcome_prior for the first 3 of up to 4 trained skills."""
    from ht_engine import training_outcome_prior
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS][:4]
    prior, sd = training_outcome_prior(tr[:3], profile, pos_code, age, own)
    # a 4th skill gets no level of its own (tested: a 'halfway' level for it made AFRN 0.46 -> 0.57); it only
    # takes part in the order (ordered_logw): above every skill you did not pick, below the 3rd
    return prior, sd


def ordered_logw(trained):
    """'The picked skills are his highest, in this order' (soft; added on top of the template)."""
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS][:4]
    idx = [SKILLS.index(k) for k in tr]
    rest = [SKILLS.index(k) for k in SKILLS if k not in tr]

    def f(x):
        out = np.zeros(len(x))
        for a, b in zip(idx, idx[1:]):
            out -= 0.5 * (np.maximum(0, x[:, b] - x[:, a]) / ORDER_SLACK) ** 2
        if idx and rest:
            out -= 0.5 * (np.maximum(0, x[:, rest].max(1) - x[:, idx[-1]]) / ORDER_SLACK) ** 2
        return out
    return f


FLAT_SD = {k: 50.0 for k in SKILLS}    # 'no template': used when the team shape decides alone


# ---------------------------------------------------------------- 2. spare-level options
def spare_filter(trained, skill):
    """Combinations where `skill` is clearly (1+ level) the highest of the skills you did not pick."""
    rest = [k for k in SKILLS if k not in (trained or [])]
    ix = SKILLS.index(skill)
    oth = [SKILLS.index(k) for k in rest if k != skill]

    def f(lv):
        if not oth:
            return np.ones(len(lv), bool)
        return np.all(lv[:, [ix]] >= lv[:, oth] + 1, axis=1)
    return f


def spare_skills(trained):
    return [k for k in SKILLS if k not in (trained or [])]


# ---------------------------------------------------------------- 3. team shape
def team_shape(players, min_players=4):
    """players: [{skill: whole level}] (your players with real levels). Per main skill (and 'all'): each other
    skill as a share of the main skill -> {main: {skill: (mean, spread)}}, or {} with too few players."""
    pl = [p for p in players if all(k in p for k in SKILLS)]
    if len(pl) < min_players:
        return {}
    out = {}
    for key in SKILLS + ['all']:
        use = [p for p in pl if key == 'all' or max(SKILLS, key=lambda k: p[k]) == key]
        if len(use) < 2:
            continue
        sh = {}
        for k in SKILLS:
            v = [(p[k] + .5) / (p[max(SKILLS, key=lambda q: p[q])] + .5) for p in use
                 if max(SKILLS, key=lambda q: p[q]) != k]
            if v:
                sh[k] = (float(np.mean(v)), max(0.05, float(np.std(v))))
        out[key] = sh
    return out


def shape_logw(main, shape):
    """Builds that look like the team shape for this main skill."""
    sh = shape.get(main) or shape.get('all') or {}
    mi = SKILLS.index(main)

    def f(x):
        m = x[:, mi]
        out = np.zeros(len(x))
        for i, k in enumerate(SKILLS):
            if i == mi:
                continue
            a, s = sh.get(k, (0.3, 0.15))
            out -= 0.5 * ((x[:, i] - a * m) / np.maximum(s * m, 0.8)) ** 2
        return out
    return f


# ---------------------------------------------------------------- 4. match ratings
# stars = A * sector-weighted skills * ((form - 0.5) / 7) ** 0.45 + XP * log10(experience) + OFFSET[position]
# fitted on 243 ratings of 10 players with real skills (sd 0.46 per match; held out per player 0.52)
RATING_A, RATING_XP, RATING_FORM_EXP = 0.3197, 1.873, 0.45
RATING_OFFSET = {'NCD': -1.728, 'NFW': -2.857, 'NIM': -2.265, 'NW': -1.566, 'NWB': -2.062}
RATING_SD_MATCH = 0.52
RATING_SYS = {'history': 0.30, 'table': 0.60}     # extra margin: other teams' tactics / orders
_RW_KEY = {'NCD': 'mCD', 'NIM': 'mNIM', 'NFW': 'mNFW', 'NW': 'lNW', 'NWB': 'lNWB'}


def _sector_sum(x, pos, loy, gk=1.0, sh=3.0):
    from role_weights import ROLE_SECTOR_WEIGHTS as RW
    s = 0.0
    for sec, ws in RW[_RW_KEY[pos]].items():
        for k, w in ws.items():
            v = x[:, SKILLS.index(k)] if k in SKILLS else ({'GK': gk, 'SH': sh}[k] + 0.5)
            s = s + w * (v + loy)
    return s


def predict_stars(x, pos, form, xp, loy, gk=1.0, sh=3.0):
    return (RATING_A * _sector_sum(x, pos, loy / 20.0, gk, sh) * ((form - 0.5) / 7) ** RATING_FORM_EXP
            + RATING_XP * np.log10(max(xp or 1, 1)) + RATING_OFFSET[pos])


def _then(x, trained, tsi_now, form_now, tsi_then, form_then):
    """Skills (N,5) as they were in an earlier match: the trained skills scaled back so his TSI then fits."""
    gi = [SKILLS.index(k) for k in (trained or [])[:2] if k in SKILLS] or [int(np.argmax(x[0]))]
    s_all = ((np.maximum(x, 1) - 1) ** 3) * _TSI_W
    s_now = s_all.sum(1)
    s_tr = s_all[:, gi].sum(1)
    ratio = np.sqrt(tsi_then / tsi_now) * ((form_now - 1) / max(form_then - 1, 0.5)) ** 0.25
    g = np.clip((ratio * s_now - (s_now - s_tr)) / np.maximum(s_tr, 1e-6), 0.05, 1.3) ** (1 / 3)
    xt = x.copy()
    xt[:, gi] = 1 + (x[:, gi] - 1) * g[:, None]
    return xt


def ratings_logw(ratings, trained, tsi_now, form_now, gk=1.0, sh=3.0, last=14):
    """ratings: {'kind': 'history', 'matches': [...]} or {'kind': 'table', 'player': {...}}.
    Returns logw(x) or None when there is nothing usable (keepers, unknown positions)."""
    if not ratings:
        return None
    kind = ratings.get('kind')
    sys_ = RATING_SYS.get(kind, 0.6)
    groups = []
    if kind == 'history':
        ms = [m for m in ratings.get('matches', []) if not m.get('mixed') and m['pos'] in RATING_OFFSET][:last]
        if not ms:
            return None

        def f(x):
            per = {}
            for m in ms:
                xt = _then(x, trained, tsi_now, form_now, m['tsi'], m['form'] or form_now)
                pred = predict_stars(xt, m['pos'], m['form'] or form_now, m['xp'], m['loy'] or 20, gk, sh)
                per.setdefault(m['pos'], []).append(m['stars'] - pred)
            out = np.zeros(len(x))
            for res in per.values():
                r = np.mean(res, axis=0)
                out -= 0.5 * r ** 2 / (RATING_SD_MATCH ** 2 / len(res) + sys_ ** 2)
            return out
        return f
    if kind == 'table':
        pl = ratings.get('player') or {}
        rows = [(q, v) for q, v in (pl.get('pos') or {}).items() if q in RATING_OFFSET and v['minutes'] >= 45]
        if not rows:
            return None
        form, xp, loy = pl.get('form') or form_now, pl.get('xp') or 1, pl.get('loy') or 20

        def f(x):
            out = np.zeros(len(x))
            for q, v in rows:
                pred = predict_stars(x, q, form, xp, loy, gk, sh)
                out -= 0.5 * (v['avg'] - pred) ** 2 / (RATING_SD_MATCH ** 2 / v['matches'] + sys_ ** 2)
            return out
        return f
    return None


def ratings_summary(ratings, last=14):
    """[(order, matches used, avg stars, max stars)] for the 'found' panel."""
    if not ratings:
        return []
    if ratings.get('kind') == 'history':
        ms = [m for m in ratings.get('matches', []) if not m.get('mixed')][:last]
        per = {}
        for m in ms:
            per.setdefault(m['pos'], []).append(m['stars'])
        return [(q, len(v), float(np.mean(v)), max(v)) for q, v in per.items()]
    pl = ratings.get('player') or {}
    return [(q, v['matches'], v['avg'], v['max']) for q, v in (pl.get('pos') or {}).items()]


def combine(*fns):
    fns = [f for f in fns if f is not None]
    if not fns:
        return None

    def f(x):
        return sum(fn(x) for fn in fns)
    return f


# ---------------------------------------------------------------- 5. TSI history: his hidden form
# Hattrick shows form as a whole level, but TSI uses the hidden value (5 = 5.00-5.99): one TSI can be ~5% off what
# the skills give at "5.5". Several TSIs since the birthday (skills about the same, other forms) average that out.
def hidden_form(points, age, form_now, stam_now, trained=False):
    """points: [dict(tsi, form, stam)] since his last birthday, newest first (today's included).
    Returns dict(form, lo, hi, n, index=[...]) or None with fewer than 3 points."""
    from ht_engine import stamina_middle
    pts = [p for p in points if p.get('tsi') and p.get('form') and p.get('stam')]
    if len(pts) < 3:
        return None
    fm = lambda f: min(float(f) + 0.5, 8.0)
    idx = [(p['tsi'] / (np.sqrt(fm(p['form']) - 1) * np.sqrt(stamina_middle(p['stam'], age) - 1))) ** 0.5
           for p in pts]
    s_now = (pts[0]['tsi'] / (np.sqrt(fm(form_now) - 1) * np.sqrt(stamina_middle(stam_now, age) - 1))) ** 0.5
    s_avg = float(np.mean(idx))
    f_eff = 1 + (fm(form_now) - 1) * (s_now / s_avg) ** 4
    f0 = float(int(form_now))
    half = HIDDEN_FORM_HALF * (1.6 if trained else 1.0)
    lo, hi = max(f0, f_eff - half), min(f0 + 0.99, f_eff + half)
    if lo >= hi:            # outside his displayed level: skills changed; keep the edge it points to
        lo, hi = (f0, f0 + 2 * half) if f_eff < f0 else (f0 + 0.99 - 2 * half, f0 + 0.99)
    return dict(form=float(min(max(f_eff, f0), f0 + 0.99)), lo=float(lo), hi=float(hi), n=len(pts),
                index=[float(v) for v in idx], s_now=float(s_now), s_avg=s_avg)


HIDDEN_FORM_HALF = 0.25


def tracker_summary(info, tsi_now=None):
    """Hattrick Portal history (ht_paste.parse_portal) -> what the solver uses:
    dict(points=[...since the birthday...], hf=hidden_form(...) or None, stable=bool, w_lo_frac=float or None,
         rows=[dict(date, form, stam, tsi, salary, index, since)]) or None.
    Seniors (28+) only use it: their skills don't grow, so TSIs since the birthday differ only by form/stamina
    (and some ageing). Tested (14 seniors, simulated history): hidden form off 0.23 -> 0.14 of a level,
    other skills 1.34 -> 1.32 levels off (small: TSI can't tell the other skills apart)."""
    import datetime as dt
    from ht_engine import stamina_middle
    h = [r for r in (info or {}).get('history') or [] if r.get('tsi') and r.get('form') and r.get('stam')]
    age, days = info.get('age'), info.get('days')
    if not h or age is None or days is None:
        return None
    upd = info.get('updated') or h[0]['date']
    bday = upd - dt.timedelta(days=int(days)) if upd else None
    fm = lambda f: min(float(f) + 0.5, 8.0)
    rows = []
    for r in h:
        since = bool(bday and r['date'] and r['date'] > bday)
        a_r = int(age) if since or not bday else int(age) - 1          # TSI's age factor changed on the birthday
        agef = max(0.125, 1 - 0.125 * (a_r - 27)) if a_r > 27 else 1.0
        idx = (r['tsi'] / (np.sqrt(fm(r['form']) - 1) * np.sqrt(stamina_middle(r['stam'], a_r) - 1) * agef)) ** 0.5
        rows.append(dict(r, index=float(idx), since=since))
    base = next((r['index'] for r in reversed(rows) if r['since']), rows[-1]['index'])
    for r in rows:
        r['rel'] = r['index'] / base * 100     # 100 = his skills at the first update after the birthday
    pts = [dict(tsi=r['tsi'], form=r['form'], stam=r['stam']) for r in rows if r['since']]
    if tsi_now and pts and round(pts[0]['tsi']) != round(float(tsi_now)):
        pts = []        # the page is older than the TSI you entered: don't mix them
    out = dict(rows=rows, points=pts, hf=None, stable=None, w_lo_frac=None, birthday=bday)
    if int(age) < 28 or int(age) > 35 or len(pts) < 3:
        return out
    out['hf'] = hidden_form(pts, int(age), pts[0]['form'], pts[0]['stam'])
    ix = [r['index'] for r in rows if r['since']][::-1]          # oldest first
    half = len(ix) // 2
    drop = 1 - np.mean(ix[half:]) / np.mean(ix[:half]) if half else 0.0
    out['drop'] = float(drop)
    out['stable'] = bool(drop < 0.03)
    if out['stable']:
        out['w_lo_frac'] = 0.985     # skills about the same since the birthday: today's wage ~ his actual wage
    return out


# ---------------------------------------------------------------- 6. salary history (Salaries tab of his page)
# Hattrick sets the wage on each birthday from his skills that day. Per season: how much of a full season of main-skill
# training shows up in his wage (training speed as in the Training planner). What didn't go into the main skill went
# into other skills -> a rough level for his second skill. A wage that stays exactly the same means nothing changed
# (not trained), so that season adds nothing. Only seasons up to 27 count for training; up to 35 for the trend.
SALARY_MAX_AGE = 35


def salary_hint(wages, spec='None', sh=None, main='PM'):
    """wages {age: wage on that birthday (without the abroad bonus)} -> dict(shares={age: share of the season on the
    main skill}, missing=levels of main training that went elsewhere, second=2nd skill if one skill got it all,
    second2=each if two skills shared it, main_level={age: main skill (if his wage were only that skill)},
    trend={age: wage without the age factor}) or None with fewer than 3 usable birthdays."""
    from ht_engine import lookup_wage, skill_at_age
    W = {int(a): float(w) for a, w in (wages or {}).items() if 17 <= int(a) <= SALARY_MAX_AGE and w}
    if len(W) < 3:
        return None
    k = (1.10 if spec and str(spec) not in ('None', 'nan', '') else 1.0) * (1 + 0.0025 * float(sh or 0))
    tr = {'DE': 'Defending', 'PM': 'Playmaking', 'SC': 'Scoring', 'WI': 'Winger (crossing)', 'Pas': 'Passing'}.get(main, 'Playmaking')

    def inv(w):
        lo, hi = 0.0, 25.0
        for _ in range(50):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if 250 + lookup_wage(m, main if main in ('DE', 'PM', 'SC', 'WI', 'Pas') else 'PM') < w else (lo, m)
        return lo
    agef = lambda a: max(0.1, 1 - 0.1 * (a - 28)) if a > 28 else 1.0
    ages = sorted(W)
    L = {a: inv(W[a] / agef(a) / k) for a in ages}
    shares, sec1, sec2, missing = {}, 4.5, 4.5, 0.0
    for a in ages:
        if a >= 28 or a + 1 not in W:
            continue
        act, full = L[a + 1] - L[a], skill_at_age(a + 1, 0, a, 0, L[a], tr) - L[a]
        if full <= 0:
            continue
        share = max(0.0, min(1.0, act / full))
        rest = 0.0 if W[a + 1] == W[a] else 1.0 - share
        shares[a] = share if W[a + 1] != W[a] else 0.0
        missing += full * rest
        if rest > 0.02:
            sec1 = skill_at_age(a + 1, 0, a, 0, sec1, 'Passing', share=rest)
            sec2 = skill_at_age(a + 1, 0, a, 0, sec2, 'Passing', share=rest / 2)
    return dict(shares=shares, missing=float(missing), second=float(sec1), second2=float(sec2), main_level=L,
                trend={a: W[a] / agef(a) for a in ages if a >= 27}, untrained=[a for a in ages if a + 1 in W and W[a + 1] == W[a] and a < 28])


def salary_budget_logw(wages, main, spec='None', age=None, base=4.5, sd=0.5):
    """Soft hint for the "Spare levels mostly in ..." options: the training that the salary history says did not go into
    his main skill went into his other skills. The time needed to train his top secondary (one skill under 28; the top two
    from 28 on, since seniors spread it) from about 4.5 should match it. Tested on 14 players with real skills, the right
    option: other skills 1.36 -> 1.08 levels off (under 28: 0.98 -> 0.80, 28+: 1.74 -> 1.35)."""
    from ht_engine import lookup_wage, skill_at_age
    W = {int(a): float(w) for a, w in (wages or {}).items() if 17 <= int(a) <= SALARY_MAX_AGE and w}
    if len(W) < 3 or main not in SKILLS:
        return None, 0.0
    k = 1.10 if spec and str(spec) not in ('None', 'nan', '') else 1.0
    tr = {'DE': 'Defending', 'PM': 'Playmaking', 'SC': 'Scoring', 'WI': 'Winger (crossing)', 'Pas': 'Passing'}[main]

    def inv(w):
        lo, hi = 0.0, 25.0
        for _ in range(50):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if 250 + lookup_wage(m, main) < w else (lo, m)
        return lo
    agef = lambda a: max(0.1, 1 - 0.1 * (a - 28)) if a > 28 else 1.0
    ages = sorted(W)
    L = {a: inv(W[a] / agef(a) / k) for a in ages}
    off = []
    for a in ages:
        if a > 27 or a + 1 not in W:
            continue
        act, full = L[a + 1] - L[a], skill_at_age(a + 1, 0, a, 0, L[a], tr) - L[a]
        f = 0.0 if W[a + 1] == W[a] else float(min(max(1 - act / max(full, 1e-6), 0), 1))
        off.append((a, f))
    A = sum(f for _, f in off)
    if not off:
        return None, 0.0
    a0 = int(round(sum(a * f for a, f in off) / A)) if A > 0.05 else 21
    lev, tot, xs, ts = base, 0.0, [base], [0.0]
    for _ in range(80):
        lev = skill_at_age(a0 + 1, 0, a0, 0, lev, 'Passing', share=0.25)
        tot += 0.25
        xs.append(lev)
        ts.append(tot)
        if lev > 21:
            break
    xs, ts = np.array(xs), np.array(ts)
    mi = SKILLS.index(main)
    oth = [i for i in range(5) if i != mi]
    top = 1 if (age is None or int(age) < 28) else 2

    def f(x):
        o = np.sort(x[:, oth], axis=1)[:, ::-1]
        T = sum(np.interp(np.maximum(o[:, j], base), xs, ts) for j in range(top))
        return -0.5 * ((T - A) / sd) ** 2
    return f, float(A)


# ---------------------------------------------------------------- 6. which second skill (Other players)
# TSI + wage can't tell which skill is his second one (tested on 36 real players: picking the best fit was right
# 11% of the time, the usual training for the position 61%). How players are really built can: the Reference DB.
# Per position + highest skill: how often each skill is the second highest. Fallback when the Reference DB has
# too few players (counted from 2,357 Reference DB players with real levels, Oct 2026).
SEC_FREQ_DEFAULT = {'CAD|DE': (72, {'PM': 0.181, 'Pas': 0.75, 'SC': 0.056, 'WI': 0.014}),
 'DFW|PM': (110, {'Pas': 0.782, 'SC': 0.173, 'WI': 0.045}),
 'DFW|Pas': (27, {'PM': 0.667, 'SC': 0.259, 'WI': 0.074}),
 'DFW|SC': (38, {'PM': 0.447, 'Pas': 0.553}),
 'K|DE': (77, {'PM': 0.558, 'Pas': 0.169, 'SC': 0.078, 'WI': 0.195}),
 'NCD|DE': (247, {'PM': 0.927, 'Pas': 0.061, 'SC': 0.012}),
 'NFW|PM': (10, {'SC': 0.7, 'WI': 0.3}),
 'NFW|SC': (159, {'DE': 0.038, 'PM': 0.239, 'Pas': 0.579, 'WI': 0.145}),
 'NFW|WI': (12, {'PM': 0.25, 'Pas': 0.25, 'SC': 0.5}),
 'NIM|DE': (36, {'PM': 0.917, 'Pas': 0.083}),
 'NIM|PM': (326, {'DE': 0.604, 'Pas': 0.393, 'WI': 0.003}),
 'NIM|Pas': (9, {'DE': 0.111, 'PM': 0.889}),
 'NWB|DE': (251, {'PM': 0.187, 'Pas': 0.036, 'SC': 0.012, 'WI': 0.765}),
 'NWB|WI': (20, {'DE': 1.0}),
 'NW|PM': (58, {'WI': 1.0}),
 'NW|WI': (152, {'DE': 0.026, 'PM': 0.882, 'Pas': 0.079, 'SC': 0.013}),
 'OCD|DE': (30, {'PM': 1.0}),
 'OCD|PM': (19, {'DE': 1.0}),
 'OIM-H|PM': (54, {'Pas': 0.87, 'SC': 0.13}),
 'OIM-Q|PM': (75, {'Pas': 0.747, 'SC': 0.24, 'WI': 0.013}),
 'PDIM|PM': (89, {'DE': 1.0}),
 'PNF|PM': (25, {'SC': 1.0}),
 'PNF|SC': (144, {'DE': 0.035, 'PM': 0.806, 'Pas': 0.16}),
 'SHWB|DE': (136, {'PM': 0.096, 'Pas': 0.059, 'SC': 0.022, 'WI': 0.824}),
 'WTM|DE': (12, {'PM': 1.0}),
 'WTM|PM': (157, {'DE': 0.197, 'Pas': 0.025, 'SC': 0.006, 'WI': 0.771})}


def secondary_freq(ref_df, pos, main, min_n=8):
    """{skill: share} of the second-highest skill for players at `pos` whose highest skill is `main`, and how many
    players that is. From the Reference DB (whole levels only), else the built-in table."""
    try:
        if ref_df is not None and not getattr(ref_df, 'empty', True):
            import pandas as _pd
            from ht_engine import normalize_position as _np_pos
            d = ref_df.copy()
            for k in SKILLS:
                d[k] = _pd.to_numeric(d[k], errors='coerce')
            d = d.dropna(subset=SKILLS)
            d = d[(d[SKILLS] % 1 == 0).all(axis=1) & (d[SKILLS] >= 1).all(axis=1)]
            d = d[~(d[SKILLS].astype(int) == [5, 5, 5, 4, 5]).all(axis=1)]   # the 'not filled in' placeholder
            d = d[d['Positie'].astype(str).map(_np_pos) == pos]
            if len(d):
                top = d[SKILLS].values.argsort(axis=1)
                mains = [SKILLS[i] for i in top[:, -1]]
                secs = [SKILLS[i] for i in top[:, -2]]
                pairs = [s for m, s in zip(mains, secs) if m == main]
                if len(pairs) >= min_n:
                    return {k: pairs.count(k) / len(pairs) for k in set(pairs)}, len(pairs)
    except Exception:
        pass
    n, f = SEC_FREQ_DEFAULT.get(f"{pos}|{main}", (0, {}))
    return dict(f), n


def other_secondary(ref_df, pos, trained, min_share=0.10):
    """The likeliest other second skill when you picked main + second: (skill, share, players) or None. Tested on 36
    real players: the usual training + this option holds the right second skill for 75% (was 61%)."""
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS]
    if len(tr) != 2:
        return None
    freq, n = secondary_freq(ref_df, pos, tr[0])
    cand = sorted(((s, k) for k, s in freq.items() if k not in tr and s >= min_share), reverse=True)
    if not cand:
        return None
    return cand[0][1], cand[0][0], n


THIRD_SLOT_MIN_AGE = 28


def third_slot_logw(trained, prior, sd3=3.0, flat=(4.5, 1.5)):
    """Main + second picked: the highest of the other skills sits at a real third-skill level (halfway between the
    second and the leftovers) instead of a leftover around 4.5. Used in the "Spare levels mostly in ..." options of
    seniors only. Tested (spare option = his real 3rd skill): seniors 0.60 -> 0.36 levels off; for younger club
    players it was worse (0.40 -> 0.52), so not used there."""
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS]
    rest = [SKILLS.index(k) for k in SKILLS if k not in tr]
    if len(tr) != 2 or len(rest) < 2:
        return None
    t3 = (float(prior.get(tr[1], 10.0)) + flat[0]) / 2

    def f(x):
        top = x[:, rest].max(1)
        return 0.5 * ((top - flat[0]) / flat[1]) ** 2 - 0.5 * ((top - t3) / sd3) ** 2
    return f


# ---------------------------------------------------------------- 7. mixed training
def mixed_prior(trained, profile, pos_code, age, own=None):
    """Main skill first, then two skills trained mixed (in turns, or one after the other): both expected at the same
    level, halfway between a second and a third trained skill, and a little looser."""
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS][:3]
    prior, sd = training_prior4(tr, profile, pos_code, age, own)
    if len(tr) == 3:
        lvl = (prior[tr[1]] + prior[tr[2]]) / 2
        prior[tr[1]] = prior[tr[2]] = lvl
        sd[tr[1]] = sd[tr[2]] = 3.5
    return prior, sd


def mixed_logw(trained):
    """Main skill highest, the two mixed skills above every other skill, no order between those two."""
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS][:3]
    if len(tr) < 3:
        return ordered_logw(tr)
    im, i1, i2 = (SKILLS.index(k) for k in tr)
    rest = [SKILLS.index(k) for k in SKILLS if k not in tr]

    def f(x):
        out = -0.5 * (np.maximum(0, np.maximum(x[:, i1], x[:, i2]) - x[:, im]) / ORDER_SLACK) ** 2
        if rest:
            out -= 0.5 * (np.maximum(0, x[:, rest].max(1) - np.minimum(x[:, i1], x[:, i2])) / ORDER_SLACK) ** 2
        return out
    return f


def mixed_setups(pos, min_share=0.10):
    """Mixed setups for a position: main + its two most common second skills (Reference DB table), when the
    second one is common enough. Returns [(main, a, b)]."""
    from ht_engine import POS_TRAINING
    usual = POS_TRAINING.get(pos)
    if not usual:
        return []
    n, f = SEC_FREQ_DEFAULT.get(f"{pos}|{usual[0]}", (0, {}))
    top = [k for k, s in sorted(f.items(), key=lambda t: -t[1]) if s >= min_share][:2]
    return [(usual[0], top[0], top[1])] if len(top) == 2 else []


# ---------------------------------------------------------------- 8. the leftover skills as a ladder
# Real players' skills that are not trained are not all "leftovers around 4.5": one is clearly higher (the 3rd skill),
# one middle, one low. Levels by age (real club players + the Reference DB, middle of the level):
#   up to 22: 6.5 / 4.8 / 3.7 (club), 5.4 / 4.2 / 3.4 (ref)    28+: 8.0 / 4.7 / 3.4 (club), 9.2 / 6.0 / 3.6 (ref)
# The ladder says which levels the leftovers have, not which skill is which; the "Spare levels mostly in ..." options
# pick that. Tested (spare option = his real 3rd skill): 36 real players 0.399 -> 0.362 levels off, 363 Reference DB
# players 1.256 -> 0.951; All Combos the same (club players) or better (ref 1.655 -> 1.554).
LEFTOVER_LADDER = {'young': (6.0, 4.5, 3.5), 'mid': (7.5, 5.0, 3.7), 'senior': (8.5, 5.0, 3.5)}
LADDER_SD = 1.5


def _ladder_band(age):
    age = int(age)
    return 'young' if age <= 22 else 'mid' if age <= 27 else 'senior'


def ladder_logw(trained, age, sd=None):
    """The skills you did not pick, highest first, sit at the ladder levels for his age (rank 3, 4, 5).
    For 2-4 picked skills; None otherwise."""
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS]
    rest = [SKILLS.index(k) for k in SKILLS if k not in tr]
    if not 2 <= len(tr) <= 4 or not rest:
        return None
    t = np.array(LEFTOVER_LADDER[_ladder_band(age)][len(tr) - 2:][:len(rest)], dtype=float)
    s_ = float(sd or LADDER_SD)

    def f(x):
        srt = -np.sort(-x[:, rest], axis=1)
        return -0.5 * (((srt - t[None, :]) / s_) ** 2).sum(1)
    return f


def ladder_sd(sd, trained):
    """The template's per-skill certainty with the leftovers freed (the ladder takes over their levels)."""
    tr = [t for t in dict.fromkeys(trained or []) if t in SKILLS]
    if not 2 <= len(tr) <= 4:
        return sd
    out = dict(sd)
    for k in SKILLS:
        if k not in tr:
            out[k] = 50.0
    return out


# ---------------------------------------------------------------- 9. a real HTMS: the most likely exact combinations
# HTMS ability = the sum of each skill's points at its whole level (Foxtrick table; matches the Hattrick Portal exactly
# on 26 tracked players). With his real HTMS the combinations that fit TSI + wage drop from ~35,000 to ~120, and his
# real combination was the most likely one for 23%, in the top 3 for 65%, top 5 for 81% (26 tracked players, his top 2
# picked as training). An average of those would land between them, so they are shown one by one.
def _htms_tables():
    from ht_engine import HTMS_ABILITY_TABLE as A
    return {k: np.array([A[min(i, 23)][k] for i in range(26)], dtype=float) for k in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']}


def htms_filter(htms, sh_levels, gk_levels=(1,)):
    """extra_filter for enumerate_outcomes: combinations (whole levels of DE PM WI Pas SC) whose HTMS ability, with set
    pieces / keeper at one of the given levels, is exactly `htms`."""
    T = _htms_tables()
    extra = sorted({float(T['SH'][int(s)] + T['GK'][int(g)]) for s in sh_levels for g in gk_levels})
    target = float(htms)

    def f(lv):
        lv = np.clip(np.asarray(lv, dtype=int), 0, 25)
        pts = sum(T[k][lv[:, i]] for i, k in enumerate(SKILLS))
        return np.isin(np.round(target - pts), np.round(extra))
    return f


def top_combinations(oc, n=3):
    """The n most likely whole-level combinations of an enumerate_outcomes result: [(levels dict, share)]."""
    if not oc or oc.get('_lv') is None:
        return []
    L, W = oc['_lv'].astype(int), oc['_w'].astype(float)
    W = W / W.sum()
    idx = np.argsort(-W)[:n]
    return [({k: int(L[i, j]) for j, k in enumerate(SKILLS)}, float(W[i])) for i in idx]


# ---------------------------------------------------------------- 10. forward profiles (scoring first, passing second)
# 83 real forwards (NFW / PNF / DFW, 27+) in the Reference DB with scoring highest and passing second come in two shapes,
# measured as levels below scoring. "Pure" (playmaking 8 or lower, 24 players) and "playmaking" (59 players).
# Leave-one-out test (Defending / Playmaking / Winger / Passing, levels off): pure forwards 1.39 with their own shape
# (1.9-2.9 the old way), playmaking forwards 1.20 (3.1-3.6); Aćim Cvijetić 0.34 (4 of 5 levels right).
# TSI + wage alone cannot tell the two apart (39% of the pure ones found); a DFW, a known playmaking level or the real
# HTMS (with set pieces known) can: with HTMS the mix of both shapes was 1.11 / 1.01 levels off.
FWD_POSITIONS = ('NFW', 'PNF', 'DFW', 'TFW')
FWD_MIN_AGE = 27
FWD_SHAPES = {
    'pure': {'DE': 12.7, 'PM': 10.1, 'WI': 9.5, 'Pas': 4.4},
    'playmaking': {'DE': 12.7, 'PM': 5.6, 'WI': 8.7, 'Pas': 3.2},
}
FWD_SHARE = {'pure': 24 / 83, 'playmaking': 59 / 83}
FWD_SD = 1.5
FWD_PM_SPLIT = 7.85          # scoring minus playmaking: above = pure, below = playmaking


def fwd_shape_logw(kind, sd=FWD_SD):
    """'His skills sit this many levels below his scoring' (logw_fn for enumerate_outcomes, levels + 0.5)."""
    off = FWD_SHAPES[kind]
    sc = SKILLS.index('SC')

    def f(x):
        out = np.zeros(len(x))
        for k, o in off.items():
            out -= 0.5 * (((x[:, sc] - x[:, SKILLS.index(k)]) - o) / sd) ** 2
        return out
    return f


def fwd_mix_logw(store=None):
    """Both shapes, weighted by how common they are; `store` gets each combination's weight under each shape."""
    fp, fm = fwd_shape_logw('pure'), fwd_shape_logw('playmaking')
    lp, lm = np.log(FWD_SHARE['pure']), np.log(FWD_SHARE['playmaking'])

    def f(x):
        a, b = fp(x) + lp, fm(x) + lm
        if store is not None:
            store['a'], store['b'] = a, b
        m = np.maximum(a, b)
        return m + np.log(np.exp(a - m) + np.exp(b - m))
    return f


def fwd_pure_share(store):
    """After a solve with fwd_mix_logw(store): how much of the weight is on the pure shape (0-1)."""
    a, b = store.get('a'), store.get('b')
    if a is None or not len(a):
        return None
    m = max(a.max(), b.max())
    pa, pb = np.exp(a - m).sum(), np.exp(b - m).sum()
    return float(pa / (pa + pb))


def fwd_pick(pos, sc, pm=None):
    """The shape to use when we know enough: DFW -> playmaking; a known playmaking level -> by scoring minus
    playmaking. None = can't tell (show both)."""
    if pos == 'DFW':
        return 'playmaking', 'DFW'
    if pm is not None and sc is not None:
        return ('pure' if float(sc) - float(pm) >= FWD_PM_SPLIT else 'playmaking'), 'pm'
    return None, None


# ---------------------------------------------------------------- 11. player profiles for other positions (27+)
# Like the forwards (section 10): real players of 27+ in the Reference DB (set-piece specialists left out) fall into two
# shapes per position group, measured as levels below the main skill (k-means, 2 groups). Back-test on 117 players
# (leave-one-out shapes): his own shape 1.36 levels off vs All Combos 1.50; for the hard ones (All Combos 1.5+ off,
# 44 players) 1.55 vs 2.28. TSI + wage pick the right shape 84% of the time, a known split skill 95%, his HTMS 85%.
# Inner midfielders: the shapes help a few (Alamgir Kazi 2.84 -> 1.09) but not on average, so they are never starred.
SHAPE_MIN_AGE = 27
SHAPE_SD = 1.5
# CD / WB: when TSI + wage alone give one shape 95%+ (49 of 117 players), it was right 96% and 1.25 levels off
# vs All Combos 1.49, so it is picked; wingers' confident picks were not better, so they need a known skill or HTMS.
SHAPE_TW_CONF = 0.95
SHAPE_GROUPS = {
    'CD': {'positions': ('NCD', 'OCD', 'CAD'), 'main': 'DE', 'split': 'PM', 'star': True, 'star_tw': True,
           'shapes': {'Playmaking defender': ({'PM': 1.6, 'WI': 12.3, 'Pas': 7.2, 'SC': 12.6}, 0.86),
                      'Pure defender': ({'PM': 11.2, 'WI': 13.1, 'Pas': 10.1, 'SC': 13.7}, 0.14)}},
    'WB': {'positions': ('NWB', 'SHWB'), 'main': 'DE', 'split': 'PM', 'star': True, 'star_tw': True,
           'shapes': {'Playmaking wingback': ({'PM': 6.2, 'WI': 2.3, 'Pas': 7.0, 'SC': 11.8}, 0.56),
                      'Pure wingback': ({'PM': 11.1, 'WI': 4.6, 'Pas': 9.6, 'SC': 13.6}, 0.44)}},
    'W': {'positions': ('NW', 'WTM'), 'main': 'WI', 'split': 'DE', 'star': True,
          'shapes': {'All-round winger': ({'DE': 7.6, 'PM': 2.1, 'Pas': 6.3, 'SC': 11.2}, 0.51),
                     'Pure winger': ({'DE': 12.3, 'PM': 2.7, 'Pas': 6.6, 'SC': 13.8}, 0.49)}},
    'IM': {'positions': ('NIM', 'OIM-H', 'OIM-Q', 'PDIM'), 'main': 'PM', 'split': 'DE', 'star': False,
           'shapes': {'Defensive midfielder': ({'DE': 3.4, 'WI': 12.2, 'Pas': 6.0, 'SC': 11.4}, 0.57),
                      'Attacking midfielder': ({'DE': 10.7, 'WI': 12.3, 'Pas': 5.5, 'SC': 9.9}, 0.43)}},
}


def shape_group(pos, age, main_skill=None):
    """The profile group for this position and age (the position tells his main skill: All Combos can get it wrong
    for exactly these players, e.g. Béla Borbola), else None."""
    if int(age) < SHAPE_MIN_AGE:
        return None
    for g, d in SHAPE_GROUPS.items():
        if pos in d['positions'] and (main_skill is None or d['main'] == main_skill):
            return g
    return None


def profile_logw(group, name, sd=SHAPE_SD):
    """'His skills sit this many levels below his main skill' (logw_fn for enumerate_outcomes)."""
    d = SHAPE_GROUPS[group]
    off, mi = d['shapes'][name][0], SKILLS.index(d['main'])

    def f(x):
        out = np.zeros(len(x))
        for k, o in off.items():
            out -= 0.5 * (((x[:, mi] - x[:, SKILLS.index(k)]) - o) / sd) ** 2
        return out
    return f


def profile_mix_logw(group, store=None):
    """Both shapes, weighted by how common they are; `store` gets each combination's weight under each shape."""
    names = list(SHAPE_GROUPS[group]['shapes'])
    fs = [profile_logw(group, n) for n in names]
    ls = [np.log(SHAPE_GROUPS[group]['shapes'][n][1]) for n in names]

    def f(x):
        a, b = fs[0](x) + ls[0], fs[1](x) + ls[1]
        if store is not None:
            store['a'], store['b'] = a, b
        m = np.maximum(a, b)
        return m + np.log(np.exp(a - m) + np.exp(b - m))
    return f


def shape_first_share(store):
    """After a solve with profile_mix_logw(store): the weight on the first shape of the group (0-1)."""
    return fwd_pure_share(store)


def shape_pick(group, main_val, split_val):
    """With his split skill known: the shape whose gap (main minus split skill) is closest. None when not known."""
    if main_val is None or split_val is None:
        return None
    d = SHAPE_GROUPS[group]
    gap = float(main_val) - float(split_val)
    return min(d['shapes'], key=lambda n: abs(gap - d['shapes'][n][0][d['split']]))


# ---------------------------------------------------------------- 12. how sure each skill is (calibrated)
# The weighted share of the combinations (TSI + wage fit) that have a skill at the build's level promises too much at
# the top: tested on 191 players with known skills, 0.94 came true 0.67 of the time. These points map the share to
# how often it really came true (isotonic fit, rounded); the same for 'within 1 level'.
SURE_EXACT = ((0.0, 0.0), (0.025, 0.11), (0.16, 0.17), (0.31, 0.19), (0.37, 0.33), (0.55, 0.5), (0.6, 0.54),
              (0.69, 0.61), (0.72, 0.67), (1.0, 0.75))
SURE_IN1 = ((0.0, 0.0), (0.05, 0.33), (0.52, 0.41), (0.55, 0.5), (0.6, 0.52), (0.7, 0.57), (0.88, 0.63),
            (0.92, 0.83), (1.0, 0.86))


def sure_skills(L, W, build):
    """L: whole levels (n x 5, DE PM WI Pas SC), W: weights. -> ({skill: (level, chance right)}, expected skills
    exactly right, expected skills within 1 level), with the chances calibrated."""
    W = np.asarray(W, dtype=float)
    W = W / W.sum()
    xe, ye = zip(*SURE_EXACT)
    x1, y1 = zip(*SURE_IN1)
    per, ex, in1 = {}, 0.0, 0.0
    for i, k in enumerate(SKILLS):
        lv = int(float(build[k]))
        p = float(W[L[:, i] == lv].sum())
        q = float(W[np.abs(L[:, i] - lv) <= 1].sum())
        pc = float(np.interp(p, xe, ye))
        per[k] = (lv, pc)
        ex += pc
        in1 += float(np.interp(q, x1, y1))
    return per, ex, in1