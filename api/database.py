#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Модуль работы с базой данных SQLite"""

import sqlite3
import json
import time
import logging
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)

DATABASE_PATH = 'data/tournaments.db'


def get_db_connection(max_retries: int = 2, base_delay: float = 0.05) -> sqlite3.Connection:
    """Получение соединения с базой данных с retry"""
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(DATABASE_PATH, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"БД заблокирована, попытка {attempt + 1}/{max_retries}, ждем {delay:.2f}с")
                time.sleep(delay)
            else:
                logger.error(f"Не удалось подключиться к БД после {max_retries} попыток: {e}")
                raise


def execute_with_retry(transaction_func: Callable, max_retries: int = 2) -> Any:
    """Выполнение транзакции с retry"""
    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_db_connection()
            result = transaction_func(conn)
            conn.commit()
            return result
        except sqlite3.OperationalError as e:
            if conn:
                conn.rollback()
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                delay = 0.1 * (2 ** attempt)
                logger.warning(f"Транзакция не выполнена, попытка {attempt + 1}/{max_retries}")
                time.sleep(delay)
            else:
                logger.error(f"Ошибка выполнения транзакции: {e}")
                raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Неожиданная ошибка в транзакции: {e}")
            raise
        finally:
            if conn:
                conn.close()


def init_database():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA cache_size = -64000")
        cursor.execute("PRAGMA foreign_keys = ON")

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
            
            CREATE TABLE IF NOT EXISTS tournament_schedule (
                tournament_id TEXT PRIMARY KEY,
                court_planner TEXT,
                court_usage TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id)
            );
            
            CREATE TABLE IF NOT EXISTS tournament_matches (
                tournament_id TEXT PRIMARY KEY,
                matches_data TEXT,
                are_matches_published INTEGER DEFAULT 0,
                is_schedule_published INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            
            INSERT OR IGNORE INTO users (username, password, role) 
            VALUES ('admin', 'admin123', 'admin');
            
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY,
                rankedin_id TEXT UNIQUE,
                first_name TEXT NOT NULL,
                middle_name TEXT,
                last_name TEXT NOT NULL,
                country_code TEXT NOT NULL,
                photo_url TEXT,
                info TEXT
            );
            
            CREATE TABLE IF NOT EXISTS participants_tournaments (
                participant_id INTEGER NOT NULL,
                tournament_id TEXT NOT NULL,
                PRIMARY KEY (participant_id, tournament_id),
                FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_courts_tournament ON courts_data(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_courts_updated ON courts_data(updated_at);
            CREATE INDEX IF NOT EXISTS idx_xml_tournament ON xml_files(tournament_id);
            CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);
            CREATE INDEX IF NOT EXISTS idx_tournaments_updated ON tournaments(updated_at);
        ''')

        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

        # Проверка WAL
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        conn.close()

        if journal_mode.upper() == 'WAL':
            logger.info("WAL режим активирован")

    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise


def _safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Безопасный парсинг JSON"""
    if not json_str:
        return default if default is not None else {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def get_tournament_data(tournament_id: str) -> Optional[Dict]:
    """Получение данных турнира из БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT metadata, classes, courts, dates, draw_data 
            FROM tournaments WHERE id = ?
        ''', (tournament_id,))
        tournament_row = cursor.fetchone()

        if not tournament_row:
            conn.close()
            return None

        cursor.execute('''
            SELECT court_planner, court_usage 
            FROM tournament_schedule WHERE tournament_id = ?
        ''', (tournament_id,))
        schedule_row = cursor.fetchone()

        cursor.execute('''
            SELECT matches_data, are_matches_published, is_schedule_published 
            FROM tournament_matches WHERE tournament_id = ?
        ''', (tournament_id,))
        matches_row = cursor.fetchone()
        conn.close()

        data = {
            "tournament_id": tournament_id,
            "metadata": _safe_json_loads(tournament_row[0], {}),
            "classes": _safe_json_loads(tournament_row[1], []),
            "courts": _safe_json_loads(tournament_row[2], []),
            "dates": _safe_json_loads(tournament_row[3], []),
            "draw_data": _safe_json_loads(tournament_row[4], {})
        }

        if schedule_row:
            data["court_planner"] = _safe_json_loads(schedule_row[0])
            data["court_usage"] = _safe_json_loads(schedule_row[1])

        if matches_row:
            data["matches_data"] = {
                "Matches": _safe_json_loads(matches_row[0], []),
                "AreMatchesPublished": bool(matches_row[1]),
                "IsSchedulePublished": bool(matches_row[2])
            }

        return data

    except Exception as e:
        logger.error(f"Ошибка получения турнира {tournament_id}: {e}")
        return None


def get_court_data(tournament_id: str, court_id: str) -> Optional[Dict]:
    """Получение данных корта из БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT court_id, court_name, event_state, class_name,
                   first_participant_score, second_participant_score, 
                   detailed_result, first_participant, second_participant, updated_at
            FROM courts_data 
            WHERE tournament_id = ? AND court_id = ?
        ''', (tournament_id, court_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"court_id": court_id, "error": "Корт не найден в БД"}

        return {
            "court_id": row[0],
            "court_name": row[1],
            "event_state": row[2],
            "class_name": row[3],
            "first_participant_score": row[4],
            "second_participant_score": row[5],
            "detailed_result": _safe_json_loads(row[6], []),
            "first_participant": _safe_json_loads(row[7], []),
            "second_participant": _safe_json_loads(row[8], []),
            "updated_at": row[9],
            "next_class_name": "",
            "next_first_participant": [],
            "next_second_participant": [],
            "next_start_time": ""
        }

    except Exception as e:
        logger.error(f"Ошибка получения корта {court_id}: {e}")
        return {"court_id": court_id, "error": str(e)}


def save_courts_data(tournament_id: str, courts_data: List[Dict]) -> int:
    """Сохранение данных кортов в БД"""
    def transaction(conn):
        cursor = conn.cursor()
        count = 0
        for court in courts_data:
            if "error" not in court:
                cursor.execute('''
                    INSERT OR REPLACE INTO courts_data 
                    (tournament_id, court_id, court_name, event_state, class_name,
                     first_participant_score, second_participant_score, 
                     detailed_result, first_participant, second_participant, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    tournament_id, str(court["court_id"]), court["court_name"],
                    court["event_state"], court["class_name"],
                    court["first_participant_score"], court["second_participant_score"],
                    json.dumps(court["detailed_result"]), json.dumps(court["first_participant"]),
                    json.dumps(court["second_participant"])
                ))
                count += 1
        return count

    return execute_with_retry(transaction)


def save_xml_file_info(tournament_id: str, file_info: Dict):
    """Сохранение информации о XML файле"""
    def transaction(conn):
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

    try:
        execute_with_retry(transaction)
    except Exception as e:
        logger.error(f"Ошибка сохранения XML info: {e}")


def get_active_tournament_ids() -> List[str]:
    """Получение ID активных турниров"""
    def transaction(conn):
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM tournaments WHERE status = ?', ('active',))
        return [row[0] for row in cursor.fetchall()]

    return execute_with_retry(transaction)


def get_court_ids_for_tournament(tournament_id: str) -> List[str]:
    """Получение ID кортов турнира"""
    def transaction(conn):
        cursor = conn.cursor()
        cursor.execute('SELECT courts FROM tournaments WHERE id = ?', (tournament_id,))
        row = cursor.fetchone()
        if row and row[0]:
            courts = json.loads(row[0])
            return [str(c.get("Item1")) for c in courts if c.get("Item1")]
        return []

    return execute_with_retry(transaction)


def get_settings() -> Dict:
    """Получение настроек"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        
        settings = {}
        for row in cursor.fetchall():
            try:
                settings[row['key']] = json.loads(row['value'])
            except json.JSONDecodeError:
                settings[row['key']] = row['value']
        
        conn.close()
        
        defaults = {
            "refreshInterval": 30,
            "autoRefresh": True,
            "debugMode": False,
            "theme": "light",
            "finishedMatchesCount": 3  # Количество последних сыгранных матчей в расписании
        }
        
        for key, value in defaults.items():
            if key not in settings:
                settings[key] = value
        
        return settings
    except Exception as e:
        logger.error(f"Ошибка получения настроек: {e}")
        return {"refreshInterval": 30, "autoRefresh": True}


def save_settings(settings: Dict):
    """Сохранение настроек"""
    def transaction(conn):
        cursor = conn.cursor()
        for key, value in settings.items():
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, json.dumps(value)))

    execute_with_retry(transaction)


def save_tournament_matches(tournament_id: str, matches_data: Dict):
    """Сохранение матчей турнира"""
    def transaction(conn):
        cursor = conn.cursor()
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
    execute_with_retry(transaction)


def get_tournament_matches(tournament_id: str) -> Optional[Dict]:
    """Получение матчей турнира из БД"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT matches_data, are_matches_published, is_schedule_published, updated_at
            FROM tournament_matches WHERE tournament_id = ?
        ''', (tournament_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return {
            "Matches": _safe_json_loads(row[0], []),
            "AreMatchesPublished": bool(row[1]),
            "IsSchedulePublished": bool(row[2]),
            "updated_at": row[3]
        }
    except Exception as e:
        logger.error(f"Ошибка получения матчей турнира {tournament_id}: {e}")
        return None
