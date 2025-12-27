#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Утилиты для работы с фото участников"""

import logging
from typing import Dict, List

from .database import execute_with_retry

logger = logging.getLogger(__name__)


def get_photo_urls_for_ids(player_ids: List[int]) -> Dict[int, str]:
    """
    Получает photo_url для списка ID игроков.
    Возвращает словарь {id: photo_url}
    """
    if not player_ids:
        return {}

    def transaction(conn):
        cursor = conn.cursor()
        placeholders = ','.join('?' for _ in player_ids)
        cursor.execute(f'''
            SELECT id, photo_url
            FROM participants
            WHERE id IN ({placeholders})
        ''', tuple(player_ids))

        return {row[0]: row[1] for row in cursor.fetchall() if row[1]}

    try:
        return execute_with_retry(transaction)
    except Exception as e:
        logger.error(f"Ошибка получения photo_url: {e}")
        return {}


def extract_player_ids(court_data: Dict) -> tuple:
    """
    Извлекает ID игроков из данных корта.
    Возвращает (team1_ids, team2_ids)
    """
    team1_players = court_data.get("first_participant", [])
    team2_players = court_data.get("second_participant", [])

    team1_ids = [p.get("id") for p in team1_players if p.get("id")]
    team2_ids = [p.get("id") for p in team2_players if p.get("id")]

    return team1_ids, team2_ids


def enrich_players_with_photos(players: List[Dict], photo_map: Dict[int, str]) -> None:
    """
    Добавляет photo_url к игрокам на месте.
    Модифицирует список players.
    """
    for player in players:
        player_id = player.get('id')
        if player_id and player_id in photo_map:
            player['photo_url'] = photo_map[player_id]


def enrich_court_data_with_photos(court_data: Dict) -> Dict:
    """
    Обогащает данные корта фотографиями игроков.
    Возвращает модифицированный court_data.
    """
    team1_ids, team2_ids = extract_player_ids(court_data)
    all_ids = team1_ids + team2_ids

    if not all_ids:
        return court_data

    photo_map = get_photo_urls_for_ids(all_ids)

    team1_players = court_data.get("first_participant", [])
    team2_players = court_data.get("second_participant", [])

    enrich_players_with_photos(team1_players, photo_map)
    enrich_players_with_photos(team2_players, photo_map)

    return court_data


def get_participant_photo_url(participant_id: int) -> str:
    """Получает photo_url для одного участника"""
    photos = get_photo_urls_for_ids([participant_id])
    return photos.get(participant_id, "")


def get_participant_info(participant_id: int) -> Dict:
    """Получает полную информацию об участнике"""
    def transaction(conn):
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, first_name, last_name, country_code, photo_url, info
            FROM participants
            WHERE id = ?
        ''', (participant_id,))

        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "firstName": row[1],
                "lastName": row[2],
                "countryCode": row[3],
                "photo_url": row[4],
                "info": row[5]
            }
        return None

    try:
        return execute_with_retry(transaction)
    except Exception as e:
        logger.error(f"Ошибка получения участника {participant_id}: {e}")
        return None
