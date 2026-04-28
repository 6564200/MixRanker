#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import json
import logging
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for

logger = logging.getLogger(__name__)

composite_bp = Blueprint('composite', __name__)

def _is_authenticated() -> bool:
    """Проверяет, авторизован ли текущий пользователь через сессию."""
    return bool(session.get('authenticated'))

def init_composite_pages_table(cursor):
    """
    Создаёт таблицу composite_pages и индекс по tournament_id (если не существуют).
    Вызывается при инициализации БД.
    """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS composite_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL,
            page_type TEXT NOT NULL CHECK(page_type IN ('round', 'elimination')),
            slot_number INTEGER NOT NULL CHECK(slot_number BETWEEN 1 AND 4),
            name TEXT,
            background_settings TEXT,
            layers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tournament_id, page_type, slot_number)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_composite_tournament 
        ON composite_pages(tournament_id)
    ''')


def delete_composite_pages_for_tournament(tournament_id: str):
    """Удаляет все composite-страницы турнира из БД. Возвращает количество удалённых записей."""
    from .database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM composite_pages WHERE tournament_id = ?', (tournament_id,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    logger.info(f'Deleted {deleted} composite pages for tournament {tournament_id}')
    return deleted

def get_composite_page(tournament_id: str, page_type: str, slot_number: int) -> Optional[Dict]:
    """
    Возвращает одну composite-страницу по турниру, типу ('round'/'elimination') и номеру слота (1–4).
    Возвращает None, если запись не найдена.
    """
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
    """
    Возвращает все composite-страницы турнира, сгруппированные по типу.
    Формат: {'round': [...], 'elimination': [...]}.
    """
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
    """
    Сохраняет (INSERT или UPDATE) composite-страницу в БД.
    data должна содержать: name, background_settings, layers.
    Возвращает сохранённую запись.
    """
    from .database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
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
    """Преобразует строку sqlite3.Row в словарь, десериализуя JSON-поля background_settings и layers."""
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
    """Все composite-страницы турнира, сгруппированные по типу."""
    try:
        pages = get_composite_pages_for_tournament(tournament_id)
        return jsonify(pages)
    except Exception as e:
        logger.error(f'api_get_composite_pages: {e}')
        return jsonify({'error': str(e)}), 500


@composite_bp.route('/api/composite/page/<tournament_id>/<page_type>/<int:slot_number>')
def api_get_composite_page(tournament_id: str, page_type: str, slot_number: int):
    """
    Одна composite-страница.
    Если запись не найдена в БД, возвращает пустой шаблон с дефолтными значениями (200 OK).
    """
    try:
        page = get_composite_page(tournament_id, page_type, slot_number)
        if not page:
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
        logger.error(f'api_get_composite_page: {e}')
        return jsonify({'error': str(e)}), 500


@composite_bp.route('/api/composite/page/<tournament_id>/<page_type>/<int:slot_number>', methods=['PUT'])
def api_save_composite_page(tournament_id: str, page_type: str, slot_number: int):
    """
    Сохраняет composite-страницу.
    Требует авторизации. Тело запроса (JSON): name, background_settings, layers.
    Возвращает сохранённую запись или 401 при отсутствии авторизации.
    """
    try:
        if not _is_authenticated():
            return jsonify({'error': 'Authentication required', 'auth_required': True}), 401
        data = request.get_json()
        page = save_composite_page(tournament_id, page_type, slot_number, data)
        return jsonify(page)
    except Exception as e:
        logger.error(f'Error saving api_save_composite_page: {e}')
        return jsonify({'error': str(e)}), 500

@composite_bp.route('/api/composite/available-pages/<tournament_id>')
def api_get_available_pages(tournament_id: str):
    """
    Список доступных сеток/таблиц турнира.
    Обращается к RankedinAPI и возвращает словарь с двумя ключами:
      'round_robin'  — список круговых групп (тип draw_type == 'round_robin'),
      'elimination'  — список сеток плей-офф (тип draw_type == 'elimination').
    Каждый элемент содержит: id, name, url, class_id, draw_index.
    """
    from .database import get_tournament_data
    from .rankedin_api import RankedinAPI

    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({'error': 'Tournament not found'}), 404

        api_client = RankedinAPI()
        xml_types = api_client.get_xml_data_types(tournament_data)

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

        logger.info(
            f"Available pages for {tournament_id}: "
            f"{len(available['round_robin'])} round_robin, "
            f"{len(available['elimination'])} elimination"
        )

        return jsonify(available)
    except Exception as e:
        logger.error(f'Error getting available pages: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500

def _get_name_class(name: str) -> str:
    """
    Возвращает CSS-класс для длинных названий турниров
    """
    if len(name) > 40:
        return "very-long-name"
    elif len(name) > 25:
        return "long-name"
    return ""


@composite_bp.route('/composite/bg/round/<int:slot_number>/<tournament_id>')
def composite_bg_round(slot_number: int, tournament_id: str):
    """
    Фоновый слой для группового этапа.
    Отрисовывает шаблон composite_bg_round_<slot_number>.html (слоты 1–4).
    Передаёт в шаблон: tournament_id, tournament_name, name_class.
    Возвращает 404, если номер слота выходит за пределы 1–4.
    """
    from .database import get_tournament_data
    
    if slot_number < 1 or slot_number > 4:
        return '', 404
    
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get('metadata', {}).get('name', 'Турнир') if tournament_data else 'Турнир'
    name_class = _get_name_class(tournament_name)
    
    return render_template('composite_bg_round.html',
                          tournament_id=tournament_id,
                          slot_number=slot_number,
                          tournament_name=tournament_name,
                          name_class=name_class)


@composite_bp.route('/composite/bg/elimination/<int:slot_number>/<tournament_id>')
def composite_bg_elimination(slot_number: int, tournament_id: str):
    """
    Фоновый слой для плей-офф сетки.
    Отрисовывает шаблон composite_bg_elimination_<slot_number>.html (слоты 1–4).
    Передаёт в шаблон: tournament_id, tournament_name, name_class.
    Возвращает 404, если номер слота выходит за пределы 1–4.
    """
    from .database import get_tournament_data
    
    if slot_number < 1 or slot_number > 4:
        return '404', 404
    
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get('metadata', {}).get('name', 'Турнир') if tournament_data else 'Турнир'
    name_class = _get_name_class(tournament_name)
    
    return render_template('composite_bg_elimination.html',
                          tournament_id=tournament_id,
                          slot_number=slot_number,
                          tournament_name=tournament_name,
                          name_class=name_class)

@composite_bp.route('/composite/<tournament_id>/<page_type>/<int:slot_number>')
def composite_page_view(tournament_id: str, page_type: str, slot_number: int):
    """
    Финальная composite-страница для трансляции.
    Отрисовывает шаблон composite_page.html с наложенными слоями и фоном.
    page_type: 'round' (групповой этап) или 'elimination' (плей-офф).
    slot_number: 1–4. Возвращает 404 при недопустимых значениях.
    """
    from .database import get_tournament_data
    
    if page_type not in ('round', 'elimination'):
        return '---', 404
    if slot_number < 1 or slot_number > 4:
        return '---', 404
    
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
    """
    Редактор composite-страницы.
    Требует авторизации (иначе редирект на главную). Отрисовывает шаблон composite_editor.html,
    передавая текущее состояние страницы из БД и имя турнира.
    page_type: 'round' или 'elimination'; slot_number: 1–4.
    """
    from .database import get_tournament_data

    if not _is_authenticated():
        return redirect(url_for('index'))

    if page_type not in ('round', 'elimination'):
        return 'Недопустимый тип страницы', 404
    if slot_number < 1 or slot_number > 4:
        return 'Недопустимый номер слота', 404

    page = get_composite_page(tournament_id, page_type, slot_number)
    tournament_data = get_tournament_data(tournament_id)
    tournament_name = tournament_data.get('metadata', {}).get('name', 'Турнир') if tournament_data else 'Турнир'

    return render_template(
        'composite_editor.html',
        tournament_id=tournament_id,
        page_type=page_type,
        slot_number=slot_number,
        page=page,
        tournament_name=tournament_name
    )
