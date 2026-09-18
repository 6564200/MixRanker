#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурация vMixRanker v2.5
"""

import os

class Config:

    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST') or '0.0.0.0'
    PORT = int(os.environ.get('FLASK_PORT', 5000))

    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'data/tournaments.db'

    RANKEDIN_API_BASE = "https://api.rankedin.com/v1"
    RANKEDIN_LIVE_API_BASE = "https://live.rankedin.com/api/v1"
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 10))  

    AUTO_REFRESH_INTERVAL = int(os.environ.get('AUTO_REFRESH_INTERVAL', 30))  
    AUTO_REFRESH_ENABLED = os.environ.get('AUTO_REFRESH_ENABLED', 'True').lower() == 'true'

    XML_OUTPUT_DIR = os.environ.get('XML_OUTPUT_DIR') or 'xml_files'
    LOGS_DIR = os.environ.get('LOGS_DIR') or 'logs'
    DATA_DIR = os.environ.get('DATA_DIR') or 'data'
    TEMPLATES_DIR = os.environ.get('TEMPLATES_DIR') or 'templates'

    XML_CLEANUP_HOURS = int(os.environ.get('XML_CLEANUP_HOURS', 24))  
    MAX_XML_FILES_PER_TOURNAMENT = int(os.environ.get('MAX_XML_FILES_PER_TOURNAMENT', 50))

    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'vmix_ranker.log'
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))

    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB

    MAX_TOURNAMENTS = int(os.environ.get('MAX_TOURNAMENTS', 100))
    MAX_COURTS_PER_TOURNAMENT = int(os.environ.get('MAX_COURTS_PER_TOURNAMENT', 20))

    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))  
    
    @staticmethod
    def init_app(app):
        """Инициализация приложения с конфигурацией"""
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    AUTO_REFRESH_INTERVAL = 15  
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    DEBUG = False
    AUTO_REFRESH_INTERVAL = 60  
    API_TIMEOUT = 15  
    XML_CLEANUP_HOURS = 48  
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("Установите переменную окружения SECRET_KEY для продакшена")
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
    TESTING = True
    DATABASE_PATH = ':memory:'  # Используем in-memory базу для тестов
    AUTO_REFRESH_ENABLED = False
    XML_OUTPUT_DIR = 'test_xml_files'
    API_TIMEOUT = 5
    AUTO_REFRESH_INTERVAL = 5


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}

def get_config():
    """Получение текущей конфигурации на основе переменной окружения"""
    config_name = os.environ.get('FLASK_CONFIG') or 'production'
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
