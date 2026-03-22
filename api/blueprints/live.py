#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, Response

from api import (
    get_tournament_data,
    get_court_data,
    get_participant_info,
    get_photo_urls_for_ids,
    enrich_court_data_with_photos,
    require_auth,
)


def _find_current_match_info(tournament_data: dict, court_id: str, logger) -> dict:
    court_usage = tournament_data.get("court_usage", [])
    if not court_usage:
        return {}

    court_id_int = int(court_id) if str(court_id).isdigit() else 0
    now = datetime.now()
    court_matches = [m for m in court_usage if m.get("CourtId") == court_id_int]
    if not court_matches:
        return {}

    active_match = None
    next_match = None
    last_finished = None

    for match in court_matches:
        match_date_str = match.get("MatchDate", "")
        if not match_date_str:
            continue

        try:
            match_dt = datetime.fromisoformat(match_date_str.replace('Z', ''))
            duration = int(match.get("Duration", 30))
            match_end = match_dt + timedelta(minutes=duration)
            has_result = bool(match.get("ChallengerResult") or match.get("ChallengedResult"))

            if match_dt <= now and (now <= match_end or not has_result):
                if not has_result:
                    active_match = match
                    break
            elif match_dt > now and not has_result:
                if next_match is None:
                    next_match = match
                else:
                    next_dt = datetime.fromisoformat(next_match.get("MatchDate", "").replace('Z', ''))
                    if match_dt < next_dt:
                        next_match = match
            elif has_result:
                if last_finished is None:
                    last_finished = match
                else:
                    last_dt = datetime.fromisoformat(last_finished.get("MatchDate", "").replace('Z', ''))
                    if match_dt > last_dt:
                        last_finished = match
        except Exception as e:
            logger.debug(f"Ошибка парсинга даты матча: {e}")
            continue

    if active_match:
        return active_match
    if next_match:
        return next_match
    if last_finished:
        return last_finished
    return {}


def create_live_blueprint(api_client, html_generator, live_manager, logger):
    bp = Blueprint("live_bp", __name__)

    @bp.route('/api/html-live/<tournament_id>/<court_id>')
    def get_live_court_html(tournament_id, court_id):
        try:
            try:
                live_manager.subscribe_court(int(court_id))
            except Exception as e:
                logger.debug(f"WebSocket subscribe failed: {e}")

            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return "<html><body><h1>Турнир не найден</h1></body></html>", 404

            court_data = get_court_data(tournament_id, str(court_id))
            if not court_data or "error" in court_data:
                return "<html><body><h1>Корт не найден</h1></body></html>", 500

            html = html_generator.generate_court_scoreboard_html(court_data, tournament_data, tournament_id, court_id)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/score_full')
    def get_live_court_score_full_html(tournament_id, court_id):
        try:
            try:
                live_manager.subscribe_court(int(court_id))
            except Exception as e:
                logger.debug(f"WebSocket subscribe failed: {e}")

            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            html = html_generator.generate_scoreboard_full_html(court_data, tournament_data, tournament_id, court_id)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            logger.error(f"Ошибка генерации score_full: {e}")
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/court/<tournament_id>/<court_id>/data')
    def get_court_data_api(tournament_id, court_id):
        try:
            try:
                live_manager.touch(int(court_id))
            except Exception:
                pass

            court_data = get_court_data(tournament_id, str(court_id))
            if not court_data:
                return jsonify({"error": "Корт не найден"}), 404

            first_participant = court_data.get("first_participant", [])
            second_participant = court_data.get("second_participant", [])
            detailed_result = court_data.get("detailed_result", [])

            team1_score = court_data.get("first_participant_score", 0)
            team2_score = court_data.get("second_participant_score", 0)

            if detailed_result:
                last_set = detailed_result[-1]
                game_score = last_set.get("gameScore", {})
                if game_score:
                    team1_score = game_score.get("first", team1_score)
                    team2_score = game_score.get("second", team2_score)

            return jsonify({
                "team1_players": first_participant,
                "team2_players": second_participant,
                "detailed_result": detailed_result,
                "team1_score": team1_score,
                "team2_score": team2_score,
                "event_state": court_data.get("event_state", ""),
                "court_name": court_data.get("court_name", ""),
                "class_name": court_data.get("class_name", ""),
                "is_first_participant_serving": court_data.get("is_first_participant_serving"),
                "is_serving_left": court_data.get("is_serving_left"),
                "is_tiebreak": court_data.get("is_tiebreak", False),
                "is_super_tiebreak": court_data.get("is_super_tiebreak", False),
            })
        except Exception as e:
            logger.error(f"Ошибка получения данных корта: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/vs')
    def get_court_vs_html(tournament_id, court_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            court_data = enrich_court_data_with_photos(court_data)
            html = html_generator.generate_court_vs_html(court_data, tournament_data)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/introduction')
    def get_court_introduction_html(tournament_id, court_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            match_info = _find_current_match_info(tournament_data, court_id, logger)
            html = html_generator.generate_match_introduction_html(court_data, match_info)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            logger.error(f"Ошибка генерации introduction: {e}")
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/next')
    def get_next_match_html(tournament_id, court_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            next_ids = []
            for p in court_data.get("next_first_participant", []) + court_data.get("next_second_participant", []):
                if p.get("id"):
                    next_ids.append(p["id"])

            if next_ids:
                photo_map = get_photo_urls_for_ids(next_ids)
                for p in court_data.get("next_first_participant", []) + court_data.get("next_second_participant", []):
                    if p.get("id") in photo_map:
                        p["photo_url"] = photo_map[p["id"]]

            html = html_generator.generate_next_match_page_html(court_data, tournament_data)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/winner')
    def get_winner_page_html(tournament_id, court_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            court_data = enrich_court_data_with_photos(court_data)

            all_ids = [
                p.get("id")
                for p in court_data.get("first_participant", []) + court_data.get("second_participant", [])
                if p.get("id")
            ]
            id_url = [{"id": pid, "photo_url": court_data.get("first_participant", [{}])[0].get("photo_url") or court_data.get("second_participant", [{}])[0].get("photo_url")} for pid in all_ids]

            html = html_generator.generate_winner_page_html(court_data, id_url, tournament_data)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/participant/<participant_id>/introduction')
    def get_introduction_page_html(participant_id):
        try:
            participant = get_participant_info(int(participant_id))
            if not participant:
                return "<html><body><h1>Участник не найден</h1></body></html>", 404

            html = html_generator.generate_introduction_page_html(participant)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/schedule/<tournament_id>')
    def get_live_schedule_html(tournament_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return "<html><body><h1>Турнир не найден</h1></body></html>", 404

            target_date = request.args.get('date')
            from api import get_settings
            settings = get_settings()
            html = html_generator.generate_schedule_html(tournament_data, target_date, settings)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/schedule/<tournament_id>/data')
    def get_schedule_data(tournament_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            target_date = request.args.get('date')
            from api import get_settings
            settings = get_settings()

            schedule_data = html_generator.get_schedule_data(tournament_data, target_date, settings)
            data_str = json.dumps(schedule_data, sort_keys=True, default=str)
            version = hashlib.md5(data_str.encode()).hexdigest()[:12]

            return jsonify({
                "version": version,
                "tournament_name": schedule_data.get("tournament_name", ""),
                "target_date": schedule_data.get("target_date", ""),
                "time_slots": schedule_data.get("time_slots", []),
                "courts": schedule_data.get("courts", []),
                "matches": schedule_data.get("matches", []),
            })
        except Exception as e:
            logger.error(f"Ошибка получения данных расписания: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/html-live/round-robin/<tournament_id>/<class_id>/<int:draw_index>')
    def get_live_round_robin_html(tournament_id, class_id, draw_index):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return "<html><body><h1>Турнир не найден</h1></body></html>", 404

            xml_types = api_client.get_xml_data_types(tournament_data)
            xml_type_info = next((
                t for t in xml_types
                if t.get("type") == "tournament_table"
                and t.get("draw_type") == "round_robin"
                and t.get("class_id") == class_id
                and t.get("draw_index") == draw_index
            ), None)
            if not xml_type_info:
                return "<html><body><h1>Таблица не найдена</h1></body></html>", 404

            html = html_generator.generate_round_robin_html(tournament_data, xml_type_info)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            logger.error(f"Ошибка round-robin HTML: {e}")
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/elimination/<tournament_id>/<class_id>/<int:draw_index>')
    def get_live_elimination_html(tournament_id, class_id, draw_index):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return "<html><body><h1>Турнир не найден</h1></body></html>", 404

            xml_types = api_client.get_xml_data_types(tournament_data)
            xml_type_info = next((
                t for t in xml_types
                if t.get("type") == "tournament_table"
                and t.get("draw_type") == "elimination"
                and t.get("class_id") == class_id
                and t.get("draw_index") == draw_index
            ), None)
            if not xml_type_info:
                return "<html><body><h1>Сетка не найдена</h1></body></html>", 404

            html = html_generator.generate_elimination_html(tournament_data, xml_type_info)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            logger.error(f"Ошибка elimination HTML: {e}")
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/elimination/<tournament_id>/<class_id>/data')
    def get_elimination_data(tournament_id, class_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            draw_index = request.args.get('draw_index', 0, type=int)
            xml_types = api_client.get_xml_data_types(tournament_data)
            xml_type_info = next((
                t for t in xml_types
                if t.get("type") == "tournament_table"
                and t.get("draw_type") == "elimination"
                and t.get("class_id") == class_id
                and t.get("draw_index") == draw_index
            ), None)

            if not xml_type_info:
                return jsonify({"error": "Сетка не найдена", "matches": []}), 404

            elimination_data = html_generator.get_elimination_data(tournament_data, xml_type_info)
            return jsonify(elimination_data)
        except Exception as e:
            logger.error(f"Ошибка получения данных elimination: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/round-robin/<tournament_id>/<class_id>/<int:draw_index>/data')
    def get_round_robin_data(tournament_id, class_id, draw_index):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            xml_types = api_client.get_xml_data_types(tournament_data)
            xml_type_info = next((
                t for t in xml_types
                if t.get("type") == "tournament_table"
                and t.get("draw_type") == "round_robin"
                and t.get("class_id") == class_id
                and t.get("draw_index") == draw_index
            ), None)

            if not xml_type_info:
                return jsonify({"error": "Группа не найдена", "matches": {}, "standings": []}), 404

            rr_data = html_generator.get_round_robin_data(tournament_data, xml_type_info)
            return jsonify(rr_data)
        except Exception as e:
            logger.error(f"Ошибка получения данных round robin: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/live/subscribe/<int:court_id>', methods=['POST'])
    @require_auth
    def subscribe_live_court(court_id):
        try:
            success = live_manager.subscribe_court(court_id)
            return jsonify({"success": success, "court_id": court_id})
        except Exception as e:
            logger.error(f"Error subscribing to court {court_id}: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/live/unsubscribe/<int:court_id>', methods=['POST'])
    @require_auth
    def unsubscribe_live_court(court_id):
        try:
            live_manager.unsubscribe_court(court_id)
            return jsonify({"success": True, "court_id": court_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/live/subscriptions')
    def get_live_subscriptions():
        try:
            courts = live_manager.get_subscribed_courts()
            return jsonify({"courts": courts, "count": len(courts)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/live/subscribe/tournament/<tournament_id>', methods=['POST'])
    @require_auth
    def subscribe_tournament_courts(tournament_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            courts = tournament_data.get("courts", [])
            court_ids = [int(c.get("Item1")) for c in courts if c.get("Item1")]
            live_manager.subscribe_courts(court_ids)

            return jsonify({
                "success": True,
                "tournament_id": tournament_id,
                "courts_subscribed": court_ids,
            })
        except Exception as e:
            logger.error(f"Error subscribing tournament {tournament_id}: {e}")
            return jsonify({"error": str(e)}), 500

    return bp
