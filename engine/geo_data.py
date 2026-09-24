"""
engine/geo_data.py
Предустановленные географические координаты городов.
Не зависит от Telegram, UI или других модулей проекта.
"""

from typing import TypedDict


class CityInfo(TypedDict):
    lat: float
    lon: float
    iso6709: str
    name: str


class CountryInfo(TypedDict):
    flag: str
    name: str
    cities: dict[str, CityInfo]


# Полный список предустановленных координат
GEO_DATA: dict[str, CountryInfo] = {
    "norway": {
        "flag": "🇳🇴",
        "name": "Норвегия",
        "cities": {
            "trondheim": {
                "name": "Тронхейм",
                "lat": 63.4305,
                "lon": 10.3951,
                "iso6709": "+63.4305+010.3951/",
            },
            "oslo": {
                "name": "Осло",
                "lat": 59.9139,
                "lon": 10.7522,
                "iso6709": "+59.9139+010.7522/",
            },
            "bergen": {
                "name": "Берген",
                "lat": 60.3913,
                "lon": 5.3221,
                "iso6709": "+60.3913+005.3221/",
            },
        },
    },
    "usa": {
        "flag": "🇺🇸",
        "name": "США",
        "cities": {
            "new_york": {
                "name": "Нью-Йорк",
                "lat": 40.7128,
                "lon": -74.0060,
                "iso6709": "+40.7128-074.0060/",
            },
            "miami": {
                "name": "Майами",
                "lat": 25.7617,
                "lon": -80.1918,
                "iso6709": "+25.7617-080.1918/",
            },
            "los_angeles": {
                "name": "Лос-Анджелес",
                "lat": 34.0522,
                "lon": -118.2437,
                "iso6709": "+34.0522-118.2437/",
            },
        },
    },
    "canada": {
        "flag": "🇨🇦",
        "name": "Канада",
        "cities": {
            "toronto": {
                "name": "Торонто",
                "lat": 43.6532,
                "lon": -79.3832,
                "iso6709": "+43.6532-079.3832/",
            },
            "vancouver": {
                "name": "Ванкувер",
                "lat": 49.2827,
                "lon": -123.1207,
                "iso6709": "+49.2827-123.1207/",
            },
            "montreal": {
                "name": "Монреаль",
                "lat": 45.5017,
                "lon": -73.5673,
                "iso6709": "+45.5017-073.5673/",
            },
        },
    },
}

# Город и страна по умолчанию
DEFAULT_COUNTRY = "norway"
DEFAULT_CITY = "trondheim"


def get_default_city() -> CityInfo:
    """Возвращает настройки города по умолчанию (Тронхейм, Норвегия)."""
    return GEO_DATA[DEFAULT_COUNTRY]["cities"][DEFAULT_CITY]


def get_city(country_key: str, city_key: str) -> CityInfo | None:
    """Возвращает информацию о городе или None, если не найден."""
    country = GEO_DATA.get(country_key)
    if country is None:
        return None
    return country["cities"].get(city_key)


def get_country_list() -> list[tuple[str, str, str]]:
    """Возвращает список кортежей (country_key, flag, name) для меню."""
    return [
        (key, data["flag"], data["name"])
        for key, data in GEO_DATA.items()
    ]


def get_city_list(country_key: str) -> list[tuple[str, str]]:
    """Возвращает список кортежей (city_key, city_name) для страны."""
    country = GEO_DATA.get(country_key)
    if country is None:
        return []
    return [
        (key, city["name"])
        for key, city in country["cities"].items()
    ]
