#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный модуль генерации HTML для vMix
Объединяет все специализированные HTML генераторы
"""

from typing import Dict, List
import logging
from .html_base import HTMLBase
from .scoreboard_html_generator import ScoreboardHTMLGenerator
from .match_pages_html_generator import MatchPagesHTMLGenerator
from .schedule_html_generator import ScheduleHTMLGenerator
from .tournament_tables_html_generator import TournamentTablesHTMLGenerator

logger = logging.getLogger(__name__)


class HTMLGenerator(HTMLBase):
    """Главный генератор HTML страниц для vMix"""
    
    def __init__(self):
        super().__init__()
        self.scoreboard = ScoreboardHTMLGenerator()
        self.match_pages = MatchPagesHTMLGenerator()
        self.schedule = ScheduleHTMLGenerator()
        self.tables = TournamentTablesHTMLGenerator()
    
    # ============= SCOREBOARD =============
    
    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует компактный scoreboard"""
        return self.scoreboard.generate_court_scoreboard_html(court_data, tournament_data)
    
    def generate_court_fullscreen_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует полноэкранный scoreboard"""
        return self.scoreboard.generate_court_fullscreen_scoreboard_html(court_data, tournament_data)
    
    # ============= MATCH PAGES =============
    
    def generate_court_vs_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует VS страницу"""
        return self.match_pages.generate_court_vs_html(court_data, tournament_data)
    
    def generate_vs_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует расширенную VS страницу"""
        return self.match_pages.generate_vs_page_html(court_data, id_url, tournament_data)
    
    def generate_winner_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует страницу победителя"""
        return self.match_pages.generate_winner_page_html(court_data, id_url, tournament_data)
    
    def generate_introduction_page_html(self, participant_info: Dict) -> str:
        """Генерирует страницу представления"""
        return self.match_pages.generate_introduction_page_html(participant_info)
    
    def generate_next_match_page_html(self, court_data: Dict, id_url: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует страницу следующего матча"""
        return self.match_pages.generate_next_match_page_html(court_data, id_url, tournament_data)
    
    # ============= SCHEDULE =============
    
    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует расписание (старая версия)"""
        return self.schedule.generate_schedule_html_new(tournament_data, target_date)
    
    def generate_schedule_html_new(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует расписание (новый дизайн)"""
        return self.schedule.generate_schedule_html_new(tournament_data, target_date)
    
    def generate_and_save_schedule_html(self, tournament_data: Dict, target_date: str = None) -> Dict:
        """Генерирует и сохраняет расписание"""
        return self.schedule.generate_and_save_schedule_html(tournament_data, target_date)
    
    # ============= TOURNAMENT TABLES =============
    
    def generate_round_robin_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML группового турнира"""
        return self.tables.generate_round_robin_html(tournament_data, xml_type_info)
    
    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML турнира на выбывание"""
        return self.tables.generate_elimination_html(tournament_data, xml_type_info)
