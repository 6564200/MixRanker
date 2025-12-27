#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страниц scoreboard для кортов
"""

from typing import Dict, List
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class ScoreboardGenerator(HTMLBaseGenerator):
    """Генератор scoreboard страниц"""

    def _extract_match_data(self, court_data: Dict) -> Dict:
        """Извлекает данные матча из court_data"""
        # Проверяем текущих участников
        team1 = court_data.get("first_participant", [])
        team2 = court_data.get("second_participant", [])

        if not team1:
            # Нет активного матча
            return {
                "team1_players": [], "team2_players": [],
                "team1_score": 0, "team2_score": 0,
                "detailed_result": [], "class_name": "",
                "show_current_match": False, "show_score": False,
                "match_state": "free"
            }

        detailed = court_data.get("detailed_result", [])
        score1 = court_data.get("first_participant_score", 0)
        score2 = court_data.get("second_participant_score", 0)
        
        # Показываем счёт если есть детальные результаты ИЛИ есть счёт
        show_score = len(detailed) > 0 or score1 > 0 or score2 > 0

        return {
            "team1_players": team1,
            "team2_players": team2,
            "team1_score": score1,
            "team2_score": score2,
            "detailed_result": detailed,
            "class_name": court_data.get("class_name", ""),
            "show_current_match": True,
            "show_score": show_score,
            "match_state": court_data.get("event_state", "")
        }

    def _format_team_name(self, players: List[Dict], use_initials: bool = True) -> str:
        """Форматирует имя команды из списка игроков"""
        if not players:
            return ""
        key = "initialLastName" if use_initials else "fullName"
        names = [p.get(key, "") for p in players if p.get(key)]
        result = " / ".join(names)
        return result.upper() if use_initials else result

    def _render_set_scores(self, detailed_result: List[Dict], max_sets: int = 3) -> tuple:
        """Рендерит HTML для счета по сетам. Возвращает (html1, html2)"""
        html1, html2 = '', ''

        if not detailed_result:
            for i in range(max_sets):
                html1 += f'<div class="set set1-{i}">-</div>'
                html2 += f'<div class="set set2-{i}">-</div>'
            return html1, html2

        for i, set_data in enumerate(detailed_result):
            s1 = set_data.get("firstParticipantScore", 0)
            s2 = set_data.get("secondParticipantScore", 0)
            cls1 = "setV" if s1 > s2 else "set"
            cls2 = "setV" if s2 > s1 else "set"
            html1 += f'<div class="{cls1} set1-{i}">{s1}</div>'
            html2 += f'<div class="{cls2} set2-{i}">{s2}</div>'

        return html1, html2

    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        """Генерирует HTML scoreboard с AJAX-обновлением"""
        match = self._extract_match_data(court_data)
        court_name = court_data.get("court_name", "Court")

        # Получаем ID из параметров или court_data
        t_id = tournament_id or court_data.get("tournament_id", "")
        c_id = court_id or court_data.get("court_id", "")

        team1_name = self._format_team_name(match["team1_players"])
        team2_name = self._format_team_name(match["team2_players"])
        detailed = match["detailed_result"]
        show_score = match["show_score"]

        html_set1, html_set2 = self._render_set_scores_smart(detailed)

        score1 = self.get_game_score_display(detailed, match["team1_score"], 'first') if show_score else "-"
        score2 = self.get_game_score_display(detailed, match["team2_score"], 'second') if show_score else "-"

        no_match_display = "none" if match["show_current_match"] else "block"
        match_display = "block" if match["show_current_match"] else "none"

        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{court_name} - Scoreboard</title>
    <link rel="stylesheet" href="/static/css/scoreboard.css?v=0.0.3">
    <style>
        .fade-update {{ transition: opacity 0.15s ease-in-out; }}
        .updating {{ opacity: 0.7; }}
        .sets-container {{ display: inline-flex; gap: 2px; }}
    </style>
</head>
<body data-tournament-id="{t_id}" data-court-id="{c_id}" data-update-interval="2000" data-mode="scoreboard">
    <div class="scoreboard-container">
        <div class="scoreboard">
            <div class="cort"><span class="text-cort" data-field="court_name">{court_name}</span></div>
            
            <div id="match-content" style="display: {match_display};">
                <div class="team-row">
                    <div class="bg-team">
                        <span class="team-name fade-update" data-field="team1_name">{team1_name}</span>
                        <div class="sets-container" data-field="team1_sets">{html_set1 if show_score else "*"}</div>
                        <div class="main-score-area bg-rad1">
                            <span class="score-text fade-update" data-field="team1_score">{score1}</span>
                        </div>
                    </div>
                </div>
                <div class="divider-bar"></div>
                <div class="team-row">
                    <div class="bg-team">
                        <span class="team-name fade-update" data-field="team2_name">{team2_name}</span>
                        <div class="sets-container" data-field="team2_sets">{html_set2 if show_score else "*"}</div>
                        <div class="main-score-area bg-rad2">
                            <span class="score-text fade-update" data-field="team2_score">{score2}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="no-match-content" style="display: {no_match_display};">
                <div class="team-row">
                    <div class="bg-team"></div>
                    <div class="team2">NO ACTIVE MATCH</div>
                    <div class="bg-score bg-rad2"></div>
                </div>
            </div>
        </div>
    </div>
    <script src="/static/js/smart_scoreboard.js?v=0.0.1"></script>
</body>
</html>'''

    def generate_smart_scoreboard_html(self, court_data: Dict, tournament_id: str, court_id: str) -> str:
        """Алиас для обратной совместимости"""
        return self.generate_court_scoreboard_html(court_data, None, tournament_id, court_id)

    def _render_set_scores_smart(self, detailed_result: List[Dict], max_sets: int = 3) -> tuple:
        """Рендерит HTML для счета по сетам с классами для JS обновления"""
        html1, html2 = '', ''

        if not detailed_result:
            for i in range(max_sets):
                html1 += f'<div class="set set1-{i}">-</div>'
                html2 += f'<div class="set set2-{i}">-</div>'
            return html1, html2

        for i, set_data in enumerate(detailed_result):
            s1 = set_data.get("firstParticipantScore", 0)
            s2 = set_data.get("secondParticipantScore", 0)
            cls1 = "setV" if s1 > s2 else "set"
            cls2 = "setV" if s2 > s1 else "set"
            html1 += f'<div class="{cls1} set1-{i}">{s1}</div>'
            html2 += f'<div class="{cls2} set2-{i}">{s2}</div>'

        return html1, html2

    def generate_court_fullscreen_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        """Генерирует полноразмерную HTML страницу scoreboard с AJAX-обновлением"""
        match = self._extract_match_data(court_data)
        court_name = court_data.get("court_name", "Court")
        
        # Получаем ID из параметров или court_data
        t_id = tournament_id or court_data.get("tournament_id", "")
        c_id = court_id or court_data.get("court_id", "")
        
        detailed = match["detailed_result"]
        show_score = match["show_score"]
        num_sets = len(detailed)

        # Счета по сетам
        scores1 = [0, 0, 0]
        scores2 = [0, 0, 0]
        for i, s in enumerate(detailed[:3]):
            scores1[i] = s.get("firstParticipantScore", 0)
            scores2[i] = s.get("secondParticipantScore", 0)

        # Имена игроков (до 2)
        names1 = [p.get("fullName", "") for p in match["team1_players"][:2]]
        names2 = [p.get("fullName", "") for p in match["team2_players"][:2]]
        names1.extend([""] * (2 - len(names1)))
        names2.extend([""] * (2 - len(names2)))

        no_match_display = "none" if match["show_current_match"] else "flex"
        match_display = "block" if match["show_current_match"] else "none"

        game1 = self.get_game_score_display(detailed, match["team1_score"], 'first') if show_score else ''
        game2 = self.get_game_score_display(detailed, match["team2_score"], 'second') if show_score else ''

        # Генерируем заголовки сетов с классом hidden для пустых
        def set_header(i):
            hidden = "" if (show_score and i < num_sets) else " hidden"
            return f'<div class="text_set{hidden}" data-field="set_header_{i}">СЕТ {i+1}</div>'

        # Генерируем ячейки счёта с классом hidden для пустых
        def set_score(i, score, team):
            hidden = "" if (show_score and i < num_sets) else " hidden"
            value = score if (show_score and i < num_sets) else ""
            return f'<div class="text_set_score fade-update{hidden}" data-field="team{team}_set{i}">{value}</div>'

        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{court_name} - Fullscreen Scoreboard</title>
    <link rel="stylesheet" href="/static/css/fullscreen_scoreboard.css?v=0.0.3">
</head>
<body data-tournament-id="{t_id}" data-court-id="{c_id}" data-update-interval="2000" data-mode="fullscreen">
    <div id="match-content" style="display: {match_display};">
        <div class="table-container">
            <div class="bg_table">
                <div class="table-wrapper">
                    <div class="bg_head_tab">
                        {set_header(0)}
                        {set_header(1)}
                        {set_header(2)}
                        <div class="text_set_itog">ГЕЙМ</div>
                    </div>
                    <div class="bg_team1">
                        <div class="command_name1">
                            <div class="player_name1 fade-update" data-field="player1_name1">{names1[0]}</div>
                            <div class="player_name2 fade-update" data-field="player1_name2">{names1[1]}</div>
                        </div>
                        <div class="set_play1">
                            {set_score(0, scores1[0], 1)}
                            {set_score(1, scores1[1], 1)}
                            {set_score(2, scores1[2], 1)}
                            <div class="text_set_itog_score fade-update" data-field="team1_game">{game1}</div>
                        </div>
                    </div>
                    <div class="bg_line"></div>
                    <div class="bg_team2">
                        <div class="command_name2">
                            <div class="player_name1 fade-update" data-field="player2_name1">{names2[0]}</div>
                            <div class="player_name2 fade-update" data-field="player2_name2">{names2[1]}</div>
                        </div>
                        <div class="set_play2">
                            {set_score(0, scores2[0], 2)}
                            {set_score(1, scores2[1], 2)}
                            {set_score(2, scores2[2], 2)}
                            <div class="text_set_itog_score fade-update" data-field="team2_game">{game2}</div>
                        </div>
                    </div>
                    <div class="bg_line"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="no-match-content" style="display: {no_match_display};">
        <div class="team-name">NO ACTIVE MATCH</div>
    </div>
    
    <script src="/static/js/smart_scoreboard.js?v=0.0.2"></script>
</body>
</html>'''

    def generate_next_match_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует страницу следующего матча"""
        court_name = court_data.get("court_name", "Court")
        next_first = court_data.get("next_first_participant", [])

        if not next_first or not id_url:
            return self.empty_page_html(f"{court_name} - Next match", "NO NEXT MATCH", "next_match.css")

        id_url_map = {d['id']: d for d in id_url}

        def build_team_html(players):
            enriched = [(p, id_url_map.get(p.get('id'), {})) for p in players if p.get('id')]
            names = '<br>'.join(p[0].get("fullName", "") for p in enriched)
            images = ''.join(f'<img src="{p[1].get("photo_url", "")}" alt="{p[0].get("fullName", "")}">' for p in enriched)
            return names, images

        next_second = court_data.get("next_second_participant", [])
        names1, images1 = build_team_html(next_first)
        names2, images2 = build_team_html(next_second)
        start_time = court_data.get("next_start_time", "")

        return f'''{self.html_head(f"{court_name} - Next match", "next_match.css", 9000)}
<body>
    <div class="next-match">
        <div class="time">{start_time}</div>
        <div class="block">
            <div class="left_team">
                <div class="left_participants">{names1}</div>
                <div class="left-images">{images1}</div>
            </div>
            <div class="right_team">
                <div class="right_participants">{names2}</div>
                <div class="right-images">{images2}</div>
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
            <thead><tr><th colspan="2">{full_name}</th></tr></thead>
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