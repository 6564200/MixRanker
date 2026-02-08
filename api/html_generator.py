#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации HTML страниц для vMix
Фасад, объединяющий специализированные генераторы
"""

from typing import Dict, List
import logging

from .html_scoreboard import ScoreboardGenerator
from .html_scoreboard_full import ScoreboardFullGenerator
from .html_introduction import IntroductionGenerator
from .html_intro_player import IntroPlayerGenerator
from .html_vs import VSGenerator
from .html_winner import WinnerGenerator
from .html_schedule import ScheduleGenerator
from .html_round_robin import RoundRobinGenerator
from .html_elimination import EliminationGenerator

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """
    Главный генератор HTML страниц для vMix.
    Делегирует работу специализированным генераторам.
    """

    def __init__(self):
        self._scoreboard = ScoreboardGenerator()
        self._scoreboard_full = ScoreboardFullGenerator()
        self._introduction = IntroductionGenerator()
        self._intro_player = IntroPlayerGenerator()
        self._vs = VSGenerator()
        self._winner = WinnerGenerator()
        self._schedule = ScheduleGenerator()
        self._round_robin = RoundRobinGenerator()
        self._elimination = EliminationGenerator()

    # === Scoreboard методы ===

    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        return self._scoreboard.generate_court_scoreboard_html(court_data, tournament_data, tournament_id, court_id)

    def generate_scoreboard_full_html(self, court_data: Dict, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        return self._scoreboard_full.generate_scoreboard_full_html(court_data, tournament_data, tournament_id, court_id)

    def generate_smart_scoreboard_html(self, court_data: Dict, tournament_id: str, court_id: str) -> str:
        return self._scoreboard.generate_smart_scoreboard_html(court_data, tournament_id, court_id)

    def generate_court_fullscreen_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        return self._scoreboard.generate_court_fullscreen_scoreboard_html(court_data, tournament_data, tournament_id, court_id)

    def generate_next_match_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        return self._scoreboard.generate_next_match_page_html(court_data, id_url, tournament_data)

    # === Introduction методы ===

    def generate_introduction_page_html(self, participant_info: Dict, tournament_id: str = None) -> str:
        """Генерирует страницу представления игрока"""
        return self._intro_player.generate_introduction_page_html(participant_info, tournament_id)

    def generate_match_introduction_html(self, court_data: Dict, match_info: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        """Генерирует страницу представления матча"""
        return self._introduction.generate_match_introduction_html(court_data, match_info, tournament_id, court_id)

    # === VS методы ===

    def generate_court_vs_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        return self._vs.generate_court_vs_html(court_data, tournament_data)

    def generate_vs_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        return self._vs.generate_vs_page_html(court_data, id_url, tournament_data)

    def generate_winner_page_html(self, court_data: Dict, id_url: List[Dict] = None, tournament_data: Dict = None, tournament_id: str = None, court_id: str = None) -> str:
        return self._winner.generate_winner_page_html(court_data, id_url, tournament_data, tournament_id, court_id)

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

    def generate_round_robin_html(self, tournament_data: Dict, xml_type_info: Dict, tournament_id: str = None) -> str:
        return self._round_robin.generate_round_robin_html(tournament_data, xml_type_info, tournament_id)

    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        return self._elimination.generate_elimination_html(tournament_data, xml_type_info)

    def get_elimination_data(self, tournament_data: Dict, xml_type_info: Dict) -> Dict:
        """Получение данных elimination для AJAX"""
        return self._elimination.get_elimination_data(tournament_data, xml_type_info)
