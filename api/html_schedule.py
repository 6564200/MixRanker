#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Р“РµРЅРµСЂР°С‚РѕСЂ HTML СЃС‚СЂР°РЅРёС† СЂР°СЃРїРёСЃР°РЅРёСЏ РјР°С‚С‡РµР№
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
from .html_base import HTMLBaseGenerator
import logging
import re

logger = logging.getLogger(__name__)


class ScheduleGenerator(HTMLBaseGenerator):
    """Р“РµРЅРµСЂР°С‚РѕСЂ schedule СЃС‚СЂР°РЅРёС†"""
    
    # FHD СЂР°Р·РјРµСЂС‹ (СѓРІРµР»РёС‡РµРЅРЅС‹Рµ)
    MATCH_HEIGHT = 86
    GAP = 8

    def _split_team_name(self, team_name: str) -> list:
        """Р Р°Р·Р±РёРІР°РµС‚ РёРјСЏ РєРѕРјР°РЅРґС‹ РЅР° РѕС‚РґРµР»СЊРЅС‹С… РёРіСЂРѕРєРѕРІ"""
        if not team_name:
            return ["TBD"]
        
        # Р Р°Р·РґРµР»РёС‚РµР»Рё: "/" РёР»Рё " / "
        if "/" in team_name:
            players = [p.strip() for p in team_name.split("/")]
            return [p for p in players if p]
        
        return [team_name]

    def _get_tournament_name_class(self, name: str) -> str:
        """РћРїСЂРµРґРµР»СЏРµС‚ CSS РєР»Р°СЃСЃ РґР»СЏ РЅР°Р·РІР°РЅРёСЏ С‚СѓСЂРЅРёСЂР° РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РґР»РёРЅС‹"""
        if len(name) > 40:
            return "very-long-name"
        elif len(name) > 25:
            return "long-name"
        return ""

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> str:
        """Р“РµРЅРµСЂРёСЂСѓРµС‚ HTML РґР»СЏ СЂР°СЃРїРёСЃР°РЅРёСЏ РјР°С‚С‡РµР№"""
        return self._generate_schedule(tournament_data, target_date, "schedule.css", filter_matches=True, settings=settings)

    def get_schedule_data(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> Dict:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РґР°РЅРЅС‹Рµ СЂР°СЃРїРёСЃР°РЅРёСЏ РІ С„РѕСЂРјР°С‚Рµ JSON РґР»СЏ AJAX"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "РќРµРёР·РІРµСЃС‚РЅС‹Р№ С‚СѓСЂРЅРёСЂ")
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return {"error": "Р”Р°РЅРЅС‹Рµ СЂР°СЃРїРёСЃР°РЅРёСЏ РЅРµ Р·Р°РіСЂСѓР¶РµРЅС‹", "matches": [], "courts": [], "time_slots": []}

        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        target_date = target_date or datetime.now().strftime("%d.%m.%Y")

        matches_data = tournament_data.get("matches_data", {})
        matches_index = self._build_matches_index(matches_data, court_names_map)

        courts_matches, all_matches = self._group_matches_by_court(court_usage, court_names_map, target_date, matches_index)

        if not courts_matches:
            return {
                "tournament_name": tournament_name,
                "target_date": target_date,
                "courts": [],
                "time_slots": [],
                "matches": []
            }

        self._enumerate_matches(courts_matches)

        finished_count = (settings or {}).get("finishedMatchesCount", 3)
        courts_matches = self._filter_matches(courts_matches, finished_count)

        time_slots = sorted({m["start_time"] for matches in courts_matches.values() for m in matches})
        sorted_courts = sorted(courts_matches.keys())

        # Р¤РѕСЂРјРёСЂСѓРµРј СЃРїРёСЃРѕРє РјР°С‚С‡РµР№ СЃ РїРѕР·РёС†РёСЏРјРё РІ СЃРµС‚РєРµ
        time_to_row = {time: idx + 1 for idx, time in enumerate(time_slots)}
        court_to_col = {court: idx + 1 for idx, court in enumerate(sorted_courts)}

        matches_list = []
        for court_name, matches in courts_matches.items():
            for match in matches:
                start_time = match.get("start_time", "")
                row = time_to_row.get(start_time, 1)
                col = court_to_col.get(court_name, 1)
                
                matches_list.append({
                    "id": match.get("TournamentMatchId", ""),
                    "row": row,
                    "col": col,
                    "court": court_name,
                    "start_time": start_time,
                    "episode": match.get("episode_number", 1),
                    "challenger": match.get("ChallengerFullName") or match.get("ChallengerName", "TBD"),
                    "challenged": match.get("ChallengedFullName") or match.get("ChallengedName", "TBD"),
                    "challenger_score": match.get("ChallengerResult", "") or "",
                    "challenged_score": match.get("ChallengedResult", "") or "",
                    "status": self.get_match_status(match)
                })

        return {
            "tournament_name": tournament_name,
            "target_date": target_date,
            "courts": sorted_courts,
            "time_slots": time_slots,
            "matches": matches_list
        }

    def _generate_schedule(self, tournament_data: Dict, target_date: str, css_file: str, filter_matches: bool, settings: Dict = None) -> str:
        """РћР±С‰РёР№ РјРµС‚РѕРґ РіРµРЅРµСЂР°С†РёРё СЂР°СЃРїРёСЃР°РЅРёСЏ"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "РќРµРёР·РІРµСЃС‚РЅС‹Р№ С‚СѓСЂРЅРёСЂ")
        tournament_id = tournament_data.get("tournament_id", "") or metadata.get("id", "")
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Р”Р°РЅРЅС‹Рµ СЂР°СЃРїРёСЃР°РЅРёСЏ РЅРµ Р·Р°РіСЂСѓР¶РµРЅС‹")

        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        target_date = target_date or datetime.now().strftime("%d.%m.%Y")

        # РЎРѕР·РґР°С‘Рј РёРЅРґРµРєСЃ РјР°С‚С‡РµР№ РґР»СЏ РѕР±РѕРіР°С‰РµРЅРёСЏ РґР°РЅРЅС‹С…
        matches_data = tournament_data.get("matches_data", {})
        matches_index = self._build_matches_index(matches_data, court_names_map)

        courts_matches, all_matches = self._group_matches_by_court(court_usage, court_names_map, target_date, matches_index)

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"РќРµС‚ РјР°С‚С‡РµР№ РЅР° {target_date}")

        self._enumerate_matches(courts_matches)

        if filter_matches:
            finished_count = (settings or {}).get("finishedMatchesCount", 3)
            courts_matches = self._filter_matches(courts_matches, finished_count)

        # time_slots С‚РѕР»СЊРєРѕ РёР· РѕС‚С„РёР»СЊС‚СЂРѕРІР°РЅРЅС‹С… РјР°С‚С‡РµР№
        time_slots = sorted({m["start_time"] for matches in courts_matches.values() for m in matches})

        return self._render_schedule_html(tournament_name, tournament_id, target_date, courts_matches, time_slots, css_file)

    def _build_court_names_map(self, courts_info: List[Dict]) -> Dict[str, str]:
        """РЎРѕР·РґР°РµС‚ РєР°СЂС‚Сѓ ID РєРѕСЂС‚Р° -> РЅР°Р·РІР°РЅРёРµ"""
        return {
            str(c["Item1"]): c["Item2"]
            for c in courts_info
            if isinstance(c, dict) and c.get("Item1") and c.get("Item2")
        }
    @staticmethod
    def _normalize_court_name(court_name: str) -> str:
        return (court_name or "").strip().lower()

    @staticmethod
    def _normalize_date(value: str) -> str:
        raw = (value or "").strip()
        if not raw:
            return ""

        if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", raw):
            return raw

        try:
            cleaned = raw.replace("Z", "").replace("T", " ")
            dt = datetime.fromisoformat(cleaned)
            return dt.strftime("%d.%m.%Y")
        except Exception:
            pass

        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", raw)
        if m:
            return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
        return raw

    @staticmethod
    def _extract_possible_match_ids(match: Dict) -> Set[str]:
        ids = set()
        for key in ("TournamentMatchId", "TournamentMatchID", "MatchId", "Id", "id"):
            value = match.get(key)
            if value not in (None, ""):
                ids.add(str(value))
        return ids

    def _build_matches_index(self, matches_data: Dict, court_names_map: Dict) -> Dict:
        """РЎРѕР·РґР°С‘С‚ РёРЅРґРµРєСЃ РјР°С‚С‡РµР№ РїРѕ РґР°С‚Рµ + РєРѕСЂС‚Сѓ РґР»СЏ Р±С‹СЃС‚СЂРѕРіРѕ РїРѕРёСЃРєР°"""
        matches_index = {"by_date_court": {}, "by_date": {}, "by_id": {}}
        matches_list = matches_data.get("Matches", []) if isinstance(matches_data, dict) else []

        for match in matches_list:
            date = self._normalize_date(match.get("Date", ""))
            court_name = self._normalize_court_name(match.get("Court", ""))

            key = (date, court_name)
            if key not in matches_index["by_date_court"]:
                matches_index["by_date_court"][key] = []
            matches_index["by_date_court"][key].append(match)
            if date not in matches_index["by_date"]:
                matches_index["by_date"][date] = []
            matches_index["by_date"][date].append(match)

            for match_id in self._extract_possible_match_ids(match):
                matches_index["by_id"][match_id] = match

        return matches_index

    @staticmethod
    def _normalize_token(value: str) -> str:
        return re.sub(r"[^0-9A-Za-zА-Яа-яЁё]", "", (value or "")).upper()

    def _get_abbrevs_from_name(self, full_name: str) -> set:
        """РџРѕР»СѓС‡Р°РµС‚ РІСЃРµ РІРѕР·РјРѕР¶РЅС‹Рµ СЃРѕРєСЂР°С‰РµРЅРёСЏ (РїРµСЂРІС‹Рµ 3 Р±СѓРєРІС‹ РєР°Р¶РґРѕРіРѕ СЃР»РѕРІР°)"""
        if not full_name:
            return set()

        parts = [self._normalize_token(p) for p in full_name.split()]
        parts = [p for p in parts if p]
        values = set(parts)

        for p in parts:
            for n in range(2, len(p) + 1):
                values.add(p[:n])
        return values

    def _match_abbrev_to_name(self, abbrev: str, full_name: str) -> bool:
        token = self._normalize_token(abbrev)
        if not token:
            return True
        return token in self._get_abbrevs_from_name(full_name)

    def _team_matches(self, team_abbrev: str, team_data: Dict) -> bool:
        parts = [p.strip() for p in re.split(r"[\\/|]", (team_abbrev or "")) if p.strip()]
        ab1 = parts[0] if len(parts) > 0 else ""
        ab2 = parts[1] if len(parts) > 1 else ""
        n1, n2 = self._extract_team_player_names(team_data)

        direct = self._match_abbrev_to_name(ab1, n1) and self._match_abbrev_to_name(ab2, n2)
        swapped = self._match_abbrev_to_name(ab1, n2) and self._match_abbrev_to_name(ab2, n1)
        return direct or swapped

    def _find_match_by_abbrev(self, matches_index: Dict, date: str, court_name: str,
                              challenger_abbrev: str, challenged_abbrev: str,
                              source_match: Optional[Dict] = None) -> Optional[Dict]:
        """РќР°С…РѕРґРёС‚ РјР°С‚С‡ РїРѕ РґР°С‚Рµ, РєРѕСЂС‚Сѓ Рё СЃРѕРєСЂР°С‰РµРЅРёСЏРј РёРјС‘РЅ"""
        if source_match:
            for match_id in self._extract_possible_match_ids(source_match):
                exact = matches_index.get("by_id", {}).get(match_id)
                if exact:
                    return exact

        key = (self._normalize_date(date), self._normalize_court_name(court_name))
        candidates = matches_index.get("by_date_court", {}).get(key, [])
        if not candidates:
            candidates = matches_index.get("by_date", {}).get(key[0], [])

        for match in candidates:
            challenger = match.get("Challenger", {})
            challenged = match.get("Challenged", {})

            same_side = (
                self._team_matches(challenger_abbrev, challenger)
                and self._team_matches(challenged_abbrev, challenged)
            )
            swapped_side = (
                self._team_matches(challenger_abbrev, challenged)
                and self._team_matches(challenged_abbrev, challenger)
            )

            if same_side or swapped_side:
                return match

        return None

    def _extract_team_player_names(self, participant: Dict) -> tuple:
        if not isinstance(participant, dict):
            return "", ""

        # Variant A: flat fields
        n1 = (participant.get("Name") or "").strip()
        n2 = (participant.get("Player2Name") or "").strip()
        if n1 or n2:
            return n1, n2

        # Variant B: nested FirstPlayer/SecondPlayer
        first = participant.get("FirstPlayer", {}) or {}
        second = participant.get("SecondPlayer", {}) or {}
        n1 = (first.get("Name") or first.get("FullName") or "").strip()
        n2 = (second.get("Name") or second.get("FullName") or "").strip()
        if n1 or n2:
            return n1, n2

        # Variant C: players array
        players = participant.get("Players", [])
        if isinstance(players, list):
            p1 = players[0] if len(players) > 0 and isinstance(players[0], dict) else {}
            p2 = players[1] if len(players) > 1 and isinstance(players[1], dict) else {}
            n1 = (p1.get("Name") or p1.get("FullName") or "").strip()
            n2 = (p2.get("Name") or p2.get("FullName") or "").strip()
            return n1, n2

        return "", ""

    def _format_full_name(self, participant: Dict) -> str:
        """Р¤РѕСЂРјР°С‚РёСЂСѓРµС‚ РёРјСЏ СѓС‡Р°СЃС‚РЅРёРєР°: Рџ.Р¤Р°РјРёР»РёСЏ/Рџ.Р¤Р°РјРёР»РёСЏ"""
        name1, name2 = self._extract_team_player_names(participant)
        
        def format_player(full_name):
            if not full_name:
                return ""
            parts = full_name.split()
            if len(parts) >= 2:
                # РџРµСЂРІР°СЏ Р±СѓРєРІР° РёРјРµРЅРё + С„Р°РјРёР»РёСЏ (РїРѕСЃР»РµРґРЅРµРµ СЃР»РѕРІРѕ)
                initial = parts[0][0].upper()
                surname = parts[-1].upper()
                return f"{initial}.{surname}"
            elif len(parts) == 1:
                return parts[0].upper()
            return ""
        
        p1 = format_player(name1)
        p2 = format_player(name2)
        
        if p1 and p2:
            return f"{p1}/{p2}"
        return p1 or p2 or "TBD"

    def _format_abbrev_team_fallback(self, team_name: str) -> str:
        if not team_name:
            return "TBD"
        parts = [p.strip() for p in re.split(r"[\\/|]", team_name) if p.strip()]
        if not parts:
            return "TBD"

        normalized = []
        for part in parts[:2]:
            # already looks like I.SURNAME
            if re.match(r"^[A-Za-zА-Яа-яЁё]\.[A-Za-zА-Яа-яЁё]+$", part):
                normalized.append(part.upper())
                continue
            token = self._normalize_token(part)
            if token:
                normalized.append(token)

        return "/".join(normalized) if normalized else team_name

    def _format_detailed_score(self, match_result: Dict) -> str:
        """Р¤РѕСЂРјР°С‚РёСЂСѓРµС‚ РґРµС‚Р°Р»СЊРЅС‹Р№ СЃС‡С‘С‚ РёР· MatchResult"""
        if not match_result:
            return ""
        
        score = match_result.get("Score", {})
        if not score:
            return ""
        
        detailed = score.get("DetailedScoring", [])
        if not detailed:
            # Р’РѕР·РІСЂР°С‰Р°РµРј РѕР±С‰РёР№ СЃС‡С‘С‚
            p1 = score.get("FirstParticipantScore", "")
            p2 = score.get("SecondParticipantScore", "")
            if p1 != "" and p2 != "":
                return f"{p1}-{p2}"
            return ""
        
        # Р¤РѕСЂРјР°С‚РёСЂСѓРµРј РїРѕ СЃРµС‚Р°Рј
        sets = []
        for s in detailed:
            p1 = s.get("FirstParticipantScore", 0)
            p2 = s.get("SecondParticipantScore", 0)
            tb = s.get("LoserTiebreak")
            if tb:
                sets.append(f"{p1}-{p2}({tb})")
            else:
                sets.append(f"{p1}-{p2}")
        
        return " ".join(sets)

    def _group_matches_by_court(self, court_usage: List, court_names_map: Dict, 
                                 target_date: str, matches_index: Dict) -> tuple:
        """Р“СЂСѓРїРїРёСЂСѓРµС‚ РјР°С‚С‡Рё РїРѕ РєРѕСЂС‚Р°Рј Рё С„РёР»СЊС‚СЂСѓРµС‚ РїРѕ РґР°С‚Рµ"""
        courts_matches = {}
        all_matches = []

        for match in court_usage:
            if not isinstance(match, dict):
                continue

            match_date = match.get("MatchDate", "")
            if not match_date:
                continue

            try:
                dt_obj = datetime.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                if dt_obj.strftime("%d.%m.%Y") != target_date:
                    continue

                court_id = str(match.get("CourtId", ""))
                court_name = court_names_map.get(court_id, f"РљРѕСЂС‚ {court_id}")

                match["start_time"] = dt_obj.strftime("%H:%M")
                match["date_formatted"] = dt_obj.strftime("%d.%m.%Y")
                match["court_name"] = court_name
                match["datetime_obj"] = dt_obj

                # РћР±РѕРіР°С‰Р°РµРј РґР°РЅРЅС‹РјРё РёР· matches
                challenger_abbrev = match.get("ChallengerName", "")
                challenged_abbrev = match.get("ChallengedName", "")
                
                rich_match = self._find_match_by_abbrev(
                    matches_index, match_date, court_name,
                    challenger_abbrev, challenged_abbrev, source_match=match
                )
                
                if rich_match:
                    # Р”РѕР±Р°РІР»СЏРµРј РїРѕР»РЅС‹Рµ РёРјРµРЅР°
                    match["ChallengerFullName"] = self._format_full_name(rich_match.get("Challenger", {}))
                    match["ChallengedFullName"] = self._format_full_name(rich_match.get("Challenged", {}))
                    # Р”РѕР±Р°РІР»СЏРµРј РґРµС‚Р°Р»СЊРЅС‹Р№ СЃС‡С‘С‚
                    match["DetailedScore"] = self._format_detailed_score(rich_match.get("MatchResult", {}))
                    match["RichMatchData"] = rich_match
                else:
                    # Fallback: показываем аккуратный формат даже без enrich из matches_data
                    match["ChallengerFullName"] = self._format_abbrev_team_fallback(challenger_abbrev)
                    match["ChallengedFullName"] = self._format_abbrev_team_fallback(challenged_abbrev)

                all_matches.append(match)
                courts_matches.setdefault(court_name, []).append(match)

            except Exception:
                continue

        return courts_matches, all_matches

    def _enumerate_matches(self, courts_matches: Dict):
        """РЎРѕСЂС‚РёСЂСѓРµС‚ Рё РЅСѓРјРµСЂСѓРµС‚ РјР°С‚С‡Рё"""
        for court_name, matches in courts_matches.items():
            matches.sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(matches, 1):
                match["episode_number"] = i

    def _filter_matches(self, courts_matches: Dict, finished_count: int = 3) -> Dict:
        """
        Р¤РёР»СЊС‚СЂСѓРµС‚ РјР°С‚С‡Рё СЃ РІС‹СЂР°РІРЅРёРІР°РЅРёРµРј РїРѕ РѕС‚СЃС‚Р°СЋС‰РµРјСѓ РєРѕСЂС‚Сѓ.
        
        1. РќР°С…РѕРґРёРј РєРѕСЂС‚ СЃ СЃР°РјС‹Рј РїРѕР·РґРЅРёРј РІСЂРµРјРµРЅРµРј СЃСЂРµРґРё РїРѕСЃР»РµРґРЅРёС… N СЃС‹РіСЂР°РЅРЅС‹С…
        2. Р‘РµСЂС‘Рј СЌС‚Рѕ РІСЂРµРјСЏ РєР°Рє С‚РѕС‡РєСѓ РѕС‚СЃРµС‡РµРЅРёСЏ
        3. РќР° РІСЃРµС… РєРѕСЂС‚Р°С… РїРѕРєР°Р·С‹РІР°РµРј РјР°С‚С‡Рё РЅР°С‡РёРЅР°СЏ СЃ СЌС‚РѕРіРѕ РІСЂРµРјРµРЅРё
        """
        if not courts_matches:
            return {}
        
        # РЁР°Рі 1: Р”Р»СЏ РєР°Р¶РґРѕРіРѕ РєРѕСЂС‚Р° РЅР°С…РѕРґРёРј РІСЂРµРјСЏ N-РіРѕ СЃС‹РіСЂР°РЅРЅРѕРіРѕ РјР°С‚С‡Р° СЃ РєРѕРЅС†Р°
        court_cutoff_times = {}
        
        for court_name, matches in courts_matches.items():
            # РњР°С‚С‡Рё СЃ СЂРµР·СѓР»СЊС‚Р°С‚Р°РјРё, РѕС‚СЃРѕСЂС‚РёСЂРѕРІР°РЅРЅС‹Рµ РїРѕ РІСЂРµРјРµРЅРё
            with_results = sorted(
                [m for m in matches if m.get("ChallengerResult") or m.get("ChallengedResult")],
                key=lambda x: x.get("datetime_obj") or datetime.min
            )

            if len(with_results) >= finished_count:
                # Р‘РµСЂС‘Рј РІСЂРµРјСЏ N-РіРѕ СЃ РєРѕРЅС†Р° (РїРµСЂРІРѕРіРѕ РёР· РїРѕРєР°Р·С‹РІР°РµРјС‹С…)
                cutoff_match = with_results[-finished_count]
                court_cutoff_times[court_name] = cutoff_match.get("datetime_obj")
            elif with_results:
                # Р•СЃР»Рё РјРµРЅСЊС€Рµ N СЃС‹РіСЂР°РЅРЅС‹С…, Р±РµСЂС‘Рј СЃР°РјС‹Р№ СЂР°РЅРЅРёР№
                court_cutoff_times[court_name] = with_results[0].get("datetime_obj")
            else:
                # РќРµС‚ СЃС‹РіСЂР°РЅРЅС‹С… вЂ” Р±РµСЂС‘Рј РїРµСЂРІС‹Р№ РЅРµСЃС‹РіСЂР°РЅРЅС‹Р№
                without_results = sorted(
                    [m for m in matches if not m.get("ChallengerResult") and not m.get("ChallengedResult")],
                    key=lambda x: x.get("datetime_obj") or datetime.min
                )
                if without_results:
                    court_cutoff_times[court_name] = without_results[0].get("datetime_obj")
        
        if not court_cutoff_times:
            return courts_matches
        
        # РЁР°Рі 2: РќР°С…РѕРґРёРј СЃР°РјРѕРµ РїРѕР·РґРЅРµРµ РІСЂРµРјСЏ РѕС‚СЃРµС‡РєРё (РѕС‚СЃС‚Р°СЋС‰РёР№ РєРѕСЂС‚)
        global_cutoff = min(t for t in court_cutoff_times.values() if t)
        
        # РЁР°Рі 3: Р¤РёР»СЊС‚СЂСѓРµРј РІСЃРµ РєРѕСЂС‚С‹ РїРѕ РіР»РѕР±Р°Р»СЊРЅРѕРјСѓ РІСЂРµРјРµРЅРё РѕС‚СЃРµС‡РєРё
        filtered = {}
        for court_name, matches in courts_matches.items():
            filtered[court_name] = [
                m for m in matches 
                if m.get("datetime_obj") and m.get("datetime_obj") >= global_cutoff
            ]
        
        return filtered

    def _render_schedule_html(self, tournament_name: str, tournament_id: str, target_date: str, courts_matches: Dict, time_slots: List, css_file: str) -> str:
        """Р РµРЅРґРµСЂРёС‚ HTML СЂР°СЃРїРёСЃР°РЅРёСЏ СЃ CSS Grid РїСЂРёРІСЏР·РєРѕР№ Рє РІСЂРµРјРµРЅРё"""
        sorted_courts = sorted(courts_matches.keys())
        
        # РЎРѕР·РґР°С‘Рј РјР°РїРїРёРЅРі РІСЂРµРјСЏ -> РЅРѕРјРµСЂ СЃС‚СЂРѕРєРё (1-indexed РґР»СЏ CSS Grid)
        time_to_row = {time: idx + 1 for idx, time in enumerate(time_slots)}
        
        # Р“РµРЅРµСЂРёСЂСѓРµРј version hash
        import hashlib
        version_data = f"{tournament_id}:{target_date}:{len(time_slots)}:{len(sorted_courts)}"
        for court in sorted_courts:
            for m in courts_matches[court]:
                version_data += f":{m.get('TournamentMatchId', '')}:{m.get('ChallengerResult', '')}:{m.get('ChallengedResult', '')}"
        version = hashlib.md5(version_data.encode()).hexdigest()[:12]
        
        # РћРїСЂРµРґРµР»СЏРµРј РєР»Р°СЃСЃ РґР»СЏ РЅР°Р·РІР°РЅРёСЏ С‚СѓСЂРЅРёСЂР°
        name_class = self._get_tournament_name_class(tournament_name)

        html = f'''{self.html_head(f"Р Р°СЃРїРёСЃР°РЅРёРµ РјР°С‚С‡РµР№ - {tournament_name}", css_file, 0)}
<body>
    <div class="schedule-container" data-tournament-id="{tournament_id}" data-target-date="{target_date}" data-version="{version}">

        <!-- Header -->
        <div class="header">
            <div class="tournament-name {name_class}">{tournament_name}</div>
            <div class="logos">
                <div class="logo logo4" style="background-image: url('/static/images/logo4.png');"></div>
                <div class="logo logo3" style="background-image: url('/static/images/logo3.png');"></div>
                <div class="logo logo2" style="background-image: url('/static/images/logo2.png');"></div>
                <div class="logo logo1" style="background-image: url('/static/images/logo1.png');"></div>
            </div>
        </div>

        <div class="main-grid">
            <div class="time-scale" style="display: grid; grid-template-rows: repeat({len(time_slots)}, {self.MATCH_HEIGHT}px); gap: {self.GAP}px; padding-top: 36px;">'''
        
        for idx, time_slot in enumerate(time_slots):
            html += f'<div class="time-slot" style="animation-delay: {0.1 + idx * 0.05}s;">{time_slot}</div>'
        
        html += '''</div>
            <div class="courts-container">
                <div class="courts-header" style="grid-template-columns: repeat(''' + str(len(sorted_courts)) + ''', 1fr);">'''
        
        for court_name in sorted_courts:
            html += f'<div class="court-header"><h3>{court_name}</h3></div>'
        
        html += f'''</div>
                <div class="matches-grid" style="display: grid; grid-template-rows: repeat({len(time_slots)}, {self.MATCH_HEIGHT}px); grid-template-columns: repeat({len(sorted_courts)}, 1fr); gap: {self.GAP}px;">'''

        # Р Р°Р·РјРµС‰Р°РµРј РјР°С‚С‡Рё РїРѕ СЃРµС‚РєРµ
        for col_idx, court_name in enumerate(sorted_courts):
            for match in courts_matches[court_name]:
                start_time = match.get("start_time")
                row = time_to_row.get(start_time, 1)
                col = col_idx + 1
                html += self._render_match_item_grid(match, row, col)

        html += '''</div></div></div></div>
    <script src="/static/js/schedule_live.js"></script>
</body></html>'''
        return html

    def _render_match_item_grid(self, match: Dict, row: int, col: int) -> str:
        """Р РµРЅРґРµСЂРёС‚ РјР°С‚С‡ СЃ CSS Grid РїРѕР·РёС†РёРѕРЅРёСЂРѕРІР°РЅРёРµРј Рё РІРµСЂС‚РёРєР°Р»СЊРЅС‹Рј СЂР°СЃРїРѕР»РѕР¶РµРЅРёРµРј РёРјС‘РЅ"""
        status_class = self.get_status_class(self.get_match_status(match))
        
        # РСЃРїРѕР»СЊР·СѓРµРј РїРѕР»РЅС‹Рµ РёРјРµРЅР° РµСЃР»Рё РµСЃС‚СЊ, РёРЅР°С‡Рµ СЃРѕРєСЂР°С‰С‘РЅРЅС‹Рµ
        challenger_full = match.get("ChallengerFullName") or match.get("ChallengerName", "TBD")
        challenged_full = match.get("ChallengedFullName") or match.get("ChallengedName", "TBD")
        #episode = match.get("episode_number", 1)
        episode = ':'

        # РЎС‡С‘С‚ РёР· court_usage
        challenger_result = match.get("ChallengerResult", "") or ""
        challenged_result = match.get("ChallengedResult", "") or ""

        challenger_wo = challenger_result == "Won W.O."
        challenged_wo = challenged_result == "Won W.O."

        if challenger_wo:
            challenger_result = ""
        if challenged_wo:
            challenged_result = ""

        # Р Р°Р·Р±РёРІР°РµРј РёРјРµРЅР° РЅР° РѕС‚РґРµР»СЊРЅС‹С… РёРіСЂРѕРєРѕРІ
        challenger_players = self._split_team_name(challenger_full)
        challenged_players = self._split_team_name(challenged_full)

        def team_html(players: list, wo: bool, result: str) -> str:
            wo_div = "<div class='match-team-wo'>W.O.</div>" if wo else ""
            score_div = f"<div class='match-team-score'>{result}</div>" if result else ""
            
            # Р•СЃР»Рё РѕРґРёРЅ РёРіСЂРѕРє - РёСЃРїРѕР»СЊР·СѓРµРј СЃС‚Р°СЂС‹Р№ С„РѕСЂРјР°С‚
            if len(players) == 1:
                return f'''<div class="match-team">
                    <div class="match-team-name">{players[0]}</div>
                    {wo_div}{score_div}
                </div>'''
            
            # Р•СЃР»Рё РЅРµСЃРєРѕР»СЊРєРѕ РёРіСЂРѕРєРѕРІ - СЂР°СЃРїРѕР»Р°РіР°РµРј РІРµСЂС‚РёРєР°Р»СЊРЅРѕ
            players_html = ''.join(f'<div class="match-player-name">{p}</div>' for p in players[:2])
            return f'''<div class="match-team">
                <div class="match-team-names">{players_html}</div>
                {wo_div}{score_div}
            </div>'''

        return f'''
            <div class="match-item {status_class} row-{row}" style="grid-row: {row}; grid-column: {col};">
                <div class="match-content">
                    <div class="match-number">{episode}</div>
                    <div class="match-teams-wrapper">
                        {team_html(challenger_players, challenger_wo, challenger_result)}
                        {team_html(challenged_players, challenged_wo, challenged_result)}
                    </div>
                </div>
            </div>''' #

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Р“РµРЅРµСЂРёСЂСѓРµС‚ РїСѓСЃС‚СѓСЋ СЃС‚СЂР°РЅРёС†Сѓ СЂР°СЃРїРёСЃР°РЅРёСЏ"""
        name_class = self._get_tournament_name_class(tournament_name)
        
        return f'''{self.html_head(f"Р Р°СЃРїРёСЃР°РЅРёРµ РјР°С‚С‡РµР№ - {tournament_name}", "schedule.css")}
<body>
    <div class="schedule-container">
        <!-- Header -->
        <div class="header">
            <div class="tournament-name {name_class}">{tournament_name}</div>
            <div class="logos">
                <div class="logo logo4" style="background-image: url('/static/images/logo4.png');"></div>
                <div class="logo logo3" style="background-image: url('/static/images/logo3.png');"></div>
                <div class="logo logo2" style="background-image: url('/static/images/logo2.png');"></div>
                <div class="logo logo1" style="background-image: url('/static/images/logo1.png');"></div>
            </div>
        </div>
        <div class="empty-message"><p>{message}</p></div>
    </div>
</body>
</html>'''

