#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vMixRanker v2.6
Веб-сервис для интеграции данных турниров rankedin.com с vMix
"""

import os
import sys
import logging
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template, Response, session
from werkzeug.utils import secure_filename
from typing import Dict, List, Optional
from config import get_config

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Создание директорий
for d in ['logs', 'data', 'xml_files', 'api', 'static/css', 'static/js', 'templates', 'static/fonts', 'static/photos']:
    os.makedirs(d, exist_ok=True)
UPLOAD_FOLDER = 'static/photos'

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/vmix_ranker.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Импорты из рефакторенных модулей
from api import (
    RankedinAPI, init_database,
    get_tournament_data, get_court_data, save_courts_data,
    execute_with_retry, save_xml_file_info,
    require_auth, register_auth_routes,
    AutoRefreshService,
    enrich_court_data_with_photos, get_participant_info, get_photo_urls_for_ids,
    get_sport_name, get_xml_type_description, get_update_frequency, get_uptime
)
from api.xml_generator import XMLFileManager

# Flask приложение
app = Flask(__name__)
config = get_config()
app.secret_key = getattr(config, 'SECRET_KEY', None) or os.urandom(24)
app.start_time = time.time()

# Глобальные объекты
api = RankedinAPI()
xml_manager = XMLFileManager('xml_files')

# Регистрация роутов аутентификации
register_auth_routes(app)


@app.after_request
def set_secure_headers(response):
    response.headers['X-Content-Type-Options'] = "nosniff"
    response.headers['X-Frame-Options'] = "SAMEORIGIN"
    return response


# === ОСНОВНЫЕ РОУТЫ ===
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except:
        return "<html><body><h1>vMixRanker</h1></body></html>"

@app.route('/static/<path:filename>')
def static_files(filename):
    from flask import send_from_directory
    return send_from_directory('static', filename)


# === API: ТУРНИРЫ ===
@app.route('/api/tournament/<tournament_id>', methods=['POST'])
@require_auth
def load_tournament(tournament_id):
    """Загрузка турнира"""
    try:
        tournament_data = api.get_full_tournament_data(tournament_id)
        if not tournament_data.get("metadata"):
            return jsonify({"success": False, "error": "Не удалось получить данные турнира"}), 400

        metadata = tournament_data.get("metadata", {})
        participants = tournament_data.get("participants", [])

        def save_transaction(conn):
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tournaments 
                (id, name, metadata, classes, courts, dates, draw_data, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                tournament_id, metadata.get("name", f"Турнир {tournament_id}"),
                json.dumps(metadata), json.dumps(tournament_data.get("classes", [])),
                json.dumps(tournament_data.get("courts", [])), json.dumps(tournament_data.get("dates", [])),
                json.dumps(tournament_data.get("draw_data", {})), "active"
            ))
            cursor.execute('''
                INSERT OR REPLACE INTO tournament_schedule 
                (tournament_id, court_planner, court_usage, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (tournament_id, json.dumps(tournament_data.get("court_planner", {})),
                  json.dumps(tournament_data.get("court_usage", {}))))

            if participants:
                cursor.executemany('''
                    INSERT OR IGNORE INTO participants (id, rankedin_id, first_name, last_name, country_code)
                    VALUES (?, ?, ?, ?, ?)
                ''', [(p.get("Id"), p.get("RankedinId"), p.get("FirstName"), p.get("LastName"), p.get("CountryShort")) for p in participants])
                cursor.executemany('''
                    INSERT OR IGNORE INTO participants_tournaments (participant_id, tournament_id) VALUES (?, ?)
                ''', [(p.get("Id"), tournament_id) for p in participants])

        execute_with_retry(save_transaction)
        logger.info(f"Турнир {tournament_id} загружен")

        return jsonify({
            "success": True, "tournament_id": tournament_id,
            "name": metadata.get("name"), "sport": get_sport_name(metadata.get("sport", 5)),
            "categories": len(tournament_data.get("classes", [])),
            "courts": len(tournament_data.get("courts", []))
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки турнира {tournament_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tournaments')
def get_tournaments():
    """Список турниров"""
    try:
        def transaction(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, metadata, status, created_at, updated_at FROM tournaments ORDER BY updated_at DESC')
            return [{
                "id": r['id'], "name": r['name'], "status": r['status'],
                "sport": json.loads(r['metadata']).get("sport", 5) if r['metadata'] else 5,
                "created_at": r['created_at'], "updated_at": r['updated_at']
            } for r in cursor.fetchall()]
        return jsonify(execute_with_retry(transaction))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tournament/<tournament_id>', methods=['DELETE'])
@require_auth
def delete_tournament(tournament_id):
    """Удаление турнира"""
    try:
        def transaction(conn):
            cursor = conn.cursor()
            cursor.execute('DELETE FROM courts_data WHERE tournament_id = ?', (tournament_id,))
            cursor.execute('DELETE FROM xml_files WHERE tournament_id = ?', (tournament_id,))
            cursor.execute('DELETE FROM tournament_schedule WHERE tournament_id = ?', (tournament_id,))
            cursor.execute('DELETE FROM tournaments WHERE id = ?', (tournament_id,))
        execute_with_retry(transaction)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tournament/<tournament_id>/courts')
def get_tournament_courts(tournament_id):
    """Данные кортов турнира"""
    try:
        def get_court_ids(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT courts FROM tournaments WHERE id = ?', (tournament_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return [str(c.get("Item1")) for c in json.loads(row[0]) if c.get("Item1")]
            return []

        court_ids = execute_with_retry(get_court_ids)
        if not court_ids:
            return jsonify([])

        courts_data = api.get_all_courts_data(court_ids)
        if courts_data:
            save_courts_data(tournament_id, courts_data)
        return jsonify(courts_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tournament/<tournament_id>/xml-types')
def get_xml_types(tournament_id):
    """Типы XML для турнира"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404
        return jsonify(api.get_xml_data_types(tournament_data))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === API: УЧАСТНИКИ ===
@app.route('/api/tournament/<tournament_id>/participants', methods=['GET', 'POST'])
def manage_participants(tournament_id):
    """Управление участниками"""
    try:
        if request.method == 'POST':
            tournament_data = api.get_full_tournament_data(tournament_id)
            participants = tournament_data.get("participants", [])
            if participants:
                def save(conn):
                    cursor = conn.cursor()
                    cursor.executemany('''
                        INSERT OR IGNORE INTO participants (id, rankedin_id, first_name, last_name, country_code)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [(p.get("Id"), p.get("RankedinId"), p.get("FirstName"), p.get("LastName"), p.get("CountryShort")) for p in participants])
                    cursor.executemany('INSERT OR IGNORE INTO participants_tournaments VALUES (?, ?)',
                                      [(p.get("Id"), tournament_id) for p in participants])
                execute_with_retry(save)

        def get_participants(conn):
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.* FROM participants p
                JOIN participants_tournaments pt ON p.id = pt.participant_id
                WHERE pt.tournament_id = ?
            ''', (tournament_id,))
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]

        return jsonify(execute_with_retry(get_participants))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/participants/upload-photo', methods=['POST'])
def upload_participant_photo():
    """Загрузка фото участника"""
    if 'photo' not in request.files:
        return jsonify({"success": False, "error": "Нет файла"}), 400

    file = request.files['photo']
    participant_id = request.form.get('participant_id')

    if file and participant_id:
        filename = f"{secure_filename(participant_id)}.png"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        info = json.dumps({
            'country': request.form.get('country'),
            'rating': request.form.get('rating'),
            'height': request.form.get('height'),
            'full_name': request.form.get('english-name')
        })

        def update(conn):
            conn.cursor().execute('UPDATE participants SET photo_url = ?, info = ? WHERE id = ?',
                                 (f"/{UPLOAD_FOLDER}/{filename}", info, participant_id))
        execute_with_retry(update)

        return jsonify({"success": True, "preview_url": f"/{UPLOAD_FOLDER}/{filename}"})
    return jsonify({"success": False}), 500


# === API: РАСПИСАНИЕ ===
@app.route('/api/tournament/<tournament_id>/schedule/reload', methods=['POST'])
def reload_tournament_schedule(tournament_id):
    """Перезагрузка расписания"""
    try:
        def get_dates(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT dates FROM tournaments WHERE id = ? AND status = ?', (tournament_id, 'active'))
            r = cursor.fetchone()
            return json.loads(r[0]) if r and r[0] else []

        dates = execute_with_retry(get_dates)
        if not dates:
            return jsonify({"error": "Турнир не найден"}), 400

        court_planner = api.get_court_planner(tournament_id, dates)
        court_usage = api.get_court_usage(tournament_id, dates)

        def save(conn):
            conn.cursor().execute('''
                UPDATE tournament_schedule SET court_planner = ?, court_usage = ?, updated_at = CURRENT_TIMESTAMP
                WHERE tournament_id = ?
            ''', (json.dumps(court_planner or {}), json.dumps(court_usage or {}), tournament_id))
        execute_with_retry(save)

        return jsonify({"success": True, "matches_count": len(court_usage) if isinstance(court_usage, list) else 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === API: XML ===
@app.route('/api/xml/<tournament_id>/<xml_type_id>')
def generate_xml(tournament_id, xml_type_id):
    """Генерация XML"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404

        xml_types = api.get_xml_data_types(tournament_data)
        xml_type_info = next((t for t in xml_types if t["id"] == xml_type_id), None)
        if not xml_type_info:
            return jsonify({"error": "Неизвестный тип XML"}), 400

        if xml_type_info["type"] == "court_score":
            court_data = api.get_court_scoreboard(str(xml_type_info.get("court_id")))
            if "error" in court_data:
                return jsonify({"error": "Ошибка получения данных корта"}), 500
            file_info = xml_manager.generate_and_save(xml_type_info, tournament_data, court_data)
        else:
            # Для турнирных таблиц обновляем данные из API
            if xml_type_info["type"] == "tournament_table":
                class_id = xml_type_info.get("class_id")
                draw_type = xml_type_info.get("draw_type")
                
                if draw_type == "round_robin":
                    fresh_data = api.get_all_draws_for_class(str(class_id)).get("round_robin", [])
                elif draw_type == "elimination":
                    fresh_data = api.get_all_draws_for_class(str(class_id)).get("elimination", [])
                else:
                    fresh_data = None
                
                if fresh_data and tournament_data.get("draw_data", {}).get(str(class_id)):
                    if draw_type == "round_robin":
                        tournament_data["draw_data"][str(class_id)]["round_robin"] = fresh_data
                    elif draw_type == "elimination":
                        tournament_data["draw_data"][str(class_id)]["elimination"] = fresh_data

            file_info = xml_manager.generate_and_save(xml_type_info, tournament_data)

        save_xml_file_info(tournament_id, file_info)
        return jsonify(file_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/xml-live/<tournament_id>/<xml_type_id>')
def get_live_xml_data(tournament_id, xml_type_id):
    """Live XML данные"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return Response("<!-- Турнир не найден -->", mimetype='application/xml'), 404

        xml_types = api.get_xml_data_types(tournament_data)
        xml_type_info = next((t for t in xml_types if t["id"] == xml_type_id), None)
        if not xml_type_info:
            return Response("<!-- Неизвестный тип -->", mimetype='application/xml'), 400

        if xml_type_info["type"] == "court_score":
            court_data = api.get_court_scoreboard(str(xml_type_info.get("court_id")))
            xml_content = xml_manager.xml_generator.generate_court_score_xml(court_data, tournament_data)
        elif xml_type_info["type"] == "tournament_table":
            xml_content = xml_manager.xml_generator.generate_tournament_table_xml(tournament_data, xml_type_info)
        else:
            return Response("<!-- Неподдерживаемый тип -->", mimetype='application/xml'), 400

        return Response(xml_content, mimetype='application/xml; charset=utf-8')
    except Exception as e:
        return Response(f"<!-- Ошибка: {e} -->", mimetype='application/xml'), 500


@app.route('/api/tournament/<tournament_id>/live-xml-info')
def get_live_xml_info(tournament_id):
    """Информация о live XML"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404

        xml_types = api.get_xml_data_types(tournament_data)
        live_xml_info = []
        for t in xml_types:
            info = {
                "id": t["id"],
                "name": t.get("name", t["id"]),
                "type": t["type"],
                "live_url": f"/api/xml-live/{tournament_id}/{t['id']}",
                "description": get_xml_type_description(t.get("type", "")),
                "update_frequency": get_update_frequency(t.get("type", ""))
            }
            # Добавляем поля для tournament_table
            if t["type"] == "tournament_table":
                info["class_id"] = t.get("class_id")
                info["class_name"] = t.get("class_name")
                info["draw_type"] = t.get("draw_type")
                info["draw_index"] = t.get("draw_index")
                info["stage_name"] = t.get("stage_name", "")
                info["group_name"] = t.get("group_name", "")
            # Добавляем поля для court_score
            elif t["type"] == "court_score":
                info["court_id"] = t.get("court_id")
                info["court_name"] = t.get("court_name")
            live_xml_info.append(info)

        return jsonify({
            "tournament_id": tournament_id,
            "tournament_name": tournament_data.get("metadata", {}).get("name", f"Турнир {tournament_id}"),
            "live_xml_count": len(live_xml_info),
            "live_xml_types": live_xml_info
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/xml/<filename>')
def serve_xml_file(filename):
    """Отдача XML файлов"""
    try:
        return send_file(f'xml_files/{filename}', mimetype='application/xml')
    except FileNotFoundError:
        return Response("<!-- Файл не найден -->", mimetype='application/xml'), 404

# === API: HTML LIVE ===
@app.route('/api/html-live/<tournament_id>/<court_id>')
def get_live_court_html(tournament_id, court_id):
    """Live HTML корта с AJAX-обновлением"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return "<html><body><h1>Турнир не найден</h1></body></html>", 404

        court_data = get_court_data(tournament_id, str(court_id))
        if not court_data or "error" in court_data:
            return "<html><body><h1>Корт не найден</h1></body></html>", 500

        html = xml_manager.html_generator.generate_court_scoreboard_html(
            court_data, tournament_data, tournament_id, court_id
        )
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/<tournament_id>/<court_id>/score')
def get_live_court_score_html(tournament_id, court_id):
    """Fullscreen scoreboard с AJAX-обновлением"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        court_data = get_court_data(tournament_id, str(court_id))
        if not tournament_data or not court_data:
            return "<html><body><h1>Не найдено</h1></body></html>", 404

        html = xml_manager.html_generator.generate_court_fullscreen_scoreboard_html(
            court_data, tournament_data, tournament_id, court_id
        )
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/<tournament_id>/<court_id>/vs')
def get_court_vs_html(tournament_id, court_id):
    """VS страница с фото"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        court_data = get_court_data(tournament_id, str(court_id))
        if not tournament_data or not court_data:
            return "<html><body><h1>Не найдено</h1></body></html>", 404

        court_data = enrich_court_data_with_photos(court_data)
        html = xml_manager.html_generator.generate_court_vs_html(court_data, tournament_data)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/<tournament_id>/<court_id>/next')
def get_next_match_html(tournament_id, court_id):
    """Следующий матч"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        court_data = get_court_data(tournament_id, str(court_id))
        if not tournament_data or not court_data:
            return "<html><body><h1>Не найдено</h1></body></html>", 404

        # Обогащаем фото для next участников
        next_ids = []
        for p in court_data.get("next_first_participant", []) + court_data.get("next_second_participant", []):
            if p.get("id"):
                next_ids.append(p["id"])
        if next_ids:
            photo_map = get_photo_urls_for_ids(next_ids)
            for p in court_data.get("next_first_participant", []) + court_data.get("next_second_participant", []):
                if p.get("id") in photo_map:
                    p["photo_url"] = photo_map[p["id"]]

        html = xml_manager.html_generator.generate_next_match_page_html(court_data, tournament_data)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/<tournament_id>/<court_id>/winner')
def get_winner_page_html(tournament_id, court_id):
    """Страница победителя"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        court_data = get_court_data(tournament_id, str(court_id))
        if not tournament_data or not court_data:
            return "<html><body><h1>Не найдено</h1></body></html>", 404

        court_data = enrich_court_data_with_photos(court_data)

        # id_url для совместимости со старым API
        all_ids = [p.get("id") for p in court_data.get("first_participant", []) + court_data.get("second_participant", []) if p.get("id")]
        id_url = [{"id": pid, "photo_url": court_data.get("first_participant", [{}])[0].get("photo_url") or court_data.get("second_participant", [{}])[0].get("photo_url")} for pid in all_ids]

        html = xml_manager.html_generator.generate_winner_page_html(court_data, id_url, tournament_data)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/participant/<participant_id>/introduction')
def get_introduction_page_html(participant_id):
    """Страница представления участника"""
    try:
        participant = get_participant_info(int(participant_id))
        if not participant:
            return "<html><body><h1>Участник не найден</h1></body></html>", 404

        html = xml_manager.html_generator.generate_introduction_page_html(participant)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/schedule/<tournament_id>')
def get_live_schedule_html(tournament_id):
    """Live расписание"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return "<html><body><h1>Турнир не найден</h1></body></html>", 404

        target_date = request.args.get('date')
        html = xml_manager.html_generator.generate_schedule_html(tournament_data, target_date)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/schedule/<tournament_id>/addreality')
def get_live_schedule_html_addreality(tournament_id):
    """Расписание AddReality"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return "<html><body><h1>Турнир не найден</h1></body></html>", 404

        target_date = request.args.get('date')
        html = xml_manager.html_generator.generate_schedule_html_addreality(tournament_data, target_date)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/round-robin/<tournament_id>/<class_id>/<int:draw_index>')
def get_live_round_robin_html(tournament_id, class_id, draw_index):
    """Round Robin HTML"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return "<html><body><h1>Турнир не найден</h1></body></html>", 404

        xml_types = api.get_xml_data_types(tournament_data)
        xml_type_info = next((t for t in xml_types if t.get("type") == "tournament_table" and 
                             t.get("draw_type") == "round_robin" and t.get("class_id") == class_id and 
                             t.get("draw_index") == draw_index), None)
        if not xml_type_info:
            return "<html><body><h1>Таблица не найдена</h1></body></html>", 404

        html = xml_manager.html_generator.generate_round_robin_html(tournament_data, xml_type_info)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/elimination/<tournament_id>/<class_id>/<int:draw_index>')
def get_live_elimination_html(tournament_id, class_id, draw_index):
    """Elimination HTML"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return "<html><body><h1>Турнир не найден</h1></body></html>", 404

        xml_types = api.get_xml_data_types(tournament_data)
        xml_type_info = next((t for t in xml_types if t.get("type") == "tournament_table" and 
                             t.get("draw_type") == "elimination" and t.get("class_id") == class_id and 
                             t.get("draw_index") == draw_index), None)
        if not xml_type_info:
            return "<html><body><h1>Сетка не найдена</h1></body></html>", 404

        html = xml_manager.html_generator.generate_elimination_html(tournament_data, xml_type_info)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

# === API: НАСТРОЙКИ И СТАТУС ===
@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Управление настройками"""
    from api import get_settings, save_settings
    
    if request.method == 'GET':
        return jsonify(get_settings())
    else:
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'error': 'Требуется аутентификация'}), 401
        save_settings(request.get_json())
        return jsonify({"success": True})


@app.route('/api/status')
def get_system_status():
    """Статус системы"""
    try:
        def get_counts(conn):
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tournaments WHERE status = ?', ('active',))
            tournaments = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM courts_data')
            courts = cursor.fetchone()[0]
            return tournaments, courts

        tournaments, courts = execute_with_retry(get_counts)
        
        return jsonify({
            "status": "running",
            "uptime": get_uptime(app.start_time),
            "active_tournaments": tournaments,
            "courts_data_count": courts,
            "auto_refresh": auto_refresh.running if 'auto_refresh' in globals() else False
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/refresh')
def refresh_all_data():
    """Принудительное обновление данных"""
    try:
        from api import get_active_tournament_ids, get_court_ids_for_tournament
        
        tournament_ids = get_active_tournament_ids()
        updated_courts = 0

        for tid in tournament_ids:
            court_ids = get_court_ids_for_tournament(tid)
            if court_ids:
                courts_data = api.get_all_courts_data(court_ids)
                if courts_data:
                    updated_courts += save_courts_data(tid, courts_data)

        return jsonify({
            "success": True,
            "updated_courts": updated_courts,
            "tournaments": len(tournament_ids)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === ФАЙЛЫ ===
@app.route('/html/<filename>')
def serve_html_file(filename):
    """Отдача HTML файлов"""
    try:
        return send_file(f'xml_files/{filename}', mimetype='text/html')
    except FileNotFoundError:
        return "<html><body><h1>Файл не найден</h1></body></html>", 404


@app.route('/api/html/schedule/<tournament_id>')
def generate_schedule_html(tournament_id):
    """Генерация HTML расписания"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404

        target_date = request.args.get('date')
        file_info = xml_manager.generate_and_save_schedule_html(tournament_data, target_date)
        return jsonify(file_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/html/<tournament_id>/<court_id>')
def generate_court_html(tournament_id, court_id):
    """Генерация HTML scoreboard для корта (файл)"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404

        court_data = api.get_court_scoreboard(str(court_id))
        if "error" in court_data:
            return jsonify({"error": "Ошибка получения данных корта"}), 500

        xml_type_info = {
            "id": f"court_{court_id}",
            "name": f"Корт {court_id} - Scoreboard HTML",
            "type": "court_score",
            "court_id": court_id,
            "court_name": court_data.get("court_name", f"Корт {court_id}")
        }

        file_info = xml_manager.generate_and_save_html(xml_type_info, tournament_data, court_data)
        return jsonify(file_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === ОТЛАДКА ===
@app.route('/api/debug/tournament/<tournament_id>')
def debug_tournament(tournament_id):
    """Отладочная информация"""
    try:
        class_id = request.args.get('class_id')
        debug_info = api.debug_tournament_structure(tournament_id, class_id)
        return jsonify({"success": True, "debug_info": debug_info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# === ОБРАБОТЧИКИ ОШИБОК ===
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Не найдено"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Внутренняя ошибка сервера"}), 500


# === ЗАПУСК ===
def create_app():
    init_database()
    return app


# Глобальный auto_refresh
auto_refresh = None

if __name__ == '__main__':
    init_database()
    
    auto_refresh = AutoRefreshService()
    auto_refresh.configure(app, api)
    auto_refresh.start()
    
    cfg = get_config()
    app.run(
        host=getattr(cfg, 'HOST', '0.0.0.0'),
        port=getattr(cfg, 'PORT', 5000),
        debug=getattr(cfg, 'DEBUG', False),
        threaded=True
    )
