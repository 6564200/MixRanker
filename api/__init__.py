#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vMixRanker API модуль v2.6
"""

__version__ = "2.6.1"

# Константы и утилиты
from .constants import (
    SPORTS, COUNTRIES, COUNTRIES_RU,
    XML_TYPE_DESCRIPTIONS, XML_UPDATE_FREQUENCIES,
    DEFAULT_RELOAD_INTERVAL,
    get_sport_name, get_country_name, get_country_name_ru,
    get_xml_type_description, get_update_frequency, get_uptime,
    COUNTRY_CODE_MAP,
    get_flag_url
)

# База данных
from .database import (
    get_db_connection, execute_with_retry, init_database,
    get_tournament_data, get_court_data, save_courts_data,
    save_xml_file_info, get_active_tournament_ids,
    get_court_ids_for_tournament, get_settings, save_settings,
    save_tournament_matches, get_tournament_matches,
    update_court_live_score
)

# Аутентификация
from .auth import require_auth, check_user_credentials, register_auth_routes

# Фоновое обновление
from .auto_refresh import AutoRefreshService

# Фото участников
from .photo_utils import (
    get_photo_urls_for_ids, extract_player_ids,
    enrich_players_with_photos, enrich_court_data_with_photos,
    get_participant_photo_url, get_participant_info
)

# API клиент
from .rankedin_api import RankedinAPI

# HTML генераторы
from .html_generator import HTMLGenerator
from .html_base import HTMLBaseGenerator
from .html_scoreboard import ScoreboardGenerator
from .html_vs import VSGenerator
from .html_schedule import ScheduleGenerator
from .html_introduction import IntroductionGenerator
from .html_intro_player import IntroPlayerGenerator
from .html_winner import WinnerGenerator
from .html_round_robin import RoundRobinGenerator
from .html_elimination import EliminationGenerator

__all__ = [
    '__version__',
    'SPORTS', 'COUNTRIES', 'COUNTRIES_RU',
    'XML_TYPE_DESCRIPTIONS', 'XML_UPDATE_FREQUENCIES',
    'DEFAULT_RELOAD_INTERVAL',
    'get_sport_name', 'get_country_name', 'get_country_name_ru',
    'get_xml_type_description', 'get_update_frequency', 'get_uptime',
    'get_db_connection', 'execute_with_retry', 'init_database',
    'get_tournament_data', 'get_court_data', 'save_courts_data',
    'save_xml_file_info', 'get_active_tournament_ids',
    'get_court_ids_for_tournament', 'get_settings', 'save_settings',
    'save_tournament_matches', 'get_tournament_matches',
    'require_auth', 'check_user_credentials', 'register_auth_routes',
    'AutoRefreshService',
    'get_photo_urls_for_ids', 'extract_player_ids',
    'enrich_players_with_photos', 'enrich_court_data_with_photos',
    'get_participant_photo_url', 'get_participant_info',
    'RankedinAPI',
    'HTMLGenerator', 'HTMLBaseGenerator',
    'ScoreboardGenerator', 'VSGenerator',
    'ScheduleGenerator', 'RoundRobinGenerator', 'EliminationGenerator',
    'COUNTRY_CODE_MAP',
    'get_flag_url',
]
