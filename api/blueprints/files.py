#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from flask import Blueprint, jsonify, Response, send_from_directory
from werkzeug.exceptions import NotFound

from api import (
    get_tournament_data,
    save_xml_file_info,
    get_xml_type_description,
    get_update_frequency,
)


def create_files_blueprint(api_client, xml_manager):
    bp = Blueprint("files_bp", __name__)
    xml_dir = 'xml_files'

    def _is_allowed_filename(filename: str, allowed_ext: set[str]) -> bool:
        if not filename:
            return False
        if filename != os.path.basename(filename):
            return False
        if '.' not in filename:
            return False
        return filename.rsplit('.', 1)[1].lower() in allowed_ext

    @bp.route('/api/xml/<tournament_id>/<xml_type_id>')
    def generate_xml(tournament_id, xml_type_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            xml_types = api_client.get_xml_data_types(tournament_data)
            xml_type_info = next((t for t in xml_types if t["id"] == xml_type_id), None)
            if not xml_type_info:
                return jsonify({"error": "Неизвестный тип XML"}), 400

            if xml_type_info["type"] == "court_score":
                court_data = api_client.get_court_scoreboard(str(xml_type_info.get("court_id")))
                if "error" in court_data:
                    return jsonify({"error": "Ошибка получения данных корта"}), 500
                file_info = xml_manager.generate_and_save(xml_type_info, tournament_data, court_data)
            else:
                if xml_type_info["type"] == "tournament_table":
                    class_id = xml_type_info.get("class_id")
                    draw_type = xml_type_info.get("draw_type")

                    if draw_type == "round_robin":
                        fresh_data = api_client.get_all_draws_for_class(str(class_id)).get("round_robin", [])
                    elif draw_type == "elimination":
                        fresh_data = api_client.get_all_draws_for_class(str(class_id)).get("elimination", [])
                    else:
                        fresh_data = None

                    if fresh_data and tournament_data.get("draw_data", {}).get(str(class_id)):
                        if draw_type == "round_robin":
                            tournament_data["draw_data"][str(class_id)]["round_robin"] = fresh_data
                        elif draw_type == "elimination":
                            tournament_data["draw_data"][str(class_id)]["elimination"] = fresh_data

                file_info = xml_manager.generate_and_save(xml_type_info, tournament_data)

            save_xml_file_info(tournament_id, file_info)
            return jsonify(file_info)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/xml-live/<tournament_id>/<xml_type_id>')
    def get_live_xml_data(tournament_id, xml_type_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return Response("<!-- Турнир не найден -->", mimetype='application/xml'), 404

            xml_types = api_client.get_xml_data_types(tournament_data)
            xml_type_info = next((t for t in xml_types if t["id"] == xml_type_id), None)
            if not xml_type_info:
                return Response("<!-- Неизвестный тип -->", mimetype='application/xml'), 400

            if xml_type_info["type"] == "court_score":
                court_data = api_client.get_court_scoreboard(str(xml_type_info.get("court_id")))
                xml_content = xml_manager.xml_generator.generate_court_score_xml(court_data, tournament_data)
            elif xml_type_info["type"] == "tournament_table":
                xml_content = xml_manager.xml_generator.generate_tournament_table_xml(tournament_data, xml_type_info)
            else:
                return Response("<!-- Неподдерживаемый тип -->", mimetype='application/xml'), 400

            return Response(xml_content, mimetype='application/xml; charset=utf-8')
        except Exception as e:
            return Response(f"<!-- Ошибка: {e} -->", mimetype='application/xml'), 500

    @bp.route('/api/tournament/<tournament_id>/live-xml-info')
    def get_live_xml_info(tournament_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            xml_types = api_client.get_xml_data_types(tournament_data)
            live_xml_info = []
            for t in xml_types:
                info = {
                    "id": t["id"],
                    "name": t.get("name", t["id"]),
                    "type": t["type"],
                    "live_url": f"/api/xml-live/{tournament_id}/{t['id']}",
                    "description": get_xml_type_description(t.get("type", "")),
                    "update_frequency": get_update_frequency(t.get("type", "")),
                }
                if t["type"] == "tournament_table":
                    info["class_id"] = t.get("class_id")
                    info["class_name"] = t.get("class_name")
                    info["draw_type"] = t.get("draw_type")
                    info["draw_index"] = t.get("draw_index")
                    info["stage_name"] = t.get("stage_name", "")
                    info["group_name"] = t.get("group_name", "")
                elif t["type"] == "court_score":
                    info["court_id"] = t.get("court_id")
                    info["court_name"] = t.get("court_name")
                live_xml_info.append(info)

            return jsonify({
                "tournament_id": tournament_id,
                "tournament_name": tournament_data.get("metadata", {}).get("name", f"Турнир {tournament_id}"),
                "live_xml_count": len(live_xml_info),
                "live_xml_types": live_xml_info,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/xml/<filename>')
    def serve_xml_file(filename):
        if not _is_allowed_filename(filename, {'xml'}):
            return Response("<!-- Invalid filename -->", mimetype='application/xml'), 400
        try:
            return send_from_directory(xml_dir, filename, mimetype='application/xml')
        except NotFound:
            return Response("<!-- Файл не найден -->", mimetype='application/xml'), 404

    @bp.route('/html/<filename>')
    def serve_html_file(filename):
        if not _is_allowed_filename(filename, {'html', 'htm'}):
            return "<html><body><h1>Invalid filename</h1></body></html>", 400
        try:
            return send_from_directory(xml_dir, filename, mimetype='text/html')
        except NotFound:
            return "<html><body><h1>Файл не найден</h1></body></html>", 404

    return bp
