#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML расписания
"""

from typing import Dict, List
from datetime import datetime as dt
import logging
from .html_base import HTMLBase

logger = logging.getLogger(__name__)


class ScheduleHTMLGenerator(HTMLBase):
    """Генератор HTML расписания"""
    
    def generate_schedule_html_new(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей с новым дизайном 3.12.2025"""
        # Метаинформация о турнире
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        # Получаем расписание
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        # Получаем информацию о кортах из tournaments.courts
        courts_info = tournament_data.get("courts", [])
        court_names_map = {}
        for court in courts_info:
            if isinstance(court, dict) and court.get("Item1") and court.get("Item2"):
                court_id = str(court["Item1"])
                court_name = court["Item2"]
                court_names_map[court_id] = court_name

        from datetime import datetime as dt
        if not target_date:
            #target_date = dt.now().strftime("%d.%m.%Y")
            target_date = dt(year=2025, month=12, day=6).strftime("%d.%m.%Y") # для тестов

        # Группируем матчи по кортам и фильтруем по дате
        courts_matches = {}
        all_matches = []

        for match in court_usage:

            if not isinstance(match, dict):
                continue

            match_date = match.get("MatchDate", "")
            if match_date:
                try:
                    dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                    match_date_formatted = dt_obj.strftime("%d.%m.%Y")

                    # Фильтруем только матчи на нужную дату
                    if match_date_formatted != target_date:
                        continue

                    court_id = str(match.get("CourtId", ""))
                    court_name = court_names_map.get(court_id, f"Корт {court_id}")

                    # Добавляем время начала для сортировки
                    match["start_time"] = dt_obj.strftime("%H:%M")
                    match["date_formatted"] = match_date_formatted
                    match["court_name"] = court_name
                    match["datetime_obj"] = dt_obj

                    all_matches.append(match)

                    if court_name not in courts_matches:
                        courts_matches[court_name] = []
                    courts_matches[court_name].append(match)

                except Exception as e:
                    continue

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        # Сортируем матчи в каждом корте по времени и присваиваем номера
        for court_name in courts_matches:
            courts_matches[court_name].sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(courts_matches[court_name], 1):
                match["episode_number"] = i

        # Создаем уникальные временные слоты
        time_slots = sorted(list(set([m["start_time"] for m in all_matches])))

        # Генерируем HTML
        html_content = f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Расписание матчей - {tournament_name}</title>
        <link rel="stylesheet" href="/static/css/schedule_new.css">
        <script>
            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="schedule-container">
            <div class="main-grid">
                <div class="time-scale">'''

        # Временные слоты
        for time_slot in time_slots:
            html_content += f'''
                    <div class="time-slot">{time_slot}</div>'''

        html_content += '''
                </div>
                
                <div class="courts-container">
                    <div class="courts-header">'''

        # Заголовки кортов
        for court_name in sorted(courts_matches.keys()):
            html_content += f'''
                        <div class="court-header">
                            <h3>{court_name}</h3>
                        </div>'''

        html_content += '''
                    </div>
                    
                    <div class="matches-grid">'''

        # Столбцы кортов с матчами
        for court_name in sorted(courts_matches.keys()):
            matches = courts_matches[court_name]

            html_content += '''
                        <div class="court-column">'''

            for match in matches:
                match_status = self._get_match_status(match)
                status_class = self._get_status_class(match_status)

                challenger_name = match.get("ChallengerName", "TBD")
                challenged_name = match.get("ChallengedName", "TBD")
                episode_number = match.get("episode_number", 1)

                # Результаты матча
                challenger_result = match.get("ChallengerResult", "0")
                challenged_result = match.get("ChallengedResult", "0")

                if not challenger_result:
                    challenger_result = "0"
                if not challenged_result:
                    challenged_result = "0"

                # Проверка на Won W.O.
                challenger_wo = ""
                challenged_wo = ""

                if challenger_result == "Won W.O.":
                    challenger_wo = "W.O."
                    challenger_result = ""
                if challenged_result == "Won W.O.":
                    challenged_wo = "W.O."
                    challenged_result = ""
                                                                            #<div class="match-number">{episode_number}</div>

                html_content += f'''
                        <div class="match-item {status_class}">
                            <div class="match-content">
                                
                                <div class="match-number">:</div>
                                <div class="match-teams-wrapper">
                                    <div class="match-team">
                                        <div class="match-team-name">{challenger_name}</div>
                                        {"<div class='match-team-wo'>Won W.O.</div>" if challenger_wo else ""}
                                        {"<div class='match-team-score'>" + challenger_result + "</div>" if challenger_result else ""}
                                    </div>
                                    <div class="match-team">
                                        <div class="match-team-name">{challenged_name}</div>
                                        {"<div class='match-team-wo'>Won W.O.</div>" if challenged_wo else ""}
                                        {"<div class='match-team-score'>" + challenged_result + "</div>" if challenged_result else ""}
                                    </div>
                                </div>
                            </div>
                        </div>'''

            html_content += '''
                        </div>'''

        html_content += '''
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>'''

        return html_content
    
    def generate_and_save_schedule_html(self, tournament_data: Dict, target_date: str = None) -> Dict:
        """Генерирует и сохраняет HTML файл расписания"""
        
        # Генерация HTML
        html_content = self.generator.generate_schedule_html(tournament_data, target_date)
        
        # Определяем дату для имени файла
        from datetime import datetime as dt
        if not target_date:
            target_date = dt.now().strftime("%d.%m.%Y")
        
        # Сохранение файла
        safe_date = target_date.replace(".", "_")
        filename = f"{tournament_data.get('tournament_id', 'unknown')}_schedule_{safe_date}.html"
        filepath = f"{self.output_dir}/{filename}"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            logger.error(f"Ошибка сохранения файла {filepath}: {e}")
            raise
        
        # Информация о файле
        import os
        if os.path.exists(filepath):
            file_stats = os.stat(filepath)
        else:
            logger.error(f"Файл не найден после создания: {filepath}")
            raise FileNotFoundError(f"Файл не создался: {filepath}")
        
        file_info = {
            "id": f"schedule_html_{safe_date}",
            "name": f"Расписание матчей HTML - {target_date}",
            "filename": filename,
            "url": f"/html/{filename}",
            "size": self._format_file_size(file_stats.st_size),
            "created": datetime.now().isoformat(),
            "type": "html_schedule",
            "target_date": target_date
        }

        return file_info
    
    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Генерирует пустую HTML страницу расписания"""
        return f'''<!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Расписание матчей - {tournament_name}</title>
                    <link rel="stylesheet" href="/static/css/schedule.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 30000);
                            </script>
                </head>
                <body>
                    <div class="schedule-container">
                        <div class="header">
                            <h1 class="tournament-title">{tournament_name}</h1>
                        </div>
                        <div class="empty-message">
                            <p>{message}</p>
                        </div>
                    </div>
                </body>
                </html>'''
