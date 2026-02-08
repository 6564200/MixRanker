#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API модуль для vMixRanker v2.5
Содержит интеграцию с rankedin.com и генерацию XML/HTML для vMix
"""

from .rankedin_api import RankedinAPI

# XML генераторы
from .xml_generator_new import XMLGenerator, generate_bracket_xml
from .xml_file_manager import XMLFileManager
from .xml_base import XMLBase
from .round_robin_generator import RoundRobinGenerator
from .elimination_generator import EliminationGenerator
from .schedule_generator import ScheduleGenerator
from .court_score_generator import CourtScoreGenerator

# HTML генераторы
from .html_generator_main import HTMLGenerator
from .html_base import HTMLBase as HTMLBaseClass
from .scoreboard_html_generator import ScoreboardHTMLGenerator
from .match_pages_html_generator import MatchPagesHTMLGenerator
from .schedule_html_generator import ScheduleHTMLGenerator
from .tournament_tables_html_generator import TournamentTablesHTMLGenerator

__version__ = '2.5.0'
__author__ = 'vMixRanker Team'

__all__ = [
    # API
    'RankedinAPI',
    
    # XML генераторы
    'XMLGenerator',
    'XMLFileManager',
    'generate_bracket_xml',
    'XMLBase',
    'RoundRobinGenerator',
    'EliminationGenerator',
    'ScheduleGenerator',
    'CourtScoreGenerator',
    
    # HTML генераторы
    'HTMLGenerator',
    'HTMLBaseClass',
    'ScoreboardHTMLGenerator',
    'MatchPagesHTMLGenerator',
    'ScheduleHTMLGenerator',
    'TournamentTablesHTMLGenerator',
]
