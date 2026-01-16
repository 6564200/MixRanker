#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страницы представления матча (Introduction)
"""

from typing import Dict, List
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class IntroductionGenerator(HTMLBaseGenerator):
    """Генератор страницы представления матча для трансляций"""

    def generate_match_introduction_html(
        self, 
        court_data: Dict, 
        match_info: Dict = None,
        tournament_id: str = None,
        court_id: str = None
    ) -> str:
        """Генерирует страницу представления матча (intro для обеих команд)"""
        
        # Получаем данные участников
        first_participant = court_data.get("first_participant", []) or court_data.get("firstParticipant", [])
        second_participant = court_data.get("second_participant", []) or court_data.get("secondParticipant", [])
        
        # Игроки команды 1
        team1_player1 = first_participant[0] if len(first_participant) > 0 else {}
        team1_player2 = first_participant[1] if len(first_participant) > 1 else {}
        
        # Игроки команды 2
        team2_player1 = second_participant[0] if len(second_participant) > 0 else {}
        team2_player2 = second_participant[1] if len(second_participant) > 1 else {}
        
        # Имена
        team1_name1 = self.format_player_name(team1_player1)
        team1_name2 = self.format_player_name(team1_player2)
        team2_name1 = self.format_player_name(team2_player1)
        team2_name2 = self.format_player_name(team2_player2)
        
        # Флаги
        team1_flag1 = self.get_flag_url(team1_player1.get("countryCode", ""))
        team1_flag2 = self.get_flag_url(team1_player2.get("countryCode", ""))
        team2_flag1 = self.get_flag_url(team2_player1.get("countryCode", ""))
        team2_flag2 = self.get_flag_url(team2_player2.get("countryCode", ""))
        
        # Название раунда
        round_name = self._get_round_name(match_info) if match_info else court_data.get("class_name", "") or court_data.get("className", "")
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Match Introduction</title>
    <link rel="stylesheet" href="/static/css/introduction.css">
</head>
<body>
    <div class="intro-container" data-tournament-id="{tournament_id or ''}" data-court-id="{court_id or ''}">
        <div class="intro-header">
            <div class="intro-header-text" data-field="round_name">{round_name}</div>
        </div>
        <div class="intro-main">
            <div class="intro-frame">
                <div class="intro-info">
                    <!-- Команда 1 (слева) -->
                    <div class="team1-flag1" data-field="team1_flag1" style="background-image: url('{team1_flag1}');"></div>
                    <div class="team1-name1" data-field="team1_name1">{team1_name1}</div>
                    <div class="team1-flag2" data-field="team1_flag2" style="background-image: url('{team1_flag2}');"></div>
                    <div class="team1-name2" data-field="team1_name2">{team1_name2}</div>
                    
                    <!-- Команда 2 (справа) -->
                    <div class="team2-name1" data-field="team2_name1">{team2_name1}</div>
                    <div class="team2-flag1" data-field="team2_flag1" style="background-image: url('{team2_flag1}');"></div>
                    <div class="team2-name2" data-field="team2_name2">{team2_name2}</div>
                    <div class="team2-flag2" data-field="team2_flag2" style="background-image: url('{team2_flag2}');"></div>
                </div>
            </div>
        </div>
    </div>
    <script src="/static/js/introduction.js"></script>
</body>
</html>'''

    def _get_round_name(self, match_info: Dict) -> str:
        """Определяет название раунда из match_info"""
        if not match_info:
            return ""
        
        # Прямые флаги
        if match_info.get("IsFinal"):
            return "ФИНАЛ"
        if match_info.get("IsSemiFinal"):
            return "1/2 ФИНАЛА"
        if match_info.get("IsQuarterFinal"):
            return "1/4 ФИНАЛА"
        
        # По Places
        places = match_info.get("Places", {})
        if places:
            place1 = places.get("Item1", 0)
            place2 = places.get("Item2", 0)
            diff = abs(place2 - place1) + 1
            
            if diff == 2:
                return "ФИНАЛ"
            elif diff == 4:
                return "1/2 ФИНАЛА"
            elif diff == 8:
                return "1/4 ФИНАЛА"
            elif diff == 16:
                return "1/8 ФИНАЛА"
            elif diff == 32:
                return "1/16 ФИНАЛА"
        
        # Групповой этап
        pool_name = match_info.get("PoolName", "")
        if pool_name:
            return pool_name.upper()
        
        # Fallback на Round
        round_num = match_info.get("Round", 0)
        if round_num:
            return f"РАУНД {round_num}"
        
        return ""
