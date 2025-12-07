#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML страниц для vMix
Отделен от xml_generator.py для улучшения структуры кода
"""

from typing import Dict, List, Any, Optional
import logging
from markupsafe import escape
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """Генератор HTML страниц для vMix"""
    
    def __init__(self):
        self.auto_reload_interval = 30000  # миллисекунды

    def _get_game_score_display(self, detailed_result: List[Dict], set_score: int, team: str) -> str:
        """Возвращает счет гейма если есть, иначе счет сетов"""
        if detailed_result and len(detailed_result) > 0:
            last_set = detailed_result[-1]
            game_score = last_set.get("gameScore")
            if game_score:
                return game_score.get(team, str(set_score))
        return str(set_score)

    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует HTML страницу scoreboard для корта с правильной логикой состояний"""

        # Определяем состояние корта
        match_state = court_data.get("current_match_state", "free")
        
        
        # Проверяем наличие участников 
        current_participants = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        next_participants = court_data.get("next_first_participant", [])
        
        # Определяем что показывать
        if current_participants and len(current_participants) > 0:
            # Есть текущий матч - показываем его
            team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
            team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
            team1_score = court_data.get("current_first_participant_score", court_data.get("first_participant_score", 0))
            team2_score = court_data.get("current_second_participant_score", court_data.get("second_participant_score", 0))
            detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
            class_name = court_data.get("current_class_name", court_data.get("class_name", ""))
            show_current_match = True
            
            # Определяем тип отображения счета
            if match_state == "live":
                show_score = True
            elif match_state == "finished":
                show_score = True
            elif match_state in ["scheduled", "playing_no_score"]:
                show_score = False  # Показываем участников но без счета
            else:
                show_score = True  # По умолчанию показываем
            
        elif next_participants and len(next_participants) > 0:
            # Нет текущего матча, но есть следующий
            team1_players = court_data.get("next_first_participant", [])
            team2_players = court_data.get("next_second_participant", [])
            team1_score = 0
            team2_score = 0
            detailed_result = []
            class_name = court_data.get("next_class_name", "")
            show_current_match = True
            show_score = False  # Следующий матч всегда без счета
            
        else:
            # Корт полностью свободен
            team1_players = []
            team2_players = []
            team1_score = 0
            team2_score = 0
            detailed_result = []
            class_name = ""
            show_current_match = False
            show_score = False

        # Формируем названия команд
        team1_name = ""
        if team1_players:
            team1_initials = [p.get("initialLastName", "") for p in team1_players if p.get("initialLastName")]
            team1_name = " / ".join(team1_initials).upper()

        team2_name = ""
        if team2_players:
            team2_initials = [p.get("initialLastName", "") for p in team2_players if p.get("initialLastName")]
            team2_name = " / ".join(team2_initials).upper()

        # Название корта
        court_name = court_data.get("court_name", "Court")

        # Определяем CSS класс для состояния
        state_class = ""
        if match_state == "live":
            state_class = " live-match"
        elif match_state == "finished":
            state_class = " finished-match"
        elif match_state in ["scheduled", "playing_no_score"]:
            state_class = " next-match"

        # Вычисляем количество сетов для определения ширины
        if show_current_match and detailed_result and len(detailed_result) > 0:
            max_sets = max(len(detailed_result), 1)
        else:
            max_sets = 1  # Минимум 1 слот для сетов
        sets_width = max_sets * 34

        # Название турнира
        tournament_name = ""
        if tournament_data and tournament_data.get("metadata"):
            full_name = tournament_data["metadata"].get("name", "")
            tournament_name = full_name[:10] if full_name else ""

        html_content = f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{court_name} - Scoreboard</title>
        <link rel="stylesheet" href="/static/css/scoreboard.css?v=0.0.1">

        <script>
            setInterval(function() {{
                location.reload();
            }}, 3000);
        </script>
    </head>
    <body>
        <div class="scoreboard-container">
            <div class="scoreboard">
                <div class="cort">
                    <span class="text-cort">{court_name}</span>
                </div>'''
        
        if show_current_match:
            html_set_score_2 = ''
            html_set_score_1 = ''

             # Сеты для команды 1
            if detailed_result and len(detailed_result) > 0:
                for i in range(min(max_sets, len(detailed_result))):
                    set_score = detailed_result[i].get("firstParticipantScore", 0)
                    html_set_score_1 = f'<div class="set set1-{i}">{set_score}</div>'
                
                for i in range(len(detailed_result), max_sets):
                    html_set1 += '<div class="set_1">-</div>'
            else:
                # Для матчей без детального счета показываем пустые сеты
                for i in range(max_sets):
                    html_set_score_1 += '<div class="set set1-{i}">-</div>'
            
            # Сеты для команды 2
            if detailed_result and len(detailed_result) > 0:
                for i in range(min(max_sets, len(detailed_result))):
                    set_score = detailed_result[i].get("secondParticipantScore", 0)
                    html_set_score_2 += f'<div class="set set1-{i}">{set_score}</div>'
                
                for i in range(len(detailed_result), max_sets):
                    html_set2 += '<div class="set_2">-</div>'
            else:
                # Для матчей без детального счета показываем пустые сеты
                for i in range(max_sets):
                    html_set_score_2 += '<div class="set set2-{i}">-</div>'
            
            html_content += f'''

                
		  	
                <!-- Team 1 Row -->
                <div class="team-row">
                    <div class="bg-team">
                        <span class="team-name">{team1_name}</span>
                        {html_set_score_1 if show_score else "*"}
                        <div class="main-score-area bg-rad1">
                        
                        </div>
                    </div>
                </div>
                
                <div class="divider-bar"></div>
                <!-- Team 2 Row -->
                <div class="team-row">
                    <div class="bg-team">
                        <span class="team-name">{team2_name}</span>
                        {html_set_score_2 if show_score else "*"}
                        <div class="main-score-area bg-rad2">
                            <span class="score-text">{self._get_game_score_display(detailed_result, team1_score, 'first') if show_score else "-"}</span>
                        </div>
                    </div>
                </div>'''
            

        else:
            # Корт полностью свободен
            html_content += '''
            <div class="team-row">
                <div class="bg-team"></div>
                <div class="team2">NO ACTIVE MATCH</div>
                <div class="bg-score bg-rad2"></div>
            </div>'''
        
        html_content += '''
            </div>
    </body>
</html>'''
        
        return html_content

    def generate_court_fullscreen_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует полноразмерную HTML страницу scoreboard текущего корта"""
        # Определяем состояние корта
        match_state = court_data.get("current_match_state", "free")

        # Проверяем наличие участников
        current_participants = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        next_participants = court_data.get("next_first_participant", [])

        # Определяем что показывать
        if current_participants and len(current_participants) > 0:
            # Есть текущий матч - показываем его
            team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
            team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
            team1_score = court_data.get("current_first_participant_score",
                                         court_data.get("first_participant_score", 0))
            team2_score = court_data.get("current_second_participant_score",
                                         court_data.get("second_participant_score", 0))
            detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
            show_current_match = True

            # Определяем тип отображения счета
            if match_state == "live":
                show_score = True
            elif match_state == "finished":
                show_score = True
            elif match_state in ["scheduled", "playing_no_score"]:
                show_score = False  # Показываем участников, но без счета
            else:
                show_score = True  # По умолчанию показываем

        elif next_participants and len(next_participants) > 0:
            # Нет текущего матча, но есть следующий
            team1_players = court_data.get("next_first_participant", [])
            team2_players = court_data.get("next_second_participant", [])
            team1_score = 0
            team2_score = 0
            detailed_result = []
            show_current_match = True
            show_score = False  # Следующий матч всегда без счета

        else:
            # Корт полностью свободен
            team1_players = []
            team2_players = []
            team1_score = 0
            team2_score = 0
            detailed_result = []
            show_current_match = False
            show_score = False

        team1_scores = [0, 0, 0, team1_score]
        team2_scores = [0, 0, 0, team2_score]
        
        if detailed_result and len(detailed_result) > 0:

            for i in range(min(len(detailed_result), 3)):
                team1_set_score = detailed_result[i].get("firstParticipantScore", 0)
                team1_scores[i] = team1_set_score
                team2_set_score = detailed_result[i].get("secondParticipantScore", 0)
                team2_scores[i] = team2_set_score

        if team1_players:
            team1_players = [p.get("fullName", "") for p in team1_players if p.get("fullName")]

        if team2_players:
            team2_players = [p.get("fullName", "") for p in team2_players if p.get("fullName")]

        # Название корта
        court_name = court_data.get("court_name", "Court")

        if show_current_match:
            html_content = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Таблица результатов матча из Figma</title>


    <link rel="stylesheet" href="/static/css/fullscreen_scoreboard.css">
            <script>
            setInterval(function() {{
                location.reload();
            }}, 1000);
        </script>
</head>
<body>

    <!-- Обертка для горизонтального скролла на маленьких экранах -->
    <div class="table-container">
        <div class="bg_table">
            <div class="table-wrapper">

                <!-- Заголовок таблицы: COURT HEADER -->
                <div class="bg_head_tab">
                    <div class="text_set">СЕТ 1</div>
                    <div class="text_set">СЕТ 2</div>
                    <div class="text_set">СЕТ 3</div>
                    <div class="text_set_itog">ГЕЙМ</div>
                </div>

                <!-- Первая команда -->
                <div class="bg_team1">
                    <div class="command_name1">
                        <div class="player_name1">{team1_players[0]}</div>
                        <div class="player_name2">{team1_players[1]}</div>
                    </div>
                    <div class="set_play1">
                        <div class="text_set_score">{team1_scores[0] if show_score else ''}</div>
                        <div class="text_set_score">{team1_scores[1] if show_score else ''}</div>
                        <div class="text_set_score">{team1_scores[2] if show_score else ''}</div>
                        <div class="text_set_itog_score">{self._get_game_score_display(detailed_result, team1_scores[3], 'first') if show_score else ''}</div>
                    </div>
                </div>

                <!-- Разделительная линия -->
                <div class="bg_line"></div>

                <!-- Вторая команда -->
                <div class="bg_team2">
                    <div class="command_name2">
                        <div class="player_name1">{team2_players[0]}</div>
                        <div class="player_name2">{team2_players[1]}</div>
                    </div>
                    <div class="set_play2">
                        <div class="text_set_score">{team2_scores[0] if show_score else ''}</div>
                        <div class="text_set_score">{team2_scores[1] if show_score else ''}</div>
                        <div class="text_set_score">{team2_scores[2] if show_score else ''}</div>
                        <div class="text_set_itog_score">{self._get_game_score_display(detailed_result, team2_scores[3], 'second') if show_score else ''}</div>
                        
                        

                    </div>
                </div>
                <div class="bg_line"></div>
            </div>
        </div>
    </div>

</body>
</html>'''

        else:
            html_content = f'''<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{court_name} - Scoreboard</title>
                    <link rel="stylesheet" href="/static/css/fullscreen_scoreboard.css">
                    <script>
                        setInterval(function() {{
                            location.reload();
                        }}, 9000);
                    </script>
                </head>
                <body>
                    <div class="scoreboard">
                        <div class="team-row no-match">
                            <div class="team-name">NO ACTIVE MATCH</div>
                        </div>
                    </div>
                </body>
                </html>
'''

        return html_content

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



    def _check_bye_advancement(self, match_data: Dict) -> Optional[Dict]:
        """Проверяет есть ли в матче Bye и возвращает информацию о проходящей команде"""
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        challenger_team = self._get_team_name_from_players(
            challenger_data.get("FirstPlayer", {}),
            challenger_data.get("SecondPlayer", {})
        )
        
        challenged_team = self._get_team_name_from_players(
            challenged_data.get("FirstPlayer", {}),
            challenged_data.get("SecondPlayer", {})
        )
        
        # Если challenger это Bye, то проходит challenged
        if challenger_team.upper() == "BYE" or not challenger_team.strip():
            if challenged_team and challenged_team.upper() != "BYE":
                return {
                    "team_name": challenged_team,
                    "first_player": challenged_data.get("FirstPlayer", {}).get("Name", ""),
                    "second_player": challenged_data.get("SecondPlayer", {}).get("Name", "")
                }
        
        # Если challenged это Bye, то проходит challenger
        elif challenged_team.upper() == "BYE" or not challenged_team.strip():
            if challenger_team and challenger_team.upper() != "BYE":
                return {
                    "team_name": challenger_team,
                    "first_player": challenger_data.get("FirstPlayer", {}).get("Name", ""),
                    "second_player": challenger_data.get("SecondPlayer", {}).get("Name", "")
                }
        
        return None

    def _get_winner_player_names(self, match_data: Dict, winner_id: int) -> tuple:
        """Возвращает имена игроков победившей команды"""
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        if challenger_data.get("EventParticipantId") == winner_id:
            first_player_name = challenger_data.get("FirstPlayer", {}).get("Name", "")
            second_player_name = challenger_data.get("SecondPlayer", {}).get("Name", "")
        elif challenged_data.get("EventParticipantId") == winner_id:
            first_player_name = challenged_data.get("FirstPlayer", {}).get("Name", "")
            second_player_name = challenged_data.get("SecondPlayer", {}).get("Name", "")
        else:
            first_player_name = ""
            second_player_name = ""
        
        return first_player_name, second_player_name

    def _create_short_name(self, full_name: str) -> str:
        """Создает сокращенное имя: первая буква + точка + фамилия"""
        if not full_name or "/" not in full_name:
            return full_name
        
        parts = full_name.split("/")
        short_parts = []
        
        for part in parts:
            part = part.strip()
            if " " in part:
                name_parts = part.split(" ")
                first_name = name_parts[0].strip()
                last_name = " ".join(name_parts[1:]).strip()
                if first_name and last_name:
                    short_name = f"{last_name.replace(' ', '')}"
                    short_parts.append(short_name)
                else:
                    short_parts.append(part)
            else:
                short_parts.append(part)
        
        return "/".join(short_parts)

    def _find_winner_team_name(self, match_data: Dict, winner_id: int) -> str:

        """Находит название команды-победителя по ID"""
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        if challenger_data.get("EventParticipantId") == winner_id:
            return self._get_team_name_from_players(
                challenger_data.get("FirstPlayer", {}),
                challenger_data.get("SecondPlayer", {})
            )
        elif challenged_data.get("EventParticipantId") == winner_id:
            return self._get_team_name_from_players(
                challenged_data.get("FirstPlayer", {}),
                challenged_data.get("SecondPlayer", {})
            )
        
        return ""

    def _find_game(self, match_data: Dict, winner_id: int) -> str:
                        #{ 'class': "match-result " + status_class, 'lost-team': short_team_lost, 'winner-team' : short_team, 'sets-info' : sets_summary, 'match-score': score_summary, 'Id': winner_id}
        """Находит название команды-победителя по ID"""
     
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        match_status = self._get_match_status(match_data)
        ger = {}
        ged = {}
        win = {}
        lost = {}

        if challenger_data.get("EventParticipantId") != winner_id:
            lost = self._get_team_name_from_players(  challenger_data.get("FirstPlayer", {}),   challenger_data.get("SecondPlayer", {}))
            ger = {'status': 'lost', 'team': self._create_short_name(lost) }
            
        elif challenged_data.get("EventParticipantId") != winner_id:
            lost = self._get_team_name_from_players(  challenged_data.get("FirstPlayer", {}),   challenged_data.get("SecondPlayer", {}))
            ged = {'status': 'lost', 'team': self._create_short_name(lost)}
            
        if challenger_data.get("EventParticipantId") == winner_id:
            win = self._get_team_name_from_players(  challenger_data.get("FirstPlayer", {}),   challenger_data.get("SecondPlayer", {}))
            ger = {'status': 'winer', 'team': self._create_short_name(win)}
            
        elif challenged_data.get("EventParticipantId") == winner_id:
            win = self._get_team_name_from_players(  challenged_data.get("FirstPlayer", {}),   challenged_data.get("SecondPlayer", {}))
            ged = {'status': 'winer', 'team': self._create_short_name(win)}
        
        
        return {'ger': ger, 'ged': ged, 'status_class': match_status, 'lost': lost, 'win':win}

    def _get_team_name_from_players(self, first_player: Dict, second_player: Dict) -> str:
        """Формирует название команды из имен игроков"""
        names = []
        if first_player and first_player.get("Name"):
            names.append(first_player["Name"])
        if second_player and second_player.get("Name"):
            names.append(second_player["Name"])
        return "/".join(names)

    def _format_score_summary(self, score_data: Dict) -> str:
        """Форматирует итоговый счет"""
        if not score_data:
            return ""
        
        first_score = score_data.get("FirstParticipantScore", 0)
        second_score = score_data.get("SecondParticipantScore", 0)
        return f"{first_score}-{second_score}"

    def _format_sets_summary(self, score_data: Dict) -> str:
        """Форматирует детальный счет по сетам"""
        if not score_data or not score_data.get("DetailedScoring"):
            return ""
        
        sets_summary = []
        for i, set_data in enumerate(score_data["DetailedScoring"]):
            first_score = set_data.get("FirstParticipantScore", 0)
            second_score = set_data.get("SecondParticipantScore", 0)
            sets_summary.append(f"({first_score}-{second_score})")
        
        return " ".join(sets_summary)

    def generate_court_score_xml(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует упрощенный XML для счета на конкретном корте с поддержкой следующего матча"""
        root = ET.Element("templateData")
        
        if tournament_data:
            metadata = tournament_data.get("metadata", {})
        
        # Базовая информация о корте
        ET.SubElement(root, "courtName").text = court_data.get("court_name", "Корт")
        ET.SubElement(root, "courtStatus").text = court_data.get("event_state", "")
        
        current_class =  court_data.get("class_name", "") or court_data.get("current_class_name")

        if current_class:
            
            ET.SubElement(root, "currentClassEvent").text = current_class[:current_class.rfind(',')] + 'l'
            ET.SubElement(root, "currentClassName").text = '' #current_class[current_class.rfind(',')+1:]
                
            ET.SubElement(root, "currentMatchState").text = court_data.get("current_match_state", "")
            
            # Дополнительная информация о текущем матче
            if court_data.get("current_duration_seconds"):
                ET.SubElement(root, "currentDurationSeconds").text = str(court_data["current_duration_seconds"])
            if court_data.get("current_is_winner_first") is not None:
                ET.SubElement(root, "currentWinnerFirst").text = str(court_data["current_is_winner_first"])
        
        team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
        if team1_players:
            for i, player in enumerate(team1_players, 1):
                ET.SubElement(root, f"player{i}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{i}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{i}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{i}FullName").text = player.get("fullName", "")
                ET.SubElement(root, f"player{i}LastNameShort").text = player.get("lastNameShort", "")
                ET.SubElement(root, f"player{i}InitialLastName").text = player.get("initialLastName", "")
        else:
            for i in range(1, 5):
                ET.SubElement(root, f"player{i}FirstName").text = ''
                ET.SubElement(root, f"player{i}MiddleName").text = ''
                ET.SubElement(root, f"player{i}LastName").text = ''
                ET.SubElement(root, f"player{i}FullName").text = ''
                ET.SubElement(root, f"player{i}LastNameShort").text = ''
                ET.SubElement(root, f"player{i}InitialLastName").text = ''
        
        team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
        if team2_players:
            for i, player in enumerate(team2_players, 1):
                player_num = i + 2  # Команда 2 начинается с player3, player4
                ET.SubElement(root, f"player{player_num}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{player_num}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{player_num}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{player_num}FullName").text = player.get("fullName", "")
                ET.SubElement(root, f"player{player_num}LastNameShort").text = player.get("lastNameShort", "")
                ET.SubElement(root, f"player{player_num}InitialLastName").text = player.get("initialLastName", "")                
        
        # Счет текущего матча
        ET.SubElement(root, "team1Score").text = str(court_data.get("current_first_participant_score", court_data.get("first_participant_score", 0)))
        ET.SubElement(root, "team2Score").text = str(court_data.get("current_second_participant_score", court_data.get("second_participant_score", 0)))
        
        # Детальный счет по сетам
        detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
        for i, set_data in enumerate(detailed_result, 1):
            ET.SubElement(root, f"set{i}Team1").text = str(set_data.get("firstParticipantScore", 0))
            ET.SubElement(root, f"set{i}Team2").text = str(set_data.get("secondParticipantScore", 0))
            if set_data.get("loserTiebreak"):
                ET.SubElement(root, f"set{i}LoserTiebreak").text = str(set_data["loserTiebreak"])
        
        # Форматированные названия команд с сокращениями 
        if team1_players:
            team1_shorts = [p.get("lastNameShort", "") for p in team1_players if p.get("lastNameShort")]
            ET.SubElement(root, "team1NamesShort").text = ("/".join(team1_shorts)).replace(" ", "")
            
            team1_initials = [p.get("initialLastName", "") for p in team1_players if p.get("initialLastName")]
            ET.SubElement(root, "team1NamesInitial").text = ("/".join(team1_initials)).replace(" ", "")
            
            team1_full = [p.get("fullName", "") for p in team1_players if p.get("fullName")]
            ET.SubElement(root, "team1NamesFull").text = "/".join(team1_full)
        else:
            ET.SubElement(root, "team1NamesShort").text = ''
            ET.SubElement(root, "team1NamesInitial").text = ''
            ET.SubElement(root, "team1NamesFull").text = ''
        
        if team2_players:
            team2_shorts = [p.get("lastNameShort", "") for p in team2_players if p.get("lastNameShort")]
            ET.SubElement(root, "team2NamesShort").text = ("/".join(team2_shorts)).replace(" ", "")
            
            team2_initials = [p.get("initialLastName", "") for p in team2_players if p.get("initialLastName")]
            ET.SubElement(root, "team2NamesInitial").text = ("/".join(team2_initials)).replace(" ", "")
            
            team2_full = [p.get("fullName", "") for p in team2_players if p.get("fullName")]
            ET.SubElement(root, "team2NamesFull").text = "/".join(team2_full)
        else:
            ET.SubElement(root, "team2NamesShort").text = ''
            ET.SubElement(root, "team2NamesInitial").text = ''
            ET.SubElement(root, "team2NamesFull").text = ''
        
        if court_data.get("next_class_name"):
            ET.SubElement(root, "nextClassName").text = court_data["next_class_name"]
            ET.SubElement(root, "nextStartTime").text = court_data.get("next_start_time", "")
            ET.SubElement(root, "nextScheduledTime").text = court_data.get("next_scheduled_time", "")
            ET.SubElement(root, "nextMatchState").text = court_data.get("next_match_state", "")
            
            # Участники следующего матча - команда 1
            next_team1 = court_data.get("next_first_participant", [])
            if next_team1:
                for i, player in enumerate(next_team1, 1):
                    ET.SubElement(root, f"nextPlayer{i}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{i}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{i}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{i}FullName").text = player.get("fullName", "")
                    ET.SubElement(root, f"nextPlayer{i}LastNameShort").text = player.get("lastNameShort", "")
                    ET.SubElement(root, f"nextPlayer{i}InitialLastName").text = player.get("initialLastName", "")
            
            # Участники следующего матча - команда 2
            next_team2 = court_data.get("next_second_participant", [])
            if next_team2:
                for i, player in enumerate(next_team2, 1):
                    player_num = i + 2  # Команда 2 начинается с nextPlayer3, nextPlayer4
                    ET.SubElement(root, f"nextPlayer{player_num}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}FullName").text = player.get("fullName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}LastNameShort").text = player.get("lastNameShort", "")
                    ET.SubElement(root, f"nextPlayer{player_num}InitialLastName").text = player.get("initialLastName", "")
            
            # Форматированные названия следующих команд
            if next_team1:
                next_team1_shorts = [p.get("lastNameShort", "") for p in next_team1 if p.get("lastNameShort")]
                ET.SubElement(root, "nextTeam1NamesShort").text = ("/".join(next_team1_shorts)).replace(" ", "")
                
                next_team1_initials = [p.get("initialLastName", "") for p in next_team1 if p.get("initialLastName")]
                ET.SubElement(root, "nextTeam1NamesInitial").text = ("/".join(next_team1_initials)).replace(" ", "")
                
                next_team1_full = [p.get("fullName", "") for p in next_team1 if p.get("fullName")]
                ET.SubElement(root, "nextTeam1NamesFull").text = "/".join(next_team1_full)
            
            if next_team2:
                next_team2_shorts = [p.get("lastNameShort", "") for p in next_team2 if p.get("lastNameShort")]
                ET.SubElement(root, "nextTeam2NamesShort").text = ("/".join(next_team2_shorts)).replace(" ", "")
                
                next_team2_initials = [p.get("initialLastName", "") for p in next_team2 if p.get("initialLastName")]
                ET.SubElement(root, "nextTeam2NamesInitial").text = ("/".join(next_team2_initials)).replace(" ", "")
                
                next_team2_full = [p.get("fullName", "") for p in next_team2 if p.get("fullName")]
                ET.SubElement(root, "nextTeam2NamesFull").text = "/".join(next_team2_full)
        else:
            ET.SubElement(root, "nextClassName").text = ''
            ET.SubElement(root, "nextStartTime").text = ''
            ET.SubElement(root, "nextScheduledTime").text = ''
            ET.SubElement(root, "nextMatchState").text = ''
            
            for i in range(1, 5):
                    ET.SubElement(root, f"nextPlayer{i}FirstName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}MiddleName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}LastName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}FullName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}LastNameShort").text = ''
                    ET.SubElement(root, f"nextPlayer{i}InitialLastName").text = ''
            
            ET.SubElement(root, "nextTeam1NamesShort").text = ''
            ET.SubElement(root, "nextTeam1NamesInitial").text = ''
            ET.SubElement(root, "nextTeam1NamesFull").text = ''
            ET.SubElement(root, "nextTeam2NamesShort").text = ''
            ET.SubElement(root, "nextTeam2NamesInitial").text = ''
            ET.SubElement(root, "nextTeam2NamesFull").text = ''
        
        # Время обновления
        ET.SubElement(root, "updated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return self._prettify_xml(root)

    def generate_schedule_xml(self, tournament_data: Dict) -> str:
        """Генерирует XML для расписания матчей турнира"""
        root = ET.Element("templateData")
        
        # Метаинформация о турнире
        metadata = tournament_data.get("metadata", {})
        tournament = ET.SubElement(root, "tournament")
        ET.SubElement(tournament, "id").text = str(tournament_data.get("tournament_id", ""))
        ET.SubElement(tournament, "name").text = metadata.get("name", "Неизвестный турнир")
        ET.SubElement(tournament, "sport").text = self._get_sport_name(metadata.get("sport", 5))
        ET.SubElement(tournament, "country").text = self._get_country_name(metadata.get("country"))
        if metadata.get("featureImage"):
            ET.SubElement(tournament, "banner").text = metadata["featureImage"]
        
        # Даты турнира
        dates = tournament_data.get("dates", [])
        if dates:
            dates_elem = ET.SubElement(root, "dates")
            ET.SubElement(dates_elem, "count").text = str(len(dates))
            for i, date in enumerate(dates, 1):
                ET.SubElement(dates_elem, f"date_{i}").text = str(date)
        
        # Расписание на основе данных court_usage
        schedule = ET.SubElement(root, "schedule")
        court_usage = tournament_data.get("court_usage")
        
        # Отладочная информация
        logger.info(f"generate_schedule_xml: court_usage type = {type(court_usage)}")
        if court_usage:
            logger.info(f"generate_schedule_xml: court_usage length = {len(court_usage) if isinstance(court_usage, (list, dict)) else 'not list/dict'}")
        
        if court_usage and isinstance(court_usage, list):
            # Обрабатываем массив матчей из запроса №6
            logger.info(f"Обрабатываем {len(court_usage)} матчей из court_usage")
            
            # Группируем матчи по кортам
            courts_matches = {}
            for match in court_usage:
                if not isinstance(match, dict):
                    continue
                    
                court_id = str(match.get("CourtId", ""))
                if court_id not in courts_matches:
                    courts_matches[court_id] = []
                courts_matches[court_id].append(match)
            
            logger.info(f"Найдено матчей по кортам: {[(k, len(v)) for k, v in courts_matches.items()]}")

            # Генерируем XML для каждого корта
            for court_id, matches in courts_matches.items():
                court_elem = ET.SubElement(schedule, "court")
                ET.SubElement(court_elem, "id").text = court_id
                ET.SubElement(court_elem, "name").text = f"Корт {court_id}"

                # Сортируем матчи по времени
                sorted_matches = sorted(matches, key=lambda x: x.get("MatchDate", ""))

                matches_elem = ET.SubElement(court_elem, "matches")
                ET.SubElement(matches_elem, "count").text = str(len(sorted_matches))

                for i, match in enumerate(sorted_matches, 1):
                    match_elem = ET.SubElement(matches_elem, f"match_{i}")

                    # Основная информация о матче
                    ET.SubElement(match_elem, "id").text = str(match.get("TournamentMatchId", ""))
                    ET.SubElement(match_elem, "challenge_id").text = str(match.get("ChallengeId", ""))
                    ET.SubElement(match_elem, "match_date").text = match.get("MatchDate", "")
                    ET.SubElement(match_elem, "duration").text = str(match.get("Duration", 30))
                    ET.SubElement(match_elem, "pool_name").text = match.get("PoolName", "")
                    ET.SubElement(match_elem, "round").text = str(match.get("Round", 1))
                    ET.SubElement(match_elem, "match_order").text = str(match.get("MatchOrder", 0))

                    # Участники
                    ET.SubElement(match_elem, "challenger_name").text = match.get("ChallengerName", "")
                    ET.SubElement(match_elem, "challenged_name").text = match.get("ChallengedName", "")
                    ET.SubElement(match_elem, "challenger_individual").text = match.get("ChallengerIndividualName", "")
                    ET.SubElement(match_elem, "challenged_individual").text = match.get("ChallengedIndividualName", "")

                    # Результаты
                    ET.SubElement(match_elem, "challenger_result").text = str(match.get("ChallengerResult", ""))
                    ET.SubElement(match_elem, "challenged_result").text = str(match.get("ChallengedResult", ""))

                    # Статус матча
                    ET.SubElement(match_elem, "is_team_match").text = str(match.get("IsPartOfTeamMatch", False))
                    ET.SubElement(match_elem, "is_final").text = str(match.get("IsFinal", False))
                    ET.SubElement(match_elem, "is_semifinal").text = str(match.get("IsSemiFinal", False))
                    ET.SubElement(match_elem, "is_quarterfinal").text = str(match.get("IsQuarterFinal", False))
                    ET.SubElement(match_elem, "consolation").text = str(match.get("Consolation", 0))

                    # Время начала 
                    match_date = match.get("MatchDate", "")
                    if match_date:
                        try:
                            from datetime import datetime as dt
                            dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                            ET.SubElement(match_elem, "start_time").text = dt_obj.strftime("%H:%M")
                            ET.SubElement(match_elem, "date_formatted").text = dt_obj.strftime("%d.%m.%Y")
                        except:
                            ET.SubElement(match_elem, "start_time").text = ""
                            ET.SubElement(match_elem, "date_formatted").text = ""

        else:
            logger.warning(f"court_usage отсутствует или имеет неверный тип: {type(court_usage)}")
            # Fallback - используем базовую информацию о кортах
            courts = tournament_data.get("courts", [])
            if courts:
                for court in courts:
                    if not isinstance(court, dict):
                        continue

                    court_elem = ET.SubElement(schedule, "court")
                    court_id = court.get("Item1", "")
                    court_name = court.get("Item2", f"Корт {court_id}")
                    
                    ET.SubElement(court_elem, "id").text = str(court_id)
                    ET.SubElement(court_elem, "name").text = court_name

                    # Заглушка для матчей
                    matches_elem = ET.SubElement(court_elem, "matches")
                    ET.SubElement(matches_elem, "count").text = "0"
                    ET.SubElement(matches_elem, "note").text = "Данные расписания не загружены"

        # Дополнительная информация
        info_elem = ET.SubElement(root, "info")
        total_matches = len(court_usage) if court_usage and isinstance(court_usage, list) else 0
        ET.SubElement(info_elem, "total_matches").text = str(total_matches)
        ET.SubElement(info_elem, "total_courts").text = str(len(tournament_data.get("courts", [])))

        # Время генерации
        ET.SubElement(root, "generated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(root, "type").text = "schedule"
        
        return self._prettify_xml(root)

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей с новым дизайном из Figma"""
        # Метаинформация о турнире
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        # Получаем расписание
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        # Получаем информацию о кортах из tournaments.courts
        courts_info = tournament_data.get("courts", [])
        court_names_map = {}
        for court in courts_info:
            if isinstance(court, dict) and court.get("Item1") and court.get("Item2"):
                court_id = str(court["Item1"])
                court_name = court["Item2"]
                court_names_map[court_id] = court_name

        from datetime import datetime as dt
        if not target_date:
            tz_yekat = ZoneInfo("Asia/Yekaterinburg")
            now_yekat = datetime.now(tz=tz_yekat)
            target_date = dt.now().strftime("%d.%m.%Y")
            #target_date = dt(year=2025, month=10, day=25).strftime("%d.%m.%Y") #для тестов

        # Группируем матчи по кортам и фильтруем по дате
        courts_matches = {}
        all_matches = []

        for match in court_usage:
            if not isinstance(match, dict):
                continue

            match_date = match.get("MatchDate", "")
            if match_date:
                try:
                    dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                    match_date_formatted = dt_obj.strftime("%d.%m.%Y")

                    # Фильтруем только матчи на нужную дату
                    if match_date_formatted != target_date:
                        continue

                    court_id = str(match.get("CourtId", ""))
                    court_name = court_names_map.get(court_id, f"Корт {court_id}")

                    # Добавляем время начала для сортировки
                    match["start_time"] = dt_obj.strftime("%H:%M")
                    match["date_formatted"] = match_date_formatted
                    match["court_name"] = court_name
                    match["datetime_obj"] = dt_obj

                    all_matches.append(match)

                    if court_name not in courts_matches:
                        courts_matches[court_name] = []
                    courts_matches[court_name].append(match)

                except Exception as e:
                    continue

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        # Сортируем матчи в каждом корте по времени и присваиваем номера
        for court_name in courts_matches:
            courts_matches[court_name].sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(courts_matches[court_name], 1):
                match["episode_number"] = i

        # Фильтруем матчи - оставляем последние 3 завершённых + все активные и будущие
        filtered_courts_matches = {}
        for court_name, matches in courts_matches.items():
            finished = []
            active_and_future = []

            for match in matches:
                status = self._get_match_status(match)
                if status == "finished":
                    finished.append(match)
                else:
                    active_and_future.append(match)

            # Берём последние 3 завершённых + все активные и будущие
            filtered_matches = finished[-3:] + active_and_future
            filtered_courts_matches[court_name] = filtered_matches

        courts_matches = filtered_courts_matches

        # Собираем все оставшиеся матчи для временных слотов
        all_remaining_matches = []
        for matches in courts_matches.values():
            all_remaining_matches.extend(matches)

        # Создаем уникальные временные слоты только для оставшихся матчей
        time_slots = sorted(list(set([m["start_time"] for m in all_remaining_matches])))

        # Генерируем HTML
        html_content = f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Расписание матчей - {tournament_name}</title>
        <link rel="stylesheet" href="/static/css/schedule_new.css">
        <script>
            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="schedule-container">
            <div class="main-grid">
                <div class="time-scale">'''

        # Временные слоты
        for time_slot in time_slots:
            html_content += f'''
                    <div class="time-slot">{time_slot}</div>'''

        html_content += '''
                </div>
                
                <div class="courts-container">
                    <div class="courts-header">'''

        # Заголовки кортов
        for court_name in sorted(courts_matches.keys()):
            html_content += f'''
                        <div class="court-header">
                            <h3>{court_name}</h3>
                        </div>'''

        html_content += '''
                    </div>
                    
                    <div class="matches-grid">'''

        # Столбцы кортов с матчами
        for court_name in sorted(courts_matches.keys()):
            matches = courts_matches[court_name]

            html_content += '''
                        <div class="court-column">'''

            for match in matches:
                match_status = self._get_match_status(match)
                status_class = self._get_status_class(match_status)

                challenger_name = match.get("ChallengerName", "TBD")
                challenged_name = match.get("ChallengedName", "TBD")
                episode_number = match.get("episode_number", 1)

                # Результаты матча
                challenger_result = match.get("ChallengerResult", "0")
                challenged_result = match.get("ChallengedResult", "0")

                if not challenger_result:
                    challenger_result = "0"
                if not challenged_result:
                    challenged_result = "0"

                # Проверка на Won W.O.
                challenger_wo = ""
                challenged_wo = ""

                if challenger_result == "Won W.O.":
                    challenger_wo = "Won W.O."
                    challenger_result = ""
                if challenged_result == "Won W.O.":
                    challenged_wo = "Won W.O."
                    challenged_result = ""

                html_content += f'''
                            <div class="match-item {status_class}">
                                <div class="match-content">
                                    <div class="match-number">{episode_number}</div>
                                    <div class="match-teams-wrapper">
                                        <div class="match-team">
                                            <div class="match-team-name">{challenger_name}</div>
                                            {"<div class='match-team-wo'>Won W.O.</div>" if challenger_wo else ""}
                                            {"<div class='match-team-score'>" + challenger_result + "</div>" if challenger_result else ""}
                                        </div>
                                        <div class="match-team">
                                            <div class="match-team-name">{challenged_name}</div>
                                            {"<div class='match-team-wo'>Won W.O.</div>" if challenged_wo else ""}
                                            {"<div class='match-team-score'>" + challenged_result + "</div>" if challenged_result else ""}
                                        </div>
                                    </div>
                                </div>
                            </div>'''

            html_content += '''
                        </div>'''

        html_content += '''
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>'''

        return html_content


    def generate_schedule_html_new(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей с новым дизайном 3.12.2025"""
        # Метаинформация о турнире
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        # Получаем расписание
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        # Получаем информацию о кортах из tournaments.courts
        courts_info = tournament_data.get("courts", [])
        court_names_map = {}
        for court in courts_info:
            if isinstance(court, dict) and court.get("Item1") and court.get("Item2"):
                court_id = str(court["Item1"])
                court_name = court["Item2"]
                court_names_map[court_id] = court_name

        from datetime import datetime as dt
        if not target_date:
            target_date = dt.now().strftime("%d.%m.%Y")
            #target_date = dt(year=2025, month=10, day=25).strftime("%d.%m.%Y") # для тестов

        # Группируем матчи по кортам и фильтруем по дате
        courts_matches = {}
        all_matches = []

        for match in court_usage:

            if not isinstance(match, dict):
                continue

            match_date = match.get("MatchDate", "")
            if match_date:
                try:
                    dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                    match_date_formatted = dt_obj.strftime("%d.%m.%Y")

                    # Фильтруем только матчи на нужную дату
                    if match_date_formatted != target_date:
                        continue

                    court_id = str(match.get("CourtId", ""))
                    court_name = court_names_map.get(court_id, f"Корт {court_id}")

                    # Добавляем время начала для сортировки
                    match["start_time"] = dt_obj.strftime("%H:%M")
                    match["date_formatted"] = match_date_formatted
                    match["court_name"] = court_name
                    match["datetime_obj"] = dt_obj

                    all_matches.append(match)

                    if court_name not in courts_matches:
                        courts_matches[court_name] = []
                    courts_matches[court_name].append(match)

                except Exception as e:
                    continue

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        # Сортируем матчи в каждом корте по времени и присваиваем номера
        for court_name in courts_matches:
            courts_matches[court_name].sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(courts_matches[court_name], 1):
                match["episode_number"] = i

        # Создаем уникальные временные слоты
        time_slots = sorted(list(set([m["start_time"] for m in all_matches])))

        # Генерируем HTML
        html_content = f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Расписание матчей - {tournament_name}</title>
        <link rel="stylesheet" href="/static/css/schedule_new.css">
        <script>
            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="schedule-container">
            <div class="main-grid">
                <div class="time-scale">'''

        # Временные слоты
        for time_slot in time_slots:
            html_content += f'''
                    <div class="time-slot">{time_slot}</div>'''

        html_content += '''
                </div>
                
                <div class="courts-container">
                    <div class="courts-header">'''

        # Заголовки кортов
        for court_name in sorted(courts_matches.keys()):
            html_content += f'''
                        <div class="court-header">
                            <h3>{court_name}</h3>
                        </div>'''

        html_content += '''
                    </div>
                    
                    <div class="matches-grid">'''

        # Столбцы кортов с матчами
        for court_name in sorted(courts_matches.keys()):
            matches = courts_matches[court_name]

            html_content += '''
                        <div class="court-column">'''

            for match in matches:
                match_status = self._get_match_status(match)
                status_class = self._get_status_class(match_status)

                challenger_name = match.get("ChallengerName", "TBD")
                challenged_name = match.get("ChallengedName", "TBD")
                episode_number = match.get("episode_number", 1)

                # Результаты матча
                challenger_result = match.get("ChallengerResult", "0")
                challenged_result = match.get("ChallengedResult", "0")

                if not challenger_result:
                    challenger_result = "0"
                if not challenged_result:
                    challenged_result = "0"

                # Проверка на Won W.O.
                challenger_wo = ""
                challenged_wo = ""

                if challenger_result == "Won W.O.":
                    challenger_wo = "W.O."
                    challenger_result = ""
                if challenged_result == "Won W.O.":
                    challenged_wo = "W.O."
                    challenged_result = ""


                html_content += f'''
                        <div class="match-item {status_class}">
                            <div class="match-content">
                                <div class="match-number">{episode_number}</div>
                                <div class="match-teams-wrapper">
                                    <div class="match-team">
                                        <div class="match-team-name">{challenger_name}</div>
                                        {"<div class='match-team-wo'>Won W.O.</div>" if challenger_wo else ""}
                                        {"<div class='match-team-score'>" + challenger_result + "</div>" if challenger_result else ""}
                                    </div>
                                    <div class="match-team">
                                        <div class="match-team-name">{challenged_name}</div>
                                        {"<div class='match-team-wo'>Won W.O.</div>" if challenged_wo else ""}
                                        {"<div class='match-team-score'>" + challenged_result + "</div>" if challenged_result else ""}
                                    </div>
                                </div>
                            </div>
                        </div>'''

            html_content += '''
                        </div>'''

        html_content += '''
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>'''

        return html_content



    def generate_schedule_html_addreality(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей с новым дизайном 3.12.2025"""
        # Метаинформация о турнире
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        # Получаем расписание
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        # Получаем информацию о кортах из tournaments.courts
        courts_info = tournament_data.get("courts", [])
        court_names_map = {}
        for court in courts_info:
            if isinstance(court, dict) and court.get("Item1") and court.get("Item2"):
                court_id = str(court["Item1"])
                court_name = court["Item2"]
                court_names_map[court_id] = court_name

        from datetime import datetime as dt
        if not target_date:
            target_date = dt.now().strftime("%d.%m.%Y")
            #target_date = dt(year=2025, month=10, day=25).strftime("%d.%m.%Y") # для тестов

        # Группируем матчи по кортам и фильтруем по дате
        courts_matches = {}
        all_matches = []

        for match in court_usage:

            if not isinstance(match, dict):
                continue

            match_date = match.get("MatchDate", "")
            if match_date:
                try:
                    dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                    match_date_formatted = dt_obj.strftime("%d.%m.%Y")

                    # Фильтруем только матчи на нужную дату
                    if match_date_formatted != target_date:
                        continue

                    court_id = str(match.get("CourtId", ""))
                    court_name = court_names_map.get(court_id, f"Корт {court_id}")

                    # Добавляем время начала для сортировки
                    match["start_time"] = dt_obj.strftime("%H:%M")
                    match["date_formatted"] = match_date_formatted
                    match["court_name"] = court_name
                    match["datetime_obj"] = dt_obj

                    all_matches.append(match)

                    if court_name not in courts_matches:
                        courts_matches[court_name] = []
                    courts_matches[court_name].append(match)

                except Exception as e:
                    continue

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        # Сортируем матчи в каждом корте по времени и присваиваем номера
        for court_name in courts_matches:
            courts_matches[court_name].sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(courts_matches[court_name], 1):
                match["episode_number"] = i

        # Создаем уникальные временные слоты
        time_slots = sorted(list(set([m["start_time"] for m in all_matches])))

        # Генерируем HTML
        html_content = f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Расписание матчей -Addreality говно {tournament_name}</title>
        <link rel="stylesheet" href="/static/css/schedule_addreality.css">
        <script>
            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="schedule-container">
            <div class="main-grid">
                <div class="time-scale">'''

        # Временные слоты
        for time_slot in time_slots:
            html_content += f'''
                    <div class="time-slot">{time_slot}</div>'''

        html_content += '''
                </div>
                
                <div class="courts-container">
                    <div class="courts-header">'''

        # Заголовки кортов
        for court_name in sorted(courts_matches.keys()):
            html_content += f'''
                        <div class="court-header">
                            <h3>{court_name}</h3>
                        </div>'''

        html_content += '''
                    </div>
                    
                    <div class="matches-grid">'''

        # Столбцы кортов с матчами
        for court_name in sorted(courts_matches.keys()):
            matches = courts_matches[court_name]

            html_content += '''
                        <div class="court-column">'''

            for match in matches:
                match_status = self._get_match_status(match)
                status_class = self._get_status_class(match_status)

                challenger_name = match.get("ChallengerName", "TBD")
                challenged_name = match.get("ChallengedName", "TBD")
                episode_number = match.get("episode_number", 1)

                # Результаты матча
                challenger_result = match.get("ChallengerResult", "0")
                challenged_result = match.get("ChallengedResult", "0")

                if not challenger_result:
                    challenger_result = "0"
                if not challenged_result:
                    challenged_result = "0"

                # Проверка на Won W.O.
                challenger_wo = ""
                challenged_wo = ""

                if challenger_result == "Won W.O.":
                    challenger_wo = "W.O."
                    challenger_result = ""
                if challenged_result == "Won W.O.":
                    challenged_wo = "W.O."
                    challenged_result = ""


                html_content += f'''
                        <div class="match-item {status_class}">
                            <div class="match-content">
                                <div class="match-number">{episode_number}</div>
                                <div class="match-teams-wrapper">
                                    <div class="match-team">
                                        <div class="match-team-name">{challenger_name}</div>
                                        {"<div class='match-team-wo'>Won W.O.</div>" if challenger_wo else ""}
                                        {"<div class='match-team-score'>" + challenger_result + "</div>" if challenger_result else ""}
                                    </div>
                                    <div class="match-team">
                                        <div class="match-team-name">{challenged_name}</div>
                                        {"<div class='match-team-wo'>Won W.O.</div>" if challenged_wo else ""}
                                        {"<div class='match-team-score'>" + challenged_result + "</div>" if challenged_result else ""}
                                    </div>
                                </div>
                            </div>
                        </div>'''

            html_content += '''
                        </div>'''

        html_content += '''
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>'''

        return html_content

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Генерирует пустую HTML страницу расписания"""
        return f'''<!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Расписание матчей - {tournament_name}</title>
                    <link rel="stylesheet" href="/static/css/schedule.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 30000);
                            </script>
                </head>
                <body>
                    <div class="schedule-container">
                        <div class="header">
                            <h1 class="tournament-title">{tournament_name}</h1>
                        </div>
                        <div class="empty-message">
                            <p>{message}</p>
                        </div>
                    </div>
                </body>
                </html>'''

    def _generate_time_slots(self, matches: list) -> list:
        """Генерирует временные слоты на основе матчей"""
        if not matches:
            return ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
        
        from datetime import datetime as dt, timedelta
        # Находим минимальное и максимальное время
        times = []
        for match in matches:
            if match.get("datetime_obj"):
                times.append(match["datetime_obj"])

        logger.info(f"time -------- {times}")
        if not times:
            return ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
        
        min_time = min(times)
        max_time = max(times)
        
        # Вычисляем общий диапазон в часах
        total_hours = (max_time - min_time).total_seconds() / 3600
        
        # Определяем оптимальный интервал в зависимости от диапазона
        if total_hours <= 2:
            interval_minutes = 15  # для коротких турниров
        elif total_hours <= 4:
            interval_minutes = 20  # для средних турниров
        elif total_hours <= 8:
            interval_minutes = 30  # для длинных турниров
        else:
            interval_minutes = 60  # для очень длинных турниров
        
        # Создаем слоты с динамическим интервалом
        time_slots = []
        # Начинаем за 30 минут до первого матча
        start_time = min_time - timedelta(minutes=30)
        start_time = start_time.replace(minute=(start_time.minute // interval_minutes) * interval_minutes, second=0, microsecond=0)
        
        # Заканчиваем через 30 минут после последнего матча
        end_time = max_time + timedelta(minutes=30)
        
        current_time = start_time
        while current_time <= end_time:
            time_slots.append(current_time.strftime("%H:%M"))
            current_time += timedelta(minutes=interval_minutes)
        return time_slots
    
    def _calculate_time_position(self, match: dict, time_slots: list) -> int:
        """Вычисляет позицию матча по времени в пикселях с улучшенным расчетом"""
        if not match.get("datetime_obj") or not time_slots:
            return 0
        
        from datetime import datetime as dt
        
        match_time = match["datetime_obj"]
        
        try:
            base_time_str = time_slots[0]
            base_time = dt.strptime(f"{match_time.date()} {base_time_str}", "%Y-%m-%d %H:%M")
        except:
            return 0
        
        # Вычисляем разность в минутах
        time_diff_minutes = (match_time - base_time).total_seconds() / 60
        
        slot_height = 80
        
        # Определяем интервал между слотами на основе их количества
        if len(time_slots) <= 1:
            minutes_per_slot = 30
        else:
            # Вычисляем интервал между слотами из временной шкалы
            try:
                first_time = dt.strptime(f"{match_time.date()} {time_slots[0]}", "%Y-%m-%d %H:%M")
                second_time = dt.strptime(f"{match_time.date()} {time_slots[1]}", "%Y-%m-%d %H:%M")
                minutes_per_slot = (second_time - first_time).total_seconds() / 60
            except:
                minutes_per_slot = 30
        # Пиксели на минуту
        pixels_per_minute = slot_height / minutes_per_slot
        position = int(time_diff_minutes * pixels_per_minute)
        return max(0, position)
    
    def _get_match_status(self, match: Dict) -> str:
        """Определяет статус матча"""
        challenger_result = match.get("ChallengerResult", "")
        challenged_result = match.get("ChallengedResult", "")
        
        if challenger_result and challenged_result:
            return "finished"
        # Проверяем время матча для определения активности
        from datetime import datetime as dt
        try:
            match_date = match.get("MatchDate", "")
            if match_date:
                dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                now = dt.now()
                duration = match.get("Duration", 30)  # минуты
                
                if dt_obj <= now <= dt_obj.replace(minute=dt_obj.minute + duration):
                    return "active"
                elif dt_obj > now:
                    return "future"
                else:
                    return "finished"
        except:
            pass
        return "future"
    
    def _get_status_class(self, status: str) -> str:
        """Возвращает CSS класс для статуса"""
        return {
            "finished": "match-finished",
            "active": "match-active", 
            "future": "match-future"
        }.get(status, "match-future")
    
    def _get_group_class(self, group_name: str) -> str:
        """Возвращает CSS класс для группы на основе хеша названия"""
        if not group_name:
            return "match-group-1"
        # Создаем хеш от названия группы для стабильного распределения цветов
        hash_value = sum(ord(c) for c in group_name.upper())
        color_number = (hash_value % 7) + 1
        
        return f"match-group-{color_number}"

    def generate_and_save_schedule_html(self, tournament_data: Dict, target_date: str = None) -> Dict:
        """Генерирует и сохраняет HTML файл расписания"""
        
        # Генерация HTML
        html_content = self.generator.generate_schedule_html(tournament_data, target_date)
        
        # Определяем дату для имени файла
        from datetime import datetime as dt
        if not target_date:
            target_date = dt.now().strftime("%d.%m.%Y")
        
        # Сохранение файла
        safe_date = target_date.replace(".", "_")
        filename = f"{tournament_data.get('tournament_id', 'unknown')}_schedule_{safe_date}.html"
        filepath = f"{self.output_dir}/{filename}"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            logger.error(f"Ошибка сохранения файла {filepath}: {e}")
            raise
        
        # Информация о файле
        import os
        if os.path.exists(filepath):
            file_stats = os.stat(filepath)
        else:
            logger.error(f"Файл не найден после создания: {filepath}")
            raise FileNotFoundError(f"Файл не создался: {filepath}")
        
        file_info = {
            "id": f"schedule_html_{safe_date}",
            "name": f"Расписание матчей HTML - {target_date}",
            "filename": filename,
            "url": f"/html/{filename}",
            "size": self._format_file_size(file_stats.st_size),
            "created": datetime.now().isoformat(),
            "type": "html_schedule",
            "target_date": target_date
        }

        return file_info

    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для турнирной сетки на выбывание (elimination)"""
        # Получаем данные elimination
        import re
        
        class_id = xml_type_info.get("class_id")
        draw_index = xml_type_info.get("draw_index", 0)
        
        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        elimination_data = class_data.get("elimination", [])
        
        if draw_index >= len(elimination_data):
            return self._generate_empty_elimination_html("Нет данных турнирной сетки")
        
        elim_data = elimination_data[draw_index]
        if not elim_data or "Elimination" not in elim_data:
            return self._generate_empty_elimination_html("Неверные данные турнирной сетки")
        
        bracket_data = elim_data["Elimination"]
        # Название турнира и класса
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Турнир")
        class_name = xml_type_info.get("class_name", "Категория")
        stage_name = xml_type_info.get("stage_name", "Плей-офф")
        
        # Анализируем структуру турнира для определения количества раундов
        rounds_data = self._analyze_elimination_structure(bracket_data)

        html_content = f'''<!DOCTYPE html>
                            <html lang="ru">
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>{class_name} - {stage_name} TEST </title>
                                <link rel="stylesheet" href="/static/css/elimination.css">
                                                        <script>
                                                            setInterval(function() {{
                                                                location.reload();
                                                            }}, 30000);
                                                        </script>
                            </head>
                            <body>
                                <div class="elimination-container">
                                    <div class="round-column">
                                    '''
        
        # Генерируем колонки для каждого раунда
        for round_index, round_info in enumerate(rounds_data):
                                  
            if round_index == 0:
                first_round_content = self._generate_first_round(bracket_data)
            else:
                # Победители
                html_content += f'''    '''
                
                if (len(rounds_data)-1) == round_index: 
                    # Финальный раунд - используем универсальную функцию
                    full_results = self._generate_match_pairs_from_api(round_index, round_info['matches'])
                    
                    html_content += f'''<div class="bracket-grid">'''
                    
                    if (len(rounds_data)-1) == 1: html_content += f'''<div class="places">{stage_name}</div> '''
                    
                    for match in full_results:
                        html_content += f'''
                            <div class="container">
                                <div class="row row-top">
                                    <div class="names">
                                        <span class="name-main {match['secondary1']}">{match['team_1_name']}</span>
                                    </div>
                                    <div class="score">
                                        <span class="set-score">{match['sets1']}</span>
                                    </div>
                                    <div class="rank rank-top">
                                        <span class="rank-number">{match['score'].split('-')[0]}</span>
                                    </div>
                                </div>
                                <div class="row row-bottom">
                                    <div class="names">
                                        <span class="name-main {match['secondary2']}">{match['team_2_name']}</span>
                                    </div>
                                    <div class="score">
                                        <span class="set-score">{match['sets2']}</span>
                                    </div>
                                    <div class="rank rank-bottom">
                                        <span class="rank-number">{match['score'].split('-')[1]}</span>
                                    </div>
                                </div>
                            </div>'''
                    html_content += '</div>'

                else: # Последующие раунды Используем универсальную функцию для формирования пар
                    full_results = self._generate_match_pairs_from_api(round_index, round_info['matches'])

                    html_content += f'''<div class="bracket-grid">'''
                    if round_index == 1: html_content += f'''<div class="places">{stage_name}</div>'''
                    
                    for match in full_results:
                            html_content += f'''
    <div class="container">
        <div class="row row-top">
            <div class="names">
                <span class="name-main {match['secondary1']}">{match['team_1_name']}</span>
            </div>
            <div class="score">
                <span class="set-score">{match['sets1']}</span>
            </div>
            <div class="rank rank-top">
                <span class="rank-number">{match['score'].split('-')[0]}</span>
            </div>
        </div>
        <div class="row row-bottom">
            <div class="names">
                <span class="name-main {match['secondary2']}">{match['team_2_name']}</span>
            </div>
            <div class="score">
                <span class="set-score">{match['sets2']}</span>
            </div>
            <div class="rank rank-bottom">
                <span class="rank-number">{match['score'].split('-')[1]}</span>
            </div>
        </div>
    </div>'''                
                    html_content += f'''</div>'''
        html_content += '''</div> '''
        
        html_content += '''
        </div>
    </div>
</body>
</html>'''
        
        return html_content

    def _analyze_elimination_structure(self, bracket_data: Dict) -> List[Dict]:
        """Анализирует структуру elimination для определения раундов"""
        rounds_data = []
        
        # Первый раунд - участники
        first_round_participants = bracket_data.get("FirstRoundParticipantCells", [])
        if first_round_participants:
            rounds_data.append({
                'title': 'Команды',
                'matches': first_round_participants,
                'type': 'participants'
            })
        
        # Анализируем матчи по раундам
        if bracket_data.get("DrawData"):
            matches_by_round = {}
            
            for round_matches in bracket_data["DrawData"]:
                for match_data in round_matches:
                    if match_data:
                        round_number = match_data.get("Round", 1)
                        if round_number not in matches_by_round:
                            matches_by_round[round_number] = []
                        matches_by_round[round_number].append(match_data)
            
            # Определяем названия раундов
            sorted_rounds = sorted(matches_by_round.keys())
            round_names = self._generate_round_names(len(sorted_rounds))
            
            for i, round_number in enumerate(sorted_rounds):
                rounds_data.append({
                    'title': round_names[i] if i < len(round_names) else f'Раунд {round_number}',
                    'matches': matches_by_round[round_number],
                    'type': 'matches',
                    'round_number': round_number
                })
        
        return rounds_data

    def _generate_round_names(self, num_rounds: int) -> List[str]:
        """Генерирует названия раундов в зависимости от их количества"""
        if num_rounds == 1:
            return ['Финал']
        elif num_rounds == 2:
            return ['Полуфинал', 'Финал']
        elif num_rounds == 3:
            return ['Четвертьфинал', 'Полуфинал', 'Финал']
        elif num_rounds == 4:
            return ['1/8 финала', 'Четвертьфинал', 'Полуфинал', 'Финал']
        elif num_rounds == 5:
            return ['1/16 финала', '1/8 финала', 'Четвертьфинал', 'Полуфинал', 'Финал']
        else:
            # Для большего количества раундов
            names = []
            for i in range(num_rounds - 3):
                names.append(f'Раунд {i + 1}')
            names.extend(['Четвертьфинал', 'Полуфинал', 'Финал'])
            return names

    def _generate_first_round(self, bracket_data: Dict):
        """для первого раунда (участники)"""

        participants = bracket_data.get("FirstRoundParticipantCells", [])
        first_round = {}
        for i, participant_data in enumerate(participants, 1):
            # Формируем название команды
            team_names = []
            if participant_data.get("FirstPlayer", {}).get("Name"):
                team_names.append(participant_data["FirstPlayer"]["Name"])
            if participant_data.get("SecondPlayer", {}).get("Name"):
                team_names.append(participant_data["SecondPlayer"]["Name"])
            
            team_name = "/".join(team_names) if team_names else "TBD"
            short_name = self._create_short_name(team_name) if team_name != "TBD" else "TBD"
            Id = participant_data.get("EventParticipantId")
            
            # Проверяем, является ли это Bye
            is_bye = team_name.upper() == "BYE" or not team_names
            css_class = "bye-team" if is_bye else "match"
            
            first_round[i] = { 'class': css_class, 'team-name': short_name, 'sets-info': '', 'match-score': '', 'Id': Id}

        return first_round

    def _generate_match_pairs_from_api(self, round_index: int, matches: List[Dict]) -> List[Dict]:
        """Универсальная функция для формирования пар матчей из API данных"""
        match_pairs = []
        
        for match_data in matches:
            match_view_model = match_data.get("MatchViewModel", {})
            is_played = match_view_model.get("IsPlayed", False)
            has_score = match_view_model.get("HasScore", False)
            cancellation_status = match_data.get("CancellationStatus", "")
            winner_id = match_data.get("WinnerParticipantId")
            
            # Получаем данные участников
            challenger_data = match_data.get("ChallengerParticipant", {})
            challenged_data = match_data.get("ChallengedParticipant", {})
            
            # Формируем имена команд
            team1_name = self._get_team_name_from_players(
                challenger_data.get("FirstPlayer", {}),
                challenger_data.get("SecondPlayer", {})
            )
            team2_name = self._get_team_name_from_players(
                challenged_data.get("FirstPlayer", {}),
                challenged_data.get("SecondPlayer", {})
            )
            
            team1_id = challenger_data.get("EventParticipantId")
            team2_id = challenged_data.get("EventParticipantId")
            
            # Базовая структура матча
            match_info = {
                'team_1_name': self._create_short_name(team1_name) if team1_name else 'TBD',
                'team_2_name': self._create_short_name(team2_name) if team2_name else 'TBD',
                'team_1_id': team1_id,
                'team_2_id': team2_id,
                'status': 'Запланирован',
                'score': '0-0',
                'sets1': '',
                'sets2': '',
                'secondary1': '',
                'secondary2': ''
            }
            
            if is_played and has_score:
                # Сыгранный матч с результатом
                match_info['status'] = 'Сыгран'
                
                # Определяем победителя и проигравшего
                if winner_id == team1_id:
                    match_info['secondary1'] = ''
                    match_info['secondary2'] = 'lost'
                elif winner_id == team2_id:
                    match_info['secondary1'] = 'lost'
                    match_info['secondary2'] = ''
                
                # Получаем счет
                score_data = match_view_model.get("Score", {})
                match_info['score'] = self._format_score_summary(score_data)
                sets_summary = self._format_sets_summary(score_data)
                
                # Парсим сеты
                import re
                sets1 = [int(x) for x in re.findall(r'\((\d+)-', sets_summary)] #-----------------------------
                sets2 = [int(x) for x in re.findall(r'-(\d+)\)', sets_summary)]
                match_info['sets1'] = ' '.join(map(str, sets1))
                match_info['sets2'] = ' '.join(map(str, sets2))
                
            elif is_played and not has_score:
                # Walkover
                match_info['status'] = 'Walkover'
                if winner_id == team1_id:
                    match_info['secondary2'] = 'lost'
                    match_info['score'] = '1-0'
                    match_info['sets2'] = 'WO'
                elif winner_id == team2_id:
                    match_info['secondary1'] = 'lost'
                    match_info['score'] = '0-1'
                    match_info['sets1'] = 'WO'
                    
            elif not is_played and not has_score:
                # Проверяем на Bye
                bye_winner = self._check_bye_advancement(match_data)
                if bye_winner:
                    match_info['status'] = 'Bye'
                    if bye_winner.get("participant_id") == team1_id:
                        match_info['team_2_name'] = 'BYE'
                        match_info['secondary1'] = 'lost'
                    elif bye_winner.get("participant_id") == team2_id:
                        match_info['team_1_name'] = 'BYE'
                        match_info['secondary2'] = 'lost'
            
            match_pairs.append(match_info)
        
        return match_pairs

    def _generate_empty_elimination_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу elimination"""
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Турнирная сетка</title>
    <link rel="stylesheet" href="/static/css/elimination.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 30000);
                            </script>
</head>
<body>
    <div class="elimination-container">
        <div class="empty-message">
            <p>{message}</p>
        </div>
    </div>
</body>
</html>'''



    def generate_round_robin_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для групповой турнирной таблицы (round robin)"""
        
        # Получаем данные round robin
        class_id = xml_type_info.get("class_id")
        draw_index = xml_type_info.get("draw_index", 0)
        
        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        round_robin_data = class_data.get("round_robin", [])
        
        if draw_index >= len(round_robin_data):
            return self._generate_empty_round_robin_html("Нет данных групповой таблицы")
        
        rr_data = round_robin_data[draw_index]
        if not rr_data or "RoundRobin" not in rr_data:
            return self._generate_empty_round_robin_html("Неверные данные групповой таблицы")
        
        group_data = rr_data["RoundRobin"]
        
        # Название турнира и класса
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Турнир")
        class_name = (xml_type_info.get("class_name", "Категория")).upper()
        group_name = (xml_type_info.get("group_name", "Группа")).upper()
        
        # Получаем участников и матчи
        participants = self._extract_rr_participants(group_data)
        
        matches_matrix = self._extract_rr_matches_matrix(group_data, len(participants))
        
        standings = self._extract_rr_standings(group_data)
        
        html_content = f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{class_name} - {group_name}</title>
        <link rel="stylesheet" href="/static/css/round_robin.css">
        <script>
            window.onload = function() {{
                window.scrollTo(0, 0); // Эта функция сработает после каждой загрузки
            }};

            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="round-robin-container">            
                <div class="round-robin-table">
                    <div class="table-title">
                        <div class="table-header">
                            <div class="cell-num"></div>
                            <div class="cell-gpp">{class_name[class_name.find(",")+1:]  } - {group_name} </div>
                        </div>
                        '''
        
        for i in range(1, len(participants) + 1):
            html_content += f'''
                                <div class="team-number-header">
                                        <div class="team-number">{i}</div>
                                </div>
                            '''
        
        html_content += '''
                            <div class="points-header">
                                <div class="points"> ОЧКИ</div>
                            </div>
                            <div class="points-header">
                                <div class="points"> МЕСТО</div>
                            </div>
                        </div>
                    '''
        
        # Строки таблицы
        for i, participant in enumerate(participants):
            place = self._get_participant_place(participant, standings)
            points = self._get_participant_points(participant, standings)
            upper_short_name = (participant.get("short_name", " ")).upper()
            html_content += f'''
                        <div class="team-row">
                            <div class="team-number-cell">
                                <div class="team-num">{i + 1}</div>
                                <div class="team-name-cell">{upper_short_name} </div>
                            </div>
                            '''
            
            # Ячейки результатов матчей
            for j in range(len(participants)):
                if i == j:
                    # Диагональная ячейка
                    html_content += f'''<div class="diagonal-cell"></div>'''
                else:
                    match_result = matches_matrix.get(f"{i}_{j}", {})
                    result_class = self._get_match_result_class(match_result)
                    
                    if match_result.get("is_bye"):
                        html_content += '<div class="match-cell-bye-cell">●</div>'
                    elif match_result.get("has_result"):
                        score = match_result.get("score", "-")
                        sets = match_result.get("sets", "")
                        html_content += f'''
                            <div class="match-cell">
                                <div class="match-score">{score}</div>
                                <div class="match-sets">{sets}</div>
                            </div>'''
                    else:
                        html_content += '<div class="match-cell-empty-cell"></div>'
            
            html_content += f'''
                            <div class="points-cell">
                                <div class="points-z">{points}</div>
                            </div>
                            <div class="place-cell">
                                <div class="place-z">{place}</div>
                            </div>
                        </div>
                            '''
        
        html_content += '''
                    </div>
                </div>

        </div>
    </body>
    </html>'''

        return html_content

    def _extract_rr_participants(self, group_data: Dict) -> List[Dict]:
        """Извлекает участников из групповых данных"""
        participants = []
        pool_data = group_data.get("Pool", [])
        
        for row_index, row in enumerate(pool_data):
            if not isinstance(row, list):
                continue
                
            for cell_index, cell in enumerate(row):
                if not isinstance(cell, dict):
                    continue
                    
                if cell.get("CellType") == "ParticipantCell" and cell.get("ParticipantCell"):
                    participant_cell = cell["ParticipantCell"]
                    
                    if participant_cell.get("Players") and isinstance(participant_cell["Players"], list):
                        team_names = []
                        player_ids = []
                        for player in participant_cell["Players"]:
                            if isinstance(player, dict) and player.get("Name"):
                                team_names.append(player["Name"])
                                if player.get("Id"):
                                    player_ids.append(str(player["Id"]))

                        if team_names:
                            full_name = "/".join(team_names)
                            short_name = self._create_short_name(full_name) if full_name != "Bye" else "Bye"
                            
                            participants.append({
                                "index": participant_cell.get("Index", len(participants)),
                                "participant_id": participant_cell.get("ParticipantId"),  # Добавляем ParticipantId
                                "full_name": full_name,
                                "short_name": short_name,
                                "is_bye": full_name.upper() == "BYE",
                                "player_ids": player_ids  # Массив ID игроков
                            })

        # Берем только первую половину
        if len(participants) > 0:
            half_count = len(participants) // 2
            if half_count > 0:
                participants = participants[:half_count]
        
        return participants

    def _extract_rr_matches_matrix(self, group_data: Dict, num_participants: int) -> Dict:
        """Извлекает матчи в формате матрицы"""
        matches_matrix = {}
        pool_data = group_data.get("Pool", [])
        
        for row_index, row in enumerate(pool_data):
            if not isinstance(row, list):
                continue
    
            for cell_index, cell in enumerate(row):
                if not isinstance(cell, dict):
                    continue
                    
                if cell.get("CellType") == "MatchCell" and cell.get("MatchCell"):
                    match_cell = cell["MatchCell"]
                    match_results = match_cell.get("MatchResults", {})
                    
                    if row_index != cell_index:  # Не диагональные элементы
                        match_key = f"{row_index-1}_{cell_index-1}"
                        
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
                            
                            # Форматируем сеты
                            detailed_scoring = score_data.get("DetailedScoring", [])
                            if detailed_scoring:
                                sets_parts = []
                                for set_data in detailed_scoring:
                                    set_first = set_data.get("FirstParticipantScore", 0)
                                    set_second = set_data.get("SecondParticipantScore", 0)
                                    sets_parts.append(f"{set_first}-{set_second}")
                                match_info["sets"] = " ".join(sets_parts)
                        else:
                            cancellation_status = match_results.get('CancellationStatus') or '' # вернет пустую если None
                            if 'Won' in cancellation_status:
                                match_info["score"] = 'Won'
                            elif 'Lost' in cancellation_status:
                                match_info["score"] = 'Lost'
                        matches_matrix[match_key] = match_info
        
        return matches_matrix

    def _extract_rr_standings(self, group_data: Dict) -> List[Dict]:
        """Извлекает турнирную таблицу"""
        standings_data = group_data.get("Standings", [])
        standings = []
        fake_id_counter = 1000
        for standing in standings_data:
            if isinstance(standing, dict):
                # Собираем ID игроков из standings
                
                player_ids = []
                # Обработка первого игрока
                player1 = standing.get('DoublesPlayer1Model')
                if isinstance(player1, dict) and player1.get('Id'):
                    player_ids.append(str(player1['Id']))
                else:
                    player_ids.append(str(fake_id_counter))
                    fake_id_counter += 1

                # Обработка второго игрока
                player2 = standing.get('DoublesPlayer2Model')
                if isinstance(player2, dict) and player2.get('Id'):
                    player_ids.append(str(player2['Id']))
                else:
                    player_ids.append(str(fake_id_counter))
                    fake_id_counter += 1
                    
                
                standings.append({
                    "participant_id": str(standing.get("ParticipantId", "")),
                    "standing": standing.get("Standing", 0),
                    "wins": standing.get("Wins", 0),
                    "match_points": standing.get("MatchPoints", 0),
                    "player_ids": player_ids  # Массив ID игроков
                })
        
        return standings

    def _get_participant_place(self, participant: Dict, standings: List[Dict]) -> int:
        """Получает место участника по сопоставлению ParticipantId или player_ids"""
        
        # Сначала пробуем сопоставить по ParticipantId
        participant_id = participant.get("participant_id")
        if participant_id:
            for standing in standings:
                if str(standing.get("participant_id", "")) == str(participant_id):
                    return standing.get("standing", 0)
        
        # Если не найдено, пробуем сопоставить по player_ids
        participant_player_ids = set(participant.get("player_ids", []))
        if participant_player_ids:
            for standing in standings:
                standing_player_ids = set(standing.get("player_ids", []))
                # Проверяем пересечение множеств ID игроков
                if participant_player_ids & standing_player_ids:  # Если есть общие элементы
                    return standing.get("standing", 0)
        
        # Fallback - по index 
        participant_index = participant.get("index", 0)
        for standing in standings:
            if int(standing.get("participant_id", -1)) == participant_index:
                return standing.get("standing", 0)
        
        return 0

    def _get_participant_points(self, participant: Dict, standings: List[Dict]) -> int:
        """Получает очки участника по сопоставлению ParticipantId или player_ids"""
        
        # Сначала пробуем сопоставить по ParticipantId
        participant_id = participant.get("participant_id")
        if participant_id:
            for standing in standings:
                if str(standing.get("participant_id", "")) == str(participant_id):
                    return standing.get("match_points", 0)  # Используем match_points вместо wins
        
        # Если не найдено, пробуем сопоставить по player_ids
        participant_player_ids = set(participant.get("player_ids", []))
        if participant_player_ids:
            for standing in standings:
                standing_player_ids = set(standing.get("player_ids", []))
                # Проверяем пересечение множеств ID игроков
                if participant_player_ids & standing_player_ids:  # Если есть общие элементы
                    return standing.get("match_points", 0)
        
        # Fallback - по index 
        participant_index = participant.get("index", 0)
        for standing in standings:
            if int(standing.get("participant_id", -1)) == participant_index:
                return standing.get("match_points", 0)
        
        return 0

    def _get_match_result_class(self, match_result: Dict) -> str:
        """Возвращает CSS класс для результата матча"""
        if match_result.get("is_bye"):
            return "bye"
        elif match_result.get("has_result"):
            return "played"
        else:
            return "empty"

    def _generate_empty_round_robin_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу round robin"""
        return f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Групповая таблица</title>
        <link rel="stylesheet" href="/static/css/round_robin.css">
        <script>
            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="round-robin-container">
            <div class="empty-message">
                <p>{message}</p>
            </div>
        </div>
    </body>
    </html>'''