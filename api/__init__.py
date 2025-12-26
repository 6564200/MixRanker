#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API модуль для vMixRanker v2.5
Содержит интеграцию с rankedin.com и генерацию XML/HTML для vMix
"""

from .rankedin_api import RankedinAPI
from .xml_generator import XMLGenerator, XMLFileManager
from .html_generator import HTMLGenerator

# Субмодули HTML генератора
from .html_base import HTMLBaseGenerator
from .html_scoreboard import ScoreboardGenerator
from .html_vs import VSGenerator
from .html_schedule import ScheduleGenerator
from .html_bracket import TournamentBracketGenerator

__version__ = '2.5.0'
__author__ = 'vMixRanker Team'

__all__ = [
    'RankedinAPI',
    'XMLGenerator', 
    'XMLFileManager',
    'HTMLGenerator',
    'HTMLBaseGenerator',
    'ScoreboardGenerator',
    'VSGenerator',
    'ScheduleGenerator',
    'TournamentBracketGenerator',
]
