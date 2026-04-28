#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор HTML страниц расписания матчей
"""

from collections import Counter
from typing import Dict, List, Optional, Set
from datetime import datetime
from .html_base import HTMLBaseGenerator
import hashlib
import logging
import re

logger = logging.getLogger(__name__)


class ScheduleGenerator(HTMLBaseGenerator):
    """Генератор schedule страниц"""
    
    # FHD размеры — определены в schedule.css / schedule_half.css через CSS-переменные

    def _split_team_name(self, team_name: str) -> list:
        """Разбивает имя команды на отдельных игроков"""
        if not team_name:
            return ["TBD"]
        
        # Разделители: "/" или " / "
        if "/" in team_name:
            players = [p.strip() for p in team_name.split("/")]
            return [p for p in players if p]
        
        return [team_name]

    def _get_tournament_name_class(self, name: str) -> str:
        """Определяет CSS класс для названия турнира в зависимости от длины"""
        if len(name) > 40:
            return "very-long-name"
        elif len(name) > 25:
            return "long-name"
        return ""

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None, settings: Dict = None) -> str:
        """Генерирует HTML для расписания матчей"""
        return self._generate_schedule(tournament_data, target_date, "schedule.css", filter_matches=True, settings=settings)

    def generate_schedule_half_html(self, tournament_data: Dict, half: int, target_date: str = None, settings: Dict = None) -> str:
        return self._generate_schedule(tournament_data, target_date, "schedule_half.css", filter_matches=True, settings=settings, half=half)

    @staticmethod
    def _split_courts(sorted_courts: list, half: int) -> list:
        half_size = (len(sorted_courts) + 1) // 2
        if half == 1:
            return sorted_courts[:half_size]
        return sorted_courts[half_size:]

    @staticmethod
    def _schedule_version(tournament_id: str, courts_matches: dict, time_slots: list) -> str:
        """Стабильный хеш версии расписания. Используется и при рендере HTML, и в API данных."""
        parts = [tournament_id]
        for court in sorted(courts_matches.keys()):
            for m in courts_matches[court]:
                parts.append("|".join([
                    str(m.get("TournamentMatchId", "")),
                    str(m.get("ChallengerResult", "") or ""),
                    str(m.get("ChallengedResult", "") or ""),
                    str(m.get("start_time", "")),
                    court,
                ]))
        return hashlib.md5("\n".join(parts).encode()).hexdigest()[:12]

    def get_schedule_data(self, tournament_data: Dict, target_date: str = None, settings: Dict = None, half: int = None) -> Dict:
        """Возвращает данные расписания в формате JSON для AJAX"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        tournament_id = str(tournament_data.get("tournament_id", "") or metadata.get("id", ""))
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return {"error": "Данные расписания не загружены", "matches": [], "courts": [], "time_slots": []}

        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        target_date = target_date or datetime.now().strftime("%d.%m.%Y")

        matches_data = tournament_data.get("matches_data", {})
        draw_data    = tournament_data.get("draw_data", {})
        matches_index = self._build_matches_index(matches_data, court_names_map)
        player_index  = self._build_player_index(matches_data, draw_data)

        courts_matches, all_matches = self._group_matches_by_court(
            court_usage, court_names_map, target_date, matches_index, player_index
        )

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

        if half is not None:
            sorted_courts_all = sorted(courts_matches.keys())
            half_set = set(self._split_courts(sorted_courts_all, half))
            courts_matches = {c: v for c, v in courts_matches.items() if c in half_set}

        time_slots = sorted({m["start_time"] for matches in courts_matches.values() for m in matches})
        sorted_courts = sorted(courts_matches.keys())

        # Формируем список матчей с позициями в сетке
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

        version = self._schedule_version(tournament_id, courts_matches, time_slots)

        return {
            "tournament_name": tournament_name,
            "target_date": target_date,
            "courts": sorted_courts,
            "time_slots": time_slots,
            "matches": matches_list,
            "version": version,
        }

    def _generate_schedule(self, tournament_data: Dict, target_date: str, css_file: str, filter_matches: bool, settings: Dict = None, half: int = None) -> str:
        """Общий метод генерации расписания"""
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        tournament_id = tournament_data.get("tournament_id", "") or metadata.get("id", "")
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        court_names_map = self._build_court_names_map(tournament_data.get("courts", []))
        target_date = target_date or datetime.now().strftime("%d.%m.%Y")

        # Создаём индекс матчей для обогащения данных
        matches_data = tournament_data.get("matches_data", {})
        draw_data    = tournament_data.get("draw_data", {})
        matches_index = self._build_matches_index(matches_data, court_names_map)
        player_index  = self._build_player_index(matches_data, draw_data)

        courts_matches, all_matches = self._group_matches_by_court(
            court_usage, court_names_map, target_date, matches_index, player_index
        )

        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        self._enumerate_matches(courts_matches)

        if filter_matches:
            finished_count = (settings or {}).get("finishedMatchesCount", 3)
            courts_matches = self._filter_matches(courts_matches, finished_count)

        if half is not None:
            sorted_courts_all = sorted(courts_matches.keys())
            half_set = set(self._split_courts(sorted_courts_all, half))
            courts_matches = {c: v for c, v in courts_matches.items() if c in half_set}
            if not courts_matches:
                return self._generate_empty_schedule_html(tournament_name, "No courts for this half")

        # time_slots только из отфильтрованных матчей
        time_slots = sorted({m["start_time"] for matches in courts_matches.values() for m in matches})

        return self._render_schedule_html(tournament_name, tournament_id, target_date, courts_matches, time_slots, css_file, half=half)

    def _build_court_names_map(self, courts_info: List[Dict]) -> Dict[str, str]:
        """Создает карту ID корта -> название"""
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
        for key in ("TournamentMatchId", "TournamentMatchID", "ChallengeId", "MatchId", "Id", "id"):
            value = match.get(key)
            if value not in (None, ""):
                ids.add(str(value))
        return ids

    def _build_matches_index(self, matches_data: Dict, court_names_map: Dict) -> Dict:
        """Создаёт индекс матчей по дате + корту для быстрого поиска"""
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

    # Заглушки — не являются реальными именами, матчируются с чем угодно
    _PENDING_TOKENS = frozenset({"PENDING", "TBD", "BYE", "WO", "WalkOver"})

    @staticmethod
    def _normalize_token(value: str) -> str:
        return re.sub(r"[^0-9A-Za-zА-Яа-я]", "", (value or "")).upper()

    @classmethod
    def _is_pending(cls, abbrev: str) -> bool:
        """True если строка — placeholder неопределённого участника."""
        token = cls._normalize_token(abbrev)
        return bool(token) and token in {cls._normalize_token(t) for t in cls._PENDING_TOKENS}

    def _get_abbrevs_from_name(self, full_name: str) -> set:
        """Получает все возможные сокращения (первые 3 буквы каждого слова)"""
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
        # Заглушка «PENDING» / «TBD» / «BYE» — считаем, что подходит к любому участнику
        if self._is_pending(team_abbrev):
            return True
        parts = [p.strip() for p in re.split(r"[\\/|]", (team_abbrev or "")) if p.strip()]
        ab1 = parts[0] if len(parts) > 0 else ""
        ab2 = parts[1] if len(parts) > 1 else ""
        n1, n2 = self._extract_team_player_names(team_data)

        direct = self._match_abbrev_to_name(ab1, n1) and self._match_abbrev_to_name(ab2, n2)
        swapped = self._match_abbrev_to_name(ab1, n2) and self._match_abbrev_to_name(ab2, n1)
        return direct or swapped

    def _detect_swap(self, match: Dict, challenger_abbrev: str, challenged_abbrev: str) -> bool:
        """Определяет, перевёрнут ли порядок сторон в rich_match относительно court_usage."""
        # Если одна из сторон — заглушка, swap не определить — считаем не перевёрнутым
        if self._is_pending(challenger_abbrev) or self._is_pending(challenged_abbrev):
            return False
        ch = match.get("Challenger", {})
        cd = match.get("Challenged", {})
        same    = self._team_matches(challenger_abbrev, ch) and self._team_matches(challenged_abbrev, cd)
        swapped = self._team_matches(challenger_abbrev, cd) and self._team_matches(challenged_abbrev, ch)
        # Если same и swapped одновременно (имена одинаковые) — считаем не перевёрнутым
        return swapped and not same

    def _find_match_by_abbrev(self, matches_index: Dict, date: str, court_name: str,
                              challenger_abbrev: str, challenged_abbrev: str,
                              source_match: Optional[Dict] = None) -> tuple:
        """Находит матч по дате, корту и сокращениям имён.
        Возвращает (match, is_swapped): is_swapped=True если Challenger/Challenged
        в matches_data стоят в обратном порядке относительно court_usage."""
        if source_match:
            for match_id in self._extract_possible_match_ids(source_match):
                exact = matches_index.get("by_id", {}).get(match_id)
                if exact:
                    return exact, self._detect_swap(exact, challenger_abbrev, challenged_abbrev)

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

            if same_side:
                return match, False
            if swapped_side:
                return match, True

        return None, False

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
        """Форматирует имя участника: П.Фамилия/П.Фамилия"""
        name1, name2 = self._extract_team_player_names(participant)
        
        def format_player(full_name):
            if not full_name:
                return ""
            parts = full_name.split()
            if len(parts) >= 2:
                # Первая буква имени + фамилия (последнее слово)
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
            if re.match(r"^[A-Za-zА-Яа-я]\.[A-Za-zА-Яа-я]+$", part):
                normalized.append(part.upper())
                continue
            token = self._normalize_token(part)
            if token:
                normalized.append(token)

        return "/".join(normalized) if normalized else team_name

    def _build_player_index(self, matches_data, draw_data: Optional[Dict] = None) -> Dict[str, str]:
        """
        Индекс: нормализованный токен имени/фамилии → отформатированное имя команды.
        Строится по участникам из matches_data И из draw_data (elimination brackets).
        Позволяет найти команды с BYE, которых нет в matches_data.

        """
        index: Dict[str, str] = {}

        def _index_participant(participant: dict, formatted: str) -> None:
            n1, n2 = self._extract_team_player_names(participant)
            for name in filter(None, [n1, n2]):
                for token in self._get_abbrevs_from_name(name):
                    if token not in index:
                        index[token] = formatted

        # ── Источник 1: matches_data ──────────────────────────────────────────
        matches_list = matches_data.get("Matches", []) if isinstance(matches_data, dict) else []
        for match in matches_list:
            for side in ("Challenger", "Challenged"):
                participant = match.get(side) or {}
                if not isinstance(participant, dict):
                    continue
                formatted = self._format_full_name(participant)
                if not formatted or formatted == "TBD":
                    continue
                _index_participant(participant, formatted)

        # ── Источник 2: draw_data (elimination brackets) ──────────────────────
        # Здесь есть сеяные команды с BYE, которых нет в matches_data
        if draw_data and isinstance(draw_data, dict):
            for class_data in draw_data.values():
                if not isinstance(class_data, dict):
                    continue
                for elim in class_data.get("elimination", []):
                    if not isinstance(elim, dict):
                        continue
                    bracket = elim.get("Elimination", {})
                    draw_rounds = bracket.get("DrawData", [])
                    for round_matches in draw_rounds:
                        if not isinstance(round_matches, list):
                            continue
                        for match in round_matches:
                            if not isinstance(match, dict):
                                continue
                            for side in ("ChallengerParticipant", "ChallengedParticipant"):
                                p = match.get(side) or {}
                                if not isinstance(p, dict):
                                    continue
                                # Структура: {FirstPlayer: {Name: "..."}, SecondPlayer: {Name: "..."}}
                                # _extract_team_player_names поддерживает Variant B (FirstPlayer/SecondPlayer)
                                formatted = self._format_full_name(p)
                                if not formatted or formatted == "TBD":
                                    continue
                                _index_participant(p, formatted)

        return index

    def _lookup_full_name_by_abbrev(self, team_abbrev: str, player_index: Dict[str, str]) -> Optional[str]:
        """
        Ищет полное имя команды по сокращению из court_usage (например "Мария/Дмитр").
        Каждая часть аббревиатуры ищется в player_index.
        Возвращает наиболее часто встречающийся кандидат, или None если не найден.
        """
        if not team_abbrev or self._is_pending(team_abbrev):
            return None

        parts = [p.strip() for p in re.split(r"[\\/|]", team_abbrev) if p.strip()]
        if not parts:
            return None

        candidates = []
        for part in parts:
            token = self._normalize_token(part)
            if token and token in player_index:
                candidates.append(player_index[token])

        if not candidates:
            return None

        most_common, _ = Counter(candidates).most_common(1)[0]
        return most_common

    def _format_detailed_score(self, match_result: Dict) -> str:
        """Форматирует детальный счёт из MatchResult"""
        if not match_result:
            return ""
        
        score = match_result.get("Score", {})
        if not score:
            return ""
        
        detailed = score.get("DetailedScoring", [])
        if not detailed:
            # Возвращаем общий счёт
            p1 = score.get("FirstParticipantScore", "")
            p2 = score.get("SecondParticipantScore", "")
            if p1 != "" and p2 != "":
                return f"{p1}-{p2}"
            return ""
        
        # Форматируем по сетам
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
                                 target_date: str, matches_index: Dict,
                                 player_index: Optional[Dict[str, str]] = None) -> tuple:
        """Группирует матчи по кортам и фильтрует по дате.

        Двухпроходное обогащение:
        1. Все матчи, у которых нашёлся rich_match, разрешаются немедленно;
           их аббревиатуры → полные имена сохраняются в abbrev_to_full.
        2. Матчи без rich_match (будущие раунды) ищут свои аббревиатуры
           в abbrev_to_full (прямое совпадение строки из court_usage),
           затем — в player_index (поиск по токенам), затем — сырой fallback.
        """
        # ── Проход 1: разрешаем известные матчи и строим словарь аббревиатур ──

        # abbrev_to_full: точная строка ChallengerName/ChallengedName из court_usage
        #                 → отформатированное полное имя команды
        abbrev_to_full: Dict[str, str] = {}

        pending_matches: List[Dict] = []   # матчи без rich_match (для 2-го прохода)
        all_matches:     List[Dict] = []
        courts_matches:  Dict[str, List] = {}

        for raw_match in court_usage:
            if not isinstance(raw_match, dict):
                continue

            match = dict(raw_match)  # копия — не мутируем кэшированный объект

            match_date = match.get("MatchDate", "")
            if not match_date:
                continue

            try:
                dt_obj = datetime.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                if dt_obj.strftime("%d.%m.%Y") != target_date:
                    continue

                # Матчи с временем ≥ 22:00 — технические W.O.-записи с дефолтным timestamp,
                # не реальные игры. Исключаем из расписания.
                if dt_obj.hour >= 22:
                    continue

                court_id   = str(match.get("CourtId", ""))
                court_name = court_names_map.get(court_id, f"Корт {court_id}")

                match["start_time"]    = dt_obj.strftime("%H:%M")
                match["date_formatted"] = dt_obj.strftime("%d.%m.%Y")
                match["court_name"]    = court_name
                match["datetime_obj"]  = dt_obj

                challenger_abbrev = match.get("ChallengerName", "")
                challenged_abbrev = match.get("ChallengedName", "")

                rich_match, is_swapped = self._find_match_by_abbrev(
                    matches_index, match_date, court_name,
                    challenger_abbrev, challenged_abbrev, source_match=match
                )

                if rich_match:
                    # Если стороны перевёрнуты в matches_data — берём имена в обратном порядке,
                    # чтобы они соответствовали ChallengerResult/ChallengedResult из court_usage
                    if is_swapped:
                        ch_full = self._format_full_name(rich_match.get("Challenged", {}))
                        cd_full = self._format_full_name(rich_match.get("Challenger", {}))
                    else:
                        ch_full = self._format_full_name(rich_match.get("Challenger", {}))
                        cd_full = self._format_full_name(rich_match.get("Challenged", {}))

                    # Сохраняем placeholder из court_usage, если rich_match не даёт реального имени
                    if ch_full == "TBD" and self._is_pending(challenger_abbrev):
                        ch_full = challenger_abbrev.strip()
                    if cd_full == "TBD" and self._is_pending(challenged_abbrev):
                        cd_full = challenged_abbrev.strip()

                    # Запоминаем соответствие аббревиатура → полное имя для 2-го прохода
                    if not self._is_pending(challenger_abbrev) and ch_full and ch_full != "TBD":
                        abbrev_to_full[challenger_abbrev] = ch_full
                    if not self._is_pending(challenged_abbrev) and cd_full and cd_full != "TBD":
                        abbrev_to_full[challenged_abbrev] = cd_full

                    match["ChallengerFullName"] = ch_full
                    match["ChallengedFullName"] = cd_full
                    match["DetailedScore"]      = self._format_detailed_score(rich_match.get("MatchResult", {}))
                    match["RichMatchData"]      = rich_match
                else:
                    # Отложим на 2-й проход
                    pending_matches.append(match)

                all_matches.append(match)
                courts_matches.setdefault(court_name, []).append(match)

            except Exception:
                continue

        # ── Проход 2: разрешаем отложенные матчи ──────────────────────────────

        pi = player_index or {}

        for match in pending_matches:
            challenger_abbrev = match.get("ChallengerName", "")
            challenged_abbrev = match.get("ChallengedName", "")

            def _resolve(abbrev: str) -> str:
                if self._is_pending(abbrev):
                    return abbrev.strip()
                # 1. Точное совпадение строки из court_usage (из 1-го прохода)
                if abbrev in abbrev_to_full:
                    return abbrev_to_full[abbrev]
                # 2. Поиск по токенам имён через player_index (включает draw_data)
                found = self._lookup_full_name_by_abbrev(abbrev, pi)
                if found:
                    return found
                # 3. Сырой fallback: нормализованная аббревиатура
                return self._format_abbrev_team_fallback(abbrev)

            match["ChallengerFullName"] = _resolve(challenger_abbrev)
            match["ChallengedFullName"] = _resolve(challenged_abbrev)

        return courts_matches, all_matches

    def _enumerate_matches(self, courts_matches: Dict):
        """Сортирует и нумерует матчи"""
        for court_name, matches in courts_matches.items():
            matches.sort(key=lambda x: x.get("datetime_obj"))
            for i, match in enumerate(matches, 1):
                match["episode_number"] = i

    def _filter_matches(self, courts_matches: Dict, finished_count: int = 3) -> Dict:
        """
        Фильтрует матчи по каждому корту независимо:
        показывает последние N сыгранных + все предстоящие.
        """
        if not courts_matches:
            return {}

        filtered = {}
        for court_name, matches in courts_matches.items():
            with_results = sorted(
                [m for m in matches if m.get("ChallengerResult") or m.get("ChallengedResult")],
                key=lambda x: x.get("datetime_obj") or datetime.min
            )

            if len(with_results) >= finished_count:
                cutoff = with_results[-finished_count].get("datetime_obj")
            elif with_results:
                cutoff = with_results[0].get("datetime_obj")
            else:
                # Нет сыгранных — показываем все
                filtered[court_name] = list(matches)
                continue

            filtered[court_name] = [
                m for m in matches
                if m.get("datetime_obj") and m.get("datetime_obj") >= cutoff
            ]

        return filtered

    def _render_schedule_html(self, tournament_name: str, tournament_id: str, target_date: str, courts_matches: Dict, time_slots: List, css_file: str, half: int = None) -> str:
        """Рендерит HTML расписания — матчи последовательно по кортам"""
        sorted_courts = sorted(courts_matches.keys())

        version = self._schedule_version(tournament_id, courts_matches, time_slots)
        name_class = self._get_tournament_name_class(tournament_name)

        html = f'''{self.html_head(f"Расписание матчей - {tournament_name}", css_file, 0)}
<body>
    <div class="schedule-container" data-tournament-id="{tournament_id}" data-target-date="{target_date}" data-version="{version}"{(' data-half="' + str(half) + '"') if half else ''}>

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

        <div class="main-grid" style="--court-cols: {len(sorted_courts)};">
            <div class="courts-container">
                <div class="courts-header">'''

        for court_name in sorted_courts:
            html += f'<div class="court-header"><h3>{court_name}</h3></div>'

        html += '</div><div class="matches-grid">'

        for court_name in sorted_courts:
            html += '<div class="court-column">'
            for match in courts_matches[court_name]:
                html += self._render_match_item_grid(match)
            html += '</div>'

        js_file = "schedule_half_live.js" if css_file == "schedule_half.css" else "schedule_live.js"
        html += f'</div></div></div></div>\n    <script src="/static/js/{js_file}"></script>\n</body></html>'
        return html

    def _render_match_item_grid(self, match: Dict) -> str:
        """Рендерит матч — последовательное расположение без grid-позиционирования"""
        status_class = self.get_status_class(self.get_match_status(match))

        challenger_full = match.get("ChallengerFullName") or match.get("ChallengerName", "TBD")
        challenged_full = match.get("ChallengedFullName") or match.get("ChallengedName", "TBD")

        challenger_result = match.get("ChallengerResult", "") or ""
        challenged_result = match.get("ChallengedResult", "") or ""

        challenger_wo = challenger_result == "Won W.O."
        challenged_wo = challenged_result == "Won W.O."

        # "Won R" — победа из-за снятия соперника (retirement): показываем бейдж R.
        challenger_ret = challenger_result == "Won R"
        challenged_ret = challenged_result == "Won R"

        if challenger_wo or challenger_ret:
            challenger_result = ""
        if challenged_wo or challenged_ret:
            challenged_result = ""

        challenger_players = self._split_team_name(challenger_full)
        challenged_players = self._split_team_name(challenged_full)

        def team_html(players: list, wo: bool, ret: bool, result: str) -> str:
            wo_div  = "<div class='match-team-wo'>W.O.</div>"  if wo  else ""
            ret_div = "<div class='match-team-ret'>Ret.</div>" if ret else ""
            score_div = f"<div class='match-team-score'>{result}</div>" if result else ""
            if len(players) == 1:
                return f'<div class="match-team"><div class="match-team-name">{players[0]}</div>{wo_div}{ret_div}{score_div}</div>'
            players_html = "".join(f'<div class="match-player-name">{p}</div>' for p in players[:2])
            return f'<div class="match-team"><div class="match-team-names">{players_html}</div>{wo_div}{ret_div}{score_div}</div>'

        return (f'<div class="match-item {status_class}">'
                f'<div class="match-content">'
                f'<div class="match-teams-wrapper">'
                f'{team_html(challenger_players, challenger_wo, challenger_ret, challenger_result)}'
                f'{team_html(challenged_players, challenged_wo, challenged_ret, challenged_result)}'
                f'</div></div></div>')

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Генерирует пустую страницу расписания"""
        name_class = self._get_tournament_name_class(tournament_name)
        
        return f'''{self.html_head(f"Расписание матчей - {tournament_name}", "schedule.css")}
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

