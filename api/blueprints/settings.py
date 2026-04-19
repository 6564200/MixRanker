#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from urllib.parse import quote
from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from api import (
    execute_with_retry,
    get_uptime,
    require_auth,
)


def create_settings_blueprint(api_client, get_auto_refresh, start_time_provider):
    bp = Blueprint("settings_bp", __name__)
    allowed_ext = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'}

    def _images_dir() -> str:
        return os.path.join(current_app.static_folder, 'images')

    def _is_allowed_image(name: str) -> bool:
        if not name:
            return False
        if name != os.path.basename(name):
            return False
        if '.' not in name:
            return False
        ext = name.rsplit('.', 1)[1].lower()
        return ext in allowed_ext

    @bp.route('/api/settings', methods=['GET', 'POST'])
    def manage_settings():
        from api import get_settings, save_settings

        if request.method == 'GET':
            return jsonify(get_settings())

        from flask import session
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'error': 'Authentication required', 'auth_required': True}), 401
        save_settings(request.get_json())
        return jsonify({"success": True})

    @bp.route('/api/status')
    def get_system_status():
        try:
            def get_counts(conn):
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM tournaments WHERE status = ?', ('active',))
                tournaments = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM courts_data')
                courts = cursor.fetchone()[0]
                return tournaments, courts

            tournaments, courts = execute_with_retry(get_counts)
            auto_refresh = get_auto_refresh()

            return jsonify({
                "status": "running",
                "uptime": get_uptime(start_time_provider()),
                "active_tournaments": tournaments,
                "courts_data_count": courts,
                "auto_refresh": auto_refresh.running if auto_refresh else False,
            })
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    @bp.route('/api/refresh')
    def refresh_all_data():
        try:
            from api import get_active_tournament_ids, get_court_ids_for_tournament, save_courts_data

            tournament_ids = get_active_tournament_ids()
            updated_courts = 0

            for tid in tournament_ids:
                court_ids = get_court_ids_for_tournament(tid)
                if court_ids:
                    courts_data = api_client.get_all_courts_data(court_ids)
                    if courts_data:
                        updated_courts += save_courts_data(tid, courts_data)

            return jsonify({
                "success": True,
                "updated_courts": updated_courts,
                "tournaments": len(tournament_ids),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/media/images', methods=['GET'])
    @require_auth
    def list_media_images():
        try:
            images_dir = _images_dir()
            os.makedirs(images_dir, exist_ok=True)
            items = []
            for name in os.listdir(images_dir):
                path = os.path.join(images_dir, name)
                if not os.path.isfile(path):
                    continue
                if not _is_allowed_image(name):
                    continue
                stat = os.stat(path)
                items.append({
                    "name": name,
                    "url": f"/static/images/{quote(name)}",
                    "size": stat.st_size,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            items.sort(key=lambda x: x["name"].lower())
            return jsonify(items)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/media/images', methods=['POST'])
    @require_auth
    def upload_media_image():
        try:
            images_dir = _images_dir()
            os.makedirs(images_dir, exist_ok=True)
            file = request.files.get('image') or request.files.get('file')
            if not file or not file.filename:
                return jsonify({"error": "No file provided"}), 400

            safe_name = secure_filename(file.filename)
            if not _is_allowed_image(safe_name):
                return jsonify({"error": "Unsupported image type"}), 400

            target = os.path.join(images_dir, safe_name)
            replaced = os.path.exists(target)
            file.save(target)
            return jsonify({
                "success": True,
                "name": safe_name,
                "url": f"/static/images/{quote(safe_name)}",
                "replaced": replaced
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/media/images/<filename>', methods=['DELETE'])
    @require_auth
    def delete_media_image(filename):
        try:
            images_dir = _images_dir()
            if not _is_allowed_image(filename):
                return jsonify({"error": "Invalid filename"}), 400
            target = os.path.join(images_dir, filename)
            if not os.path.isfile(target):
                return jsonify({"error": "File not found"}), 404
            os.remove(target)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/media/images/rename', methods=['POST'])
    @require_auth
    def rename_media_image():
        try:
            images_dir = _images_dir()
            data = request.get_json(silent=True) or {}
            old_name = data.get('old_name', '').strip()
            new_name = secure_filename(data.get('new_name', '').strip())

            if not _is_allowed_image(old_name) or not _is_allowed_image(new_name):
                return jsonify({"error": "Invalid filename"}), 400

            old_path = os.path.join(images_dir, old_name)
            new_path = os.path.join(images_dir, new_name)
            if not os.path.isfile(old_path):
                return jsonify({"error": "Source file not found"}), 404
            if os.path.exists(new_path):
                return jsonify({"error": "Target filename already exists"}), 409

            os.rename(old_path, new_path)
            return jsonify({
                "success": True,
                "name": new_name,
                "url": f"/static/images/{quote(new_name)}"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return bp
