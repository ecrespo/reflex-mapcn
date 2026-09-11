"""Static sample data shared by the demo pages."""

from __future__ import annotations

import dataclasses

# --- Caracas points of interest ----------------------------------------------

CARACAS = [-66.9036, 10.4806]


@dataclasses.dataclass
class Place:
    """A point of interest rendered as a marker."""

    id: int
    name: str
    category: str
    lng: float
    lat: float


PLACES: list[Place] = [
    Place(id=1, name="Plaza Bolívar", category="Landmark", lng=-66.9146, lat=10.5061),
    Place(id=2, name="Parque del Este", category="Park", lng=-66.8464, lat=10.4926),
    Place(
        id=3,
        name="Teleférico Warairarepano",
        category="Attraction",
        lng=-66.8858,
        lat=10.5215,
    ),
    Place(
        id=4,
        name="Universidad Central de Venezuela",
        category="University",
        lng=-66.8907,
        lat=10.4915,
    ),
    Place(
        id=5,
        name="Museo de Arte Contemporáneo",
        category="Museum",
        lng=-66.8855,
        lat=10.4965,
    ),
]

# --- New York walking route (from the mapcn docs) ----------------------------

NYC_ROUTE: list[list[float]] = [
    [-74.006, 40.7128],  # City Hall
    [-73.9857, 40.7484],  # Empire State Building
    [-73.9772, 40.7527],  # Grand Central
    [-73.9654, 40.7829],  # Central Park
]

NYC_STOPS = [
    {"name": "City Hall", "lng": -74.006, "lat": 40.7128},
    {"name": "Empire State Building", "lng": -73.9857, "lat": 40.7484},
    {"name": "Grand Central Terminal", "lng": -73.9772, "lat": 40.7527},
    {"name": "Central Park", "lng": -73.9654, "lat": 40.7829},
]

# --- San Francisco delivery route (progress demo, from the mapcn docs) -------

SF_ROUTE: list[list[float]] = [
    [-122.394, 37.7953],
    [-122.3952, 37.7967],
    [-122.397, 37.7986],
    [-122.3975, 37.7992],
    [-122.3976, 37.7993],
    [-122.3981, 37.799],
    [-122.3984, 37.7989],
    [-122.4066, 37.7979],
    [-122.4071, 37.7981],
    [-122.4072, 37.7982],
    [-122.4072, 37.7984],
    [-122.4082, 37.8034],
    [-122.4064, 37.8037],
    [-122.4063, 37.8036],
    [-122.4063, 37.8034],
    [-122.4067, 37.8032],
    [-122.4067, 37.803],
    [-122.4067, 37.8028],
    [-122.4064, 37.8025],
    [-122.4062, 37.802],
    [-122.406, 37.8019],
    [-122.4058, 37.8018],
    [-122.4056, 37.8018],
    [-122.4055, 37.8019],
    [-122.4054, 37.8021],
    [-122.4056, 37.8025],
]

# --- Arcs -------------------------------------------------------------------

HUB = {"name": "Caracas", "lng": -66.9036, "lat": 10.4806}

DESTINATIONS = [
    {"name": "Madrid", "lng": -3.7038, "lat": 40.4168},
    {"name": "Barcelona", "lng": 2.1734, "lat": 41.3851},
    {"name": "Miami", "lng": -80.1918, "lat": 25.7617},
    {"name": "Bogotá", "lng": -74.0721, "lat": 4.711},
    {"name": "Buenos Aires", "lng": -58.3816, "lat": -34.6037},
    {"name": "Lisboa", "lng": -9.1393, "lat": 38.7223},
    {"name": "Ciudad de México", "lng": -99.1332, "lat": 19.4326},
    {"name": "Nueva York", "lng": -74.006, "lat": 40.7128},
]

ARCS = [
    {
        "id": dest["name"],
        "from": [HUB["lng"], HUB["lat"]],
        "to": [dest["lng"], dest["lat"]],
        "destination": dest["name"],
    }
    for dest in DESTINATIONS
]

# Shipping lanes with extra properties used by MapLibre expressions.
LANES = [
    {
        "id": "shg-lax",
        "origin": "Shanghai",
        "destination": "Los Angeles",
        "from": [121.4737, 31.2304],
        "to": [-118.2437, 34.0522],
        "volume": "24.8k TEU",
        "mode": "sea",
    },
    {
        "id": "sin-rtm",
        "origin": "Singapore",
        "destination": "Rotterdam",
        "from": [103.8198, 1.3521],
        "to": [4.4777, 51.9244],
        "volume": "9.4k TEU",
        "mode": "sea",
    },
    {
        "id": "san-cpt",
        "origin": "Santos",
        "destination": "Cape Town",
        "from": [-46.3322, -23.9608],
        "to": [18.4241, -33.9249],
        "volume": "3.2k TEU",
        "mode": "sea",
    },
    {
        "id": "syd-nrt",
        "origin": "Sydney",
        "destination": "Tokyo",
        "from": [151.2093, -33.8688],
        "to": [139.6917, 35.6895],
        "volume": "640 tons",
        "mode": "air",
    },
    {
        "id": "dxb-jfk",
        "origin": "Dubai",
        "destination": "New York",
        "from": [55.2708, 25.2048],
        "to": [-74.006, 40.7128],
        "volume": "980 tons",
        "mode": "air",
    },
    {
        "id": "ccs-mad",
        "origin": "Caracas",
        "destination": "Madrid",
        "from": [-66.9036, 10.4806],
        "to": [-3.7038, 40.4168],
        "volume": "1.2k tons",
        "mode": "air",
    },
]

MODE_COLORS = {"air": "#a78bfa", "sea": "#34d399"}

LANE_ENDPOINTS: list[dict] = []
_seen: set[str] = set()
for _lane in LANES:
    for _key, _coords in (("origin", _lane["from"]), ("destination", _lane["to"])):
        if _lane[_key] not in _seen:
            _seen.add(_lane[_key])
            LANE_ENDPOINTS.append(
                {"name": _lane[_key], "lng": _coords[0], "lat": _coords[1]}
            )

# --- GeoJSON ----------------------------------------------------------------

WORLD_GEOJSON_URL = (
    "https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@v5.1.2/geojson/"
    "ne_110m_admin_0_countries.geojson"
)

EARTHQUAKES_URL = "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"

# Inline polygons over Caracas (parks).
CARACAS_PARKS = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Parque del Este", "area_ha": 82},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-66.8545, 10.4890],
                        [-66.8400, 10.4890],
                        [-66.8400, 10.4965],
                        [-66.8545, 10.4965],
                        [-66.8545, 10.4890],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "Parque Los Caobos", "area_ha": 22},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-66.8930, 10.4955],
                        [-66.8860, 10.4955],
                        [-66.8860, 10.5010],
                        [-66.8930, 10.5010],
                        [-66.8930, 10.4955],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {"name": "Jardín Botánico", "area_ha": 70},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-66.8880, 10.4880],
                        [-66.8810, 10.4880],
                        [-66.8810, 10.4940],
                        [-66.8880, 10.4940],
                        [-66.8880, 10.4880],
                    ]
                ],
            },
        },
    ],
}

# --- Custom styles ----------------------------------------------------------

MAP_STYLES = {
    "Default (CARTO)": "",
    "OpenFreeMap Bright": "https://tiles.openfreemap.org/styles/bright",
    "OpenFreeMap Liberty": "https://tiles.openfreemap.org/styles/liberty",
    "OpenFreeMap Positron": "https://tiles.openfreemap.org/styles/positron",
}
