#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML для Elimination (турнирных сеток на выбывание)
"""

from typing import Dict, List
from .html_base import HTMLBaseGenerator
import logging

logger = logging.getLogger(__name__)


class EliminationGenerator(HTMLBaseGenerator):
    """Генератор турнирных сеток Elimination"""

    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для турнирной сетки на выбывание"""
        class_id = xml_type_info.get("class_id")
        draw_index = xml_type_info.get("draw_index", 0)

        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        elimination_data = class_data.get("elimination", [])

        if draw_index >= len(elimination_data):
            return self._generate_empty_html("Нет данных турнирной сетки")

        elim_data = elimination_data[draw_index]
        if not elim_data or "Elimination" not in elim_data:
            return self._generate_empty_html("Неверные данные турнирной сетки")

        bracket = elim_data["Elimination"]
        class_name = (xml_type_info.get("class_name", "Категория")).upper()
        stage_name = (xml_type_info.get("stage_name", "Плей-офф")).upper()

        rounds = self._analyze_structure(bracket)

        return self._render_html(class_name, stage_name, rounds)

    def _render_html(self, class_name: str, stage_name: str, rounds: List[Dict]) -> str:
        """Рендерит HTML elimination сетки"""
        html = f'''{self.html_head(f"{class_name} - {stage_name}", "elimination.css", 30000)}
<body>
    <div class="elimination-container">
        <div class="round-column">'''

        for round_idx, round_info in enumerate(rounds):
            if round_info.get('type') == 'participants':
                continue

            matches = self._generate_match_pairs(round_idx, round_info['matches'])
            html += '<div class="bracket-grid">'

            if round_idx == 1:
                html += f'<div class="places">{stage_name}</div>'

            for match in matches:
                html += self._render_match(match)

            html += '</div>'

        html += '''</div></div></body></html>'''
        return html

    def _render_match(self, match: Dict) -> str:
        """Рендерит один матч elimination"""
        score_parts = match['score'].split('-')
        score1 = score_parts[0] if score_parts else '0'
        score2 = score_parts[1] if len(score_parts) > 1 else '0'

        return f'''<div class="container">
            <div class="row row-top">
                <div class="names"><span class="name-main {match.get('secondary1', '')}">{match.get('team_1_name', 'TBD')}</span></div>
                <div class="score">{" ".join([f'<span class="set-score">{word}</span>' for word in match.get('sets1', '').split()])}</div>
                <div class="rank rank-top"><span class="rank-number">{score1}</span></div>
            </div>
            <div class="row row-bottom">
                <div class="names"><span class="name-main {match.get('secondary2', '')}">{match.get('team_2_name', 'TBD')}</span></div>
                <div class="score">{" ".join([f'<span class="set-score">{word}</span>' for word in match.get('sets2', '').split()])}</div>
                <div class="rank rank-bottom"><span class="rank-number">{score2}</span></div>
            </div>
        </div>'''

    def _generate_empty_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу"""
        return self.empty_page_html("Турнирная сетка", message, "elimination.css")

    def _analyze_structure(self, bracket: Dict) -> List[Dict]:
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

    def _generate_match_pairs(self, round_index: int, matches: List[Dict]) -> List[Dict]:
        """Формирует пары матчей из API данных"""
        result = []

        for match in matches:
            vm = match.get("MatchViewModel", {})
            is_played = vm.get("IsPlayed", False)
            has_score = vm.get("HasScore", False)
            winner_id = match.get("WinnerParticipantId")

            challenger = match.get("ChallengerParticipant", {})
            challenged = match.get("ChallengedParticipant", {})

            team1 = self.get_team_name_from_players(
                challenger.get("FirstPlayer", {}), 
                challenger.get("SecondPlayer", {})
            )
            team2 = self.get_team_name_from_players(
                challenged.get("FirstPlayer", {}), 
                challenged.get("SecondPlayer", {})
            )

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
                first_score = score.get('FirstParticipantScore', 0)
                second_score = score.get('SecondParticipantScore', 0)
                
                if winner_id == team2_id:
                    team1_total = second_score
                    team2_total = first_score
                else:
                    team1_total = first_score
                    team2_total = second_score
                
                info['score'] = f"{team1_total}-{team2_total}"
                
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
