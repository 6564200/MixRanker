#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML для Round Robin (групповых таблиц)
"""

from typing import Dict, List, Optional
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class RoundRobinGenerator(HTMLBaseGenerator):
    """Генератор групповых таблиц Round Robin"""

    def generate_round_robin_html(
        self, 
        tournament_data: Dict, 
        xml_type_info: Dict,
        tournament_id: str = None
    ) -> str:
        """Генерирует HTML для групповой турнирной таблицы"""
        class_id = xml_type_info.get("class_id")
        draw_index = xml_type_info.get("draw_index", 0)

        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        round_robin_data = class_data.get("round_robin", [])

        if draw_index >= len(round_robin_data):
            return self._generate_empty_html("Нет данных групповой таблицы")

        rr_data = round_robin_data[draw_index]
        if not rr_data or "RoundRobin" not in rr_data:
            return self._generate_empty_html("Неверные данные групповой таблицы")

        group_data = rr_data["RoundRobin"]
        class_name = (xml_type_info.get("class_name", "Категория")).upper()
        group_name = (xml_type_info.get("group_name", "Группа")).upper()

        participants = self._extract_participants(group_data)
        matches_matrix = self._extract_matches_matrix(group_data, len(participants))
        standings = self._extract_standings(group_data)

        return self._render_html(
            class_name, group_name, participants, matches_matrix, standings,
            tournament_id, class_id, draw_index
        )

    def _render_html(
        self, 
        class_name: str, 
        group_name: str,
        participants: List[Dict], 
        matches_matrix: Dict, 
        standings: List[Dict],
        tournament_id: str = None,
        class_id: str = None,
        draw_index: int = 0
    ) -> str:
        """Рендерит HTML round robin таблицы с адаптивным масштабированием"""
        
        num_participants = len(participants)
        
        # FHD базовые размеры (3/4 экрана = ~1440x810)
        col_width = 175
        team_cell_width = 550
        num_width = 70
        points_col_width = 130
        row_height = 85
        header_height = 65
        gap = 2
        
        # Общая ширина/высота таблицы
        table_width = team_cell_width + (num_participants * col_width) + (2 * points_col_width)
        table_height = header_height + (num_participants * (row_height + gap))

        # Заголовок
        display_name = class_name[class_name.find(",") + 1:].strip() if "," in class_name else class_name
        
        # Заголовки номеров команд
        num_cols_html = ''.join(
            f'<div class="team-number-header" style="width:{col_width}px;">'
            f'<div class="team-number" style="width:{col_width}px;">{i}</div></div>' 
            for i in range(1, num_participants + 1)
        )

        html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{class_name} - {group_name}</title>
    <link rel="stylesheet" href="/static/css/round_robin.css">
</head>
<body>
    <div class="round-robin-container" 
         data-tournament-id="{tournament_id or ''}" 
         data-class-id="{class_id or ''}"
         data-draw-index="{draw_index}">
        <div class="round-robin-table" style="width:{table_width}px;">
            <div class="table-title" style="width:{table_width}px;">
                <div class="table-header" style="width:{team_cell_width}px;">
                    <div class="cell-num" style="width:{num_width}px;"></div>
                    <div class="cell-gpp" data-field="title">{display_name} - {group_name}</div>
                </div>
                {num_cols_html}
                <div class="points-header" style="width:{points_col_width}px;">
                    <div class="points" style="width:{points_col_width}px;">ОЧКИ</div>
                </div>
                <div class="points-header" style="width:{points_col_width}px;">
                    <div class="points" style="width:{points_col_width}px;">МЕСТО</div>
                </div>
            </div>'''

        # Строки участников
        for i, participant in enumerate(participants):
            place = self._get_participant_place(participant, standings)
            points = self._get_participant_points(participant, standings)
            short_name = (participant.get("short_name", " ")).upper()
            participant_id = participant.get("participant_id", "")

            # Ячейки матчей
            cells = []
            for j in range(num_participants):
                if i == j:
                    cells.append(f'<div class="diagonal-cell" style="width:{col_width}px;"></div>')
                else:
                    match_result = matches_matrix.get(f"{i}_{j}", {})
                    cells.append(self._render_match_cell(match_result, col_width, i, j))

            html += f'''
            <div class="team-row" style="width:{table_width}px;" data-participant-id="{participant_id}" data-row-index="{i}">
                <div class="team-number-cell" style="width:{team_cell_width}px;">
                    <div class="team-num" style="width:{num_width}px;">{i + 1}</div>
                    <div class="team-name-cell" style="width:{team_cell_width - num_width}px;" data-field="team_name_{i}">{short_name}</div>
                </div>
                {''.join(cells)}
                <div class="points-cell" style="width:{points_col_width}px;">
                    <div class="points-z" style="width:{points_col_width}px;" data-field="points_{i}">{points}</div>
                </div>
                <div class="place-cell" style="width:{points_col_width}px;">
                    <div class="place-z" style="width:{points_col_width}px;" data-field="place_{i}">{place}</div>
                </div>
            </div>'''

        html += '''
        </div>
    </div>
    <script src="/static/js/round_robin.js"></script>
</body>
</html>'''
        return html

    def _render_match_cell(self, match_result: Dict, col_width: int, row: int, col: int) -> str:
        """Рендерит ячейку матча с data-атрибутами"""
        style = f'style="width:{col_width}px;"'
        data_attrs = f'data-row="{row}" data-col="{col}"'
        
        if match_result.get("is_bye"):
            return f'<div class="match-cell-bye-cell" {style}>●</div>'
        
        if match_result.get("has_result"):
            score = match_result.get("score", "-")
            sets = match_result.get("sets", "")
            return f'''<div class="match-cell" {style} {data_attrs}>
                <div class="match-score" data-field="score_{row}_{col}">{score}</div>
                <div class="match-sets" data-field="sets_{row}_{col}">{sets}</div>
            </div>'''
        
        return f'<div class="match-cell-empty-cell" {style} {data_attrs}></div>'

    def _generate_empty_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу"""
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Round Robin</title>
    <link rel="stylesheet" href="/static/css/round_robin.css">
</head>
<body>
    <div class="round-robin-container">
        <div class="empty-message">{message}</div>
    </div>
    <script src="/static/js/round_robin.js"></script>
</body>
</html>'''

    def _extract_participants(self, group_data: Dict) -> List[Dict]:
        """Извлекает участников из групповых данных"""
        participants = []

        for row in group_data.get("Pool", []):
            if not isinstance(row, list):
                continue
            for cell in row:
                if not isinstance(cell, dict):
                    continue
                if cell.get("CellType") == "ParticipantCell" and cell.get("ParticipantCell"):
                    participant = self._parse_participant_cell(cell["ParticipantCell"], len(participants))
                    if participant:
                        participants.append(participant)

        half = len(participants) // 2
        return participants[:half] if half > 0 else participants

    def _parse_participant_cell(self, cell: Dict, fallback_index: int) -> Optional[Dict]:
        """Парсит ячейку участника"""
        players = cell.get("Players", [])
        if not isinstance(players, list):
            return None

        team_names = [p["Name"] for p in players if isinstance(p, dict) and p.get("Name")]
        if not team_names:
            return None

        full_name = "/".join(team_names)
        player_ids = [str(p["Id"]) for p in players if isinstance(p, dict) and p.get("Id")]

        return {
            "index": cell.get("Index", fallback_index),
            "participant_id": cell.get("ParticipantId"),
            "full_name": full_name,
            "short_name": self.create_short_name(full_name) if full_name != "Bye" else "Bye",
            "is_bye": full_name.upper() == "BYE",
            "player_ids": player_ids
        }

    def _extract_matches_matrix(self, group_data: Dict, num_participants: int) -> Dict:
        """Извлекает матчи в формате матрицы"""
        matches_matrix = {}

        for row_idx, row in enumerate(group_data.get("Pool", [])):
            if not isinstance(row, list):
                continue
            for cell_idx, cell in enumerate(row):
                if not isinstance(cell, dict):
                    continue
                if cell.get("CellType") == "MatchCell" and cell.get("MatchCell"):
                    match_info = self._parse_match_cell(cell["MatchCell"])
                    if row_idx != cell_idx:
                        matches_matrix[f"{row_idx - 1}_{cell_idx - 1}"] = match_info

        return matches_matrix

    def _parse_match_cell(self, match_cell: Dict) -> Dict:
        """Парсит ячейку матча"""
        match_results = match_cell.get("MatchResults", {})
        match_info = {
            "has_result": bool(match_results.get("IsPlayed", False)),
            "is_bye": False,
            "score": "",
            "sets": ""
        }

        if match_results.get("HasScore") and match_results.get("Score"):
            score_data = match_results["Score"]
            first_score = score_data.get("FirstParticipantScore", 0)
            second_score = score_data.get("SecondParticipantScore", 0)
            match_info["score"] = f"{first_score}-{second_score}"

            detailed_scoring = score_data.get("DetailedScoring", [])
            if detailed_scoring:
                sets_parts = [f"{s.get('FirstParticipantScore', 0)}-{s.get('SecondParticipantScore', 0)}" 
                              for s in detailed_scoring]
                match_info["sets"] = " ".join(sets_parts)
        else:
            cancellation = match_results.get('CancellationStatus') or ''
            if 'Won' in cancellation:
                match_info["score"] = 'Won'
            elif 'Lost' in cancellation:
                match_info["score"] = 'Lost'

        return match_info

    def _extract_standings(self, group_data: Dict) -> List[Dict]:
        """Извлекает турнирную таблицу"""
        standings_data = group_data.get("Standings", [])
        standings = []
        fake_id_counter = 1000

        for standing in standings_data:
            if not isinstance(standing, dict):
                continue

            player_ids = []
            for key in ['DoublesPlayer1Model', 'DoublesPlayer2Model']:
                player = standing.get(key)
                if isinstance(player, dict) and player.get('Id'):
                    player_ids.append(str(player['Id']))
                else:
                    player_ids.append(str(fake_id_counter))
                    fake_id_counter += 1

            standings.append({
                "participant_id": str(standing.get("ParticipantId", "")),
                "standing": standing.get("Standing", 0),
                "wins": standing.get("Wins", 0),
                "match_points": standing.get("MatchPoints", 0),
                "player_ids": player_ids
            })

        return standings

    def _get_participant_place(self, participant: Dict, standings: List[Dict]) -> str:
        """Получает место участника"""
        for standing in standings:
            if set(standing.get("player_ids", [])) == set(participant.get("player_ids", [])):
                return str(standing.get("standing", "-"))
        return "-"

    def _get_participant_points(self, participant: Dict, standings: List[Dict]) -> str:
        """Получает очки участника"""
        for standing in standings:
            if set(standing.get("player_ids", [])) == set(participant.get("player_ids", [])):
                return str(standing.get("match_points", "-"))
        return "-"
