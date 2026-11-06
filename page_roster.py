import io
import csv
import pandas as pd
from nicegui import ui, app
try:   # Hattrick specialty icons
    import spec_icons as SI
except ImportError:
    SI = None
from shell import apply_theme, require_login, render_sidebar, ht_row, markup_block, copy_text, tt_card, page_title, opt_panel, ACCENT
from ht_engine import get_flag, forum_stamina
try:   # newer ht_engine.py only: position fit and position score from the contribution table
    from ht_engine import best_positions, position_score, order_fit, ORDER_LABELS, CONTRIBUTIONS
except ImportError:
    best_positions = None
from data_layer import (
    load_user_db, delete_player, export_roster_to_excel, get_db_connection,
    get_watchlists, create_watchlist, add_to_watchlist,
    remove_from_watchlist, delete_watchlist, rename_watchlist, get_user_pref, set_user_pref,
)


def players_to_hattrick_markup(players_df, include_skills=True):
    """Selected players as a Hattrick markup table (optionally without the 7 skills,
    i.e. only the player data with form and stamina)."""
    def num(v, dec=0):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return ''
        if pd.isna(f):
            return ''
        return f'{f:.{dec}f}'
    def level(v):
        # Form / stamina as Hattrick shows them (whole number); keep a sub-level if one is stored.
        s = num(v, 2)
        if not s:
            return ''
        f = float(s)
        return str(int(f)) if f == int(f) else f'{f:.1f}'

    def known(v):
        # 0 / empty HTMS: leave the cell empty rather than printing 0.
        s = num(v)
        return s if s and float(s) > 0 else ''

    skills = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH'] if include_skills else []
    head = ['Player', 'Pos', 'Age', 'Spec', 'Form', 'Stamina', 'TSI', 'Wage', 'HTMS', 'HTMS28'] + skills
    lines = ['[table]', ht_row(head, header=True)]
    for _, p in players_df.iterrows():
        age = num(p.get('Leeftijd'))
        days = num(p.get('dag(en)'))
        if days and days != '0':
            age = f'{age} ({days}d)'
        spec = str(p.get('Specialiteit', '') or '')
        lines.append(ht_row([f"[b]{p.get('Speler', '')}[/b]", str(p.get('Positie', '') or ''), age,
                             '' if spec == 'None' else spec, level(p.get('Vorm')), level(forum_stamina(p.get('Conditie'))),
                             num(p.get('TSI')), num(p.get('Loon')),
                             known(p.get('HTMS')), known(p.get('HTMS28'))] + [num(p.get(sk), 2) for sk in skills]))
    lines.append('[/table]')
    return '\n'.join(lines)


def players_to_csv(players_df):
    """Convert selected players to CSV string."""
    output = io.StringIO()
    export_cols = [c for c in ['Speler','Nationality','Positie','Leeftijd','dag(en)',
                                'Specialiteit','Vorm','Conditie','TSI','Loon',
                                'HTMS','HTMS28','GK','DE','PM','WI','Pas','SC','SH']
                   if c in players_df.columns]
    players_df[export_cols].to_csv(output, index=False)
    return output.getvalue()


@ui.page('/roster')
def roster_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    df_all = load_user_db(user)
    render_sidebar(user, '/roster')

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):

        page_title('/roster')

        if df_all.empty:
            ui.label('No players in your roster yet. Add a player or import a CSV/HRF from the sidebar.').classes('text-gray-400')
            return

        # ── Country filter (remembered per user) ─────────────────────────────
        nat_col = df_all['Nationality'].fillna('Unknown').astype(str).str.strip().replace('', 'Unknown') \
            if 'Nationality' in df_all.columns else pd.Series(['Unknown'] * len(df_all), index=df_all.index)
        counts = nat_col.value_counts()
        ALL = 'All countries'
        options = {ALL: f'🌍 All countries ({len(df_all)})'}
        options.update({c: f'{get_flag(c)} {c} ({n})' for c, n in counts.sort_index().items()})
        # Watchlists in the same filter (key 'wl::<name>')
        try:
            _wls = {n: set(m) for n, m in (get_watchlists(user) or {}).items() if n != '__EMPTY__'}
        except Exception:
            _wls = {}
        for _n, _m in sorted(_wls.items()):
            options[f'wl::{_n}'] = f"📋 {_n} ({int(df_all['Speler'].isin(_m).sum())})"
        saved = get_user_pref(user, 'roster_country', ALL)   # saved in the database (follows you to every device)
        def _abroad_series(df):
            if 'Foreign' not in df.columns:
                return pd.Series([False] * len(df), index=df.index)
            return pd.to_numeric(df['Foreign'], errors='coerce').fillna(0).astype(int) == 1

        with ui.row().classes('w-full items-center gap-4 mb-4 tt-pbar'):
            country_sel = ui.select(options, value=saved if saved in options else ALL,
                                    label='Country / Watchlist').classes('w-72')
            abroad_cb = ui.switch(f'✈️ Abroad only ({int(_abroad_series(df_all).sum())})',
                                    value=bool(get_user_pref(user, 'roster_abroad', False)))

        body_area = ui.column().classes('w-full')

        def render_body():
            body_area.clear()
            country = country_sel.value or ALL
            if country == ALL:
                mask = pd.Series([True] * len(df_all), index=df_all.index)
            elif str(country).startswith('wl::'):
                mask = df_all['Speler'].isin(_wls.get(country[4:], set()))
            else:
                mask = nat_col == country
            if abroad_cb.value:   # players trained outside their own country
                mask &= _abroad_series(df_all)
            df_raw = df_all[mask].reset_index(drop=True)
            with body_area:
                _body(df_raw)

        def on_country(e):
            set_user_pref(user, 'roster_country', e.value)
            render_body()
        country_sel.on_value_change(on_country)

        def on_abroad(e):
            set_user_pref(user, 'roster_abroad', bool(e.value))
            render_body()
        abroad_cb.on_value_change(on_abroad)

        def _body(df_raw):
            if df_raw.empty:
                ui.label('No players for this filter.').classes('text-gray-400')
                return
            OVERVIEW_FIELDS = [('Positie', 'Position'), ('TSI', 'TSI'), ('Loon', 'Wage'), ('HTMS', 'HTMS'), ('HTMS28', 'HTMS28')]

            def is_missing(v):
                if pd.isna(v) or str(v).strip() in ('', 'nan', 'NaN', 'None'):
                    return True
                try:
                    return float(v) <= 0
                except (TypeError, ValueError):
                    return False

            # Watchlists first (filled further down, once the roster table exists).
            wl_slot = ui.column().classes('w-full gap-0')

            # ── Completeness card ──────────────────────────────────────────────────
            with tt_card('🟧 Player Data Completeness'):
                tot = len(df_raw)
                with ui.grid(columns=len(OVERVIEW_FIELDS)).classes('w-full gap-3 tt-tiles'):
                    for field, label in OVERVIEW_FIELDS:
                        n_missing = df_raw[field].apply(is_missing).sum() if field in df_raw.columns else tot
                        color = 'text-green-400' if n_missing == 0 else 'text-red-400'
                        with ui.column().classes('gap-0 tt-tile'):
                            ui.label(f'{tot - n_missing}/{tot} set').classes(f'tt-tilev {color}')
                            ui.label(label).classes('text-sm text-gray-400')

            # ── Remove player + Export actions ────────────────────────────────────
            with ui.card().classes('w-full p-4 mb-4'):
              with ui.grid(columns=3).classes('w-full gap-3 grid-cols-1 lg:grid-cols-3'):
                with opt_panel('🗑️', 'Remove player'):
                    player_names = df_raw['Speler'].dropna().tolist()
                    def plabel(n):
                        rows = df_raw[df_raw['Speler']==n]
                        if rows.empty: return n
                        pos = str(rows.iloc[0].get('Positie','') or '')
                        age = str(int(rows.iloc[0].get('Leeftijd',0)) if rows.iloc[0].get('Leeftijd') else '')
                        return f"{n} ({pos}, {age})" if pos else n
                    player_labels = {plabel(n): n for n in player_names}
                    del_select = ui.select(list(player_labels.keys()),
                                           value=(list(player_labels.keys())[0] if player_labels else None)
                                           ).classes('w-full').props('dense outlined')
                    _del_row = ui.row().classes('w-full items-center justify-between no-wrap')
                    with _del_row:
                        confirm_del_cb = ui.checkbox('Confirm').props('dense')

                    def do_delete_player():
                        if not del_select.value:
                            ui.notify('⚠️ Select a player first.', type='warning'); return
                        if not confirm_del_cb.value:
                            ui.notify('⚠️ Check Confirm first.', type='warning'); return
                        real_name = player_labels.get(del_select.value, del_select.value)
                        ok, msg = delete_player(user, real_name)
                        ui.notify(msg, type='positive' if ok else 'negative')
                        if ok:
                            ui.navigate.to('/roster')

                    with _del_row:
                        ui.button('🗑️ Remove', on_click=do_delete_player).props('outline dense no-caps color=negative') \
                            .tooltip('Remove the selected player (tick Confirm first)')

                with opt_panel('📤', 'Export selected'):
                    sel_count_label = ui.label('0 selected').classes('text-xs text-gray-400')

                    def export_hattrick(include_skills=True):
                        sel_df = get_selected_df()
                        if sel_df is None: return
                        markup = players_to_hattrick_markup(sel_df, include_skills=include_skills)
                        what = 'Hattrick markup' + ('' if include_skills else ' (form & stamina, no skills)')
                        copy_text(markup, f'{what} for {len(sel_df)} player(s)')
                        export_area.clear()
                        with export_area:
                            markup_block(markup, f'{what} for {len(sel_df)} player(s)',
                                         f'📋 {what} — {len(sel_df)} player(s), already copied')

                    def export_csv():
                        sel_df = get_selected_df()
                        if sel_df is None: return
                        csv_str = players_to_csv(sel_df)
                        ui.download(csv_str.encode('utf-8-sig'), filename='roster_export.csv', media_type='text/csv')
                        export_area.clear()
                        with export_area:
                            markup_block(csv_str, f'CSV for {len(sel_df)} player(s)',
                                         f'📄 CSV — {len(sel_df)} player(s), downloaded as roster_export.csv')

                    _exp_row = ui.row().classes('w-full gap-2 flex-wrap')
                    with _exp_row:
                        ui.button('📋 HT Markup', on_click=lambda: export_hattrick(True)).props('outline dense no-caps').classes('text-xs')
                        ui.button('📋 Markup (no skills)', on_click=lambda: export_hattrick(False)).props('outline dense no-caps').classes('text-xs')
                        ui.button('📄 CSV', on_click=export_csv).props('outline dense no-caps').classes('text-xs')

                    def reset_htms():
                        # For HTMS values the app estimated (e.g. older imports without HTMS):
                        # 0 = unknown, so the Auto-Solver ticks "HTMS Unknown" by itself.
                        sel_df = get_selected_df()
                        if sel_df is None: return
                        conn = get_db_connection()
                        cur = conn.cursor()
                        for name in sel_df['Speler']:
                            cur.execute('UPDATE skills_data SET HTMS=0, HTMS28=0 WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                                        (user, name))
                        conn.commit()
                        conn.close()
                        load_user_db.clear()
                        ui.notify(f'❓ HTMS set to unknown for {len(sel_df)} player(s).', type='positive')
                        ui.navigate.to('/roster')

                    with _exp_row:
                        ui.button('❓ Reset HTMS', on_click=reset_htms).props('outline dense no-caps').classes('text-xs') \
                            .tooltip('Set HTMS/HTMS28 of the selected players to unknown (for estimated, not real, values)')

                with opt_panel('📊', 'Shown players'):

                    # Full roster export (independent of the selection above)
                    def export_full_roster():
                        if df_raw.empty:
                            ui.notify('No players to export.', type='warning')
                            return
                        buf = export_roster_to_excel(df_raw)
                        ui.download(buf.getvalue(), f'{user}_roster.xlsx')

                    ui.label('All players in the list below').classes('text-xs text-gray-400')
                    ui.button('📊 Excel (.xlsx)', on_click=export_full_roster).props('outline dense no-caps').classes('text-xs')
              export_area = ui.column().classes('w-full')

            # ── Full roster with selection ─────────────────────────────────────────
            with ui.card().classes('w-full p-4'):
                with ui.row().classes('w-full justify-between items-center mb-3'):
                    n_abroad = int(_abroad_series(df_raw).sum())
                    ui.label(f"📋 Roster (All Skills) — {len(df_raw)} player{'s' if len(df_raw) != 1 else ''}"
                             + (f' · ✈️ {n_abroad} abroad' if n_abroad else '')).classes('text-md font-semibold')

                selected_names = set()

                df_raw = df_raw.copy()
                df_raw['Abroad'] = _abroad_series(df_raw).map({True: '✈️', False: ''})
                if best_positions is not None:
                    def _bp(r):
                        try:
                            sk = {k: float(r.get(k) or 1.0) for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC')}
                            return ' · '.join(f'{o} {f:.0f}' for o, f in best_positions(sk, r.get('Specialiteit'), 3))
                        except Exception:
                            return ''
                    df_raw['Best position'] = [_bp(r) for _, r in df_raw.iterrows()]
                disp_cols = [c for c in ['Speler', 'Nationality', 'Abroad', 'Positie', 'Best position', 'Leeftijd', 'dag(en)',
                                          'Specialiteit', 'Vorm', 'Conditie', 'TSI', 'Loon',
                                          'HTMS', 'HTMS28', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
                             if c in df_raw.columns]
                table_df = df_raw[disp_cols].copy()
                rows = table_df.to_dict('records')

                with ui.element('div').classes('w-full overflow-x-auto'):
                        roster_table = ui.table(
                    columns=[{'name': c, 'label': c, 'field': c, 'sortable': True} for c in disp_cols],
                    rows=rows,
                    row_key='Speler',
                    selection='multiple',
                ).classes('w-full').props('dense flat')
                if SI is not None:
                    SI.table_specs(roster_table)

                def on_selection(e):
                    selected_names.clear()
                    for row in roster_table.selected:
                        selected_names.add(row['Speler'])
                    sel_count_label.set_text(f'{len(selected_names)} selected')

                roster_table.on('selection', on_selection)

                with ui.row().classes('gap-2 mt-2'):
                    def select_all():
                        roster_table.selected = rows[:]
                        selected_names.clear()
                        selected_names.update(r['Speler'] for r in rows)
                        sel_count_label.set_text(f'{len(selected_names)} selected')

                    def select_none():
                        roster_table.selected = []
                        selected_names.clear()
                        sel_count_label.set_text('0 selected')

                    ui.button('Select All', on_click=select_all).props('outline sm')
                    ui.button('Select None', on_click=select_none).props('outline sm')


                def get_selected_df():
                    if not selected_names:
                        ui.notify('⚠️ Select at least one player first.', type='warning')
                        return None
                    return df_raw[df_raw['Speler'].isin(selected_names)].copy()
            # ── Watchlist management ───────────────────────────────────────────────
            if best_positions is not None and not df_raw.empty:
                with tt_card('🏅 Position ranking', 'Who is best for one position: contribution-weighted skills + experience'):
                    _ord = {o: f'{o} · {ORDER_LABELS.get(o, o)}' for o in CONTRIBUTIONS}
                    rk_sel = ui.select(_ord, value='NCD', label='Position').classes('w-72')
                    rk_box = ui.column().classes('w-full')

                    def render_ranking(_=None):
                        rk_box.clear()
                        o = rk_sel.value
                        rows = []
                        for _, r in df_raw.iterrows():
                            if o == 'PNF' and str(r.get('Specialiteit') or '').strip().lower() != 'powerful':
                                continue
                            sk = {k: float(r.get(k) or 1.0) for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC')}
                            xp = r.get('Ervaring')
                            rows.append({'Player': r.get('Speler'), 'Pos': r.get('Positie'), 'Age': r.get('Leeftijd'),
                                         'XP': '' if xp is None or pd.isna(xp) else int(float(xp)),
                                         'Score': round(position_score(sk, o, xp), 2),
                                         'Fit %': round(order_fit(sk, o), 1)})
                        rows.sort(key=lambda d: -d['Score'])
                        for i, d in enumerate(rows, 1):
                            d['#'] = i
                        with rk_box:
                            ui.table(columns=[{'name': c, 'label': c, 'field': c, 'sortable': True, 'align': 'left'}
                                              for c in ['#', 'Player', 'Pos', 'Age', 'XP', 'Score', 'Fit %']],
                                     rows=rows, row_key='Player', pagination=15).props('dense flat').classes('w-full')
                            ui.label('Score: how strong he is there (skill-level scale). Fit %: how well his skills '
                                     'suit that position, whatever his strength.').classes('text-xs text-gray-400')
                    rk_sel.on_value_change(render_ranking)
                    render_ranking()

            with wl_slot, tt_card('📋 Watchlists', 'Groups of players: filter the Roster, Auto-Solver and Estimator on them. Saved in the database.'):
                roster_names = sorted(str(n) for n in df_all['Speler'].dropna().unique())

                def refresh_filter_options():
                    """Keep the Country / Watchlist filter at the top in step with the lists."""
                    lists = {n: set(m) for n, m in (get_watchlists(user) or {}).items()}
                    _wls.clear(); _wls.update(lists)
                    opts = {k: v for k, v in options.items() if not str(k).startswith('wl::')}
                    for _n, _m in sorted(lists.items()):
                        opts[f'wl::{_n}'] = f"📋 {_n} ({int(df_all['Speler'].isin(_m).sum())})"
                    options.clear(); options.update(opts)
                    country_sel.set_options(opts, value=country_sel.value if country_sel.value in opts else ALL)

                def changed(msg):
                    ui.notify(msg, type='positive')
                    refresh_filter_options()
                    render_watchlists.refresh()

                # New list: name + Enter (or the button)
                with ui.row().classes('w-full items-center gap-2 no-wrap'):
                    new_list_input = ui.input(placeholder='New watchlist name (e.g. U21 candidates)') \
                        .props('dense outlined clearable').classes('flex-1')

                    def do_create():
                        name = (new_list_input.value or '').strip()
                        if not name:
                            ui.notify('Enter a name first.', type='warning')
                            return
                        if create_watchlist(user, name):
                            new_list_input.set_value('')
                            changed(f'✅ Watchlist "{name}" created')
                        else:
                            ui.notify(f'A list called "{name}" already exists.', type='warning')
                    new_list_input.on('keydown.enter', lambda: do_create())
                    ui.button('➕ New list', on_click=do_create).props('unelevated no-caps').style(f'background:{ACCENT}; color:white;')

                rename_dialog = ui.dialog()
                confirm_dialog = ui.dialog()

                def open_rename(ln):
                    rename_dialog.clear()
                    with rename_dialog, ui.card().classes('p-4 min-w-[320px]'):
                        ui.label(f'Rename "{ln}"').classes('text-md font-semibold')
                        inp = ui.input('New name', value=ln).props('dense outlined autofocus').classes('w-full')

                        def ok():
                            nn = (inp.value or '').strip()
                            if rename_watchlist(user, ln, nn):
                                rename_dialog.close()
                                changed(f'✏️ Renamed to "{nn}"')
                            else:
                                ui.notify('Choose a new name that is not used yet.', type='warning')
                        inp.on('keydown.enter', lambda: ok())
                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                            ui.button('Cancel', on_click=rename_dialog.close).props('flat no-caps')
                            ui.button('Save', on_click=ok).props('unelevated no-caps').style(f'background:{ACCENT}; color:white;')
                    rename_dialog.open()

                def open_delete(ln, n):
                    confirm_dialog.clear()
                    with confirm_dialog, ui.card().classes('p-4 min-w-[320px]'):
                        ui.label(f'Delete watchlist "{ln}"?').classes('text-md font-semibold')
                        ui.label(f'{n} player(s) in it. The players themselves stay in your roster.').classes('text-sm text-gray-400')

                        def ok():
                            delete_watchlist(user, ln)
                            confirm_dialog.close()
                            changed(f'🗑️ Watchlist "{ln}" deleted')
                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                            ui.button('Cancel', on_click=confirm_dialog.close).props('flat no-caps')
                            ui.button('Delete', on_click=ok).props('unelevated no-caps color=red')
                    confirm_dialog.open()

                # player names in the lists (and the ones picked to add): white text on a soft blue chip
                ui.add_css('.tt-wchip.q-chip, .tt-wlpick .q-chip { background: rgba(47,110,168,.28) !important; color: #FFFFFF !important;'
                           ' border: 1px solid rgba(106,163,214,.55); font-weight: 500; }'
                           '.tt-wchip .q-chip__icon--remove, .tt-wlpick .q-chip__icon--remove { color: #FFFFFF !important; opacity: .7; }'
                           '.tt-wlpick.q-field--float .q-field__native { padding-top: 20px !important; padding-bottom: 4px !important; }')

                @ui.refreshable
                def render_watchlists():
                    lists = {k: [p for p in v if p != '__EMPTY__'] for k, v in (get_watchlists(user) or {}).items()}
                    if not lists:
                        ui.label('No watchlists yet. Type a name above and press Enter.').classes('text-sm text-gray-500 mt-3')
                        return
                    with ui.grid(columns=3).classes('w-full gap-3 mt-3 grid-cols-1 md:grid-cols-2 xl:grid-cols-3'):
                        for ln, members in lists.items():
                            with ui.card().classes('p-3 gap-2').style('background:#1C1C24; border:1px solid #3B3B4D;'):
                                with ui.row().classes('w-full items-center no-wrap gap-2'):
                                    ui.label(f'📋 {ln}').classes('text-md font-semibold flex-1 min-w-0 truncate')
                                    ui.badge(str(len(members))).props('color=primary')
                                    ui.button(icon='edit', on_click=lambda ln=ln: open_rename(ln)) \
                                        .props('flat round dense size=sm').tooltip('Rename')
                                    ui.button(icon='delete', on_click=lambda ln=ln, n=len(members): open_delete(ln, n)) \
                                        .props('flat round dense size=sm color=red').tooltip('Delete list')
                                # Players as chips: click × to take one out
                                with ui.row().classes('w-full gap-1'):
                                    if not members:
                                        ui.label('Empty: add players below.').classes('text-xs text-gray-500')
                                    for pn in members:
                                        ui.chip(pn, removable=True,
                                                on_value_change=lambda e, ln=ln, pn=pn: (
                                                    remove_from_watchlist(user, ln, pn),
                                                    changed(f'Removed {pn} from "{ln}"')) if not e.value else None) \
                                            .props('dense').classes('text-xs tt-wchip')
                                # Add players: pick from the roster (type to search), or the rows ticked in the table
                                with ui.row().classes('w-full items-center gap-2 no-wrap'):
                                    pick = ui.select([n for n in roster_names if n not in members], multiple=True,
                                                     with_input=True, label='Add players') \
                                        .props('dense outlined use-chips').classes('flex-1 min-w-0 tt-wlpick')

                                    def do_add(ln=ln, pick=pick):
                                        names = list(pick.value or []) or sorted(selected_names)
                                        if not names:
                                            ui.notify('Pick players in the box, or tick them in the roster table.', type='warning')
                                            return
                                        n = sum(1 for pn in names if add_to_watchlist(user, ln, pn))
                                        changed(f'✅ Added {n} player(s) to "{ln}"')
                                    ui.button(icon='person_add', on_click=do_add).props('flat round dense').tooltip(
                                        'Add the players picked here (or, when none are picked, the rows ticked in the roster table)')

                render_watchlists()

                # Paste a team's "Players" table: match ratings per player, saved for the Auto-Solver (🧭 Other).
                try:
                    import ht_paste as _HP
                except ImportError:
                    _HP = None
                if _HP is not None:
                    with ui.expansion('📋 Paste a team\'s "Players" table (match ratings for the Auto-Solver)', value=False) \
                            .classes('w-full mt-3').props('dense'):
                        ui.label('In Hattrick: the team\'s Players statistics (select recent matches for young players), '
                                 'Ctrl+A, Ctrl+C, paste here. Players are matched by name with your roster; their ratings '
                                 'are saved and used when you solve them as 🧭 Other.').classes('text-xs text-gray-400')
                        wl_box = ui.textarea(placeholder='Paste the Players table here…') \
                            .props('outlined dense input-style="max-height:160px"').classes('w-full') \
                            .style('font-family:monospace; font-size:12px;')
                        with ui.row().classes('items-center gap-2'):
                            wl_read = ui.button('🔍 Read and save').props('unelevated no-caps')
                            wl_status = ui.label('').classes('text-sm')
                        wl_found = ui.column().classes('w-full')

                        def _wl_read():
                            import datetime as _dt
                            tab = _HP.parse_team_table(wl_box.value or '')
                            wl_found.clear()
                            if not tab:
                                wl_status.set_text('✗ No Players table recognised')
                                wl_status.style('color:#F87171;')
                                return
                            roster = {n.lower(): n for n in roster_names}
                            in_lists = {p for v in (get_watchlists(user) or {}).values() for p in v}
                            rows, saved, missing = [], 0, []
                            today = _dt.date.today().strftime('%d-%m-%Y')
                            for name, pl in tab.items():
                                hit = roster.get(name.lower())
                                pos = ' · '.join(f"{_HP.ORDER_LABEL.get(q, q)} {v['avg']:g}/{v['max']:g}×{v['matches']}"
                                                 for q, v in pl['pos'].items()) or 'no matches'
                                if hit and pl['pos']:
                                    set_user_pref(user, f'ratings::{hit}', {'kind': 'table', 'player': pl,
                                                                            'source': 'team table', 'date': today})
                                    saved += 1
                                rows.append({'Player': name, 'Positions (avg/max × matches)': pos,
                                             'Watchlist': '📋' if hit in in_lists else '',
                                             'Saved': '✓' if (hit and pl['pos']) else ('not in roster' if not hit else '–')})
                            for wl_name in sorted(in_lists - {'__EMPTY__'}):
                                if wl_name.lower() not in {n.lower() for n in tab}:
                                    missing.append(wl_name)
                            wl_status.set_text(f'✓ {len(tab)} players read · ratings saved for {saved}')
                            wl_status.style('color:#34D399;')
                            with wl_found:
                                if missing:
                                    ui.label('⚠ Watchlist players not in this table: ' + ', '.join(missing[:12])
                                             + (' …' if len(missing) > 12 else '')).classes('text-xs').style('color:#FBBF24;')
                                cols = [{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in rows[0]]
                                ui.table(columns=cols, rows=rows, row_key='Player', pagination=20) \
                                    .props('dense flat').classes('w-full')
                        wl_read.on_click(_wl_read)

        render_body()