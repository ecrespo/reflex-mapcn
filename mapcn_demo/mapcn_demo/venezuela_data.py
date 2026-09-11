"""Reference data for the Venezuela country demo.

State polygons live in ``assets/venezuela_estados.geojson`` (derived from the
Apache Superset country-map plugin, Apache-2.0) with normalised properties:
``iso``, ``name``, ``capital`` and ``region``.
"""

from __future__ import annotations

import dataclasses

# Served by Reflex from the demo's assets/ folder.
VENEZUELA_STATES_URL = "/venezuela_estados.geojson"

# Rough country box used for the initial fit and to keep the camera nearby.
VENEZUELA_BOUNDS = [[-73.6, 0.5], [-59.5, 12.5]]
VENEZUELA_MAX_BOUNDS = [[-80.0, -3.0], [-53.0, 18.0]]
VENEZUELA_CENTER = [-66.2, 7.9]

# Administrative regions and the color used for their states.
REGION_COLORS = {
    "Capital": "#ef4444",
    "Central": "#f97316",
    "Centro-Occidental": "#eab308",
    "Zuliana": "#22c55e",
    "Los Andes": "#14b8a6",
    "Los Llanos": "#84cc16",
    "Nororiental": "#3b82f6",
    "Insular": "#06b6d4",
    "Guayana": "#a855f7",
}

# [west, south, east, north] per state (computed from the polygons).
STATE_BOUNDS: dict[str, list[float]] = {
    "Amazonas": [-67.8751, 0.6493, -63.3649, 6.1932],
    "Anzoátegui": [-65.7026, 7.6602, -62.6858, 10.2617],
    "Apure": [-72.3958, 6.0807, -66.3246, 8.0717],
    "Aragua": [-67.8742, 9.3935, -66.5431, 10.5431],
    "Barinas": [-71.8471, 7.2874, -67.519, 9.0234],
    "Bolívar": [-67.4563, 3.5608, -60.268, 8.448],
    "Carabobo": [-68.4232, 9.8197, -67.529, 10.5951],
    "Cojedes": [-68.9924, 8.5328, -67.7563, 10.1287],
    "Delta Amacuro": [-62.5976, 7.7518, -59.8156, 10.0515],
    "Dependencias Federales": [-67.6888, 10.885, -64.5568, 12.069],
    "Distrito Capital": [-67.1511, 10.393, -66.8536, 10.5752],
    "Falcón": [-71.282, 10.3048, -68.2388, 12.1989],
    "Guárico": [-68.0365, 7.6361, -64.7899, 10.0194],
    "Isla de Aves": [-63.6436, 15.694, -63.6346, 15.7006],
    "La Guaira": [-67.4051, 10.3959, -66.308, 10.6327],
    "Lara": [-70.8581, 9.3957, -68.8855, 10.7647],
    "Mérida": [-71.9449, 7.6845, -70.5347, 9.3525],
    "Miranda": [-67.2202, 9.9289, -65.4258, 10.6486],
    "Monagas": [-64.0557, 8.3857, -62.0076, 10.3147],
    "Nueva Esparta": [-64.4086, 10.7337, -63.7877, 11.1791],
    "Portuguesa": [-70.1825, 8.1125, -68.5735, 9.8443],
    "Sucre": [-64.5361, 10.0421, -61.8458, 10.762],
    "Táchira": [-72.4912, 7.3634, -71.3176, 8.6114],
    "Trujillo": [-71.0908, 8.9553, -70.0158, 10.0316],
    "Yaracuy": [-69.2376, 9.8511, -68.2517, 10.7325],
    "Zulia": [-73.3908, 8.3827, -70.6363, 11.8508],
}

STATE_INFO: dict[str, dict[str, str]] = {
    "Amazonas": {"capital": "Puerto Ayacucho", "region": "Guayana"},
    "Anzoátegui": {"capital": "Barcelona", "region": "Nororiental"},
    "Apure": {"capital": "San Fernando de Apure", "region": "Los Llanos"},
    "Aragua": {"capital": "Maracay", "region": "Central"},
    "Barinas": {"capital": "Barinas", "region": "Los Andes"},
    "Bolívar": {"capital": "Ciudad Bolívar", "region": "Guayana"},
    "Carabobo": {"capital": "Valencia", "region": "Central"},
    "Cojedes": {"capital": "San Carlos", "region": "Central"},
    "Delta Amacuro": {"capital": "Tucupita", "region": "Guayana"},
    "Dependencias Federales": {"capital": "Gran Roque", "region": "Insular"},
    "Distrito Capital": {"capital": "Caracas", "region": "Capital"},
    "Falcón": {"capital": "Coro", "region": "Centro-Occidental"},
    "Guárico": {"capital": "San Juan de los Morros", "region": "Los Llanos"},
    "Isla de Aves": {"capital": "—", "region": "Insular"},
    "La Guaira": {"capital": "La Guaira", "region": "Capital"},
    "Lara": {"capital": "Barquisimeto", "region": "Centro-Occidental"},
    "Mérida": {"capital": "Mérida", "region": "Los Andes"},
    "Miranda": {"capital": "Los Teques", "region": "Capital"},
    "Monagas": {"capital": "Maturín", "region": "Nororiental"},
    "Nueva Esparta": {"capital": "La Asunción", "region": "Insular"},
    "Portuguesa": {"capital": "Guanare", "region": "Centro-Occidental"},
    "Sucre": {"capital": "Cumaná", "region": "Nororiental"},
    "Táchira": {"capital": "San Cristóbal", "region": "Los Andes"},
    "Trujillo": {"capital": "Trujillo", "region": "Los Andes"},
    "Yaracuy": {"capital": "San Felipe", "region": "Centro-Occidental"},
    "Zulia": {"capital": "Maracaibo", "region": "Zuliana"},
}

STATE_NAMES = sorted(STATE_INFO)


@dataclasses.dataclass
class City:
    """A city rendered as a marker."""

    name: str
    state: str
    kind: str  # "nacional" | "estadal" | "ciudad"
    lng: float
    lat: float


CITIES: list[City] = [
    City("Caracas", "Distrito Capital", "nacional", -66.9036, 10.4806),
    City("Maracaibo", "Zulia", "estadal", -71.6125, 10.6427),
    City("Valencia", "Carabobo", "estadal", -68.0077, 10.1620),
    City("Barquisimeto", "Lara", "estadal", -69.3470, 10.0678),
    City("Maracay", "Aragua", "estadal", -67.5958, 10.2469),
    City("Ciudad Guayana", "Bolívar", "ciudad", -62.6337, 8.3533),
    City("Barcelona", "Anzoátegui", "estadal", -64.6833, 10.1333),
    City("Puerto La Cruz", "Anzoátegui", "ciudad", -64.6333, 10.2167),
    City("Maturín", "Monagas", "estadal", -63.1833, 9.7500),
    City("Cumaná", "Sucre", "estadal", -64.1667, 10.4500),
    City("Mérida", "Mérida", "estadal", -71.1449, 8.5822),
    City("San Cristóbal", "Táchira", "estadal", -72.2250, 7.7669),
    City("Ciudad Bolívar", "Bolívar", "estadal", -63.5497, 8.1222),
    City("Barinas", "Barinas", "estadal", -70.2069, 8.6226),
    City("Puerto Ayacucho", "Amazonas", "estadal", -67.6236, 5.6631),
    City("San Fernando de Apure", "Apure", "estadal", -67.4728, 7.8939),
    City("San Carlos", "Cojedes", "estadal", -68.5833, 9.6611),
    City("Tucupita", "Delta Amacuro", "estadal", -62.0500, 9.0611),
    City("Coro", "Falcón", "estadal", -69.6667, 11.4045),
    City("Punto Fijo", "Falcón", "ciudad", -70.1997, 11.6942),
    City("San Juan de los Morros", "Guárico", "estadal", -67.3536, 9.9111),
    City("Los Teques", "Miranda", "estadal", -67.0431, 10.3444),
    City("La Asunción", "Nueva Esparta", "estadal", -63.8861, 11.0333),
    City("Porlamar", "Nueva Esparta", "ciudad", -63.8500, 10.9500),
    City("Guanare", "Portuguesa", "estadal", -69.7422, 9.0419),
    City("Acarigua", "Portuguesa", "ciudad", -69.2019, 9.5597),
    City("Trujillo", "Trujillo", "estadal", -70.4361, 9.3667),
    City("Valera", "Trujillo", "ciudad", -70.6036, 9.3178),
    City("La Guaira", "La Guaira", "estadal", -66.9333, 10.6000),
    City("San Felipe", "Yaracuy", "estadal", -68.7333, 10.3333),
    City("Gran Roque", "Dependencias Federales", "estadal", -66.6667, 11.9500),
    City("Cabimas", "Zulia", "ciudad", -71.4383, 10.3986),
    City("El Tigre", "Anzoátegui", "ciudad", -64.2589, 8.8919),
    City("Carúpano", "Sucre", "ciudad", -63.2583, 10.6667),
]

# Basemap styles with street-level detail (OpenStreetMap data via OpenFreeMap).
VENEZUELA_STYLES = {
    "OpenFreeMap Liberty (calles, POIs)": "https://tiles.openfreemap.org/styles/liberty",
    "OpenFreeMap Bright": "https://tiles.openfreemap.org/styles/bright",
    "OpenFreeMap Positron (claro)": "https://tiles.openfreemap.org/styles/positron",
    "CARTO (por defecto, claro/oscuro)": "",
}
