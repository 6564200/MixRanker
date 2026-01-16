#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор Winner страницы
"""

from typing import Dict, List
from .html_base import HTMLBaseGenerator
from .constants import get_country_name_ru
import logging

logger = logging.getLogger(__name__)


class WinnerGenerator(HTMLBaseGenerator):
    """Генератор страницы победителя"""

    def generate_winner_page_html(
        self, 
        court_data: Dict, 
        id_url: List[Dict] = None, 
        tournament_data: Dict = None,
        tournament_id: str = None,
        court_id: str = None
    ) -> str:
        """Генерирует HTML страницу победителей"""
        court_name = court_data.get("court_name", "Court")
        event_state = court_data.get("event_state", "")
        class_name = court_data.get("class_name", "")

        if event_state != 'Finished':
            return self._empty_winner_html(court_name)

        score1 = court_data.get("first_participant_score", 0)
        score2 = court_data.get("second_participant_score", 0)

        if score1 > score2:
            winners = court_data.get("first_participant", [])
            losers = court_data.get("second_participant", [])
        else:
            winners = court_data.get("second_participant", [])
            losers = court_data.get("first_participant", [])

        if not winners:
            return self._empty_winner_html(court_name)

        losers_name = ' / '.join(l.get("initialLastName", l.get("lastName", "")) for l in losers)

        detailed = court_data.get("detailed_result", [])
        scores_html = ''.join(
            f'<div class="set_score" data-field="set{i}_score">{r.get("firstParticipantScore")}/{r.get("secondParticipantScore")}</div>'
            for i, r in enumerate(detailed)
        )

        winners_table = []
        winners_images = []

        for i, w in enumerate(winners[:2]):
            code = w.get("countryCode", "").lower()
            if code == 'rin':
                code = 'ru'
            flag_url = f"/static/flags/4x3/{code}.svg"
            country_name = get_country_name_ru(w.get("countryCode", ""))
            full_name = w.get("fullName", "")
            
            # Берём photo_url напрямую из данных игрока
            photo_url = w.get("photo_url", "")
            
            logger.debug(f"Winner {i}: {full_name}, photo_url: {photo_url}")

            winners_table.append(f'''<div>
                <img src="{flag_url}" class="flag-icon" data-field="winner{i}_flag" alt="{code}">
                <div class="player-info">
                    <div class="win_name" data-field="winner{i}_name">{full_name}</div>
                    <div class="country_name" data-field="winner{i}_country">{country_name}</div>
                </div>
            </div>''')

            if photo_url:
                winners_images.append(f'<img src="{photo_url}" data-field="winner{i}_photo" alt="{full_name}">')
            else:
                winners_images.append(f'<img src="/static/images/silhouette.png" class="silhouette" data-field="winner{i}_photo" alt="Player">')

        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{court_name} - Winner</title>
    <link rel="stylesheet" href="/static/css/winner.css">
</head>
<body>
    <div class="winner" data-tournament-id="{tournament_id or ''}" data-court-id="{court_id or ''}">
        <div class="winner_container">
            <div class="class_name" data-field="class_name">{class_name}</div>
            <div class="txt_winner">ПОБЕДИТЕЛЬ</div>
            <div class="winners_table">{''.join(winners_table)}</div>
            <div class="image_container">{''.join(winners_images)}</div>
            <div class="info_block">
                <span>ПРОТИВ</span>
                <span class="loser" data-field="loser_name">{losers_name}</span>
                <div class="score">{scores_html}</div>
            </div>
        </div>
    </div>
    <script src="/static/js/winner.js"></script>
</body>
</html>'''

    def _empty_winner_html(self, court_name: str) -> str:
        """Пустая страница без победителя"""
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{court_name} - Winner</title>
    <link rel="stylesheet" href="/static/css/winner.css">
</head>
<body>
    <div class="winner">
        <div class="winner_container">
            <div class="no-winner">NO WINNER</div>
        </div>
    </div>
    <script src="/static/js/winner.js"></script>
</body>
</html>'''