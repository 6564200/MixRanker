#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страниц расписания матчей
"""

from typing import Dict, List, Optional
from datetime import datetime
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class ScheduleGenerator(HTMLBaseGenerator):
    """Генератор schedule страниц"""
    
    # FHD размеры (увеличенные)
    MATCH_HEIGHT = 86
    GAP = 8

    def _split_team_name(self, team_name: str) -> list:
        """Разбивает имя команды на отдельных игроков"""
        if not team_name:
            return ["TBD"]
        
        # Разделители: "/" или " / "
        if "/" in team_name:
            players = [p.strip() for p in team_name.split("/")]
            return [p for p in players if p]
        
        return [team_name]

    def _get_tournament_name_class(self, name: str) -> str:
        """Определяет CSS класс для названия турнира в зависимости от длины"""
        if len(name) > 40:
            return "very-long-name"
        elif len(name) > 25:
            return "long-name"
        return ""

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> str:
        """Генерирует HTML для расписания матчей"""
        return self._generate_schedule(tournament_data, target_date, "schedule.css", filter_matches=True, settings=settings)

    def get_schedule_data(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> Dict:
        """Возвращает данные расписания в формате JSON для AJAX"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return {"error": "Данные расписания не загружены", "matches": [], "courts": [], "time_slots": []}

        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        target_date = target_date or datetime.now().strftime("%d.%m.%Y")

        matches_data = tournament_data.get("matches_data", {})
        matches_index = self._build_matches_index(matches_data, court_names_map)

        courts_matches, all_matches = self._group_matches_by_court(court_usage, court_names_map, target_date, matches_index)

        if not courts_matches:
            return {
                "tournament_name": tournament_name,
                "target_date": target_date,
                "courts": [],
                "time_slots": [],
                "matches": []
            }

        self._enumerate_matches(courts_matches)

        finished_count = (settings or {}).get("finishedMatchesCount", 3)
        courts_matches = self._filter_matches(courts_matches, finished_count)

        time_slots = sorted({m["start_time"] for matches in courts_matches.values() for m in matches})
        sorted_courts = sorted(courts_matches.keys())

        # Формируем список матчей с позициями в сетке
        time_to_row = {time: idx + 1 for idx, time in enumerate(time_slots)}
        court_to_col = {court: idx + 1 for idx, court in enumerate(sorted_courts)}

        matches_list = []
        for court_name, matches in courts_matches.items():
            for match in matches:
                start_time = match.get("start_time", "")
                row = time_to_row.get(start_time, 1)
                col = court_to_col.get(court_name, 1)
                
                matches_list.append({
                    "id": match.get("TournamentMatchId", ""),
                    "row": row,
                    "col": col,
                    "court": court_name,
                    "start_time": start_time,
                    "episode": match.get("episode_number", 1),
                    "challenger": match.get("ChallengerFullName") or match.get("ChallengerName", "TBD"),
                    "challenged": match.get("ChallengedFullName") or match.get("ChallengedName", "TBD"),
                    "challenger_score": match.get("ChallengerResult", "") or "",
                    "challenged_score": match.get("ChallengedResult", "") or "",
                    "status": self.get_match_status(match)
                })

        return {
            "tournament_name": tournament_name,
            "target_date": target_date,
            "courts": sorted_courts,
            "time_slots": time_slots,
            "matches": matches_list
        }

    def _generate_schedule(self, tournament_data: Dict, target_date: str, css_file: str, filter_matches: bool, settings: Dict = None) -> str:
        """Общий метод генерации расписания"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        tournament_id = tournament_data.get("tournament_id", "") or metadata.get("id", "")
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        target_date = target_date or datetime.now().strftime("%d.%m.%Y")

        # Создаём индекс матчей для обогащения данных
        matches_data = tournament_data.get("matches_data", {})
        matches_index = self._build_matches_index(matches_data, court_names_map)

        courts_matches, all_matches = self._group_matches_by_court(court_usage, court_names_map, target_date, matches_index)

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        self._enumerate_matches(courts_matches)

        if filter_matches:
            finished_count = (settings or {}).get("finishedMatchesCount", 3)
            courts_matches = self._filter_matches(courts_matches, finished_count)

        # time_slots только из отфильтрованных матчей
        time_slots = sorted({m["start_time"] for matches in courts_matches.values() for m in matches})

        return self._render_schedule_html(tournament_name, tournament_id, target_date, courts_matches, time_slots, css_file)

    def _build_court_names_map(self, courts_info: List[Dict]) -> Dict[str, str]:
        """Создает карту ID корта -> название"""
        return {
            str(c["Item1"]): c["Item2"]
            for c in courts_info
            if isinstance(c, dict) and c.get("Item1") and c.get("Item2")
        }

    def _build_matches_index(self, matches_data: Dict, court_names_map: Dict) -> Dict:
        """Создаёт индекс матчей по дате + корту для быстрого поиска"""
        matches_index = {}
        matches_list = matches_data.get("Matches", []) if isinstance(matches_data, dict) else []
        
        # Инвертируем карту кортов: название -> id
        court_name_to_id = {v.lower(): k for k, v in court_names_map.items()}
        
        for match in matches_list:
            date = match.get("Date", "")
            court_name = match.get("Court", "").lower()
            
            key = (date, court_name)
            if key not in matches_index:
                matches_index[key] = []
            matches_index[key].append(match)
        
        return matches_index

    def _get_abbrevs_from_name(self, full_name: str) -> set:
        """Получает все возможные сокращения (первые 3 буквы каждого слова)"""
        if not full_name:
            return set()
        parts = full_name.split()
        return {p[:3] for p in parts if len(p) >= 3}

    def _find_match_by_abbrev(self, matches_index: Dict, date: str, court_name: str, 
                              challenger_abbrev: str, challenged_abbrev: str) -> Optional[Dict]:
        """Находит матч по дате, корту и сокращениям имён"""
        key = (date, court_name.lower())
        candidates = matches_index.get(key, [])
        
        # Разбиваем сокращения "Hau/Kro" -> ["Hau", "Kro"]
        ch_parts = challenger_abbrev.split('/') if challenger_abbrev else []
        ch_abbrev1 = ch_parts[0] if len(ch_parts) > 0 else ''
        ch_abbrev2 = ch_parts[1] if len(ch_parts) > 1 else ''
        
        chd_parts = challenged_abbrev.split('/') if challenged_abbrev else []
        chd_abbrev1 = chd_parts[0] if len(chd_parts) > 0 else ''
        chd_abbrev2 = chd_parts[1] if len(chd_parts) > 1 else ''
        
        for match in candidates:
            challenger = match.get("Challenger", {})
            challenged = match.get("Challenged", {})
            
            # Получаем все возможные сокращения
            ch_all1 = self._get_abbrevs_from_name(challenger.get("Name", ""))
            ch_all2 = self._get_abbrevs_from_name(challenger.get("Player2Name", ""))
            chd_all1 = self._get_abbrevs_from_name(challenged.get("Name", ""))
            chd_all2 = self._get_abbrevs_from_name(challenged.get("Player2Name", ""))
            
            # Проверяем совпадение
            ch_match = (ch_abbrev1 in ch_all1 and ch_abbrev2 in ch_all2)
            chd_match = (chd_abbrev1 in chd_all1 and chd_abbrev2 in chd_all2)
            
            if ch_match and chd_match:
                return match
        
        return None

    def _format_full_name(self, participant: Dict) -> str:
        """Форматирует имя участника: П.Фамилия/П.Фамилия"""
        name1 = participant.get("Name", "")
        name2 = participant.get("Player2Name", "")
        
        def format_player(full_name):
            if not full_name:
                return ""
            parts = full_name.split()
            if len(parts) >= 2:
                # Первая буква имени + фамилия (последнее слово)
                initial = parts[0][0].upper()
                surname = parts[-1].upper()
                return f"{initial}.{surname}"
            elif len(parts) == 1:
                return parts[0].upper()
            return ""
        
        p1 = format_player(name1)
        p2 = format_player(name2)
        
        if p1 and p2:
            return f"{p1}/{p2}"
        return p1 or p2 or "TBD"

    def _format_detailed_score(self, match_result: Dict) -> str:
        """Форматирует детальный счёт из MatchResult"""
        if not match_result:
            return ""
        
        score = match_result.get("Score", {})
        if not score:
            return ""
        
        detailed = score.get("DetailedScoring", [])
        if not detailed:
            # Возвращаем общий счёт
            p1 = score.get("FirstParticipantScore", "")
            p2 = score.get("SecondParticipantScore", "")
            if p1 != "" and p2 != "":
                return f"{p1}-{p2}"
            return ""
        
        # Форматируем по сетам
        sets = []
        for s in detailed:
            p1 = s.get("FirstParticipantScore", 0)
            p2 = s.get("SecondParticipantScore", 0)
            tb = s.get("LoserTiebreak")
            if tb:
                sets.append(f"{p1}-{p2}({tb})")
            else:
                sets.append(f"{p1}-{p2}")
        
        return " ".join(sets)

    def _group_matches_by_court(self, court_usage: List, court_names_map: Dict, 
                                 target_date: str, matches_index: Dict) -> tuple:
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

                # Обогащаем данными из matches
                challenger_abbrev = match.get("ChallengerName", "")
                challenged_abbrev = match.get("ChallengedName", "")
                
                rich_match = self._find_match_by_abbrev(
                    matches_index, match_date, court_name,
                    challenger_abbrev, challenged_abbrev
                )
                
                if rich_match:
                    # Добавляем полные имена
                    match["ChallengerFullName"] = self._format_full_name(rich_match.get("Challenger", {}))
                    match["ChallengedFullName"] = self._format_full_name(rich_match.get("Challenged", {}))
                    # Добавляем детальный счёт
                    match["DetailedScore"] = self._format_detailed_score(rich_match.get("MatchResult", {}))
                    match["RichMatchData"] = rich_match

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

    def _filter_matches(self, courts_matches: Dict, finished_count: int = 3) -> Dict:
        """
        Фильтрует матчи с выравниванием по отстающему корту.
        
        1. Находим корт с самым поздним временем среди последних N сыгранных
        2. Берём это время как точку отсечения
        3. На всех кортах показываем матчи начиная с этого времени
        """
        if not courts_matches:
            return {}
        
        # Шаг 1: Для каждого корта находим время N-го сыгранного матча с конца
        court_cutoff_times = {}
        
        for court_name, matches in courts_matches.items():
            # Матчи с результатами, отсортированные по времени
            with_results = sorted(
                [m for m in matches if m.get("ChallengerResult") or m.get("ChallengedResult")],
                key=lambda x: x.get("datetime_obj") or datetime.min
            )

            if len(with_results) >= finished_count:
                # Берём время N-го с конца (первого из показываемых)
                cutoff_match = with_results[-finished_count]
                court_cutoff_times[court_name] = cutoff_match.get("datetime_obj")
            elif with_results:
                # Если меньше N сыгранных, берём самый ранний
                court_cutoff_times[court_name] = with_results[0].get("datetime_obj")
            else:
                # Нет сыгранных — берём первый несыгранный
                without_results = sorted(
                    [m for m in matches if not m.get("ChallengerResult") and not m.get("ChallengedResult")],
                    key=lambda x: x.get("datetime_obj") or datetime.min
                )
                if without_results:
                    court_cutoff_times[court_name] = without_results[0].get("datetime_obj")
        
        if not court_cutoff_times:
            return courts_matches
        
        # Шаг 2: Находим самое позднее время отсечки (отстающий корт)
        global_cutoff = min(t for t in court_cutoff_times.values() if t)
        
        # Шаг 3: Фильтруем все корты по глобальному времени отсечки
        filtered = {}
        for court_name, matches in courts_matches.items():
            filtered[court_name] = [
                m for m in matches 
                if m.get("datetime_obj") and m.get("datetime_obj") >= global_cutoff
            ]
        
        return filtered

    def _render_schedule_html(self, tournament_name: str, tournament_id: str, target_date: str, courts_matches: Dict, time_slots: List, css_file: str) -> str:
        """Рендерит HTML расписания с CSS Grid привязкой к времени"""
        sorted_courts = sorted(courts_matches.keys())
        
        # Создаём маппинг время -> номер строки (1-indexed для CSS Grid)
        time_to_row = {time: idx + 1 for idx, time in enumerate(time_slots)}
        
        # Генерируем version hash
        import hashlib
        version_data = f"{tournament_id}:{target_date}:{len(time_slots)}:{len(sorted_courts)}"
        for court in sorted_courts:
            for m in courts_matches[court]:
                version_data += f":{m.get('TournamentMatchId', '')}:{m.get('ChallengerResult', '')}:{m.get('ChallengedResult', '')}"
        version = hashlib.md5(version_data.encode()).hexdigest()[:12]
        
        # Определяем класс для названия турнира
        name_class = self._get_tournament_name_class(tournament_name)

        html = f'''{self.html_head(f"Расписание матчей - {tournament_name}", css_file, 0)}
<body>
    <div class="schedule-container" data-tournament-id="{tournament_id}" data-target-date="{target_date}" data-version="{version}">

        <!-- Header -->
        <div class="header">
            <div class="tournament-name {name_class}">{tournament_name}</div>
            <div class="logos">
                <div class="logo logo4" style="background-image: url('/static/images/logo4.png');"></div>
                <div class="logo logo3" style="background-image: url('/static/images/logo3.png');"></div>
                <div class="logo logo2" style="background-image: url('/static/images/logo2.png');"></div>
                <div class="logo logo1" style="background-image: url('/static/images/logo1.png');"></div>
            </div>
        </div>

        <div class="main-grid">
            <div class="time-scale" style="display: grid; grid-template-rows: repeat({len(time_slots)}, {self.MATCH_HEIGHT}px); gap: {self.GAP}px; padding-top: 36px;">'''
        
        for idx, time_slot in enumerate(time_slots):
            html += f'<div class="time-slot" style="animation-delay: {0.1 + idx * 0.05}s;">{time_slot}</div>'
        
        html += '''</div>
            <div class="courts-container">
                <div class="courts-header" style="grid-template-columns: repeat(''' + str(len(sorted_courts)) + ''', 1fr);">'''
        
        for court_name in sorted_courts:
            html += f'<div class="court-header"><h3>{court_name}</h3></div>'
        
        html += f'''</div>
                <div class="matches-grid" style="display: grid; grid-template-rows: repeat({len(time_slots)}, {self.MATCH_HEIGHT}px); grid-template-columns: repeat({len(sorted_courts)}, 1fr); gap: {self.GAP}px;">'''

        # Размещаем матчи по сетке
        for col_idx, court_name in enumerate(sorted_courts):
            for match in courts_matches[court_name]:
                start_time = match.get("start_time")
                row = time_to_row.get(start_time, 1)
                col = col_idx + 1
                html += self._render_match_item_grid(match, row, col)

        html += '''</div></div></div></div>
    <script src="/static/js/schedule_live.js"></script>
</body></html>'''
        return html

    def _render_match_item_grid(self, match: Dict, row: int, col: int) -> str:
        """Рендерит матч с CSS Grid позиционированием и вертикальным расположением имён"""
        status_class = self.get_status_class(self.get_match_status(match))
        
        # Используем полные имена если есть, иначе сокращённые
        challenger_full = match.get("ChallengerFullName") or match.get("ChallengerName", "TBD")
        challenged_full = match.get("ChallengedFullName") or match.get("ChallengedName", "TBD")
        episode = match.get("episode_number", 1)

        # Счёт из court_usage
        challenger_result = match.get("ChallengerResult", "") or ""
        challenged_result = match.get("ChallengedResult", "") or ""

        challenger_wo = challenger_result == "Won W.O."
        challenged_wo = challenged_result == "Won W.O."

        if challenger_wo:
            challenger_result = ""
        if challenged_wo:
            challenged_result = ""

        # Разбиваем имена на отдельных игроков
        challenger_players = self._split_team_name(challenger_full)
        challenged_players = self._split_team_name(challenged_full)

        def team_html(players: list, wo: bool, result: str) -> str:
            wo_div = "<div class='match-team-wo'>W.O.</div>" if wo else ""
            score_div = f"<div class='match-team-score'>{result}</div>" if result else ""
            
            # Если один игрок - используем старый формат
            if len(players) == 1:
                return f'''<div class="match-team">
                    <div class="match-team-name">{players[0]}</div>
                    {wo_div}{score_div}
                </div>'''
            
            # Если несколько игроков - располагаем вертикально
            players_html = ''.join(f'<div class="match-player-name">{p}</div>' for p in players[:2])
            return f'''<div class="match-team">
                <div class="match-team-names">{players_html}</div>
                {wo_div}{score_div}
            </div>'''

        return f'''
            <div class="match-item {status_class} row-{row}" style="grid-row: {row}; grid-column: {col};">
                <div class="match-content">
                    <div class="match-number">{episode}</div>
                    <div class="match-teams-wrapper">
                        {team_html(challenger_players, challenger_wo, challenger_result)}
                        {team_html(challenged_players, challenged_wo, challenged_result)}
                    </div>
                </div>
            </div>'''

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Генерирует пустую страницу расписания"""
        name_class = self._get_tournament_name_class(tournament_name)
        
        return f'''{self.html_head(f"Расписание матчей - {tournament_name}", "schedule.css")}
<body>
    <div class="schedule-container">
        <!-- Header -->
        <div class="header">
            <div class="tournament-name {name_class}">{tournament_name}</div>
            <div class="logos">
                <div class="logo logo4" style="background-image: url('/static/images/logo4.png');"></div>
                <div class="logo logo3" style="background-image: url('/static/images/logo3.png');"></div>
                <div class="logo logo2" style="background-image: url('/static/images/logo2.png');"></div>
                <div class="logo logo1" style="background-image: url('/static/images/logo1.png');"></div>
            </div>
        </div>
        <div class="empty-message"><p>{message}</p></div>
    </div>
</body>
</html>'''