#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Общий модуль парсинга теннисного счёта и данных игроков.
Единый источник правды для rankedin_api.py и rankedin_live.py
"""

from typing import Dict, List


def extract_players(players) -> List[Dict]:
    """Извлечение данных игроков из списка API"""
    if not isinstance(players, list):
        return []
    result = []
    for p in players:
        if not isinstance(p, dict):
            continue
        first = (p.get("firstName") or "").strip()
        last = (p.get("lastName") or "").strip()
        result.append({
            "id": p.get("id", ""),
            "firstName": first,
            "lastName": last,
            "countryCode": p.get("countryCode", ""),
            "fullName": f"{first} {last}".strip(),
            "initialLastName": f"{first[:1]}. {last}".strip() if first and last else ""
        })
    return result


def _convert_game_score(value: int, other: int) -> str:
    """Конвертация очков гейма в теннисный формат (0, 15, 30, 40, AD)"""
    if value <= 3:
        return {0: "0", 1: "15", 2: "30", 3: "40"}.get(value, str(value))
    # Deuce / Advantage
    return "AD" if value > other else "40"


def parse_detailed_result(detailed: List[Dict], is_tiebreak: bool = False,
                          is_super_tiebreak: bool = False,
                          tiebreak_score: tuple = None) -> List[Dict]:
    """
    Парсинг detailed_result из данных rankedin API / SignalR.
    
    Args:
        detailed: список сетов из API
        is_tiebreak: флаг текущего тай-брейка из state
        is_super_tiebreak: флаг супер тай-брейка из state
        tiebreak_score: (score1, score2) текущий счёт тай-брейка
    """
    result = []
    num_sets = len(detailed)

    for i, set_data in enumerate(detailed):
        if not isinstance(set_data, dict):
            continue

        set_info = {
            "firstParticipantScore": set_data.get("firstParticipantScore", 0),
            "secondParticipantScore": set_data.get("secondParticipantScore", 0),
            "loserTiebreak": set_data.get("loserTiebreak")
        }

        games = set_data.get("detailedResult", [])
        is_last_set = (i == num_sets - 1)

        if games:
            last = games[-1] if isinstance(games[-1], dict) else {}
            g1 = last.get("firstParticipantScore", 0)
            g2 = last.get("secondParticipantScore", 0)

            set_score1 = set_data.get("firstParticipantScore", 0)
            set_score2 = set_data.get("secondParticipantScore", 0)

            # Определяем тай-брейк:
            # 1. Обычный тай-брейк (6:6 в сете)
            # 2. Супер тай-брейк (3-й сет с 0:0 и флаг из state)
            # 3. loserTiebreak указан в данных
            is_set_tiebreak = (
                (set_score1 == 6 and set_score2 == 6) or
                (set_score1 == 0 and set_score2 == 0 and is_last_set
                 and (is_tiebreak or is_super_tiebreak)) or
                last.get("loserTiebreak") is not None
            )

            if is_set_tiebreak:
                set_info["gameScore"] = {"first": str(g1), "second": str(g2)}
                set_info["isTieBreak"] = True
                if is_last_set and is_super_tiebreak:
                    set_info["isSuperTieBreak"] = True
            else:
                set_info["gameScore"] = {
                    "first": _convert_game_score(g1, g2),
                    "second": _convert_game_score(g2, g1)
                }

        result.append(set_info)

    return result
