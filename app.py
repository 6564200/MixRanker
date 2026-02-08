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
from api.html_generator import HTMLGenerator

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
    get_sport_name, get_xml_type_description, get_update_frequency, get_uptime,
    save_tournament_matches, get_tournament_matches
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
html_generator = HTMLGenerator()

# Регистрация роутов аутентификации
register_auth_routes(app)

# Регистрация blueprints
from api.display_windows import display_bp
from api.composite_pages import composite_bp
app.register_blueprint(display_bp)
app.register_blueprint(composite_bp)


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
        
        # Загружаем матчи
        matches_data = api.get_tournament_matches(tournament_id)

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
            
            # Сохраняем матчи
            if matches_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO tournament_matches 
                    (tournament_id, matches_data, are_matches_published, is_schedule_published, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    tournament_id,
                    json.dumps(matches_data.get("Matches", [])),
                    1 if matches_data.get("AreMatchesPublished") else 0,
                    1 if matches_data.get("IsSchedulePublished") else 0
                ))

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
        # Удаляем композитные страницы
        from api.composite_pages import delete_composite_pages_for_tournament
        delete_composite_pages_for_tournament(tournament_id)
        
        def transaction(conn):
            cursor = conn.cursor()
            cursor.execute('DELETE FROM courts_data WHERE tournament_id = ?', (tournament_id,))
            cursor.execute('DELETE FROM xml_files WHERE tournament_id = ?', (tournament_id,))
            cursor.execute('DELETE FROM tournament_schedule WHERE tournament_id = ?', (tournament_id,))
            cursor.execute('DELETE FROM tournament_matches WHERE tournament_id = ?', (tournament_id,))
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
            
        # данными о следующем матче из court_usage
        tournament_data = get_tournament_data(tournament_id)
        if tournament_data:
            courts_data = _enrich_courts_with_next_match(courts_data, tournament_data)
            
        return jsonify(courts_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _enrich_courts_with_next_match(courts_data: list, tournament_data: dict) -> list:
    """Добавляет информацию о следующем матче из court_usage"""
    court_usage = tournament_data.get("court_usage", [])
    matches_data = tournament_data.get("matches_data", {})
    matches_list = matches_data.get("Matches", []) if isinstance(matches_data, dict) else []
    
    # Индекс матчей по ChallengeId для получения полных имён
    matches_index = {m.get("Id"): m for m in matches_list}
    
    from datetime import datetime
    
    for court in courts_data:
        if "error" in court:
            continue
            
        court_id = int(court.get("court_id", 0))
        
        # Фильтруем матчи этого корта
        court_matches = [m for m in court_usage if m.get("CourtId") == court_id]
        
        # Ищем матчи без результата, сортируем по времени
        pending_matches = []
        for match in court_matches:
            has_result = match.get("ChallengerResult") or match.get("ChallengedResult")
            if not has_result:
                match_date_str = match.get("MatchDate", "")
                try:
                    match_dt = datetime.fromisoformat(match_date_str.replace('Z', ''))
                    pending_matches.append((match_dt, match))
                except:
                    continue
        
        # Сортируем по времени
        pending_matches.sort(key=lambda x: x[0])
        
        # Следующий матч = первый без результата
        if pending_matches:
            next_match = pending_matches[0][1]
            challenge_id = next_match.get("ChallengeId")
            rich_match = matches_index.get(challenge_id, {})
            
            court["next_first_participant"] = _extract_players(rich_match.get("Challenger", {}))
            court["next_second_participant"] = _extract_players(rich_match.get("Challenged", {}))
            court["next_class_name"] = next_match.get("PoolName", "") or rich_match.get("Draw", "")
            court["next_start_time"] = next_match.get("MatchDate", "")
    
    return courts_data


def _extract_players(team_data: dict) -> list:
    """Извлекает список игроков из данных команды"""
    if not team_data:
        return []
    
    players = []
    name = team_data.get("Name", "")
    if name:
        parts = name.split()
        players.append({
            "firstName": parts[0] if parts else "",
            "lastName": " ".join(parts[1:]) if len(parts) > 1 else "",
            "countryCode": team_data.get("CountryShort", "")
        })
    
    name2 = team_data.get("Player2Name", "")
    if name2:
        parts = name2.split()
        players.append({
            "firstName": parts[0] if parts else "",
            "lastName": " ".join(parts[1:]) if len(parts) > 1 else "",
            "countryCode": team_data.get("Player2CountryShort", "")
        })
    
    return players


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
    """Загрузка и обработка фото участника"""
    from PIL import Image
    
    participant_id = request.form.get('participant_id')
    if not participant_id:
        return jsonify({"success": False, "error": "Не указан ID участника"}), 400

    # Сохраняем дополнительную информацию
    info = json.dumps({
        'country': request.form.get('country', ''),
        'rating': request.form.get('rating', ''),
        'height': request.form.get('height', ''),
        'position': request.form.get('position', ''),
        'full_name': request.form.get('english', '')
    })
    
    filename = f"{secure_filename(participant_id)}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    preview_url = f"/{UPLOAD_FOLDER}/{filename}"
    
    photo_saved = False
    
    # Если есть файл фото - обрабатываем
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename:
            try:
                # Параметры кропа из формы
                crop_x = float(request.form.get('crop_x', 0))
                crop_y = float(request.form.get('crop_y', 0))
                crop_scale = float(request.form.get('crop_scale', 1.0))
                
                # Целевые размеры
                OUTPUT_WIDTH = 1500
                OUTPUT_HEIGHT = 2048
                
                # Загружаем исходное изображение
                img = Image.open(file)
                
                # Конвертируем в RGBA
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Масштабируем исходное изображение
                scaled_width = int(img.width * crop_scale)
                scaled_height = int(img.height * crop_scale)
                
                if scaled_width > 0 and scaled_height > 0:
                    img_scaled = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                else:
                    img_scaled = img
                
                # Создаём прозрачный холст выходного размера
                canvas = Image.new('RGBA', (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
                
                # Вставляем масштабированное изображение
                paste_x = int(crop_x)
                paste_y = int(crop_y)
                canvas.paste(img_scaled, (paste_x, paste_y), img_scaled)
                
                # Сохраняем
                canvas.save(filepath, 'PNG', optimize=True)
                photo_saved = True
                logger.info(f"Фото участника {participant_id} сохранено: {filepath}")
                
            except Exception as e:
                logger.error(f"Ошибка обработки изображения: {e}")
                # Fallback: сохраняем оригинал
                try:
                    file.seek(0)
                    with open(filepath, 'wb') as f:
                        f.write(file.read())
                    photo_saved = True
                except Exception as e2:
                    logger.error(f"Fallback сохранение не удалось: {e2}")
    
    # Обновляем БД
    def update(conn):
        cursor = conn.cursor()
        if photo_saved:
            cursor.execute(
                'UPDATE participants SET photo_url = ?, info = ? WHERE id = ?',
                (preview_url, info, participant_id)
            )
        else:
            cursor.execute(
                'UPDATE participants SET info = ? WHERE id = ?',
                (info, participant_id)
            )
    
    execute_with_retry(update)
    
    return jsonify({
        "success": True,
        "preview_url": preview_url if photo_saved else None
    })


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


# === API: МАТЧИ ===
@app.route('/api/tournament/<tournament_id>/matches', methods=['GET'])
def get_matches(tournament_id):
    """Получение матчей турнира"""
    try:
        matches_data = get_tournament_matches(tournament_id)
        if not matches_data:
            return jsonify({"Matches": [], "AreMatchesPublished": False, "IsSchedulePublished": False})
        return jsonify(matches_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tournament/<tournament_id>/matches/reload', methods=['POST'])
def reload_tournament_matches(tournament_id):
    """Перезагрузка матчей турнира"""
    try:
        matches_data = api.get_tournament_matches(tournament_id)
        if not matches_data:
            return jsonify({"error": "Не удалось получить матчи"}), 400
        
        save_tournament_matches(tournament_id, matches_data)
        matches_count = len(matches_data.get("Matches", []))
        return jsonify({"success": True, "matches_count": matches_count})
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

        html = html_generator.generate_court_scoreboard_html(
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

        html = html_generator.generate_court_fullscreen_scoreboard_html(
            court_data, tournament_data, tournament_id, court_id
        )
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/<tournament_id>/<court_id>/score_full')
def get_live_court_score_full_html(tournament_id, court_id):
    """Полноэкранный scoreboard 4K/FHD/HD с логотипами и флагами"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        court_data = get_court_data(tournament_id, str(court_id))
        if not tournament_data or not court_data:
            return "<html><body><h1>Не найдено</h1></body></html>", 404

        html = html_generator.generate_scoreboard_full_html(
            court_data, tournament_data, tournament_id, court_id
        )
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        logger.error(f"Ошибка генерации score_full: {e}")
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/court/<tournament_id>/<court_id>/data')
def get_court_data_api(tournament_id, court_id):
    """JSON данные корта для AJAX обновления scoreboard"""
    try:
        court_data = get_court_data(tournament_id, str(court_id))
        if not court_data:
            return jsonify({"error": "Корт не найден"}), 404
        
        # Формируем данные для JS
        first_participant = court_data.get("first_participant", [])
        second_participant = court_data.get("second_participant", [])
        detailed_result = court_data.get("detailed_result", [])
        
        # Текущий счёт
        team1_score = court_data.get("first_participant_score", 0)
        team2_score = court_data.get("second_participant_score", 0)
        
        # Проверяем геймовый счёт в последнем сете
        if detailed_result:
            last_set = detailed_result[-1]
            game_score = last_set.get("gameScore", {})
            if game_score:
                team1_score = game_score.get("first", team1_score)
                team2_score = game_score.get("second", team2_score)
        
        return jsonify({
            "team1_players": first_participant,
            "team2_players": second_participant,
            "detailed_result": detailed_result,
            "team1_score": team1_score,
            "team2_score": team2_score,
            "event_state": court_data.get("event_state", ""),
            "court_name": court_data.get("court_name", ""),
            "class_name": court_data.get("class_name", "")
        })
    except Exception as e:
        logger.error(f"Ошибка получения данных корта: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/html-live/<tournament_id>/<court_id>/vs')
def get_court_vs_html(tournament_id, court_id):
    """VS страница с фото"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        court_data = get_court_data(tournament_id, str(court_id))
        if not tournament_data or not court_data:
            return "<html><body><h1>Не найдено</h1></body></html>", 404

        court_data = enrich_court_data_with_photos(court_data)
        html = html_generator.generate_court_vs_html(court_data, tournament_data)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/html-live/<tournament_id>/<court_id>/introduction')
def get_court_introduction_html(tournament_id, court_id):
    """Introduction страница - представление участников матча"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        court_data = get_court_data(tournament_id, str(court_id))
        if not tournament_data or not court_data:
            return "<html><body><h1>Не найдено</h1></body></html>", 404

        # Находим информацию о раунде из court_usage
        match_info = _find_current_match_info(tournament_data, court_id, court_data)
        
        html = html_generator.generate_match_introduction_html(court_data, match_info)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        logger.error(f"Ошибка генерации introduction: {e}")
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


def _find_current_match_info(tournament_data: dict, court_id: str, court_data: dict) -> dict:
    """
    Находит информацию о текущем матче из court_usage.
    Приоритет:
    1. Активный матч (идёт сейчас)
    2. Следующий матч (ещё не начался)
    3. Последний сыгранный (если нет будущих)
    """
    court_usage = tournament_data.get("court_usage", [])
    if not court_usage:
        return {}
    
    court_id_int = int(court_id) if court_id.isdigit() else 0
    
    from datetime import datetime
    now = datetime.now()
    
    # Фильтруем матчи только для этого корта
    court_matches = [m for m in court_usage if m.get("CourtId") == court_id_int]
    
    if not court_matches:
        return {}
    
    active_match = None
    next_match = None
    last_finished = None
    
    for match in court_matches:
        match_date_str = match.get("MatchDate", "")
        if not match_date_str:
            continue
            
        try:
            match_dt = datetime.fromisoformat(match_date_str.replace('Z', ''))
            duration = match.get("Duration", 30)
            match_end = match_dt.replace(minute=match_dt.minute + duration)
            
            has_result = match.get("ChallengerResult") or match.get("ChallengedResult")
            
            # Активный: время начала <= сейчас <= время конца, или время прошло но нет результата
            if match_dt <= now and (now <= match_end or not has_result):
                if not has_result:
                    active_match = match
                    break  # Активный матч - приоритет
            
            # Следующий: время в будущем, нет результата
            elif match_dt > now and not has_result:
                if next_match is None or match_dt < datetime.fromisoformat(next_match.get("MatchDate", "").replace('Z', '')):
                    next_match = match
            
            # Последний сыгранный: есть результат
            elif has_result:
                if last_finished is None or match_dt > datetime.fromisoformat(last_finished.get("MatchDate", "").replace('Z', '')):
                    last_finished = match
                    
        except Exception as e:
            logger.debug(f"Ошибка парсинга даты матча: {e}")
            continue
    
    # Возвращаем по приоритету
    if active_match:
        return active_match
    if next_match:
        return next_match
    if last_finished:
        return last_finished
    
    return {}


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

        html = html_generator.generate_next_match_page_html(court_data, tournament_data)
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

        html = html_generator.generate_winner_page_html(court_data, id_url, tournament_data)
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

        html = html_generator.generate_introduction_page_html(participant)
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
        from api import get_settings
        settings = get_settings()
        html = html_generator.generate_schedule_html(tournament_data, target_date, settings)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/schedule/<tournament_id>/data')
def get_schedule_data(tournament_id):
    """JSON данные расписания для AJAX обновлений"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404

        target_date = request.args.get('date')
        from api import get_settings
        settings = get_settings()
        
        # Получаем данные расписания
        schedule_data = html_generator.get_schedule_data(tournament_data, target_date, settings)
        
        # Генерируем hash для определения изменений
        import hashlib
        data_str = json.dumps(schedule_data, sort_keys=True, default=str)
        version = hashlib.md5(data_str.encode()).hexdigest()[:12]
        
        return jsonify({
            "version": version,
            "tournament_name": schedule_data.get("tournament_name", ""),
            "target_date": schedule_data.get("target_date", ""),
            "time_slots": schedule_data.get("time_slots", []),
            "courts": schedule_data.get("courts", []),
            "matches": schedule_data.get("matches", [])
        })
    except Exception as e:
        logger.error(f"Ошибка получения данных расписания: {e}")
        return jsonify({"error": str(e)}), 500

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

        html = html_generator.generate_round_robin_html(tournament_data, xml_type_info)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        logger.error(f"Ошибка round-robin HTML: {e}")
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

        html = html_generator.generate_elimination_html(tournament_data, xml_type_info)
        return Response(html, mimetype='text/html; charset=utf-8')
    except Exception as e:
        logger.error(f"Ошибка elimination HTML: {e}")
        return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500


@app.route('/api/elimination/<tournament_id>/<class_id>/data')
def get_elimination_data(tournament_id, class_id):
    """JSON данные elimination для AJAX обновлений"""
    try:
        tournament_data = get_tournament_data(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404

        draw_index = request.args.get('draw_index', 0, type=int)
        
        xml_types = api.get_xml_data_types(tournament_data)
        xml_type_info = next((t for t in xml_types if t.get("type") == "tournament_table" and 
                             t.get("draw_type") == "elimination" and t.get("class_id") == class_id and 
                             t.get("draw_index") == draw_index), None)
        
        if not xml_type_info:
            return jsonify({"error": "Сетка не найдена", "matches": []}), 404

        elimination_data = html_generator.get_elimination_data(tournament_data, xml_type_info)
        
        return jsonify(elimination_data)
    except Exception as e:
        logger.error(f"Ошибка получения данных elimination: {e}")
        return jsonify({"error": str(e)}), 500

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
