import json
import re
from contextlib import contextmanager
from pathlib import Path
from nicegui import ui, app
from data_layer import (
    verify_user, record_login, get_db_connection,
    DB_STATUS,
)
import i18n
from i18n import tr
i18n.install()   # English / Dutch: translates every text on its way to the browser

# Accent color: muted steel-blue — used only for buttons/highlights/borders,
# never for body text, so it can't clash or read as an odd hue against the
# dark background regardless of monitor/rendering.
ACCENT = '#2F6EA8'        # v2.9 blue: buttons, borders, highlights
ACCENT_DARK = '#1F4A75'   # deep blue: menu, page headers, card headers
NAVY = '#0C2036'          # darkest blue (bottom of the gradients)
GOLD = '#F6C510'          # gold accent: logo, the page you are on, switches
FORM_GREEN = '#4E8A5B'    # form / stamina bars
ACCENT_SOFT = 'rgba(47, 110, 168, 0.18)'


def _ic(d):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" width="17" height="17">' + d + '</svg>')


# Line icons for the menu and the page headers (one per page)
ICONS = {
    '/import': _ic('<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 19h16"/>'),
    '/': _ic('<path d="M4 6h10"/><path d="M18 6h2"/><circle cx="16" cy="6" r="2"/><path d="M4 12h4"/><path d="M12 12h8"/>'
             '<circle cx="10" cy="12" r="2"/><path d="M4 18h12"/><circle cx="18" cy="18" r="2"/>'),
    '/autosolver': _ic('<path d="M4 20L15 9"/><path d="M15 4v3"/><path d="M15 11v3"/><path d="M19 9h-3"/><path d="M14 9h-3"/>'
                       '<path d="M18 5l-1.5 1.5"/><path d="M18 13l-1.5-1.5"/>'),
    '/training': _ic('<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>'),
    '/roster': _ic('<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/>'
                   '<path d="M16 14c2.8 0 5 2.2 5 5"/>'),
    '/reference': _ic('<ellipse cx="12" cy="5.5" rx="7.5" ry="2.8"/><path d="M4.5 5.5v13c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8v-13"/>'
                      '<path d="M4.5 12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8"/>'),
    '/lineup': _ic('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 12h18"/><circle cx="12" cy="12" r="2.6"/>'
                   '<path d="M8 4v3h8V4"/><path d="M8 20v-3h8v3"/>'),
    '/predictor': _ic('<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/>'),
    '/tstc': _ic('<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>'),
    '/boxplot': _ic('<path d="M4 20h16"/><path d="M7 16V9"/><rect x="5" y="10" width="4" height="4" rx=".5"/><path d="M12 17V5"/>'
                    '<rect x="10" y="7" width="4" height="6" rx=".5"/><path d="M17 15V8"/><rect x="15" y="10" width="4" height="3" rx=".5"/>'),
    '/config': _ic('<path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>'),
    '/users': _ic('<circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7"/>'),
    'manuals': _ic('<path d="M4 5.5C4 4.7 4.7 4 5.5 4H11v16H5.5c-.8 0-1.5-.7-1.5-1.5z"/><path d="M20 5.5c0-.8-.7-1.5-1.5-1.5H13v16h5.5'
                   'c.8 0 1.5-.7 1.5-1.5z"/>'),
}


def logo_svg(size=46, uid='m'):
    """The Tooltrick logo: the gold T on a blue tactics board (an X, an O and a dotted gold run between them)."""
    return f'''<svg width="{size}" height="{size}" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="display:block">
<defs><linearGradient id="bd{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a5d8f"/><stop offset="1" stop-color="#0c2036"/></linearGradient>
<linearGradient id="gd{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe066"/><stop offset="1" stop-color="#e0a300"/></linearGradient></defs>
<rect x="2" y="2" width="60" height="60" rx="15" fill="url(#bd{uid})" stroke="url(#gd{uid})" stroke-width="3"/>
<g stroke="rgba(255,255,255,.22)" stroke-width="1.4" fill="none"><line x1="3.5" y1="40" x2="60.5" y2="40"/><path d="M24 62v-7a8 8 0 0 1 16 0v7"/></g>
<g stroke="rgba(255,255,255,.55)" stroke-width="2.6" stroke-linecap="round"><path d="M9 47l5 5M14 47l-5 5"/></g>
<circle cx="53" cy="49.5" r="3.6" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="2.4"/>
<path d="M15 45C20 31 43 30 49.5 45" fill="none" stroke="#f6c510" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="1 4.2"/>
<path d="M46.5 42.5l3 3 1.5-4" fill="none" stroke="#f6c510" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M15 12h34v9H37.5v19h-11V21H15z" fill="#0c2036" opacity=".45" transform="translate(1.2 1.6)"/>
<path d="M15 12h34v9H37.5v19h-11V21H15z" fill="url(#gd{uid})"/>
<path d="M15 12h34v3H15z" fill="#fff" opacity=".28"/></svg>'''


WORDMARK = ('<span style="font-family:Oswald,sans-serif;font-weight:700;letter-spacing:.06em;color:#FFFFFF">TOOL</span>'
            '<span style="font-family:Oswald,sans-serif;font-weight:700;letter-spacing:.06em;color:#F6C510">TRICK</span>')

# The faint pitch and formulas drawn on the page headers
CHALK_SVG = ('<svg class="tt-chalk" viewBox="0 0 1200 200" preserveAspectRatio="xMaxYMid slice" xmlns="http://www.w3.org/2000/svg">'
             '<g fill="none" stroke="rgba(255,255,255,.09)" stroke-width="2"><rect x="30" y="14" width="1140" height="172" rx="4"/>'
             '<line x1="760" y1="14" x2="760" y2="186"/><circle cx="760" cy="100" r="40"/><rect x="1060" y="55" width="110" height="90"/>'
             '<path d="M840 60 q120 -50 230 15" stroke-dasharray="8 7" stroke="rgba(246,197,16,.30)"/></g>'
             '<g font-family="Oswald,sans-serif" fill="rgba(255,255,255,.09)" font-size="24">'
             '<text x="860" y="44">TSI = S² · √form</text><text x="980" y="176">a³/(a³+b³)</text><text x="560" y="176">wage = main + ½·rest</text>'
             '<text x="1080" y="44">5-5-5</text><text x="620" y="56">×1.199</text></g></svg>')

FONT_CSS = ('<style>'
    + ''.join(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
              f"src:url(/tt-fonts/{fam.lower()}-latin-{w}-normal.woff2) format('woff2');"
              "unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}"
              f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
              f"src:url(/tt-fonts/{fam.lower()}-latin-ext-{w}-normal.woff2) format('woff2');"
              "unicode-range:U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}"
              for fam, ws in (('Oswald', (500, 600, 700)), ('Barlow', (400, 500, 600, 700))) for w in ws)
    + '</style>')
# fonts are served from the "fonts" folder next to the app files (no outside requests)
FONT_DIR = Path(__file__).parent / 'fonts'
if FONT_DIR.is_dir():
    app.add_static_files('/tt-fonts', str(FONT_DIR))

# v2.9 look: deep-blue menu and headers, gold accents, Oswald titles and Barlow text
BLUE_CSS = ('<style>'
    'body, .q-field__native, .q-field__input, .q-btn, .q-item, .q-table { font-family: Barlow, Roboto, "Segoe UI", sans-serif !important; }'
    '.q-card { background-color: #19202A !important; border: 1px solid #283242 !important; border-radius: 12px !important;'
    '  box-shadow: 0 1px 2px rgba(0,0,0,.25), 0 6px 18px rgba(0,0,0,.18) !important; }'
    '.q-table { background-color: #19202A !important; } .q-table th { font-family: Oswald, sans-serif !important; letter-spacing: .06em;'
    '  text-transform: uppercase; font-size: 12px !important; color: #8FA3BA !important; }'
    '.q-field--outlined .q-field__control:before { border-color: #33465C !important; }'
    '.q-field--outlined:hover .q-field__control:before { border-color: #2F6EA8 !important; }'
    '.q-btn { font-weight: 600; } .q-btn.bg-primary { background: linear-gradient(180deg,#3577B4,#2F6EA8) !important; }'
    # card header strip (tt_card / player_card)
    '.tt-chead { background: linear-gradient(120deg, #1C2838 0%, #25374D 100%) !important; position: relative; overflow: hidden;'
    '  border-bottom: 2px solid rgba(246,197,16,.45); }'
    '.tt-chead:after { content: ""; position: absolute; right: -34px; top: -44px; width: 130px; height: 130px; border-radius: 50%;'
    '  border: 2px solid rgba(255,255,255,.07); pointer-events: none; }'
    '.tt-ctitle { font-family: Oswald, sans-serif !important; font-weight: 600 !important; font-size: 17px !important;'
    '  letter-spacing: .02em !important; text-transform: none !important; color: #FFFFFF; }'
    '.tt-card { border: 1px solid #283242 !important; }'
    # v2.9.1 soft denim: calmer, greyer blue; the page background a touch bluer than black
    'body, .q-layout, .q-page-container { background-color: #12161D !important; }'
    # page header (hero)
    '.tt-hero { position: relative; overflow: hidden; border-radius: 16px; padding: 16px 24px 16px; margin-bottom: 14px; color: #fff;'
    '  background: radial-gradient(ellipse at 75% 15%, rgba(255,255,255,.07), transparent 60%), linear-gradient(135deg, #2B4766, #18263A);'
    '  box-shadow: 0 6px 20px rgba(0,0,0,.28); border: 1px solid rgba(255,255,255,.06); }'
    '.tt-hero .tt-chalk { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }'
    '.tt-hero > * { position: relative; }'
    '.tt-kicker { font-size: 12.5px; font-weight: 600; color: #B7CCE3; letter-spacing: .04em; }'
    '.tt-badge { width: 42px; height: 42px; border-radius: 50%; background: #F6C510; color: #0C2036; display: grid; place-items: center;'
    '  box-shadow: 0 0 0 5px rgba(246,197,16,.22); flex-shrink: 0; } .tt-badge svg { width: 22px; height: 22px; }'
    '.tt-h1 { font-family: Oswald, sans-serif !important; font-weight: 700 !important; font-size: 30px !important; line-height: 1.15;'
    '  letter-spacing: -.005em; color: #FFFFFF; }'
    '.tt-goldrule { width: 96px; height: 4px; border-radius: 4px; background: #F6C510; margin: 10px 0 8px; }'
    '.tt-htag { color: #F3E7A6; font-size: 15px; font-weight: 500; max-width: 900px; }'
    '@media (max-height: 820px) { .tt-hero { padding: 12px 20px; } .tt-h1 { font-size: 26px !important; } .tt-goldrule { margin: 7px 0 6px; } }'
    '@media (max-width: 768px) { .tt-h1 { font-size: 24px !important; } .tt-htag { font-size: 13.5px; } .tt-hero { padding: 12px 16px; }'
    '  .tt-chalk text { display: none; } }'
    '@media (max-width: 768px) { .q-card.tt-card { padding: 0 !important; } }'
    # button toggles: deep blue with a gold line under the chosen one
    '.tt-us.q-btn-group { border: 1px solid #33465C !important; }'
    '.tt-us .q-btn.bg-ttus { background: #1F4A75 !important; box-shadow: inset 0 -3px 0 #F6C510; }'
    # switches: gold when on
    '.q-toggle__inner--truthy .q-toggle__track { background: #F6C510 !important; opacity: .9 !important; }'
    '.q-toggle__inner--truthy .q-toggle__thumb:after { background: #FFFFFF !important; }'
    '.q-toggle__inner--truthy { color: #F6C510 !important; }'
    '.q-expansion-item { border-radius: 12px !important; }'
    'body .q-btn.tt-goldbtn.tt-goldbtn { background: linear-gradient(180deg, #FFD84A, #F6C510) !important; color: #0C2036 !important;'
    '  min-height: 40px; font-weight: 700; box-shadow: 0 4px 14px rgba(246,197,16,.22); }'
    'body .q-btn.tt-goldbtn.tt-goldbtn .q-icon, body .q-btn.tt-goldbtn.tt-goldbtn .q-btn__content { color: #0C2036 !important; }'
    # stat tiles: a coloured line on top, the number big
    '.tt-tiles.nicegui-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }'
    '@media (min-width: 900px) { .tt-tiles.nicegui-grid { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)) !important; } }'
    '.tt-tile { background: #1B2230; border: 1px solid #2A3647; border-top: 4px solid #24782E; border-radius: 12px;'
    '  padding: 10px 14px 12px; box-shadow: 0 1px 2px rgba(0,0,0,.2), 0 4px 14px rgba(0,0,0,.12); min-width: 0; }'
    '.tt-tile:nth-child(even) { border-top-color: #F6C510; }'
    '.tt-tile .text-sm.font-semibold, .tt-tilev { font-family: Oswald, sans-serif !important; font-size: 22px !important;'
    '  font-weight: 600 !important; line-height: 1.25; }'
    # Auto-Solver: one option on the left, the list of options on the right
    '.tt-as-res.nicegui-grid { grid-template-columns: minmax(0, 1fr) !important; }'
    '@media (min-width: 1100px) { .tt-as-res.nicegui-grid { grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr) !important; } }'
    '@media (min-width: 1100px) { .tt-optcol { position: sticky; top: 12px; } }'
    '.tt-optlist-h { font-family: Oswald, sans-serif; font-weight: 600; font-size: 15px; letter-spacing: .08em; text-transform: uppercase; color: #9FB0C3; }'
    '.tt-optitem { border: 1px solid #2A3647; border-radius: 10px; padding: 9px 12px; transition: border-color .15s, background .15s; }'
    '.tt-optitem:hover { border-color: #3A5068; background: rgba(255,255,255,.03); }'
    '.tt-optitem-on { border-color: #F6C510 !important; box-shadow: 0 0 0 2px rgba(246,197,16,.18); }'
    '.tt-optnum { width: 26px; height: 26px; border-radius: 50%; background: #24312A; color: #CFE3CC; display: grid; place-items: center;'
    '  font-family: Oswald, sans-serif; font-weight: 700; font-size: 13px; flex-shrink: 0; }'
    '.tt-optitem-on .tt-optnum { background: #F6C510; color: #0C2036; }'
    '.tt-optstar { margin-left: auto; color: #F6C510; font-size: 15px; letter-spacing: 1px; flex-shrink: 0; cursor: help; }'
    '.tt-optt { line-height: 1.25; } .tt-opts { line-height: 1.25; }'
    '.q-card.tt-hidecard { display: none !important; }'
    # solver diagnostics tiles: label on top (one line), the number big, details small
    '.tt-tiles.nicegui-grid { align-items: stretch !important; }'
    '.tt-dlab { font-size: 12px; font-weight: 600; color: #9FB0C3; text-transform: uppercase; letter-spacing: .06em;'
    '  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }'
    '.tt-dval { font-family: Oswald, sans-serif !important; font-size: 28px !important; font-weight: 600 !important; color: #FFFFFF;'
    '  line-height: 1.2; margin: 2px 0 2px; }'
    '.tt-dsub { font-size: 12.5px; color: #9FB0C3; line-height: 1.35; }'
    '.tt-dgold { color: #F6C510 !important; font-weight: 600; }'
    '.tt-pbar { background: #19202B; border: 1px solid #2A3647; border-radius: 12px; padding: 10px 14px; }'
    # pills in the page header (quick switches)
    '.q-btn.tt-pill { border: 1px solid rgba(255,255,255,.35) !important; border-radius: 999px !important; color: #FFFFFF !important;'
    '  background: transparent !important; padding: 0 14px; min-height: 32px; font-weight: 500; font-size: 14px; }'
    '.q-btn.tt-pill:hover { border-color: #F6C510 !important; }'
    '.q-btn.tt-pill.tt-pill-on { background: #F6C510 !important; border-color: #F6C510 !important; color: #0C2036 !important; font-weight: 600; }'
    # forms with the label above the box (title case, not inside the box)
    '.tt-ftop .q-field { padding-top: 21px; }'
    '.tt-ftop .q-field:not(.q-textarea):not(.q-select--multiple) .q-field__label,'
    '.tt-ftop .q-field:not(.q-textarea):not(.q-select--multiple).q-field--float .q-field__label { top: -21px !important; left: -14px !important; transform: none !important;'
    '  font-size: 12.5px !important; text-transform: none !important; letter-spacing: 0 !important; color: #9FB0C3 !important;'
    '  font-weight: 500 !important; overflow: visible; }'
    '.tt-ftop .q-field:not(.q-textarea):not(.q-select--multiple).q-field--labeled .q-field__native,'
    '.tt-ftop .q-field:not(.q-textarea):not(.q-select--multiple).q-field--labeled .q-field__input { padding-top: 0 !important; min-height: 40px !important; }'
    '.tt-ftop .q-field:not(.q-textarea):not(.q-select--multiple) .q-field__control,'
    '.tt-ftop .q-field:not(.q-textarea):not(.q-select--multiple) .q-field__marginal { height: 40px !important; min-height: 40px !important; }'
    '.tt-ftop .q-field__control { border-radius: 8px !important; background: #1F2733 !important; }'
    '.tt-ftop .q-field--outlined .q-field__control:before { border-color: #33465C !important; border-radius: 8px !important; }'
    '.tt-ftop .q-field__control-container, .tt-ftop .q-field__control { overflow: visible !important; }'
    '.q-btn.tt-ghost { border: 1px solid #3A4B60 !important; color: #E7EEF6 !important; background: transparent !important; }'
    '.q-btn.tt-ghost:hover { border-color: #F6C510 !important; }'
    '.tt-cbadge { width: 28px; height: 28px; border-radius: 50%; background: #F6C510; display: inline-grid; place-items: center;'
    '  font-size: 14px; flex-shrink: 0; color: #0C2036; }'
    # labels above the boxes everywhere (not in the lineup slots, tables or the compact skill boxes)
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) { padding-top: 21px; }'
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) .q-field__label {'
    '  top: -21px !important; left: -14px !important; transform: none !important; font-size: 12.5px !important;'
    '  text-transform: none !important; letter-spacing: 0 !important; color: #9FB0C3 !important; font-weight: 500 !important;'
    '  max-width: none !important; overflow: visible; }'
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) .q-field__native,'
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) .q-field__input,'
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) .q-field__prefix,'
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) .q-field__suffix'
    '  { padding-top: 0 !important; }'
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) .q-field__control-container,'
    'body .q-field--labeled:not(.q-textarea):not(.q-select--multiple):not(.tt-slot .q-field):not(.q-table .q-field):not(.tt-flabel-in .q-field) .q-field__control'
    '  { overflow: visible !important; }'
    'body .q-field--outlined .q-field__control { border-radius: 8px !important; }'
    'body .q-field--outlined .q-field__control:before { border-color: #33465C !important; border-radius: 8px !important; }'
    'body .q-field--outlined .q-field__control { background: #1F2733 !important; }'
    # outline buttons: light text with a quiet border, gold on hover
    '.q-btn--outline { color: #E7EEF6 !important; }'
    '.q-btn--outline:before { border-color: #3A4B60 !important; }'
    '.q-btn--outline:hover:before { border-color: #F6C510 !important; }'
    '.tt-otitle { font-family: Oswald, sans-serif; font-weight: 600 !important; font-size: 17px; letter-spacing: .02em;'
    '  border-bottom: 2px solid rgba(246,197,16,.55); }'
    '</style>')


def form_stamina_color(v):
    """Form / stamina colour by level (same in every page): 1 red, 2 brown, 3-4 orange, 5-6 yellow, 7+ green."""
    lv = int(float(v or 0))
    return ('#B23B3B' if lv <= 1 else '#8B5A2B' if lv == 2 else '#D9822B' if lv <= 4
            else '#C9A227' if lv <= 6 else FORM_GREEN)

DARK_CSS = f'''
<style>
body {{ background-color: #0E1117 !important; color: #FAFAFA !important; }}
.nicegui-content {{ background-color: #0E1117; }}
.q-card {{ background-color: #1C1C24 !important; border: 1px solid #3B3B4D !important; }}
.q-field__control {{ background-color: #262730 !important; border-radius: 8px !important; }}
.q-field__native, .q-field__input {{ font-size: 15px !important; font-weight: 500 !important; }}
.q-field__label {{ font-size: 13px !important; color: #D3D5DC !important; }}
.q-field--outlined .q-field__control:before {{ border-color: #3B3B4D !important; }}
.q-table {{ background-color: #1C1C24 !important; color: #FAFAFA !important; }}
.q-table th {{ color: #A6A6B0 !important; }}
.q-btn {{ border-radius: 8px !important; }}
.q-btn--flat {{ justify-content: flex-start !important; }}
.q-btn--flat .q-btn__content {{ justify-content: flex-start !important; }}
.nav-btn .q-btn__content {{ justify-content: flex-start !important; flex-wrap: nowrap !important; }}
.nav-btn {{ height: 40px !important; min-height: 40px !important; }}
.nav-btn .q-btn__content {{ white-space: nowrap !important; overflow: hidden !important; }}
.nav-btn .block {{ overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; display: block !important; }}
.q-uploader__header {{ background-color: #262730 !important; color: #FAFAFA !important; }}
.q-uploader {{ background-color: #1C1C24 !important; border: 1px solid #3B3B4D !important; border-radius: 8px !important; }}
.q-uploader__list {{ background-color: #1C1C24 !important; }}
.q-checkbox__label {{ font-size: 14px !important; }}

/* Mobile: hide sidebar by default, show hamburger */
@media (max-width: 768px) {{
  .q-drawer {{ width: 280px !important; }}
  .q-page-container {{ padding-left: 0 !important; }}
  .mobile-hamburger {{ display: flex !important; }}
  .mobile-hide {{ display: none !important; }}
  /* Make tables scrollable horizontally */
  .q-table__container {{ overflow-x: auto !important; }}
  /* Larger touch targets */
  .q-btn {{ min-height: 40px !important; }}
  .q-field {{ margin-bottom: 8px !important; }}
  /* Reduce page padding on mobile */
  .nicegui-content {{ padding: 8px !important; }}
  /* Larger text in cards on mobile */
  .q-card {{ padding: 12px !important; }}
  /* Make number inputs easier to tap */
  .q-field__control {{ min-height: 48px !important; }}
  /* Stack page header */
  .text-3xl {{ font-size: 1.5rem !important; }}
}}
@media (min-width: 769px) {{
  .mobile-hamburger {{ display: none !important; }}
}}
</style>
'''

NAV_PAGES = [
    ('/import', '📥 Import Players'),
    ('/', '⚽ Subskill Estimator'),
    ('/autosolver', '⚡ Subskill Auto-Solver'),
    ('/training', '🏋️ Training Planner'),
    ('/lineup', '📋 Match Ratings & Lineup Calculator'),
    ('/predictor', '🎯 Score Predictor'),
    ('/tstc', '📈 Team Spirit & Confidence'),
    ('/boxplot', '📦 Boxplot (BETA)'),
    ('/config', '🌐 Country Target Skills Config'),
    ('/reference', '🗄️ Reference Player Database'),
    ('/roster', '📊 Roster Overview'),
    ('/users', '👥 Account & User Management'),
]


LOGO_SVG = None   # built below, after logo_svg() (the login page logo)
SIDEBAR_LOGO_SVG = f'''
<div style="text-align:center; padding: 4px 0 10px 0;">
  <svg width="44" height="44" viewBox="0 0 250 250" xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;">
    <circle cx="125" cy="120" r="110" fill="#0E1117" stroke="{ACCENT}" stroke-width="8"/>
    <circle cx="125" cy="120" r="95" fill="none" stroke="#FAFAFA" stroke-width="3" stroke-dasharray="8,8"/>
    <circle cx="125" cy="120" r="80" fill="#1C1C24" stroke="{ACCENT}" stroke-width="3"/>
    <circle cx="125" cy="50" r="24" fill="#FAFAFA"/>
    <path d="M125 35 L133 46 L130 58 L120 58 L117 46 Z" fill="#0E1117"/>
    <path d="M125 35 L125 26 M133 46 L145 42 M130 58 L138 70 M120 58 L112 70 M117 46 L105 42" stroke="#0E1117" stroke-width="2.5"/>
    <g transform="rotate(45, 125, 125)">
       <rect x="117" y="65" width="16" height="110" fill="{ACCENT}" rx="4"/>
       <circle cx="125" cy="65" r="18" fill="{ACCENT}"/>
       <circle cx="125" cy="57" r="10" fill="#1C1C24"/>
       <circle cx="125" cy="175" r="14" fill="{ACCENT}"/>
    </g>
    <g transform="rotate(-45, 125, 125)">
       <rect x="119" y="80" width="12" height="80" fill="#FAFAFA" rx="2"/>
       <path d="M119 80 L125 55 L131 80 Z" fill="{ACCENT}"/>
       <rect x="116" y="160" width="18" height="25" fill="{ACCENT}" rx="3"/>
    </g>
    <rect x="45" y="110" width="35" height="45" fill="#0E1117" stroke="{ACCENT}" stroke-width="2.5" rx="3"/>
    <rect x="50" y="115" width="25" height="10" fill="{ACCENT}"/>
    <rect x="50" y="130" width="6" height="6" fill="#FAFAFA"/>
    <rect x="59" y="130" width="6" height="6" fill="#FAFAFA"/>
    <rect x="68" y="130" width="6" height="6" fill="#FAFAFA"/>
    <rect x="50" y="140" width="6" height="6" fill="#FAFAFA"/>
    <rect x="59" y="140" width="6" height="6" fill="#FAFAFA"/>
    <rect x="68" y="140" width="6" height="6" fill="#FAFAFA"/>
    <rect x="170" y="110" width="35" height="45" fill="#0E1117" stroke="#FAFAFA" stroke-width="2.5" rx="3"/>
    <path d="M175 120 L180 125 L188 115" fill="none" stroke="{ACCENT}" stroke-width="2"/>
    <path d="M175 132 L180 137 L188 127" fill="none" stroke="{ACCENT}" stroke-width="2"/>
    <path d="M175 144 L180 149 L188 139" fill="none" stroke="{ACCENT}" stroke-width="2"/>
    <line x1="192" y1="120" x2="200" y2="120" stroke="#FAFAFA" stroke-width="2"/>
    <line x1="192" y1="132" x2="200" y2="132" stroke="#FAFAFA" stroke-width="2"/>
    <line x1="192" y1="144" x2="200" y2="144" stroke="#FAFAFA" stroke-width="2"/>
    <path d="M 15 170 Q 125 200 235 170 L 230 215 Q 125 240 20 215 Z" fill="{ACCENT}" stroke="#0E1117" stroke-width="4"/>
    <path d="M 22 177 Q 125 203 228 177 L 224 210 Q 125 233 26 210 Z" fill="{ACCENT}"/>
    <text x="125" y="210" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-weight="900" font-size="38" fill="#FAFAFA" stroke="#0E1117" stroke-width="6" paint-order="stroke" letter-spacing="1">Tooltrick</text>
    <text x="125" y="210" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-weight="900" font-size="38" fill="#FAFAFA" letter-spacing="1">Tooltrick</text>
  </svg>
  <div style="font-size:14px; font-weight:800; color:#FAFAFA; letter-spacing:0.5px; margin-top:2px;">TOOLTRICK</div>
</div>
'''


def metric_color(delta, tolerance):
    """Green when within tolerance of target (matching/close), red otherwise —
    color-coded feedback showing how close a calculated value is to target."""
    return ACCENT if abs(delta) < tolerance else '#F87171'


# Shared card style (Score Predictor / Lineup Simulator look): a header strip in the accent colour,
# small uppercase section titles, and button toggles whose selected button shows the accent colour.
TT_CSS = (
    f'<style>'
    f'.tt-us.q-btn-group {{ border: 1px solid {ACCENT}; border-radius: 8px; overflow: hidden; }}'
    f'.tt-us .q-btn {{ color: #B8BCC8; background: #1F2029; padding: 2px 10px; }}'
    f'.tt-us .q-btn.bg-ttus {{ background: {ACCENT} !important; color: #FFFFFF !important; font-weight: 600; }}'
    # Switches: clearly green when on, grey when off.
    f'.q-toggle__inner--truthy .q-toggle__track {{ background: #22C55E !important; opacity: 0.85 !important; }}'
    f'.q-toggle__inner--truthy .q-toggle__thumb:after {{ background: #FFFFFF !important; }}'
    f'.q-toggle__inner--falsy .q-toggle__track {{ background: #4B5563 !important; opacity: 0.8 !important; }}'
    f'.q-toggle__inner--falsy .q-toggle__thumb:after {{ background: #9CA3AF !important; }}'
    f'</style>')


# Input boxes (v2.8.0 look): 44px high, 6px corners, a soft border and shadow, small grey capital labels
# inside the box and a blue glow on the box you type in. On wider screens the boxes in forms are narrower,
# with more room between them. Text areas and multi-selects keep growing with their content.
_F = '.q-field:not(.q-textarea):not(.q-select--multiple)'
FIELD_CSS = (
    '<style>'
    '.q-field__control { border-radius:6px !important; background:linear-gradient(180deg,#1E2029,#1A1C24) !important;'
    '  box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 1px 3px rgba(0,0,0,.35) !important;'
    '  padding-left:14px !important; padding-right:12px !important; transition: box-shadow .15s; }'
    '.q-field--outlined .q-field__control:before { border:1px solid #3A3F52 !important; border-radius:6px !important; }'
    '.q-field--outlined .q-field__control:after { border-radius:6px !important; }'
    '.q-field--outlined:hover .q-field__control:before { border-color:#2F6EA8 !important; }'
    'body .q-field.q-field--focused .q-field__control { box-shadow: 0 0 0 3px rgba(47,110,168,.30), 0 1px 3px rgba(0,0,0,.35) !important; }'
    '.q-field--outlined.q-field--focused .q-field__control:after { border:1px solid #6AA3D6 !important; }'
    '.q-field__label { font-size:11px !important; text-transform:uppercase; letter-spacing:.06em;'
    '  color:#8A94A6 !important; font-weight:600 !important; }'
    '.tt-swbox { height:44px; display:flex; align-items:center; padding:0 12px; border:1px solid #3A3F52; border-radius:6px;'
    '  background:linear-gradient(180deg,#1E2029,#1A1C24); box-sizing:border-box; }'
    '.tt-gridbtn.q-btn { height:44px; max-width:220px; }'
    '.tt-swbox { max-width:220px; white-space:nowrap; }'
    '.q-field__native, .q-field__input { font-size:14px !important; box-sizing:border-box !important; line-height:1.3 !important; }'
    '.q-field--labeled .q-field__control-container { padding-top:0 !important; }'
    '.q-select .q-field__input { padding-top:0 !important; min-height:0 !important; height:auto !important; }'
    '.q-select:not(.q-select--multiple) .q-field__native { flex-wrap:nowrap !important; align-items:center !important; }'
    '.q-field--with-bottom { padding-bottom:4px !important; }'
    + _F + ' .q-field__control, ' + _F + ' .q-field__marginal { height:44px !important; min-height:44px !important; }'
    + _F + '.q-field--labeled .q-field__native, ' + _F + '.q-field--labeled .q-field__input, '
    + _F + '.q-field--labeled .q-field__suffix, ' + _F + '.q-field--labeled .q-field__prefix'
    '  { padding-top:15px !important; padding-bottom:0 !important; min-height:44px !important; }'
    + _F + '.q-select.q-field--labeled .q-field__input { padding-top:0 !important; min-height:0 !important; }'
    + _F + ' .q-field__label { top:12px !important; }'
    + _F + '.q-field--float .q-field__label { transform: translateY(-8px) scale(.85) !important; }'
    '.q-btn, .q-btn-group, .q-btn-toggle, .q-uploader, .q-menu, .q-card, .q-expansion-item { border-radius:6px !important; }'
    '.tt-spec { background:#F59E0B !important; opacity:1 !important; }'
    '@media (min-width: 769px) {'
    '  .nicegui-grid:has(> .q-field) { column-gap:44px !important; row-gap:24px !important; align-content:start !important; }'
    '  .nicegui-grid > .q-field:not(.q-textarea), .nicegui-grid > .nicegui-row > .q-field:not(.q-textarea) { max-width:220px !important; }'
    '  .nicegui-row:has(> .q-field) { column-gap:24px !important; }'
    '  .nicegui-row > .q-field.flex-1 { max-width:400px !important; }'
    '}'
    '</style>')


def _split_icon(title):
    """'📊 Skills' -> ('📊', 'Skills'): a leading emoji goes into the gold circle of the card header."""
    t = str(title or '')
    head, _, rest = t.partition(' ')
    if rest and head and not any(ch.isalnum() for ch in head):
        return head, rest
    return '', t


@contextmanager
def tt_card(title, subtitle=None, classes='w-full mb-4'):
    """A card with the accent header strip; yields the padded body column."""
    icon, text = _split_icon(title)
    with ui.card().classes(f'{classes} p-0 gap-0 overflow-hidden tt-card'):
        with ui.element('div').classes('w-full px-4 pt-3 pb-2 tt-chead'):
            with ui.row().classes('items-center gap-3 no-wrap'):
                if icon:
                    ui.html(f'<span class="tt-cbadge">{icon}</span>')
                with ui.column().classes('gap-0 min-w-0'):
                    ui.label(text).classes('tt-ctitle')
                    if subtitle:
                        ui.label(subtitle).classes('text-xs').style('color: #C6D8EC;')
        with ui.column().classes('w-full px-4 pt-3 pb-4 gap-2') as body:
            yield body


@contextmanager
def player_card(title, name=None, info=None, links=None, classes='w-full mb-4'):
    """Like tt_card, but with the player in the blue header (as in the Estimator): his name, a line such as
    'NCD · 🇵🇱 Poland' and links on the right. Without a player it shows the plain title."""
    with ui.card().classes(f'{classes} p-0 gap-0 overflow-hidden tt-card'):
        with ui.row().classes('w-full items-center justify-between gap-2 px-4 py-2 tt-chead'):
            with ui.row().classes('items-center gap-3'):
                if name:
                    ui.label(name).classes('text-lg font-semibold text-white').style('font-family: Oswald, sans-serif; font-size: 20px;')
                    if info:
                        ui.label(info).classes('text-sm text-white')
                else:
                    ui.label(title).classes('tt-ctitle')
            if links:
                with ui.row().classes('gap-4 items-center'):
                    for text, url in links:
                        ui.link(text, url, new_tab=True).classes('text-sm').style('color:#FAFAFA !important;')
        with ui.column().classes('w-full px-4 pt-3 pb-4 gap-2') as body:
            yield body


def opt_panel(icon, title):
    """A small option panel (soft background, accent title); use as a context manager."""
    col = ui.column().classes('gap-1 p-3 rounded-lg w-full').style(
        f'background:{ACCENT_SOFT}; border:1px solid rgba(47,110,168,0.35);')
    with col:
        ui.label(f'{icon} {title}').classes('text-xs font-bold uppercase').style(f'color:{ACCENT}; letter-spacing:0.12em;')
    return col


def opt_hint(text):
    """A grey one-line hint under a switch in an option panel."""
    return ui.label(text).classes('text-xs text-gray-400 leading-tight -mt-1 ml-10')


def tt_section(name):
    ui.label(name).classes('text-xs font-bold uppercase mt-1').style(f'color: {ACCENT}; letter-spacing: 0.12em;')


def apply_theme():
    ui.add_head_html(DARK_CSS)
    ui.add_head_html(TT_CSS)
    ui.add_head_html(FIELD_CSS)
    ui.add_head_html(FONT_CSS)
    ui.add_head_html(BLUE_CSS)
    try:   # Hattrick specialty icons (spec_icons.py)
        import spec_icons
        ui.add_head_html(spec_icons.CSS)
    except ImportError:
        pass
    ui.colors(primary=ACCENT, dark='#0E1117')
    ui.dark_mode().enable()
    # Outlined style: a clear bordered box with the label cut into the top
    # border when floated, instead of Quasar's default underline style —
    # avoids the label/value overlap issue entirely, no custom height math needed.
    ui.input.default_props('outlined')
    ui.number.default_props('outlined')
    ui.select.default_props('outlined')
    ui.textarea.default_props('outlined')


def _logout():
    """Log out, but keep the language for the login page."""
    keep = i18n.lang()
    app.storage.user.clear()
    app.storage.user['lang'] = keep


def lang_flags(username=None):
    """🇬🇧 / 🇳🇱: switch the app language (stored with the account, so it follows you to every device)."""
    cur = i18n.lang()

    def pick(code):
        if code != cur:
            i18n.set_lang(code, username)
            ui.navigate.reload()
    with ui.row().classes('gap-1 items-center no-wrap'):
        for code, flag in i18n.LANGS.items():
            ui.button(flag, on_click=lambda c=code: pick(c)).props('flat dense round size=sm') \
                .style('font-size: 18px; min-width: 30px; ' + ('opacity: 1; background: rgba(255,255,255,.18);' if code == cur
                                                               else 'opacity: .55;')) \
                .tooltip({'en': 'English', 'nl': 'Nederlands'}[code])


def require_login():
    """Returns the logged-in username, or None (and renders the login form)."""
    user = app.storage.user.get('username')
    if user:
        return user

    with ui.column().classes('absolute-center items-center w-full px-4'):
        with ui.card().classes('w-full max-w-sm p-6'):
            ui.html('<div style="display:flex;flex-direction:column;align-items:center;padding:6px 0 12px">'
                    + logo_svg(84, 'login') + '<div style="font-size:26px;margin-top:10px;line-height:1">' + WORDMARK + '</div>'
                    '<div style="font-size:10px;color:#8FA3BA;letter-spacing:2px;text-transform:uppercase;margin-top:4px">'
                    'Hattrick Toolkit</div></div>').classes('w-full')
            with ui.row().classes('w-full justify-center'):
                lang_flags()
            ui.label('Sign in to continue').classes('text-sm text-center w-full text-gray-400 mb-4')
            username = ui.input('Username').classes('w-full')
            password = ui.input('Password', password=True).classes('w-full')
            error_label = ui.label('').classes('text-red-400 text-sm')

            def do_login():
                if verify_user(username.value, password.value):
                    app.storage.user['username'] = username.value.strip()
                    record_login(username.value.strip())
                    try:   # the language this user chose before (English when none)
                        from data_layer import get_user_pref
                        i18n.set_lang(get_user_pref(username.value.strip(), 'lang', i18n.lang()) or 'en')
                    except Exception:
                        pass
                    ui.navigate.to('/')
                else:
                    error_label.set_text('Invalid username or password.')

            password.on('keydown.enter', lambda: do_login())
            ui.button('🔑 Log In', on_click=do_login).classes('w-full mt-2')
            ui.label('App made by Onkruud · v2.9.1').classes('text-xs text-center w-full text-gray-500 mt-4')
            if available_manuals():
                with ui.row().classes('w-full justify-center gap-4 mt-1'):
                    for label, url in available_manuals():
                        ui.link(label, url, new_tab=True).classes('text-xs').style(f'color: {ACCENT};')
    return None


# User manuals (PDF), served from the "manuals" folder next to the app files.
MANUAL_DIR = Path(__file__).parent / 'manuals'
MANUALS = [('📘 Manual (English)', 'Tooltrick_manual_EN.pdf'),
           ('📗 Handleiding (Nederlands)', 'Tooltrick_manual_NL.pdf')]
# Always serve the folder (created if missing), so PDFs put there later show up after a page refresh.
try:
    MANUAL_DIR.mkdir(exist_ok=True)
except OSError:
    pass
if MANUAL_DIR.is_dir():
    app.add_static_files('/manuals', str(MANUAL_DIR))


def _manual_file(name):
    """The manual file: the exact name, or the newest download of it ('Tooltrick_manual_EN (1).pdf')."""
    exact = MANUAL_DIR / name
    if exact.is_file():
        return exact.name
    stem = name[:-4]
    try:
        found = sorted(MANUAL_DIR.glob(stem + '*.pdf'), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        found = []
    return found[0].name if found else None


def available_manuals():
    """(label, url) of the manuals that are really there."""
    from urllib.parse import quote
    out = []
    for label, f in MANUALS:
        real = _manual_file(f)
        if real:
            out.append((label, '/manuals/' + quote(real)))
    return out


def render_db_status_badge():
    # get_db_connection() only sets DB_STATUS once it's actually been called —
    # trigger one cheap call so the badge reflects reality on first render too.
    try:
        get_db_connection().close()
    except Exception:
        pass
    backend = DB_STATUS.get('backend', 'unknown')
    if backend == 'turso':
        with ui.row().classes('items-center gap-1 mb-3'):
            ui.icon('cloud_done', color=ACCENT).classes('text-sm')
            ui.label('Connected: Database').classes('text-xs text-gray-300')
    elif 'turso failed' in backend:
        with ui.row().classes('items-center gap-1 mb-1'):
            ui.icon('cloud_off', color='#F87171').classes('text-sm')
            ui.label('Database connection failed — using local backup').classes('text-xs text-red-400')
        ui.label(DB_STATUS.get('detail', '')).classes('text-xs text-gray-500 mb-3').style('word-break: break-word;')
    else:
        with ui.row().classes('items-center gap-1 mb-3'):
            ui.icon('storage', color='#A6A6B0').classes('text-sm')
            ui.label('Connected: Local Database').classes('text-xs text-gray-400')


# Menu groups: (section, [(href, icon, short label)]) — every page from NAV_PAGES, grouped.
NAV_GROUPS = [
    ('Players', [('/import', '📥', 'Import players'), ('/', '⚽', 'Subskill Estimator'), ('/autosolver', '⚡', 'Auto-Solver'),
                 ('/training', '🏋️', 'Training planner'), ('/roster', '📊', 'Roster'), ('/reference', '🗄️', 'Reference database')]),
    ('Match', [('/lineup', '📋', 'Lineup Simulator'), ('/predictor', '🎯', 'Score Predictor'),
               ('/tstc', '📈', 'Team spirit & confidence'), ('/boxplot', '📦', 'Boxplot (BETA)')]),
    ('Settings', [('/config', '🌐', 'Country target skills'), ('/users', '👥', 'Account & users')]),
]
NAV_CSS = (
    '<style>'
    # no rubber-band bounce when scrolling past the top/bottom with a trackpad (Mac)
    'html, body, .q-layout, .q-page-container, .q-drawer, .q-drawer__content, .tt-navcol { overscroll-behavior: none !important; }'
    # the logo bar and the page title band share one height, so their bottom lines run on
    ':root { --tt-headh: 70px; }'
    '.tt-head { height: var(--tt-headh) !important; padding-top: 0 !important; padding-bottom: 0 !important; box-sizing: border-box; }'
    '.tt-titlebar { display: flex; align-items: center; gap: 14px; height: var(--tt-headh); position: relative; margin-bottom: 8px; }'
    '.tt-titlebar:before { content: ""; position: absolute; top: 0; bottom: 0; left: -100vw; right: -100vw; z-index: 0;'
    '  background: linear-gradient(180deg, #161925, #12141C); border-bottom: 1px solid #3A3F52; }'
    '.tt-titlebar > * { position: relative; z-index: 1; }'
    '.tt-titlebar .tt-tbar { width: 5px; height: 56%; border-radius: 3px; flex-shrink: 0; }'
    '.q-page-container { overflow-x: clip; }'
    '.tt-tsub { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-left: 14px; margin-left: 4px;'
    '  border-left: 1px solid #3A3F52; line-height: 1.3; }'
    '@media (max-width: 900px) { .tt-tsub { display: none; } }'
    '@media (min-width: 1024px) { .tt-titlebar { margin-top: -32px !important; } }'
    '@media (max-height: 895px) { :root { --tt-headh: 64px; } }'
    '@media (max-height: 820px) { :root { --tt-headh: 60px; } }'
    '@media (max-height: 740px) { :root { --tt-headh: 55px; } .tt-titlebar .text-3xl { font-size: 1.6rem !important; } }'
    # menu background: a touch lighter at the top than the page
    '.q-drawer { background: linear-gradient(180deg, #151822 0%, #0F1118 60%) !important; border-right: 1px solid #2F6EA8 !important; }'
    # the three groups as small cards
    '.tt-navgroup { background: linear-gradient(180deg,#191C27,#14161F); border: 1px solid #3A3F52; border-radius: 12px;'
    '  padding: 4px 8px 6px; margin-top: 8px; box-shadow: 0 2px 10px rgba(0,0,0,.30); width: 100%; box-sizing: border-box; }'
    '.tt-navsec { display: flex; align-items: center; gap: 8px; width: 100%; margin: 4px 2px 6px; color: #7D8798;'
    '  font-size: 10.5px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }'
    '.tt-navsec:after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, #2F6EA8, rgba(47,110,168,0)); }'
    # menu items: icon in a small tile, then the name
    '.tt-nav.q-btn { justify-content: flex-start !important; text-align: left; border-radius: 8px; padding: 2px 8px;'
    '  min-height: 36px; margin: 1px 0; border: 1px solid transparent; color: #C9CDD6 !important; font-size: 14px;'
    '  position: relative; transition: background .15s, border-color .15s; }'
    '.tt-nav.q-btn .q-btn__content { justify-content: flex-start; gap: 10px; flex-wrap: nowrap; }'
    '.tt-nav.q-btn.nav-btn { height: auto !important; }'   # the old fixed 40px nav-btn height would block the smaller sizes
    # row height follows the screen height: 13 rows share what is left after header, account card, titles and log out
    '.tt-nav.q-btn { min-height: clamp(24px, calc((100vh - 300px) / 13), 38px) !important; margin: 0 !important; }'
    '.tt-ico { width: clamp(20px, calc((100vh - 300px) / 13 - 9px), 28px) !important; height: clamp(20px, calc((100vh - 300px) / 13 - 9px), 28px) !important; }'
    '.tt-ico { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 8px;'
    '  background: #1C2030; border: 1px solid rgba(47,110,168,.55); font-size: 15px; flex-shrink: 0; transition: all .15s; }'
    '.tt-navtxt { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #C9CDD6; }'
    '.tt-nav-on .tt-navtxt { color: #FFFFFF; }'
    '.tt-logout.q-btn:hover .tt-navtxt { color: #FCA5A5; }'
    '.tt-nav.q-btn:hover { background: rgba(47,110,168,.08); border-color: rgba(47,110,168,.55); }'
    '.tt-nav.q-btn:hover .tt-ico { border-color: #6AA3D6; }'
    # the page you are on: blue tile with a soft glow, a light frame and a small dot
    '.tt-nav-on.q-btn { background: linear-gradient(90deg, rgba(47,110,168,.30), rgba(47,110,168,.08)) !important;'
    '  border-color: rgba(106,163,214,.45) !important; color: #FFFFFF !important; font-weight: 600;'
    '  box-shadow: 0 0 18px rgba(47,110,168,.18); }'
    '.tt-nav-on .tt-ico { background: linear-gradient(135deg, #1F4A75, #6AA3D6); border-color: #9CC3E6;'
    '  box-shadow: 0 0 10px rgba(106,163,214,.45); }'
    '.tt-nav-on.q-btn:after { content: ""; position: absolute; right: 8px; top: 50%; width: 6px; height: 6px; margin-top: -3px;'
    '  border-radius: 50%; background: #9CC3E6; box-shadow: 0 0 8px #9CC3E6; }'
    # account box: like the cards, with a ring around the letter and a green online dot
    '.tt-acc { background: linear-gradient(180deg,#1E2230,#181B26); border: 1px solid #3A3F52; border-radius: 10px;'
    '  box-shadow: 0 2px 8px rgba(0,0,0,.35); }'
    '.tt-av { position: relative; box-shadow: 0 0 0 2px #1E2230, 0 0 0 4px #6AA3D6; }'
    '.tt-av:after { content: ""; position: absolute; right: -2px; bottom: -2px; width: 10px; height: 10px; border-radius: 50%;'
    '  background: #34D399; border: 2px solid #1E2230; }'
    # log out: a card-style button with a red-tinted icon tile; red glow on hover
    '.tt-logout.q-btn { justify-content: flex-start !important; border-radius: 10px; min-height: 42px; padding: 4px 8px;'
    '  background: linear-gradient(180deg,#1C1F2B,#161922); border: 1px solid #3A3F52; color: #C9CDD6 !important;'
    '  box-shadow: 0 2px 8px rgba(0,0,0,.30); transition: all .15s; }'
    '.tt-logout.q-btn .q-btn__content { justify-content: flex-start; gap: 10px; flex-wrap: nowrap; width: 100%; }'
    '.tt-ico-out { background: rgba(248,113,113,.10) !important; border-color: rgba(248,113,113,.35) !important; color: #F87171; }'
    '.tt-logout-arrow { margin-left: auto; color: #4A5268; transition: all .15s; }'
    '.tt-logout.q-btn:hover { border-color: rgba(248,113,113,.55); background: linear-gradient(180deg,#2A1E24,#1E1820);'
    '  color: #FCA5A5 !important; box-shadow: 0 0 16px rgba(248,113,113,.15); }'
    '.tt-logout.q-btn:hover .tt-ico-out { background: rgba(248,113,113,.22) !important; }'
    '.tt-logout.q-btn:hover .tt-logout-arrow { color: #F87171; transform: translateX(2px); }'
    # shorter screens: the menu steps down in size so it never needs scrolling
    '@media (max-height: 895px) {'
    '  .tt-ico { font-size: 14px !important; }'
    '  .tt-navgroup { margin-top: 7px !important; padding: 3px 8px 5px !important; }'
    '  .tt-head { padding-top: 9px !important; padding-bottom: 9px !important; }'
    '  .tt-logout.q-btn { min-height: 40px !important; }'
    '}'
    '@media (max-height: 820px) {'
    '  .tt-navgroup { margin-top: 6px !important; padding: 2px 8px 4px !important; }'
    '  .tt-navsec { margin: 2px 2px 3px !important; }'
    '  .tt-head { padding-top: 7px !important; padding-bottom: 7px !important; }'
    '  .tt-acc { margin-top: 8px !important; padding-top: 5px !important; padding-bottom: 5px !important; }'
    '  .tt-logout.q-btn { min-height: 36px !important; }'
    '}'
    '@media (max-height: 740px) {'
    '  .tt-nav.q-btn { font-size: 13.5px !important; padding: 1px 8px !important; }'
    '  .tt-ico { font-size: 13px !important; border-radius: 6px !important; }'
    '  .tt-navgroup { margin-top: 5px !important; padding: 2px 6px 3px !important; border-radius: 10px !important; }'
    '  .tt-navsec { font-size: 9.5px !important; margin: 1px 2px 2px !important; }'
    '  .tt-logo svg { width: 36px !important; height: 36px !important; }'
    '  .tt-head { padding-top: 6px !important; padding-bottom: 6px !important; }'
    '  .tt-dbline { display: none !important; }'
    '  .tt-acc { padding-top: 4px !important; padding-bottom: 4px !important; }'
    '  .tt-av { width: 24px !important; height: 24px !important; font-size: 12px !important; }'
    '  .tt-logout.q-btn { min-height: 34px !important; }'
    '}'
    '@media (max-height: 650px) {'
    '  .tt-nav.q-btn { font-size: 13px !important; }'
    '  .tt-ico { font-size: 12px !important; }'
    '  .tt-navgroup { margin-top: 4px !important; padding: 1px 6px 2px !important; }'
    '  .tt-acc { margin-top: 5px !important; }'
    '  .tt-logout.q-btn { min-height: 30px !important; }'
    '}'
    '</style>')

# v2.9 menu: a deep-blue gradient, white text, line icons, and gold for the page you are on
NAV_BLUE_CSS = ('<style>'
    '.q-drawer { background: linear-gradient(180deg, #22344A 0%, #1A2331 35%, #14181F 100%) !important;'
    '  border-right: 1px solid rgba(255,255,255,.07) !important; }'
    '.tt-head { background: transparent !important; border-bottom: 1px solid rgba(255,255,255,.12); }'
    '.tt-navgroup { background: transparent !important; border: 0 !important; box-shadow: none !important; padding: 2px 2px 4px !important; }'
    '.tt-navsec { color: #9FB0C3 !important; font-family: Oswald, sans-serif; letter-spacing: .18em !important; }'
    '.tt-navsec:after { background: linear-gradient(90deg, rgba(255,255,255,.18), rgba(255,255,255,0)) !important; }'
    '.tt-nav.q-btn { color: #E7EEF6 !important; border-color: transparent !important; }'
    '.tt-navtxt { color: #E7EEF6 !important; font-weight: 500; }'
    '.tt-ico { background: rgba(255,255,255,.08) !important; border: 1px solid rgba(255,255,255,.10) !important; color: #D5E3F2; }'
    '.tt-ico svg { width: 16px; height: 16px; }'
    '.tt-nav.q-btn:hover { background: rgba(255,255,255,.07) !important; }'
    '.tt-nav.q-btn:hover .tt-ico { border-color: rgba(246,197,16,.55) !important; }'
    '.tt-nav-on.q-btn { background: rgba(246,197,16,.15) !important; border-color: transparent !important; box-shadow: inset 3px 0 0 #F6C510 !important; }'
    '.tt-nav-on .tt-ico { background: #F6C510 !important; border-color: #F6C510 !important; color: #0C2036 !important; box-shadow: none !important; }'
    '.tt-nav-on .tt-navtxt { color: #FFFFFF !important; font-weight: 600; }'
    '.tt-nav-on.q-btn:after { display: none !important; }'
    '.tt-acc { background: rgba(255,255,255,.07) !important; border: 1px solid rgba(255,255,255,.12) !important; box-shadow: none !important; }'
    '.tt-av { box-shadow: 0 0 0 2px #163A5E, 0 0 0 4px rgba(246,197,16,.6) !important; }'
    '.tt-av:after { border-color: #163A5E !important; }'
    '.tt-acc .text-gray-300, .tt-acc .text-gray-400 { color: #B7CCE3 !important; }'
    '.tt-logout.q-btn { background: rgba(255,255,255,.06) !important; border: 1px solid rgba(255,255,255,.12) !important; box-shadow: none !important; }'
    '.tt-logout.q-btn:hover { background: rgba(248,113,113,.14) !important; border-color: rgba(248,113,113,.55) !important; }'
    '.tt-logout-arrow { color: rgba(255,255,255,.4) !important; }'
    '</style>')


# Page headers: (icon, title, what the page is for). Titles match the menu.
PAGE_INFO = {
    '/import': ('📥', 'Import Players', 'Upload a Hattrick CSV, an App CSV/XLSX export or a .hrf file. Nothing is saved '
                'until you review the parsed players below and confirm.'),
    '/': ('⚽', 'Subskill Estimator', 'Enter a player\'s data and skills, and see his TSI, wage and HTMS.'),
    '/autosolver': ('⚡', 'Subskill Auto-Solver', 'Estimate a player\'s subskills from his TSI, wage, age and position.'),
    '/training': ('🏋️', 'Training Planner', 'See when a player reaches his next skill levels.'),
    '/roster': ('📊', 'Roster', 'All your players with every skill, ready to copy to the Hattrick forum.'),
    '/reference': ('🗄️', 'Reference Database', 'Real players with known skills, used as peers by the Auto-Solver.'),
    '/lineup': ('📋', 'Lineup Simulator', 'Build a lineup and see the match ratings it will get.'),
    '/predictor': ('🎯', 'Score Predictor', 'Compare two teams\' ratings and see the expected score and chances.'),
    '/tstc': ('📈', 'Team Spirit & Confidence Estimator', 'Plan attitudes and expected results, and see the team spirit and '
              'confidence you will have going into each match.'),
    '/boxplot': ('📦', 'Boxplot (BETA)', 'An average hides a lot. See how many goals a team really scores, match by match.'),
    '/config': ('🌐', 'Country Target Skills', 'The skill profile per position and age the solver aims at, per country.'),
    '/users': ('👥', 'Account & Users', 'Your password and roster, and (admin) the user accounts.'),
}


def page_title(href, subtitle=None):
    """The page header: a deep-blue band with a faint pitch, the menu group, a gold badge with the page icon,
    the title, a gold line and one line on what the page is for."""
    icon, title, sub = PAGE_INFO.get(href, ('', href, None))
    text = subtitle if subtitle is not None else sub
    group = next((sec for sec, items in NAV_GROUPS if any(h == href for h, _, _ in items)), '')
    with ui.element('div').classes('w-full tt-hero mt-12 md:mt-0') as hero:   # room for the phone menu button
        ui.html(CHALK_SVG).classes('tt-chalk-wrap').style('position:absolute; inset:0;')
        if group:
            ui.label(tr(group)).classes('tt-kicker')
        with ui.row().classes('items-center gap-3 no-wrap').style('margin-top: 4px;'):
            badge = ICONS.get(href)
            ui.html(f'<div class="tt-badge">{badge}</div>' if badge else f'<div class="tt-badge" style="font-size:20px">{icon}</div>')
            ui.label(title).classes('tt-h1')
        ui.element('div').classes('tt-goldrule')
        if text:
            ui.label(text).classes('tt-htag')
    return hero


def _logo_svg(size=46):
    """The Tooltrick logo at the given size."""
    return logo_svg(size, 'side')


def render_sidebar(current_user, active_href):
    ui.add_head_html(NAV_CSS)
    ui.add_head_html(NAV_BLUE_CSS)
    drawer = ui.left_drawer(fixed=True, bordered=True).classes('p-0').style('border-right: 1px solid rgba(255,255,255,.08); width: 280px')
    with drawer:
        with ui.column().classes('w-full h-full gap-0 no-wrap'):
            # Header strip: the logo, name and version
            with ui.row().classes('w-full items-center gap-3 no-wrap px-4 py-3 tt-head'):
                ui.html(_logo_svg(44)).classes('tt-logo')
                with ui.column().classes('gap-0 flex-grow'):
                    ui.html(WORDMARK).style('font-size: 20px; line-height: 1.1;')
                    ui.label('v2.9.1 · Hattrick Toolkit').classes('text-xs').style('color: #B7CCE3;')
                lang_flags(current_user)
                # Close button — only visible on mobile
                ui.button(icon='close', on_click=drawer.hide).props('flat round dense color=white') \
                    .classes('mobile-hamburger').style('opacity: 0.8')

            # Account card: who is logged in, and which database is connected
            with ui.row().classes('items-center gap-3 no-wrap mx-3 mt-3 mb-1 px-3 py-2 tt-acc').style(
                    'width: calc(100% - 24px);'):
                ui.label((str(current_user or '?')[:1] or '?').upper()).classes('font-bold text-sm tt-av').style(
                    f'background: {GOLD}; color: {NAVY}; width: 30px; height: 30px; border-radius: 50%; '
                    'display: flex; align-items: center; justify-content: center; flex-shrink: 0;')
                with ui.column().classes('gap-0 min-w-0'):
                    ui.label(str(current_user)).classes('text-sm font-semibold')
                    with ui.element('div').classes('text-xs tt-dbline').style('margin-bottom: -12px;'):
                        render_db_status_badge()

            # The pages, in three groups (each a small card)
            def nav_item(icon, label, on=False, on_click=None):
                btn = ui.button(on_click=on_click).props('flat no-caps align=left color=grey-4') \
                    .classes('w-full nav-btn tt-nav' + (' tt-nav-on' if on else ''))
                with btn:
                    ui.html(f'<span class="tt-ico">{icon}</span>')
                    ui.label(tr(label)).classes('tt-navtxt')
                return btn

            with ui.column().classes('w-full gap-0 px-3 pb-3 flex-grow tt-navcol').style('overflow-y: auto;'):
                for section, items in NAV_GROUPS:
                    with ui.element('div').classes('tt-navgroup'):
                        ui.label(section).classes('tt-navsec')
                        for href, icon, label in items:
                            nav_item(ICONS.get(href, icon), label, href == active_href, lambda h=href: ui.navigate.to(h))
                        if section == 'Settings' and available_manuals():
                            # Manuals: a small menu (English / Nederlands)
                            with nav_item(ICONS['manuals'], 'Manuals'):
                                with ui.menu().props('anchor="top right" self="top left"'):
                                    for m_label, url in available_manuals():
                                        ui.menu_item(m_label, on_click=lambda u=url: ui.navigate.to(u, new_tab=True))

            # Log out, always at the bottom
            with ui.element('div').classes('w-full px-3 py-2').style('border-top: 1px solid rgba(255,255,255,.10);'):
                with ui.button(on_click=lambda: (_logout(), ui.navigate.to('/'))).props('flat no-caps color=grey-4') \
                        .classes('w-full tt-logout'):
                    with ui.element('span').classes('tt-ico tt-ico-out'):
                        ui.icon('logout', size='17px')
                    ui.label(tr('Log out')).classes('tt-navtxt font-semibold')
                    ui.icon('chevron_right', size='18px').classes('tt-logout-arrow')

    # Hamburger button — only visible on mobile
    with ui.page_sticky(position='top-left', x_offset=8, y_offset=8):
        ui.button(icon='menu', on_click=drawer.toggle).props('flat round color=white').classes('mobile-hamburger').style('background: #1C1C24; border: 1px solid #3B3B4D;')


# ── Hattrick markup helpers (shared by predictor / TS-TC pages) ─────────────
def ht_row(cells, header=False):
    tag = 'th' if header else 'td'
    return '[tr]' + ''.join(f'[{tag}]{c}[/{tag}]' for c in cells) + '[/tr]'


def compact_tables(text):
    """Hattrick turns every line break into an empty line, and breaks inside a [table]
    end up as blank space above the table — so each table is written on one line."""
    return re.sub(r'\[table\].*?\[/table\]', lambda m: re.sub(r'\s*\n\s*', '', m.group(0)),
                  text, flags=re.S | re.I)


def copy_text(text, what):
    """Copy text to the user's clipboard (with a fallback for browsers without the Clipboard API)."""
    text = compact_tables(text)
    ui.run_javascript(f'''
        var text = {json.dumps(text)};
        navigator.clipboard.writeText(text).catch(() => {{
            const ta = document.createElement("textarea");
            ta.value = text; document.body.appendChild(ta); ta.select();
            document.execCommand("copy"); document.body.removeChild(ta);
        }});
    ''')
    ui.notify(f'📋 {what} copied ({len(text)} characters)', type='positive')


def markup_block(text, what, title='📋 Hattrick markup'):
    """Text preview with a copy button (same pattern as the Auto-Solver)."""
    if '[table]' in text.lower():
        text = compact_tables(text)
    with ui.row().classes('w-full items-center gap-2 mt-3'):
        ui.label(title).classes('text-xs text-gray-400')
        ui.button('📋 Copy', on_click=lambda: copy_text(text, what)).props('outline dense')
    ui.textarea(value=text).classes('w-full font-mono text-xs').props('rows=6 readonly outlined')