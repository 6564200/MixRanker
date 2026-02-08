#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый модуль для генерации XML
Содержит общие утилиты и константы
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class XMLBase:
    """Базовый класс для XML генераторов"""

    def __init__(self):
        self.encoding = 'utf-8'

    def _prettify_xml(self, elem: ET.Element) -> str:
        """Форматирует XML для читаемости"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def _add_error_xml(self, root: ET.Element, message: str):
        """Добавляет элемент ошибки в XML"""
        error = ET.SubElement(root, "error")
        error.text = message
        logger.error(f"XML Error: {message}")

    def _get_sport_name(self, sport_id: int) -> str:
        """Возвращает название спорта по ID"""
        sports = {
            1: "Tennis",
            2: "Squash",
            3: "Badminton",
            4: "Table Tennis",
            5: "Padel",
            6: "Beach Tennis",
            7: "Pickle Ball"
        }
        return sports.get(sport_id, "Unknown Sport")

    def _get_country_name(self, country_id: Optional[int]) -> str:
        """Возвращает название страны по ID"""
        if not country_id:
            return ""

        countries = {
            1: "United States",
            7: "Canada",
            33: "France",
            49: "Germany",
            146: "Russia",
            34: "Spain",
            39: "Italy",
            44: "United Kingdom"
        }
        return countries.get(country_id, f"Country_{country_id}")

    def _add_tournament_metadata(self, root: ET.Element, tournament_data: Dict):
        """Добавляет метаинформацию о турнире"""
        metadata = tournament_data.get("metadata", {})
        tournament = ET.SubElement(root, "tournament")
        ET.SubElement(tournament, "id").text = str(tournament_data.get("tournament_id", ""))
        ET.SubElement(tournament, "name").text = metadata.get("name", "Неизвестный турнир")
        ET.SubElement(tournament, "sport").text = self._get_sport_name(metadata.get("sport", 5))
        ET.SubElement(tournament, "country").text = self._get_country_name(metadata.get("country"))
        if metadata.get("featureImage"):
            ET.SubElement(tournament, "banner").text = metadata["featureImage"]
        return tournament

    def _add_class_info(self, root: ET.Element, class_id: int, class_data: Dict, draw_type: str):
        """Добавляет информацию о классе"""
        class_info_elem = ET.SubElement(root, "class")
        ET.SubElement(class_info_elem, "id").text = str(class_id)
        ET.SubElement(class_info_elem, "name").text = class_data.get("class_info", {}).get("Name", f"Категория {class_id}")
        ET.SubElement(class_info_elem, "type").text = draw_type
        return class_info_elem
