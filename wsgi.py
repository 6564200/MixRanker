#!/usr/bin/env python3
"""
WSGI entry point for gunicorn/uwsgi
"""
from app import create_app

# Создаём приложение - это запустит все сервисы (AutoRefresh, LiveManager)
application = create_app()

# Для совместимости с разными WSGI серверами
app = application

if __name__ == "__main__":
    application.run()