#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовые утилиты для генерации HTML
"""

from typing import Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


class HTMLBaseGenerator:
    """Базовый класс с общими утилитами для HTML генераторов"""
    
    AUTO_RELOAD_INTERVAL = 30000  # миллисекунды
    
    @staticmethod
    def get_game_score_display(detailed_result: List[Dict], set_score: int, team: str) -> str:
        """Возвращает счет гейма если есть, иначе счет сетов"""
        if detailed_result and len(detailed_result) > 0:
            last_set = detailed_result[-1]
            game_score = last_set.get("gameScore")
            if game_score:
                return game_score.get(team, str(set_score))
        return str(set_score)

    @staticmethod
    def get_match_status(match: Dict) -> str:
        """Определяет статус матча"""
        challenger_result = match.get("ChallengerResult", "")
        challenged_result = match.get("ChallengedResult", "")
        
        if challenger_result and challenged_result:
            return "finished"
        
        try:
            match_date = match.get("MatchDate", "")
            if match_date:
                dt_obj = datetime.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                now = datetime.now()
                duration = match.get("Duration", 30)
                
                if dt_obj <= now <= dt_obj.replace(minute=dt_obj.minute + duration):
                    return "active"
                elif dt_obj > now:
                    return "future"
                else:
                    return "finished"
        except:
            pass
        return "future"

    @staticmethod
    def get_status_class(status: str) -> str:
        """Возвращает CSS класс для статуса"""
        return {
            "finished": "match-finished",
            "active": "match-active",
            "future": "match-future"
        }.get(status, "match-future")

    @staticmethod
    def get_team_name_from_players(first_player: Dict, second_player: Dict) -> str:
        """Формирует название команды из имен игроков"""
        names = []
        if first_player and first_player.get("Name"):
            names.append(first_player["Name"])
        if second_player and second_player.get("Name"):
            names.append(second_player["Name"])
        return "/".join(names)

    @staticmethod
    def create_short_name(full_name: str) -> str:
        """Создает сокращенное имя: фамилия"""
        if not full_name or "/" not in full_name:
            return full_name
        
        parts = full_name.split("/")
        short_parts = []
        
        for part in parts:
            part = part.strip()
            if " " in part:
                name_parts = part.split(" ")
                last_name = " ".join(name_parts[1:]).strip()
                if last_name:
                    short_parts.append(last_name.replace(' ', ''))
                else:
                    short_parts.append(part)
            else:
                short_parts.append(part)
        
        return "/".join(short_parts)

    @staticmethod
    def format_score_summary(score_data: Dict) -> str:
        """Форматирует итоговый счет"""
        if not score_data:
            return ""
        first_score = score_data.get("FirstParticipantScore", 0)
        second_score = score_data.get("SecondParticipantScore", 0)
        return f"{first_score}-{second_score}"

    @staticmethod
    def format_sets_summary(score_data: Dict) -> str:
        """Форматирует детальный счет по сетам"""
        if not score_data or not score_data.get("DetailedScoring"):
            return ""
        
        sets_summary = []
        for set_data in score_data["DetailedScoring"]:
            set_first = set_data.get("FirstParticipantScore", 0)
            set_second = set_data.get("SecondParticipantScore", 0)
            sets_summary.append(f"{set_first}-{set_second}")
        
        return " ".join(sets_summary)

    @staticmethod
    def html_head(title: str, css_file: str, reload_interval: int = 30000) -> str:
        """Генерирует стандартный HTML head"""
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/{css_file}">
    <script>
        setInterval(function() {{
            location.reload();
        }}, {reload_interval});
    </script>
</head>'''

    @staticmethod
    def empty_page_html(title: str, message: str, css_file: str) -> str:
        """Генерирует пустую HTML страницу с сообщением"""
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/{css_file}">
    <script>
        setInterval(function() {{
            location.reload();
        }}, 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="empty-message">
            <p>{message}</p>
        </div>
    </div>
</body>
</html>'''
