import pandas as pd
from nicegui import ui, app
from shell import apply_theme, require_login, render_sidebar, markup_block, ACCENT, ACCENT_DARK, page_title, _split_icon
from i18n import tr, trf
import numpy as np
from scipy.optimize import linear_sum_assignment
from data_layer import (load_user_db, safe_float, build_pitch_overview_svg, get_db_connection, get_watchlists,
                        save_named_lineup, get_saved_lineups, delete_saved_lineup, set_user_pref)
from ht_engine import (
    experience_rating_bonus, MID_EXPERIENCE_BLANCO_SHARE,
    normalize_position,
    normalize_nationality, get_flag, hatstats, indirect_set_piece_ratings, special_event_counts,
    PITCH_LAYOUT, COACH_MULTIPLIERS, WEATHER_SPECIALTY_MULT, LOCATION_MULTIPLIERS, ATTITUDE_MULTIPLIERS,
    STACK_PENALTY_MULT, get_predictor_key, get_player_status, get_weather_multiplier, get_stack_combo_type,
    get_tactic_mults, get_team_spirit_multiplier, get_team_confidence_multiplier, clean_spec,
    infer_position_from_skills,
)
from role_weights import get_role_weights
from richtskills_data import RICHTSKILLS_DEFAULT

POSITION_SHORT_DISPLAY = {
    'K': 'K', 'NCD': 'CD', 'OCD': 'CD', 'CAD': 'CD', 'NWB': 'WB', 'SHWB': 'WB',
    'PDIM': 'DM', 'NIM': 'IM', 'OIM-Q': 'IM', 'OIM-H': 'IM',
    'NW': 'W', 'WTM': 'W', 'DFW': 'FW', 'NFW': 'FW', 'PNF': 'FW',
}
SKILL_KEYS = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC']

# Formation (defenders-midfielders-forwards) -> pitch slots. Midfield includes the wingers.
_DEF = {2: ['LCD', 'RCD'], 3: ['LCD', 'CD', 'RCD'], 4: ['LWB', 'LCD', 'RCD', 'RWB'], 5: ['LWB', 'LCD', 'CD', 'RCD', 'RWB']}
_MID = {2: ['LIM', 'RIM'], 3: ['LIM', 'CM', 'RIM'], 4: ['LW', 'LIM', 'RIM', 'RW'], 5: ['LW', 'LIM', 'CM', 'RIM', 'RW']}
_FWD = {0: [], 1: ['CFW'], 2: ['LFW', 'RFW'], 3: ['LFW', 'CFW', 'RFW']}
FORMATIONS = {f'{d}-{m}-{f}': ['K'] + _DEF[d] + _MID[m] + _FWD[f]
              for d, m, f in [(5, 5, 0), (5, 4, 1), (5, 3, 2), (5, 2, 3), (4, 5, 1), (4, 4, 2),
                              (4, 3, 3), (3, 5, 2), (3, 4, 3), (2, 5, 3)]}
BEST_FORMATION = 'Best (auto)'
# The most used Hattrick lineup, the default: wing-back - CD - wing-back, NW + 3 NIM + WTM,
# a powerful forward (PNF) when there is one, and a normal forward.
DEFAULT_FORMATION = '3-5-2 (WB-CD-WB)'
FORMATIONS[DEFAULT_FORMATION] = ['K', 'LWB', 'CD', 'RWB', 'LW', 'LIM', 'CM', 'RIM', 'RW', 'LFW', 'RFW']
FORMATION_ROLES = {DEFAULT_FORMATION: {'K': 'K', 'LWB': 'NWB', 'CD': 'CD', 'RWB': 'NWB',
                                       'LW': 'WTM', 'LIM': 'NIM', 'CM': 'NIM', 'RIM': 'NIM', 'RW': 'NW',
                                       'LFW': 'PNF', 'RFW': 'NFW'}}


def _player_skills(prow):
    return {sk: max(safe_float(prow.get(sk, 0.0)) - 1.0, 0.0) for sk in SKILL_KEYS}




def weights_role(role, specialty):
    """The role whose contributions apply. In Hattrick a 'technical defensive forward' is simply a DFW
    played by a Technical player: the specialty gives the extra passing to the side attack (41% vs 31%).
    So DFW/TDFW + Technical -> TDFW contributions, and DFW/TDFW without Technical -> DFW."""
    if role in ('DFW', 'TDFW'):
        return 'TDFW' if str(specialty or '').strip() == 'Technical' else 'DFW'
    return role

NORMAL_ROLES = ('NIM', 'NW', 'CD', 'NCD', 'NWB', 'NFW', 'K')   # Auto-Fill's role when the player's own position doesn't fit

HT_POST_LIMIT = 3000   # characters a Hattrick forum post may hold (the copy button warns above it)
_PITCH_ROWS = [('FW', [None, 'LFW', 'CFW', 'RFW', None]),
               ('MID', ['LW', 'LIM', 'CM', 'RIM', 'RW']),
               ('DEF', ['LWB', 'LCD', 'CD', 'RCD', 'RWB']),
               ('K', [None, None, 'K', None, None])]


def lineup_markup(lineup_players, ratings, sp_info=None, head=''):
    """Lineup as a Hattrick forum table shaped like the pitch, with the sector ratings right under
    each line (attack under the forwards, midfield under the midfield, defence under the defence).
    Surname + role per player keeps it well within a forum post."""
    def cell(slot):
        p = lineup_players.get(slot) if slot else None
        if not p:
            return ''
        name = str(p.get('Speler', '') or '').strip().split(' ')[-1]
        return f"{name} ({p.get('Positie', '')})"

    def r(sec):
        v = (ratings or {}).get(sec)
        return f'[b]{sec} {float(v):.2f}[/b]' if v is not None else ''
    rating_rows = {'FW': ['', r('LA'), r('CA'), r('RA'), ''],
                   'MID': ['', '', r('MID'), '', ''],
                   'DEF': [r('LD'), '', r('CD'), '', r('RD')]}
    rows = []
    for line, slots in _PITCH_ROWS:
        if any(lineup_players.get(s) for s in slots if s):
            rows.append('[tr]' + ''.join(f'[td]{cell(s)}[/td]' for s in slots) + '[/tr]')
        if line in rating_rows:
            rows.append('[tr]' + ''.join(f'[td]{c}[/td]' for c in rating_rows[line]) + '[/tr]')
    out = (f'[b]{head}[/b]\n' if head else '') + '[table]' + ''.join(rows) + '[/table]'
    if ratings:
        extra = [f'HatStats {hatstats(ratings):.0f}']
        if sp_info:
            c = sp_info.get('counts', {})
            isp = sp_info.get('isp', {})
            extra.append(f"ISP {float(isp.get('att', 0)):.2f} / {float(isp.get('def', 0)):.2f}")
            extra.append(f"PNF {c.get('PNF', 0)} · CD {c.get('CD', 0)} · PDIM {c.get('PDIM', 0)}")
        out += '\n' + ' · '.join(extra)
    return out

def lineup_page_css():
    return ('<style>'
            '.tt-lu-main.nicegui-grid { grid-template-columns: minmax(0, 1fr) !important; }'
            '@media (min-width: 1100px) { .tt-lu-main.nicegui-grid { grid-template-columns: minmax(0, 3fr) minmax(0, 2fr) !important; } }'
            '.tt-pitch { min-height: 560px; padding: 22px 14px 18px !important; }'
            '.tt-pitch-row { margin: 22px 0 !important; }'
            '.tt-tok { width: 46px !important; height: 46px !important; font-size: 13px !important; }'
            # on the pitch: the ratings box (bottom right, Hattrick style), the formation/tactic box (bottom left)
            # and the captain tag (top left); the players never move for them
            '.tt-pitch-row:last-child { min-height: 150px; }'
            '.tt-onpitch { position: absolute; z-index: 4; background: rgba(9,22,38,.9); border: 1px solid rgba(246,197,16,.55);'
            '  border-radius: 9px; box-shadow: 0 4px 12px rgba(0,0,0,.35); color: #C9D4E0; }'
            '.tt-onpitch:empty { display: none; }'
            '.tt-ratbox { right: 12px; bottom: 12px; padding: 5px 6px; }'
            '.tt-rbg { display: grid; grid-template-columns: repeat(3, 54px); gap: 3px; text-align: center; }'
            '.tt-rbg div { background: rgba(255,255,255,.07); border-radius: 5px; padding: 1px 0 2px; }'
            '.tt-rbg b { display: block; font: 600 13px Oswald, sans-serif; line-height: 1.2; color: #fff; }'
            '.tt-rbg span { display: block; font-size: 8px; color: #9FB0C3; text-transform: uppercase; letter-spacing: .03em; }'
            '.tt-rbg .tt-rbm { grid-column: 1 / -1; background: rgba(246,197,16,.16); }'
            '.tt-rbg .tt-rbm b { color: #F6C510; font-size: 15px; }'
            '.tt-tacbox { left: 12px; bottom: 12px; padding: 5px 9px 6px; min-width: 156px; }'
            '.tt-tb-fm { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding-bottom: 3px; margin-bottom: 3px;'
            '  border-bottom: 1px solid rgba(255,255,255,.12); }'
            '.tt-tb-fm b { font: 700 19px Oswald, sans-serif; color: #fff; letter-spacing: .04em; }'
            '.tt-tb-h, .tt-tb-fm span { font: 600 9.5px Oswald, sans-serif; letter-spacing: .12em; text-transform: uppercase; color: #9FB0C3; }'
            '.tt-tb-h { color: #F6C510; margin-bottom: 1px; }'
            '.tt-tb-r { display: flex; justify-content: space-between; gap: 14px; font-size: 11px; line-height: 1.55; }'
            '.tt-tb-r b { font: 600 12.5px Oswald, sans-serif; color: #fff; }'
            '.tt-tb-on, .tt-tb-on b { color: #F6C510 !important; }'
            '.tt-tb-hs { border-top: 1px solid rgba(255,255,255,.12); margin-top: 2px; padding-top: 2px; }'
            '.tt-captag { left: 12px; top: 12px; padding: 4px 10px; font-size: 12px; border-color: rgba(255,255,255,.25); }'
            '.tt-captag b { color: #F6C510; }'
            '.tt-pitch { position: relative; border-radius: 12px; padding: 14px 12px 10px; overflow: hidden;'
            '  background: repeating-linear-gradient(180deg, #24782E 0 12.5%, #1F6D29 12.5% 25%); border: 1px solid #2E8A39; }'
            '.tt-pitch-lines { position: absolute; inset: 0; pointer-events: none; }'
            '.tt-pitch-lines svg { width: 100%; height: 100%; display: block; }'
            '.tt-pitch-row { position: relative; margin: 10px 0; }'
            '.tt-pitch .tt-slot { background: transparent !important; border: 0 !important; padding: 0 !important; }'
            '.tt-tok { width: 40px; height: 40px; border-radius: 50%; background: #14304D; border: 2px solid #FFFFFF; color: #FFFFFF;'
            '  display: grid; place-items: center; font: 600 12px Oswald, sans-serif; line-height: 1; margin: 0 auto 3px;'
            '  box-shadow: 0 3px 8px rgba(0,0,0,.4); position: relative; }'
            '.tt-tok small { position: absolute; right: -6px; top: -4px; background: #F6C510; color: #0C2036; border-radius: 999px;'
            '  font: 700 9px Barlow, sans-serif; padding: 1px 4px; }'
            '.tt-tok small:empty { display: none; }'
            '.tt-pitch .tt-slot .q-field__label { display: none !important; }'
            '.tt-pitch .tt-slot .q-field { padding-top: 0 !important; width: 100%; }'
            '.tt-pitch .tt-slot .q-field:not(.q-textarea):not(.q-select--multiple) .q-field__control { background: rgba(10,26,44,.85) !important; border-radius: 999px !important;'
            '  min-height: 26px !important; height: 26px !important; padding: 0 6px !important; }'
            '.tt-pitch .tt-slot .q-field:not(.q-textarea):not(.q-select--multiple) .q-field__marginal { height: 26px !important; min-height: 26px !important; }'
            '.tt-pitch .tt-slot .q-field:not(.q-textarea):not(.q-select--multiple) .q-field__native, .tt-pitch .tt-slot .q-field:not(.q-textarea):not(.q-select--multiple) .q-field__input { min-height: 26px !important; padding: 0 !important; }'
            '.tt-pitch .tt-slot .q-field__control:before { border-color: rgba(255,255,255,.35) !important; border-radius: 999px !important; }'
            '.tt-pitch .tt-slot .q-field__append { display: none !important; }'
            '.tt-pitch .tt-slot .q-field__native { justify-content: center; min-height: 26px !important; padding: 0 !important;'
            '  font-size: 12.5px !important; font-weight: 600 !important; color: #FFFFFF; text-shadow: 0 1px 2px rgba(0,0,0,.6); }'
            '.tt-pitch .tt-slot .q-field + .q-field.q-field:not(.q-textarea):not(.q-select--multiple) .q-field__control { background: rgba(246,197,16,.18) !important; height: 22px !important;'
            '  min-height: 22px !important; margin-top: 3px; }'
            '.tt-pitch .tt-slot .q-field + .q-field .q-field__native { font-size: 11px !important; color: #F6E7A6; min-height: 22px !important; }'
            '.tt-pitch .tt-slot .q-field + .q-field.q-field:not(.q-textarea):not(.q-select--multiple) .q-field__marginal { height: 22px !important; min-height: 22px !important; }'
            '.tt-pitch .tt-pitch-row.nicegui-grid { column-gap: 6px !important; }'
            # names: the pill may reach into the gap next to it; on hover it grows to show the whole name
            '.tt-pitch .tt-slot { position: relative; }'
            '.tt-pitch .tt-slot > .q-field:first-of-type { width: calc(100% + 10px) !important; margin: 0 -5px; }'
            '.tt-pitch .tt-slot .q-field__native { font-size: 12px !important; letter-spacing: -.01em; }'
            '.tt-pitch .tt-slot > .q-field:first-of-type { max-width: 180px; }'
            '.tt-pitch .tt-slot > .q-field + .q-field { max-width: 130px; }'
            '.tt-pitch .tt-slot:hover { z-index: 20; }'
            '.tt-pitch .tt-slot:hover > .q-field:first-of-type { width: max-content !important; min-width: min(calc(100% + 10px), 180px); max-width: none;'
            '  position: relative; left: 50%; transform: translateX(-50%); margin: 0; }'
            '.tt-pitch .tt-slot:hover > .q-field:first-of-type .q-field__control { box-shadow: 0 6px 18px rgba(0,0,0,.55); background: #0C2036 !important; }'
            '.tt-pitch .tt-slot:hover .q-field__native > span, .tt-pitch .tt-slot:hover .q-field__native > span > span { overflow: visible !important; text-overflow: clip !important; }'
            '.tt-biglvl { font-family: Oswald, sans-serif; font-size: 40px; font-weight: 700; color: #F6C510; line-height: 1; }'
            '.tt-kvrow { padding: 6px 0; border-bottom: 1px dashed #33465C; }'
            '.tt-kvv { font-family: Oswald, sans-serif; font-size: 16px; font-weight: 600; }'
            '.tt-capt { border: 1px solid #2A3647; border-radius: 10px; padding: 8px 10px; }'
            '.tt-capn { width: 26px; height: 26px; border-radius: 50%; background: rgba(255,255,255,.1); color: #D5E3F2;'
            '  display: grid; place-items: center; font-family: Oswald, sans-serif; font-weight: 700; flex-shrink: 0; }'
            '.tt-capn-on { background: #F6C510; color: #0C2036; }'
            '</style>')


PITCH_LINES_SVG = ('<svg viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
                   '<g fill="none" stroke="rgba(255,255,255,.55)" stroke-width=".35" vector-effect="non-scaling-stroke">'
                   '<rect x="1.5" y="1.5" width="97" height="97"/><line x1="1.5" y1="50" x2="98.5" y2="50"/>'
                   '<ellipse cx="50" cy="50" rx="9" ry="7"/><rect x="27" y="1.5" width="46" height="14"/>'
                   '<rect x="27" y="84.5" width="46" height="14"/></g></svg>')


def tactic_levels_from_lineup(lp):
    """Tactic levels from the players on the pitch (Hattrick Codex): long shots, AIM/AOW and counter-attacks."""
    out = {'LS': None, 'AIM': None, 'CA': None}
    outf = [p for sid, p in lp.items() if sid != 'K']
    if not outf:
        return out
    g = lambda p, k, d=0.0: safe_float(p.get(k, d))
    sc = sum(g(p, 'SC') for p in outf) / len(outf)
    sp = sum(g(p, 'SH') for p in outf) / len(outf)
    out['LS'] = max(1.0, 1.66 * sc + 0.55 * sp - 7.6)
    out['AIM'] = max(1.0, sum(g(p, 'Pas') for p in outf) / 5.0 - 2.0)
    defs = [p for sid, p in lp.items() if sid in ('LWB', 'LCD', 'CD', 'RCD', 'RWB')]
    if defs:
        out['CA'] = max(1.0, 0.0173 * sum(g(p, 'Vorm', 6.0) * (2 * g(p, 'Pas') + g(p, 'DE')) for p in defs) + 1.04)
    return out


@ui.page('/lineup')
def lineup_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    df_raw = load_user_db(user)
    render_sidebar(user, '/lineup')
    ui.add_head_html(lineup_page_css())

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_title('/lineup')

        if df_raw.empty:
            ui.label('⚠️ Please import or add players to your roster first.').classes('text-yellow-400')
            return

        def player_pos_display(pname):
            prow_match = df_raw[df_raw['Speler'] == pname]
            if prow_match.empty:
                return '?'
            prow = prow_match.iloc[0]
            pos = str(prow.get('Positie', '') or '').strip()
            if pos not in RICHTSKILLS_DEFAULT:
                pos = infer_position_from_skills(safe_float(prow.get('GK', 1.0)), safe_float(prow.get('DE', 1.0)), safe_float(prow.get('PM', 1.0)),
                                                  safe_float(prow.get('WI', 1.0)), safe_float(prow.get('Pas', 1.0)), safe_float(prow.get('SC', 1.0)))
            return POSITION_SHORT_DISPLAY.get(pos, pos)

        player_names = df_raw['Speler'].dropna().tolist()
        player_option_map = {'-- Empty --': '-- Empty --'}
        for name in player_names:
            player_option_map[name] = f'{name} ({player_pos_display(name)})'
        try:
            import spec_icons as SI
            _spn = dict(zip(df_raw['Speler'], df_raw['Specialiteit'])) if 'Specialiteit' in df_raw.columns else {}
            SPEC_BY_LABEL = {lab: _spn.get(n) for n, lab in player_option_map.items()}
        except Exception:
            SI, SPEC_BY_LABEL = None, {}

        # Filter by country / watchlist (same choices as the Auto-Solver).
        try:
            watchlists = get_watchlists(user)
        except Exception:
            watchlists = {}
        countries = (sorted(set(normalize_nationality(c) for c in df_raw['Nationality'].dropna().unique()))
                     if 'Nationality' in df_raw.columns else [])
        ALL_PLAYERS = '🌍 All Players'
        filter_opts = [ALL_PLAYERS] + [f'{get_flag(c)} {c}' for c in countries] + \
                      [f'📋 {n}' for n in watchlists if n != '__EMPTY__']

        def _base_filtered_names():
            val = filter_select.value or ALL_PLAYERS
            if val == ALL_PLAYERS:
                return player_names
            if val.startswith('📋 '):
                members = set(watchlists.get(val[len('📋 '):], []))
                return [p for p in player_names if p in members]
            country = val.split(' ', 1)[1] if ' ' in val else val
            return df_raw[df_raw['Nationality'].apply(normalize_nationality) == country]['Speler'].dropna().tolist()

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

        def filtered_option_map(keep=()):
            names = set(get_filtered_names()) | {k for k in keep if k and k != '-- Empty --'}
            return {k: v for k, v in player_option_map.items() if k == '-- Empty --' or k in names}

        # Same look as the Score Predictor: team-colour cards with section titles and button toggles.
        _C, _CD = ACCENT, ACCENT_DARK
        ui.add_css(
            f'.tt-us.q-btn-group {{ border: 1px solid {_C}; border-radius: 8px; overflow: hidden; }}'
            f'.tt-us .q-btn {{ color: #B8BCC8; background: #1F2029; padding: 2px 10px; }}'
            f'.tt-us .q-btn.bg-ttus {{ background: {_C} !important; color: #FFFFFF !important; font-weight: 600; }}'
            '.tt-slot { background: #1C1C24; border: 1px solid #3B3B4D; border-radius: 8px; padding: 6px 8px 4px; }'
            # chosen player in a slot: one line, specialty icon first, no '(position)' (the role is shown below)
            '.tt-slot .q-field__native > span { display:flex; align-items:center; min-width:0; overflow:hidden; white-space:nowrap; }'
            '.tt-slot .q-field__native > span > span { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }'
            '.tt-slot .q-field__native > span > .tt-spec { order:-1; flex-shrink:0; margin-left:0; margin-right:6px; }'
            '.tt-slot .q-field__native > span > span:not(.tt-spec):not(:first-child) { display:none; }'
            '.tt-slot .q-select:not(.q-field--focused) .q-field__input { width:0 !important; min-width:0 !important; flex:0 0 0 !important; padding:0 !important; }'
            '.tt-slot .q-field__control { padding-left:8px !important; padding-right:4px !important; }'
            '.tt-slot .q-field__append { padding-left:2px !important; }'
            '.tt-tile { background: #262730; border-radius: 8px; padding: 6px 10px; text-align: center; }')

        def tt_section(name, color=_C):
            ui.label(name).classes('text-xs font-bold uppercase mt-1').style(f'color: {color}; letter-spacing: 0.12em;')

        def tt_header(title, sub_label=None):
            _ic, _tx = _split_icon(title)
            with ui.element('div').classes('w-full px-4 pt-3 pb-2 tt-chead'):
                with ui.row().classes('items-center gap-3 no-wrap'):
                    if _ic:
                        ui.html(f'<span class="tt-cbadge">{_ic}</span>')
                    ui.label(_tx).classes('tt-ctitle')
                if sub_label is not None:
                    return ui.label(sub_label).classes('text-xs').style('color: #DCE6F0;')
            return None

        with ui.column().classes('w-full gap-0') as _top_holder:
            with ui.card().classes('w-full p-0 gap-0 overflow-hidden tt-card') as settings_card:
                tt_header('⚙️ Match settings')
                with ui.column().classes('w-full px-4 pt-2 pb-3 gap-2'):
                    tt_section('Tactic')
                    with ui.row().classes('w-full gap-2 no-wrap items-end'):
                        tactic_select = ui.select(['Normal', 'AIM', 'AOW', 'Counter', 'Creative', 'Long Shots'], value='Normal',
                                                  label='Team Tactic').props('dense').classes('flex-grow min-w-0')
                        tskill_input = ui.number('Tactic Skill Level', value=10.0, min=1.0, max=30.0, step=1.0).props('dense').classes('w-36')
                    tactic_area = ui.row().classes('w-full gap-2 items-center')   # "use the level from the pitch"
                    tt_section('Attitude & venue')
                    with ui.row().classes('w-full items-center gap-2 flex-wrap'):
                        attitude_select = ui.toggle({'PIC (Play It Cool)': 'PIC', 'Normal': 'Normal', 'MOTS (Match of the Season)': 'MOTS'},
                                                    value='Normal') \
                            .props('dense no-caps unelevated toggle-color=ttus toggle-text-color=white').classes('tt-toggle tt-us').mark('lineup-attitude')
                        location_select = ui.toggle({'Away / neutral': 'Away / neutral', 'Home': 'Home', 'Derby': 'Derby'},
                                                    value='Away / neutral') \
                            .props('dense no-caps unelevated toggle-color=ttus toggle-text-color=white').classes('tt-toggle tt-us').mark('lineup-venue')
                    tt_section('Team')
                    # One box each: the exact number, with Hattrick's name for it shown right in the box (6.5 -> content)
                    from ht_engine import TS_LEVELS, TC_LEVELS, level_name
                    with ui.grid(columns=2).classes('w-full gap-2'):
                        ts_input = ui.number(tr('Team spirit'), value=5.0, min=0.1, max=10.99, step=0.01).props('dense')
                        tc_input = ui.number(tr('Team confidence'), value=4.5, min=0.0, max=9.99, step=0.01).props('dense')

                    def _name_suffix(num, names):
                        num.props(f'suffix="{tr(level_name(num.value, names))}"')
                    _name_suffix(ts_input, TS_LEVELS)
                    _name_suffix(tc_input, TC_LEVELS)
                    ts_input.on_value_change(lambda e: _name_suffix(ts_input, TS_LEVELS))
                    tc_input.on_value_change(lambda e: _name_suffix(tc_input, TC_LEVELS))
                    _ts_txt = lambda: f"{ts_input.value} ({tr(level_name(ts_input.value, TS_LEVELS))})"
                    _tc_txt = lambda: f"{tc_input.value} ({tr(level_name(tc_input.value, TC_LEVELS))})"
                    tt_section('Coach & weather')
                    _coach_keys = list(COACH_MULTIPLIERS.keys())
                    _coach_mid = _coach_keys.index('Neutral Coach') if 'Neutral Coach' in _coach_keys else len(_coach_keys) // 2
                    with ui.row().classes('w-full items-center gap-3 no-wrap'):
                        ui.label('100% DEF').classes('text-xs text-gray-400')
                        coach_slider = ui.slider(min=0, max=len(_coach_keys) - 1, step=1, value=_coach_mid) \
                            .props('dense color=blue-grey-5 markers').classes('flex-grow')
                        ui.label('100% ATT').classes('text-xs text-gray-400')
                    with ui.grid(columns=2).classes('w-full gap-2'):
                        coach_select = ui.select(_coach_keys, value=_coach_keys[_coach_mid], label='Coach Setting').props('dense')
                        weather_select = ui.select(list(WEATHER_SPECIALTY_MULT.keys()), value='Normal / Overcast', label='Weather').props('dense')
                    # slider and drop-down are one setting: everything calculates from coach_select
                    coach_slider.on_value_change(lambda e: coach_select.set_value(_coach_keys[int(e.value)])
                                                 if coach_select.value != _coach_keys[int(e.value)] else None)
                    coach_select.on_value_change(lambda e: coach_slider.set_value(_coach_keys.index(e.value))
                                                 if e.value in _coach_keys and int(coach_slider.value) != _coach_keys.index(e.value) else None)

            with ui.card().classes('w-full p-0 gap-0 overflow-hidden tt-card') as ratings_card:
                ratings_sub = tt_header('🏁 Sector ratings', 'Put players on the pitch: the ratings follow every change you make')
                ratings_area = ui.column().classes('w-full px-4 pt-2 pb-3 gap-2')

        # Live ratings: every change (settings, players, roles) recalculates after a short pause,
        # so typing a number or dragging the slider doesn't recalculate on every step.
        def _live_tick():
            live_timer.deactivate()
            try:
                if build_lineup_players()[0]:
                    calculate()
            except Exception:
                pass
        live_timer = ui.timer(0.35, _live_tick, active=False)

        def live_recalc(_=None):
            live_timer.deactivate()
            live_timer.activate()

        slot_widgets = {}
        ALL_SLOTS = [s for row in PITCH_LAYOUT for s in row]

        def player_slot_score(prow, pos_label, roles, forced=None):
            """Best (score, role) for this player in this slot. forced: the formation's fixed role."""
            skills = _player_skills(prow)
            status = get_player_status(safe_float(prow.get('Vorm', 6.0)), safe_float(prow.get('Conditie', 6.0)),
                                       safe_float(prow.get('Ervaring', 4.0)))
            if forced:
                role = forced
                if forced == 'PNF' and clean_spec(prow.get('Specialiteit', 'None')) != 'Powerful':
                    return (0.0, role)          # the PNF slot is for a powerful forward only
            else:
                # Role: the player's own position if it fits this slot (WTM, PDIM, OIM-H, ...), otherwise
                # the normal role. Taking the role with the biggest total of all contributions picked
                # roles that feed many sectors (DW on the wing, IMTW in midfield) and cost midfield.
                own = normalize_position(str(prow.get('Positie') or ''))
                role = own if own in roles else next((r for r in roles if r in NORMAL_ROLES), roles[0])
            weights = get_role_weights(get_predictor_key(pos_label, weights_role(role, clean_spec(prow.get('Specialiteit', 'None')))))
            if not weights:
                return (0.0, role)
            sc = sum(w * skills.get(sk, 0.0) for sw in weights.values() for sk, w in sw.items()) * status
            return (sc, role)

        def best_assignment(slot_ids, pool, forced_roles=None):
            """Optimal player-to-slot assignment (Hungarian method) for the given slots."""
            slots = [s for s in ALL_SLOTS if s[0] in slot_ids]
            rows = list(pool.iterrows())
            if not rows or not slots:
                return 0.0, {}
            forced_roles = dict(forced_roles or {})
            # PNF slot: only when there's a powerful forward in the pool, otherwise a normal forward.
            if 'PNF' in forced_roles.values() and not any(
                    clean_spec(r.get('Specialiteit', 'None')) == 'Powerful'
                    and normalize_position(str(r.get('Positie') or '')) in ('NFW', 'PNF') for _, r in rows):
                forced_roles = {k: ('NFW' if v == 'PNF' else v) for k, v in forced_roles.items()}
            score = np.zeros((len(rows), len(slots)))
            role = {}
            for i, (_, prow) in enumerate(rows):
                for j, (sid, lbl, roles) in enumerate(slots):
                    score[i, j], role[(i, j)] = player_slot_score(prow, lbl, roles, forced_roles.get(sid))
            ri, ci = linear_sum_assignment(-score)
            assign = {slots[j][0]: (rows[i][1]['Speler'], role[(i, j)]) for i, j in zip(ri, ci) if score[i, j] > 0}
            return float(sum(score[i, j] for i, j in zip(ri, ci))), assign

        def active_slot_ids():
            f = formation_select.value
            return set(FORMATIONS[f]) if f in FORMATIONS else {s[0] for s in ALL_SLOTS}

        DEF_SLOTS = ['LWB', 'LCD', 'CD', 'RCD', 'RWB']
        MID_SLOTS = ['LW', 'LIM', 'CM', 'RIM', 'RW']
        FWD_SLOTS = ['LFW', 'CFW', 'RFW']

        def filled(sid):
            w = slot_widgets.get(sid)
            return bool(w) and w['player'].value not in (None, '-- Empty --')

        def lineup_formation():
            """The lineup actually on the pitch, e.g. '4-4-2' (for the ratings / score predictor)."""
            d, m, f = (sum(filled(s) for s in grp) for grp in (DEF_SLOTS, MID_SLOTS, FWD_SLOTS))
            return f'{d}-{m}-{f}', d + m + f + (1 if filled('K') else 0)

        def apply_filter(_=None):
            for sid, w in slot_widgets.items():
                cur = w['player'].value
                w['player'].set_options(filtered_option_map(keep=(cur,)), value=cur)

        def auto_fill():
            pool = df_raw[df_raw['Speler'].isin(set(get_filtered_names()))].dropna(subset=['Speler'])
            if pool.empty:
                ui.notify('⚠️ No players in this filter.', type='warning')
                return
            if formation_select.value == BEST_FORMATION:
                # Only formations with two central defenders and two wing-backs (4-5-1, 4-4-2, 4-3-3):
                # three CDs instead of wing-backs isn't how national teams are normally set up.
                best = max(((best_assignment(set(ids), pool), name) for name, ids in FORMATIONS.items()
                            if name.startswith('4-')), key=lambda x: x[0][0])
                (_, assignment), chosen = best
                formation_select.set_value(chosen)
                ui.notify(f'🪄 Best formation for these players: {chosen}', type='positive')
            else:
                _, assignment = best_assignment(active_slot_ids(), pool, FORMATION_ROLES.get(formation_select.value))
            for sid, w in slot_widgets.items():
                if w.get('col') is not None:      # pitch slots: empty the ones outside the formation
                    w['player'].set_value('-- Empty --')
            # At most one winger towards middle: a second WTM plays as a normal winger.
            if assignment.get('LW', (None, ''))[1] == 'WTM' and assignment.get('RW', (None, ''))[1] == 'WTM':
                assignment['RW'] = (assignment['RW'][0], 'NW')
            for sid, (pname, prole) in assignment.items():
                slot_widgets[sid]['player'].set_value(pname)
                slot_widgets[sid]['role'].set_value(prole)
            used = {p for p, _ in assignment.values()}
            active = active_slot_ids()
            rest = []
            for _, prow in pool.iterrows():
                if prow['Speler'] in used:
                    continue
                rest.append((max(player_slot_score(prow, lbl, roles)[0] for sid, lbl, roles in ALL_SLOTS if sid in active),
                             prow['Speler']))
            bench = [p for _, p in sorted(rest, reverse=True)[:5]]
            for i in range(1, 6):
                slot_widgets[f'SUB{i}']['player'].set_value(bench[i - 1] if i <= len(bench) else '-- Empty --')

        # Pitch: five fixed columns (left wing .. right wing), so every line lines up as a formation.
        SLOT_COL = {'LFW': 2, 'CFW': 3, 'RFW': 4, 'LW': 1, 'LIM': 2, 'CM': 3, 'RIM': 4, 'RW': 5,
                    'LWB': 1, 'LCD': 2, 'CD': 3, 'RCD': 4, 'RWB': 5, 'K': 3}
        LINE_NAMES = ['Attack', 'Midfield', 'Defence', 'Keeper']
        with ui.card().classes('w-full p-0 gap-0 overflow-hidden tt-card') as pitch_card:
            pitch_sub = tt_header('⚽ Lineup', 'Choose a player and role per position, or let Auto-Fill pick the best XI')
            with ui.column().classes('w-full px-4 pt-3 pb-3 gap-1'):
                with ui.row().classes('w-full gap-2 items-end flex-wrap'):
                    filter_select = ui.select(filter_opts, value=ALL_PLAYERS, label='Players from (country / watchlist)').props('dense').classes('w-64')
                    abroad_cb = ui.switch('✈️ Abroad only').props('dense')
                    formation_select = ui.select([BEST_FORMATION, DEFAULT_FORMATION] + [f for f in FORMATIONS if f != DEFAULT_FORMATION],
                                                 value=DEFAULT_FORMATION, label='Formation').props('dense').classes('w-48')
                    TAKER_AUTO = '(best set pieces on the pitch)'
                    taker_select = ui.select([TAKER_AUTO], value=TAKER_AUTO, label='Set-piece taker').props('dense').classes('w-60')
                    ui.button('🪄 Auto-Fill Best XI', on_click=lambda: auto_fill(), color=None).props('no-caps').classes('tt-goldbtn')
                with ui.element('div').classes('w-full mt-2 tt-pitch'):
                    ui.html(PITCH_LINES_SVG).classes('tt-pitch-lines')
                    rat_box = ui.html('').classes('tt-onpitch tt-ratbox')
                    tac_box = ui.html('').classes('tt-onpitch tt-tacbox')
                    cap_tag = ui.html('').classes('tt-onpitch tt-captag')
                    for line_idx, row_slots in enumerate(PITCH_LAYOUT):
                        with ui.grid(columns=5).classes('w-full gap-2 tt-pitch-row'):
                            for slot_id, pos_label, allowed_roles in row_slots:
                                with ui.column().classes('gap-0 min-w-0 tt-slot items-center').style(f'grid-column: {SLOT_COL.get(slot_id, 3)};') as slot_col:
                                    _short = 'GK' if slot_id == 'K' else pos_label.split(' ')[0]
                                    _side = {'(LI)': 'L', '(RE)': 'R', '(CNT)': 'C'}.get(pos_label.split(' ')[-1], '')
                                    ui.html(f'<div class="tt-tok">{_short}<small>{_side}</small></div>')
                                    p_select = ui.select(player_option_map, value='-- Empty --', label=pos_label,
                                                         with_input=True).props('dense borderless').classes('w-full')
                                    if SI is not None:
                                        SI.player_select(p_select, SPEC_BY_LABEL, selected=False, short=True)
                                    r_select = ui.select(allowed_roles, value=allowed_roles[0]).props('dense borderless') \
                                        .classes('w-full text-xs')
                                    r_select.bind_visibility_from(p_select, 'value', backward=lambda v: v != '-- Empty --')
                                    slot_widgets[slot_id] = {'player': p_select, 'role': r_select, 'col': slot_col}

                                    def _own_role(e, r_select=r_select, allowed=allowed_roles):
                                        # a player picked by hand gets his own position as role if it fits here
                                        name = e.value if e.value != '-- Empty --' else None
                                        if not name or df_raw.empty:
                                            return
                                        rows = df_raw[df_raw['Speler'] == name]
                                        if not rows.empty:
                                            own = normalize_position(str(rows.iloc[0].get('Positie') or ''))
                                            if own in allowed and r_select.value != own:
                                                r_select.set_value(own)
                                    p_select.on_value_change(_own_role)
                                    # on the pitch: 'J. Ciežkowski'; hover for the whole name
                                    with p_select:
                                        _tip = ui.tooltip('').props('anchor="top middle" self="bottom middle" :offset="[0, 6]"')

                                    p_select.on_value_change(lambda e, tip=_tip: tip.set_text(
                                        '' if not e.value or e.value == '-- Empty --' else str(e.value)))
                rat_line = ui.row().classes('w-full items-center justify-between gap-2 mt-2 no-wrap')
                tt_section('Bench')
                with ui.grid(columns=5).classes('w-full gap-2'):
                    for i in range(1, 6):
                        sub_id = f'SUB{i}'
                        with ui.column().classes('min-w-0 gap-0 tt-slot'):
                            sub_select = ui.select(player_option_map, value='-- Empty --', label=f'Substitute {i}',
                                                   with_input=True).props('dense borderless').classes('w-full')
                            if SI is not None:
                                SI.player_select(sub_select, SPEC_BY_LABEL, selected=False)
                        slot_widgets[sub_id] = {'player': sub_select, 'role': None, 'col': None}

        filter_select.on_value_change(apply_filter)
        abroad_cb.on_value_change(apply_filter)

        # ── Layout: the pitch full width; match settings and the captain picker below it ──
        # (the ratings, the formation + tactic level and the captain show in boxes on the pitch)
        with ui.column().classes('w-full gap-4 mb-2') as _main:
            _pitch_holder = ui.column().classes('w-full gap-4 min-w-0')
            with ui.grid(columns=2).classes('w-full gap-4 items-start tt-lu-main'):
                _left = ui.column().classes('w-full gap-4 min-w-0')
                _right = ui.column().classes('w-full gap-4 min-w-0')
        _main.move(_top_holder, target_index=0)
        pitch_card.move(_pitch_holder)
        ratings_card.move(_left)
        ratings_card.set_visibility(False)   # the ratings now show in the box on the pitch
        settings_card.move(_left)
        with _right:
            with ui.card().classes('w-full p-0 gap-0 overflow-hidden tt-card'):
                tt_header('©️ Captain picker', 'Ranked by leadership, then experience (the 11 on the pitch)')
                captain_area = ui.column().classes('w-full px-4 pt-3 pb-4 gap-2')

        def render_side():
            lp, _ = build_lineup_players()
            lv = tactic_levels_from_lineup(lp)
            cur = tactic_select.value
            key = {'Long Shots': 'LS', 'AIM': 'AIM', 'AOW': 'AIM', 'Counter': 'CA'}.get(cur)
            # the box on the pitch: formation, tactic levels and HatStats
            _f = lambda v: f"{v:.1f}" if v is not None else '–'
            _sr = last_sector_ratings.get('value') or {}
            _hs = f"{hatstats(_sr):.0f}" if (lp and _sr) else '–'
            rows = ''.join(f'<div class="tt-tb-r{" tt-tb-on" if key == k else ""}"><span>{tr(lab)}</span><b>{_f(lv.get(k))}</b></div>'
                           for k, lab in (('LS', 'Long shots'), ('AIM', 'AIM/AOW'), ('CA', 'Counter')))
            tac_box.set_content(
                f'<div class="tt-tb-fm"><span>{tr("Formation")}</span><b>{lineup_formation()[0] if lp else "–"}</b></div>'
                f'<div class="tt-tb-h">{tr("Tactic level")}</div>{rows}'
                f'<div class="tt-tb-r tt-tb-hs"><span>HatStats</span><b>{_hs}</b></div>')
            tactic_area.clear()
            if key and lv.get(key) is not None:
                with tactic_area:
                    ui.button(trf('Use {} as the tactic skill level', f"{min(30.0, max(1.0, lv[key])):.1f}"), color=None,
                              on_click=lambda v=lv[key]: tskill_input.set_value(round(min(30.0, max(1.0, v)), 1))) \
                        .props('unelevated no-caps dense').classes('tt-ghost')
            captain_area.clear()
            with captain_area:
                cands = sorted(((safe_float(p.get('Leiderschap', 0)), safe_float(p.get('Ervaring', 0)), p.get('Speler', '?'))
                                for sid, p in lp.items()), key=lambda t: (-t[0], -t[1]))
                if not cands:
                    ui.label('Put players on the pitch to pick a captain.').classes('text-sm text-gray-400')
            cap_tag.set_content(f'©️ {tr("Captain")}: <b>{cands[0][2]}</b>' if cands else '')
            with captain_area:
                for i, (ld, xp, nm) in enumerate(cands[:3]):
                    with ui.row().classes('w-full items-center gap-3 no-wrap tt-capt'):
                        ui.label(str(i + 1)).classes('tt-capn' + (' tt-capn-on' if i == 0 else ''))
                        with ui.column().classes('gap-0 min-w-0'):
                            ui.label(nm).classes('font-semibold truncate')
                            ui.label(trf('leadership {} · experience {}', f"{ld:.0f}", f"{xp:.0f}")).classes('text-xs text-gray-400')

        SLOT_POS_LABEL = {sid: lbl for row in PITCH_LAYOUT for sid, lbl, _ in row}

        def build_lineup_players():
            lineup_players, used_players = {}, []
            for row_slots in PITCH_LAYOUT:
                for slot_id, pos_label, allowed_roles in row_slots:
                    sel_p = slot_widgets[slot_id]['player'].value
                    if sel_p and sel_p != '-- Empty --':
                        p_row_db = df_raw[df_raw['Speler'] == sel_p].iloc[0]
                        p_dict = p_row_db.to_dict()
                        p_dict['Positie'] = slot_widgets[slot_id]['role'].value
                        lineup_players[slot_id] = p_dict
                        used_players.append(sel_p)
            return lineup_players, used_players

        last_sector_ratings = {'value': {}}

        def refresh_taker_options():
            names = [TAKER_AUTO] + sorted({w['player'].value for w in slot_widgets.values()
                                           if w.get('role') is not None and w['player'].value not in (None, '-- Empty --')})
            keep = taker_select.value if taker_select.value in names else TAKER_AUTO
            taker_select.set_options(names, value=keep)

        def set_piece_summary(lineup_players):
            """ISP attack/defence (HO formulas), keeper GK/SH and #PNF/#CD/#PDIM of this lineup."""
            sk = lambda p: {k: float(safe_float(p.get(k, 0))) for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH')}
            keeper = sk(lineup_players['K']) if 'K' in lineup_players else None
            players = [sk(p) if sid != 'K' else keeper for sid, p in lineup_players.items()]
            taker = None
            if taker_select.value not in (None, TAKER_AUTO):
                for p in lineup_players.values():
                    if p.get('Speler') == taker_select.value:
                        taker = sk(p)
            if taker is None:
                outf = [(sid, p) for sid, p in lineup_players.items() if sid != 'K'] or list(lineup_players.items())
                tsid, tp = max(outf, key=lambda it: float(safe_float(it[1].get('SH', 0)))) if outf else (None, None)
                taker = sk(tp) if tp is not None else None
                taker_name = tp.get('Speler') if tp is not None else '-'
            else:
                taker_name = taker_select.value
            att, dfn = indirect_set_piece_ratings(players, keeper, taker)
            return {'isp': {'att': round(att, 2), 'def': round(dfn, 2)}, 'taker': taker_name,
                    'keeper': {'gk': round(keeper['GK'], 2), 'sh': round(keeper['SH'], 2)} if keeper else None,
                    'counts': special_event_counts(lineup_players)}

        def refresh_pitch_preview():
            refresh_taker_options()
            lineup_players, _ = build_lineup_players()
            try:
                render_side()
            except NameError:
                pass

        for slot_id, widgets in slot_widgets.items():
            widgets['player'].on_value_change(lambda e: (refresh_pitch_preview(), live_recalc()))
            if widgets['role'] is not None:
                widgets['role'].on_value_change(lambda e: (refresh_pitch_preview(), live_recalc()))

        # (the old 'Field picture' is gone: the formation shows in the box on the pitch)
        refresh_pitch_preview()

        warning_area = ui.column().classes('w-full')
        results_area = ui.column().classes('w-full')

        def calculate():
            warning_area.clear()
            results_area.clear()

            lineup_players, used_players = build_lineup_players()

            dupes = sorted({p for p in used_players if used_players.count(p) > 1})
            if dupes:
                with warning_area:
                    ui.label(f"⚠️ Same player in multiple slots: {', '.join(dupes)}. Fix before calculating.").classes('text-yellow-400')
            if len(used_players) > 11:
                with warning_area:
                    ui.label(f'⚠️ {len(used_players)} players selected — a valid lineup needs exactly 11.').classes('text-yellow-400')

            if not lineup_players:
                with warning_area:
                    ui.label('⚠️ Select at least one player on the pitch first.').classes('text-yellow-400')
                return

            SLOT_POS_LABEL = {sid: lbl for row in PITCH_LAYOUT for sid, lbl, _ in row}
            ts_mult = get_team_spirit_multiplier(ts_input.value)
            tc_mult = get_team_confidence_multiplier(tc_input.value)
            coach_def, coach_off = COACH_MULTIPLIERS.get(coach_select.value, (1.0, 1.0))
            mid_m, rd_m, cd_m, ld_m, ra_m, ca_m, la_m = get_tactic_mults(tactic_select.value)
            tactic_fx = min(max(float(tskill_input.value), 0.0) / 20.0, 1.0)
            eff = lambda raw: 1.0 + (raw - 1.0) * tactic_fx
            TACTIC_MULT_BY_SECTOR = {'MID': eff(mid_m), 'RD': eff(rd_m), 'CD': eff(cd_m), 'LD': eff(ld_m), 'RA': eff(ra_m), 'CA': eff(ca_m), 'LA': eff(la_m)}
            SECTOR_BUCKET = {'CD': 'def', 'RD': 'def', 'LD': 'def', 'MID': 'mid', 'CA': 'att', 'RA': 'att', 'LA': 'att'}
            COACH_MULT_BY_BUCKET = {'def': coach_def, 'mid': 1.0, 'att': coach_off}
            SECTOR_CONSTANTS = {'MID': 0.266, 'RD': 0.67, 'CD': 0.375, 'LD': 0.67, 'RA': 0.47, 'CA': 0.3675, 'LA': 0.47}
            POSITION_CLUSTER_PENALTY = {'CD': {1: 1.0, 2: 0.964, 3: 0.900}, 'IM': {1: 1.0, 2: 0.935, 3: 0.825}, 'FW': {1: 1.0, 2: 0.945, 3: 0.865}}
            loc_mult = LOCATION_MULTIPLIERS.get(location_select.value, 1.0)
            att_mult = ATTITUDE_MULTIPLIERS.get(attitude_select.value, 1.0)

            cd_count = sum(1 for slot in ['LCD', 'CD', 'RCD'] if slot in lineup_players)
            im_count = sum(1 for slot in ['LIM', 'CM', 'RIM'] if slot in lineup_players)
            fw_count = sum(1 for slot in ['LFW', 'CFW', 'RFW'] if slot in lineup_players)

            contributions = {}
            for slot_id, prow in lineup_players.items():
                pos_label = SLOT_POS_LABEL[slot_id]
                role_code = str(prow.get('Positie', '') or '')
                specialty = clean_spec(prow.get('Specialiteit', 'None'))
                weights = get_role_weights(get_predictor_key(pos_label, weights_role(role_code, specialty)))
                status_mult = get_player_status(safe_float(prow.get('Vorm', 6.0)), safe_float(prow.get('Conditie', 6.0)), safe_float(prow.get('Ervaring', 4.0)))
                # Midfield: form x stamina only; experience comes in as a small rating bonus (WesselV1)
                # further on. Defence and attack keep BLANCO's experience factor (their calibration).
                status_mid = get_player_status(safe_float(prow.get('Vorm', 6.0)), safe_float(prow.get('Conditie', 6.0)),
                                               safe_float(prow.get('Ervaring', 4.0)), with_experience=False)
                weather_mult = get_weather_multiplier(weather_select.value, specialty)
                stack_type = get_stack_combo_type(role_code, specialty)
                skills = _player_skills(prow)
                pos_penalty = 1.0
                if slot_id in ['LCD', 'CD', 'RCD']: pos_penalty = POSITION_CLUSTER_PENALTY['CD'].get(cd_count, 1.0)
                elif slot_id in ['LIM', 'CM', 'RIM']: pos_penalty = POSITION_CLUSTER_PENALTY['IM'].get(im_count, 1.0)
                elif slot_id in ['LFW', 'CFW', 'RFW']: pos_penalty = POSITION_CLUSTER_PENALTY['FW'].get(fw_count, 1.0)
                per_sector_raw = {sector: sum(w * skills.get(sk, 0.0) for sk, w in sw.items()) for sector, sw in weights.items()}
                contributions[slot_id] = {
                    'player': prow.get('Speler', '?'), 'role': role_code, 'specialty': specialty,
                    'status_mult': status_mult, 'weather_mult': weather_mult, 'stack_type': stack_type,
                    'pos_penalty': pos_penalty, 'per_sector_raw': per_sector_raw,
                    'status_mid': status_mid, 'xp': safe_float(prow.get('Ervaring', 4.0)),
                }

            by_stack = {}
            for slot_id, c in contributions.items():
                if c['stack_type']:
                    by_stack.setdefault(c['stack_type'], []).append(slot_id)
            for stack_type, slot_ids in by_stack.items():
                for i, slot_id in enumerate(sorted(slot_ids)):
                    contributions[slot_id]['stack_penalty'] = STACK_PENALTY_MULT.get(min(i + 1, 3), STACK_PENALTY_MULT[3])
            for slot_id, c in contributions.items():
                c.setdefault('stack_penalty', 1.0)
                mult = c['status_mult'] * c['weather_mult'] * c['stack_penalty'] * c['pos_penalty']
                # Midfield: half of BLANCO's experience factor + half of WesselV1's rating bonus (added
                # below); fits Finland's real-match ratings (Pernaug). Other sectors: BLANCO.
                _b = MID_EXPERIENCE_BLANCO_SHARE
                _st_mid = c['status_mid'] * (1.0 + _b * (c['status_mult'] / max(c['status_mid'], 1e-9) - 1.0))
                mult_mid = _st_mid * c['weather_mult'] * c['stack_penalty'] * c['pos_penalty']
                c['per_sector_final'] = {sector: val * (mult_mid if sector == 'MID' else mult)
                                         for sector, val in c['per_sector_raw'].items()}

            sector_totals = {}
            for c in contributions.values():
                for sector, val in c['per_sector_final'].items():
                    sector_totals[sector] = sector_totals.get(sector, 0.0) + val

            sector_ratings = {}
            for sector in ['LD', 'CD', 'RD', 'MID', 'LA', 'CA', 'RA']:
                raw_total = sector_totals.get(sector, 0.0)
                base_rating = (raw_total ** 1.2) * SECTOR_CONSTANTS.get(sector, 1.0)
                bucket = SECTOR_BUCKET[sector]
                morale_mult = (ts_mult * loc_mult * att_mult) if bucket == 'mid' else (tc_mult if bucket == 'att' else 1.0)
                final_raw = base_rating * morale_mult * COACH_MULT_BY_BUCKET[bucket] * TACTIC_MULT_BY_SECTOR[sector]
                sector_ratings[sector] = (final_raw / 4.0) + 1.0
                if sector == 'MID' and raw_total > 0:
                    # the WesselV1 half of midfield experience: each player's bonus, weighted by his share
                    sector_ratings[sector] += (1.0 - MID_EXPERIENCE_BLANCO_SHARE) * sum(
                        c['per_sector_final'].get('MID', 0.0) / raw_total * experience_rating_bonus('MID', c['xp'])
                        for c in contributions.values() if c['per_sector_final'].get('MID', 0.0) > 0)

            last_sector_ratings['value'] = sector_ratings
            refresh_pitch_preview()
            team_hatstats = hatstats(sector_ratings)
            sp_info = set_piece_summary(build_lineup_players()[0])
            last_sector_ratings['sp'] = sp_info
            # Remembered for the Score Predictor ("📥 Load from Lineup Simulator").
            try:
                _lr = {
                    'ratings': {k: round(float(v), 2) for k, v in sector_ratings.items()},
                    'formation': lineup_formation()[0], 'tactic': tactic_select.value,
                    'attitude': attitude_select.value, 'location': location_select.value,
                    'hatstats': round(team_hatstats, 1), **sp_info,
                }
                set_user_pref(user, 'lineup_ratings', _lr)   # in the database: also on another device
            except Exception:
                pass

            # The ratings card at the top: large numbers per sector, in pitch order
            ratings_area.clear()
            _att_short = {'PIC (Play It Cool)': 'PIC', 'Normal': 'Normal', 'MOTS (Match of the Season)': 'MOTS'}
            ratings_sub.set_text(f"{lineup_formation()[0]} · {tactic_select.value} · {_att_short.get(attitude_select.value, attitude_select.value)}"
                                 f" · {location_select.value} · TS {_ts_txt()} · TC {_tc_txt()}")

            def tile(label, value, big=False):
                with ui.column().classes('tt-tile w-full gap-0 items-center'):
                    ui.label(label).classes('text-xs text-gray-300').style('letter-spacing: 0.06em;')
                    ui.label(f'{value:.2f}').classes('text-3xl font-bold' if big else 'text-2xl font-bold')
                    with ui.element('div').classes('w-full rounded mt-1').style('height: 4px; background: #33364A; overflow: hidden;'):
                        ui.element('div').style(f'height: 100%; width: {max(0.0, min(value / 20.0, 1.0)) * 100:.0f}%; background: {_C};')
            _r = lambda k: f"{sector_ratings.get(k, 0.0):.2f}"
            _c = lambda k, lab, cls='': f'<div class="{cls}"><b>{_r(k)}</b><span>{tr(lab)}</span></div>'
            rat_box.set_content('<div class="tt-rbg">' + _c('LA', 'L att') + _c('CA', 'C att') + _c('RA', 'R att')
                                + _c('MID', 'Midfield', 'tt-rbm') + _c('LD', 'L def') + _c('CD', 'C def') + _c('RD', 'R def') + '</div>')
            rat_line.clear()
            with rat_line:
                ui.label(f"Indirect set pieces: attack {sp_info['isp']['att']:.2f} · defence {sp_info['isp']['def']:.2f} "
                         f"(taker: {sp_info['taker']}) · Special events: {sp_info['counts']['PNF']} PNF, "
                         f"{sp_info['counts']['CD']} CD, {sp_info['counts']['PDIM']} PDIM").classes('text-xs text-gray-400')
                ui.button('🎯 Open in Score Predictor', on_click=lambda: ui.navigate.to('/predictor')).props('dense no-caps outline')
            with ratings_area:
                tt_section('Attack')
                with ui.grid(columns=3).classes('w-full gap-2'):
                    tile('RIGHT', sector_ratings.get('RA', 0.0)); tile('CENTRE', sector_ratings.get('CA', 0.0)); tile('LEFT', sector_ratings.get('LA', 0.0))
                tt_section('Midfield')
                tile('MIDFIELD', sector_ratings.get('MID', 0.0), big=True)
                tt_section('Defence')
                with ui.grid(columns=3).classes('w-full gap-2'):
                    tile('RIGHT', sector_ratings.get('RD', 0.0)); tile('CENTRE', sector_ratings.get('CD', 0.0)); tile('LEFT', sector_ratings.get('LD', 0.0))
                c_ = sp_info['counts']
                with ui.row().classes('w-full items-center justify-between gap-2 mt-1 pt-2 no-wrap').style('border-top: 1px solid #3B3B4D;'):
                    ui.label(f'HatStats: {team_hatstats:.1f}  ·  Lineup: {lineup_formation()[0]}').classes('text-sm font-semibold')
                    ui.button('🎯 Open in Score Predictor', on_click=lambda: ui.navigate.to('/predictor')).props('dense no-caps') \
                        .style(f'background-color: {_C}; color: white;')
                ui.label(f"Indirect set pieces: attack {sp_info['isp']['att']:.2f} · defence {sp_info['isp']['def']:.2f} "
                         f"(taker: {sp_info['taker']})  ·  Special events: {c_['PNF']} PNF, {c_['CD']} CD, {c_['PDIM']} PDIM"
                         ).classes('text-xs text-gray-400')

            with results_area:

                ui.label(f"Coach: {coach_select.value} | Tactic: {tactic_select.value} (Skill {tskill_input.value}) | "
                         f"Location: {location_select.value} | Attitude: {attitude_select.value} | "
                         f"TS: {_ts_txt()} | ZV: {_tc_txt()} | Weather: {weather_select.value}").classes('text-sm text-gray-400 mt-2')

                _head = (f"{lineup_formation()[0]} · {tactic_select.value} · {attitude_select.value} · "
                         f"{location_select.value} · TS {_ts_txt()} · TC {_tc_txt()}")
                _mk = lineup_markup(lineup_players, sector_ratings, sp_info, _head)
                markup_block(_mk, 'Lineup', title=f'📋 Lineup for the HT forum ({len(_mk)} / {HT_POST_LIMIT} characters)')

                ui.label('🔍 Player Contribution Breakdown').classes('text-lg font-semibold mt-4')
                breakdown_rows = []
                for slot_id, c in sorted(contributions.items(), key=lambda kv: kv[0]):
                    sectors_str = ', '.join(f"{sec} {val:.1f}" for sec, val in sorted(c['per_sector_final'].items(), key=lambda kv2: -kv2[1]))
                    breakdown_rows.append({
                        'Slot': slot_id, 'Player': c['player'], 'Role': c['role'], 'Specialty': c['specialty'],
                        'Status Mult': round(c['status_mult'], 3), 'Weather Mult': round(c['weather_mult'], 3),
                        'Crowding': round(c['pos_penalty'], 3), 'Sector Contributions': sectors_str,
                    })
                cols = ['Slot', 'Player', 'Role', 'Specialty', 'Status Mult', 'Weather Mult', 'Crowding', 'Sector Contributions']
                ui.table(columns=[{'name': c, 'label': c, 'field': c} for c in cols], rows=breakdown_rows).classes('w-full').props('dense flat')

        # ── Named lineups: save the whole lineup (players, roles, match settings, ratings) under a
        # name, load it back here, or load its ratings in the Score Predictor. The roster is not touched.
        CONTEXT_FIELDS = {'coach': coach_select, 'ts': ts_input, 'weather': weather_select, 'tactic': tactic_select,
                          'tc': tc_input, 'tskill': tskill_input, 'location': location_select, 'attitude': attitude_select}
        for _c in CONTEXT_FIELDS.values():
            _c.on_value_change(live_recalc)
        tactic_select.on_value_change(lambda _: render_side())
        render_side()
        taker_select.on_value_change(live_recalc)

        def save_lineup():
            name = (lineup_name_input.value or '').strip()
            if not name:
                ui.notify('⚠️ Give the lineup a name first.', type='warning')
                return
            lineup_players, _ = build_lineup_players()
            if not lineup_players:
                ui.notify('⚠️ No players on the pitch to save.', type='warning')
                return
            calculate()   # store ratings that belong to exactly this lineup and these settings
            ratings = last_sector_ratings['value'] or {}
            data = {
                'slots': {sid: {'player': w['player'].value, 'role': w['role'].value}
                          for sid, w in slot_widgets.items() if w.get('role') is not None and w['player'].value not in (None, '-- Empty --')},
                'subs': [slot_widgets[f'SUB{i}']['player'].value for i in range(1, 6)],
                'formation': lineup_formation()[0], 'context': {k: c.value for k, c in CONTEXT_FIELDS.items()},
                'ratings': {k: round(float(v), 2) for k, v in ratings.items()},
                'hatstats': round(hatstats(ratings), 1) if ratings else 0.0,
                'taker_choice': taker_select.value, **(last_sector_ratings.get('sp') or {}),
            }
            try:
                save_named_lineup(user, name, data)
                refresh_saved_list(select=name)
                ui.notify(f'💾 Lineup "{name}" saved ({data["formation"]}, HatStats {data["hatstats"]:.0f}).', type='positive')
            except Exception as e:
                ui.notify(f'Error saving lineup: {e}', type='negative')

        def load_lineup():
            name = saved_select.value
            data = get_saved_lineups(user).get(name)
            if not data:
                ui.notify('⚠️ Choose a saved lineup first.', type='warning')
                return
            filter_select.set_value(ALL_PLAYERS)
            abroad_cb.set_value(False)
            for k, c in CONTEXT_FIELDS.items():
                if k in data.get('context', {}):
                    v = data['context'][k]
                    if k == 'location' and v == 'Away':      # saved before 'Away / neutral'
                        v = 'Away / neutral'
                    c.set_value(v)
            for sid, w in slot_widgets.items():
                if w.get('role') is not None:
                    w['player'].set_value('-- Empty --')
            missing = []
            for sid, d in data.get('slots', {}).items():
                if sid in slot_widgets and d.get('player') in player_option_map:
                    slot_widgets[sid]['player'].set_value(d['player'])
                    slot_widgets[sid]['role'].set_value(d['role'])
                else:
                    missing.append(d.get('player'))
            for i, p in enumerate(data.get('subs', [])[:5], start=1):
                slot_widgets[f'SUB{i}']['player'].set_value(p if p in player_option_map else '-- Empty --')
            lineup_name_input.set_value(name)
            refresh_taker_options()
            if data.get('taker_choice') in (taker_select.options or []):
                taker_select.set_value(data['taker_choice'])
            calculate()
            ui.notify(f'📂 Lineup "{name}" loaded.' + (f' Not in your roster anymore: {", ".join(map(str, missing))}.' if missing else ''),
                      type='positive' if not missing else 'warning')

        def delete_lineup():
            name = saved_select.value
            if not name:
                return
            delete_saved_lineup(user, name)
            refresh_saved_list()
            ui.notify(f'🗑️ Lineup "{name}" deleted.', type='positive')

        def refresh_saved_list(select=None):
            names = list(get_saved_lineups(user).keys())
            saved_select.set_options(names, value=(select if select in names else (names[0] if names else None)))

        with ui.row().classes('gap-3 mt-4 items-center flex-wrap w-full'):
            ui.button('📊 Recalculate', on_click=calculate).props('no-caps') \
                .style(f'background-color: {_C}; color: white; font-weight: 600;')
            lineup_name_input = ui.input('Lineup name', placeholder='NL U21 vs Romania, 4-4-2').classes('w-64')
            ui.button('💾 Save lineup', on_click=save_lineup).props('outline')
            saved_select = ui.select([], label='Saved lineups').classes('w-64')
            ui.button('📂 Load', on_click=load_lineup).props('outline')
            ui.button(icon='delete', on_click=delete_lineup).props('flat round dense color=grey').tooltip('Delete saved lineup')
        refresh_saved_list()

        warning_area
        results_area