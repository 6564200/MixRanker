#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML страниц матчей (VS, winner, intro)
ВНИМАНИЕ: Код скопирован из оригинального xml_generator.py
"""

from typing import Dict, List
import logging
from .html_base import HTMLBase

logger = logging.getLogger(__name__)


class MatchPagesHTMLGenerator(HTMLBase):
    """Генератор HTML страниц матчей - точная копия из xml_generator.py"""
    
    def generate_next_match_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует страницу HTML, заявляющей следующую игру на текущем корте"""
        court_name = court_data.get("court_name", "Court")
        next_participants = court_data.get("next_first_participant", [])
        if not next_participants or not id_url:
            html_content = f'''<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{court_name} - Next match</title>
                    <link rel="stylesheet" href="/static/css/next_match.css">
                    <script>
                        setInterval(function() {{
                            location.reload();
                        }}, 9000);
                    </script>
                </head>
                <body>
                    <div class="next-match">NO NEXT MATCH</div>
                </body>
                </html>'''
            return html_content

        team1_players = court_data.get("next_first_participant", [])
        team2_players = court_data.get("next_second_participant", [])
        id_url_dict = {d['id']: d for d in id_url}
        team1_players = [(p, id_url_dict[p.get('id')]) for p in team1_players if p.get('id')]
        team2_players = [(p, id_url_dict[p.get('id')]) for p in team2_players if p.get('id')]
        start_time = court_data.get("next_start_time", "")

        html_content = f'''<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{court_name} - Next match</title>
                    <link rel="stylesheet" href="/static/css/next_match.css">
                    <script>
                        setInterval(function() {{
                            location.reload();
                        }}, 9000);
                    </script>
                </head>
                <body>
                    <div class="next-match">
                        <div class="time">{start_time}</div>
                        <div class="block">
                            <div class="left_team">
                                <div class="left_participants">
                                    {'<br>'.join([p[0].get("fullName") for p in team1_players])}
                                </div>
                                <div class="left-images">
                                    {''.join(f'<img src="{p[1]["photo_url"]}" alt="{p[0].get("fullName")}">' for p in team1_players)}
                                </div>
                            </div>
                            <div class="right_team">
                                <div class="right_participants">
                                    {'<br>'.join([p[0].get("fullName") for p in team2_players])}
                                </div>
                                <div class="right-images">
                                    {''.join(f'<img src="{p[1]["photo_url"]} alt={p[0].get("fullName")}">' for p in team2_players)}
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>'''

        return html_content

    def generate_court_vs_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
            """
            Генерирует VS страницу (versus) с фотографиями игроков
                HTML строка
            """
            # Получаем данные текущего матча
            team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
            team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
            detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
            
            # Заголовок
            header_location = "ПАДЕЛ-АРЕНА РМК, ЕКАТЕРИНБУРГ"
            header_title = tournament_data.get("metadata", {}).get("name", "ТУРНИР") if tournament_data else "ТУРНИР"
            
            # Получаем счета по сетам и геймам (как в fullscreen)
            team1_scores = [0, 0, 0, 0]
            team2_scores = [0, 0, 0, 0]
            
            if detailed_result and len(detailed_result) > 0:
                for i in range(min(len(detailed_result), 3)):
                    team1_set_score = detailed_result[i].get("firstParticipantScore", 0)
                    team1_scores[i] = team1_set_score
                    team2_set_score = detailed_result[i].get("secondParticipantScore", 0)
                    team2_scores[i] = team2_set_score
            
            # Формируем блоки сетов (только ненулевые)
            sets_html = ""
            visible_sets = []
            
            for i in range(3):
                team1_score = team1_scores[i]
                team2_score = team2_scores[i]
                
                # Показываем сет только если счет не 0-0
                if team1_score != 0 or team2_score != 0:
                    visible_sets.append({
                        'number': i + 1,
                        'team1_score': team1_score,
                        'team2_score': team2_score
                    })
            
            # Генерируем HTML для видимых сетов
            for set_info in visible_sets:
                sets_html += f'''
                    <div class="set-block">
                        <div class="set-header">
                            <div class="set-header-text">СЕТ {set_info['number']}</div>
                        </div>
                        <div class="set-scores">
                            <div class="set-score">{set_info['team1_score']}</div>
                            <div class="score-divider"></div>
                            <div class="set-score">{set_info['team2_score']}</div>
                        </div>
                    </div>
                '''
            
            # Добавляем блок ГЕЙМЫ (зеленый, как ИТОГ в fullscreen)
            # Используем метод _get_game_score_display для получения текущих геймов
            team1_game = self._get_game_score_display(detailed_result, team1_scores[3], 'first')
            team2_game = self._get_game_score_display(detailed_result, team2_scores[3], 'second')
            

            sets_html += f'''
                <div class="set-block game-block">
                    <div class="set-header game-header">
                        <div class="set-header-text">ГЕЙМЫ</div>
                    </div>
                    <div class="set-scores">
                        <div class="set-score">{team1_game}</div>
                        <div class="score-divider"></div>
                        <div class="set-score">{team2_game}</div>
                    </div>
                </div>
            '''
            
            # Формируем фото команды 1 (левая сторона)
            team1_photos = []
            for player in team1_players[:2]:  # Максимум 2 игрока
                photo_url = player.get("photo_url")
                if photo_url:
                    team1_photos.append(f'<img src="{photo_url}" class="player-photo" alt="{player.get("fullName", "")}">')
                else:
                    team1_photos.append('<img src="/static/images/silhouette.png" class="player-photo silhouette" alt="Player">')
            
            # Формируем фото команды 2 (правая сторона)
            team2_photos = []
            for player in team2_players[:2]:  # Максимум 2 игрока
                photo_url = player.get("photo_url")
                if photo_url:
                    team2_photos.append(f'<img src="{photo_url}" class="player-photo" alt="{player.get("fullName", "")}">')
                else:
                    team2_photos.append('<img src="/static/images/silhouette.png" class="player-photo silhouette" alt="Player">')
            
            # Формируем имена для нижней планки
            team1_names = ""
            for player in team1_players[:2]:
                full_name = player.get("fullName", "")
                team1_names += f'<div class="player-name">{full_name}</div>'
            
            team2_names = ""
            for player in team2_players[:2]:
                full_name = player.get("fullName", "")
                team2_names += f'<div class="player-name">{full_name}</div>'
            
            # Генерируем HTML----------------------------------{header_location}---------------{header_title}
            html_content = f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VS - {header_title}</title>
        <link rel="stylesheet" href="/static/css/vs.css">

    </head>
    <body>
        <div class="vs-container">
            <!-- Header -->
            <div class="header-text">
                <div class="header-location"></div>
                <div class="header-title"></div>
            </div>
            
            <!-- Teams with photos -->
            <div class="teams-wrapper">
                <!-- Team 1 (left) -->
                <div class="team-container team-left">
                    {''.join(team1_photos)}
                </div>
                
                <!-- Team 2 (right) -->
                <div class="team-container team-right">
                    {''.join(team2_photos)}
                </div>
            </div>
            
            <!-- Score section -->
            <div class="score-section">
                {sets_html}
            </div>
            
            <!-- Bottom plashka with team names -->
            <div class="bottom-plashka">
                <div class="plashka-border"></div>
                <div class="plashka-content">
                    <div class="team-names team-left">
                        {team1_names}
                    </div>
                    <div class="team-names team-right">
                        {team2_names}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>'''
            
            return html_content

    def generate_vs_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует HTML VS-страницу текущего корта"""
        court_name = court_data.get("court_name", "Court")
        match_state = court_data.get("current_match_state", "free")

        current_participants = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        if not current_participants or not id_url:
            html_content = f'''<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{court_name} - Next match</title>
                    <link rel="stylesheet" href="/static/css/vs.css">
                    <script>
                        setInterval(function() {{
                            location.reload();
                        }}, 9000);
                    </script>
                </head>
                <body>
                    <div class="vs">NO CURRENT MATCH</div>
                </body>
                </html>'''
            return html_content


        team1_score = court_data.get("current_first_participant_score",
                                     court_data.get("first_participant_score", 0))
        team2_score = court_data.get("current_second_participant_score",
                                     court_data.get("second_participant_score", 0))
        detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))

        team1_scores = [0, 0, 0, team1_score]
        team2_scores = [0, 0, 0, team2_score]
        if detailed_result and len(detailed_result) > 0:
            for i in range(min(len(detailed_result), 3)):
                team1_set_score = detailed_result[i].get("firstParticipantScore", 0)
                team1_scores[i] = team1_set_score
                team2_set_score = detailed_result[i].get("secondParticipantScore", 0)
                team2_scores[i] = team2_set_score

        team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
        team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
        id_url_dict = {d['id']: d for d in id_url}
        team1_players = [(p, id_url_dict[p.get('id')]) for p in team1_players if p.get('id')]
        team2_players = [(p, id_url_dict[p.get('id')]) for p in team2_players if p.get('id')]

        html_content = f'''<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{court_name} - VS</title>
                <link rel="stylesheet" href="/static/css/vs.css">
                <script>
                    setInterval(function() {{
                        location.reload();
                    }}, 9000);
                </script>
            </head>
            <body>
                <div class="next-match">
                    <div class="scoreboard">
                        <table id="first_set">
                            <thead>
                                <tr>
                                    <th colspan="2">Сет 1</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{team1_scores[0]}</td>
                                    <td>{team2_scores[0]}</td>
                                </tr>
                            </tbody>
                        </table>
                        <table id="second_set">
                            <thead>
                                <tr>
                                    <th colspan="2">Сет 2</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{team1_scores[1]}</td>
                                    <td>{team2_scores[1]}</td>
                                </tr>
                            </tbody>
                        </table>
                        <table id="third_set">
                            <thead>
                                <tr>
                                    <th colspan="2">Сет 3</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{team1_scores[2]}</td>
                                    <td>{team2_scores[2]}</td>
                                </tr>
                            </tbody>
                        </table>
                        <table id="final">
                            <thead>
                                <tr>
                                    <th colspan="2">ГЕЙМ</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>{team1_scores[3]}</td>
                                    <td>{team2_scores[3]}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="block">
                        <div class="left_team">
                            <div class="left_participants">
                                {'<br>'.join([p[0].get("fullName") for p in team1_players])}
                            </div>
                            <div class="left-images">
                                {''.join(f'<img src="{p[1]["photo_url"]}" alt="{p[0].get("fullName")}">' for p in team1_players)}
                            </div>
                        </div>
                        <div class="right_team">
                            <div class="right_participants">
                                {'<br>'.join([p[0].get("fullName") for p in team2_players])}
                            </div>
                            <div class="right-images">
                                {''.join(f'<img src="{p[1]["photo_url"]} alt={p[0].get("fullName")}">' for p in team2_players)}
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>'''

        return html_content

    def generate_introduction_page_html(self, participant_info: Dict) -> str:
        full_name = f'{participant_info["firstName"]} {participant_info["lastName"]}'
        country = participant_info['country']
        rating = participant_info['rating']
        height = participant_info['height']
        position = participant_info['position']

        html_content = f'''<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{participant_info['id']} - Introduction</title>
                <link rel="stylesheet" href="/static/css/introduction.css">
                <script>
                    setInterval(function() {{
                        location.reload();
                    }}, 9000);
                </script>
            </head>
            <body>
                <div class="introduction">
                    <table>
                        <thead>
                            <tr>
                                <th colspan="2">{full_name}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="key">СТРАНА</td>
                                <td class="value">{country}</td>
                            </tr>
                            <tr>
                                <td class="key">РЕЙТИНГ FIP</td>
                                <td class="value">{rating}</td>
                            </tr>
                            <tr>
                                <td class="key">РОСТ</td>
                                <td class="value">{height}</td>
                            </tr>
                            <tr>
                                <td class="key">ИГРОВАЯ ПОЗИЦИЯ</td>
                                <td class="value">{position}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </body>
            </html>'''
        return html_content

    def generate_winner_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует HTML страницу победителей текущего корта"""
        court_name = court_data.get("court_name", "Court")
        match_state = court_data.get("current_match_state", "free")

        current_participants = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        if not match_state == 'finished' or not current_participants or not id_url:
            html_content = f'''<!DOCTYPE html>
                        <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>{court_name} - Winner</title>
                            <link rel="stylesheet" href="/static/css/winner.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 9000);
                            </script>
                        </head>
                        <body>
                            <div class="winner">NO WINNER</div>
                        </body>
                        </html>'''
            return html_content

        first_win = court_data.get("current_is_winner_first")
        if first_win:
            winners = court_data.get("current_first_participant") or court_data.get("first_participant", [])
            losers = court_data.get("current_second_participant") or court_data.get("second_participant", [])
        else:
            winners = court_data.get("current_second_participant") or court_data.get("second_participant", [])
            losers = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        id_url_dict = {d['id']: d for d in id_url}
        winners = [(p, id_url_dict[p.get('id')]) for p in winners if p.get('id')]
        losers_name = ' / '.join([l.get("initialLastName", l.get("lastName"))] for l in losers)

        scores = []
        detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
        if detailed_result and len(detailed_result) > 0:
            for result in detailed_result:
                scores.append(f'{result.get("firstParticipantScore")}/{result.get("secondParticipantScore")}')

        html_content = f'''<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{court_name} - Winner</title>
                <link rel="stylesheet" href="/static/css/winner.css">
                <script>
                    setInterval(function() {{
                        location.reload();
                    }}, 9000);
                </script>
            </head>
            <body>
                <div class="winner">
                    <div class="winner_container">
                        <span>ПОБЕДИТЕЛЬ</span>
                        <table>
                            {["".join(f'<tr><td>{winner[0].get("fullName")}</td></tr>') for winner in winners]}
                        </table>
                        <div class="image_container">
                            {[f'<img src="{winner[1]}">' for winner in winners]}
                        </div>
                        <div class="info_block>
                            <span>ПРОТИВ</span>
                            <span class="loser">{losers_name}</span>
                            {[f'<div class="set_score>{score}</div>' for score in scores]}
                        </div>
                    </div>
                </div>
            </body>
            </html>'''
        return html_content