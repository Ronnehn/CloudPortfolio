import io
import warnings
import pandas as pd
from nicegui import ui, app, run
from shell import apply_theme, require_login, render_sidebar, ACCENT, tt_card, page_title
from data_layer import archive_player_rows
from data_layer import (
    read_uploaded_csv, import_nt_players_csv, get_db_connection, load_user_db,
    add_players_to_reference_db, get_reference_players_count, get_richtskills_for_age,
    generate_hattrick_csv_template, generate_app_csv_template, generate_htp_csv_template,
    get_watchlists, create_watchlist, add_to_watchlist,
)
from ht_engine import (
    parse_hrf_to_dataframe, SPECIALITY_OPTIONS, infer_position_from_skills,
    calculate_exact, calculate_tsi_for_form, estimate_htms_from_profile, profile_shape_solution,
    auto_solve_subskills, healthy_tsi, normalize_nationality,
    match_slot, slot_fits_position, MATCH_SLOT_DEFAULT, LAST_MATCH_MAX_AGE_DAYS,
)
from richtskills_data import RICHTSKILLS_DEFAULT
try:   # Hattrick specialty icons
    import spec_icons as SI
except ImportError:
    SI = None

POSITION_OPTIONS = list(RICHTSKILLS_DEFAULT.keys())

# Columns actually written to the skills_data table for this user.
DB_COLS = ['username', 'PlayerID', 'Speler', 'Positie', 'Leeftijd', 'dag(en)', 'Specialiteit',
           'Vorm', 'Conditie', 'Ervaring', 'TSI', 'Loon', 'Leiderschap', 'Nationality',
           'Injuries', 'Transfer-listed', 'HTMS', 'HTMS28', 'HTMS_est', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']

# What we show in the review table (kept compact — full data still travels with each row).
DISPLAY_COLS = ['Status', 'Data', 'Speler', 'Positie', 'Played', 'Leeftijd', 'Specialiteit', 'Nationality',
                'Vorm', 'Conditie', 'TSI', 'TSI Δ', 'Loon', 'HTMS', 'HTMS28', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
COL_LABELS = {'Played': 'Last match', 'Vorm': 'Form', 'Conditie': 'Stamina', 'Loon': 'Wage', 'TSI Δ': 'TSI Δ (vs roster)'}

# Updating players already in the roster: a field the file doesn't contain keeps the roster's value.
KEEP_GROUPS = [('Positie', ['Positie'], 'Pos'), ('Loon', ['Loon'], 'Wage'),
               ('skills', ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH'], 'Skills'),
               ('HTMS', ['HTMS', 'HTMS28', 'HTMS_est'], 'HTMS'), ('Ervaring', ['Ervaring'], 'XP'),
               ('Leiderschap', ['Leiderschap'], 'LS'), ('Specialiteit', ['Specialiteit'], 'Spec'),
               ('Nationality', ['Nationality'], 'Nat'), ('Injuries', ['Injuries'], 'Inj'),
               ('Transfer-listed', ['Transfer-listed'], 'TL'), ('Vorm', ['Vorm'], 'Form'),
               ('Conditie', ['Conditie'], 'Stamina'), ('Leeftijd', ['Leeftijd'], 'Age'), ('dag(en)', ['dag(en)'], 'Days')]

EDIT_NUM_FIELDS = ['TSI', 'Loon', 'HTMS', 'HTMS28']
EDIT_SKILL_FIELDS = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
MISSING_LABELS = {'Positie': 'Pos', 'TSI': 'TSI', 'Loon': 'Wage', 'skills': 'Skills'}


# ── Auto-calculate helpers ───────────────────────────────────────────────────
def _f(v, default):
    try:
        v = float(v)
        return default if pd.isna(v) else v
    except (TypeError, ValueError):
        return default


def missing_set(row):
    """Fields the uploaded file did NOT supply (placeholder values in the row)."""
    return {m for m in str(row.get('_missing', '') or '').split(',') if m}


def data_badge(row):
    labels = [MISSING_LABELS[m] for m in MISSING_LABELS if m in missing_set(row)]
    kept = row.get('_kept') or ''
    if kept and not labels:
        return f'✓ file + roster ({kept})'
    if not labels:
        return '✓ file'
    return ('🧮 est. ' if row.get('_auto') else '⚠️ missing ') + ', '.join(labels)


def _slot_of(row):
    """Last-match slot as text, or None (a player without a last match comes in as NaN)."""
    v = row.get('_lm_slot')
    return v if isinstance(v, str) and v.strip() else None


def last_match_recent(row):
    """True when the last match is recent enough to say something about the player's position now."""
    d = row.get('_lm_date')
    if d is None or (isinstance(d, float) and pd.isna(d)) or not d:
        return True          # no date in the file: assume it's current
    try:
        _ts = pd.to_datetime(d, errors='coerce')
        if pd.isna(_ts):
            return True
        return (pd.Timestamp.now().normalize() - _ts).days <= LAST_MATCH_MAX_AGE_DAYS
    except (TypeError, ValueError):
        return True


def position_mismatch(row):
    """True when the player last played in a slot his stored position doesn't normally play
    (e.g. stored as NFW, played IM). Old matches and positions taken from the match don't count."""
    slot = _slot_of(row)
    if not slot or row.get('_pos_from_match') or not last_match_recent(row):
        return False
    rating = row.get('_lm_rating')
    if rating is not None and not pd.isna(rating) and float(rating) <= 0:
        return False
    return not slot_fits_position(slot, row.get('Positie'))


def played_badge(row):
    """'IM · 10★ · 17-10' plus a hint: ⚠️ when it doesn't fit the stored position,
    → NIM when the position was taken from the match, 🕰 when the match is old."""
    slot = _slot_of(row)
    if not slot:
        return ''
    parts = [slot]
    rating = row.get('_lm_rating')
    if rating is not None and not pd.isna(rating):
        parts.append(f'{float(rating):g}★')
    d = row.get('_lm_date')
    # an empty "Last match date" (e.g. a youth player who never played) comes in as NaN / NaT
    _ts = pd.to_datetime(d, errors='coerce') if d is not None and not (isinstance(d, float) and pd.isna(d)) else pd.NaT
    if not pd.isna(_ts):
        parts.append(_ts.strftime('%d-%m-%y'))
    txt = ' · '.join(parts)
    if row.get('_pos_from_match'):
        return f'{txt} → {row.get("Positie")}'
    if not last_match_recent(row):
        return f'🕰 {txt}'
    return f'⚠️ {txt}' if position_mismatch(row) else txt


def _solve_scale(fn, target, lo=0.05, hi=3.0):
    """Bisection for k where fn(k) ≈ target (fn is non-decreasing in k)."""
    if fn(hi) <= target:
        return hi, True
    if fn(lo) >= target:
        return lo, True
    for _ in range(50):
        mid = (lo + hi) / 2
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, False


def auto_estimate(vals, missing, ref_df=None):
    """Fill placeholder values with estimates that are consistent with each other.

    - Skills known, position missing → position inferred from the skills.
    - Skills missing → the position's age/country target profile (Config page),
      scaled so the calculated TSI matches the real TSI (or the wage if no TSI).
    - TSI / wage / HTMS / HTMS28 missing → calculated from the (estimated) skills
      with the same formulas the Estimator uses.
    Only fields in `missing` are overwritten. Returns (updates, note) or (None, error).
    """
    age = int(_f(vals.get('Leeftijd'), 20))
    days = int(_f(vals.get('dag(en)'), 0))
    spec = vals.get('Specialiteit') or 'None'
    form = min(8.0, max(1.0, _f(vals.get('Vorm'), 6.0)))
    cond = min(9.0, max(1.0, _f(vals.get('Conditie'), 6.0)))
    nat = vals.get('Nationality') or 'Netherlands'
    pos = vals.get('Positie')
    skills = {sk: _f(vals.get(sk), 1.0) for sk in EDIT_SKILL_FIELDS}
    updates, notes = {}, []

    if 'skills' not in missing:
        if 'Positie' in missing or pos not in RICHTSKILLS_DEFAULT:
            pos = infer_position_from_skills(*[skills[s] for s in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC']], spec,
                                             sh=skills.get('SH'))
            updates['Positie'] = pos
            notes.append(f'position inferred from skills → {pos}')
    else:
        if 'Positie' in missing or pos not in RICHTSKILLS_DEFAULT:
            return None, 'Pick the Position first — this file has no skills to infer it from.'
        bench = get_richtskills_for_age(nat, age, spec=spec).get(pos) or RICHTSKILLS_DEFAULT[pos]

        def profile(k):
            return {sk: round(min(25.0, max(1.0, 1.0 + (float(bench.get(sk, 1.0)) - 1.0) * k)), 2)
                    for sk in EDIT_SKILL_FIELDS}

        tsi = _f(vals.get('TSI'), 0.0) if 'TSI' not in missing else 0.0
        tsi = healthy_tsi(tsi, _f(vals.get('Injuries'), 0.0))   # injured: Hattrick shows a lowered TSI
        wage = _f(vals.get('Loon'), 0.0) if 'Loon' not in missing else 0.0
        if tsi > 0 and wage > 0:
            # Same as Auto-Solver option 1 (trained since the birthday, profile-guided).
            res, _ = auto_solve_subskills(
                tsi, wage, 0, 0, age, days, spec, form, cond, pos,
                get_richtskills_for_age(nat, age, spec=spec), True, True, None,
                bool(_f(vals.get('Foreign'), 0)), None, ref_df, default_only=True,
                exclude_player=(vals.get('PlayerID'), vals.get('Speler')))
            skills = {sk: round(float(res[0][sk]), 3) for sk in EDIT_SKILL_FIELDS}
            how = 'Auto-Solver option 1'
        elif tsi > 0 or wage > 0:
            # Only TSI or only wage: profile shape fitted to whichever is known.
            ps = profile_shape_solution(pos, age, days, spec, form, cond, tsi, wage,
                                        bool(_f(vals.get('Foreign'), 0)), bench)
            skills = {sk: round(float(ps[sk]), 3) for sk in EDIT_SKILL_FIELDS}
            how = ' + '.join(x for x in (f'TSI {tsi:,.0f}' if tsi > 0 else '',
                                         f'wage {wage:,.0f}' if wage > 0 else '') if x)
        else:
            skills, how = profile(1.0), 'no TSI or wage to fit'
        updates.update(skills)
        notes.append(f'skills = {how}' if how == 'Auto-Solver option 1' else f'skills = {pos} age-{age} profile shape fitted to {how}')

    res = calculate_exact(age, days, spec, form, cond, *[skills[s] for s in EDIT_SKILL_FIELDS])
    if 'TSI' in missing:
        updates['TSI'] = int(round(res[1]))
        notes.append(f"TSI calculated → {updates['TSI']:,}")
    if 'Loon' in missing:
        updates['Loon'] = int(round(res[3]))
        notes.append(f"wage calculated → {updates['Loon']:,}")
    if 'HTMS' in missing:
        if 'skills' in missing and (_f(vals.get('TSI'), 0) > 0 or _f(vals.get('Loon'), 0) > 0):
            # The skills are only the position profile scaled to TSI, and HTMS counts whole
            # levels, so their HTMS was the same for a whole position (e.g. 853 for every U21
            # keeper). Use the per-player estimate from TSI + wage instead, marked as estimate.
            est_h, est_h28, _ = estimate_htms_from_profile(
                age, days, _f(vals.get('TSI'), 0), _f(vals.get('Loon'), 0), form, cond,
                spec=spec, pos_code=pos, exclude_player=(vals.get('PlayerID'), vals.get('Speler')))
            updates['HTMS'] = int(est_h)
            updates['HTMS28'] = int(est_h28)
            updates['HTMS_est'] = 1
            notes.append(f'HTMS estimated → {int(est_h)} (estimate, not real)')
        else:
            updates['HTMS'] = int(res[5])
            updates['HTMS28'] = int(round(res[6]))
            updates['HTMS_est'] = 1 if 'skills' in missing else 0
    if not notes:
        return {}, 'Nothing to calculate — every value came from the file.'
    return updates, '; '.join(notes)


@ui.page('/import')
def import_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    render_sidebar(user, '/import')

    with ui.column().classes('w-full max-w-6xl mx-auto p-2 md:p-4'):
        page_title('/import')

        state = {'rows': []}
        preview_card = ui.column().classes('w-full')

        # ── Step 1: Upload ──────────────────────────────────────────────────
        def make_row_id(row, idx):
            try:
                pid = int(row.get('PlayerID', 0) or 0)
            except (TypeError, ValueError):
                pid = 0
            return f'pid_{pid}' if pid else f'row_{idx}_{str(row.get("Speler", ""))}'

        def parse_upload(content, filename):
            fname = filename.lower()
            if fname.endswith('.hrf'):
                buf = io.BytesIO(content)
                buf.name = filename
                return parse_hrf_to_dataframe(buf, user)
            elif fname.endswith('.xlsx'):
                raw = pd.read_excel(io.BytesIO(content))
                return import_nt_players_csv(raw, user)
            else:
                buf = io.BytesIO(content)
                buf.name = filename
                return import_nt_players_csv(read_uploaded_csv(buf), user)

        async def handle_upload(e):
            try:
                content = await e.file.read()
                df = parse_upload(content, e.file.name)
                if df.empty:
                    ui.notify('⚠️ No valid player rows found in that file.', type='warning')
                    return

                rows = []
                rate = wage_rate()
                for idx, r in df.reset_index(drop=True).iterrows():
                    row = r.to_dict()
                    if 'Loon' in row and pd.notna(row['Loon']):
                        row['_wage_raw'] = float(row['Loon'])        # as in the file
                        row['Loon'] = float(row['Loon']) * rate      # in euro
                    for numcol in ['TSI', 'Loon', 'HTMS', 'HTMS28'] + EDIT_SKILL_FIELDS:
                        if numcol in row and pd.notna(row[numcol]):
                            row[numcol] = round(float(row[numcol]), 2)
                    if 'Leeftijd' in row and pd.notna(row['Leeftijd']):
                        row['Leeftijd'] = int(row['Leeftijd'])
                    row['_row_id'] = make_row_id(row, idx)
                    row['Data'], row['Played'] = data_badge(row), played_badge(row)
                    rows.append(row)

                # Recognise players already in the roster (by PlayerID, else by name). For those,
                # fields the file doesn't contain keep the roster's value (wage, position, skills…),
                # and the TSI change since the last import is shown.
                present = df.attrs.get('present')          # None (e.g. HRF): the file is complete
                try:
                    roster = load_user_db(user)
                except Exception:
                    roster = pd.DataFrame()
                by_id, by_name = {}, {}
                if roster is not None and not roster.empty:
                    for _, pr in roster.iterrows():
                        rec = pr.to_dict()
                        try:
                            rid = int(float(rec.get('PlayerID') or 0))
                        except (TypeError, ValueError):
                            rid = 0
                        if rid:
                            by_id[rid] = rec
                        by_name[str(rec.get('Speler', '')).strip().lower()] = rec
                n_upd = 0
                for row in rows:
                    try:
                        rid = int(float(row.get('PlayerID') or 0))
                    except (TypeError, ValueError):
                        rid = 0
                    prev = by_id.get(rid) if rid else None
                    if prev is None:
                        prev = by_name.get(str(row.get('Speler', '')).strip().lower())
                    if prev is None:
                        row['Status'], row['TSI Δ'] = '🆕 new', ''
                        continue
                    n_upd += 1
                    row['Status'] = '♻️ update'
                    old_tsi = float(prev.get('TSI') or 0)
                    row['TSI Δ'] = f"{float(row.get('TSI') or 0) - old_tsi:+,.0f}" if old_tsi > 0 else ''
                    if not rid and prev.get('PlayerID'):
                        row['PlayerID'] = prev.get('PlayerID')
                    if present is not None:
                        kept = []
                        miss = missing_set(row)
                        for field, cols_, label in KEEP_GROUPS:
                            # In the file AND filled in for this player: use the file's value.
                            # (A column only some rows fill, e.g. wage for new players, doesn't
                            # wipe the roster value of the others.)
                            if field in present and field not in miss:
                                continue
                            vals = {c: prev.get(c) for c in cols_}
                            if all(v is None or (isinstance(v, float) and pd.isna(v)) for v in vals.values()):
                                continue
                            if field == 'Positie' and not str(vals['Positie'] or '').strip():
                                continue
                            if field == 'Loon' and not float(vals['Loon'] or 0) > 0:
                                continue
                            if field == 'HTMS' and not float(vals['HTMS'] or 0) > 0:
                                continue
                            row.update({c: (round(float(v), 2) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                                        for c, v in vals.items() if v is not None})
                            if field == 'Loon':
                                row['_wage_raw'] = None     # roster wage is already in euro
                            miss.discard(field)
                            kept.append(label)
                        row['_missing'] = ','.join(sorted(miss))
                        row['_kept'] = ', '.join(kept)
                        row['Data'], row['Played'] = data_badge(row), played_badge(row)

                # Last match: no position in the file or roster -> start from the slot he last played
                # (IM -> NIM, W -> NW, ...; editable). Otherwise: flag a slot that doesn't fit.
                n_from_match, mismatched = 0, []
                for row in rows:
                    slot = _slot_of(row)
                    if slot and 'Positie' in missing_set(row) and last_match_recent(row):
                        row['Positie'] = MATCH_SLOT_DEFAULT[slot]
                        row['_pos_from_match'] = True
                        miss = missing_set(row)
                        miss.discard('Positie')
                        row['_missing'] = ','.join(sorted(miss))
                        n_from_match += 1
                    row['Data'], row['Played'] = data_badge(row), played_badge(row)
                    if position_mismatch(row):
                        mismatched.append(f"{row.get('Speler', '')} ({row.get('Positie')}, played {slot})")

                state['rows'] = rows
                if mismatched:
                    ui.notify(f'⚠️ {len(mismatched)} player(s) last played outside their stored position: '
                              + ', '.join(mismatched[:4]) + (' …' if len(mismatched) > 4 else '')
                              + '. Check the Last match column.', type='warning', timeout=9000, multi_line=True)
                if n_from_match:
                    ui.notify(f'📍 {n_from_match} player(s) without a position: taken from their last match '
                              '(e.g. IM → NIM). Check with ✏️ before importing.', type='info', timeout=7000)
                if n_upd:
                    ui.notify(f'♻️ {n_upd} of {len(rows)} players are already in your roster: they will be updated.',
                              type='info', timeout=6000)
                ui.notify(f'✅ Parsed {len(rows)} players from {e.file.name}. Review below before importing.',
                          type='positive', timeout=5000)
                render_preview.refresh()
            except Exception as ex:
                ui.notify(f'Import Error: {ex}', type='negative')

        # Currency of the wages in the file. Default templates and manual entries are in euro;
        # HTP, HRF or other exports can use another currency.
        CUR_EUR, CUR_USD, CUR_SEK = '€ Euro', '$ US Dollar', 'kr Swedish krona (Hattrick base unit, ÷10)'
        # Hattrick's own unit is the Swedish krona: 1 € = 10 kr. The dollar is taken as 1:1 with
        # the euro (Hattrick's baseline); change WAGE_RATES['$'] if your files say otherwise.
        WAGE_RATES = {CUR_EUR: 1.0, CUR_USD: 1.0, CUR_SEK: 0.1}

        def wage_rate():
            return WAGE_RATES.get(cur_select.value, 1.0)

        def reapply_currency(_=None):
            # Changing the currency after uploading converts the parsed wages again.
            if not state.get('rows'):
                return
            rate = wage_rate()
            for row in state['rows']:
                if row.get('_wage_raw') is not None:
                    row['Loon'] = round(row['_wage_raw'] * rate, 2)
            render_preview.refresh()

        with tt_card('1️⃣ Upload File'):
            with ui.row().classes('w-full items-end gap-3 mb-2'):
                cur_select = ui.select([CUR_EUR, CUR_USD, CUR_SEK], value=CUR_EUR,
                                       label='Wages in this file are in').classes('w-80')
            cur_select.on_value_change(reapply_currency)
            ui.upload(label='Upload Roster (.csv, .xlsx or .hrf)', on_upload=handle_upload, auto_upload=True) \
                .props('accept=".csv,.xlsx,.hrf"').classes('w-full')

            with ui.expansion('📄 Need a template?', icon='description').classes('w-full mt-2'):
                with ui.row().classes('gap-2 flex-wrap mt-1'):
                    ui.button('Default Hattrick CSV',
                              on_click=lambda: ui.download(generate_hattrick_csv_template(), 'default_hattrick.csv')
                              ).props('outline size=sm')
                    ui.button('App Template CSV (POS/WAGE)',
                              on_click=lambda: ui.download(generate_app_csv_template(), 'app_template.csv')
                              ).props('outline size=sm')
                    ui.button('HTP CSV Template',
                              on_click=lambda: ui.download(generate_htp_csv_template(), 'Template_HTP.csv')
                              ).props('outline size=sm')

        # ── Step 2: Review / edit / select ──────────────────────────────────
        @ui.refreshable
        def render_preview():
            preview_card.clear()
            if not state['rows']:
                with preview_card:
                    ui.label('No file uploaded yet — upload a roster file above to see a preview here.') \
                        .classes('text-gray-500 text-sm')
                return

            with preview_card:
                with tt_card(f"2️⃣ Review Import — {len(state['rows'])} players parsed"):
                    with ui.row().classes('w-full justify-end items-center mb-2 flex-wrap gap-2'):
                        add_ref_cb = ui.switch('🗄️ Also add to Reference Database', value=True).props('dense')

                    # Optionally put the imported players on a watchlist (existing or new).
                    NO_LIST, NEW_LIST = '— no watchlist —', '➕ New watchlist…'
                    try:
                        existing_lists = sorted(n for n in get_watchlists(user) if n != '__EMPTY__')
                    except Exception:
                        existing_lists = []
                    with ui.row().classes('w-full items-center gap-2 mb-2 flex-wrap'):
                        wl_select = ui.select([NO_LIST] + existing_lists + [NEW_LIST], value=NO_LIST,
                                              label='📋 Also add to watchlist').classes('w-64')
                        wl_new = ui.input('New watchlist name').classes('w-56')
                        wl_new.bind_visibility_from(wl_select, 'value', backward=lambda v: v == NEW_LIST)
                        # Club import: players of another nationality than the club's country are foreign
                        # (+20% wage). Leave it on "not a club import" for NT / U21 lists: there it can't be told.
                        NO_CLUB = '— not a club import —'
                        try:
                            from ht_engine import COUNTRY_LIST as _CL
                        except Exception:
                            _CL = []
                        club_sel = ui.select([NO_CLUB] + list(_CL), value=NO_CLUB, with_input=True,
                                             label="🏟️ My club's country").classes('w-64') \
                            .tooltip('Club import: every player from another country gets the foreign flag (+20% wage), '
                                     'the others not. Not for NT / U21 lists.')

                    ui.label('Uncheck any players you don\'t want to import. Click ✏️ to correct a row before importing.') \
                        .classes('text-xs text-gray-400 mb-2')

                    # Edit button pinned as the FIRST column (right after the checkbox) and kept
                    # stuck to the left edge while scrolling, so it's always reachable without
                    # having to scroll all the way across the skill columns to find it.
                    ui.add_head_html('''
                        <style>
                        .import-edit-col { position: sticky !important; left: 0; z-index: 2;
                                            background-color: #1C1C24 !important; }
                        .import-edit-col.q-table--col-auto-width { z-index: 3; }
                        </style>
                    ''')

                    cols = [{'name': 'edit', 'label': '', 'field': 'edit',
                             'classes': 'import-edit-col', 'headerClasses': 'import-edit-col'}] \
                        + [{'name': c, 'label': COL_LABELS.get(c, c), 'field': c, 'align': 'left'} for c in DISPLAY_COLS]

                    with ui.element('div').classes('w-full overflow-x-auto'):
                        table = ui.table(
                            columns=cols, rows=state['rows'], row_key='_row_id', selection='multiple',
                        ).classes('w-full').props('dense flat')
                        # NiceGUI stores table rows as its own *copies* (observable dicts),
                        # so edits to the original list never reached the table. Point
                        # state['rows'] at the table's own rows so every edit shows up.
                        state['rows'] = table.rows
                        table.selected = state['rows'][:]  # everything included by default

                        table.add_slot('body-cell-edit', '''
                            <q-td :props="props" class="import-edit-col">
                                <q-btn icon="edit" flat dense round size="sm" color="primary"
                                       @click="() => $parent.$emit('edit_row', props.row)" />
                            </q-td>
                        ''')

                    sel_label = ui.label(f"{len(table.selected)} of {len(state['rows'])} players selected for import") \
                        .classes('text-xs text-gray-400 mt-2')

                    def on_selection(e):
                        sel_label.set_text(f"{len(table.selected)} of {len(state['rows'])} players selected for import")
                    table.on('selection', on_selection)

                    with ui.row().classes('gap-2 mt-2'):
                        def sel_all():
                            table.selected = state['rows'][:]
                            sel_label.set_text(f"{len(table.selected)} of {len(state['rows'])} players selected for import")
                        def sel_none():
                            table.selected = []
                            sel_label.set_text(f"0 of {len(state['rows'])} players selected for import")
                        ui.button('Select All', on_click=sel_all).props('outline sm')
                        ui.button('Select None', on_click=sel_none).props('outline sm')

                        async def bulk_auto_calc():
                            selected_ids = {r.get('_row_id') for r in table.selected}
                            done, skipped = 0, 0
                            ref_df = _ref_df()
                            todo = [r for r in state['rows'] if r.get('_row_id') in selected_ids
                                    and (missing_set(r) & set(MISSING_LABELS))]
                            for i, row in enumerate(todo, 1):
                                missing = missing_set(row)
                                progress_label.set_text(f'🧮 Calculating {i}/{len(todo)}: {row.get("Speler", "")}…')
                                updates, _note = await run.io_bound(auto_estimate, dict(row), missing, ref_df)
                                if updates is None:
                                    skipped += 1
                                    continue
                                row.update(updates)
                                row['_auto'] = True
                                row['Data'], row['Played'] = data_badge(row), played_badge(row)
                                done += 1
                            progress_label.set_text('')
                            table.update()
                            msg = f'🧮 Auto-calculated {done} player(s).'
                            if skipped:
                                msg += f' {skipped} skipped — set their Position via ✏️ first (no skills in file).'
                            ui.notify(msg, type='positive' if done else 'warning', timeout=6000)
                        ui.button('🧮 Auto-calculate missing values', on_click=bulk_auto_calc).props('outline sm')

                    # ── Edit dialog for a single row ────────────────────────
                    edit_dialog = ui.dialog()
                    with edit_dialog, ui.card().classes('p-4 w-full max-w-lg'):
                        ui.label('✏️ Edit Player Before Import').classes('text-lg font-bold mb-2')
                        edit_inputs = {}
                        with ui.grid(columns=2).classes('w-full gap-3'):
                            edit_inputs['Speler'] = ui.input('Name')
                            edit_inputs['Positie'] = ui.select(POSITION_OPTIONS, label='Position')
                            edit_inputs['Leeftijd'] = ui.number('Age', min=15, max=45)
                            edit_inputs['dag(en)'] = ui.number('Days', min=0, max=111)
                            edit_inputs['Vorm'] = ui.number('Form', min=1.0, max=8.0, step=0.1)
                            edit_inputs['Conditie'] = ui.number('Stamina', min=1.0, max=9.0, step=0.1)
                            edit_inputs['Specialiteit'] = ui.select(SPECIALITY_OPTIONS, label='Specialty')
                            if SI is not None:
                                SI.spec_select(edit_inputs['Specialiteit'])
                            edit_inputs['Nationality'] = ui.input('Nationality')
                            for f in EDIT_NUM_FIELDS:
                                edit_inputs[f] = ui.number(f, min=0)

                        ui.label('Skills').classes('text-sm font-semibold mt-2')
                        with ui.grid(columns=7).classes('w-full gap-2'):
                            for sk in EDIT_SKILL_FIELDS:
                                edit_inputs[sk] = ui.number(sk, min=1.0, max=25.0, step=0.1)

                        auto_note = ui.label('').classes('text-xs text-gray-400 mt-2').style('white-space: normal;')

                        editing_row_id = {'id': None}
                        auto_filled = {}  # field -> value written by 🧮, so it isn't mistaken for a user edit

                        def current_row():
                            return next((r for r in state['rows'] if r['_row_id'] == editing_row_id['id']), None)

                        def _changed(a, b):
                            try:
                                return abs(float(a) - float(b)) > 1e-6
                            except (TypeError, ValueError):
                                return str(a) != str(b)

                        def effective_missing(row):
                            """Placeholder fields, minus any the user has typed a real value into."""
                            missing = missing_set(row)
                            def user_set(k):
                                v = edit_inputs[k].value
                                return _changed(v, row.get(k)) and (k not in auto_filled or _changed(v, auto_filled[k]))
                            # The position shown in the dialog counts as confirmed — you're looking at it.
                            if edit_inputs['Positie'].value in RICHTSKILLS_DEFAULT:
                                missing.discard('Positie')
                            for k in ('TSI', 'Loon', 'HTMS'):
                                if k in missing and user_set(k):
                                    missing.discard(k)
                            if 'skills' in missing and any(user_set(sk) for sk in EDIT_SKILL_FIELDS):
                                missing.discard('skills')
                            return missing

                        def open_edit(e):
                            editing_row_id['id'] = e.args['_row_id']
                            row = current_row() or e.args
                            auto_filled.clear()
                            for k, inp in edit_inputs.items():
                                inp.set_value(row.get(k))
                            labels = [MISSING_LABELS[m] for m in MISSING_LABELS if m in missing_set(row)]
                            auto_note.set_text(('Not in file: ' + ', '.join(labels) + ' — 🧮 previews estimates; 💾 Save fills them in automatically.')
                                               if labels else 'All values came from the file.')
                            edit_dialog.open()
                        table.on('edit_row', open_edit)

                        def dialog_auto_calc():
                            row = current_row()
                            if row is None:
                                return
                            vals = {k: inp.value for k, inp in edit_inputs.items()}
                            updates, note = auto_estimate(vals, effective_missing(row))
                            if updates is None:
                                ui.notify(f'⚠️ {note}', type='warning')
                                return
                            for k, v in updates.items():
                                if k in edit_inputs:
                                    auto_filled[k] = v
                                    edit_inputs[k].set_value(v)
                            auto_note.set_text('🧮 ' + note + ' — review, then 💾 Save.')

                        def save_edit():
                            row = current_row()
                            if row is not None:
                                missing = effective_missing(row)
                                if row.get('_pos_from_match') and edit_inputs['Positie'].value != row.get('Positie'):
                                    row['_pos_from_match'] = False     # chosen by hand now
                                for k, inp in edit_inputs.items():
                                    row[k] = inp.value
                                note = ''
                                # Saving always replaces any remaining placeholders with
                                # calculated values, so the table never keeps 5/5/5 skills
                                # or a 1000 wage after you've saved a row.
                                if missing & {'TSI', 'Loon', 'skills', 'HTMS'}:
                                    updates, note = auto_estimate(row, missing)
                                    if updates:
                                        row.update(updates)
                                        row['_auto'] = True
                                elif auto_filled:
                                    row['_auto'] = True
                                row['_missing'] = ','.join(sorted(missing))
                                row['Data'], row['Played'] = data_badge(row), played_badge(row)
                            table.update()
                            edit_dialog.close()
                            ui.notify('✅ Row updated' + (f' — 🧮 {note}' if note else '') + '.',
                                      type='positive', timeout=7000)

                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('🧮 Auto-calculate', on_click=dialog_auto_calc).props('outline')
                            ui.button('Cancel', on_click=edit_dialog.close).props('flat')
                            ui.button('💾 Save Changes', on_click=save_edit).style(f'background-color:{ACCENT}; color:white;')

                    ui.separator().classes('my-3')

                    # ── Step 3: Commit ──────────────────────────────────────
                    def _ref_df():
                        try:
                            from data_layer import get_reference_players_df
                            return get_reference_players_df()
                        except Exception:
                            return None

                    async def do_confirm_import():
                        # Resolve the selection back to the rows in state['rows'] by _row_id.
                        # table.selected can hold client-side copies (e.g. after a row was
                        # unticked and re-ticked), which would miss edits made via ✏️ —
                        # so a corrected TSI/Position could silently be lost on import.
                        selected_ids = {r.get('_row_id') for r in table.selected}
                        selected_rows = [r for r in state['rows'] if r.get('_row_id') in selected_ids]
                        if not selected_rows:
                            ui.notify('⚠️ Select at least one player to import.', type='warning')
                            return

                        # Never save placeholders (skills 5/5/5, wage 1,000): calculate what's
                        # still missing with Auto-Solver option 1 first.
                        todo = [r for r in selected_rows if not r.get('_auto')
                                and (missing_set(r) & {'skills', 'TSI', 'Loon', 'HTMS'})]
                        if todo:
                            ref_df = _ref_df()
                            for i, row in enumerate(todo, 1):
                                progress_label.set_text(f'🧮 Calculating {i}/{len(todo)}: {row.get("Speler", "")}…')
                                updates, _note = await run.io_bound(auto_estimate, dict(row), missing_set(row), ref_df)
                                if updates:
                                    row.update(updates)
                                    row['_auto'] = True
                                    row['Data'], row['Played'] = data_badge(row), played_badge(row)
                            progress_label.set_text('')

                        clean_rows = []
                        for row in selected_rows:
                            clean = {c: row.get(c) for c in DB_COLS}
                            clean['username'] = user
                            fv = row.get('Foreign')
                            clean['_file_foreign'] = None if (fv is None or pd.isna(fv)) else int(fv)
                            # HTMS not in the file = an estimate, never a real HTMS.
                            if clean.get('HTMS_est') is None:
                                clean['HTMS_est'] = 1 if 'HTMS' in missing_set(row) else 0
                            try:
                                clean['PlayerID'] = int(clean.get('PlayerID') or 0)
                            except (TypeError, ValueError):
                                clean['PlayerID'] = 0
                            clean_rows.append(clean)
                        import_df = pd.DataFrame(clean_rows)

                        conn = get_db_connection()
                        cursor = conn.cursor()
                        # Abroad flag: from the file when it has one (HTP: IsAbroad), otherwise keep
                        # the flag the player already has.
                        foreign_flags = []
                        for _, r in import_df.iterrows():
                            ff = r.get('_file_foreign')
                            if ff is not None and not pd.isna(ff):
                                foreign_flags.append(int(ff))
                                continue
                            pid = int(r['PlayerID'] or 0)
                            if pid:
                                prev = cursor.execute('SELECT "Foreign" FROM skills_data WHERE LOWER(username)=LOWER(?) AND PlayerID=?;',
                                                      (user, pid)).fetchone()
                            else:
                                prev = cursor.execute('SELECT "Foreign" FROM skills_data WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                                                      (user, str(r['Speler']))).fetchone()
                            foreign_flags.append(int(prev[0] or 0) if prev else 0)
                        if club_sel.value and club_sel.value != NO_CLUB and 'Nationality' in import_df.columns:
                            _club = normalize_nationality(club_sel.value)
                            foreign_flags = [0 if normalize_nationality(str(n or '')) == _club else 1
                                             for n in import_df['Nationality'].tolist()]
                        import_df['Foreign'] = foreign_flags
                        import_df = import_df.drop(columns=['_file_foreign'], errors='ignore')
                        # Performance history: move the player's previous import to player_history, keep his
                        # TSI-at-22 / TSI-at-17 baselines, and set them from this import when he is that age now.
                        base22, base17 = [], []
                        for _, r in import_df.iterrows():
                            _keep = archive_player_rows(cursor, user, int(r['PlayerID'] or 0), str(r['Speler']),
                                                        r.get('Leeftijd'), r.get('dag(en)'))
                            _age = int(float(r.get('Leeftijd') or 0))
                            base22.append(_keep.get('TSI_22') or (float(r['TSI']) if _age == 22 and r.get('TSI') else None))
                            base17.append(_keep.get('TSI_17') or (float(r['TSI']) if _age == 17 and r.get('TSI') else None))
                        import_df['TSI_22'] = base22
                        import_df['TSI_17'] = base17
                        for _, r in import_df.iterrows():
                            pid = int(r['PlayerID'] or 0)
                            if pid:
                                # Also the same player stored earlier without a PlayerID (else he
                                # was added a second time instead of updated).
                                cursor.execute(
                                    'DELETE FROM skills_data WHERE LOWER(username)=LOWER(?) AND '
                                    '(PlayerID=? OR ((PlayerID IS NULL OR PlayerID=0) AND Speler=?));',
                                    (user, pid, str(r['Speler'])))
                            else:
                                cursor.execute(
                                    'DELETE FROM skills_data WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                                    (user, str(r['Speler'])))
                        conn.commit()
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore', category=UserWarning)
                            import_df.to_sql('skills_data', conn, if_exists='append', index=False)
                        conn.close()
                        load_user_db.clear()

                        ref_msg = ''
                        if add_ref_cb.value:
                            added = add_players_to_reference_db(import_df, source='import_preview', added_by=user)
                            ref_msg = f' 🗄️ {added} added to Reference DB ({get_reference_players_count()} total).'

                        wl_msg = ''
                        wl_name = wl_select.value
                        if wl_name == NEW_LIST:
                            wl_name = (wl_new.value or '').strip()
                            if wl_name:
                                create_watchlist(user, wl_name)
                            else:
                                ui.notify('⚠️ No watchlist name given, players imported without a watchlist.', type='warning')
                        if wl_name and wl_name not in (NO_LIST, NEW_LIST):
                            n_added = sum(1 for nm in import_df['Speler'].astype(str) if add_to_watchlist(user, wl_name, nm))
                            wl_msg = f' 📋 {n_added} added to watchlist "{wl_name}".'

                        ui.notify(f'✅ Imported {len(import_df)} of {len(state["rows"])} parsed players!{ref_msg}{wl_msg}',
                                  type='positive', timeout=6000)
                        state['rows'] = []
                        render_preview.refresh()

                    progress_label = ui.label('').classes('text-sm text-gray-300')
                    ui.button('✅ Confirm Import', on_click=do_confirm_import, color=None).classes('mt-2 tt-goldbtn')

        render_preview()