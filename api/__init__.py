#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vMixRanker API модуль v2.6
"""

__version__ = "2.6.0"

# Константы и утилиты
from .constants import (
    SPORTS, COUNTRIES, COUNTRIES_RU,
    XML_TYPE_DESCRIPTIONS, XML_UPDATE_FREQUENCIES,
    DEFAULT_RELOAD_INTERVAL,
    get_sport_name, get_country_name, get_country_name_ru,
    get_xml_type_description, get_update_frequency, get_uptime
)

# База данных
from .database import (
    get_db_connection, execute_with_retry, init_database,
    get_tournament_data, get_court_data, save_courts_data,
    save_xml_file_info, get_active_tournament_ids,
    get_court_ids_for_tournament, get_settings, save_settings
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
from .html_bracket import TournamentBracketGenerator

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
    'require_auth', 'check_user_credentials', 'register_auth_routes',
    'AutoRefreshService',
    'get_photo_urls_for_ids', 'extract_player_ids',
    'enrich_players_with_photos', 'enrich_court_data_with_photos',
    'get_participant_photo_url', 'get_participant_info',
    'RankedinAPI',
    'HTMLGenerator', 'HTMLBaseGenerator',
    'ScoreboardGenerator', 'VSGenerator',
    'ScheduleGenerator', 'TournamentBracketGenerator'
]
