from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class AppSettings(BaseModel):
    openai_api_key: Optional[str] = None
    github_token: Optional[str] = None
    search_delay_min: float = 2.0
    search_delay_max: float = 5.0
    enabled_engines: list = ["bing", "duckduckgo"]
    enabled_modules: list = ["dorks", "github", "cloud"]


_settings_store = {}


@router.get("/")
async def get_settings():
    return {
        "openai_configured": bool(_settings_store.get("openai_api_key")),
        "github_configured": bool(_settings_store.get("github_token")),
        "enabled_engines": _settings_store.get("enabled_engines", ["bing", "duckduckgo"]),
        "enabled_modules": _settings_store.get("enabled_modules", ["dorks", "github", "cloud"]),
        "search_delay_min": _settings_store.get("search_delay_min", 2.0),
        "search_delay_max": _settings_store.get("search_delay_max", 5.0),
    }


@router.post("/")
async def update_settings(settings: AppSettings):
    if settings.openai_api_key:
        _settings_store["openai_api_key"] = settings.openai_api_key
    if settings.github_token:
        _settings_store["github_token"] = settings.github_token
    _settings_store["enabled_engines"] = settings.enabled_engines
    _settings_store["enabled_modules"] = settings.enabled_modules
    _settings_store["search_delay_min"] = settings.search_delay_min
    _settings_store["search_delay_max"] = settings.search_delay_max
    return {"message": "Settings updated"}
