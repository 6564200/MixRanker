#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Модуль аутентификации"""

import logging
from functools import wraps
from datetime import timedelta
from flask import session, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

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


def _is_password_hash(password_value: str) -> bool:
    """Quick check for Werkzeug password hash formats."""
    if not isinstance(password_value, str):
        return False
    return password_value.startswith(('pbkdf2:', 'scrypt:', 'argon2:'))


def _verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify password with hash support and plaintext fallback."""
    if not stored_password:
        return False
    if _is_password_hash(stored_password):
        try:
            return check_password_hash(stored_password, provided_password)
        except ValueError:
            return False
    return stored_password == provided_password


def check_user_credentials(username: str, password: str) -> bool:
    """Проверка учетных данных пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user and _verify_password(user['password'], password):
            
            if not _is_password_hash(user['password']):
                cursor.execute(
                    'UPDATE users SET password = ?, last_login = CURRENT_TIMESTAMP WHERE username = ?',
                    (generate_password_hash(password), username)
                )
            else:
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
                except Exception:
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

    @app.route('/api/auth/change-password', methods=['POST'])
    @require_auth
    def change_password():
        """Change password for current authenticated user."""
        try:
            data = request.get_json(silent=True) or {}
            current_password = data.get('current_password', '')
            new_password = data.get('new_password', '')
            confirm_password = data.get('confirm_password', '')

            if not current_password or not new_password or not confirm_password:
                return jsonify({'error': 'All password fields are required'}), 400

            if new_password != confirm_password:
                return jsonify({'error': 'New password confirmation does not match'}), 400

            if len(new_password) < 6:
                return jsonify({'error': 'New password must be at least 6 characters'}), 400

            username = session.get('username')
            if not username:
                return jsonify({'error': 'Authentication required', 'auth_required': True}), 401

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()

            if not user or not _verify_password(user['password'], current_password):
                conn.close()
                return jsonify({'error': 'Current password is incorrect'}), 400

            cursor.execute(
                'UPDATE users SET password = ? WHERE username = ?',
                (generate_password_hash(new_password), username)
            )
            conn.commit()
            conn.close()

            logger.info(f"Password changed for user: {username}")
            return jsonify({'success': True, 'message': 'Password changed successfully'})

        except Exception as e:
            logger.error(f"Password change error: {e}")
            return jsonify({'error': 'Server error'}), 500
