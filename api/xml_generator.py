#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль генерации XML файлов для vMix
Создает XML файлы на основе данных турниров rankedin.com
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Any, Optional
import logging
from markupsafe import escape
from .constants import get_sport_name, get_country_name

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
        ET.SubElement(tournament, "sport").text = self.get_sport_name(metadata.get("sport", 5))
        ET.SubElement(tournament, "country").text = self.get_country_name(metadata.get("country"))
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

        ET.SubElement(root, "generated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        return self._prettify_xml(root)

    def _add_round_robin_data(self, root: ET.Element, class_data: Dict, draw_index: int):
        """Добавляет данные группового этапа """
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

                # Добавляем информацию об участниках в плоском формате
                for i, participant in enumerate(participants_list, 1):
                    try:
                        #    continue
                            
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
                            if (matches.find(f"id{p2}ShortTeam_name")).text == 'Bye':
                                ET.SubElement(matches, f"{match_prefix}_first_second_score").text = "●"
                            else:
                                ET.SubElement(matches, f"{match_prefix}_first_second_score").text = "-"
                            ET.SubElement(matches, f"{match_prefix}_winner").text = ""

                    except Exception as e:
                        logger.error(f"Ошибка обработки матча {match.get('match_id', 'unknown')}: {e}")
                        continue

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
            self._add_error_xml(root, f"Критическая ошибка: {str(e)}")


    def _get_game_score_display(self, detailed_result: List[Dict], set_score: int, team: str) -> str:
        """Возвращает счет гейма если есть, иначе счет сетов"""
        if detailed_result and len(detailed_result) > 0:
            last_set = detailed_result[-1]
            game_score = last_set.get("gameScore")
            if game_score:
                return game_score.get(team, str(set_score))
        return str(set_score)

    def _add_elimination_data(self, root: ET.Element, class_data: Dict, draw_index: int):
        #Добавляет данные игр на выбывание в плоском формате с обработкой Bye и Walkover
        elimination_data = class_data.get("elimination", [])
        if draw_index < len(elimination_data):
            elim_data = elimination_data[draw_index]
            
            if "Elimination" in elim_data:
                bracket_data = elim_data["Elimination"]
                
                # Создаем плоский формат вместо иерархического
                participants = ET.SubElement(root, "participants")

                # Определяем места
                places_start = bracket_data.get("PlacesStartPos", 1)
                places_end = bracket_data.get("PlacesEndPos", 1)
                places_text = f"{places_start}-{places_end}" if places_start != places_end else str(places_start)
                ET.SubElement(participants, "places").text = places_text

                # Добавляем информацию о классе
                class_name = class_data.get("class_info", {}).get("Name", f"Категория {draw_index}")
                ET.SubElement(participants, "class_name").text = class_name

                if bracket_data.get("FirstRoundParticipantCells"):
                    for i, participant_data in enumerate(bracket_data["FirstRoundParticipantCells"], 1):
                        # Формируем название команды
                        team_names = []
                        if participant_data.get("FirstPlayer", {}).get("Name"):
                            team_names.append(participant_data["FirstPlayer"]["Name"])
                        if participant_data.get("SecondPlayer", {}).get("Name"):
                            team_names.append(participant_data["SecondPlayer"]["Name"])
                        team_name = "/".join(team_names) if team_names else "Bye"
                        
                        # Создаем сокращенное название
                        short_name = self._create_short_name(team_name) if team_name != "Bye" else "Bye"
                        
                        ET.SubElement(participants, f"round_0_team_{i}_name").text = team_name
                        ET.SubElement(participants, f"round_0_team_{i}_ShortName").text = short_name

                # 2. Обрабатываем матчи по раундам
                if bracket_data.get("DrawData"):
                    # Группируем матчи по номеру раунда из данных
                    matches_by_round = {}
                    
                    for round_matches in bracket_data["DrawData"]:
                        for match_data in round_matches:
                            if match_data:
                                # Получаем номер раунда из данных матча
                                round_number = match_data.get("Round", 1)
                                if round_number not in matches_by_round:
                                    matches_by_round[round_number] = []
                                matches_by_round[round_number].append(match_data)

                    # Обрабатываем матчи сгруппированные по раундам
                    for round_number in sorted(matches_by_round.keys()):
                        round_matches = matches_by_round[round_number]

                        match_counter = 1
                        for match_data in round_matches:
                            match_view_model = match_data.get("MatchViewModel", {})
                            prefix = f"round_{round_number}_{match_counter}"

                            # Корт
                            ET.SubElement(participants, f"{prefix}_court").text = match_data.get("CourtName", "")

                            # Статус матча
                            is_played = match_view_model.get("IsPlayed", False)
                            has_score = match_view_model.get("HasScore", False)
                            cancellation_status = match_data.get("CancellationStatus", "")
                            winner_id = match_data.get("WinnerParticipantId")
                            
                            ET.SubElement(participants, f"{prefix}_is_played").text = str(is_played)
                            ET.SubElement(participants, f"{prefix}_has_score").text = str(has_score)
                            ET.SubElement(participants, f"{prefix}_cancellation_status").text = str(cancellation_status)

                            # ОБРАБОТКА РАЗЛИЧНЫХ СЦЕНАРИЕВ
                            if is_played and has_score:
                                # 1. Обычный сыгранный матч со счетом
                                if winner_id:
                                    winning_team = self._find_winner_team_name(match_data, winner_id)
                                    ET.SubElement(participants, f"{prefix}_team").text = winning_team
                                    short_name = self._create_short_name(winning_team)
                                    ET.SubElement(participants, f"{prefix}_Shortteam").text = short_name

                                    # Имена игроков победившей команды
                                    first_player_name, second_player_name = self._get_winner_player_names(match_data, winner_id)
                                    ET.SubElement(participants, f"{prefix}_player1_name").text = first_player_name
                                    ET.SubElement(participants, f"{prefix}_player2_name").text = second_player_name

                                # Счет
                                score_data = match_view_model.get("Score", {})
                                score_summary = self._format_score_summary(score_data)
                                sets_summary = self._format_sets_summary(score_data)

                                ET.SubElement(participants, f"{prefix}_score").text = score_summary
                                ET.SubElement(participants, f"{prefix}_sets_summary").text = sets_summary
                                ET.SubElement(participants, f"{prefix}_match_type").text = "normal"

                            elif is_played and not has_score:
                                if winner_id:
                                    winning_team = self._find_winner_team_name(match_data, winner_id)
                                    ET.SubElement(participants, f"{prefix}_team").text = winning_team
                                    short_name = self._create_short_name(winning_team)
                                    ET.SubElement(participants, f"{prefix}_Shortteam").text = short_name

                                    # Имена игроков победившей команды
                                    first_player_name, second_player_name = self._get_winner_player_names(match_data, winner_id)
                                    ET.SubElement(participants, f"{prefix}_player1_name").text = first_player_name
                                    ET.SubElement(participants, f"{prefix}_player2_name").text = second_player_name

                                    # Указываем что это walkover
                                    if "W.O." in cancellation_status.upper() or "WALKOVER" in cancellation_status.upper():
                                        ET.SubElement(participants, f"{prefix}_score").text = "W.O."
                                        ET.SubElement(participants, f"{prefix}_sets_summary").text = "Walkover"
                                        ET.SubElement(participants, f"{prefix}_match_type").text = "walkover"
                                    else:
                                        ET.SubElement(participants, f"{prefix}_score").text = "●"
                                        ET.SubElement(participants, f"{prefix}_sets_summary").text = "Без игры"
                                        ET.SubElement(participants, f"{prefix}_match_type").text = "forfeit"
                                else:
                                    # Нет информации о победителе
                                    ET.SubElement(participants, f"{prefix}_team").text = ""
                                    ET.SubElement(participants, f"{prefix}_score").text = "W.O."
                                    ET.SubElement(participants, f"{prefix}_sets_summary").text = ""
                                    ET.SubElement(participants, f"{prefix}_match_type").text = "walkover"

                            elif not is_played and not has_score:
                                # 3. Матч не сыгран - проверяем на Bye
                                bye_winner = self._check_bye_advancement(match_data)

                                if bye_winner:
                                    # Один из участников Bye - автоматически проходит другой
                                    ET.SubElement(participants, f"{prefix}_team").text = bye_winner["team_name"]
                                    short_name = self._create_short_name(bye_winner["team_name"])
                                    ET.SubElement(participants, f"{prefix}_Shortteam").text = short_name
                                    ET.SubElement(participants, f"{prefix}_player1_name").text = bye_winner["first_player"]
                                    ET.SubElement(participants, f"{prefix}_player2_name").text = bye_winner["second_player"]
                                    ET.SubElement(participants, f"{prefix}_score").text = "●"
                                    ET.SubElement(participants, f"{prefix}_sets_summary").text = "Проходит без игры"
                                    ET.SubElement(participants, f"{prefix}_match_type").text = "bye"
                                else:
                                    # Обычный несыгранный матч
                                    ET.SubElement(participants, f"{prefix}_team").text = ""
                                    ET.SubElement(participants, f"{prefix}_player1_name").text = ""
                                    ET.SubElement(participants, f"{prefix}_score").text = ""
                                    ET.SubElement(participants, f"{prefix}_sets_summary").text = ""
                                    ET.SubElement(participants, f"{prefix}_match_type").text = ""

                            else:
                                # 4. Другие случаи - пустые поля
                                ET.SubElement(participants, f"{prefix}_team").text = ""
                                ET.SubElement(participants, f"{prefix}_player1_name").text = ""
                                ET.SubElement(participants, f"{prefix}_score").text = ""
                                ET.SubElement(participants, f"{prefix}_sets_summary").text = ""
                                ET.SubElement(participants, f"{prefix}_match_type").text = "unknown"

                            match_counter += 1

    def _check_bye_advancement(self, match_data: Dict) -> Optional[Dict]:
        """Проверяет есть ли в матче Bye и возвращает информацию о проходящей команде"""
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        challenger_team = self._get_team_name_from_players(
            challenger_data.get("FirstPlayer", {}),
            challenger_data.get("SecondPlayer", {})
        )
        
        challenged_team = self._get_team_name_from_players(
            challenged_data.get("FirstPlayer", {}),
            challenged_data.get("SecondPlayer", {})
        )
        
        # Если challenger это Bye, то проходит challenged
        if challenger_team.upper() == "BYE" or not challenger_team.strip():
            if challenged_team and challenged_team.upper() != "BYE":
                return {
                    "team_name": challenged_team,
                    "first_player": challenged_data.get("FirstPlayer", {}).get("Name", ""),
                    "second_player": challenged_data.get("SecondPlayer", {}).get("Name", "")
                }
        
        # Если challenged это Bye, то проходит challenger
        elif challenged_team.upper() == "BYE" or not challenged_team.strip():
            if challenger_team and challenger_team.upper() != "BYE":
                return {
                    "team_name": challenger_team,
                    "first_player": challenger_data.get("FirstPlayer", {}).get("Name", ""),
                    "second_player": challenger_data.get("SecondPlayer", {}).get("Name", "")
                }
        
        return None

    def _get_winner_player_names(self, match_data: Dict, winner_id: int) -> tuple:
        """Возвращает имена игроков победившей команды"""
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        if challenger_data.get("EventParticipantId") == winner_id:
            first_player_name = challenger_data.get("FirstPlayer", {}).get("Name", "")
            second_player_name = challenger_data.get("SecondPlayer", {}).get("Name", "")
        elif challenged_data.get("EventParticipantId") == winner_id:
            first_player_name = challenged_data.get("FirstPlayer", {}).get("Name", "")
            second_player_name = challenged_data.get("SecondPlayer", {}).get("Name", "")
        else:
            first_player_name = ""
            second_player_name = ""
        
        return first_player_name, second_player_name

    def _create_short_name(self, full_name: str) -> str:
        """Создает сокращенное имя: первая буква + точка + фамилия"""
        if not full_name or "/" not in full_name:
            return full_name
        
        parts = full_name.split("/")
        short_parts = []
        
        for part in parts:
            part = part.strip()
            if " " in part:
                name_parts = part.split(" ")
                first_name = name_parts[0].strip()
                last_name = " ".join(name_parts[1:]).strip()
                if first_name and last_name:
                    short_name = f"{last_name.replace(' ', '')}"
                    short_parts.append(short_name)
                else:
                    short_parts.append(part)
            else:
                short_parts.append(part)
        
        return "/".join(short_parts)

    def _find_winner_team_name(self, match_data: Dict, winner_id: int) -> str:

        """Находит название команды-победителя по ID"""
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        
        if challenger_data.get("EventParticipantId") == winner_id:
            return self._get_team_name_from_players(
                challenger_data.get("FirstPlayer", {}),
                challenger_data.get("SecondPlayer", {})
            )
        elif challenged_data.get("EventParticipantId") == winner_id:
            return self._get_team_name_from_players(
                challenged_data.get("FirstPlayer", {}),
                challenged_data.get("SecondPlayer", {})
            )
        
        return ""

    def _find_game(self, match_data: Dict, winner_id: int) -> str:
                        #{ 'class': "match-result " + status_class, 'lost-team': short_team_lost, 'winner-team' : short_team, 'sets-info' : sets_summary, 'match-score': score_summary, 'Id': winner_id}
        """Находит название команды-победителя по ID"""
     
        challenger_data = match_data.get("ChallengerParticipant", {})
        challenged_data = match_data.get("ChallengedParticipant", {})
        match_status = self._get_match_status(match_data)
        ger = {}
        ged = {}
        win = {}
        lost = {}

        if challenger_data.get("EventParticipantId") != winner_id:
            lost = self._get_team_name_from_players(  challenger_data.get("FirstPlayer", {}),   challenger_data.get("SecondPlayer", {}))
            ger = {'status': 'lost', 'team': self._create_short_name(lost) }
            
        elif challenged_data.get("EventParticipantId") != winner_id:
            lost = self._get_team_name_from_players(  challenged_data.get("FirstPlayer", {}),   challenged_data.get("SecondPlayer", {}))
            ged = {'status': 'lost', 'team': self._create_short_name(lost)}
            
        if challenger_data.get("EventParticipantId") == winner_id:
            win = self._get_team_name_from_players(  challenger_data.get("FirstPlayer", {}),   challenger_data.get("SecondPlayer", {}))
            ger = {'status': 'winer', 'team': self._create_short_name(win)}
            
        elif challenged_data.get("EventParticipantId") == winner_id:
            win = self._get_team_name_from_players(  challenged_data.get("FirstPlayer", {}),   challenged_data.get("SecondPlayer", {}))
            ged = {'status': 'winer', 'team': self._create_short_name(win)}
        
        
        return {'ger': ger, 'ged': ged, 'status_class': match_status, 'lost': lost, 'win':win}

    def _get_team_name_from_players(self, first_player: Dict, second_player: Dict) -> str:
        """Формирует название команды из имен игроков"""
        names = []
        if first_player and first_player.get("Name"):
            names.append(first_player["Name"])
        if second_player and second_player.get("Name"):
            names.append(second_player["Name"])
        return "/".join(names)

    def _format_score_summary(self, score_data: Dict) -> str:
        """Форматирует итоговый счет"""
        if not score_data:
            return ""
        
        first_score = score_data.get("FirstParticipantScore", 0)
        second_score = score_data.get("SecondParticipantScore", 0)
        return f"{first_score}-{second_score}"

    def _format_sets_summary(self, score_data: Dict) -> str:
        """Форматирует детальный счет по сетам"""
        if not score_data or not score_data.get("DetailedScoring"):
            return ""
        
        sets_summary = []
        for i, set_data in enumerate(score_data["DetailedScoring"]):
            first_score = set_data.get("FirstParticipantScore", 0)
            second_score = set_data.get("SecondParticipantScore", 0)
            sets_summary.append(f"({first_score}-{second_score})")
        
        return " ".join(sets_summary)

    def generate_court_score_xml(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует упрощенный XML для счета на конкретном корте с поддержкой следующего матча"""
        root = ET.Element("templateData")
        
        if tournament_data:
            metadata = tournament_data.get("metadata", {})
        
        # Базовая информация о корте
        ET.SubElement(root, "courtName").text = court_data.get("court_name", "Корт")
        ET.SubElement(root, "courtStatus").text = court_data.get("event_state", "")
        
        current_class =  court_data.get("class_name", "") or court_data.get("current_class_name")

        if current_class:
            
            ET.SubElement(root, "currentClassEvent").text = current_class[:current_class.rfind(',')] + 'l'
            ET.SubElement(root, "currentClassName").text = '' #current_class[current_class.rfind(',')+1:]
                
            ET.SubElement(root, "currentMatchState").text = court_data.get("current_match_state", "")
            
            # Дополнительная информация о текущем матче
            if court_data.get("current_duration_seconds"):
                ET.SubElement(root, "currentDurationSeconds").text = str(court_data["current_duration_seconds"])
            if court_data.get("current_is_winner_first") is not None:
                ET.SubElement(root, "currentWinnerFirst").text = str(court_data["current_is_winner_first"])
        
        team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
        if team1_players:
            for i, player in enumerate(team1_players, 1):
                ET.SubElement(root, f"player{i}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{i}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{i}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{i}FullName").text = player.get("fullName", "")
                ET.SubElement(root, f"player{i}LastNameShort").text = player.get("lastNameShort", "")
                ET.SubElement(root, f"player{i}InitialLastName").text = player.get("initialLastName", "")
        else:
            for i in range(1, 5):
                ET.SubElement(root, f"player{i}FirstName").text = ''
                ET.SubElement(root, f"player{i}MiddleName").text = ''
                ET.SubElement(root, f"player{i}LastName").text = ''
                ET.SubElement(root, f"player{i}FullName").text = ''
                ET.SubElement(root, f"player{i}LastNameShort").text = ''
                ET.SubElement(root, f"player{i}InitialLastName").text = ''
        
        team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
        if team2_players:
            for i, player in enumerate(team2_players, 1):
                player_num = i + 2  # Команда 2 начинается с player3, player4
                ET.SubElement(root, f"player{player_num}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{player_num}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{player_num}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{player_num}FullName").text = player.get("fullName", "")
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
        else:
            ET.SubElement(root, "team1NamesShort").text = ''
            ET.SubElement(root, "team1NamesInitial").text = ''
            ET.SubElement(root, "team1NamesFull").text = ''
        
        if team2_players:
            team2_shorts = [p.get("lastNameShort", "") for p in team2_players if p.get("lastNameShort")]
            ET.SubElement(root, "team2NamesShort").text = ("/".join(team2_shorts)).replace(" ", "")
            
            team2_initials = [p.get("initialLastName", "") for p in team2_players if p.get("initialLastName")]
            ET.SubElement(root, "team2NamesInitial").text = ("/".join(team2_initials)).replace(" ", "")
            
            team2_full = [p.get("fullName", "") for p in team2_players if p.get("fullName")]
            ET.SubElement(root, "team2NamesFull").text = "/".join(team2_full)
        else:
            ET.SubElement(root, "team2NamesShort").text = ''
            ET.SubElement(root, "team2NamesInitial").text = ''
            ET.SubElement(root, "team2NamesFull").text = ''
        
        if court_data.get("next_class_name"):
            ET.SubElement(root, "nextClassName").text = court_data["next_class_name"]
            ET.SubElement(root, "nextStartTime").text = court_data.get("next_start_time", "")
            ET.SubElement(root, "nextScheduledTime").text = court_data.get("next_scheduled_time", "")
            ET.SubElement(root, "nextMatchState").text = court_data.get("next_match_state", "")
            
            # Участники следующего матча - команда 1
            next_team1 = court_data.get("next_first_participant", [])
            if next_team1:
                for i, player in enumerate(next_team1, 1):
                    ET.SubElement(root, f"nextPlayer{i}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{i}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{i}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{i}FullName").text = player.get("fullName", "")
                    ET.SubElement(root, f"nextPlayer{i}LastNameShort").text = player.get("lastNameShort", "")
                    ET.SubElement(root, f"nextPlayer{i}InitialLastName").text = player.get("initialLastName", "")
            
            # Участники следующего матча - команда 2
            next_team2 = court_data.get("next_second_participant", [])
            if next_team2:
                for i, player in enumerate(next_team2, 1):
                    player_num = i + 2  # Команда 2 начинается с nextPlayer3, nextPlayer4
                    ET.SubElement(root, f"nextPlayer{player_num}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}FullName").text = player.get("fullName", "")
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
        else:
            ET.SubElement(root, "nextClassName").text = ''
            ET.SubElement(root, "nextStartTime").text = ''
            ET.SubElement(root, "nextScheduledTime").text = ''
            ET.SubElement(root, "nextMatchState").text = ''
            
            for i in range(1, 5):
                    ET.SubElement(root, f"nextPlayer{i}FirstName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}MiddleName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}LastName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}FullName").text = ''
                    ET.SubElement(root, f"nextPlayer{i}LastNameShort").text = ''
                    ET.SubElement(root, f"nextPlayer{i}InitialLastName").text = ''
            
            ET.SubElement(root, "nextTeam1NamesShort").text = ''
            ET.SubElement(root, "nextTeam1NamesInitial").text = ''
            ET.SubElement(root, "nextTeam1NamesFull").text = ''
            ET.SubElement(root, "nextTeam2NamesShort").text = ''
            ET.SubElement(root, "nextTeam2NamesInitial").text = ''
            ET.SubElement(root, "nextTeam2NamesFull").text = ''
        
        # Время обновления
        ET.SubElement(root, "updated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        return self._prettify_xml(root)

    def generate_schedule_xml(self, tournament_data: Dict) -> str:
        """Генерирует XML для расписания матчей турнира"""
        root = ET.Element("templateData")
        
        # Метаинформация о турнире
        metadata = tournament_data.get("metadata", {})
        tournament = ET.SubElement(root, "tournament")
        ET.SubElement(tournament, "id").text = str(tournament_data.get("tournament_id", ""))
        ET.SubElement(tournament, "name").text = metadata.get("name", "Неизвестный турнир")
        ET.SubElement(tournament, "sport").text = self.get_sport_name(metadata.get("sport", 5))
        ET.SubElement(tournament, "country").text = self.get_country_name(metadata.get("country"))
        if metadata.get("featureImage"):
            ET.SubElement(tournament, "banner").text = metadata["featureImage"]
        
        # Даты турнира
        dates = tournament_data.get("dates", [])
        if dates:
            dates_elem = ET.SubElement(root, "dates")
            ET.SubElement(dates_elem, "count").text = str(len(dates))
            for i, date in enumerate(dates, 1):
                ET.SubElement(dates_elem, f"date_{i}").text = str(date)
        
        # Расписание на основе данных court_usage
        schedule = ET.SubElement(root, "schedule")
        court_usage = tournament_data.get("court_usage")
        
        # Отладочная информация
        logger.info(f"generate_schedule_xml: court_usage type = {type(court_usage)}")
        if court_usage:
            logger.info(f"generate_schedule_xml: court_usage length = {len(court_usage) if isinstance(court_usage, (list, dict)) else 'not list/dict'}")
        
        if court_usage and isinstance(court_usage, list):
            # Обрабатываем массив матчей из запроса №6
            logger.info(f"Обрабатываем {len(court_usage)} матчей из court_usage")
            
            # Группируем матчи по кортам
            courts_matches = {}
            for match in court_usage:
                if not isinstance(match, dict):
                    continue
                    
                court_id = str(match.get("CourtId", ""))
                if court_id not in courts_matches:
                    courts_matches[court_id] = []
                courts_matches[court_id].append(match)
            
            logger.info(f"Найдено матчей по кортам: {[(k, len(v)) for k, v in courts_matches.items()]}")

            # Генерируем XML для каждого корта
            for court_id, matches in courts_matches.items():
                court_elem = ET.SubElement(schedule, "court")
                ET.SubElement(court_elem, "id").text = court_id
                ET.SubElement(court_elem, "name").text = f"Корт {court_id}"

                # Сортируем матчи по времени
                sorted_matches = sorted(matches, key=lambda x: x.get("MatchDate", ""))

                matches_elem = ET.SubElement(court_elem, "matches")
                ET.SubElement(matches_elem, "count").text = str(len(sorted_matches))

                for i, match in enumerate(sorted_matches, 1):
                    match_elem = ET.SubElement(matches_elem, f"match_{i}")

                    # Основная информация о матче
                    ET.SubElement(match_elem, "id").text = str(match.get("TournamentMatchId", ""))
                    ET.SubElement(match_elem, "challenge_id").text = str(match.get("ChallengeId", ""))
                    ET.SubElement(match_elem, "match_date").text = match.get("MatchDate", "")
                    ET.SubElement(match_elem, "duration").text = str(match.get("Duration", 30))
                    ET.SubElement(match_elem, "pool_name").text = match.get("PoolName", "")
                    ET.SubElement(match_elem, "round").text = str(match.get("Round", 1))
                    ET.SubElement(match_elem, "match_order").text = str(match.get("MatchOrder", 0))

                    # Участники
                    ET.SubElement(match_elem, "challenger_name").text = match.get("ChallengerName", "")
                    ET.SubElement(match_elem, "challenged_name").text = match.get("ChallengedName", "")
                    ET.SubElement(match_elem, "challenger_individual").text = match.get("ChallengerIndividualName", "")
                    ET.SubElement(match_elem, "challenged_individual").text = match.get("ChallengedIndividualName", "")

                    # Результаты
                    ET.SubElement(match_elem, "challenger_result").text = str(match.get("ChallengerResult", ""))
                    ET.SubElement(match_elem, "challenged_result").text = str(match.get("ChallengedResult", ""))

                    # Статус матча
                    ET.SubElement(match_elem, "is_team_match").text = str(match.get("IsPartOfTeamMatch", False))
                    ET.SubElement(match_elem, "is_final").text = str(match.get("IsFinal", False))
                    ET.SubElement(match_elem, "is_semifinal").text = str(match.get("IsSemiFinal", False))
                    ET.SubElement(match_elem, "is_quarterfinal").text = str(match.get("IsQuarterFinal", False))
                    ET.SubElement(match_elem, "consolation").text = str(match.get("Consolation", 0))

                    # Время начала 
                    match_date = match.get("MatchDate", "")
                    if match_date:
                        try:
                            from datetime import datetime as dt
                            dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                            ET.SubElement(match_elem, "start_time").text = dt_obj.strftime("%H:%M")
                            ET.SubElement(match_elem, "date_formatted").text = dt_obj.strftime("%d.%m.%Y")
                        except:
                            ET.SubElement(match_elem, "start_time").text = ""
                            ET.SubElement(match_elem, "date_formatted").text = ""

        else:
            logger.warning(f"court_usage отсутствует или имеет неверный тип: {type(court_usage)}")
            # Fallback - используем базовую информацию о кортах
            courts = tournament_data.get("courts", [])
            if courts:
                for court in courts:
                    if not isinstance(court, dict):
                        continue

                    court_elem = ET.SubElement(schedule, "court")
                    court_id = court.get("Item1", "")
                    court_name = court.get("Item2", f"Корт {court_id}")
                    
                    ET.SubElement(court_elem, "id").text = str(court_id)
                    ET.SubElement(court_elem, "name").text = court_name

                    # Заглушка для матчей
                    matches_elem = ET.SubElement(court_elem, "matches")
                    ET.SubElement(matches_elem, "count").text = "0"
                    ET.SubElement(matches_elem, "note").text = "Данные расписания не загружены"

        # Дополнительная информация
        info_elem = ET.SubElement(root, "info")
        total_matches = len(court_usage) if court_usage and isinstance(court_usage, list) else 0
        ET.SubElement(info_elem, "total_matches").text = str(total_matches)
        ET.SubElement(info_elem, "total_courts").text = str(len(tournament_data.get("courts", [])))

        # Время генерации
        ET.SubElement(root, "generated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(root, "type").text = "schedule"
        
        return self._prettify_xml(root)

    def _add_error_xml(self, root: ET.Element, error_message: str):
        """Добавляет информацию об ошибке в XML"""
        error_elem = ET.SubElement(root, "error")
        ET.SubElement(error_elem, "message").text = str(error_message)
        ET.SubElement(error_elem, "timestamp").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(error_elem, "type").text = "data_processing_error"

class XMLFileManager:
    """Менеджер XML и HTML файлов"""
    
    def __init__(self, output_dir: str = "xml_files"):
        self.output_dir = output_dir
        self.xml_generator = XMLGenerator()
        
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_and_save(self, xml_type_info: Dict, tournament_data: Dict, 
                         court_data: Dict = None) -> Dict:
        xml_type = xml_type_info.get("type")
        
        if xml_type == "tournament_table":
            xml_content = self.xml_generator.generate_tournament_table_xml(tournament_data, xml_type_info)
        elif xml_type == "schedule":
            xml_content = self.xml_generator.generate_schedule_xml(tournament_data)
        elif xml_type == "court_score":
            xml_content = self.xml_generator.generate_court_score_xml(court_data, tournament_data)
        else:
            raise ValueError(f"Неизвестный тип XML: {xml_type}")
        
        filename = self._get_filename(xml_type_info, tournament_data)
        filepath = f"{self.output_dir}/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
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
            xml_id = xml_type_info.get("id", "unknown")
            return f"{tournament_id}_{xml_type}_{xml_id}.xml"
    
    def _format_file_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def generate_all_tournament_xml(self, tournament_data: Dict, courts_data: List[Dict] = None) -> List[Dict]:
        from api.rankedin_api import RankedinAPI
        api = RankedinAPI()
        xml_types = api.get_xml_data_types(tournament_data)
        generated_files = []
        
        for xml_type_info in xml_types:
            try:
                xml_type = xml_type_info.get("type")
                if xml_type == "court_score":
                    court_id = xml_type_info.get("court_id")
                    if courts_data:
                        court_data = next((c for c in courts_data if str(c.get("court_id")) == str(court_id)), None)
                        if court_data:
                            file_info = self.generate_and_save(xml_type_info, tournament_data, court_data)
                            generated_files.append(file_info)
                else:
                    file_info = self.generate_and_save(xml_type_info, tournament_data)
                    generated_files.append(file_info)
            except Exception as e:
                logger.error(f"Ошибка генерации XML {xml_type_info.get('name')}: {e}")
                continue
        
        return generated_files
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        import os, time
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