#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страницы представления игрока (Player Introduction)
"""

from typing import Dict
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class IntroPlayerGenerator(HTMLBaseGenerator):
    """Генератор страницы представления отдельного игрока"""

    def generate_introduction_page_html(
        self, 
        participant_info: Dict,
        tournament_id: str = None
    ) -> str:
        """Генерирует страницу представления участника"""
        
        # Данные игрока
        first_name = participant_info.get("firstName", "") or participant_info.get("FirstName", "")
        last_name = participant_info.get("lastName", "") or participant_info.get("LastName", "")
        full_name = f"{first_name} {last_name}".strip().upper()
        
        country = participant_info.get("country", "") or participant_info.get("Country", "")
        country_code = participant_info.get("countryCode", "") or participant_info.get("CountryShort", "")
        rating = participant_info.get("rating", "") or participant_info.get("Rating", "")
        height = participant_info.get("height", "") or participant_info.get("Height", "")
        position = participant_info.get("position", "") or participant_info.get("Position", "")
        
        # URL флага
        flag_url = self.get_flag_url(country_code)
        
        # ID участника
        player_id = participant_info.get("id", "") or participant_info.get("Id", "")
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{player_id} - Introduction</title>
    <link rel="stylesheet" href="/static/css/intro_player.css">
</head>
<body>
    <div class="intro-player-container" data-tournament-id="{tournament_id or ''}" data-player-id="{player_id}">
        <div class="player-card">
            <div class="player-header">
                <div class="player-flag" data-field="player_flag" style="background-image: url('{flag_url}');"></div>
                <div class="player-name" data-field="player_name">{full_name}</div>
            </div>
            <div class="player-info">
                <div class="info-row">
                    <span class="info-label">СТРАНА</span>
                    <span class="info-value" data-field="player_country">{country}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">РЕЙТИНГ FIP</span>
                    <span class="info-value" data-field="player_rating">{rating}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">РОСТ</span>
                    <span class="info-value" data-field="player_height">{height}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">ИГРОВАЯ ПОЗИЦИЯ</span>
                    <span class="info-value" data-field="player_position">{position}</span>
                </div>
            </div>
        </div>
    </div>
    <script src="/static/js/intro_player.js"></script>
</body>
</html>'''
