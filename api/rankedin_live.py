#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket клиент для live-счёта RankedIn (SignalR)
Получает обновления счёта в реальном времени
"""

import json
import time
import threading
import logging
from typing import Dict, Optional, Callable, List
from datetime import datetime

import requests
import websocket

logger = logging.getLogger(__name__)

# Константы SignalR
BASE_URL = "https://live.rankedin.com"
HUB_PATH = "/scores"
PROTOCOL_SEPARATOR = "\x1e"

# Таймаут неактивности (секунды)
INACTIVITY_TIMEOUT = 60


class RankedinLiveClient:
    """WebSocket клиент для одного корта"""
    
    def __init__(self, court_id: int, on_update: Callable[[Dict], None] = None):
        self.court_id = court_id
        self.on_update = on_update
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
        self._stop_event = threading.Event()
        
    def _negotiate(self) -> Optional[Dict]:
        """Получение токена для WebSocket подключения"""
        url = f"{BASE_URL}{HUB_PATH}/negotiate?negotiateVersion=1"
        headers = {
            "User-Agent": "MixRanker/2.6",
            "Accept": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
        }
        
        try:
            resp = requests.post(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Court {self.court_id}: negotiate failed: {e}")
            return None
    
    def _on_message(self, ws, message: str):
        """Обработка входящих сообщений SignalR"""
        frames = message.split(PROTOCOL_SEPARATOR)
        
        for frame in frames:
            if not frame.strip():
                continue
            
            try:
                data = json.loads(frame)
            except json.JSONDecodeError:
                continue
            
            msg_type = data.get("type")
            
            # type=1 — invocation (событие от сервера)
            if msg_type == 1:
                target = data.get("target")
                args = data.get("arguments", [])
                
                # Логируем все входящие сообщения с сырыми данными
                if target in ("ReceiveMatchUpdate", "ReceiveMatchAction"):
                    # Извлекаем courtId из данных
                    if args and len(args) > 0:
                        first_arg = args[0]
                        if isinstance(first_arg, list) and len(first_arg) > 0:
                            incoming_court_id = first_arg[0].get("courtId") if isinstance(first_arg[0], dict) else "unknown"
                        elif isinstance(first_arg, dict):
                            incoming_court_id = first_arg.get("courtId", "unknown")
                        else:
                            incoming_court_id = "unknown"
                    else:
                        incoming_court_id = "no_args"
                    
                    logger.info(f"Court {self.court_id}: received {target}, incoming_courtId={incoming_court_id}, my_courtId={self.court_id}, match={incoming_court_id == self.court_id}")
                
                if target == "ReceiveMatchUpdate" and args:
                    # args[0] — это список обновлений
                    updates = args[0] if isinstance(args[0], list) else [args[0]]
                    self._handle_match_update(updates)

                elif target == "ReceiveMatchAction" and args:
                    # args[0] — это список действий
                    actions = args[0] if isinstance(args[0], list) else [args[0]]
                    self._handle_match_action(actions)
            
            # type=6 — ping (keepalive)
            elif msg_type == 6:
                try:
                    ws.send(json.dumps({"type": 6}) + PROTOCOL_SEPARATOR)
                except:
                    pass
    
    def _handle_match_update(self, updates: List[Dict]):
        """Обработка обновления счёта (ReceiveMatchUpdate)"""
        for update in updates:
            if not isinstance(update, dict):
                logger.warning(f"Court {self.court_id}: update is not dict: {type(update)}")
                continue
                
            update_court_id = update.get("courtId")
            logger.debug(f"Court {self.court_id}: received update for court {update_court_id}")
            
            if update_court_id != self.court_id:
                logger.debug(f"Court {self.court_id}: skipping update for different court {update_court_id}")
                continue
            
            logger.info(f"Court {self.court_id}: match update - score={update.get('score', {}).get('firstParticipantScore')}-{update.get('score', {}).get('secondParticipantScore')}, tiebreak={update.get('isTieBreak')}")
            
            court_data = self._transform_update(update)
            
            logger.info(f"Court {self.court_id}: transformed data court_id={court_data.get('court_id')}")
            
            if self.on_update:
                self.on_update(court_data)
    
    def _handle_match_action(self, actions: List[Dict]):
        """Обработка действий в матче (ReceiveMatchAction) - содержит полные данные"""
        for action in actions:
            if not isinstance(action, dict):
                continue
                
            action_court_id = action.get("courtId")
            if action_court_id != self.court_id:
                continue
            
            action_type = action.get("action", "")
            logger.info(f"Court {self.court_id}: match action: {action_type}")
            
            # courtModel содержит полные данные о матче
            court_model = action.get("courtModel")
            if court_model:
                court_data = self._transform_action(action, court_model)
                if self.on_update:
                    self.on_update(court_data)
    
    def _transform_update(self, update: Dict) -> Dict:
        """Преобразование данных ReceiveMatchUpdate в формат БД"""
        try:
            score = update.get("score", {})
            serve = update.get("serve", {})
            
            court_id = update.get("courtId")
            logger.debug(f"_transform_update: courtId from update = {court_id}")
            
            is_tiebreak = update.get("isTieBreak", False)
            is_super_tiebreak = update.get("isSuperTieBreak", False)
            
            detailed_result = self._parse_detailed_result(
                score.get("detailedResult", []),
                is_tiebreak=is_tiebreak,
                is_super_tiebreak=is_super_tiebreak
            )
            
            return {
                "court_id": str(court_id),
                "match_id": str(update.get("matchId", "")),
                "first_participant_score": score.get("firstParticipantScore", 0),
                "second_participant_score": score.get("secondParticipantScore", 0),
                "detailed_result": detailed_result,
                "is_tiebreak": is_tiebreak,
                "is_super_tiebreak": is_super_tiebreak,
                "is_first_participant_serving": serve.get("isFirstParticipantServing"),
                "is_serving_left": serve.get("isServingLeft"),
                "current_match_state": "live",
                "event_state": "active",
                "live_update": True,
                "updated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"_transform_update error: {e}, update={update}")
            raise
    
    def _transform_action(self, action: Dict, court_model: Dict) -> Dict:
        """Преобразование данных ReceiveMatchAction в формат БД"""
        details = court_model.get("details", {})
        live_match = court_model.get("liveMatch", {})
        base = live_match.get("base", {})
        state = live_match.get("state", {})
        
        score = state.get("score", {})
        serve = state.get("serve", {})
        
        is_tiebreak = state.get("isTieBreak", False)
        is_super_tiebreak = state.get("isSuperTieBreak", False)
        
        detailed_result = self._parse_detailed_result(
            score.get("detailedResult", []),
            is_tiebreak=is_tiebreak,
            is_super_tiebreak=is_super_tiebreak
        )
        
        # Извлекаем участников
        first_participant = self._extract_players(base.get("firstParticipant", []))
        second_participant = self._extract_players(base.get("secondParticipant", []))
        
        return {
            "court_id": str(action.get("courtId")),
            "court_name": details.get("courtName", ""),
            "event_state": details.get("eventState", "active"),
            "match_id": str(state.get("matchId") or action.get("matchId", "")),
            "class_name": base.get("className", ""),
            "first_participant": first_participant,
            "second_participant": second_participant,
            "first_participant_score": score.get("firstParticipantScore", 0),
            "second_participant_score": score.get("secondParticipantScore", 0),
            "detailed_result": detailed_result,
            "is_tiebreak": is_tiebreak,
            "is_super_tiebreak": state.get("isSuperTieBreak", False),
            "is_first_participant_serving": serve.get("isFirstParticipantServing"),
            "is_serving_left": serve.get("isServingLeft"),
            "current_match_state": "live",
            "live_update": True,
            "updated_at": datetime.now().isoformat()
        }
    
    def _extract_players(self, players: List) -> List[Dict]:
        """Извлечение данных игроков"""
        if not isinstance(players, list):
            return []
        
        result = []
        for p in players:
            if not isinstance(p, dict):
                continue
            result.append({
                "id": p.get("id", ""),
                "firstName": (p.get("firstName") or "").strip(),
                "lastName": (p.get("lastName") or "").strip(),
                "countryCode": p.get("countryCode", ""),
                "fullName": f"{(p.get('firstName') or '').strip()} {(p.get('lastName') or '').strip()}".strip(),
                "initialLastName": f"{(p.get('firstName') or '').strip()[:1]}. {(p.get('lastName') or '').strip()}".strip() if p.get('firstName') and p.get('lastName') else ""
            })
        return result
    
    def _parse_detailed_result(self, detailed: List[Dict], is_tiebreak: bool = False, 
                                is_super_tiebreak: bool = False) -> List[Dict]:
        """Парсинг detailed_result из SignalR формата"""
        result = []
        num_sets = len(detailed)
        
        for i, set_data in enumerate(detailed):
            if not isinstance(set_data, dict):
                continue
            
            is_last_set = (i == num_sets - 1)
            
            set_info = {
                "firstParticipantScore": set_data.get("firstParticipantScore", 0),
                "secondParticipantScore": set_data.get("secondParticipantScore", 0),
                "loserTiebreak": set_data.get("loserTiebreak")
            }
            
            games = set_data.get("detailedResult", [])
            if games and isinstance(games, list):
                last_game = games[-1] if isinstance(games[-1], dict) else {}
                g1 = last_game.get("firstParticipantScore", 0)
                g2 = last_game.get("secondParticipantScore", 0)
                
                set_score1 = set_data.get("firstParticipantScore", 0)
                set_score2 = set_data.get("secondParticipantScore", 0)
                
                # Проверяем тай-брейк:
                # 1. Обычный тай-брейк (6:6 в сете)
                # 2. Супер тай-брейк (3-й сет с счётом 0:0 и флаг is_tiebreak/is_super_tiebreak)
                # 3. loserTiebreak указан
                is_set_tiebreak = (
                    (set_score1 == 6 and set_score2 == 6) or  # Обычный тай-брейк 6:6
                    (set_score1 == 0 and set_score2 == 0 and is_last_set and (is_tiebreak or is_super_tiebreak)) or  # Супер тай-брейк
                    last_game.get("loserTiebreak") is not None
                )
                
                if is_set_tiebreak:
                    # В тай-брейке показываем очки как есть
                    set_info["gameScore"] = {"first": str(g1), "second": str(g2)}
                    set_info["isTieBreak"] = True
                    if is_last_set and is_super_tiebreak:
                        set_info["isSuperTieBreak"] = True
                else:
                    # Обычный гейм - конвертируем в теннисный формат (0, 15, 30, 40, AD)
                    def conv(v, other):
                        if v <= 3:
                            return {0: "0", 1: "15", 2: "30", 3: "40"}.get(v, str(v))
                        else:
                            # При преимуществе - лидер AD, отстающий 40
                            if v > other:
                                return "AD"
                            else:
                                return "40"
                    set_info["gameScore"] = {"first": conv(g1, g2), "second": conv(g2, g1)}
            
            result.append(set_info)
        
        return result
    
    def _on_open(self, ws):
        """Обработка открытия соединения"""
        logger.info(f"Court {self.court_id}: WebSocket connected")
        
        # Handshake
        handshake = {"protocol": "json", "version": 1}
        ws.send(json.dumps(handshake) + PROTOCOL_SEPARATOR)
        
        # JoinCourtRoom
        join_msg = {
            "type": 1,
            "target": "JoinCourtRoom",
            "arguments": [{
                "courtId": self.court_id,
                "UserId": "0",
                "StreamId": 0
            }],
            "invocationId": "0"
        }
        ws.send(json.dumps(join_msg) + PROTOCOL_SEPARATOR)
        logger.info(f"Court {self.court_id}: joined room")
        
        self.reconnect_delay = 5
    
    def _on_error(self, ws, error):
        """Обработка ошибки"""
        logger.error(f"Court {self.court_id}: WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Обработка закрытия соединения"""
        logger.warning(f"Court {self.court_id}: WebSocket closed: {close_status_code} {close_msg}")
        
        if self.is_running and not self._stop_event.is_set():
            logger.info(f"Court {self.court_id}: reconnecting in {self.reconnect_delay}s...")
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            self._connect()
    
    def _connect(self):
        """Установка WebSocket соединения"""
        if self._stop_event.is_set():
            return
        
        nego = self._negotiate()
        if not nego:
            if self.is_running:
                time.sleep(self.reconnect_delay)
                self._connect()
            return
        
        ws_url = nego["url"].replace("https://", "wss://")
        access_token = nego["accessToken"]
        ws_full_url = f"{ws_url}&access_token={access_token}"
        
        self.ws = websocket.WebSocketApp(
            ws_full_url,
            header={"Origin": BASE_URL},
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self.ws.run_forever(ping_interval=None)
    
    def start(self):
        """Запуск клиента в отдельном потоке"""
        if self.is_running:
            return
        
        self.is_running = True
        self._stop_event.clear()
        self.ws_thread = threading.Thread(target=self._connect, daemon=True)
        self.ws_thread.start()
        logger.info(f"Court {self.court_id}: live client started")
    
    def stop(self):
        """Остановка клиента"""
        self.is_running = False
        self._stop_event.set()
        
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        logger.info(f"Court {self.court_id}: live client stopped")


class RankedinLiveManager:
    """Менеджер live-подключений для нескольких кортов с авто-отпиской"""
    
    def __init__(self):
        self.clients: Dict[int, RankedinLiveClient] = {}
        self.last_access: Dict[int, float] = {}  # court_id -> timestamp
        self._lock = threading.Lock()
        self._update_callback: Optional[Callable[[str, Dict], None]] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """Запуск менеджера с фоновой очисткой"""
        if self._running:
            return
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("LiveManager: started with auto-cleanup")
    
    def stop(self):
        """Остановка менеджера"""
        self._running = False
        self.unsubscribe_all()
        logger.info("LiveManager: stopped")
    
    def _cleanup_loop(self):
        """Фоновый цикл очистки неактивных подписок"""
        while self._running:
            time.sleep(10)  # Проверяем каждые 10 сек
            self._cleanup_inactive()
    
    def _cleanup_inactive(self):
        """Отписка от неактивных кортов"""
        now = time.time()
        to_remove = []
        
        with self._lock:
            for court_id, last_time in self.last_access.items():
                if now - last_time > INACTIVITY_TIMEOUT:
                    to_remove.append(court_id)
        
        for court_id in to_remove:
            logger.info(f"Court {court_id}: unsubscribing due to inactivity ({INACTIVITY_TIMEOUT}s)")
            self.unsubscribe_court(court_id)
    
    def set_update_callback(self, callback: Callable[[str, Dict], None]):
        """Установка callback для обновлений (tournament_id, court_data)"""
        self._update_callback = callback
    
    def _on_court_update(self, court_id: int, court_data: Dict):
        """Обработка обновления от корта"""
        # Используем court_id из данных, а не из параметра
        actual_court_id = court_data.get("court_id", court_id)
        logger.info(f"_on_court_update: param_court_id={court_id}, data_court_id={actual_court_id}")
        
        if self._update_callback:
            tournament_id = self._get_tournament_for_court(actual_court_id)
            if tournament_id:
                self._update_callback(tournament_id, court_data)
    
    def _get_tournament_for_court(self, court_id: int) -> Optional[str]:
        """Получение tournament_id для корта из БД"""
        try:
            from .database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tournament_id FROM courts_data WHERE court_id = ? LIMIT 1",
                (str(court_id),)
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting tournament for court {court_id}: {e}")
            return None
    
    def touch(self, court_id: int):
        """Обновление времени последнего доступа к корту"""
        with self._lock:
            self.last_access[court_id] = time.time()
    
    def subscribe_court(self, court_id: int) -> bool:
        """Подписка на live-обновления корта"""
        with self._lock:
            # Обновляем время доступа
            self.last_access[court_id] = time.time()
            
            if court_id in self.clients:
                logger.debug(f"Court {court_id}: already subscribed, refreshing")
                return True
            
            client = RankedinLiveClient(
                court_id,
                on_update=lambda data: self._on_court_update(court_id, data)
            )
            client.start()
            self.clients[court_id] = client
            
            logger.info(f"Court {court_id}: subscribed to live updates")
            return True
    
    def unsubscribe_court(self, court_id: int):
        """Отписка от live-обновлений корта"""
        with self._lock:
            if court_id in self.clients:
                self.clients[court_id].stop()
                del self.clients[court_id]
            if court_id in self.last_access:
                del self.last_access[court_id]
            logger.info(f"Court {court_id}: unsubscribed from live updates")
    
    def subscribe_courts(self, court_ids: List[int]):
        """Подписка на несколько кортов"""
        for court_id in court_ids:
            self.subscribe_court(court_id)
    
    def unsubscribe_all(self):
        """Отписка от всех кортов"""
        with self._lock:
            for client in self.clients.values():
                client.stop()
            self.clients.clear()
            self.last_access.clear()
            logger.info("All live subscriptions stopped")
    
    def get_subscribed_courts(self) -> List[int]:
        """Получение списка подписанных кортов"""
        with self._lock:
            return list(self.clients.keys())
    
    def is_subscribed(self, court_id: int) -> bool:
        """Проверка подписки на корт"""
        with self._lock:
            return court_id in self.clients


# Глобальный экземпляр менеджера
live_manager = RankedinLiveManager()