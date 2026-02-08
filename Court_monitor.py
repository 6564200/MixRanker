#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скрипт для мониторинга состояний кортов rankedin.com"""

import sqlite3
import json
import time
import argparse
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# Добавляем текущую директорию в путь для импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CourtMonitor:
    """Мониторинг состояний кортов с записью изменений в БД"""
    
    def __init__(self, db_path: str = "court_states.db"):
        self.db_path = db_path
        self.api = RankedinAPI()
        self.last_states = {}  # Хранение предыдущих состояний
        self._init_db()
    
    def _init_db(self):
        """Инициализация БД"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS court_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    court_id TEXT NOT NULL,
                    court_name TEXT,
                    event_state TEXT,
                    current_match_state TEXT,
                    class_name TEXT,
                    first_participant TEXT,
                    second_participant TEXT,
                    first_participant_score INTEGER,
                    second_participant_score INTEGER,
                    detailed_result TEXT,
                    next_class_name TEXT,
                    next_first_participant TEXT,
                    next_second_participant TEXT,
                    next_start_time TEXT,
                    raw_data TEXT,
                    changed_fields TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_court_timestamp 
                ON court_states(court_id, timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_match_state 
                ON court_states(current_match_state)
            """)
            
            logger.info(f"БД инициализирована: {self.db_path}")
    
    def _has_changes(self, court_id: str, new_data: Dict) -> tuple[bool, List[str]]:
        """Проверка наличия изменений в данных корта"""
        if court_id not in self.last_states:
            return True, ["initial_state"]
        
        old = self.last_states[court_id]
        changed_fields = []
        
        # Ключевые поля для отслеживания
        compare_fields = [
            "current_match_state", "event_state", "class_name",
            "first_participant_score", "second_participant_score",
            "detailed_result", "next_class_name"
        ]
        
        for field in compare_fields:
            old_val = json.dumps(old.get(field), sort_keys=True)
            new_val = json.dumps(new_data.get(field), sort_keys=True)
            if old_val != new_val:
                changed_fields.append(field)
        
        return len(changed_fields) > 0, changed_fields
    
    def _save_state(self, data: Dict, changed_fields: List[str]):
        """Сохранение состояния в БД"""
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO court_states (
                    timestamp, court_id, court_name, event_state,
                    current_match_state, class_name,
                    first_participant, second_participant,
                    first_participant_score, second_participant_score,
                    detailed_result,
                    next_class_name, next_first_participant, next_second_participant,
                    next_start_time, raw_data, changed_fields
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                data.get("court_id"),
                data.get("court_name"),
                data.get("event_state"),
                data.get("current_match_state"),
                data.get("class_name"),
                json.dumps(data.get("first_participant", []), ensure_ascii=False),
                json.dumps(data.get("second_participant", []), ensure_ascii=False),
                data.get("first_participant_score"),
                data.get("second_participant_score"),
                json.dumps(data.get("detailed_result", []), ensure_ascii=False),
                data.get("next_class_name"),
                json.dumps(data.get("next_first_participant", []), ensure_ascii=False),
                json.dumps(data.get("next_second_participant", []), ensure_ascii=False),
                data.get("next_start_time"),
                json.dumps(data, ensure_ascii=False),
                json.dumps(changed_fields)
            ))
        
        logger.info(f"Корт {data.get('court_id')}: {data.get('current_match_state')} | Изменения: {', '.join(changed_fields)}")
    
    def monitor_courts(self, tournament_id: str, interval: int = 5, duration: Optional[int] = None):
        """
        Мониторинг кортов турнира
        
        Args:
            tournament_id: ID турнира
            interval: Интервал опроса в секундах
            duration: Длительность работы в секундах (None = бесконечно)
        """
        # Получаем список кортов
        logger.info(f"Получение списка кортов турнира {tournament_id}...")
        courts_info = self.api.get_tournament_courts(tournament_id)
        
        if not courts_info or "Courts" not in courts_info:
            logger.error("Не удалось получить список кортов")
            return
        
        court_ids = [str(c["Item1"]) for c in courts_info["Courts"] if isinstance(c, dict)]
        logger.info(f"Найдено кортов: {len(court_ids)} - {court_ids}")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while True:
                iteration += 1
                logger.info(f"\n=== Итерация {iteration} ===")
                
                for court_id in court_ids:
                    data = self.api.get_court_scoreboard(court_id)
                    
                    if "error" in data:
                        logger.warning(f"Корт {court_id}: {data['error']}")
                        continue
                    
                    has_changes, changed_fields = self._has_changes(court_id, data)
                    
                    if has_changes:
                        self._save_state(data, changed_fields)
                        self.last_states[court_id] = data
                    else:
                        logger.debug(f"Корт {court_id}: без изменений")
                
                # Проверка длительности
                if duration and (time.time() - start_time) >= duration:
                    logger.info(f"Достигнута максимальная длительность {duration}с")
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("\nОстановка мониторинга...")
        finally:
            self._print_statistics()
    
    def _print_statistics(self):
        """Вывод статистики"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    court_id,
                    COUNT(*) as changes,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM court_states
                GROUP BY court_id
            """)
            
            logger.info("\n=== Статистика ===")
            for row in cursor:
                logger.info(f"Корт {row[0]}: {row[1]} изменений ({row[2]} - {row[3]})")


def main():
    parser = argparse.ArgumentParser(description='Мониторинг состояний кортов rankedin.com')
    parser.add_argument('tournament_id', help='ID турнира')
    parser.add_argument('-i', '--interval', type=int, default=5, help='Интервал опроса (сек, по умолчанию 5)')
    parser.add_argument('-d', '--duration', type=int, help='Длительность работы (сек, по умолчанию бесконечно)')
    parser.add_argument('-db', '--database', default='court_states.db', help='Путь к БД')
    parser.add_argument('-v', '--verbose', action='store_true', help='Подробный вывод')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    monitor = CourtMonitor(args.database)
    monitor.monitor_courts(args.tournament_id, args.interval, args.duration)


if __name__ == "__main__":
    main()