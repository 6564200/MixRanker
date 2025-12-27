#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Модуль для работы с API rankedin.com"""

import requests
import logging
import json
import time
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
            'User-Agent': 'vMixRanker/2.6',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def _make_request(self, url: str, method: str = 'GET', data: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """Выполняет HTTP запрос с retry"""
        for attempt in range(max_retries):
            try:
                resp = self.session.post(url, json=data, timeout=self.timeout) if method.upper() == 'POST' else self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                else:
                    logger.error(f"Ошибка запроса к {url}: {e}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка запроса к {url}: {e}")
                return None
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка JSON от {url}: {e}")
                return None
        return None

    def _get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """GET-запрос к API"""
        try:
            resp = self.session.get(f"{self.api_base}{endpoint}", params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"GET {endpoint}: {e}")
            return None

    # === ОСНОВНЫЕ ЗАПРОСЫ ===
    def get_tournament_metadata(self, tournament_id: str) -> Optional[Dict]:
        return self._get("/metadata/GetFeatureMetadataAsync", {"feature": "Tournament", "id": tournament_id})

    def get_tournament_classes(self, tournament_id: str) -> Optional[List[Dict]]:
        return self._get("/Tournament/GetTournamentClassesAsync", {"tournamentId": tournament_id})

    def get_tournament_courts(self, tournament_id: str) -> Optional[Dict]:
        return self._get("/Tournament/GetTournamentTimetableInfoAsync/", {"tournamentId": tournament_id})

    def get_tournament_dates(self, tournament_id: str) -> Optional[List[str]]:
        return self._get("/Tournament/GetTimetableDatesAsync", {"tournamentId": tournament_id})

    def get_court_planner(self, tournament_id: str, dates: List[str]) -> Optional[Dict]:
        return self._make_request(f"{self.api_base}/Tournament/GetCourtPlannerAsync", 'POST', {"tournamentId": tournament_id, "dates": dates})

    def get_court_usage(self, tournament_id: str, dates: List[str]) -> Optional[Dict]:
        return self._make_request(f"{self.api_base}/Tournament/GetCourtUsageAsync", 'POST', {"tournamentId": tournament_id, "dates": dates})

    def get_classes_and_draws(self, tournament_id: str) -> Optional[List[Dict]]:
        return self._get("/tournament/GetClassesAndDrawNamesAsync/", {"tournamentId": tournament_id})

    def get_tournament_participants(self, tournament_id: str) -> Optional[List[Dict]]:
        return self._get("/Tournament/GetAllSeedsAsync", {"tournamentId": tournament_id})

    def get_court_scoreboard(self, court_id: str) -> Dict:
        result = self._make_request(f"{self.live_api_base}/court/{court_id}/scoreboard")
        if result and not result.get('error'):
            return self._process_court_data(result, court_id)
        return {"court_id": court_id, "error": "Ошибка получения данных"}

    def get_all_courts_data(self, court_ids: List[str]) -> List[Dict]:
        return [d for cid in court_ids if (d := self.get_court_scoreboard(str(cid))) and "error" not in d]

    def get_tournament_matches(self, tournament_id: str) -> Optional[Dict]:
        """Получение всех матчей турнира с результатами"""
        return self._get("/tournament/GetMatchesSectionAsync", {"Id": tournament_id})
