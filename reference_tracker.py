import pandas as pd
from nicegui import ui

# Minimum players per cell for KNN to be reliable
TARGET_GOOD = 20   # ✓ green — KNN reliable
TARGET_OK   = 10    # ~ amber — KNN marginal
# < 10 = red — KNN falls back to formula only

# Positions where KNN is active (SHWB/K excluded due to SH variance)
KNN_ACTIVE = {'NFW','NW','NCD','NIM','WTM','PNF','DFW','NWB','OIM-H','OIM-Q','PDIM'}

AGE_BANDS = [(17,21,'U21'),(22,25,'22-25'),(26,29,'26-29'),(30,33,'30-33'),(34,35,'34-35')]   # 36+: mostly not playing, not used as peers

# Positions to track gaps for — exclude rare/niche positions
GAP_POSITIONS = {'NFW','NW','NCD','NIM','WTM','PNF','DFW','NWB','OIM-H','OIM-Q','CAD','OCD','PDIM'}

POSITIONS = [
    ('SHWB', 'Shooting WB',        False),
    ('K',    'Keeper',              False),
    ('NCD',  'Normal CD',           True),
    ('NWB',  'Normal WB',           True),
    ('NIM',  'Normal IM',           True),
    ('OIM-H','Offensive IM (Head)', True),
    ('OIM-Q','Offensive IM (Quick)',True),
    ('NW',   'Normal Winger',       True),
    ('WTM',  'Winger→Mid',          True),
    ('NFW',  'Normal FW',           True),
    ('PNF',  'Powerful NF',         True),
    ('DFW',  'Defensive FW',        True),
    ('TDFW', 'Tech Def FW',         True),
    ('PDIM', 'Powerful DIM',        True),
    ('OCD',  'Offensive CD',        True),
    ('CAD',  'Counter-attack CD',   True),
]


def get_coverage(df):
    """Returns dict of {pos: {age_label: count}} for all positions."""
    result = {}
    for pos, _, _ in POSITIONS:
        result[pos] = {}
        sub = df[df['Positie'] == pos] if not df.empty else pd.DataFrame()
        for lo, hi, label in AGE_BANDS:
            n = len(sub[(sub['Leeftijd'] >= lo) & (sub['Leeftijd'] <= hi)]) if not sub.empty else 0
            result[pos][label] = n
    return result


def render_tracker_dashboard(df):
    """Redesigned tracker showing Position × Age band coverage grid."""

    ui.label('📈 Reference DB Coverage').classes('text-2xl font-bold mt-4 mb-2')

    coverage = get_coverage(df)
    total = len(df) if not df.empty else 0

    # Summary counts
    with ui.row().classes('gap-4 mb-4 flex-wrap'):
        ui.label(f'Total: {total}').classes('text-lg font-bold text-white')
        _old = int((df['Leeftijd'] >= 36).sum()) if not df.empty and 'Leeftijd' in df.columns else 0
        if _old:
            ui.label(f'{_old} aged 36+ (not used as peers)').classes('text-sm text-gray-400')
        good_cells = sum(1 for pos_data in coverage.values()
                        for n in pos_data.values() if n >= TARGET_GOOD)
        ok_cells   = sum(1 for pos_data in coverage.values()
                        for n in pos_data.values() if TARGET_OK <= n < TARGET_GOOD)
        bad_cells  = sum(1 for pos_data in coverage.values()
                        for n in pos_data.values() if 0 < n < TARGET_OK)
        empty_cells= sum(1 for pos_data in coverage.values()
                        for n in pos_data.values() if n == 0)
        ui.label(f'✅ {good_cells} good').classes('text-green-400 text-sm')
        ui.label(f'🟡 {ok_cells} thin').classes('text-amber-400 text-sm')
        ui.label(f'🔴 {bad_cells} poor').classes('text-red-400 text-sm')
        ui.label(f'⬜ {empty_cells} missing').classes('text-gray-500 text-sm')

    # Main coverage grid
    with ui.card().classes('w-full p-4'):
        # Header row
        with ui.row().classes('w-full gap-0 mb-1'):
            ui.label('Position').classes('text-xs text-gray-400 font-bold w-32')
            ui.label('KNN').classes('text-xs text-gray-400 font-bold w-10 text-center')
            for _, _, label in AGE_BANDS:
                ui.label(label).classes('text-xs text-gray-400 font-bold w-16 text-center')
            ui.label('Total').classes('text-xs text-gray-400 font-bold w-14 text-right')

        ui.separator().classes('mb-1')

        for pos, label, knn_active in POSITIONS:
            pos_data = coverage[pos]
            pos_total = sum(pos_data.values())
            if pos_total == 0 and pos not in ('SHWB','NFW','NW','NCD','K','NIM','WTM','PNF'):
                continue  # hide empty minor positions

            with ui.row().classes('w-full gap-0 items-center py-0.5'):
                # Position label
                with ui.column().classes('w-32'):
                    ui.label(f'{pos}').classes('text-sm font-semibold')
                    ui.label(label).classes('text-xs text-gray-500')

                # KNN indicator
                knn_icon = '🔵' if knn_active else '⚪'
                ui.label(knn_icon).classes('w-10 text-center text-sm')

                # Age band cells
                for _, _, band_label in AGE_BANDS:
                    n = pos_data[band_label]
                    if n >= TARGET_GOOD:
                        bg = 'bg-green-900/60'
                        tc = 'text-green-300'
                    elif n >= TARGET_OK:
                        bg = 'bg-amber-900/60'
                        tc = 'text-amber-300'
                    elif n > 0:
                        bg = 'bg-red-900/60'
                        tc = 'text-red-300'
                    else:
                        bg = 'bg-gray-800/30'
                        tc = 'text-gray-600'
                    ui.label(str(n) if n > 0 else '—').classes(
                        f'w-16 text-center text-sm font-mono rounded py-0.5 {bg} {tc}'
                    )

                # Total
                ui.label(str(pos_total)).classes('w-14 text-right text-sm font-bold text-gray-300')

    # Priority gaps — what to collect next
    ui.label('🎯 Priority Gaps').classes('text-lg font-semibold mt-4 mb-2')

    gaps, filled = [], []
    for pos, _, knn_active in POSITIONS:
        if not knn_active:
            continue
        if pos not in GAP_POSITIONS:
            continue  # skip TDFW (same build as DFW)
        for lo, hi, label in AGE_BANDS:
            n = coverage[pos].get(label, 0)
            if n < TARGET_GOOD:
                priority = 'HIGH' if n < TARGET_OK else 'MED'
                gaps.append((priority, pos, label, n, TARGET_GOOD - n))
            else:
                filled.append((pos, label, n))

    # Sort by priority then by fewest players
    gaps.sort(key=lambda x: (0 if x[0]=='HIGH' else 1, x[3]))

    if not gaps:
        ui.label('✅ All positions well covered!').classes('text-green-400')
    else:
        with ui.grid(columns=3).classes('w-full gap-2 grid-cols-1 md:grid-cols-3'):
            for priority, pos, age_label, n, needed in gaps:
                color = 'border-red-600' if priority == 'HIGH' else 'border-amber-600'
                dot   = '🔴' if priority == 'HIGH' else '🟡'
                with ui.card().classes(f'p-3 border {color}'):
                    ui.label(f'{dot} {pos} · {age_label}').classes('text-sm font-bold')
                    ui.label(f'{n} players — need {needed} more').classes('text-xs text-gray-400')

    # Groups that reached the target: out of the list above, kept here (collapsed) for reference
    if filled:
        with ui.expansion(f'✅ Filled — {len(filled)} groups with {TARGET_GOOD}+ players (archive)').classes('w-full mt-3'):
            with ui.grid(columns=4).classes('w-full gap-2 grid-cols-2 md:grid-cols-4'):
                for pos, age_label, n in sorted(filled):
                    with ui.card().classes('p-2 border border-green-800'):
                        ui.label(f'✅ {pos} · {age_label}').classes('text-sm font-bold text-green-300')
                        ui.label(f'{n} players').classes('text-xs text-gray-400')