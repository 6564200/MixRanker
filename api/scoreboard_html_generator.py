#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML scoreboard для кортов
ВНИМАНИЕ: Код скопирован из оригинального xml_generator.py для сохранения совместимости с CSS
"""

from typing import Dict
import logging
from .html_base import HTMLBase

logger = logging.getLogger(__name__)


class ScoreboardHTMLGenerator(HTMLBase):
    """Генератор HTML scoreboard - точная копия из xml_generator.py"""
    
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
                    html_set_score_1 += f'<div class="set set1-{i}">{set_score}</div>'
                
                for i in range(len(detailed_result), max_sets):
                    html_set_score_1 += '<div class="set_1">-</div>'
            else:
                # Для матчей без детального счета показываем пустые сеты
                for i in range(max_sets):
                    html_set_score_1 += f'<div class="set set1-{i}">-</div>'
            
            # Сеты для команды 2
            if detailed_result and len(detailed_result) > 0:
                for i in range(min(max_sets, len(detailed_result))):
                    set_score = detailed_result[i].get("secondParticipantScore", 0)
                    html_set_score_2 += f'<div class="set set1-{i}">{set_score}</div>'
                
                for i in range(len(detailed_result), max_sets):
                    html_set_score_2 += '<div class="set_2">-</div>'
            else:
                # Для матчей без детального счета показываем пустые сеты
                for i in range(max_sets):
                    html_set_score_2 += f'<div class="set set2-{i}">-</div>'
            
            html_content += f'''

                
		  	
                <!-- Team 1 Row -->
                <div class="team-row">
                    <div class="bg-team">
                        <span class="team-name">{team1_name}</span>
                        {html_set_score_1 if show_score else "*"}
                        <div class="main-score-area bg-rad1">
                            <span class="score-text">{self._get_game_score_display(detailed_result, team1_score, 'first') if show_score else "-"}</span>
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
                            <span class="score-text">{self._get_game_score_display(detailed_result, team2_score, 'second') if show_score else "-"}</span>
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
                        <div class="player_name1">{team1_players[0] if len(team1_players) > 0 else ''}</div>
                        <div class="player_name2">{team1_players[1] if len(team1_players) > 1 else ''}</div>
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
                        <div class="player_name1">{team2_players[0] if len(team2_players) > 0 else ''}</div>
                        <div class="player_name2">{team2_players[1] if len(team2_players) > 1 else ''}</div>
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