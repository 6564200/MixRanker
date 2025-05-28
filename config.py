#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация vMixRanker v2.5
"""

import os
from datetime import timedelta

class Config:
    """Базовая конфигурация"""
    
    # Flask настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vmix-ranker-v2-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST') or '0.0.0.0'
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # База данных
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'data/tournaments.db'
    
    # Rankedin API настройки
    RANKEDIN_API_BASE = "https://api.rankedin.com/v1"
    RANKEDIN_LIVE_API_BASE = "https://live.rankedin.com/api/v1"
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 10))  # секунды
    
    # Настройки обновления
    AUTO_REFRESH_INTERVAL = int(os.environ.get('AUTO_REFRESH_INTERVAL', 30))  # секунды
    AUTO_REFRESH_ENABLED = os.environ.get('AUTO_REFRESH_ENABLED', 'True').lower() == 'true'
    
    # Папки
    XML_OUTPUT_DIR = os.environ.get('XML_OUTPUT_DIR') or 'xml_files'
    LOGS_DIR = os.environ.get('LOGS_DIR') or 'logs'
    DATA_DIR = os.environ.get('DATA_DIR') or 'data'
    TEMPLATES_DIR = os.environ.get('TEMPLATES_DIR') or 'templates'
    
    # XML файлы
    XML_CLEANUP_HOURS = int(os.environ.get('XML_CLEANUP_HOURS', 24))  # часы
    MAX_XML_FILES_PER_TOURNAMENT = int(os.environ.get('MAX_XML_FILES_PER_TOURNAMENT', 50))
    
    # Логирование
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'vmix_ranker.log'
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Безопасность
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # Производительность
    MAX_TOURNAMENTS = int(os.environ.get('MAX_TOURNAMENTS', 100))
    MAX_COURTS_PER_TOURNAMENT = int(os.environ.get('MAX_COURTS_PER_TOURNAMENT', 20))
    
    # Кэширование
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))  # 5 минут
    
    @staticmethod
    def init_app(app):
        """Инициализация приложения с конфигурацией"""
        pass

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    AUTO_REFRESH_INTERVAL = 15  # Более частое обновление для разработки
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    
    # Проверка обязательных переменных окружения
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("Установите переменную окружения SECRET_KEY для продакшена")
    
    # Более консервативные настройки для продакшена
    AUTO_REFRESH_INTERVAL = 60  # Реже обновляем в продакшене
    API_TIMEOUT = 15  # Больший таймаут
    XML_CLEANUP_HOURS = 48  # Храним файлы дольше
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Настройка логирования для продакшена
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/vmix_ranker_prod.log',
                maxBytes=Config.LOG_MAX_SIZE,
                backupCount=Config.LOG_BACKUP_COUNT
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('vMixRanker Production startup')

class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # Используем in-memory базу для тестов
    AUTO_REFRESH_ENABLED = False
    XML_OUTPUT_DIR = 'test_xml_files'
    
    # Быстрые настройки для тестов
    API_TIMEOUT = 5
    AUTO_REFRESH_INTERVAL = 5

# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Получение текущей конфигурации на основе переменной окружения"""
    config_name = os.environ.get('FLASK_CONFIG') or 'default'
    return config[config_name]

# Настройки по умолчанию для приложения
DEFAULT_SETTINGS = {
    "refresh_interval": Config.AUTO_REFRESH_INTERVAL,
    "auto_refresh": Config.AUTO_REFRESH_ENABLED,
    "debug_mode": Config.DEBUG,
    "theme": "light",
    "xml_cleanup_hours": Config.XML_CLEANUP_HOURS,
    "max_tournaments": Config.MAX_TOURNAMENTS,
    "api_timeout": Config.API_TIMEOUT
}

# Спорты поддерживаемые rankedin.com
SUPPORTED_SPORTS = {
    1: {"name": "Tennis", "icon": "fa-tennis-ball"},
    2: {"name": "Squash", "icon": "fa-square"},
    3: {"name": "Badminton", "icon": "fa-shuttlecock"},
    4: {"name": "Table Tennis", "icon": "fa-ping-pong-paddle-ball"},
    5: {"name": "Padel", "icon": "fa-table-tennis-paddle-ball"},
    6: {"name": "Beach Tennis", "icon": "fa-volleyball"},
    7: {"name": "Pickle Ball", "icon": "fa-baseball"}
}

# Статусы турниров
TOURNAMENT_STATUSES = {
    "active": {"name": "Активный", "class": "success"},
    "finished": {"name": "Завершен", "class": "secondary"},
    "pending": {"name": "Ожидание", "class": "warning"},
    "error": {"name": "Ошибка", "class": "danger"}
}

# XML типы
XML_TYPES = {
    "tournament_table": {
        "name": "Турнирная таблица",
        "description": "Групповые этапы и игры на выбывание",
        "icon": "fa-table"
    },
    "schedule": {
        "name": "Расписание матчей",
        "description": "График игр по дням и времени",
        "icon": "fa-calendar"
    },
    "court_score": {
        "name": "Счет на корте",
        "description": "Текущий счет и информация о матче",
        "icon": "fa-scoreboard"
    }
}

# Страны (основные)
COUNTRIES = {
    1: "United States",
    7: "Canada",
    33: "France", 
    34: "Spain",
    39: "Italy",
    44: "United Kingdom",
    49: "Germany", 
    146: "Russia",
    # Добавить больше по необходимости
}