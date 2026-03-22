#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .tournaments import create_tournaments_blueprint
from .files import create_files_blueprint
from .live import create_live_blueprint
from .settings import create_settings_blueprint

__all__ = [
    "create_tournaments_blueprint",
    "create_files_blueprint",
    "create_live_blueprint",
    "create_settings_blueprint",
]
