"""Team Spirit (TS) & Team Confidence (TC) estimator.

Rules copied from BLANCO_TS_Inschatter.xlsx and BLANCO_TC_Inschatter.xlsx:
  TS  after a match: TS × attitude factor (PIC ×4/3, Normal ×1, MOTS ×0.5),
      then one drift step per day toward 5 (step size depends on the current TS).
  TC  after a match: TC + 0.5·GF^0.97 − 0.5·GA^0.97 (power fitted to forum data), then a drift step the
      same day and one per following day toward 5.
  Break between rounds: both move 40% (or 60%) of the way back to 5,
  replacing one daily step.
"""
import bisect
import math
from nicegui import ui
from shell import apply_theme, require_login, render_sidebar, ACCENT, ht_row, markup_block, tt_card, page_title
from i18n import tr

TS_ATTITUDE = {'PIC': 4.0 / 3.0, 'Normal': 1.0, 'MOTS': 0.5}

# (from TS, daily change) — 'Data'!B2:C17 of the TS sheet
TS_DRIFT = [(0.0, 0.5), (1.99, 0.2), (2.5, 0.14), (3.5, 0.07), (4.5, 0.02), (5.0, 0.01), (5.01, -0.01),
            (5.5, -0.03), (6.5, -0.08), (7.5, -0.14), (8.5, -0.2), (9.5, -0.3), (10.0, -0.43),
            (11.0, -0.67), (12.0, -0.8), (13.0, -1.0)]
# (from TC, days to cover 0.99) — 'Data'!B1:D12 of the TC sheet; step = ±0.99 / days
TC_DRIFT = [(0.0, 0.99 / 5), (1.5, 0.99 / 8), (2.5, 0.99 / 10), (3.5, 0.99 / 40), (4.5, 0.99 / 50),
            (4.99, 0.0), (5.0, -0.99 / 50), (5.5, -0.99 / 29), (6.5, -0.99 / 14), (7.5, -0.99 / 10),
            (8.5, -0.99 / 8), (9.5, -0.99 / 5)]

TS_WORDS = ['like the Cold War', 'murderous', 'furious', 'irritated', 'composed', 'calm', 'content',
            'satisfied', 'delirious', 'walking on clouds', 'Paradise on Earth!']
TC_WORDS = ['non-existent', 'disastrous', 'wretched', 'poor', 'decent', 'strong', 'wonderful',
            'slightly exaggerated', 'exaggerated', 'completely exaggerated']
RESETS = {'No break': 0.0, 'Break 40%': 0.4, 'Break 60%': 0.6}


def _step(table, value):
    keys = [k for k, _ in table]
    return table[max(0, bisect.bisect_right(keys, value) - 1)][1]


def ts_drift(ts):
    return max(0.0, ts + _step(TS_DRIFT, ts))


def tc_drift(tc):
    return max(0.0, tc + _step(TC_DRIFT, tc))


def reset_toward_5(v, pct):
    return v - pct * (v - 5.0)


def tc_after_result(tc, gf, ga):
    """Confidence after a match (BLANCO's formula, with the power fitted to forum data). Since September 2024 a win never costs
    confidence, however many goals were conceded, so a win's effect is at least 0.
    Hattrick's newer, slower system (fan expectations, coach leadership, psychologist) isn't
    published: this stays an estimate."""
    # power 0.97 (was 0.7071): reproduces the forum data (17254721.301 / 17354587.264):
    # 1-0 has 4.5% more effect than 2-1, and 2-1 1.8% more than 3-2 - so it's about goal difference.
    delta = 0.5 * max(gf, 0) ** 0.97 - 0.5 * max(ga, 0) ** 0.97
    if gf > ga:
        delta = max(delta, 0.0)
    return max(0.0, tc + delta)


def word(value, words):
    # Same banding as the sheets: 4.5–5.49 is level 4, 5.5–6.49 level 5, …
    idx = int(math.floor(value + 0.5)) - 1
    return words[min(max(idx, 0), len(words) - 1)]


def simulate(ts, tc, matches):
    """matches: dicts with att, gf, ga, days (days until the next match), reset (0/0.4/0.6)."""
    out = []
    for m in matches:
        row = {'ts_before': ts, 'tc_before': tc}
        ts = ts * TS_ATTITUDE.get(m['att'], 1.0)
        tc = tc_drift(tc_after_result(tc, m['gf'], m['ga']))   # TC updates the same day
        row['ts_after'], row['tc_after'] = ts, tc
        for day in range(int(m['days'])):
            if m['reset'] and day == 1:          # break replaces one daily step
                ts, tc = reset_toward_5(ts, m['reset']), reset_toward_5(tc, m['reset'])
            else:
                ts, tc = ts_drift(ts), tc_drift(tc)
        out.append(row)
    return out, ts, tc


@ui.page('/tstc')
def tstc_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    render_sidebar(user, '/tstc')

    with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
        page_title('/tstc')

        with tt_card('Team spirit & confidence now'):
            with ui.row().classes('gap-4 items-end'):
                ts_in = ui.number('Team spirit now', value=5.0, min=0, max=14, step=0.01, format='%.2f').classes('w-40')
                tc_in = ui.number('Team confidence now', value=5.0, min=0, max=10, step=0.01, format='%.2f').classes('w-44')
            ui.label('Use the value at the start of the first match below (the sub-level, e.g. 5.5 = calm).'
                     ).classes('text-xs text-gray-400 mt-1')

        # ── What-if for the next match ───────────────────────────────────────
        whatif = ui.column().classes('w-full')

        def render_whatif():
            whatif.clear()
            ts0, tc0 = float(ts_in.value or 0), float(tc_in.value or 0)
            with whatif:
                with tt_card('Next match: what happens after it'):
                    with ui.row().classes('w-full gap-8 flex-wrap'):
                        with ui.column():
                            ui.label('Team spirit right after the match').classes('text-sm text-gray-400')
                            rows = [{'Attitude': a, 'TS': f'{ts0 * f:.2f}', 'Level': word(ts0 * f, TS_WORDS)}
                                    for a, f in TS_ATTITUDE.items()]
                            ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in ['Attitude', 'TS', 'Level']],
                                     rows=rows).props('dense flat')
                    # Every score from 0-0 to 5-5: TC depends on goals for AND against, not just the difference.
                    ui.label('Team confidence right after the match — our goals down, opponent goals across'
                             ).classes('text-sm text-gray-400 mt-3')
                    goals = range(6)
                    grid, mrows = {}, []
                    for gf in goals:
                        row = {'us': f'{gf}'}
                        for ga in goals:
                            v = tc_drift(tc_after_result(tc0, gf, ga))
                            grid[(gf, ga)] = v
                            row[str(ga)] = f'{v:.2f} ({v - tc0:+.2f})'
                        mrows.append(row)
                    mcols = [{'name': 'us', 'label': 'Us \\ Opp', 'field': 'us', 'align': 'center'}] + \
                            [{'name': str(g), 'label': str(g), 'field': str(g), 'align': 'center'} for g in goals]
                    with ui.element('div').classes('w-full overflow-x-auto'):
                        ui.table(columns=mcols, rows=mrows).props('dense flat')
                    ui.label('Levels: ' + ', '.join(f'{lo:.1f}+ {w}' for lo, w in
                             [(3.5, 'poor'), (4.5, 'decent'), (5.5, 'strong'), (6.5, 'wonderful'), (7.5, 'slightly exaggerated')])
                             ).classes('text-xs text-gray-500')

                    ts_rows = [(a, ts0 * f) for a, f in TS_ATTITUDE.items()]
                    lines = [f'[b]Next match[/b] (now: TS {ts0:.2f}, TC {tc0:.2f})',
                             '[table]', ht_row(['Attitude', 'TS after', 'Level'], header=True)]
                    lines += [ht_row([a, f'{v:.2f}', word(v, TS_WORDS)]) for a, v in ts_rows]
                    lines += ['[/table]', '[b]Team confidence after the match[/b] (our goals down, opponent goals across)',
                              '[table]', ht_row(['Us \\ Opp'] + [str(g) for g in goals], header=True)]
                    lines += [ht_row([f'[b]{gf}[/b]'] + [f'{grid[(gf, ga)]:.2f} ({grid[(gf, ga)] - tc0:+.2f})' for ga in goals])
                              for gf in goals]
                    lines.append('[/table]')
                    markup_block('\n'.join(lines), 'Next-match table')

        # ── Match plan ───────────────────────────────────────────────────────
        plan = [
            {'name': tr('Match 1'), 'att': 'Normal', 'gf': 1, 'ga': 1, 'days': 3, 'reset': 'No break'},
            {'name': tr('Match 2'), 'att': 'Normal', 'gf': 1, 'ga': 1, 'days': 4, 'reset': 'No break'},
        ]

        def bind(row, key, cast=None):
            return lambda e: row.__setitem__(key, cast(e.value) if (cast and e.value is not None) else e.value)

        with tt_card('Match plan'):
            ui.label('Days to next match: Fri → Mon = 3, Mon → Fri = 4. A break (e.g. between tournament rounds) '
                     'moves both values part of the way back to 5.').classes('text-xs text-gray-400 mb-2')

            @ui.refreshable
            def render_plan():
                for idx, row in enumerate(plan):
                    with ui.row().classes('w-full items-center gap-2 flex-wrap mb-1'):
                        ui.input('Match', value=row['name'], on_change=bind(row, 'name')).classes('w-44')
                        ui.select(list(TS_ATTITUDE), value=row['att'], label='Attitude', on_change=bind(row, 'att')).classes('w-28')
                        ui.number('Goals for', value=row['gf'], min=0, max=20, step=1, on_change=bind(row, 'gf', float)).classes('w-24')
                        ui.number('Against', value=row['ga'], min=0, max=20, step=1, on_change=bind(row, 'ga', float)).classes('w-24')
                        ui.number('Days to next', value=row['days'], min=0, max=30, step=1, on_change=bind(row, 'days', float)).classes('w-28')
                        ui.select(list(RESETS), value=row['reset'], label='After this match', on_change=bind(row, 'reset')).classes('w-44')

                        def remove(i=idx):
                            plan.pop(i)
                            render_plan.refresh()
                        ui.button(icon='delete', on_click=remove).props('flat round dense color=grey')
            render_plan()

            def add_match():
                last_days = plan[-1]['days'] if plan else 4
                plan.append({'name': tr(f'Match {len(plan) + 1}'), 'att': 'Normal', 'gf': 1, 'ga': 1,
                             'days': 4 if last_days == 3 else 3, 'reset': 'No break'})
                render_plan.refresh()

            with ui.row().classes('gap-4 mt-2'):
                ui.button('➕ Add match', on_click=add_match).props('outline')
                ui.button('📈 Calculate', on_click=lambda: calculate(), color=None).classes('tt-goldbtn')

        result_area = ui.column().classes('w-full')

        def calculate():
            render_whatif()
            result_area.clear()
            if not plan:
                return
            matches = [{'att': r['att'], 'gf': float(r['gf'] or 0), 'ga': float(r['ga'] or 0),
                        'days': int(r['days'] or 0), 'reset': RESETS.get(r['reset'], 0.0)} for r in plan]
            rows_out, ts_end, tc_end = simulate(float(ts_in.value or 0), float(tc_in.value or 0), matches)
            table_rows = []
            for r, m, o in zip(plan, matches, rows_out):
                table_rows.append({
                    'Match': r['name'], 'Attitude': r['att'], 'Result': f"{int(m['gf'])}-{int(m['ga'])}",
                    'TS before': f"{o['ts_before']:.2f} ({word(o['ts_before'], TS_WORDS)})",
                    'TC before': f"{o['tc_before']:.2f} ({word(o['tc_before'], TC_WORDS)})",
                    'TS after': f"{o['ts_after']:.2f}", 'TC after': f"{o['tc_after']:.2f}",
                })
            cols = ['Match', 'Attitude', 'Result', 'TS before', 'TC before', 'TS after', 'TC after']
            with result_area:
                with tt_card('Going into each match'):
                    ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in cols],
                             rows=table_rows).classes('w-full').props('dense flat')
                    ui.label(f'After the last period: team spirit {ts_end:.2f} ({word(ts_end, TS_WORDS)}), '
                             f'team confidence {tc_end:.2f} ({word(tc_end, TC_WORDS)}).').classes('text-sm mt-2')

                    lines = [f'[b]Team spirit & confidence plan[/b] (start: TS {float(ts_in.value or 0):.2f}, '
                             f'TC {float(tc_in.value or 0):.2f})', '[table]', ht_row(cols, header=True)]
                    lines += [ht_row([r[c] for c in cols]) for r in table_rows]
                    lines += ['[/table]', f'After the last period: TS [b]{ts_end:.2f}[/b] ({word(ts_end, TS_WORDS)}), '
                              f'TC [b]{tc_end:.2f}[/b] ({word(tc_end, TC_WORDS)})']
                    markup_block('\n'.join(lines), 'Match plan')

        ts_in.on_value_change(lambda e: render_whatif())
        tc_in.on_value_change(lambda e: render_whatif())
        calculate()