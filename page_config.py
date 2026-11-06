import io
import pandas as pd
from nicegui import ui, app
from shell import apply_theme, require_login, render_sidebar, tt_card, page_title
from data_layer import (
    get_country_age_richtskills, get_richtskills_for_age, save_country_age_richtskills,
    delete_country_age_richtskills, export_richtskills_to_csv, export_richtskills_to_excel,
    import_richtskills_dataframe,
)
from ht_engine import COUNTRY_LIST, get_flag
from richtskills_data import RICHTSKILLS_DEFAULT, RICHTSKILLS_AGE_MIN, RICHTSKILLS_AGE_MAX
try:
    from richtskills_data import country_target_log
except ImportError:          # older richtskills_data.py
    country_target_log = None


@ui.page('/config')
def config_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    render_sidebar(user, '/config')

    pos_list = list(RICHTSKILLS_DEFAULT.keys())

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        page_title('/config')

        with ui.row().classes('gap-4'):
            country_select = ui.select(COUNTRY_LIST, value=('Netherlands' if 'Netherlands' in COUNTRY_LIST else COUNTRY_LIST[0]), label='Country').classes('w-64')
            age_select = ui.select(list(range(RICHTSKILLS_AGE_MIN, RICHTSKILLS_AGE_MAX + 1)), value=RICHTSKILLS_AGE_MIN, label='Age').classes('w-32')
            pos_select = ui.select(pos_list, value=pos_list[0], label='Position').classes('w-40')

        content = ui.column().classes('w-full')

        @ui.refreshable
        def render_content():
            content.clear()
            country, age, pos = country_select.value, age_select.value, pos_select.value
            stored_for_age = get_country_age_richtskills(country, age) or {}
            has_override = pos in stored_for_age
            bench_all = get_richtskills_for_age(country, age)
            bench = bench_all.get(pos, bench_all.get('NFW', RICHTSKILLS_DEFAULT['NFW']))
            status_txt = 'custom override saved' if has_override else 'best-guess estimate'

            with content:
                with tt_card(f'🎯 Target Skills — {get_flag(country)} {country} / Age {age} / {pos} ({status_txt})'):
                    inputs = {}
                    with ui.grid(columns=7).classes('w-full gap-4'):
                        for sk, icon in [('GK', '🧤'), ('DE', '🛡️'), ('PM', '⚙️'), ('WI', '🏃'), ('Pas', '🎯'), ('SC', '⚽'), ('SH', '🥅')]:
                            inputs[sk] = ui.number(f'{icon} {sk}', value=float(bench.get(sk, 1.0)), min=1.0, max=25.0, step=0.1)

                    with ui.row().classes('gap-4 mt-2'):
                        def do_save():
                            new_vals = {sk: float(inp.value) for sk, inp in inputs.items()}
                            stored_for_age[pos] = new_vals
                            save_country_age_richtskills(country, age, stored_for_age)
                            ui.notify(f'✅ Saved target skills for {country}, Age {age}, {pos}.', type='positive')
                            render_content.refresh()
                        ui.button('💾 Save as Target for this Age / Position', on_click=do_save, color=None).classes('tt-goldbtn')

                        if has_override:
                            def do_reset():
                                stored_for_age.pop(pos, None)
                                if stored_for_age:
                                    save_country_age_richtskills(country, age, stored_for_age)
                                else:
                                    delete_country_age_richtskills(country, age)
                                ui.notify('↩️ Reverted to best-guess estimate.', type='positive')
                                render_content.refresh()
                            ui.button('↩️ Reset to Best-Guess Estimate', on_click=do_reset)

                with tt_card(f'📋 Full Age Curve Preview — {get_flag(country)} {country} / {pos}'):
                    preview_rows = []
                    for a in range(RICHTSKILLS_AGE_MIN, RICHTSKILLS_AGE_MAX + 1):
                        b = get_richtskills_for_age(country, a).get(pos, {})
                        row = {'Age': a, 'Custom': '✅' if pos in (get_country_age_richtskills(country, a) or {}) else ''}
                        row.update({sk: round(b.get(sk, 1.0), 2) for sk in ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']})
                        preview_rows.append(row)
                    cols = ['Age', 'Custom', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
                    ui.table(columns=[{'name': c, 'label': c, 'field': c} for c in cols], rows=preview_rows).classes('w-full').props('dense flat')

                with tt_card('📤 Import / Export to CSV / XLSX'):
                    with ui.row().classes('gap-4'):
                        def download_csv():
                            ui.download(export_richtskills_to_csv(country), f'{country}_richtskills.csv')
                        def download_xlsx():
                            buf = export_richtskills_to_excel(country)
                            ui.download(buf.getvalue(), f'{country}_richtskills.xlsx')
                        ui.button('📥 Export as CSV', on_click=download_csv)
                        ui.button('📥 Export as Excel', on_click=download_xlsx)

                    async def handle_upload(e):
                        try:
                            content = await e.file.read()
                            if e.file.name.lower().endswith('.xlsx'):
                                df = pd.read_excel(io.BytesIO(content))
                            else:
                                df = pd.read_csv(io.BytesIO(content))
                            rows_applied, ages_touched = import_richtskills_dataframe(df, country)
                            if rows_applied == 0:
                                ui.notify('⚠️ No valid rows found.', type='warning')
                            else:
                                ui.notify(f'✅ Applied {rows_applied} rows across {ages_touched} ages.', type='positive')
                                render_content.refresh()
                        except Exception as ex:
                            ui.notify(f'Import Error: {ex}', type='negative')

                    ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=".csv,.xlsx"').classes('w-full mt-2')

        # ── Log: which countries have their own targets (built in), and which have custom ones saved ──
        if country_target_log is not None:
            with tt_card('📒 Country targets log', 'Countries with their own target skills, and for which age group'):
                rows = []
                for r in country_target_log():
                    rows.append({'Country': f"{get_flag(r['country'])} {r['country']}",
                                 'U22': '✓' if r['u21'] else '–', 'NT': '✓' if r['nt'] else '–',
                                 'Richtskills': '✓' if r.get('richt') else '–',
                                 'Training planner': '✓' if r.get('planner') else '–', 'Added': r['date']})
                try:   # custom targets saved in the app (this page), per country and age
                    from data_layer import get_db_connection
                    conn = get_db_connection()
                    saved = conn.cursor().execute('SELECT country, age FROM country_age_richtskills ORDER BY country, age;').fetchall()
                    conn.close()
                    by_c = {}
                    for c, a in saved:
                        by_c.setdefault(c, []).append(int(a))
                    # one row per country: a country already in the log gets the custom ages merged in
                    by_name = {str(r['Country']).split(' ', 1)[-1].strip().lower(): r for r in rows}
                    for c, ages in by_c.items():
                        r = by_name.get(str(c).strip().lower())
                        if r is not None:
                            if min(ages) <= 21:
                                r['U22'] = '✓'
                            if max(ages) >= 22:
                                r['NT'] = '✓'
                            r['Richtskills'] = '✓'
                            continue
                        rows.append({'Country': f'{get_flag(c)} {c}', 'U22': '✓' if min(ages) <= 21 else '–',
                                     'NT': '✓' if max(ages) >= 22 else '–', 'Richtskills': '✓', 'Training planner': '–',
                                     'Added': ''})
                except Exception:
                    pass
                cols = ['Country', 'U22', 'NT', 'Richtskills', 'Training planner', 'Added']
                ui.table(columns=[{'name': c, 'label': c, 'field': c, 'align': 'left'} for c in cols],
                         rows=rows).props('dense flat wrap-cells').classes('w-full')

        country_select.on_value_change(lambda e: render_content.refresh())
        age_select.on_value_change(lambda e: render_content.refresh())
        pos_select.on_value_change(lambda e: render_content.refresh())
        render_content()