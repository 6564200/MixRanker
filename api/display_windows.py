#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Р В РЎС™Р В РЎвЂўР В РўвЂР РЋРЎвЂњР В Р’В»Р РЋР Р‰ Р РЋРЎвЂњР В РЎвЂ”Р РЋР вЂљР В Р’В°Р В Р вЂ Р В Р’В»Р В Р’ВµР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В°Р В РЎВР В РЎвЂ Р РЋРІР‚С™Р РЋР вЂљР В Р’В°Р В Р вЂ¦Р РЋР С“Р В Р’В»Р РЋР РЏР РЋРІР‚В Р В РЎвЂР В РЎвЂ (Display Windows)
"""

import json
import logging
from os.path import basename
from typing import Dict, List, Optional
from urllib.parse import quote
from flask import Blueprint, jsonify, request, render_template, session

logger = logging.getLogger(__name__)

# Blueprint Р В РўвЂР В Р’В»Р РЋР РЏ Р В РЎВР В Р’В°Р РЋР вЂљР РЋРІвЂљВ¬Р РЋР вЂљР РЋРЎвЂњР РЋРІР‚С™Р В РЎвЂўР В Р вЂ 
display_bp = Blueprint('display', __name__)
DEFAULT_PLACEHOLDER_IMAGE = 'bg_001.png'
ALLOWED_PLACEHOLDER_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'}

def _is_authenticated() -> bool:
    return bool(session.get('authenticated'))


def _normalize_placeholder_image(name: Optional[str]) -> str:
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
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _has_any_nonzero_score(detailed_result: List[Dict]) -> bool:
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
    detailed_result = court_data.get('detailed_result', []) or []
    if _has_any_nonzero_score(detailed_result):
        return True

    first_participant_score = _to_int_safe(court_data.get('first_participant_score'))
    second_participant_score = _to_int_safe(court_data.get('second_participant_score'))
    return first_participant_score > 0 or second_participant_score > 0


# === Р В Р’ВР В РЎСљР В Р’ВР В Р’В¦Р В Р’ВР В РЎвЂ™Р В РІР‚С”Р В Р’ВР В РІР‚вЂќР В РЎвЂ™Р В Р’В¦Р В Р’ВР В Р вЂЎ Р В РЎС›Р В РЎвЂ™Р В РІР‚ВР В РІР‚С”Р В Р’ВР В Р’В¦Р В Р’В« ===

def init_display_windows_table(cursor):
    """Р В Р Р‹Р В РЎвЂўР В Р’В·Р В РўвЂР В Р’В°Р В Р вЂ¦Р В РЎвЂР В Р’Вµ Р РЋРІР‚С™Р В Р’В°Р В Р’В±Р В Р’В»Р В РЎвЂР РЋРІР‚В Р РЋРІР‚в„– display_windows"""
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
    
    # Р В Р Р‹Р В РЎвЂўР В Р’В·Р В РўвЂР В Р’В°Р РЋРІР‚ВР В РЎВ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В° Р В РЎвЂ”Р РЋРЎвЂњР В Р’В»Р В Р’В° (Р В РўвЂР В РЎвЂў 6) Р В Р’ВµР РЋР С“Р В Р’В»Р В РЎвЂ Р В РЎвЂР РЋРІР‚В¦ Р В Р вЂ¦Р В Р’ВµР РЋРІР‚С™
    for i in range(1, 7):
        cursor.execute('SELECT COUNT(*) FROM display_windows WHERE type = "pool" AND slot_number = ?', (i,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO display_windows (type, slot_number, name, settings)
                VALUES ('pool', ?, ?, ?)
            ''', (i, f'Р В РЎСџР РЋРЎвЂњР В Р’В» {i}', json.dumps({'items': [], 'current_index': 0})))
    
    # Р В Р Р‹Р В РЎвЂўР В Р’В·Р В РўвЂР В Р’В°Р РЋРІР‚ВР В РЎВ 10 Р В РЎвЂўР В РЎвЂќР В РЎвЂўР В Р вЂ¦ Р В РЎвЂќР В РЎвЂўР РЋР вЂљР РЋРІР‚С™Р В РЎвЂўР В Р вЂ  Р В РЎвЂ”Р В РЎвЂў Р РЋРЎвЂњР В РЎВР В РЎвЂўР В Р’В»Р РЋРІР‚РЋР В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋР вЂ№
    cursor.execute('SELECT COUNT(*) FROM display_windows WHERE type = "court"')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 11):
            cursor.execute('''
                INSERT INTO display_windows (type, slot_number, name, mode)
                VALUES ('court', ?, ?, 'auto')
            ''', (i, f'Р В РЎв„ўР В РЎвЂўР РЋР вЂљР РЋРІР‚С™ {i}'))


# === CRUD Р В РЎвЂєР В РЎСџР В РІР‚СћР В Р’В Р В РЎвЂ™Р В Р’В¦Р В Р’ВР В Р’В ===

def get_display_window(window_type: str, slot_number: int) -> Optional[Dict]:
    """Р В РЎСџР В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В Р’ВµР В Р вЂ¦Р В РЎвЂР В Р’Вµ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В° Р В РЎвЂ”Р В РЎвЂў Р РЋРІР‚С™Р В РЎвЂР В РЎвЂ”Р РЋРЎвЂњ Р В РЎвЂ Р В Р вЂ¦Р В РЎвЂўР В РЎВР В Р’ВµР РЋР вЂљР РЋРЎвЂњ Р РЋР С“Р В Р’В»Р В РЎвЂўР РЋРІР‚С™Р В Р’В°"""
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
    """Р В РЎСџР В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В Р’ВµР В Р вЂ¦Р В РЎвЂР В Р’Вµ Р В Р вЂ Р РЋР С“Р В Р’ВµР РЋРІР‚В¦ Р В РЎвЂўР В РЎвЂќР В РЎвЂўР В Р вЂ¦"""
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
    """Р В РЎвЂєР В Р’В±Р В Р вЂ¦Р В РЎвЂўР В Р вЂ Р В Р’В»Р В Р’ВµР В Р вЂ¦Р В РЎвЂР В Р’Вµ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В°"""
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
    """Р В РЎСџР РЋР вЂљР В Р’ВµР В РЎвЂўР В Р’В±Р РЋР вЂљР В Р’В°Р В Р’В·Р В РЎвЂўР В Р вЂ Р В Р’В°Р В Р вЂ¦Р В РЎвЂР В Р’Вµ Р РЋР С“Р РЋРІР‚С™Р РЋР вЂљР В РЎвЂўР В РЎвЂќР В РЎвЂ Р В РІР‚ВР В РІР‚Сњ Р В Р вЂ  Р РЋР С“Р В Р’В»Р В РЎвЂўР В Р вЂ Р В Р’В°Р РЋР вЂљР РЋР Р‰"""
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


# === Р В РІР‚С”Р В РЎвЂєР В РІР‚СљР В Р’ВР В РЎв„ўР В РЎвЂ™ Р В РЎвЂєР В РЎСџР В Р’В Р В РІР‚СћР В РІР‚СњР В РІР‚СћР В РІР‚С”Р В РІР‚СћР В РЎСљР В Р’ВР В Р вЂЎ Р В Р Р‹Р В РЎС›Р В Р’В Р В РЎвЂ™Р В РЎСљР В Р’ВР В Р’В¦Р В Р’В« Р В РІР‚СњР В РІР‚С”Р В Р вЂЎ Р В РЎв„ўР В РЎвЂєР В Р’В Р В РЎС›Р В РЎвЂ™ ===

def get_court_display_page(tournament_id: str, court_id: str, enforce_winner_result: bool = False) -> Dict:
    """Р В РЎвЂєР В РЎвЂ”Р РЋР вЂљР В Р’ВµР В РўвЂР В Р’ВµР В Р’В»Р РЋР РЏР В Р’ВµР РЋРІР‚С™ Р В РЎвЂќР В Р’В°Р В РЎвЂќР РЋРЎвЂњР РЋР вЂ№ Р РЋР С“Р РЋРІР‚С™Р РЋР вЂљР В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋРІР‚В Р РЋРЎвЂњ Р В РЎвЂ”Р В РЎвЂўР В РЎвЂќР В Р’В°Р В Р’В·Р РЋРІР‚в„–Р В Р вЂ Р В Р’В°Р РЋРІР‚С™Р РЋР Р‰ Р В РўвЂР В Р’В»Р РЋР РЏ Р В РЎвЂќР В РЎвЂўР РЋР вЂљР РЋРІР‚С™Р В Р’В° Р В Р вЂ¦Р В Р’В° Р В РЎвЂўР РЋР С“Р В Р вЂ¦Р В РЎвЂўР В Р вЂ Р В Р’Вµ Р РЋР С“Р В РЎвЂўР РЋР С“Р РЋРІР‚С™Р В РЎвЂўР РЋР РЏР В Р вЂ¦Р В РЎвЂР РЋР РЏ"""
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

    # Р В РЎв„ўР В РЎвЂўР РЋР вЂљР РЋРІР‚С™ Р В РЎвЂ”Р РЋРЎвЂњР РЋР С“Р РЋРІР‚С™
    if not first_participant and not second_participant:
        return {
            'page': 'empty',
            'url': None,
            'state': 'empty'
        }
    
    # Р В РЎС™Р В Р’В°Р РЋРІР‚С™Р РЋРІР‚РЋ Р В Р’В·Р В Р’В°Р В Р вЂ Р В Р’ВµР РЋР вЂљР РЋРІвЂљВ¬Р РЋРІР‚ВР В Р вЂ¦ - Р В РЎвЂ”Р РЋР вЂљР В РЎвЂўР В Р вЂ Р В Р’ВµР РЋР вЂљР РЋР РЏР В Р’ВµР В РЎВ Р В РЎвЂўР В Р’В±Р В Р’В° Р В РЎвЂ”Р В РЎвЂўР В Р’В»Р РЋР РЏ
    is_finished_state = event_state == 'finished' or current_match_state == 'finished'
    if is_finished_state:
        if (not enforce_winner_result) or _is_match_result_ready_for_winner(court_data):
            return {
                'page': 'winner',
                'url': f'/api/html-live/{tournament_id}/{court_id}/winner',
                'state': 'finished'
            }
    
    # Р В РЎСџР РЋР вЂљР В РЎвЂўР В Р вЂ Р В Р’ВµР РЋР вЂљР РЋР РЏР В Р’ВµР В РЎВ Р В Р’ВµР РЋР С“Р РЋРІР‚С™Р РЋР Р‰ Р В Р’В»Р В РЎвЂ Р РЋР С“Р РЋРІР‚РЋР РЋРІР‚ВР РЋРІР‚С™
    # Проверяем наличие очков: сеты ИЛИ любые очки внутри гейма/тай-брейка.
    # Только first_participant_score недостаточно — он равен 0 весь первый сет.
    has_current_points = (
        first_participant_score > 0 or
        second_participant_score > 0 or
        _has_any_nonzero_score(court_data.get('detailed_result', []))
    )
    
    # Р В РЎС™Р В Р’В°Р РЋРІР‚С™Р РЋРІР‚РЋ Р В РЎвЂР В РўвЂР РЋРІР‚ВР РЋРІР‚С™ (Live) - Р В РЎвЂ”Р РЋР вЂљР В РЎвЂўР В Р вЂ Р В Р’ВµР РЋР вЂљР РЋР РЏР В Р’ВµР В РЎВ Р В РЎвЂўР В Р’В±Р В Р’В° Р В РЎвЂ”Р В РЎвЂўР В Р’В»Р РЋР РЏ
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
    
    # Р В РЎСџР В РЎвЂў Р РЋРЎвЂњР В РЎВР В РЎвЂўР В Р’В»Р РЋРІР‚РЋР В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋР вЂ№ - VS (Р В РЎВР В Р’В°Р РЋРІР‚С™Р РЋРІР‚РЋ Р В Р’В·Р В Р’В°Р В РЎвЂ”Р В Р’В»Р В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋР вЂљР В РЎвЂўР В Р вЂ Р В Р’В°Р В Р вЂ¦)
    return {
        'page': 'vs',
        'url': f'/api/html-live/{tournament_id}/{court_id}/vs',
        'state': 'scheduled'
    }


# === API ENDPOINTS ===

@display_bp.route('/api/display/windows')
def api_get_windows():
    """Р В РЎСџР В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В РЎвЂР РЋРІР‚С™Р РЋР Р‰ Р В Р вЂ Р РЋР С“Р В Р’Вµ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В°"""
    try:
        windows = get_all_display_windows()
        return jsonify(windows)
    except Exception as e:
        logger.error(f'Р В РЎвЂєР РЋРІвЂљВ¬Р В РЎвЂР В Р’В±Р В РЎвЂќР В Р’В° Р В РЎвЂ”Р В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В Р’ВµР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р В РЎвЂўР В РЎвЂќР В РЎвЂўР В Р вЂ¦: {e}')
        return jsonify({'error': str(e)}), 500


@display_bp.route('/api/display/window/<window_type>/<int:slot_number>')
def api_get_window(window_type: str, slot_number: int):
    """Р В РЎСџР В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В РЎвЂР РЋРІР‚С™Р РЋР Р‰ Р В РЎвЂќР В РЎвЂўР В Р вЂ¦Р В РЎвЂќР РЋР вЂљР В Р’ВµР РЋРІР‚С™Р В Р вЂ¦Р В РЎвЂўР В Р’Вµ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В РЎвЂў"""
    try:
        window = get_display_window(window_type, slot_number)
        if not window:
            return jsonify({'error': 'Р В РЎвЂєР В РЎвЂќР В Р вЂ¦Р В РЎвЂў Р В Р вЂ¦Р В Р’Вµ Р В Р вЂ¦Р В Р’В°Р В РІвЂћвЂ“Р В РўвЂР В Р’ВµР В Р вЂ¦Р В РЎвЂў'}), 404
        return jsonify(window)
    except Exception as e:
        logger.error(f'Р В РЎвЂєР РЋРІвЂљВ¬Р В РЎвЂР В Р’В±Р В РЎвЂќР В Р’В° Р В РЎвЂ”Р В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В Р’ВµР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В°: {e}')
        return jsonify({'error': str(e)}), 500


@display_bp.route('/api/display/window/<window_type>/<int:slot_number>', methods=['PUT'])
def api_update_window(window_type: str, slot_number: int):
    """Update display window (auth required)"""
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
    """Р В РЎСџР В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В РЎвЂР РЋРІР‚С™Р РЋР Р‰ Р РЋРІР‚С™Р В Р’ВµР В РЎвЂќР РЋРЎвЂњР РЋРІР‚В°Р В Р’ВµР В Р’Вµ Р РЋР С“Р В РЎвЂўР РЋР С“Р РЋРІР‚С™Р В РЎвЂўР РЋР РЏР В Р вЂ¦Р В РЎвЂР В Р’Вµ Р В РЎвЂќР В РЎвЂўР РЋР вЂљР РЋРІР‚С™Р В Р’В° Р В РЎвЂ Р РЋР вЂљР В Р’ВµР В РЎвЂќР В РЎвЂўР В РЎВР В Р’ВµР В Р вЂ¦Р В РўвЂР РЋРЎвЂњР В Р’ВµР В РЎВР РЋРЎвЂњР РЋР вЂ№ Р РЋР С“Р РЋРІР‚С™Р РЋР вЂљР В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋРІР‚В Р РЋРЎвЂњ"""
    try:
        window = get_display_window('court', slot_number)
        if not window:
            return jsonify({'error': 'Р В РЎвЂєР В РЎвЂќР В Р вЂ¦Р В РЎвЂў Р В Р вЂ¦Р В Р’Вµ Р В Р вЂ¦Р В Р’В°Р В РІвЂћвЂ“Р В РўвЂР В Р’ВµР В Р вЂ¦Р В РЎвЂў'}), 404
        
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
        
        return jsonify(page_info)
    except Exception as e:
        logger.error(f'Р В РЎвЂєР РЋРІвЂљВ¬Р В РЎвЂР В Р’В±Р В РЎвЂќР В Р’В° Р В РЎвЂ”Р В РЎвЂўР В Р’В»Р РЋРЎвЂњР РЋРІР‚РЋР В Р’ВµР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р РЋР С“Р В РЎвЂўР РЋР С“Р РЋРІР‚С™Р В РЎвЂўР РЋР РЏР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р В РЎвЂќР В РЎвЂўР РЋР вЂљР РЋРІР‚С™Р В Р’В°: {e}')
        return jsonify({'error': str(e)}), 500


# === HTML Р В Р Р‹Р В РЎС›Р В Р’В Р В РЎвЂ™Р В РЎСљР В Р’ВР В Р’В¦Р В Р’В« Р В РЎвЂєР В РЎв„ўР В РЎвЂєР В РЎСљ ===

@display_bp.route('/display/manager')
def display_manager():
    """Р В Р Р‹Р РЋРІР‚С™Р РЋР вЂљР В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋРІР‚В Р В Р’В° Р РЋРЎвЂњР В РЎвЂ”Р РЋР вЂљР В Р’В°Р В Р вЂ Р В Р’В»Р В Р’ВµР В Р вЂ¦Р В РЎвЂР РЋР РЏ Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В°Р В РЎВР В РЎвЂ Р РЋРІР‚С™Р РЋР вЂљР В Р’В°Р В Р вЂ¦Р РЋР С“Р В Р’В»Р РЋР РЏР РЋРІР‚В Р В РЎвЂР В РЎвЂ"""
    return render_template('display_manager_page.html')


@display_bp.route('/display/pool/<int:slot_number>')
def display_pool(slot_number: int):
    """Р В Р Р‹Р РЋРІР‚С™Р РЋР вЂљР В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋРІР‚В Р В Р’В° Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В° Р В РЎвЂ”Р РЋРЎвЂњР В Р’В»Р В Р’В°"""
    if slot_number < 1 or slot_number > 6:
        return 'Р В РЎСљР В Р’ВµР В РўвЂР В РЎвЂўР В РЎвЂ”Р РЋРЎвЂњР РЋР С“Р РЋРІР‚С™Р В РЎвЂР В РЎВР РЋРІР‚в„–Р В РІвЂћвЂ“ Р В Р вЂ¦Р В РЎвЂўР В РЎВР В Р’ВµР РЋР вЂљ Р РЋР С“Р В Р’В»Р В РЎвЂўР РЋРІР‚С™Р В Р’В°', 404
    
    window = get_display_window('pool', slot_number)
    return render_template('display_pool.html', 
                          slot_number=slot_number, 
                          window=window,
                          placeholder_url=window['placeholder_url'] if window else f"/static/images/{DEFAULT_PLACEHOLDER_IMAGE}")


@display_bp.route('/display/court/<int:slot_number>')
def display_court(slot_number: int):
    """Р В Р Р‹Р РЋРІР‚С™Р РЋР вЂљР В Р’В°Р В Р вЂ¦Р В РЎвЂР РЋРІР‚В Р В Р’В° Р В РЎвЂўР В РЎвЂќР В Р вЂ¦Р В Р’В° Р В РЎвЂќР В РЎвЂўР РЋР вЂљР РЋРІР‚С™Р В Р’В°"""
    if slot_number < 1 or slot_number > 10:
        return 'Р В РЎСљР В Р’ВµР В РўвЂР В РЎвЂўР В РЎвЂ”Р РЋРЎвЂњР РЋР С“Р РЋРІР‚С™Р В РЎвЂР В РЎВР РЋРІР‚в„–Р В РІвЂћвЂ“ Р В Р вЂ¦Р В РЎвЂўР В РЎВР В Р’ВµР РЋР вЂљ Р РЋР С“Р В Р’В»Р В РЎвЂўР РЋРІР‚С™Р В Р’В°', 404
    
    window = get_display_window('court', slot_number)
    return render_template('display_court.html', 
                          slot_number=slot_number, 
                          window=window,
                          placeholder_url=window['placeholder_url'] if window else f"/static/images/{DEFAULT_PLACEHOLDER_IMAGE}")
