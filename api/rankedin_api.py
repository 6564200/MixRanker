#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Модуль для работы с API rankedin.com"""

from .rankedin_api_base import RankedinAPI as BaseAPI
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RankedinAPI(BaseAPI):
    """
    API клиент rankedin.com"""

    # === ОБРАБОТКА ДАННЫХ КОРТА ===
    def _process_court_data(self, data: Dict, court_id: str) -> Dict:
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
            result.update(self._empty_next())
        else:
            result.update(self._empty_current())
            result.update(self._empty_next())
        return result

    def _empty_current(self) -> Dict:
        return {"class_name": "", "first_participant_score": 0, "second_participant_score": 0, "detailed_result": [], "first_participant": [], "second_participant": [], "is_tiebreak": False, "is_super_tiebreak": False, "current_match_state": "free"}

    def _empty_next(self) -> Dict:
        return {"next_class_name": "", "next_first_participant": [], "next_second_participant": [], "next_start_time": ""}

    def _extract_match(self, m: Dict) -> Dict:
        if not m:
            return {}
        return {
            "class_name": m.get("className", ""),
            "first_participant": self._extract_players(m.get("firstParticipant", [])),
            "second_participant": self._extract_players(m.get("secondParticipant", []))
        }

    def _extract_next(self, m: Dict) -> Dict:
        if not m:
            return self._empty_next()
        return {
            "next_class_name": m.get("className", ""),
            "next_first_participant": self._extract_players(m.get("firstParticipant", [])),
            "next_second_participant": self._extract_players(m.get("secondParticipant", [])),
            "next_start_time": m.get("startTime", "")
        }

    def _extract_players(self, players) -> List[Dict]:
        if not isinstance(players, list):
            return []
        return [{
            "id": p.get("id", ""),
            "firstName": (p.get("firstName") or "").strip(),
            "lastName": (p.get("lastName") or "").strip(),
            "countryCode": p.get("countryCode", ""),
            "fullName": f"{(p.get('firstName') or '').strip()} {(p.get('lastName') or '').strip()}".strip(),
            "initialLastName": f"{(p.get('firstName') or '').strip()[:1]}. {(p.get('lastName') or '').strip()}".strip() if p.get('firstName') and p.get('lastName') else ""
        } for p in players]

    def _parse_detailed(self, detailed: List[Dict], is_tiebreak: bool = False, 
                        is_super_tiebreak: bool = False, tiebreak_score: tuple = None) -> List[Dict]:
        result = []
        for i, s in enumerate(detailed):
            if not isinstance(s, dict):
                continue
            info = {
                "firstParticipantScore": s.get("firstParticipantScore", 0), 
                "secondParticipantScore": s.get("secondParticipantScore", 0), 
                "loserTiebreak": s.get("loserTiebreak")
            }
            
            games = s.get("detailedResult", [])
            is_last_set = (i == len(detailed) - 1)
            
            if games:
                # Берём последний элемент из вложенного detailedResult
                last = games[-1]
                g1, g2 = last.get("firstParticipantScore", 0), last.get("secondParticipantScore", 0)
                
                # Проверяем тай-брейк:
                # 1. Супер тай-брейк (3-й сет с счётом 0:0 по сетам)
                # 2. Обычный тай-брейк (6:6 в сете)
                # 3. Флаг isTieBreak из state
                set_score1 = s.get("firstParticipantScore", 0)
                set_score2 = s.get("secondParticipantScore", 0)
                
                is_set_tiebreak = (
                    (set_score1 == 6 and set_score2 == 6) or  # Обычный тай-брейк 6:6
                    (set_score1 == 0 and set_score2 == 0 and is_last_set and (is_tiebreak or is_super_tiebreak)) or  # Супер тай-брейк
                    last.get("loserTiebreak") is not None
                )
                
                if is_set_tiebreak:
                    # В тай-брейке показываем очки как есть
                    info["gameScore"] = {"first": str(g1), "second": str(g2)}
                    info["isTieBreak"] = True
                    if is_last_set and is_super_tiebreak:
                        info["isSuperTieBreak"] = True
                else:
                    # Обычный гейм - конвертируем в теннисный формат (0, 15, 30, 40, AD)
                    def conv(v, other): 
                        if v <= 3:
                            return {0: "0", 1: "15", 2: "30", 3: "40"}[v]
                        else:
                            # v >= 4: при равенстве или отставании — 40, при лидерстве — AD
                            if v > other:
                                return "AD"
                            else:
                                return "40"
                    info["gameScore"] = {"first": conv(g1, g2), "second": conv(g2, g1)}
            result.append(info)
        return result

    # === DRAWS ===
    def get_all_draws_for_class(self, class_id: str) -> Dict[str, List[Dict]]:
        draws = {"round_robin": [], "elimination": []}
        for stage in [0, 1, 2]:
            for strength in [0, 1, 2, 3]:
                try:
                    url = f"{self.api_base}/tournament/GetDrawsForStageAndStrengthAsync?tournamentClassId={class_id}&drawStrength={strength}&drawStage={stage}&isReadonly=true&language=ru"
                    result = self._make_request(url)
                    if not result or not isinstance(result, list):
                        continue
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
        if draws["elimination"]:
            draws["elimination"].sort(key=lambda x: x.get('Elimination', {}).get('Consolation', 0))
        return draws

    def get_full_tournament_data(self, tournament_id: str) -> Dict:
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
        """Генерирует список доступных типов XML"""
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
                types.append({"id": f"court_{court['Item1']}", "name": f"{court.get('Item2', f'Корт {court['Item1']}')} - Счет", "type": "court_score", "court_id": court["Item1"], "court_name": court.get("Item2", "")})

        return types