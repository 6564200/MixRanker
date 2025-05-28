#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vMixRanker v2.0 - Главное приложение v6
Веб-сервис для интеграции данных турниров rankedin.com с vMix
"""

import os
import sys
import logging
import sqlite3
import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, render_template, Response, session
from werkzeug.exceptions import NotFound
from functools import wraps
import hashlib

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Создание необходимых директорий
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('xml_files', exist_ok=True)
os.makedirs('api', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/vmix_ranker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Импорты модулей приложения
try:
    from api.rankedin_api import RankedinAPI
    from api.xml_generator import XMLFileManager
except ImportError as e:
    logger.error(f"Ошибка импорта модулей: {e}")
    logger.info("Создайте файлы api/rankedin_api.py и api/xml_generator.py из артефактов")
    sys.exit(1)

# Создание Flask приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'vmix-ranker-v2-secret-key'
app.config['SESSION_TYPE'] = 'filesystem'

# Глобальные объекты
api = RankedinAPI()
xml_manager = XMLFileManager('xml_files')

# База данных
DATABASE_PATH = 'data/tournaments.db'

def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            metadata TEXT,
            classes TEXT,
            courts TEXT,
            dates TEXT,
            draw_data TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS courts_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL,
            court_id TEXT NOT NULL,
            court_name TEXT,
            event_state TEXT,
            class_name TEXT,
            first_participant_score INTEGER DEFAULT 0,
            second_participant_score INTEGER DEFAULT 0,
            detailed_result TEXT,
            first_participant TEXT,
            second_participant TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
            UNIQUE(tournament_id, court_id)
        );
        
        CREATE TABLE IF NOT EXISTS xml_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id TEXT NOT NULL,
            xml_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            size TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
        );
        
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
        
        -- Создаем админа по умолчанию (пароль: admin123)
        INSERT OR IGNORE INTO users (username, password, role) 
        VALUES ('admin', 'admin123', 'admin');
        
        -- Индексы для производительности
        CREATE INDEX IF NOT EXISTS idx_courts_tournament ON courts_data(tournament_id);
        CREATE INDEX IF NOT EXISTS idx_courts_updated ON courts_data(updated_at);
        CREATE INDEX IF NOT EXISTS idx_xml_tournament ON xml_files(tournament_id);
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

# Декоратор для проверки аутентификации
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'error': 'Требуется аутентификация', 'auth_required': True}), 401
        return f(*args, **kwargs)
    return decorated_function

# Функция проверки пользователя
def check_user_credentials(username, password):
    """Проверяет учетные данные пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and user['password'] == password:
            # Обновляем время последнего входа
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?', (username,))
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Ошибка проверки пользователя: {e}")
        return False

def get_db_connection():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Роуты для аутентификации

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Авторизация пользователя"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Введите имя пользователя и пароль'}), 400
        
        if check_user_credentials(username, password):
            session['authenticated'] = True
            session['username'] = username
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=24)
            
            return jsonify({
                'success': True, 
                'message': 'Успешная авторизация',
                'username': username
            })
        else:
            return jsonify({'error': 'Неверные учетные данные'}), 401
            
    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        return jsonify({'error': 'Ошибка сервера'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    session.clear()
    return jsonify({'success': True, 'message': 'Выход выполнен'})

@app.route('/api/auth/status')
def auth_status():
    """Проверка статуса аутентификации"""
    if 'authenticated' in session and session['authenticated']:
        return jsonify({
            'authenticated': True, 
            'username': session.get('username', '')
        })
    else:
        return jsonify({'authenticated': False})

# Роут для управления пользователями
@app.route('/api/users', methods=['GET', 'POST'])
@require_auth
def manage_users():
    """Управление пользователями (только для просмотра списка)"""
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, username, role, created_at, last_login FROM users ORDER BY username')
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row['id'],
                    'username': row['username'],
                    'role': row['role'],
                    'created_at': row['created_at'],
                    'last_login': row['last_login']
                })
            
            conn.close()
            return jsonify(users)
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        # Добавление нового пользователя
        try:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            if not username or not password:
                return jsonify({'error': 'Имя пользователя и пароль обязательны'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                          (username, password, 'admin'))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': f'Пользователь {username} создан'})
            
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {e}")
            return jsonify({'error': str(e)}), 500

# === ОСНОВНЫЕ РОУТЫ ===
@app.route('/')
def index():
    """Главная страница с полным интерфейсом"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Ошибка загрузки шаблона: {e}")
        # Fallback на простую страницу если шаблон не найден
        return simple_html_page()
        
# Роут для статических файлов 
@app.route('/static/<path:filename>')
def static_files(filename):
    """Обслуживание статических файлов"""
    from flask import send_from_directory
    return send_from_directory('static', filename)
        
@app.route('/simple')
def simple_html_page():
    """Главная страница"""
    try:
        # Простая HTML страница с информацией
        html_content = '''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>vMixRanker v2.0</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                .info { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .api-list { background: #f5f5f5; padding: 15px; border-radius: 8px; }
                code { background: #ffeb3b; padding: 2px 4px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>🏆 vMixRanker v2.0</h1>
            <div class="info">
                <h3>Система интеграции турниров rankedin.com с vMix</h3>
                <p><strong>Статус:</strong> ✅ Работает</p>
                <p><strong>Версия:</strong> 2.0.0</p>
                <p><strong>Время запуска:</strong> ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
            </div>
            
            <h3>📋 API Endpoints:</h3>
            <div class="api-list">
                <p><strong>Турниры:</strong></p>
                <ul>
                    <li><code>POST /api/tournament/&lt;id&gt;</code> - Загрузка турнира</li>
                    <li><code>GET /api/tournaments</code> - Список турниров</li>
                    <li><code>DELETE /api/tournament/&lt;id&gt;</code> - Удаление турнира</li>
                </ul>
                
                <p><strong>Корты:</strong></p>
                <ul>
                    <li><code>GET /api/tournament/&lt;id&gt;/courts</code> - Данные кортов</li>
                </ul>
                
                <p><strong>XML Generation:</strong></p>
                <ul>
                    <li><code>GET /api/tournament/&lt;id&gt;/xml-types</code> - Доступные типы XML</li>
                    <li><code>GET /api/xml/&lt;tournament_id&gt;/&lt;type_id&gt;</code> - Генерация XML</li>
                    <li><code>GET /api/xml-live/&lt;tournament_id&gt;/&lt;type_id&gt;</code> - Live XML данные</li>
                    <li><code>POST /api/xml/&lt;id&gt;/all</code> - Генерация всех XML</li>
                </ul>
                
                <p><strong>Система:</strong></p>
                <ul>
                    <li><code>GET /api/status</code> - Статус системы</li>
                    <li><code>GET /api/refresh</code> - Обновление данных</li>
                    <li><code>GET/POST /api/settings</code> - Настройки</li>
                </ul>
            </div>
            
            <h3>🔗 Использование с vMix:</h3>
            <div class="info">
                <p><strong>Статичные файлы:</strong> <code>http://localhost:5000/xml/filename.xml</code></p>
                <p><strong>Live данные:</strong> <code>http://localhost:5000/api/xml-live/tournament_id/xml_type</code></p>
                <p><strong>Интерфейс:</strong> Скопируйте HTML код из артефакта в templates/index.html</p>
            </div>
        </body>
        </html>
        '''
        return html_content
    except Exception as e:
        logger.error(f"Ошибка главной страницы: {e}")
        return f"<h1>vMixRanker v2.0</h1><p>Ошибка: {e}</p>"

# === API РОУТЫ ===

@app.route('/api/tournament/<tournament_id>', methods=['POST'])
@require_auth
def load_tournament(tournament_id):
    """Загрузка турнира"""
    try:
        logger.info(f"Начало загрузки турнира {tournament_id}")
        
        # Получение полных данных турнира
        tournament_data = api.get_full_tournament_data(tournament_id)
        
        if not tournament_data.get("metadata"):
            return jsonify({
                "success": False,
                "error": "Не удалось получить данные турнира. Проверьте ID турнира."
            }), 400
        
        # Сохранение в базу данных
        conn = get_db_connection()
        cursor = conn.cursor()
        
        metadata = tournament_data.get("metadata", {})
        
        cursor.execute('''
            INSERT OR REPLACE INTO tournaments 
            (id, name, metadata, classes, courts, dates, draw_data, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            tournament_id,
            metadata.get("name", f"Турнир {tournament_id}"),
            json.dumps(metadata),
            json.dumps(tournament_data.get("classes", [])),
            json.dumps(tournament_data.get("courts", [])),
            json.dumps(tournament_data.get("dates", [])),
            json.dumps(tournament_data.get("draw_data", {})),
            "active"
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Турнир {tournament_id} успешно загружен")
        
        return jsonify({
            "success": True,
            "tournament_id": tournament_id,
            "name": metadata.get("name", f"Турнир {tournament_id}"),
            "sport": get_sport_name(metadata.get("sport", 5)),
            "country": metadata.get("country"),
            "categories": len(tournament_data.get("classes", [])),
            "courts": len(tournament_data.get("courts", [])),
            "message": "Турнир успешно загружен"
        })
        
    except Exception as e:
        logger.error(f"Ошибка загрузки турнира {tournament_id}: {e}")
        return jsonify({
            "success": False,
            "error": f"Ошибка загрузки турнира: {str(e)}"
        }), 500

@app.route('/api/tournaments')
def get_tournaments():
    """Получение списка загруженных турниров"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, metadata, status, created_at, updated_at
            FROM tournaments
            ORDER BY updated_at DESC
        ''')
        
        tournaments = []
        for row in cursor.fetchall():
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
            
            tournaments.append({
                "id": row['id'],
                "name": row['name'],
                "sport": metadata.get("sport", 5),
                "country": metadata.get("country"),
                "banner": metadata.get("featureImage"),
                "status": row['status'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at'],
                "courts": 0,
                "categories": 0
            })
        
        conn.close()
        return jsonify(tournaments)
        
    except Exception as e:
        logger.error(f"Ошибка получения турниров: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tournament/<tournament_id>/courts')
def get_tournament_courts(tournament_id):
    """Получение данных кортов турнира"""
    try:
        # Получение информации о кортах из базы
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT courts FROM tournaments WHERE id = ?', (tournament_id,))
        tournament_row = cursor.fetchone()
        
        if not tournament_row:
            return jsonify({"error": "Турнир не найден"}), 404
        
        courts_info = json.loads(tournament_row['courts']) if tournament_row['courts'] else []
        
        if not courts_info:
            return jsonify([])
        
        # Получение актуальных данных кортов через API
        court_ids = [str(court.get("Item1")) for court in courts_info if court.get("Item1")]
        courts_data = api.get_all_courts_data(court_ids)
        
        # Сохранение обновленных данных в базу
        for court_data in courts_data:
            if "error" not in court_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO courts_data 
                    (tournament_id, court_id, court_name, event_state, class_name,
                     first_participant_score, second_participant_score, 
                     detailed_result, first_participant, second_participant, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    tournament_id,
                    str(court_data["court_id"]),
                    court_data["court_name"],
                    court_data["event_state"],
                    court_data["class_name"],
                    court_data["first_participant_score"],
                    court_data["second_participant_score"],
                    json.dumps(court_data["detailed_result"]),
                    json.dumps(court_data["first_participant"]),
                    json.dumps(court_data["second_participant"])
                ))
        
        conn.commit()
        conn.close()
        
        return jsonify(courts_data)
        
    except Exception as e:
        logger.error(f"Ошибка получения кортов для турнира {tournament_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tournament/<tournament_id>/xml-types')
def get_xml_types(tournament_id):
    """Получение доступных типов XML для турнира"""
    try:
        # Получение данных турнира из базы
        tournament_data = get_tournament_data_from_db(tournament_id)
        
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404
        
        # Генерация типов XML
        xml_types = api.get_xml_data_types(tournament_data)
        
        return jsonify(xml_types)
        
    except Exception as e:
        logger.error(f"Ошибка получения типов XML для турнира {tournament_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/xml/<tournament_id>/<xml_type_id>')
def generate_xml(tournament_id, xml_type_id):
    """Генерация конкретного XML файла"""
    try:
        # Получение данных турнира
        tournament_data = get_tournament_data_from_db(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404
        
        # Получение информации о типе XML
        xml_types = api.get_xml_data_types(tournament_data)
        xml_type_info = next((t for t in xml_types if t["id"] == xml_type_id), None)
        
        if not xml_type_info:
            return jsonify({"error": "Неизвестный тип XML"}), 400
        
        # Генерация XML
        if xml_type_info["type"] == "court_score":
            # Для корта нужны актуальные данные
            court_id = xml_type_info.get("court_id")
            court_data = api.get_court_scoreboard(str(court_id))
            if "error" in court_data:
                return jsonify({"error": "Ошибка получения данных корта"}), 500
            
            file_info = xml_manager.generate_and_save(xml_type_info, tournament_data, court_data)
        else:
            # Для турнирных таблиц получаем свежие данные из API
            if xml_type_info["type"] == "tournament_table":
                # Обновляем данные турнира перед генерацией
                class_id = xml_type_info.get("class_id")
                draw_type = xml_type_info.get("draw_type")
                
                if draw_type == "round_robin":
                    fresh_data = api.get_round_robin_draws(str(class_id))
                elif draw_type == "elimination":
                    fresh_data = api.get_elimination_draws(str(class_id))
                else:
                    fresh_data = None
                
                # Обновляем данные в tournament_data
                if fresh_data and tournament_data.get("draw_data", {}).get(str(class_id)):
                    if draw_type == "round_robin":
                        tournament_data["draw_data"][str(class_id)]["round_robin"] = fresh_data
                    elif draw_type == "elimination":
                        tournament_data["draw_data"][str(class_id)]["elimination"] = fresh_data
            
            file_info = xml_manager.generate_and_save(xml_type_info, tournament_data)
        
        # Сохранение информации о файле в базу
        save_xml_file_info(tournament_id, file_info)
        
        return jsonify(file_info)
        
    except Exception as e:
        logger.error(f"Ошибка генерации XML {xml_type_id} для турнира {tournament_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/xml-live/<tournament_id>/<xml_type_id>')
def get_live_xml_data(tournament_id, xml_type_id):
    """Получение актуальных XML данных без сохранения файла"""
    try:
        # Получение данных турнира
        tournament_data = get_tournament_data_from_db(tournament_id)
        if not tournament_data:
            return Response("<!-- Турнир не найден -->", mimetype='application/xml'), 404
        
        # Получение информации о типе XML
        xml_types = api.get_xml_data_types(tournament_data)
        xml_type_info = next((t for t in xml_types if t["id"] == xml_type_id), None)
        
        if not xml_type_info:
            return Response("<!-- Неизвестный тип XML -->", mimetype='application/xml'), 400
        
        # Генерация XML без сохранения
        xml_content = ""
        
        if xml_type_info["type"] == "court_score":
            court_id = xml_type_info.get("court_id")
            court_data = api.get_court_scoreboard(str(court_id))
            if "error" not in court_data:
                xml_content = xml_manager.generator.generate_court_score_xml(court_data, tournament_data)
        
        elif xml_type_info["type"] == "tournament_table":
            # Получаем свежие данные
            class_id = xml_type_info.get("class_id")
            draw_type = xml_type_info.get("draw_type")
            
            if draw_type == "round_robin":
                fresh_data = api.get_round_robin_draws(str(class_id))
                if fresh_data:
                    tournament_data["draw_data"][str(class_id)]["round_robin"] = fresh_data
            elif draw_type == "elimination":
                fresh_data = api.get_elimination_draws(str(class_id))
                if fresh_data:
                    tournament_data["draw_data"][str(class_id)]["elimination"] = fresh_data
            
            xml_content = xml_manager.generator.generate_tournament_table_xml(tournament_data, xml_type_info)
        
        elif xml_type_info["type"] == "schedule":
            xml_content = xml_manager.generator.generate_schedule_xml(tournament_data)
        
        # Возвращаем XML как текст
        return Response(xml_content, mimetype='application/xml; charset=utf-8')
        
    except Exception as e:
        logger.error(f"Ошибка получения live XML {xml_type_id} для турнира {tournament_id}: {e}")
        return Response(f"<!-- Ошибка: {str(e)} -->", mimetype='application/xml'), 500

@app.route('/api/tournament/<tournament_id>/live-xml-info')
def get_live_xml_info(tournament_id):
    """Получение информации о всех доступных live XML для турнира"""
    try:
        tournament_data = get_tournament_data_from_db(tournament_id)
        if not tournament_data:
            logger.error(f"Турнир {tournament_id} не найден в базе данных")
            return jsonify({"error": "Турнир не найден"}), 404
        
        # Дополнительная проверка структуры данных
        if not isinstance(tournament_data, dict):
            logger.error(f"Данные турнира {tournament_id} имеют неверный формат: {type(tournament_data)}")
            return jsonify({"error": "Неверный формат данных турнира"}), 500
        
        # Логируем структуру для отладки
        logger.info(f"Структура данных турнира {tournament_id}: metadata={tournament_data.get('metadata') is not None}, draw_data={tournament_data.get('draw_data') is not None}")
        
        xml_types = api.get_xml_data_types(tournament_data)
        
        if not xml_types:
            logger.warning(f"Не найдено доступных XML типов для турнира {tournament_id}")
            xml_types = []
        
        live_xml_info = []
        for xml_type in xml_types:
            if not isinstance(xml_type, dict):
                logger.warning(f"Пропускаем неверный XML тип: {xml_type}")
                continue
                
            live_xml_info.append({
                "id": xml_type.get("id", ""),
                "name": xml_type.get("name", ""),
                "type": xml_type.get("type", ""),
                "live_url": f"/api/xml-live/{tournament_id}/{xml_type.get('id', '')}",
                "vmix_url": f"http://localhost:5000/api/xml-live/{tournament_id}/{xml_type.get('id', '')}",
                "description": get_xml_type_description(xml_type.get("type", "")),
                "update_frequency": get_update_frequency(xml_type.get("type", ""))
            })
        
        # Безопасное получение названия турнира
        tournament_name = "Неизвестный турнир"
        if tournament_data.get("metadata") and isinstance(tournament_data["metadata"], dict):
            tournament_name = tournament_data["metadata"].get("name", "Неизвестный турнир")
        
        return jsonify({
            "tournament_id": tournament_id,
            "tournament_name": tournament_name,
            "live_xml_count": len(live_xml_info),
            "live_xml_types": live_xml_info,
            "base_url": f"http://localhost:5000/api/xml-live/{tournament_id}/",
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения live XML info для турнира {tournament_id}: {e}")
        logger.error(f"Детали ошибки: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/xml/<tournament_id>/all', methods=['POST'])
def generate_all_xml(tournament_id):
    """Генерация всех XML файлов для турнира"""
    try:
        # Получение данных турнира
        tournament_data = get_tournament_data_from_db(tournament_id)
        if not tournament_data:
            return jsonify({"error": "Турнир не найден"}), 404
        
        # Получение актуальных данных кортов
        court_ids = [str(court.get("Item1")) for court in tournament_data.get("courts", []) if court.get("Item1")]
        courts_data = api.get_all_courts_data(court_ids) if court_ids else []
        
        # Генерация всех XML файлов
        generated_files = xml_manager.generate_all_tournament_xml(tournament_data, courts_data)
        
        # Сохранение информации о файлах в базу
        for file_info in generated_files:
            save_xml_file_info(tournament_id, file_info)
        
        return jsonify(generated_files)
        
    except Exception as e:
        logger.error(f"Ошибка массовой генерации XML для турнира {tournament_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tournament/<tournament_id>', methods=['DELETE'])
@require_auth
def delete_tournament(tournament_id):
    """Удаление турнира"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Удаление связанных данных
        cursor.execute('DELETE FROM courts_data WHERE tournament_id = ?', (tournament_id,))
        cursor.execute('DELETE FROM xml_files WHERE tournament_id = ?', (tournament_id,))
        cursor.execute('DELETE FROM tournaments WHERE id = ?', (tournament_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Турнир {tournament_id} удален")
        return jsonify({"success": True, "message": "Турнир удален"})
        
    except Exception as e:
        logger.error(f"Ошибка удаления турнира {tournament_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/xml/<filename>')
def serve_xml_file(filename):
    """Отдача XML файлов с динамическим обновлением"""
    try:
        # Парсим имя файла для получения информации о турнире
        parts = filename.replace('.xml', '').split('_')
        
        if len(parts) >= 2:
            tournament_id = parts[0]
            xml_type = parts[1]
            
            # Если это файл корта или турнирной таблицы, обновляем данные
            if xml_type in ['court', 'table']:
                tournament_data = get_tournament_data_from_db(tournament_id)
                if tournament_data:
                    try:
                        # Определяем тип XML и регенерируем
                        if xml_type == 'court' and len(parts) >= 3:
                            court_id = parts[2]
                            court_data = api.get_court_scoreboard(court_id)
                            if court_data and "error" not in court_data:
                                xml_content = xml_manager.generator.generate_court_score_xml(court_data, tournament_data)
                                
                                # Сохраняем обновленный файл
                                filepath = f'xml_files/{filename}'
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    f.write(xml_content)
                        
                        elif xml_type == 'table':
                            # Регенерируем турнирную таблицу с актуальными данными
                            xml_types = api.get_xml_data_types(tournament_data)
                            for xml_type_info in xml_types:
                                if xml_type_info["id"] in filename:
                                    # Получаем свежие данные
                                    class_id = xml_type_info.get("class_id")
                                    draw_type = xml_type_info.get("draw_type")
                                    
                                    if draw_type == "round_robin":
                                        fresh_data = api.get_round_robin_draws(str(class_id))
                                        if fresh_data:
                                            tournament_data["draw_data"][str(class_id)]["round_robin"] = fresh_data
                                    elif draw_type == "elimination":
                                        fresh_data = api.get_elimination_draws(str(class_id))
                                        if fresh_data:
                                            tournament_data["draw_data"][str(class_id)]["elimination"] = fresh_data
                                    
                                    xml_content = xml_manager.generator.generate_tournament_table_xml(tournament_data, xml_type_info)
                                    
                                    filepath = f'xml_files/{filename}'
                                    with open(filepath, 'w', encoding='utf-8') as f:
                                        f.write(xml_content)
                                    break
                                    
                    except Exception as e:
                        logger.error(f"Ошибка обновления XML файла {filename}: {e}")
        
        # Отдаем файл
        return send_file(f'xml_files/{filename}', 
                        mimetype='application/xml',
                        as_attachment=False,
                        download_name=filename)
    except FileNotFoundError:
        return Response("<!-- XML файл не найден -->", mimetype='application/xml'), 404
    except Exception as e:
        logger.error(f"Ошибка отдачи XML файла {filename}: {e}")
        return Response(f"<!-- Ошибка: {str(e)} -->", mimetype='application/xml'), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Управление настройками"""
    if request.method == 'GET':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT key, value FROM settings')
            settings_rows = cursor.fetchall()
            
            settings = {}
            for row in settings_rows:
                try:
                    settings[row['key']] = json.loads(row['value'])
                except json.JSONDecodeError:
                    settings[row['key']] = row['value']
            
            # Настройки по умолчанию
            default_settings = {
                "refresh_interval": 30,
                "auto_refresh": True,
                "debug_mode": False,
                "theme": "light",
                "xml_cleanup_hours": 24
            }
            
            # Объединение с дефолтными настройками
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            
            conn.close()
            return jsonify(settings)
            
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        
        # POST запросы ТРЕБУЮТ аутентификации
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'error': 'Требуется аутентификация', 'auth_required': True}), 401
            
        try:
            settings = request.get_json()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for key, value in settings.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, json.dumps(value)))
            
            conn.commit()
            conn.close()
            
            return jsonify({"success": True, "message": "Настройки сохранены"})
            
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def get_system_status():
    """Получение статуса системы"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Статистика
        cursor.execute('SELECT COUNT(*) FROM tournaments')
        tournament_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM courts_data')
        court_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM xml_files')
        xml_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT MAX(updated_at) FROM courts_data')
        last_update = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "status": "active",
            "version": "2.0.0",
            "tournaments": tournament_count,
            "courts": court_count,
            "xml_files": xml_count,
            "last_update": last_update,
            "uptime": get_uptime()
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/refresh')
def refresh_all_data():
    """Обновление всех данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получение всех активных турниров
        cursor.execute('SELECT id FROM tournaments WHERE status = ?', ('active',))
        tournament_ids = [row[0] for row in cursor.fetchall()]
        
        updated_courts = 0
        updated_tables = 0
        
        for tournament_id in tournament_ids:
            try:
                # 1. Обновление данных кортов
                cursor.execute('SELECT courts FROM tournaments WHERE id = ?', (tournament_id,))
                tournament_row = cursor.fetchone()
                
                if tournament_row and tournament_row[0]:
                    courts_info = json.loads(tournament_row[0])
                    court_ids = [str(court.get("Item1")) for court in courts_info if court.get("Item1")]
                    
                    # Обновление данных кортов
                    courts_data = api.get_all_courts_data(court_ids)
                    
                    for court_data in courts_data:
                        if "error" not in court_data:
                            cursor.execute('''
                                INSERT OR REPLACE INTO courts_data 
                                (tournament_id, court_id, court_name, event_state, class_name,
                                 first_participant_score, second_participant_score, 
                                 detailed_result, first_participant, second_participant, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            ''', (
                                tournament_id,
                                str(court_data["court_id"]),
                                court_data["court_name"],
                                court_data["event_state"],
                                court_data["class_name"],
                                court_data["first_participant_score"],
                                court_data["second_participant_score"],
                                json.dumps(court_data["detailed_result"]),
                                json.dumps(court_data["first_participant"]),
                                json.dumps(court_data["second_participant"])
                            ))
                            updated_courts += 1
                
                # 2. Обновление турнирных таблиц
                cursor.execute('SELECT draw_data FROM tournaments WHERE id = ?', (tournament_id,))
                draw_data_row = cursor.fetchone()
                
                if draw_data_row and draw_data_row[0]:
                    draw_data = json.loads(draw_data_row[0])
                    updated_draw_data = {}
                    
                    for class_id, class_data in draw_data.items():
                        updated_draw_data[class_id] = class_data.copy()
                        
                        # Обновляем Round Robin данные
                        if class_data.get("round_robin"):
                            fresh_rr_data = api.get_round_robin_draws(class_id)
                            if fresh_rr_data:
                                updated_draw_data[class_id]["round_robin"] = fresh_rr_data
                                updated_tables += 1
                        
                        # Обновляем Elimination данные
                        if class_data.get("elimination"):
                            fresh_elim_data = api.get_elimination_draws(class_id)
                            if fresh_elim_data:
                                updated_draw_data[class_id]["elimination"] = fresh_elim_data
                                updated_tables += 1
                    
                    # Сохраняем обновленные данные
                    if updated_draw_data != draw_data:
                        cursor.execute('''
                            UPDATE tournaments 
                            SET draw_data = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE id = ?
                        ''', (json.dumps(updated_draw_data), tournament_id))
                        
            except Exception as e:
                logger.error(f"Ошибка обновления турнира {tournament_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "updated_courts": updated_courts,
            "updated_tables": updated_tables,
            "tournaments": len(tournament_ids),
            "updated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка обновления данных: {e}")
        return jsonify({"error": str(e)}), 500

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_tournament_data_from_db(tournament_id: str) -> dict:
    """Получение данных турнира из базы данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT metadata, classes, courts, dates, draw_data 
            FROM tournaments WHERE id = ?
        ''', (tournament_id,))
        
        tournament_row = cursor.fetchone()
        conn.close()
        
        if not tournament_row:
            logger.warning(f"Турнир {tournament_id} не найден в базе данных")
            return None
        
        # Безопасный парсинг JSON данных
        def safe_json_loads(json_str, default=None):
            if not json_str:
                return default if default is not None else {}
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Ошибка парсинга JSON: {e}")
                return default if default is not None else {}
        
        tournament_data = {
            "tournament_id": tournament_id,
            "metadata": safe_json_loads(tournament_row[0], {}),
            "classes": safe_json_loads(tournament_row[1], []),
            "courts": safe_json_loads(tournament_row[2], []),
            "dates": safe_json_loads(tournament_row[3], []),
            "draw_data": safe_json_loads(tournament_row[4], {})
        }
        
        logger.debug(f"Загружены данные турнира {tournament_id}: metadata={bool(tournament_data['metadata'])}, classes={len(tournament_data['classes'])}, draw_data={len(tournament_data['draw_data'])}")
        
        return tournament_data
        
    except Exception as e:
        logger.error(f"Ошибка получения данных турнира {tournament_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def save_xml_file_info(tournament_id: str, file_info: dict):
    """Сохранение информации о XML файле в базу данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO xml_files 
            (tournament_id, xml_type, filename, name, url, size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            tournament_id,
            file_info.get("type", ""),
            file_info.get("filename", ""),
            file_info.get("name", ""),
            file_info.get("url", ""),
            file_info.get("size", "")
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка сохранения информации о XML файле: {e}")

def get_uptime():
    """Получение времени работы приложения"""
    if hasattr(app, 'start_time'):
        uptime_seconds = time.time() - app.start_time
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        return f"{int(uptime_hours)}ч {int(uptime_minutes)}м"
    return "Неизвестно"

def get_sport_name(sport_id: int) -> str:
    """Возвращает название спорта по ID"""
    sports = {
        1: "Tennis",
        2: "Squash", 
        3: "Badminton",
        4: "Table Tennis",
        5: "Padel",
        6: "Beach Tennis",
        7: "Pickle Ball"
    }
    return sports.get(sport_id, "Unknown Sport")

def get_xml_type_description(xml_type):
    """Возвращает описание типа XML"""
    descriptions = {
        "court_score": "Актуальный счет и участники матча на корте",
        "tournament_table": "Турнирная таблица с результатами матчей",
        "schedule": "Расписание матчей по дням и времени"
    }
    return descriptions.get(xml_type, "Неизвестный тип XML")

def get_update_frequency(xml_type):
    """Возвращает частоту обновления для типа XML"""
    frequencies = {
        "court_score": "Каждый запрос (real-time)",
        "tournament_table": "Каждый запрос", 
        "schedule": "Каждый запрос"
    }
    return frequencies.get(xml_type, "По запросу")


# === АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ ===

class AutoRefreshService:
    """Сервис автоматического обновления данных"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.interval = 30  # секунды
    
    def start(self):
        """Запуск автоматического обновления"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self.thread.start()
            logger.info("Автоматическое обновление запущено")
    
    def stop(self):
        """Остановка автоматического обновления"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Автоматическое обновление остановлено")
    
    def _refresh_loop(self):
        """Цикл автоматического обновления"""
        while self.running:
            try:
                # Получение настроек
                with app.app_context():
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute('SELECT value FROM settings WHERE key = ?', ('auto_refresh',))
                    auto_refresh_row = cursor.fetchone()
                    
                    cursor.execute('SELECT value FROM settings WHERE key = ?', ('refresh_interval',))
                    interval_row = cursor.fetchone()
                    
                    # Проверка настроек
                    auto_refresh = True
                    if auto_refresh_row:
                        try:
                            auto_refresh = json.loads(auto_refresh_row[0])
                        except:
                            auto_refresh = True
                    
                    self.interval = 30
                    if interval_row:
                        try:
                            self.interval = json.loads(interval_row[0])
                        except:
                            self.interval = 30
                    
                    if auto_refresh:
                        # Получение всех активных турниров
                        cursor.execute('SELECT id FROM tournaments WHERE status = ?', ('active',))
                        tournament_ids = [row[0] for row in cursor.fetchall()]
                        
                        updated_courts = 0
                        updated_tables = 0
                        
                        for tournament_id in tournament_ids:
                            try:
                                # 1. Обновление данных кортов
                                cursor.execute('SELECT courts FROM tournaments WHERE id = ?', (tournament_id,))
                                tournament_row = cursor.fetchone()
                                
                                if tournament_row and tournament_row[0]:
                                    courts_info = json.loads(tournament_row[0])
                                    court_ids = [str(court.get("Item1")) for court in courts_info if court.get("Item1")]
                                    
                                    # Обновление данных кортов
                                    courts_data = api.get_all_courts_data(court_ids)
                                    
                                    for court_data in courts_data:
                                        if "error" not in court_data:
                                            cursor.execute('''
                                                INSERT OR REPLACE INTO courts_data 
                                                (tournament_id, court_id, court_name, event_state, class_name,
                                                 first_participant_score, second_participant_score, 
                                                 detailed_result, first_participant, second_participant, updated_at)
                                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                            ''', (
                                                tournament_id,
                                                str(court_data["court_id"]),
                                                court_data["court_name"],
                                                court_data["event_state"],
                                                court_data["class_name"],
                                                court_data["first_participant_score"],
                                                court_data["second_participant_score"],
                                                json.dumps(court_data["detailed_result"]),
                                                json.dumps(court_data["first_participant"]),
                                                json.dumps(court_data["second_participant"])
                                            ))
                                            updated_courts += 1
                                
                                # 2. Обновление турнирных таблиц
                                cursor.execute('SELECT draw_data FROM tournaments WHERE id = ?', (tournament_id,))
                                draw_data_row = cursor.fetchone()
                                
                                if draw_data_row and draw_data_row[0]:
                                    draw_data = json.loads(draw_data_row[0])
                                    updated_draw_data = {}
                                    
                                    for class_id, class_data in draw_data.items():
                                        updated_draw_data[class_id] = class_data.copy()
                                        
                                        # Обновляем Round Robin данные
                                        if class_data.get("round_robin"):
                                            fresh_rr_data = api.get_round_robin_draws(class_id)
                                            if fresh_rr_data:
                                                updated_draw_data[class_id]["round_robin"] = fresh_rr_data
                                                updated_tables += 1
                                        
                                        # Обновляем Elimination данные
                                        if class_data.get("elimination"):
                                            fresh_elim_data = api.get_elimination_draws(class_id)
                                            if fresh_elim_data:
                                                updated_draw_data[class_id]["elimination"] = fresh_elim_data
                                                updated_tables += 1
                                    
                                    # Сохраняем обновленные данные
                                    if updated_draw_data != draw_data:
                                        cursor.execute('''
                                            UPDATE tournaments 
                                            SET draw_data = ?, updated_at = CURRENT_TIMESTAMP 
                                            WHERE id = ?
                                        ''', (json.dumps(updated_draw_data), tournament_id))
                                        
                            except Exception as e:
                                logger.error(f"Ошибка обновления турнира {tournament_id}: {e}")
                                continue
                        
                        conn.commit()
                        if updated_courts > 0 or updated_tables > 0:
                            logger.debug(f"Автоматическое обновление: {updated_courts} кортов, {updated_tables} турнирных таблиц")
                    
                    conn.close()
                    
                    # Очистка старых XML файлов
                    try:
                        xml_manager.cleanup_old_files(24)
                    except:
                        pass
                
            except Exception as e:
                logger.error(f"Ошибка автоматического обновления: {e}")
            
            # Ожидание
            time.sleep(self.interval)

# === ОБРАБОТЧИКИ ОШИБОК ===

@app.route('/api/debug/tournament/<tournament_id>')
def debug_tournament(tournament_id):
    """Отладочная информация о структуре турнира"""
    try:
        class_id = request.args.get('class_id')
        
        debug_info = api.debug_tournament_structure(tournament_id, class_id)
        
        return jsonify({
            "success": True,
            "tournament_id": tournament_id,
            "debug_info": debug_info,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка отладки турнира {tournament_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/debug/tournament/<tournament_id>/raw-data/<class_id>')
def get_raw_tournament_data(tournament_id, class_id):
    """Получение сырых данных из API для отладки"""
    try:
        stage = int(request.args.get('stage', 0))
        strength = int(request.args.get('strength', 0))
        
        # Прямой запрос к API
        url = f"{api.api_base}/tournament/GetDrawsForStageAndStrengthAsync"
        params = f"?tournamentClassId={class_id}&drawStrength={strength}&drawStage={stage}&isReadonly=true&language=ru"
        
        result = api._make_request(url + params)
        
        analysis = {
            "total_items": len(result) if result and isinstance(result, list) else 0,
            "items_analysis": []
        }
        
        if result and isinstance(result, list):
            for i, item in enumerate(result):
                if isinstance(item, dict):
                    item_analysis = {
                        "index": i,
                        "BaseType": item.get("BaseType", "Unknown"),
                        "has_RoundRobin": item.get("RoundRobin") is not None,
                        "has_Elimination": item.get("Elimination") is not None,
                        "RatingId": item.get("RatingId", "")
                    }
                    
                    if item.get("Elimination"):
                        elim_info = item["Elimination"]
                        item_analysis["elimination_info"] = {
                            "Consolation": elim_info.get("Consolation", 0),
                            "PlacesStartPos": elim_info.get("PlacesStartPos", 1),
                            "PlacesEndPos": elim_info.get("PlacesEndPos", 1),
                            "DrawType": elim_info.get("DrawType", 0)
                        }
                    
                    analysis["items_analysis"].append(item_analysis)
        
        return jsonify({
            "success": True,
            "tournament_id": tournament_id,
            "class_id": class_id,
            "stage": stage,
            "strength": strength,
            "url": url + params,
            "analysis": analysis,
            "raw_data": result,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения сырых данных: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Страница не найдена"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Внутренняя ошибка сервера: {error}")
    return jsonify({"error": "Внутренняя ошибка сервера"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Необработанная ошибка: {e}")
    return jsonify({"error": "Произошла неожиданная ошибка"}), 500

# === ИНИЦИАЛИЗАЦИЯ И ЗАПУСК ===

def create_app():
    """Создание и настройка приложения"""
    # Инициализация базы данных
    init_database()
    
    # Время запуска
    app.start_time = time.time()
    
    # Запуск автоматического обновления
    auto_refresh = AutoRefreshService()
    auto_refresh.start()
    
    # Сохранение ссылки на сервис для остановки
    app.auto_refresh = auto_refresh
    
    logger.info("vMixRanker v2.0 инициализирован")
    return app

if __name__ == '__main__':
    # Создание приложения
    app = create_app()
    
    # Вывод информации о запуске
    print("=" * 60)
    print("🏆 vMixRanker v2.0 - Система интеграции турниров с vMix")
    print("=" * 60)
    print(f"🌐 Веб-интерфейс: http://localhost:5000")
    print(f"📊 API базовый URL: http://localhost:5000/api")
    print("🔗 Основные endpoints:")
    print("   POST /api/tournament/<id> - Загрузка турнира")
    print("   GET  /api/tournaments - Список турниров")
    print("   GET  /api/tournament/<id>/courts - Данные кортов")
    print("   GET  /api/xml/<id>/<type> - Генерация XML")
    print("   GET  /api/xml-live/<id>/<type> - Live XML данные")
    print("=" * 60)
    print("💡 Для остановки нажмите Ctrl+C")
    print("📝 Логи сохраняются в logs/vmix_ranker.log")
    print("=" * 60)
    
    try:
        # Запуск Flask приложения
        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки")
        if hasattr(app, 'auto_refresh'):
            app.auto_refresh.stop()
        print("✅ vMixRanker остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка запуска: {e}")
        print(f"❌ Ошибка запуска: {e}")
    finally:
        print("👋 До свидания!")