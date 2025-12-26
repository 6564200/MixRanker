#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML для турнирных сеток (Round Robin и Elimination)
"""

from typing import Dict, List, Optional
import re
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class TournamentBracketGenerator(HTMLBaseGenerator):
    """Генератор турнирных сеток"""

    # === ROUND ROBIN ===
    
    def generate_round_robin_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для групповой турнирной таблицы"""
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
        
        metadata = tournament_data.get("metadata", {})
        class_name = (xml_type_info.get("class_name", "Категория")).upper()
        group_name = (xml_type_info.get("group_name", "Группа")).upper()
        
        participants = self._extract_rr_participants(group_data)
        matches_matrix = self._extract_rr_matches_matrix(group_data, len(participants))
        standings = self._extract_rr_standings(group_data)
        
        return self._render_round_robin_html(class_name, group_name, participants, matches_matrix, standings)

    def _render_round_robin_html(self, class_name: str, group_name: str, 
                                  participants: List[Dict], matches_matrix: Dict, standings: List[Dict]) -> str:
        """Рендерит HTML round robin таблицы"""
        html = f'''{self.html_head(f"{class_name} - {group_name}", "round_robin.css", 30000).replace(
            "</head>", """<script>
            window.onload = function() { window.scrollTo(0, 0); };
        </script>
</head>""")}
<body>
    <div class="round-robin-container">
        <div class="round-robin-table">
            <div class="table-title">
                <div class="table-header">
                    <div class="cell-num"></div>
                    <div class="cell-gpp">{class_name[class_name.find(",")+1:]} - {group_name}</div>
                </div>'''
        
        for i in range(1, len(participants) + 1):
            html += f'<div class="team-number-header"><div class="team-number">{i}</div></div>'
        
        html += '''<div class="points-header"><div class="points">ОЧКИ</div></div>
                   <div class="points-header"><div class="points">МЕСТО</div></div>
                </div>'''
        
        for i, participant in enumerate(participants):
            place = self._get_participant_place(participant, standings)
            points = self._get_participant_points(participant, standings)
            upper_short_name = (participant.get("short_name", " ")).upper()
            
            html += f'''<div class="team-row">
                <div class="team-number-cell">
                    <div class="team-num">{i + 1}</div>
                    <div class="team-name-cell">{upper_short_name}</div>
                </div>'''
            
            for j in range(len(participants)):
                if i == j:
                    html += '<div class="diagonal-cell"></div>'
                else:
                    match_result = matches_matrix.get(f"{i}_{j}", {})
                    html += self._render_rr_match_cell(match_result)
            
            html += f'''<div class="points-cell"><div class="points-z">{points}</div></div>
                        <div class="place-cell"><div class="place-z">{place}</div></div>
                    </div>'''
        
        html += '''</div></div></div></body></html>'''
        return html

    def _render_rr_match_cell(self, match_result: Dict) -> str:
        """Рендерит ячейку матча round robin"""
        if match_result.get("is_bye"):
            return '<div class="match-cell-bye-cell">●</div>'
        elif match_result.get("has_result"):
            score = match_result.get("score", "-")
            sets = match_result.get("sets", "")
            return f'''<div class="match-cell">
                <div class="match-score">{score}</div>
                <div class="match-sets">{sets}</div>
            </div>'''
        else:
            return '<div class="match-cell-empty-cell"></div>'

    def _extract_rr_participants(self, group_data: Dict) -> List[Dict]:
        """Извлекает участников из групповых данных"""
        participants = []
        pool_data = group_data.get("Pool", [])
        
        for row in pool_data:
            if not isinstance(row, list):
                continue
            for cell in row:
                if not isinstance(cell, dict):
                    continue
                if cell.get("CellType") == "ParticipantCell" and cell.get("ParticipantCell"):
                    participant = self._parse_participant_cell(cell["ParticipantCell"], len(participants))
                    if participant:
                        participants.append(participant)
        
        # Берем только первую половину
        if len(participants) > 0:
            half_count = len(participants) // 2
            if half_count > 0:
                participants = participants[:half_count]
        
        return participants

    def _parse_participant_cell(self, participant_cell: Dict, fallback_index: int) -> Optional[Dict]:
        """Парсит ячейку участника"""
        if not participant_cell.get("Players") or not isinstance(participant_cell["Players"], list):
            return None
        
        team_names = []
        player_ids = []
        for player in participant_cell["Players"]:
            if isinstance(player, dict) and player.get("Name"):
                team_names.append(player["Name"])
                if player.get("Id"):
                    player_ids.append(str(player["Id"]))
        
        if not team_names:
            return None
        
        full_name = "/".join(team_names)
        short_name = self.create_short_name(full_name) if full_name != "Bye" else "Bye"
        
        return {
            "index": participant_cell.get("Index", fallback_index),
            "participant_id": participant_cell.get("ParticipantId"),
            "full_name": full_name,
            "short_name": short_name,
            "is_bye": full_name.upper() == "BYE",
            "player_ids": player_ids
        }

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
                    match_info = self._parse_match_cell(cell["MatchCell"])
                    if row_index != cell_index:
                        match_key = f"{row_index-1}_{cell_index-1}"
                        matches_matrix[match_key] = match_info
        
        return matches_matrix

    def _parse_match_cell(self, match_cell: Dict) -> Dict:
        """Парсит ячейку матча"""
        match_results = match_cell.get("MatchResults", {})
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
            
            detailed_scoring = score_data.get("DetailedScoring", [])
            if detailed_scoring:
                sets_parts = [f"{s.get('FirstParticipantScore', 0)}-{s.get('SecondParticipantScore', 0)}" 
                              for s in detailed_scoring]
                match_info["sets"] = " ".join(sets_parts)
        else:
            cancellation = match_results.get('CancellationStatus') or ''
            if 'Won' in cancellation:
                match_info["score"] = 'Won'
            elif 'Lost' in cancellation:
                match_info["score"] = 'Lost'
        
        return match_info

    def _extract_rr_standings(self, group_data: Dict) -> List[Dict]:
        """Извлекает турнирную таблицу"""
        standings_data = group_data.get("Standings", [])
        standings = []
        fake_id_counter = 1000
        
        for standing in standings_data:
            if not isinstance(standing, dict):
                continue
            
            player_ids = []
            for key in ['DoublesPlayer1Model', 'DoublesPlayer2Model']:
                player = standing.get(key)
                if isinstance(player, dict) and player.get('Id'):
                    player_ids.append(str(player['Id']))
                else:
                    player_ids.append(str(fake_id_counter))
                    fake_id_counter += 1
            
            standings.append({
                "participant_id": str(standing.get("ParticipantId", "")),
                "standing": standing.get("Standing", 0),
                "wins": standing.get("Wins", 0),
                "match_points": standing.get("MatchPoints", 0),
                "player_ids": player_ids
            })
        
        return standings

    def _get_participant_place(self, participant: Dict, standings: List[Dict]) -> int:
        """Получает место участника"""
        participant_id = participant.get("participant_id")
        if participant_id:
            for standing in standings:
                if str(standing.get("participant_id", "")) == str(participant_id):
                    return standing.get("standing", 0)
        
        participant_player_ids = set(participant.get("player_ids", []))
        if participant_player_ids:
            for standing in standings:
                if participant_player_ids & set(standing.get("player_ids", [])):
                    return standing.get("standing", 0)
        
        return 0

    def _get_participant_points(self, participant: Dict, standings: List[Dict]) -> int:
        """Получает очки участника"""
        participant_id = participant.get("participant_id")
        if participant_id:
            for standing in standings:
                if str(standing.get("participant_id", "")) == str(participant_id):
                    return standing.get("match_points", 0)
        
        participant_player_ids = set(participant.get("player_ids", []))
        if participant_player_ids:
            for standing in standings:
                if participant_player_ids & set(standing.get("player_ids", [])):
                    return standing.get("match_points", 0)
        
        return 0

    def _generate_empty_round_robin_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу round robin"""
        return self.empty_page_html("Групповая таблица", message, "round_robin.css")

    # === ELIMINATION ===
    
    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для турнирной сетки на выбывание"""
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
        class_name = xml_type_info.get("class_name", "Категория")
        stage_name = xml_type_info.get("stage_name", "Плей-офф")
        
        rounds_data = self._analyze_elimination_structure(bracket_data)
        
        return self._render_elimination_html(class_name, stage_name, bracket_data, rounds_data)

    def _render_elimination_html(self, class_name: str, stage_name: str, 
                                  bracket_data: Dict, rounds_data: List[Dict]) -> str:
        """Рендерит HTML elimination сетки"""
        html = f'''{self.html_head(f"{class_name} - {stage_name}", "elimination.css", 30000)}
<body>
    <div class="elimination-container">
        <div class="round-column">'''
        
        for round_index, round_info in enumerate(rounds_data):
            if round_index == 0:
                continue  # Первый раунд - участники, пропускаем
            
            full_results = self._generate_match_pairs_from_api(round_index, round_info['matches'])
            html += '<div class="bracket-grid">'
            
            if round_index == 1:
                html += f'<div class="places">{stage_name}</div>'
            
            for match in full_results:
                html += self._render_elimination_match(match)
            
            html += '</div>'
        
        html += '''</div></div></body></html>'''
        return html

    def _render_elimination_match(self, match: Dict) -> str:
        """Рендерит один матч elimination"""
        score_parts = match['score'].split('-')
        score1 = score_parts[0] if len(score_parts) > 0 else '0'
        score2 = score_parts[1] if len(score_parts) > 1 else '0'
        
        return f'''<div class="container">
            <div class="row row-top">
                <div class="names"><span class="name-main {match['secondary1']}">{match['team_1_name']}</span></div>
                <div class="score"><span class="set-score">{match['sets1']}</span></div>
                <div class="rank rank-top"><span class="rank-number">{score1}</span></div>
            </div>
            <div class="row row-bottom">
                <div class="names"><span class="name-main {match['secondary2']}">{match['team_2_name']}</span></div>
                <div class="score"><span class="set-score">{match['sets2']}</span></div>
                <div class="rank rank-bottom"><span class="rank-number">{score2}</span></div>
            </div>
        </div>'''

    def _analyze_elimination_structure(self, bracket_data: Dict) -> List[Dict]:
        """Анализирует структуру elimination для определения раундов"""
        rounds_data = []
        
        first_round_participants = bracket_data.get("FirstRoundParticipantCells", [])
        if first_round_participants:
            rounds_data.append({
                'title': 'Команды',
                'matches': first_round_participants,
                'type': 'participants'
            })
        
        if bracket_data.get("DrawData"):
            matches_by_round = {}
            for round_matches in bracket_data["DrawData"]:
                for match_data in round_matches:
                    if match_data:
                        round_number = match_data.get("Round", 1)
                        if round_number not in matches_by_round:
                            matches_by_round[round_number] = []
                        matches_by_round[round_number].append(match_data)
            
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
        """Генерирует названия раундов"""
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
            names = [f'Раунд {i + 1}' for i in range(num_rounds - 3)]
            names.extend(['Четвертьфинал', 'Полуфинал', 'Финал'])
            return names

    def _generate_match_pairs_from_api(self, round_index: int, matches: List[Dict]) -> List[Dict]:
        """Формирует пары матчей из API данных"""
        match_pairs = []
        
        for match_data in matches:
            match_view_model = match_data.get("MatchViewModel", {})
            is_played = match_view_model.get("IsPlayed", False)
            has_score = match_view_model.get("HasScore", False)
            winner_id = match_data.get("WinnerParticipantId")
            
            challenger_data = match_data.get("ChallengerParticipant", {})
            challenged_data = match_data.get("ChallengedParticipant", {})
            
            team1_name = self.get_team_name_from_players(
                challenger_data.get("FirstPlayer", {}),
                challenger_data.get("SecondPlayer", {})
            )
            team2_name = self.get_team_name_from_players(
                challenged_data.get("FirstPlayer", {}),
                challenged_data.get("SecondPlayer", {})
            )
            
            team1_id = challenger_data.get("EventParticipantId")
            team2_id = challenged_data.get("EventParticipantId")
            
            match_info = {
                'team_1_name': self.create_short_name(team1_name) if team1_name else 'TBD',
                'team_2_name': self.create_short_name(team2_name) if team2_name else 'TBD',
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
                match_info['status'] = 'Сыгран'
                if winner_id == team1_id:
                    match_info['secondary2'] = 'lost'
                elif winner_id == team2_id:
                    match_info['secondary1'] = 'lost'
                
                score_data = match_view_model.get("Score", {})
                match_info['score'] = self.format_score_summary(score_data)
                sets_summary = self.format_sets_summary(score_data)
                
                sets1 = re.findall(r'(\d+)-\d+', sets_summary)
                sets2 = re.findall(r'\d+-(\d+)', sets_summary)
                match_info['sets1'] = ' '.join(sets1)
                match_info['sets2'] = ' '.join(sets2)
                
            elif is_played and not has_score:
                match_info['status'] = 'Walkover'
                if winner_id == team1_id:
                    match_info['secondary2'] = 'lost'
                    match_info['score'] = '1-0'
                    match_info['sets2'] = 'WO'
                elif winner_id == team2_id:
                    match_info['secondary1'] = 'lost'
                    match_info['score'] = '0-1'
                    match_info['sets1'] = 'WO'
            
            match_pairs.append(match_info)
        
        return match_pairs

    def _check_bye_advancement(self, match_data: Dict) -> Optional[Dict]:
        """Проверяет есть ли в матче Bye"""
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        challenger_team = self.get_team_name_from_players(
            challenger_data.get("FirstPlayer", {}),
            challenger_data.get("SecondPlayer", {})
        )
        challenged_team = self.get_team_name_from_players(
            challenged_data.get("FirstPlayer", {}),
            challenged_data.get("SecondPlayer", {})
        )
        
        if challenger_team.upper() == "BYE" or not challenger_team.strip():
            if challenged_team and challenged_team.upper() != "BYE":
                return {"team_name": challenged_team, "participant_id": challenged_data.get("EventParticipantId")}
        elif challenged_team.upper() == "BYE" or not challenged_team.strip():
            if challenger_team and challenger_team.upper() != "BYE":
                return {"team_name": challenger_team, "participant_id": challenger_data.get("EventParticipantId")}
        
        return None

    def _generate_empty_elimination_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу elimination"""
        return self.empty_page_html("Турнирная сетка", message, "elimination.css")
