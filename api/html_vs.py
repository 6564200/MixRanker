#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор VS (versus) и Winner страниц
"""

from typing import Dict, List
from .html_base import HTMLBaseGenerator
from .constants import get_country_name_ru
import logging

logger = logging.getLogger(__name__)


class VSGenerator(HTMLBaseGenerator):
    """Генератор VS и Winner страниц"""

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
        """Генерирует HTML блоков сетов"""
        html = ""
        for i in range(3):
            if scores1[i] or scores2[i]:
                html += f'''
                <div class="set-block">
                    <div class="set-header"><div class="set-header-text">СЕТ {i + 1}</div></div>
                    <div class="set-scores">
                        <div class="set-score">{scores1[i]}</div>
                        <div class="score-divider"></div>
                        <div class="set-score">{scores2[i]}</div>
                    </div>
                </div>'''

        # Блок геймов
        game1 = self.get_game_score_display(detailed, scores1[3], 'first')
        game2 = self.get_game_score_display(detailed, scores2[3], 'second')

        html += f'''
            <div class="set-block game-block">
                <div class="set-header game-header"><div class="set-header-text">ГЕЙМЫ</div></div>
                <div class="set-scores">
                    <div class="set-score">{game1}</div>
                    <div class="score-divider"></div>
                    <div class="set-score">{game2}</div>
                </div>
            </div>'''

        return html

    def generate_court_vs_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует VS страницу с фотографиями игроков"""
        team1 = court_data.get("first_participant", [])
        team2 = court_data.get("second_participant", [])
        scores1, scores2, detailed = self._extract_scores(court_data)

        header_title = tournament_data.get("metadata", {}).get("name", "ТУРНИР") if tournament_data else "ТУРНИР"
        sets_html = self._build_sets_html(scores1, scores2, detailed)

        team1_photos = self._generate_player_photos_html(team1[:2])
        team2_photos = self._generate_player_photos_html(team2[:2])

        team1_names = ''.join(f'<div class="player-name">{p.get("fullName", "")}</div>' for p in team1[:2])
        team2_names = ''.join(f'<div class="player-name">{p.get("fullName", "")}</div>' for p in team2[:2])

        return f'''{self.html_head(f"VS - {header_title}", "vs.css")}
<body>
    <div class="vs-container">
        <div class="header-text">
            <div class="header-location"></div>
            <div class="header-title"></div>
        </div>
        <div class="teams-wrapper">
            <div class="team-container team-left">{team1_photos}</div>
            <div class="team-container team-right">{team2_photos}</div>
        </div>
        <div class="score-section">{sets_html}</div>
        <div class="bottom-plashka">
            <div class="plashka-border"></div>
            <div class="plashka-content">
                <div class="team-names team-left">{team1_names}</div>
                <div class="team-names team-right">{team2_names}</div>
            </div>
        </div>
    </div>
</body>
</html>'''

    def generate_winner_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует HTML страницу победителей"""
        court_name = court_data.get("court_name", "Court")
        event_state = court_data.get("event_state", "")
        class_name = court_data.get("class_name")

        if event_state != 'Finished' or not id_url:
            return self.empty_page_html(f"{court_name} - Winner", "NO WINNER", "winner.css")

        score1 = court_data.get("first_participant_score", 0)
        score2 = court_data.get("second_participant_score", 0)

        if score1 > score2:
            winners = court_data.get("first_participant", [])
            losers = court_data.get("second_participant", [])
        else:
            winners = court_data.get("second_participant", [])
            losers = court_data.get("first_participant", [])

        if not winners:
            return self.empty_page_html(f"{court_name} - Winner", "NO WINNER", "winner.css")

        id_url_map = {d['id']: d for d in id_url}
        winners_enriched = [(p, id_url_map.get(p.get('id'), {})) for p in winners if p.get('id')]
        losers_name = ' / '.join(l.get("initialLastName", l.get("lastName", "")) for l in losers)

        detailed = court_data.get("detailed_result", [])
        scores_html = ''.join(
            f'<div class="set_score">{r.get("firstParticipantScore")}/{r.get("secondParticipantScore")}</div>'
            for r in detailed
        )

        winners_table = []
        winners_images = []

        for w, photo_data in winners_enriched:
            code = w.get("countryCode", "").lower()
            if code == 'rin':
                code = 'ru'
            flag_url = f"/static/flags/4x3/{code}.svg"
            country_name = get_country_name_ru(w.get("countryCode", ""))
            full_name = w.get("fullName", "")

            winners_table.append(f'''<div>
                <img src="{flag_url}" class="flag-icon" alt="{code}">
                <div class="player-info">
                    <div class="win_name">{full_name}</div>
                    <div class="country_name">{country_name}</div>
                </div>
            </div>''')

            photo_url = photo_data.get("photo_url", "")
            if photo_url:
                winners_images.append(f'<img src="{photo_url}" alt="{full_name}">')
            else:
                winners_images.append('<img src="/static/images/silhouette.png" class="silhouette" alt="Player">')

        return f'''{self.html_head(f"{court_name} - Winner", "winner.css", 100000)}
<body>
    <div class="winner">
        <div class="winner_container">
            <div class="class_name">{class_name}</div>
            <div class="txt_winner">ПОБЕДИТЕЛЬ</div>
            <div class="winners_table">{''.join(winners_table)}</div>
            <div class="image_container">{''.join(winners_images)}</div>
            <div class="info_block">
                <span>ПРОТИВ</span>
                <span class="loser">{losers_name}</span>
                <div class="score">{scores_html}</div>
            </div>
        </div>
    </div>
</body>
</html>'''
