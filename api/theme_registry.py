#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from typing import Dict, List

from flask import render_template

from .constants import get_flag_url, get_country_name_ru
from .database import get_db_connection
from .html_base import HTMLBaseGenerator


class ThemeRegistry:
    """
    Реестр тем оформления страниц трансляции.
    Хранит список допустимых тем для каждого типа страницы (_PAGE_THEMES)
    и предоставляет методы валидации и перечисления тем.
    DEFAULT_THEME используется как запасной вариант при неизвестной или пустой теме.
    """
    DEFAULT_THEME = "default"
    _PAGE_THEMES = {
        "vs": {"default", "arena"},
        "winner": {"default", "arena"},
        "scoreboard": {"default", "arena"},
        "scoreboard_full": {"default", "arena"},
        "introduction": {"default", "arena"},
        "next": {"default", "arena"},
        "intro_player": {"default", "arena"},
        "schedule": {"default", "arena"},
        "round_robin": {"default", "arena"},
        "elimination": {"default", "arena"},
    }

    @classmethod
    def normalize_theme(cls, theme: str, page: str) -> str:
        """
        Нормализует и валидирует тему для конкретного типа страницы.
        Если тема пустая или не входит в список допустимых для данного page —
        возвращает DEFAULT_THEME. Сравнение регистронезависимо.
        """
        requested = (theme or "").strip().lower()
        if not requested:
            return cls.DEFAULT_THEME
        allowed = cls._PAGE_THEMES.get(page, {cls.DEFAULT_THEME})
        if requested in allowed:
            return requested
        return cls.DEFAULT_THEME

    @classmethod
    def list_themes(cls, page: str) -> List[str]:
        """Возвращает отсортированный список допустимых тем для указанного типа страницы."""
        return sorted(cls._PAGE_THEMES.get(page, {cls.DEFAULT_THEME}))


def get_window_theme_for_court(tournament_id: str, court_id: str, page: str = "vs") -> str:
    """
    Читает тему из настроек display_window для конкретного корта турнира.
    Ищет активное окно типа 'court' с совпадающими tournament_id и court_id,
    берёт последнее по updated_at/id и извлекает поле settings.theme.
    Результат валидируется через ThemeRegistry.normalize_theme.
    При любой ошибке или отсутствии записи возвращает DEFAULT_THEME.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT settings
            FROM display_windows
            WHERE type = 'court' AND tournament_id = ? AND court_id = ? AND is_active = 1
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (str(tournament_id), str(court_id)),
        )
        row = cursor.fetchone()
        if not row:
            return ThemeRegistry.DEFAULT_THEME

        raw_settings = row["settings"] if hasattr(row, "keys") else row[0]
        settings = json.loads(raw_settings) if raw_settings else {}
        theme = settings.get("theme")
        return ThemeRegistry.normalize_theme(theme, page)
    except Exception:
        return ThemeRegistry.DEFAULT_THEME
    finally:
        conn.close()


def build_vs_view_model(court_data: Dict, tournament_data: Dict, tournament_id: str, court_id: str, theme: str) -> Dict:
    """
    Строит view-model для страницы VS (противостояние двух команд перед матчем или в начале).
    Извлекает до 2 игроков каждой команды, до 3 уже сыгранных сетов (с ненулевым счётом),
    формирует строки имён через HTMLBaseGenerator.format_player_name и добавляет URL флага и фото.
    Внутренняя функция _player_row формирует словарь одного игрока:
      name, flag_url, photo_url, has_photo.
    Возвращает словарь, готовый для передачи в шаблон themes/<theme>/vs.html.
    """
    base = HTMLBaseGenerator()
    team1 = (court_data or {}).get("first_participant", [])[:2]
    team2 = (court_data or {}).get("second_participant", [])[:2]

    detailed = (court_data or {}).get("detailed_result", [])[:3]
    sets = []
    for idx, item in enumerate(detailed):
        first_score = int(item.get("firstParticipantScore", 0) or 0)
        second_score = int(item.get("secondParticipantScore", 0) or 0)
        if first_score > 0 or second_score > 0:
            sets.append({"index": idx + 1, "team1": first_score, "team2": second_score})

    def _player_row(player: Dict) -> Dict:
        photo_url = player.get("photo_url") or "/static/images/silhouette.png"
        return {
            "name": base.format_player_name(player),
            "flag_url": get_flag_url(player.get("countryCode", "")),
            "photo_url": photo_url,
            "has_photo": bool(player.get("photo_url")),
        }

    return {
        "theme": theme,
        "tournament_id": tournament_id or "",
        "court_id": court_id or "",
        "tournament_name": ((tournament_data or {}).get("metadata", {}) or {}).get("name", "TOURNAMENT"),
        "team1": [_player_row(p) for p in team1],
        "team2": [_player_row(p) for p in team2],
        "sets": sets,
    }


def render_vs_themed(court_data: Dict, tournament_data: Dict, tournament_id: str, court_id: str, theme: str) -> str:
    """
    Рендерит HTML-страницу VS для заданной темы.
    Нормализует тему, строит view-model через build_vs_view_model
    и отрисовывает шаблон themes/<theme>/vs.html.
    """
    normalized_theme = ThemeRegistry.normalize_theme(theme, "vs")
    vm = build_vs_view_model(court_data, tournament_data, tournament_id, court_id, normalized_theme)
    return render_template(f"themes/{normalized_theme}/vs.html", **vm)


def build_winner_view_model(court_data: Dict, tournament_id: str, court_id: str, theme: str) -> Dict:
    """
    Строит view-model для страницы победителя.
    Определяет победителя и проигравшего по сравнению счёта сетов (score1 vs score2).
    Внутренняя функция _winner_row формирует словарь игрока-победителя:
      name (fullName), country (на русском), flag_url, photo_url, has_photo.
    Особый случай: код страны 'rin' заменяется на 'ru' для корректного флага.
    Формирует строку loser_name (initialLastName через слеш) и список set_scores ('X/Y' для каждого сета).
    Возвращает словарь, готовый для шаблона themes/<theme>/winner.html.
    """
    first_participant = (court_data or {}).get("first_participant", [])
    second_participant = (court_data or {}).get("second_participant", [])
    score1 = int((court_data or {}).get("first_participant_score", 0) or 0)
    score2 = int((court_data or {}).get("second_participant_score", 0) or 0)

    if score1 > score2:
        winners = first_participant
        losers = second_participant
    else:
        winners = second_participant
        losers = first_participant

    def _winner_row(player: Dict) -> Dict:
        country_code = (player.get("countryCode", "") or "").lower()
        if country_code == "rin":
            country_code = "ru"
        original_country = player.get("countryCode", "")
        return {
            "name": player.get("fullName", ""),
            "country": get_country_name_ru(original_country),
            "flag_url": f"/static/flags/4x3/{country_code}.svg" if country_code else "",
            "photo_url": player.get("photo_url") or "/static/images/silhouette.png",
            "has_photo": bool(player.get("photo_url")),
        }

    loser_names = " / ".join(
        p.get("initialLastName", p.get("lastName", "")) for p in losers[:2]
    )

    detailed = (court_data or {}).get("detailed_result", [])
    set_scores = []
    for idx, item in enumerate(detailed):
        set_scores.append(
            f"{int(item.get('firstParticipantScore', 0) or 0)}/{int(item.get('secondParticipantScore', 0) or 0)}"
        )

    return {
        "theme": theme,
        "tournament_id": tournament_id or "",
        "court_id": court_id or "",
        "court_name": (court_data or {}).get("court_name", "Court"),
        "class_name": (court_data or {}).get("class_name", ""),
        "winners": [_winner_row(p) for p in winners[:2]],
        "loser_name": loser_names,
        "set_scores": set_scores,
        "has_winners": bool(winners),
    }


def render_winner_themed(court_data: Dict, tournament_id: str, court_id: str, theme: str) -> str:
    """
    Рендерит HTML-страницу победителя для заданной темы.
    Нормализует тему, строит view-model через build_winner_view_model
    и отрисовывает шаблон themes/<theme>/winner.html.
    """
    normalized_theme = ThemeRegistry.normalize_theme(theme, "winner")
    vm = build_winner_view_model(court_data, tournament_id, court_id, normalized_theme)
    return render_template(f"themes/{normalized_theme}/winner.html", **vm)


def apply_theme_to_html(html: str, theme: str, page: str) -> str:
    """
    Внедряет тему оформления в готовую HTML-строку без повторного рендеринга шаблона.
    Используется для страниц, которые генерируются не через themed-шаблоны (round_robin, schedule и т.п.).
    Действия:
      1. Вставляет <link> на CSS темы перед </head>,
      2. Добавляет класс 'theme-<name>' к тегу <body> (создаёт атрибут class, если его нет).
    Для DEFAULT_THEME ('default') возвращает HTML без изменений.
    """
    normalized_theme = ThemeRegistry.normalize_theme(theme, page)
    if normalized_theme == ThemeRegistry.DEFAULT_THEME:
        return html

    css_href = f"/static/themes/{normalized_theme}/{page}.css"
    css_link = f'<link rel="stylesheet" href="{css_href}">'

    if "</head>" in html:
        html = html.replace("</head>", f"    {css_link}\n</head>", 1)

    body_marker = "<body"
    body_index = html.find(body_marker)
    if body_index == -1:
        return html

    body_end = html.find(">", body_index)
    if body_end == -1:
        return html

    body_open = html[body_index:body_end + 1]
    if 'class="' in body_open:
        html = html[:body_index] + body_open.replace('class="', f'class="theme-{normalized_theme} ', 1) + html[body_end + 1:]
    else:
        html = html[:body_end] + f' class="theme-{normalized_theme}"' + html[body_end:]

    return html
