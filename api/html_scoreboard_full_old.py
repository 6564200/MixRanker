#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор полноэкранного HTML scoreboard
"""
from .html_base import HTMLBaseGenerator
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ScoreboardFullGenerator(HTMLBaseGenerator):
    """Генератор полноэкранного scoreboard для 4K/FHD/HD"""

    def generate_scoreboard_full_html(
        self, 
        court_data: Dict, 
        tournament_data: Dict = None,
        tournament_id: str = None,
        court_id: str = None
    ) -> str:
        """Генерирует полноэкранный HTML scoreboard"""
        
        # Извлекаем данные
        match = self._extract_match_data(court_data)
        tournament_name = self._get_tournament_name(tournament_data)
        
        # Данные игроков
        team1_players = match["team1_players"]
        team2_players = match["team2_players"]
        
        # Счёт
        detailed_result = match["detailed_result"]
        team1_game_score = match["team1_score"]  # Текущие геймы (40, 30...)
        team2_game_score = match["team2_score"]
        
        # Итоговый счёт по сетам
        team1_sets_won = sum(1 for s in detailed_result if s.get("firstParticipantScore", 0) > s.get("secondParticipantScore", 0))
        team2_sets_won = sum(1 for s in detailed_result if s.get("secondParticipantScore", 0) > s.get("firstParticipantScore", 0))
        
        # Показывать ли колонку СЧЁТ (текущие геймы)
        event_state = match["event_state"].lower()
        is_finished = event_state == "finished"
        show_game_score = not is_finished and (team1_game_score != 0 or team2_game_score != 0)
        
        # Формируем HTML для сетов
        sets_header_html = self._render_sets_header(detailed_result)
        team1_sets_html = self._render_team_sets(detailed_result, "first")
        team2_sets_html = self._render_team_sets(detailed_result, "second")
        
        # HTML для колонки СЧЁТ (текущие геймы)
        # game_score_header = '<div class="header-cell game-score">СЧЁТ</div>' if show_game_score else ''                                        {game_score_header}
        # team1_game_html = f'<div class="score-cell game-score" data-field="team1_game">{team1_game_score}</div>' if show_game_score else ''    {team1_game_html}
        # team2_game_html = f'<div class="score-cell game-score" data-field="team2_game">{team2_game_score}</div>' if show_game_score else ''    {team2_game_html}
        
        # Формируем HTML для игроков
        team1_html = self._render_team_block(team1_players, "team1")
        team2_html = self._render_team_block(team2_players, "team2")
        
        # Проверяем наличие матча
        has_match = match["show_current_match"]
        
        # Формируем контент таблицы
        if has_match:
            table_content = f'''
            <!-- Team 1 -->
            <div class="team-row" data-team="1">
                {team1_html}
                <div class="scores-block">
                    {team1_sets_html}
                    <div class="score-cell total" data-field="team1_total">{team1_game_score}</div>
                </div>
            </div>
            
            <!-- Green Line -->
            <div class="green-line"></div>
            
            <!-- Team 2 -->
            <div class="team-row" data-team="2">
                {team2_html}
                <div class="scores-block">
                    {team2_sets_html}
                    <div class="score-cell total" data-field="team2_total">{team2_game_score}</div>
                </div>
            </div>
            
            <!-- Bottom Green Line -->
            <div class="green-line"></div>
            '''
        else:
            table_content = '''
            <!-- No Match -->
            <div class="no-match">
                <span class="no-match-text">Нет активного матча</span>
            </div>
            '''
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scoreboard Full - {tournament_name}</title>
    <link rel="stylesheet" href="/static/css/scoreboard_full.css">
</head>
<body>
    <div class="scoreboard-full-container" data-tournament-id="{tournament_id}" data-court-id="{court_id}">
        
        <!-- Header -->
        <div class="header">
            <div class="tournament-name">{tournament_name}</div>
            <div class="logos">
                <div class="logo logo4" style="background-image: url('/static/images/logo4.png');"></div>
                <div class="logo logo3" style="background-image: url('/static/images/logo3.png');"></div>
                <div class="logo logo2" style="background-image: url('/static/images/logo2.png');"></div>
                <div class="logo logo1" style="background-image: url('/static/images/logo1.png');"></div>
            </div>
        </div>
        
        <!-- Table -->
        <div class="table">
            <!-- Table Header -->
            <div class="table-header">
              <div class="table-header-block">
                {sets_header_html}
                
                <div class="header-cell total">СЧЕТ</div>
              </div>
            </div>
            
            {table_content}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="banner banner-arena">ПАДЕЛ-АРЕНА РМК</div>
            <div class="banner banner-address">БОЛЬШАКОВА, 90</div>
        </div>
        
    </div>
    <script src="/static/js/scoreboard_full.js"></script>
</body>
</html>'''

    def _extract_match_data(self, court_data: Dict) -> Dict:
        """Извлекает данные матча из court_data"""
        if not court_data:
            return self._empty_match_data()
        
        first_participant = court_data.get("first_participant") or court_data.get("firstParticipant") or []
        second_participant = court_data.get("second_participant") or court_data.get("secondParticipant") or []
        detailed_result = court_data.get("detailed_result") or court_data.get("detailedResult") or []
        
        # Текущий счёт в геймах
        team1_score = court_data.get("first_participant_score") or court_data.get("firstParticipantScore") or 0
        team2_score = court_data.get("second_participant_score") or court_data.get("secondParticipantScore") or 0
        
        # Проверяем геймовый счёт в последнем сете
        if detailed_result:
            last_set = detailed_result[-1]
            game_score = last_set.get("gameScore", {})
            if game_score:
                team1_score = game_score.get("first", team1_score)
                team2_score = game_score.get("second", team2_score)
        
        event_state = court_data.get("event_state", "").lower()
        show_match = bool(first_participant or second_participant) and event_state != "idle"
        
        return {
            "team1_players": first_participant,
            "team2_players": second_participant,
            "detailed_result": detailed_result,
            "team1_score": team1_score,
            "team2_score": team2_score,
            "show_current_match": show_match,
            "event_state": event_state
        }

    def _empty_match_data(self) -> Dict:
        """Пустые данные матча"""
        return {
            "team1_players": [],
            "team2_players": [],
            "detailed_result": [],
            "team1_score": 0,
            "team2_score": 0,
            "show_current_match": False,
            "event_state": ""
        }

    def _get_tournament_name(self, tournament_data: Dict) -> str:
        """Получает название турнира"""
        if not tournament_data:
            return "ТУРНИР"
        metadata = tournament_data.get("metadata", {})
        return metadata.get("name", "ТУРНИР")

    def _render_sets_header(self, detailed_result: List) -> str:
        """Рендерит заголовки сетов - только для сыгранных"""
        num_sets = len(detailed_result) if detailed_result else 0
        html = ""
        for i in range(num_sets):
            html += f'<div class="header-cell">СЕТ {i + 1}</div>'
        return html

    def _render_team_sets(self, detailed_result: List, team: str) -> str:
        """Рендерит счёт по сетам для команды - только сыгранные"""
        html = ""
        
        if not detailed_result:
            return html
        
        score_key = "firstParticipantScore" if team == "first" else "secondParticipantScore"
        team_prefix = "team1" if team == "first" else "team2"
        
        for i, set_data in enumerate(detailed_result):
            score = set_data.get(score_key, "-")
            html += f'<div class="score-cell" data-field="{team_prefix}_set{i + 1}">{score}</div>'
        
        return html

    def _render_team_block(self, players: List, team_prefix: str) -> str:
        """Рендерит блок команды с именами и флагами"""
        player1 = players[0] if len(players) > 0 else {}
        player2 = players[1] if len(players) > 1 else {}
        
        name1 = self.format_player_name(player1)
        name2 = self.format_player_name(player2)
        
        flag1_url = self.get_flag_url(player1.get("countryCode", ""))
        flag2_url = self.get_flag_url(player2.get("countryCode", ""))
        
        return f'''
            <div class="team-name-block">
                <div class="player-row">
                    <div class="player-flag" data-field="{team_prefix}_flag1" style="background-image: url('{flag1_url}');"></div>
                    <div class="player-name" data-field="{team_prefix}_player1">{name1}</div>
                </div>
                <div class="player-row">
                    <div class="player-flag" data-field="{team_prefix}_flag2" style="background-image: url('{flag2_url}');"></div>
                    <div class="player-name" data-field="{team_prefix}_player2">{name2}</div>
                </div>
            </div>
        '''