import math
import time
from nicegui import ui, app
from shell import apply_theme, require_login, render_sidebar, ACCENT, ACCENT_DARK, FORM_GREEN, copy_text, page_title, opt_panel, opt_hint, form_stamina_color, tt_card
from i18n import tr, tr_list
from data_layer import get_user_pref, set_user_pref
from data_layer import (
    load_user_db, get_db_connection, get_country_richtskills, safe_float, safe_int,
    get_watchlists, sync_player_to_reference_db,
)
from ht_engine import (
    normalize_position,
    get_flag, normalize_nationality, player_links, player_forum_markup,
    calculate_exact, calculate_htms_ability, calculate_htms_potential, clean_spec,
    is_player_u21, sh_fallback_for, skill_level_label, SPECIALITY_OPTIONS, lookup_wage, HATTRICK_SKILL_WORDS,
)
from richtskills_data import RICHTSKILLS_DEFAULT
import json as _json


class _Slider(ui.slider):
    """Slider whose value isn't echoed back while dragging (keeps the thumb smooth on slow connections)."""
    LOOPBACK = False


# Skill bars you can drag (like the Auto-Solver, without locks): the level word follows while dragging,
# the number box and the calculated TSI / wage update when you let go.
EST_SLIDER_CSS = '''
<style>
.tt-eskbar { position: relative; }
.tt-est-form.nicegui-grid { column-gap: 14px !important; row-gap: 16px !important; }
@media (min-width: 900px) { .tt-estbar { flex-wrap: nowrap !important; } }
.tt-est-form.nicegui-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
@media (min-width: 768px) { .tt-est-form.nicegui-grid { grid-template-columns: repeat(4, minmax(0, 1fr)) !important; } }
@media (min-width: 1280px) { .tt-est-form.nicegui-grid { grid-template-columns: repeat(6, minmax(0, 1fr)) !important; } }
.tt-est-main.nicegui-grid { grid-template-columns: minmax(0, 1fr) !important; }
@media (min-width: 1100px) { .tt-est-main.nicegui-grid { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr) !important; } }
@media (max-width: 767px) { .tt-est-form .col-span-2 { grid-column: span 2 / span 2; } }
@media (max-width: 600px) { .tt-est-save.nicegui-grid { grid-template-columns: minmax(0, 1fr) !important; } }
.tt-est-form.nicegui-grid > .q-field { max-width: none !important; }
.tt-chk.nicegui-grid { grid-template-columns: 70px 1fr 1fr 1fr !important; column-gap: 8px; row-gap: 6px; }
.tt-chk-h { font-family: Oswald, sans-serif; font-size: 11.5px; letter-spacing: .1em; text-transform: uppercase; color: #8FA3BA; }
.tt-chk-n { font-size: 14px; color: #C9D4E0; }
.tt-chk-v { font-family: Oswald, sans-serif; font-size: 17px; font-weight: 600; color: #FFFFFF; }
.tt-chk-d { font-size: 14px; font-weight: 600; }
@media (min-width: 1280px) { .tt-est-form.nicegui-grid { grid-template-columns: repeat(8, minmax(0, 1fr)) !important; } }
.tt-skrow { padding: 3px 0; }
.tt-est-form .q-select .q-field__native { flex-wrap: nowrap !important; overflow: hidden; }
.tt-est-form .q-select .q-field__native span { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
.tt-skname { width: 90px; flex-shrink: 0; font-size: 13.5px; color: #9FB0C3; }
.tt-sknum { width: 76px; flex-shrink: 0; }
.q-field.tt-sknum:not(.q-textarea):not(.q-select--multiple) .q-field__control { height: 34px !important; min-height: 34px !important; padding: 0 6px !important; border-radius: 8px !important; }
.tt-sknum .q-field__native { text-align: center; font-family: Oswald, sans-serif !important; font-weight: 600 !important; font-size: 16px !important;
  padding: 0 !important; min-height: 34px !important; color: #FFFFFF; }
.q-field.tt-sknum:not(.q-textarea):not(.q-select--multiple) .q-field__marginal { height: 34px !important; min-height: 34px !important; }
.tt-elvl { width: 30px; flex-shrink: 0; text-align: right; font-family: Oswald, sans-serif; font-weight: 600; font-size: 16px; color: #FFFFFF; }
.tt-eskbar .q-slider__thumb { opacity: 0; transition: opacity .15s; }
.tt-eskbar:hover .q-slider__thumb { opacity: 1; }
.tt-src { display: inline-block; margin-top: 8px; font-size: 11.5px; color: #8FA3BA; border: 1px dashed #33465C; border-radius: 6px; padding: 2px 8px; }
.tt-eskbar .q-slider__track { background: #262D38; border-radius: 6px; }
.tt-eskbar .q-slider__inner { background: transparent; }
.tt-eskbar .q-slider__selection { background: var(--fs, #24782E); border-radius: 6px; }
.tt-eskbar .q-slider__thumb { color: #FAFAFA; }
.tt-eword { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); font-size: 12px; color: #FAFAFA;
            pointer-events: none; z-index: 2; white-space: nowrap; }
.tt-chip { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; margin-right: 6px; }
</style>
'''
try:   # Hattrick specialty icons
    import spec_icons as SI
except ImportError:
    SI = None


# Rough upper bound for main-skill growth per training week for young players with
# full training (levels/week). Only used to flag clearly impossible growth since the
# last birthday (when Hattrick last updated the wage).
MAX_TRAIN_RATE = 0.20
MAX_TRAIN_RATE_GK = 0.30

@ui.page('/')
def estimator_page():
    apply_theme()
    user = require_login()
    if not user:
        return

    df_raw = load_user_db(user)
    render_sidebar(user, '/')

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        hero = page_title('/')

        all_player_names = df_raw['Speler'].dropna().tolist() if not df_raw.empty else []

        # Build display labels: "Rene Schigt (NFW, 21)"
        def player_label(name):
            if df_raw.empty: return name
            rows = df_raw[df_raw['Speler'] == name]
            if rows.empty: return name
            pos = str(rows.iloc[0].get('Positie','') or '')
            age = str(int(rows.iloc[0].get('Leeftijd',0)) if rows.iloc[0].get('Leeftijd') else '')
            return f"{name} ({pos}, {age})" if pos else name

        def names_to_labels(names):
            return {player_label(n): n for n in names}

        def label_to_name(label):
            if not label: return label
            return all_labels.get(label, label.split(' (')[0] if ' (' in label else label)

        all_labels = names_to_labels(all_player_names)
        all_label_list = list(all_labels.keys())

        try:
            watchlists = get_watchlists(user)
        except Exception:
            watchlists = {}
        countries = sorted(set(normalize_nationality(c) for c in df_raw['Nationality'].dropna().unique())) if not df_raw.empty and 'Nationality' in df_raw.columns else []

        filter_opts = ['🌍 All Players'] + [f'{get_flag(c)} {c}' for c in countries] + [f'📋 {n}' for n in watchlists if n != '__EMPTY__']

        def _base_filtered_names():
            try:
                val = (filter_select.value or '🌍 All Players')
            except Exception:
                return all_player_names
            if val == '🌍 All Players' or df_raw.empty:
                return all_player_names
            if not val.startswith('🌍') and not val.startswith('📋'):
                country = val.split(' ', 1)[1] if ' ' in val else val
                return df_raw[df_raw['Nationality'].apply(normalize_nationality) == country]['Speler'].dropna().tolist()
            if val.startswith('📋 '):
                list_name = val[len('📋 '):]
                members = [p for p in watchlists.get(list_name, []) if p != '__EMPTY__']
                return [p for p in all_player_names if p in members]
            return all_player_names


        def _is_abroad(name):
            if df_raw.empty or 'Foreign' not in df_raw.columns:
                return False
            rows = df_raw[df_raw['Speler'] == name]
            try:
                return (not rows.empty) and int(float(rows['Foreign'].iloc[0] or 0)) == 1
            except (TypeError, ValueError):
                return False

        def get_filtered_names():
            names = _base_filtered_names()
            try:
                if abroad_cb.value:   # "✈️ Abroad only": players trained outside their own country
                    names = [n for n in names if _is_abroad(n)]
            except NameError:
                pass
            return names

        picker_state = {'is_new': True, 'selected': None}

        # Order: New player -> filter -> player -> abroad only (abroad last).
        with ui.row().classes('items-center gap-3 w-full mb-4 tt-estbar').style(
                'background:#19202B; border:1px solid #2A3647; border-radius:12px; padding:10px 14px;'):
            player_select = ui.select(all_label_list, label='Search Existing Player', with_input=True).classes('flex-1 min-w-[220px]')
            if SI is not None and not df_raw.empty and 'Specialiteit' in df_raw.columns:
                _sp = dict(zip(df_raw['Speler'], df_raw['Specialiteit']))
                SI.player_select(player_select, {lab: _sp.get(n) for lab, n in all_labels.items()}, selected=False)
            filter_select = ui.select(filter_opts, value='🌍 All Players', label='Filter').classes('w-56').style('flex-shrink:0;')
            add_new_btn = ui.button('New player', icon='person_add', color=None).props('unelevated no-caps') \
                .classes('tt-ghost').style('height:44px; border-radius:8px; flex-shrink:0;')
        abroad_cb = ui.checkbox('Abroad only (filter)').classes('hidden')

        # Quick switches in the page header: edit the chosen player, start a new one, abroad only
        with hero:
            with ui.row().classes('gap-2 mt-3 items-center'):
                pill_edit = ui.button('✏️ Edit player', color=None,
                                      on_click=lambda: player_select.run_method('showPopup')).props('flat no-caps').classes('tt-pill')
                pill_new = ui.button('➕ New player', color=None, on_click=lambda: on_add_new()).props('flat no-caps').classes('tt-pill')
                pill_abroad = ui.button('✈️ Abroad only', color=None,
                                        on_click=lambda: abroad_cb.set_value(not abroad_cb.value)).props('flat no-caps').classes('tt-pill')

        def paint_pills():
            for btn, on in ((pill_edit, not picker_state['is_new']), (pill_new, picker_state['is_new']),
                            (pill_abroad, bool(abroad_cb.value))):
                (btn.classes(add='tt-pill-on') if on else btn.classes(remove='tt-pill-on'))

        def on_filter_change(e):
            filtered = get_filtered_names()
            filtered_labels = list(names_to_labels(filtered).keys())
            player_select.options = filtered_labels
            player_select.value = None
            picker_state['is_new'] = True
            picker_state['selected'] = None
            player_select.update()
            render_content.refresh()

        filter_select.on_value_change(on_filter_change)
        abroad_cb.on_value_change(on_filter_change)
        abroad_cb.on_value_change(lambda _: paint_pills())

        content = ui.column().classes('w-full')
        # Remember the filter in the database (follows you to every device).
        _f0, _a0 = get_user_pref(user, 'estimator_filter', None), get_user_pref(user, 'estimator_abroad', False)
        _filter_restore = {'f': _f0 if _f0 in filter_opts else None, 'a': bool(_a0)}
        filter_select.on_value_change(lambda e: set_user_pref(user, 'estimator_filter', e.value))
        abroad_cb.on_value_change(lambda e: set_user_pref(user, 'estimator_abroad', bool(e.value)))

        save_state = {'name': None, 'dirty': False, 't': 0.0}

        @ui.refreshable
        def render_content():
            content.clear()
            paint_pills()
            # Reload fresh data — picks up any applied solver changes
            fresh_df = load_user_db(user)
            is_new = picker_state['is_new']
            selected = picker_state['selected']

            if is_new:
                p_id, p_name, p_pos, p_age, p_days, p_spec = 0, '', 'NFW', 20, 0, 'None'
                p_vorm, p_cond, p_tsi, p_wage, p_htms, p_htms28 = 6.0, 6.0, 1000, 1000, 500, 1900
                p_nat, p_lead, p_inj, p_transfer, p_nt = 'Netherlands', 5.0, 0.0, 'Not transfer-listed', 0
                p_xp = 4.0
                p_foreign = False
                skills = {'GK': 1.0, 'DE': 5.0, 'PM': 5.0, 'WI': 5.0, 'Pas': 4.0, 'SC': 5.0, 'SH': sh_fallback_for('NFW', 20, 0)}
            else:
                p = fresh_df[fresh_df['Speler'] == selected].iloc[0]
                p_id, p_name = safe_int(p.get('PlayerID', 0)), str(p.get('Speler', 'Player'))
                p_pos = str(p.get('Positie', 'NFW') or 'NFW')
                p_pos = normalize_position(p_pos)   # e.g. a stored lineup role 'CD' -> 'NCD'
                p_age, p_days = safe_int(p.get('Leeftijd', 20)), safe_int(p.get('dag(en)', 0))
                p_spec = clean_spec(p.get('Specialiteit', 'None'))
                p_vorm, p_cond = safe_float(p.get('Vorm', 6.0)), safe_float(p.get('Conditie', 6.0))
                p_tsi, p_wage = safe_int(p.get('TSI', 1000)), safe_int(p.get('Loon', 1000))
                p_htms, p_htms28 = safe_int(p.get('HTMS', 180)), safe_int(p.get('HTMS28', 180))
                p_nat = str(p.get('Nationality', 'Netherlands') or 'Netherlands')
                p_lead, p_inj = safe_float(p.get('Leiderschap', 5.0)), safe_float(p.get('Injuries', 0.0))
                p_xp = safe_float(p.get('Ervaring', 4.0))
                p_transfer = str(p.get('Transfer-listed', '') or '')
                p_nt = safe_int(p.get('National team player', 0))
                p_foreign = bool(safe_int(p.get('Foreign', 0)))
                skills = {
                    'GK': safe_float(p.get('GK', 1.0)), 'DE': safe_float(p.get('DE', 5.0)), 'PM': safe_float(p.get('PM', 5.0)),
                    'WI': safe_float(p.get('WI', 5.0)), 'Pas': safe_float(p.get('Pas', 4.0)), 'SC': safe_float(p.get('SC', 5.0)),
                    'SH': safe_float(p.get('SH', sh_fallback_for(p_pos, p_age, p_days))),
                }

            sen_bench, u21_bench = get_country_richtskills(p_nat)
            is_u21 = is_player_u21(p_age, p_days)
            pos_options = list((u21_bench if is_u21 else sen_bench).keys())

            state = dict(vorm=p_vorm, cond=p_cond, **skills)

            with content:
                # ── Player profile box (Hattline-style): data on the left, skill bars on the right ──
                SKILL_ROWS = [('GK', 'Keeper'), ('DE', 'Defending'), ('PM', 'Playmaking'), ('WI', 'Winger'),
                              ('Pas', 'Passing'), ('SC', 'Scoring'), ('SH', 'Set pieces')]

                def skill_bar_html(v, vmax=20.0, color='#24782E'):
                    v = max(0.0, min(float(v or 0.0), vmax))
                    word = skill_level_label(v)
                    return (f'<div style="position:relative;height:24px;border-radius:6px;background:#262730;overflow:hidden">'
                            f'<div style="position:absolute;left:0;top:0;bottom:0;width:{v / vmax * 100:.1f}%;'
                            f'background:{color};transition:width .2s"></div>'
                            f'<span style="position:absolute;left:8px;top:0;line-height:24px;font-size:12px;color:#FAFAFA">{word}</span></div>')

                # ── Player details: a full-width card, labels above the boxes ──
                with ui.card().classes('w-full p-0 mb-4 overflow-hidden tt-card'):
                    with ui.row().classes('w-full items-center justify-between gap-2 px-4 py-2 tt-chead'):
                        with ui.row().classes('items-center gap-3 min-w-0'):
                            ui.html('<span class="tt-cbadge">👤</span>')
                            ui.label('Player details').classes('tt-ctitle')
                            ui.label(f'{p_pos} · {get_flag(p_nat)} {p_nat} · Benchmarks: {"U21" if is_u21 else "Senior"}'
                                     + (' · ✈️ ' + tr('abroad') if p_foreign else '')
                                     + (' · 🏷️ ' + tr('transfer-listed') if p_transfer.strip() else '')).classes('text-sm truncate').style('color:#C6D8EC;')
                        links_box = ui.row().classes('gap-4 items-center')

                    with ui.column().classes('w-full gap-3 px-4 pt-3 pb-4'):
                        with ui.grid(columns=8).classes('w-full tt-est-form tt-ftop'):
                            name_input = ui.input('Name *', value=p_name).classes('w-full col-span-2')
                            id_input = ui.number('PlayerID', value=p_id, format='%d').classes('w-full')
                            pos_input = ui.select(pos_options, value=(p_pos if p_pos in pos_options else pos_options[0]), label='Position').classes('w-full')
                            spec_input = ui.select(SPECIALITY_OPTIONS, value=(p_spec if p_spec in SPECIALITY_OPTIONS else 'None'), label='Specialty').classes('w-full')
                            if SI is not None:
                                SI.spec_select(spec_input)
                            nat_input = ui.input('Nationality', value=p_nat).classes('w-full')
                            age_input = ui.number('Age (years)', value=p_age, min=17, max=45, format='%d').classes('w-full')
                            days_input = ui.number('Days', value=p_days, min=0, max=111, format='%d').classes('w-full')
                            tsi_input = ui.number('TSI *', value=p_tsi, step=100, format='%d').classes('w-full')
                            wage_input = ui.number('Wage *', value=p_wage, step=50, format='%d').classes('w-full')
                            xp_input = ui.number('Experience', value=p_xp, min=0.0, max=20.0, step=0.5).classes('w-full')
                            lead_input = ui.number('Leadership', value=p_lead, min=0.0, max=20.0, step=0.5).classes('w-full')
                            inj_input = ui.number('Injuries (weeks)', value=p_inj, min=0.0, max=10.0, step=1.0).classes('w-full')
                            transfer_input = ui.select({'Not transfer-listed': 'Not listed', 'Transfer-listed': 'Listed'},
                                                       value=('Transfer-listed' if p_transfer.strip() else 'Not transfer-listed'),
                                                       label='Transfer list').classes('w-full')
                            htms_input = ui.number('HTMS', value=p_htms, step=1, format='%d').classes('w-full')
                            htms28_input = ui.number('HTMS28', value=p_htms28, step=1, format='%d').classes('w-full')
                        with ui.row().classes('w-full items-center gap-x-6 gap-y-2'):
                            foreign_cb = ui.switch('Foreign player', value=p_foreign).props('dense').tooltip('+20% wage')
                            nt_input = ui.switch('National team player', value=bool(p_nt)).props('dense')
                            auto_sync_cb = ui.switch('Update HTMS', value=True).props('dense') \
                                .tooltip('On save: HTMS / HTMS28 from the saved skills')
                            ref_sync_cb = ui.switch('Sync corrected skills', value=True).props('dense') \
                                .tooltip('On save: also store them in the Reference DB')

                # ── Skills on the left; the check and saving on the right ──
                with ui.grid(columns=2).classes('w-full gap-4 mb-2 items-start tt-est-main'):
                    with tt_card('📊 Skills', classes='w-full'):
                        subskill_inputs = {}
                        ui.add_head_html(EST_SLIDER_CSS)
                        skill_sliders = {}
                        skill_boxes = {}

                        def drag_js(word_id, vmax, prefix=''):
                            # while dragging: the whole level shows on the right
                            return ("(v) => { const w = document.getElementById('c%d'); if (!w) return; "
                                    "w.innerText = Math.max(0, Math.min(20, Math.floor(v))); }" % word_id)

                        def lvl(v):
                            return str(max(0, min(20, int(math.floor(float(v or 0))))))

                        def paint_top():
                            top = max(SKILL_KEYS, key=lambda k: float(state.get(k) or 0))
                            for k, box in skill_boxes.items():
                                box.style(f'--fs: {"#F6C510" if k == top else "#24782E"};')

                        SKILL_KEYS = [k for k, _ in SKILL_ROWS]
                        for key, label in SKILL_ROWS:
                            with ui.row().classes('w-full items-center gap-3 no-wrap tt-skrow'):
                                ui.label(label).classes('tt-skname')
                                v0 = max(0.0, min(float(state[key] or 0), 20.0))
                                inp = ui.number(value=float(state[key] or 0), step=0.1, min=0.0, max=25.0, format='%.2f') \
                                    .props('dense').classes('tt-sknum')
                                with ui.element('div').classes('flex-1 min-w-0 tt-eskbar') as box:
                                    sl = _Slider(min=0, max=20, step=0.01, value=round(v0, 2)) \
                                        .props('dense track-size=18px thumb-size=14px').classes('w-full')
                                word = ui.label(lvl(v0)).classes('tt-elvl')
                                subskill_inputs[key] = inp
                                skill_sliders[key] = (sl, word)
                                skill_boxes[key] = box
                                sl.on('update:modelValue', js_handler=drag_js(word.id, 20))
                                sl.on('change', lambda e, inp=inp: inp.set_value(round(float(e.args), 3))
                                      if not isinstance(e.args, dict) else None)

                                def on_change(e, key=key, sl=sl, word=word):
                                    state[key] = float(e.value or 0.0)
                                    sl.value = round(max(0.0, min(state[key], 20.0)), 2)
                                    word.set_text(lvl(min(state[key], 20.0)))
                                    paint_top()
                                    update_calc()
                                inp.on_value_change(on_change)
                        paint_top()

                        # Form (max 8) and stamina (max 9): sliders coloured by level, same row layout as the skills.
                        fs_color = form_stamina_color
                        fs_widgets = {}
                        for fs_label, fs_val, fs_max, fs_key in (('Form', p_vorm, 8.0, 'vorm'), ('Stamina', p_cond, 9.4, 'cond')):
                            with ui.row().classes('w-full items-center gap-3 no-wrap tt-skrow'):
                                ui.label(fs_label).classes('tt-skname')
                                fv = max(1.0, min(float(fs_val or 1.0), fs_max))
                                fs_inp = ui.number(value=float(fs_val or 0), min=1.0, max=fs_max, step=0.01, format='%.2f') \
                                    .props('dense').classes('tt-sknum')
                                with ui.element('div').classes('flex-1 min-w-0 tt-eskbar').style(f'--fs: {fs_color(fv)};') as fs_box:
                                    fs_sl = _Slider(min=1.0, max=fs_max, step=0.01, value=round(fv, 2)) \
                                        .props('dense track-size=18px thumb-size=14px').classes('w-full')
                                fs_word = ui.label(lvl(fv)).classes('tt-elvl')
                                fs_sl.on('update:modelValue', js_handler=drag_js(fs_word.id, fs_max))
                                fs_sl.on('change', lambda e, inp=fs_inp: inp.set_value(round(float(e.args), 3))
                                         if not isinstance(e.args, dict) else None)
                            fs_widgets[fs_key] = (fs_sl, fs_word, fs_box)
                            if fs_key == 'vorm':
                                vorm_input = fs_inp
                            else:
                                cond_input = fs_inp

                        def fs_paint(k, v, vmax):
                            sl_, word_, box_ = fs_widgets[k]
                            v = max(1.0, min(float(v or 1.0), vmax))
                            sl_.value = round(v, 2)
                            word_.set_text(lvl(v))
                            box_.style(f'--fs: {fs_color(v)};')

                        with ui.row().classes('w-full gap-2 mt-3'):
                            ui.button('🎯 Find Form & Stamina', color=None, on_click=lambda: find_form_stamina()) \
                                .props('unelevated').classes('tt-ghost')

                    with ui.column().classes('w-full gap-4'):
                        with tt_card('🎯 Check: calculated vs real', classes='w-full'):
                            # Calculated TSI / wage / HTMS next to the real values
                            calc_slot = ui.column().classes('w-full gap-0')
                        with tt_card('💾 Save', classes='w-full'):
                            save_lbl = ui.label('' if is_new else '✓ Changes save automatically').classes('text-sm text-gray-400')
                            with ui.column().classes('gap-3 items-start'):
                                ui.button('💾 Save All Player Data & Subskills', on_click=lambda: do_save_all(), color=None) \
                                    .props('unelevated').classes('tt-goldbtn').style('min-height:46px; font-size:15px;')
                                # Built from the current fields at the moment of clicking.
                                ui.button('📋 Copy Player (for HT Forum)', color=None,
                                          on_click=lambda: copy_text(forum_markup(), 'Player')).props('unelevated').classes('tt-ghost')

                foreign_cb.on_value_change(lambda _: update_calc())

                def on_vorm_change(e):
                    state['vorm'] = float(e.value or 6.0)
                    fs_paint('vorm', state['vorm'], 8.0)
                    update_calc()

                def on_cond_change(e):
                    state['cond'] = float(e.value or 6.0)
                    fs_paint('cond', state['cond'], 9.4)
                    update_calc()

                vorm_input.on_value_change(on_vorm_change)
                cond_input.on_value_change(on_cond_change)

                def find_form_stamina():
                    """Binary search form and stamina to match actual TSI exactly."""
                    actual_tsi = float(tsi_input.value or 0)
                    if actual_tsi <= 0:
                        ui.notify('⚠️ Enter actual TSI first.', type='warning')
                        return
                    age  = int(age_input.value or 20)
                    days = int(days_input.value or 0)
                    spec = spec_input.value
                    gk   = float(subskill_inputs['GK'].value or 1.0)
                    de   = float(subskill_inputs['DE'].value or 5.0)
                    pm   = float(subskill_inputs['PM'].value or 5.0)
                    wi   = float(subskill_inputs['WI'].value or 5.0)
                    pas  = float(subskill_inputs['Pas'].value or 4.0)
                    sc   = float(subskill_inputs['SC'].value or 5.0)
                    sh   = float(subskill_inputs['SH'].value or 1.0)

                    # Try current cond, binary search form
                    cond = float(cond_input.value or 6.0)
                    best_form = None
                    best_diff = float('inf')

                    for form_int in range(1, 9):
                        lo, hi = float(form_int), min(float(form_int) + 0.99, 8.0)
                        _,tsi_lo,_,_,_,_,_ = calculate_exact(age,days,spec,lo,cond,gk,de,pm,wi,pas,sc,sh)
                        _,tsi_hi,_,_,_,_,_ = calculate_exact(age,days,spec,hi,cond,gk,de,pm,wi,pas,sc,sh)
                        if tsi_lo <= actual_tsi <= tsi_hi + 500:
                            lo2, hi2 = lo, hi
                            for _ in range(25):
                                mid = (lo2+hi2)/2
                                _,tsi_mid,_,_,_,_,_ = calculate_exact(age,days,spec,mid,cond,gk,de,pm,wi,pas,sc,sh)
                                if tsi_mid < actual_tsi: lo2 = mid
                                else: hi2 = mid
                            candidate = round((lo2+hi2)/2, 4)   # 4 decimals, so the TSI can match exactly
                            _,tsi_c,_,_,_,_,_ = calculate_exact(age,days,spec,candidate,cond,gk,de,pm,wi,pas,sc,sh)
                            diff = abs(tsi_c - actual_tsi)
                            if diff < best_diff:
                                best_diff = diff
                                best_form = candidate

                    if best_form is None:
                        # TSI out of range for current cond — try cond search too
                        for cond_int in range(1, 10):
                            for form_int in range(1, 9):
                                # middle of each level, but never above Hattrick's maxima (form 8, stamina 9)
                                _,tsi_t,_,_,_,_,_ = calculate_exact(age,days,spec,
                                    min(float(form_int)+0.5, 8.0), min(float(cond_int)+0.5, 9.4),
                                    gk,de,pm,wi,pas,sc,sh)
                                if abs(tsi_t - actual_tsi) < best_diff:
                                    best_diff = abs(tsi_t - actual_tsi)
                                    best_form = min(float(form_int)+0.5, 8.0)
                                    cond = min(float(cond_int)+0.5, 9.4)

                    if best_form is not None:
                        vorm_input.set_value(best_form)
                        cond_input.set_value(round(cond, 2))
                        update_calc()
                        ui.notify(f'✓ Form={best_form:.2f} Stamina={cond:.2f} — TSI delta: {best_diff:+.0f}',
                                  type='positive' if best_diff < 100 else 'warning')
                    else:
                        ui.notify('⚠️ Could not find matching form/stamina. Check skills.', type='warning')

                # Calc panel, built once into the slot under the skills (no refresh flicker).
                with calc_slot:
                    range_html = ui.html('').classes('hidden')   # (kept for the fit check below; shown in the table now)
                    if p_pos == 'K':
                        ui.label('ℹ️ Keeper TSI depends only on GK + Form — DE/PM/WI/Pas/SC do not affect TSI.').classes('text-xs text-amber-400')
                    with ui.grid(columns=4).classes('w-full tt-chk items-center'):
                        for h in ('', 'Real', 'Calculated', 'Difference'):
                            ui.label(h).classes('tt-chk-h')
                        ui.label('TSI').classes('tt-chk-n')
                        tsi_val_label = ui.label('').classes('tt-chk-v')
                        tsi_calc_label = ui.label('').classes('tt-chk-v')
                        tsi_delta_label = ui.label('').classes('tt-chk-d')
                        ui.label('Wage').classes('tt-chk-n')
                        wage_real_label = ui.label('').classes('tt-chk-v')
                        wage_val_label = ui.label('').classes('tt-chk-v')
                        wage_delta_label = ui.label('').classes('tt-chk-d')
                        ui.label('HTMS').classes('tt-chk-n')
                        htms_real_label = ui.label('').classes('tt-chk-v')
                        htms_val_label = ui.label('').classes('tt-chk-v')
                        htms_delta_label = ui.label('').classes('tt-chk-d')
                        ui.label('HTMS28').classes('tt-chk-n')
                        htms28_real_label = ui.label('').classes('tt-chk-v')
                        htms28_val_label = ui.label('').classes('tt-chk-v')
                        htms28_delta_label = ui.label('').classes('tt-chk-d')
                    with ui.row().classes('w-full gap-3 mt-2'):
                        tsi_floor_label = ui.label('').classes('text-xs text-gray-400')
                        tsi_ceil_label = ui.label('').classes('text-xs text-gray-400')
                    wage_hint_label = ui.label('').classes('text-xs text-gray-400').style('white-space: normal;')
                    ui.html('<span class="tt-src">TSI from all skills + form · wage: main skill + 50% of the rest</span>')

                def update_calc():
                    age  = int(age_input.value or 20)
                    days = int(days_input.value or 0)
                    spec = spec_input.value
                    cond = float(cond_input.value or 6.0)
                    gk   = float(subskill_inputs['GK'].value or 1.0)
                    de   = float(subskill_inputs['DE'].value or 5.0)
                    pm   = float(subskill_inputs['PM'].value or 5.0)
                    wi   = float(subskill_inputs['WI'].value or 5.0)
                    pas  = float(subskill_inputs['Pas'].value or 4.0)
                    sc   = float(subskill_inputs['SC'].value or 5.0)
                    sh   = float(subskill_inputs['SH'].value or 1.0)

                    # Use form exactly as entered — let user tune form/stamina
                    # to match actual TSI when skills are known.
                    # Form decimal inference only happens in the Autosolver.
                    vorm_raw  = float(vorm_input.value or 6.0)
                    actual_tsi = float(tsi_input.value or 0)
                    best_vorm = vorm_raw

                    calc_tsi_low, calc_tsi_curr, calc_tsi_high, calc_wage_curr, calc_wage_28, htms_curr, htms28 = calculate_exact(
                        age, days, spec,
                        best_vorm, cond,
                        gk, de, pm, wi, pas, sc, sh
                    )
                    
                    if foreign_cb.value:
                        calc_wage_curr *= 1.20
                        calc_wage_28 *= 1.20

                    tsi_delta = calc_tsi_curr - float(tsi_input.value or 0)
                    wage_delta = calc_wage_curr - float(wage_input.value or 0)
                    wage_is_stale = int(days_input.value or 0) > 0
                    htms_delta = htms_curr - float(htms_input.value or 0)
                    htms28_delta = (htms28 - float(htms28_input.value or 0)) if isinstance(htms28, (int, float)) else 0.0

                    def get_color(delta, neutral=False):
                        if neutral: return '#A6A6B0'
                        if delta == 0: return '#34D399'
                        if delta > 0: return '#34D399'
                        return '#F87171'
                        
                    def get_sign(delta):
                        return '+' if delta > 0 else ''

                    tsi_val_label.set_text(f'{int(actual_tsi):,.0f}' if actual_tsi > 0 else f'{calc_tsi_curr:,.0f}')
                    wage_real_label.set_text(f'€{float(wage_input.value or 0):,.0f}')
                    htms_real_label.set_text(f'{float(htms_input.value or 0):,.0f}')
                    htms28_real_label.set_text(f'{float(htms28_input.value or 0):,.0f}')
                    tsi_calc_label.set_text(f'{calc_tsi_curr:,.0f}')
                    tsi_delta_label.set_text(f'{get_sign(tsi_delta)}{tsi_delta:,.0f}')
                    tsi_delta_label.style(f'color: {get_color(tsi_delta)}')
                    tsi_floor_label.set_text(f'Floor: {calc_tsi_low:,.0f}')
                    tsi_ceil_label.set_text(f'Ceiling: {calc_tsi_high:,.0f}')

                    # Update Wage UI
                    wage_val_label.set_text(f'€{calc_wage_curr:,.0f}')
                    wage_delta_txt = f"{'+' if wage_delta > 0 else '−' if wage_delta < 0 else ''}€{abs(wage_delta):,.0f}"
                    wage_delta_label.set_text(wage_delta_txt)
                    # Hattrick only updates the wage on the birthday (X years, 0 days), so with
                    # days > 0 the actual wage reflects the skills at the last birthday.
                    actual_wage = float(wage_input.value or 0)
                    skills_now = {'GK': gk, 'DE': de, 'PM': pm, 'WI': wi, 'Pas': pas, 'SC': sc}
                    main = max(skills_now, key=lambda k: lookup_wage(skills_now[k], k))
                    wage_mult = 1.20 if foreign_cb.value else 1.0

                    def wage_with(main_val):
                        sk = dict(skills_now, **{main: main_val})
                        return calculate_exact(age, days, spec, best_vorm, cond, sk['GK'], sk['DE'], sk['PM'],
                                               sk['WI'], sk['Pas'], sk['SC'], sh)[3] * wage_mult

                    implied = None
                    if actual_wage > 0:
                        lo, hi = 1.0, 25.0
                        if wage_with(lo) <= actual_wage <= wage_with(hi):
                            for _ in range(40):
                                mid = (lo + hi) / 2
                                lo, hi = (mid, hi) if wage_with(mid) < actual_wage else (lo, mid)
                            implied = (lo + hi) / 2
                    pct = (wage_delta / actual_wage * 100) if actual_wage > 0 else 0.0
                    if not wage_is_stale:
                        wage_delta_label.style(f'color: {get_color(wage_delta)}')
                        wage_hint_label.set_text(
                            f'{pct:+.1f}% — birthday today, so the wage should match the current skills.'
                            + (f' Wage fits {main} {implied:.2f}.' if implied else ''))
                    elif wage_delta >= -actual_wage * 0.01:
                        # Calculated >= actual: skills may have grown since the birthday.
                        weeks = max(days / 7.0, 0.0)
                        msg = f'{pct:+.1f}% — wage is from the last birthday ({days} days ≈ {weeks:.1f} training weeks ago).'
                        color = '#A6A6B0'
                        wage_delta_label.style(f'color: {color}')
                        wage_hint_label.set_text(msg)
                    else:
                        # Calculated < actual: current skills are lower than at the birthday — too low.
                        wage_delta_label.style('color: #F87171')
                        wage_hint_label.set_text(
                            f'{pct:+.1f}% — too low: the birthday wage needs more skill than you entered now.'
                            + (f' {main} should be at least ≈ {implied:.2f} (now {skills_now[main]:.2f}).' if implied else ''))

                    # Quick check: do these skills fit his TSI and wage?
                    def chip(ok, text):
                        bg, fg = ('rgba(52,211,153,.15)', '#34D399') if ok else ('rgba(248,113,113,.15)', '#F87171')
                        return f'<span class="tt-chip" style="background:{bg}; color:{fg};">{"✓" if ok else "✗"} {text}</span>'
                    parts = []
                    if actual_tsi > 0:
                        if abs(tsi_delta) < 1:   # the TSI has to match exactly, not just fall between floor and ceiling
                            parts.append(chip(True, 'TSI matches exactly'))
                        elif calc_tsi_low <= actual_tsi <= calc_tsi_high:
                            parts.append(chip(False, f'TSI off by {abs(tsi_delta):,.0f}'))
                        elif actual_tsi < calc_tsi_low:
                            parts.append(chip(False, f'TSI too high by {calc_tsi_low - actual_tsi:,.0f}'))
                        else:
                            parts.append(chip(False, f'TSI too low by {actual_tsi - calc_tsi_high:,.0f}'))
                    if actual_wage > 0:
                        tol = actual_wage * 0.01
                        # the wage was set on his birthday: since then training can add a little (about 2.5% a week)
                        grow = actual_wage * min(0.40, max(0.02, 0.025 * days / 7.0)) if wage_is_stale else 0.0
                        if abs(wage_delta) <= tol:
                            parts.append(chip(True, 'Wage fits'))
                        elif 0 < wage_delta <= grow:
                            parts.append(chip(True, 'Wage fits (he trained since his birthday)'))
                        elif wage_delta < 0:
                            parts.append(chip(False, f'Wage too low by €{-wage_delta:,.0f}'))
                        else:
                            parts.append(chip(False, f'Wage too high by €{wage_delta:,.0f}'))
                    range_html.set_content(''.join(parts))
                    _ok, _bad, _warn = '#34D399', '#F87171', '#F0A24A'
                    if actual_tsi > 0:
                        _tp = tsi_delta / actual_tsi * 100
                        _tok = abs(tsi_delta) < 1   # exact match only
                        tsi_delta_label.set_text('0 ✓' if _tok else f'{tsi_delta:+,.0f} ({_tp:+.2f}%) ✗')
                        tsi_delta_label.style(f'color: {_ok if _tok else _bad}')
                    if actual_wage > 0:
                        _wok = any('Wage fits' in p_ for p_ in parts)
                        wage_delta_label.set_text(('+' if wage_delta >= 0 else '−') + f'€{abs(wage_delta):,.0f} ({pct:+.1f}%) ' + ('✓' if _wok else '✗'))
                        wage_delta_label.style(f'color: {_ok if _wok else _bad}')
                    for _lab, _d in ((htms_delta_label, htms_delta), (htms28_delta_label, htms28_delta)):
                        _lab.style(f'color: {_ok if abs(_d) < 1 else _warn}')

                    # Update HTMS UI
                    htms_val_label.set_text(f'{htms_curr:,.0f}')
                    htms_delta_label.set_text(f'{get_sign(htms_delta)}{htms_delta:,.0f}')
                    htms_delta_label.style(f'color: {get_color(htms_delta)}')
                    
                    # Update HTMS28 UI
                    htms28_val_label.set_text(f'{htms28:,.0f}' if isinstance(htms28, (int, float)) else str(htms28))
                    if isinstance(htms28, (int, float)):
                        htms28_delta_label.set_text(f'{get_sign(htms28_delta)}{htms28_delta:,.0f}')
                        htms28_delta_label.style(f'color: {get_color(htms28_delta)}')
                    else:
                        htms28_delta_label.set_text(f'{get_sign(htms28_delta)}{htms28_delta:,.0f}')
                        htms28_delta_label.style(f'color: {get_color(htms28_delta, True)}')
                    for _lab, _d in ((htms_delta_label, htms_delta), (htms28_delta_label, htms28_delta)):
                        _lab.style(f'color: {"#34D399" if abs(_d) < 1 else "#F0A24A"}')

                # Run once sequentially on startup
                update_calc()
                # Recalculate when the profile numbers change too, not only the skills.
                for _inp in (age_input, days_input, spec_input, tsi_input, wage_input, htms_input, htms28_input):
                    _inp.on_value_change(lambda _: update_calc())

                def do_save_all(quiet=False):
                    if quiet and is_new:
                        return   # a new player is saved with the button (he needs a name first)
                    if quiet and not (name_input.value or '').strip():
                        return   # don't autosave while the name is being retyped
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        
                        # Clean numbers: skills and form/stamina to 3 decimals.
                        live_skills = {k: round(float(inp.value or 0.0), 3) for k, inp in subskill_inputs.items()}
                        live_vorm = round(float(vorm_input.value or 6.0), 3)
                        live_cond = round(float(cond_input.value or 6.0), 3)
                        
                        htms_ability = calculate_htms_ability(live_skills['GK'], live_skills['DE'], live_skills['PM'], live_skills['WI'], live_skills['Pas'], live_skills['SC'], live_skills['SH'])
                        htms_potential = calculate_htms_potential(int(age_input.value), int(days_input.value), htms_ability)
                        
                        if auto_sync_cb.value:
                            htms_persist = htms_ability
                            htms28_persist = htms_potential if isinstance(htms_potential, (int, float)) else htms_input.value
                        else:
                            htms_persist = htms_input.value
                            htms28_persist = htms28_input.value
                        
                        if is_new:
                            if not name_input.value.strip():
                                ui.notify('⚠️ Enter a player name first.', type='warning')
                                conn.close()
                                return
                            cursor.execute(
                                'INSERT INTO skills_data (username, PlayerID, Speler, Positie, Leeftijd, "dag(en)", Specialiteit, Vorm, Conditie, TSI, Loon, HTMS, HTMS28, Nationality, Leiderschap, Injuries, "Transfer-listed", "National team player", GK, DE, PM, WI, Pas, SC, SH, Ervaring, "Foreign") '
                                'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);',
                                (user, int(id_input.value), name_input.value.strip(), pos_input.value, int(age_input.value), int(days_input.value),
                                 spec_input.value, live_vorm, live_cond, int(tsi_input.value), int(wage_input.value),
                                 float(htms_persist), float(htms28_persist), nat_input.value, float(lead_input.value), float(inj_input.value),
                                 ('Transfer-listed' if transfer_input.value == 'Transfer-listed' else ''), int(nt_input.value),
                                 live_skills['GK'], live_skills['DE'], live_skills['PM'], live_skills['WI'], live_skills['Pas'], live_skills['SC'], live_skills['SH'], float(xp_input.value or 0),
                                 1 if foreign_cb.value else 0)
                            )
                        else:
                            cursor.execute(
                                'UPDATE skills_data SET PlayerID=?, Speler=?, Positie=?, Leeftijd=?, "dag(en)"=?, Specialiteit=?, Vorm=?, Conditie=?, TSI=?, Loon=?, HTMS=?, HTMS28=?, Nationality=?, Leiderschap=?, Injuries=?, "Transfer-listed"=?, "National team player"=?, GK=?, DE=?, PM=?, WI=?, Pas=?, SC=?, SH=?, Ervaring=?, "Foreign"=? WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                                (int(id_input.value), name_input.value.strip(), pos_input.value, int(age_input.value), int(days_input.value), spec_input.value,
                                 live_vorm, live_cond, int(tsi_input.value), int(wage_input.value),
                                 float(htms_persist), float(htms28_persist), nat_input.value, float(lead_input.value), float(inj_input.value),
                                 ('Transfer-listed' if transfer_input.value == 'Transfer-listed' else ''), int(nt_input.value),
                                 live_skills['GK'], live_skills['DE'], live_skills['PM'], live_skills['WI'], live_skills['Pas'], live_skills['SC'], live_skills['SH'],
                                 float(xp_input.value or 0), 1 if foreign_cb.value else 0, user, save_state['name'])
                            )
                            save_state['name'] = name_input.value.strip()
                        conn.commit(); conn.close()
                        load_user_db.clear()

                        ref_msg = ''
                        if ref_sync_cb.value:
                            ref_row = {
                                'PlayerID': int(id_input.value or 0), 'Speler': name_input.value.strip(),
                                'Nationality': nat_input.value, 'Positie': pos_input.value, 'Specialiteit': spec_input.value,
                                'Leeftijd': int(age_input.value), 'dag(en)': int(days_input.value),
                                'TSI': int(tsi_input.value), 'Loon': int(wage_input.value),
                                'HTMS': float(htms_persist),
                                'HTMS28': float(htms28_persist) if isinstance(htms28_persist, (int, float)) else 0.0,
                                'GK': live_skills['GK'], 'DE': live_skills['DE'], 'PM': live_skills['PM'],
                                'WI': live_skills['WI'], 'Pas': live_skills['Pas'], 'SC': live_skills['SC'], 'SH': live_skills['SH'],
                            }
                            ref_result = sync_player_to_reference_db(ref_row, user, source='estimator')
                            if ref_result == 'updated':
                                ref_msg = ' 🗄️ Reference DB entry updated with corrected skills.'
                            elif ref_result == 'inserted':
                                ref_msg = ' 🗄️ Added to Reference DB.'

                        save_state['dirty'] = False
                        save_lbl.set_text(f"✓ Saved {time.strftime('%H:%M:%S')}")
                        if not quiet:
                            ui.notify(f'✅ Player & Skills saved successfully!{ref_msg}', type='positive')
                        if is_new:
                            picker_state['is_new'] = False
                            picker_state['selected'] = name_input.value.strip()
                            player_select.set_value(name_input.value.strip())
                            render_content.refresh()
                        # Don't refresh for existing players — avoids reloading
                        # stale data from DB before Turso write propagates
                    except Exception as e:
                        ui.notify(f'Error saving profile: {e}', type='negative')


                # Autosave (existing players): about a second after the last change, without a confirmation.
                save_state.update(name=selected, dirty=False, t=0.0)

                def _mark_dirty(_=None):
                    if is_new:
                        return
                    save_state['dirty'] = True
                    save_state['t'] = time.monotonic()
                    save_lbl.set_text('… saving')

                def _autosave_tick():
                    if save_state['dirty'] and time.monotonic() - save_state['t'] >= 1.0:
                        do_save_all(quiet=True)
                ui.timer(0.5, _autosave_tick)
                for _inp in [id_input, name_input, pos_input, spec_input, age_input, days_input, tsi_input, wage_input,
                             xp_input, lead_input, nat_input, inj_input, transfer_input, nt_input, htms_input, htms28_input,
                             vorm_input, cond_input, foreign_cb, *subskill_inputs.values()]:
                    _inp.on_value_change(_mark_dirty)

                # Profile links in the title line of Player Profiles (when a PlayerID is filled in).
                def render_player_links(_=None):
                    links_box.clear()
                    ht_url, htp_url = player_links(id_input.value)
                    if ht_url:
                        with links_box:
                            # White on the blue profile header (blue links were unreadable there).
                            ui.link('🔗 View in Hattrick', ht_url, new_tab=True).classes('text-sm').style('color:#FAFAFA !important;')
                            ui.link('🔗 View in Hattrick Portal', htp_url, new_tab=True).classes('text-sm').style('color:#FAFAFA !important;')
                render_player_links()
                id_input.on_value_change(render_player_links)

                # The player as HT forum markup.

                def forum_markup():
                    return player_forum_markup(
                        (name_input.value or 'Player').strip(), id_input.value, age_input.value, days_input.value,
                        xp_input.value, lead_input.value, tsi_input.value, pos_input.value, wage_input.value,
                        spec_input.value, inj_input.value, vorm_input.value, cond_input.value,
                        {k: float(inp.value or 0) for k, inp in subskill_inputs.items()})


        def on_add_new():
            picker_state['is_new'] = True
            picker_state['selected'] = None
            player_select.set_value(None)
            render_content.refresh()

        def on_player_pick(e):
            if e.value:
                picker_state['is_new'] = False
                # Convert label back to real player name
                picker_state['selected'] = label_to_name(e.value)
                render_content.refresh()

        add_new_btn.on_click(on_add_new)
        player_select.on_value_change(on_player_pick)
        render_content()
        if _filter_restore['a']:
            abroad_cb.set_value(True)
        if _filter_restore['f'] is not None and _filter_restore['f'] != filter_select.value:
            filter_select.set_value(_filter_restore['f'])