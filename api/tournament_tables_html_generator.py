#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML турнирных таблиц (Round Robin, Elimination)
"""

from typing import Dict
import logging
from .html_base import HTMLBase

logger = logging.getLogger(__name__)


class TournamentTablesHTMLGenerator(HTMLBase):
    """Генератор HTML турнирных таблиц"""
    
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
    
    def _render_participant_cell(self, cell: Dict) -> str:
        """Рендерит ячейку участника"""
        participant_cell = cell.get("ParticipantCell", {})
        players = participant_cell.get("Players", [])
        
        if not players:
            return '<td class="participant">-</td>'
        
        names = [p.get("Name", "") for p in players if isinstance(p, dict)]
        name_str = " / ".join(names)
        
        return f'<td class="participant">{name_str}</td>'
    
    def _render_standing_cell(self, cell: Dict) -> str:
        """Рендерит ячейку позиции"""
        standing_cell = cell.get("StandingCell", {})
        position = standing_cell.get("Position", "-")
        played = standing_cell.get("Played", 0)
        won = standing_cell.get("Won", 0)
        points = standing_cell.get("Points", 0)
        
        return f'<td class="standing">{position} ({won}/{played})</td>'
    
    def _render_match_cell(self, cell: Dict) -> str:
        """Рендерит ячейку матча"""
        match_cell = cell.get("MatchCell", {})
        sets = match_cell.get("Sets", [])
        
        if not sets:
            return '<td class="match">-</td>'
        
        scores = []
        for set_data in sets:
            if isinstance(set_data, dict):
                s1 = set_data.get("Score1", 0)
                s2 = set_data.get("Score2", 0)
                scores.append(f"{s1}:{s2}")
        
        return f'<td class="match">{" ".join(scores)}</td>'
    
    def _render_elimination_match(self, match: Dict) -> str:
        """Рендерит матч турнирной сетки"""
        participants = match.get("Participants", [])
        
        p1_name = "TBD"
        p2_name = "TBD"
        
        if len(participants) > 0 and participants[0]:
            players1 = participants[0].get("Players", [])
            if players1:
                p1_name = " / ".join([p.get("Name", "") for p in players1])
        
        if len(participants) > 1 and participants[1]:
            players2 = participants[1].get("Players", [])
            if players2:
                p2_name = " / ".join([p.get("Name", "") for p in players2])
        
        sets = match.get("Sets", [])
        score_html = ""
        if sets:
            scores = [f'{s.get("Score1", 0)}:{s.get("Score2", 0)}' for s in sets if isinstance(s, dict)]
            score_html = f'<div class="score">{" ".join(scores)}</div>'
        
        return f'''
        <div class="match">
            <div class="participant">{p1_name}</div>
            <div class="participant">{p2_name}</div>
            {score_html}
        </div>'''
    
    def _generate_empty_table_html(self, message: str) -> str:
        """Генерирует пустую таблицу"""
        return f'''<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><title>Турнирная таблица</title></head>
<body><div style="text-align:center;padding:50px;">{message}</div></body>
</html>'''
