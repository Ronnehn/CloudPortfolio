"""Expected stamina by age and stamina-training share (Hattrick Codex, giocatori.html, NRGJACK's tables).
Rows: stamina share 10-50%; columns: age 17-36. '7+' = upper part of solid (7), '8−' = lower part of excellent (8)."""
AGES = list(range(17, 37))
_ROWS = '''10|5 5+ 6− 6+ 7− 7+ 8− 8− 7+ 7 7− 6+ 6 6− 5+ 5 5 5− 4+ 4
11|5+ 6− 6+ 7− 7+ 8− 8 8− 7+ 7 7 7− 6+ 6 6− 5+ 5 5− 4+ 4
12|5+ 6− 6+ 7− 7+ 8− 8 8− 7+ 7 7 7− 6+ 6 6− 5+ 5 5 5− 4+
13|5+ 6− 6+ 7− 7+ 8− 8 8− 7+ 7 7 7− 6+ 6 6 6− 5+ 5 5− 4+
14|6− 6+ 7− 7+ 8− 8 8 8 8− 7+ 7 7 7− 6+ 6 6− 5+ 5 5− 4+
15|6 6+ 7− 7+ 8− 8 8 8 8− 7+ 7 7 7− 6+ 6 6 6− 5 5− 4+
16|6+ 7− 7 7+ 8− 8 8 8 8 8− 7+ 7 7− 6+ 6 6 6− 5+ 5− 4+
17|6+ 7− 7 7+ 8− 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6− 5+ 5 5−
18|7− 7 7+ 8− 8 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6− 5+ 5 5
19|7 7 7+ 8− 8 8 8 8 8 8 8− 7+ 7 7− 6+ 6 6 6− 5+ 5
20|7 7 7+ 8− 8 8 8 8 8 8 8− 7+ 7 7 6+ 6+ 6 6− 5+ 5
21|7 7 7+ 8− 8 8 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6− 5+ 5
22|7 7+ 8− 8 8 8 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6 6− 5+
23|7 7+ 8− 8 8 8 8 8 8 8 8− 7+ 7 7 7 7− 6+ 6 6− 5+
24|7 7+ 8− 8 8 8 8 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6− 5+
25|7 7+ 8− 8 8 8 8 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6− 5+
26|7+ 8− 8 8 8 8 8+ 8 8 8 8 8 8− 7+ 7 7− 6+ 6 6 6−
27|7+ 8− 8 8 8 8 8+ 8+ 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6
28|7+ 8− 8 8 8 8 8+ 8+ 8 8 8 8 8− 7+ 7 7 7− 6+ 6 6
29|8− 8 8 8 8 8 8+ 8+ 8 8 8 8 8 8− 7+ 7 7− 6+ 6 6
30|8 8 8 8 8 8+ 9− 8+ 8 8 8 8 8 8− 7+ 7 7− 6+ 6 6
31|8 8 8 8 8 8+ 9− 9− 8+ 8 8 8 8 8− 7+ 7 7 7− 6+ 6
32|8 8 8 8 8 8+ 9− 9− 8+ 8 8 8 8 8 8− 7+ 7 7− 6+ 6
33|8 8 8 8 8+ 9− 9 9 9− 8+ 8 8 8 8 8− 7+ 7 7− 6+ 6
34|8 8 8 8 8+ 9− 9 9 9− 8+ 8 8 8 8 8− 7+ 7 7− 6+ 6
35|8 8 8 8 8+ 9− 9 9 9 9− 8+ 8 8 8 8− 7+ 7 7 7− 6+
36|8 8 8 8+ 9− 9 9 9 9 9− 8+ 8 8 8 8− 7+ 7 7 7− 6+
37|8 8 8 8+ 9− 9 9 9 9 9− 8+ 8 8 8 8 8− 7+ 7 7− 6+
38|8 8 8 8+ 9− 9 9 9 9 9 9− 8+ 8 8 8 8− 7+ 7 7− 6+
39|8 8 8+ 9− 9 9 9 9 9 9 9− 8+ 8 8 8 8− 7+ 7 7 7−
40|8 8 8+ 9− 9 9 9 9 9 9 9− 8+ 8 8 8 8− 7+ 7 7 7
41|8 8 8+ 9− 9 9 9 9 9 9 9 9− 8+ 8 8 8 8− 7+ 7 7
42|8 8+ 9− 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8− 7+ 7 7
43|8 8+ 9− 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8 8− 7+ 7
44|8 8+ 9− 9 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8− 7+ 7
45|8+ 9− 9 9 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8 8− 7+
46|8+ 9− 9 9 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8 8− 7+
47|8+ 9− 9 9 9 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8 8−
48|9− 9 9 9 9 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8 8
49|9 9 9 9 9 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8 8
50|9 9 9 9 9 9 9 9 9 9 9 9 9 9 9− 8+ 8 8 8 8'''
TABLE = {int(r.split('|')[0]): r.split('|')[1].split() for r in _ROWS.split('\n')}
WORDS = {4: 'weak', 5: 'inadequate', 6: 'passable', 7: 'solid', 8: 'excellent', 9: 'formidable'}


def expected_stamina(age, share):
    """('7+', 7, '+') for this age and stamina share (shares below 10 use 10, above 50 use 50)."""
    a = min(max(int(age), AGES[0]), AGES[-1])
    s = min(max(int(round(float(share))), 10), 50)
    code = TABLE[s][AGES.index(a)]
    lvl = int(code[0]); mod = code[1:] if len(code) > 1 else ''
    return code, lvl, mod


def stamina_text(code):
    lvl = int(code[0]); mod = code[1:]
    w = WORDS.get(lvl, str(lvl))
    return w + (' (high)' if mod == '+' else ' (low)' if mod in ('−', '-') else '')


def share_for(age, target_level):
    """Smallest stamina share that keeps him at (at least) this level at this age, or None above 50%."""
    for s in range(10, 51):
        code, lvl, mod = expected_stamina(age, s)
        if lvl > target_level or (lvl == target_level and mod != '−'):
            return s
    return None