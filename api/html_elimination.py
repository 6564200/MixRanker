#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML для Elimination (турнирных сеток на выбывание)
С поддержкой AJAX обновления без перезагрузки страницы
"""

from typing import Dict, List, Optional
from .html_base import HTMLBaseGenerator
import logging
import hashlib
import json

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
        tournament_id = tournament_data.get("metadata", {}).get("tournament_id", "")

        rounds = self._analyze_structure(bracket)
        
        # Версия для AJAX
        version = self._calculate_version(rounds)

        return self._render_html(tournament_id, class_id, draw_index, class_name, stage_name, rounds, version)

    def get_elimination_data(self, tournament_data: Dict, xml_type_info: Dict) -> Dict:
        """Возвращает данные elimination в формате JSON для AJAX"""
        class_id = xml_type_info.get("class_id")
        draw_index = xml_type_info.get("draw_index", 0)

        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        elimination_data = class_data.get("elimination", [])

        if draw_index >= len(elimination_data):
            return {"error": "Нет данных турнирной сетки", "matches": []}

        elim_data = elimination_data[draw_index]
        if not elim_data or "Elimination" not in elim_data:
            return {"error": "Неверные данные турнирной сетки", "matches": []}

        bracket = elim_data["Elimination"]
        rounds = self._analyze_structure(bracket)
        
        # Собираем все матчи в плоский список
        matches = []
        match_index = 0
        for round_idx, round_info in enumerate(rounds):
            if round_info.get('type') == 'participants':
                continue
            
            round_matches = self._generate_match_pairs(round_idx, round_info['matches'])
            for match in round_matches:
                match['match_id'] = f"match_{round_idx}_{match_index}"
                match['round_index'] = round_idx
                match['round_title'] = round_info.get('title', '')
                
                # Разбиваем score на части для удобства
                score_parts = match['score'].split('-')
                match['score1'] = score_parts[0] if score_parts else '0'
                match['score2'] = score_parts[1] if len(score_parts) > 1 else '0'
                
                matches.append(match)
                match_index += 1

        version = self._calculate_version(rounds)

        return {
            "class_id": class_id,
            "draw_index": draw_index,
            "matches": matches,
            "version": version
        }

    def _calculate_version(self, rounds: List[Dict]) -> str:
        """Вычисляет хеш версии данных для определения изменений"""
        data_str = json.dumps(rounds, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()[:8]

    def _render_html(self, tournament_id: str, class_id: str, draw_index: int,
                     class_name: str, stage_name: str, rounds: List[Dict], version: str) -> str:
        """Рендерит HTML elimination сетки с поддержкой AJAX"""
        
        # Генерируем HTML без авто-обновления (JS сделает это)
        html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1920, height=1080">
    <title>{class_name} - {stage_name}</title>
    <link rel="stylesheet" href="/static/css/elimination.css">
</head>
<body>
    <div class="elimination-container" 
         data-tournament-id="{tournament_id}"
         data-class-id="{class_id}"
         data-draw-index="{draw_index}"
         data-version="{version}">
        <div class="round-column">'''

        match_index = 0
        for round_idx, round_info in enumerate(rounds):
            if round_info.get('type') == 'participants':
                continue

            matches = self._generate_match_pairs(round_idx, round_info['matches'])
            html += '<div class="bracket-grid">'

            if round_idx == 1:
                html += f'<div class="places">{stage_name}</div>'

            for match in matches:
                match_id = f"match_{round_idx}_{match_index}"
                html += self._render_match(match, match_id)
                match_index += 1

            html += '</div>'

        html += '''</div>
    </div>
    <script src="/static/js/elimination_live.js"></script>
</body>
</html>'''
        return html

    def _render_match(self, match: Dict, match_id: str) -> str:
        """Рендерит один матч elimination с data-атрибутами для AJAX"""
        score_parts = match['score'].split('-')
        score1 = score_parts[0] if score_parts else '0'
        score2 = score_parts[1] if len(score_parts) > 1 else '0'

        sets1_html = " ".join([f'<span class="set-score">{word}</span>' for word in match.get('sets1', '').split() if word])
        sets2_html = " ".join([f'<span class="set-score">{word}</span>' for word in match.get('sets2', '').split() if word])

        return f'''<div class="container" data-match-id="{match_id}">
            <div class="row row-top">
                <div class="names"><span class="name-main {match.get('secondary1', '')}">{match.get('team_1_name', 'TBD')}</span></div>
                <div class="score">{sets1_html}</div>
                <div class="rank rank-top"><span class="rank-number">{score1}</span></div>
            </div>
            <div class="row row-bottom">
                <div class="names"><span class="name-main {match.get('secondary2', '')}">{match.get('team_2_name', 'TBD')}</span></div>
                <div class="score">{sets2_html}</div>
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
                'status': 'scheduled',
                'score': '0-0',
                'sets1': '',
                'sets2': '',
                'secondary1': '',
                'secondary2': ''
            }

            if is_played and has_score:
                info['status'] = 'finished'
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
                info['status'] = 'walkover'
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
