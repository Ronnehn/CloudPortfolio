# ==============================================================================
# Reading pages copied from Hattrick (Ctrl+A, Ctrl+C): a player's page, his match history, and a team's
# "Players" statistics table. Every reader is tolerant: tabs or spaces, a cut-off first/last row, rows on one
# line or two. Whatever can't be read is skipped, never guessed.
# ==============================================================================
import re

# Hattrick slot -> the app's normal order for that slot
SLOT_ORDER = {'CD': 'NCD', 'IM': 'NIM', 'FW': 'NFW', 'WB': 'NWB', 'LB': 'NWB', 'RB': 'NWB', 'W': 'NW', 'LW': 'NW',
              'RW': 'NW', 'WI': 'NW', 'GK': 'K', 'KP': 'K'}
SECTION_ORDER = {'Keeper': 'K', 'Central Defender': 'NCD', 'Wing Back': 'NWB', 'Inner Midfielder': 'NIM',
                 'Winger': 'NW', 'Forward': 'NFW'}
SPECIALTIES = ('Technical', 'Quick', 'Powerful', 'Unpredictable', 'Head', 'Regainer', 'Support')
ORDER_LABEL = {'NCD': 'Central defender', 'NWB': 'Wing back', 'NIM': 'Inner midfielder', 'NW': 'Winger',
               'NFW': 'Forward', 'K': 'Keeper'}

_NUM = r'(?:\d{1,3}(?:[  .,]\d{3})+|\d+|-)'
_ROW = re.compile(r"(\d{2})\s*\((\d{1,3})\)\s+(" + _NUM + r")\s+(\d|-)\s+(\d|-)\s+(\d{1,2}|-)\s+(\d{1,2}|-)\b(.*)")
_SLOT = re.compile(r"\b(CD|IM|FW|WB|LB|RB|LW|RW|W|GK|KP)\s*\((\d{1,3})'?\)")
_STARS = re.compile(r'^\s*(\d{1,2}(?:[.,]5|[.,]0)?)\s*$')


def _clean(t):
    return (t or '').replace('‭', '').replace('‬', '').replace('‎', '').replace('‏', '')


def _int(s):
    return int(re.sub(r'[  .,]', '', s))


def parse_match_history(text):
    """A player's match history -> [dict(age, days, tsi, form, stam, loy, xp, pos, slot, minutes, stars, mixed)],
    newest first (as on the page). The position he played longest counts when he switched during a match;
    rows without TSI (e.g. 'Best performance'), without stars or with 0 minutes are skipped."""
    lines = [_clean(x) for x in (text or '').splitlines()]
    out, i = [], 0
    while i < len(lines):
        m = _ROW.search(lines[i])
        if not m:
            i += 1
            continue
        slots = _SLOT.findall(m.group(8))
        stars, j = None, i + 1
        tail = _SLOT.sub('', m.group(8)).strip()
        st = re.findall(r'(?<![\d(])(\d{1,2}(?:[.,]5|[.,]0)?)\s*$', tail)
        if st and slots:
            stars = float(st[0].replace(',', '.'))
        while stars is None and j < len(lines) and j <= i + 4:
            t = lines[j]
            if _ROW.search(t):
                break
            more = _SLOT.findall(t)
            if more:
                slots += more
            elif _STARS.match(t):
                stars = float(_STARS.match(t).group(1).replace(',', '.'))
            elif t.strip() not in ('', '-'):
                break
            j += 1
        i = max(i + 1, j)
        if m.group(3) == '-' or m.group(4) == '-' or not slots or stars is None:
            continue
        slot, mins = max(((s, int(n)) for s, n in slots), key=lambda t: t[1])
        if mins == 0 or not (0 < stars <= 20):
            continue
        num = lambda g: int(g) if g != '-' else None
        out.append(dict(age=int(m.group(1)), days=int(m.group(2)), tsi=float(_int(m.group(3))), form=num(m.group(4)),
                        stam=num(m.group(5)), loy=num(m.group(6)), xp=num(m.group(7)), pos=SLOT_ORDER[slot], slot=slot,
                        minutes=mins, stars=stars, mixed=len(slots) > 1))
    return out


def parse_team_table(text):
    """A team's 'Players' statistics table -> {name: dict(spec, form, stam, loy, xp,
    pos={order: dict(avg, max, matches, minutes)})}. Players under 'No Matches' get no positions."""
    out, sect = {}, None
    for raw in (text or '').splitlines():
        line = _clean(raw).strip()
        if not line or line.startswith('Player name'):
            continue
        if line in SECTION_ORDER:
            sect = SECTION_ORDER[line]
            continue
        if line.startswith('No Matches'):
            sect = None
            continue
        m = re.match(r"(.+?)\s{2,}(?:(\w+)\s+)?(\d)\s+(\d)\s+(\d{1,2})\s+(\d{1,2})(?:\s+(\d+)\s*\((\d+)'\)\s+"
                     r"(\d{1,2}(?:[.,]\d)?)\s+(\d{1,2}(?:[.,]\d)?))?\s*$", line)
        if not m:
            continue
        name = m.group(1).strip()
        spec = m.group(2) if m.group(2) in SPECIALTIES else None
        p = out.setdefault(name, dict(spec=spec, form=int(m.group(3)), stam=int(m.group(4)), loy=int(m.group(5)),
                                      xp=int(m.group(6)), pos={}))
        if sect and m.group(7):
            p['pos'][sect] = dict(avg=float(m.group(9).replace(',', '.')), max=float(m.group(10).replace(',', '.')),
                                  matches=int(m.group(7)), minutes=int(m.group(8)))
    return out


_WORD_NUM = r'[A-Za-z\- ]*?\(?(\d{1,2})\)?'


def parse_player_page(text):
    """A player's own page -> dict with what could be read: name, id, age, days, tsi, wage (as paid),
    base_wage (without the foreign bonus), foreign, form, stamina, xp, leadership, loyalty, spec."""
    t = _clean(text)
    out = {}
    m = (re.search(r'^\s*(?:\d+\.\s*)?([^\n(]{3,60}?)\s*\n?\s*\((\d{6,10})\)', t, re.M)
         or re.search(r'^\s*(?:\d+\.\s*)?([^\n(]{3,60}?)\s*\n\s*[A-Z]{2,4}\s*\n\s*\((\d{6,10})\)', t, re.M))
    if m:
        out['name'], out['id'] = m.group(1).strip(), int(m.group(2))
    m = re.search(r'(\d{2}) years and (\d{1,3}) days', t)
    if m:
        out['age'], out['days'] = int(m.group(1)), int(m.group(2))
    m = re.search(r'\bTSI\s+(' + _NUM + r')', t)
    if m and m.group(1) != '-':
        out['tsi'] = float(_int(m.group(1)))
    m = re.search(r'\bWage\s+(' + _NUM + r')\s*€?(?:\s*\((' + _NUM + r')\s*€?\))?', t)
    if m:
        out['wage'] = float(_int(m.group(1)))
        if m.group(2):
            out['base_wage'] = float(_int(m.group(2)))
    out['foreign'] = bool(re.search(r'foreign player', t, re.I))
    m = re.search(r'\((\d{1,2})\)\s+experience', t, re.I)
    if m:
        out['xp'] = int(m.group(1))
    m = re.search(r'\((\d{1,2})\)\s+leadership', t, re.I)
    if m:
        out['leadership'] = int(m.group(1))
    m = re.search(r'\((\d{1,2})\)\s+loyalty', t, re.I)
    if m:
        out['loyalty'] = int(m.group(1))
    m = re.search(r'\bForm\s+[A-Za-z ]*?(\d{1,2})\b', t)
    if m:
        out['form'] = int(m.group(1))
    m = re.search(r'\bStamina\s+[A-Za-z ]*?(\d{1,2})\b', t)
    if m:
        out['stamina'] = int(m.group(1))
    m = re.search(r'\bSpecialty\s+(\S+)', t)
    if m:
        out['spec'] = m.group(1) if m.group(1) in SPECIALTIES else 'None'
    return out if any(k in out for k in ('tsi', 'wage', 'age')) else {}


def detect(text):
    """What was pasted: 'portal', 'salaries', 'history', 'table', 'player' or None (in that order of preference)."""
    if parse_portal(text):
        return 'portal'
    if parse_salaries(text):
        return 'salaries'
    if len(parse_match_history(text)) >= 1:
        return 'history'
    tab = parse_team_table(text)
    if tab and any(p['pos'] for p in tab.values()):
        return 'table'
    if parse_player_page(text):
        return 'player'
    return None


def split_players(text):
    """Several pasted match histories -> {player id: text}."""
    parts = re.split(r'\((\d{6,10})\)', text or '')
    return {int(parts[k]): parts[k + 1] for k in range(1, len(parts) - 1, 2)}


# ---------------------------------------------------------------- Hattrick Portal player page (tracker history)
# Works on the page's HTML (loaded by the app) and on the page copied with Ctrl+A, Ctrl+C. In the copied text only
# the oldest history row has full values and the newer rows show changes; the HTML has the full value of every row.
PORTAL_RATE = {'€': 1.0, 'eur': 1.0, 'kr': 10.0, 'sek': 10.0}    # Hattrick: 1 € = 10 Swedish kronor (Portal default)
_DASH = '–−'


def _sint(s):
    s = (s or '').strip().replace('&ndash;', '-')
    for d in _DASH:
        s = s.replace(d, '-')
    s = re.sub(r'[  ,.]', '', s)
    return int(s) if re.fullmatch(r'[+-]?\d+', s or 'x') else None


def _date(s, day_first=False):
    import datetime as dt
    m = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', s or '')
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    mo, d = (b, a) if (day_first or a > 12) else (a, b)
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def _wage_eur(t):
    m = re.search(r'Wage:?\s*(' + _NUM + r')\s*(€|kr|SEK|EUR)?(\s*/\s*week)?([^\n<]*)', t, re.I)
    if not m or m.group(1) == '-':
        return None, None, None, None
    unit = (m.group(2) or '€').lower()
    rate = PORTAL_RATE.get(unit)
    foreign = bool(re.search(r'including\s+20\s*%\s*bonus', m.group(4) or '', re.I))
    return (float(_int(m.group(1))) / rate if rate else None), f"{m.group(1)} {m.group(2) or '€'}", foreign, rate


def parse_portal(text):
    """Hattrick Portal player page -> dict(name, id, age, days, tsi, wage (€, as paid), wage_text, foreign, form,
    stamina, xp, spec, updated (date), history=[dict(date, form, stam, xp, tsi, salary)] newest first) or {}."""
    raw = text or ''
    if 'Total Skill Index' not in raw:
        return {}
    out = {}
    is_html = '<td' in raw and 'grvHistory' in raw
    t = re.sub(r'<[^>]+>', ' ', raw).replace('&nbsp;', ' ').replace('&prime;', "'").replace('&ndash;', '–') if is_html else raw
    t = _clean(t)
    m = re.search(r'([^\n()<>]{3,60}?)\s*\((\d{6,10})\)', t)
    if m:
        out['name'], out['id'] = re.sub(r'\s+', ' ', m.group(1)).strip(), int(m.group(2))
    m = re.search(r'(\d{2}) years and (\d{1,3}) days', t)
    if m:
        out['age'], out['days'] = int(m.group(1)), int(m.group(2))
    m = re.search(r'Total Skill Index \(TSI\):?\s*(' + _NUM + ')', t)
    if m and m.group(1) != '-':
        out['tsi'] = float(_int(m.group(1)))
    w, wt, fo, rate = _wage_eur(t)
    if wt:
        out['wage_text'], out['foreign'], out['rate'] = wt, fo, rate
        if w:
            out['wage'] = round(w)
    m = re.search(r'Specialit?y:?\s*(\w+)', t)
    out['spec'] = m.group(1) if m and m.group(1) in SPECIALTIES else 'None'
    m = re.search(r'Last update:?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})', t)
    upd = m.group(1) if m else None
    hist = []
    if is_html:
        for rm in re.finditer(r'<tr>\s*<td>\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s*</td>(.*?)</tr>', raw, re.S):
            cells = dict((k, v) for k, v in re.findall(
                r'grvHistory_lbl(Form|StaminaSkill|Experience|TSI|Salary)_\d+"\s+title="([^"]*)"', rm.group(2)))
            row = dict(date=rm.group(1), form=_sint(cells.get('Form')), stam=_sint(cells.get('StaminaSkill')),
                       xp=_sint(cells.get('Experience')), tsi=_sint(cells.get('TSI')), salary=_sint(cells.get('Salary')))
            if row['tsi']:
                hist.append(row)
        m = re.search(r'PlayerForm_hplSkillLevel"\s+title="(\d+)"', raw)
        if m:
            out['form'] = int(m.group(1))
        m = re.search(r'StaminaSkill_hplSkillLevel"\s+title="(\d+)"', raw)
        if m:
            out['stamina'] = int(m.group(1))
        m = re.search(r'Expirience_hplSkillLevel"\s+title="(\d+)"', raw) or re.search(r'Experience_hplSkillLevel"\s+title="(\d+)"', raw)
        if m:
            out['xp'] = int(m.group(1))
    else:
        # copied text: tab-separated rows, newest first; the oldest row has full values, the rest show changes.
        # Only the "History" table (Date / Form / Stamina / ...): a tracker page also has the "Tracker skill
        # history" table with date rows, which must not be read as TSI history.
        hm = re.search(r'\n\s*Date\tForm[^\n]*\n', t)
        hist_text = t[hm.end():] if hm else ''
        rows = []
        for line in hist_text.splitlines():
            m = re.match(r'\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\t(.*)$', line)
            if not m:
                continue
            c = (m.group(2).split('\t') + [''] * 5)[:5]
            rows.append((m.group(1), c))
        if rows and all(_sint(v) is not None and not v.strip()[:1] in '+-' + _DASH for v in rows[-1][1][:4]):
            cur = [_sint(v) for v in rows[-1][1]]
            full = [(rows[-1][0], list(cur))]
            for d, c in reversed(rows[:-1]):
                for i, v in enumerate(c):
                    dv = _sint(v)
                    if dv is not None and cur[i] is not None:
                        cur[i] = cur[i] + dv
                full.append((d, list(cur)))
            for d, c in reversed(full):
                hist.append(dict(date=d, form=c[0], stam=c[1], xp=c[2], tsi=c[3], salary=c[4]))
    # The page's own text: current form, stamina and experience (more exact than adding up the history's changes)
    m = re.search(r'In ([a-z-]+)(?:\s*[+\-' + _DASH + r']\d)?\s+form,\s*([a-z-]+)(?:\s*[+\-' + _DASH + r']\d)?\s+stamina', t)
    if m and m.group(1) in LEVEL_WORDS and m.group(2) in LEVEL_WORDS:
        out['form'], out['stamina'] = LEVEL_WORDS[m.group(1)], LEVEL_WORDS[m.group(2)]
    m = re.search(r'Has ([a-z -]+?)(?:\s*[+\-' + _DASH + r']\d)?\s+experience', t)
    if m and m.group(1).strip() in LEVEL_WORDS:
        out['xp'] = LEVEL_WORDS[m.group(1).strip()]
    _tracker(t, out)
    if hist:
        day_first = any(int(re.match(r'(\d+)', h['date']).group(1)) > 12 for h in hist)
        for h in hist:
            h['date'] = _date(h['date'], day_first)
        out['history'] = hist
        out.setdefault('form', hist[0]['form'])
        out.setdefault('stamina', hist[0]['stam'])
        out.setdefault('xp', hist[0]['xp'])
        out['updated'] = _date(upd, day_first) if upd else hist[0]['date']
    else:
        day_first = False
    for k in ('tracker_date', 'training_date'):
        if out.get(k + '_text'):
            out[k] = _date(out[k + '_text'], day_first)
    return out if 'tsi' in out else {}


LEVEL_WORDS = {'non-existent': 0, 'disastrous': 1, 'wretched': 2, 'poor': 3, 'weak': 4, 'inadequate': 5, 'passable': 6,
               'solid': 7, 'excellent': 8, 'formidable': 9, 'outstanding': 10, 'brilliant': 11, 'magnificent': 12,
               'world class': 13, 'supernatural': 14, 'titanic': 15, 'extra-terrestrial': 16, 'mythical': 17,
               'magical': 18, 'utopian': 19, 'divine': 20}
_TRACK_SKILL = {'Keeper': 'GK', 'Defending': 'DE', 'Playmaking': 'PM', 'Winger': 'WI', 'Passing': 'Pas', 'Scoring': 'SC',
                'Set Pieces': 'SH'}
_POP_COLS = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']


def _tracker(t, out):
    """The tracker part of a Hattrick Portal page (players in a tracker): HTMS, skills with the Portal's sub-level
    estimate, the date the tracker saw them, the last training and the level-up history. Adds to out."""
    m = re.search(r'HTMS Points:\s*Ability:\s*(' + _NUM + r')\s*/\s*Potential:\s*(' + _NUM + ')', t)
    if m:
        out['htms'], out['htms28'] = float(_int(m.group(1))), float(_int(m.group(2)))
    sk = {}
    for m in re.finditer(r'\b(Keeper|Defending|Playmaking|Winger|Passing|Scoring|Set Pieces):\s*(\d{1,2})/20\s*(?:[A-Za-z][A-Za-z -]*[A-Za-z])?\s*([+-]\d+[.,]\d+)?', t):
        sub = float(m.group(3).replace(',', '.')) if m.group(3) else 0.0
        sk[_TRACK_SKILL[m.group(1)]] = (int(m.group(2)), sub)
    if len(sk) == 7:
        out['tracker_skills'] = sk
    m = re.search(r'Skills in the tracker \(on (\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\)', t)
    if m:
        out['tracker_date_text'] = m.group(1)
    m = re.search(r'Training was (\d{1,2}[/.-]\d{1,2}[/.-]\d{4})', t)
    if m:
        out['training_date_text'] = m.group(1)
    # level-up history: newest first; the oldest row has the full levels, the others +1 / +2 ...
    sm = re.search(r'Tracker skill history\s*\n(.*?)(?:\n\s*History\s*\n|$)', t, re.S)
    if sm:
        pops = []
        for line in sm.group(1).splitlines():
            m = re.match(r'\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\t(.*)$', line)
            if not m:
                continue
            cells = (m.group(2).split('\t') + [''] * 7)[:7]
            pops.append((m.group(1), {k: c.strip() for k, c in zip(_POP_COLS, cells) if c.strip()}))
        if pops:
            out['tracker_pops'] = pops


# ---------------------------------------------------------------- Hattrick player page: "Salaries" tab
_SAL = re.compile(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\s+(\d{1,3})\s+(\d{2})\s+(' + _NUM + r')\s*€?')


def parse_salaries(text):
    """The Salaries tab of a player's page (Date, Season, Age, Wage, +20%) -> {age: wage on that birthday, €, without
    the +20% abroad bonus}. One row per birthday; if an age shows twice (season change), the newest row counts."""
    out = {}
    for m in _SAL.finditer(_clean(text or '')):
        if m.group(6) == '-':
            continue
        age = int(m.group(5))
        if 16 <= age <= 45 and age not in out:
            out[age] = float(_int(m.group(6)))
    return out if len(out) >= 2 else {}


_SKILL_WORDS = {'Keeper': 'GK', 'Defending': 'DE', 'Playmaking': 'PM', 'Winger': 'WI', 'Passing': 'Pas',
                'Scoring': 'SC', 'Set Pieces': 'SH'}


def parse_page_skills(text):
    """Skill levels on a player page you can see the skills of (your own players): {'DE': 12, ...} or {}."""
    out = {}
    for line in _clean(text or '').splitlines():
        for word, key in _SKILL_WORDS.items():
            m = re.match(r'\s*' + word + r'\b[^\d\n]*?(\d{1,2})\s*$', line)
            if m:
                out[key] = int(m.group(1))
    return out if len(out) >= 5 else {}


def salary_abroad(info, salaries):
    """True / False when the paid wage on his page vs his last birthday wage shows the +20% abroad bonus; else None."""
    try:
        w, last = float(info.get('wage') or 0), float(salaries[max(salaries)])
    except (TypeError, ValueError, KeyError):
        return None
    if not w or not last:
        return None
    if abs(w / last - 1.2) < 0.01:
        return True
    if abs(w / last - 1.0) < 0.01:
        return False
    return None