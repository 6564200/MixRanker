#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страниц расписания матчей
"""

from typing import Dict, List
from datetime import datetime
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class ScheduleGenerator(HTMLBaseGenerator):
    """Генератор schedule страниц"""

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей"""
        return self._generate_schedule(tournament_data, target_date, "schedule_new.css", filter_matches=True)

    def generate_schedule_html_new(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания (новый дизайн)"""
        return self._generate_schedule(tournament_data, target_date, "schedule_new.css", filter_matches=False)

    def generate_schedule_html_addreality(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания (Addreality дизайн)"""
        return self._generate_schedule(tournament_data, target_date, "schedule_addreality.css", filter_matches=False)

    def _generate_schedule(self, tournament_data: Dict, target_date: str, css_file: str, filter_matches: bool) -> str:
        """Общий метод генерации расписания"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        target_date = target_date or datetime.now().strftime("%d.%m.%Y")

        courts_matches, all_matches = self._group_matches_by_court(court_usage, court_names_map, target_date)

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        self._enumerate_matches(courts_matches)

        if filter_matches:
            courts_matches = self._filter_matches(courts_matches)

        # time_slots только из отфильтрованных матчей
        time_slots = sorted({m["start_time"] for matches in courts_matches.values() for m in matches})

        return self._render_schedule_html(tournament_name, courts_matches, time_slots, css_file)

    def _build_court_names_map(self, courts_info: List[Dict]) -> Dict[str, str]:
        """Создает карту ID корта -> название"""
        return {
            str(c["Item1"]): c["Item2"]
            for c in courts_info
            if isinstance(c, dict) and c.get("Item1") and c.get("Item2")
        }

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
                if dt_obj.strftime("%d.%m.%Y") != target_date:
                    continue

                court_id = str(match.get("CourtId", ""))
                court_name = court_names_map.get(court_id, f"Корт {court_id}")

                match["start_time"] = dt_obj.strftime("%H:%M")
                match["date_formatted"] = dt_obj.strftime("%d.%m.%Y")
                match["court_name"] = court_name
                match["datetime_obj"] = dt_obj

                all_matches.append(match)
                courts_matches.setdefault(court_name, []).append(match)

            except Exception:
                continue

        return courts_matches, all_matches

    def _enumerate_matches(self, courts_matches: Dict):
        """Сортирует и нумерует матчи"""
        for court_name, matches in courts_matches.items():
            matches.sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(matches, 1):
                match["episode_number"] = i

    def _filter_matches(self, courts_matches: Dict) -> Dict:
        """Фильтрует матчи: последние 3 с результатами + все без результатов"""
        filtered = {}
        for court_name, matches in courts_matches.items():
            # Матчи с результатами (реально сыгранные)
            with_results = [m for m in matches if m.get("ChallengerResult") or m.get("ChallengedResult")]
            # Матчи без результатов (ещё не сыграны)
            without_results = [m for m in matches if not m.get("ChallengerResult") and not m.get("ChallengedResult")]
            # Последние 3 сыгранных + все несыгранные
            filtered[court_name] = with_results[-3:] + without_results
        return filtered

    def _render_schedule_html(self, tournament_name: str, courts_matches: Dict, time_slots: List, css_file: str) -> str:
        """Рендерит HTML расписания с CSS Grid привязкой к времени"""
        sorted_courts = sorted(courts_matches.keys())
        
        # Создаём маппинг время -> номер строки (1-indexed для CSS Grid)
        time_to_row = {time: idx + 1 for idx, time in enumerate(time_slots)}

        html = f'''{self.html_head(f"Расписание матчей - {tournament_name}", css_file, 30000)}
<body>
    <div class="schedule-container">
        <div class="main-grid">
            <div class="time-scale" style="display: grid; grid-template-rows: repeat({len(time_slots)}, 86px); gap: 16px; padding-top: 64px;">'''
        
        for time_slot in time_slots:
            html += f'<div class="time-slot">{time_slot}</div>'
        
        html += '''</div>
            <div class="courts-container">
                <div class="courts-header">'''
        
        for court_name in sorted_courts:
            html += f'<div class="court-header"><h3>{court_name}</h3></div>'
        
        html += f'''</div>
                <div class="matches-grid" style="display: grid; grid-template-rows: repeat({len(time_slots)}, 86px); grid-template-columns: repeat({len(sorted_courts)}, 534px); gap: 16px;">'''

        # Размещаем матчи по сетке
        for col_idx, court_name in enumerate(sorted_courts):
            for match in courts_matches[court_name]:
                start_time = match.get("start_time")
                row = time_to_row.get(start_time, 1)
                col = col_idx + 1
                html += self._render_match_item_grid(match, row, col)

        html += '''</div></div></div></div></body></html>'''
        return html

    def _render_match_item_grid(self, match: Dict, row: int, col: int) -> str:
        """Рендерит матч с CSS Grid позиционированием"""
        status_class = self.get_status_class(self.get_match_status(match))
        challenger = match.get("ChallengerName", "TBD")
        challenged = match.get("ChallengedName", "TBD")
        episode = match.get("episode_number", 1)

        challenger_result = match.get("ChallengerResult", "") or ""
        challenged_result = match.get("ChallengedResult", "") or ""

        challenger_wo = challenger_result == "Won W.O."
        challenged_wo = challenged_result == "Won W.O."

        if challenger_wo:
            challenger_result = ""
        if challenged_wo:
            challenged_result = ""

        def team_html(name, wo, result):
            wo_div = "<div class='match-team-wo'>Won W.O.</div>" if wo else ""
            score_div = f"<div class='match-team-score'>{result}</div>" if result else ""
            return f'''<div class="match-team">
                <div class="match-team-name">{name}</div>
                {wo_div}{score_div}
            </div>'''

        return f'''
            <div class="match-item {status_class}" style="grid-row: {row}; grid-column: {col};">
                <div class="match-content">
                    <div class="match-number">{episode}</div>
                    <div class="match-teams-wrapper">
                        {team_html(challenger, challenger_wo, challenger_result)}
                        {team_html(challenged, challenged_wo, challenged_result)}
                    </div>
                </div>
            </div>'''

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Генерирует пустую страницу расписания"""
        return f'''{self.html_head(f"Расписание матчей - {tournament_name}", "schedule.css")}
<body>
    <div class="schedule-container">
        <div class="header"><h1 class="tournament-title">{tournament_name}</h1></div>
        <div class="empty-message"><p>{message}</p></div>
    </div>
</body>
</html>'''