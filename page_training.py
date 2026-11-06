"""Training planner: when does a player reach each next level, where will he be at 21 / 22, and does
that meet his country's U21 minimum? Training speed: HT-Tools formula (ht_engine.training_schedule)."""
from nicegui import ui
from shell import apply_theme, require_login, render_sidebar, ACCENT, tt_card, tt_section, page_title, ht_row, markup_block
from i18n import tr as tr_, trf as trf_
try:   # expected stamina by age and stamina share
    import stamina_data as SD
except ImportError:
    SD = None
TRAIN_CSS = ('<style>'
             '.tt-tr-main.nicegui-grid { grid-template-columns: minmax(0, 1fr) !important; }'
             '@media (min-width: 1100px) { .tt-tr-main.nicegui-grid { grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr) !important; } }'
             '.tt-sttab { width: 100%; border-collapse: collapse; font-size: 14px; }'
             '.tt-sttab th { font-family: Oswald, sans-serif; font-size: 12px; letter-spacing: .08em; text-transform: uppercase;'
             '  color: #8FA3BA; text-align: left; padding: 6px 8px; border-bottom: 1px solid #2A3647; }'
             '.tt-sttab th.tt-hl { color: #F6C510; }'
             '.tt-sttab td { padding: 7px 8px; border-bottom: 1px solid #2A3647; }'
             '.tt-sttab td b { font-family: Oswald, sans-serif; font-size: 15px; }'
             '.tt-sttab tr.tt-hlrow td { background: rgba(246,197,16,.10); }'
             '.tt-kvv { font-family: Oswald, sans-serif; font-size: 16px; font-weight: 600; }'
             '</style>')
from data_layer import get_user_pref, set_user_pref
from data_layer import load_user_db, safe_float, safe_int, get_watchlists
from ht_engine import (
    normalize_position, normalize_nationality, get_flag, clean_spec, skill_level_label,
    TRAINING_TYPES, SKILL_TRAINING, TRAINING_SKILL, TRAINED_SKILL, TRAINING_COACH_FACTOR, TRAINING_MAX_AGE,
    training_schedule, skill_at_age,
)
from richtskills_data import country_minimums_21
try:   # Hattrick specialty icons
    import spec_icons as SI
except ImportError:
    SI = None
try:   # newer ht_engine.py only: training advice from the contribution table
    from ht_engine import training_advice, best_positions, ORDER_LABELS, CONTRIBUTIONS
except ImportError:
    training_advice = None
try:
    from richtskills_data import country_minimums_29
except ImportError:          # older richtskills_data.py
    def country_minimums_29(country, pos, spec=None):
        return None
try:
    from richtskills_data import country_guide_roles
except ImportError:          # older richtskills_data.py
    def country_guide_roles(country, pos):
        return []
try:
    from richtskills_data import country_guide_ages
except ImportError:
    def country_guide_ages(country):
        return (21, 29)

SKILLS = [('GK', 'Keeper'), ('DE', 'Defending'), ('PM', 'Playmaking'), ('WI', 'Winger'),
          ('Pas', 'Passing'), ('SC', 'Scoring'), ('SH', 'Set pieces')]
SKILL_NAME = dict(SKILLS)
COACH_LEVELS = {4: '4 - weak', 5: '5 - inadequate', 6: '6 - passable', 7: '7 - solid', 8: '8 - excellent'}
# Main training per position when TRAINED_SKILL has none (DFW: passing).
EXTRA_TRAINED = {'DFW': 'Pas', 'TDFW': 'Pas'}
ALL = '🌍 All Players'


def age_txt(y, d):
    return f'{int(y)}y {int(d)}d'


@ui.page('/training')
def training_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    df = load_user_db(user)
    render_sidebar(user, '/training')
    ui.add_head_html(TRAIN_CSS)

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_title('/training')
        if df.empty:
            ui.label('No players in your roster yet.').classes('text-gray-400')
            return

        names = df['Speler'].dropna().tolist()
        try:
            watchlists = get_watchlists(user)
        except Exception:
            watchlists = {}
        countries = sorted(set(normalize_nationality(c) for c in df['Nationality'].dropna().unique())) \
            if 'Nationality' in df.columns else []
        filter_opts = [ALL] + [f'{get_flag(c)} {c}' for c in countries] + [f'📋 {n}' for n in watchlists if n != '__EMPTY__']

        def label(n):
            r = df[df['Speler'] == n].iloc[0]
            return f"{n} ({r.get('Positie', '') or '?'}, {safe_int(r.get('Leeftijd', 0))})"

        def filtered():
            v = filter_select.value or ALL
            if v == ALL:
                return names
            if v.startswith('📋 '):
                members = set(watchlists.get(v[2:].strip(), []))
                return [n for n in names if n in members]
            c = v.split(' ', 1)[1] if ' ' in v else v
            return df[df['Nationality'].apply(normalize_nationality) == c]['Speler'].dropna().tolist()

        with ui.row().classes('w-full gap-3 items-center no-wrap mb-4 tt-pbar'):
            filter_select = ui.select(filter_opts, value=ALL, label='Filter by Country / Watchlist').classes('w-56')
            player_select = ui.select({n: label(n) for n in names}, label='Player', with_input=True).classes('flex-1 min-w-0')
            if SI is not None and 'Specialiteit' in df.columns:
                _sp = dict(zip(df['Speler'], df['Specialiteit']))
                SI.player_select(player_select, {label(n): _sp.get(n) for n in names}, selected=False, value_specs=_sp)

        def on_filter(_):
            player_select.set_options({n: label(n) for n in filtered()}, value=None)
        filter_select.on_value_change(on_filter)
        # Remember the filter in the database (follows you to every device).
        _f0 = get_user_pref(user, 'training_filter', None)
        if _f0 and _f0 in filter_opts and _f0 != filter_select.value:
            filter_select.value = _f0   # runs on_filter
        filter_select.on_value_change(lambda e: set_user_pref(user, 'training_filter', e.value))

        content = ui.column().classes('w-full')

        def render(_=None):
            content.clear()
            name = player_select.value
            if not name:
                with content:
                    ui.label('Pick a player to plan his training.').classes('text-gray-400')
                return
            p = df[df['Speler'] == name].iloc[0]
            pos = normalize_position(str(p.get('Positie') or 'NFW'))
            age, days = safe_int(p.get('Leeftijd', 20)), safe_int(p.get('dag(en)', 0))
            spec = clean_spec(p.get('Specialiteit', 'None'))
            nat = str(p.get('Nationality') or '')
            skills = {k: safe_float(p.get(k, 1.0)) for k, _ in SKILLS}
            main = TRAINED_SKILL.get(pos) or EXTRA_TRAINED.get(pos, 'PM')

            with content:
                with tt_card(f'{name}', f'{pos} · {age_txt(age, days)} · {get_flag(nat)} {nat}'
                                        + (f' · {spec}' if spec != 'None' else '')):
                    with ui.grid(columns=7).classes('w-full gap-2'):
                        for k, n in SKILLS:
                            with ui.column().classes('gap-0'):
                                ui.label(n).classes('text-xs text-gray-400')
                                ui.label(f'{skills[k]:.2f}').classes('text-lg font-bold')
                    if age > TRAINING_MAX_AGE:
                        ui.label(f'The planner only looks ahead until age {TRAINING_MAX_AGE}.').classes('text-amber-400 text-sm')
                        return

                with tt_card('Training setup', 'Set to the normal training for his position and a solid coach. Change what you like.'):
                    with ui.grid(columns=3).classes('w-full gap-3 grid-cols-1 md:grid-cols-3'):
                        tr_sel = ui.select(list(TRAINING_TYPES), value=SKILL_TRAINING[main], label='Training')
                        share = ui.number('Share of the weeks (%)', value=100, min=1, max=100, step=5) \
                            .tooltip('Put 50 if you swap between this and another training every other week')
                        coach = ui.select(COACH_LEVELS, value=7, label='Coach level')
                        assist = ui.number('Assistant coach levels (0-15)', value=10, min=0, max=15, step=1)
                        intensity = ui.number('Intensity (%)', value=100, min=1, max=100, step=5)
                        stamina = ui.number('Stamina share (%)', value=10, min=0, max=100, step=5)

                roles = country_guide_roles(nat, pos)
                role_sel = None
                if roles:
                    role_opts = {i: r[0] + (f" ({'/'.join(s[0] for s in r[1])})" if r[1] else '')
                                 + (' ✓' if r[1] and spec in r[1] else '') for i, r in enumerate(roles)}
                    default = next((i for i, r in enumerate(roles) if r[1] and spec in r[1] and pos == 'K'), 0)
                    with ui.row().classes('w-full -mt-2 mb-2'):
                        role_sel = ui.select(role_opts, value=default,
                                             label=f'{get_flag(nat)} {nat} NT role (guide targets)').classes('w-80')

                result = ui.column().classes('w-full')

                def calc(_=None):
                    result.clear()
                    tr = tr_sel.value
                    sk = TRAINING_SKILL.get(tr, main)
                    kw = dict(coach=int(coach.value or 7), assistants=int(assist.value or 0),
                              intensity=float(intensity.value or 100), stamina=float(stamina.value or 0),
                              share=float(share.value or 100) / 100.0)
                    sched = training_schedule(age, days, skills[sk], tr, **kw)
                    with result:
                        # ── At a glance: stamina and the next levels ──
                        st_share = float(stamina.value or 0)
                        st_code = SD.expected_stamina(age, st_share)[0] if SD else None
                        with ui.grid(columns=4).classes('w-full gap-3 tt-tiles mb-4'):
                            for val, lab in ((f'{st_share:.0f}%', tr_('stamina share in this setup')),
                                             (tr_(SD.stamina_text(st_code)) if st_code else '–', trf_('stamina he can keep at {}', age)),
                                             (f'{sched[0][3]:.1f}' if sched else '–', trf_('weeks to {} {}', SKILL_NAME[sk], int(skills[sk]) + 1)),
                                             (f'{int(coach.value or 7)} · {int(assist.value or 0)}', tr_('coach level · assistant levels'))):
                                with ui.column().classes('gap-0 tt-tile'):
                                    ui.label(val).classes('tt-tilev')
                                    ui.label(lab).classes('text-sm text-gray-400')
                        with ui.grid(columns=2).classes('w-full gap-4 mb-2 items-start tt-tr-main'):
                            with tt_card('🔋 Stamina calculator', 'The stamina a player keeps, by age and stamina share (Hattrick Codex)', classes='w-full'):
                                if SD:
                                    shares = sorted({10, 15, 20, 30, int(min(50, max(10, round(st_share))))})
                                    ages = [a for a in range(max(17, age - 3), min(36, age + 3) + 1)]
                                    hdr = ''.join(f'<th class="{"tt-hl" if s_ == int(min(50, max(10, round(st_share)))) else ""}">{s_}%</th>' for s_ in shares)
                                    body = ''
                                    for a in ages:
                                        cells = ''.join(f'<td>{tr_(SD.stamina_text(SD.expected_stamina(a, s_)[0]))}</td>' for s_ in shares)
                                        body += f'<tr class="{"tt-hlrow" if a == age else ""}"><td><b>{a}</b></td>{cells}</tr>'
                                    ui.html(f'<table class="tt-sttab"><tr><th>{tr_("Age")}</th>{hdr}</tr>{body}</table>').classes('w-full')
                                    _need = SD.share_for(age, 8)
                                    ui.label(trf_('To keep him at excellent stamina at {}: {}', age,
                                                  f'{_need}%' if _need else tr_('not possible (over 50%)'))).classes('text-sm mt-2')
                                    ui.label(tr_('Rule of thumb for the team: average age of the squad − 10 = stamina share (%).')).classes('text-xs text-gray-400')
                            with tt_card('📈 Next levels', trf_('{} with this setup', SKILL_NAME[sk]), classes='w-full'):
                                if not sched:
                                    ui.label(trf_('No new level before {}', TRAINING_MAX_AGE)).classes('text-gray-400')
                                mx = max((w for *_x, w in sched[:4]), default=1.0) or 1.0
                                for lev, y_, d_, wk in sched[:4]:
                                    with ui.row().classes('w-full items-center justify-between no-wrap'):
                                        ui.label(f'{SKILL_NAME[sk]} {int(lev) - 1} → {int(lev)}').classes('text-sm')
                                        ui.label(trf_('{} weeks', f'{wk:.1f}')).classes('tt-kvv')
                                    with ui.element('div').classes('w-full').style('height:10px;border-radius:999px;background:#262D38;overflow:hidden;margin-bottom:8px'):
                                        ui.element('div').style(f'height:100%;width:{max(6, 100 * (1 - wk / (mx * 1.15))):.0f}%;'
                                                                'background:linear-gradient(90deg,#2F6EA8,#5AA0DC)')
                        with tt_card(f'{tr}: {SKILL_NAME[sk]} {skills[sk]:.2f} now'):
                            proj = []
                            for y in (21, 22):
                                if (age, days) < (y, 0):
                                    proj.append(f'at {y}y 0d: {skill_at_age(y, 0, age, days, skills[sk], tr, **kw):.2f}')
                            if proj:
                                ui.label(f'{SKILL_NAME[sk]} ' + ' · '.join(proj)).classes('text-md font-semibold').style(f'color:{ACCENT};')
                            if not sched:
                                ui.label(f'He won\'t reach a new level before {TRAINING_MAX_AGE}.').classes('text-gray-400')
                            else:
                                rows, total = [], 0.0
                                for lev, y, d, wk in sched:
                                    total += wk
                                    rows.append({'Level': skill_level_label(lev), 'Reached at': age_txt(y, d),
                                                 'Weeks': f'{wk:.1f}', 'Total weeks': f'{total:.1f}'})
                                cols = ['Level', 'Reached at', 'Weeks', 'Total weeks']
                                ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in cols],
                                         rows=rows).props('dense flat').classes('w-full')

                        mins = country_minimums_21(nat, pos, spec)
                        if mins and (age, days) < (22, 0):
                            at21 = dict(skills)
                            if (age, days) < (21, 0):
                                at21[sk] = skill_at_age(21, 0, age, days, skills[sk], tr, **kw)
                            with tt_card(f'{get_flag(nat)} {nat} U21 minimum for {pos}',
                                         'What he needs at 21 to get picked. Only the skill you train moves here, '
                                         'the others stay where they are today.'):
                                rows, short = [], []
                                for k, n in SKILLS:
                                    if k not in mins:
                                        continue
                                    ok = at21[k] >= float(mins[k]) - 1e-9
                                    if not ok:
                                        short.append(f'{n} {at21[k]:.2f} / {float(mins[k]):g}')
                                    rows.append({'Skill': n, 'Minimum': f'{float(mins[k]):g}', 'Now': f'{skills[k]:.2f}',
                                                 'At 21y 0d': f'{at21[k]:.2f}' + (' 📈' if k == sk and at21[k] != skills[k] else ''),
                                                 'Check': '✓' if ok else f'✗ {at21[k] - float(mins[k]):+.2f}'})
                                cols = ['Skill', 'Minimum', 'Now', 'At 21y 0d', 'Check']
                                ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in cols],
                                         rows=rows).props('dense flat').classes('w-full')
                                if short:
                                    ui.label('✗ Not enough at 21: ' + ', '.join(short)).classes('text-sm font-semibold') \
                                        .style('color:#F87171;')
                                else:
                                    ui.label('✓ He makes the U21 minimum at 21.').classes('text-sm font-semibold').style('color:#34D399;')

                        mins29 = country_minimums_29(nat, pos, spec)
                        if mins29 and (age, days) >= (21, 0):
                            at29 = dict(skills)
                            if (age, days) < (29, 0):
                                at29[sk] = skill_at_age(29, 0, age, days, skills[sk], tr, **kw)
                            with tt_card(f'{get_flag(nat)} {nat} NT minimum for {pos}',
                                         'What he needs at 29 to get picked for the NT. Only the skill you train moves '
                                         'here, the others stay where they are today.'):
                                rows, short = [], []
                                for k, n in SKILLS:
                                    if k not in mins29:
                                        continue
                                    m = float(mins29[k])
                                    ok = at29[k] >= m - 1e-9
                                    if not ok:
                                        short.append(f'{n} {at29[k]:.2f} / {m:g}')
                                    rows.append({'Skill': n, 'Minimum': f'{m:g}', 'Now': f'{skills[k]:.2f}',
                                                 'At 29y 0d': f'{at29[k]:.2f}' + (' 📈' if k == sk and at29[k] != skills[k] else ''),
                                                 'Check': '✓' if ok else f'✗ {at29[k] - m:+.2f}'})
                                cols = ['Skill', 'Minimum', 'Now', 'At 29y 0d', 'Check']
                                ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in cols],
                                         rows=rows).props('dense flat').classes('w-full')
                                if short:
                                    ui.label('✗ Not enough at 29: ' + ', '.join(short)).classes('text-sm font-semibold') \
                                        .style('color:#F87171;')
                                else:
                                    ui.label('✓ He makes the NT minimum at 29.').classes('text-sm font-semibold').style('color:#34D399;')

                        if roles and role_sel is not None:
                            role, _specs, t21, t29 = roles[int(role_sel.value or 0)]
                            t21, t29 = t21 or {}, t29 or {}
                            young = (age, days) < (21, 0)
                            at21 = dict(skills)
                            if young:
                                at21[sk] = skill_at_age(21, 0, age, days, skills[sk], tr, **kw)
                            ya, yb = country_guide_ages(nat)
                            la, lb = f'Target at {ya}', f'Target at {yb}'
                            with tt_card(f'{get_flag(nat)} {nat} NT targets: {role}',
                                         f'About what a good player in this role has at {ya} and {yb}. A guide, not a '
                                         'hard rule.'):
                                rows = []
                                for k, n in SKILLS:
                                    if k not in t21 and k not in t29:
                                        continue
                                    row = {'Skill': n, 'Now': f'{skills[k]:.2f}'}
                                    if young:
                                        row['At 21y 0d'] = f'{at21[k]:.2f}' + (' 📈' if k == sk and at21[k] != skills[k] else '')
                                    if k in t21:
                                        v = at21[k] - t21[k]
                                        row[la] = f'{t21[k]:g}' + ('  ✓' if v >= -1e-9 else f'  (✗ {v:+.2f})')
                                    else:
                                        row[la] = '–'
                                    if k in t29:
                                        need = t29[k] - skills[k]
                                        row[lb] = f'{t29[k]:g}'
                                        row['Still needed'] = '✓' if need <= 1e-9 else \
                                            (f'{need:g} level' + ('s' if abs(need - 1) > 1e-9 else '') if abs(need - round(need)) < 1e-9
                                             else f'{need:.1f} levels')
                                    else:
                                        row[lb], row['Still needed'] = '–', ''
                                    rows.append(row)
                                cols = ['Skill', 'Now'] + (['At 21y 0d'] if young else []) + ([la] if t21 else []) + [lb, 'Still needed']
                                ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in cols],
                                         rows=rows).props('dense flat').classes('w-full')
                                # When the trained skill reaches its targets with this setup.
                                lines = []
                                for lbl, tg in ((f'Target at {ya}', t21.get(sk)), (f'Target at {yb}', t29.get(sk))):
                                    if tg is None:
                                        continue
                                    if skills[sk] >= tg:
                                        lines.append(f'{lbl} ({tg:g}) already reached')
                                        continue
                                    hit = next((s for s in sched if s[0] >= tg), None)
                                    lines.append(f'{lbl} ({tg:g}) ' + (f'reached at {age_txt(hit[1], hit[2])}' if hit
                                                 else f'not reached before {TRAINING_MAX_AGE} with this training'))
                                if lines:
                                    ui.label(f'{SKILL_NAME[sk]}: ' + ', '.join(lines) + '.').classes('text-sm font-semibold') \
                                        .style(f'color:{ACCENT};')

                # Ageing: every Monday a player loses a little of each skill from the age it starts dropping
                # (Schum's drop table). Shown from 27 on, for the skills that count for him.
                try:
                    from ht_engine import weekly_skill_drop
                except ImportError:
                    weekly_skill_drop = None
                if weekly_skill_drop is not None and age >= 26 and pos != 'K':
                    _sk = [k for k, _ in sorted(((k, skills[k]) for k in ('DE', 'PM', 'WI', 'Pas', 'SC', 'SH')),
                                                key=lambda t: -t[1])[:4]]
                    _ages = [a for a in range(max(age, 27), 36)]
                    _rows = [{'Skill': SKILL_NAME[k], **{str(a): (f"−{weekly_skill_drop(k, a) * 16:.2f}" if weekly_skill_drop(k, a) else '–')
                                                          for a in _ages}} for k in _sk]
                    with tt_card('📉 Loss from ageing per season', 'How much each of his main skills drops in a season at '
                                 'each age (16 Mondays), before training. Training on a skill can make up for it.'):
                        ui.table(columns=[{'name': 'Skill', 'label': 'Skill', 'field': 'Skill', 'align': 'left'}]
                                 + [{'name': str(a), 'label': str(a), 'field': str(a), 'align': 'right'} for a in _ages],
                                 rows=_rows).props('dense flat').classes('w-full')

                # Which training adds most to his rating in a chosen position (contribution table).
                adv_box = ui.column().classes('w-full')
                adv_order = None
                if training_advice is not None and pos != 'K':
                    _fits = best_positions({k: skills[k] for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC')}, spec,
                                           n=len(CONTRIBUTIONS))
                    _opts = {o: f"{ORDER_LABELS.get(o, o)} ({f:.0f}%)" for o, f in _fits if o != 'K'}
                    with adv_box:
                        with tt_card('📈 Which training helps his rating most',
                                     'What 16 weeks of each training adds to his rating in this position, with the '
                                     'setup above'):
                            adv_order = ui.select(_opts, value=next(iter(_opts)), label='Position (fit %)').classes('w-72')
                            adv_out = ui.column().classes('w-full')

                def calc_advice(_=None):
                    if adv_order is None:
                        return
                    adv_out.clear()
                    kw = dict(coach=int(coach.value or 7), assistants=int(assist.value or 0),
                              intensity=float(intensity.value or 100), stamina=float(stamina.value or 0),
                              share=float(share.value or 100) / 100.0)
                    rows = training_advice(skills, adv_order.value, age, days, **kw)
                    with adv_out:
                        if not rows:
                            ui.label(f'The planner only looks ahead until age {TRAINING_MAX_AGE}.').classes('text-gray-400')
                            return
                        best = rows[0]['gain_score'] or 1.0
                        ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'}
                                          for c in ['Training', 'Now', 'After a season', 'Rating gain', 'vs best']],
                                 rows=[{'Training': SKILL_NAME[r['skill']], 'Now': f"{r['now']:.2f}",
                                        'After a season': f"{r['after']:.2f}", 'Rating gain': f"+{r['gain_score']:.2f}",
                                        'vs best': f"{r['gain_score'] / best * 100:.0f}%"} for r in rows]) \
                            .props('dense flat').classes('w-full')
                        ui.label('Only his rating in this position counts here, not the higher wage, his TSI or the '
                                 'other players training with him.').classes('text-xs text-gray-400')

                for w in (tr_sel, share, coach, assist, intensity, stamina) + ((role_sel,) if role_sel else ()):
                    w.on_value_change(calc)
                    w.on_value_change(calc_advice)
                if adv_order is not None:
                    adv_order.on_value_change(calc_advice)
                calc()
                calc_advice()

        player_select.on_value_change(render)
        render()