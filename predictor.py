"""
predictor.py — core engine for the relocatable satellite ground station.

Location-aware, satellite-agnostic pass prediction built on Skyfield.
No UI here: the dashboard (app.py) and any CLI import from this module.

Concepts:
  TLE      two-line element set — a satellite's orbit at an epoch (goes stale).
  Az/El    azimuth (compass bearing) + elevation (height above horizon) = where to look.
  AOS/LOS  acquisition / loss of signal — when it rises above / sets below the horizon.
  Subpoint the lat/lon on Earth directly beneath the satellite (for the live map).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

import socket
socket.setdefaulttimeout(20)

# CONFIG

# Ground stations. Add a place = add a line. tz is an IANA name (handles DST).
STATIONS: dict[str, dict] = {
    "Canberra":  {"lat": -35.2809, "lon": 149.1300, "elev_m": 577, "tz": "Australia/Sydney"},
    "Ann Arbor": {"lat":  42.2808, "lon": -83.7430, "elev_m": 256, "tz": "America/Detroit"},
}

# Satellites to track, by NORAD catalog number (the stable identifier).
# Verify/adjust at https://celestrak.org  (NOAA APT birds are decommissioned — use Meteor).
SATELLITES: list[dict] = [
    {"label": "ISS",         "norad": 25544},
    {"label": "Meteor-M2-3", "norad": 57166},
    {"label": "Meteor-M2-4", "norad": 59051},
]

GP_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR={norad}&FORMAT=tle"

# CelesTrak rate-limits repeated automated requests (cloud/shared IPs get 403/429
# especially hard), so blindly re-downloading every run is what makes the fetch
# fail in deployment. When a cache window is requested, re-download only if the
# cached tle_<norad>.tle is older than this many hours.
TLE_MAX_AGE_H = 12.0

# Skyfield event codes from find_events()
RISE, CULMINATE, SET = 0, 1, 2

_TS = load.timescale()


# Data types

@dataclass
class Pass:
    satellite: str
    rise: datetime          # tz-aware, local to the station
    peak: datetime
    set: datetime
    peak_elevation: float   # degrees
    peak_azimuth: float     # degrees
    track_az: list = field(default_factory=list)   # for the polar sky plot
    track_el: list = field(default_factory=list)

    @property
    def duration_min(self) -> float:
        return (self.set - self.rise).total_seconds() / 60.0

    @property
    def peak_direction(self) -> str:
        return compass(self.peak_azimuth)


# Helpers

def compass(azimuth_deg: float) -> str:
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return points[round(azimuth_deg / 22.5) % 16]


def station_site(station: str):
    s = STATIONS[station]
    return wgs84.latlon(s["lat"], s["lon"], elevation_m=s["elev_m"])


def station_tz(station: str) -> ZoneInfo:
    return ZoneInfo(STATIONS[station]["tz"])


def timescale():
    return _TS


# Loading satellites

def fetch_satellite(norad: int, max_age_h: float | None = None) -> EarthSatellite | None:
    """Load one satellite's TLE, caching to tle_<norad>.tle, with a fallback.

    max_age_h=None (default): always try a fresh download, but if the network
    fails, fall back to the cached file so a celestrak hiccup doesn't take the
    whole app down. This is why the repo ships the ISS/Meteor .tle files — they
    are the offline safety net.
    max_age_h set: skip the download entirely while the cache is younger than
    that many hours (used by the conjunction screener, which must not re-fetch
    a whole object list every run).

    Returns None only when the object can't be loaded at all — no network *and*
    no cached file. A stale-but-usable TLE is preferred over nothing; its age
    is surfaced in the UI (see tle_age_days), never assumed fresh.
    """
    path = f"tle_{norad}.tle"
    try:
        age_s = time.time() - os.path.getmtime(path)
    except OSError:
        age_s = None
    fresh = max_age_h is not None and age_s is not None and age_s < max_age_h * 3600.0

    sats = None
    try:
        sats = load.tle_file(GP_URL.format(norad=norad),
                             filename=path, reload=not fresh)
    except Exception:
        if age_s is not None:                      # download failed; use the cache
            try:
                sats = load.tle_file(path)
            except Exception:
                return None
    if not sats:
        return None
    for s in sats:
        if s.model.satnum == norad:
            return s
    return sats[0]


def load_satellites(configs=SATELLITES) -> tuple[dict[str, EarthSatellite], list[str]]:
    """Return ({label: satellite}, [labels that failed to load])."""
    loaded, failed = {}, []
    for cfg in configs:
        sat = fetch_satellite(cfg["norad"])
        if sat is None:
            failed.append(cfg["label"])
        else:
            sat.name = cfg["label"]
            loaded[cfg["label"]] = sat
    return loaded, failed


def tle_age_days(sat: EarthSatellite) -> float:
    return _TS.now() - sat.epoch


# Predictions

def _sample_track(sat, site, t_rise, t_set, n=40):
    """Sample az/el across a pass for the polar sky plot."""
    jd0, jd1 = t_rise.tt, t_set.tt
    times = _TS.tt_jd(np.linspace(jd0, jd1, n))
    alt, az, _ = (sat - site).at(times).altaz()
    return list(az.degrees), list(alt.degrees)


def find_passes(sat, site, tz, days=3, min_elevation=25.0, horizon=10.0) -> list[Pass]:
    """All passes of `sat` over `site` in the next `days`, filtered by peak elevation."""
    t0 = _TS.now()
    t1 = _TS.from_datetime(t0.utc_datetime() + timedelta(days=days))
    times, events = sat.find_events(site, t0, t1, altitude_degrees=horizon)

    passes, cur = [], {}
    for t, e in zip(times, events):
        if e == RISE:
            cur = {"rise": t}
        elif e == CULMINATE:
            cur["peak"] = t
        elif e == SET and "rise" in cur and "peak" in cur:
            cur["set"] = t
            alt, az, _ = (sat - site).at(cur["peak"]).altaz()
            if alt.degrees >= min_elevation:
                taz, tel = _sample_track(sat, site, cur["rise"], cur["set"])
                passes.append(Pass(
                    satellite=getattr(sat, "name", "sat"),
                    rise=cur["rise"].astimezone(tz),
                    peak=cur["peak"].astimezone(tz),
                    set=cur["set"].astimezone(tz),
                    peak_elevation=alt.degrees,
                    peak_azimuth=az.degrees,
                    track_az=taz, track_el=tel,
                ))
            cur = {}
    return passes


def upcoming_passes(sats: dict, station: str, days=3, min_elevation=25.0) -> list[Pass]:
    """Flat, time-sorted list of passes across all satellites for one station."""
    site, tz = station_site(station), station_tz(station)
    out = []
    for sat in sats.values():
        out.extend(find_passes(sat, site, tz, days=days, min_elevation=min_elevation))
    out.sort(key=lambda p: p.rise)
    return out


def current_position(sat) -> dict:
    """Live sub-satellite point (lat/lon on Earth) + altitude, for the map."""
    sp = wgs84.subpoint(sat.at(_TS.now()))
    return {"label": getattr(sat, "name", "sat"),
            "lat": sp.latitude.degrees,
            "lon": sp.longitude.degrees,
            "alt_km": sp.elevation.km}


def ground_track(sat, minutes_ahead=35, n=60) -> dict:
    """Sampled sub-points from now forward, for drawing a short ground track."""
    now = _TS.now()
    times = _TS.tt_jd(np.linspace(now.tt, now.tt + minutes_ahead / 1440.0, n))
    sp = wgs84.subpoint(sat.at(times))
    return {"label": getattr(sat, "name", "sat"),
            "lat": list(sp.latitude.degrees),
            "lon": list(sp.longitude.degrees)}
