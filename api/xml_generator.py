#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации XML файлов для vMix
Создает XML файлы на основе данных турниров rankedin.com
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class XMLGenerator:
    """Генератор XML файлов для vMix"""
    
    def __init__(self):
        self.encoding = 'utf-8'
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Форматирует XML для читаемости"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def generate_tournament_table_xml(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """
        Генерирует XML для турнирной таблицы
        Поддерживает групповые этапы и игры на выбывание
        """
        root = ET.Element("templateData")
        
        # Метаинформация
        metadata = tournament_data.get("metadata", {})
        tournament = ET.SubElement(root, "tournament")
        ET.SubElement(tournament, "id").text = str(tournament_data.get("tournament_id", ""))
        ET.SubElement(tournament, "name").text = metadata.get("name", "Неизвестный турнир")
        ET.SubElement(tournament, "sport").text = self._get_sport_name(metadata.get("sport", 5))
        ET.SubElement(tournament, "country").text = self._get_country_name(metadata.get("country"))
        if metadata.get("featureImage"):
            ET.SubElement(tournament, "banner").text = metadata["featureImage"]
        
        # Информация о классе
        class_id = xml_type_info.get("class_id")
        draw_type = xml_type_info.get("draw_type")
        draw_index = xml_type_info.get("draw_index", 0)
        
        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        class_info_elem = ET.SubElement(root, "class")
        ET.SubElement(class_info_elem, "id").text = str(class_id)
        ET.SubElement(class_info_elem, "name").text = class_data.get("class_info", {}).get("Name", f"Категория {class_id}")
        ET.SubElement(class_info_elem, "type").text = draw_type
        
        # Данные турнирной таблицы
        if draw_type == "round_robin":
            self._add_round_robin_data(root, class_data, draw_index)
        elif draw_type == "elimination":
            self._add_elimination_data(root, class_data, draw_index)
        
        # Время генерации (обновляется каждый раз)
        ET.SubElement(root, "generated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return self._prettify_xml(root)

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
        """Возвращает название страны по ID (упрощенная версия)"""
        if not country_id:
            return ""
        
        # Некоторые популярные страны
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

    def _add_round_robin_data(self, root: ET.Element, class_data: Dict, draw_index: int):
        """Добавляет данные группового этапа в новом формате"""
        try:
            # Проверяем входные данные
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
            
            # Создаем DataTab вместо group
            data_tab = ET.SubElement(root, "DataTab")
            matches = ET.SubElement(data_tab, "matches")
            
            # Базовая информация о группе
            group_name = group_data.get("Name", "Группа")
            ET.SubElement(matches, "classes").text = str(group_name)
            ET.SubElement(matches, "type").text = "Групповой турнир"
            
            # Собираем участников из Pool данных
            participants_list = []
            
            try:
                # Извлекаем участников из Pool структуры
                pool_data = group_data.get("Pool", [])
                if not pool_data or not isinstance(pool_data, list):
                    logger.warning("Нет данных Pool или неверный формат")
                    ET.SubElement(matches, "error").text = "Отсутствуют данные участников"
                    return
                    
                for row_index, row in enumerate(pool_data):
                    if not isinstance(row, list):
                        continue
                        
                    for cell_index, cell in enumerate(row):
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
                                
                                # Игроки в паре
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
                                
                                if participant_info["players"]:  # Добавляем только если есть игроки
                                    participants_list.append(participant_info)
                
                # Сортируем участников по индексу
                participants_list.sort(key=lambda x: x.get("index", 0))
                
                # Добавляем информацию об участниках в плоском формате
                for i, participant in enumerate(participants_list, 1):
                    try:
                        if not isinstance(participant, dict) or not participant.get("players"):
                            continue
                            
                        # Первый игрок
                        if len(participant["players"]) > 0:
                            player1 = participant["players"][0]
                            if isinstance(player1, dict):
                                player1_name = player1.get("name", "")
                                if player1_name:
                                    ET.SubElement(matches, f"id{i}PlayerName1").text = str(player1_name)
                        
                        # Второй игрок
                        if len(participant["players"]) > 1:
                            player2 = participant["players"][1]
                            if isinstance(player2, dict):
                                player2_name = player2.get("name", "")
                                if player2_name:
                                    ET.SubElement(matches, f"id{i}PlayerName2").text = str(player2_name)
                        
                        # Названия команд
                        if len(participant["players"]) >= 2:
                            name1 = participant["players"][0].get("name", "") if isinstance(participant["players"][0], dict) else ""
                            name2 = participant["players"][1].get("name", "") if isinstance(participant["players"][1], dict) else ""
                            
                            if name1 and name2:
                                team_name = f"{name1}/{name2}"
                                
                                # Создаем короткое название
                                try:
                                    parts1 = name1.split()
                                    parts2 = name2.split()
                                    if len(parts1) >= 2 and len(parts2) >= 2:
                                        short_team_name = f"{parts1[0][0]}.{parts1[-1]}/{parts2[0][0]}.{parts2[-1]}"
                                    else:
                                        short_team_name = f"{name1}/{name2}"
                                except (IndexError, AttributeError):
                                    short_team_name = f"{name1}/{name2}"
                                
                                ET.SubElement(matches, f"id{i}Team_name").text = team_name
                                ET.SubElement(matches, f"id{i}ShortTeam_name").text = short_team_name
                                
                        elif len(participant["players"]) == 1:
                            name1 = participant["players"][0].get("name", "") if isinstance(participant["players"][0], dict) else ""
                            if name1:
                                try:
                                    parts1 = name1.split()
                                    if len(parts1) >= 2:
                                        short_name = f"{parts1[0][0]}.{parts1[-1]}"
                                    else:
                                        short_name = name1
                                except (IndexError, AttributeError):
                                    short_name = name1
                                    
                                ET.SubElement(matches, f"id{i}Team_name").text = name1
                                ET.SubElement(matches, f"id{i}ShortTeam_name").text = short_name
                                
                    except Exception as e:
                        logger.error(f"Ошибка обработки участника {i}: {e}")
                        continue
                
                # Обрабатываем матчи из Pool структуры
                matches_data = []
                
                try:
                    for row_index, row in enumerate(pool_data):
                        if not isinstance(row, list):
                            continue
                            
                        for cell_index, cell in enumerate(row):
                            if not isinstance(cell, dict):
                                continue
                                
                            if cell.get("CellType") == "MatchCell" and cell.get("MatchCell"):
                                match_cell = cell["MatchCell"]
                                if not isinstance(match_cell, dict):
                                    continue
                                    
                                match_results = match_cell.get("MatchResults", {})
                                if not isinstance(match_results, dict):
                                    match_results = {}
                                
                                # Определяем участников матча по позиции в таблице
                                participant1_index = row_index
                                participant2_index = cell_index
                                
                                if participant1_index != participant2_index:  # Избегаем матчей сами с собой
                                    match_info = {
                                        "participant1": participant1_index,
                                        "participant2": participant2_index,
                                        "match_id": str(match_cell.get("MatchId", "")),
                                        "challenge_id": str(match_cell.get("ChallengeId", "")),
                                        "state": int(match_cell.get("State", 0)),
                                        "court": str(match_cell.get("Court", "")),
                                        "date": str(match_cell.get("Date", "")),
                                        "is_played": bool(match_results.get("IsPlayed", False)),
                                        "match_results": match_results
                                    }
                                    
                                    matches_data.append(match_info)
                                    
                except Exception as e:
                    logger.error(f"Ошибка обработки матчей: {e}")
                
                # Добавляем информацию о матчах в плоском формате
                for match in matches_data:
                    try:
                        if not isinstance(match, dict):
                            continue
                            
                        p1 = match.get("participant1", 0)
                        p2 = match.get("participant2", 0)
                        match_prefix = f"id{p1}vs{p2}Match"
                        
                        ET.SubElement(matches, f"{match_prefix}_state").text = str(match.get("state", 0))
                        ET.SubElement(matches, f"{match_prefix}_court").text = str(match.get("court", ""))
                        ET.SubElement(matches, f"{match_prefix}_date").text = str(match.get("date", ""))
                        ET.SubElement(matches, f"{match_prefix}_is_played").text = str(match.get("is_played", False))
                        
                        # Счет матча
                        match_results = match.get("match_results", {})
                        if isinstance(match_results, dict) and match_results.get("HasScore") and match_results.get("Score"):
                            score_data = match_results["Score"]
                            if isinstance(score_data, dict):
                                first_score = int(score_data.get("FirstParticipantScore", 0))
                                second_score = int(score_data.get("SecondParticipantScore", 0))
                                
                                ET.SubElement(matches, f"{match_prefix}_first_second_score").text = f"{first_score}-{second_score}"
                                
                                winner = "first" if score_data.get("IsFirstParticipantWinner") else "second"
                                ET.SubElement(matches, f"{match_prefix}_winner").text = winner
                                
                                # Детальный счет по сетам
                                detailed_scoring = score_data.get("DetailedScoring", [])
                                if isinstance(detailed_scoring, list):
                                    for set_index, set_data in enumerate(detailed_scoring, 1):
                                        if isinstance(set_data, dict):
                                            set_first = int(set_data.get("FirstParticipantScore", 0))
                                            set_second = int(set_data.get("SecondParticipantScore", 0))
                                            set_winner = "first" if set_data.get("IsFirstParticipantWinner") else "second"
                                            
                                            ET.SubElement(matches, f"{match_prefix}_set{set_index}_first_second_score").text = f"{set_first}-{set_second}"
                                            ET.SubElement(matches, f"{match_prefix}_set{set_index}_winner").text = set_winner
                        else:
                            # Если нет счета
                            ET.SubElement(matches, f"{match_prefix}_first_second_score").text = "0-0"
                            ET.SubElement(matches, f"{match_prefix}_winner").text = ""
                            
                    except Exception as e:
                        logger.error(f"Ошибка обработки матча {match.get('match_id', 'unknown')}: {e}")
                        continue
                
                # Добавляем турнирную таблицу (standings) в плоском формате
                standings_data = group_data.get("Standings", [])
                if isinstance(standings_data, list):
                    try:
                        for standing in standings_data:
                            if not isinstance(standing, dict):
                                continue
                                
                            position = int(standing.get("Standing", 0))
                            if position <= 0:
                                continue
                            
                            # Находим соответствующего участника по ID
                            participant_id = str(standing.get("ParticipantId", ""))
                            
                            # Имена игроков из standings
                            team_names = []
                            if standing.get("DoublesPlayer1Model") and isinstance(standing["DoublesPlayer1Model"], dict):
                                name1 = standing["DoublesPlayer1Model"].get("Name", "")
                                if name1:
                                    team_names.append(name1)
                            if standing.get("DoublesPlayer2Model") and isinstance(standing["DoublesPlayer2Model"], dict):
                                name2 = standing["DoublesPlayer2Model"].get("Name", "")
                                if name2:
                                    team_names.append(name2)
                            
                            team_name = " / ".join(team_names)
                            
                            # Статистика позиции
                            prefix = f"P{position}"
                            ET.SubElement(matches, f"{prefix}_participant_id").text = participant_id
                            ET.SubElement(matches, f"{prefix}_team_name").text = team_name
                            ET.SubElement(matches, f"{prefix}_match_points").text = str(standing.get("MatchPoints", 0))
                            ET.SubElement(matches, f"{prefix}_wins").text = str(standing.get("Wins", 0))
                            ET.SubElement(matches, f"{prefix}_losses").text = str(standing.get("Losses", 0))
                            ET.SubElement(matches, f"{prefix}_draws").text = str(standing.get("Draws", 0))
                            ET.SubElement(matches, f"{prefix}_games_won").text = str(standing.get("GamesWon", 0))
                            ET.SubElement(matches, f"{prefix}_games_lost").text = str(standing.get("GamesLost", 0))
                            ET.SubElement(matches, f"{prefix}_points_scored").text = str(standing.get("ScoredPoints", 0))
                            ET.SubElement(matches, f"{prefix}_points_conceded").text = str(standing.get("ConcededPoints", 0))
                            ET.SubElement(matches, f"{prefix}_points_difference").text = str(standing.get("PointsDifference", 0))
                            ET.SubElement(matches, f"{prefix}_played").text = str(standing.get("Played", 0))
                            
                    except Exception as e:
                        logger.error(f"Ошибка обработки турнирной таблицы: {e}")
                
            except Exception as e:
                logger.error(f"Ошибка извлечения участников: {e}")
                self._add_error_xml(root, f"Ошибка обработки участников: {str(e)}")
                
        except Exception as e:
            logger.error(f"Критическая ошибка в _add_round_robin_data: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Добавляем базовую структуру чтобы XML был валидным
            self._add_error_xml(root, f"Критическая ошибка: {str(e)}")

    def _add_error_xml(self, root: ET.Element, error_message: str):
        """Добавляет структуру ошибки в XML"""
        data_tab = ET.SubElement(root, "DataTab")
        matches = ET.SubElement(data_tab, "matches")
        ET.SubElement(matches, "error").text = error_message
        ET.SubElement(matches, "classes").text = "Ошибка"
        ET.SubElement(matches, "type").text = "Ошибка загрузки данных"
  
    def _add_elimination_data(self, root: ET.Element, class_data: Dict, draw_index: int):
        """Добавляет данные игр на выбывание"""
        elimination_data = class_data.get("elimination", [])
        if draw_index < len(elimination_data):
            elim_data = elimination_data[draw_index]
            
            if "Elimination" in elim_data:
                bracket_data = elim_data["Elimination"]
                
                # Информация о сетке
                bracket = ET.SubElement(root, "bracket")
                ET.SubElement(bracket, "width").text = str(bracket_data.get("Width", 0))
                ET.SubElement(bracket, "height").text = str(bracket_data.get("Height", 0))
                ET.SubElement(bracket, "draw_type").text = str(bracket_data.get("DrawType", 0))
                ET.SubElement(bracket, "consolation").text = str(bracket_data.get("Consolation", 0))
                ET.SubElement(bracket, "places_start").text = str(bracket_data.get("PlacesStartPos", 1))
                ET.SubElement(bracket, "places_end").text = str(bracket_data.get("PlacesEndPos", 1))
                ET.SubElement(bracket, "is_qualification").text = str(bracket_data.get("IsQualification", False))
                ET.SubElement(bracket, "is_for_teams").text = str(bracket_data.get("IsForTeams", False))
                ET.SubElement(bracket, "is_for_doubles").text = str(bracket_data.get("IsForDoubles", True))
                
                # Участники первого раунда
                if bracket_data.get("FirstRoundParticipantCells"):
                    participants = ET.SubElement(bracket, "participants")
                    for participant_data in bracket_data["FirstRoundParticipantCells"]:
                        participant = ET.SubElement(participants, "participant")
                        ET.SubElement(participant, "event_participant_id").text = str(participant_data.get("EventParticipantId", 0))
                        ET.SubElement(participant, "participant_type").text = str(participant_data.get("ParticipantType", 0))
                        ET.SubElement(participant, "is_qualifier").text = str(participant_data.get("IsQualifier", False))
                        ET.SubElement(participant, "seed").text = str(participant_data.get("Seed", ""))
                        ET.SubElement(participant, "draw_id").text = str(participant_data.get("DrawId", 0))
                        
                        # Игроки в команде
                        players = ET.SubElement(participant, "players")
                        
                        # Первый игрок
                        if participant_data.get("FirstPlayer"):
                            first_player = participant_data["FirstPlayer"]
                            player1 = ET.SubElement(players, "player")
                            ET.SubElement(player1, "id").text = str(first_player.get("Id", 0))
                            ET.SubElement(player1, "name").text = first_player.get("Name", "")
                            ET.SubElement(player1, "rankedin_id").text = first_player.get("RankedinId", "")
                            ET.SubElement(player1, "country").text = first_player.get("CountryShort", "")
                            ET.SubElement(player1, "rating_begin").text = str(first_player.get("RatingBegin", 0) or 0)
                            ET.SubElement(player1, "rating_end").text = str(first_player.get("RatingEnd", 0) or 0)
                        
                        # Второй игрок
                        if participant_data.get("SecondPlayer"):
                            second_player = participant_data["SecondPlayer"]
                            player2 = ET.SubElement(players, "player")
                            ET.SubElement(player2, "id").text = str(second_player.get("Id", 0))
                            ET.SubElement(player2, "name").text = second_player.get("Name", "")
                            ET.SubElement(player2, "rankedin_id").text = second_player.get("RankedinId", "")
                            ET.SubElement(player2, "country").text = second_player.get("CountryShort", "")
                            ET.SubElement(player2, "rating_begin").text = str(second_player.get("RatingBegin", 0) or 0)
                            ET.SubElement(player2, "rating_end").text = str(second_player.get("RatingEnd", 0) or 0)
                        
                        # Название команды
                        team_names = []
                        if participant_data.get("FirstPlayer", {}).get("Name"):
                            team_names.append(participant_data["FirstPlayer"]["Name"])
                        if participant_data.get("SecondPlayer", {}).get("Name"):
                            team_names.append(participant_data["SecondPlayer"]["Name"])
                        ET.SubElement(participant, "team_name").text = (" / ".join(team_names)).replace(" ", "")
                
                # Раунды и матчи
                if bracket_data.get("DrawData"):
                    rounds = ET.SubElement(bracket, "rounds")
                    
                    for round_index, round_matches in enumerate(bracket_data["DrawData"]):
                        round_elem = ET.SubElement(rounds, "round")
                        ET.SubElement(round_elem, "number").text = str(round_index + 1)
                        
                        # Матчи раунда
                        matches = ET.SubElement(round_elem, "matches")
                        for match_data in round_matches:
                            if match_data:  # Проверяем, что матч не null
                                match = ET.SubElement(matches, "match")
                                
                                # Основная информация о матче
                                ET.SubElement(match, "match_id").text = str(match_data.get("MatchId", 0))
                                ET.SubElement(match, "challenge_id").text = str(match_data.get("ChallengeId", 0))
                                ET.SubElement(match, "round").text = str(match_data.get("Round", 0))
                                ET.SubElement(match, "max_round").text = str(match_data.get("MaxRound", 0))
                                ET.SubElement(match, "court").text = match_data.get("CourtName", "")
                                ET.SubElement(match, "date").text = match_data.get("Date", "")
                                ET.SubElement(match, "match_state").text = str(match_data.get("MatchState", 0))
                                ET.SubElement(match, "match_order").text = str(match_data.get("MatchOrder", 0))
                                ET.SubElement(match, "is_published").text = str(match_data.get("IsPublished", False))
                                ET.SubElement(match, "has_qualifiers").text = str(match_data.get("HasQualifiers", False))
                                
                                # Challenger (первый участник)
                                challenger = ET.SubElement(match, "challenger")
                                challenger_data = match_data.get("ChallengerParticipant", {})
                                ET.SubElement(challenger, "event_participant_id").text = str(challenger_data.get("EventParticipantId", 0))
                                ET.SubElement(challenger, "seed").text = str(challenger_data.get("Seed", ""))
                                ET.SubElement(challenger, "is_qualifier").text = str(challenger_data.get("IsQualifier", False))
                                
                                # Игроки challenger
                                challenger_players = ET.SubElement(challenger, "players")
                                if challenger_data.get("FirstPlayer"):
                                    first_player = challenger_data["FirstPlayer"]
                                    player1 = ET.SubElement(challenger_players, "player")
                                    ET.SubElement(player1, "id").text = str(first_player.get("Id", 0))
                                    ET.SubElement(player1, "name").text = first_player.get("Name", "")
                                    ET.SubElement(player1, "rankedin_id").text = first_player.get("RankedinId", "")
                                    ET.SubElement(player1, "country").text = first_player.get("CountryShort", "")
                                    ET.SubElement(player1, "rating_begin").text = str(first_player.get("RatingBegin", 0) or 0)
                                    ET.SubElement(player1, "rating_end").text = str(first_player.get("RatingEnd", 0) or 0)
                                
                                if challenger_data.get("SecondPlayer"):
                                    second_player = challenger_data["SecondPlayer"]
                                    player2 = ET.SubElement(challenger_players, "player")
                                    ET.SubElement(player2, "id").text = str(second_player.get("Id", 0))
                                    ET.SubElement(player2, "name").text = second_player.get("Name", "")
                                    ET.SubElement(player2, "rankedin_id").text = second_player.get("RankedinId", "")
                                    ET.SubElement(player2, "country").text = second_player.get("CountryShort", "")
                                    ET.SubElement(player2, "rating_begin").text = str(second_player.get("RatingBegin", 0) or 0)
                                    ET.SubElement(player2, "rating_end").text = str(second_player.get("RatingEnd", 0) or 0)
                                
                                # Название команды challenger
                                challenger_names = []
                                if challenger_data.get("FirstPlayer", {}).get("Name"):
                                    challenger_names.append(challenger_data["FirstPlayer"]["Name"])
                                if challenger_data.get("SecondPlayer", {}).get("Name"):
                                    challenger_names.append(challenger_data["SecondPlayer"]["Name"])
                                ET.SubElement(challenger, "team_name").text = (" / ".join(challenger_names)).replace(" ", "")
                                
                                # Challenged (второй участник)
                                challenged = ET.SubElement(match, "challenged")
                                challenged_data = match_data.get("ChallengedParticipant", {})
                                ET.SubElement(challenged, "event_participant_id").text = str(challenged_data.get("EventParticipantId", 0))
                                ET.SubElement(challenged, "seed").text = str(challenged_data.get("Seed", ""))
                                ET.SubElement(challenged, "is_qualifier").text = str(challenged_data.get("IsQualifier", False))
                                
                                # Игроки challenged
                                challenged_players = ET.SubElement(challenged, "players")
                                if challenged_data.get("FirstPlayer"):
                                    first_player = challenged_data["FirstPlayer"]
                                    player1 = ET.SubElement(challenged_players, "player")
                                    ET.SubElement(player1, "id").text = str(first_player.get("Id", 0))
                                    ET.SubElement(player1, "name").text = first_player.get("Name", "")
                                    ET.SubElement(player1, "rankedin_id").text = first_player.get("RankedinId", "")
                                    ET.SubElement(player1, "country").text = first_player.get("CountryShort", "")
                                    ET.SubElement(player1, "rating_begin").text = str(first_player.get("RatingBegin", 0) or 0)
                                    ET.SubElement(player1, "rating_end").text = str(first_player.get("RatingEnd", 0) or 0)
                                
                                if challenged_data.get("SecondPlayer"):
                                    second_player = challenged_data["SecondPlayer"]
                                    player2 = ET.SubElement(challenged_players, "player")
                                    ET.SubElement(player2, "id").text = str(second_player.get("Id", 0))
                                    ET.SubElement(player2, "name").text = second_player.get("Name", "")
                                    ET.SubElement(player2, "rankedin_id").text = second_player.get("RankedinId", "")
                                    ET.SubElement(player2, "country").text = second_player.get("CountryShort", "")
                                    ET.SubElement(player2, "rating_begin").text = str(second_player.get("RatingBegin", 0) or 0)
                                    ET.SubElement(player2, "rating_end").text = str(second_player.get("RatingEnd", 0) or 0)
                                
                                # Название команды challenged
                                challenged_names = []
                                if challenged_data.get("FirstPlayer", {}).get("Name"):
                                    challenged_names.append(challenged_data["FirstPlayer"]["Name"])
                                if challenged_data.get("SecondPlayer", {}).get("Name"):
                                    challenged_names.append(challenged_data["SecondPlayer"]["Name"])
                                ET.SubElement(challenged, "team_name").text = " / ".join(challenged_names)
                                
                                # Результат матча
                                match_view_model = match_data.get("MatchViewModel", {})
                                result = ET.SubElement(match, "result")
                                ET.SubElement(result, "has_score").text = str(match_view_model.get("HasScore", False))
                                ET.SubElement(result, "is_played").text = str(match_view_model.get("IsPlayed", False))
                                ET.SubElement(result, "has_cancellation").text = str(match_view_model.get("HasCancellation", False))
                                
                                # Счет, если есть
                                if match_view_model.get("HasScore") and match_view_model.get("Score"):
                                    score_data = match_view_model["Score"]
                                    score = ET.SubElement(result, "score")
                                    ET.SubElement(score, "first_score").text = str(score_data.get("FirstParticipantScore", 0))
                                    ET.SubElement(score, "second_score").text = str(score_data.get("SecondParticipantScore", 0))
                                    ET.SubElement(score, "winner").text = "challenger" if score_data.get("IsFirstParticipantWinner") else "challenged"
                                    
                                    # Детальный счет по сетам
                                    if score_data.get("DetailedScoring"):
                                        sets = ET.SubElement(score, "sets")
                                        for set_index, set_data in enumerate(score_data["DetailedScoring"]):
                                            set_elem = ET.SubElement(sets, "set")
                                            set_elem.set("number", str(set_index + 1))
                                            ET.SubElement(set_elem, "first_score").text = str(set_data.get("FirstParticipantScore", 0))
                                            ET.SubElement(set_elem, "second_score").text = str(set_data.get("SecondParticipantScore", 0))
                                            ET.SubElement(set_elem, "winner").text = "challenger" if set_data.get("IsFirstParticipantWinner") else "challenged"
                                
                                # Победитель матча
                                if match_data.get("WinnerParticipantId"):
                                    ET.SubElement(match, "winner_participant_id").text = str(match_data["WinnerParticipantId"])
                
                # Все матчи (включая DrawCells для дополнительной информации)
                if bracket_data.get("DrawCells"):
                    all_matches = ET.SubElement(bracket, "draw_cells")
                    for cell_index, cell_data in enumerate(bracket_data["DrawCells"]):
                        if cell_data:
                            cell = ET.SubElement(all_matches, "cell")
                            ET.SubElement(cell, "index").text = str(cell_index)
                            ET.SubElement(cell, "round").text = str(cell_data.get("Round", 0))
                            ET.SubElement(cell, "match_id").text = str(cell_data.get("MatchId", 0))
                            ET.SubElement(cell, "court").text = cell_data.get("CourtName", "")
                            ET.SubElement(cell, "date").text = cell_data.get("Date", "")
    

    def generate_court_score_xml(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует упрощенный XML для счета на конкретном корте с поддержкой следующего матча"""
        root = ET.Element("templateData")
        
        # Информация о турнире (если есть)
        if tournament_data:
            metadata = tournament_data.get("metadata", {})
            ET.SubElement(root, "tournamentName").text = metadata.get("name", "Турнир")
            ET.SubElement(root, "tournamentSport").text = self._get_sport_name(metadata.get("sport", 5))
        
        # Базовая информация о корте
        ET.SubElement(root, "courtId").text = str(court_data.get("court_id", ""))
        ET.SubElement(root, "courtName").text = court_data.get("court_name", "Корт")
        ET.SubElement(root, "courtStatus").text = court_data.get("event_state", "")
        ET.SubElement(root, "courtSport").text = court_data.get("sport", "")
        
        # === ТЕКУЩИЙ МАТЧ ===
        current_class = court_data.get("current_class_name") or court_data.get("class_name", "")
        if current_class:
            ET.SubElement(root, "currentClassName").text = current_class
            ET.SubElement(root, "currentMatchId").text = str(court_data.get("current_match_id", ""))
            ET.SubElement(root, "currentMatchState").text = court_data.get("current_match_state", "")
            ET.SubElement(root, "currentIsSingles").text = str(court_data.get("current_is_singles", False))
            
            # Дополнительная информация о текущем матче
            if court_data.get("current_duration_seconds"):
                ET.SubElement(root, "currentDurationSeconds").text = str(court_data["current_duration_seconds"])
            if court_data.get("current_is_winner_first") is not None:
                ET.SubElement(root, "currentWinnerFirst").text = str(court_data["current_is_winner_first"])
        
        # Участники команды 1 (текущий матч)
        team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
        if team1_players:
            for i, player in enumerate(team1_players, 1):
                ET.SubElement(root, f"player{i}Id").text = str(player.get("id", ""))
                ET.SubElement(root, f"player{i}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{i}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{i}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{i}FullName").text = player.get("fullName", "")
                ET.SubElement(root, f"player{i}Country").text = player.get("countryCode", "")
                ET.SubElement(root, f"player{i}LastNameShort").text = player.get("lastNameShort", "")
                ET.SubElement(root, f"player{i}InitialLastName").text = player.get("initialLastName", "")
        
        # Участники команды 2 (текущий матч)
        team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
        if team2_players:
            for i, player in enumerate(team2_players, 1):
                player_num = i + 2  # Команда 2 начинается с player3, player4
                ET.SubElement(root, f"player{player_num}Id").text = str(player.get("id", ""))
                ET.SubElement(root, f"player{player_num}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{player_num}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{player_num}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{player_num}FullName").text = player.get("fullName", "")
                ET.SubElement(root, f"player{player_num}Country").text = player.get("countryCode", "")
                ET.SubElement(root, f"player{player_num}LastNameShort").text = player.get("lastNameShort", "")
                ET.SubElement(root, f"player{player_num}InitialLastName").text = player.get("initialLastName", "")
        
        # Счет текущего матча
        ET.SubElement(root, "team1Score").text = str(court_data.get("current_first_participant_score", court_data.get("first_participant_score", 0)))
        ET.SubElement(root, "team2Score").text = str(court_data.get("current_second_participant_score", court_data.get("second_participant_score", 0)))
        
        # Детальный счет по сетам
        detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
        for i, set_data in enumerate(detailed_result, 1):
            ET.SubElement(root, f"set{i}Team1").text = str(set_data.get("firstParticipantScore", 0))
            ET.SubElement(root, f"set{i}Team2").text = str(set_data.get("secondParticipantScore", 0))
            if set_data.get("loserTiebreak"):
                ET.SubElement(root, f"set{i}LoserTiebreak").text = str(set_data["loserTiebreak"])
        
        # Форматированные названия команд с сокращениями 
        if team1_players:
            team1_shorts = [p.get("lastNameShort", "") for p in team1_players if p.get("lastNameShort")]
            ET.SubElement(root, "team1NamesShort").text = ("/".join(team1_shorts)).replace(" ", "")
            
            team1_initials = [p.get("initialLastName", "") for p in team1_players if p.get("initialLastName")]
            ET.SubElement(root, "team1NamesInitial").text = ("/".join(team1_initials)).replace(" ", "")
            
            team1_full = [p.get("fullName", "") for p in team1_players if p.get("fullName")]
            ET.SubElement(root, "team1NamesFull").text = "/".join(team1_full)
        
        if team2_players:
            team2_shorts = [p.get("lastNameShort", "") for p in team2_players if p.get("lastNameShort")]
            ET.SubElement(root, "team2NamesShort").text = ("/".join(team2_shorts)).replace(" ", "")
            
            team2_initials = [p.get("initialLastName", "") for p in team2_players if p.get("initialLastName")]
            ET.SubElement(root, "team2NamesInitial").text = ("/".join(team2_initials)).replace(" ", "")
            
            team2_full = [p.get("fullName", "") for p in team2_players if p.get("fullName")]
            ET.SubElement(root, "team2NamesFull").text = "/".join(team2_full)
        
        # === СЛЕДУЮЩИЙ МАТЧ (если есть) ===
        if court_data.get("next_class_name"):
            ET.SubElement(root, "nextClassName").text = court_data["next_class_name"]
            ET.SubElement(root, "nextMatchId").text = str(court_data.get("next_match_id", ""))
            ET.SubElement(root, "nextStartTime").text = court_data.get("next_start_time", "")
            ET.SubElement(root, "nextScheduledTime").text = court_data.get("next_scheduled_time", "")
            ET.SubElement(root, "nextMatchState").text = court_data.get("next_match_state", "")
            ET.SubElement(root, "nextIsSingles").text = str(court_data.get("next_is_singles", False))
            
            # Участники следующего матча - команда 1
            next_team1 = court_data.get("next_first_participant", [])
            if next_team1:
                for i, player in enumerate(next_team1, 1):
                    ET.SubElement(root, f"nextPlayer{i}Id").text = str(player.get("id", ""))
                    ET.SubElement(root, f"nextPlayer{i}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{i}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{i}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{i}FullName").text = player.get("fullName", "")
                    ET.SubElement(root, f"nextPlayer{i}Country").text = player.get("countryCode", "")
                    ET.SubElement(root, f"nextPlayer{i}LastNameShort").text = player.get("lastNameShort", "")
                    ET.SubElement(root, f"nextPlayer{i}InitialLastName").text = player.get("initialLastName", "")
            
            # Участники следующего матча - команда 2
            next_team2 = court_data.get("next_second_participant", [])
            if next_team2:
                for i, player in enumerate(next_team2, 1):
                    player_num = i + 2  # Команда 2 начинается с nextPlayer3, nextPlayer4
                    ET.SubElement(root, f"nextPlayer{player_num}Id").text = str(player.get("id", ""))
                    ET.SubElement(root, f"nextPlayer{player_num}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}FullName").text = player.get("fullName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}Country").text = player.get("countryCode", "")
                    ET.SubElement(root, f"nextPlayer{player_num}LastNameShort").text = player.get("lastNameShort", "")
                    ET.SubElement(root, f"nextPlayer{player_num}InitialLastName").text = player.get("initialLastName", "")
            
            # Форматированные названия следующих команд
            if next_team1:
                next_team1_shorts = [p.get("lastNameShort", "") for p in next_team1 if p.get("lastNameShort")]
                ET.SubElement(root, "nextTeam1NamesShort").text = ("/".join(next_team1_shorts)).replace(" ", "")
                
                next_team1_initials = [p.get("initialLastName", "") for p in next_team1 if p.get("initialLastName")]
                ET.SubElement(root, "nextTeam1NamesInitial").text = ("/".join(next_team1_initials)).replace(" ", "")
                
                next_team1_full = [p.get("fullName", "") for p in next_team1 if p.get("fullName")]
                ET.SubElement(root, "nextTeam1NamesFull").text = "/".join(next_team1_full)
            
            if next_team2:
                next_team2_shorts = [p.get("lastNameShort", "") for p in next_team2 if p.get("lastNameShort")]
                ET.SubElement(root, "nextTeam2NamesShort").text = ("/".join(next_team2_shorts)).replace(" ", "")
                
                next_team2_initials = [p.get("initialLastName", "") for p in next_team2 if p.get("initialLastName")]
                ET.SubElement(root, "nextTeam2NamesInitial").text = ("/".join(next_team2_initials)).replace(" ", "")
                
                next_team2_full = [p.get("fullName", "") for p in next_team2 if p.get("fullName")]
                ET.SubElement(root, "nextTeam2NamesFull").text = "/".join(next_team2_full)
        
        # Время обновления (всегда актуальное)
        ET.SubElement(root, "updated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return self._prettify_xml(root)

    
    def generate_all_courts_xml(self, courts_data: List[Dict], tournament_data: Dict = None) -> str:
        """Генерирует XML для всех кортов турнира"""
        root = ET.Element("templateData")
        
        # Информация о турнире
        if tournament_data:
            metadata = tournament_data.get("metadata", {})
            tournament = ET.SubElement(root, "tournament")
            ET.SubElement(tournament, "id").text = str(tournament_data.get("tournament_id", ""))
            ET.SubElement(tournament, "name").text = metadata.get("name", "Турнир")
            ET.SubElement(tournament, "sport").text = self._get_sport_name(metadata.get("sport", 5))
        
        # Все корты
        courts = ET.SubElement(root, "courts")
        ET.SubElement(courts, "count").text = str(len(courts_data))
        
        for court_data in courts_data:
            if "error" in court_data:
                continue
                
            court = ET.SubElement(courts, "court")
            ET.SubElement(court, "id").text = str(court_data.get("court_id", ""))
            ET.SubElement(court, "name").text = court_data.get("court_name", "")
            ET.SubElement(court, "status").text = court_data.get("event_state", "")
            
            # Участники и счет (упрощенно)
            if court_data.get("first_participant"):
                team1_names = [f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() 
                              for p in court_data["first_participant"]]
                ET.SubElement(court, "team1").text = (" / ".join(team1_names)).replace(" ", "")
            
            if court_data.get("second_participant"):
                team2_names = [f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() 
                              for p in court_data["second_participant"]]
                ET.SubElement(court, "team2").text = (" / ".join(team2_names)).replace(" ", "")
            
            ET.SubElement(court, "score").text = f"{court_data.get('first_participant_score', 0)}-{court_data.get('second_participant_score', 0)}"
        
        ET.SubElement(root, "updated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        return self._prettify_xml(root)
    

class XMLFileManager:
    """Менеджер XML файлов"""
    
    def __init__(self, output_dir: str = "xml_files"):
        self.output_dir = output_dir
        self.generator = XMLGenerator()
        
        # Создаем директорию если её нет
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_and_save(self, xml_type_info: Dict, tournament_data: Dict, 
                         court_data: Dict = None) -> Dict:
        """Генерирует и сохраняет XML файл"""
        xml_type = xml_type_info.get("type")
        
        # Генерация XML в зависимости от типа
        if xml_type == "tournament_table":
            xml_content = self.generator.generate_tournament_table_xml(tournament_data, xml_type_info)
        elif xml_type == "schedule":
            xml_content = self.generator.generate_schedule_xml(tournament_data)
        elif xml_type == "court_score":
            xml_content = self.generator.generate_court_score_xml(court_data, tournament_data)
        else:
            raise ValueError(f"Неизвестный тип XML: {xml_type}")
        
        # Сохранение файла
        filename = self._get_filename(xml_type_info, tournament_data)
        filepath = f"{self.output_dir}/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        # Информация о файле
        import os
        file_stats = os.stat(filepath)
        
        return {
            "id": xml_type_info["id"],
            "name": xml_type_info["name"],
            "filename": filename,
            "url": f"/xml/{filename}",
            "size": self._format_file_size(file_stats.st_size),
            "created": datetime.now().isoformat(),
            "type": xml_type
        }
    
    def _get_filename(self, xml_type_info: Dict, tournament_data: Dict) -> str:
        """Генерирует имя файла"""
        tournament_id = tournament_data.get("tournament_id", "unknown")
        xml_type = xml_type_info.get("type")
        
        if xml_type == "court_score":
            court_id = xml_type_info.get("court_id", "")
            court_name = xml_type_info.get("court_name", f"court_{court_id}")
            safe_name = "".join(c for c in court_name if c.isalnum() or c in "._-").replace(" ", "_")
            return f"{tournament_id}_court_{court_id}_{safe_name}.xml"
        
        elif xml_type == "tournament_table":
            class_id = xml_type_info.get("class_id", "")
            draw_type = xml_type_info.get("draw_type", "")
            draw_index = xml_type_info.get("draw_index", 0)
            
            # Создаем понятное имя файла
            if draw_type == "round_robin":
                group_name = xml_type_info.get("group_name", f"group_{draw_index}")
                safe_group = "".join(c for c in group_name if c.isalnum() or c in "._-").replace(" ", "_")
                return f"{tournament_id}_table_{class_id}_rr_{safe_group}.xml"
            else:
                stage_name = xml_type_info.get("stage_name", f"stage_{draw_index}")
                safe_stage = "".join(c for c in stage_name if c.isalnum() or c in "._-").replace(" ", "_")
                return f"{tournament_id}_table_{class_id}_elim_{safe_stage}.xml"
        
        elif xml_type == "schedule":
            return f"{tournament_id}_schedule.xml"
        
        else:
            # Fallback для неизвестных типов
            xml_id = xml_type_info.get("id", "unknown")
            return f"{tournament_id}_{xml_type}_{xml_id}.xml"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Форматирует размер файла"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def generate_all_tournament_xml(self, tournament_data: Dict, courts_data: List[Dict] = None) -> List[Dict]:
        """Генерирует все доступные XML файлы для турнира"""
        from .rankedin_api import RankedinAPI
        
        api = RankedinAPI()
        xml_types = api.get_xml_data_types(tournament_data)
        
        generated_files = []
        
        for xml_type_info in xml_types:
            try:
                xml_type = xml_type_info.get("type")
                
                if xml_type == "court_score":
                    # Для каждого корта нужны отдельные данные
                    court_id = xml_type_info.get("court_id")
                    if courts_data:
                        court_data = next((c for c in courts_data if str(c.get("court_id")) == str(court_id)), None)
                        if court_data:
                            file_info = self.generate_and_save(xml_type_info, tournament_data, court_data)
                            generated_files.append(file_info)
                else:
                    # Турнирные таблицы и расписание
                    file_info = self.generate_and_save(xml_type_info, tournament_data)
                    generated_files.append(file_info)
                
            except Exception as e:
                logger.error(f"Ошибка генерации XML {xml_type_info.get('name')}: {e}")
                continue
        
        return generated_files
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Удаляет старые XML файлы"""
        import os
        import time
        
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        removed_count = 0
        
        try:
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.xml'):
                    filepath = os.path.join(self.output_dir, filename)
                    file_time = os.path.getmtime(filepath)
                    
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        removed_count += 1
                        
        except Exception as e:
            logger.error(f"Ошибка очистки старых файлов: {e}")
        
        if removed_count > 0:
            logger.info(f"Удалено {removed_count} старых XML файлов")
        
        return removed_count


# Функции для обратной совместимости
def generate_scoreboard_xml(tournament_data: Dict, courts_data: List[Dict]) -> str:
    """Обертка для старого кода"""
    generator = XMLGenerator()
    return generator.generate_all_courts_xml(courts_data, tournament_data)

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