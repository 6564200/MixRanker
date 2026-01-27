#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовые утилиты для генерации HTML
"""

from typing import Dict, List
from datetime import datetime
import logging

from .constants import DEFAULT_RELOAD_INTERVAL, COUNTRY_CODE_MAP, get_flag_url

logger = logging.getLogger(__name__)


class HTMLBaseGenerator:
    """Базовый класс с общими утилитами для HTML генераторов"""

    RELOAD_INTERVAL = DEFAULT_RELOAD_INTERVAL

    @staticmethod
    def get_game_score_display(detailed_result: List[Dict], set_score: int, team: str) -> str:
        
        """Возвращает счет гейма если есть, иначе счет сетов"""
        if detailed_result:
            logger.error(f"detailed_result: {detailed_result}")
            last_set = detailed_result[-1]
            game_score = last_set.get("gameScore")
            if game_score:
                return game_score.get(team, str(set_score))
        return str(set_score)

    @staticmethod
    def get_match_status(match: Dict) -> str:
        """Определяет статус матча"""
        # Finished только если есть результат
        challenger_result = match.get("ChallengerResult")
        challenged_result = match.get("ChallengedResult")
        
        if challenger_result or challenged_result:
            return "finished"

        match_date = match.get("MatchDate", "")
        if not match_date:
            return "future"

        try:
            dt_obj = datetime.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
            now = datetime.now()
            duration = match.get("Duration", 30)

            match_end = dt_obj.replace(minute=dt_obj.minute + duration)
            
            if dt_obj <= now <= match_end:
                return "active"
            elif now > match_end:
                # Время прошло, но результата нет - всё ещё active (идёт игра)
                return "active"
            else:
                return "future"
        except Exception:
            return "future"

    @staticmethod
    def get_status_class(status: str) -> str:
        """Возвращает CSS класс для статуса"""
        return {"finished": "match-finished", "active": "match-active", "future": "match-future"}.get(status, "match-future")

    @staticmethod
    def get_team_name_from_players(first_player: Dict, second_player: Dict) -> str:
        """Формирует название команды из имен игроков"""
        names = [p.get("Name") for p in [first_player, second_player] if p and p.get("Name")]
        return " / ".join(names)

    @staticmethod
    def create_short_name(full_name: str) -> str:
        """Создает сокращенное имя: фамилия"""
        if not full_name or "/" not in full_name:
            return full_name

        short_parts = []
        for part in full_name.split("/"):
            part = part.strip()
            if " " in part:
                name_parts = part.split(" ")
                last_name = " ".join(name_parts[1:]).strip()
                short_parts.append(last_name.replace(' ', '') if last_name else part)
            else:
                short_parts.append(part)

        return " / ".join(short_parts)

    @classmethod
    def html_head(cls, title: str, css_file: str, reload_interval: int = None) -> str:
        """Генерирует стандартный HTML head. reload_interval=0 отключает auto-reload"""
        interval = reload_interval if reload_interval is not None else cls.RELOAD_INTERVAL
        reload_script = f'<script>setInterval(function(){{ location.reload(); }}, {interval});</script>' if interval > 0 else ''
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/{css_file}">
    {reload_script}
</head>'''

    @classmethod
    def empty_page_html(cls, title: str, message: str, css_file: str) -> str:
        """Генерирует пустую HTML страницу с сообщением"""
        return f'''{cls.html_head(title, css_file)}
<body>
    <div class="container">
        <div class="empty-message"><p>{message}</p></div>
    </div>
</body>
</html>'''

    @staticmethod
    def get_flag_url(country_code: str) -> str:
        """Возвращает URL флага по коду страны"""
        return get_flag_url(country_code)

    @staticmethod
    def format_player_name(player: Dict) -> str:
        """Форматирует имя игрока в верхнем регистре"""
        if not player:
            return ""
        full_name = player.get("fullName", "")
        if full_name:
            return full_name.upper()
        first = player.get("firstName", "")
        last = player.get("lastName", "")
        return f"{first} {last}".strip().upper()