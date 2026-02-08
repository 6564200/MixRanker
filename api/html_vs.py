#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор VS (versus) страниц
"""

from typing import Dict, List
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class VSGenerator(HTMLBaseGenerator):
    """Генератор VS страниц"""

    def _extract_scores(self, court_data: Dict) -> tuple:
        """Извлекает счета по сетам. Возвращает (scores1, scores2, detailed)"""
        detailed = court_data.get("detailed_result", [])
        score1 = court_data.get("first_participant_score", 0)
        score2 = court_data.get("second_participant_score", 0)

        scores1 = [0, 0, 0, score1]
        scores2 = [0, 0, 0, score2]

        for i, s in enumerate(detailed[:3]):
            scores1[i] = s.get("firstParticipantScore", 0)
            scores2[i] = s.get("secondParticipantScore", 0)

        return scores1, scores2, detailed

    def _generate_player_photos_html(self, players: List[Dict]) -> str:
        """Генерирует HTML для фото игроков"""
        html = []
        for p in players[:2]:
            photo = p.get("photo_url")
            name = p.get("fullName", "")
            if photo:
                html.append(f'<img src="{photo}" class="player-photo" alt="{name}">')
            else:
                html.append('<img src="/static/images/silhouette.png" class="player-photo silhouette" alt="Player">')
        return ''.join(html)

    def _build_sets_html(self, scores1: List[int], scores2: List[int], detailed: List[Dict]) -> str:
        """Генерирует HTML блоков сетов с data-field атрибутами"""
        html = ""
        for i in range(3):
            if scores1[i] or scores2[i]:
                
                html += f'''
                <div class="set-block">
                    <div class="set-header"><div class="set-header-text">СЕТ {i + 1}</div></div>
                    <div class="set-scores">
                        <div class="set-score" data-field="set{i+1}_score1">{scores1[i]}</div>
                        <div class="score-divider"></div>
                        <div class="set-score" data-field="set{i+1}_score2">{scores2[i]}</div>
                    </div>
                </div>'''

        return html

    def generate_court_vs_html(
        self, 
        court_data: Dict, 
        tournament_data: Dict = None,
        tournament_id: str = None,
        court_id: str = None
    ) -> str:
        """Генерирует VS страницу с фотографиями игроков"""
        team1 = court_data.get("first_participant", [])
        team2 = court_data.get("second_participant", [])
        scores1, scores2, detailed = self._extract_scores(court_data)

        header_title = tournament_data.get("metadata", {}).get("name", "ТУРНИР") if tournament_data else "ТУРНИР"
        sets_html = self._build_sets_html(scores1, scores2, detailed)

        team1_photos = self._generate_player_photos_html(team1[:2])
        team2_photos = self._generate_player_photos_html(team2[:2])

        # Имена с флагами и data-field
        team1_names = ''
        for i, p in enumerate(team1[:2]):
            name = self.format_player_name(p)
            flag_url = self.get_flag_url(p.get("countryCode", ""))
            team1_names += f'''<div class="player-row">
                <div class="player-flag" data-field="team1_flag{i+1}" style="background-image: url('{flag_url}');"></div>
                <div class="player-name" data-field="team1_player{i+1}">{name}</div>
            </div>'''
        
        team2_names = ''
        for i, p in enumerate(team2[:2]):
            name = self.format_player_name(p)
            flag_url = self.get_flag_url(p.get("countryCode", ""))
            team2_names += f'''<div class="player-row">
                <div class="player-name" data-field="team2_player{i+1}">{name}</div>
                <div class="player-flag" data-field="team2_flag{i+1}" style="background-image: url('{flag_url}');"></div>
            </div>'''

        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VS - {header_title}</title>
    <link rel="stylesheet" href="/static/css/vs.css">
</head>
<body>
    <div class="vs-container" data-tournament-id="{tournament_id or ''}" data-court-id="{court_id or ''}">
        <div class="header-text">
            <div class="header-location"></div>
            <div class="header-title" data-field="tournament_name">{header_title}</div>
        </div>
        <div class="teams-wrapper">
            <div class="team-container team-left">{team1_photos}</div>
            <div class="team-container team-right">{team2_photos}</div>
        </div>
        <div class="bottom-section">
            <div class="score-section">{sets_html}</div>
            <div class="bottom-plashka">
                <div class="plashka-border"></div>
                <div class="plashka-content">
                    <div class="team-names team-left">{team1_names}</div>
                    <div class="team-names team-right">{team2_names}</div>
                </div>
            </div>
        </div>
    </div>
    <script src="/static/js/vs.js"></script>
</body>
</html>'''