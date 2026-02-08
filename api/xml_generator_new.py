#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главный модуль генерации XML файлов для vMix
Объединяет все специализированные генераторы
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict
import logging
from .xml_base import XMLBase
from .round_robin_generator import RoundRobinGenerator
from .elimination_generator import EliminationGenerator
from .schedule_generator import ScheduleGenerator
from .court_score_generator import CourtScoreGenerator

logger = logging.getLogger(__name__)


class XMLGenerator(XMLBase):
    """Главный генератор XML файлов для vMix"""

    def __init__(self):
        super().__init__()
        self.rr_generator = RoundRobinGenerator()
        self.elim_generator = EliminationGenerator()
        self.schedule_generator = ScheduleGenerator()
        self.court_generator = CourtScoreGenerator()

    def generate_tournament_table_xml(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """
        Генерирует XML для турнирной таблицы
        Поддерживает групповые этапы и игры на выбывание
        """
        root = ET.Element("templateData")
        
        # Метаинформация
        self._add_tournament_metadata(root, tournament_data)
        
        # Информация о классе
        class_id = xml_type_info.get("class_id")
        draw_type = xml_type_info.get("draw_type")
        draw_index = xml_type_info.get("draw_index", 0)
        
        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        self._add_class_info(root, class_id, class_data, draw_type)
        
        # Данные турнирной таблицы
        if draw_type == "round_robin":
            self.rr_generator.add_round_robin_data(root, class_data, draw_index)
        elif draw_type == "elimination":
            self.elim_generator.add_elimination_data(root, class_data, draw_index)
        
        ET.SubElement(root, "generated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return self._prettify_xml(root)

    def generate_schedule_xml(self, tournament_data: Dict) -> str:
        """Генерирует XML расписания"""
        return self.schedule_generator.generate_schedule_xml(tournament_data)

    def generate_court_score_xml(self, court_data: Dict, tournament_data: Dict) -> str:
        """Генерирует XML счета корта"""
        return self.court_generator.generate_court_score_xml(court_data, tournament_data)


def generate_bracket_xml(tournament_data: Dict) -> str:
    """Обертка для старого кода"""
    generator = XMLGenerator()
    
    # Пытаемся найти elimination данные
    for class_id, class_data in tournament_data.get("draw_data", {}).items():
        if class_data.get("elimination"):
            xml_type_info = {
                "type": "tournament_table",
                "class_id": class_id,
                "draw_type": "elimination",
                "draw_index": 0
            }
            return generator.generate_tournament_table_xml(tournament_data, xml_type_info)
    
    # Если нет elimination данных, создаем пустой XML
    root = ET.Element("templateData")
    ET.SubElement(root, "error").text = "Нет данных турнирной сетки"
    return generator._prettify_xml(root)
