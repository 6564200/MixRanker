#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор VS (versus) и Winner страниц
"""

from typing import Dict, List
from .html_base import HTMLBaseGenerator
import logging
from .country_utils import get_country_name_ru

logger = logging.getLogger(__name__)


class VSGenerator(HTMLBaseGenerator):
    """Генератор VS и Winner страниц"""

    def generate_court_vs_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует VS страницу с фотографиями игроков"""
        team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
        team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
        detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
        
        header_title = tournament_data.get("metadata", {}).get("name", "ТУРНИР") if tournament_data else "ТУРНИР"
        
        # Счета по сетам
        team1_scores = [0, 0, 0, 0]
        team2_scores = [0, 0, 0, 0]
        
        if detailed_result:
            for i in range(min(len(detailed_result), 3)):
                team1_scores[i] = detailed_result[i].get("firstParticipantScore", 0)
                team2_scores[i] = detailed_result[i].get("secondParticipantScore", 0)
        
        # Генерируем блоки сетов
        sets_html = ""
        for i in range(3):
            if team1_scores[i] != 0 or team2_scores[i] != 0:
                sets_html += f'''
                <div class="set-block">
                    <div class="set-header"><div class="set-header-text">СЕТ {i + 1}</div></div>
                    <div class="set-scores">
                        <div class="set-score">{team1_scores[i]}</div>
                        <div class="score-divider"></div>
                        <div class="set-score">{team2_scores[i]}</div>
                    </div>
                </div>'''
        
        # Блок геймов
        team1_game = self.get_game_score_display(detailed_result, team1_scores[3], 'first')
        team2_game = self.get_game_score_display(detailed_result, team2_scores[3], 'second')
        
        sets_html += f'''
            <div class="set-block game-block">
                <div class="set-header game-header"><div class="set-header-text">ГЕЙМЫ</div></div>
                <div class="set-scores">
                    <div class="set-score">{team1_game}</div>
                    <div class="score-divider"></div>
                    <div class="set-score">{team2_game}</div>
                </div>
            </div>'''
        
        # Фото команд
        team1_photos = self._generate_player_photos(team1_players[:2])
        team2_photos = self._generate_player_photos(team2_players[:2])
        
        # Имена
        team1_names = ''.join(f'<div class="player-name">{p.get("fullName", "")}</div>' for p in team1_players[:2])
        team2_names = ''.join(f'<div class="player-name">{p.get("fullName", "")}</div>' for p in team2_players[:2])
        
        return f'''{self.html_head(f"VS - {header_title}", "vs.css", 30000)}
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

    def generate_vs_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует HTML VS-страницу текущего корта с фото из id_url"""
        court_name = court_data.get("court_name", "Court")
        current_participants = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        
        if not current_participants or not id_url:
            return self.empty_page_html(f"{court_name} - VS", "NO CURRENT MATCH", "vs.css")
        
        detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
        team1_score = court_data.get("current_first_participant_score", court_data.get("first_participant_score", 0))
        team2_score = court_data.get("current_second_participant_score", court_data.get("second_participant_score", 0))
        
        team1_scores = [0, 0, 0, team1_score]
        team2_scores = [0, 0, 0, team2_score]
        if detailed_result:
            for i in range(min(len(detailed_result), 3)):
                team1_scores[i] = detailed_result[i].get("firstParticipantScore", 0)
                team2_scores[i] = detailed_result[i].get("secondParticipantScore", 0)
        
        team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
        team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
        id_url_dict = {d['id']: d for d in id_url}
        
        team1_players = [(p, id_url_dict.get(p.get('id'), {})) for p in team1_players if p.get('id')]
        team2_players = [(p, id_url_dict.get(p.get('id'), {})) for p in team2_players if p.get('id')]
        
        team1_names = '<br>'.join([p[0].get("fullName", "") for p in team1_players])
        team2_names = '<br>'.join([p[0].get("fullName", "") for p in team2_players])
        team1_images = ''.join(f'<img src="{p[1].get("photo_url", "")}" alt="{p[0].get("fullName", "")}">' for p in team1_players)
        team2_images = ''.join(f'<img src="{p[1].get("photo_url", "")}" alt="{p[0].get("fullName", "")}">' for p in team2_players)
        
        return f'''{self.html_head(f"{court_name} - VS", "vs.css", 100000)}
<body>
    <div class="vs">
        <div class="scoreboard">
            <table>
                <thead><tr><th>СЕТ1</th><th>СЕТ2</th><th>СЕТ3</th></tr></thead>
                <tbody>
                    <tr><td>{team1_scores[0]}</td><td>{team1_scores[1]}</td><td>{team1_scores[2]}</td></tr>
                    <tr><td>{team2_scores[0]}</td><td>{team2_scores[1]}</td><td>{team2_scores[2]}</td></tr>
                </tbody>
            </table>
            <table>
                <thead><tr><th colspan="2">СЕТЫ</th></tr></thead>
                <tbody><tr><td>{team1_scores[3]}</td><td>{team2_scores[3]}</td></tr></tbody>
            </table>
        </div>
        <div class="block">
            <div class="left_team">
                <div class="left_participants">{team1_names}</div>
                <div class="right_participants">{team2_names}</div>
            </div>
            <div class="teams-wrapper">
                <div class="team-container team-left">{team1_images}</div>
                <div class="team-container team-left">{team2_images}</div>
            </div>
        </div>
    </div>
</body>
</html>'''

    def generate_winner_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        court_name = court_data.get("court_name", "Court")
        event_state = court_data.get("event_state", "")
        class_name = court_data.get("class_name")
        
        if event_state != 'Finished' or not id_url:
            return self.empty_page_html(f"{court_name} - Winner", "NO WINNER", "winner.css")
        
        first_participant_score = court_data.get("current_first_participant_score", court_data.get("first_participant_score", 0))
        second_participant_score = court_data.get("current_second_participant_score", court_data.get("second_participant_score", 0))
        
        if first_participant_score > second_participant_score:
            winners = court_data.get("current_first_participant") or court_data.get("first_participant", [])
            losers = court_data.get("current_second_participant") or court_data.get("second_participant", [])
        else:
            winners = court_data.get("current_second_participant") or court_data.get("second_participant", [])
            losers = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        
        if not winners:
            return self.empty_page_html(f"{court_name} - Winner", "NO WINNER", "winner.css")
        
        id_url_dict = {d['id']: d for d in id_url}
        winners_with_photos = [(p, id_url_dict.get(p.get('id'), {})) for p in winners if p.get('id')]
        losers_name = ' / '.join([l.get("initialLastName", l.get("lastName", "")) for l in losers])
        
        scores = []
        detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
        if detailed_result:
            for result in detailed_result:
                scores.append(f'{result.get("firstParticipantScore")}/{result.get("secondParticipantScore")}')
        
        winners_table = []
        for w in winners_with_photos:
            country_code = w[0].get("countryCode", "").lower()
            if country_code == 'rin':
                country_code = 'ru'
            flag_url = f"/static/flags/4x3/{country_code}.svg"
            country_name = get_country_name_ru(w[0].get("countryCode", ""))
            
            winners_table.append(f'''<div>
                <img src="{flag_url}" class="flag-icon" alt="{country_code}">
                <div class="player-info">
                    <div class="win_name">{w[0].get("fullName", "")}</div>
                    <div class="country_name">{country_name}</div>
                </div>
            </div>''')
        
        winners_table_html = ''.join(winners_table)
        winners_images = []
        for w in winners_with_photos:
            photo_url = w[1].get("photo_url", "")
            if photo_url:
                winners_images.append(f'<img src="{photo_url}" alt="{w[0].get("fullName", "")}">')
            else:
                winners_images.append('<img src="/static/images/silhouette.png" class="silhouette" alt="Player">')
        winners_images_html = ''.join(winners_images)
        scores_html = ''.join(f'<div class="set_score">{score}</div>' for score in scores)
        
        return f'''{self.html_head(f"{court_name} - Winner", "winner.css", 100000)}
    <body>
        <div class="winner">
            <div class="winner_container">
                <div class="class_name">{class_name}</div>
                <div class="txt_winner">ПОБЕДИТЕЛЬ</div>
                <div class="winners_table">{winners_table_html}</div>
                <div class="image_container">{winners_images}</div>
                <div class="info_block">
                    <span>ПРОТИВ</span>
                    <span class="loser">{losers_name}</span>
                    <div class="score">{scores_html}</div>
                </div>
            </div>
        </div>
    </body>
    </html>'''

    def _generate_player_photos(self, players: List[Dict]) -> str:
        """Генерирует HTML для фото игроков"""
        photos = []
        for player in players:
            photo_url = player.get("photo_url")
            if photo_url:
                photos.append(f'<img src="{photo_url}" class="player-photo" alt="{player.get("fullName", "")}">')
            else:
                photos.append('<img src="/static/images/silhouette.png" class="player-photo silhouette" alt="Player">')
        return ''.join(photos)
