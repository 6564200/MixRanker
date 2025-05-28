#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API модуль для vMixRanker v2.5
Содержит интеграцию с rankedin.com и генерацию XML для vMix
"""

from .rankedin_api import RankedinAPI, fetch_tournament_data, get_court_ids, get_court_scores
from .xml_generator import XMLGenerator, XMLFileManager, generate_scoreboard_xml, generate_bracket_xml

__version__ = '2.5.0'
__author__ = 'vMixRanker Team'

__all__ = [
    'RankedinAPI',
    'XMLGenerator', 
    'XMLFileManager',
    'fetch_tournament_data',
    'get_court_ids',
    'get_court_scores',
    'generate_scoreboard_xml',
    'generate_bracket_xml'
]