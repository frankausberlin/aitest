# HF Top Datasets UI - live Hugging Face API browser for datasets
from __future__ import annotations
import ipywidgets as widgets
from ipywidgets import Button, Box, Layout, Textarea
from IPython.display import display, HTML
from huggingface_hub import HfApi
import requests
from functools import lru_cache
from datetime import datetime
from typing import List, Dict, Any

class ButtonBox:
    def _clicker(self, b):
        self.position, self.button = [(i, but) for i, but in enumerate(self.buttons) if b == but][0]
        self.unselect()
        self.buttons[self.position].style = {'button_color': self.color}
        if self.clicker:
            self.clicker(self)

    def append(self, description, select=True):
        b = Button(
            description=description if len(description) <= self.maxchar else f'{description[:(self.maxchar-3)]}...',
            layout=Layout(width='auto', height='21px'),
            tooltip=f'{description}',
        )
        self.buttons.append(b)
        self.box.children = [*self.box.children, b]
        if select:
            self.button, self.position = b, len(self.buttons) - 1
            self._clicker(b)
        b.on_click(self._clicker)

    def remove(self, position=None):
        if position is None:
            position = self.position
        if position is None or not position < len(self.buttons) or position < 0:
            return
        self.box.children = [*self.box.children[:position], *self.box.children[position+1:]]
        self.buttons = [*self.buttons[:position], *self.buttons[position+1:]]
        self.button, self.position = None, -1

    def unselect(self):
        for b in self.buttons:
            b.style = {'button_color': None}

    def __init__(self, descriptions, clicker=None, maxchar=60, color='powderblue'):
        self.descriptions = descriptions if len(descriptions) == len(set(descriptions)) else list(set(descriptions))
        self.clicker, self.maxchar, self.color, self.position, self.button = clicker, maxchar, color, -1, None
        self.buttons = [
            Button(
                description=i if len(i) <= maxchar else f'{i[:(maxchar-3)]}...',
                layout=Layout(width='auto', height='21px'),
                tooltip=f'{i}',
            )
            for i in descriptions
        ]
        self.box = Box(layout=Layout(display='flex', flex_flow='wrap'), children=self.buttons)
        for button in self.buttons:
            button.on_click(self._clicker)

def _normalize_list(val):
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, dict):
        return list(val.values())
    if isinstance(val, list):
        return val
    return []

def _lower_flatten(items):
    out = []
    for x in items:
        if isinstance(x, dict):
            for v in x.values():
                if isinstance(v, str):
                    out.append(v.lower())
        elif isinstance(x, list):
            out.extend([str(y).lower() for y in x])
        else:
            out.append(str(x).lower())
    return list({*out})

def extract_tasks(card):
    c = card or {}
    return _lower_flatten(_normalize_list(c.get('task_categories') or c.get('task_ids') or c.get('tasks')))

def extract_languages(card):
    c = card or {}
    return _lower_flatten(_normalize_list(c.get('language') or c.get('languages') or c.get('langs')))

@lru_cache(maxsize=2048)
def cached_dataset_info(repo_id: str):
    api = HfApi()
    return api.dataset_info(repo_id)

def build_dataset_record(info):
    card = getattr(info, 'cardData', None)
    tasks = extract_tasks(card)
    langs = extract_languages(card)
    record = {
        'id': info.id,
        'downloads': getattr(info, 'downloads', None),
        'likes': getattr(info, 'likes', None),
        'last_modified': getattr(info, 'lastModified', None),
        'card': card,
        'tasks': tasks,
        'languages': langs,
        'license': (card or {}).get('license'),
    }
    return record

def list_all_time(limit=50, search_text='', task='Any', language='Any', require_license=False, require_carddata=False, backend_limit=500):
    api = HfApi()
    lst = api.list_datasets(sort='downloads', direction=-1, limit=backend_limit, full=True)
    records = []
    search = (search_text or '').strip().lower()
    for info in lst:
        rec = build_dataset_record(info)
        if search:
            pretty = (rec['card'] or {}).get('pretty_name') or ''
            if search not in rec['id'].lower() and search not in str(pretty).lower():
                continue
        if task != 'Any' and task.lower() not in rec['tasks']:
            continue
        if language != 'Any':
            if language == 'multi':
                if not (len(rec['languages']) > 1 or 'multilingual' in rec['languages']):
                    continue
            else:
                if language.lower() not in rec['languages']:
                    continue
        if require_license and not rec['license']:
            continue
        # require_carddata
        if require_carddata and not rec['card']:
            continue
        records.append(rec)
        if len(records) >= limit:
            break
    return records

def list_trending(period='week', limit=50, search_text='', task='Any', language='Any', require_license=False, require_carddata=False):
    url = f'https://huggingface.co/api/trending/datasets?period={period}'
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []
    ids = []
    for item in data:
        rid = item.get('repoId') or item.get('id') or item.get('name')
        if rid:
            ids.append(rid)
    records = []
    search = (search_text or '').strip().lower()
    for rid in ids:
        try:
            info = cached_dataset_info(rid)
        except Exception:
            continue
        rec = build_dataset_record(info)
        if search:
            pretty = (rec['card'] or {}).get('pretty_name') or ''
            if search not in rec['id'].lower() and search not in str(pretty).lower():
                continue
        if task != 'Any' and task.lower() not in rec['tasks']:
            continue
        if language != 'Any':
            if language == 'multi':
                if not (len(rec['languages']) > 1 or 'multilingual' in rec['languages']):
                    continue
            else:
                if language.lower() not in rec['languages']:
                    continue
        if require_license and not rec['license']:
            continue
        if require_carddata and not rec['card']:
            continue
        records.append(rec)
        if len(records) >= limit:
            break
    return records

def html_escape(s):
    import html
    return html.escape(str(s), quote=True)

def render_details(rec):
    card = rec.get('card') or {}
    pretty = card.get('pretty_name') or rec['id']
    summary = card.get('dataset_summary') or card.get('description') or ''
    if isinstance(summary, list):
        summary = ' '.join([str(x) for x in summary])
    hub_url = f"https://huggingface.co/datasets/{rec['id']}"
    # languages and tasks
    languages = ', '.join(rec['languages']) if rec['languages'] else 'n/a'
    tasks = ', '.join(rec['tasks']) if rec['tasks'] else 'n/a'
    likes = rec.get('likes')
    downloads = rec.get('downloads')
    last_mod = rec.get('last_modified')
    last_mod_str = last_mod.strftime('%Y-%m-%d %H:%M') if hasattr(last_mod, 'strftime') else str(last_mod or 'n/a')
    html_block = (
        "<div style='font-family:system-ui;line-height:1.4'>\n"
        f"<h3 style='margin:0 0 6px 0'>{html_escape(pretty)} <small style='color:#666'>({html_escape(rec['id'])})</small></h3>\n"
        f"<p style='margin:0 0 6px 0;color:#333'>{html_escape(summary)[:500]}{'...' if summary and len(summary)>500 else ''}</p>\n"
        f"<p style='margin:0 0 6px 0'><b>Downloads:</b> {downloads if downloads is not None else 'n/a'} &nbsp; <b>Likes:</b> {likes if likes is not None else 'n/a'} &nbsp; <b>Last modified:</b> {html_escape(last_mod_str)}</p>\n"
        f"<p style='margin:0 0 6px 0'><b>Languages:</b> {html_escape(languages)} &nbsp; <b>Tasks:</b> {html_escape(tasks)} &nbsp; <b>License:</b> {html_escape(card.get('license','n/a'))}</p>\n"
        f"<p><a href='{hub_url}' target='_blank'>Open on Hugging Face →</a></p>\n"
        "</div>"
    )
    return html_block

def render_ui():
    metric = widgets.ToggleButtons(
        options=['All-time downloads', 'Trending (week)', 'Trending (month)'],
        value='All-time downloads',
        description='Metric:',
    )
    limit_slider = widgets.IntSlider(value=50, min=5, max=200, step=5, description='Top N:', continuous_update=False)
    search_box = widgets.Text(value='', description='Search:')
    task_dd = widgets.Dropdown(
        options=['Any','text-classification','question-answering','translation','summarization','token-classification','image-classification','object-detection','speech-recognition','audio-classification'],
        value='Any',
        description='Task:',
    )
    lang_dd = widgets.Dropdown(options=['Any','en','de','fr','es','zh','multi'], value='Any', description='Lang:')
    lic_cb = widgets.Checkbox(value=False, description='Require license')
    card_cb = widgets.Checkbox(value=False, description='Require metadata')
    refresh_btn = widgets.Button(description='Refresh', button_style='info')
    status = widgets.HTML('')
    details = widgets.HTML('Select a dataset...')

    buttonbox = ButtonBox([])

    container = widgets.VBox([
        widgets.HBox([metric, limit_slider, refresh_btn]),
        widgets.HBox([search_box, task_dd, lang_dd, lic_cb, card_cb]),
        status,
        buttonbox.box,
        widgets.HTML('<hr/>'),
        details,
    ])

    _current_records = {}

    def populate_buttons(records):
        buttonbox.box.children = ()
        buttonbox.buttons = []
        for rec in records:
            title = (rec.get('card') or {}).get('pretty_name') or rec['id']
            desc = f'{title}'
            buttonbox.append(desc, select=False)
            buttonbox.buttons[-1].tooltip = rec['id']

    def refresh(_=None):
        status.value = 'Loading…'
        details.value = ''
        metric_val = metric.value
        limit = limit_slider.value
        search = search_box.value
        task = task_dd.value
        lang = lang_dd.value
        require_license = lic_cb.value
        require_card = card_cb.value
        if metric_val == 'All-time downloads':
            records = list_all_time(limit, search, task, lang, require_license, require_card)
        elif metric_val == 'Trending (week)':
            records = list_trending('week', limit, search, task, lang, require_license, require_card)
        else:
            records = list_trending('month', limit, search, task, lang, require_license, require_card)
        _current_records.clear()
        for r in records:
            _current_records[r['id']] = r
        populate_buttons(records)
        status.value = f'Showing {len(records)} datasets for “{metric_val}”. Click a button to see details.'

    def on_select(bbox):
        try:
            ds_id = bbox.button.tooltip
            rec = _current_records.get(ds_id)
            if rec is None:
                info = cached_dataset_info(ds_id)
                rec = build_dataset_record(info)
            details.value = render_details(rec)
        except Exception as e:
            details.value = f'<pre>{e}</pre>'

    refresh_btn.on_click(refresh)
    for w in [metric, limit_slider, search_box, task_dd, lang_dd, lic_cb, card_cb]:
        w.observe(lambda change: refresh(), names='value')
    buttonbox.clicker = on_select

    display(container)
    refresh()