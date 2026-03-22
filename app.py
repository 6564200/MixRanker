#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import time
from typing import Dict

from flask import Flask, jsonify, render_template

from config import get_config
from api import (
    RankedinAPI,
    init_database,
    register_auth_routes,
    AutoRefreshService,
    update_court_live_score,
)
from api.html_generator import HTMLGenerator
from api.rankedin_live import live_manager
from api.xml_generator import XMLFileManager
from api.display_windows import display_bp
from api.composite_pages import composite_bp
from api.blueprints import (
    create_tournaments_blueprint,
    create_files_blueprint,
    create_live_blueprint,
    create_settings_blueprint,
)


for d in ['logs', 'data', 'xml_files', 'api', 'static/css', 'static/js', 'templates', 'static/fonts', 'static/photos']:
    os.makedirs(d, exist_ok=True)

UPLOAD_FOLDER = 'static/photos'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/vmix_ranker.log'), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


api_client = RankedinAPI()
xml_manager = XMLFileManager('xml_files')
html_generator = HTMLGenerator()
auto_refresh = None
_services_started = False


def _register_core_routes(app: Flask):
    @app.after_request
    def set_secure_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response

    @app.route('/')
    def index():
        try:
            return render_template('index.html')
        except Exception:
            return '<html><body><h1>vMixRanker</h1></body></html>'

    @app.errorhandler(404)
    def not_found_error(_error):
        return jsonify({"error": "Не найдено"}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500


def _start_background_services(app: Flask):
    global auto_refresh, _services_started

    if _services_started:
        return

    _services_started = True

    auto_refresh = AutoRefreshService()
    auto_refresh.configure(app, api_client)
    auto_refresh.start()
    logger.info('AutoRefresh service started')

    def on_live_update(tournament_id: str, court_data: Dict):
        try:
            update_court_live_score(tournament_id, court_data)
            logger.debug(f"Live update: court {court_data.get('court_id')}")
        except Exception as e:
            logger.error(f'Live update error: {e}')

    live_manager.set_update_callback(on_live_update)
    live_manager.start()
    logger.info('LiveManager (WebSocket) service started')


def create_app():
    app = Flask(__name__)

    cfg = get_config()
    secret_key = getattr(cfg, 'SECRET_KEY', None)
    if not secret_key:
        raise RuntimeError('SECRET_KEY environment variable is required')
    app.secret_key = secret_key
    app.start_time = time.time()

    init_database()
    register_auth_routes(app)

    app.register_blueprint(display_bp)
    app.register_blueprint(composite_bp)

    app.register_blueprint(create_tournaments_blueprint(api_client, UPLOAD_FOLDER, logger))
    app.register_blueprint(create_files_blueprint(api_client, xml_manager))
    app.register_blueprint(create_live_blueprint(api_client, html_generator, live_manager, logger))
    app.register_blueprint(create_settings_blueprint(api_client, lambda: auto_refresh, lambda: app.start_time))

    _register_core_routes(app)
    _start_background_services(app)

    return app


if __name__ == '__main__':
    application = create_app()
    cfg = get_config()
    application.run(
        host=getattr(cfg, 'HOST', '0.0.0.0'),
        port=getattr(cfg, 'PORT', 5000),
        debug=getattr(cfg, 'DEBUG', False),
        threaded=True,
    )
