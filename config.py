#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ vMixRanker v2.5
"""

import os

class Config:
    """Р‘Р°Р·РѕРІР°СЏ РєРѕРЅС„РёРіСѓСЂР°С†РёСЏ"""
    
    # Flask РЅР°СЃС‚СЂРѕР№РєРё
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST') or '0.0.0.0'
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # Р‘Р°Р·Р° РґР°РЅРЅС‹С…
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'data/tournaments.db'
    
    # Rankedin API РЅР°СЃС‚СЂРѕР№РєРё
    RANKEDIN_API_BASE = "https://api.rankedin.com/v1"
    RANKEDIN_LIVE_API_BASE = "https://live.rankedin.com/api/v1"
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 10))  # СЃРµРєСѓРЅРґС‹
    
    # РќР°СЃС‚СЂРѕР№РєРё РѕР±РЅРѕРІР»РµРЅРёСЏ
    AUTO_REFRESH_INTERVAL = int(os.environ.get('AUTO_REFRESH_INTERVAL', 30))  # СЃРµРєСѓРЅРґС‹
    AUTO_REFRESH_ENABLED = os.environ.get('AUTO_REFRESH_ENABLED', 'True').lower() == 'true'
    
    # РџР°РїРєРё
    XML_OUTPUT_DIR = os.environ.get('XML_OUTPUT_DIR') or 'xml_files'
    LOGS_DIR = os.environ.get('LOGS_DIR') or 'logs'
    DATA_DIR = os.environ.get('DATA_DIR') or 'data'
    TEMPLATES_DIR = os.environ.get('TEMPLATES_DIR') or 'templates'
    
    # XML С„Р°Р№Р»С‹
    XML_CLEANUP_HOURS = int(os.environ.get('XML_CLEANUP_HOURS', 24))  # С‡Р°СЃС‹
    MAX_XML_FILES_PER_TOURNAMENT = int(os.environ.get('MAX_XML_FILES_PER_TOURNAMENT', 50))
    
    # Р›РѕРіРёСЂРѕРІР°РЅРёРµ
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'vmix_ranker.log'
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Р‘РµР·РѕРїР°СЃРЅРѕСЃС‚СЊ
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # РџСЂРѕРёР·РІРѕРґРёС‚РµР»СЊРЅРѕСЃС‚СЊ
    MAX_TOURNAMENTS = int(os.environ.get('MAX_TOURNAMENTS', 100))
    MAX_COURTS_PER_TOURNAMENT = int(os.environ.get('MAX_COURTS_PER_TOURNAMENT', 20))
    
    # РљСЌС€РёСЂРѕРІР°РЅРёРµ
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))  # 5 РјРёРЅСѓС‚
    
    @staticmethod
    def init_app(app):
        """РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ РїСЂРёР»РѕР¶РµРЅРёСЏ СЃ РєРѕРЅС„РёРіСѓСЂР°С†РёРµР№"""
        pass

class DevelopmentConfig(Config):
    """РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РґР»СЏ СЂР°Р·СЂР°Р±РѕС‚РєРё"""
    DEBUG = True
    AUTO_REFRESH_INTERVAL = 15  # Р‘РѕР»РµРµ С‡Р°СЃС‚РѕРµ РѕР±РЅРѕРІР»РµРЅРёРµ РґР»СЏ СЂР°Р·СЂР°Р±РѕС‚РєРё
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РґР»СЏ РїСЂРѕРґР°РєС€РµРЅР°"""
    DEBUG = False
    
    # Р‘РѕР»РµРµ РєРѕРЅСЃРµСЂРІР°С‚РёРІРЅС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё РґР»СЏ РїСЂРѕРґР°РєС€РµРЅР°
    AUTO_REFRESH_INTERVAL = 60  # Р РµР¶Рµ РѕР±РЅРѕРІР»СЏРµРј РІ РїСЂРѕРґР°РєС€РµРЅРµ
    API_TIMEOUT = 15  # Р‘РѕР»СЊС€РёР№ С‚Р°Р№РјР°СѓС‚
    XML_CLEANUP_HOURS = 48  # РҐСЂР°РЅРёРј С„Р°Р№Р»С‹ РґРѕР»СЊС€Рµ
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # РџСЂРѕРІРµСЂРєР° РѕР±СЏР·Р°С‚РµР»СЊРЅС‹С… РїРµСЂРµРјРµРЅРЅС‹С… РѕРєСЂСѓР¶РµРЅРёСЏ
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("РЈСЃС‚Р°РЅРѕРІРёС‚Рµ РїРµСЂРµРјРµРЅРЅСѓСЋ РѕРєСЂСѓР¶РµРЅРёСЏ SECRET_KEY РґР»СЏ РїСЂРѕРґР°РєС€РµРЅР°")
        
        # РќР°СЃС‚СЂРѕР№РєР° Р»РѕРіРёСЂРѕРІР°РЅРёСЏ РґР»СЏ РїСЂРѕРґР°РєС€РµРЅР°
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
    """РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РґР»СЏ С‚РµСЃС‚РёСЂРѕРІР°РЅРёСЏ"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # РСЃРїРѕР»СЊР·СѓРµРј in-memory Р±Р°Р·Сѓ РґР»СЏ С‚РµСЃС‚РѕРІ
    AUTO_REFRESH_ENABLED = False
    XML_OUTPUT_DIR = 'test_xml_files'
    
    # Р‘С‹СЃС‚СЂС‹Рµ РЅР°СЃС‚СЂРѕР№РєРё РґР»СЏ С‚РµСЃС‚РѕРІ
    API_TIMEOUT = 5
    AUTO_REFRESH_INTERVAL = 5

# РЎР»РѕРІР°СЂСЊ РєРѕРЅС„РёРіСѓСЂР°С†РёР№
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}

def get_config():
    """РџРѕР»СѓС‡РµРЅРёРµ С‚РµРєСѓС‰РµР№ РєРѕРЅС„РёРіСѓСЂР°С†РёРё РЅР° РѕСЃРЅРѕРІРµ РїРµСЂРµРјРµРЅРЅРѕР№ РѕРєСЂСѓР¶РµРЅРёСЏ"""
    config_name = os.environ.get('FLASK_CONFIG') or 'production'
    return config[config_name]

# РќР°СЃС‚СЂРѕР№РєРё РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ РґР»СЏ РїСЂРёР»РѕР¶РµРЅРёСЏ
DEFAULT_SETTINGS = {
    "refresh_interval": Config.AUTO_REFRESH_INTERVAL,
    "auto_refresh": Config.AUTO_REFRESH_ENABLED,
    "debug_mode": Config.DEBUG,
    "theme": "light",
    "xml_cleanup_hours": Config.XML_CLEANUP_HOURS,
    "max_tournaments": Config.MAX_TOURNAMENTS,
    "api_timeout": Config.API_TIMEOUT
}
