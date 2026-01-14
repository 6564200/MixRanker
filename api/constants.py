#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Общие константы и утилиты для vMixRanker
Централизованное место для всех справочников и повторяющихся функций
"""

# Спорты
SPORTS = {
    1: "Tennis",
    2: "Squash",
    3: "Badminton",
    4: "Table Tennis",
    5: "Padel",
    6: "Beach Tennis",
    7: "Pickle Ball"
}

# Страны
COUNTRIES = {
    1: "United States", 7: "Canada", 33: "France", 34: "Spain",
    39: "Italy", 44: "United Kingdom", 49: "Germany", 146: "Russia"
}

# Страны на русском
COUNTRIES_RU = {
    'ru': 'Россия', 'rin': 'Россия', 'us': 'США', 'gb': 'Великобритания',
    'de': 'Германия', 'fr': 'Франция', 'es': 'Испания', 'it': 'Италия',
    'br': 'Бразилия', 'ar': 'Аргентина', 'pt': 'Португалия', 'nl': 'Нидерланды',
    'be': 'Бельгия', 'ch': 'Швейцария', 'at': 'Австрия', 'se': 'Швеция',
    'no': 'Норвегия', 'dk': 'Дания', 'fi': 'Финляндия', 'pl': 'Польша',
    'cz': 'Чехия', 'ua': 'Украина', 'by': 'Беларусь', 'kz': 'Казахстан',
    'cn': 'Китай', 'jp': 'Япония', 'kr': 'Южная Корея', 'au': 'Австралия',
    'nz': 'Новая Зеландия', 'za': 'ЮАР', 'eg': 'Египет', 'ae': 'ОАЭ',
    'il': 'Израиль', 'tr': 'Турция', 'gr': 'Греция', 'ro': 'Румыния',
    'bg': 'Болгария', 'rs': 'Сербия', 'hr': 'Хорватия', 'si': 'Словения',
    'sk': 'Словакия', 'hu': 'Венгрия', 'mx': 'Мексика', 'cl': 'Чили',
    'co': 'Колумбия', 'pe': 'Перу', 've': 'Венесуэла', 'uy': 'Уругвай',
    'ec': 'Эквадор', 'ca': 'Канада', 'in': 'Индия', 'pk': 'Пакистан',
    'bd': 'Бангладеш', 'th': 'Таиланд', 'vn': 'Вьетнам', 'id': 'Индонезия',
    'my': 'Малайзия', 'sg': 'Сингапур', 'ph': 'Филиппины', 'ee': 'Эстония',
    'lv': 'Латвия', 'lt': 'Литва', 'md': 'Молдова', 'am': 'Армения',
    'az': 'Азербайджан', 'ge': 'Грузия', 'uz': 'Узбекистан', 'mn': 'Монголия'
}


# Маппинг кодов стран для флагов (3-буквенные → 2-буквенные ISO)
COUNTRY_CODE_MAP = {
    "rin": "ru",
    "rus": "ru", 
    "bra": "br",
    "arg": "ar",
    "esp": "es",
    "ita": "it",
    "fra": "fr",
    "ger": "de",
    "gbr": "gb",
    "usa": "us",
    "den": "dk",
    "dnk": "dk",
}

def get_flag_url(country_code: str) -> str:
    """Возвращает URL флага по коду страны"""
    if not country_code:
        return ""
    code = country_code.lower()
    code = COUNTRY_CODE_MAP.get(code, code)
    return f"https://flagcdn.com/w160/{code}.png"


# XML типы описания
XML_TYPE_DESCRIPTIONS = {
    "court_score": "Актуальный счет и участники матча на корте",
    "tournament_table": "Турнирная таблица с результатами матчей",
    "schedule": "Расписание матчей по дням и времени"
}

XML_UPDATE_FREQUENCIES = {
    "court_score": "Каждый запрос (real-time)",
    "tournament_table": "Каждый запрос",
    "schedule": "Каждый запрос"
}

# Интервал автоперезагрузки по умолчанию (мс)
DEFAULT_RELOAD_INTERVAL = 30000


def get_sport_name(sport_id: int) -> str:
    """Возвращает название спорта по ID"""
    return SPORTS.get(sport_id, "Unknown Sport")


def get_country_name(country_id: int) -> str:
    """Возвращает название страны по ID"""
    if not country_id:
        return ""
    return COUNTRIES.get(country_id, f"Country_{country_id}")


def get_country_name_ru(country_code: str) -> str:
    """Возвращает название страны на русском по коду"""
    return COUNTRIES_RU.get(country_code.lower(), country_code.upper())


def get_xml_type_description(xml_type: str) -> str:
    """Возвращает описание типа XML"""
    return XML_TYPE_DESCRIPTIONS.get(xml_type, "Неизвестный тип XML")


def get_update_frequency(xml_type: str) -> str:
    """Возвращает частоту обновления для типа XML"""
    return XML_UPDATE_FREQUENCIES.get(xml_type, "По запросу")


def get_uptime(start_time: float) -> str:
    """Получение времени работы приложения"""
    import time
    uptime_seconds = time.time() - start_time
    uptime_hours = uptime_seconds // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60
    return f"{int(uptime_hours)}ч {int(uptime_minutes)}м"
