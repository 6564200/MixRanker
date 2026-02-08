#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль управления окнами трансляции (Display Windows)
"""

import json
import logging
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request, render_template

logger = logging.getLogger(__name__)

# Blueprint для маршрутов
display_bp = Blueprint('display', __name__)


# === ИНИЦИАЛИЗАЦИЯ ТАБЛИЦЫ ===

def init_display_windows_table(cursor):
    """Создание таблицы display_windows"""
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
    
    # Создаём 3 окна пула по умолчанию
    cursor.execute('SELECT COUNT(*) FROM display_windows WHERE type = "pool"')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 4):
            cursor.execute('''
                INSERT INTO display_windows (type, slot_number, name, settings)
                VALUES ('pool', ?, ?, ?)
            ''', (i, f'Пул {i}', json.dumps({'items': [], 'current_index': 0})))
    
    # Создаём 10 окон кортов по умолчанию
    cursor.execute('SELECT COUNT(*) FROM display_windows WHERE type = "court"')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 11):
            cursor.execute('''
                INSERT INTO display_windows (type, slot_number, name, mode)
                VALUES ('court', ?, ?, 'auto')
            ''', (i, f'Корт {i}'))


# === CRUD ОПЕРАЦИИ ===

def get_display_window(window_type: str, slot_number: int) -> Optional[Dict]:
    """Получение окна по типу и номеру слота"""
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
    """Получение всех окон"""
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
    """Обновление окна"""
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
    """Преобразование строки БД в словарь"""
    return {
        'id': row['id'],
        'type': row['type'],
        'slot_number': row['slot_number'],
        'name': row['name'],
        'tournament_id': row['tournament_id'],
        'court_id': row['court_id'],
        'mode': row['mode'],
        'manual_page': row['manual_page'],
        'settings': json.loads(row['settings']) if row['settings'] else {},
        'is_active': bool(row['is_active']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }


# === ЛОГИКА ОПРЕДЕЛЕНИЯ СТРАНИЦЫ ДЛЯ КОРТА ===

def get_court_display_page(tournament_id: str, court_id: str) -> Dict:
    """Определяет какую страницу показывать для корта на основе состояния"""
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
    detailed_result = court_data.get('detailed_result', [])
    logger.error(f'event_state: {event_state} current_match_state: {current_match_state}')
    # Корт пуст
    if not first_participant and not second_participant:
        return {
            'page': 'empty',
            'url': None,
            'state': 'empty'
        }
    
    # Матч завершён - проверяем оба поля
    if event_state == 'finished' or current_match_state == 'finished':
        return {
            'page': 'winner',
            'url': f'/api/html-live/{tournament_id}/{court_id}/winner',
            'state': 'finished'
        }
    
    # Проверяем есть ли счёт
    has_score = False
    if detailed_result:
        for set_data in detailed_result:
            if set_data.get('firstParticipantScore', 0) > 0 or set_data.get('secondParticipantScore', 0) > 0:
                has_score = True
                break
            if set_data.get('gameScore'):
                game = set_data['gameScore']
                if game.get('first', '0') != '0' or game.get('second', '0') != '0':
                    has_score = True
                    break
    
    # Матч идёт (Live) - проверяем оба поля
    if event_state in ('active', 'live', 'playing') or current_match_state in ('live', 'playing_no_score'):
        if has_score:
            return {
                'page': 'scoreboard',
                'url': f'/api/html-live/{tournament_id}/{court_id}/score_full',
                'state': 'playing'
            }
        else:
            return {
                'page': 'vs',
                'url': f'/api/html-live/{tournament_id}/{court_id}/vs',
                'state': 'starting'
            }
    
    # По умолчанию - VS (матч запланирован)
    return {
        'page': 'vs',
        'url': f'/api/html-live/{tournament_id}/{court_id}/vs',
        'state': 'scheduled'
    }


# === API ENDPOINTS ===

@display_bp.route('/api/display/windows')
def api_get_windows():
    """Получить все окна"""
    try:
        windows = get_all_display_windows()
        return jsonify(windows)
    except Exception as e:
        logger.error(f'Ошибка получения окон: {e}')
        return jsonify({'error': str(e)}), 500


@display_bp.route('/api/display/window/<window_type>/<int:slot_number>')
def api_get_window(window_type: str, slot_number: int):
    """Получить конкретное окно"""
    try:
        window = get_display_window(window_type, slot_number)
        if not window:
            return jsonify({'error': 'Окно не найдено'}), 404
        return jsonify(window)
    except Exception as e:
        logger.error(f'Ошибка получения окна: {e}')
        return jsonify({'error': str(e)}), 500


@display_bp.route('/api/display/window/<window_type>/<int:slot_number>', methods=['PUT'])
def api_update_window(window_type: str, slot_number: int):
    """Обновить окно"""
    try:
        data = request.get_json()
        success = update_display_window(window_type, slot_number, data)
        if success:
            window = get_display_window(window_type, slot_number)
            return jsonify(window)
        return jsonify({'error': 'Не удалось обновить окно'}), 400
    except Exception as e:
        logger.error(f'Ошибка обновления окна: {e}')
        return jsonify({'error': str(e)}), 500


@display_bp.route('/api/display/court/<int:slot_number>/state')
def api_get_court_state(slot_number: int):
    """Получить текущее состояние корта и рекомендуемую страницу"""
    try:
        window = get_display_window('court', slot_number)
        if not window:
            return jsonify({'error': 'Окно не найдено'}), 404
        
        if not window.get('tournament_id') or not window.get('court_id'):
            return jsonify({
                'page': 'empty',
                'url': None,
                'state': 'not_configured'
            })
        
        page_info = get_court_display_page(window['tournament_id'], window['court_id'])
        page_info['mode'] = window['mode']
        page_info['manual_page'] = window['manual_page']
        
        return jsonify(page_info)
    except Exception as e:
        logger.error(f'Ошибка получения состояния корта: {e}')
        return jsonify({'error': str(e)}), 500


# === HTML СТРАНИЦЫ ОКОН ===

@display_bp.route('/display/manager')
def display_manager():
    """Страница управления окнами трансляции"""
    return render_template('display_manager_page.html')


@display_bp.route('/display/pool/<int:slot_number>')
def display_pool(slot_number: int):
    """Страница окна пула"""
    if slot_number < 1 or slot_number > 3:
        return 'Недопустимый номер слота', 404
    
    window = get_display_window('pool', slot_number)
    return render_template('display_pool.html', 
                          slot_number=slot_number, 
                          window=window)


@display_bp.route('/display/court/<int:slot_number>')
def display_court(slot_number: int):
    """Страница окна корта"""
    if slot_number < 1 or slot_number > 10:
        return 'Недопустимый номер слота', 404
    
    window = get_display_window('court', slot_number)
    return render_template('display_court.html', 
                          slot_number=slot_number, 
                          window=window)