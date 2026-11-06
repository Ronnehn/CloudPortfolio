import pandas as pd
from nicegui import ui, app
from shell import apply_theme, require_login, render_sidebar, ACCENT, ACCENT_DARK, ht_row, markup_block, tt_card, tt_section, page_title
from data_layer import get_saved_lineups, save_prediction, get_saved_predictions, delete_saved_prediction, get_user_pref, set_user_pref
from ht_engine import (
    hatstats,
    get_tactic_mults, calculate_expected_score, poisson_win_draw_loss, COUNTER_SOURCES,
    counter_pct_from_level, attitude_factor, aim_aow_redirect, long_shot_goal_prob, ATTITUDE_MULTIPLIERS, COUNTRY_LIST, get_flag,
)

SECTORS = ['MID', 'RD', 'CD', 'LD', 'RA', 'CA', 'LA']
SECTOR_NAMES = {'MID': 'Midfield', 'RD': 'Right Defense', 'CD': 'Central Defense', 'LD': 'Left Defense',
                'RA': 'Right Attack', 'CA': 'Central Attack', 'LA': 'Left Attack'}
_RATING_WORDS = ['non-existent', 'disastrous', 'wretched', 'poor', 'weak', 'inadequate', 'passable', 'solid',
                 'excellent', 'formidable', 'outstanding', 'brilliant', 'magnificent', 'world class', 'supernatural',
                 'titanic', 'extra-terrestrial', 'mythical', 'magical', 'utopian', 'divine']
_SUBLEVELS = ['very low', 'low', 'high', 'very high']


def rating_text(v):
    """Hattrick rating as words: 9.36 -> 'formidable low' (.00-.24 very low, .25 low, .50 high, .75 very high)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return ''
    lvl = max(0, min(int(v), len(_RATING_WORDS) - 1))
    sub = max(0, min(int((v - int(v)) * 4 + 1e-9), 3))
    return f'{_RATING_WORDS[lvl]} {_SUBLEVELS[sub]}'
SECTOR_LABELS = {'MID': 'Midfield', 'RD': 'Right def', 'CD': 'Central def', 'LD': 'Left def',
                 'RA': 'Right att', 'CA': 'Central att', 'LA': 'Left att'}
TACTICS = ['Normal', 'AIM', 'AOW', 'Counter', 'Creative', 'Long Shots']
AS_ENTERED = 'As entered'
# This match's attitude: 'As entered' (no conversion), then from the lowest (PIC) up.
ATTITUDES = [AS_ENTERED, 'PIC (Play It Cool)', 'Normal', 'MOTS (Match of the Season)']
ATT_SHORT = {AS_ENTERED: AS_ENTERED, 'PIC (Play It Cool)': 'PIC', 'Normal': 'Normal', 'MOTS (Match of the Season)': 'MOTS'}
# Compact buttons for attitude and venue on the team cards (value -> label)
ATT_TOGGLE = {AS_ENTERED: 'As entered', 'PIC (Play It Cool)': 'PIC', 'Normal': 'Normal', 'MOTS (Match of the Season)': 'MOTS'}
VENUE_TOGGLE = {'Away / neutral': 'Away', 'Home': 'Home', 'Derby': 'Derby'}
# Team card colours: our own steel blue, and a muted copper for the opponent (both readable on dark)
TEAM_COLORS = {'us': (ACCENT, ACCENT_DARK), 'opp': ('#A86A4A', '#4A2A1C')}
ATT_LONG = {v: k for k, v in ATT_SHORT.items()}
# Midfield venue bonus (same values as the lineup page). Away and neutral ground: no bonus.
VENUES = {'Home': 1.19892, 'Away / neutral': 1.0, 'Derby': 1.11493}   # Unwritten Manual; derby = away team only
CODE_OVERRIDES = {'England': 'ENG', 'Scotland': 'SCO', 'Wales': 'WAL', 'Northern Ireland': 'NIR'}


def country_code(name):
    """Short code for a country: from its flag's letters (🇳🇱 -> NL), else first 3 letters."""
    if not name:
        return '?'
    if name in CODE_OVERRIDES:
        return CODE_OVERRIDES[name]
    flag = get_flag(name) or ''
    letters = ''.join(chr(ord(ch) - 0x1F1E6 + 65) for ch in flag if 0x1F1E6 <= ord(ch) <= 0x1F1FF)
    if len(letters) == 2:
        return letters
    if len(flag) == 2 and flag.isalpha():
        return flag.upper()
    return name[:3].upper()


FORMATIONS = ['5-5-0', '5-4-1', '5-3-2', '5-2-3', '4-5-1', '4-4-2', '4-3-3', '3-5-2', '3-4-3', '2-5-3']

# Example: NL 4-4-2, PIC, Counter, 100% DEF coach (HT ratings for that exact setup).
MY_DEFAULT = {'MID': 7.82, 'RD': 15.85, 'CD': 17.53, 'LD': 16.11, 'RA': 9.56, 'CA': 9.61, 'LA': 10.74}
OPP_DEFAULT = {'MID': 13.0, 'RD': 9.25, 'CD': 13.5, 'LD': 9.75, 'RA': 12.25, 'CA': 17.0, 'LA': 12.5}
# Set-piece defaults from the BLANCO Score Predictor sheet.
SP_DEFAULT = {'ISPOFF': 9.0, 'ISPDEF': 12.0, 'DIRSP': 0.25}



class _Hidden:
    """A remembered value without a field on the page (where the ratings come from: normal
    attitude, away/neutral, unless a loaded lineup says otherwise)."""
    def __init__(self, value):
        self.value = value
        self._cbs = []

    def set_value(self, v):
        self.value = v
        for cb in self._cbs:
            cb(None)

    def on_value_change(self, cb):
        self._cbs.append(cb)
        return self

def mid_factor(seen_as, play_as, seen_venue, play_venue):
    """Midfield conversion from the match the ratings came from to this match:
    attitude (MOTS/Normal/PIC) and venue (home/derby/away) both only affect midfield."""
    att = 1.0 if play_as == AS_ENTERED else attitude_factor(seen_as, play_as)
    return att * VENUES.get(play_venue, 1.0) / VENUES.get(seen_venue, 1.0)


def eff_mid_settings(box):
    """(seen attitude, play attitude, seen venue, play venue) actually used. With 'use ratings
    as entered' on, 'seen' = 'play', so midfield is not converted at all."""
    if box.get('as_entered') is not None and box['as_entered'].value:
        return box['play'].value, box['play'].value, box['venue'].value, box['venue'].value
    return box['seen'].value, box['play'].value, box['seen_v'].value, box['venue'].value


def build_team(ratings, tactic, seen_as, play_as, apply_tactic, sp,
               seen_venue='Away / neutral', play_venue='Away / neutral'):
    """Ratings -> engine team dict. Midfield is converted from the attitude/venue the
    ratings were seen with to this match's; tactic rating effects are only applied
    when the entered ratings don't already include them."""
    m = get_tactic_mults(tactic) if apply_tactic else (1.0,) * 7
    team = {sec: float(ratings[sec] or 0) * m[i] for i, sec in enumerate(SECTORS)}
    team['MID'] *= mid_factor(seen_as, play_as, seen_venue, play_venue)
    team.update({'DIRSP': float(sp['DIRSP'] or 0), 'ISPOFF': float(sp['ISPOFF'] or 0),
                 'ISPDEF': float(sp['ISPDEF'] or 0),
                 # special events (Pernaug): powerful forwards, central defenders, powerful DIMs
                 'N_PNF': int(sp.get('N_PNF') or 0), 'N_CD': int(sp.get('N_CD') or 0),
                 'N_PDIM': int(sp.get('N_PDIM') or 0)})
    return team


LEVEL_TACTICS = ('Counter', 'AIM', 'AOW', 'Long Shots')   # tactics whose level changes the prediction
LS_DEFAULT = {'ls_sc': 12.0, 'ls_sp': 10.0}      # average long-shot shooter
GK_DEFAULT = {'gk': 17.0, 'gk_sp': 12.0}         # keeper facing long shots


def tactic_flags(tactic, level, shooter=None, keeper=None, source='nick', match_rating=None):
    """shooter = (scoring, set pieces) of this team's long-shot takers,
    keeper = (keeping, set pieces) of the opposing goalkeeper — only used for Long Shots."""
    flags = {'AIM': 1 if tactic == 'AIM' else 0, 'AOW': 1 if tactic == 'AOW' else 0, 'PRESS': 0,
             'CAPCT': counter_pct_from_level(level, source, match_rating) if tactic == 'Counter' else 0.0,
             'REDIR': aim_aow_redirect(level) if tactic in ('AIM', 'AOW') else None}
    if tactic == 'Long Shots' and shooter and keeper:
        # Same level curve as AIM/AOW: share of centre/wing chances that become a long shot.
        flags['LS_CONV'] = aim_aow_redirect(level)
        flags['LS_GOAL'] = long_shot_goal_prob(shooter[0] or 0, shooter[1] or 0, keeper[0] or 0, keeper[1] or 0)
    return flags


def match_avg(a, b):
    """Average rating of a match: both teams' 7 ratings together (for the counter share)."""
    vals = [float(v or 0) for v in list(a) + list(b)]
    return sum(vals) / len(vals) if vals else None


def predict(us, us_flags, opp, opp_flags):
    res = calculate_expected_score(us, opp, us_flags, opp_flags)
    w, d, l = poisson_win_draw_loss(res['goals_nl'], res['goals_o'])
    return res, w, d, l


def delta_color(delta):
    if abs(delta) < 0.005:
        return '#C084FC'
    return '#34D399' if delta > 0 else '#F87171'


@ui.page('/predictor')
def predictor_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    render_sidebar(user, '/predictor')

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_title('/predictor')
        ui.add_css(''.join(
            f'.tt-{sd}.q-btn-group {{ border: 1px solid {c}; border-radius: 8px; overflow: hidden; }}'
            f'.tt-{sd} .q-btn {{ color: #B8BCC8; background: #1F2029; padding: 2px 10px; }}'
            f'.tt-{sd} .q-btn.bg-tt{sd} {{ background: {c} !important; color: #FFFFFF !important; font-weight: 600; }}'
            for sd, (c, _) in TEAM_COLORS.items()))
        # Save / load bar: filled in at the end, once both teams and the formation mix exist.
        with tt_card('📁 Lineups & saved predictions') as save_bar:
            pass

        # ── Shared settings ──────────────────────────────────────────────────
        with tt_card('⚙️ Calculation settings'):
            with ui.grid(columns=2).classes('w-full gap-6 grid-cols-1 md:grid-cols-2'):
                with ui.column().classes('w-full gap-1'):
                    tt_section('Ratings')
                    apply_tac = ui.switch('Apply the tactic penalty (only for ratings without the tactic)', value=False)
                    used_summary = ui.label('').classes('text-sm font-semibold').style(f'color: {ACCENT};')
                with ui.column().classes('w-full gap-1'):
                    tt_section('Counter data')
                    counter_src = ui.toggle(COUNTER_SOURCES, value='nick') \
                        .props('dense no-caps unelevated toggle-color=ttus toggle-text-color=white') \
                        .classes('tt-toggle tt-us').mark('counter-source') \
                        .tooltip('nickarana\'s live data. CA-Original: one value per tactic level. '
                                 'CA-Nick: tactic level × match rating (levels 16-20), slightly lower for high-rated matches')
        teams = {}

        def refresh_summary():
            # One line next to the switch with what each team's ratings become in the calculation.
            if len(teams) < 2:
                return
            used_summary.set_text('Ratings used — ' + '  ·  '.join(
                f"{(b['code'].value or '').strip() or '?'}: {b['used_txt']}" for b in teams.values()))

        LAST_CALC = '(last calculated lineup)'

        def lineup_choices():
            try:
                return [LAST_CALC] + list(get_saved_lineups(user).keys())
            except Exception:
                return [LAST_CALC]

        # ── Team inputs ──────────────────────────────────────────────────────
        def team_inputs(title, defaults, tactic_default, formation_default, country_default, side='us'):
            box = {'r': {}, 'sp': {}}
            col, col_dark = TEAM_COLORS[side]

            def section(name):
                ui.label(name).classes('text-xs font-bold uppercase mt-1').style(f'color: {col}; letter-spacing: 0.12em;')

            def rating(sec, label):
                box['r'][sec] = ui.number(label, value=defaults[sec], min=0.0, max=30.0, step=0.01, format='%.2f') \
                    .props('dense').classes('w-full').mark(f'{side}-{sec}')

            with ui.card().classes('w-full p-0 gap-0 overflow-hidden').style(f'border: 1px solid {col} !important;'):
                # Header strip in the team colour: who plays, and in which lineup
                with ui.element('div').classes('w-full px-4 pt-3 pb-2').style(
                        f'background: linear-gradient(120deg, {col_dark} 0%, {col} 100%);'):
                    ui.label(title).classes('tt-ctitle')
                    with ui.row().classes('w-full gap-2 no-wrap items-end'):
                        box['country'] = ui.select(COUNTRY_LIST, value=country_default, label='Country',
                                                   with_input=True).props('dense').classes('flex-grow min-w-0')
                        box['code'] = ui.input('Short name', value=country_code(country_default)).props('dense').classes('w-28')
                        box['form'] = ui.select(FORMATIONS, value=formation_default, label='Lineup',
                                                new_value_mode='add-unique').props('dense').classes('w-28')
                box['country'].on_value_change(lambda e: box['code'].set_value(country_code(e.value)))

                with ui.column().classes('w-full px-4 pt-2 pb-3 gap-2'):
                    section('Defence')
                    with ui.grid(columns=3).classes('w-full gap-2'):
                        rating('RD', 'Right'); rating('CD', 'Centre'); rating('LD', 'Left')

                    section('Midfield')
                    rating('MID', 'Midfield')
                    # The ratings are the base (as entered = PIC, away/neutral); a loaded lineup remembers
                    # the attitude/venue it was calculated with, so nothing is counted twice.
                    box['seen'] = _Hidden('PIC (Play It Cool)')
                    box['seen_v'] = _Hidden('Away / neutral')
                    with ui.row().classes('w-full items-center gap-2 flex-wrap'):
                        box['play'] = ui.toggle(ATT_TOGGLE, value='PIC (Play It Cool)') \
                            .props(f'dense no-caps unelevated toggle-color=tt{side} toggle-text-color=white') \
                            .classes(f'tt-toggle tt-{side}').mark(f'{side}-attitude')
                        box['venue'] = ui.toggle(VENUE_TOGGLE, value='Away / neutral') \
                            .props(f'dense no-caps unelevated toggle-color=tt{side} toggle-text-color=white') \
                            .classes(f'tt-toggle tt-{side}').mark(f'{side}-venue')

                    section('Attack')
                    with ui.grid(columns=3).classes('w-full gap-2'):
                        rating('RA', 'Right'); rating('CA', 'Centre'); rating('LA', 'Left')

                    section('Tactic')
                    with ui.row().classes('w-full gap-2 no-wrap items-end'):
                        box['tac1'] = ui.select(TACTICS, value=tactic_default, label='Tactic').props('dense').classes('flex-grow min-w-0')
                        # Counter: share of counters. AIM/AOW: share of attacks moved to the centre / wings.
                        box['ca'] = ui.number('Tactic level', value=13, min=1, max=25, step=1).props('dense').classes('w-28')
                    box['ca'].bind_visibility_from(box['tac1'], 'value', backward=lambda v: v in LEVEL_TACTICS)
                    box['ca_info'] = ui.label('').classes('text-xs text-gray-400 -mt-1')
                    box['ca_info'].bind_visibility_from(box['tac1'], 'value', backward=lambda v: v == 'Counter')

                    def upd_ca_info(_=None):
                        mr = match_avg(*[[t['r'][x].value for x in SECTORS] for t in teams.values()]) if len(teams) == 2 else None
                        pct = counter_pct_from_level(box['ca'].value, counter_src.value, mr)
                        extra = f', match rating {mr:.1f}' if (mr and counter_src.value == 'nick') else ''
                        box['ca_info'].set_text(f"≈ {pct * 100:.1f}% of the opponent's missed chances become counters "
                                                f"({COUNTER_SOURCES[counter_src.value]}{extra})")
                    box['upd_ca_info'] = upd_ca_info
                    for _w in (box['ca'], box['tac1'], counter_src):
                        _w.on_value_change(upd_ca_info)
                    upd_ca_info()
                    with ui.grid(columns=2).classes('w-full gap-2') as ls_grid:
                        box['ls_sc'] = ui.number('Long-shot takers: avg scoring', value=LS_DEFAULT['ls_sc'], min=1, max=25, step=0.1).props('dense')
                        box['ls_sp'] = ui.number('Long-shot takers: avg set pieces', value=LS_DEFAULT['ls_sp'], min=1, max=25, step=0.1).props('dense')
                    ls_grid.bind_visibility_from(box['tac1'], 'value', backward=lambda v: v == 'Long Shots')

                    with ui.expansion('Set pieces · PNF · CD · PDIM · keeper', icon='sports_soccer', value=False) \
                            .classes('w-full').props('dense'):
                        with ui.grid(columns=3).classes('w-full gap-2'):
                            box['sp']['ISPOFF'] = ui.number('Indirect SP attack', value=SP_DEFAULT['ISPOFF'], step=0.25).props('dense')
                            box['sp']['ISPDEF'] = ui.number('Indirect SP defence', value=SP_DEFAULT['ISPDEF'], step=0.25).props('dense')
                            box['sp']['DIRSP'] = ui.number('Direct SP factor', value=SP_DEFAULT['DIRSP'], step=0.05).props('dense')
                        with ui.grid(columns=3).classes('w-full gap-2'):
                            box['sp']['N_PNF'] = ui.number('PNF', value=0, min=0, max=3, step=1, format='%d').props('dense')
                            box['sp']['N_CD'] = ui.number('CD', value=0, min=0, max=3, step=1, format='%d').props('dense')
                            box['sp']['N_PDIM'] = ui.number('PDIM', value=0, min=0, max=3, step=1, format='%d').props('dense')
                        with ui.grid(columns=2).classes('w-full gap-2'):
                            box['gk'] = ui.number('Keeper: keeping', value=GK_DEFAULT['gk'], min=1, max=25, step=0.1).props('dense')
                            box['gk_sp'] = ui.number('Keeper: set pieces', value=GK_DEFAULT['gk_sp'], min=1, max=25, step=0.1).props('dense')
                        ui.label('Filled in automatically when you load a lineup. The keeper only matters against Long Shots.') \
                            .classes('text-xs text-gray-400')

                    # Footer: what the calculation uses
                    with ui.row().classes('w-full items-center justify-between gap-2 mt-1 pt-2').style('border-top: 1px solid #3B3B4D;'):
                        box['mid_used'] = ui.label('').classes('text-xs font-semibold').style(f'color: {col};')
                        box['hatstats'] = ui.label('').classes('text-xs text-gray-400')

            def load_from_lineup(choice=None):
                choice = choice or LAST_CALC
                if choice == LAST_CALC:
                    data = get_user_pref(user, 'lineup_ratings')
                else:
                    saved = get_saved_lineups(user).get(choice) or {}
                    ctx = saved.get('context', {})
                    data = {'ratings': saved.get('ratings', {}), 'formation': saved.get('formation'),
                            'tactic': ctx.get('tactic'), 'attitude': ctx.get('attitude'),
                            'location': ctx.get('location'), 'hatstats': saved.get('hatstats', 0)} if saved else None
                if data and choice != LAST_CALC:
                    data.update({k: saved.get(k) for k in ('isp', 'keeper', 'counts', 'taker') if saved.get(k) is not None})
                if not data or not data.get('ratings'):
                    ui.notify('No ratings for that lineup: calculate or save one in the Lineup Simulator first.', type='warning')
                    return
                for sec in SECTORS:
                    if sec in data['ratings']:
                        box['r'][sec].set_value(data['ratings'][sec])
                if data.get('formation'):
                    box['form'].set_value(data['formation'])
                if data.get('tactic') in TACTICS:
                    box['tac1'].set_value(data['tactic'])
                # The lineup ratings already include its attitude and venue: tell the predictor.
                if data.get('attitude') in ATTITUDES:
                    box['seen'].set_value(data['attitude'])
                    box['play'].set_value(data['attitude'])
                # Set pieces, keeper and special events of the lineup
                if data.get('isp'):
                    box['sp']['ISPOFF'].set_value(data['isp'].get('att'))
                    box['sp']['ISPDEF'].set_value(data['isp'].get('def'))
                if data.get('keeper'):
                    box['gk'].set_value(data['keeper'].get('gk'))
                    box['gk_sp'].set_value(data['keeper'].get('sh'))
                if data.get('counts'):
                    for k in ('PNF', 'CD', 'PDIM'):
                        box['sp'][f'N_{k}'].set_value(int(data['counts'].get(k, 0)))
                venue = {'Home': 'Home', 'Derby': 'Derby', 'Away': 'Away / neutral', 'Away / neutral': 'Away / neutral'}.get(data.get('location'))
                if venue:
                    box['seen_v'].set_value(venue)
                    box['venue'].set_value(venue)
                ui.notify(f"📥 Loaded {data.get('formation', '')} lineup ratings (HatStats {data.get('hatstats', 0):.0f}). "
                          'They already include the tactic penalty.',
                          type='positive')
            box['load_lineup'] = load_from_lineup        # used by the bar at the top

            def upd_mid(_=None):
                # Everything that changes the entered ratings: attitude/venue (midfield) and,
                # with the switch on, the tactic penalty (e.g. Counter MID ×0.93, AIM RD/LD ×0.86).
                tm = get_tactic_mults(box['tac1'].value) if apply_tac.value else (1.0,) * 7
                mf = mid_factor(*eff_mid_settings(box))
                parts = []
                for i, sec in enumerate(SECTORS):
                    f = tm[i] * (mf if sec == 'MID' else 1.0)
                    if abs(f - 1) > 1e-9:
                        parts.append(f"{sec} {float(box['r'][sec].value or 0) * f:.2f} (×{f:.3f})")
                box['used_txt'] = ', '.join(parts) if parts else 'as entered'
                box['mid_used'].set_text('Used in calculation: ' + box['used_txt'])
                box['hatstats'].set_text(f"HatStats (as entered): {hatstats({s: float(box['r'][s].value or 0) for s in SECTORS}):.1f}")
                refresh_summary()
            for k in ('seen', 'play', 'seen_v', 'venue', 'tac1'):
                box[k].on_value_change(upd_mid)
            for sec in SECTORS:
                box['r'][sec].on_value_change(upd_mid)
            apply_tac.on_value_change(upd_mid)
            upd_mid()
            return box

        with ui.column().classes('w-full gap-3 mb-4'):
            with ui.grid(columns=2).classes('w-full gap-4 grid-cols-1 md:grid-cols-2'):
                with ui.column().classes('w-full min-w-0'):
                    my = team_inputs('Your team', MY_DEFAULT, 'Counter', '4-4-2',
                                     'Netherlands' if 'Netherlands' in COUNTRY_LIST else COUNTRY_LIST[0], side='us')
                with ui.column().classes('w-full min-w-0'):
                    opp = team_inputs('Opponent', OPP_DEFAULT, 'Normal', '3-5-2',
                                      'Czech Republic' if 'Czech Republic' in COUNTRY_LIST else COUNTRY_LIST[0], side='opp')
            teams.update(my=my, opp=opp)
            for _b in (my, opp):
                for _sec in SECTORS:
                    _b['r'][_sec].on_value_change(lambda e: [t['upd_ca_info']() for t in teams.values()])
                _b['upd_ca_info']()
            for b in (my, opp):
                b['code'].on_value_change(lambda e: refresh_summary())
            refresh_summary()

            # Only one team can be at home: home -> the other is away, derby -> both derby.
            def sync_venue(other):
                def handler(e):
                    if e.value == 'Home' and other['venue'].value == 'Home':
                        other['venue'].set_value('Away / neutral')
                    elif e.value == 'Derby':
                        other['venue'].set_value('Derby')
                    elif e.value != 'Derby' and other['venue'].value == 'Derby':
                        other['venue'].set_value('Away / neutral')
                return handler
            my['venue'].on_value_change(sync_venue(opp))
            opp['venue'].on_value_change(sync_venue(my))

            sim_results = ui.column().classes('w-full mt-4')

            def both_avg():
                return match_avg([my['r'][x].value for x in SECTORS], [opp['r'][x].value for x in SECTORS])

            def opp_team():
                return (build_team({s: opp['r'][s].value for s in SECTORS}, opp['tac1'].value, eff_mid_settings(opp)[0],
                                   eff_mid_settings(opp)[1], apply_tac.value, {k: v.value for k, v in opp['sp'].items()},
                                   eff_mid_settings(opp)[2], eff_mid_settings(opp)[3]),
                        tactic_flags(opp['tac1'].value, opp['ca'].value, (opp['ls_sc'].value, opp['ls_sp'].value),
                                     (my['gk'].value, my['gk_sp'].value), counter_src.value, both_avg()))

            def my_team(tactic):
                return (build_team({s: my['r'][s].value for s in SECTORS}, tactic, eff_mid_settings(my)[0],
                                   eff_mid_settings(my)[1], apply_tac.value, {k: v.value for k, v in my['sp'].items()},
                                   eff_mid_settings(my)[2], eff_mid_settings(my)[3]),
                        tactic_flags(tactic, my['ca'].value, (my['ls_sc'].value, my['ls_sp'].value),
                                     (opp['gk'].value, opp['gk_sp'].value), counter_src.value, both_avg()))

            def cc(box):
                return (box['code'].value or '').strip() or country_code(box['country'].value)

            def describe(box):
                venue = {'Home': ', home', 'Derby': ', derby'}.get(box['venue'].value, '')
                return f"{cc(box)} {box['form'].value or '?'} ({box['tac1'].value}, {ATT_SHORT[box['play'].value]}{venue})"

            def run_sim():
                sim_results.clear()
                o_team, o_flags = opp_team()
                with sim_results:
                    with ui.grid(columns=2).classes('w-full gap-4 grid-cols-1 md:grid-cols-2'):
                        for tac in [my['tac1'].value]:
                            m_team, m_flags = my_team(tac)
                            res, w, d, l = predict(m_team, m_flags, o_team, o_flags)
                            delta = res['goals_nl'] - res['goals_o']
                            with ui.card().classes('p-4'):
                                ui.label(f'{describe(my)}  vs  {describe(opp)}').classes('font-bold text-lg mb-1')
                                us_c, op_c = cc(my), cc(opp)
                                ui.label(f"{us_c} goals: {res['goals_nl']:.2f}").classes('text-cyan-400 font-semibold')
                                ui.label(f"{op_c} goals: {res['goals_o']:.2f}").classes('text-rose-400 font-semibold')
                                ui.label(f'Δ {delta:+.2f}').classes('font-bold').style(f'color: {delta_color(delta)};')
                                ui.label(f'{us_c} win {w*100:.1f}% · Draw {d*100:.1f}% · {op_c} win {l*100:.1f}%').classes('text-sm mt-1')
                                ui.label(f"Possession {us_c}: {res['possession_nl']*100:.1f}%").classes('text-gray-400 text-sm')
                                # the Boxplot (BETA) page shows the goal spread of this match
                                try:
                                    set_user_pref(user, 'boxplot_match', {
                                        'us': m_team, 'us_flags': m_flags, 'opp': o_team, 'opp_flags': o_flags,
                                        'us_name': my['country'].value or us_c, 'opp_name': opp['country'].value or op_c,
                                        'desc': f'{describe(my)}  vs  {describe(opp)}'})
                                except Exception:
                                    pass
                                ui.button('📦 Boxplot (BETA)', on_click=lambda: ui.navigate.to('/boxplot')) \
                                    .props('dense outline no-caps').classes('mt-2') \
                                    .tooltip('How often each number of goals happens in this match')

                    # Ratings actually used (after attitude / venue / tactic adjustments)
                    def used_cells(box, team):
                        cells, notes = [], []
                        for sec in SECTORS:
                            entered, used = float(box['r'][sec].value or 0), team[sec]
                            if abs(used - entered) > 0.005:
                                cells.append(f'{used:.2f}*')
                                notes.append(f'{sec} {entered:.2f} → {used:.2f} (×{used / entered:.3f})' if entered else sec)
                            else:
                                cells.append(f'{used:.2f}')
                        return cells, notes
                    my_cells, my_notes = used_cells(my, m_team)
                    op_cells, op_notes = used_cells(opp, o_team)
                    with ui.card().classes('w-full p-4 mt-2'):
                        ui.label('Ratings used in this prediction').classes('text-sm font-semibold mb-1')
                        rows = [dict(Team=f'{us_c} {my["form"].value or ""}', **dict(zip(SECTORS, my_cells))),
                                dict(Team=f'{op_c} {opp["form"].value or ""}', **dict(zip(SECTORS, op_cells)))]
                        ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in ['Team'] + SECTORS],
                                 rows=rows).classes('w-full').props('dense flat')
                        notes = [f'{us_c}: ' + ', '.join(my_notes)] if my_notes else []
                        notes += [f'{op_c}: ' + ', '.join(op_notes)] if op_notes else []
                        ui.label(('* adjusted from what you entered — ' + ' | '.join(notes)) if notes
                                 else 'No adjustments — the ratings are used exactly as entered.'
                                 ).classes('text-xs text-gray-400 mt-1')

                    lines = [
                        f'[b]Score prediction: {describe(my)} vs {describe(opp)}[/b]',
                        '[table]',
                        ht_row([''] + SECTORS, header=True),
                        ht_row([f'[b]{us_c}[/b] {my["form"].value or ""}'] + my_cells),
                        ht_row([f'[b]{op_c}[/b] {opp["form"].value or ""}'] + op_cells),
                        '[/table]',
                    ] + ([f'[i]* adjusted: ' + ' | '.join(notes) + '[/i]'] if notes else []) + [
                        '[table]',
                        ht_row([us_c, op_c, 'Δ', f'{us_c} win', 'Draw', f'{op_c} win', f'Possession {us_c}'], header=True),
                        ht_row([f"{res['goals_nl']:.2f}", f"{res['goals_o']:.2f}", f'[b]{delta:+.2f}[/b]',
                                f'{w*100:.1f}%', f'{d*100:.1f}%', f'{l*100:.1f}%', f"{res['possession_nl']*100:.1f}%"]),
                        '[/table]',
                    ]
                    markup_block('\n'.join(lines), 'Prediction')

            with ui.row().classes('items-center gap-3 mt-4'):
                ui.button('🚀 Run prediction', on_click=run_sim, color=None).classes('tt-goldbtn')

                def _test_box():
                    import page_boxplot
                    page_boxplot.store_test_match(user)
                    ui.navigate.to('/boxplot')
                ui.button('🧪 Boxplot test match', on_click=_test_box).props('outline no-caps') \
                    .tooltip('Opens the Boxplot page with a made-up close match (Team A vs Team B), just to try it out')

        # ── Weighted lineup mix ──────────────────────────────────────────────
        with ui.card().classes('w-full p-4'):
            ui.label("📊 Opponent's possible lineups vs your team").classes('text-md font-semibold mb-1')
            ui.label('Weight = how likely the lineup is (e.g. 50 / 40 / 10); W.AVG = expected outcome over all of them.'
                     ).classes('text-xs text-gray-400 mb-2')

            mix_rows = [
                {'w': 50, 'name': '2-5-3', **OPP_DEFAULT, 'tac': 'Normal', 'seen': 'PIC', 'seen_v': 'Away / neutral', 'play': 'PIC', 'ca': 13},
                {'w': 40, 'name': '3-4-3', **OPP_DEFAULT, 'tac': 'Normal', 'seen': 'PIC', 'seen_v': 'Away / neutral', 'play': 'PIC', 'ca': 13},
                {'w': 10, 'name': '3-5-2', **OPP_DEFAULT, 'tac': 'Normal', 'seen': 'PIC', 'seen_v': 'Away / neutral', 'play': 'PIC', 'ca': 13},
            ]

            def bind(row, key, cast=None, after=None):
                def handler(e):
                    row[key] = cast(e.value) if (cast and e.value is not None) else e.value
                    if after:
                        after()
                return handler

            def row_mid_text(row):
                tm = get_tactic_mults(row['tac']) if apply_tac.value else (1.0,) * 7
                mf = mid_factor(ATT_LONG[row['seen']], ATT_LONG[row['play']], row.get('seen_v', 'Away / neutral'),
                                opp['venue'].value)
                parts = []
                for i, sec in enumerate(SECTORS):
                    f = tm[i] * (mf if sec == 'MID' else 1.0)
                    if abs(f - 1) > 1e-9:
                        parts.append(f'{sec} {float(row[sec] or 0) * f:.2f} (×{f:.3f})')
                return 'Used in calculation: ' + (', '.join(parts) if parts else 'as entered')

            @ui.refreshable
            def render_rows():
                o_col, o_dark = TEAM_COLORS['opp']
                with ui.grid(columns=2).classes('w-full gap-3 grid-cols-1 md:grid-cols-2'):
                    for idx, row in enumerate(mix_rows):
                        with ui.card().classes('w-full p-0 gap-0 overflow-hidden').style(f'border: 1px solid {o_col} !important;'):
                            mid_lbl = ui.label('')
                            upd = (lambda r=row, lbl=mid_lbl: lbl.set_text(row_mid_text(r)))
                            # Header: how likely, which lineup, which tactic
                            with ui.element('div').classes('w-full px-3 pt-2 pb-2').style(
                                    f'background: linear-gradient(120deg, {o_dark} 0%, {o_col} 100%);'):
                                with ui.row().classes('w-full gap-2 no-wrap items-end'):
                                    ui.number('Weight %', value=row['w'], min=0, step=5, on_change=bind(row, 'w', float)) \
                                        .props('dense').classes('w-20')
                                    ui.input('Lineup', value=row['name'], on_change=bind(row, 'name')).props('dense').classes('flex-grow min-w-0')
                                    tac_sel = ui.select(TACTICS, value=row['tac'], label='Tactic',
                                                        on_change=bind(row, 'tac', None, lambda: render_rows.refresh())) \
                                        .props('dense').classes('w-32')
                                    ui.number('Level', value=row['ca'], min=1, max=25, step=1, on_change=bind(row, 'ca', float)) \
                                        .props('dense').classes('w-16') \
                                        .bind_visibility_from(tac_sel, 'value', backward=lambda v: v in LEVEL_TACTICS)

                                    def remove(i=idx):
                                        mix_rows.pop(i)
                                        render_rows.refresh()
                                    ui.button(icon='delete', on_click=remove).props('flat round dense') \
                                        .style('color: #FFFFFF;').tooltip('Remove this lineup')
                            with ui.column().classes('w-full px-3 pt-2 pb-2 gap-1'):
                                def mix_rating(sec, label):
                                    ui.number(label, value=row[sec], min=0.0, max=30.0, step=0.01, format='%.2f',
                                              on_change=bind(row, sec, float, upd)).props('dense').classes('w-full')

                                def mix_section(name):
                                    ui.label(name).classes('text-xs font-bold uppercase').style(f'color: {o_col}; letter-spacing: 0.12em;')
                                mix_section('Defence')
                                with ui.grid(columns=3).classes('w-full gap-2'):
                                    mix_rating('RD', 'Right'); mix_rating('CD', 'Centre'); mix_rating('LD', 'Left')
                                mix_section('Midfield')
                                with ui.row().classes('w-full gap-2 no-wrap items-center'):
                                    with ui.element('div').classes('flex-grow min-w-0'):
                                        mix_rating('MID', 'Midfield')
                                    ui.toggle({k: k for k in ATT_LONG}, value=row['play'], on_change=bind(row, 'play', None, upd)) \
                                        .props('dense no-caps unelevated toggle-color=ttopp toggle-text-color=white') \
                                        .classes('tt-toggle tt-opp')
                                mix_section('Attack')
                                with ui.grid(columns=3).classes('w-full gap-2'):
                                    mix_rating('RA', 'Right'); mix_rating('CA', 'Centre'); mix_rating('LA', 'Left')
                                with ui.grid(columns=2).classes('w-full gap-2') as ls_row:
                                    ui.number('LS scoring', value=row.get('ls_sc', LS_DEFAULT['ls_sc']), min=1, max=25, step=0.1,
                                              on_change=bind(row, 'ls_sc', float)).props('dense')
                                    ui.number('LS set pieces', value=row.get('ls_sp', LS_DEFAULT['ls_sp']), min=1, max=25, step=0.1,
                                              on_change=bind(row, 'ls_sp', float)).props('dense')
                                ls_row.bind_visibility_from(tac_sel, 'value', backward=lambda v: v == 'Long Shots')
                                # Footer: what's used, and a shortcut to copy the opponent card above
                                with ui.row().classes('w-full items-center justify-between gap-2 mt-1 pt-1 no-wrap') \
                                        .style('border-top: 1px solid #3B3B4D;'):
                                    mid_lbl.move(target_container=ui.element('div').classes('min-w-0'))
                                    mid_lbl.classes('text-xs font-semibold').style(f'color: {o_col};')

                                    def fill_from_opp(r=row):
                                        for sec in SECTORS:
                                            r[sec] = float(opp['r'][sec].value or 0)
                                        render_rows.refresh()
                                    ui.button('Use opponent card', on_click=fill_from_opp).props('flat dense no-caps') \
                                        .style(f'color: {o_col};')
                            upd()
            render_rows()
            opp['venue'].on_value_change(lambda e: render_rows.refresh())
            apply_tac.on_value_change(lambda e: render_rows.refresh())

            mix_result_area = ui.column().classes('w-full mt-4')

            def calculate_mix():
                mix_result_area.clear()
                if not mix_rows:
                    ui.notify('Add at least one lineup row.', type='warning')
                    return
                seen, dupes = {}, []
                for row in mix_rows:
                    key = tuple(round(float(row[s] or 0), 2) for s in SECTORS)
                    if key in seen:
                        dupes.append(f"{row['name']} = {seen[key]}")
                    else:
                        seen[key] = row['name']
                if dupes:
                    ui.notify('⚠️ Same ratings entered for: ' + '; '.join(dupes)
                              + '. Enter each lineup\'s own ratings, otherwise the results are identical.',
                              type='warning', timeout=8000, multi_line=True)
                results, mix_store = [], []
                for row in mix_rows:
                    r_team = build_team({s: row[s] for s in SECTORS}, row['tac'], ATT_LONG[row['seen']],
                                        ATT_LONG[row['play']], apply_tac.value,
                                        {k: v.value for k, v in opp['sp'].items()},
                                        row.get('seen_v', 'Away / neutral'), opp['venue'].value)
                    r_flags = tactic_flags(row['tac'], row['ca'], (row.get('ls_sc', LS_DEFAULT['ls_sc']), row.get('ls_sp', LS_DEFAULT['ls_sp'])),
                                           (my['gk'].value, my['gk_sp'].value), counter_src.value,
                                           match_avg([my['r'][x].value for x in SECTORS], [row[x] for x in SECTORS]))
                    us, us_flags = my_team(my['tac1'].value)
                    res, w, d, l = predict(us, us_flags, r_team, r_flags)
                    mix_store.append({'name': f"{row['name']} ({row['tac']}, {row['play']})", 'weight': float(row['w'] or 0),
                                      'us': us, 'us_flags': us_flags, 'opp': r_team, 'opp_flags': r_flags})
                    results.append({'Weight': float(row['w'] or 0), 'Lineup': f"{row['name']} ({row['tac']}, {row['play']})",
                                    'MID': r_team['MID'],
                                    'Us': res['goals_nl'], 'Opp': res['goals_o'],
                                    'Δ': res['goals_nl'] - res['goals_o'],
                                    'Win%': w * 100, 'Draw%': d * 100, 'Loss%': l * 100})

                try:
                    set_user_pref(user, 'boxplot_mix', {'rows': mix_store, 'us_name': my['country'].value or cc(my),
                                                        'opp_name': opp['country'].value or cc(opp)})
                except Exception:
                    pass
                df = pd.DataFrame(results)
                total_w = df['Weight'].sum()
                if total_w > 0:
                    w_norm = df['Weight'] / total_w
                    avg_row = {'Weight': 100.0, 'Lineup': 'W.AVG'}
                    for c in ['Us', 'Opp', 'Δ', 'Win%', 'Draw%', 'Loss%']:
                        avg_row[c] = (df[c] * w_norm).sum()
                    df['Weight'] = df['Weight'] / total_w * 100
                    df = pd.concat([df, pd.DataFrame([avg_row])], ignore_index=True)

                disp = df.copy()
                disp['Weight'] = disp['Weight'].map(lambda v: f'{v:.0f}%')
                disp['MID'] = disp['MID'].map(lambda v: '' if pd.isna(v) else f'{v:.2f}')
                disp['Us'] = disp['Us'].map(lambda v: f'{v:.2f}')
                disp['Opp'] = disp['Opp'].map(lambda v: f'{v:.2f}')
                disp['Δ'] = [f'{v:+.3f}' if lu == 'W.AVG' else f'{v:+.2f}' for v, lu in zip(df['Δ'], df['Lineup'])]
                for c in ['Win%', 'Draw%', 'Loss%']:
                    disp[c] = disp[c].map(lambda v: f'{v:.1f}%')
                cols = ['Weight', 'Lineup', 'MID', 'Us', 'Opp', 'Δ', 'Win%', 'Draw%', 'Loss%']
                us_c, op_c = cc(my), cc(opp)
                labels = {'Weight': 'Weight', 'Lineup': f'{op_c} lineup', 'MID': f'{op_c} MID used', 'Us': us_c, 'Opp': op_c, 'Δ': 'Δ',
                          'Win%': f'{us_c} win', 'Draw%': 'Draw', 'Loss%': f'{op_c} win'}
                with mix_result_area:
                    ui.label(f'{describe(my)}  vs  {op_c} lineups').classes('text-sm text-gray-400 mb-1')
                    ui.table(columns=[{'name': c, 'label': labels[c], 'field': c, 'align': 'left'} for c in cols],
                             rows=disp[cols].to_dict('records')).classes('w-full').props('dense flat')

                    # Our team first: lineup and its ratings (as Hattrick shows them), then the weighted table
                    lines = [f'[b]{us_c}: {my["form"].value or "?"}, {ATT_SHORT.get(my["play"].value, my["play"].value)}, {my["tac1"].value}'
                             + {'Home': ', Home', 'Derby': ', Derby'}.get(my['venue'].value, '') + '[/b]', '[table]']
                    for sec in SECTORS:
                        v = float(my['r'][sec].value or 0)
                        lines.append(ht_row([SECTOR_NAMES[sec], rating_text(v), f'{v:.2f}']))
                    lines += ['[/table]', '', f'[b]{describe(my)} vs {op_c} lineups[/b]', '[table]',
                              ht_row([labels[c] for c in cols], header=True)]
                    for rec in disp[cols].to_dict('records'):
                        cells = [rec[c] for c in cols]
                        if rec['Lineup'] == 'W.AVG':
                            cells = [f'[b]{c}[/b]' for c in cells]
                        lines.append(ht_row(cells))
                    lines.append('[/table]')
                    markup_block('\n'.join(lines), 'Weighted table')

            # Results already on screen follow the switch straight away.
            def rerun_shown(_=None):
                if sim_results.default_slot.children:
                    run_sim()
                if mix_result_area.default_slot.children:
                    calculate_mix()
            apply_tac.on_value_change(rerun_shown)
            counter_src.on_value_change(rerun_shown)

            with ui.row().classes('gap-4 mt-2'):
                def add_row():
                    mix_rows.append({'w': 0, 'name': f'Lineup {len(mix_rows) + 1}', **OPP_DEFAULT,
                                     'tac': 'Normal', 'seen': 'PIC', 'seen_v': 'Away / neutral', 'play': 'PIC', 'ca': 13})
                    render_rows.refresh()
                ui.button('➕ Add lineup', on_click=add_row).props('outline')
                ui.button('🚀 Calculate weighted mix', on_click=calculate_mix, color=None).classes('tt-goldbtn')

            # ── Save / load predictions ──────────────────────────────────────
            TEAM_FIELDS = ('country', 'code', 'form', 'play', 'venue', 'tac1', 'ca', 'ls_sc', 'ls_sp', 'gk', 'gk_sp')

            def team_state(b):
                d = {k: b[k].value for k in TEAM_FIELDS if k in b}
                d['r'] = {sec: b['r'][sec].value for sec in SECTORS}
                d['sp'] = {k: w.value for k, w in b['sp'].items()}
                d['seen'], d['seen_v'] = b['seen'].value, b['seen_v'].value   # what the ratings are based on
                return d

            def apply_team(b, d):
                for k in TEAM_FIELDS:                     # country before its short name
                    if k in b and d.get(k) is not None:
                        b[k].set_value(d[k])
                for sec, v in (d.get('r') or {}).items():
                    if sec in b['r'] and v is not None:
                        b['r'][sec].set_value(v)
                for k, v in (d.get('sp') or {}).items():
                    if k in b['sp'] and v is not None:
                        b['sp'][k].set_value(v)
                if d.get('seen'):
                    b['seen'].set_value(d['seen'])
                if d.get('seen_v'):
                    b['seen_v'].set_value(d['seen_v'])

            def collect():
                return {'version': 1, 'apply_tac': apply_tac.value, 'counter_src': counter_src.value,
                        'us': team_state(my), 'opp': team_state(opp),
                        'mix': [dict(r) for r in mix_rows]}

            def saved_names():
                return list(get_saved_predictions(user).keys())

            with save_bar:
                BTN = 'width: 96px; height: 40px; background-color: %s; color: white;' % ACCENT
                with ui.grid(columns=2).classes('w-full gap-x-8 gap-y-2 grid-cols-1 md:grid-cols-2'):
                    # Left: load a lineup from the Lineup Simulator into one of the teams
                    with ui.column().classes('w-full gap-2'):
                        tt_section('Load a lineup')
                        with ui.row().classes('w-full items-center gap-2 no-wrap'):
                            lu_sel = ui.select(lineup_choices(), value=LAST_CALC, label='From the Lineup Simulator',
                                               with_input=True).props('dense').classes('flex-1 min-w-0')
                            lu_sel.on('focus', lambda: lu_sel.set_options(lineup_choices(), value=lu_sel.value))

                            def do_load_lineup():
                                (my if lu_target.value == 'us' else opp)['load_lineup'](lu_sel.value)
                            ui.button('📥 Load', on_click=do_load_lineup).props('dense no-caps unelevated') \
                                .style(BTN).mark('load-lineup')
                        with ui.row().classes('w-full items-center gap-2 no-wrap').style('min-height: 40px;'):
                            ui.label('Into').classes('text-sm text-gray-400')
                            lu_target = ui.toggle({'us': 'Your team', 'opp': 'Opponent'}, value='us') \
                                .props('dense no-caps unelevated toggle-color=ttus toggle-text-color=white') \
                                .classes('tt-toggle tt-us').mark('load-target')

                    # Right: saved predictions (both teams + the opponent's lineup mix)
                    with ui.column().classes('w-full gap-2'):
                        tt_section('Saved predictions')
                        with ui.row().classes('w-full items-center gap-2 no-wrap'):
                            pred_sel = ui.select(saved_names(), label='Saved prediction', with_input=True) \
                                .props('dense').classes('flex-1 min-w-0')

                            def do_load():
                                name = pred_sel.value
                                data = get_saved_predictions(user).get(name) if name else None
                                if not data:
                                    ui.notify('Choose a saved prediction first.', type='warning')
                                    return
                                apply_tac.set_value(bool(data.get('apply_tac', False)))
                                if data.get('counter_src') in COUNTER_SOURCES:
                                    counter_src.set_value(data['counter_src'])
                                apply_team(my, data.get('us') or {})
                                apply_team(opp, data.get('opp') or {})
                                if data.get('mix') is not None:
                                    mix_rows[:] = [dict(r) for r in data['mix']]
                                    render_rows.refresh()
                                pred_name.set_value(name)
                                ui.notify(f'Loaded "{name}" (saved {data.get("saved_at", "")}).', type='positive')
                            ui.button('📂 Load', on_click=do_load).props('dense no-caps unelevated') \
                                .style(BTN).mark('load-prediction')

                            def do_delete():
                                name = pred_sel.value
                                if not name:
                                    return
                                delete_saved_prediction(user, name)
                                pred_sel.set_options(saved_names(), value=None)
                                ui.notify(f'Deleted "{name}".')
                            ui.button(icon='delete', on_click=do_delete).props('flat round dense color=grey') \
                                .classes('w-8').mark('delete-prediction').tooltip('Delete the chosen prediction')
                        with ui.row().classes('w-full items-center gap-2 no-wrap'):
                            pred_name = ui.input('Save as', placeholder='e.g. NL – SUI, Pernaug lineups') \
                                .props('dense').classes('flex-1 min-w-0')

                            def do_save():
                                name = (pred_name.value or '').strip()
                                if not name:
                                    ui.notify('Give the prediction a name first.', type='warning')
                                    return
                                save_prediction(user, name, collect())
                                pred_sel.set_options(saved_names(), value=name)
                                ui.notify(f'Saved "{name}": both teams and the opponent\'s lineup mix.', type='positive')
                            ui.button('💾 Save', on_click=do_save).props('dense no-caps unelevated') \
                                .style(BTN).mark('save-prediction')
                            ui.element('div').classes('w-8')   # room of the bin icon above, so the buttons line up