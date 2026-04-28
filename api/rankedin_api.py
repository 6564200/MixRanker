#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Модуль для работы с API rankedin.com"""

from .rankedin_api_base import RankedinAPI as BaseAPI
from .score_parser import extract_players, parse_detailed_result
from typing import Dict, List, Optional
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)


class RankedinAPI(BaseAPI):
    """
    Расширенный API-клиент rankedin.com.
    Наследует транспортный слой (HTTP-запросы, retry) из BaseAPI и добавляет:
      - обработку данных корта (_process_court_data и вспомогательные методы),
      - загрузку сеток турнира по всем стадиям и группам силы (get_all_draws_for_class),
      - сборку полного снимка данных турнира (get_full_tournament_data),
      - формирование списка доступных типов отображения (get_xml_data_types).
    """

    # === ОБРАБОТКА ДАННЫХ КОРТА ===
    def _process_court_data(self, data: Dict, court_id: str) -> Dict:
        """
        Преобразует сырой JSON-ответ live API (scoreboard) в нормализованный словарь корта.
        Определяет текущее состояние корта по наличию liveMatch / previousMatch / nextMatch:
          - liveMatch есть         → идёт матч (live / playing_no_score),
          - только nextMatch       → матч ещё не начался (scheduled),
          - только previousMatch   → матч завершён (finished),
          - ничего нет             → корт свободен (free).
        Возвращает словарь с полями: court_id, court_name, event_state,
        class_name, first/second_participant, счёт, detailed_result,
        флаги тай-брейка, подача, current_match_state и данные следующего матча.
        """
        if not data:
            return {"court_id": court_id, "error": "Пустые данные"}

        details = data.get("details", {})
        result = {
            "court_id": details.get("courtId", court_id),
            "court_name": details.get("courtName", f"Корт {court_id}"),
            "event_state": details.get("eventState", ""),
        }

        live, prev, nxt = data.get("liveMatch"), data.get("previousMatch"), data.get("nextMatch")

        if live:
            base = live.get("base", {}) or live
            result.update(self._extract_match(base))
            state = live.get("state", {})
            if state.get("score"):
                s = state["score"]
                is_tiebreak = state.get("isTieBreak", False)
                is_super_tiebreak = state.get("isSuperTieBreak", False)
                
                # Текущий счёт - в тай-брейке это очки тай-брейка
                current_score1 = s.get("firstParticipantScore", 0)
                current_score2 = s.get("secondParticipantScore", 0)
                
                # Данные о подаче
                serve = state.get("serve", {})
                
                result.update({
                    "first_participant_score": current_score1,
                    "second_participant_score": current_score2,
                    "detailed_result": self._parse_detailed(
                        s.get("detailedResult", []), 
                        is_tiebreak=is_tiebreak,
                        is_super_tiebreak=is_super_tiebreak,
                        tiebreak_score=(current_score1, current_score2)
                    ),
                    "is_tiebreak": is_tiebreak,
                    "is_super_tiebreak": is_super_tiebreak,
                    "is_first_participant_serving": serve.get("isFirstParticipantServing"),
                    "is_serving_left": serve.get("isServingLeft"),
                    "current_match_state": "live"
                })
            else:
                result.update({"first_participant_score": 0, "second_participant_score": 0, "detailed_result": [], "current_match_state": "playing_no_score"})
            result.update(self._extract_next(nxt) if nxt else self._empty_next())
        elif nxt and not prev:
            result.update(self._extract_match(nxt))
            result.update({"first_participant_score": 0, "second_participant_score": 0, "detailed_result": [], "current_match_state": "scheduled"})
            result.update(self._empty_next())
        elif prev:
            result.update(self._extract_match(prev))
            if "score" in prev:
                s = prev["score"]
                result.update({
                    "first_participant_score": s.get("firstParticipantScore", 0),
                    "second_participant_score": s.get("secondParticipantScore", 0),
                    "detailed_result": self._parse_detailed(s.get("detailedResult", [])),
                    "is_tiebreak": False,
                    "is_super_tiebreak": False,
                    "current_match_state": "finished"
                })
            else:
                result.update({
                    "first_participant_score": 0,
                    "second_participant_score": 0,
                    "detailed_result": [],
                    "is_tiebreak": False,
                    "is_super_tiebreak": False,
                    "current_match_state": "finished"
                })
            result.update(self._empty_next())
        else:
            result.update(self._empty_current())
            result.update(self._empty_next())
        return result

    def _empty_current(self) -> Dict:
        """Возвращает пустую структуру текущего матча со state='free' (корт свободен)."""
        return {"class_name": "", "first_participant_score": 0, "second_participant_score": 0, "detailed_result": [], "first_participant": [], "second_participant": [], "is_tiebreak": False, "is_super_tiebreak": False, "current_match_state": "free"}

    def _empty_next(self) -> Dict:
        """Возвращает пустую структуру следующего матча (когда nextMatch отсутствует)."""
        return {"next_class_name": "", "next_first_participant": [], "next_second_participant": [], "next_start_time": ""}

    def _extract_match(self, m: Dict) -> Dict:
        """
        Извлекает базовые поля матча: class_name, first_participant, second_participant.
        Используется для liveMatch.base, previousMatch и nextMatch (без счёта).
        Возвращает пустой словарь, если m равен None или пуст.
        """
        if not m:
            return {}
        return {
            "class_name": m.get("className", ""),
            "first_participant": self._extract_players(m.get("firstParticipant", [])),
            "second_participant": self._extract_players(m.get("secondParticipant", []))
        }

    def _extract_next(self, m: Dict) -> Dict:
        """
        Извлекает данные следующего матча: next_class_name, next_first/second_participant, next_start_time.
        Возвращает _empty_next(), если m равен None или пуст.
        """
        if not m:
            return self._empty_next()
        return {
            "next_class_name": m.get("className", ""),
            "next_first_participant": self._extract_players(m.get("firstParticipant", [])),
            "next_second_participant": self._extract_players(m.get("secondParticipant", [])),
            "next_start_time": m.get("startTime", "")
        }

    def _extract_players(self, players) -> List[Dict]:
        """Делегирует разбор списка игроков функции extract_players из score_parser."""
        return extract_players(players)

    def _parse_detailed(self, detailed: List[Dict], is_tiebreak: bool = False,
                        is_super_tiebreak: bool = False, tiebreak_score: tuple = None) -> List[Dict]:
        """
        Делегирует разбор детального счёта (сеты, геймы, тай-брейки) функции
        parse_detailed_result из score_parser.
        tiebreak_score — текущий счёт тай-брейка в виде (score1, score2), если is_tiebreak=True.
        """
        return parse_detailed_result(detailed, is_tiebreak, is_super_tiebreak, tiebreak_score)

    # === DRAWS ===
    def get_all_draws_for_class(self, class_id: str) -> Dict[str, List[Dict]]:
        """
        Загружает все сетки (draws) для одной категории турнира (class_id).
        Перебирает комбинации drawStage (0–2) × drawStrength (0–3), делая паузу 0.25 с
        между запросами для соблюдения rate limit (не более 4 запросов/сек).
        Ранняя остановка: если stage=0 / strength=0 вернули пустой результат —
        дальнейший перебор по этому измерению не имеет смысла.
        Возвращает словарь {'round_robin': [...], 'elimination': [...]};
        сетки elimination сортируются по полю Consolation (основная сетка первой).
        """
        draws = {"round_robin": [], "elimination": []}
        for stage in [0, 1, 2]:
            stage_had_results = False
            for strength in [0, 1, 2, 3]:
                try:
                    time.sleep(0.25)  # throttle: не более 4 запросов/сек
                    url = f"{self.api_base}/tournament/GetDrawsForStageAndStrengthAsync?tournamentClassId={class_id}&drawStrength={strength}&drawStage={stage}&isReadonly=true&language=ru"
                    result = self._make_request(url)
                    if not result or not isinstance(result, list):
                        # Если strength=0 уже пуст — дальше по strength нет смысла
                        if strength == 0:
                            break
                        continue
                    stage_had_results = True
                    for item in result:
                        if not isinstance(item, dict):
                            continue
                        bt, has_rr, has_el = item.get("BaseType", ""), bool(item.get("RoundRobin")), bool(item.get("Elimination"))
                        if bt == "RoundRobin" and has_rr:
                            draws["round_robin"].append(item)
                        elif bt == "Elimination" and has_el:
                            draws["elimination"].append(item)
                        elif has_rr and not has_el:
                            draws["round_robin"].append(item)
                        elif has_el and not has_rr:
                            draws["elimination"].append(item)
                except Exception:
                    continue
            # Если stage 0 совсем пуст — дальше тоже нет смысла
            if stage == 0 and not stage_had_results:
                break
        if draws["elimination"]:
            draws["elimination"].sort(key=lambda x: x.get('Elimination', {}).get('Consolation', 0))
        return draws

    def get_full_tournament_data(self, tournament_id: str) -> Dict:
        """
        Собирает полный снимок данных турнира из нескольких API-эндпоинтов и возвращает единый словарь.
        Порядок загрузки:
          1. metadata    — название, даты, параметры турнира,
          2. participants — все сиды/участники,
          3. classes     — категории (классы) турнира,
          4. courts      — список кортов,
          5. dates       — игровые даты,
          6. court_planner / court_usage — назначение матчей на корты (только если есть даты),
          7. draw_data   — сетки по каждой категории (round_robin + elimination).
        Поле loaded_at содержит ISO-timestamp момента загрузки.
        """
        data = {"tournament_id": tournament_id, "metadata": {}, "classes": [], "courts": [], "dates": [], "participants": [], "draw_data": {}, "court_planner": {}, "court_usage": {}, "loaded_at": datetime.now().isoformat()}

        data["metadata"] = self.get_tournament_metadata(tournament_id) or {}
        data["participants"] = self.get_tournament_participants(tournament_id) or []
        data["classes"] = self.get_tournament_classes(tournament_id) or []
        courts_info = self.get_tournament_courts(tournament_id)
        if courts_info and "Courts" in courts_info:
            data["courts"] = courts_info["Courts"]
        data["dates"] = self.get_tournament_dates(tournament_id) or []

        if data["dates"]:
            data["court_planner"] = self.get_court_planner(tournament_id, data["dates"]) or {}
            data["court_usage"] = self.get_court_usage(tournament_id, data["dates"]) or []

        classes_draws = self.get_classes_and_draws(tournament_id) or data["classes"]
        for cls in classes_draws:
            cid = cls.get("Id")
            if not cid:
                continue
            draws = self.get_all_draws_for_class(str(cid))
            data["draw_data"][str(cid)] = {"class_info": cls, "round_robin": draws["round_robin"], "elimination": draws["elimination"]}

        return data

    def get_xml_data_types(self, tournament_data: Dict) -> List[Dict]:
        """
        Формирует список доступных типов отображения для данного турнира.
        Каждый элемент описывает один источник данных и содержит id, name, type и доп. поля.
        Типы элементов:
          'tournament_table' (draw_type='round_robin')  — таблица кругового этапа,
          'tournament_table' (draw_type='elimination')  — сетка плей-офф,
          'schedule'                                    — расписание матчей (если есть корты/даты),
          'court_score'                                 — табло конкретного корта.
        Для elimination автоматически формируется читаемое название стадии
        (Финал / Места N-M / Место N) на основе PlacesStartPos, PlacesEndPos и Consolation.
        """
        types = []
        draw_data = tournament_data.get("draw_data", {})
        classes = tournament_data.get("classes", [])

        for cid, cdata in draw_data.items():
            if not isinstance(cdata, dict):
                continue
            info = cdata.get("class_info", {})
            if not info:
                info = next((c for c in classes if str(c.get("Id")) == str(cid)), {})
            name = info.get("Name", f"Категория {cid}")

            for i, rr in enumerate(cdata.get("round_robin", [])):
                gname = "Групповой этап"
                if isinstance(rr, dict) and rr.get("RoundRobin", {}).get("Name"):
                    gname = rr["RoundRobin"]["Name"]
                types.append({"id": f"table_{cid}_rr_{i}", "name": f"{name} - {gname}", "type": "tournament_table", "class_id": cid, "class_name": name, "draw_type": "round_robin", "draw_index": i, "group_name": gname})

            for i, el in enumerate(cdata.get("elimination", [])):
                sname = "Плей-офф"
                if isinstance(el, dict) and el.get("Elimination"):
                    e = el["Elimination"]
                    ps, pe, c = e.get("PlacesStartPos", 1), e.get("PlacesEndPos", 1), e.get("Consolation", 0)
                    sname = f"Места {ps}-{pe}" if ps != pe else f"Место {ps}" if c else ("Финал" if ps == 1 and pe == 1 else f"Места 1-{pe}")
                types.append({"id": f"table_{cid}_elim_{i}", "name": f"{name} - {sname}", "type": "tournament_table", "class_id": cid, "class_name": name, "draw_type": "elimination", "draw_index": i, "stage_name": sname})

        if tournament_data.get("court_usage") or tournament_data.get("dates"):
            types.append({"id": "schedule", "name": "Расписание матчей", "type": "schedule"})

        for court in tournament_data.get("courts", []):
            if isinstance(court, dict) and court.get("Item1"):
                court_id = court['Item1']
                court_name = court.get('Item2', f'Корт {court_id}')
                types.append({"id": f"court_{court_id}", "name": f"{court_name} - Счет", "type": "court_score", "court_id": court_id, "court_name": court.get("Item2", "")})

        return types