#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML страниц для vMix
Фасад, объединяющий специализированные генераторы
"""

from typing import Dict, List
import logging

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
        self._scoreboard = ScoreboardGenerator()
        self._vs = VSGenerator()
        self._schedule = ScheduleGenerator()
        self._bracket = TournamentBracketGenerator()

    # === Scoreboard методы ===

    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        return self._scoreboard.generate_court_scoreboard_html(court_data, tournament_data, tournament_id, court_id)

    def generate_smart_scoreboard_html(self, court_data: Dict, tournament_id: str, court_id: str) -> str:
        return self._scoreboard.generate_smart_scoreboard_html(court_data, tournament_id, court_id)

    def generate_court_fullscreen_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        return self._scoreboard.generate_court_fullscreen_scoreboard_html(court_data, tournament_data, tournament_id, court_id)

    def generate_next_match_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        return self._scoreboard.generate_next_match_page_html(court_data, id_url, tournament_data)

    def generate_introduction_page_html(self, participant_info: Dict) -> str:
        return self._scoreboard.generate_introduction_page_html(participant_info)

    # === VS методы ===

    def generate_court_vs_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        return self._vs.generate_court_vs_html(court_data, tournament_data)

    def generate_vs_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        return self._vs.generate_vs_page_html(court_data, id_url, tournament_data)

    def generate_winner_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        return self._vs.generate_winner_page_html(court_data, id_url, tournament_data)

    # === Schedule методы ===

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> str:
        return self._schedule.generate_schedule_html(tournament_data, target_date, settings)

    def generate_schedule_html_new(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> str:
        return self._schedule.generate_schedule_html_new(tournament_data, target_date, settings)

    def generate_schedule_html_addreality(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> str:
        return self._schedule.generate_schedule_html_addreality(tournament_data, target_date, settings)

    def get_schedule_data(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> Dict:
        return self._schedule.get_schedule_data(tournament_data, target_date, settings)

    # === Bracket методы ===

    def generate_round_robin_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        return self._bracket.generate_round_robin_html(tournament_data, xml_type_info)

    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        return self._bracket.generate_elimination_html(tournament_data, xml_type_info)
