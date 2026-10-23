#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Переключение дизайна эфирной графики (LIGA / FPR / старый / ...).

КАК ЭТО РАБОТАЕТ
  Каждый дизайн — это папка  static/themes/<имя>/  с подпапками:
      css/     — CSS-файлы
      images/  — картинки (фоны, логотипы)
      fonts/   — шрифты (на них ссылаются из CSS темы: url('../fonts/файл'))
      js/      — JS-файлы (необязательно)

  Если в папке дизайна лежит файл с ТЕМ ЖЕ ИМЕНЕМ, что у стандартного
  (например  static/themes/fpr/css/vs.css), то при включённом дизайне
  вместо  /static/css/vs.css  страница получит  /static/themes/fpr/css/vs.css.
  Файлов, которых в теме нет, подставляются стандартные.
  Дизайн «old» (старый) — это обычные файлы проекта без изменений, папки не требует,
  в списке всегда последний.
  Необязательный файл static/themes/<имя>/theme.json вида {"title": "FPR", "order": 2}
  задаёт подпись и порядок в списке.

  Список дизайнов берётся из имён папок в static/themes — ничего регистрировать
  не нужно. Выбранный дизайн хранится в файле  data/active_design.txt.

  Подмена делается в готовом HTML-ответе (ссылки на /static/css, /static/js,
  /static/images), поэтому работает и за nginx (статика отдаётся напрямую).
  Новый дизайн подхватывается при следующей перезагрузке страницы / Browser Source.
"""

import json
import logging
import os
import re
import threading
from typing import List

from flask import Blueprint, jsonify, request

from .auth import require_auth

logger = logging.getLogger(__name__)

DEFAULT_DESIGN = 'old'      # исходный вид проекта (обычные файлы static/*)
DEFAULT_TITLE = 'Старый'
THEMES_SUBDIR = 'themes'

_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$')

# <link ... href="/static/css/vs.css?v=1" ...>
_LINK_RE = re.compile(
    r'''(<link\b[^>]*?\bhref=)(["'])/static/css/([^"'?#/]+\.css)((?:\?[^"']*)?)\2''', re.IGNORECASE)
# <script ... src="/static/js/vs.js" ...>
_SCRIPT_RE = re.compile(
    r'''(<script\b[^>]*?\bsrc=)(["'])/static/js/([^"'?#/]+\.js)((?:\?[^"']*)?)\2''', re.IGNORECASE)
# любое упоминание /static/images/<файл> (img, inline style, <style>)
_IMAGE_RE = re.compile(r'''/static/images/([^"'\s)?#<>]+)''')
_HTML_TAG_RE = re.compile(r'<html\b', re.IGNORECASE)


def is_valid_name(name: str) -> bool:
    return bool(name) and bool(_NAME_RE.match(name))


def _theme_meta(static_dir: str, design: str) -> dict:
    try:
        with open(os.path.join(static_dir, THEMES_SUBDIR, design, 'theme.json'), encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def list_designs(static_dir: str) -> List[str]:
    """Папки из static/themes (по theme.json "order", затем по имени) + 'old' в конце."""
    themes_dir = os.path.join(static_dir, THEMES_SUBDIR)
    names = []
    if os.path.isdir(themes_dir):
        for entry in os.listdir(themes_dir):
            if entry == DEFAULT_DESIGN or not is_valid_name(entry):
                continue
            if os.path.isdir(os.path.join(themes_dir, entry)):
                names.append(entry)

    def sort_key(name):
        order = _theme_meta(static_dir, name).get('order', 100)
        return (order if isinstance(order, (int, float)) else 100, name)

    return sorted(names, key=sort_key) + [DEFAULT_DESIGN]


def design_title(static_dir: str, design: str) -> str:
    """Подпись дизайна для списка (theme.json -> title, иначе имя папки)."""
    if design == DEFAULT_DESIGN:
        return DEFAULT_TITLE
    title = str(_theme_meta(static_dir, design).get('title', '')).strip()
    return title or design


def _theme_file(static_dir: str, design: str, sub: str, filename: str):
    """Путь к файлу темы, если он существует, иначе None."""
    if not filename or filename != os.path.basename(filename):
        return None
    path = os.path.join(static_dir, THEMES_SUBDIR, design, sub, filename)
    return path if os.path.isfile(path) else None


def _versioned_url(design: str, sub: str, filename: str, path: str) -> str:
    try:
        version = int(os.path.getmtime(path))
    except OSError:
        version = 0
    return f'/static/{THEMES_SUBDIR}/{design}/{sub}/{filename}?v={version}'


def apply_design(html: str, design: str, static_dir: str) -> str:
    """
    Подменяет в HTML ссылки на стандартные css/js/картинки на файлы выбранной темы
    (только если такие файлы в теме есть). Для 'old' возвращает html без изменений.
    """
    if not html or design == DEFAULT_DESIGN or not is_valid_name(design):
        return html
    if not os.path.isdir(os.path.join(static_dir, THEMES_SUBDIR, design)):
        return html

    def swap_asset(sub):
        def _swap(match):
            prefix, quote, filename, _query = match.groups()
            path = _theme_file(static_dir, design, sub, filename)
            if not path:
                return match.group(0)
            return f'{prefix}{quote}{_versioned_url(design, sub, filename, path)}{quote}'
        return _swap

    def swap_image(match):
        filename = match.group(1)
        path = _theme_file(static_dir, design, 'images', filename)
        if not path:
            return match.group(0)
        return f'/static/{THEMES_SUBDIR}/{design}/images/{filename}'

    html = _LINK_RE.sub(swap_asset('css'), html)
    html = _SCRIPT_RE.sub(swap_asset('js'), html)
    html = _IMAGE_RE.sub(swap_image, html)
    # метка на <html data-design="..."> — удобно для своих стилей/отладки
    html = _HTML_TAG_RE.sub(f'<html data-design="{design}"', html, count=1)
    return html


class DesignStore:
    """Хранит имя активного дизайна в текстовом файле (читает с кэшем по mtime)."""

    def __init__(self, state_file: str, static_dir: str):
        self.state_file = state_file
        self.static_dir = static_dir
        self._lock = threading.Lock()
        self._mtime = None
        self._name = DEFAULT_DESIGN

    def get(self) -> str:
        try:
            mtime = os.path.getmtime(self.state_file)
        except OSError:
            return DEFAULT_DESIGN
        with self._lock:
            if mtime != self._mtime:
                try:
                    with open(self.state_file, 'r', encoding='utf-8') as fh:
                        name = fh.read().strip()
                except OSError:
                    name = DEFAULT_DESIGN
                self._name = name if is_valid_name(name) else DEFAULT_DESIGN
                self._mtime = mtime
            name = self._name
        # дизайн мог быть удалён с диска — тогда возвращаемся к old
        return name if name in list_designs(self.static_dir) else DEFAULT_DESIGN

    def set(self, name: str) -> None:
        os.makedirs(os.path.dirname(self.state_file) or '.', exist_ok=True)
        tmp = self.state_file + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(name)
        os.replace(tmp, self.state_file)
        with self._lock:
            self._mtime = None


def register_design_switch(app):
    """Подключает API /api/design и подмену ссылок в HTML-ответах."""
    data_dir = os.environ.get('DATA_DIR') or 'data'
    store = DesignStore(os.path.join(data_dir, 'active_design.txt'), app.static_folder)
    bp = Blueprint('design_switch', __name__)

    @bp.route('/api/design', methods=['GET'])
    def get_design():
        return jsonify({
            'active': store.get(),
            'available': list_designs(app.static_folder),
            'titles': {n: design_title(app.static_folder, n) for n in list_designs(app.static_folder)},
        })

    @bp.route('/api/design', methods=['POST'])
    @require_auth
    def set_design():
        payload = request.get_json(silent=True) or {}
        name = str(payload.get('design', '')).strip()
        if name not in list_designs(app.static_folder):
            return jsonify({'error': 'Неизвестный дизайн'}), 400
        store.set(name)
        logger.info('Active design switched to %s', name)
        return jsonify({'success': True, 'active': name})

    app.register_blueprint(bp)

    @app.after_request
    def _apply_design(response):
        try:
            if (response.direct_passthrough or response.status_code != 200
                    or response.mimetype != 'text/html'):
                return response
            design = store.get()
            if design == DEFAULT_DESIGN:
                return response
            html = response.get_data(as_text=True)
            if '</head>' not in html:
                return response
            new_html = apply_design(html, design, app.static_folder)
            if new_html != html:
                response.set_data(new_html)
        except Exception:
            logger.exception('Design switch failed; page served with the original (old) design')
        return response

    return store
