#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from os.path import basename
from typing import Dict, List, Optional
from urllib.parse import quote
from flask import Blueprint, jsonify, request, render_template, session

logger = logging.getLogger(__name__)

display_bp = Blueprint('display', __name__)
DEFAULT_PLACEHOLDER_IMAGE = 'bg_001.png'
ALLOWED_PLACEHOLDER_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'}

def _is_authenticated() -> bool:
    """Проверяет, авторизован ли текущий пользователь через сессию Flask."""
    return bool(session.get('authenticated'))


def _normalize_placeholder_image(name: Optional[str]) -> str:
    """
    Проверяет и нормализует имя файла изображения-заглушки (placeholder).
    Допустимые расширения: png, jpg, jpeg, webp, gif, svg.
    Запрещены пути с каталогами (только basename).
    Возвращает переданное имя или DEFAULT_PLACEHOLDER_IMAGE при невалидном значении.
    """
    if not name:
        return DEFAULT_PLACEHOLDER_IMAGE
    if name != basename(name):
        return DEFAULT_PLACEHOLDER_IMAGE
    if '.' not in name:
        return DEFAULT_PLACEHOLDER_IMAGE
    ext = name.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_PLACEHOLDER_EXTENSIONS:
        return DEFAULT_PLACEHOLDER_IMAGE
    return name


def _to_int_safe(value) -> int:
    """Безопасно приводит значение к int. При ошибке (None, строка, и т.п.) возвращает 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _has_any_nonzero_score(detailed_result: List[Dict]) -> bool:
    """
    Проверяет, есть ли хотя бы одно ненулевое очко в detailed_result.
    Анализирует счёт по сетам (firstParticipantScore / secondParticipantScore)
    и внутри гейма/тай-брейка (gameScore.first / gameScore.second).
    Возвращает True, если найдено любое очко > 0.
    """
    for set_data in detailed_result or []:
        first_score = _to_int_safe(set_data.get('firstParticipantScore'))
        second_score = _to_int_safe(set_data.get('secondParticipantScore'))
        if first_score > 0 or second_score > 0:
            return True

        game_score = set_data.get('gameScore') or {}
        game_first = _to_int_safe(game_score.get('first'))
        game_second = _to_int_safe(game_score.get('second'))
        if game_first > 0 or game_second > 0:
            return True

    return False


def _is_match_result_ready_for_winner(court_data: Dict) -> bool:
    """
    Определяет, готов ли результат матча для отображения экрана победителя.
    Считается готовым, если есть хотя бы одно ненулевое очко в detailed_result
    или ненулевой общий счёт (first_participant_score / second_participant_score).
    """
    detailed_result = court_data.get('detailed_result', []) or []
    if _has_any_nonzero_score(detailed_result):
        return True

    first_participant_score = _to_int_safe(court_data.get('first_participant_score'))
    second_participant_score = _to_int_safe(court_data.get('second_participant_score'))
    return first_participant_score > 0 or second_participant_score > 0

def init_display_windows_table(cursor):
    """
    Создаёт таблицу display_windows и заполняет её начальными записями (если не существуют).
    Типы окон:
      'pool'  — 6 слотов для отображения групп/расписания (с настройками items и current_index),
      'court' — 10 слотов для отображения состояния кортов (mode по умолчанию 'auto').
    Вызывается при инициализации БД.
    """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS display_windows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('pool', 'court')),
            slot_number INTEGER,
            name TEXT,
            tournament_id TEXT,
            court_id TEXT,
            mode TEXT DEFAULT 'auto' CHECK(mode IN ('auto', 'manual')),
            manual_page TEXT,
            settings TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    for i in range(1, 7):
        cursor.execute('SELECT COUNT(*) FROM display_windows WHERE type = "pool" AND slot_number = ?', (i,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO display_windows (type, slot_number, name, settings)
                VALUES ('pool', ?, ?, ?)
            ''', (i, f'Слот {i}', json.dumps({'items': [], 'current_index': 0})))
    
    cursor.execute('SELECT COUNT(*) FROM display_windows WHERE type = "court"')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 11):
            cursor.execute('''
                INSERT INTO display_windows (type, slot_number, name, mode)
                VALUES ('court', ?, ?, 'auto')
            ''', (i, f'Корт {i}'))

def get_display_window(window_type: str, slot_number: int) -> Optional[Dict]:
    """
    Возвращает одно окно отображения по типу ('pool' или 'court') и номеру слота.
    Возвращает None, если запись не найдена в БД.
    """
    from .database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM display_windows 
        WHERE type = ? AND slot_number = ?
    ''', (window_type, slot_number))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return _row_to_dict(row)


def get_all_display_windows() -> Dict[str, List[Dict]]:
    """
    Возвращает все окна отображения, сгруппированные по типу.
    Формат: {'pool': [...], 'court': [...]}, отсортированные по типу и номеру слота.
    """
    from .database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM display_windows ORDER BY type, slot_number')
    rows = cursor.fetchall()
    conn.close()
    
    result = {'pool': [], 'court': []}
    for row in rows:
        window = _row_to_dict(row)
        result[window['type']].append(window)
    
    return result


def update_display_window(window_type: str, slot_number: int, data: Dict) -> bool:
    """
    Обновляет поля окна отображения в БД (только переданные ключи).
    Поддерживает обновление: name, tournament_id, court_id, mode, manual_page, settings, is_active.
    Использует execute_with_retry для защиты от конкурентных блокировок SQLite.
    Возвращает True при успешном обновлении, False — если нет полей или строка не найдена.
    """
    from .database import get_db_connection, execute_with_retry

    def transaction(conn):
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if 'name' in data:
            updates.append('name = ?')
            values.append(data['name'])
        if 'tournament_id' in data:
            updates.append('tournament_id = ?')
            values.append(data['tournament_id'])
        if 'court_id' in data:
            updates.append('court_id = ?')
            values.append(data['court_id'])
        if 'mode' in data:
            updates.append('mode = ?')
            values.append(data['mode'])
        if 'manual_page' in data:
            updates.append('manual_page = ?')
            values.append(data['manual_page'])
        if 'settings' in data:
            updates.append('settings = ?')
            values.append(json.dumps(data['settings']) if isinstance(data['settings'], dict) else data['settings'])
        if 'is_active' in data:
            updates.append('is_active = ?')
            values.append(1 if data['is_active'] else 0)
        
        if not updates:
            return False
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        values.extend([window_type, slot_number])
        
        cursor.execute(f'''
            UPDATE display_windows 
            SET {', '.join(updates)}
            WHERE type = ? AND slot_number = ?
        ''', values)
        
        return cursor.rowcount > 0
    
    return execute_with_retry(transaction)


def _row_to_dict(row) -> Dict:
    """
    Преобразует строку sqlite3.Row в словарь.
    Десериализует JSON-поле settings, нормализует placeholder_image
    и формирует готовый URL изображения-заглушки (placeholder_url).
    """
    settings = json.loads(row['settings']) if row['settings'] else {}
    placeholder_image = _normalize_placeholder_image(settings.get('placeholder_image'))

    return {
        'id': row['id'],
        'type': row['type'],
        'slot_number': row['slot_number'],
        'name': row['name'],
        'tournament_id': row['tournament_id'],
        'court_id': row['court_id'],
        'mode': row['mode'],
        'manual_page': row['manual_page'],
        'settings': settings,
        'placeholder_image': placeholder_image,
        'placeholder_url': f"/static/images/{quote(placeholder_image)}",
        'is_active': bool(row['is_active']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }

def get_court_display_page(tournament_id: str, court_id: str, enforce_winner_result: bool = False) -> Dict:
    """
    Определяет, какую страницу показывать на экране корта, исходя из текущего состояния матча.
    Возвращает словарь {'page', 'url', 'state'} с одним из вариантов:
      'empty'      — корт не настроен или данные отсутствуют,
      'winner'     — матч завершён (и результат готов, если enforce_winner_result=True),
      'scoreboard' — матч идёт, есть очки → /score_full,
      'vs'         — матч начинается или ожидает старта → /vs.
    enforce_winner_result=True используется в авто-режиме: экран победителя
    показывается только при наличии хотя бы одного ненулевого счёта.
    """
    from .database import get_court_data
    
    court_data = get_court_data(tournament_id, court_id)
    
    if not court_data or 'error' in court_data:
        return {
            'page': 'empty',
            'url': None,
            'state': 'empty'
        }
    
    event_state = (court_data.get('event_state') or '').lower()
    current_match_state = (court_data.get('current_match_state') or '').lower()
    first_participant = court_data.get('first_participant', [])
    second_participant = court_data.get('second_participant', [])
    first_participant_score = _to_int_safe(court_data.get('first_participant_score'))
    second_participant_score = _to_int_safe(court_data.get('second_participant_score'))

    if not first_participant and not second_participant:
        return {
            'page': 'empty',
            'url': None,
            'state': 'empty'
        }
    
    is_finished_state = event_state == 'finished' or current_match_state == 'finished'
    if is_finished_state:
        if (not enforce_winner_result) or _is_match_result_ready_for_winner(court_data):
            return {
                'page': 'winner',
                'url': f'/api/html-live/{tournament_id}/{court_id}/winner',
                'state': 'finished'
            }
    
    # Проверяем наличие очков: сеты ИЛИ любые очки внутри гейма/тай-брейка.
    # Только first_participant_score недостаточно — он равен 0 весь первый сет.
    has_current_points = (
        first_participant_score > 0 or
        second_participant_score > 0 or
        _has_any_nonzero_score(court_data.get('detailed_result', []))
    )
    
    if event_state in ('active', 'live', 'playing') or current_match_state in ('live', 'playing_no_score'):
        if current_match_state == 'playing_no_score':
            return {
                'page': 'vs',
                'url': f'/api/html-live/{tournament_id}/{court_id}/vs',
                'state': 'starting'
            }
        if has_current_points:
            return {
                'page': 'scoreboard',
                'url': f'/api/html-live/{tournament_id}/{court_id}/score_full',
                'state': 'playing'
            }
        return {
            'page': 'vs',
            'url': f'/api/html-live/{tournament_id}/{court_id}/vs',
            'state': 'starting'
        }
    
    return {
        'page': 'vs',
        'url': f'/api/html-live/{tournament_id}/{court_id}/vs',
        'state': 'scheduled'
    }


# === API ENDPOINTS ===

@display_bp.route('/api/display/windows')
def api_get_windows():
    """Все окна отображения, сгруппированные по типу ('pool' и 'court')."""
    try:
        windows = get_all_display_windows()
        return jsonify(windows)
    except Exception as e:
        logger.error(f'api_get_windows: {e}')
        return jsonify({'error': str(e)}), 500


@display_bp.route('/api/display/window/<window_type>/<int:slot_number>')
def api_get_window(window_type: str, slot_number: int):
    """Одно окно отображения. 404, если не найдено."""
    try:
        window = get_display_window(window_type, slot_number)
        if not window:
            return jsonify({'error': 'api_get_window'}), 404
        return jsonify(window)
    except Exception as e:
        logger.error(f'api_get_window: {e}')
        return jsonify({'error': str(e)}), 500


@display_bp.route('/api/display/window/<window_type>/<int:slot_number>', methods=['PUT'])
def api_update_window(window_type: str, slot_number: int):
    """
    Обновляет параметры окна отображения.
    Требует авторизации. Тело запроса (JSON): любые поля из
    name, tournament_id, court_id, mode, manual_page, settings, is_active.
    Возвращает обновлённый объект окна или 401/400 при ошибках.
    """
    try:
        if not _is_authenticated():
            return jsonify({'error': 'Authentication required', 'auth_required': True}), 401

        data = request.get_json()
        success = update_display_window(window_type, slot_number, data)
        if success:
            window = get_display_window(window_type, slot_number)
            return jsonify(window)

        return jsonify({'error': 'Не удалось обновить окно'}), 400
    except Exception as e:
        logger.error(f'Error updating window: {e}')
        return jsonify({'error': str(e)}), 500

@display_bp.route('/api/display/court/<int:slot_number>/state')
def api_get_court_state(slot_number: int):
    """
    Текущее состояние экрана корта.
    В авто-режиме автоматически подписывается на live-обновления (rankedin_live).
    Возвращает: page, url, state, mode, manual_page, placeholder_image/url, background_type.
    Возможные состояния (state): empty, not_configured, finished, starting, playing, scheduled.
    """
    try:
        window = get_display_window('court', slot_number)
        if not window:
            return jsonify({'error': 'api_get_court_state'}), 404
        
        if not window.get('tournament_id') or not window.get('court_id'):
            return jsonify({
                'page': 'empty',
                'url': None,
                'state': 'not_configured',
                'placeholder_image': window['placeholder_image'],
                'placeholder_url': window['placeholder_url']
            })

        # Keep live updates active in auto mode so VS -> scoreboard switches quickly
        # even before score_full page is opened.
        if window.get('mode') == 'auto':
            try:
                from .rankedin_live import live_manager
                live_court_id = int(window['court_id'])
                if not live_manager.is_subscribed(live_court_id):
                    live_manager.subscribe_court(live_court_id)
                live_manager.touch(live_court_id)
            except Exception as e:
                logger.debug(f'Auto live subscribe/touch failed for court {window.get("court_id")}: {e}')
        
        page_info = get_court_display_page(
            window['tournament_id'],
            window['court_id'],
            enforce_winner_result=(window.get('mode') == 'auto')
        )
        page_info['mode'] = window['mode']
        page_info['manual_page'] = window['manual_page']
        page_info['placeholder_image'] = window['placeholder_image']
        page_info['placeholder_url'] = window['placeholder_url']
        page_info['background_type'] = (window.get('settings') or {}).get('background_type', 'image')

        return jsonify(page_info)
    except Exception as e:
        logger.error(f'api_get_court_state: {e}')
        return jsonify({'error': str(e)}), 500

@display_bp.route('/display/manager')
def display_manager():
    """Страница менеджера окон отображения (display_manager_page.html)."""
    return render_template('display_manager_page.html')


@display_bp.route('/display/pool/<int:slot_number>')
def display_pool(slot_number: int):
    """
    Страница пула (слоты 1–6).
    Отрисовывает display_pool.html с настройками окна, изображением-заглушкой и типом фона.
    Возвращает 404 при недопустимом номере слота.
    """
    if slot_number < 1 or slot_number > 6:
        return 'display_pool', 404
    
    window = get_display_window('pool', slot_number)
    bg_type = (window.get('settings', {}).get('background_type') or 'image') if window else 'image'
    return render_template('display_pool.html',
                          slot_number=slot_number,
                          window=window,
                          placeholder_url=window['placeholder_url'] if window else f"/static/images/{DEFAULT_PLACEHOLDER_IMAGE}",
                          background_type=bg_type)


@display_bp.route('/display/media-dashboard/<tournament_id>')
def display_media_dashboard(tournament_id: str):
    """
    Media Dashboard турнира.
    Отображает сводную панель мониторинга всех кортов.
    Передаёт в шаблон: tournament_id, tournament_name, текущую дату.
    """
    from api import get_tournament_data
    from datetime import date
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get("metadata", {}).get("name", f"Турнир {tournament_id}") if tournament_data else f"Турнир {tournament_id}"
    current_date = date.today().strftime("%d.%m.%Y")
    return render_template('media_dashboard.html',
                           tournament_id=tournament_id,
                           tournament_name=tournament_name,
                           current_date=current_date)


@display_bp.route('/display/court/<int:slot_number>')
def display_court(slot_number: int):
    """
    Страница экрана корта (слоты 1–10).
    Отрисовывает display_court.html с настройками окна, изображением-заглушкой и типом фона.
    Возвращает 404 при недопустимом номере слота.
    """
    if slot_number < 1 or slot_number > 10:
        return 'display_court', 404
    
    window = get_display_window('court', slot_number)
    bg_type = (window.get('settings', {}).get('background_type') or 'image') if window else 'image'
    return render_template('display_court.html',
                          slot_number=slot_number,
                          window=window,
                          placeholder_url=window['placeholder_url'] if window else f"/static/images/{DEFAULT_PLACEHOLDER_IMAGE}",
                          background_type=bg_type)
