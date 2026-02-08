#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для генерации XML турниров на выбывание (Elimination)
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import logging
from .xml_base import XMLBase

logger = logging.getLogger(__name__)


class EliminationGenerator(XMLBase):
    """Генератор XML для турниров на выбывание"""

    def add_elimination_data(self, root: ET.Element, class_data: Dict, draw_index: int):
        """Добавляет данные турнира на выбывание"""
        try:
            if not class_data or not isinstance(class_data, dict):
                logger.error("class_data отсутствует или имеет неверный формат")
                self._add_error_xml(root, "Отсутствуют данные класса")
                return

            elimination_data = class_data.get("elimination", [])
            if not elimination_data or not isinstance(elimination_data, list):
                logger.warning("Нет данных elimination")
                self._add_error_xml(root, "Отсутствуют данные турнира на выбывание")
                return

            if draw_index >= len(elimination_data):
                logger.warning(f"Индекс {draw_index} вне диапазона")
                self._add_error_xml(root, f"Индекс этапа {draw_index} вне диапазона")
                return

            elim_stage = elimination_data[draw_index]
            if not elim_stage or not isinstance(elim_stage, dict):
                logger.warning(f"Данные этапа {draw_index} некорректны")
                self._add_error_xml(root, f"Неверные данные этапа {draw_index}")
                return

            bracket_data = elim_stage.get("Bracket", {})
            if not bracket_data:
                logger.warning("Нет данных Bracket")
                self._add_error_xml(root, "Отсутствует структура Bracket")
                return

            # Создаем структуру bracket
            bracket = ET.SubElement(root, "bracket")
            stage_name = bracket_data.get("Name", "Турнирная сетка")
            ET.SubElement(bracket, "name").text = stage_name

            # Добавляем раунды
            self._add_rounds(bracket, bracket_data)

        except Exception as e:
            logger.error(f"Ошибка при обработке данных на выбывание: {e}", exc_info=True)
            self._add_error_xml(root, f"Ошибка обработки: {str(e)}")

    def _add_rounds(self, bracket: ET.Element, bracket_data: Dict):
        """Добавляет раунды турнира"""
        rounds_data = bracket_data.get("Rounds", [])
        if not rounds_data:
            return

        rounds_elem = ET.SubElement(bracket, "rounds")

        for round_idx, round_data in enumerate(rounds_data):
            if not isinstance(round_data, dict):
                continue

            round_elem = ET.SubElement(rounds_elem, "round")
            ET.SubElement(round_elem, "index").text = str(round_idx)
            ET.SubElement(round_elem, "name").text = round_data.get("Name", f"Раунд {round_idx + 1}")

            # Добавляем матчи раунда
            self._add_matches(round_elem, round_data)

    def _add_matches(self, round_elem: ET.Element, round_data: Dict):
        """Добавляет матчи раунда"""
        matches_data = round_data.get("Matches", [])
        if not matches_data:
            return

        matches_elem = ET.SubElement(round_elem, "matches")

        for match_idx, match_data in enumerate(matches_data):
            if not isinstance(match_data, dict):
                continue

            match_elem = ET.SubElement(matches_elem, "match")
            ET.SubElement(match_elem, "index").text = str(match_idx)
            ET.SubElement(match_elem, "match_id").text = str(match_data.get("Id", ""))

            # Участники
            self._add_match_participants(match_elem, match_data)
            
            # Счет
            self._add_match_score(match_elem, match_data)

    def _add_match_participants(self, match_elem: ET.Element, match_data: Dict):
        """Добавляет участников матча"""
        participants = match_data.get("Participants", [])
        if not participants or len(participants) < 2:
            return

        # Участник 1
        participant1 = participants[0] if len(participants) > 0 else {}
        p1_elem = ET.SubElement(match_elem, "participant1")
        self._add_participant_info(p1_elem, participant1)

        # Участник 2
        participant2 = participants[1] if len(participants) > 1 else {}
        p2_elem = ET.SubElement(match_elem, "participant2")
        self._add_participant_info(p2_elem, participant2)

    def _add_participant_info(self, parent_elem: ET.Element, participant: Dict):
        """Добавляет информацию об участнике"""
        if not participant:
            ET.SubElement(parent_elem, "name").text = "TBD"
            return

        ET.SubElement(parent_elem, "seed").text = str(participant.get("Seed", ""))
        
        players = participant.get("Players", [])
        if players:
            players_elem = ET.SubElement(parent_elem, "players")
            for player in players:
                if isinstance(player, dict):
                    player_elem = ET.SubElement(players_elem, "player")
                    ET.SubElement(player_elem, "name").text = str(player.get("Name", ""))
                    ET.SubElement(player_elem, "country").text = str(player.get("CountryShort", ""))

    def _add_match_score(self, match_elem: ET.Element, match_data: Dict):
        """Добавляет счет матча"""
        sets_data = match_data.get("Sets", [])
        if not sets_data:
            return

        sets_elem = ET.SubElement(match_elem, "sets")
        
        for set_idx, set_data in enumerate(sets_data):
            if isinstance(set_data, dict):
                set_elem = ET.SubElement(sets_elem, "set")
                ET.SubElement(set_elem, "number").text = str(set_idx + 1)
                ET.SubElement(set_elem, "score1").text = str(set_data.get("Score1", ""))
                ET.SubElement(set_elem, "score2").text = str(set_data.get("Score2", ""))
