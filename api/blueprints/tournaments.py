#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from werkzeug.utils import secure_filename

from api import (
    require_auth,
    get_tournament_data,
    save_courts_data,
    execute_with_retry,
    save_tournament_matches,
    get_tournament_matches,
    get_sport_name,
    get_court_has_referee,
)
def _extract_players(team_data: dict) -> list:
    if not team_data:
        return []

    players = []
    name = team_data.get("Name", "")
    if name:
        parts = name.split()
        players.append({
            "firstName": parts[0] if parts else "",
            "lastName": " ".join(parts[1:]) if len(parts) > 1 else "",
            "countryCode": team_data.get("CountryShort", "")
        })

    name2 = team_data.get("Player2Name", "")
    if name2:
        parts = name2.split()
        players.append({
            "firstName": parts[0] if parts else "",
            "lastName": " ".join(parts[1:]) if len(parts) > 1 else "",
            "countryCode": team_data.get("Player2CountryShort", "")
        })

    return players


def _enrich_courts_with_next_match(courts_data: list, tournament_data: dict) -> list:
    court_usage = tournament_data.get("court_usage", [])
    matches_data = tournament_data.get("matches_data", {})
    matches_list = matches_data.get("Matches", []) if isinstance(matches_data, dict) else []
    matches_index = {m.get("Id"): m for m in matches_list}

    for court in courts_data:
        if "error" in court:
            continue

        court_id = int(court.get("court_id", 0))
        court_matches = [m for m in court_usage if m.get("CourtId") == court_id]

        pending_matches = []
        for match in court_matches:
            has_result = match.get("ChallengerResult") or match.get("ChallengedResult")
            if has_result:
                continue
            match_date_str = match.get("MatchDate", "")
            try:
                match_dt = datetime.fromisoformat(match_date_str.replace('Z', ''))
                pending_matches.append((match_dt, match))
            except (ValueError, TypeError):
                continue

        pending_matches.sort(key=lambda x: x[0])
        if pending_matches:
            next_match = pending_matches[0][1]
            challenge_id = next_match.get("ChallengeId")
            rich_match = matches_index.get(challenge_id, {})

            court["next_first_participant"] = _extract_players(rich_match.get("Challenger", {}))
            court["next_second_participant"] = _extract_players(rich_match.get("Challenged", {}))
            court["next_class_name"] = next_match.get("PoolName", "") or rich_match.get("Draw", "")
            court["next_start_time"] = next_match.get("MatchDate", "")

    return courts_data


def create_tournaments_blueprint(api_client, upload_folder: str, logger):
    bp = Blueprint("tournaments_bp", __name__)

    @bp.route('/api/tournament/<tournament_id>', methods=['POST'])
    @require_auth
    def load_tournament(tournament_id):
        try:
            tournament_data = api_client.get_full_tournament_data(tournament_id)
            if not tournament_data.get("metadata"):
                return jsonify({"success": False, "error": "Не удалось получить данные турнира"}), 400

            metadata = tournament_data.get("metadata", {})
            participants = tournament_data.get("participants", [])
            matches_data = api_client.get_tournament_matches(tournament_id)

            def save_transaction(conn):
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO tournaments 
                    (id, name, metadata, classes, courts, dates, draw_data, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    tournament_id, metadata.get("name", f"Турнир {tournament_id}"),
                    json.dumps(metadata), json.dumps(tournament_data.get("classes", [])),
                    json.dumps(tournament_data.get("courts", [])), json.dumps(tournament_data.get("dates", [])),
                    json.dumps(tournament_data.get("draw_data", {})), "active"
                ))
                cursor.execute('''
                    INSERT OR REPLACE INTO tournament_schedule 
                    (tournament_id, court_planner, court_usage, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (tournament_id, json.dumps(tournament_data.get("court_planner", {})),
                      json.dumps(tournament_data.get("court_usage", {}))))

                if matches_data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO tournament_matches 
                        (tournament_id, matches_data, are_matches_published, is_schedule_published, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        tournament_id,
                        json.dumps(matches_data.get("Matches", [])),
                        1 if matches_data.get("AreMatchesPublished") else 0,
                        1 if matches_data.get("IsSchedulePublished") else 0
                    ))

                if participants:
                    cursor.executemany('''
                        INSERT OR IGNORE INTO participants (id, rankedin_id, first_name, last_name, country_code)
                        VALUES (?, ?, ?, ?, ?)
                    ''', [(p.get("Id"), p.get("RankedinId"), p.get("FirstName"), p.get("LastName"), p.get("CountryShort")) for p in participants])
                    cursor.executemany('''
                        INSERT OR IGNORE INTO participants_tournaments (participant_id, tournament_id) VALUES (?, ?)
                    ''', [(p.get("Id"), tournament_id) for p in participants])

            execute_with_retry(save_transaction)
            logger.info(f"Турнир {tournament_id} загружен")

            return jsonify({
                "success": True, "tournament_id": tournament_id,
                "name": metadata.get("name"), "sport": get_sport_name(metadata.get("sport", 5)),
                "categories": len(tournament_data.get("classes", [])),
                "courts": len(tournament_data.get("courts", []))
            })
        except Exception as e:
            logger.error(f"Ошибка загрузки турнира {tournament_id}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/api/tournaments')
    def get_tournaments():
        try:
            def transaction(conn):
                cursor = conn.cursor()
                cursor.execute('SELECT id, name, metadata, status, created_at, updated_at FROM tournaments ORDER BY updated_at DESC')
                return [{
                    "id": r['id'], "name": r['name'], "status": r['status'],
                    "sport": json.loads(r['metadata']).get("sport", 5) if r['metadata'] else 5,
                    "created_at": r['created_at'], "updated_at": r['updated_at']
                } for r in cursor.fetchall()]
            return jsonify(execute_with_retry(transaction))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/tournament/<tournament_id>', methods=['DELETE'])
    @require_auth
    def delete_tournament(tournament_id):
        try:
            from api.composite_pages import delete_composite_pages_for_tournament
            delete_composite_pages_for_tournament(tournament_id)

            def transaction(conn):
                cursor = conn.cursor()
                cursor.execute('DELETE FROM courts_data WHERE tournament_id = ?', (tournament_id,))
                cursor.execute('DELETE FROM xml_files WHERE tournament_id = ?', (tournament_id,))
                cursor.execute('DELETE FROM tournament_schedule WHERE tournament_id = ?', (tournament_id,))
                cursor.execute('DELETE FROM tournament_matches WHERE tournament_id = ?', (tournament_id,))
                cursor.execute('DELETE FROM tournaments WHERE id = ?', (tournament_id,))
            execute_with_retry(transaction)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/tournament/<tournament_id>/courts')
    def get_tournament_courts(tournament_id):
        try:
            def get_court_ids(conn):
                cursor = conn.cursor()
                cursor.execute('SELECT courts FROM tournaments WHERE id = ?', (tournament_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    return [str(c.get("Item1")) for c in json.loads(row[0]) if c.get("Item1")]
                return []

            court_ids = execute_with_retry(get_court_ids)
            if not court_ids:
                return jsonify([])

            courts_data = api_client.get_all_courts_data(court_ids)
            if courts_data:
                save_courts_data(tournament_id, courts_data)

            tournament_data = get_tournament_data(tournament_id)
            if tournament_data:
                courts_data = _enrich_courts_with_next_match(courts_data, tournament_data)

            for court in courts_data:
                if "error" not in court:
                    court["has_referee"] = get_court_has_referee(tournament_id, str(court.get("court_id", "")))

            return jsonify(courts_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/tournament/<tournament_id>/xml-types')
    def get_xml_types(tournament_id):
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404
            return jsonify(api_client.get_xml_data_types(tournament_data))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/tournament/<tournament_id>/participants', methods=['GET', 'POST'])
    def manage_participants(tournament_id):
        try:
            if request.method == 'POST':
                if 'authenticated' not in session or not session['authenticated']:
                    return jsonify({'error': 'Authentication required', 'auth_required': True}), 401
                tournament_data = api_client.get_full_tournament_data(tournament_id)
                participants = tournament_data.get("participants", [])
                if participants:
                    def save(conn):
                        cursor = conn.cursor()
                        cursor.executemany('''
                            INSERT OR IGNORE INTO participants (id, rankedin_id, first_name, last_name, country_code)
                            VALUES (?, ?, ?, ?, ?)
                        ''', [(p.get("Id"), p.get("RankedinId"), p.get("FirstName"), p.get("LastName"), p.get("CountryShort")) for p in participants])
                        cursor.executemany('INSERT OR IGNORE INTO participants_tournaments VALUES (?, ?)',
                                          [(p.get("Id"), tournament_id) for p in participants])
                    execute_with_retry(save)

            def get_participants(conn):
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.* FROM participants p
                    JOIN participants_tournaments pt ON p.id = pt.participant_id
                    WHERE pt.tournament_id = ?
                ''', (tournament_id,))
                cols = [d[0] for d in cursor.description]
                return [dict(zip(cols, r)) for r in cursor.fetchall()]

            return jsonify(execute_with_retry(get_participants))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/participants/upload-photo', methods=['POST'])
    @require_auth
    def upload_participant_photo():
        from PIL import Image

        participant_id = request.form.get('participant_id')
        if not participant_id:
            return jsonify({"success": False, "error": "Не указан ID участника"}), 400

        info = json.dumps({
            'country': request.form.get('country', ''),
            'rating': request.form.get('rating', ''),
            'height': request.form.get('height', ''),
            'position': request.form.get('position', ''),
            'full_name': request.form.get('english', '')
        })

        filename = f"{secure_filename(participant_id)}.png"
        filepath = os.path.join(upload_folder, filename)
        preview_url = f"/{upload_folder}/{filename}"

        photo_saved = False
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename:
                try:
                    crop_x = float(request.form.get('crop_x', 0))
                    crop_y = float(request.form.get('crop_y', 0))
                    crop_scale = float(request.form.get('crop_scale', 1.0))
                    output_width = 1500
                    output_height = 2048
                    img = Image.open(file)
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    scaled_width = int(img.width * crop_scale)
                    scaled_height = int(img.height * crop_scale)
                    if scaled_width > 0 and scaled_height > 0:
                        img_scaled = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                    else:
                        img_scaled = img
                    canvas = Image.new('RGBA', (output_width, output_height), (0, 0, 0, 0))
                    canvas.paste(img_scaled, (int(crop_x), int(crop_y)), img_scaled)
                    canvas.save(filepath, 'PNG', optimize=True)
                    photo_saved = True
                except Exception as e:
                    logger.error(f"Image process error: {e}")
                    try:
                        file.seek(0)
                        with open(filepath, 'wb') as f:
                            f.write(file.read())
                        photo_saved = True
                    except Exception as e2:
                        logger.error(f"Image fallback save error: {e2}")

        def update(conn):
            cursor = conn.cursor()
            if photo_saved:
                cursor.execute('UPDATE participants SET photo_url = ?, info = ? WHERE id = ?', (preview_url, info, participant_id))
            else:
                cursor.execute('UPDATE participants SET info = ? WHERE id = ?', (info, participant_id))

        execute_with_retry(update)
        return jsonify({"success": True, "preview_url": preview_url if photo_saved else None})

    @bp.route('/api/tournament/<tournament_id>/schedule/reload', methods=['POST'])
    @require_auth
    def reload_tournament_schedule(tournament_id):
        try:
            def get_dates(conn):
                cursor = conn.cursor()
                cursor.execute('SELECT dates FROM tournaments WHERE id = ? AND status = ?', (tournament_id, 'active'))
                r = cursor.fetchone()
                return json.loads(r[0]) if r and r[0] else []

            dates = execute_with_retry(get_dates)
            if not dates:
                return jsonify({"error": "Турнир не найден"}), 400

            court_planner = api_client.get_court_planner(tournament_id, dates)
            court_usage = api_client.get_court_usage(tournament_id, dates)

            def save(conn):
                conn.cursor().execute('''
                    UPDATE tournament_schedule SET court_planner = ?, court_usage = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE tournament_id = ?
                ''', (json.dumps(court_planner or {}), json.dumps(court_usage or {}), tournament_id))
            execute_with_retry(save)

            return jsonify({"success": True, "matches_count": len(court_usage) if isinstance(court_usage, list) else 0})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/tournament/<tournament_id>/matches', methods=['GET'])
    def get_matches(tournament_id):
        try:
            matches_data = get_tournament_matches(tournament_id)
            if not matches_data:
                return jsonify({"Matches": [], "AreMatchesPublished": False, "IsSchedulePublished": False})
            return jsonify(matches_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/tournament/<tournament_id>/matches/reload', methods=['POST'])
    @require_auth
    def reload_tournament_matches(tournament_id):
        try:
            matches_data = api_client.get_tournament_matches(tournament_id)
            if not matches_data:
                return jsonify({"error": "Не удалось получить матчи"}), 400

            save_tournament_matches(tournament_id, matches_data)
            matches_count = len(matches_data.get("Matches", []))
            return jsonify({"success": True, "matches_count": matches_count})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return bp
