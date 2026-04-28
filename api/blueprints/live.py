#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, Response

from api import (
    get_tournament_data,
    get_court_data,
    get_participant_info,
    get_photo_urls_for_ids,
    enrich_court_data_with_photos,
    require_auth,
    get_court_has_referee,
    set_court_has_referee,
)


def _find_current_match_info(tournament_data: dict, court_id: str, logger) -> dict:
    """
    Определяет наиболее актуальный матч на корте из расписания (court_usage).
    Приоритет выбора:
      1. active_match  — матч в пределах своего временного окна без результата,
      2. next_match    — ближайший будущий матч без результата,
      3. last_finished — последний завершённый матч (с результатом).
    Возвращает словарь матча или пустой dict, если матчей нет.
    """
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


def _get_next_match_participants(tournament_data: dict, court_id: str) -> dict:
    """
    Возвращает участников ближайшего запланированного (незавершённого) матча на корте.
    Ищет матч в court_usage по court_id, сортирует незавершённые по дате и берёт первый.
    Дополняет данные из matches_data (полные имена, страна) через ChallengeId.
    Переводит тип сетки ('RoundRobin'/'Elimination') в русское название.
    Возвращает словарь с ключами: next_first_participant, next_second_participant,
    next_class_name, next_start_time. При отсутствии матча возвращает пустой dict.
    """
    court_usage = tournament_data.get("court_usage", [])
    matches_data = tournament_data.get("matches_data", {})
    matches_list = matches_data.get("Matches", []) if isinstance(matches_data, dict) else []
    matches_index = {m.get("Id"): m for m in matches_list}

    court_id_int = int(court_id) if str(court_id).isdigit() else 0
    court_matches = [m for m in court_usage if m.get("CourtId") == court_id_int]

    pending = []
    for match in court_matches:
        if match.get("ChallengerResult") or match.get("ChallengedResult"):
            continue
        date_str = match.get("MatchDate", "")
        try:
            pending.append((datetime.fromisoformat(date_str.replace('Z', '')), match))
        except (ValueError, TypeError):
            continue

    if not pending:
        return {}

    pending.sort(key=lambda x: x[0])
    next_match = pending[0][1]
    rich_match = matches_index.get(next_match.get("ChallengeId"), {})

    def extract_players(team_data: dict) -> list:
        """Формирует список игроков команды из данных court_usage (Name/Player2Name)."""
        if not team_data:
            return []
        players = []
        for name_key, country_key in [("Name", "CountryShort"), ("Player2Name", "Player2CountryShort")]:
            name = team_data.get(name_key, "")
            if not name:
                continue
            parts = name.split()
            first = parts[0] if parts else ""
            last = " ".join(parts[1:]) if len(parts) > 1 else ""
            initial_last = f"{first[0]}. {last}" if first else last
            players.append({
                "firstName": first,
                "lastName": last,
                "fullName": name,
                "initialLastName": initial_last,
                "countryCode": team_data.get(country_key, ""),
            })
        return players

    _DRAW_TYPE_LABELS = {"RoundRobin": "Групповой", "Elimination": "Плей-офф"}

    raw_class = next_match.get("PoolName", "") or rich_match.get("Draw", "")
    next_class_name = _DRAW_TYPE_LABELS.get(raw_class, raw_class)

    return {
        "next_first_participant": extract_players(rich_match.get("Challenger", {})),
        "next_second_participant": extract_players(rich_match.get("Challenged", {})),
        "next_class_name": next_class_name,
        "next_start_time": next_match.get("MatchDate", ""),
    }


def _apply_no_referee_mode(court_data: dict) -> dict:
    """
    Переключает корт в режим «без судьи» (has_referee=False).
    Заменяет текущих участников и класс на данные следующего матча,
    обнуляет счёт и флаги тай-брейка/подачи, очищает event_state.
    Используется, когда судья ещё не зафиксировал старт матча —
    на экране показывается анонс следующей пары, а не пустой корт.
    """
    court_data = dict(court_data)
    court_data["first_participant"] = court_data.get("next_first_participant", [])
    court_data["second_participant"] = court_data.get("next_second_participant", [])
    next_class = court_data.get("next_class_name", "")
    if next_class:
        court_data["class_name"] = next_class
    court_data["first_participant_score"] = 0
    court_data["second_participant_score"] = 0
    court_data["detailed_result"] = []
    court_data["is_tiebreak"] = False
    court_data["is_super_tiebreak"] = False
    court_data["is_first_participant_serving"] = None
    court_data["event_state"] = ""
    return court_data


def create_live_blueprint(api_client, html_generator, live_manager, logger):
    """
    Фабрика Flask Blueprint со всеми live-маршрутами.
    Принимает зависимости через параметры (dependency injection):
      api_client     — клиент rankedin API (для get_xml_data_types),
      html_generator — генератор HTML-страниц (scoreboard, vs, schedule и т.п.),
      live_manager   — менеджер WebSocket-подписок на корты,
      logger         — логгер модуля.
    Возвращает зарегистрированный Blueprint 'live_bp'.
    """
    bp = Blueprint("live_bp", __name__)

    @bp.route('/api/html-live/<tournament_id>/<court_id>')
    def get_live_court_html(tournament_id, court_id):
        """
        Основная страница табло корта (scoreboard).
        Подписывает корт на live-обновления через WebSocket.
        В режиме без судьи показывает следующий матч вместо текущего.
        """
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

            if not get_court_has_referee(tournament_id, str(court_id)):
                next_data = _get_next_match_participants(tournament_data, court_id)
                court_data.update(next_data)
                court_data = _apply_no_referee_mode(court_data)

            html = html_generator.generate_court_scoreboard_html(court_data, tournament_data, tournament_id, court_id)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/score_full')
    def get_live_court_score_full_html(tournament_id, court_id):
        """
        Расширенная страница счёта с фотографиями игроков.
        Обогащает данные корта фото через enrich_court_data_with_photos.
        В режиме без судьи показывает следующий матч.
        """
        try:
            try:
                live_manager.subscribe_court(int(court_id))
            except Exception as e:
                logger.debug(f"WebSocket subscribe failed: {e}")

            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            if not get_court_has_referee(tournament_id, str(court_id)):
                next_data = _get_next_match_participants(tournament_data, court_id)
                court_data.update(next_data)
                court_data = _apply_no_referee_mode(court_data)

            court_data = enrich_court_data_with_photos(court_data)
            html = html_generator.generate_scoreboard_full_html(court_data, tournament_data, tournament_id, court_id)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            logger.error(f"Ошибка генерации score_full: {e}")
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/court/<tournament_id>/<court_id>/data')
    def get_court_data_api(tournament_id, court_id):
        """
        JSON-данные корта для AJAX-опроса (счёт, участники, подача, тай-брейк).
        Обновляет касание live_manager (touch) для удержания WebSocket-соединения.
        Если есть detailed_result — в team1_score/team2_score возвращает текущий
        счёт внутри гейма (gameScore), а не только счёт по сетам.
        В режиме без судьи подставляет следующий матч.
        """
        try:
            try:
                live_manager.touch(int(court_id))
            except Exception:
                pass

            court_data = get_court_data(tournament_id, str(court_id))
            if not court_data:
                return jsonify({"error": "Корт не найден"}), 404

            if not get_court_has_referee(tournament_id, str(court_id)):
                tournament_data = get_tournament_data(tournament_id)
                if tournament_data:
                    next_data = _get_next_match_participants(tournament_data, court_id)
                    court_data.update(next_data)
                court_data = _apply_no_referee_mode(court_data)

            court_data = enrich_court_data_with_photos(court_data)

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
        """
        Страница анонса матча «VS» с именами и фотографиями игроков.
        В режиме без судьи показывает следующий матч.
        """
        try:
            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            if not get_court_has_referee(tournament_id, str(court_id)):
                next_data = _get_next_match_participants(tournament_data, court_id)
                court_data.update(next_data)
                court_data = _apply_no_referee_mode(court_data)

            court_data = enrich_court_data_with_photos(court_data)
            html = html_generator.generate_court_vs_html(
                court_data, tournament_data, tournament_id, court_id
            )
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/court/<tournament_id>/<court_id>/vs-data')
    def get_court_vs_data(tournament_id, court_id):
        """
        JSON-данные для AJAX-обновления страницы VS.
        Возвращает имена (uppercase) и фото всех 4 игроков (2 команды × 2),
        а также счёт до 3 сетов (firstParticipantScore/secondParticipantScore).
        В режиме без судьи подставляет следующий матч.
        """
        try:
            court_data = get_court_data(tournament_id, str(court_id))
            if not court_data:
                return jsonify({"error": "Корт не найден"}), 404

            if not get_court_has_referee(tournament_id, str(court_id)):
                tournament_data = get_tournament_data(tournament_id)
                if tournament_data:
                    next_data = _get_next_match_participants(tournament_data, court_id)
                    court_data.update(next_data)
                court_data = _apply_no_referee_mode(court_data)

            court_data = enrich_court_data_with_photos(court_data)

            team1 = court_data.get("first_participant", [])
            team2 = court_data.get("second_participant", [])
            detailed = court_data.get("detailed_result", [])

            def player_name(player):
                """Возвращает имя игрока в верхнем регистре (fullName или firstName+lastName)."""
                if not player:
                    return ""
                full = player.get("fullName", "")
                if full:
                    return full.upper()
                return f"{player.get('firstName', '')} {player.get('lastName', '')}".strip().upper()

            def photo_url(player):
                """Возвращает URL фото игрока или пустую строку."""
                return player.get("photo_url", "") if player else ""

            def set_score(idx, key):
                """Возвращает счёт сета с индексом idx по ключу key или пустую строку."""
                if idx < len(detailed):
                    return detailed[idx].get(key, "")
                return ""

            return jsonify({
                "team1_player1": player_name(team1[0] if team1 else None),
                "team1_player2": player_name(team1[1] if len(team1) > 1 else None),
                "team2_player1": player_name(team2[0] if team2 else None),
                "team2_player2": player_name(team2[1] if len(team2) > 1 else None),
                "team1_photo1": photo_url(team1[0] if team1 else None),
                "team1_photo2": photo_url(team1[1] if len(team1) > 1 else None),
                "team2_photo1": photo_url(team2[0] if team2 else None),
                "team2_photo2": photo_url(team2[1] if len(team2) > 1 else None),
                "set1_score1": set_score(0, "firstParticipantScore"),
                "set1_score2": set_score(0, "secondParticipantScore"),
                "set2_score1": set_score(1, "firstParticipantScore"),
                "set2_score2": set_score(1, "secondParticipantScore"),
                "set3_score1": set_score(2, "firstParticipantScore"),
                "set3_score2": set_score(2, "secondParticipantScore"),
            })
        except Exception as e:
            logger.error(f"Ошибка vs-data: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/introduction')
    def get_court_introduction_html(tournament_id, court_id):
        """
        Страница представления игроков перед матчем.
        Определяет актуальный матч через _find_current_match_info (active → next → last).
        В режиме без судьи показывает следующий матч.
        """
        try:
            tournament_data = get_tournament_data(tournament_id)
            court_data = get_court_data(tournament_id, str(court_id))
            if not tournament_data or not court_data:
                return "<html><body><h1>Не найдено</h1></body></html>", 404

            match_info = _find_current_match_info(tournament_data, court_id, logger)

            if not get_court_has_referee(tournament_id, str(court_id)):
                next_data = _get_next_match_participants(tournament_data, court_id)
                court_data.update(next_data)
                court_data = _apply_no_referee_mode(court_data)

            court_data = enrich_court_data_with_photos(court_data)
            html = html_generator.generate_match_introduction_html(court_data, match_info)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            logger.error(f"Ошибка генерации introduction: {e}")
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/html-live/<tournament_id>/<court_id>/next')
    def get_next_match_html(tournament_id, court_id):
        """
        Страница анонса следующего матча на корте.
        Загружает фотографии игроков следующего матча по их id и встраивает в court_data.
        """
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
        """
        Страница победителя завершённого матча.
        Обогащает данные фотографиями обоих участников и передаёт в generate_winner_page_html.
        """
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
        """
        Персональная страница представления одного участника турнира.
        Загружает данные участника по id и генерирует HTML через generate_introduction_page_html.
        """
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
        """
        GET /api/html-live/schedule/<tournament_id>[?date=DD.MM.YYYY]
        HTML-страница расписания матчей турнира на все корты.
        Опциональный параметр date задаёт дату; по умолчанию — сегодня.
        """
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

    @bp.route('/api/html-live/schedule/<tournament_id>/half/<int:half_num>')
    def get_live_schedule_half_html(tournament_id, half_num):
        """
        GET /api/html-live/schedule/<tournament_id>/half/<half_num>[?date=DD.MM.YYYY]
        HTML-страница расписания для половины кортов турнира (half_num: 1 или 2).
        Используется при разбивке расписания на два экрана. 400 при неверном half_num.
        """
        try:
            if half_num not in (1, 2):
                return "<html><body><h1>Неверный номер половины (1 или 2)</h1></body></html>", 400
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return "<html><body><h1>Турнир не найден</h1></body></html>", 404

            target_date = request.args.get('date')
            from api import get_settings
            settings = get_settings()
            html = html_generator.generate_schedule_half_html(tournament_data, half_num, target_date, settings)
            return Response(html, mimetype='text/html; charset=utf-8')
        except Exception as e:
            return f"<html><body><h1>Ошибка: {e}</h1></body></html>", 500

    @bp.route('/api/schedule/<tournament_id>/data')
    def get_schedule_data(tournament_id):
        """
        GET /api/schedule/<tournament_id>/data[?date=DD.MM.YYYY&half=1|2]
        JSON-данные расписания для AJAX-обновления JS-клиентом (schedule_live.js).
        Возвращает: version (хеш для детекции изменений), tournament_name, target_date,
        time_slots, courts, matches. Параметр half фильтрует корты по половине.
        """
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            target_date = request.args.get('date')
            half_param = request.args.get('half')
            half = int(half_param) if half_param in ('1', '2') else None
            from api import get_settings
            settings = get_settings()

            schedule_data = html_generator.get_schedule_data(tournament_data, target_date, settings, half)

            return jsonify({
                "version": schedule_data.get("version", ""),
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
        """
        GET /api/html-live/round-robin/<tournament_id>/<class_id>/<draw_index>
        HTML-страница таблицы кругового этапа для конкретной группы.
        Ищет нужный xml_type_info по class_id и draw_index среди tournament_table round_robin.
        404, если группа не найдена в данных турнира.
        """
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
        """
        GET /api/html-live/elimination/<tournament_id>/<class_id>/<draw_index>
        HTML-страница сетки плей-офф для конкретной стадии.
        Ищет нужный xml_type_info по class_id и draw_index среди tournament_table elimination.
        404, если сетка не найдена в данных турнира.
        """
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
        """
        GET /api/elimination/<tournament_id>/<class_id>/data[?draw_index=N]
        JSON-данные сетки плей-офф для AJAX-обновления (elimination_live.js).
        Параметр draw_index (по умолчанию 0) выбирает нужную стадию внутри категории.
        """
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
        """
        JSON-данные кругового этапа для AJAX-обновления (round_robin_live.js).
        Возвращает matches (матчи группы) и standings (турнирная таблица).
        """
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
        """
        POST /api/live/subscribe/<court_id> — подписывает корт на live-обновления WebSocket.
        Требует авторизации. Возвращает {success, court_id}.
        """
        try:
            success = live_manager.subscribe_court(court_id)
            return jsonify({"success": success, "court_id": court_id})
        except Exception as e:
            logger.error(f"Error subscribing to court {court_id}: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/live/unsubscribe/<int:court_id>', methods=['POST'])
    @require_auth
    def unsubscribe_live_court(court_id):
        """
        POST /api/live/unsubscribe/<court_id> — отписывает корт от live-обновлений WebSocket.
        Требует авторизации. Возвращает {success, court_id}.
        """
        try:
            live_manager.unsubscribe_court(court_id)
            return jsonify({"success": True, "court_id": court_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/live/subscriptions')
    def get_live_subscriptions():
        """
        GET /api/live/subscriptions — список всех активных WebSocket-подписок на корты.
        Возвращает {courts: [...court_id], count: N}.
        """
        try:
            courts = live_manager.get_subscribed_courts()
            return jsonify({"courts": courts, "count": len(courts)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/court/<tournament_id>/<court_id>/settings', methods=['GET'])
    def get_court_settings(tournament_id, court_id):
        """
        GET /api/court/<tournament_id>/<court_id>/settings
        Возвращает настройки корта: {has_referee: bool}.
        has_referee=False активирует режим «без судьи» (показ следующего матча).
        """
        try:
            has_referee = get_court_has_referee(tournament_id, str(court_id))
            return jsonify({"has_referee": has_referee})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/court/<tournament_id>/<court_id>/settings', methods=['POST'])
    @require_auth
    def update_court_settings(tournament_id, court_id):
        """
        POST /api/court/<tournament_id>/<court_id>/settings — обновляет настройки корта.
        Требует авторизации. Тело (JSON): {has_referee: bool}.
        Сохраняет флаг через set_court_has_referee и возвращает {success, has_referee}.
        """
        try:
            data = request.get_json(force=True) or {}
            has_referee = bool(data.get("has_referee", True))
            set_court_has_referee(tournament_id, str(court_id), has_referee)
            return jsonify({"success": True, "has_referee": has_referee})
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек корта {court_id}: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/media-dashboard/<tournament_id>/data')
    def get_media_dashboard_data(tournament_id):
        """
        GET /api/media-dashboard/<tournament_id>/data
        JSON-данные для сводной панели мониторинга (Media Dashboard) — все корты турнира.
        Для каждого корта: текущий матч + следующий матч, переведённые названия типов сеток
        (RoundRobin→Групповой, Elimination→Плей-офф), stage_type (group/playoff),
        нормализованные поля team1/team2_players и team1/team2_score для JS.
        Также возвращает список уникальных категорий (categories) для фильтрации.
        """
        try:
            tournament_data = get_tournament_data(tournament_id)
            if not tournament_data:
                return jsonify({"error": "Турнир не найден"}), 404

            tournament_name = tournament_data.get("metadata", {}).get("name", f"Турнир {tournament_id}")

            # Технические значения из rankedin API → читаемые русские названия
            _DRAW_LABELS = {"RoundRobin": "Групповой", "Elimination": "Плей-офф"}

            # Определяем тип этапа по draw_data: round_robin → group, elimination → playoff
            draw_data = tournament_data.get("draw_data", {})
            class_stage_map = {}
            for class_info in draw_data.values():
                name = class_info.get("class_info", {}).get("Name", "")
                if not name:
                    continue
                has_el = bool(class_info.get("elimination"))
                has_rr = bool(class_info.get("round_robin"))
                if has_el:
                    class_stage_map[name] = "playoff"
                elif has_rr:
                    class_stage_map[name] = "group"

            courts_list = tournament_data.get("courts", [])
            categories = []
            seen_categories = set()
            courts_result = []

            for court in courts_list:
                court_id = str(court.get("Item1", ""))
                if not court_id:
                    continue

                court_data = get_court_data(tournament_id, court_id)
                if not court_data:
                    continue

                # Добавляем данные следующего матча
                next_data = _get_next_match_participants(tournament_data, court_id)
                court_data.update(next_data)

                # Переводим технические значения draw-типа в читаемые названия
                raw_class = court_data.get("class_name", "")
                class_name = _DRAW_LABELS.get(raw_class, raw_class)
                if class_name != raw_class:
                    court_data["class_name"] = class_name

                raw_next = next_data.get("next_class_name", "")
                next_class = _DRAW_LABELS.get(raw_next, raw_next)
                court_data["court_id"] = court_id
                court_data["stage_type"] = class_stage_map.get(class_name, "")
                court_data["next_stage_type"] = class_stage_map.get(next_class, "")

                # Нормализуем поля для JS
                court_data.setdefault("team1_players", court_data.get("first_participant", []))
                court_data.setdefault("team2_players", court_data.get("second_participant", []))
                court_data.setdefault("team1_score",   court_data.get("first_participant_score", 0))
                court_data.setdefault("team2_score",   court_data.get("second_participant_score", 0))

                if class_name and class_name not in seen_categories:
                    seen_categories.add(class_name)
                    categories.append(class_name)

                courts_result.append(court_data)

            return jsonify({
                "tournament_name": tournament_name,
                "courts": courts_result,
                "categories": categories,
            })
        except Exception as e:
            logger.error(f"Ошибка media-dashboard: {e}")
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/live/subscribe/tournament/<tournament_id>', methods=['POST'])
    @require_auth
    def subscribe_tournament_courts(tournament_id):
        """
        POST /api/live/subscribe/tournament/<tournament_id>
        Подписывает сразу все корты турнира на live-обновления WebSocket.
        Требует авторизации. Возвращает {success, tournament_id, courts_subscribed: [...]}.
        """
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
