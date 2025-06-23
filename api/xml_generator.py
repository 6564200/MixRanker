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
        """Возвращает название страны по ID """
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
                        #if not isinstance(participant, dict) or not participant.get("players"):
                        #    continue
                            
                        # Первый игрок
                        if len(participant["players"]) > 0:
                            player1 = participant["players"][0]
                            if isinstance(player1, dict):
                                player1_name = player1.get("name", "")
                                if player1_name:
                                    ET.SubElement(matches, f"id{i}PlayerName1").text = str(player1_name)
                                    #ET.SubElement(matches, f"id{i}Player1_Id").text = str(player1.get("id", ""))

                        # Второй игрок
                        if len(participant["players"]) > 1:
                            player2 = participant["players"][1]
                            if isinstance(player2, dict):
                                player2_name = player2.get("name", "")
                                if player2_name:
                                    ET.SubElement(matches, f"id{i}PlayerName2").text = str(player2_name)
                                    #ET.SubElement(matches, f"id{i}Player2_Id").text = str(player2.get("id", ""))

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
            self._add_error_xml(root, f"Критическая ошибка: {str(e)}")


    def generate_court_scoreboard_html(self, court_data: Dict, tournament_data: Dict = None) -> str:
        """Генерирует HTML страницу scoreboard для корта с правильной логикой состояний"""

        # Определяем состояние корта
        match_state = court_data.get("current_match_state", "free")
        
        # Проверяем наличие участников 
        current_participants = court_data.get("current_first_participant") or court_data.get("first_participant", [])
        next_participants = court_data.get("next_first_participant", [])
        
        # Определяем что показывать
        if current_participants and len(current_participants) > 0:
            # Есть текущий матч - показываем его
            team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
            team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
            team1_score = court_data.get("current_first_participant_score", court_data.get("first_participant_score", 0))
            team2_score = court_data.get("current_second_participant_score", court_data.get("second_participant_score", 0))
            detailed_result = court_data.get("current_detailed_result", court_data.get("detailed_result", []))
            class_name = court_data.get("current_class_name", court_data.get("class_name", ""))
            show_current_match = True
            
            # Определяем тип отображения счета
            if match_state == "live":
                show_score = True
            elif match_state == "finished":
                show_score = True
            elif match_state in ["scheduled", "playing_no_score"]:
                show_score = False  # Показываем участников но без счета
            else:
                show_score = True  # По умолчанию показываем
            
        elif next_participants and len(next_participants) > 0:
            # Нет текущего матча, но есть следующий
            team1_players = court_data.get("next_first_participant", [])
            team2_players = court_data.get("next_second_participant", [])
            team1_score = 0
            team2_score = 0
            detailed_result = []
            class_name = court_data.get("next_class_name", "")
            show_current_match = True
            show_score = False  # Следующий матч всегда без счета
            
        else:
            # Корт полностью свободен
            team1_players = []
            team2_players = []
            team1_score = 0
            team2_score = 0
            detailed_result = []
            class_name = ""
            show_current_match = False
            show_score = False

        # Формируем названия команд
        team1_name = ""
        if team1_players:
            team1_initials = [p.get("initialLastName", "") for p in team1_players if p.get("initialLastName")]
            team1_name = " / ".join(team1_initials).upper()

        team2_name = ""
        if team2_players:
            team2_initials = [p.get("initialLastName", "") for p in team2_players if p.get("initialLastName")]
            team2_name = " / ".join(team2_initials).upper()

        # Название корта
        court_name = court_data.get("court_name", "Court")

        # Определяем CSS класс для состояния
        state_class = ""
        if match_state == "live":
            state_class = " live-match"
        elif match_state == "finished":
            state_class = " finished-match"
        elif match_state in ["scheduled", "playing_no_score"]:
            state_class = " next-match"

        # Вычисляем количество сетов для определения ширины
        if show_current_match and detailed_result and len(detailed_result) > 0:
            max_sets = max(len(detailed_result), 1)
        else:
            max_sets = 1  # Минимум 1 слот для сетов
        sets_width = max_sets * 34

        # Название турнира
        tournament_name = ""
        if tournament_data and tournament_data.get("metadata"):
            full_name = tournament_data["metadata"].get("name", "")
            tournament_name = full_name[:10] if full_name else ""

        html_content = f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{court_name} - Scoreboard</title>
        <link rel="stylesheet" href="/static/css/scoreboard.css">
        <style>
            .sets {{
                width: {sets_width}px;
            }}
        </style>
        <script>
            setInterval(function() {{
                location.reload();
            }}, 9000);
        </script>
    </head>
    <body>
        <div class="scoreboard">'''
        
        if show_current_match:
            # Показываем матч (текущий, следующий или без счета)
            html_content += f'''
            <div class="team-row team1{state_class}">
                <div class="team-name">{team1_name}</div>
                <div class="sets">'''
            
            # Сеты для команды 1
            if detailed_result and len(detailed_result) > 0:
                # Показываем сеты если есть детальные результаты (live или finished)
                for i in range(min(max_sets, len(detailed_result))):
                    set_score = detailed_result[i].get("firstParticipantScore", 0)
                    html_content += f'<div class="set">{set_score}</div>'
                
                for i in range(len(detailed_result), max_sets):
                    html_content += '<div class="set">-</div>'
            else:
                # Для матчей без детального счета показываем пустые сеты
                for i in range(max_sets):
                    html_content += '<div class="set">-</div>'
            
            html_content += f'''
                </div>
                <div class="score">{team1_score if show_score else "-"}</div>
            </div>
            
            <div class="team-row team2{state_class}">
                <div class="team-name">{team2_name}</div>
                <div class="sets">'''
            
            # Сеты для команды 2
            if detailed_result and len(detailed_result) > 0:
                # Показываем сеты если есть детальные результаты (live или finished)
                for i in range(min(max_sets, len(detailed_result))):
                    set_score = detailed_result[i].get("secondParticipantScore", 0)
                    html_content += f'<div class="set">{set_score}</div>'
                
                for i in range(len(detailed_result), max_sets):
                    html_content += '<div class="set">-</div>'
            else:
                # Для матчей без детального счета показываем пустые сеты
                for i in range(max_sets):
                    html_content += '<div class="set">-</div>'
            
            html_content += f'''
                </div>
                <div class="score">{team2_score if show_score else "-"}</div>
            </div>'''
            
        else:
            # Корт полностью свободен
            html_content += '''
            <div class="team-row no-match">
                <div class="team-name">NO ACTIVE MATCH</div>
            </div>'''
        
        html_content += '''
            </div>
            <div class="info-bar">
                <div class="tournament-name">''' + tournament_name + (' - ' + class_name if class_name else '') + '''</div>
                <div class="court-name">''' + court_name + '''</div>
            </div>
        </body>
        </html>'''
        
        return html_content



    def _add_elimination_data(self, root: ET.Element, class_data: Dict, draw_index: int):
        """Добавляет данные игр на выбывание в плоском формате с обработкой Bye и Walkover"""
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

                # 1. Обрабатываем участников первого раунда (round_0)
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
                                # 2. Walkover (W.O.) - сыгран но нет счета
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
                                    ET.SubElement(participants, f"{prefix}_match_type").text = "pending"

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
        
        # Проверяем challenger (первый участник)
        challenger_team = self._get_team_name_from_players(
            challenger_data.get("FirstPlayer", {}),
            challenger_data.get("SecondPlayer", {})
        )
        
        # Проверяем challenged (второй участник)  
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
                    short_name = f"{first_name[0]}.{last_name.replace(' ', '')}"
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
        
        # Информация о турнире (если есть)
        if tournament_data:
            metadata = tournament_data.get("metadata", {})
            # ET.SubElement(root, "tournamentName").text = metadata.get("name", "Турнир")
            # ET.SubElement(root, "tournamentSport").text = self._get_sport_name(metadata.get("sport", 5))
        
        # Базовая информация о корте
        # ET.SubElement(root, "courtId").text = str(court_data.get("court_id", ""))
        ET.SubElement(root, "courtName").text = court_data.get("court_name", "Корт")
        ET.SubElement(root, "courtStatus").text = court_data.get("event_state", "")
        # ET.SubElement(root, "courtSport").text = court_data.get("sport", "")
        
        # === ТЕКУЩИЙ МАТЧ ===
        current_class = court_data.get("current_class_name") or court_data.get("class_name", "")
        if current_class:
            ET.SubElement(root, "currentClassName").text = current_class
            # ET.SubElement(root, "currentMatchId").text = str(court_data.get("current_match_id", ""))
            ET.SubElement(root, "currentMatchState").text = court_data.get("current_match_state", "")
            # ET.SubElement(root, "currentIsSingles").text = str(court_data.get("current_is_singles", False))
            
            # Дополнительная информация о текущем матче
            if court_data.get("current_duration_seconds"):
                ET.SubElement(root, "currentDurationSeconds").text = str(court_data["current_duration_seconds"])
            if court_data.get("current_is_winner_first") is not None:
                ET.SubElement(root, "currentWinnerFirst").text = str(court_data["current_is_winner_first"])
        
        # Участники команды 1 (текущий матч)
        team1_players = court_data.get("current_first_participant", court_data.get("first_participant", []))
        if team1_players:
            for i, player in enumerate(team1_players, 1):
                # ET.SubElement(root, f"player{i}Id").text = str(player.get("id", ""))
                ET.SubElement(root, f"player{i}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{i}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{i}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{i}FullName").text = player.get("fullName", "")
                # ET.SubElement(root, f"player{i}Country").text = player.get("countryCode", "")
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
        
        # Участники команды 2 (текущий матч)
        team2_players = court_data.get("current_second_participant", court_data.get("second_participant", []))
        if team2_players:
            for i, player in enumerate(team2_players, 1):
                player_num = i + 2  # Команда 2 начинается с player3, player4
                # ET.SubElement(root, f"player{player_num}Id").text = str(player.get("id", ""))
                ET.SubElement(root, f"player{player_num}FirstName").text = player.get("firstName", "")
                ET.SubElement(root, f"player{player_num}MiddleName").text = player.get("middleName", "")
                ET.SubElement(root, f"player{player_num}LastName").text = player.get("lastName", "")
                ET.SubElement(root, f"player{player_num}FullName").text = player.get("fullName", "")
                # ET.SubElement(root, f"player{player_num}Country").text = player.get("countryCode", "")
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
        
        # === СЛЕДУЮЩИЙ МАТЧ (если есть) ===
        if court_data.get("next_class_name"):
            ET.SubElement(root, "nextClassName").text = court_data["next_class_name"]
            # ET.SubElement(root, "nextMatchId").text = str(court_data.get("next_match_id", ""))
            ET.SubElement(root, "nextStartTime").text = court_data.get("next_start_time", "")
            ET.SubElement(root, "nextScheduledTime").text = court_data.get("next_scheduled_time", "")
            ET.SubElement(root, "nextMatchState").text = court_data.get("next_match_state", "")
            # ET.SubElement(root, "nextIsSingles").text = str(court_data.get("next_is_singles", False))
            
            # Участники следующего матча - команда 1
            next_team1 = court_data.get("next_first_participant", [])
            if next_team1:
                for i, player in enumerate(next_team1, 1):
                    # ET.SubElement(root, f"nextPlayer{i}Id").text = str(player.get("id", ""))
                    ET.SubElement(root, f"nextPlayer{i}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{i}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{i}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{i}FullName").text = player.get("fullName", "")
                    # ET.SubElement(root, f"nextPlayer{i}Country").text = player.get("countryCode", "")
                    ET.SubElement(root, f"nextPlayer{i}LastNameShort").text = player.get("lastNameShort", "")
                    ET.SubElement(root, f"nextPlayer{i}InitialLastName").text = player.get("initialLastName", "")
            
            # Участники следующего матча - команда 2
            next_team2 = court_data.get("next_second_participant", [])
            if next_team2:
                for i, player in enumerate(next_team2, 1):
                    player_num = i + 2  # Команда 2 начинается с nextPlayer3, nextPlayer4
                    # ET.SubElement(root, f"nextPlayer{player_num}Id").text = str(player.get("id", ""))
                    ET.SubElement(root, f"nextPlayer{player_num}FirstName").text = player.get("firstName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}MiddleName").text = player.get("middleName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}LastName").text = player.get("lastName", "")
                    ET.SubElement(root, f"nextPlayer{player_num}FullName").text = player.get("fullName", "")
                    # ET.SubElement(root, f"nextPlayer{player_num}Country").text = player.get("countryCode", "")
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
        ET.SubElement(tournament, "sport").text = self._get_sport_name(metadata.get("sport", 5))
        ET.SubElement(tournament, "country").text = self._get_country_name(metadata.get("country"))
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

    def generate_schedule_html(self, tournament_data: Dict, target_date: str = None) -> str:
        """Генерирует HTML для расписания матчей с временной шкалой и позиционированием"""
        # Метаинформация о турнире
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Неизвестный турнир")
        # Получаем расписание
        court_usage = tournament_data.get("court_usage")

        if not court_usage or not isinstance(court_usage, list):
            return self._generate_empty_schedule_html(tournament_name, "Данные расписания не загружены")

        # Получаем информацию о кортах из tournaments.courts
        courts_info = tournament_data.get("courts", [])
        court_names_map = {}
        for court in courts_info:
            if isinstance(court, dict) and court.get("Item1") and court.get("Item2"):
                court_id = str(court["Item1"])
                court_name = court["Item2"]
                court_names_map[court_id] = court_name

        # Фильтруем матчи по дате (если не указана, берем текущую)
        from datetime import datetime as dt
        if not target_date:
            target_date = dt.now().strftime("%d.%m.%Y")
        
        # Группируем матчи по кортам и фильтруем по дате
        courts_matches = {}
        all_matches = []  # Все матчи для общей нумерации
        
        for match in court_usage:
            if not isinstance(match, dict):
                continue
                
            match_date = match.get("MatchDate", "")
            if match_date:
                try:
                    dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                    match_date_formatted = dt_obj.strftime("%d.%m.%Y")
                    
                    # Фильтруем только матчи на нужную дату
                    if match_date_formatted != target_date:
                        continue
                        
                    court_id = str(match.get("CourtId", ""))
                    court_name = court_names_map.get(court_id, f"Корт {court_id}")
                    
                    # Добавляем время начала для сортировки и позиционирования
                    match["start_time"] = dt_obj.strftime("%H:%M")
                    match["date_formatted"] = match_date_formatted
                    match["court_name"] = court_name
                    match["datetime_obj"] = dt_obj
                    
                    all_matches.append(match)
                    
                    if court_name not in courts_matches:
                        courts_matches[court_name] = []
                    courts_matches[court_name].append(match)
                    
                except Exception as e:
                    continue
        
        if not courts_matches:
            return self._generate_empty_schedule_html(tournament_name, f"Нет матчей на {target_date}")

        # Сортируем матчи в каждом корте по времени и присваиваем номера для каждого корта отдельно
        for court_name in courts_matches:
            courts_matches[court_name].sort(key=lambda x: x.get("datetime_obj"))
            # Присваиваем номера матчей для каждого корта отдельно
            for i, match in enumerate(courts_matches[court_name], 1):
                match["episode_number"] = i

        
        # Создаем временную шкалу
        time_slots = self._generate_time_slots(all_matches)
        
        # Генерируем HTML
        html_content = f'''<!DOCTYPE html>
                        <html lang="ru">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>Расписание матчей - {tournament_name}</title>
                            <link rel="stylesheet" href="/static/css/schedule.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 30000);
                            </script>
                        </head>
                        <body>
                            <div class="schedule-container">
                                <div class="header">
                                    <h1 class="tournament-title">{tournament_name}</h1>
                                    <h2 class="date-title">{target_date}</h2>
                                </div>
                                
                                <div class="main-grid">
                                    <div class="time-scale">'''
        
        # Генерируем временную шкалу
        for time_slot in time_slots:
            html_content += f'''
                <div class="time-slot">{time_slot}</div>'''
        
        html_content += '''
            </div>
            
            <div class="courts-container">
                <div class="courts-header">'''
        
        # Заголовки кортов
        for court_name in sorted(courts_matches.keys()):
            html_content += f'''
                    <div class="court-header">
                        <h3>{court_name}</h3>
                    </div>'''
        
        html_content += '''
                </div>
                
                <div class="matches-grid">'''
        
        # Столбцы кортов с позиционированными матчами
        for court_name in sorted(courts_matches.keys()):
            matches = courts_matches[court_name]
            
            html_content += f'''
                    <div class="court-column">'''
            
            # Генерируем матчи с абсолютным позиционированием по времени
            for match in matches:
                match_status = self._get_match_status(match)
                status_class = self._get_status_class(match_status)
                
                pool_name = match.get("PoolName", "")
                challenger_name = match.get("ChallengerName", "TBD")
                challenged_name = match.get("ChallengedName", "TBD")
                episode_number = match.get("episode_number", 1)
                
                # Результаты матча
                challenger_result = match.get("ChallengerResult", "")
                challenged_result = match.get("ChallengedResult", "")
                
                result_text = ""
                if challenger_result and challenged_result:
                    result_text = f"{challenger_result} - {challenged_result}"
                else:
                    result_text = "0 - 0"
                
                # Цвет группы
                group_class = self._get_group_class(pool_name)
                
                # Форматируем названия команд в одну строку
                teams_text = f"{challenger_name} vs {challenged_name}"
                
                # Вычисляем позицию по времени
                position_top = self._calculate_time_position(match, time_slots)
                
                html_content += f'''
                        <div class="match-item {status_class}" style="top: {position_top}px;">
                            <div class="match-content">
                                <div class="match-number">{episode_number}</div>
                                <div class="match-info">
                                    <div class="match-group-horizontal {group_class}">{pool_name}</div>
                                    <div class="match-teams-horizontal">{teams_text}
                                    
                                    </div>
                                </div>
                                <div class="match-result-horizontal">{result_text}</div>
                            </div>
                        </div>'''
            
            html_content += '''
                    </div>'''
        
        html_content += '''
                                    </div>
                                </div>
                            </div>
                        </div>
                    </body>
                    </html>'''
        return html_content

    def _generate_empty_schedule_html(self, tournament_name: str, message: str) -> str:
        """Генерирует пустую HTML страницу расписания"""
        return f'''<!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Расписание матчей - {tournament_name}</title>
                    <link rel="stylesheet" href="/static/css/schedule.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 30000);
                            </script>
                </head>
                <body>
                    <div class="schedule-container">
                        <div class="header">
                            <h1 class="tournament-title">{tournament_name}</h1>
                        </div>
                        <div class="empty-message">
                            <p>{message}</p>
                        </div>
                    </div>
                </body>
                </html>'''

    def _generate_time_slots(self, matches: list) -> list:
        """Генерирует временные слоты на основе матчей"""
        if not matches:
            return ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
        
        from datetime import datetime as dt, timedelta
        # Находим минимальное и максимальное время
        times = []
        for match in matches:
            if match.get("datetime_obj"):
                times.append(match["datetime_obj"])
        
        if not times:
            return ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
        
        min_time = min(times)
        max_time = max(times)
        
        # Вычисляем общий диапазон в часах
        total_hours = (max_time - min_time).total_seconds() / 3600
        
        # Определяем оптимальный интервал в зависимости от диапазона
        if total_hours <= 2:
            interval_minutes = 15  # для коротких турниров
        elif total_hours <= 4:
            interval_minutes = 20  # для средних турниров
        elif total_hours <= 8:
            interval_minutes = 30  # для длинных турниров
        else:
            interval_minutes = 60  # для очень длинных турниров
        
        # Создаем слоты с динамическим интервалом
        time_slots = []
        # Начинаем за 30 минут до первого матча
        start_time = min_time - timedelta(minutes=30)
        start_time = start_time.replace(minute=(start_time.minute // interval_minutes) * interval_minutes, second=0, microsecond=0)
        
        # Заканчиваем через 30 минут после последнего матча
        end_time = max_time + timedelta(minutes=30)
        
        current_time = start_time
        while current_time <= end_time:
            time_slots.append(current_time.strftime("%H:%M"))
            current_time += timedelta(minutes=interval_minutes)
        return time_slots
    
    def _calculate_time_position(self, match: dict, time_slots: list) -> int:
        """Вычисляет позицию матча по времени в пикселях с улучшенным расчетом"""
        if not match.get("datetime_obj") or not time_slots:
            return 0
        
        from datetime import datetime as dt
        
        match_time = match["datetime_obj"]
        
        # Находим базовое время (первый слот)
        try:
            base_time_str = time_slots[0]
            base_time = dt.strptime(f"{match_time.date()} {base_time_str}", "%Y-%m-%d %H:%M")
        except:
            return 0
        
        # Вычисляем разность в минутах
        time_diff_minutes = (match_time - base_time).total_seconds() / 60
        
        # Высота одного временного слота - 80px (уменьшено для компактности)
        slot_height = 80
        
        # Определяем интервал между слотами на основе их количества
        if len(time_slots) <= 1:
            minutes_per_slot = 30
        else:
            # Вычисляем интервал между слотами из временной шкалы
            try:
                first_time = dt.strptime(f"{match_time.date()} {time_slots[0]}", "%Y-%m-%d %H:%M")
                second_time = dt.strptime(f"{match_time.date()} {time_slots[1]}", "%Y-%m-%d %H:%M")
                minutes_per_slot = (second_time - first_time).total_seconds() / 60
            except:
                minutes_per_slot = 30
        # Пиксели на минуту
        pixels_per_minute = slot_height / minutes_per_slot
        position = int(time_diff_minutes * pixels_per_minute)
        return max(0, position)
    
    def _get_match_status(self, match: Dict) -> str:
        """Определяет статус матча"""
        challenger_result = match.get("ChallengerResult", "")
        challenged_result = match.get("ChallengedResult", "")
        
        if challenger_result and challenged_result:
            return "finished"
        # Проверяем время матча для определения активности
        from datetime import datetime as dt
        try:
            match_date = match.get("MatchDate", "")
            if match_date:
                dt_obj = dt.fromisoformat(match_date.replace('T', ' ').replace('Z', ''))
                now = dt.now()
                duration = match.get("Duration", 30)  # минуты
                
                if dt_obj <= now <= dt_obj.replace(minute=dt_obj.minute + duration):
                    return "active"
                elif dt_obj > now:
                    return "future"
                else:
                    return "finished"
        except:
            pass
        return "future"
    
    def _get_status_class(self, status: str) -> str:
        """Возвращает CSS класс для статуса"""
        return {
            "finished": "match-finished",
            "active": "match-active", 
            "future": "match-future"
        }.get(status, "match-future")
    
    def _get_group_class(self, group_name: str) -> str:
        """Возвращает CSS класс для группы на основе хеша названия"""
        if not group_name:
            return "match-group-1"
        # Создаем хеш от названия группы для стабильного распределения цветов
        hash_value = sum(ord(c) for c in group_name.upper())
        # Используем остаток от деления на 7 для получения номера цвета (1-7)
        color_number = (hash_value % 7) + 1
        
        return f"match-group-{color_number}"

    def generate_and_save_schedule_html(self, tournament_data: Dict, target_date: str = None) -> Dict:
        """Генерирует и сохраняет HTML файл расписания"""
        
        # Генерация HTML
        html_content = self.generator.generate_schedule_html(tournament_data, target_date)
        
        # Определяем дату для имени файла
        from datetime import datetime as dt
        if not target_date:
            target_date = dt.now().strftime("%d.%m.%Y")
        
        # Сохранение файла
        safe_date = target_date.replace(".", "_")
        filename = f"{tournament_data.get('tournament_id', 'unknown')}_schedule_{safe_date}.html"
        filepath = f"{self.output_dir}/{filename}"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            logger.error(f"Ошибка сохранения файла {filepath}: {e}")
            raise
        
        # Информация о файле
        import os
        if os.path.exists(filepath):
            file_stats = os.stat(filepath)
        else:
            logger.error(f"Файл не найден после создания: {filepath}")
            raise FileNotFoundError(f"Файл не создался: {filepath}")
        
        file_info = {
            "id": f"schedule_html_{safe_date}",
            "name": f"Расписание матчей HTML - {target_date}",
            "filename": filename,
            "url": f"/html/{filename}",
            "size": self._format_file_size(file_stats.st_size),
            "created": datetime.now().isoformat(),
            "type": "html_schedule",
            "target_date": target_date
        }

        return file_info

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

    def generate_elimination_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для турнирной сетки на выбывание (elimination)"""
        # Получаем данные elimination
        class_id = xml_type_info.get("class_id")
        draw_index = xml_type_info.get("draw_index", 0)
        
        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        elimination_data = class_data.get("elimination", [])
        
        if draw_index >= len(elimination_data):
            return self._generate_empty_elimination_html("Нет данных турнирной сетки")
        
        elim_data = elimination_data[draw_index]
        if not elim_data or "Elimination" not in elim_data:
            return self._generate_empty_elimination_html("Неверные данные турнирной сетки")
        
        bracket_data = elim_data["Elimination"]
        
        # Название турнира и класса
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Турнир")
        class_name = xml_type_info.get("class_name", "Категория")
        stage_name = xml_type_info.get("stage_name", "Плей-офф")
        
        # Анализируем структуру турнира для определения количества раундов
        rounds_data = self._analyze_elimination_structure(bracket_data)
        
        html_content = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{class_name} - {stage_name}</title>
    <link rel="stylesheet" href="/static/css/elimination.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 30000);
                            </script>
</head>
<body>
    <div class="elimination-container">
        <div class="tournament-header">
            <h1>{tournament_name}</h1>
            <h2>{class_name} - {stage_name}</h2>
        </div>
        <div class="bracket-grid" style="grid-template-columns: repeat({len(rounds_data)}, 1fr);">'''
        
        # Генерируем колонки для каждого раунда
        for round_index, round_info in enumerate(rounds_data):
            if round_index == 0:
                # Первый раунд - команды
                html_content += f'''
                                    <div class="round-column">
                                        <div class="round-header">{round_info['title']}</div>
                                        <div class="round-matches">'''
                html_content += self._generate_first_round_html(bracket_data)
            else:
                # Победители
                if (len(rounds_data)-1) == round_index: 
                    html_content += f'''
                                    <div class="round-column-win">
                                        <div class="round-header">{round_info['title']}</div>
                                        <div class="round-matches">'''
                    html_content += self._generate_subsequent_round_html(round_index, round_info['matches'])
                else: # Последующие раунды
                    html_content += f'''
                                        <div class="round-column-2">
                                            <div class="round-header">{round_info['title']}</div>
                                            <div class="round-matches">'''
                    html_content += self._generate_subsequent_round_html(round_index, round_info['matches'])
            
            html_content += '''
                </div>
            </div>'''
        
        html_content += '''
        </div>
    </div>
</body>
</html>'''
        
        return html_content

    def _analyze_elimination_structure(self, bracket_data: Dict) -> List[Dict]:
        """Анализирует структуру elimination для определения раундов"""
        rounds_data = []
        
        # Первый раунд - участники
        first_round_participants = bracket_data.get("FirstRoundParticipantCells", [])
        if first_round_participants:
            rounds_data.append({
                'title': 'Команды',
                'matches': first_round_participants,
                'type': 'participants'
            })
        
        # Анализируем матчи по раундам
        if bracket_data.get("DrawData"):
            matches_by_round = {}
            
            for round_matches in bracket_data["DrawData"]:
                for match_data in round_matches:
                    if match_data:
                        round_number = match_data.get("Round", 1)
                        if round_number not in matches_by_round:
                            matches_by_round[round_number] = []
                        matches_by_round[round_number].append(match_data)
            
            # Определяем названия раундов
            sorted_rounds = sorted(matches_by_round.keys())
            round_names = self._generate_round_names(len(sorted_rounds))
            
            for i, round_number in enumerate(sorted_rounds):
                rounds_data.append({
                    'title': round_names[i] if i < len(round_names) else f'Раунд {round_number}',
                    'matches': matches_by_round[round_number],
                    'type': 'matches',
                    'round_number': round_number
                })
        
        return rounds_data

    def _generate_round_names(self, num_rounds: int) -> List[str]:
        """Генерирует названия раундов в зависимости от их количества"""
        if num_rounds == 1:
            return ['Финал']
        elif num_rounds == 2:
            return ['Полуфинал', 'Финал']
        elif num_rounds == 3:
            return ['Четвертьфинал', 'Полуфинал', 'Финал']
        elif num_rounds == 4:
            return ['1/8 финала', 'Четвертьфинал', 'Полуфинал', 'Финал']
        elif num_rounds == 5:
            return ['1/16 финала', '1/8 финала', 'Четвертьфинал', 'Полуфинал', 'Финал']
        else:
            # Для большего количества раундов
            names = []
            for i in range(num_rounds - 3):
                names.append(f'Раунд {i + 1}')
            names.extend(['Четвертьфинал', 'Полуфинал', 'Финал'])
            return names

    def _generate_first_round_html(self, bracket_data: Dict) -> str:
        """Генерирует HTML для первого раунда (участники)"""
        html = ""
        participants = bracket_data.get("FirstRoundParticipantCells", [])
        
        for i, participant_data in enumerate(participants, 1):
            # Формируем название команды
            team_names = []
            if participant_data.get("FirstPlayer", {}).get("Name"):
                team_names.append(participant_data["FirstPlayer"]["Name"])
            if participant_data.get("SecondPlayer", {}).get("Name"):
                team_names.append(participant_data["SecondPlayer"]["Name"])
            
            team_name = "/".join(team_names) if team_names else "TBD"
            short_name = self._create_short_name(team_name) if team_name != "TBD" else "TBD"
            
            # Проверяем, является ли это Bye
            is_bye = team_name.upper() == "BYE" or not team_names
            css_class = "bye-team" if is_bye else ""
            
            html += f'''
            <div class="team-slot {css_class}">
                <div class="team-number">{i}</div>
                <div class="team-name">{short_name}</div>
            </div>'''
        return html

    def _generate_subsequent_round_html(self, round_index: int, matches: List[Dict]) -> str:
        """Генерирует HTML для последующих раундов с обработкой Bye и Walkover"""
        html = ""
        
        for match_counter, match_data in enumerate(matches, 1):
            match_view_model = match_data.get("MatchViewModel", {})
            is_played = match_view_model.get("IsPlayed", False)
            has_score = match_view_model.get("HasScore", False)
            cancellation_status = match_data.get("CancellationStatus", "")
            winner_id = match_data.get("WinnerParticipantId")
            
            # Определяем тип матча и CSS класс
            match_type = "pending"
            status_class = "pending"
            
            if is_played and has_score:
                # Обычный сыгранный матч
                match_type = "normal"
                status_class = "played"
                
                winning_team = self._find_winner_team_name(match_data, winner_id)
                short_team = self._create_short_name(winning_team)
                
                # Счет
                score_data = match_view_model.get("Score", {})
                score_summary = self._format_score_summary(score_data)
                sets_summary = self._format_sets_summary(score_data)
                
                html += f'''
                <div class="match-result {status_class}">
                    <div class="winner-team">{short_team}</div>
                    <div class="sets-info">{sets_summary}</div>
                    <div class="match-score">{score_summary}</div>
                    
                </div>'''
                
            elif is_played and not has_score:
                # Walkover (W.O.)
                match_type = "walkover"
                status_class = "walkover"
                
                if winner_id:
                    winning_team = self._find_winner_team_name(match_data, winner_id)
                    short_team = self._create_short_name(winning_team)
                    
                    if "W.O." in cancellation_status.upper() or "WALKOVER" in cancellation_status.upper():
                        score_text = "W.O."
                        sets_text = "Walkover"
                    else:
                        score_text = "●"
                        sets_text = "Forfeit"
                        
                    html += f'''
                    <div class="match-result {status_class}">
                        <div class="winner-team">{short_team}</div>
                        <div class="sets-info walkover-info">{sets_text}</div>
                        <div class="match-score walkover-score">{score_text}</div>
                        
                    </div>'''
                else:
                    html += f'''
                    <div class="match-result {status_class}">
                        <div class="winner-team"> </div>
                        <div class="match-score walkover-score">W.O.</div>
                        <div class="sets-info walkover-info">Walkover</div>
                    </div>'''
                    
            elif not is_played and not has_score:
                # Проверяем на Bye
                bye_winner = self._check_bye_advancement(match_data)
                
                if bye_winner:
                    # Автоматический проход через Bye
                    match_type = "bye"
                    status_class = "bye"
                    
                    short_team = self._create_short_name(bye_winner["team_name"])
                    
                    html += f'''
                    <div class="match-result {status_class}">
                        <div class="winner-team">{short_team}</div>
                        
                        <div class="sets-info bye-info">Bye</div>
                        <div class="match-score bye-score">●</div>
                    </div>'''
                else:
                    # Обычный несыгранный матч
                    html += f'''
                    <div class="match-result pending">
                        <div class="winner-team"> </div>
                        <div class="match-score"> </div>
                        <div class="sets-info"></div>
                    </div>'''
            else:
                # Неопределенное состояние
                html += f'''
                <div class="match-result pending">
                    <div class="winner-team"> </div>
                    <div class="match-score"> </div>
                    <div class="sets-info"></div>
                </div>'''
        
        return html


    def _generate_empty_elimination_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу elimination"""
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Турнирная сетка</title>
    <link rel="stylesheet" href="/static/css/elimination.css">
                            <script>
                                setInterval(function() {{
                                    location.reload();
                                }}, 30000);
                            </script>
</head>
<body>
    <div class="elimination-container">
        <div class="empty-message">
            <p>{message}</p>
        </div>
    </div>
</body>
</html>'''



    def generate_round_robin_html(self, tournament_data: Dict, xml_type_info: Dict) -> str:
        """Генерирует HTML для групповой турнирной таблицы (round robin)"""
        
        # Получаем данные round robin
        class_id = xml_type_info.get("class_id")
        draw_index = xml_type_info.get("draw_index", 0)
        
        class_data = tournament_data.get("draw_data", {}).get(str(class_id), {})
        round_robin_data = class_data.get("round_robin", [])
        
        if draw_index >= len(round_robin_data):
            return self._generate_empty_round_robin_html("Нет данных групповой таблицы")
        
        rr_data = round_robin_data[draw_index]
        if not rr_data or "RoundRobin" not in rr_data:
            return self._generate_empty_round_robin_html("Неверные данные групповой таблицы")
        
        group_data = rr_data["RoundRobin"]
        
        # Название турнира и класса
        metadata = tournament_data.get("metadata", {})
        tournament_name = metadata.get("name", "Турнир")
        class_name = xml_type_info.get("class_name", "Категория")
        group_name = xml_type_info.get("group_name", "Группа")

        # Получаем участников и матчи
        participants = self._extract_rr_participants(group_data)
        
        matches_matrix = self._extract_rr_matches_matrix(group_data, len(participants))

        standings = self._extract_rr_standings(group_data)
        
        html_content = f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{class_name} - {group_name}</title>
        <link rel="stylesheet" href="/static/css/round_robin.css">
        <script>
            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="round-robin-container">
            <div class="tournament-header">
                <h1>{tournament_name}</h1>
                <h2>{class_name} - {group_name}</h2>
            </div>
            
            <div class="table-wrapper">
                <table class="round-robin-table">
                    <thead>
                        <tr>
                            <th class="team-number-header"><span>№</span></th>
                            <th class="group-header"><span>{class_name}</span></th>'''
        
        # Заголовки столбцов (номера команд)
        for i in range(1, len(participants) + 1):
            html_content += f'<th class="team-number-header"><span>{i}</span></th>'
        
        html_content += '''
                            <th class="points-header"><span>ОЧКИ</span></th>
                            <th class="place-header"><span>МЕСТО</span></th>
                        </tr>
                    </thead>
                    <tbody>'''
        
        # Строки таблицы
        for i, participant in enumerate(participants):
            place = self._get_participant_place(participant, standings)
            points = self._get_participant_points(participant, standings)
            
            # Определяем CSS класс для места
            place_class = ""
            if place == 1:
                place_class = " winner"
            elif place == 2:
                place_class = " second"
            elif place == 3:
                place_class = " third"
            
            html_content += f'''
                        <tr class="team-row{place_class}">
                            <td class="team-number-cell">
                                <div class="team-number">{i + 1}</div>
                            </td>
                            <td class="team-name-cell">
                                <div class="team-name">{participant.get("short_name", " ")}</div>
                            </td>'''
            
            # Ячейки результатов матчей
            for j in range(len(participants)):
                if i == j:
                    # Диагональная ячейка
                    html_content += '<td class="diagonal-cell"></td>'
                else:
                    match_result = matches_matrix.get(f"{i}_{j}", {})
                    result_class = self._get_match_result_class(match_result)
                    
                    if match_result.get("is_bye"):
                        html_content += '<td class="match-cell bye-cell">●</td>'
                    elif match_result.get("has_result"):
                        score = match_result.get("score", "-")
                        sets = match_result.get("sets", "")
                        html_content += f'''
                            <td class="match-cell {result_class}">
                                <div class="match-score">{score}</div>
                                <div class="match-sets">{sets}</div>
                            </td>'''
                    else:
                        html_content += '<td class="match-cell empty-cell"></td>'
            
            html_content += f'''
                            <td class="points-cell"><span>{points}</span></td>
                            <td class="place-cell"><span>{place}</span></td>
                        </tr>'''
        
        html_content += '''
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>'''

        return html_content

    def _extract_rr_participants(self, group_data: Dict) -> List[Dict]:
        """Извлекает участников из групповых данных"""
        participants = []
        pool_data = group_data.get("Pool", [])
        
        for row_index, row in enumerate(pool_data):
            if not isinstance(row, list):
                continue
                
            for cell_index, cell in enumerate(row):
                if not isinstance(cell, dict):
                    continue
                    
                if cell.get("CellType") == "ParticipantCell" and cell.get("ParticipantCell"):
                    participant_cell = cell["ParticipantCell"]
                    
                    if participant_cell.get("Players") and isinstance(participant_cell["Players"], list):
                        team_names = []
                        player_ids = []
                        for player in participant_cell["Players"]:
                            if isinstance(player, dict) and player.get("Name"):
                                team_names.append(player["Name"])
                                if player.get("Id"):
                                    player_ids.append(str(player["Id"]))

                        if team_names:
                            full_name = "/".join(team_names)
                            short_name = self._create_short_name(full_name) if full_name != "Bye" else "Bye"
                            
                            participants.append({
                                "index": participant_cell.get("Index", len(participants)),
                                "participant_id": participant_cell.get("ParticipantId"),  # Добавляем ParticipantId
                                "full_name": full_name,
                                "short_name": short_name,
                                "is_bye": full_name.upper() == "BYE",
                                "player_ids": player_ids  # Массив ID игроков
                            })

        # Берем только первую половину
        if len(participants) > 0:
            half_count = len(participants) // 2
            if half_count > 0:
                participants = participants[:half_count]
        
        return participants

    def _extract_rr_matches_matrix(self, group_data: Dict, num_participants: int) -> Dict:
        """Извлекает матчи в формате матрицы"""
        matches_matrix = {}
        pool_data = group_data.get("Pool", [])
        
        for row_index, row in enumerate(pool_data):
            if not isinstance(row, list):
                continue
    
            for cell_index, cell in enumerate(row):
                if not isinstance(cell, dict):
                    continue
                    
                if cell.get("CellType") == "MatchCell" and cell.get("MatchCell"):
                    match_cell = cell["MatchCell"]
                    match_results = match_cell.get("MatchResults", {})
                    
                    if row_index != cell_index:  # Не диагональные элементы
                        match_key = f"{row_index-1}_{cell_index-1}"
                        
                        match_info = {
                            "has_result": bool(match_results.get("IsPlayed", False)),
                            "is_bye": False,
                            "score": "",
                            "sets": ""
                        }
                        
                        if match_results.get("HasScore") and match_results.get("Score"):
                            score_data = match_results["Score"]
                            first_score = score_data.get("FirstParticipantScore", 0)
                            second_score = score_data.get("SecondParticipantScore", 0)
                            
                            match_info["score"] = f"{first_score}-{second_score}"
                            
                            # Форматируем сеты
                            detailed_scoring = score_data.get("DetailedScoring", [])
                            if detailed_scoring:
                                sets_parts = []
                                for set_data in detailed_scoring:
                                    set_first = set_data.get("FirstParticipantScore", 0)
                                    set_second = set_data.get("SecondParticipantScore", 0)
                                    sets_parts.append(f"{set_first}-{set_second}")
                                match_info["sets"] = " ".join(sets_parts)
                        else:
                            cancellation_status = match_results.get('CancellationStatus') or '' # вернет пустую если None
                            if 'Won' in cancellation_status:
                                match_info["score"] = 'Won'
                            elif 'Lost' in cancellation_status:
                                match_info["score"] = 'Lost'
                        matches_matrix[match_key] = match_info
        
        return matches_matrix

    def _extract_rr_standings(self, group_data: Dict) -> List[Dict]:
        """Извлекает турнирную таблицу"""
        standings_data = group_data.get("Standings", [])
        standings = []
        
        for standing in standings_data:
            if isinstance(standing, dict):
                # Собираем ID игроков из standings
                player_ids = []
                if standing.get('DoublesPlayer1Model', {}).get('Id'):
                    player_ids.append(str(standing['DoublesPlayer1Model']['Id']))
                if standing.get('DoublesPlayer2Model', {}).get('Id'):
                    player_ids.append(str(standing['DoublesPlayer2Model']['Id']))
                
                standings.append({
                    "participant_id": str(standing.get("ParticipantId", "")),
                    "standing": standing.get("Standing", 0),
                    "wins": standing.get("Wins", 0),
                    "match_points": standing.get("MatchPoints", 0),
                    "player_ids": player_ids  # Массив ID игроков
                })
        
        return standings

    def _get_participant_place(self, participant: Dict, standings: List[Dict]) -> int:
        """Получает место участника по сопоставлению ParticipantId или player_ids"""
        
        # Сначала пробуем сопоставить по ParticipantId
        participant_id = participant.get("participant_id")
        if participant_id:
            for standing in standings:
                if str(standing.get("participant_id", "")) == str(participant_id):
                    return standing.get("standing", 0)
        
        # Если не найдено, пробуем сопоставить по player_ids
        participant_player_ids = set(participant.get("player_ids", []))
        if participant_player_ids:
            for standing in standings:
                standing_player_ids = set(standing.get("player_ids", []))
                # Проверяем пересечение множеств ID игроков
                if participant_player_ids & standing_player_ids:  # Если есть общие элементы
                    return standing.get("standing", 0)
        
        # Fallback - по index 
        participant_index = participant.get("index", 0)
        for standing in standings:
            if int(standing.get("participant_id", -1)) == participant_index:
                return standing.get("standing", 0)
        
        return 0

    def _get_participant_points(self, participant: Dict, standings: List[Dict]) -> int:
        """Получает очки участника по сопоставлению ParticipantId или player_ids"""
        
        # Сначала пробуем сопоставить по ParticipantId
        participant_id = participant.get("participant_id")
        if participant_id:
            for standing in standings:
                if str(standing.get("participant_id", "")) == str(participant_id):
                    return standing.get("match_points", 0)  # Используем match_points вместо wins
        
        # Если не найдено, пробуем сопоставить по player_ids
        participant_player_ids = set(participant.get("player_ids", []))
        if participant_player_ids:
            for standing in standings:
                standing_player_ids = set(standing.get("player_ids", []))
                # Проверяем пересечение множеств ID игроков
                if participant_player_ids & standing_player_ids:  # Если есть общие элементы
                    return standing.get("match_points", 0)
        
        # Fallback - по index 
        participant_index = participant.get("index", 0)
        for standing in standings:
            if int(standing.get("participant_id", -1)) == participant_index:
                return standing.get("match_points", 0)
        
        return 0

    def _get_match_result_class(self, match_result: Dict) -> str:
        """Возвращает CSS класс для результата матча"""
        if match_result.get("is_bye"):
            return "bye"
        elif match_result.get("has_result"):
            return "played"
        else:
            return "empty"

    def _generate_empty_round_robin_html(self, message: str) -> str:
        """Генерирует пустую HTML страницу round robin"""
        return f'''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Групповая таблица</title>
        <link rel="stylesheet" href="/static/css/round_robin.css">
        <script>
            setInterval(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="round-robin-container">
            <div class="empty-message">
                <p>{message}</p>
            </div>
        </div>
    </body>
    </html>'''

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
            
            # Создаем имя файла
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