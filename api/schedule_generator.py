#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для генерации XML расписания турниров
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional
import logging
from .xml_base import XMLBase

logger = logging.getLogger(__name__)


class ScheduleGenerator(XMLBase):
    """Генератор XML для расписания"""

    def generate_schedule_xml(self, tournament_data: Dict) -> str:
        """Генерирует XML расписания турнира"""
        root = ET.Element("templateData")
        
        # Метаинформация
        self._add_tournament_metadata(root, tournament_data)
        
        # Расписание
        schedule = ET.SubElement(root, "schedule")
        
        # Получаем матчи
        matches = self._extract_matches(tournament_data)
        
        # Группируем по датам
        matches_by_date = self._group_matches_by_date(matches)
        
        # Добавляем дни
        for date_str, date_matches in sorted(matches_by_date.items()):
            self._add_day_schedule(schedule, date_str, date_matches)
        
        ET.SubElement(root, "generated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return self._prettify_xml(root)

    def _extract_matches(self, tournament_data: Dict) -> List[Dict]:
        """Извлекает все матчи из турнирных данных"""
        matches = []
        
        draw_data = tournament_data.get("draw_data", {})
        for class_id, class_data in draw_data.items():
            # Round Robin матчи
            if "round_robin" in class_data:
                matches.extend(self._extract_rr_matches(class_data, class_id))
            
            # Elimination матчи
            if "elimination" in class_data:
                matches.extend(self._extract_elim_matches(class_data, class_id))
        
        return matches

    def _extract_rr_matches(self, class_data: Dict, class_id: str) -> List[Dict]:
        """Извлекает матчи из групповых турниров"""
        matches = []
        
        for rr_group in class_data.get("round_robin", []):
            group_data = rr_group.get("RoundRobin", {})
            pool = group_data.get("Pool", [])
            
            for row in pool:
                if not isinstance(row, list):
                    continue
                    
                for cell in row:
                    if isinstance(cell, dict) and cell.get("CellType") == "MatchCell":
                        match_cell = cell.get("MatchCell", {})
                        if match_cell.get("ScheduledTime"):
                            matches.append({
                                "class_id": class_id,
                                "type": "round_robin",
                                "time": match_cell.get("ScheduledTime"),
                                "court": match_cell.get("Court", ""),
                                "participants": self._get_match_participants(match_cell)
                            })
        
        return matches

    def _extract_elim_matches(self, class_data: Dict, class_id: str) -> List[Dict]:
        """Извлекает матчи из турниров на выбывание"""
        matches = []
        
        for elim_stage in class_data.get("elimination", []):
            bracket = elim_stage.get("Bracket", {})
            rounds = bracket.get("Rounds", [])
            
            for round_data in rounds:
                for match_data in round_data.get("Matches", []):
                    if match_data.get("ScheduledTime"):
                        matches.append({
                            "class_id": class_id,
                            "type": "elimination",
                            "round": round_data.get("Name", ""),
                            "time": match_data.get("ScheduledTime"),
                            "court": match_data.get("Court", ""),
                            "participants": self._get_match_participants(match_data)
                        })
        
        return matches

    def _get_match_participants(self, match_data: Dict) -> List[str]:
        """Извлекает имена участников матча"""
        participants = []
        
        for p in match_data.get("Participants", []):
            if p and p.get("Players"):
                player_names = [player.get("Name", "") for player in p["Players"] if player]
                if player_names:
                    participants.append(" / ".join(player_names))
        
        return participants

    def _group_matches_by_date(self, matches: List[Dict]) -> Dict[str, List[Dict]]:
        """Группирует матчи по датам"""
        by_date = {}
        
        for match in matches:
            try:
                time_str = match.get("time", "")
                if time_str:
                    dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d")
                    
                    if date_str not in by_date:
                        by_date[date_str] = []
                    by_date[date_str].append(match)
            except Exception as e:
                logger.warning(f"Ошибка парсинга времени: {e}")
        
        return by_date

    def _add_day_schedule(self, schedule: ET.Element, date_str: str, matches: List[Dict]):
        """Добавляет расписание на день"""
        day = ET.SubElement(schedule, "day")
        ET.SubElement(day, "date").text = date_str
        
        matches_elem = ET.SubElement(day, "matches")
        
        # Сортируем по времени
        sorted_matches = sorted(matches, key=lambda m: m.get("time", ""))
        
        for match in sorted_matches:
            match_elem = ET.SubElement(matches_elem, "match")
            
            try:
                time_str = match.get("time", "")
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                ET.SubElement(match_elem, "time").text = dt.strftime("%H:%M")
            except:
                ET.SubElement(match_elem, "time").text = ""
            
            ET.SubElement(match_elem, "court").text = str(match.get("court", ""))
            ET.SubElement(match_elem, "class").text = str(match.get("class_id", ""))
            
            participants = match.get("participants", [])
            if len(participants) >= 2:
                ET.SubElement(match_elem, "participant1").text = participants[0]
                ET.SubElement(match_elem, "participant2").text = participants[1]
