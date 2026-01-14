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
        class_name = (xml_type_info.get("class_name", "Категория")).upper()
        group_name = (xml_type_info.get("group_name", "Группа")).upper()

        participants = self._extract_rr_participants(group_data)
        matches_matrix = self._extract_rr_matches_matrix(group_data, len(participants))
        standings = self._extract_rr_standings(group_data)

        return self._render_round_robin_html(class_name, group_name, participants, matches_matrix, standings)

    def _render_round_robin_html(self, class_name: str, group_name: str,
                                  participants: List[Dict], matches_matrix: Dict, standings: List[Dict]) -> str:
        """Рендерит HTML round robin таблицы"""
        head = self.html_head(f"{class_name} - {group_name}", "round_robin.css")
        # Добавляем скрипт скролла
        head = head.replace("</head>", "<script>window.onload=function(){window.scrollTo(0,0);};</script></head>")

        num_participants = len(participants)
        
        # Динамические размеры
        col_width = 175  # ширина колонки матча
        team_cell_width = 770  # ширина ячейки с номером и именем
        points_col_width = 175  # ширина колонки очков/места
        row_height = 83
        header_height = 64
        gap = 2
        
        # Общая ширина таблицы
        table_width = team_cell_width + (num_participants * col_width) + (2 * points_col_width)
        # Общая высота таблицы
        table_height = header_height + (num_participants * (row_height + gap))

        # Заголовок таблицы
        display_name = class_name[class_name.find(",") + 1:].strip() if "," in class_name else class_name
        num_cols = ''.join(f'<div class="team-number-header" style="width:{col_width}px;"><div class="team-number" style="width:{col_width}px;">{i}</div></div>' for i in range(1, num_participants + 1))

        html = f'''{head}
<body style="width:{table_width}px; height:{table_height}px;">
    <div class="round-robin-container">
        <div class="round-robin-table" style="width:{table_width}px; height:{table_height}px;">
            <div class="table-title" style="width:{table_width}px;">
                <div class="table-header" style="width:{team_cell_width}px;">
                    <div class="cell-num"></div>
                    <div class="cell-gpp">{display_name} - {group_name}</div>
                </div>
                {num_cols}
                <div class="points-header" style="width:{points_col_width}px;"><div class="points" style="width:{points_col_width}px;">ОЧКИ</div></div>
                <div class="points-header" style="width:{points_col_width}px;"><div class="points" style="width:{points_col_width}px;">МЕСТО</div></div>
            </div>'''

        for i, participant in enumerate(participants):
            place = self._get_participant_place(participant, standings)
            points = self._get_participant_points(participant, standings)
            short_name = (participant.get("short_name", " ")).upper()

            # Ячейки матчей
            cells = []
            for j in range(num_participants):
                if i == j:
                    cells.append(f'<div class="diagonal-cell" style="width:{col_width}px;"></div>')
                else:
                    match_result = matches_matrix.get(f"{i}_{j}", {})
                    cells.append(self._render_rr_match_cell(match_result, col_width))

            html += f'''<div class="team-row" style="width:{table_width}px;">
                <div class="team-number-cell" style="width:{team_cell_width}px;">
                    <div class="team-num">{i + 1}</div>
                    <div class="team-name-cell">{short_name}</div>
                </div>
                {''.join(cells)}
                <div class="points-cell" style="width:{points_col_width}px;"><div class="points-z" style="width:{points_col_width}px;">{points}</div></div>
                <div class="place-cell" style="width:{points_col_width}px;"><div class="place-z" style="width:{points_col_width}px;">{place}</div></div>
            </div>'''

        html += '''</div></div></body></html>'''
        return html

    def _render_rr_match_cell(self, match_result: Dict, col_width: int = 175) -> str:
        """Рендерит ячейку матча round robin"""
        style = f'style="width:{col_width}px;"'
        if match_result.get("is_bye"):
            return f'<div class="match-cell-bye-cell" {style}>●</div>'
        if match_result.get("has_result"):
            return f'''<div class="match-cell" {style}>
                <div class="match-score">{match_result.get("score", "-")}</div>
                <div class="match-sets">{match_result.get("sets", "")}</div>
            </div>'''
        return f'<div class="match-cell-empty-cell" {style}></div>'

    def _extract_rr_participants(self, group_data: Dict) -> List[Dict]:
        """Извлекает участников из групповых данных"""
        participants = []

        for row in group_data.get("Pool", []):
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
        half = len(participants) // 2
        return participants[:half] if half > 0 else participants

    def _parse_participant_cell(self, cell: Dict, fallback_index: int) -> Optional[Dict]:
        """Парсит ячейку участника"""
        players = cell.get("Players", [])
        if not isinstance(players, list):
            return None

        team_names = [p["Name"] for p in players if isinstance(p, dict) and p.get("Name")]
        if not team_names:
            return None

        full_name = "/".join(team_names)
        player_ids = [str(p["Id"]) for p in players if isinstance(p, dict) and p.get("Id")]

        return {
            "index": cell.get("Index", fallback_index),
            "participant_id": cell.get("ParticipantId"),
            "full_name": full_name,
            "short_name": self.create_short_name(full_name) if full_name != "Bye" else "Bye",
            "is_bye": full_name.upper() == "BYE",
            "player_ids": player_ids
        }

    def _extract_rr_matches_matrix(self, group_data: Dict, num_participants: int) -> Dict:
        """Извлекает матчи в формате матрицы"""
        matches_matrix = {}

        for row_idx, row in enumerate(group_data.get("Pool", [])):
            if not isinstance(row, list):
                continue
            for cell_idx, cell in enumerate(row):
                if not isinstance(cell, dict):
                    continue
                if cell.get("CellType") == "MatchCell" and cell.get("MatchCell"):
                    match_info = self._parse_match_cell(cell["MatchCell"])
                    if row_idx != cell_idx:
                        matches_matrix[f"{row_idx - 1}_{cell_idx - 1}"] = match_info

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

        bracket = elim_data["Elimination"]
        class_name = (xml_type_info.get("class_name", "Категория")).upper()
        stage_name = (xml_type_info.get("stage_name", "Плей-офф")).upper()

        rounds = self._analyze_elimination_structure(bracket)

        return self._render_elimination_html(class_name, stage_name, rounds)

    def _render_elimination_html(self, class_name: str, stage_name: str, rounds: List[Dict]) -> str:
        """Рендерит HTML elimination сетки"""
        html = f'''{self.html_head(f"{class_name} - {stage_name}", "elimination.css", 30000)}
<body>
    <div class="elimination-container">
        <div class="round-column">'''

        for round_idx, round_info in enumerate(rounds):
            if round_info.get('type') == 'participants':
                continue

            matches = self._generate_match_pairs_from_api(round_idx, round_info['matches'])
            html += '<div class="bracket-grid">'

            if round_idx == 1:
                html += f'<div class="places">{stage_name}</div>'

            for match in matches:
                html += self._render_elimination_match(match)

            html += '</div>'

        html += '''</div></div></body></html>'''
        return html

    def _render_elimination_match(self, match: Dict) -> str:
        """Рендерит один матч elimination"""
        score_parts = match['score'].split('-')
        score1 = score_parts[0] if score_parts else '0'
        score2 = score_parts[1] if len(score_parts) > 1 else '0'

        return f'''<div class="container">
            <div class="row row-top">
                <div class="names"><span class="name-main {match['secondary1']}">{match['team_1_name']}</span></div>
                <div class="score">{" ".join([f'<span class="set-score">{word}</span>' for word in match['sets1'].split()]) }</div>
                <div class="rank rank-top"><span class="rank-number">{score1}</span></div>
            </div>
            <div class="row row-bottom">
                <div class="names"><span class="name-main {match['secondary2']}">{match['team_2_name']}</span></div>
                <div class="score">{" ".join([f'<span class="set-score">{word}</span>' for word in match['sets2'].split()]) }</div>
                <div class="rank rank-bottom"><span class="rank-number">{score2}</span></div>
            </div>
        </div>'''

    def _analyze_elimination_structure(self, bracket: Dict) -> List[Dict]:
        """Анализирует структуру elimination для определения раундов"""
        rounds = []

        first_round = bracket.get("FirstRoundParticipantCells", [])
        if first_round:
            rounds.append({'title': 'Команды', 'matches': first_round, 'type': 'participants'})

        draw_data = bracket.get("DrawData")
        if not draw_data:
            return rounds

        matches_by_round = {}
        for round_matches in draw_data:
            for match in round_matches:
                if match:
                    rnd = match.get("Round", 1)
                    matches_by_round.setdefault(rnd, []).append(match)

        sorted_rounds = sorted(matches_by_round.keys())
        round_names = self._generate_round_names(len(sorted_rounds))

        for i, rnd in enumerate(sorted_rounds):
            rounds.append({
                'title': round_names[i] if i < len(round_names) else f'Раунд {rnd}',
                'matches': matches_by_round[rnd],
                'type': 'matches',
                'round_number': rnd
            })

        return rounds

    def _generate_round_names(self, num_rounds: int) -> List[str]:
        """Генерирует названия раундов"""
        names_map = {
            1: ['Финал'],
            2: ['Полуфинал', 'Финал'],
            3: ['Четвертьфинал', 'Полуфинал', 'Финал'],
            4: ['1/8 финала', 'Четвертьфинал', 'Полуфинал', 'Финал'],
            5: ['1/16 финала', '1/8 финала', 'Четвертьфинал', 'Полуфинал', 'Финал']
        }

        if num_rounds in names_map:
            return names_map[num_rounds]

        names = [f'Раунд {i + 1}' for i in range(num_rounds - 3)]
        names.extend(['Четвертьфинал', 'Полуфинал', 'Финал'])
        return names

    def _generate_match_pairs_from_api(self, round_index: int, matches: List[Dict]) -> List[Dict]:
        """Формирует пары матчей из API данных"""
        result = []

        for match in matches:
            vm = match.get("MatchViewModel", {})
            is_played = vm.get("IsPlayed", False)
            has_score = vm.get("HasScore", False)
            winner_id = match.get("WinnerParticipantId")

            challenger = match.get("ChallengerParticipant", {})
            challenged = match.get("ChallengedParticipant", {})

            team1 = self.get_team_name_from_players(challenger.get("FirstPlayer", {}), challenger.get("SecondPlayer", {}))
            team2 = self.get_team_name_from_players(challenged.get("FirstPlayer", {}), challenged.get("SecondPlayer", {}))

            team1_id = challenger.get("EventParticipantId")
            team2_id = challenged.get("EventParticipantId")

            info = {
                'team_1_name': self.create_short_name(team1) if team1 else 'TBD',
                'team_2_name': self.create_short_name(team2) if team2 else 'TBD',
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
                info['status'] = 'Сыгран'
                if winner_id == team1_id:
                    info['secondary2'] = 'lost'
                elif winner_id == team2_id:
                    info['secondary1'] = 'lost'

                score = vm.get("Score", {})
                
                # Определяем нужно ли менять местами счёт
                # FirstParticipantScore всегда относится к победителю
                # Если победитель - team2 (challenged), меняем местами
                first_score = score.get('FirstParticipantScore', 0)
                second_score = score.get('SecondParticipantScore', 0)
                
                if winner_id == team2_id:
                    # Победитель - team2, но FirstParticipantScore - счёт победителя
                    # Значит меняем местами
                    team1_total = second_score
                    team2_total = first_score
                else:
                    # Победитель - team1 или нет победителя
                    team1_total = first_score
                    team2_total = second_score
                
                info['score'] = f"{team1_total}-{team2_total}"
                
                # Тоже для детального счёта по сетам
                detailed = score.get("DetailedScoring", [])
                sets1_parts = []
                sets2_parts = []
                
                for s in detailed:
                    s_first = s.get('FirstParticipantScore', 0)
                    s_second = s.get('SecondParticipantScore', 0)
                    
                    if winner_id == team2_id:
                        sets1_parts.append(str(s_second))
                        sets2_parts.append(str(s_first))
                    else:
                        sets1_parts.append(str(s_first))
                        sets2_parts.append(str(s_second))
                
                info['sets1'] = ' '.join(sets1_parts)
                info['sets2'] = ' '.join(sets2_parts)

            elif is_played and not has_score:
                info['status'] = 'Walkover'
                if winner_id == team1_id:
                    info['secondary2'] = 'lost'
                    info['score'] = '1-0'
                    info['sets2'] = 'WO'
                elif winner_id == team2_id:
                    info['secondary1'] = 'lost'
                    info['score'] = '0-1'
                    info['sets1'] = 'WO'

            result.append(info)

        return result

    def _check_bye_advancement(self, match: Dict) -> Optional[Dict]:
        """Проверяет есть ли в матче Bye"""
        challenger = match.get("ChallengerParticipant", {})
        challenged = match.get("ChallengedParticipant", {})

        team1 = self.get_team_name_from_players(challenger.get("FirstPlayer", {}), challenger.get("SecondPlayer", {}))
        team2 = self.get_team_name_from_players(challenged.get("FirstPlayer", {}), challenged.get("SecondPlayer", {}))

        if team1.upper() == "BYE" or not team1.strip():
            if team2 and team2.upper() != "BYE":
                return {"team_name": team2, "participant_id": challenged.get("EventParticipantId")}
        elif team2.upper() == "BYE" or not team2.strip():
            if team1 and team1.upper() != "BYE":
                return {"team_name": team1, "participant_id": challenger.get("EventParticipantId")}

        return None

    def _generate_empty_elimination_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу elimination"""
        return self.empty_page_html("Турнирная сетка", message, "elimination.css")