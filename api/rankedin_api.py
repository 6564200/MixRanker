#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с API rankedin.com
"""

import requests
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class RankedinAPI:
    """Класс для работы с API rankedin.com"""
    
    def __init__(self, timeout: int = 10):
        self.api_base = "https://api.rankedin.com/v1"
        self.live_api_base = "https://live.rankedin.com/api/v1"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'vMixRanker/2.5',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, url: str, method: str = 'GET', data: Dict = None) -> Optional[Dict]:
        """Выполняет HTTP запрос с обработкой ошибок"""
        try:
            if method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=self.timeout)
            else:
                response = self.session.get(url, timeout=self.timeout)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout при запросе к {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON от {url}: {e}")
            return None
    
    # ЗАПРОС №1: Метаданные турнира
    def get_tournament_metadata(self, tournament_id: str) -> Optional[Dict]:
        """
        Получение метаданных турнира (название, описание, спорт, страна, баннер)
        https://api.rankedin.com/v1/metadata/GetFeatureMetadataAsync?feature=Tournament&id={tournamentId}
        """
        url = f"{self.api_base}/metadata/GetFeatureMetadataAsync"
        params = f"?feature=Tournament&id={tournament_id}"
        
        logger.info(f"Получение метаданных турнира {tournament_id}")
        result = self._make_request(url + params)
        
        if result:
            logger.info(f"Метаданные турнира {tournament_id}: {result.get('name', 'Без названия')}")
        
        return result
    
    # ЗАПРОС №2: Категории турнира
    def get_tournament_classes(self, tournament_id: str) -> Optional[List[Dict]]:
        """
        Получение списка категорий турнира
        https://api.rankedin.com/v1/Tournament/GetTournamentClassesAsync?tournamentId={tournamentId}
        """
        url = f"{self.api_base}/Tournament/GetTournamentClassesAsync"
        params = f"?tournamentId={tournament_id}"
        
        logger.info(f"Получение категорий турнира {tournament_id}")
        result = self._make_request(url + params)
        
        if result:
            logger.info(f"Найдено {len(result)} категорий для турнира {tournament_id}")
        
        return result
    
    # ЗАПРОС №3: Информация о кортах
    def get_tournament_courts(self, tournament_id: str) -> Optional[Dict]:
        """
        Получение информации о кортах турнира
        https://api.rankedin.com/v1/Tournament/GetTournamentTimetableInfoAsync/?tournamentId={tournamentId}
        """
        url = f"{self.api_base}/Tournament/GetTournamentTimetableInfoAsync/"
        params = f"?tournamentId={tournament_id}"
        
        logger.info(f"Получение информации о кортах турнира {tournament_id}")
        result = self._make_request(url + params)
        
        if result and 'Courts' in result:
            logger.info(f"Найдено {len(result['Courts'])} кортов для турнира {tournament_id}")
        
        return result
    
    # ЗАПРОС №4: Даты проведения турнира
    def get_tournament_dates(self, tournament_id: str) -> Optional[List[str]]:
        """
        Получение дат проведения турнира
        https://api.rankedin.com/v1/Tournament/GetTimetableDatesAsync?tournamentId={tournamentId}
        """
        url = f"{self.api_base}/Tournament/GetTimetableDatesAsync"
        params = f"?tournamentId={tournament_id}"
        
        logger.info(f"Получение дат турнира {tournament_id}")
        result = self._make_request(url + params)
        
        if result:
            logger.info(f"Турнир {tournament_id} проводится {len(result)} дней")
        
        return result
    


    # ЗАПРОС №5: Планировщик кортов
    def get_court_planner(self, tournament_id: str, dates: List[str]) -> Optional[Dict]:
        """
        Получение расписания кортов на указанные даты
        https://api.rankedin.com/v1/Tournament/GetCourtPlannerAsync (POST)
        """
        url = f"{self.api_base}/Tournament/GetCourtPlannerAsync"
        data = {
            "tournamentId": tournament_id,
            "dates": dates
        }
        
        logger.info(f"Получение расписания кортов для турнира {tournament_id}, даты: {dates}")
        result = self._make_request(url, method='POST', data=data)
        
        if result:
            logger.info(f"Планировщик кортов для турнира {tournament_id}: получено {len(result) if isinstance(result, list) else 'object'}")
        else:
            logger.warning(f"Не удалось получить планировщик кортов для турнира {tournament_id}")
        
        return result

    # ЗАПРОС №6: Использование кортов
    def get_court_usage(self, tournament_id: str, dates: List[str]) -> Optional[Dict]:
        """
        Получение информации об использовании кортов (матчи, результаты)
        https://api.rankedin.com/v1/Tournament/GetCourtUsageAsync (POST)
        """
        url = f"{self.api_base}/Tournament/GetCourtUsageAsync"
        data = {
            "tournamentId": tournament_id,
            "dates": dates
        }
        
        logger.info(f"Получение использования кортов для турнира {tournament_id}, даты: {dates}")
        result = self._make_request(url, method='POST', data=data)
        
        if result:
            if isinstance(result, list):
                logger.info(f"Использование кортов для турнира {tournament_id}: получено {len(result)} матчей")
                # Логируем первый матч для примера
                if len(result) > 0:
                    first_match = result[0]
                    logger.info(f"Пример матча: CourtId={first_match.get('CourtId')}, MatchDate={first_match.get('MatchDate')}, Teams={first_match.get('ChallengerName')} vs {first_match.get('ChallengedName')}")
            else:
                logger.info(f"Использование кортов для турнира {tournament_id}: получен объект типа {type(result)}")
        else:
            logger.warning(f"Не удалось получить использование кортов для турнира {tournament_id}")
        
        return result


    
    # ЗАПРОС №7: Табло корта
    def get_court_scoreboard(self, court_id: str) -> Optional[Dict]:
        """
        Получение данных табло конкретного корта
        https://live.rankedin.com/api/v1/court/{CourtId}/scoreboard
        """
        url = f"{self.live_api_base}/court/{court_id}/scoreboard"
        
        logger.debug(f"Получение данных табло корта {court_id}")
        result = self._make_request(url)
        
        if result and not result.get('error'):
            # Обработка данных корта
            processed_result = self._process_court_data(result, court_id)
            return processed_result
        
        return result or {"court_id": court_id, "error": "Ошибка получения данных"}

    def _process_court_data(self, data: Dict, court_id: str) -> Dict:
        """Обрабатывает данные корта в единый формат с поддержкой различных структур JSON"""
        if not data:
            return {"court_id": court_id, "error": "Пустые данные"}

        # Базовая информация о корте
        details = data.get("details", {})
        result = {
            "court_id": details.get("courtId", court_id),
            "court_name": details.get("courtName", f"Корт {court_id}"),
            "event_state": details.get("eventState", "Неизвестный статус"),
            "sport": details.get("sport", ""),
        }
        
        # ТЕКУЩИЙ/АКТИВНЫЙ МАТЧ (liveMatch имеет приоритет, потом previousMatch)
        current_match = data.get("liveMatch") or data.get("previousMatch", {})
        if current_match:
            result.update(self._extract_match_data(current_match, "current"))
        else:
            # Если нет текущего матча, инициализируем пустые значения
            result.update({
                "current_class_name": "",
                "current_first_participant_score": 0,
                "current_second_participant_score": 0,
                "current_detailed_result": [],
                "current_first_participant": [],
                "current_second_participant": [],
                "current_match_state": "free",
                "current_match_id": None,
                "current_is_winner_first": None
            })
        
        # СЛЕДУЮЩИЙ МАТЧ (nextMatch)
        next_match = data.get("nextMatch", {})
        if next_match:
            result.update(self._extract_match_data(next_match, "next"))
        else:
            result.update({
                "next_class_name": "",
                "next_first_participant": [],
                "next_second_participant": [],
                "next_scheduled_time": "",
                "next_start_time": "",
                "next_match_state": "none",
                "next_match_id": None
            })
        
        # Обратная совместимость со старым форматом
        result.update({
            "class_name": result.get("current_class_name", ""),
            "first_participant_score": result.get("current_first_participant_score", 0),
            "second_participant_score": result.get("current_second_participant_score", 0),
            "detailed_result": result.get("current_detailed_result", []),
            "first_participant": result.get("current_first_participant", []),
            "second_participant": result.get("current_second_participant", [])
        })
        
        return result

    def _extract_match_data(self, match_data: Dict, prefix: str) -> Dict:
        """Извлекает данные матча с указанным префиксом"""
        if not match_data:
            return {}
        
        result = {}
        
        # ID матча
        result[f"{prefix}_match_id"] = match_data.get("matchId")
        
        # Название класса/категории
        result[f"{prefix}_class_name"] = match_data.get("className", "")
        
        # Тип матча
        result[f"{prefix}_is_singles"] = match_data.get("isSinglesMatch", False)
        
        # Участники
        first_participants = match_data.get("firstParticipant", [])
        second_participants = match_data.get("secondParticipant", [])
        
        result[f"{prefix}_first_participant"] = self._extract_players(first_participants)
        result[f"{prefix}_second_participant"] = self._extract_players(second_participants)
        
        # Счет (только для текущего/завершенного матча)
        if prefix in ["current", "live"] and "score" in match_data:
            score_data = match_data["score"]
            result[f"{prefix}_first_participant_score"] = score_data.get("firstParticipantScore", 0)
            result[f"{prefix}_second_participant_score"] = score_data.get("secondParticipantScore", 0)
            
            # Информация о победителе
            result[f"{prefix}_is_winner_first"] = match_data.get("isFirstParticipantWinner")
            
            # Детализированные результаты по сетам
            detailed_result = score_data.get("detailedResult", [])
            result[f"{prefix}_detailed_result"] = [
                {
                    "firstParticipantScore": set_data.get("firstParticipantScore", 0),
                    "secondParticipantScore": set_data.get("secondParticipantScore", 0),
                    "loserTiebreak": set_data.get("loserTiebreak")
                }
                for set_data in detailed_result
            ]
            
            # Состояние матча
            result[f"{prefix}_match_state"] = "finished" if match_data.get("isFirstParticipantWinner") is not None else "playing"
            
            # Дополнительная информация
            result[f"{prefix}_duration_seconds"] = match_data.get("totalDurationInSeconds", 0)
            result[f"{prefix}_cancellation_type"] = match_data.get("cancellationType")
        
        # Время для следующего матча
        if prefix == "next":
            result[f"{prefix}_start_time"] = match_data.get("startTime", "")
            result[f"{prefix}_scheduled_time"] = match_data.get("startTime", "")  # Дублирование для совместимости
            result[f"{prefix}_match_state"] = "scheduled"
        
        return result

    def _extract_players(self, players_data) -> List[Dict]:
        """Извлекает информацию об игроках с дополнительными полями для vMix"""
        if not isinstance(players_data, list):
            return []
        
        return [
            {
                "id": player.get("id", ""),
                "firstName": (player.get("firstName") or "").strip(),
                "middleName": (player.get("middleName") or "").strip(),
                "lastName": (player.get("lastName") or "").strip(),
                "countryCode": player.get("countryCode", ""),
                "fullName": f"{(player.get('firstName') or '').strip()} {(player.get('lastName') or '').strip()}".strip(),
                # Новые поля для vMix (пункты 3 и 4)
                "lastNameShort": (player.get("lastName") or "").strip()[:3].upper() if (player.get("lastName") or "").strip() else "",
                "initialLastName": f"{(player.get('firstName') or '').strip()[:1]}. {(player.get('lastName') or '').strip()}".strip() if (player.get('firstName') or '').strip() and (player.get('lastName') or '').strip() else ""
            }
            for player in players_data
        ]

    
    # ЗАПРОС №8: Классы и турнирные сетки
    def get_classes_and_draws(self, tournament_id: str) -> Optional[List[Dict]]:
        """
        Получение информации о классах и турнирных сетках
        https://api.rankedin.com/v1/tournament/GetClassesAndDrawNamesAsync/?tournamentId={tournamentId}
        """
        url = f"{self.api_base}/tournament/GetClassesAndDrawNamesAsync/"
        params = f"?tournamentId={tournament_id}"
        
        logger.info(f"Получение классов и сеток для турнира {tournament_id}")
        result = self._make_request(url + params)
        
        if result and len(result) > 0:
            logger.info(f"Найдено {len(result)} классов через GetClassesAndDrawNamesAsync для турнира {tournament_id}")
            return result
        else:
            logger.warning(f"GetClassesAndDrawNamesAsync вернул пустой результат для турнира {tournament_id}")
            return None

    def get_classes_and_draws_fallback(self, tournament_id: str, classes: List[Dict]) -> List[Dict]:
        """
        Fallback функция для создания структуры классов и сеток на основе данных GetTournamentClassesAsync
        """
        logger.info(f"Используем fallback для получения данных классов турнира {tournament_id}")
        
        classes_with_draws = []
        
        for class_info in classes:
            class_id = class_info.get("Id")
            if not class_id:
                continue
                
            # Создаем базовую структуру класса
            class_with_draws = {
                "Id": class_id,
                "Name": class_info.get("Name", f"Класс {class_id}"),
                "TournamentDraws": []
            }
            
            # Пробуем найти доступные сетки для этого класса
            found_draws = []
            
            # Проверяем разные комбинации stage и strength
            for stage in [0, 1]:
                for strength in [0, 1, 2]:
                    try:
                        url = f"{self.api_base}/tournament/GetDrawsForStageAndStrengthAsync"
                        params = f"?tournamentClassId={class_id}&drawStrength={strength}&drawStage={stage}&isReadonly=true&language=ru"
                        
                        result = self._make_request(url + params)
                        if result and isinstance(result, list) and len(result) > 0:
                            # Нашли данные для этой комбинации
                            draw_info = {
                                "Stage": stage,
                                "Strength": strength,
                                "DataCount": len(result)
                            }
                            found_draws.append(draw_info)
                            logger.debug(f"Найдены данные для класса {class_id}: stage={stage}, strength={strength}, элементов={len(result)}")
                            
                    except Exception as e:
                        logger.debug(f"Ошибка проверки stage={stage}, strength={strength} для класса {class_id}: {e}")
                        continue
            
            if found_draws:
                class_with_draws["TournamentDraws"] = found_draws
                classes_with_draws.append(class_with_draws)
                logger.info(f"Класс {class_id}: найдено {len(found_draws)} сеток")
            else:
                logger.warning(f"Для класса {class_id} не найдено сеток")
        
        logger.info(f"Fallback: создано {len(classes_with_draws)} классов с сетками")
        return classes_with_draws

    # ЗАПРОС №9: Групповые этапы (Round Robin) - УМНАЯ ВЕРСИЯ
    def get_round_robin_draws(self, tournament_class_id: str, draw_strength: int = 0, draw_stage: int = 0) -> Optional[List[Dict]]:
        """
        Получение данных для указанного stage и strength
        Умная фильтрация: сначала по BaseType, потом по содержимому
        """
        url = f"{self.api_base}/tournament/GetDrawsForStageAndStrengthAsync"
        params = f"?tournamentClassId={tournament_class_id}&drawStrength={draw_strength}&drawStage={draw_stage}&isReadonly=true&language=ru"
        
        logger.info(f"Получение данных для класса {tournament_class_id}, stage={draw_stage}, strength={draw_strength}")
        result = self._make_request(url + params)
        
        if result:
            logger.info(f"Получено {len(result)} элементов данных для класса {tournament_class_id}")
            
            # Логируем типы данных для отладки
            round_robin_count = 0
            elimination_count = 0
            for item in result:
                if isinstance(item, dict):
                    base_type = item.get("BaseType", "Unknown")
                    has_rr = bool(item.get("RoundRobin"))
                    has_elim = bool(item.get("Elimination"))
                    
                    if has_rr:
                        round_robin_count += 1
                    if has_elim:
                        elimination_count += 1
                        
                    logger.debug(f"  BaseType={base_type}, RoundRobin={has_rr}, Elimination={has_elim}")
            
            logger.info(f"Класс {tournament_class_id}: {round_robin_count} с RoundRobin, {elimination_count} с Elimination")
            
            # Умная фильтрация для stage=0 (ожидаем групповые данные)
            if draw_stage == 0:
                # Сначала пробуем фильтровать по BaseType = "RoundRobin"
                filtered_by_basetype = [item for item in result if isinstance(item, dict) and item.get("BaseType") == "RoundRobin"]
                
                if filtered_by_basetype:
                    logger.info(f"Найдено {len(filtered_by_basetype)} элементов с BaseType=RoundRobin")
                    return filtered_by_basetype
                
                # Если нет элементов с BaseType=RoundRobin, фильтруем по содержимому
                filtered_by_content = [item for item in result if isinstance(item, dict) and item.get("RoundRobin") is not None]
                
                if filtered_by_content:
                    logger.info(f"Найдено {len(filtered_by_content)} элементов с полем RoundRobin")
                    return filtered_by_content
                
                # Если нет ни того, ни другого, возвращаем все
                logger.warning(f"Не найдено RoundRobin данных, возвращаем все {len(result)} элементов")
                return result
        
        return result

    # ЗАПРОС №10: Игры на выбывание (Elimination) - УМНАЯ ВЕРСИЯ
    def get_elimination_draws(self, tournament_class_id: str, draw_strength: int = 0, draw_stage: int = 1) -> Optional[List[Dict]]:
        """
        Получение данных игр на выбывание
        Умная фильтрация: сначала по BaseType, потом по содержимому
        """
        url = f"{self.api_base}/tournament/GetDrawsForStageAndStrengthAsync"
        params = f"?tournamentClassId={tournament_class_id}&drawStrength={draw_strength}&drawStage={draw_stage}&isReadonly=true&language=ru"
        
        logger.info(f"Получение данных на выбывание для класса {tournament_class_id}, stage={draw_stage}, strength={draw_strength}")
        result = self._make_request(url + params)
        
        if result:
            logger.info(f"Получено {len(result)} элементов данных на выбывание для класса {tournament_class_id}")
            
            # Умная фильтрация для stage=1 (ожидаем данные на выбывание)
            if draw_stage == 1:
                # Сначала пробуем фильтровать по BaseType = "Elimination"
                filtered_by_basetype = [item for item in result if isinstance(item, dict) and item.get("BaseType") == "Elimination"]
                
                if filtered_by_basetype:
                    logger.info(f"Найдено {len(filtered_by_basetype)} элементов с BaseType=Elimination")
                    return filtered_by_basetype
                
                # Если нет элементов с BaseType=Elimination, фильтруем по содержимому
                filtered_by_content = [item for item in result if isinstance(item, dict) and item.get("Elimination") is not None]
                
                if filtered_by_content:
                    logger.info(f"Найдено {len(filtered_by_content)} элементов с полем Elimination")
                    return filtered_by_content
                
                # Если нет ни того, ни другого, возвращаем все
                logger.warning(f"Не найдено Elimination данных, возвращаем все {len(result)} элементов")
                return result
        
        return result

    # Универсальная функция для получения всех данных:
    def get_all_draws_for_class(self, tournament_class_id: str) -> Dict[str, List[Dict]]:
        """Получение всех данных турнирных сеток для класса с умной классификацией"""
        all_draws = {
            "round_robin": [],
            "elimination": []
        }
        
        # Список проверенных комбинаций для избежания дублирования
        processed_items = set()
        
        # Пробуем разные комбинации stage и strength
        for stage in [0, 1, 2]:
            for strength in [0, 1, 2, 3]:
                try:
                    url = f"{self.api_base}/tournament/GetDrawsForStageAndStrengthAsync"
                    params = f"?tournamentClassId={tournament_class_id}&drawStrength={strength}&drawStage={stage}&isReadonly=true&language=ru"
                    
                    result = self._make_request(url + params)
                    if result and isinstance(result, list):
                        logger.debug(f"Класс {tournament_class_id}: stage={stage}, strength={strength} - получено {len(result)} элементов")
                        
                        for item in result:
                            if not isinstance(item, dict):
                                continue
                                
                            # Создаем уникальный идентификатор для элемента
                            rating_id = item.get('RatingId', '')
                            consolation = item.get('Elimination', {}).get('Consolation', 0) if item.get('Elimination') else 0
                            base_type = item.get('BaseType', '')
                            
                            # Уникальный ключ учитывает и содержимое
                            has_rr = bool(item.get("RoundRobin"))
                            has_elim = bool(item.get("Elimination"))
                            item_key = f"{rating_id}_{consolation}_{base_type}_{has_rr}_{has_elim}_{stage}_{strength}"
                            
                            if item_key in processed_items:
                                continue
                            
                            # УМНАЯ КЛАССИФИКАЦИЯ:
                            # 1. Если BaseType соответствует содержимому - используем это
                            # 2. Если BaseType не соответствует - классифицируем по содержимому
                            
                            if base_type == "RoundRobin" and has_rr:
                                # Идеальный случай: BaseType и содержимое совпадают
                                all_draws["round_robin"].append(item)
                                processed_items.add(item_key)
                                logger.debug(f"Добавлен RoundRobin (идеальный): stage={stage}, strength={strength}")
                                
                            elif base_type == "Elimination" and has_elim:
                                # Идеальный случай: BaseType и содержимое совпадают
                                all_draws["elimination"].append(item)
                                processed_items.add(item_key)
                                logger.debug(f"Добавлен Elimination (идеальный): consolation={consolation}")
                                
                            elif has_rr and not has_elim:
                                # Содержимое указывает на RoundRobin, независимо от BaseType
                                all_draws["round_robin"].append(item)
                                processed_items.add(item_key)
                                logger.debug(f"Добавлен RoundRobin (по содержимому, BaseType={base_type})")
                                
                            elif has_elim and not has_rr:
                                # Содержимое указывает на Elimination, независимо от BaseType
                                all_draws["elimination"].append(item)
                                processed_items.add(item_key)
                                logger.debug(f"Добавлен Elimination (по содержимому, BaseType={base_type})")
                                
                            else:
                                logger.warning(f"Неопределенный элемент: BaseType={base_type}, RR={has_rr}, Elim={has_elim}")
                                
                except Exception as e:
                    logger.debug(f"Не удалось получить данные для класса {tournament_class_id}, stage={stage}, strength={strength}: {e}")
                    continue
        
        # Сортируем elimination данные по consolation для правильного порядка
        if all_draws["elimination"]:
            all_draws["elimination"].sort(key=lambda x: x.get('Elimination', {}).get('Consolation', 0))
        
        logger.info(f"Для класса {tournament_class_id}: {len(all_draws['round_robin'])} групповых, {len(all_draws['elimination'])} на выбывание")
        return all_draws

    def debug_tournament_structure(self, tournament_id: str, class_id: str = None) -> Dict:
        """Отладочная функция для анализа структуры турнира"""
        debug_info = {
            "tournament_id": tournament_id,
            "api_responses": {},
            "class_analysis": {}
        }
        
        # Проверяем основные API endpoints
        try:
            metadata = self.get_tournament_metadata(tournament_id)
            debug_info["api_responses"]["metadata"] = bool(metadata)
            
            classes = self.get_tournament_classes(tournament_id)
            debug_info["api_responses"]["classes"] = len(classes) if classes else 0
            
            classes_and_draws = self.get_classes_and_draws(tournament_id)
            debug_info["api_responses"]["classes_and_draws"] = len(classes_and_draws) if classes_and_draws else 0
            
            courts = self.get_tournament_courts(tournament_id)
            debug_info["api_responses"]["courts"] = len(courts.get("Courts", [])) if courts else 0
            
            dates = self.get_tournament_dates(tournament_id)
            debug_info["api_responses"]["dates"] = len(dates) if dates else 0
            
        except Exception as e:
            debug_info["api_error"] = str(e)
        
        # Анализируем конкретный класс если указан
        if class_id and classes:
            class_info = next((c for c in classes if str(c.get("Id")) == str(class_id)), None)
            if class_info:
                debug_info["class_analysis"][class_id] = {
                    "class_name": class_info.get("Name", ""),
                    "draws_found": {}
                }
                
                # Проверяем все комбинации для этого класса
                for stage in [0, 1, 2]:
                    for strength in [0, 1, 2, 3]:
                        try:
                            url = f"{self.api_base}/tournament/GetDrawsForStageAndStrengthAsync"
                            params = f"?tournamentClassId={class_id}&drawStrength={strength}&drawStage={stage}&isReadonly=true&language=ru"
                            
                            result = self._make_request(url + params)
                            if result and isinstance(result, list):
                                key = f"stage_{stage}_strength_{strength}"
                                debug_info["class_analysis"][class_id]["draws_found"][key] = {
                                    "count": len(result),
                                    "types": []
                                }
                                
                                for item in result:
                                    if isinstance(item, dict):
                                        base_type = item.get("BaseType", "Unknown")
                                        has_rr = bool(item.get("RoundRobin"))
                                        has_elim = bool(item.get("Elimination"))
                                        
                                        debug_info["class_analysis"][class_id]["draws_found"][key]["types"].append({
                                            "BaseType": base_type,
                                            "has_RoundRobin": has_rr,
                                            "has_Elimination": has_elim
                                        })
                        except:
                            continue
        
        return debug_info



    # Комплексные методы для получения всех данных турнира
    def get_full_tournament_data(self, tournament_id: str) -> Dict[str, Any]:
        """Получение всех данных турнира одним вызовом - исправленная версия"""
        logger.info(f"Начало полной загрузки данных турнира {tournament_id}")
        
        tournament_data = {
            "tournament_id": tournament_id,
            "metadata": None,
            "classes": [],
            "courts": [],
            "dates": [],
            "court_usage": None,
            "draw_data": {},
            "loaded_at": datetime.now().isoformat()
        }
        
        # 1. Метаданные турнира
        metadata = self.get_tournament_metadata(tournament_id)
        if metadata:
            tournament_data["metadata"] = metadata
        
        # 2. Категории турнира
        classes = self.get_tournament_classes(tournament_id)
        if classes:
            tournament_data["classes"] = classes
        
        # 3. Корты турнира
        courts_info = self.get_tournament_courts(tournament_id)
        if courts_info and "Courts" in courts_info:
            tournament_data["courts"] = courts_info["Courts"]
        
        # 4. Даты турнира
        dates = self.get_tournament_dates(tournament_id)
        if dates:
            tournament_data["dates"] = dates
            
            # 5. Планировщик кортов (запрос №5)
            court_planner = self.get_court_planner(tournament_id, dates)
            if court_planner:
                tournament_data["court_planner"] = court_planner
            
            # 6. Использование кортов с расписанием матчей (запрос №6)
            court_usage = self.get_court_usage(tournament_id, dates)
            if court_usage:
                tournament_data["court_usage"] = court_usage
        
        # 8. Классы и сетки - с fallback логикой
        classes_and_draws = self.get_classes_and_draws(tournament_id)
        
        if classes_and_draws and len(classes_and_draws) > 0:
            # Используем данные от GetClassesAndDrawNamesAsync
            logger.info("Используем данные от GetClassesAndDrawNamesAsync")
            for class_info in classes_and_draws:
                class_id = class_info.get("Id")
                if not class_id:
                    continue
                
                tournament_data["draw_data"][str(class_id)] = {
                    "class_info": class_info,
                    "round_robin": [],
                    "elimination": []
                }
                
                # Используем универсальную функцию для получения всех данных
                all_draws = self.get_all_draws_for_class(str(class_id))
                tournament_data["draw_data"][str(class_id)]["round_robin"] = all_draws["round_robin"]
                tournament_data["draw_data"][str(class_id)]["elimination"] = all_draws["elimination"]
                
        elif tournament_data.get("classes"):
            # Fallback: используем данные от GetTournamentClassesAsync
            logger.info("GetClassesAndDrawNamesAsync пуст, используем fallback через GetTournamentClassesAsync")
            classes_with_draws = self.get_classes_and_draws_fallback(tournament_id, tournament_data["classes"])
            
            for class_info in classes_with_draws:
                class_id = class_info.get("Id")
                if not class_id:
                    continue
                
                tournament_data["draw_data"][str(class_id)] = {
                    "class_info": class_info,
                    "round_robin": [],
                    "elimination": []
                }
                
                # Используем универсальную функцию
                all_draws = self.get_all_draws_for_class(str(class_id))
                tournament_data["draw_data"][str(class_id)]["round_robin"] = all_draws["round_robin"]
                tournament_data["draw_data"][str(class_id)]["elimination"] = all_draws["elimination"]
        
        else:
            logger.error(f"Не удалось получить данные классов для турнира {tournament_id}")
        
        # Логируем результаты
        total_rr = 0
        total_elim = 0
        for class_id, class_data in tournament_data["draw_data"].items():
            rr_count = len(class_data.get("round_robin", []))
            elim_count = len(class_data.get("elimination", []))
            total_rr += rr_count
            total_elim += elim_count
            logger.info(f"Класс {class_id}: {rr_count} групповых этапов, {elim_count} этапов на выбывание")
        
        logger.info(f"Завершена полная загрузка турнира {tournament_id}: {total_rr} групповых, {total_elim} на выбывание")
        return tournament_data
   
   
   
   
    
    def get_all_courts_data(self, court_ids: List[str]) -> List[Dict]:
        """Получение данных всех кортов"""
        courts_data = []
        
        for court_id in court_ids:
            court_data = self.get_court_scoreboard(str(court_id))
            if court_data and "error" not in court_data:
                courts_data.append(court_data)
        
        return courts_data

    def get_xml_data_types(self, tournament_data: Dict) -> List[Dict]:
        """Генерирует список доступных типов XML на основе данных турнира"""
        xml_types = []
        
        # Проверяем входные данные
        if not tournament_data or not isinstance(tournament_data, dict):
            logger.error(f"get_xml_data_types: Неверные входные данные: {type(tournament_data)}")
            return xml_types
        
        try:
            # 1. Турнирные таблицы (из классов и сеток)
            draw_data = tournament_data.get("draw_data")
            if draw_data and isinstance(draw_data, dict):
                for class_id, class_data in draw_data.items():
                    if not isinstance(class_data, dict):
                        logger.warning(f"Пропускаем класс {class_id}: неверный формат данных")
                        continue
                    
                    # Получаем информацию о классе из разных источников
                    class_info = class_data.get("class_info", {})
                    
                    # Если нет class_info, пытаемся получить название класса из основных данных турнира
                    if not class_info and tournament_data.get("classes"):
                        classes = tournament_data["classes"]
                        if isinstance(classes, list):
                            matching_class = next((c for c in classes if isinstance(c, dict) and str(c.get("Id")) == str(class_id)), None)
                            if matching_class:
                                class_info = matching_class
                    
                    # Формируем название класса
                    class_name = "Неизвестная категория"
                    if isinstance(class_info, dict):
                        class_name = class_info.get("Name", f"Категория {class_id}")
                    else:
                        class_name = f"Категория {class_id}"
                    
                    # Групповые этапы
                    round_robin_data = class_data.get("round_robin")
                    if round_robin_data and isinstance(round_robin_data, list):
                        for i, rr_data in enumerate(round_robin_data):
                            # Получаем название группы из данных
                            group_name = "Групповой этап"
                            if isinstance(rr_data, dict):
                                if "RoundRobin" in rr_data and isinstance(rr_data["RoundRobin"], dict) and rr_data["RoundRobin"].get("Name"):
                                    group_name = f"Группа {rr_data['RoundRobin']['Name']}"
                                elif rr_data.get("Name"):
                                    group_name = f"Группа {rr_data['Name']}"
                            
                            xml_types.append({
                                "id": f"table_{class_id}_rr_{i}",
                                "name": f"{class_name} - {group_name}",
                                "type": "tournament_table",
                                "class_id": class_id,
                                "class_name": class_name,
                                "draw_type": "round_robin",
                                "draw_index": i,
                                "group_name": group_name
                            })
                    
                    # Игры на выбывание
                    elimination_data = class_data.get("elimination")
                    if elimination_data and isinstance(elimination_data, list):
                        for i, elim_data in enumerate(elimination_data):
                            # Определяем тип плей-офф по данным
                            stage_name = "Плей-офф"
                            
                            if isinstance(elim_data, dict):
                                if "Elimination" in elim_data and isinstance(elim_data["Elimination"], dict):
                                    elimination_info = elim_data["Elimination"]
                                    places_start = elimination_info.get("PlacesStartPos", 1)
                                    places_end = elimination_info.get("PlacesEndPos", 1)
                                    consolation = elimination_info.get("Consolation", 0)
                                    
                                    # Определяем название этапа
                                    if consolation == 0:  # Основная сетка
                                        if places_start == 1 and places_end == 1:
                                            stage_name = "Финал"
                                        elif places_start == 1:
                                            stage_name = f"Места 1-{places_end}"
                                        else:
                                            stage_name = f"Места {places_start}-{places_end}"
                                    else:  # Утешительные матчи
                                        if places_start == places_end:
                                            stage_name = f"Место {places_start}"
                                        else:
                                            stage_name = f"Места {places_start}-{places_end}"
                                elif elim_data.get("PlacesStartPos"):
                                    # Прямой доступ к данным elimination
                                    places_start = elim_data.get("PlacesStartPos", 1)
                                    places_end = elim_data.get("PlacesEndPos", 1)
                                    if places_start == places_end:
                                        stage_name = f"Место {places_start}"
                                    else:
                                        stage_name = f"Места {places_start}-{places_end}"
                            
                            xml_types.append({
                                "id": f"table_{class_id}_elim_{i}",
                                "name": f"{class_name} - {stage_name}",
                                "type": "tournament_table", 
                                "class_id": class_id,
                                "class_name": class_name,
                                "draw_type": "elimination",
                                "draw_index": i,
                                "stage_name": stage_name
                            })
            
            # 2. Расписание
            if tournament_data.get("court_usage") or tournament_data.get("dates"):
                xml_types.append({
                    "id": "schedule",
                    "name": "Расписание матчей",
                    "type": "schedule"
                })
            
            # 3. Счет на кортах
            courts = tournament_data.get("courts")
            if courts and isinstance(courts, list):
                for court in courts:
                    if isinstance(court, dict):
                        court_id = court.get("Item1")
                        court_name = court.get("Item2", f"Корт {court_id}")
                        
                        if court_id:  # Только если есть ID корта
                            xml_types.append({
                                "id": f"court_{court_id}",
                                "name": f"{court_name} - Счет",
                                "type": "court_score",
                                "court_id": court_id,
                                "court_name": court_name
                            })
            
            logger.info(f"Сгенерировано {len(xml_types)} типов XML")
            return xml_types
            
        except Exception as e:
            logger.error(f"Ошибка в get_xml_data_types: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return xml_types  # Возвращаем пустой список вместо None
    
    
    
    
    

# Функции-обертки для обратной совместимости
def fetch_tournament_data(tournament_class_id: str) -> Optional[Dict]:
    """Обертка для старого кода - получение данных турнира"""
    api = RankedinAPI()
    return api.get_round_robin_draws(tournament_class_id)

def get_court_ids(tournament_id: str) -> List[str]:
    """Обертка для старого кода - получение ID кортов"""
    api = RankedinAPI()
    courts_info = api.get_tournament_courts(tournament_id)
    
    if courts_info and "Courts" in courts_info:
        return [str(court.get("Item1")) for court in courts_info["Courts"] if court.get("Item1")]
    
    return []

def get_court_scores(court_id: str) -> Dict:
    """Обертка для старого кода - получение данных корта"""
    api = RankedinAPI()
    return api.get_court_scoreboard(court_id) or {"court_id": court_id, "error": "Ошибка получения данных"}