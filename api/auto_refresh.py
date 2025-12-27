#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сервис автоматического обновления данных"""

import threading
import time
import json
import logging
from typing import List, Tuple

from .database import execute_with_retry, get_db_connection

logger = logging.getLogger(__name__)


class AutoRefreshService:
    """Сервис автоматического обновления данных с разными интервалами"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AutoRefreshService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.running = False
        self.thread = None
        self.base_interval = 30
        self.cycle_interval = 15

        self.cycle_counter = 0
        self.courts_update_frequency = 1
        self.tables_update_frequency = 2
        self.schedule_update_frequency = 4

        self._initialized = True
        self.app = None
        self.api = None

    def configure(self, app, api):
        """Конфигурация сервиса"""
        self.app = app
        self.api = api

    def start(self):
        """Запуск автоматического обновления"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self.thread.start()
            logger.info(f"AutoRefresh ЗАПУЩЕН: корты={self.cycle_interval}с, таблицы={self.base_interval}с")

    def stop(self):
        """Остановка автоматического обновления"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("AutoRefresh остановлен")

    def _refresh_loop(self):
        """Цикл автоматического обновления"""
        while self.running:
            try:
                with self.app.app_context():
                    self.cycle_counter += 1
                    auto_refresh, base_interval, tournament_ids = self._get_settings_and_tournaments()

                    if not auto_refresh or not tournament_ids:
                        time.sleep(self.cycle_interval)
                        continue

                    if base_interval != self.base_interval:
                        self._update_intervals(base_interval)

                    self._execute_updates(tournament_ids)

            except Exception as e:
                logger.error(f"AutoRefresh ошибка (цикл {self.cycle_counter}): {e}")

            time.sleep(self.cycle_interval)

    def _update_intervals(self, base_interval: int):
        """Обновление интервалов"""
        self.base_interval = base_interval
        self.cycle_interval = max(base_interval // 2, 5)
        self.tables_update_frequency = max(base_interval // self.cycle_interval, 1)
        self.schedule_update_frequency = max((base_interval * 2) // self.cycle_interval, 1)

    def _execute_updates(self, tournament_ids: List[str]):
        """Выполнение обновлений"""
        if self.cycle_counter % self.courts_update_frequency == 0:
            start = time.time()
            count = self._update_courts_data(tournament_ids)
            if count > 0:
                logger.info(f"КОРТЫ: обновлено {count} за {time.time() - start:.1f}с")

        if self.cycle_counter % self.tables_update_frequency == 0:
            start = time.time()
            count = self._update_tournament_tables(tournament_ids)
            if count > 0:
                logger.info(f"ТАБЛИЦЫ: обновлено {count} за {time.time() - start:.1f}с")

        if self.cycle_counter % self.schedule_update_frequency == 0:
            start = time.time()
            count = self._update_tournament_schedules(tournament_ids)
            if count > 0:
                logger.info(f"РАСПИСАНИЕ: обновлено {count} за {time.time() - start:.1f}с")

    def _get_settings_and_tournaments(self) -> Tuple[bool, int, List[str]]:
        """Получает настройки и список турниров"""
        def transaction(conn):
            cursor = conn.cursor()

            cursor.execute('SELECT value FROM settings WHERE key = ?', ('autoRefresh',))
            auto_row = cursor.fetchone()

            cursor.execute('SELECT value FROM settings WHERE key = ?', ('refreshInterval',))
            interval_row = cursor.fetchone()

            auto_refresh = True
            if auto_row:
                try:
                    auto_refresh = json.loads(auto_row[0])
                except:
                    pass

            interval = 30
            if interval_row:
                try:
                    interval = json.loads(interval_row[0])
                except:
                    pass

            cursor.execute('SELECT id FROM tournaments WHERE status = ?', ('active',))
            ids = [row[0] for row in cursor.fetchall()]

            return auto_refresh, interval, ids

        try:
            return execute_with_retry(transaction)
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            return True, 30, []

    def _update_courts_data(self, tournament_ids: List[str]) -> int:
        """Обновляет данные кортов"""
        updated = 0

        for tid in tournament_ids:
            try:
                def get_court_ids(conn):
                    cursor = conn.cursor()
                    cursor.execute('SELECT courts FROM tournaments WHERE id = ?', (tid,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        courts = json.loads(row[0])
                        return [str(c.get("Item1")) for c in courts if c.get("Item1")]
                    return []

                court_ids = execute_with_retry(get_court_ids)
                if not court_ids:
                    continue

                courts_data = self.api.get_all_courts_data(court_ids)
                if not courts_data:
                    continue

                def save_courts(conn):
                    nonlocal updated
                    cursor = conn.cursor()
                    for court in courts_data:
                        if "error" not in court:
                            cursor.execute('''
                                INSERT OR REPLACE INTO courts_data 
                                (tournament_id, court_id, court_name, event_state, class_name,
                                 first_participant_score, second_participant_score, 
                                 detailed_result, first_participant, second_participant, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            ''', (
                                tid, str(court["court_id"]), court["court_name"],
                                court["event_state"], court["class_name"],
                                court["first_participant_score"], court["second_participant_score"],
                                json.dumps(court["detailed_result"]), json.dumps(court["first_participant"]),
                                json.dumps(court["second_participant"])
                            ))
                            updated += 1

                execute_with_retry(save_courts)

            except Exception as e:
                logger.error(f"Ошибка обновления кортов турнира {tid}: {e}")

        return updated

    def _update_tournament_tables(self, tournament_ids: List[str]) -> int:
        """Обновляет турнирные таблицы"""
        updated = 0

        for tid in tournament_ids:
            try:
                def get_draw_data(conn):
                    cursor = conn.cursor()
                    cursor.execute('SELECT draw_data FROM tournaments WHERE id = ?', (tid,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        return json.loads(row[0])
                    return {}

                draw_data = execute_with_retry(get_draw_data)
                if not draw_data:
                    continue

                updated_draw_data = {}
                for class_id, class_data in draw_data.items():
                    try:
                        fresh = self.api.get_all_draws_for_class(class_id)
                        updated_draw_data[class_id] = {
                            "class_info": class_data.get("class_info", {}),
                            "round_robin": fresh.get("round_robin", []),
                            "elimination": fresh.get("elimination", [])
                        }

                        old_rr = len(class_data.get("round_robin", []))
                        old_el = len(class_data.get("elimination", []))
                        new_rr = len(fresh.get("round_robin", []))
                        new_el = len(fresh.get("elimination", []))

                        if old_rr != new_rr or old_el != new_el:
                            updated += 1

                    except Exception as e:
                        logger.error(f"Ошибка обновления класса {class_id}: {e}")
                        updated_draw_data[class_id] = class_data.copy()

                if updated_draw_data and updated_draw_data != draw_data:
                    def save_draw(conn):
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE tournaments 
                            SET draw_data = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE id = ?
                        ''', (json.dumps(updated_draw_data), tid))

                    execute_with_retry(save_draw)

            except Exception as e:
                logger.error(f"Ошибка обновления таблиц турнира {tid}: {e}")

        return updated

    def _update_tournament_schedules(self, tournament_ids: List[str]) -> int:
        """Обновляет расписание турниров"""
        updated = 0

        for tid in tournament_ids:
            try:
                def get_dates(conn):
                    cursor = conn.cursor()
                    cursor.execute('SELECT dates FROM tournaments WHERE id = ?', (tid,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        return json.loads(row[0])
                    return []

                dates = execute_with_retry(get_dates)
                if not dates:
                    continue

                court_planner = self.api.get_court_planner(tid, dates)
                court_usage = self.api.get_court_usage(tid, dates)

                if court_planner or court_usage:
                    def save_schedule(conn):
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR REPLACE INTO tournament_schedule 
                            (tournament_id, court_planner, court_usage, updated_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (tid, json.dumps(court_planner or {}), json.dumps(court_usage or {})))

                    execute_with_retry(save_schedule)
                    updated += 1

            except Exception as e:
                logger.error(f"Ошибка обновления расписания турнира {tid}: {e}")

        return updated
