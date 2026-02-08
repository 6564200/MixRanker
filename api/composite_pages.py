#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль управления композитными страницами (Composite Pages)
Страницы с несколькими iframe поверх фонового HTML
"""

import json
import logging
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request, render_template

logger = logging.getLogger(__name__)

# Blueprint для маршрутов
composite_bp = Blueprint('composite', __name__)


# === ИНИЦИАЛИЗАЦИЯ ТАБЛИЦЫ ===

def init_composite_pages_table(cursor):
    """Создание таблицы composite_pages"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS composite_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL,
            page_type TEXT NOT NULL CHECK(page_type IN ('round', 'elimination')),
            slot_number INTEGER NOT NULL CHECK(slot_number BETWEEN 1 AND 3),
            name TEXT,
            background_settings TEXT,
            layers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tournament_id, page_type, slot_number)
        )
    ''')
    
    # Индекс для быстрого поиска по турниру
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_composite_tournament 
        ON composite_pages(tournament_id)
    ''')


def delete_composite_pages_for_tournament(tournament_id: str):
    """Удаление всех композитных страниц турнира"""
    from .database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM composite_pages WHERE tournament_id = ?', (tournament_id,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    logger.info(f'Deleted {deleted} composite pages for tournament {tournament_id}')
    return deleted


# === CRUD ОПЕРАЦИИ ===

def get_composite_page(tournament_id: str, page_type: str, slot_number: int) -> Optional[Dict]:
    """Получение композитной страницы"""
    from .database import get_db_connection
    import sqlite3
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM composite_pages 
        WHERE tournament_id = ? AND page_type = ? AND slot_number = ?
    ''', (tournament_id, page_type, slot_number))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return _row_to_dict(row)


def get_composite_pages_for_tournament(tournament_id: str) -> Dict[str, List[Dict]]:
    """Получение всех композитных страниц турнира"""
    from .database import get_db_connection
    import sqlite3
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM composite_pages 
        WHERE tournament_id = ?
        ORDER BY page_type, slot_number
    ''', (tournament_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = {'round': [], 'elimination': []}
    for row in rows:
        page = _row_to_dict(row)
        result[page['page_type']].append(page)
    
    return result


def save_composite_page(tournament_id: str, page_type: str, slot_number: int, data: Dict) -> Dict:
    """Сохранение/обновление композитной страницы"""
    from .database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем существует ли запись
    cursor.execute('''
        SELECT id FROM composite_pages 
        WHERE tournament_id = ? AND page_type = ? AND slot_number = ?
    ''', (tournament_id, page_type, slot_number))
    
    existing = cursor.fetchone()
    
    name = data.get('name', f'{page_type.capitalize()} {slot_number}')
    background_settings = json.dumps(data.get('background_settings', {}))
    layers = json.dumps(data.get('layers', []))
    
    if existing:
        cursor.execute('''
            UPDATE composite_pages 
            SET name = ?, background_settings = ?, layers = ?, updated_at = CURRENT_TIMESTAMP
            WHERE tournament_id = ? AND page_type = ? AND slot_number = ?
        ''', (name, background_settings, layers, tournament_id, page_type, slot_number))
    else:
        cursor.execute('''
            INSERT INTO composite_pages (tournament_id, page_type, slot_number, name, background_settings, layers)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tournament_id, page_type, slot_number, name, background_settings, layers))
    
    conn.commit()
    conn.close()
    
    return get_composite_page(tournament_id, page_type, slot_number)


def _row_to_dict(row) -> Dict:
    """Преобразование строки БД в словарь"""
    return {
        'id': row['id'],
        'tournament_id': row['tournament_id'],
        'page_type': row['page_type'],
        'slot_number': row['slot_number'],
        'name': row['name'],
        'background_settings': json.loads(row['background_settings']) if row['background_settings'] else {},
        'layers': json.loads(row['layers']) if row['layers'] else [],
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }


# === API ENDPOINTS ===

@composite_bp.route('/api/composite/pages/<tournament_id>')
def api_get_composite_pages(tournament_id: str):
    """Получить все композитные страницы турнира"""
    try:
        pages = get_composite_pages_for_tournament(tournament_id)
        return jsonify(pages)
    except Exception as e:
        logger.error(f'Ошибка получения композитных страниц: {e}')
        return jsonify({'error': str(e)}), 500


@composite_bp.route('/api/composite/page/<tournament_id>/<page_type>/<int:slot_number>')
def api_get_composite_page(tournament_id: str, page_type: str, slot_number: int):
    """Получить конкретную композитную страницу"""
    try:
        page = get_composite_page(tournament_id, page_type, slot_number)
        if not page:
            # Возвращаем пустую структуру
            return jsonify({
                'tournament_id': tournament_id,
                'page_type': page_type,
                'slot_number': slot_number,
                'name': f'{page_type.capitalize()} {slot_number}',
                'background_settings': {},
                'layers': []
            })
        return jsonify(page)
    except Exception as e:
        logger.error(f'Ошибка получения композитной страницы: {e}')
        return jsonify({'error': str(e)}), 500


@composite_bp.route('/api/composite/page/<tournament_id>/<page_type>/<int:slot_number>', methods=['PUT'])
def api_save_composite_page(tournament_id: str, page_type: str, slot_number: int):
    """Сохранить композитную страницу"""
    try:
        data = request.get_json()
        page = save_composite_page(tournament_id, page_type, slot_number, data)
        return jsonify(page)
    except Exception as e:
        logger.error(f'Ошибка сохранения композитной страницы: {e}')
        return jsonify({'error': str(e)}), 500


@composite_bp.route('/api/composite/available-pages/<tournament_id>')
def api_get_available_pages(tournament_id: str):
    """Получить список доступных страниц для слоёв (round_robin, elimination)"""
    import requests
    from flask import request
    
    try:
        # Используем тот же API что и main.js
        base_url = request.host_url.rstrip('/')
        response = requests.get(f'{base_url}/api/tournament/{tournament_id}/live-xml-info', timeout=10)
        
        if response.status_code != 200:
            return jsonify({'error': 'Не удалось получить данные турнира'}), 404
        
        live_xml_info = response.json()
        xml_types = live_xml_info.get('live_xml_types', [])
        
        available = {
            'round_robin': [],
            'elimination': []
        }
        
        for xml_type in xml_types:
            if xml_type.get('type') != 'tournament_table':
                continue
            
            draw_type = xml_type.get('draw_type', '')
            class_id = xml_type.get('class_id')
            draw_index = xml_type.get('draw_index', 0)
            name = xml_type.get('name', f'Draw {draw_index}')
            
            if draw_type == 'round_robin':
                available['round_robin'].append({
                    'id': f'{class_id}_{draw_index}',
                    'name': name,
                    'url': f'/api/html-live/round-robin/{tournament_id}/{class_id}/{draw_index}',
                    'class_id': class_id,
                    'draw_index': draw_index
                })
            elif draw_type == 'elimination':
                available['elimination'].append({
                    'id': f'{class_id}_{draw_index}',
                    'name': name,
                    'url': f'/api/html-live/elimination/{tournament_id}/{class_id}/{draw_index}',
                    'class_id': class_id,
                    'draw_index': draw_index
                })
        
        logger.info(f'Available pages for {tournament_id}: {len(available["round_robin"])} round_robin, {len(available["elimination"])} elimination')
        
        return jsonify(available)
    except Exception as e:
        logger.error(f'Ошибка получения доступных страниц: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


# === ФОНОВЫЕ СТРАНИЦЫ ===

def _get_name_class(name: str) -> str:
    """Определяет CSS класс для названия турнира"""
    if len(name) > 40:
        return "very-long-name"
    elif len(name) > 25:
        return "long-name"
    return ""


@composite_bp.route('/composite/bg/round/<int:slot_number>/<tournament_id>')
def composite_bg_round(slot_number: int, tournament_id: str):
    """Фоновая страница для Round Robin"""
    from .database import get_tournament_data
    
    if slot_number < 1 or slot_number > 3:
        return 'Недопустимый номер слота', 404
    
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get('metadata', {}).get('name', 'Турнир') if tournament_data else 'Турнир'
    name_class = _get_name_class(tournament_name)
    
    return render_template(f'composite_bg_round_{slot_number}.html',
                          tournament_id=tournament_id,
                          tournament_name=tournament_name,
                          name_class=name_class)


@composite_bp.route('/composite/bg/elimination/<int:slot_number>/<tournament_id>')
def composite_bg_elimination(slot_number: int, tournament_id: str):
    """Фоновая страница для Elimination"""
    from .database import get_tournament_data
    
    if slot_number < 1 or slot_number > 3:
        return 'Недопустимый номер слота', 404
    
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get('metadata', {}).get('name', 'Турнир') if tournament_data else 'Турнир'
    name_class = _get_name_class(tournament_name)
    
    return render_template(f'composite_bg_elimination_{slot_number}.html',
                          tournament_id=tournament_id,
                          tournament_name=tournament_name,
                          name_class=name_class)


# === HTML СТРАНИЦЫ ===

@composite_bp.route('/composite/<tournament_id>/<page_type>/<int:slot_number>')
def composite_page_view(tournament_id: str, page_type: str, slot_number: int):
    """Отображение композитной страницы"""
    from .database import get_tournament_data
    
    if page_type not in ('round', 'elimination'):
        return 'Недопустимый тип страницы', 404
    if slot_number < 1 or slot_number > 3:
        return 'Недопустимый номер слота', 404
    
    page = get_composite_page(tournament_id, page_type, slot_number)
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get('metadata', {}).get('name', 'Турнир') if tournament_data else 'Турнир'
    
    return render_template('composite_page.html',
                          tournament_id=tournament_id,
                          page_type=page_type,
                          slot_number=slot_number,
                          page=page,
                          tournament_name=tournament_name)


@composite_bp.route('/composite/editor/<tournament_id>/<page_type>/<int:slot_number>')
def composite_editor_view(tournament_id: str, page_type: str, slot_number: int):
    """Редактор композитной страницы"""
    from .database import get_tournament_data
    
    if page_type not in ('round', 'elimination'):
        return 'Недопустимый тип страницы', 404
    if slot_number < 1 or slot_number > 3:
        return 'Недопустимый номер слота', 404
    
    page = get_composite_page(tournament_id, page_type, slot_number)
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get('metadata', {}).get('name', 'Турнир') if tournament_data else 'Турнир'
    
    return render_template('composite_editor.html',
                          tournament_id=tournament_id,
                          page_type=page_type,
                          slot_number=slot_number,
                          page=page,
                          tournament_name=tournament_name)