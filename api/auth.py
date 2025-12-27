#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Модуль аутентификации"""

import logging
from functools import wraps
from datetime import timedelta
from flask import session, jsonify, request

from .database import get_db_connection

logger = logging.getLogger(__name__)


def require_auth(f):
    """Декоратор проверки аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'error': 'Требуется аутентификация', 'auth_required': True}), 401
        return f(*args, **kwargs)
    return decorated_function


def check_user_credentials(username: str, password: str) -> bool:
    """Проверка учетных данных пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?', (username,))
            conn.commit()
            conn.close()
            return True

        conn.close()
        return False
    except Exception as e:
        logger.error(f"Ошибка проверки пользователя: {e}")
        return False


def register_auth_routes(app):
    """Регистрация роутов аутентификации"""

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Авторизация пользователя"""
        try:
            if request.content_type and 'application/json' in request.content_type:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Пустой JSON'}), 400
            elif request.form:
                data = {
                    'username': request.form.get('username', ''),
                    'password': request.form.get('password', '')
                }
            else:
                try:
                    data = request.get_json(force=True)
                except:
                    return jsonify({'error': 'Неверный формат данных'}), 400

            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            if not username or not password:
                return jsonify({'error': 'Введите имя пользователя и пароль'}), 400

            if check_user_credentials(username, password):
                session['authenticated'] = True
                session['username'] = username
                session.permanent = True
                app.permanent_session_lifetime = timedelta(hours=24)

                logger.info(f"Успешная авторизация: {username}")
                return jsonify({
                    'success': True,
                    'message': 'Успешная авторизация',
                    'username': username
                })
            else:
                logger.warning(f"Неудачная попытка авторизации: {username}")
                return jsonify({'error': 'Неверные учетные данные'}), 401

        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            return jsonify({'error': 'Ошибка сервера'}), 500

    @app.route('/api/auth/logout', methods=['POST'])
    def logout():
        """Выход из системы"""
        session.clear()
        return jsonify({'success': True, 'message': 'Выход выполнен'})

    @app.route('/api/auth/status')
    def auth_status():
        """Проверка статуса аутентификации"""
        if 'authenticated' in session and session['authenticated']:
            return jsonify({
                'authenticated': True,
                'username': session.get('username', '')
            })
        return jsonify({'authenticated': False})
