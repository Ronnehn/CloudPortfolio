import pandas as pd
from nicegui import ui, app, run
from shell import markup_block, copy_text, apply_theme, require_login, render_sidebar, ACCENT, ACCENT_DARK, tt_card, page_title, opt_panel, opt_hint, form_stamina_color, player_card
from i18n import tr, trf
import math
import json
from data_layer import get_user_pref, set_user_pref
from data_layer import (
    load_user_db, get_db_connection, get_country_richtskills, get_richtskills_for_age,
    find_similar_players, safe_float, safe_int,
    get_watchlists, sync_player_to_reference_db,
    get_country_age_richtskills, save_country_age_richtskills, delete_country_age_richtskills,
)
from richtskills_data import estimate_age_richtskills
from ht_engine import lookup_wage as H_lookup_wage, fast_rebalance, stamina_max, calculate_tsi_for_form
from ht_engine import (
    forum_stamina,
    normalize_position,
    get_flag, normalize_nationality,
    clean_spec, sh_fallback_for, skill_level_label, auto_solve_subskills,
    estimate_htms_from_profile, hattrick_skill_band, SPECIALITY_OPTIONS,
    HATTRICK_SKILL_WORD_OPTIONS, HATTRICK_SKILL_WORDS, birthday_wage_range,
    calculate_htms_potential, player_links, player_forum_markup, healthy_tsi, INJURY_TSI_PER_WEEK, tsi_after_birthday,
)
try:   # newer ht_engine.py only; without it the page still works, just without the non-target estimate
    from ht_engine import non_target_profile
except ImportError:
    non_target_profile = None
try:
    from ht_engine import full_training_gain
except ImportError:
    full_training_gain = None
try:   # newer ht_engine.py only: all whole-level outcomes that fit TSI + wage, ranked by a template
    from ht_engine import enumerate_outcomes, outcome_build, nt_outcome_prior, training_outcome_prior
except ImportError:
    enumerate_outcomes = outcome_build = nt_outcome_prior = training_outcome_prior = None
try:
    from ht_engine import wage_fit_build
except ImportError:
    wage_fit_build = None
try:   # newer ht_engine.py: split the combinations into groups (focused / in between / all-round)
    from ht_engine import outcome_split
except ImportError:
    outcome_split = None
try:   # every result shows his TSI exactly (no '-1 vs target')
    from ht_engine import snap_tsi
    from ht_engine import edge_safe
except ImportError:
    snap_tsi = None
try:   # Hattrick specialty icons next to names and in the Specialty dropdown
    import spec_icons as SI
except ImportError:
    SI = None
try:   # usual training per position, the default answer to "current training" for Other players
    from ht_engine import POS_TRAINING
except ImportError:
    POS_TRAINING = {}
TRAIN_SKILLS = {'DE': 'Defending', 'PM': 'Playmaking', 'WI': 'Winger', 'Pas': 'Passing', 'SC': 'Scoring'}
try:   # training order / spare-level options / team shape / match ratings, and the Hattrick page readers
    import ht_extras as HX
    import ht_paste as HP
except ImportError:
    HX = HP = None
# Tactic presets: fill in the trained skills (main first) for a typical role.
TACTIC_PRESETS = {'DE+PM+SC+Pas': '🛡️ Pressing defender: DE + PM + SC + Pas (Pas about equal to SC)',
                  'DE+Pas': '⚡ Counter-attack defender: DE + Pas',
                  'DE+Pas+PM': '⚡ Counter-attack defender + midfield: DE + Pas + PM',
                  'PM+DE+SC': '🎯 Long-shot player (29+): PM + DE + SC, high set pieces'}
LONGSHOT_SETUP = 'PM+DE+SC'
TRACKER_FRESH_DAYS = 42   # Portal tracker skills older than this (vs the page's last update) are not filled in
UNKNOWN_SETUP = 'unknown'
# Usual training setups (main first) offered in one dropdown for Other players; 'custom' opens three dropdowns.
COMMON_SETUPS = [('DE', 'PM'), ('DE', 'PM', 'Pas'), ('DE', 'WI'), ('DE', 'WI', 'PM'), ('DE',),
                 ('PM', 'Pas'), ('PM', 'DE'), ('PM', 'Pas', 'SC'), ('PM',),
                 ('WI', 'PM'), ('WI', 'PM', 'Pas'), ('WI',),
                 ('SC', 'Pas'), ('SC', 'PM'), ('SC', 'Pas', 'PM'), ('SC',), ('Pas', 'PM'), ('Pas', 'SC')]
SINCE_OPTIONS = {'main': 'His main training', 'none': 'No training', 'main2': 'Main + second training (half each)',
                 'DE': 'Defending', 'PM': 'Playmaking', 'WI': 'Winger', 'Pas': 'Passing', 'SC': 'Scoring'}


def _setup_key(skills):
    return '+'.join(skills)


def training_setups(pos):
    """{key: label} with the usual training of this position first."""
    usual = tuple(POS_TRAINING.get(pos, ()))[:2]
    out = {}
    if usual:
        out[_setup_key(usual)] = ' + '.join(usual) + f' (usual for {pos})'
    if HX is not None and hasattr(HX, 'mixed_setups'):   # mixed: two second skills trained in turns
        for m, a, b in HX.mixed_setups(pos):
            out[f'{m}+{a}/{b}'] = f'{m} + {a} / {b} mixed (both second skills about equal)'
    if HX is not None:   # near the top: unknown training and the tactic presets
        out[UNKNOWN_SETUP] = "❔ unknown: use the shape of my players"
        for k, lab in TACTIC_PRESETS.items():
            out[k] = lab
    for st in COMMON_SETUPS:
        out.setdefault(_setup_key(st), ' + '.join(st) if len(st) > 1 else f'{st[0]} only (no second training)')
    out['custom'] = 'custom… (up to 4 skills)'
    return out
try:   # newer ht_engine.py only: solve with the contribution table (+ tactic accent) instead of the target skills
    from ht_engine import POSITION_ORDERS, ACCENTS
except ImportError:
    POSITION_ORDERS, ACCENTS = None, None
ORDER_NAMES = {'K': 'Keeper', 'NCD': 'Normal CD', 'CDTW': 'CD towards wing', 'OCD': 'Offensive CD',
               'NWB': 'Normal WB', 'DWB': 'Defensive WB', 'OWB': 'Offensive WB', 'WBTM': 'WB towards middle',
               'NW': 'Normal winger', 'DW': 'Defensive winger', 'OW': 'Offensive winger', 'WTM': 'Winger towards middle',
               'NIM': 'Normal IM', 'OIM': 'Offensive IM', 'IMTW': 'IM towards wing', 'DIM': 'Defensive IM',
               'NFW': 'Normal FW', 'FTW': 'FW towards wing', 'PNF': 'Powerful FW', 'TDFW': 'Defensive FW (technical)'}
from richtskills_data import RICHTSKILLS_DEFAULT

# Colour of the non-target estimate (no country / custom target skills), distinct from the regular options.
NT_COLOR, NT_DARK = '#3E8E74', '#1F4D40'
OC_COLOR, OC_DARK = '#1F4A75', '#0C2036'   # all-outcomes estimate (same deep blue as the menu)
OC_ALT = '#2F6EA8'           # its alternative builds (lighter)
LAST_OUTCOME_TEMPLATE = {}   # template of the last All Combos solve (for tests; not shown)
SHOW_SHAPE_OPTION = False


class QuietSlider(ui.slider):
    """A slider whose value is not echoed back by the server while dragging (the echo made the thumb jump back
    and look stuck on slower connections)."""
    LOOPBACK = False


# Live preview of an option card while a slider is dragged, computed in the browser (no server round trip):
# TSI grows with S^2 (S = sum of w*(skill-1)^3) and with sqrt((form-1)(stamina-1)), so the free skills' scale
# follows in one step. The server checks the wage and the allowed range when the slider is released.
LIVE_JS = '''
<style>
.tt-skbar { position: relative; }
.tt-skbar .q-slider__track { background: #262730; border-radius: 5px; }
.tt-skbar .q-slider__inner { background: transparent; }
.tt-skbar .q-slider__selection { background: #24782E; border-radius: 5px; }
.tt-skbar.tt-follow .q-slider__selection { background: repeating-linear-gradient(45deg, #24782E 0 6px, #3F8F4A 6px 12px); }
.tt-skbar .q-slider__thumb { color: #FAFAFA; }
.tt-fs .q-slider__selection { background: var(--fs) !important; }
.tt-fs .q-slider__thumb { color: var(--fs) !important; }
.tt-fs .q-slider__track { background: #262730; }
.tt-skbar.tt-locked .q-slider__thumb { color: #CBD5E1; }
.tt-word { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); font-size: 11px; color: #FAFAFA;
           pointer-events: none; z-index: 2; white-space: nowrap; }
</style>
<script>
window.ttCfg = window.ttCfg || {};
// Live preview while a bar (or form / stamina) is dragged, in the browser (no server round trip): TSI grows with
// S^2 (S = sum of w*(skill-1)^3) and with sqrt((form-1)(stamina-1)); the skills that are not locked follow in one
// step. The server checks the wage and stores the result when the slider is released.
window.ttLive = function (key, which, v) {
  const c = window.ttCfg[key]; if (!c) return;
  c.cur[which] = Number(v);
  const el = (id) => document.getElementById('c' + id);
  const f = c.cur.f, st = c.cur.c;
  const target = c.k0 * Math.pow(((c.f0 - 1) * (c.c0 - 1)) / Math.max((f - 1) * (st - 1), 1e-6), 0.25);
  const fixedSet = new Set(c.locked); if (c.order.includes(which)) fixedSet.add(which);
  let fixed = 0, free0 = 0; const vals = {};
  for (const k of c.order) {
    if (fixedSet.has(k)) { vals[k] = c.cur[k]; fixed += c.w[k] * Math.pow(Math.max(c.cur[k] - 1, 0), 3); }
    else free0 += c.w[k] * Math.pow(Math.max(c.base[k] - 1, 0), 3);
  }
  const rem = target - fixed;
  const stat = el(c.ids.status);
  if (rem < 0) { if (stat) { stat.innerText = c.t.toomuch; stat.style.color = '#F87171'; } return; }
  const g = free0 > 0 ? Math.cbrt(rem / free0) : 0;
  for (const k of c.order) if (!(k in vals)) vals[k] = 1 + Math.max(c.base[k] - 1, 0) * g;
  for (const k of c.order) {
    const x = Math.max(0, Math.min(vals[k], 20)), n = Math.max(0, Math.min(20, Math.floor(x)));
    if (k !== which) {
      const s = el(c.ids.sl[k]);
      if (s) {
        const pct = (x / 20 * 100).toFixed(2) + '%';
        const sel = s.querySelector('.q-slider__selection'); if (sel) sel.style.width = pct;
        const th = s.querySelector('.q-slider__thumb'); if (th) th.style.left = pct;
      }
    }
    const w = el(c.ids.word[k]); if (w) w.innerText = n + ' - ' + c.words[n];
    const t = el(c.ids.val[k]); if (t) { t.innerText = vals[k].toFixed(3); t.style.color = fixedSet.has(k) ? '' : '#FBBF24'; }
  }
  const fc = el(c.ids.fc); if (fc) fc.innerText = c.t.form + ' ' + f.toFixed(3) + '  ' + c.t.cond + ' ' + st.toFixed(3);
  if (which === 'f' || which === 'c') { const l = el(c.ids[which + 'lab']); if (l) l.innerText = (which === 'f' ? c.t.form : c.t.stamina) + ' ' + Number(v).toFixed(2); }
  if (stat) { stat.innerText = c.t.release; stat.style.color = '#9CA3AF'; }
};
</script>
'''   # solver skill shape switch (Target skills / Contribution table): hidden


def get_suffix(val):
    n = max(0, min(20, int(math.floor(float(val)))))
    return tr(f"- {HATTRICK_SKILL_WORDS[n]}")

@ui.page('/autosolver')
def autosolver_page():
    apply_theme()
    ui.add_head_html(LIVE_JS)
    user = require_login()
    if not user:
        return

    df_raw = load_user_db(user)
    render_sidebar(user, '/autosolver')

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_title('/autosolver')

        # ── Filter bar ────────────────────────────────────────────────────────
        all_player_names = df_raw['Speler'].dropna().tolist() if not df_raw.empty else []

        # Build display labels with position: "Rene Schigt (NFW)"
        def player_label(name):
            if df_raw.empty: return name
            rows = df_raw[df_raw['Speler'] == name]
            if rows.empty: return name
            pos = str(rows.iloc[0].get('Positie', '') or '')
            age = str(int(rows.iloc[0].get('Leeftijd', 0)) if rows.iloc[0].get('Leeftijd') else '')
            return f"{name} ({pos}, {age})" if pos else name

        def names_to_labels(names):
            return {player_label(n): n for n in names}

        all_labels = names_to_labels(all_player_names)
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

        # One row, like the Estimator: filter -> player -> abroad only.
        with ui.row().classes('w-full gap-3 items-center mb-4 no-wrap tt-pbar'):
            filter_select = ui.select(
                filter_opts, value='🌍 All Players',
                label='Filter by Country / Watchlist'
            ).classes('w-56').style('flex-shrink:0;')
            player_select = ui.select(
                ['-- Select a player --'] + list(all_labels.keys()),
                value='-- Select a player --',
                label='Player'
            ).classes('flex-1 min-w-0')
            abroad_cb = ui.checkbox('✈️ Abroad only').style('flex-shrink:0;')
            if SI is not None and not df_raw.empty and 'Specialiteit' in df_raw.columns:
                _sp = dict(zip(df_raw['Speler'], df_raw['Specialiteit']))
                SI.player_select(player_select, {lab: _sp.get(n) for lab, n in all_labels.items()})

        def on_filter_change(e):
            filtered = get_filtered_names()
            filtered_labels = names_to_labels(filtered)
            player_select.options = ['-- Select a player --'] + list(filtered_labels.keys())
            player_select.value = '-- Select a player --'
            player_select.update()

        # Remember the filter in the database (follows you to every device).
        _f0, _a0 = get_user_pref(user, 'autosolver_filter', None), get_user_pref(user, 'autosolver_abroad', False)
        if (_f0 and _f0 in filter_opts and _f0 != filter_select.value) or _a0:
            if _f0 in filter_opts:
                filter_select.value = _f0
            abroad_cb.value = bool(_a0)
            on_filter_change(None)
        filter_select.on_value_change(on_filter_change)
        abroad_cb.on_value_change(on_filter_change)
        filter_select.on_value_change(lambda e: set_user_pref(user, 'autosolver_filter', e.value))
        abroad_cb.on_value_change(lambda e: set_user_pref(user, 'autosolver_abroad', bool(e.value)))

        content = ui.column().classes('w-full')

        # Reverse map: label → real player name
        def label_to_name(label):
            if not label or label == '-- Select a player --': return label
            # Try current all_labels first, then filtered
            return all_labels.get(label, label.split(' (')[0] if ' (' in label else label)

        @ui.refreshable
        def render_content():
            content.clear()
            selected_label = player_select.value
            selected = label_to_name(selected_label)
            is_empty = (selected_label == '-- Select a player --' or not selected_label)

            if is_empty:
                s_id, s_pos, s_age, s_days, s_spec, s_nat = 0, 'NFW', 20, 15, 'None', 'Netherlands'
                s_vorm, s_cond, s_tsi, s_wage, s_htms, s_htms28 = 6.0, 6.0, 15000, 2100, 500, 1900
                s_htms_est = False
                s_sh = sh_fallback_for(s_pos, s_age, s_days, 'None')
                s_skills = {'GK': 0.0, 'DE': 0.0, 'PM': 0.0, 'WI': 0.0, 'Pas': 0.0, 'SC': 0.0}
                s_foreign = False
                s_inj = 0.0
            else:
                p = df_raw[df_raw['Speler'] == selected].iloc[0]
                s_foreign = bool(safe_int(p.get('Foreign', 0)))
                s_id = safe_int(p.get('PlayerID', 0))
                s_pos = str(p.get('Positie', 'NFW') or 'NFW')
                s_pos = normalize_position(s_pos)   # e.g. a stored lineup role 'CD' -> 'NCD'
                s_age, s_days = safe_int(p.get('Leeftijd', 20)), safe_int(p.get('dag(en)', 0))
                s_spec, s_nat = clean_spec(p.get('Specialiteit', 'None')), str(p.get('Nationality', 'Netherlands') or 'Netherlands')
                # Hattrick shows form/condition as whole levels. Older "Apply" runs stored the
                # solver's own guess (e.g. 6.22); using that again would feed the solver its
                # previous answer, so start from the displayed level.
                s_vorm = float(int(safe_float(p.get('Vorm', 6.0))))
                s_cond = float(int(safe_float(p.get('Conditie', 6.0))))
                s_tsi, s_wage = safe_int(p.get('TSI', 15000)), safe_int(p.get('Loon', 2100))
                s_inj = safe_float(p.get('Injuries', 0.0))
                s_htms, s_htms28 = safe_int(p.get('HTMS', 185)), safe_int(p.get('HTMS28', 0))
                # Estimated HTMS (from an earlier solve or the import) is shown, but not used as a target.
                s_htms_est = bool(safe_int(p.get('HTMS_est', 0)))
                s_sh = safe_float(p.get('SH', sh_fallback_for(s_pos, s_age, s_days, s_spec)))
                s_skills = {
                    'GK': safe_float(p.get('GK', 0.0)), 'DE': safe_float(p.get('DE', 0.0)), 'PM': safe_float(p.get('PM', 0.0)),
                    'WI': safe_float(p.get('WI', 0.0)), 'Pas': safe_float(p.get('Pas', 0.0)), 'SC': safe_float(p.get('SC', 0.0)),
                    'SH': s_sh
                }

            with content:
                ht_url, htp_url = player_links(s_id) if not is_empty else (None, None)
                _info = (f'{s_pos} · {get_flag(s_nat)} {s_nat}' + (' · ✈️ ' + tr('abroad') if s_foreign else '')
                         + (' · 🩹 ' + trf('{} wk injured', f'{s_inj:g}') if s_inj > 0 else ''))
                _links = [('🔗 View in Hattrick', ht_url), ('🔗 View in Hattrick Portal', htp_url)] if ht_url else None
                ui.add_head_html('<style>'
                    '.tt-asline { border-top: 1px solid #3A3F52; }'
                    '.tt-htms.tt-unk .q-field__native { opacity: .35; }'
                    '.tt-unksw { font-size: 11px; color: #9AA3B2; }'
                    '.tt-unksw .q-toggle__label { padding-left: 4px; }'
                    '.tt-adv > .q-expansion-item__container > .q-item { background: transparent !important; padding: 0 !important; min-height: 30px; }'
                    '.tt-adv > .q-expansion-item__container > .q-item .q-focus-helper { display: none; }'
                    '.tt-ssec { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; color: #2F6EA8; font-size: 12px;'
                    '  font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }'
                    '.tt-ssec:after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, #2F6EA8, rgba(47,110,168,.08)); }'
                    '.tt-trpanel { background: rgba(47,110,168,.10); border: 1px solid rgba(47,110,168,.35); border-radius: 8px; }'
                    '</style>')
                with player_card('🎯 Target Parameters', None if is_empty else selected, _info, _links):
                    with ui.grid(columns=4).classes('w-full gap-4 grid-cols-2 md:grid-cols-4'):
                        all_pos_options = list(RICHTSKILLS_DEFAULT.keys())
                        if 'SHWB' not in all_pos_options: all_pos_options.append('SHWB')
                        if s_pos not in all_pos_options: all_pos_options.append(s_pos)
                        pos_input = ui.select(all_pos_options, value=s_pos, label='Position').classes('w-full')
                        age_input = ui.number('Age', value=s_age, min=17, max=45, format='%d').classes('w-full')
                        spec_input = ui.select(SPECIALITY_OPTIONS, value=(s_spec if s_spec in SPECIALITY_OPTIONS else 'None'), label='Specialty').classes('w-full')
                        if SI is not None:
                            SI.spec_select(spec_input)
                        days_input = ui.number('Days', value=s_days, min=0, max=111, format='%d').classes('w-full')
                        
                        cond_input = ui.number('Condition', value=s_cond, min=1.0, max=9.0, step=0.1).classes('w-full')
                        cond_input.props(f'suffix="{get_suffix(s_cond)}"')
                        cond_input.on_value_change(lambda e: cond_input.props(f'suffix="{get_suffix(e.value or 0.0)}"'))
                            
                        vorm_input = ui.number('Form', value=s_vorm, min=1.0, max=8.0, step=0.1).classes('w-full')
                        vorm_input.props(f'suffix="{get_suffix(s_vorm)}"')
                        vorm_input.on_value_change(lambda e: vorm_input.props(f'suffix="{get_suffix(e.value or 0.0)}"'))

                        tsi_input = ui.number('Target Actual TSI', value=s_tsi, step=100, format='%d').classes('w-full')
                        wage_input = ui.number('Target Actual Wage (€)', value=s_wage, step=50, format='%d').classes('w-full')

                        # HTMS: an 'unknown' switch inside the box (on = the solver estimates it, the number is greyed)
                        htms_input = ui.number('Target Actual HTMS', value=s_htms, step=1, format='%d').classes('w-full tt-htms')
                        with htms_input.add_slot('append'):
                            htms_unknown_cb = ui.switch('unknown', value=True).props('dense size=xs').classes('tt-unksw') \
                                .tooltip('On: HTMS is not known and is estimated. Switch off to solve with this HTMS.')
                        htms28_input = ui.number('Target Actual HTMS28', value=s_htms28, step=1, format='%d').classes('w-full tt-htms')
                        with htms28_input.add_slot('append'):
                            htms28_unknown_cb = ui.switch('unknown', value=True).props('dense size=xs').classes('tt-unksw') \
                                .tooltip('On: HTMS28 is not known and is estimated. Switch off to solve with this HTMS28.')

                        def _unk_look(inp, unk):
                            if unk:
                                inp.props('readonly'); inp.classes(add='tt-unk')
                            else:
                                inp.props(remove='readonly'); inp.classes(remove='tt-unk')
                        htms_unknown_cb.on_value_change(lambda e: _unk_look(htms_input, e.value))
                        htms28_unknown_cb.on_value_change(lambda e: _unk_look(htms28_input, e.value))
                        _unk_look(htms_input, True); _unk_look(htms28_input, True)
                        with ui.element('div').classes('w-full tt-swbox'):
                            foreign_cb = ui.switch('✈️ Abroad (+20% wage)', value=s_foreign).props('dense')
                        ui.button('💾 Save to player', on_click=lambda: save_params()).props('outline no-caps') \
                            .classes('w-full tt-gridbtn') \
                            .tooltip('Store these values (position, age, days, specialty, form, stamina, TSI, wage, '
                                     'injury, and HTMS when not unknown) in the player\'s data')


                    def solve_tsi():
                        """TSI the solver works with: the healthy TSI when the injury box is ticked."""
                        t = float(tsi_input.value or 0)
                        if inj_cb.value:
                            t = healthy_tsi(t, inj_weeks.value)
                        if bday_cb.value:
                            t = tsi_after_birthday(t, int(age_input.value or 0), pos_input.value)
                        return t


                    # ── Solve options: grouped panels with switches ──────────────────────────────
                    _opt_panel, _hint = opt_panel, opt_hint

                    # What kind of player is this? Decides the skill template everything is built on.
                    _type0 = 'NT'   # every player opens as NT
                    _npos0 = normalize_position(s_pos)
                    _tr0 = POS_TRAINING.get(_npos0, ('SC', 'Pas'))
                    # Other: his training so far, as one of the usual setups (or custom: three dropdowns).
                    _setups = training_setups(_npos0)
                    # Imported whole skill levels (your own players): his real top 3 skills are the best guess for
                    # his training, whatever position he is listed at (AFRN: 2.06 -> 0.66 levels off).
                    _imp = [s_skills.get(k, 0.0) for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC')] + [s_sh]
                    _imp_top = []
                    if (not is_empty and all(v and float(v) >= 1 and float(v) == int(float(v)) for v in _imp)
                            and [int(v) for v in _imp] != [1, 5, 5, 5, 4, 5, 1]):
                        _imp_top = sorted(TRAIN_SKILLS, key=lambda k: -float(s_skills.get(k, 0.0)))[:3]
                    _tr_main = _imp_top[0] if _imp_top else _tr0[0]
                    with ui.column().classes('w-full gap-3 mt-5'):
                        with ui.row().classes('w-full items-center justify-between gap-3 no-wrap'):
                            ui.label('Player type & training').classes('tt-ssec')
                            # Which skill shape is used (follows the player type, not selectable).
                            with ui.row().classes('items-center gap-2 no-wrap'):
                                ui.label('Skill shape').classes('text-xs text-gray-400')
                                shape_tog = ui.toggle({'shape': '🎯 Target'}, value='shape') \
                                    .props('no-caps unelevated dense toggle-color=primary').style('pointer-events:none;')
                        with ui.grid(columns=4).classes('w-full gap-4 grid-cols-2 md:grid-cols-4 items-center'):
                            with ui.row().classes('items-center gap-3 no-wrap col-span-2'):
                                ui.label('Player type').classes('text-sm font-semibold')
                                type_sel = ui.toggle({'NT': '🏆 NT', 'U22': '🦁 U22', 'Other': '🧭 Other'}, value=_type0) \
                                    .props('no-caps unelevated toggle-color=primary') \
                                    .tooltip('NT / U22: trained like a national-team player, solved with the target skills for '
                                             'his age. Other: trained differently (e.g. your own club players): tell what he '
                                             'trains and the solve is built around that.')
                            # Trained since the birthday (all player types).
                            since_sel = ui.select(SINCE_OPTIONS, value='main', label='Trained since birthday') \
                                .classes('w-full col-span-2').tooltip(
                                    'The wage was set on his birthday; TSI is today. Which training he had since then. '
                                    'None: today\'s skills are the birthday skills.')
                        # Other: his training so far, as one of the usual setups (or custom: four drop-downs).
                        with ui.column().classes('w-full gap-3 p-3 tt-trpanel') as train_row:
                            ui.label('🧭 His training').classes('text-xs font-bold uppercase') \
                                .style(f'color:{ACCENT}; letter-spacing:0.12em;')
                            with ui.grid(columns=4).classes('w-full gap-4 grid-cols-2 md:grid-cols-4 items-center'):
                                setup_sel = ui.select(_setups, value=('custom' if _imp_top else _setup_key(_tr0[:2])), label='Training') \
                                    .classes('w-full col-span-2').tooltip('The skills he is (mostly) trained in, main first')
                                ui.label('Pick a usual setup, or custom… to choose up to 4 skills (main first).') \
                                    .classes('text-xs text-gray-400 col-span-2')
                            with ui.grid(columns=4).classes('w-full gap-4 grid-cols-2 md:grid-cols-4') as custom_row:
                                tr1_sel = ui.select(TRAIN_SKILLS, value=(_imp_top[0] if _imp_top else _tr0[0]),
                                                    label='Main training').classes('w-full')
                                tr2_sel = ui.select({'': '— none', **TRAIN_SKILLS}, value=(_imp_top[1] if _imp_top else _tr0[1]),
                                                    label='Second training').classes('w-full')
                                tr3_sel = ui.select({'': '— none', **TRAIN_SKILLS}, value=(_imp_top[2] if _imp_top else ''),
                                                    label='Third training').classes('w-full')
                                tr4_sel = ui.select({'': '— none', **TRAIN_SKILLS}, value='',
                                                    label='Fourth training').classes('w-full') \
                                    .tooltip('Optional: a 4th skill he clearly has (multiskill players)')
                    shape_row = None   # solver skill shape switch: only when SHOW_SHAPE_OPTION (made below)
                    custom_row.bind_visibility_from(setup_sel, 'value', backward=lambda v: v == 'custom')

                    def trained_skills():
                        """Trained skills in order (main first)."""
                        if setup_sel.value == 'custom':
                            return list(dict.fromkeys(t for t in (tr1_sel.value, tr2_sel.value, tr3_sel.value,
                                                                  tr4_sel.value) if t))
                        if setup_sel.value == UNKNOWN_SETUP:
                            return []
                        return [t for t in str(setup_sel.value).replace('/', '+').split('+') if t in TRAIN_SKILLS]

                    def mixed_training():
                        """'PM+DE/Pas': the two second skills were trained in turns (about equal)."""
                        return type_sel.value == 'Other' and '/' in str(setup_sel.value or '')

                    def since_skills():
                        v = since_sel.value
                        main_tr = ((trained_skills() if type_sel.value == 'Other' else [])
                                   or list(POS_TRAINING.get(normalize_position(pos_input.value), ('SC', 'Pas'))))
                        if v == 'none':
                            return []
                        if v == 'main':
                            return main_tr[:1]
                        if v == 'main2':
                            return main_tr[:2]
                        return [v]

                    def _type_change(e=None):
                        v = type_sel.value
                        train_row.set_visibility(v == 'Other')
                        if shape_row is not None:
                            shape_row.set_visibility(v != 'Other')
                        shape_tog.set_options({'shape': '🧭 Training' if v == 'Other' else '🎯 Target'}, value='shape')
                    type_sel.on_value_change(_type_change)

                    def _pos_training(e):
                        _p = normalize_position(e.value)
                        _t = POS_TRAINING.get(_p)
                        setup_sel.set_options(training_setups(_p), value=_setup_key(_t[:2]) if _t else setup_sel.value)
                        if _t:
                            tr1_sel.set_value(_t[0]); tr2_sel.set_value(_t[1]); tr3_sel.set_value(''); tr4_sel.set_value('')
                    pos_input.on_value_change(_pos_training)

                    def save_foreign(e):
                        # Stored straight away: it changes how skills are read from the wage.
                        if is_empty:
                            return
                        conn = get_db_connection()
                        conn.cursor().execute('UPDATE skills_data SET "Foreign"=? WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                                              (1 if e.value else 0, user, selected))
                        conn.commit(); conn.close()
                        load_user_db.clear()
                        ui.notify(f"🌍 {selected}: {'abroad' if e.value else 'not abroad'} — saved", type='positive')
                    foreign_cb.on_value_change(save_foreign)

                    adv_exp = ui.expansion(value=False).classes('w-full mt-5 tt-adv').props('dense')
                    with adv_exp.add_slot('header'):
                        ui.label('⚙️ Advanced settings').classes('tt-ssec')
                    with adv_exp, ui.grid(columns=2).classes('w-full gap-3 pt-3 grid-cols-1 md:grid-cols-2 items-stretch'):
                        with _opt_panel('🩹', 'TSI correction').classes('gap-2'):
                            with ui.row().classes('w-full items-center justify-between gap-2 no-wrap'):
                                with ui.column().classes('gap-1'):
                                    inj_cb = ui.switch('Injured', value=bool(s_inj and s_inj > 0)).props('dense') \
                                        .tooltip('Hattrick shows a lowered TSI while injured: solve with the healthy TSI')
                                    _hint('Solves with his healthy TSI')
                                inj_weeks = ui.number('Weeks', value=float(s_inj or 0), min=0, max=15, step=1, format='%d') \
                                    .props('dense').classes('w-24')
                            bday_cb = ui.switch('TSI from before birthday', value=False).props('dense').tooltip(
                                'Hattrick applies the new age to TSI only at the first weekly update after the birthday. '
                                'Switch on when the TSI has not changed since the birthday (days 0-6).')
                            _hint('TSI not updated yet since his birthday (days 0-6)')

                        with _opt_panel('🗄️', 'Reference DB').classes('gap-2'):
                            use_ref_sw = ui.switch('Compare with peers', value=False).props('dense') \
                                .tooltip('Off: solve from TSI, wage and the age profile only, without reference players')
                            _hint('Also looks at similar players with known skills')
                            ref_sync_cb = ui.switch('Sync applied skills', value=True).props('dense') \
                                .tooltip('When you apply a result, also store it in the Reference DB')
                            _hint('Applying a result also stores it there')


                    # Injured players: Hattrick shows a lowered TSI (healthy / (1 + 0.15 x weeks)). With the
                    # box ticked the solver works with the healthy TSI worked back from it.
                    with ui.row().classes('items-center gap-4 mt-1 w-full'):
                        inj_weeks.bind_enabled_from(inj_cb, 'value')
                        if s_inj and float(s_inj) > 0:
                            adv_exp.set_value(True)   # injured: show the TSI correction
                        inj_note = ui.label('').classes('text-sm').style('color:#FBBF24;')

                        def _inj_note(*_):
                            try:
                                t0 = float(tsi_input.value or 0)
                                parts = []
                                if inj_cb.value and float(inj_weeks.value or 0) > 0:
                                    parts.append(f"injury x {1 + INJURY_TSI_PER_WEEK * float(inj_weeks.value):.2f}")
                                if bday_cb.value:
                                    parts.append(f"new age x {tsi_after_birthday(1.0, int(age_input.value or 0), pos_input.value):.2f}")
                                if parts:
                                    inj_note.set_text(f"Solving with TSI {solve_tsi():,.0f} ({', '.join(parts)})")
                                elif int(days_input.value or 0) <= 6 and int(age_input.value or 0) >= 28:
                                    inj_note.set_text('Birthday less than a week ago: if TSI has not changed since, switch on "TSI from before birthday".')
                                else:
                                    inj_note.set_text('')
                            except (TypeError, ValueError):
                                inj_note.set_text('')
                        inj_cb.on_value_change(_inj_note)
                        inj_weeks.on_value_change(_inj_note)
                        bday_cb.on_value_change(_inj_note)
                        tsi_input.on_value_change(_inj_note)
                        days_input.on_value_change(_inj_note)
                    _inj_note()

                    # Save the values above to the player (e.g. after correcting a wrong TSI or wage). Not automatic:
                    # trying other values here for a solve should never change the player by accident.
                    def save_params():
                        if is_empty:
                            ui.notify('⚠️ Select an existing player first.', type='warning')
                            return
                        try:
                            vals = {'Positie': pos_input.value, 'Leeftijd': int(age_input.value or 0),
                                    'dag(en)': int(days_input.value or 0), 'Specialiteit': spec_input.value,
                                    'Vorm': float(vorm_input.value or 0), 'Conditie': float(cond_input.value or 0),
                                    'TSI': float(tsi_input.value or 0), 'Loon': float(wage_input.value or 0),
                                    'Injuries': float(inj_weeks.value or 0) if inj_cb.value else 0.0}
                            if not htms_unknown_cb.value:
                                vals.update(HTMS=float(htms_input.value or 0), HTMS_est=0)
                            if not htms28_unknown_cb.value:
                                vals['HTMS28'] = float(htms28_input.value or 0)
                            conn = get_db_connection()
                            conn.cursor().execute(
                                'UPDATE skills_data SET ' + ', '.join(f'"{k}"=?' for k in vals) +
                                ' WHERE LOWER(username)=LOWER(?) AND Speler=?;', (*vals.values(), user, selected))
                            conn.commit(); conn.close()
                            load_user_db.clear()
                            ui.notify(f'💾 {selected}: values saved', type='positive')
                        except Exception as ex:
                            ui.notify(f'Save failed: {ex}', type='negative')


                    class _NoRef:   # the solver code reads "don't use peers"
                        @property
                        def value(self):
                            return not use_ref_sw.value
                    no_ref_cb = _NoRef()

                    shape_sel = order_sel = accent_sel = None
                    # The contribution-table skill shape tested worse than the target skills everywhere, so it is not
                    # offered on the page any more (set SHOW_SHAPE_OPTION = True to bring the switch back).
                    if POSITION_ORDERS and SHOW_SHAPE_OPTION:
                        def _order_opts(pos):
                            return {o: f'{o} · {ORDER_NAMES.get(o, o)}'
                                    for o in POSITION_ORDERS.get(normalize_position(pos), ['NFW'])}
                        with adv_exp, ui.row().classes('items-center gap-4 w-full pt-3') as shape_row:
                            ui.label('Solver skill shape').classes('text-sm font-semibold').tooltip(
                                'For the solver options only (not All Combos). Target skills tested best; the '
                                'contribution table is here for comparison.')
                            with ui.row().classes('items-center gap-4'):
                                shape_sel = ui.toggle({'target': '🎯 Target skills', 'contribution': '📊 Contribution table'},
                                                      value='target').props('no-caps unelevated toggle-color=primary')
                                _oo = _order_opts(pos_input.value)
                                order_sel = ui.select(_oo, value=next(iter(_oo)), label='Order').props('dense').classes('w-60')
                                accent_sel = ui.select(ACCENTS, value='none', label='Tactic accent').props('dense').classes('w-44') \
                                    .tooltip('Counter-attack: defenders with more passing (passing counts twice defending). '
                                             'Long shots: more scoring and set pieces for every outfield player.')
                                order_sel.bind_visibility_from(shape_sel, 'value', backward=lambda v: v == 'contribution')
                                accent_sel.bind_visibility_from(shape_sel, 'value', backward=lambda v: v == 'contribution')

                        def _on_pos_orders(e):
                            _o = _order_opts(e.value)
                            order_sel.set_options(_o, value=next(iter(_o)))
                        pos_input.on_value_change(_on_pos_orders)
                    _type_change()

                # A saved Country Target Skills entry replaces the built-in profile for this
                # country / age / position and steers every skill the solver can't see directly.
                # Show it, and let the user ignore or remove it (e.g. an SHWB target with more
                # passing than winger made the solver hand out passing instead of winger).
                custom_state = {'ignore': False}
                _sk_order = ['DE', 'SH', 'WI', 'PM', 'Pas', 'SC', 'GK']

                @ui.refreshable
                def render_custom_target():
                    try:
                        age_v = int(age_input.value or 0)
                    except (TypeError, ValueError):
                        return
                    pos_v = pos_input.value
                    custom = (get_country_age_richtskills(s_nat, age_v) or {}).get(pos_v)
                    if not custom:
                        return
                    builtin = estimate_age_richtskills(age_v, spec_input.value, s_nat).get(pos_v, {})
                    with ui.card().classes('w-full p-4 mb-4 border border-amber-600 bg-amber-900/10'):
                        ui.label(f'⚠️ Custom target skills saved for {get_flag(s_nat)} {s_nat} / age {age_v} / {pos_v}'
                                 ).classes('text-md font-semibold text-amber-300')
                        ui.label('The solver aims at these values instead of the built-in profile. Skills it cannot '
                                 'see directly (winger, passing, set pieces) follow them closely.').classes('text-xs text-gray-400 mb-2')
                        cols = [{'name': 'row', 'label': '', 'field': 'row', 'align': 'left'}] + \
                               [{'name': k, 'label': k, 'field': k, 'align': 'center'} for k in _sk_order]
                        rows = [dict(row='Custom (saved)', **{k: f"{float(custom.get(k, 1.0)):.1f}" for k in _sk_order}),
                                dict(row='Built-in profile', **{k: f"{float(builtin.get(k, 1.0)):.1f}" for k in _sk_order})]
                        ui.table(columns=cols, rows=rows).props('dense flat').classes('w-full')
                        with ui.row().classes('items-center gap-4 mt-2'):
                            ui.switch('Ignore it for this solve (use the built-in profile)',
                                        value=custom_state['ignore'],
                                        on_change=lambda e: custom_state.__setitem__('ignore', e.value))

                            def remove_custom():
                                cur = dict(get_country_age_richtskills(s_nat, age_v) or {})
                                cur.pop(pos_v, None)
                                if cur:
                                    save_country_age_richtskills(s_nat, age_v, cur)
                                else:
                                    delete_country_age_richtskills(s_nat, age_v)
                                custom_state['ignore'] = False
                                ui.notify(f'↩️ Removed custom target for {s_nat} / age {age_v} / {pos_v}. '
                                          'Other ages may have one too: check Country Target Skills.', type='positive')
                                render_custom_target.refresh()

                            ui.button('🗑️ Remove this custom target', on_click=remove_custom).props('outline color=amber')

                render_custom_target()
                age_input.on_value_change(lambda e: render_custom_target.refresh())
                pos_input.on_value_change(lambda e: render_custom_target.refresh())
                spec_input.on_value_change(lambda e: render_custom_target.refresh())

                paste_state = {'ratings': None, 'what': '', 'tracker': None, 'salary': None}
                _skey = f'salary::{selected}' if not is_empty else None
                if _skey and HP is not None:
                    _ss = get_user_pref(user, _skey, None)
                    if isinstance(_ss, dict) and len(_ss) >= 3:
                        paste_state['salary'] = {int(a): float(w) for a, w in _ss.items()}
                _tkey = f'portal::{selected}' if not is_empty else None
                if _tkey and HP is not None:
                    _st = get_user_pref(user, _tkey, None)
                    if isinstance(_st, dict) and _st.get('history'):
                        try:
                            import datetime as _dt0
                            _st = dict(_st, updated=_dt0.date.fromisoformat(_st['updated']) if _st.get('updated') else None,
                                       history=[dict(h, date=_dt0.date.fromisoformat(h['date']) if h.get('date') else None)
                                                for h in _st['history']])
                            paste_state['tracker'] = _st
                        except Exception:
                            pass
                _rkey = f'ratings::{selected}' if not is_empty else None
                if _rkey and HP is not None:
                    _saved = get_user_pref(user, _rkey, None)
                    if isinstance(_saved, dict) and _saved.get('kind'):
                        paste_state['ratings'] = _saved
                        paste_state['what'] = (f"Saved match ratings ({_saved.get('source', 'paste')}, "
                                               f"{_saved.get('date', '?')}) — paste again to replace, Clear to remove")

                def _save_ratings(r, source):
                    if not _rkey:
                        return
                    import datetime as _dt
                    r = dict(r, source=source, date=_dt.date.today().strftime('%d-%m-%Y'))
                    paste_state['ratings'] = r
                    try:
                        set_user_pref(user, _rkey, r)
                    except Exception:
                        pass
                if HP is not None:
                    with tt_card('📋 Paste from Hattrick'):
                        ui.label("Paste a page you copied with Ctrl+A, Ctrl+C: his player page, his match history, a team's "
                                 "Players table or his Hattrick Portal page. Half a page works too. Match ratings only count "
                                 "for 🧭 Other players.").classes('text-xs text-gray-400')
                        paste_box = ui.textarea(placeholder='Paste here…').props('outlined dense input-style="max-height:160px"') \
                            .classes('w-full').style('font-family:monospace; font-size:12px;')
                        with ui.row().classes('items-center gap-2 w-full'):
                            read_btn = ui.button('🔍 Read').props('unelevated no-caps')
                            portal_btn = ui.button('🌐 Load from Hattrick Portal').props('outline no-caps')
                            if not htp_url:
                                portal_btn.disable()
                            ui.label('🔒 Need login first').classes('text-xs text-gray-400').tooltip(
                                'Log in on the Hattrick Portal in your browser first, otherwise the page can\'t be loaded.')
                            clear_btn = ui.button('Clear').props('flat no-caps')
                            paste_status = ui.label('').classes('text-sm')
                        found_area = ui.column().classes('w-full gap-1')

                    def _render_tracker():
                        info = paste_state.get('tracker')
                        if not info or HX is None:
                            return
                        sm = HX.tracker_summary(info, solve_tsi())
                        if not sm:
                            return
                        with found_area:
                            upd = info.get('updated')
                            ui.label(f"Hattrick Portal: {info.get('name', '')}, {len(sm['rows'])} TSI updates"
                                     + (f" (page from {upd.strftime('%d-%m-%Y')})" if upd else '')
                                     + '. Saved with this player.').classes('text-sm font-semibold')
                            cols = [{'name': c, 'label': l, 'field': c, 'align': 'left' if c == 'd' else 'right'}
                                    for c, l in (('d', 'Date'), ('f', 'Form'), ('c', 'Stamina'), ('t', 'TSI'),
                                                 ('w', 'Wage €'), ('i', 'Skill index'), ('b', ''))]
                            data = [{'d': r['date'].strftime('%d-%m-%Y') if r['date'] else '?', 'f': r['form'], 'c': r['stam'],
                                     't': f"{r['tsi']:,}", 'w': f"{r['salary'] / info['rate']:,.0f}" if (r.get('salary') and info.get('rate')) else '',
                                     'i': f"{r['rel']:.1f}", 'b': 'since birthday' if r['since'] else ''} for r in sm['rows']]
                            ui.table(columns=cols, rows=data, row_key='d').props('dense flat').classes('w-full')
                            ui.label('Skill index is his TSI without the effect of form, stamina and age. 100 is the first '
                                     'update after his birthday. If it stays flat, his skills didn\'t change.').classes('text-xs text-gray-400')
                            if int(info.get('age') or 0) > 35:
                                msg = 'Not used for players over 35: most of them hardly play anymore, so form and stamina drop and his TSI says little about his skills.'
                            elif int(info.get('age') or 0) < 28:
                                msg = ('Not used for players under 28: they still get better from training every week, so '
                                       'the TSI changes come from training too, not only from form.')
                            elif not sm['points']:
                                msg = ('Not used: this page is older than the TSI above. Load it again.' if sm['rows']
                                       else 'Not used: there are no TSI updates since his birthday.')
                            elif not sm.get('hf'):
                                msg = f"Not used yet: it needs 3 TSI updates since his birthday and has {len(sm['points'])}."
                            else:
                                hf = sm['hf']
                                msg = (f"Used for 🎲 All Combos. From {hf['n']} TSI updates since his birthday, his real form "
                                       f"is about {hf['form']:.2f} (between {hf['lo']:.2f} and {hf['hi']:.2f}).")
                                msg += (" His skills haven't dropped since then, so his wage should match his skills now."
                                        if sm.get('stable') else f" His skill index is {sm['drop'] * 100:.0f}% lower than at his birthday.")
                            ui.label(msg).classes('text-xs').style('color:#60A5FA;')

                    def _render_salary():
                        sal = paste_state.get('salary')
                        if not sal or HX is None or not hasattr(HX, 'salary_hint'):
                            return
                        try:
                            main = (POS_TRAINING.get(normalize_position(pos_input.value)) or ('PM',))[0]
                        except Exception:
                            main = 'PM'
                        h = HX.salary_hint(sal, spec_input.value, None, main if main in ('DE', 'PM', 'WI', 'Pas', 'SC') else 'PM')
                        with found_area:
                            ui.label(f"Salary history: {len(sal)} birthdays ({min(sal)}–{max(sal)}). Saved with this player.") \
                                .classes('text-sm font-semibold')
                            if not h:
                                return
                            ages = sorted(h['shares'])
                            if ages:
                                ui.label('Share of each season that went into his main skill: '
                                         + '  '.join(f"{a}: {h['shares'][a] * 100:.0f}%" for a in ages)).classes('text-xs text-gray-400')
                            msg = (f"About {h['missing']:.1f} levels of main-skill training went into other skills. "
                                   f"Used in the 🎲 Spare levels options (🧭 Other players).")
                            if h.get('untrained'):
                                msg += f" Exactly the same wage after {', '.join(str(a) for a in h['untrained'])}: not trained then."
                            ui.label(msg).classes('text-xs').style('color:#60A5FA;')

                    def _render_found():
                        found_area.clear()
                        _render_tracker()
                        _render_salary()
                        r = paste_state['ratings']
                        if not r:
                            return
                        rows = HX.ratings_summary(r) if HX else []
                        with found_area:
                            ui.label(paste_state['what']).classes('text-sm font-semibold')
                            cols = [{'name': 'p', 'label': 'Position', 'field': 'p', 'align': 'left'},
                                    {'name': 'n', 'label': 'Matches used', 'field': 'n'},
                                    {'name': 'a', 'label': 'Avg ★', 'field': 'a'}, {'name': 'm', 'label': 'Max ★', 'field': 'm'},
                                    {'name': 'u', 'label': 'Used', 'field': 'u'}]
                            data = []
                            for q, n, a, m in rows:
                                use = q in HX.RATING_OFFSET and (r.get('kind') == 'history' or
                                                                 (r['player']['pos'][q]['minutes'] >= 45))
                                data.append({'p': HP.ORDER_LABEL.get(q, q), 'n': n, 'a': f'{a:.1f}', 'm': f'{m:g}',
                                             'u': '✓' if use else '– (keeper / short spells)'})
                            ui.table(columns=cols, rows=data, row_key='p').props('dense flat').classes('w-full')
                            if r.get('kind') == 'history' and r.get('matches'):
                                m0 = r['matches'][0]
                                ui.label(f"Newest match: {m0['age']} ({m0['days']}) · TSI {m0['tsi']:,.0f} · form {m0['form']} · "
                                         f"stamina {m0['stam']} · experience {m0['xp']} · loyalty {m0['loy']}").classes('text-xs text-gray-400')
                            if r.get('kind') == 'table':
                                ui.label('Tip: for young players select only recent matches in the table; a whole season '
                                         'mixes in older, lower ratings.').classes('text-xs text-gray-400')

                    def _clear_paste():
                        if _rkey and paste_state.get('ratings'):
                            try:
                                set_user_pref(user, _rkey, None)
                            except Exception:
                                pass
                        if _tkey and paste_state.get('tracker'):
                            try:
                                set_user_pref(user, _tkey, None)
                            except Exception:
                                pass
                        paste_state['ratings'] = None
                        paste_state['tracker'] = None
                        if _skey and paste_state.get('salary'):
                            try:
                                set_user_pref(user, _skey, None)
                            except Exception:
                                pass
                        paste_state['salary'] = None
                        paste_state['what'] = ''
                        paste_box.set_value('')
                        paste_status.set_text('')
                        found_area.clear()

                    def _use_table_player(tab, name):
                        paste_state['ratings'] = {'kind': 'table', 'player': tab[name]}
                        _save_ratings(paste_state['ratings'], 'team table')
                        paste_state['what'] = f"Found: team table — {name} · saved with this player"
                        paste_status.set_text(f'✓ Team table: {name}')
                        paste_status.style('color:#34D399;')
                        _render_found()

                    def _use_portal(info, how):
                        done = []
                        for key, inp, lab in (('age', age_input, 'age'), ('days', days_input, 'days'), ('tsi', tsi_input, 'TSI'),
                                              ('wage', wage_input, 'wage'), ('form', vorm_input, 'form'),
                                              ('stamina', cond_input, 'stamina')):
                            if info.get(key) is not None:
                                inp.set_value(info[key])
                                done.append(lab + (f" €{info['wage']:,.0f} (the Portal shows {info['wage_text']}; 10 kr = €1)"
                                                   if key == 'wage' and info.get('wage_text', '').endswith('kr') else ''))
                        if info.get('spec') in SPECIALITY_OPTIONS:
                            spec_input.set_value(info['spec'])
                            done.append('specialty')
                        if info.get('wage_text'):
                            foreign_cb.set_value(bool(info.get('foreign')))
                            done.append('plays abroad: ' + ('yes' if info.get('foreign') else 'no'))
                        # Players in a Portal tracker: their skill levels and HTMS. Only when the tracker saw the skills
                        # recently; older levels may have gone up since and would mislead the solver.
                        _tsk, _td = info.get('tracker_skills'), info.get('tracker_date')
                        _ref_day = info.get('updated') or info.get('training_date')
                        _age_days = (_ref_day - _td).days if (_td and _ref_day) else None
                        if _tsk and _age_days is not None and _age_days <= TRACKER_FRESH_DAYS:
                            for _sk, (_lvl, _sub) in _tsk.items():
                                if _sk in skill_bands and 0 <= int(_lvl) < len(HATTRICK_SKILL_WORD_OPTIONS):
                                    known_skills[_sk][1].set_value(True)          # sub-level still unknown ...
                                    skill_bands[_sk].set_value(HATTRICK_SKILL_WORD_OPTIONS[int(_lvl)])   # ... within this level
                            done.append(f"skill levels from the tracker (seen {_td.strftime('%d-%m-%Y')})")
                            if info.get('htms'):
                                htms_input.set_value(info['htms']); htms_unknown_cb.set_value(False)
                                done.append(f"HTMS {info['htms']:.0f}")
                            if info.get('htms28'):
                                htms28_input.set_value(info['htms28']); htms28_unknown_cb.set_value(False)
                        elif _tsk and _td:
                            done.append(f"not the tracker skills: seen {_td.strftime('%d-%m-%Y')}, too long ago (they may have gone up since)")
                        paste_state['tracker'] = info
                        if _tkey:
                            try:
                                set_user_pref(user, _tkey, dict(info, updated=info['updated'].isoformat() if info.get('updated') else None,
                                                                history=[dict(h, date=h['date'].isoformat() if h.get('date') else None)
                                                                         for h in info.get('history', [])]))
                            except Exception:
                                pass
                        paste_status.set_text(f"✓ {how}{(' — ' + info['name']) if info.get('name') else ''}: filled in " + ', '.join(done))
                        paste_status.style('color:#34D399;')
                        _render_found()

                    async def _load_portal():
                        if not htp_url:
                            return
                        portal_btn.disable()
                        paste_status.set_text('Loading Hattrick Portal… (the site is slow, this can take up to a minute)')
                        paste_status.style('color:#9CC3E6;')

                        # The Portal only shows players it already has. A player it doesn't have yet gives a "was last
                        # seen having a pint at the local pub" page; opening his page on the Portal in your own browser
                        # makes the Portal fetch him. So: try, and if he's unknown, open his page in a new tab and keep
                        # checking for a minute.
                        urls = [htp_url, htp_url.replace('/Tracker/Player.aspx', '/Player.aspx')]

                        def _get(u):
                            import requests
                            r = requests.get(u, timeout=(15, 75), headers={'User-Agent': 'Tooltrick (Hattrick toolkit; one page on request)'})
                            r.raise_for_status()
                            return r.text

                        async def _try():
                            why = ''
                            for u in urls:
                                try:
                                    html = await run.io_bound(_get, u)
                                except Exception as e:
                                    why = 'timeout' if 'imeout' in str(e) else 'error'
                                    continue
                                got = HP.parse_portal(html)
                                if got:
                                    return got, ''
                                why = 'unknown' if 'local pub' in html else 'empty'
                            return None, why
                        import asyncio as _aio
                        try:
                            info, why = await _try()
                            if not info and why == 'unknown':
                                found_area.clear()
                                with found_area:
                                    ui.link('🔗 Open his Hattrick Portal page (if your browser blocked the new tab)', urls[1], new_tab=True) \
                                        .classes('text-sm')
                                for i in range(12):
                                    paste_status.set_text(f"Hattrick Portal doesn't have him yet. His Portal page is open in a new "
                                                          f"tab, which makes the Portal fetch him. Checking again… ({(i + 1) * 5} s)")
                                    paste_status.style('color:#FBBF24;')
                                    await _aio.sleep(5)
                                    info, why2 = await _try()
                                    if info:
                                        break
                        finally:
                            portal_btn.enable()
                        if not info:
                            if why == 'unknown':
                                paste_status.set_text("✗ Hattrick Portal still doesn't have him. Wait until his Portal page shows "
                                                      "his TSI, then click 🌐 Load again.")
                            else:
                                paste_status.set_text("✗ Couldn't load the page" + (' (the site took too long)' if why == 'timeout' else '')
                                                      + ". Try again, or open it with the link above and paste it here (Ctrl+A, Ctrl+C).")
                            paste_status.style('color:#F87171;')
                            return
                        if s_id and info.get('id') and int(info['id']) != int(s_id):
                            paste_status.set_text('✗ The page is about another player')
                            paste_status.style('color:#F87171;')
                            return
                        _use_portal(info, 'Hattrick Portal')

                    def _read_paste():
                        text = paste_box.value or ''
                        kind = HP.detect(text)
                        found_area.clear()
                        if kind is None:
                            paste_status.set_text('✗ Nothing recognised: copy his player page, his match history, a team\'s Players table or his Hattrick Portal page')
                            paste_status.style('color:#F87171;')
                            return
                        if kind == 'portal':
                            _use_portal(HP.parse_portal(text), 'Hattrick Portal page')
                            return
                        if kind == 'salaries':
                            info = HP.parse_player_page(text)
                            sal = HP.parse_salaries(text)
                            ab = HP.salary_abroad(info, sal)
                            if ab is not None:
                                info['foreign'] = ab
                            paste_state['salary'] = sal
                            if _skey:
                                try:
                                    set_user_pref(user, _skey, {str(a): w for a, w in sal.items()})
                                except Exception:
                                    pass
                            kind = 'player'
                            _sal_note = f"salary history ({len(sal)} birthdays, saved with this player)"
                        else:
                            _sal_note = ''
                        if kind == 'player':
                            info = HP.parse_player_page(text) if not _sal_note else info
                            done = []
                            for key, inp, lab in (('age', age_input, 'age'), ('days', days_input, 'days'), ('tsi', tsi_input, 'TSI'),
                                                  ('wage', wage_input, 'wage'), ('form', vorm_input, 'form'),
                                                  ('stamina', cond_input, 'stamina')):
                                if key in info:
                                    inp.set_value(info[key])
                                    done.append(lab)
                            if info.get('spec') and info['spec'] in SPECIALITY_OPTIONS:
                                spec_input.set_value(info['spec'])
                                done.append('specialty')
                            if 'wage' in info:
                                foreign_cb.set_value(bool(info.get('foreign')))
                                done.append('plays abroad: ' + ('yes' if info.get('foreign') else 'no'))
                            if _sal_note:
                                done.append(_sal_note)
                            paste_status.set_text(f"✓ Player page{(' — ' + info['name']) if info.get('name') else ''}: filled in "
                                                  + ', '.join(done))
                            paste_status.style('color:#34D399;')
                            _render_found()
                            return
                        if kind == 'history':
                            parts = HP.split_players(text)
                            part, who = text, ''
                            if len(parts) > 1:
                                pid = int(s_id or 0)
                                if pid in parts:
                                    part, who = parts[pid], selected
                                else:
                                    part = next(iter(parts.values()))
                                    who = '(first player in the paste)'
                            ms = HP.parse_match_history(part)
                            paste_state['ratings'] = {'kind': 'history', 'matches': ms}
                            _save_ratings(paste_state['ratings'], 'match history')
                            skipped = sum(1 for m in ms if m['mixed'])
                            paste_state['what'] = (f"Found: match history {who} — {len(ms)} matches read"
                                                   + (f", {skipped} with a position switch not used" if skipped else '')
                                                   + ' · the newest 14 are used · saved with this player')
                            paste_status.set_text(f'✓ Match history: {len(ms)} matches')
                            paste_status.style('color:#34D399;')
                            _render_found()
                            return
                        tab = HP.parse_team_table(text)
                        names = list(tab)
                        want = (selected or '').strip().lower() if not is_empty else ''
                        hit = next((n for n in names if n.lower() == want), None) or \
                            next((n for n in names if want and want.split()[-1] in n.lower()), None)
                        if hit:
                            _use_table_player(tab, hit)
                            return
                        paste_status.set_text(f'Team table with {len(names)} players: pick the player')
                        paste_status.style('color:#FBBF24;')
                        with found_area:
                            ui.select(names, label='Player in the table',
                                      on_change=lambda e: _use_table_player(tab, e.value)).props('dense').classes('w-72')
                    read_btn.on_click(_read_paste)
                    clear_btn.on_click(_clear_paste)
                    portal_btn.on_click(_load_portal)
                    if htp_url:
                        # Browsers only allow a new tab straight from the click itself (not later from the server), so the
                        # Portal page opens here, in the browser. Opening it is also what makes the Portal fetch / update him.
                        _pu = htp_url.replace('/Tracker/Player.aspx', '/Player.aspx')
                        portal_btn.on('click', js_handler=f"() => window.open('{_pu}', '_blank')")
                    if paste_state['ratings'] or paste_state['tracker'] or paste_state.get('salary'):
                        _render_found()
                        paste_status.set_text('✓ Saved ' + ' and '.join(x for x, y in (('match ratings', paste_state['ratings']),
                                                                                       ('Hattrick Portal history', paste_state['tracker']),
                                                                                       ('salary history', paste_state.get('salary'))) if y) + ' loaded')
                        paste_status.style('color:#34D399;')

                with tt_card('🔗 Known Subskills (from Skill Estimator)'):
                    with ui.row().classes('w-full justify-end items-center mb-2'):
                        
                        def toggle_all_unknowns():
                            new_val = not all(cb.value for _, cb in known_skills.values())
                            for _, cb in known_skills.values():
                                cb.set_value(new_val)

                        ui.button('☑️ Toggle All Unknowns', on_click=toggle_all_unknowns).props('outline sm').classes('text-xs')

                    known_skills = {}
                    skill_bands = {}
                    sh_holder = {'value': s_sh}

                    # Same look as the Estimator: one row per skill with a bar out of 20. Known: the
                    # exact value; unknown: optionally a level (band) to stay within.
                    def known_bar_html(v, word=None, faded=False):
                        v = max(0.0, min(float(v or 0.0), 20.0))
                        fill = '#3B4A5A' if faded else ACCENT
                        txt = word if word is not None else skill_level_label(v)
                        return (f'<div style="position:relative;height:24px;border-radius:6px;background:#262730;overflow:hidden">'
                                f'<div style="position:absolute;left:0;top:0;bottom:0;width:{v / 20 * 100:.1f}%;background:{fill}"></div>'
                                f'<span style="position:absolute;left:8px;top:0;line-height:24px;font-size:12px;color:#FAFAFA">{txt}</span></div>')

                    # Imported whole skill levels (Hattrick CSV of your own players: e.g. DE 12, PM 12) are real
                    # levels: fill them in as the level, so the solver only works out the sublevels. Not for the
                    # import's fill-in values when a file had no skills (GK 1, DE 5, PM 5, WI 5, PS 4, SC 5, SP 1),
                    # and not for decimals (estimates from an earlier solve).
                    _lv = [s_skills.get(k, 0.0) for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH')]
                    levels_known = (not is_empty and all(v and float(v) >= 1 and float(v) == int(float(v)) for v in _lv)
                                    and [int(v) for v in _lv] != [1, 5, 5, 5, 4, 5, 1])
                    _fill_btn_row = ui.row().classes('w-full items-center gap-2 mb-1')

                    with ui.grid(columns=2).classes('w-full gap-x-8 gap-y-0 grid-cols-1 md:grid-cols-2'):
                        for sk, sk_name in [('GK', 'Keeper'), ('DE', 'Defending'), ('PM', 'Playmaking'), ('WI', 'Winger'),
                                            ('Pas', 'Passing'), ('SC', 'Scoring'), ('SH', 'Set pieces')]:
                            initial_val = s_skills.get(sk, 0.0)
                            is_unk = True   # default: all unknown (untick a skill to use it as known)
                            with ui.row().classes('w-full items-center gap-3 no-wrap py-1').style('border-bottom:1px solid #3B3B4D;'):
                                ui.label(sk_name).classes('text-sm').style('width:84px; flex-shrink:0;')
                                bar = ui.html(known_bar_html(0, '(unknown)', True) if is_unk else known_bar_html(initial_val)).classes('flex-1 min-w-0')
                                val_input = ui.number(value=(initial_val if initial_val > 0 else 5.0), min=0.0, max=25.0, step=0.1).props('dense').style('width:112px; flex-shrink:0;')
                                word_select = ui.select(['(unknown)'] + HATTRICK_SKILL_WORD_OPTIONS, value='(unknown)').props('dense').style('width:150px; flex-shrink:0;')
                                unknown_cb = ui.checkbox('❓', value=is_unk).props('dense').tooltip('Unknown')

                            val_input.bind_visibility_from(unknown_cb, 'value', backward=lambda v: not v)
                            word_select.bind_visibility_from(unknown_cb, 'value')

                            def on_val_change(e, bar=bar):
                                bar.set_content(known_bar_html(float(e.value or 0.0)))
                            val_input.on_value_change(on_val_change)

                            def on_word_change(e, bar=bar):
                                if e.value and e.value != '(unknown)':
                                    lv = int(e.value.split(' - ')[0])
                                    bar.set_content(known_bar_html(lv + 0.5, f"{lv} - {HATTRICK_SKILL_WORDS[lv]} (level)", True))
                                else:
                                    bar.set_content(known_bar_html(0, '(unknown)', True))
                            word_select.on_value_change(on_word_change)

                            def on_unk_change(e, bar=bar, num_in=val_input, ws=word_select):
                                if e.value:
                                    ws.set_value('(unknown)')
                                    bar.set_content(known_bar_html(0, '(unknown)', True))
                                else:
                                    bar.set_content(known_bar_html(float(num_in.value or 0.0)))
                            unknown_cb.on_value_change(on_unk_change)

                            known_skills[sk] = (val_input, unknown_cb)
                            skill_bands[sk] = word_select

                    # Imported whole skill levels (own players): not filled in by default (everything starts
                    # unknown); one click puts them in as levels, so the solver only works out the sublevels.
                    if levels_known:
                        def _fill_levels():
                            for _sk, _ws in skill_bands.items():
                                _v = float(s_skills.get(_sk, 0.0) or 0.0)
                                if _v >= 1:
                                    _ws.set_value(HATTRICK_SKILL_WORD_OPTIONS[max(0, min(int(_v), len(HATTRICK_SKILL_WORD_OPTIONS) - 1))])
                            ui.notify('📥 Imported skill levels filled in', type='positive')

                        def _clear_levels():
                            for _ws in skill_bands.values():
                                _ws.set_value('(unknown)')
                        with _fill_btn_row:
                            ui.button('📥 Use imported skill levels', on_click=_fill_levels).props('outline dense no-caps') \
                                .tooltip('This player has whole skill levels from your import: fill them in, so the solver '
                                         'only works out the sublevels')
                            ui.button('Clear', on_click=_clear_levels).props('flat dense no-caps')

                solved_state = {'done': False}
                results_area = ui.column().classes('w-full')
                similar_area = ui.column().classes('w-full')

                def solver_richtskills(active_richtskills):
                    """The solver's target skills. Other: his training instead of the target skills (trained skills at
                    their levels, the rest leftovers), so the solver options are built around how he was trained.
                    Tested: AFRN main skill 2.3 -> 0.2 levels off; All Combos stays the best card for these players."""
                    if type_sel.value != 'Other' or training_outcome_prior is None:
                        return active_richtskills
                    pos = normalize_position(pos_input.value)
                    age = int(age_input.value)
                    prof = dict((active_richtskills or {}).get(pos) or
                                estimate_age_richtskills(age, spec_input.value, s_nat).get(pos, {}))
                    if not prof:
                        return active_richtskills
                    peers = own_position_players(pos)
                    own = {k: sum(pp[k] for pp in peers) / len(peers) for k in peers[0]} if len(peers) >= 2 else None
                    tr = trained_skills() or [POS_TRAINING.get(pos, ('SC', 'Pas'))[0]]
                    prior, _ = training_outcome_prior(tr, prof, pos, age, own)
                    prof.update(prior)
                    return {**(active_richtskills or {}), pos: prof}

                def own_position_players(pos):
                    """Your imported players at this position with real whole skill levels (not the selected one)."""
                    out = []
                    if df_raw.empty:
                        return out
                    for _, _r in df_raw.iterrows():
                        if str(_r.get('Speler')) == str(selected) or normalize_position(str(_r.get('Positie') or '')) != pos:
                            continue
                        _v = [safe_float(_r.get(k)) for k in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']]
                        if all(v >= 1 and v == int(v) for v in _v) and [int(v) for v in _v] != [1, 5, 5, 5, 4, 5, 1]:
                            out.append({k: safe_float(_r.get(k)) + 0.5 for k in ['DE', 'PM', 'WI', 'Pas', 'SC']})
                    return out

                def own_players_levels():
                    """All your imported players with real whole skill levels (not the selected one): {skill: level}."""
                    out = []
                    if df_raw.empty:
                        return out
                    for _, _r in df_raw.iterrows():
                        if str(_r.get('Speler')) == str(selected) or normalize_position(str(_r.get('Positie') or '')) == 'K':
                            continue
                        _v = [safe_float(_r.get(k)) for k in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']]
                        if all(v >= 1 and v == int(v) for v in _v) and [int(v) for v in _v] != [1, 5, 5, 5, 4, 5, 1]:
                            out.append({k: safe_float(_r.get(k)) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']})
                    return out

                def own_players_sh():
                    """Set pieces of your imported players with real whole levels."""
                    if df_raw.empty:
                        return []
                    out = []
                    for _, _r in df_raw.iterrows():
                        if normalize_position(str(_r.get('Positie') or '')) == 'K':
                            continue
                        v = safe_float(_r.get('SH'))
                        if v >= 1 and v == int(v):
                            out.append(v)
                    return out

                def other_secondary_option(tr_used, prof, pos, age, gk, sh, lv, kw0, rat_fn, bform, ob, ks):
                    """Main + second picked: the same solve with the other likely second skill (from the Reference DB,
                    e.g. NIM PM + DE: 60% of the NIM there). TSI + wage can't tell the second skill apart, so it is shown
                    as its own option."""
                    if HX is None or not hasattr(HX, 'other_secondary') or len(tr_used) != 2:
                        return None
                    try:
                        from data_layer import get_reference_players_df
                        ref = get_reference_players_df()
                    except Exception:
                        ref = None
                    alt = HX.other_secondary(ref, pos, tr_used)
                    if not alt:
                        return None
                    k2, share, n_ref = alt
                    # balanced: the other second skill gets the most, the usual second keeps a share (tested on the 14
                    # players who get this option: 1.86 -> 1.46 levels off; Kazi NIM 1.43 -> 0.63)
                    tr2 = [tr_used[0], k2, tr_used[1]]
                    peers = own_position_players(pos)
                    own = {k: sum(pp[k] for pp in peers) / len(peers) for k in peers[0]} if len(peers) >= 2 else None
                    prior2, sd2 = HX.training_prior4(tr2, prof, pos, age, own)
                    kw = dict(kw0)
                    _lad2 = HX.ladder_logw(tr2, age) if hasattr(HX, 'ladder_logw') and not paste_state.get('salary') else None
                    if _lad2 is not None:
                        sd2 = HX.ladder_sd(sd2, tr2)
                    kw['logw_fn'] = HX.combine(HX.ordered_logw(tr2), _lad2, rat_fn)
                    oc2 = enumerate_outcomes(solve_tsi(), float(wage_input.value), age, int(days_input.value),
                                             spec_input.value, float(vorm_input.value), float(cond_input.value), pos,
                                             foreign_cb.value, prior2, sd2, sh, lv or None, since_skills(), **kw)
                    if not oc2:
                        return None
                    b = outcome_build(oc2, solve_tsi(), age, int(days_input.value), spec_input.value, bform,
                                      float(cond_input.value), pos, gk=gk, sh=sh, is_foreign=foreign_cb.value)
                    for k, v in ks.items():
                        if k in ('GK', 'SH'):
                            b[k] = float(v)
                    b['Strategy'] = f"Other second skill: {TRAIN_SKILLS[k2]}"
                    b['Outcomes'] = True
                    b['OutcomeAlt'] = True
                    if ob.get('Counts'):
                        # counted with its own weights (All Combos' weights assume the usual second skill)
                        try:
                            import numpy as _np
                            _L = oc2['_lv'].astype(float); _W = oc2['_w'].astype(float); _W = _W / _W.sum()
                            _b = _np.array([int(float(b[k])) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']], dtype=float)
                            _near = (_np.abs(_L - _b) <= 1).all(1)
                            b['Counts'] = dict({k: v for k, v in ob['Counts'].items() if k not in ('opt', 'opt_label')},
                                               opt=int(_near.sum()),
                                               opt_label=trf('within 1 level of this build ({}% of the likely ones with {} second)',
                                                             f"{float(_W[_near].sum()) * 100:.0f}", tr(TRAIN_SKILLS[k2])))
                        except Exception:
                            b['Counts'] = {k: v for k, v in ob['Counts'].items() if k not in ('opt', 'opt_label')}
                    b['Note'] = trf('{}, then {}, then {}: {}% of the {} with {} highest in the Reference DB ({} players) '
                                    'have {} second. TSI and wage fit both equally well.',
                                    tr(TRAIN_SKILLS[tr2[0]]), tr(TRAIN_SKILLS[k2]), tr(TRAIN_SKILLS[tr_used[1]]),
                                    f"{share * 100:.0f}", pos, tr(TRAIN_SKILLS[tr2[0]]), n_ref, tr(TRAIN_SKILLS[k2]))
                    return b

                enum_ctx = {}

                def htms_options(ks, bands):
                    """A real HTMS entered (the 'unknown' switch off): the 3 most likely exact whole-level combinations that fit
                    TSI + wage + his HTMS, one card each. Tested on 26 Portal-tracked players: his real combination was in
                    the top 3 for 65%, top 5 for 81% (out of ~120 that fit; ~35,000 without HTMS)."""
                    if HX is None or not hasattr(HX, 'htms_filter') or htms_unknown_cb.value or not enum_ctx:
                        return []
                    try:
                        htms = float(htms_input.value or 0)
                    except (TypeError, ValueError):
                        return []
                    if htms <= 0:
                        return []
                    c = enum_ctx
                    lvl = lambda k, dflt: ([int(float(ks[k]))] if k in ks else
                                           (list(range(int(bands[k][0]), int(bands[k][1]) + 1)) if k in bands else dflt))
                    # Only with his set-pieces level known: HTMS counts it too, and with it unknown the real combination
                    # was in the top 3 for 8% instead of 65% (26 tracked players).
                    sh_lv = lvl('SH', None)
                    if not sh_lv or len(sh_lv) != 1:
                        return []
                    flt = HX.htms_filter(htms, sh_lv, lvl('GK', [1]))
                    sd2 = dict(c['sd']) if isinstance(c['sd'], dict) else c['sd']
                    if isinstance(sd2, dict):
                        for k in ['DE', 'PM', 'WI', 'Pas', 'SC']:
                            if k not in c['tr']:
                                sd2[k] = max(sd2.get(k, 1.5), 3.0)   # tested: leftovers looser when HTMS decides
                    kw = dict(c['kw'])
                    old = kw.get('extra_filter')
                    kw['extra_filter'] = flt if old is None else (lambda L, a=flt, b=old: a(L) & b(L))
                    oc = enumerate_outcomes(solve_tsi(), float(wage_input.value), c['age'], int(days_input.value), spec_input.value,
                                            float(vorm_input.value), float(cond_input.value), c['pos'], foreign_cb.value,
                                            c['prior'], sd2, c['sh'], c['lv'] or None, since_skills(), **kw)
                    out = []
                    for i, (lvd, share) in enumerate(HX.top_combinations(oc, 3)):
                        exact = {k: int(v) for k, v in lvd.items()}
                        b = outcome_build(dict(oc, est={k: v + 0.5 for k, v in exact.items()}, lo=exact, hi=exact, lv_min=exact, lv_max=exact),
                                          solve_tsi(), c['age'], int(days_input.value), spec_input.value, c['bform'],
                                          float(cond_input.value), c['pos'], gk=c['gk'], sh=c['sh'], is_foreign=foreign_cb.value)
                        for k, v in ks.items():
                            if k in ('GK', 'SH'):
                                b[k] = float(v)
                        b['Strategy'] = trf('Fits his HTMS: combination {}', i + 1)
                        b['Outcomes'] = True
                        b['OutcomeAlt'] = True
                        b['Note'] = trf('{}% of the {} combinations that fit TSI, wage and HTMS {}. Levels: {}', f"{share * 100:.0f}",
                                        f"{oc['n']:,}", f"{htms:.0f}",
                                        ' · '.join(f"{k} {exact[k]}" for k in ['DE', 'PM', 'WI', 'Pas', 'SC']))
                        out.append(b)
                    return out

                def forward_options(ks, bands, ob):
                    """Forwards (27+) with scoring first: the two real forward shapes (pure / playmaking). Picked by itself
                    when a DFW, a known playmaking level or his real HTMS (set pieces known) tells which one he is;
                    otherwise both are shown, the likelier first. See ht_extras section 10 for the tests."""
                    if HX is None or not hasattr(HX, 'FWD_SHAPES') or not enum_ctx or not ob:
                        return []
                    c = enum_ctx
                    pos, age = c['pos'], int(c['age'])
                    K5_ = ['DE', 'PM', 'WI', 'Pas', 'SC']
                    if pos not in HX.FWD_POSITIONS or age < HX.FWD_MIN_AGE:
                        return []
                    if max(K5_, key=lambda k: float(ob.get(k, 0) or 0)) != 'SC':
                        return []
                    mid = lambda k: (float(ks[k]) if k in ks else
                                     ((float(bands[k][0]) + float(bands[k][1])) / 2 if k in bands else None))
                    sc = mid('SC') if mid('SC') is not None else float(ob.get('SC', 0) or 0)
                    pick, why = HX.fwd_pick(pos, sc, mid('PM'))
                    kw = dict(c['kw'])
                    kw.pop('logw_fn', None)
                    # his real HTMS (with set pieces known) decides between the shapes
                    htms_note = ''
                    if pick is None and hasattr(HX, 'htms_filter') and not htms_unknown_cb.value:
                        try:
                            htms = float(htms_input.value or 0)
                        except (TypeError, ValueError):
                            htms = 0
                        sh_lv = ([int(float(ks['SH']))] if 'SH' in ks else
                                 (list(range(int(bands['SH'][0]), int(bands['SH'][1]) + 1)) if 'SH' in bands else None))
                        if htms > 0 and sh_lv and len(sh_lv) == 1:
                            flt = HX.htms_filter(htms, sh_lv, [int(float(ks['GK']))] if 'GK' in ks else [1])
                            old = kw.get('extra_filter')
                            kw['extra_filter'] = flt if old is None else (lambda L, a=flt, b=old: a(L) & b(L))
                            htms_note = f"HTMS {htms:.0f}"
                    flat = {k: 8.0 for k in K5_}

                    def _solve(lw):
                        return enumerate_outcomes(solve_tsi(), float(wage_input.value), age, int(days_input.value),
                                                  spec_input.value, float(vorm_input.value), float(cond_input.value), pos,
                                                  foreign_cb.value, flat, 50.0, c['sh'], c['lv'] or None, since_skills(),
                                                  logw_fn=lw, **kw)
                    share = None
                    if pick is None:
                        store = {}
                        if _solve(HX.fwd_mix_logw(store)) is None:
                            return []
                        share = HX.fwd_pure_share(store)
                        if share is None:
                            return []
                        if htms_note:      # with his HTMS the evidence is strong enough to pick
                            pick, why = ('pure' if share >= 0.5 else 'playmaking'), 'htms'
                    order = [pick, 'playmaking' if pick == 'pure' else 'pure'] if pick else \
                        sorted(['pure', 'playmaking'], key=lambda k: -(share if k == 'pure' else 1 - share))
                    names = {'pure': 'Pure forward (passing second)', 'playmaking': 'Playmaking forward'}
                    shape_txt = {k: ' · '.join(f"{TRAIN_SKILLS[s]} −{v:.0f}" for s, v in HX.FWD_SHAPES[k].items())
                                 for k in HX.FWD_SHAPES}
                    out = []
                    for i, kind in enumerate(order):
                        oc = _solve(HX.fwd_shape_logw(kind))
                        if not oc:
                            continue
                        b = outcome_build(oc, solve_tsi(), age, int(days_input.value), spec_input.value, c['bform'],
                                          float(cond_input.value), pos, gk=c['gk'], sh=c['sh'], is_foreign=foreign_cb.value)
                        for k, v in ks.items():
                            if k in ('GK', 'SH'):
                                b[k] = float(v)
                        b['Strategy'] = trf('Forward profile: {}', tr(names[kind]))
                        b['Outcomes'] = True
                        b['OutcomeAlt'] = i > 0
                        if i == 0 and pick:
                            if why == 'DFW':
                                reason = tr('picked because he is a DFW (13 of the 14 DFWs are playmaking forwards)')
                            elif why == 'pm':
                                reason = trf('picked because his playmaking is known ({} below his scoring)', f"{sc - mid('PM'):.0f}")
                            else:
                                reason = trf('picked because his real {} fits this shape best ({}%)', htms_note,
                                             f"{(share if kind == 'pure' else 1 - share) * 100:.0f}")
                        elif share is not None:
                            reason = trf('{}% likely from TSI + wage alone (they can\'t tell the two shapes apart well)',
                                         f"{(share if kind == 'pure' else 1 - share) * 100:.0f}")
                        else:
                            reason = tr('the other shape, if the pick above is wrong')
                        b['Note'] = ''
                        b['FwdPicked'] = bool(i == 0 and pick)
                        b['Sub'] = reason if (i == 0 and pick) else trf('{}% likely', f"{(share if kind == 'pure' else 1 - share) * 100:.0f}") if share is not None else ''
                        out.append(b)
                    return out

                def shape_options(ks, bands, ob):
                    """Players of 27+ at CD / WB / W / IM: the two real shapes of his position group (ht_extras section 11).
                    Picked by itself when his split skill or his real HTMS (set pieces known) tells which one he is;
                    otherwise both are shown, the likelier first. Inner midfielders are shown but never picked."""
                    if HX is None or not hasattr(HX, 'SHAPE_GROUPS') or not enum_ctx or not ob:
                        return []
                    c = enum_ctx
                    pos, age = c['pos'], int(c['age'])
                    K5_ = ['DE', 'PM', 'WI', 'Pas', 'SC']
                    grp = HX.shape_group(pos, age)
                    if grp is None:
                        return []
                    G_ = HX.SHAPE_GROUPS[grp]
                    names = list(G_['shapes'])
                    mid = lambda k: (float(ks[k]) if k in ks else
                                     ((float(bands[k][0]) + float(bands[k][1])) / 2 if k in bands else None))
                    main_v = mid(G_['main']) if mid(G_['main']) is not None else float(ob.get(G_['main'], 0) or 0)
                    pick = HX.shape_pick(grp, main_v, mid(G_['split']))
                    why = 'split' if pick else None
                    kw = dict(c['kw'])
                    kw.pop('logw_fn', None)
                    htms_note = ''
                    if pick is None and hasattr(HX, 'htms_filter') and not htms_unknown_cb.value:
                        try:
                            htms = float(htms_input.value or 0)
                        except (TypeError, ValueError):
                            htms = 0
                        sh_lv = ([int(float(ks['SH']))] if 'SH' in ks else
                                 (list(range(int(bands['SH'][0]), int(bands['SH'][1]) + 1)) if 'SH' in bands else None))
                        if htms > 0 and sh_lv and len(sh_lv) == 1:
                            flt = HX.htms_filter(htms, sh_lv, [int(float(ks['GK']))] if 'GK' in ks else [1])
                            old = kw.get('extra_filter')
                            kw['extra_filter'] = flt if old is None else (lambda L, a=flt, b=old: a(L) & b(L))
                            htms_note = f"HTMS {htms:.0f}"
                    flat = {k: 8.0 for k in K5_}

                    def _solve(lw):
                        return enumerate_outcomes(solve_tsi(), float(wage_input.value), age, int(days_input.value),
                                                  spec_input.value, float(vorm_input.value), float(cond_input.value), pos,
                                                  foreign_cb.value, flat, 50.0, c['sh'], c['lv'] or None, since_skills(),
                                                  logw_fn=lw, **kw)
                    share = None
                    if pick is None:
                        store = {}
                        if _solve(HX.profile_mix_logw(grp, store)) is None:
                            return []
                        share = HX.shape_first_share(store)
                        if share is None:
                            return []
                        if htms_note:
                            pick, why = (names[0] if share >= 0.5 else names[1]), 'htms'
                        elif G_.get('star_tw') and max(share, 1 - share) >= HX.SHAPE_TW_CONF:
                            pick, why = (names[0] if share >= 0.5 else names[1]), 'tw'
                    sh_of = lambda n: (share if n == names[0] else 1 - share) if share is not None else None
                    order = [pick, [n for n in names if n != pick][0]] if pick else sorted(names, key=lambda n: -sh_of(n))
                    picked = bool(pick) and G_['star']
                    out = []
                    for i, name in enumerate(order):
                        oc = _solve(HX.profile_logw(grp, name))
                        if not oc:
                            continue
                        b = outcome_build(oc, solve_tsi(), age, int(days_input.value), spec_input.value, c['bform'],
                                          float(cond_input.value), pos, gk=c['gk'], sh=c['sh'], is_foreign=foreign_cb.value)
                        for k, v in ks.items():
                            if k in ('GK', 'SH'):
                                b[k] = float(v)
                        b['Strategy'] = trf('Player profile: {}', tr(name))
                        b['Outcomes'] = True
                        b['OutcomeAlt'] = i > 0
                        if i == 0 and pick:
                            if why == 'split':
                                b['Sub'] = trf('picked because his {} is known ({} below his {})', tr(TRAIN_SKILLS[G_['split']]),
                                               f"{main_v - mid(G_['split']):.0f}", tr(TRAIN_SKILLS[G_['main']]))
                            elif why == 'tw':
                                b['Sub'] = trf('picked: {}% likely from his TSI + wage', f"{sh_of(name) * 100:.0f}")
                            else:
                                b['Sub'] = trf('picked because his real {} fits this shape best ({}%)', htms_note,
                                               f"{sh_of(name) * 100:.0f}")
                        else:
                            b['Sub'] = trf('{}% likely', f"{sh_of(name) * 100:.0f}") if share is not None else ''
                        b['Note'] = ''
                        b['FwdPicked'] = bool(i == 0 and picked)
                        out.append(b)
                    return out

                def all_outcomes_option(ks, bands, active_richtskills):
                    """Every whole-level combination that fits TSI + wage, averaged with the template of the player type."""
                    pos = normalize_position(pos_input.value)
                    age = int(age_input.value)
                    prof = (active_richtskills or {}).get(pos) or estimate_age_richtskills(age, spec_input.value, s_nat).get(pos, {})
                    sd, ptype = None, type_sel.value
                    extra, tr_used, rat_fn = None, [], None
                    lad_used = {'on': False}
                    if ptype == 'Other':
                        tr = trained_skills()
                        if not tr and HX is not None:          # training unknown: how your players are built
                            shapes = HX.team_shape(own_players_levels())
                            tr_used = [POS_TRAINING.get(pos, ('SC', 'Pas'))[0]]
                            if shapes:
                                prior, sd = dict(prof), dict(HX.FLAT_SD)
                                extra = HX.shape_logw(tr_used[0], shapes)
                                src = f"shape of your {len(own_players_levels())} players (training unknown)"
                            else:
                                prior = nt_outcome_prior(prof, pos, age)
                                src = 'NT template (fewer than 4 of your players have real skill levels)'
                        else:
                            tr = tr or [POS_TRAINING.get(pos, ('SC', 'Pas'))[0]]
                            tr_used = tr
                            peers = own_position_players(pos)
                            own = {k: sum(pp[k] for pp in peers) / len(peers) for k in peers[0]} if len(peers) >= 2 else None
                            if HX is not None and mixed_training() and hasattr(HX, 'mixed_prior'):
                                prior, sd = HX.mixed_prior(tr, prof, pos, age, own)
                                extra = HX.mixed_logw(tr)         # both second skills about equal, no order
                            elif HX is not None:
                                prior, sd = HX.training_prior4(tr, prof, pos, age, own)
                                extra = HX.ordered_logw(tr)       # your picks are his highest skills, in this order
                            else:
                                prior, sd = training_outcome_prior(tr, prof, pos, age, own)
                            # the skills you did not pick: a ladder (one higher, one middle, one low) instead of all ~4.5
                            _lad = (HX.ladder_logw(tr, age) if HX is not None and hasattr(HX, 'ladder_logw')
                                    and not paste_state.get('salary') else None)
                            if _lad is not None:
                                lad_used.update(on=True, sd0=sd, extra0=extra)   # kept for the seniors' spare options
                                sd = HX.ladder_sd(sd, tr)
                                extra = HX.combine(extra, _lad)
                            src = 'training ' + ' + '.join(tr) + (f", levels from your {len(peers)} {pos} players" if own else '')
                    elif ptype == 'NT':
                        prior, src = nt_outcome_prior(prof, pos, age), 'NT target skills, adjusted to real NT players'
                    else:
                        prior, src = {k: float(prof.get(k, 1.0)) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']}, 'U22 target skills'
                    lv = {k: (int(float(v)), int(float(v))) for k, v in ks.items()}
                    lv.update({k: (int(b[0]), int(b[1])) for k, b in bands.items()})
                    if 'SH' in ks:
                        sh = float(ks['SH'])
                    elif 'SH' in bands:
                        sh = (bands['SH'][0] + bands['SH'][1]) / 2
                    else:
                        sh = float(prof.get('SH', 3.0))
                        if ptype == 'Other':
                            # NT seniors train set pieces; most other players don't (your players: median 2-4.5).
                            # Long-shot players: high set pieces (about 0.85 x their main skill at 29+).
                            if setup_sel.value == LONGSHOT_SETUP:
                                sh = min(20.0, 0.85 * max(max(float(prof.get(k, 1.0)) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']), 10.0))
                            else:
                                _shs = sorted(v for v in own_players_sh() if v >= 1)
                                sh = float(_shs[len(_shs) // 2]) + 0.5 if len(_shs) >= 4 else 4.0
                    gk = float(ks['GK']) if 'GK' in ks else ((bands['GK'][0] + bands['GK'][1]) / 2 if 'GK' in bands else 1.0)
                    if ptype == 'Other' and HX is not None and paste_state.get('ratings'):
                        rat_fn = HX.ratings_logw(paste_state['ratings'], tr_used, solve_tsi(), float(vorm_input.value), gk, sh)
                    _kw = {'logw_fn': HX.combine(extra, rat_fn)} if HX is not None else {}
                    # Hattrick Portal history (seniors): his hidden form from the TSIs since the birthday, and a tighter
                    # wage window when his skills stayed the same since then
                    _bform, _trk = float(vorm_input.value), None
                    if HX is not None and paste_state.get('tracker'):
                        try:
                            _trk = HX.tracker_summary(paste_state['tracker'], solve_tsi())
                        except Exception:
                            _trk = None
                    if _trk and _trk.get('hf') and int(float(_trk['hf']['form'])) == int(float(vorm_input.value)):
                        _kw['form_range'] = (_trk['hf']['lo'], _trk['hf']['hi'])
                        _bform = float(_trk['hf']['form'])
                    if _trk and _trk.get('w_lo_frac'):
                        _kw['w_lo_frac'] = _trk['w_lo_frac']

                    def _enum(flt=None, with_ratings=True, extra_lw=None, no_ladder=False):
                        kw = dict(_kw)
                        sd_ = sd
                        if no_ladder and lad_used['on']:
                            # without the leftover ladder (template + training order + ratings only)
                            sd_ = lad_used['sd0']
                            kw['logw_fn'] = HX.combine(lad_used['extra0'], rat_fn if with_ratings else None)
                        elif not with_ratings and HX is not None:
                            kw['logw_fn'] = HX.combine(extra)
                        if extra_lw is not None and HX is not None:
                            kw['logw_fn'] = HX.combine(kw.get('logw_fn'), extra_lw)
                        if flt is not None:
                            kw['extra_filter'] = flt
                        return enumerate_outcomes(solve_tsi(), float(wage_input.value), age, int(days_input.value),
                                                  spec_input.value, float(vorm_input.value), float(cond_input.value), pos,
                                                  foreign_cb.value, prior, sd_, sh, lv or None, since_skills(), **kw)
                    oc = _enum()
                    enum_ctx.clear()
                    enum_ctx.update(prior=prior, sd=sd, kw=dict(_kw), sh=sh, gk=gk, lv=lv, bform=_bform, tr=list(tr_used), age=age, pos=pos,
                                    ob_counts=None)
                    if not oc:
                        return None
                    ob = outcome_build(oc, solve_tsi(), age, int(days_input.value), spec_input.value, _bform,
                                       float(cond_input.value), pos, gk=gk, sh=sh, is_foreign=foreign_cb.value)
                    for k, v in ks.items():   # known values stay exactly as entered
                        if k in ('GK', 'SH'):
                            ob[k] = float(v)
                    ob['Strategy'] = 'All Combos'
                    ob['Outcomes'] = True
                    ob['_oc'] = oc     # the combinations, to count how many are close to the other options (taken off later)
                    ob['Template'] = src   # kept for reference, not shown
                    LAST_OUTCOME_TEMPLATE['src'] = src
                    _c = oc.get('counts') or {}
                    _wk = int(days_input.value or 0) / 7.0
                    if _c:
                        # shown as coloured counts (render_results); Note keeps only extra remarks
                        ob['Counts'] = dict(grid=_c['grid'], tsi=_c['tsi'], levels=_c['levels'], wage=_c['wage'],
                                            tsi_v=solve_tsi(), wage_v=float(wage_input.value))
                        ob['Note'] = ''
                    else:
                        ob['Note'] = f"{oc['n']:,} whole-level combinations fit TSI + wage"
                    if rat_fn is not None:
                        _oc0 = _enum(with_ratings=False)
                        if _oc0:
                            _b0 = outcome_build(_oc0, solve_tsi(), age, int(days_input.value), spec_input.value,
                                                _bform, float(cond_input.value), pos, gk=gk, sh=sh,
                                                is_foreign=foreign_cb.value)
                            _used = ', '.join(f"{HP.ORDER_LABEL.get(q, q)} ×{n}" for q, n, a, m in HX.ratings_summary(paste_state['ratings'])
                                              if q in HX.RATING_OFFSET)
                            ob['Note'] += (f"With match ratings ({_used}). Without them: "
                                           + ' · '.join(f"{k} {_b0[k]:.1f}" for k in ['DE', 'PM', 'WI', 'Pas', 'SC']))
                    out = [ob]
                    # Other with picked training: one option per skill you did not pick ("spare levels mostly in ...")
                    # instead of the alternative below. Tested: the matching option 0.58/0.28/0.48 -> 0.40/0.28/0.34
                    # levels off (3 teams); ranked by the match ratings when they are pasted.
                    _cnt = (lambda n, lab: dict(ob['Counts'], opt=int(n), opt_label=lab)) if ob.get('Counts') else (lambda n, lab: None)
                    # Custom with 4 (or more) skills leaves 1 spare skill: show focused / in between / all-round instead,
                    # so there are 4 options like the other setups.
                    def _spread(which):
                        """Builds for focused (his main skill far above the other trained ones) / in between / all-round."""
                        import numpy as _np
                        _ix = [['DE', 'PM', 'WI', 'Pas', 'SC'].index(t) for t in tr_used]
                        groups = outcome_split(oc, lambda L: L[:, _ix[1:]].mean(1) / _np.maximum(L[:, _ix[0]], 1.0), 3)
                        _sec = ' + '.join(tr_used[1:])
                        labs = [(f"Focused on {TRAIN_SKILLS[tr_used[0]]}", f"have {_sec} lowest"),
                                ('In between', f"have {_sec} in the middle"),
                                (f"All-round: more {_sec}", f"have {_sec} highest")]
                        res_ = []
                        for gi, ((title, lab), g) in enumerate(zip(labs, groups)):
                            if gi not in which:
                                continue
                            gb = outcome_build(dict(oc, est=g['est'], lo=g['lo'], hi=g['hi']), solve_tsi(), age,
                                               int(days_input.value), spec_input.value, _bform, float(cond_input.value),
                                               pos, gk=gk, sh=sh, is_foreign=foreign_cb.value)
                            for k, v in ks.items():
                                if k in ('GK', 'SH'):
                                    gb[k] = float(v)
                            gb['Strategy'] = title
                            gb['Outcomes'] = True
                            gb['OutcomeAlt'] = True
                            gb['Counts'] = _cnt(g['n'], lab)
                            gb['Note'] = f"{', '.join(tr_used)} in this order"
                            res_.append(gb)
                        return res_
                    if ptype == 'Other' and HX is not None and len(tr_used) >= 2 and len(HX.spare_skills(tr_used)) <= 1 \
                            and outcome_split is not None:
                        return out + _spread((0, 1, 2))
                    # Salary history (Salaries tab pasted): how much training went into his other skills sets how
                    # high they go in each "Spare levels" option. With it, these options also show when you picked
                    # only his main training (the 3 likeliest).
                    sal_fn = sal_A = None
                    if ptype == 'Other' and HX is not None and paste_state.get('salary') and hasattr(HX, 'salary_budget_logw'):
                        try:
                            sal_fn, sal_A = HX.salary_budget_logw(paste_state['salary'], tr_used[0], spec_input.value, age)
                        except Exception:
                            sal_fn = None
                    if ptype == 'Other' and HX is not None and (len(tr_used) >= 2 or sal_fn is not None):
                        spares = []
                        # seniors with main + second picked: the spare skill sits at a real third-skill level
                        # 28+: the spare options keep the third-skill nudge (tested a little better than the ladder there:
                        # Reference DB 1.005 vs 1.054); younger players use the ladder (0.876 -> 0.725)
                        _senior = hasattr(HX, 'third_slot_logw') and age >= HX.THIRD_SLOT_MIN_AGE
                        _slot = HX.third_slot_logw(tr_used, prior) if _senior else None
                        # All Combos is generally right about his main and second skill: the spare options stay at or
                        # under those levels, and 'mostly in X' keeps X at least where All Combos has it (more X, not less)
                        _sk5 = ['DE', 'PM', 'WI', 'Pas', 'SC']
                        _cap = {k: int(float(ob[k])) for k in tr_used[:2] if k in _sk5}
                        _base_flt = _kw.get('extra_filter')

                        def _spare_flt(x, strict):
                            import numpy as _np
                            sf = HX.spare_filter(tr_used, x)
                            xi = _sk5.index(x)

                            def f(L):
                                m = sf(L)
                                if _base_flt is not None:
                                    m = m & _base_flt(L)
                                if strict >= 1:
                                    for k, v in _cap.items():
                                        m = m & (L[:, _sk5.index(k)] <= v)
                                if strict >= 2:
                                    m = m & (L[:, xi] >= int(float(ob[x])))
                                return m
                            return f
                        for x in HX.spare_skills(tr_used):
                            ocx = None
                            for _strict in (2, 1, 0):
                                ocx = _enum(_spare_flt(x, _strict), extra_lw=HX.combine(sal_fn, _slot), no_ladder=_senior)
                                if ocx:
                                    break
                            if not ocx:
                                continue
                            bx = outcome_build(ocx, solve_tsi(), age, int(days_input.value), spec_input.value,
                                               _bform, float(cond_input.value), pos, gk=gk, sh=sh,
                                               is_foreign=foreign_cb.value)
                            # the same with the decimals: main + second not above All Combos, X not below it;
                            # the other spare skills take up the difference so TSI stays exact
                            _fix = {k: min(float(bx[k]), float(ob[k])) for k in _cap}
                            if _strict >= 2:
                                _fix[x] = max(float(bx[x]), float(ob[x]))
                            if any(abs(_fix[k] - float(bx[k])) > 1e-9 for k in _fix):
                                _nb = fast_rebalance(bx, _fix, solve_tsi(), age, int(days_input.value), spec_input.value,
                                                     float(bx['Vorm']), float(bx['Cond']), foreign_cb.value)
                                if _nb is not None and all(float(_nb[k]) >= 1.0 for k in _sk5):
                                    bx.update({k: _nb[k] for k in _sk5 + ['Calc_TSI', 'Calc_Wage', 'Calc_HTMS', 'Calc_HTMS28']})
                            for k, v in ks.items():
                                if k in ('GK', 'SH'):
                                    bx[k] = float(v)
                            fit = None
                            if rat_fn is not None:
                                import numpy as _np
                                fit = float(rat_fn(_np.array([[bx[k] for k in ['DE', 'PM', 'WI', 'Pas', 'SC']]]))[0])
                            spares.append((x, ocx['n'], fit, bx))
                        tot = oc['n'] or 1
                        spares.sort(key=lambda t: -(t[2] if t[2] is not None else t[1]))
                        if len(tr_used) == 1:
                            spares = spares[:3]
                        for rank, (x, n, fit, bx) in enumerate(spares):
                            bx['Strategy'] = f"Spare levels mostly in {TRAIN_SKILLS[x]}"
                            bx['Outcomes'] = True
                            bx['OutcomeAlt'] = True
                            bx['Counts'] = _cnt(n, f"have most of the rest in {TRAIN_SKILLS[x]} ({n / tot * 100:.0f}%)")
                            bx['Note'] = ('Fits his match ratings best' if fit is not None and rank == 0 else '')
                            if sal_fn is not None:
                                bx['Note'] = (bx['Note'] + ' · ' if bx['Note'] else '') + \
                                    f"Other skills set by his salary history (about {sal_A:.1f} seasons of training went into them)"
                            if not bx['Counts']:
                                bx['Note'] = (f"{n:,} of the {tot:,} combinations ({n / tot * 100:.0f}%) have most of his skills "
                                              f"after {' + '.join(tr_used)} in {TRAIN_SKILLS[x]}")
                            out.append(bx)
                        if len(spares) == 2 and outcome_split is not None and len(tr_used) >= 2:
                            out += _spread((2,))          # 3 skills picked: the 4th option is the all-round build
                        _os = other_secondary_option(tr_used, prof, pos, age, gk, sh, lv, _kw, rat_fn, _bform, ob, ks)
                        if _os is not None:
                            out.insert(1, _os)
                        return out
                    # The combinations often fall in two groups (e.g. more passing + less scoring, or the other way round).
                    # Show the group that differs most from the estimate as a second option, when it differs by 0.75+
                    # of a level somewhere. (Tested: for 21% of the Dutch U22 it is clearly the better build; for Other
                    # players with their training answered it rarely is, but it is shown there too.)
                    alts = oc.get('alts') or []
                    if len(alts) == 2:
                        builds = []
                        for a in alts:
                            ab = outcome_build(dict(oc, est=a['est'], lo=a['lo'], hi=a['hi']), solve_tsi(), age,
                                               int(days_input.value), spec_input.value, _bform,
                                               float(cond_input.value), pos, gk=gk, sh=sh, is_foreign=foreign_cb.value)
                            builds.append((max(abs(ab[k] - ob[k]) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']), a, ab))
                        dmax, a, ab = max(builds, key=lambda t: t[0])
                        LAST_OUTCOME_TEMPLATE['alt_gap'] = round(dmax, 2)
                        # Other: always shown (same number of options whatever training is picked); with a narrow
                        # training like DE + PM the two groups are often close, and the card then says so.
                        if dmax >= 0.75 or ptype == 'Other':
                            for k, v in ks.items():
                                if k in ('GK', 'SH'):
                                    ab[k] = float(v)
                            diff = sorted(((k, ab[k] - ob[k]) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']), key=lambda t: -abs(t[1]))
                            thr = 0.5 if dmax >= 0.75 else 0.2
                            more = [f"more {TRAIN_SKILLS[k]}" for k, d in diff[:3] if d >= thr]
                            less = [f"less {TRAIN_SKILLS[k]}" for k, d in diff[:3] if d <= -thr]
                            ab['Strategy'] = 'Alternative: ' + (', '.join(more + less) or 'close to option 1')
                            ab['Counts'] = _cnt(round(a['share'] * oc['n']), f"in this shape ({a['share'] * 100:.0f}% of the weight)")
                            ab['Outcomes'] = True
                            ab['OutcomeAlt'] = True
                            if dmax >= 0.75:
                                ab['Note'] = (f"The other likely shape ({a['share'] * 100:.0f}% of the combinations). "
                                              'Pick it when you know he has more of these skills.')
                            else:
                                ab['Note'] = (f"The other likely shape ({a['share'] * 100:.0f}% of the combinations), "
                                              f"only {dmax:.1f} level away from option 1: with this training the "
                                              'combinations mostly agree.')
                            out.append(ab)
                    return out

                async def run_solver():
                    if custom_state['ignore']:
                        active_richtskills = estimate_age_richtskills(int(age_input.value), spec_input.value, s_nat)
                    else:
                        active_richtskills = get_richtskills_for_age(s_nat, int(age_input.value), spec=spec_input.value)
                    ks = {}
                    bands = {}
                    for sk, (val_input, unknown_cb) in known_skills.items():
                        if unknown_cb.value:
                            wsel = skill_bands[sk].value
                            if wsel != '(unknown)':
                                bands[sk] = hattrick_skill_band(int(wsel.split(' - ')[0]))
                        else:
                            ks[sk] = float(val_input.value)

                    # Pre-load reference DB in main process (cached here, avoids
                    # two Turso round-trips per solve inside the subprocess)
                    try:
                        from data_layer import get_reference_players_df
                        if no_ref_cb.value:
                            # An empty table (not None): the engine then uses no peers at all,
                            # and doesn't load the Reference DB itself either.
                            pre_ref_df = pd.DataFrame(columns=['Positie', 'Leeftijd', 'TSI', 'Loon', 'HTMS',
                                                               'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH'])
                        else:
                            pre_ref_df = get_reference_players_df()
                        # Never compare a player with himself (e.g. an earlier, wrong result
                        # that was synced to the Reference DB would keep pulling him back).
                        if pre_ref_df is not None and not pre_ref_df.empty:
                            _self = pd.Series(False, index=pre_ref_df.index)
                            if 'PlayerID' in pre_ref_df.columns and int(float(s_id or 0)) > 0:
                                _self |= pd.to_numeric(pre_ref_df['PlayerID'], errors='coerce').fillna(0).astype(int) == int(float(s_id))
                            if 'Speler' in pre_ref_df.columns and selected:
                                _self |= pre_ref_df['Speler'].astype(str).str.strip().str.lower() == str(selected).strip().lower()
                            pre_ref_df = pre_ref_df[~_self].reset_index(drop=True)
                    except Exception:
                        pre_ref_df = None

                    shape_kw = {}
                    if shape_sel is not None and shape_sel.value == 'contribution':
                        shape_kw = dict(shape='contribution', order=order_sel.value,
                                        accent=None if accent_sel.value == 'none' else accent_sel.value)

                    spinner_holder = solve_status
                    solve_status.classes(remove='hidden')
                    solve_btn.disable()
                    status_label = solve_dots
                    results_area.clear()

                    import asyncio
                    keepalive_running = {'active': True}
                    async def keepalive_ping():
                        dots = 0
                        while keepalive_running['active']:
                            await asyncio.sleep(5)
                            if not keepalive_running['active']:
                                break
                            dots = (dots % 3) + 1
                            status_label.set_text(f'({"." * dots})')

                    asyncio.ensure_future(keepalive_ping())

                    try:
                        results, diagnostics = await asyncio.wait_for(
                            run.io_bound(
                                auto_solve_subskills, solve_tsi(), float(wage_input.value),
                                float(htms_input.value), float(htms28_input.value), int(age_input.value), int(days_input.value),
                                spec_input.value, float(vorm_input.value), float(cond_input.value), pos_input.value,
                                solver_richtskills(active_richtskills), htms_unknown_cb.value, htms28_unknown_cb.value,
                                (ks or None), foreign_cb.value, (bands or None), pre_ref_df,
                                exclude_player=(s_id, selected),
                                untrained=not since_skills(), **shape_kw
                            ),
                            timeout=90.0
                        )
                    except asyncio.TimeoutError:
                        keepalive_running['active'] = False
                        solve_status.classes(add='hidden')
                        solve_btn.enable()
                        ui.notify('⏱️ Solver timed out — try marking more skills as known to speed it up.', type='warning')
                        return
                    except Exception as e:
                        keepalive_running['active'] = False
                        solve_status.classes(add='hidden')
                        solve_btn.enable()
                        ui.notify(f'Solve error: {e}', type='negative')
                        return

                    if type_sel.value == 'Other':   # the solver options are built on his training here
                        for _r in results:
                            _r['Strategy'] = str(_r.get('Strategy', '')).replace('Target Skills Benchmark', 'Training shape')
                    if enumerate_outcomes is not None and normalize_position(pos_input.value) != 'K':
                        try:
                            obs = await run.io_bound(all_outcomes_option, ks, bands, active_richtskills)
                            if obs:
                                try:
                                    _hc = await run.io_bound(htms_options, ks, bands)
                                except Exception:
                                    _hc = []
                                if _hc:
                                    obs = [obs[0]] + _hc + list(obs[1:])     # right after All Combos
                                try:
                                    _fw = await run.io_bound(forward_options, ks, bands, obs[0])
                                except Exception:
                                    _fw = []
                                if _fw:
                                    obs = [obs[0]] + _fw + list(obs[1:])     # forward profiles right after All Combos
                                try:
                                    _sp = await run.io_bound(shape_options, ks, bands, obs[0])
                                except Exception:
                                    _sp = []
                                if _sp:
                                    obs = [obs[0]] + _sp + list(obs[1:])     # player profiles right after All Combos
                                for ob in obs:
                                    ob['Target_HTMS'] = results[0].get('Target_HTMS', 0) if results else 0
                                    ob['Target_HTMS28'] = results[0].get('Target_HTMS28', 0) if results else 0
                                if type_sel.value == 'Other' and HX is not None:
                                    # regular solver options were 1.4-1.9 levels off for Other players (tests): not shown
                                    results = list(obs)
                                else:
                                    results = list(obs) + list(results)
                            else:
                                ui.notify('All Combos: no whole-level combination fits this TSI + wage', type='warning')
                        except Exception as e:
                            ui.notify(f'All Combos skipped: {e}', type='warning')

                    if snap_tsi is not None and normalize_position(pos_input.value) != 'K':
                        _fixed = {k: v for k, v in ks.items() if k not in ('GK', 'SH')}
                        for _i, _r in enumerate(results):
                            _nb = snap_tsi(_r, solve_tsi(), int(age_input.value), int(days_input.value), spec_input.value,
                                           float(_r.get('Vorm', vorm_input.value)), float(_r.get('Cond', cond_input.value)),
                                           _fixed, foreign_cb.value)
                            if _nb is not _r:
                                _r.update({k: _nb[k] for k in ['DE', 'PM', 'WI', 'Pas', 'SC', 'Calc_TSI', 'Calc_Wage',
                                                               'Calc_HTMS', 'Calc_HTMS28']})
                        # NT / U22 solver options: when the wage does not fit (the All Combos builds always do), move the
                        # skill that sets the wage just enough; the other skills follow so TSI stays exact.
                        if wage_fit_build is not None:
                            _ceil = float((diagnostics or {}).get('wage_ceiling') or 0)
                            for _r in results:
                                if _r.get('Saved'):
                                    continue
                                _nb, _mk, _dv = wage_fit_build(
                                    _r, float(wage_input.value or 0), solve_tsi(), normalize_position(pos_input.value),
                                    int(age_input.value), int(days_input.value), spec_input.value,
                                    float(_r.get('Vorm', vorm_input.value)), float(_r.get('Cond', cond_input.value)),
                                    _fixed, foreign_cb.value, _ceil)
                                if _mk:
                                    _r.update({k: _nb[k] for k in ['DE', 'PM', 'WI', 'Pas', 'SC', 'Calc_TSI', 'Calc_Wage',
                                                                   'Calc_HTMS', 'Calc_HTMS28']})
                                    _r['Note'] = ((_r.get('Note') or '') + ' · ' if _r.get('Note') else '') + trf(
                                        'Wage fitted: {} {} so the wage matches (the other skills follow, TSI stays exact)',
                                        ' + '.join(tr(TRAIN_SKILLS.get(_k, _k)) for _k in _mk.split('+')), f"{_dv:+.2f}")

                    # no skill a hair under the next level (shown and saved as the next level: TSI and HTMS would jump)
                    try:
                        for _r in results:
                            _nb = edge_safe(_r, solve_tsi(), int(age_input.value), int(days_input.value), spec_input.value,
                                            float(_r.get('Vorm', vorm_input.value)), float(_r.get('Cond', cond_input.value)),
                                            {k: v for k, v in ks.items() if k not in ('GK', 'SH')}, foreign_cb.value)
                            if _nb is not _r:
                                _r.update({k: _nb[k] for k in ['DE', 'PM', 'WI', 'Pas', 'SC', 'Calc_TSI', 'Calc_Wage',
                                                               'Calc_HTMS', 'Calc_HTMS28']})
                    except NameError:
                        pass
                    # The regular solver options (NT / U22): how many of the combinations that fit TSI + wage
                    # are close to this build (every skill within 1 level of it)
                    _oc_all = next((r.pop('_oc') for r in results if '_oc' in r), None)
                    for r in results:
                        r.pop('_oc', None)
                    if _oc_all is not None and _oc_all.get('_lv') is not None:
                        import numpy as _np
                        _base = next((r.get('Counts') for r in results if r.get('Outcomes') and r.get('Counts')), None)
                        _L = _oc_all['_lv'].astype(float)
                        _W = _oc_all['_w'].astype(float); _W = _W / _W.sum()
                        for r in results:
                            if HX is not None and hasattr(HX, 'sure_skills') and not r.get('Saved'):
                                try:
                                    r['Sure'] = HX.sure_skills(_L.astype(int), _W, r)
                                except Exception:
                                    pass
                            # All Combos gets its count too; options that already have their own (shape / spare skill) keep it
                            if r.get('Saved') or (r.get('Counts') or {}).get('opt') is not None:
                                continue
                            try:
                                b = _np.array([int(float(r[k])) for k in ['DE', 'PM', 'WI', 'Pas', 'SC']], dtype=float)
                            except (KeyError, TypeError, ValueError):
                                continue
                            near = (_np.abs(_L - b) <= 1).all(1)
                            n_near, share = int(near.sum()), float(_W[near].sum())
                            lab = (f"within 1 level of this build ({share * 100:.0f}% of the likely ones)" if n_near
                                   else 'within 1 level of this build: none, so this build is unlikely')
                            if r.get('Counts'):
                                r['Counts'] = dict(r['Counts'], opt=n_near, opt_label=lab)
                            elif _base:
                                r['Counts'] = dict(_base, opt=n_near, opt_label=lab)
                            else:
                                r['Note'] = ((r.get('Note') or '') + ' · ' if r.get('Note') else '') + f"{n_near:,} combinations {lab}"

                    keepalive_running['active'] = False
                    solve_status.classes(add='hidden')
                    solve_btn.enable()
                    solve_dots.set_text('(10-20s)')
                    render_diagnostics_and_results(results, diagnostics)

                    tp = {
                        'position': pos_input.value, 'age': int(age_input.value), 'spec': spec_input.value, 'wage': float(wage_input.value),
                        'tsi': solve_tsi(), 'htms': None if htms_unknown_cb.value else float(htms_input.value),
                        'htms28': None if htms28_unknown_cb.value else float(htms28_input.value),
                        'exclude_player_id': s_id if not is_empty else None,
                    }
                    similar = find_similar_players(
                        position=tp['position'], age=tp['age'], spec=tp['spec'], tsi=tp['tsi'],
                        htms=tp['htms'], htms28=tp['htms28'], wage=tp['wage'], k=8,
                        exclude_player_id=tp.get('exclude_player_id')
                    )
                    similar_area.clear()
                    with similar_area:
                        with tt_card('🗄️ Similar Real Players (Reference Database)'):
                            if similar.empty:
                                ui.label('No players in the Reference Database yet.').classes('text-gray-400')
                            else:
                                cols = [c for c in ['Speler', 'Positie', 'Leeftijd', 'Specialiteit', 'TSI', 'Loon', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH', 'match_score'] if c in similar.columns]
                                ui.table(
                                    columns=[{'name': c, 'label': c, 'field': c} for c in cols],
                                    rows=similar[cols].to_dict('records')
                                ).classes('w-full')

                def render_diagnostics_and_results(results, diag):
                    results_area.clear()
                    with results_area:
                        with tt_card('🔬 Reverse-Engineering & Solver Diagnostics'):
                            with ui.row().classes('items-center justify-end w-full mb-2'):
                                if diag.get('shape'):
                                    _o, _a = diag['shape']
                                    _sp = diag.get('shape_profile') or {}
                                    ui.badge(f"📊 Contribution shape: {_o}" + (f" · {ACCENTS.get(_a, _a)}" if _a else ''),
                                             color='teal').props('outline').tooltip(
                                        'Aimed at: ' + ' · '.join(f'{k} {_sp[k]:.1f}' for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH') if k in _sp))
                                ui.badge('Reverse-Engineered Estimate Active', color='indigo').props('outline')

                            with ui.grid(columns=4).classes('w-full gap-3 pt-1 tt-tiles'):
                                with ui.column().classes('gap-0 tt-tile'):
                                    ui.label('Wage (base)').classes('tt-dlab')
                                    ui.label(f"€{diag['base_wage']:,.0f}").classes('tt-dval')
                                    ui.label(f"×{diag['age_wage_factor']:.2f} for his age · €{diag['norm_wage_28']:,.0f} at 28").classes('tt-dsub')

                                with ui.column().classes('gap-0 tt-tile'):
                                    # Worked out from the wage, i.e. the value on the last birthday.
                                    wks_b = int(days_input.value or 0) / 7.0
                                    if pos_input.value == 'K':
                                        # Keepers: GK comes from TSI (today), not from the wage.
                                        ui.label("Main skill (GK) from TSI").classes('tt-dlab')
                                    else:
                                        ui.label(f"Main skill ({diag['primary_col']}) at birthday").classes('tt-dlab') \
                                            .tooltip(f"{wks_b:.1f} weeks ago" if wks_b > 0 else 'today')
                                    _pb = diag.get('inferred_primary_birthday', diag['inferred_primary'])
                                    ui.label(f"{_pb:.2f}").classes('tt-dval')
                                    ui.label(f"{skill_level_label(_pb)}").classes('tt-dsub')
                                    if diag.get('main_range'):
                                        _ml, _mh, _mj = diag['main_range']
                                        ui.label(f"Possible: {_ml:.2f} – {_mh:.2f}").classes('tt-dsub tt-dgold').tooltip(
                                                f"What TSI + wage allow: {_mh:.2f} when the other skills are low, "
                                                f"{_ml:.2f} when {_mj} is as high as the main skill (Hattrick pays the "
                                                f"best-paid skill in full, the others half). Option 2 (multiskill) aims "
                                                f"in the middle of this range.")
                                        _days = int(days_input.value or 0)
                                        _since = since_skills()
                                        if (full_training_gain is not None and _days >= 7 and int(age_input.value or 0) < 28
                                                and diag['primary_col'] in _since):
                                            try:
                                                _g = full_training_gain(diag['primary_col'], float(_mh), int(age_input.value),
                                                                        _days / 7.0 / len(_since))
                                            except Exception:
                                                _g = 0.0
                                            if _g >= 0.05:
                                                ui.label(f"Today: {_ml:.2f} – {_mh + _g:.2f}").classes('tt-dsub tt-dgold').tooltip(
                                                        f"The wage was set on the birthday ({_days / 7.0:.1f} wk ago). Since then "
                                                        f"full {diag['primary_col']} training adds up to +{_g:.2f}, so the options "
                                                        f"below (today's skills) can be up to {_mh + _g:.2f}.")


                                with ui.column().classes('gap-0 tt-tile'):
                                    ui.label('Other skills (average)').classes('tt-dlab')
                                    ui.label(f"~{diag['residual_secondary_avg']:.2f}").classes('tt-dval')
                                    ui.label(f"TSI factor for his age ×{diag['age_tsi_factor']:.3f}").classes('tt-dsub')

                                with ui.column().classes('gap-0 tt-tile'):
                                    ui.label('HTMS').classes('tt-dlab')
                                    ui.label(f"{diag['active_target_htms']}").classes('tt-dval')
                                    ui.label(f"HTMS28 {diag['active_target_htms28']}").classes('tt-dsub')
                                    # Explain source of HTMS anchor clearly
                                    htms_mode = diag.get('htms_mode','')
                                    if 'Calculated from Known Skills' in htms_mode:
                                        ui.label('✅ Exact — all skills known').classes('tt-dsub text-green-400')
                                    elif 'Partial Known Skills' in htms_mode:
                                        n_known = htms_mode.split('(')[1].split('/')[0] if '(' in htms_mode else '?'
                                        ui.label(f'🔶 Estimated — {n_known} known + wage + bench').classes('tt-dsub text-amber-400')
                                    elif 'Exact Target' in htms_mode:
                                        ui.label('✅ Exact — entered by user').classes('tt-dsub text-green-400')
                                    else:
                                        ui.label('🔵 Estimated from TSI + Wage').classes('tt-dsub')
                                    if diag.get('ref_players_found', 0) > 0:
                                        ui.label(f"Ref DB: {diag.get('ref_players_found')} peers").classes('text-xs text-gray-400')

                        render_results(results, diag)
                        solved_state['done'] = True

                def render_results(results, diag):
                    def delta_str(actual, target, prefix=''):
                        delta = actual - target
                        sign = '+' if delta > 0 else ''
                        return f"{prefix}{sign}{delta:,.1f} vs target"

                    def tsi_delta_str(actual, target):
                        # Hattrick shows TSI as a whole number: compare whole numbers (59,370.4 = 59,370)
                        d = int(round(actual)) - int(round(target))
                        return ('±0' if d == 0 else f'{d:+,d}') + ' vs target'

                    def delta_color(actual, target, pct_threshold):
                        delta = actual - target
                        if delta == 0:
                            return '#9CC3E6'
                        threshold = max(abs(target), 1) * pct_threshold
                        if abs(delta) < threshold:
                            return '#9CC3E6'
                        return '#34D399' if delta > 0 else '#F87171'

                    shown = list(results)

                    def wage_eval(res):
                        """(text, colour, ok) for the wage line of a card."""
                        actual_w = float(wage_input.value or 0)
                        d_days = int(days_input.value or 0)
                        if d_days > 0 and actual_w > 0:
                            w_lo, w_typ, w_hi, wks = birthday_wage_range(
                                {k: res[k] for k in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']},
                                pos_input.value, int(age_input.value), d_days, spec_input.value, foreign_cb.value)
                            ceiling = float((diag or {}).get('wage_ceiling') or 0)
                            _senior_drop = 0.0
                            if int(age_input.value or 0) >= 28:
                                _senior_drop = min(0.20, 0.005 * max(0, min(d_days, 111)) / 7.0)
                            ok = True
                            if actual_w > w_hi * 1.02 / max(1.0 - _senior_drop, 0.8):
                                w_txt, w_col, ok = '✗ skills too low for this wage', '#F87171', False
                            elif _senior_drop > 0 and actual_w > w_hi * 1.02:
                                w_txt, w_col = '✓ fits (skills dropped since the birthday)', '#34D399'
                            elif int(age_input.value or 0) >= 28 and w_hi > actual_w * 1.005:
                                w_txt, w_col = ('⚠ more than his wage: after the birthday a senior only loses skill',
                                                '#FBBF24')
                            elif ceiling and w_hi > ceiling * 1.10:
                                w_txt, w_col, ok = '⚠ more growth since the birthday than training allows', '#FBBF24', False
                            else:
                                w_txt, w_col = '✓ fits', '#34D399'
                            return (f"Actual wage: €{actual_w:,.0f} · Wage for these skills today: €{w_hi:,.0f} "
                                    f"(actual set on birthday, {wks:.1f} wk ago) {w_txt}"), w_col, ok
                        dev = float(res['Calc_Wage']) / max(float(wage_input.value or 0), 1.0) - 1
                        return (f"Wage: €{res['Calc_Wage']:,.0f}  ({delta_str(res['Calc_Wage'], wage_input.value)})",
                                delta_color(res['Calc_Wage'], wage_input.value, 0.005), abs(dev) <= 0.02)

                    def render_card_sliders(res, refs):
                        """Adjust the result right in the card: drag a skill bar, the skills that are not locked follow so TSI
                        stays exact. Locked (🔒): the main skill from the start and every bar you drag; click a lock to let
                        that skill follow again. Form / stamina: two small sliders. Only numbers move while dragging (in the
                        browser); the server checks the wage and updates the card when you let go."""
                        K5n = ['DE', 'PM', 'WI', 'Pas', 'SC']
                        if not refs.get('sl'):
                            return
                        base = dict(res)
                        main = max(K5n, key=lambda k: H_lookup_wage(float(base[k]), k))
                        st = {'key': f'card{id(res)}', 'locked': {main}, 'n': 0}

                        def put(el, text):
                            st['n'] += 1
                            el.set_content(f'{text}<!--{st["n"]}-->')

                        def cur():
                            v = {k: float(refs['sl'][k].value) for k in K5n}
                            v['f'], v['c'] = float(st['f'].value), float(st['c'].value)
                            return v

                        def build(v, locked):
                            return fast_rebalance(base, {k: v[k] for k in locked}, solve_tsi(), int(age_input.value),
                                                  int(days_input.value), spec_input.value, v['f'], v['c'], is_foreign=foreign_cb.value)

                        def main_range(v):
                            okv = []
                            for x in range(int(max(1.0, v[main] - 4) * 20), int((v[main] + 4) * 20) + 1):
                                nb = build(dict(v, **{main: x / 20}), st['locked'] | {main})
                                if nb is not None and wage_eval(nb)[2]:
                                    okv.append(x / 20)
                            return (min(okv), max(okv)) if okv else None

                        def show_locks():
                            for k in K5n:
                                on = k in st['locked']
                                refs['lock'][k].props(f"icon={'lock' if on else 'lock_open'}")
                                refs['lock'][k].tooltip('Locked: stays where it is (click to let it follow)' if on else
                                                        'Follows to keep TSI exact (drag the bar or click to lock it)')
                                refs['box'][k].classes(remove='tt-follow tt-locked').classes(add='tt-locked' if on else 'tt-follow')
                            free = [TRAIN_SKILLS[k] for k in K5n if k not in st['locked']]
                            put(st['follow'], (', '.join(free) + (' follows' if len(free) == 1 else ' follow')
                                               + ' (striped) so TSI stays exact · 🔒 = set by you, click to free it again')
                                if free else '⚠ Every skill is locked: free one (click a 🔒) so TSI can stay exact')
                            ui.run_javascript(f"if (window.ttCfg[{json.dumps(st['key'])}]) window.ttCfg[{json.dumps(st['key'])}].locked = "
                                              f"{json.dumps(sorted(st['locked']))};")

                        def paint(snap_main=True):
                            v = cur()
                            note = ''
                            if snap_main and main in st['locked']:
                                rng = main_range(v)
                                if rng and not (rng[0] - 1e-6 <= v[main] <= rng[1] + 1e-6):
                                    v[main] = min(max(v[main], rng[0]), rng[1])
                                    note = f' · {TRAIN_SKILLS[main]} kept within {rng[0]:.2f}–{rng[1]:.2f} (what the wage allows)'
                            nb = build(v, st['locked'])
                            if nb is None:
                                put(st['status'], '✗ These skills alone are already more than his TSI allows')
                                st['status'].style('color:#F87171;')
                                return
                            res.update({k: nb[k] for k in K5n + ['Vorm', 'Cond', 'Calc_TSI', 'Calc_Wage', 'Calc_HTMS', 'Calc_HTMS28']})
                            for k in K5n:
                                refs['sl'][k].set_value(round(float(res[k]), 2))
                                put(refs['word'][k], skill_level_label(res[k]))
                                put(refs['val'][k], f"{res[k]:.3f}")
                                refs['val'][k].style('color:' + ('inherit' if k in st['locked'] else '#FBBF24') + ';')
                            put(st['flab'], f"Form {res['Vorm']:.2f}")
                            put(st['clab'], f"Stamina {res['Cond']:.2f}")
                            refs['tsi'].set_text(f"TSI: {res['Calc_TSI']:,.0f}  ({tsi_delta_str(res['Calc_TSI'], solve_tsi())})")
                            wt, wc, ok = wage_eval(res)
                            refs['wage'].set_text(wt); refs['wage'].style(f'color: {wc};')
                            put(refs['fc'], f"Form {res['Vorm']:.3f}  Cond {res['Cond']:.3f}")
                            tsi_ok = abs(float(res['Calc_TSI']) - solve_tsi()) < 1.0
                            ui.run_javascript(f"if (window.ttCfg[{json.dumps(st['key'])}]) window.ttCfg[{json.dumps(st['key'])}].cur = "
                                              f"{json.dumps(dict({k: float(res[k]) for k in K5n}, f=float(res['Vorm']), c=float(res['Cond'])))};")
                            if not tsi_ok:
                                put(st['status'], '✗ TSI no longer fits: free a skill (click a 🔒)')
                                st['status'].style('color:#F87171;')
                            else:
                                put(st['status'], ('✓ adjusted: Apply saves what this card shows' if ok else '✗ the wage does not fit these skills') + note)
                                st['status'].style(f"color:{'#34D399' if ok else '#F87171'};")

                        def released(e, k):
                            try:
                                refs['sl'][k].value = float(e.args) if not isinstance(e.args, dict) else refs['sl'][k].value
                            except (TypeError, ValueError):
                                pass
                            st['locked'].add(k)
                            show_locks()
                            paint()

                        def toggle_lock(k):
                            if k in st['locked']:
                                st['locked'].discard(k)
                            else:
                                st['locked'].add(k)
                            show_locks()
                            paint(snap_main=False)

                        def reset():
                            """Back to the solver's result exactly (no rebalancing)."""
                            st['locked'] = {main}
                            res.update({k: base[k] for k in K5n + ['Vorm', 'Cond', 'Calc_TSI', 'Calc_Wage', 'Calc_HTMS', 'Calc_HTMS28']})
                            for k in K5n:
                                refs['sl'][k].set_value(round(float(base[k]), 2))
                                put(refs['word'][k], skill_level_label(base[k]))
                                put(refs['val'][k], f"{float(base[k]):.3f}")
                                refs['val'][k].style('color:inherit;')
                            st['f'].set_value(round(float(base['Vorm']), 2))
                            st['c'].set_value(round(float(base['Cond']), 2))
                            put(st['flab'], f"Form {float(base['Vorm']):.2f}")
                            put(st['clab'], f"Stamina {float(base['Cond']):.2f}")
                            refs['tsi'].set_text(f"TSI: {res['Calc_TSI']:,.0f}  ({tsi_delta_str(res['Calc_TSI'], solve_tsi())})")
                            wt, wc, _ = wage_eval(res)
                            refs['wage'].set_text(wt); refs['wage'].style(f'color: {wc};')
                            put(refs['fc'], f"Form {float(base['Vorm']):.3f}  Cond {float(base['Cond']):.3f}")
                            put(st['status'], '')
                            show_locks()
                            ui.run_javascript(f"if (window.ttCfg[{json.dumps(st['key'])}]) window.ttCfg[{json.dumps(st['key'])}].cur = "
                                              f"{json.dumps(dict({k: float(base[k]) for k in K5n}, f=float(base['Vorm']), c=float(base['Cond'])))};")

                        for k in K5n:
                            sl = refs['sl'][k]
                            sl.on('update:modelValue', js_handler=f"(v) => window.ttLive('{st['key']}', '{k}', v)")
                            sl.on('change', lambda e, k=k: released(e, k))
                            refs['lock'][k].on_click(lambda k=k: toggle_lock(k))

                        # form / stamina decimals: two small sliders under the bars
                        f0, c0 = int(float(base['Vorm'])), int(float(base['Cond']))
                        with ui.row().classes('w-full gap-6 no-wrap mt-1'):
                            for key, lo, hi, v0, lab in (('f', float(f0), min(f0 + 0.99, 8.0), float(base['Vorm']), 'Form'),
                                                          ('c', float(c0), round(min(c0 + 0.99, stamina_max(int(age_input.value))), 2),
                                                           float(base['Cond']), 'Stamina')):
                                with ui.column().classes('flex-1 gap-0'):
                                    with ui.row().classes('w-full justify-between'):
                                        st[key + 'lab'] = ui.html(f'{lab} {v0:.2f}').classes('text-xs text-gray-400')
                                        ui.label(f'{lo:.2f} – {hi:.2f}').classes('text-xs text-gray-500')
                                    with ui.element('div').classes('w-full tt-fs').style(f'--fs: {form_stamina_color(v0)};'):
                                        sl = QuietSlider(min=lo, max=hi, step=0.01, value=round(v0, 2)).props('dense').classes('w-full')
                                    sl.on('update:modelValue', js_handler=f"(v) => window.ttLive('{st['key']}', '{key}', v)")
                                    sl.on('change', lambda e, key=key, sl=sl: (setattr(sl, 'value', float(e.args) if not isinstance(e.args, dict) else sl.value), paint()))
                                    st[key] = sl
                        st['follow'] = ui.html('').classes('text-xs').style('color:#FBBF24;')
                        st['status'] = ui.html('').classes('text-xs')
                        with ui.row().classes('w-full justify-end'):
                            ui.button('↺ Reset', on_click=reset).props('outline dense no-caps size=sm')
                        show_locks()
                        _w = {'DE': 1.034, 'PM': 1.031, 'WI': 0.840, 'Pas': 1.000, 'SC': 1.038}
                        _s0 = sum(_w[k] * max(float(base[k]) - 1.0, 0.0) ** 3 for k in K5n)
                        _t0 = calculate_tsi_for_form(int(age_input.value), float(base['Vorm']), float(base['Cond']),
                                                     float(base.get('GK', 1.0)), *[float(base[k]) for k in K5n])
                        cfg = {'k0': _s0 * (solve_tsi() / _t0) ** 0.5 if _t0 > 0 else _s0,
                               'f0': float(base['Vorm']), 'c0': float(base['Cond']), 'w': _w, 'order': K5n,
                               'locked': sorted(st['locked']), 'base': {k: float(base[k]) for k in K5n},
                               'words': [tr(HATTRICK_SKILL_WORDS[i]) for i in range(21)],
                               't': {'form': tr('Form'), 'stamina': tr('Stamina'), 'cond': tr('Cond'),
                                     'release': tr('… release to check the wage'),
                                     'toomuch': tr('✗ These skills alone are already more than his TSI allows')},
                               'cur': dict({k: float(base[k]) for k in K5n}, f=float(base['Vorm']), c=float(base['Cond'])),
                               'ids': {'sl': {k: refs['sl'][k].id for k in K5n}, 'word': {k: refs['word'][k].id for k in K5n},
                                       'val': {k: refs['val'][k].id for k in K5n}, 'fc': refs['fc'].id, 'status': st['status'].id,
                                       'flab': st['flab'].id, 'clab': st['clab'].id}}
                        ui.run_javascript(f"window.ttCfg[{json.dumps(st['key'])}] = {json.dumps(cfg)};")

                    def bar_html(v):
                        v = max(0.0, min(float(v), 20.0))
                        return (f'<div style="position:relative;height:16px;border-radius:5px;background:#262730;overflow:hidden">'
                                f'<div style="position:absolute;left:0;top:0;bottom:0;width:{v / 20 * 100:.1f}%;background:#24782E"></div>'
                                f'<span style="position:absolute;left:6px;top:0;line-height:16px;font-size:11px;color:#FAFAFA">'
                                f'{skill_level_label(v)}</span></div>')

                    ui.label('✨ Estimated Subskill Alternative Builds').classes('text-lg font-semibold mt-2 mb-2')
                    _entries = []
                    _fwd_picked = []   # a forward profile picked by DFW / known playmaking / real HTMS
                    with ui.grid(columns=2).classes('w-full gap-4 items-start tt-as-res'):
                        _opt_left = ui.column().classes('w-full gap-0 min-w-0')
                        _opt_right = ui.column().classes('w-full gap-0 min-w-0 tt-optcol')
                    with _opt_left:
                        opt_no = 0
                        for idx, res in enumerate(shown):
                            if not res.get('Saved'):
                                opt_no += 1
                            _nt = False
                            _oc = bool(res.get('Outcomes'))
                            _cc, _cd = ((OC_ALT, OC_COLOR) if res.get('OutcomeAlt') else (OC_COLOR, OC_DARK)) if _oc else (NT_COLOR, NT_DARK)
                            _border = 'border: 2px solid #2F6EA8;' if res.get('Saved') else (f'border: 2px solid {_cc};' if (_nt or _oc) else '')
                            _head = ACCENT if res.get('Saved') else (f'linear-gradient(120deg, {_cd} 0%, {_cc} 100%)' if (_nt or _oc) else ACCENT_DARK)
                            _icon = '🎲 ' if _oc else ('🟢 ' if _nt else '')
                            with ui.card().classes('p-4 overflow-hidden w-full').style(_border) as _ocard:
                                _cn = res.get('Counts') or {}
                                _sub = (res.get('Sub') or (_cn.get('opt_label') if _cn.get('opt') is not None else '')
                                        or ('average of all that fit' if res.get('Strategy') == 'All Combos' else '')
                                        or (str(res.get('Note') or '').split('. ')[0][:70]))
                                _entries.append((_ocard, str(res.get('Strategy', '')), _sub, '📌' if res.get('Saved') else str(opt_no)))
                                if res.get('FwdPicked'):
                                    _fwd_picked.append(len(_entries) - 1)
                                ui.label(f"📌 {res['Strategy']}" if res.get('Saved') else f"{_icon}Option {opt_no}: {res['Strategy']}").classes('font-bold text-white -mx-4 -mt-4 mb-2 px-4 py-2 tt-otitle').style(f'background:{_head}; align-self: stretch;')
                                if res.get('Warning'):
                                    ui.label(f"⚠️ {res['Warning']}").classes('text-sm').style('color: #FBBF24;')
                                if res.get('Counts'):
                                    _cc = res['Counts']
                                    _chip = ('<span style="background:{bg};color:{fg};border-radius:6px;padding:1px 7px;'
                                             'font-weight:700;">{n}</span>')
                                    ui.html(
                                        f"Combinations: {_cc['grid']:,} possible → "
                                        + _chip.format(bg='rgba(96,165,250,.20)', fg='#60A5FA', n=f"{_cc['tsi']:,}")
                                        + f" fit TSI {_cc['tsi_v']:,.0f}"
                                        + ((" → " + _chip.format(bg='rgba(167,139,250,.20)', fg='#A78BFA', n=f"{_cc['levels']:,}")
                                            + " fit your known levels") if _cc['levels'] != _cc['tsi'] else '')
                                        + " → " + _chip.format(bg='rgba(52,211,153,.22)', fg='#34D399', n=f"{_cc['wage']:,}")
                                        + f" also fit wage €{_cc['wage_v']:,.0f}"
                                        + ((" → " + _chip.format(bg='rgba(251,191,36,.20)', fg='#FBBF24', n=f"{_cc['opt']:,}")
                                            + f" <span style=\"color:#FBBF24\">{_cc['opt_label']}</span>") if _cc.get('opt') is not None else '')
                                    ).classes('text-xs text-gray-300 tt-counts')
                                if res.get('Sure'):
                                    _per, _ex, _in1 = res['Sure']
                                    _ord = sorted(_per, key=lambda k: -float(res.get(k, 0) or 0))
                                    ui.html(f"<b>{tr('How sure')}:</b> " + ' · '.join(
                                        f"{tr(TRAIN_SKILLS[k])} {_per[k][0]} – {_per[k][1] * 100:.0f}%" for k in _ord)
                                        + ' · ' + trf('about {} of 5 skills exactly right, {} within 1 level', f"{_ex:.1f}", f"{_in1:.1f}")
                                        ).classes('text-xs text-gray-300 tt-sure').tooltip(
                                        tr('The chance each skill is at this level. Tested on 191 players with known skills.'))
                                if res.get('Note'):
                                    ui.label(res['Note']).classes('text-xs text-gray-400')
                                refs = {'bar': {}, 'val': {}}
                                refs['tsi'] = ui.label(f"TSI: {res['Calc_TSI']:,.0f}  ({tsi_delta_str(res['Calc_TSI'], solve_tsi())})" + (' · corrected TSI' if ((inj_cb.value and float(inj_weeks.value or 0) > 0) or bday_cb.value) else '')).classes('text-base font-semibold').style(f'color: {delta_color(res["Calc_TSI"], solve_tsi(), 0.005)};')
                                _wt, _wc, _ok = wage_eval(res)
                                refs['wage'] = ui.label(_wt).classes('text-sm font-semibold').style(f'color: {_wc};')

                                # Skills as bars out of 20 (same look as the Estimator). Adjustable cards: the five outfield
                                # skills are sliders inside their bar (drag the bar), with a lock to keep a skill where it is.
                                _adj = (not res.get('Saved')) and normalize_position(pos_input.value) != 'K'
                                refs.update({'sl': {}, 'box': {}, 'word': {}, 'lock': {}})
                                with ui.column().classes('w-full gap-1 mt-2 mb-2'):
                                    for sk, sk_name in [('GK', 'Keeper'), ('DE', 'Defending'), ('PM', 'Playmaking'), ('WI', 'Winger'),
                                                        ('Pas', 'Passing'), ('SC', 'Scoring'), ('SH', 'Set pieces')]:
                                        v = max(0.0, min(float(res[sk]), 20.0))
                                        with ui.row().classes('w-full items-center gap-2 no-wrap').style('min-height:24px;'):
                                            ui.label(sk_name).classes('text-xs text-gray-400').style('width:72px; flex-shrink:0;')
                                            if _adj and sk in ('DE', 'PM', 'WI', 'Pas', 'SC'):
                                                with ui.element('div').classes('flex-1 min-w-0 tt-skbar') as _box:
                                                    refs['sl'][sk] = QuietSlider(min=0, max=20, step=0.01, value=round(v, 2)) \
                                                        .props('dense track-size=16px thumb-size=18px').classes('w-full')
                                                    refs['word'][sk] = ui.html(skill_level_label(v)).classes('tt-word')
                                                refs['box'][sk] = _box
                                            else:
                                                refs['bar'][sk] = ui.html(bar_html(v)).classes('flex-1 min-w-0')
                                            refs['val'][sk] = ui.html(f"{res[sk]:.3f}").classes('text-sm font-bold text-right').style('width:52px; flex-shrink:0;')
                                            if _adj:
                                                if sk in ('DE', 'PM', 'WI', 'Pas', 'SC'):
                                                    refs['lock'][sk] = ui.button(icon='lock_open').props('flat round dense size=xs') \
                                                        .style('width:22px; flex-shrink:0;')
                                                else:
                                                    ui.element('div').style('width:22px; flex-shrink:0;')

                                refs['fc'] = ui.html(f"Form {res['Vorm']:.3f}  Cond {res['Cond']:.3f}").classes('text-sm text-gray-400')
                                htms_v, htms28_v = res['Calc_HTMS'], res['Calc_HTMS28']
                                htms_is_estimated = htms_unknown_cb.value
                                htms_label = 'vs estimate' if htms_is_estimated else 'vs target'
                                if isinstance(htms_v, (int, float)):
                                    # An estimated HTMS isn't a real target: show the difference neutrally.
                                    _hc = '#9CA3AF' if htms_is_estimated else delta_color(htms_v, res['Target_HTMS'], 0.01)
                                    ui.label(f"HTMS: {htms_v:.1f}  ({delta_str(htms_v, res['Target_HTMS']).replace('vs target', htms_label)})").classes('text-sm font-semibold').style(f'color: {_hc};')
                                else:
                                    ui.label(f"HTMS: {htms_v}").classes('text-sm text-gray-400')
                                if isinstance(htms28_v, (int, float)):
                                    _hc28 = '#9CA3AF' if htms_is_estimated else delta_color(htms28_v, res['Target_HTMS28'], 0.01)
                                    ui.label(f"HTMS28: {htms28_v:.1f}  ({delta_str(htms28_v, res['Target_HTMS28']).replace('vs target', htms_label)})").classes('text-sm font-semibold').style(f'color: {_hc28};')
                                else:
                                    ui.label(f"HTMS28: {htms28_v}").classes('text-sm text-gray-400')

                                if not res.get('Saved') and normalize_position(pos_input.value) != 'K':
                                    render_card_sliders(res, refs)

                                if res.get('Saved'):
                                    continue   # already saved: no apply / copy buttons
                                idx = opt_no - 1

                                def apply_option(res=res):
                                    if is_empty:
                                        ui.notify('⚠️ Select an existing player first.', type='warning')
                                        return
                                    try:
                                        prow = df_raw[df_raw['Speler'] == selected]
                                        cur_htms = safe_float(prow['HTMS'].iloc[0]) if not prow.empty else 0.0
                                        cur_htms28 = safe_float(prow['HTMS28'].iloc[0]) if not prow.empty else 0.0
                                        conn = get_db_connection()
                                        cursor = conn.cursor()
                                        # Always store an HTMS, and remember whether it is real:
                                        # - "HTMS Unknown" ticked: the HTMS of the applied skills, marked as estimate
                                        #   (shown everywhere, but never offered as a target on the next solve);
                                        # - unticked: the HTMS you entered, marked as real.
                                        if htms_unknown_cb.value:
                                            new_htms = float(res['Calc_HTMS'])
                                            new_h28 = (float(res['Calc_HTMS28']) if isinstance(res['Calc_HTMS28'], (int, float))
                                                       else float(calculate_htms_potential(int(age_input.value), int(days_input.value), new_htms)))
                                            htms_est = 1
                                        else:
                                            new_htms = float(htms_input.value or 0) or float(res['Calc_HTMS'])
                                            new_h28 = (float(htms28_input.value) if (not htms28_unknown_cb.value and (htms28_input.value or 0) > 0)
                                                       else float(calculate_htms_potential(int(age_input.value), int(days_input.value), new_htms)))
                                            htms_est = 0
                                        cursor.execute(
                                            'UPDATE skills_data SET GK=?,DE=?,PM=?,WI=?,Pas=?,SC=?,SH=?,Vorm=?,Conditie=?,HTMS=?,HTMS28=?,HTMS_est=? '
                                            'WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                                            (*[round(float(res[_k]), 6) for _k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH')],
                                             # Keep the solver's sub-level (e.g. 6.54). The solver page itself
                                             # still starts from the whole level when it loads the player.
                                             round(float(res['Vorm']), 6), round(float(res['Cond']), 6),
                                             new_htms, new_h28, htms_est, user, selected))
                                        cursor.execute('UPDATE skills_data SET "Foreign"=? WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                                                       (1 if foreign_cb.value else 0, user, selected))
                                        conn.commit(); conn.close()
                                        load_user_db.clear()

                                        ref_msg = ''
                                        if ref_sync_cb.value:
                                            ref_row = {
                                                'PlayerID': prow.get('PlayerID', [0]).iloc[0] if not prow.empty else 0,
                                                'Speler': selected,
                                                'Nationality': prow.get('Nationality', ['Netherlands']).iloc[0] if not prow.empty else 'Netherlands',
                                                'Positie': prow.get('Positie', ['']).iloc[0] if not prow.empty else '',
                                                'Specialiteit': prow.get('Specialiteit', ['None']).iloc[0] if not prow.empty else 'None',
                                                'Leeftijd': prow.get('Leeftijd', [20]).iloc[0] if not prow.empty else 20,
                                                'dag(en)': prow.get('dag(en)', [0]).iloc[0] if not prow.empty else 0,
                                                'TSI': prow.get('TSI', [1000]).iloc[0] if not prow.empty else 1000,
                                                'Loon': prow.get('Loon', [1000]).iloc[0] if not prow.empty else 1000,
                                                'HTMS': float(res['Calc_HTMS']) if isinstance(res['Calc_HTMS'], (int, float)) else cur_htms,
                                                'HTMS28': float(res['Calc_HTMS28']) if isinstance(res['Calc_HTMS28'], (int, float)) else cur_htms28,
                                                'GK': res['GK'], 'DE': res['DE'], 'PM': res['PM'], 'WI': res['WI'],
                                                'Pas': res['Pas'], 'SC': res['SC'], 'SH': res['SH'],
                                            }
                                            ref_result = sync_player_to_reference_db(ref_row, user, source='autosolver')
                                            if ref_result == 'updated':
                                                ref_msg = ' 🗄️ Reference DB entry updated.'
                                            elif ref_result == 'inserted':
                                                ref_msg = ' 🗄️ Added to Reference DB.'

                                        ui.notify(f'✅ Option {idx + 1} applied to {selected}!{ref_msg}', type='positive')
                                    except Exception as e:
                                        ui.notify(f'Error applying: {e}', type='negative')

                                ui.button(f'📥 Apply Option {idx + 1}', on_click=apply_option, color=None).classes('mt-2 w-full tt-goldbtn')

                                def make_ht_markup(res=res, idx=idx, diag=diag):
                                    from ht_engine import skill_level_label
                                    htms_str   = f"{res['Calc_HTMS']:.2f}"   if isinstance(res['Calc_HTMS'],  (int,float)) else '?'
                                    htms28_str = f"{res['Calc_HTMS28']:.2f}" if isinstance(res['Calc_HTMS28'],(int,float)) else '?'
                                    htms_tag   = ' (Est.)' if htms_unknown_cb.value else ''
                                    foreign_str = 'Yes' if foreign_cb.value else 'No'
                                    tsi_delta  = res['Calc_TSI'] - solve_tsi()
                                    wage_delta = res['Calc_Wage'] - float(wage_input.value or 0)
                                    pri_col = diag.get('primary_col', 'SC')
                                    pri_val = diag.get('inferred_primary_birthday', diag.get('inferred_primary', 0))
                                    pri_word = skill_level_label(pri_val)
                                    sec_avg = diag.get('residual_secondary_avg', 0)
                                    peers   = diag.get('ref_players_found', 0)

                                    # Pull extra player data if available
                                    pid_link = ''; spec_short = spec_input.value or '-'
                                    xp = '-'; ls = '-'; nat = '-'
                                    if not is_empty:
                                        try:
                                            prow = df_raw[df_raw['Speler'] == selected]
                                            if not prow.empty:
                                                pid = prow.get('PlayerID', [None]).iloc[0]
                                                if pid and str(pid) not in ('0','nan',''):
                                                    pid_link = f"[playerid={int(float(pid))}]"
                                                xp_val = prow.get('Ervaring', [None]).iloc[0]
                                                if xp_val and str(xp_val) not in ('nan',''):
                                                    xp = str(int(float(xp_val)))
                                                ls_val = prow.get('Leiderschap', [None]).iloc[0]
                                                if ls_val and str(ls_val) not in ('nan',''):
                                                    ls = str(int(float(ls_val)))
                                                nat_val = prow.get('Nationality', [None]).iloc[0]
                                                if nat_val and str(nat_val) not in ('nan',''):
                                                    nat = str(nat_val)
                                        except Exception:
                                            pass

                                    # Spec short code like HT shows: H=Head, Q=Quick, U=Unpred, T=Tech, P=Powerful
                                    spec_map = {'Head':'H','Quick':'Q','Unpredictable':'U','Technical':'T','Powerful':'P','None':'-','Geen':'-'}
                                    spec_code = spec_map.get(spec_short, spec_short[:1])
                                    player_label = f"{pid_link}" if pid_link else f"[b]{selected or 'Player'}[/b] ({spec_code})"

                                    # Nat short code (3 letter)
                                    nat3_map = {
                                        'Netherlands':'NLD','Nederland':'NLD','Belgium':'BEL','België':'BEL',
                                        'Germany':'DEU','Deutschland':'DEU','France':'FRA','Spain':'ESP',
                                        'Italy':'ITA','England':'ENG','Portugal':'POR','Brazil':'BRA',
                                        'Argentina':'ARG','Sweden':'SWE','Norway':'NOR','Denmark':'DEN',
                                        'Finland':'FIN','Poland':'POL','Turkey':'TUR','Croatia':'CRO',
                                        'Serbia':'SRB','Romania':'ROU','Greece':'GRE','Russia':'RUS',
                                        'Ukraine':'UKR','Japan':'JPN','Switzerland':'SUI','Austria':'AUT',
                                        'Czech Republic':'CZE','USA':'USA','Mexico':'MEX','Colombia':'COL',
                                        'Chile':'CHI','Uruguay':'URU','Iceland':'ISL',
                                    }
                                    nat3 = nat3_map.get(nat, nat[:3].upper() if nat != '-' else '-')
                                    age_str = f"{age_input.value},{days_input.value}"

                                    header = "[tr][th]ID[/th][th]Name[/th][th]Pos[/th][th]Age[/th][th]Nat[/th][th]FO[/th][th]CO[/th][th]GK[/th][th]DEF[/th][th]PM[/th][th]WI[/th][th]PS[/th][th]SC[/th][th]SP[/th][th]XP[/th][th]LS[/th][th]HTMS[/th][th]HTMS28[/th][/tr]"
                                    row    = f"[tr][td]{player_label}[/td][td][b]{selected or '?'}[/b][/td][td]{pos_input.value}[/td][td]{age_str}[/td][td]{nat3}[/td][td]{res['Vorm']:.1f}[/td][td]{forum_stamina(res['Cond']):.1f}[/td][td]{res['GK']:.2f}[/td][td]{res['DE']:.2f}[/td][td]{res['PM']:.2f}[/td][td]{res['WI']:.2f}[/td][td]{res['Pas']:.2f}[/td][td]{res['SC']:.2f}[/td][td]{res['SH']:.2f}[/td][td]{xp}[/td][td]{ls}[/td][td]{htms_str}{htms_tag}[/td][td]{htms28_str}{htms_tag}[/td][/tr]"

                                    lines = [
                                        f"[b]Option {idx+1}: {res['Strategy']}[/b]",
                                        f"[b]TSI:[/b] {res['Calc_TSI']:,.0f} vs target {solve_tsi():,.0f} (diff {tsi_delta:+,.0f}) | [b]Wage:[/b] \u20ac{res['Calc_Wage']:,.0f} vs target \u20ac{float(wage_input.value or 0):,.0f} (diff {wage_delta:+,.0f}) | Foreign: {foreign_str}",
                                        f"[b]HTMS:[/b] {htms_str}{htms_tag} | [b]HTMS28:[/b] {htms28_str}{htms_tag} | [b]Inferred Primary ({pri_col}):[/b] {pri_val:.2f} ({pri_word}) | [b]Avg Sec:[/b] {sec_avg:.2f} | [b]DB Peers:[/b] {peers}",
                                        *([f"[i]Combinations: {res['Counts']['grid']:,} possible → {res['Counts']['tsi']:,} fit TSI → "
                                           f"{res['Counts']['wage']:,} also fit wage"
                                           + (f" → {res['Counts']['opt']:,} {res['Counts'].get('opt_label', '')}" if res['Counts'].get('opt') is not None else '')
                                           + "[/i]"] if res.get('Counts') else []),
                                        "",
                                        f"[table]{header}{row}[/table]",
                                    ]
                                    markup = '\n'.join(lines)
                                    if len(markup) > 3900:
                                        markup = markup[:3897] + '...'
                                    return markup

                                def copy_markup(res=res, idx=idx):
                                    markup = make_ht_markup(res, idx)
                                    char_count = len(markup)
                                    import json
                                    markup_json = json.dumps(markup)
                                    ui.run_javascript(f'''
                                        var text = {markup_json};
                                        navigator.clipboard.writeText(text).then(
                                            () => console.log("Copied"),
                                            () => {{
                                                const ta = document.createElement("textarea");
                                                ta.value = text;
                                                document.body.appendChild(ta);
                                                ta.select();
                                                document.execCommand("copy");
                                                document.body.removeChild(ta);
                                            }}
                                        );
                                    ''')
                                    ui.notify(f'📋 Option {idx+1} copied! ({char_count} chars)', type='positive')


                                # Same option as one player for the HT forum (Hattline "Copy Player" layout).
                                def make_forum_markup(res=res):
                                    prow = df_raw[df_raw['Speler'] == selected] if not is_empty else df_raw.iloc[0:0]
                                    def val(col):
                                        return prow[col].iloc[0] if (not prow.empty and col in prow.columns) else None
                                    return player_forum_markup(
                                        selected or 'Player', val('PlayerID'), age_input.value, days_input.value,
                                        val('Ervaring'), val('Leiderschap'), tsi_input.value, pos_input.value,
                                        wage_input.value, spec_input.value, val('Injuries'),
                                        res['Vorm'], res['Cond'], {k: res[k] for k in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']})
                                # Markup is only built when a button is clicked, and goes straight to the
                                # clipboard (no text boxes: lighter page, faster results).
                                with ui.row().classes('w-full items-center gap-2 mt-3'):
                                    ui.button('📋 Copy HT markup', on_click=copy_markup).props('outline dense no-caps')
                                    ui.button('📋 Copy player (HT forum)',
                                              on_click=lambda res=res, idx=idx: copy_text(make_forum_markup(res), f'Option {idx + 1} as player')
                                              ).props('outline dense no-caps')

                    # Options list on the right: one option at a time on the left, click another to show it
                    _rows = []

                    def _pick_opt(i):
                        for j, (_c, _t, _s, _n) in enumerate(_entries):
                            (_c.classes(remove='tt-hidecard') if j == i else _c.classes(add='tt-hidecard'))
                        for j, _r in enumerate(_rows):
                            (_r.classes(add='tt-optitem-on') if j == i else _r.classes(remove='tt-optitem-on'))
                    with _opt_right:
                        with ui.card().classes('w-full p-4 gap-2 tt-optlist'):
                            ui.label('Options').classes('tt-optlist-h')
                            for i, (_c, _t, _s, _n) in enumerate(_entries):
                                with ui.row().classes('w-full items-center gap-3 no-wrap tt-optitem cursor-pointer') as _r:
                                    ui.label(_n).classes('tt-optnum')
                                    import html as _html
                                    ui.html(f'<div class="font-semibold tt-optt">{_html.escape(tr(_t))}</div>'
                                            + (f'<div class="text-xs text-gray-400 tt-opts">{_html.escape(_s)}</div>' if _s else '')).classes('min-w-0')
                                    # stars: in a test on 191 players with known skills, All Combos was the closest
                                    # option for 44%, the Alternative for 27% (one of the two: 71%)
                                    # a picked forward profile beats them (Aćim with his HTMS: 0.24 levels off, All Combos 1.85)
                                    if _fwd_picked:
                                        _star = '★★' if i == _fwd_picked[0] else ('★' if _t == 'All Combos' else '')
                                    else:
                                        _star = '★★' if _t == 'All Combos' else ('★' if str(_t).startswith('Alternative') else '')
                                    if _star:
                                        with ui.label(_star).classes('tt-optstar'):
                                            ui.tooltip(tr('Most often the closest to his real skills') if _star == '★★'
                                                       else tr('Second most often the closest'))
                                _r.on('click', lambda _e=None, i=i: _pick_opt(i))
                                _rows.append(_r)
                    if _entries:
                        _pick_opt(_fwd_picked[0] if _fwd_picked else 0)

                with ui.row().classes('items-center gap-4 mt-4 flex-wrap'):
                    solve_btn = ui.button('⚡ Run Subskill Auto-Solver', on_click=run_solver, color=None).classes('tt-goldbtn').style('min-height: 48px; font-size: 16px;')
                    solve_status = ui.row().classes('items-center gap-2 hidden')
                    with solve_status:
                        ui.spinner(size='sm', color='white')
                        ui.label('Solving…').classes('text-sm font-semibold').style('color: #2F6EA8;')
                        solve_dots = ui.label('(10-20s)').classes('text-xs text-gray-400')
                results_area
                similar_area

        player_select.on_value_change(lambda e: render_content.refresh())
        render_content()