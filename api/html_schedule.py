#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страниц расписания матчей
"""

from typing import Dict, List
from datetime import datetime
from zoneinfo import ZoneInfo
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class ScheduleGenerator(HTMLBaseGenerator):
    """Генератор schedule страниц"""

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        court_usage = tournament_data.get("court_usage")
        
        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")
        
        # Карта имен кортов
        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        
        if not target_date:
            target_date = datetime.now().strftime("%d.%m.%Y")
        
        # Группируем матчи по кортам
        courts_matches, all_matches = self._group_matches_by_court(court_usage, court_names_map, target_date)
        
        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")
        
        # Нумеруем и фильтруем матчи
        self._enumerate_matches(courts_matches)
        courts_matches = self._filter_matches(courts_matches)
        
        # Временные слоты
        all_remaining_matches = [m for matches in courts_matches.values() for m in matches]
        time_slots = sorted(set(m["start_time"] for m in all_remaining_matches))
        
        return self._render_schedule_html(tournament_name, courts_matches, time_slots, "schedule_new.css")

    def generate_schedule_html_new(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания (новый дизайн)"""
        return self._generate_schedule_variant(tournament_data, target_date, "schedule_new.css", filter_matches=False)

    def generate_schedule_html_addreality(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания (Addreality дизайн)"""
        return self._generate_schedule_variant(tournament_data, target_date, "schedule_addreality.css", filter_matches=False)

    def _generate_schedule_variant(self, tournament_data: Dict, target_date: str, css_file: str, filter_matches: bool = True) -> str:
        """Общий метод генерации расписания"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        court_usage = tournament_data.get("court_usage")
        
        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")
        
        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        
        if not target_date:
            target_date = datetime.now().strftime("%d.%m.%Y")
        
        courts_matches, all_matches = self._group_matches_by_court(court_usage, court_names_map, target_date)
        
        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")
        
        self._enumerate_matches(courts_matches)
        
        if filter_matches:
            courts_matches = self._filter_matches(courts_matches)
        
        time_slots = sorted(set(m["start_time"] for m in all_matches))
        
        return self._render_schedule_html(tournament_name, courts_matches, time_slots, css_file)

    def _build_court_names_map(self, courts_info: List[Dict]) -> Dict[str, str]:
        """Создает карту ID корта -> название"""
        court_names_map = {}
        for court in courts_info:
            if isinstance(court, dict) and court.get("Item1") and court.get("Item2"):
                court_names_map[str(court["Item1"])] = court["Item2"]
        return court_names_map

    def _group_matches_by_court(self, court_usage: List, court_names_map: Dict, target_date: str) -> tuple:
        """Группирует матчи по кортам и фильтрует по дате"""
        courts_matches = {}
        all_matches = []
        
        for match in court_usage:
            if not isinstance(match, dict):
                continue
            
            match_date = match.get("MatchDate", "")
            if not match_date:
                continue
            
            try:
                dt_obj = datetime.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                match_date_formatted = dt_obj.strftime("%d.%m.%Y")
                
                if match_date_formatted != target_date:
                    continue
                
                court_id = str(match.get("CourtId", ""))
                court_name = court_names_map.get(court_id, f"Корт {court_id}")
                
                match["start_time"] = dt_obj.strftime("%H:%M")
                match["date_formatted"] = match_date_formatted
                match["court_name"] = court_name
                match["datetime_obj"] = dt_obj
                
                all_matches.append(match)
                
                if court_name not in courts_matches:
                    courts_matches[court_name] = []
                courts_matches[court_name].append(match)
                
            except Exception:
                continue
        
        return courts_matches, all_matches

    def _enumerate_matches(self, courts_matches: Dict):
        """Сортирует и нумерует матчи"""
        for court_name in courts_matches:
            courts_matches[court_name].sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(courts_matches[court_name], 1):
                match["episode_number"] = i

    def _filter_matches(self, courts_matches: Dict) -> Dict:
        """Фильтрует матчи: последние 3 завершённых + все активные и будущие"""
        filtered = {}
        for court_name, matches in courts_matches.items():
            finished = [m for m in matches if self.get_match_status(m) == "finished"]
            active_future = [m for m in matches if self.get_match_status(m) != "finished"]
            filtered[court_name] = finished[-3:] + active_future
        return filtered

    def _render_schedule_html(self, tournament_name: str, courts_matches: Dict, time_slots: List, css_file: str) -> str:
        """Рендерит HTML расписания"""
        html = f'''{self.html_head(f"Расписание матчей - {tournament_name}", css_file, 30000)}
<body>
    <div class="schedule-container">
        <div class="main-grid">
            <div class="time-scale">'''
        
        for time_slot in time_slots:
            html += f'<div class="time-slot">{time_slot}</div>'
        
        html += '''</div>
            <div class="courts-container">
                <div class="courts-header">'''
        
        for court_name in sorted(courts_matches.keys()):
            html += f'<div class="court-header"><h3>{court_name}</h3></div>'
        
        html += '''</div>
                <div class="matches-grid">'''
        
        for court_name in sorted(courts_matches.keys()):
            html += '<div class="court-column">'
            for match in courts_matches[court_name]:
                html += self._render_match_item(match)
            html += '</div>'
        
        html += '''</div>
            </div>
        </div>
    </div>
</body>
</html>'''
        
        return html

    def _render_match_item(self, match: Dict) -> str:
        """Рендерит один элемент матча"""
        status_class = self.get_status_class(self.get_match_status(match))
        challenger_name = match.get("ChallengerName", "TBD")
        challenged_name = match.get("ChallengedName", "TBD")
        episode = match.get("episode_number", 1)
        
        challenger_result = match.get("ChallengerResult", "") or ""
        challenged_result = match.get("ChallengedResult", "") or ""
        
        challenger_wo = "Won W.O." if challenger_result == "Won W.O." else ""
        challenged_wo = "Won W.O." if challenged_result == "Won W.O." else ""
        
        if challenger_wo:
            challenger_result = ""
        if challenged_wo:
            challenged_result = ""
        
        return f'''
            <div class="match-item {status_class}">
                <div class="match-content">
                    <div class="match-number">{episode}</div>
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

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Генерирует пустую страницу расписания"""
        return f'''{self.html_head(f"Расписание матчей - {tournament_name}", "schedule.css", 30000)}
<body>
    <div class="schedule-container">
        <div class="header"><h1 class="tournament-title">{tournament_name}</h1></div>
        <div class="empty-message"><p>{message}</p></div>
    </div>
</body>
</html>'''
