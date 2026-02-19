"""
API Server Package

Main FastAPI application is located in api_server.app
Import it via: from api_server.app import app
"""

from .app import app as fastapi_app

__all__ = ["fastapi_app"]
