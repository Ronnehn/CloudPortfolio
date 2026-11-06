"""Boxplot (BETA): the spread behind an average. Slot 1 shows how often each number of goals happens in the
last Score Predictor match (same chance model as the predictor, worked out exactly, no random replays).
Slots 2-4 are reserved for later boxplots."""
import numpy as np
from nicegui import ui
from shell import apply_theme, require_login, render_sidebar, tt_card, page_title
from data_layer import get_user_pref
from i18n import tr, trf
import json as _json
import ht_engine as H

US_COLOR, OPP_COLOR = '#5E95CC', '#C27D56'          # team colours (checked for colour-blind contrast on the dark cards)
INK, MUTED, CARD, GRID = '#E6E8EE', '#9AA3B2', '#1C1C24', '#2E3140'
TOP = 6                                             # bars 0..5 and 6+
LAST, MIX = 'Last prediction', "Opponent's possible lineups (weighted)"
MODES = {'100': '100 matches', '1000': '1,000 matches', '10000': '10,000 matches', 'exact': 'Exact chance'}


def store_test_match(user):
    """A made-up close match (Team A slightly better than Team B), only to try out the boxplot."""
    from data_layer import set_user_pref
    sp = {'DIRSP': 0.0, 'ISPOFF': 11.0, 'ISPDEF': 11.0, 'N_PNF': 0, 'N_CD': 2, 'N_PDIM': 0}
    flags = {'AIM': 0, 'AOW': 0, 'PRESS': 0, 'CAPCT': 0.0, 'REDIR': None}
    set_user_pref(user, 'boxplot_match', {
        'us': dict(RD=13.0, CD=15.0, LD=13.25, MID=12.75, RA=12.0, CA=13.5, LA=12.25, **sp), 'us_flags': flags,
        'opp': dict(RD=12.75, CD=14.5, LD=13.0, MID=12.25, RA=12.25, CA=13.0, LA=11.75, **sp), 'opp_flags': dict(flags),
        'us_name': 'Team A', 'opp_name': 'Team B', 'desc': '🧪 Test match: Team A vs Team B (made-up ratings)'})


def score_matrix(src):
    """P[a, b] for one stored match, or the weighted mix of several."""
    if 'rows' in src:
        rows = [r for r in src['rows'] if r.get('weight', 0) > 0] or src['rows']
        tot = sum(max(r.get('weight', 0), 0) for r in rows) or len(rows)
        M = None
        for r in rows:
            w = (max(r.get('weight', 0), 0) or 1) / tot
            P = H.goal_distribution(r['us'], r['opp'], r['us_flags'], r['opp_flags']) * w
            M = P if M is None else M + P
        return M
    return H.goal_distribution(src['us'], src['opp'], src['us_flags'], src['opp_flags'])


def summary(p):
    """Spread of one team's goals from its probabilities p[k]."""
    k = np.arange(len(p)); cdf = np.cumsum(p)
    q = lambda x: int(np.searchsorted(cdf, x - 1e-9))
    return dict(mean=float((k * p).sum()), p10=q(0.10), q25=q(0.25), med=q(0.50), q75=q(0.75), p90=q(0.90),
                mode=int(np.argmax(p)), pmode=float(p.max()))


def _js(template, *exprs):
    """A JavaScript string expression for a translated template: '{}' parts become the given JS expressions."""
    parts = trf(template, *(['\x00'] * len(exprs))).split('\x00')
    out = _json.dumps(parts[0])
    for e, p in zip(exprs, parts[1:]):
        out += f' + ({e}) + ' + _json.dumps(p)
    return out


def goals_txt(k, top=False):
    """'1 goal' / '3 goals' (k = 6 with top: '6+ goals')."""
    lab = f'{k}+' if top else str(k)
    return trf('{} goal', lab) if (k == 1 and not top) else trf('{} goals', lab)


def goals_label(k):
    return f'{k}+' if k == TOP else str(k)


def team_chart(name, p, color, n=None):
    """p = chance (or share of the replays) of each number of goals; n = number of replays, None = exact chances."""
    s = summary(p)
    pct = [float(p[k] * 100) for k in range(TOP)] + [float(p[TOP:].sum() * 100)]
    vals = [int(round(v * n / 100)) for v in pct] if n else [round(v, 1) for v in pct]
    if n:
        lab_fmt = 'p => p.value > 0 ? p.value + "x" : ""'
        tip_fmt = 'p => ' + _js('{} goals: {} out of {} matches', 'p.name', 'p.value', str(n))
    else:
        lab_fmt = 'p => p.value >= 2 ? Math.round(p.value) + "%" : ""'
        tip_fmt = 'p => ' + _js('{} goals in {}% of matches', 'p.name', 'p.value.toFixed(1)')
    opt = {
        'backgroundColor': 'transparent', 'animation': False,
        'title': {'text': name, 'subtext': trf('scores {} goals on average', f"{s['mean']:.1f}") + (' · ' + trf('{} matches played', f'{n:,}') if n else ''), 'left': 4, 'top': 0,
                  'textStyle': {'color': INK, 'fontSize': 15}, 'subtextStyle': {'color': MUTED, 'fontSize': 12}},
        'tooltip': {'trigger': 'item', 'backgroundColor': '#262730', 'borderColor': '#3B3B4D', 'textStyle': {'color': INK}},
        'grid': [{'left': 24, 'right': 24, 'top': 58, 'height': 150}, {'left': 24, 'right': 24, 'top': 238, 'height': 30}],
        # bars on a category axis (0 .. 6+); the box below on a value axis with the same centres (-0.5 .. 6.5)
        'xAxis': [{'type': 'category', 'gridIndex': 0, 'data': [goals_label(k) for k in range(TOP + 1)],
                   'axisLine': {'lineStyle': {'color': GRID}}, 'axisTick': {'show': False},
                   'axisLabel': {'color': MUTED, 'fontSize': 12}},
                  {'type': 'value', 'gridIndex': 1, 'min': -0.5, 'max': TOP + 0.5, 'show': False}],
        'yAxis': [{'type': 'value', 'gridIndex': 0, 'show': False, 'max': max(vals) * 1.25 or 1},
                  {'type': 'category', 'gridIndex': 1, 'data': [''], 'show': False}],
        'series': [
            {'type': 'bar', 'xAxisIndex': 0, 'yAxisIndex': 0, 'barWidth': 34, 'data': vals,
             'itemStyle': {'color': color, 'borderRadius': [4, 4, 0, 0]},
             'label': {'show': True, 'position': 'top', 'color': INK, 'fontSize': 12,
                       ':formatter': lab_fmt},
             'tooltip': {':formatter': tip_fmt}},
            {'type': 'boxplot', 'xAxisIndex': 1, 'yAxisIndex': 1, 'boxWidth': [18, 18],
             'data': [[min(s['p10'], TOP), min(s['q25'], TOP), min(s['med'], TOP), min(s['q75'], TOP), min(s['p90'], TOP)]],
             'itemStyle': {'color': color + '59', 'borderColor': INK, 'borderWidth': 1.5},
             'tooltip': {':formatter': '() => ' + _js('Half of the matches: {} to {} goals<br>8 out of 10 matches: {} to {} goals<br>Middle result: {}',
                                                     *[_json.dumps(str(s[k])) for k in ('q25', 'q75', 'p10', 'p90', 'med')])}},
            {'type': 'scatter', 'xAxisIndex': 1, 'yAxisIndex': 1, 'symbol': 'diamond', 'symbolSize': 13, 'z': 5,
             'data': [[round(s['mean'], 2), '']], 'itemStyle': {'color': CARD, 'borderColor': INK, 'borderWidth': 1.5},
             'tooltip': {':formatter': '() => ' + _js('Average: {} goals (no single match ends like that)', _json.dumps(f"{s['mean']:.2f}"))}},
        ]}
    ui.echart(opt).classes('w-full').style('height: 278px;')
    often = trf('{} out of {}', int(round(s['pmode'] * n)), f'{n:,}') if n else trf('{}% of matches', f"{s['pmode'] * 100:.0f}")
    rng_ = lambda a, b: goals_txt(a) if a == b else trf('{} to {} goals', a, b)
    ui.label(trf('Usually {} ({}). Half of the matches: {}. 8 out of 10 matches: {}.', goals_txt(s['mode'], s['mode'] == TOP), often,
                 rng_(s['q25'], s['q75']), rng_(s['p10'], s['p90']))) \
        .classes('text-xs').style(f'color: {MUTED}; margin: 0 0 14px 24px;')


def score_chart(M, us_name, opp_name, n=None):
    cap = 5                                          # 0..4 and 5+
    G = np.zeros((cap + 1, cap + 1))
    for a in range(M.shape[0]):
        for b in range(M.shape[1]):
            G[min(a, cap), min(b, cap)] += M[a, b]
    G = np.round(G * n) if n else G * 100
    top = set(np.argsort(G.ravel())[::-1][:3].tolist())
    data = []
    for a in range(cap + 1):
        for b in range(cap + 1):
            item = {'value': [b, a, int(G[a, b]) if n else round(float(G[a, b]), 1)]}
            if G[a, b] > 0.55 * G.max():
                item['label'] = {'color': '#0E1117', 'fontWeight': 'bold'}
            if a * (cap + 1) + b in top:
                item['itemStyle'] = {'borderColor': '#FBBF24', 'borderWidth': 2}
            data.append(item)
    lab = [str(i) for i in range(cap)] + [f'{cap}+']
    opt = {
        'backgroundColor': 'transparent', 'animation': False,
        'tooltip': {'backgroundColor': '#262730', 'borderColor': '#3B3B4D', 'textStyle': {'color': INK},
                    ':formatter': 'p => ' + _js('{} {} – {} {}: {}', _json.dumps(us_name), 'p.value[1]', 'p.value[0]', _json.dumps(opp_name),
                                                 _js('{} out of {} matches', 'p.value[2]', str(n)) if n else _js('{}% of matches', 'p.value[2].toFixed(1)'))},
        'grid': {'left': 46, 'right': 10, 'top': 10, 'bottom': 46},
        'xAxis': {'type': 'category', 'data': lab, 'name': trf('Goals {}', opp_name), 'nameLocation': 'middle', 'nameGap': 28,
                  'nameTextStyle': {'color': MUTED}, 'axisLabel': {'color': MUTED}, 'axisLine': {'show': False}, 'axisTick': {'show': False}},
        'yAxis': {'type': 'category', 'data': lab, 'inverse': True, 'name': trf('Goals {}', us_name), 'nameLocation': 'middle', 'nameGap': 30,
                  'nameTextStyle': {'color': MUTED}, 'axisLabel': {'color': MUTED}, 'axisLine': {'show': False}, 'axisTick': {'show': False}},
        'visualMap': {'show': False, 'min': 0, 'max': float(G.max()), 'inRange': {'color': ['#20232D', '#1F4A75', '#5E95CC', '#BFD7F0']}},
        'series': [{'type': 'heatmap', 'data': data,
                    'label': {'show': True, 'fontSize': 11, ':formatter': ('p => p.value[2] > 0 ? p.value[2] : ""' if n else 'p => p.value[2] >= 0.5 ? Math.round(p.value[2]) : ""'),
                              'color': INK},
                    'itemStyle': {'borderColor': CARD, 'borderWidth': 2}}]}
    ui.echart(opt).classes('w-full').style('height: 330px;')


@ui.page('/boxplot')
def boxplot_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    render_sidebar(user, '/boxplot')

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_title('/boxplot')
        last, mix = get_user_pref(user, 'boxplot_match', None), get_user_pref(user, 'boxplot_mix', None)
        choices = ([LAST] if last else []) + ([MIX] if mix and mix.get('rows') else [])

        with tt_card('🎲 Slot 1 · Goals per match', 'Not just the average: how many goals each team really scores'):
            if not choices:
                ui.label('Nothing to show yet. Run a prediction in the Score Predictor, or try the test match.') \
                    .classes('text-sm').style(f'color: {MUTED};')
                with ui.row().classes('gap-2'):
                    ui.button('🎯 Go to the Score Predictor', on_click=lambda: ui.navigate.to('/predictor')).props('outline no-caps')
                    ui.button('🧪 Try a test match', on_click=lambda: (store_test_match(user), ui.navigate.reload())) \
                        .props('outline no-caps')
            else:
                with ui.row().classes('items-center gap-4'):
                    src_sel = ui.toggle(choices, value=choices[0]).props('dense no-caps unelevated toggle-color=primary')
                    mode_sel = ui.toggle(MODES, value='100').props('dense no-caps unelevated toggle-color=primary') \
                        .tooltip('Play this match 100, 1,000 or 10,000 times and count the goals. '
                                 'Exact chance: what you would get if you played it forever.')
                    again = ui.button('🎲 Play again', on_click=lambda: render()).props('dense outline no-caps')
                body = ui.column().classes('w-full gap-0')
                rng = np.random.default_rng()

                def render(_=None):
                    body.clear()
                    src = last if src_sel.value == LAST else mix
                    M = score_matrix(src)
                    n = None if mode_sel.value == 'exact' else int(mode_sel.value)
                    again.set_visibility(n is not None)
                    if n:   # play n matches with the same chances and count what happens
                        idx = rng.choice(M.size, size=n, p=(M / M.sum()).ravel())
                        M = np.bincount(idx, minlength=M.size).reshape(M.shape) / n
                    us_name, opp_name = src.get('us_name', 'Your team'), src.get('opp_name', 'Opponent')
                    p_us, p_opp = M.sum(axis=1), M.sum(axis=0)
                    w, d, l = float(np.tril(M, -1).sum()), float(np.trace(M)), float(np.triu(M, 1).sum())
                    with body:
                        head = last.get('desc') if src_sel.value == LAST else f"{us_name} vs {len(mix['rows'])} possible {opp_name} lineups"
                        head += f"  ·  played {n:,} times" if n else "  ·  exact chances"
                        ui.label(head).classes('text-sm font-semibold mt-2').style(f'color: {INK};')
                        with ui.row().classes('w-full gap-6 no-wrap items-start').style('flex-wrap: wrap;'):
                            with ui.column().classes('gap-0').style('flex: 3 1 460px; min-width: 300px;'):
                                team_chart(us_name, p_us, US_COLOR, n)
                                team_chart(opp_name, p_opp, OPP_COLOR, n)
                            with ui.column().classes('gap-1').style('flex: 2 1 320px; min-width: 280px;'):
                                ui.label(f'Final scores (out of {n:,} matches)' if n else 'Final scores (% of matches)') \
                                    .classes('text-sm font-bold').style(f'color: {INK};')
                                ui.label('Yellow boxes: the 3 most common scores. Point at a box for the details.') \
                                    .classes('text-xs').style(f'color: {MUTED};')
                                score_chart(M, us_name, opp_name, n)
                                res = (f'{us_name} won {round(w * n)}  ·  Draw {round(d * n)}  ·  {opp_name} won {round(l * n)}' if n
                                       else f'{us_name} win {w * 100:.0f}%  ·  Draw {d * 100:.0f}%  ·  {opp_name} win {l * 100:.0f}%')
                                ui.label(res) \
                                    .classes('text-sm font-bold').style(f'color: {INK};')
                        ui.label('How to read the box: the coloured box holds half of the matches, the lines reach 8 out of 10 '
                                 'matches, the white stripe is the middle result and ◇ is the average. An average of 1.6 goals '
                                 'never happens in a real match: a team scores 1 or 2.') \
                            .classes('text-xs mt-2').style(f'color: {MUTED};')

                src_sel.on_value_change(render)
                mode_sel.on_value_change(render)
                render()

        for n in (2, 3, 4):
            with tt_card(f'🔒 Slot {n} · coming later', 'Room for another boxplot'):
                ui.label('Kept free for a future boxplot.').classes('text-sm').style(f'color: {MUTED};')