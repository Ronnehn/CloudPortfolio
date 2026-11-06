import io
import pandas as pd
from nicegui import ui, app
try:   # Hattrick specialty icons
    import spec_icons as SI
except ImportError:
    SI = None
from shell import apply_theme, require_login, render_sidebar, ACCENT, tt_card, page_title
from data_layer import (
    get_reference_players_count, get_reference_players_df, clear_reference_players_db,
    import_reference_players_file, read_uploaded_csv,
    update_reference_player, set_reference_position, delete_reference_players,
    set_reference_abroad, reference_likely_abroad,
)
try:   # newer data_layer.py / ht_engine.py only: bulk re-estimate with All Combos
    from data_layer import apply_reference_reestimate, undo_reference_reestimate, last_reference_reestimate
    from ht_engine import reestimate_reference_row
except ImportError:
    reestimate_reference_row = None
from nicegui import run
from ht_engine import RICHTSKILLS_DEFAULT, SPECIALITY_OPTIONS
try:
    from ht_engine import infer_position_from_skills
except ImportError:
    infer_position_from_skills = None
from data_layer import get_user_pref, set_user_pref
try:   # health check of the reference players (copies, wage/TSI that don't fit the skills)
    import ref_check as RC
except ImportError:
    RC = None
from reference_tracker import render_tracker_dashboard

ALL = '— all —'
SKILLS = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
POSITIONS = list(RICHTSKILLS_DEFAULT.keys())


@ui.page('/reference')
def reference_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    render_sidebar(user, '/reference')

    with ui.column().classes('w-full max-w-6xl mx-auto p-2 md:p-4'):
        page_title('/reference')

        with tt_card('📥 Bulk Import (CSV / XLSX)'):

            async def handle_upload(e):
                try:
                    content = await e.file.read()
                    if e.file.name.lower().endswith('.xlsx'):
                        df = pd.read_excel(io.BytesIO(content))
                    else:
                        buf = io.BytesIO(content)
                        buf.name = e.file.name
                        df = read_uploaded_csv(buf)
                    added = import_reference_players_file(df)
                    if added == 0:
                        ui.notify('⚠️ No new players added — check the file has valid rows.', type='warning')
                    else:
                        ui.notify(f'✅ Added {added} players. Total now: {get_reference_players_count()}.', type='positive')
                        render_view.refresh()
                except Exception as ex:
                    ui.notify(f'Import Error: {ex}', type='negative')

            ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=".csv,.xlsx"').classes('w-full')

            def export_reference():
                d = get_reference_players_df()
                if d.empty:
                    ui.notify('The reference database is empty.', type='warning')
                    return
                import datetime as _dt
                ui.download.content(d.to_csv(index=False).encode('utf-8'),
                                    f"reference_players_{_dt.date.today().strftime('%Y-%m-%d')}.csv", 'text/csv')
                ui.notify(f'⬇️ Exported {len(d)} reference players.', type='positive')

            ui.button('⬇️ Export the reference database (CSV)', on_click=export_reference).props('outline no-caps').classes('mt-2')

        # ── Edit one player ────────────────────────────────────────────────────
        edit_dialog = ui.dialog()

        def open_editor(row):
            edit_dialog.clear()
            fields = {}
            with edit_dialog, ui.card().classes('p-4').style('min-width: 640px; max-width: 95vw;'):
                ui.label(f"✏️ {row.get('Speler', '')}").classes('text-lg font-semibold')
                ui.label(f"Source: {row.get('source') or '-'}  ·  added {row.get('added_date') or '-'}").classes('text-xs text-gray-400')
                with ui.grid(columns=3).classes('w-full gap-3 mt-2'):
                    fields['Speler'] = ui.input('Name', value=row.get('Speler') or '')
                    pos = row.get('Positie') if row.get('Positie') in POSITIONS else None
                    fields['Positie'] = ui.select(POSITIONS, value=pos, label='Position')
                    spec = row.get('Specialiteit') if row.get('Specialiteit') in SPECIALITY_OPTIONS else 'None'
                    fields['Specialiteit'] = ui.select(SPECIALITY_OPTIONS, value=spec, label='Specialty')
                    if SI is not None:
                        SI.spec_select(fields['Specialiteit'])
                    fields['Nationality'] = ui.input('Nationality', value=row.get('Nationality') or '')
                    fields['Leeftijd'] = ui.number('Age', value=row.get('Leeftijd'), format='%d')
                    fields['dag(en)'] = ui.number('Days', value=row.get('dag(en)'), format='%d')
                    fields['TSI'] = ui.number('TSI', value=row.get('TSI'), format='%d')
                    fields['Loon'] = ui.number('Wage', value=row.get('Loon'), format='%d')
                    fields['PlayerID'] = ui.number('PlayerID', value=row.get('PlayerID'), format='%d')
                    fields['HTMS'] = ui.number('HTMS', value=row.get('HTMS'), format='%d')
                    fields['HTMS28'] = ui.number('HTMS28', value=row.get('HTMS28'), format='%d')
                fields['Foreign'] = ui.switch('✈️ Plays abroad (wage includes +20%)',
                                                value=bool(int(float(row.get('Foreign') or 0))))
                ui.label('Skills').classes('text-sm font-semibold mt-3')
                with ui.grid(columns=7).classes('w-full gap-2'):
                    for sk in SKILLS:
                        fields[sk] = ui.number(sk, value=row.get(sk), step=0.1, min=0, max=25)

                def save():
                    vals = {k: (f.value if not isinstance(f.value, str) else f.value.strip()) for k, f in fields.items()}
                    vals['Foreign'] = 1 if fields['Foreign'].value else 0
                    update_reference_player(row['id'], vals)
                    edit_dialog.close()
                    ui.notify(f"✅ {vals.get('Speler')} saved.", type='positive')
                    render_view.refresh()

                def remove():
                    delete_reference_players([row['id']])
                    edit_dialog.close()
                    ui.notify(f"🗑️ {row.get('Speler')} removed from the Reference Database.", type='positive')
                    render_view.refresh()

                with ui.row().classes('w-full justify-between mt-4'):
                    ui.button('🗑️ Delete player', on_click=remove).props('flat color=red no-caps')
                    with ui.row().classes('gap-2'):
                        ui.button('Cancel', on_click=edit_dialog.close).props('flat no-caps')
                        ui.button('💾 Save', on_click=save, color=None).props('unelevated no-caps').classes('tt-goldbtn')
            edit_dialog.open()

        # ── Re-estimate estimated rows with All Combos ──────────────────────
        re_state = {'preview': [], 'running': False}

        def _real_levels(r):
            """Whole skill levels from an import = real skills: never re-estimated. (Keeper 0 = not in the file.)"""
            if RC is not None:
                return RC.is_real(r)
            try:
                v = [float(r.get(k)) for k in SKILLS]
            except (TypeError, ValueError):
                return False
            return all(x >= 1 and x == int(x) for x in v) and [int(x) for x in v] != [1, 5, 5, 5, 4, 5, 1]

        def render_reestimate(df_all, table):
            with tt_card('🎲 Re-estimate with All Combos'):
                srcs = sorted(x for x in df_all.get('source', pd.Series(dtype=str)).dropna().astype(str).unique() if x)
                with ui.row().classes('w-full items-center gap-4'):
                    src_sel = ui.select(srcs, multiple=True, value=[x for x in srcs if x != 'bulk_csv'],
                                        label='Sources to include').props('dense use-chips').classes('min-w-[260px]') \
                        .tooltip('bulk_csv is left out by default: files you uploaded here often hold real skills')
                    mode_sel = ui.toggle({'auto': 'NT / U22 by age', 'other': 'Other (usual training)'}, value='auto') \
                        .props('no-caps unelevated toggle-color=primary') \
                        .tooltip('NT / U22: U22 template up to 21, NT template from 22. Other: built around the usual '
                                 'training for each position.')
                    only_sel = ui.switch('Only players selected above', value=False).props('dense')
                status = ui.label('').classes('text-sm')
                preview_box = ui.column().classes('w-full')

                def candidates():
                    d = get_reference_players_df()
                    if only_sel.value:
                        ids = {r['id'] for r in (table.selected or [])}
                        d = d[d['id'].isin(ids)]
                    if 'source' in d.columns and src_sel.value is not None:
                        d = d[d['source'].astype(str).isin(src_sel.value or [])]
                    return [r for _, r in d.iterrows() if not _real_levels(r)]

                async def do_preview():
                    if re_state['running']:
                        return
                    rows = candidates()
                    if not rows:
                        ui.notify('No estimated rows match these choices.', type='warning')
                        return
                    re_state['running'] = True
                    preview_box.clear()
                    out, skipped = [], 0
                    for i, r in enumerate(rows):
                        status.set_text(f'Calculating {i + 1} / {len(rows)} …')
                        new, note = await run.io_bound(reestimate_reference_row, r.to_dict(), mode_sel.value)
                        if new is None:
                            skipped += 1
                            continue
                        old = {k: float(r.get(k) or 0) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']}
                        ch = max(abs(new[k] - old[k]) for k in old)
                        out.append(dict(id=int(r['id']), Player=str(r.get('Speler')), Pos=str(r.get('Positie')),
                                        Age=int(float(r.get('Leeftijd') or 0)),
                                        **{f'{k}': f"{old[k]:.1f} → {new[k]:.1f}" for k in old},
                                        Change=round(ch, 2), Note=note, _new=new))
                    re_state['running'] = False
                    re_state['preview'] = out
                    status.set_text(f'{len(out)} players recalculated' + (f', {skipped} skipped (no fit / no data)' if skipped else '')
                                    + '. Nothing is saved yet.')
                    with preview_box:
                        cols = [{'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                for c in ['Player', 'Pos', 'Age', 'DE', 'PM', 'WI', 'Pas', 'SC', 'Change', 'Note']]
                        ui.table(columns=cols, rows=[{k: v for k, v in o.items() if k != '_new'} for o in
                                                     sorted(out, key=lambda o: -o['Change'])],
                                 row_key='id', pagination=15).props('dense flat').classes('w-full')
                        ui.button(f'💾 Save these {len(out)} new estimates', on_click=do_apply) \
                            .props('unelevated no-caps').style(f'background:{ACCENT}; color:white;')

                def do_apply():
                    ups = [(o['id'], o['_new']) for o in re_state['preview']]
                    n = apply_reference_reestimate(ups, user)
                    re_state['preview'] = []
                    ui.notify(f'✅ {n} reference players updated (source: all_combos). Undo is available.', type='positive')
                    render_view.refresh()

                def do_undo():
                    n = undo_reference_reestimate()
                    ui.notify(f'↩️ {n} reference players restored to their previous values.' if n else 'Nothing to undo.',
                              type='positive' if n else 'warning')
                    render_view.refresh()

                with ui.row().classes('items-center gap-3'):
                    ui.button('🔍 Preview', on_click=do_preview).props('outline no-caps').tooltip(
                        'Recalculates estimated skills from TSI + wage. Real skills (whole levels from an import) and '
                        'keepers are never changed. Nothing is saved until you confirm; Undo puts the old values back.')
                    last = last_reference_reestimate()
                    if last:
                        ui.button(f'↩️ Undo last re-estimate ({last[1]} players)', on_click=do_undo).props('flat no-caps')

        def render_position_check(df_all):
            """Which reference players the current position rules would place elsewhere (WTM, CAD, OCD, ...)."""
            with tt_card('🔁 Re-check positions'):
                ui.label('Checks every reference player against the position rules again, for example WTM has more '
                         'playmaking than winger and CAD has high defending and passing. Nothing changes until you apply, '
                         'and Undo puts the old positions back.').classes('text-xs text-gray-400')
                with ui.row().classes('items-center gap-4'):
                    only_real = ui.switch('Only players with real skills (whole levels)', value=True).props('dense') \
                        .tooltip('Estimated skills were built on the position\'s own profile, so they mostly confirm it')
                    skip_own = ui.switch('Skip roster / watchlist players', value=True).props('dense') \
                        .tooltip('Your own and watched players still need solving: leave their positions alone')
                    ui.button('🔍 Check', on_click=lambda: do_check()).props('outline no-caps')
                    last = get_user_pref(user, 'ref_pos_undo', None)
                    if last and user.lower() == 'admin':
                        ui.button(f'↩️ Undo last change ({len(last)} players)', on_click=lambda: do_undo()).props('flat no-caps')
                box = ui.column().classes('w-full')
                st = {'rows': []}

                def do_check():
                    d = get_reference_players_df()
                    out = []
                    names, ids = (RC.skip_lists(user) if (RC is not None and skip_own.value) else ([], []))
                    n_skip = 0
                    for _, r in d.iterrows():
                        if only_real.value and not _real_levels(r):
                            continue
                        if names or ids:
                            if RC.is_skipped(r, names, ids):
                                n_skip += 1
                                continue
                        try:
                            v = [float(r.get(k) or 0) for k in SKILLS]
                        except (TypeError, ValueError):
                            continue
                        new = infer_position_from_skills(v[0], v[1], v[2], v[3], v[4], v[5], spec=r.get('Specialiteit'), sh=v[6])
                        old = str(r.get('Positie') or '')
                        same = (new == old) or ({new, old} <= {'DFW', 'TDFW'}) or (old in ('OIM-Q', 'OIM-H') and new in ('OIM-Q', 'OIM-H'))
                        if not same:
                            out.append({'id': int(r['id']), 'Player': str(r.get('Speler')), 'Age': int(float(r.get('Leeftijd') or 0)),
                                        'Now': old, 'Suggested': new,
                                        'Skills': ' / '.join(f"{k} {float(r.get(k) or 0):g}" for k in ['DE', 'PM', 'WI', 'Pas', 'SC', 'SH'])})
                    st['rows'] = out
                    box.clear()
                    with box:
                        if not out:
                            ui.label('✓ Every player already has the position the rules give.').classes('text-sm').style('color:#34D399;')
                            return
                        from collections import Counter
                        cnt = Counter(f"{o['Now']} → {o['Suggested']}" for o in out)
                        ui.label(f"{len(out)} players would move: " + ', '.join(f'{k} ({n})' for k, n in cnt.most_common())
                                 + (f' · {n_skip} roster / watchlist players skipped' if n_skip else ''))\
                            .classes('text-sm font-semibold')
                        cols = [{'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                for c in ['Player', 'Age', 'Now', 'Suggested', 'Skills']]
                        st['table'] = ui.table(columns=cols, rows=out, row_key='id', selection='multiple', pagination=15) \
                            .props('dense flat').classes('w-full')
                        if user.lower() == 'admin':
                            with ui.row().classes('gap-2'):
                                ui.button('Apply to selected', on_click=lambda: do_apply(True)).props('outline no-caps')
                                ui.button(f'Apply all {len(out)}', on_click=lambda: do_apply(False)) \
                                    .props('unelevated no-caps').style(f'background:{ACCENT}; color:white;')
                        else:
                            ui.label('Only an admin can change positions.').classes('text-xs').style('color:#FBBF24;')

                def do_apply(selected_only):
                    if user.lower() != 'admin':
                        return
                    rows = (st['table'].selected or []) if selected_only else st['rows']
                    if not rows:
                        ui.notify('Select players first.', type='warning')
                        return
                    set_user_pref(user, 'ref_pos_undo', [[o['id'], o['Now']] for o in rows])
                    by_new = {}
                    for o in rows:
                        by_new.setdefault(o['Suggested'], []).append(o['id'])
                    for pos, ids in by_new.items():
                        set_reference_position(ids, pos)
                    ui.notify(f'✅ {len(rows)} positions updated. Undo is available.', type='positive')
                    render_view.refresh()

                def do_undo():
                    last = get_user_pref(user, 'ref_pos_undo', None) or []
                    by_old = {}
                    for rid, old in last:
                        by_old.setdefault(old, []).append(rid)
                    for pos, ids in by_old.items():
                        set_reference_position(ids, pos)
                    set_user_pref(user, 'ref_pos_undo', None)
                    ui.notify(f'↩️ {len(last)} positions restored.', type='positive')
                    render_view.refresh()

        def render_ref_check(df_all):
            """Which reference players look wrong: copies, wage or TSI that his skills can't give, position."""
            with tt_card('🩺 Check reference players'):
                ui.label('Looks for mistakes in the players with real skills: the same player saved twice, a wage that is '
                         'too low for his skills, a TSI his skills can\'t give, a wrong abroad setting, or a position that '
                         'doesn\'t match his skills. Your roster and watchlist players can be left out, since they still '
                         'need solving. Nothing changes until an admin clicks a button.').classes('text-xs text-gray-400')
                is_admin = user.lower() == 'admin'
                with ui.row().classes('items-center gap-3'):
                    chk_btn = ui.button('🩺 Check').props('outline no-caps')
                    skip_rw = ui.switch('Skip roster / watchlist players', value=True).props('dense') \
                        .tooltip('Your own and watched players still need solving: leave them out of the check')
                    if is_admin:
                        for _key, _lab in (('ref_dedupe_undo', 'removing copies'), ('ref_problem_undo', 'removing problem players')):
                            _last = get_user_pref(user, _key, None)
                            if _last:
                                ui.button(f"↩️ Undo {_lab} ({_last.get('n', 0)} players)",
                                          on_click=lambda k=_key: do_undo(k)).props('flat no-caps')
                        _ab = get_user_pref(user, 'ref_abroad_undo', None)
                        if _ab:
                            ui.button(f'↩️ Undo abroad fixes ({len(_ab)} players)', on_click=lambda: do_undo_abroad()).props('flat no-caps')
                if not is_admin:
                    ui.label('Only an admin can fix or remove reference players.').classes('text-xs').style('color:#FBBF24;')
                box = ui.column().classes('w-full')
                st = {'copies': [], 'abroad': [], 'problems': []}
                confirm = ui.dialog()

                async def do_check():
                    box.clear()
                    with box:
                        ui.label('Checking…').classes('text-sm')
                    names, ids = RC.skip_lists(user) if skip_rw.value else ([], [])
                    d = get_reference_players_df()
                    rows, copies, n_chk, n_skip = await run.io_bound(RC.check_reference, d, names, ids)
                    st['copies'] = copies
                    st['abroad'] = [(r['id'], r['abroad_to'], r['was_abroad']) for r in rows if r.get('abroad_to') is not None]
                    st['problems'] = [r['id'] for r in rows if {'wage', 'tsi'} & set(r['kinds'])]
                    box.clear()
                    with box:
                        from collections import Counter
                        cnt = Counter(k for r in rows for k in r['kinds'])
                        lab = {'copy': 'extra copies', 'wage': 'wage too low', 'tsi': 'TSI doesn\'t fit',
                               'abroad': 'abroad flag', 'position': 'position'}
                        ui.label(f"{n_chk} players checked" + (f", {n_skip} skipped (roster / watchlists)" if skip_rw.value else '') + " · "
                                 + (', '.join(f"{lab[k]}: {cnt[k]}" for k in lab if cnt.get(k)) or 'nothing found'))\
                            .classes('text-sm font-semibold')
                        if not rows:
                            ui.label('✓ Every checked player looks right.').classes('text-sm').style('color:#34D399;')
                            return
                        kinds = ui.select({k: lab[k] for k in lab if cnt.get(k)}, multiple=True, value=[k for k in lab if cnt.get(k)],
                                          label='Show').props('dense use-chips').classes('min-w-[320px]')
                        cols = ([{'name': 'edit', 'label': '', 'field': 'edit'}] if is_admin else []) + \
                               [{'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                for c in ['Player', 'Pos', 'Age', 'Source', 'Problem']]
                        data = [{k: v for k, v in r.items() if k not in ('kinds', 'abroad_to', 'was_abroad')} | {'_k': r['kinds']}
                                for r in rows]
                        tbl = ui.table(columns=cols, rows=data, row_key='id', pagination=15).props('dense flat').classes('w-full')
                        if is_admin:
                            tbl.add_slot('body-cell-edit', '''
                                <q-td :props="props">
                                    <q-btn flat dense round size="sm" icon="edit" @click="() => $parent.$emit('edit', props.row)" />
                                </q-td>''')

                        def _edit(e):
                            full = get_reference_players_df()
                            hit = full[full['id'] == int(e.args['id'])]
                            if not hit.empty:
                                open_editor(hit.iloc[0].where(pd.notna(hit.iloc[0]), None).to_dict())
                        tbl.on('edit', _edit)

                        def _filter(_=None):
                            tbl.rows = [r for r in data if set(r['_k']) & set(kinds.value or [])]
                            tbl.update()
                        kinds.on_value_change(_filter)
                        if is_admin:
                            with ui.row().classes('gap-2 mt-2'):
                                if copies:
                                    ui.button(f'🗑️ Remove the {len(copies)} extra copies',
                                              on_click=lambda: ask_remove('copies')).props('unelevated no-caps color=red')
                                if st['abroad']:
                                    ui.button(f"✈️ Fix the {len(st['abroad'])} abroad flags", on_click=lambda: do_fix_abroad()) \
                                        .props('outline no-caps')
                                if st['problems']:
                                    ui.button(f"🗑️ Remove the {len(st['problems'])} wage/TSI problem players",
                                              on_click=lambda: ask_remove('problems')).props('outline no-caps color=red')
                            ui.label('Click ✏️ to fix or delete one player. Positions: use "🔁 Re-check positions" below. '
                                     'Every button can be undone.').classes('text-xs text-gray-400')

                chk_btn.on_click(do_check)

                def ask_remove(what):
                    ids = st['copies'] if what == 'copies' else st['problems']
                    confirm.clear()
                    with confirm, ui.card().classes('p-4'):
                        ui.label(f"Remove {len(ids)} " + ('extra copies?' if what == 'copies' else 'players whose wage or TSI '
                                 "doesn't fit their skills?")).classes('text-lg font-semibold')
                        ui.label(('For each player the first copy stays. ' if what == 'copies' else '') + 'You can undo this.') \
                            .classes('text-sm text-gray-400')
                        with ui.row().classes('w-full justify-end gap-2 mt-3'):
                            ui.button('Cancel', on_click=confirm.close).props('flat no-caps')
                            ui.button('🗑️ Yes, remove them', on_click=lambda: do_remove(what)).props('unelevated no-caps color=red')
                    confirm.open()

                def do_remove(what):
                    confirm.close()
                    if user.lower() != 'admin':
                        return
                    ids = st['copies'] if what == 'copies' else st['problems']
                    batch = RC.delete_with_backup(ids)
                    set_user_pref(user, 'ref_dedupe_undo' if what == 'copies' else 'ref_problem_undo', {'batch': batch, 'n': len(ids)})
                    ui.notify(f"🗑️ {len(ids)} " + ('extra copies' if what == 'copies' else 'problem players')
                              + ' removed. Undo is available.', type='positive')
                    render_view.refresh()

                def do_undo(key):
                    last = get_user_pref(user, key, None) or {}
                    n = RC.restore_batch(last.get('batch')) if last.get('batch') else 0
                    set_user_pref(user, key, None)
                    ui.notify(f'↩️ {n} players put back.', type='positive')
                    render_view.refresh()

                def do_fix_abroad():
                    if user.lower() != 'admin' or not st['abroad']:
                        return
                    set_user_pref(user, 'ref_abroad_undo', [[i, was] for i, to, was in st['abroad']])
                    for flag in (0, 1):
                        ids = [i for i, to, was in st['abroad'] if to == flag]
                        if ids:
                            set_reference_abroad(ids, bool(flag))
                    ui.notify(f"✈️ {len(st['abroad'])} abroad flags fixed. Undo is available.", type='positive')
                    render_view.refresh()

                def do_undo_abroad():
                    last = get_user_pref(user, 'ref_abroad_undo', None) or []
                    for flag in (0, 1):
                        ids = [i for i, was in last if int(was) == flag]
                        if ids:
                            set_reference_abroad(ids, bool(flag))
                    set_user_pref(user, 'ref_abroad_undo', None)
                    ui.notify(f'↩️ {len(last)} abroad flags put back.', type='positive')
                    render_view.refresh()

        # ── Search, filter, table, bulk actions ───────────────────────────────
        flt = {'q': '', 'pos': ALL, 'nat': ALL, 'src': ALL, 'likely': False}

        @ui.refreshable
        def render_view():
            df_all = get_reference_players_df()
            render_tracker_dashboard(df_all)

            with tt_card(f'📋 Reference Players ({len(df_all)} total)'):
                if df_all.empty:
                    ui.label('No reference players yet.').classes('text-gray-400')
                    return

                likely = set(reference_likely_abroad(df_all))
                df_all = df_all.copy()
                df_all['Abroad'] = [('✈️' if int(float(f or 0)) == 1 else ('⚠️ likely' if i in likely else ''))
                                    for i, f in zip(df_all['id'], df_all.get('Foreign', pd.Series([0] * len(df_all))))]
                nats = sorted(x for x in df_all.get('Nationality', pd.Series(dtype=str)).dropna().astype(str).unique() if x)
                srcs = sorted(x for x in df_all.get('source', pd.Series(dtype=str)).dropna().astype(str).unique() if x)
                with ui.row().classes('w-full items-center gap-3 no-wrap'):
                    q = ui.input('Search name', value=flt['q']).props('clearable dense').classes('flex-1 min-w-0')
                    fpos = ui.select([ALL] + POSITIONS, value=flt['pos'], label='Position').props('dense').classes('w-36')
                    fnat = ui.select([ALL] + nats, value=flt['nat'] if flt['nat'] in [ALL] + nats else ALL, label='Country').props('dense').classes('w-44')
                    fsrc = ui.select([ALL] + srcs, value=flt['src'] if flt['src'] in [ALL] + srcs else ALL, label='Source').props('dense').classes('w-44')
                    flik = ui.switch(f'⚠️ Likely abroad only ({len(likely)})', value=flt['likely']).props('dense')

                show_cols = [c for c in ['Speler', 'Abroad', 'Nationality', 'Positie', 'Specialiteit', 'Leeftijd', 'TSI', 'Loon',
                                         'HTMS', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH', 'source'] if c in df_all.columns]
                labels = {'Speler': 'Player', 'Positie': 'Pos', 'Specialiteit': 'Spec', 'Leeftijd': 'Age', 'Loon': 'Wage',
                          'Nationality': 'Country', 'source': 'Source'}
                cols = [{'name': 'edit', 'label': '', 'field': 'edit'}] + \
                       [{'name': c, 'label': labels.get(c, c), 'field': c, 'sortable': True, 'align': 'left'} for c in show_cols]

                def filtered_rows():
                    d = df_all
                    if flt['q']:
                        d = d[d['Speler'].astype(str).str.contains(flt['q'], case=False, na=False)]
                    if flt['pos'] != ALL:
                        d = d[d['Positie'].astype(str) == flt['pos']]
                    if flt['nat'] != ALL and 'Nationality' in d.columns:
                        d = d[d['Nationality'].astype(str) == flt['nat']]
                    if flt['src'] != ALL and 'source' in d.columns:
                        d = d[d['source'].astype(str) == flt['src']]
                    if flt['likely']:
                        d = d[d['id'].isin(likely)]
                    d = d.copy()
                    for sk in SKILLS:
                        if sk in d.columns:
                            d[sk] = pd.to_numeric(d[sk], errors='coerce').round(2)
                    return d[['id'] + show_cols].where(pd.notna(d[['id'] + show_cols]), None).to_dict('records')

                count_lbl = ui.label('').classes('text-xs text-gray-400')
                table = ui.table(columns=cols, rows=filtered_rows(), row_key='id', selection='multiple',
                                 pagination=25).classes('w-full').props('dense flat')
                table.add_slot('body-cell-edit', '''
                    <q-td :props="props">
                        <q-btn flat dense round size="sm" icon="edit" @click="() => $parent.$emit('edit', props.row)" />
                    </q-td>''')
                table.on('edit', lambda e: open_editor(e.args))
                if SI is not None:
                    SI.table_specs(table)

                def apply_filters(_=None):
                    flt.update(q=(q.value or '').strip(), pos=fpos.value, nat=fnat.value, src=fsrc.value, likely=bool(flik.value))
                    table.rows = filtered_rows()
                    table.selected = []
                    table.update()
                    count_lbl.set_text(f'{len(table.rows)} shown')
                for w in (q, fpos, fnat, fsrc, flik):
                    w.on_value_change(apply_filters)
                count_lbl.set_text(f'{len(table.rows)} shown')

                # Bulk actions on the selected players
                with ui.row().classes('w-full items-center gap-3 mt-2'):
                    bulk_pos = ui.select(POSITIONS, label='New position').props('dense').classes('w-40')

                    def do_set_pos():
                        ids = [r['id'] for r in table.selected]
                        if not ids or not bulk_pos.value:
                            ui.notify('⚠️ Select players and a position first.', type='warning')
                            return
                        set_reference_position(ids, bulk_pos.value)
                        ui.notify(f'✅ {len(ids)} player(s) set to {bulk_pos.value}.', type='positive')
                        render_view.refresh()

                    def do_delete_sel():
                        ids = [r['id'] for r in table.selected]
                        if not ids:
                            ui.notify('⚠️ Select players first.', type='warning')
                            return
                        delete_reference_players(ids)
                        ui.notify(f'🗑️ {len(ids)} player(s) removed.', type='positive')
                        render_view.refresh()

                    ui.button('Set position of selected', on_click=do_set_pos).props('outline dense no-caps')
                    def do_abroad(flag):
                        ids = [r['id'] for r in table.selected]
                        if not ids:
                            ui.notify('⚠️ Select players first.', type='warning')
                            return
                        set_reference_abroad(ids, flag)
                        ui.notify(f"✅ {len(ids)} player(s) marked as {'abroad (+20%)' if flag else 'not abroad'}.", type='positive')
                        render_view.refresh()

                    ui.button('✈️ Mark selected as abroad', on_click=lambda: do_abroad(True)).props('outline dense no-caps')
                    ui.button('Not abroad', on_click=lambda: do_abroad(False)).props('outline dense no-caps')
                    ui.button('🗑️ Delete selected', on_click=do_delete_sel).props('outline dense no-caps color=red')

            if reestimate_reference_row is not None and not df_all.empty:
                render_reestimate(df_all, table)
            if RC is not None and not df_all.empty:
                render_ref_check(df_all)
            if infer_position_from_skills is not None and not df_all.empty:
                render_position_check(df_all)

            # Danger Zone (clear everything) - only for admins
            if user.lower() == 'admin':
                with tt_card('🗑️ Danger Zone'):
                    confirm_cb = ui.checkbox('I understand this permanently deletes all reference players')

                    def do_clear():
                        if not confirm_cb.value:
                            ui.notify('⚠️ Check the confirmation box first.', type='warning')
                            return
                        clear_reference_players_db()
                        ui.notify('✅ Reference database cleared.', type='positive')
                        render_view.refresh()

                    ui.button('🗑️ Clear Reference Database', on_click=do_clear).props('color=red')

        render_view()