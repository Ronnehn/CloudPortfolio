# ==============================================================================
# Health check of the Reference Database (players with real skills only):
#   - extra copies of the same player (same name, age, days and TSI)
#   - wage lower than his skills earn (22+; younger players train fast on a low wage until their birthday)
#   - wage that only fits with the other "abroad" setting
#   - TSI that his skills can't give at any form/stamina (or only at form 1)
#   - position that the position rules would set differently (fix with "Re-check positions")
# Players in your roster or watchlists are skipped: they are the ones still to be solved.
# ==============================================================================
import json
import datetime as dt
import pandas as pd

SK7 = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
K5 = ['DE', 'PM', 'WI', 'Pas', 'SC']


def is_real(r):
    try:
        v = [float(r.get(k)) for k in SK7]
    except (TypeError, ValueError):
        return False
    return all(x >= 1 and x == int(x) for x in v[1:6]) and [int(x) for x in v] != [1, 5, 5, 5, 4, 5, 1]


def _num(v, d=0.0):
    try:
        f = float(v)
        return d if f != f else f
    except (TypeError, ValueError):
        return d


def _form_needed(H, age, tsi, sk):
    """Form (stamina ~8) at which these whole levels (middle of each level) give this TSI; None = no form can."""
    mid = [s + 0.5 if (i > 0 or s > 1) else s for i, s in enumerate(sk[:6])]
    for c in (8.5, 7.5, 9.5, 6.5, 5.5):
        f = lambda x: H.calculate_tsi_for_form(age, x, c, *mid) - tsi
        lo, hi = 1.01, 8.99
        if f(lo) > 0 or f(hi) < 0:
            continue
        for _ in range(30):
            m = (lo + hi) / 2
            lo, hi = (lo, m) if f(m) > 0 else (m, hi)
        return (lo + hi) / 2
    return None


def check_reference(df, skip_names=(), skip_ids=()):
    """-> (rows, copy_ids, n_checked, n_skipped). rows: [dict(id, Player, Pos, Age, Source, Problem, kinds)]."""
    import ht_engine as H
    skip_n = {str(n).strip().lower() for n in skip_names if str(n).strip()}
    skip_i = {int(i) for i in skip_ids if _num(i) > 0}
    out, copy_ids, n_checked, n_skipped = [], [], 0, 0
    seen = {}
    d = df.sort_values('id') if 'id' in df.columns else df
    for _, r in d.iterrows():
        name = str(r.get('Speler') or '').strip()
        if name.lower() in skip_n or int(_num(r.get('PlayerID'))) in skip_i:
            n_skipped += 1
            continue
        if not is_real(r):
            continue
        n_checked += 1
        age, days = int(_num(r.get('Leeftijd'))), int(_num(r.get('dag(en)')))
        tsi, wage = _num(r.get('TSI')), _num(r.get('Loon'))
        spec = r.get('Specialiteit') if isinstance(r.get('Specialiteit'), str) else 'None'
        sk = [_num(r.get(k), 1.0) for k in SK7]
        probs, kinds, abroad_to = [], [], None
        key = (name.lower(), age, days, round(tsi))
        if key in seen:
            copy_ids.append(int(r['id']))
            probs.append(f"extra copy of #{seen[key]}")
            kinds.append('copy')
        else:
            seen[key] = int(r['id'])
        if tsi > 0 and wage > 0:
            lo = H.calculate_exact(age, days, spec, 6.5, 7.5, *sk)[3]
            hi = H.calculate_exact(age, days, spec, 6.5, 7.5, *[v + 0.999 if (i > 0 or v > 1) else v for i, v in enumerate(sk)])[3]
            ab = int(_num(r.get('Foreign'))) == 1

            def fits(fx):
                return lo * fx * 0.97 <= wage <= hi * fx * (1.10 if age >= 28 else 1.03) or \
                    (age < 28 and lo * fx * 0.80 <= wage <= hi * fx * 1.03)
            if not fits(1.2 if ab else 1.0):
                if fits(1.0 if ab else 1.2):
                    probs.append('wage only fits if ' + ('NOT abroad' if ab else 'abroad'))
                    kinds.append('abroad')
                    abroad_to = 0 if ab else 1
                elif age > 21 and wage < lo * (1.2 if ab else 1.0) * 0.97:
                    probs.append(f"wage €{wage:,.0f} is below what these skills earn (≥ €{lo * (1.2 if ab else 1.0):,.0f})")
                    kinds.append('wage')
            fn = _form_needed(H, age, tsi, sk)
            if fn is None:
                probs.append("TSI can't come from these skills at any form")
                kinds.append('tsi')
            elif fn < 2.0:
                probs.append(f"TSI only fits at form {fn:.1f}")
                kinds.append('tsi')
        try:
            new = H.infer_position_from_skills(*sk[:6], spec=spec, sh=sk[6])
            old = str(r.get('Positie') or '')
            if new and new != old and not ({new, old} <= {'DFW', 'TDFW'}) and not ({new, old} <= {'OIM-Q', 'OIM-H'}):
                probs.append(f"skills look like {new}")
                kinds.append('position')
        except Exception:
            pass
        if probs:
            out.append(dict(id=int(r['id']), Player=name, Pos=str(r.get('Positie') or ''), Age=age,
                            Source=str(r.get('source') or ''), Problem='; '.join(probs), kinds=kinds,
                            abroad_to=abroad_to, was_abroad=int(_num(r.get('Foreign')))))
    return out, copy_ids, n_checked, n_skipped


def delete_with_backup(ids):
    """Delete reference rows, keeping a copy in reference_backup. Returns the batch name (for undo)."""
    from data_layer import get_db_connection, get_reference_players_df
    ids = [int(i) for i in ids]
    if not ids:
        return None
    batch = 'dedupe-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d%H%M%S')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS reference_backup (id INTEGER PRIMARY KEY AUTOINCREMENT, batch TEXT NOT NULL, '
                'ref_id INTEGER NOT NULL, data_json TEXT, saved_at TEXT);')
    cols = [d[0] for d in cur.execute('SELECT * FROM reference_players LIMIT 0;').description]
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    for k in range(0, len(ids), 200):
        part = ids[k:k + 200]
        rows = cur.execute(f'SELECT * FROM reference_players WHERE id IN ({",".join("?" * len(part))});', part).fetchall()
        for row in rows:
            rec = dict(zip(cols, row))
            cur.execute('INSERT INTO reference_backup (batch, ref_id, data_json, saved_at) VALUES (?, ?, ?, ?);',
                        (batch, int(rec['id']), json.dumps(rec, default=str), now))
        cur.execute(f'DELETE FROM reference_players WHERE id IN ({",".join("?" * len(part))});', part)
    conn.commit()
    conn.close()
    try:
        get_reference_players_df.clear()
    except Exception:
        pass
    return batch


def restore_batch(batch):
    """Put the rows of a delete_with_backup batch back (same ids). Returns how many."""
    from data_layer import get_db_connection, get_reference_players_df
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute('SELECT data_json FROM reference_backup WHERE batch=?;', (batch,)).fetchall()
    cols = [d[0] for d in cur.execute('SELECT * FROM reference_players LIMIT 0;').description]
    n = 0
    for (js,) in rows:
        rec = {k: v for k, v in json.loads(js).items() if k in cols}
        ks = list(rec)
        cur.execute(f'INSERT OR REPLACE INTO reference_players ({", ".join(chr(34) + k + chr(34) for k in ks)}) '
                    f'VALUES ({", ".join("?" * len(ks))});', [rec[k] for k in ks])
        n += 1
    cur.execute('DELETE FROM reference_backup WHERE batch=?;', (batch,))
    conn.commit()
    conn.close()
    try:
        get_reference_players_df.clear()
    except Exception:
        pass
    return n


def skip_lists(user):
    """Names and player IDs in this user's roster and watchlists (these are skipped: they still need solving)."""
    try:
        from data_layer import load_user_db, get_watchlists
        ros = load_user_db(user)
        names = list(ros['Speler'].astype(str)) if 'Speler' in ros.columns else []
        ids = list(pd.to_numeric(ros.get('PlayerID', pd.Series(dtype=float)), errors='coerce').fillna(0).astype(int))
        for lst in (get_watchlists(user) or {}).values():
            names += list(lst)
        return names, ids
    except Exception:
        return [], []


def is_skipped(r, names, ids):
    n = {str(x).strip().lower() for x in names}
    return str(r.get('Speler') or '').strip().lower() in n or int(_num(r.get('PlayerID'))) in {int(i) for i in ids if _num(i) > 0}