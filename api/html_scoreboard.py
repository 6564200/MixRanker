#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страниц scoreboard для кортов
"""

from typing import Dict, List, Optional
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class ScoreboardGenerator(HTMLBaseGenerator):
    """Генератор scoreboard страниц"""

    def _extract_match_data(self, court_data: Dict) -> Dict:
        """Извлекает данные матча из court_data"""
        match_state = court_data.get("current_match_state", "free")
        current_participants = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        next_participants = court_data.get("next_first_participant", [])
        
        if current_participants:
            return {
                "team1_players": court_data.get("current_first_participant", court_data.get("first_participant", [])),
                "team2_players": court_data.get("current_second_participant", court_data.get("second_participant", [])),
                "team1_score": court_data.get("current_first_participant_score", court_data.get("first_participant_score", 0)),
                "team2_score": court_data.get("current_second_participant_score", court_data.get("second_participant_score", 0)),
                "detailed_result": court_data.get("current_detailed_result", court_data.get("detailed_result", [])),
                "class_name": court_data.get("current_class_name", court_data.get("class_name", "")),
                "show_current_match": True,
                "show_score": match_state in ["live", "finished"] or match_state not in ["scheduled", "playing_no_score"],
                "match_state": match_state
            }
        elif next_participants:
            return {
                "team1_players": court_data.get("next_first_participant", []),
                "team2_players": court_data.get("next_second_participant", []),
                "team1_score": 0,
                "team2_score": 0,
                "detailed_result": [],
                "class_name": court_data.get("next_class_name", ""),
                "show_current_match": True,
                "show_score": False,
                "match_state": "next"
            }
        else:
            return {
                "team1_players": [],
                "team2_players": [],
                "team1_score": 0,
                "team2_score": 0,
                "detailed_result": [],
                "class_name": "",
                "show_current_match": False,
                "show_score": False,
                "match_state": "free"
            }

    def _format_team_name(self, players: List[Dict], use_initials: bool = True) -> str:
        """Форматирует имя команды из списка игроков"""
        if not players:
            return ""
        if use_initials:
            initials = [p.get("initialLastName", "") for p in players if p.get("initialLastName")]
            return " / ".join(initials).upper()
        else:
            names = [p.get("fullName", "") for p in players if p.get("fullName")]
            return " / ".join(names)

    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует HTML страницу scoreboard для корта"""
        match_data = self._extract_match_data(court_data)
        court_name = court_data.get("court_name", "Court")
        
        team1_name = self._format_team_name(match_data["team1_players"])
        team2_name = self._format_team_name(match_data["team2_players"])
        detailed_result = match_data["detailed_result"]
        show_score = match_data["show_score"]
        
        
        # Сеты
        max_sets = max(len(detailed_result), 1) if match_data["show_current_match"] and detailed_result else 1
        
        html_set_score_1 = ''
        html_set_score_2 = ''
        
        if detailed_result:
            for i, set_data in enumerate(detailed_result):
                score1 = set_data.get("firstParticipantScore", 0)
                score2 = set_data.get("secondParticipantScore", 0)
                if score1 > score2:
                    html_set_score_1 += f'<div class="setV set1-{i}">{score1}</div>'
                    html_set_score_2 += f'<div class="set set2-{i}">{score2}</div>'
                elif score1 < score2:
                    html_set_score_1 += f'<div class="set set1-{i}">{score1}</div>'
                    html_set_score_2 += f'<div class="setV set2-{i}">{score2}</div>'
                else:
                    html_set_score_1 += f'<div class="set set1-{i}">{score1}</div>'
                    html_set_score_2 += f'<div class="set set2-{i}">{score2}</div>'                    
        else:
            for i in range(max_sets):
                html_set_score_1 += f'<div class="set set1-{i}">-</div>'
                html_set_score_2 += f'<div class="set set2-{i}">-</div>'
                
        logger.info(f"generate_court_scoreboard_html: court = {html_set_score_1} - {html_set_score_2}")
        
        html_content = f'''{self.html_head(f"{court_name} - Scoreboard", "scoreboard.css?v=0.0.1", 3000)}
<body>
    <div class="scoreboard-container">
        <div class="scoreboard">
            <div class="cort">
                <span class="text-cort">{court_name}</span>
            </div>'''
        
        if match_data["show_current_match"]:
            html_content += f'''
            <!-- Team 1 Row -->
            <div class="team-row">
                <div class="bg-team">
                    <span class="team-name">{team1_name}</span>
                    {html_set_score_1 if show_score else "*"}
                    <div class="main-score-area bg-rad1">
                        <span class="score-text">{self.get_game_score_display(detailed_result, match_data["team1_score"], 'first') if show_score else "-"}</span>
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
                        <span class="score-text">{self.get_game_score_display(detailed_result, match_data["team2_score"], 'first') if show_score else "-"}</span>
                    </div>
                </div>
            </div>'''
        else:
            html_content += '''
            <div class="team-row">
                <div class="bg-team"></div>
                <div class="team2">NO ACTIVE MATCH</div>
                <div class="bg-score bg-rad2"></div>
            </div>'''
        
        html_content += '''
        </div>
    </div>
</body>
</html>'''
        
        return html_content

    def generate_court_fullscreen_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует полноразмерную HTML страницу scoreboard"""
        match_data = self._extract_match_data(court_data)
        court_name = court_data.get("court_name", "Court")
        detailed_result = match_data["detailed_result"]
        show_score = match_data["show_score"]
        
        # Счета по сетам
        team1_scores = [0, 0, 0, match_data["team1_score"]]
        team2_scores = [0, 0, 0, match_data["team2_score"]]
        
        if detailed_result:
            for i in range(min(len(detailed_result), 3)):
                team1_scores[i] = detailed_result[i].get("firstParticipantScore", 0)
                team2_scores[i] = detailed_result[i].get("secondParticipantScore", 0)
        
        # Имена игроков
        team1_players = [p.get("fullName", "") for p in match_data["team1_players"] if p.get("fullName")]
        team2_players = [p.get("fullName", "") for p in match_data["team2_players"] if p.get("fullName")]
        
        # Заполняем до 2 игроков
        while len(team1_players) < 2:
            team1_players.append("")
        while len(team2_players) < 2:
            team2_players.append("")

        if match_data["show_current_match"]:
            return f'''{self.html_head("Таблица результатов матча", "fullscreen_scoreboard.css", 1000)}
<body>
    <div class="table-container">
        <div class="bg_table">
            <div class="table-wrapper">
                <div class="bg_head_tab">
                    <div class="text_set">СЕТ 1</div>
                    <div class="text_set">СЕТ 2</div>
                    <div class="text_set">СЕТ 3</div>
                    <div class="text_set_itog">ГЕЙМ</div>
                </div>
                
                <div class="bg_team1">
                    <div class="command_name1">
                        <div class="player_name1">{team1_players[0]}</div>
                        <div class="player_name2">{team1_players[1]}</div>
                    </div>
                    <div class="set_play1">
                        <div class="text_set_score">{team1_scores[0] if show_score else ''}</div>
                        <div class="text_set_score">{team1_scores[1] if show_score else ''}</div>
                        <div class="text_set_score">{team1_scores[2] if show_score else ''}</div>
                        <div class="text_set_itog_score">{self.get_game_score_display(detailed_result, team1_scores[3], 'first') if show_score else ''}</div>
                    </div>
                </div>
                
                <div class="bg_line"></div>
                
                <div class="bg_team2">
                    <div class="command_name2">
                        <div class="player_name1">{team2_players[0]}</div>
                        <div class="player_name2">{team2_players[1]}</div>
                    </div>
                    <div class="set_play2">
                        <div class="text_set_score">{team2_scores[0] if show_score else ''}</div>
                        <div class="text_set_score">{team2_scores[1] if show_score else ''}</div>
                        <div class="text_set_score">{team2_scores[2] if show_score else ''}</div>
                        <div class="text_set_itog_score">{self.get_game_score_display(detailed_result, team2_scores[3], 'second') if show_score else ''}</div>
                    </div>
                </div>
                <div class="bg_line"></div>
            </div>
        </div>
    </div>
</body>
</html>'''
        else:
            return f'''{self.html_head(f"{court_name} - Scoreboard", "fullscreen_scoreboard.css", 9000)}
<body>
    <div class="scoreboard">
        <div class="team-row no-match">
            <div class="team-name">NO ACTIVE MATCH</div>
        </div>
    </div>
</body>
</html>'''

    def generate_next_match_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует страницу следующего матча"""
        court_name = court_data.get("court_name", "Court")
        next_participants = court_data.get("next_first_participant", [])
        
        if not next_participants or not id_url:
            return self.empty_page_html(f"{court_name} - Next match", "NO NEXT MATCH", "next_match.css")
        
        team1_players = court_data.get("next_first_participant", [])
        team2_players = court_data.get("next_second_participant", [])
        id_url_dict = {d['id']: d for d in id_url}
        
        team1_players = [(p, id_url_dict.get(p.get('id'), {})) for p in team1_players if p.get('id')]
        team2_players = [(p, id_url_dict.get(p.get('id'), {})) for p in team2_players if p.get('id')]
        start_time = court_data.get("next_start_time", "")
        
        team1_names = '<br>'.join([p[0].get("fullName", "") for p in team1_players])
        team2_names = '<br>'.join([p[0].get("fullName", "") for p in team2_players])
        team1_images = ''.join(f'<img src="{p[1].get("photo_url", "")}" alt="{p[0].get("fullName", "")}">' for p in team1_players)
        team2_images = ''.join(f'<img src="{p[1].get("photo_url", "")}" alt="{p[0].get("fullName", "")}">' for p in team2_players)
        
        return f'''{self.html_head(f"{court_name} - Next match", "next_match.css", 9000)}
<body>
    <div class="next-match">
        <div class="time">{start_time}</div>
        <div class="block">
            <div class="left_team">
                <div class="left_participants">{team1_names}</div>
                <div class="left-images">{team1_images}</div>
            </div>
            <div class="right_team">
                <div class="right_participants">{team2_names}</div>
                <div class="right-images">{team2_images}</div>
            </div>
        </div>
    </div>
</body>
</html>'''

    def generate_introduction_page_html(self, participant_info: Dict) -> str:
        """Генерирует страницу представления участника"""
        full_name = f'{participant_info.get("firstName", "")} {participant_info.get("lastName", "")}'
        
        return f'''{self.html_head(f"{participant_info.get('id', '')} - Introduction", "introduction.css", 9000)}
<body>
    <div class="introduction">
        <table>
            <thead>
                <tr><th colspan="2">{full_name}</th></tr>
            </thead>
            <tbody>
                <tr><td class="key">СТРАНА</td><td class="value">{participant_info.get('country', '')}</td></tr>
                <tr><td class="key">РЕЙТИНГ FIP</td><td class="value">{participant_info.get('rating', '')}</td></tr>
                <tr><td class="key">РОСТ</td><td class="value">{participant_info.get('height', '')}</td></tr>
                <tr><td class="key">ИГРОВАЯ ПОЗИЦИЯ</td><td class="value">{participant_info.get('position', '')}</td></tr>
            </tbody>
        </table>
    </div>
</body>
</html>'''
