#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML страниц для vMix
Фасад, объединяющий специализированные генераторы
"""

from typing import Dict, List, Any, Optional
import logging

from .html_base import HTMLBaseGenerator
from .html_scoreboard import ScoreboardGenerator
from .html_vs import VSGenerator
from .html_schedule import ScheduleGenerator
from .html_bracket import TournamentBracketGenerator

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """
    Главный генератор HTML страниц для vMix.
    Делегирует работу специализированным генераторам.
    """
    
    def __init__(self):
        self.auto_reload_interval = 30000
        self._scoreboard = ScoreboardGenerator()
        self._vs = VSGenerator()
        self._schedule = ScheduleGenerator()
        self._bracket = TournamentBracketGenerator()

    # === Scoreboard методы ===
    
    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует HTML страницу scoreboard для корта"""
        return self._scoreboard.generate_court_scoreboard_html(court_data, tournament_data)

    def generate_court_fullscreen_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует полноразмерную HTML страницу scoreboard"""
        return self._scoreboard.generate_court_fullscreen_scoreboard_html(court_data, tournament_data)

    def generate_next_match_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует страницу следующего матча"""
        return self._scoreboard.generate_next_match_page_html(court_data, id_url, tournament_data)

    def generate_introduction_page_html(self, participant_info: Dict) -> str:
        """Генерирует страницу представления участника"""
        return self._scoreboard.generate_introduction_page_html(participant_info)

    # === VS методы ===
    
    def generate_court_vs_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует VS страницу с фотографиями игроков"""
        return self._vs.generate_court_vs_html(court_data, tournament_data)

    def generate_vs_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует HTML VS-страницу текущего корта"""
        return self._vs.generate_vs_page_html(court_data, id_url, tournament_data)

    def generate_winner_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует HTML страницу победителей"""
        return self._vs.generate_winner_page_html(court_data, id_url, tournament_data)

    # === Schedule методы ===
    
    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей"""
        return self._schedule.generate_schedule_html(tournament_data, target_date)

    def generate_schedule_html_new(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания (новый дизайн)"""
        return self._schedule.generate_schedule_html_new(tournament_data, target_date)

    def generate_schedule_html_addreality(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания (Addreality дизайн)"""
        return self._schedule.generate_schedule_html_addreality(tournament_data, target_date)

    # === Bracket методы ===
    
    def generate_round_robin_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для групповой турнирной таблицы"""
        return self._bracket.generate_round_robin_html(tournament_data, xml_type_info)

    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для турнирной сетки на выбывание"""
        return self._bracket.generate_elimination_html(tournament_data, xml_type_info)

    # === Утилиты (для обратной совместимости) ===
    
    def _get_game_score_display(self, detailed_result: List[Dict], set_score: int, team: str) -> str:
        return HTMLBaseGenerator.get_game_score_display(detailed_result, set_score, team)

    def _get_match_status(self, match: Dict) -> str:
        return HTMLBaseGenerator.get_match_status(match)

    def _get_status_class(self, status: str) -> str:
        return HTMLBaseGenerator.get_status_class(status)

    def _get_team_name_from_players(self, first_player: Dict, second_player: Dict) -> str:
        return HTMLBaseGenerator.get_team_name_from_players(first_player, second_player)

    def _create_short_name(self, full_name: str) -> str:
        return HTMLBaseGenerator.create_short_name(full_name)

    def _format_score_summary(self, score_data: Dict) -> str:
        return HTMLBaseGenerator.format_score_summary(score_data)

    def _format_sets_summary(self, score_data: Dict) -> str:
        return HTMLBaseGenerator.format_sets_summary(score_data)

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        return self._schedule._generate_empty_schedule_html(tournament_name, message)

    def _generate_empty_round_robin_html(self, message: str) -> str:
        return self._bracket._generate_empty_round_robin_html(message)

    def _generate_empty_elimination_html(self, message: str) -> str:
        return self._bracket._generate_empty_elimination_html(message)

    # === RoundRobin вспомогательные (для обратной совместимости) ===
    
    def _extract_rr_participants(self, group_data: Dict) -> List[Dict]:
        return self._bracket._extract_rr_participants(group_data)

    def _extract_rr_matches_matrix(self, group_data: Dict, num_participants: int) -> Dict:
        return self._bracket._extract_rr_matches_matrix(group_data, num_participants)

    def _extract_rr_standings(self, group_data: Dict) -> List[Dict]:
        return self._bracket._extract_rr_standings(group_data)

    def _get_participant_place(self, participant: Dict, standings: List[Dict]) -> int:
        return self._bracket._get_participant_place(participant, standings)

    def _get_participant_points(self, participant: Dict, standings: List[Dict]) -> int:
        return self._bracket._get_participant_points(participant, standings)

    def _get_match_result_class(self, match_result: Dict) -> str:
        if match_result.get("is_bye"):
            return "bye"
        elif match_result.get("has_result"):
            return "played"
        return "empty"

    # === Elimination вспомогательные (для обратной совместимости) ===
    
    def _analyze_elimination_structure(self, bracket_data: Dict) -> List[Dict]:
        return self._bracket._analyze_elimination_structure(bracket_data)

    def _generate_round_names(self, num_rounds: int) -> List[str]:
        return self._bracket._generate_round_names(num_rounds)

    def _generate_first_round(self, bracket_data: Dict):
        return self._bracket._generate_first_round(bracket_data) if hasattr(self._bracket, '_generate_first_round') else {}

    def _generate_match_pairs_from_api(self, round_index: int, matches: List[Dict]) -> List[Dict]:
        return self._bracket._generate_match_pairs_from_api(round_index, matches)

    def _check_bye_advancement(self, match_data: Dict) -> Optional[Dict]:
        return self._bracket._check_bye_advancement(match_data)

    def _get_winner_player_names(self, match_data: Dict, winner_id: int) -> tuple:
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        if challenger_data.get("EventParticipantId") == winner_id:
            return (challenger_data.get("FirstPlayer", {}).get("Name", ""),
                    challenger_data.get("SecondPlayer", {}).get("Name", ""))
        elif challenged_data.get("EventParticipantId") == winner_id:
            return (challenged_data.get("FirstPlayer", {}).get("Name", ""),
                    challenged_data.get("SecondPlayer", {}).get("Name", ""))
        return ("", "")

    def _find_winner_team_name(self, match_data: Dict, winner_id: int) -> str:
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
