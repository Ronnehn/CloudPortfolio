"""English / Dutch for the whole app.

The app is written in English. When a user picks Dutch (the flag in the menu), every text the browser shows is
looked up in NL (i18n_nl.py) on its way out: labels, buttons, tooltips, field labels, drop-down options,
notifications and plain HTML text. The app's own logic keeps working with the English texts, so nothing else
has to change. Texts with numbers in them are matched with templates ('{}' = any value).
"""
import re
from nicegui import app, ui

LANGS = {'en': '🇬🇧', 'nl': '🇳🇱'}
DEFAULT_LANG = 'en'
_EXACT, _PATTERNS, _RAW, _EN = {}, [], {}, {}
_installed = False


def load():
    """(Re)build the lookup tables from i18n_nl.NL."""
    global _EXACT, _PATTERNS, _RAW, _EN
    try:
        from i18n_nl import NL
    except ImportError:
        NL = {}
    try:
        from i18n_nl import EN as _en
        _EN = dict(_en)
    except ImportError:
        _EN = {}
    _EXACT, _PATTERNS, _RAW = {}, [], dict(NL)
    for en, nl in NL.items():
        if '{}' in en:
            rx = re.compile('^' + re.escape(en).replace(r'\{\}', '(.*?)') + '$', re.S)
            _PATTERNS.append((rx, nl))
        else:
            _EXACT[en] = nl
    # longer templates first, so the most specific one wins
    _PATTERNS.sort(key=lambda p: -len(p[0].pattern))


def lang():
    try:
        return app.storage.user.get('lang', DEFAULT_LANG)
    except Exception:
        return DEFAULT_LANG


def set_lang(code, username=None):
    code = code if code in LANGS else DEFAULT_LANG
    try:
        app.storage.user['lang'] = code
    except Exception:
        pass
    if username:
        try:
            from data_layer import set_user_pref
            set_user_pref(username, 'lang', code)
        except Exception:
            pass


def _tr_nl(s):
    if s in _EXACT:
        return _EXACT[s]
    core = s.strip()
    if core != s and core in _EXACT:          # keep the spaces around it
        return s.replace(core, _EXACT[core])
    for rx, nl in _PATTERNS:
        m = rx.match(s)
        if m:
            parts = [_tr_nl(g) if g and re.search('[A-Za-z]{3}', g) else g for g in m.groups()]
            try:
                return nl.format(*parts)
            except (IndexError, KeyError):
                return s
    # a list ('more Winger, more Scoring, less Passing'): translate each part
    if ', ' in s:
        parts = s.split(', ')
        tp = [_tr_nl(p) for p in parts]
        if tp != parts:
            return ', '.join(tp)
    # an icon or symbol in front ('✗ ', '👤 ', '📋 '): translate the rest
    m = _LEAD.match(s)
    if m and m.group(2) and m.group(1):
        rest = _tr_nl(m.group(2))
        if rest != m.group(2):
            return m.group(1) + rest
    return s


_LEAD = re.compile(r'^([^A-Za-z0-9(\[\-]+)(.*)$', re.S)


def tr(s):
    """The text in the user's language (unchanged in English, or when there is no translation)."""
    if not isinstance(s, str) or not s:
        return s
    if lang() != 'nl':
        return _EN.get(s, s)      # a few Dutch column names shown as labels
    return _tr_nl(s)


_TAG_TEXT = re.compile(r'>([^<>]*[A-Za-z][^<>]*)<')


def tr_html(s):
    """Translate the text between the tags of a small HTML snippet."""
    if not isinstance(s, str):
        return s
    if lang() != 'nl':
        return _EN.get(s, s)
    if '<' not in s:
        return _tr_nl(s)

    def one(m):
        t = m.group(1)
        lead = t[:len(t) - len(t.lstrip())]; trail = t[len(t.rstrip()):]
        return '>' + lead + _tr_nl(t.strip()) + trail + '<'
    return _TAG_TEXT.sub(one, '>' + s + '<')[1:-1]     # also the text before the first / after the last tag


def trf(template, *values):
    """Translate a template with '{}' first, then fill in the values (for texts built in pieces, e.g. charts)."""
    t = _RAW.get(template, template) if lang() == 'nl' else template
    try:
        return t.format(*values)
    except (IndexError, KeyError):
        return template.format(*values)


def tr_list(items):
    return [tr(x) for x in items]


def install():
    """Hook the translation into NiceGUI once (at import of the app)."""
    global _installed
    if _installed:
        return
    _installed = True
    load()
    from nicegui.elements.mixins.text_element import TextElement
    from nicegui.elements.mixins.label_element import LabelElement
    from nicegui.elements.choice_element import ChoiceElement
    from nicegui.elements.html import Html
    import nicegui.elements.button as _btn
    import nicegui.elements.expansion as _exp

    # texts (label, switch, checkbox, tooltip, ...) and the classes that show their text as a 'label' prop
    for cls in {TextElement, _btn.Button, _exp.Expansion}:
        orig = cls.__dict__.get('_text_to_model_text')
        if orig is None:
            continue

        def patched(self, text, _orig=orig):
            _orig(self, tr(text))
        cls._text_to_model_text = patched
    try:
        import nicegui.elements.button_dropdown as _bd
        _o = _bd.DropdownButton._text_to_model_text
        _bd.DropdownButton._text_to_model_text = lambda self, text, _o=_o: _o(self, tr(text))
    except Exception:
        pass

    # field labels (input, number, select, ...)
    _li = LabelElement.__init__

    def label_init(self, *args, label=None, **kwargs):
        _li(self, *args, label=tr(label), **kwargs)
    LabelElement.__init__ = label_init
    _lc = LabelElement._handle_label_change
    LabelElement._handle_label_change = lambda self, label, _lc=_lc: _lc(self, tr(label))

    # drop-down / toggle options: values stay English, only the shown labels change
    _uo = ChoiceElement._update_options

    def update_options(self):
        _uo(self)
        if True:
            self._props['options'] = [dict(o, label=tr(o['label']) if isinstance(o.get('label'), str) else o.get('label'))
                                      for o in self._props.get('options', [])]
    ChoiceElement._update_options = update_options
    # the chosen option in a drop-down is sent with its label too
    from nicegui.elements.select import Select
    _vm = Select._value_to_model_value

    def value_to_model(self, value):
        mv = _vm(self, value)
        if lang() != 'nl':
            return mv
        fix = lambda o: dict(o, label=tr(o['label'])) if isinstance(o, dict) and isinstance(o.get('label'), str) else o
        return [fix(o) for o in mv] if isinstance(mv, list) else fix(mv)
    Select._value_to_model_value = value_to_model

    # plain HTML snippets (level words in the skill bars, the check chips, ...)
    _hc = Html._handle_content_change
    Html._handle_content_change = lambda self, content, _hc=_hc: _hc(self, tr_html(content))

    # small texts set as properties: field suffix / prefix / placeholder / hint
    from nicegui.props import Props
    _call = Props.__call__

    def props_call(self, add=None, *, remove=None):
        r = _call(self, add, remove=remove)
        if add and lang() == 'nl':
            for k in ('suffix', 'prefix', 'placeholder', 'hint'):
                v = self.get(k)
                if isinstance(v, str) and v:
                    t = tr(v)
                    if t != v:
                        self[k] = t
        return r
    Props.__call__ = props_call
    from nicegui.elements.input import Input
    _ii = Input.__init__

    def input_init(self, *args, placeholder=None, **kwargs):
        _ii(self, *args, placeholder=tr(placeholder), **kwargs)
    Input.__init__ = input_init

    # table column headers
    from nicegui.elements.table import Table
    _nc = Table._normalize_columns

    def normalize_columns(self, columns):
        cols = _nc(self, columns)
        if not cols:
            return cols
        return [dict(c, label=tr(c['label'])) if isinstance(c, dict) and isinstance(c.get('label'), str) else c for c in cols]
    Table._normalize_columns = normalize_columns

    # notifications
    _notify = ui.notify

    def notify(message, *args, **kwargs):
        return _notify(tr(message) if isinstance(message, str) else message, *args, **kwargs)
    ui.notify = notify