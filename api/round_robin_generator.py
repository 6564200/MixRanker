#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для генерации XML групповых турниров (Round Robin)
"""

import xml.etree.ElementTree as ET
from typing import Dict, List
import logging
from .xml_base import XMLBase

logger = logging.getLogger(__name__)


class RoundRobinGenerator(XMLBase):
    """Генератор XML для групповых турниров"""

    def add_round_robin_data(self, root: ET.Element, class_data: Dict, draw_index: int):
        """Добавляет данные группового этапа"""
        try:
            # Проверка входных данных
            if not class_data or not isinstance(class_data, dict):
                logger.error("class_data отсутствует или имеет неверный формат")
                self._add_error_xml(root, "Отсутствуют данные класса")
                return

            round_robin_data = class_data.get("round_robin", [])
            if not round_robin_data or not isinstance(round_robin_data, list):
                logger.warning("Нет данных round_robin или неверный формат")
                self._add_error_xml(root, "Отсутствуют данные групповых турниров")
                return

            if draw_index >= len(round_robin_data):
                logger.warning(f"Индекс {draw_index} превышает количество групповых данных ({len(round_robin_data)})")
                self._add_error_xml(root, f"Индекс группы {draw_index} вне диапазона")
                return

            rr_data = round_robin_data[draw_index]
            if not rr_data or not isinstance(rr_data, dict):
                logger.warning(f"Данные группы {draw_index} отсутствуют или имеют неверный формат")
                self._add_error_xml(root, f"Неверные данные группы {draw_index}")
                return

            if "RoundRobin" not in rr_data:
                logger.warning("Нет данных RoundRobin в групповых данных")
                self._add_error_xml(root, "Отсутствует структура RoundRobin")
                return

            group_data = rr_data["RoundRobin"]
            if not group_data or not isinstance(group_data, dict):
                logger.warning("Данные RoundRobin отсутствуют или имеют неверный формат")
                self._add_error_xml(root, "Неверная структура RoundRobin")
                return

            # Создаем DataTab
            data_tab = ET.SubElement(root, "DataTab")
            matches = ET.SubElement(data_tab, "matches")

            # Базовая информация о группе
            group_name = group_data.get("Name", "Группа")
            ET.SubElement(matches, "classes").text = str(group_name)
            ET.SubElement(matches, "type").text = "Групповой турнир"

            # Извлекаем и добавляем участников
            participants_list = self._extract_participants(group_data, matches)
            
            # Добавляем таблицу результатов
            self._add_results_table(matches, group_data, participants_list)

        except Exception as e:
            logger.error(f"Ошибка при обработке групповых данных: {e}", exc_info=True)
            self._add_error_xml(root, f"Ошибка обработки: {str(e)}")

    def _extract_participants(self, group_data: Dict, matches: ET.Element) -> List[Dict]:
        """Извлекает участников из Pool данных"""
        participants_list = []

        try:
            pool_data = group_data.get("Pool", [])
            if not pool_data or not isinstance(pool_data, list):
                logger.warning("Нет данных Pool или неверный формат")
                ET.SubElement(matches, "error").text = "Отсутствуют данные участников"
                return participants_list

            for row in pool_data:
                if not isinstance(row, list):
                    continue

                for cell in row:
                    if not isinstance(cell, dict):
                        continue

                    if cell.get("CellType") == "ParticipantCell" and cell.get("ParticipantCell"):
                        participant_cell = cell["ParticipantCell"]
                        if not isinstance(participant_cell, dict):
                            continue

                        if participant_cell.get("Players") and isinstance(participant_cell["Players"], list):
                            participant_info = {
                                "index": participant_cell.get("Index", 0),
                                "seed": participant_cell.get("Seed", ""),
                                "players": []
                            }

                            for player in participant_cell["Players"]:
                                if isinstance(player, dict):
                                    participant_info["players"].append({
                                        "id": str(player.get("Id", "")),
                                        "name": str(player.get("Name", "")),
                                        "rankedin_id": str(player.get("RankedinId", "")),
                                        "country": str(player.get("CountryShort", "")),
                                        "rating_begin": player.get("RatingBegin", 0) or 0,
                                        "rating_end": player.get("RatingEnd", 0) or 0
                                    })

                            if participant_info["players"]:
                                participants_list.append(participant_info)

        except Exception as e:
            logger.error(f"Ошибка извлечения участников: {e}", exc_info=True)

        return participants_list

    def _add_results_table(self, matches: ET.Element, group_data: Dict, participants_list: List[Dict]):
        """Добавляет таблицу результатов"""
        try:
            pool_data = group_data.get("Pool", [])
            if not pool_data:
                return

            # Строки таблицы
            for row_idx, row in enumerate(pool_data):
                if not isinstance(row, list) or row_idx == 0:
                    continue

                row_elem = ET.SubElement(matches, f"row_{row_idx}")
                
                for cell_idx, cell in enumerate(row):
                    if not isinstance(cell, dict):
                        continue

                    cell_type = cell.get("CellType", "")
                    
                    if cell_type == "ParticipantCell" and cell.get("ParticipantCell"):
                        self._add_participant_cell(row_elem, cell["ParticipantCell"])
                    elif cell_type == "StandingCell" and cell.get("StandingCell"):
                        self._add_standing_cell(row_elem, cell["StandingCell"])
                    elif cell_type == "MatchCell" and cell.get("MatchCell"):
                        self._add_match_cell(row_elem, cell["MatchCell"], cell_idx)

        except Exception as e:
            logger.error(f"Ошибка добавления таблицы результатов: {e}", exc_info=True)

    def _add_participant_cell(self, row_elem: ET.Element, participant_cell: Dict):
        """Добавляет ячейку участника"""
        participant = ET.SubElement(row_elem, "participant")
        ET.SubElement(participant, "seed").text = str(participant_cell.get("Seed", ""))
        
        players_elem = ET.SubElement(participant, "players")
        for player in participant_cell.get("Players", []):
            if isinstance(player, dict):
                player_elem = ET.SubElement(players_elem, "player")
                ET.SubElement(player_elem, "name").text = str(player.get("Name", ""))
                ET.SubElement(player_elem, "country").text = str(player.get("CountryShort", ""))

    def _add_standing_cell(self, row_elem: ET.Element, standing_cell: Dict):
        """Добавляет ячейку позиции"""
        standing = ET.SubElement(row_elem, "standing")
        ET.SubElement(standing, "position").text = str(standing_cell.get("Position", ""))
        ET.SubElement(standing, "played").text = str(standing_cell.get("Played", 0))
        ET.SubElement(standing, "won").text = str(standing_cell.get("Won", 0))
        ET.SubElement(standing, "lost").text = str(standing_cell.get("Lost", 0))
        ET.SubElement(standing, "points").text = str(standing_cell.get("Points", 0))

    def _add_match_cell(self, row_elem: ET.Element, match_cell: Dict, cell_idx: int):
        """Добавляет ячейку матча"""
        match = ET.SubElement(row_elem, f"match_{cell_idx}")
        
        if match_cell.get("Sets") and isinstance(match_cell["Sets"], list):
            sets_elem = ET.SubElement(match, "sets")
            for set_data in match_cell["Sets"]:
                if isinstance(set_data, dict):
                    set_elem = ET.SubElement(sets_elem, "set")
                    ET.SubElement(set_elem, "score1").text = str(set_data.get("Score1", ""))
                    ET.SubElement(set_elem, "score2").text = str(set_data.get("Score2", ""))
