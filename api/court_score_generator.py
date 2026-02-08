#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для генерации XML счета кортов
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Optional
import logging
from .xml_base import XMLBase

logger = logging.getLogger(__name__)


class CourtScoreGenerator(XMLBase):
    """Генератор XML для счета на корте"""

    def generate_court_score_xml(self, court_data: Dict, tournament_data: Dict) -> str:
        """Генерирует XML счета корта"""
        root = ET.Element("templateData")
        
        # Метаинформация турнира
        self._add_tournament_metadata(root, tournament_data)
        
        # Информация о корте
        court = ET.SubElement(root, "court")
        ET.SubElement(court, "id").text = str(court_data.get("court_id", ""))
        ET.SubElement(court, "name").text = court_data.get("court_name", "")
        
        # Текущий матч
        current_match = court_data.get("current_match")
        if current_match:
            self._add_match_data(root, current_match, tournament_data)
        else:
            ET.SubElement(root, "status").text = "no_match"
        
        ET.SubElement(root, "generated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return self._prettify_xml(root)

    def _add_match_data(self, root: ET.Element, match_data: Dict, tournament_data: Dict):
        """Добавляет данные матча"""
        match = ET.SubElement(root, "match")
        
        ET.SubElement(match, "id").text = str(match_data.get("Id", ""))
        ET.SubElement(match, "status").text = match_data.get("Status", "scheduled")
        
        # Участники
        participants = match_data.get("Participants", [])
        if len(participants) >= 2:
            # Участник 1
            p1 = ET.SubElement(match, "participant1")
            self._add_participant_data(p1, participants[0])
            
            # Участник 2
            p2 = ET.SubElement(match, "participant2")
            self._add_participant_data(p2, participants[1])
        
        # Счет
        self._add_score_data(match, match_data)

    def _add_participant_data(self, parent: ET.Element, participant: Dict):
        """Добавляет данные участника"""
        if not participant:
            ET.SubElement(parent, "name").text = "TBD"
            return
        
        ET.SubElement(parent, "seed").text = str(participant.get("Seed", ""))
        
        players = participant.get("Players", [])
        if players:
            names = []
            countries = []
            
            for player in players:
                if isinstance(player, dict):
                    names.append(player.get("Name", ""))
                    country = player.get("CountryShort", "")
                    if country:
                        countries.append(country)
            
            ET.SubElement(parent, "name").text = " / ".join(names)
            if countries:
                ET.SubElement(parent, "country").text = " / ".join(countries)

    def _add_score_data(self, match: ET.Element, match_data: Dict):
        """Добавляет счет матча"""
        sets = match_data.get("Sets", [])
        if not sets:
            return
        
        score = ET.SubElement(match, "score")
        
        # Счет по сетам
        sets_elem = ET.SubElement(score, "sets")
        for idx, set_data in enumerate(sets):
            if isinstance(set_data, dict):
                set_elem = ET.SubElement(sets_elem, "set")
                ET.SubElement(set_elem, "number").text = str(idx + 1)
                ET.SubElement(set_elem, "score1").text = str(set_data.get("Score1", ""))
                ET.SubElement(set_elem, "score2").text = str(set_data.get("Score2", ""))
        
        # Общий счет по сетам
        won_sets_1 = sum(1 for s in sets if isinstance(s, dict) and s.get("Score1", 0) > s.get("Score2", 0))
        won_sets_2 = sum(1 for s in sets if isinstance(s, dict) and s.get("Score2", 0) > s.get("Score1", 0))
        
        ET.SubElement(score, "sets_won_1").text = str(won_sets_1)
        ET.SubElement(score, "sets_won_2").text = str(won_sets_2)
