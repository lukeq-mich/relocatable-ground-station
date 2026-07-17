"""
conjunctions.py — conjunction (close-approach) screening for the ground station.

Screens pairs of tracked objects for close approaches over a forward window,
using the same Skyfield/SGP4 propagation and TLE cache as predictor.py.
No UI here: the dashboard (app.py) imports from this module.

Concepts:
  Conjunction  two objects passing close to each other in orbit.
  TCA          time of closest approach — when the separation is at its minimum.
  Miss distance  the separation at TCA.
  Screening    a coarse geometric filter that finds candidate close approaches.

WHAT THIS MODULE IS NOT — read before trusting a number:
  This is a *geometric screening* tool built on TLE-derived state vectors.
  TLE + SGP4 positions carry errors on the order of a kilometre (growing with
  TLE age), so a computed miss distance of, say, 3 km is statistically
  indistinguishable from 0 km — or from 8 km. Operational conjunction
  assessment (as flown by CSpOC, ESA, LeoLabs, ...) propagates full state
  *covariance* and computes a probability of collision (Pc) via methods like
  Foster or Alfano, using owner/operator ephemerides far more accurate than
  TLEs. This module does none of that: no covariance, no Pc. An event flagged
  here means "worth a look with better data", never "collision predicted" —
  and a clean screen does not certify safety.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from scipy.optimize import minimize_scalar
from skyfield.api import EarthSatellite

import predictor as P

# CONFIG

# Objects screened against the tracked satellites (predictor.SATELLITES), by
# NORAD catalog number. Curated for the demo: objects whose orbits actually
# cross the Meteor/ISS altitude shells, dominated by the two fragmentation
# events that define today's LEO debris environment.
#
# NOTE — catalogs change. Objects decay, get re-designated, or drop out of
# tracking, so anything here can stop resolving; failures are reported by the
# loader, not silently skipped. Verify IDs (or add individual debris
# fragments, e.g. search "FENGYUN 1C DEB") at https://celestrak.org.
DEBRIS_OBJECTS: list[dict] = [
    # Largest tracked remnants of the two defining LEO fragmentation events.
    {"label": "Fengyun-1C (frag)",  "norad": 25730},  # 2007 ASAT test, ~850 km SSO
    {"label": "Cosmos-2251 (frag)", "norad": 22675},  # 2009 collision, ~790 km
    {"label": "Iridium-33 (frag)",  "norad": 24946},  # 2009 collision, ~780 km
    # Large derelicts sharing the Meteor sun-synchronous shell — the objects a
    # real Meteor operator gets conjunction warnings about most often.
    {"label": "Envisat", "norad": 27386},  # 8 t derelict, ~770 km
    {"label": "NOAA-15", "norad": 25338},  # decommissioned, ~810 km
    {"label": "NOAA-18", "norad": 28654},  # decommissioned, ~850 km
    {"label": "NOAA-19", "norad": 33591},  # decommissioned, ~870 km
    # Active neighbours in the same shell (screening isn't only about debris).
    {"label": "Suomi NPP", "norad": 37849},  # ~825 km SSO
    {"label": "Metop-B",   "norad": 38771},  # ~815 km SSO
    {"label": "Metop-C",   "norad": 43689},  # ~815 km SSO
]

# Screening defaults. 72 h is a typical operational screening horizon; beyond
# that TLE error growth makes the geometry meaningless. 5 km is a demo-scale
# threshold — generous enough to fire on real approaches between our handful
# of objects, and honest about TLE-level (km) position uncertainty.
WINDOW_HOURS = 72.0
THRESHOLD_KM = 5.0

# Coarse sampling step for bracketing minima. Between two LEO objects the
# pairwise distance oscillates no faster than roughly once per half orbit
# (~45 min), so 60 s sampling cleanly brackets every local minimum; each
# bracket is then refined numerically (see _refine). The step does NOT limit
# which approaches are found — see the gate in screen() for why.
STEP_S = 60.0

MU_EARTH = 398600.4418  # km^3/s^2

_TS = P.timescale()


# Data types

@dataclass
class Conjunction:
    obj1: str
    obj2: str
    tca: datetime            # tz-aware UTC
    miss_km: float
    rel_speed_km_s: float
    tca_jd_tt: float         # Skyfield TT Julian date, for follow-up geometry

    @property
    def pair(self) -> str:
        return f"{self.obj1} ↔ {self.obj2}"


# Loading the screening set
#
# TLE ingestion + caching lives in predictor.fetch_satellite (shared with pass
# prediction). Screening passes max_age_h so a whole object list isn't
# re-downloaded on every run — the cache is honoured, and a stale cache is
# used if the network is unavailable rather than dropping the object.

def load_screening_set(extra_norads: tuple[int, ...] = ()) -> tuple[dict[str, EarthSatellite], list[str]]:
    """Tracked satellites + debris list + any user-added NORAD IDs.

    Returns ({label: satellite}, [labels that failed to load]) — failures are
    reported because objects decay, get re-designated, or drop out of the
    catalog; a missing object is information, not noise.
    """
    loaded: dict[str, EarthSatellite] = {}
    failed: list[str] = []
    seen: set[int] = set()

    configs = (P.SATELLITES + DEBRIS_OBJECTS
               + [{"label": f"NORAD {n}", "norad": n} for n in extra_norads])
    for cfg in configs:
        if cfg["norad"] in seen:
            continue
        seen.add(cfg["norad"])
        sat = P.fetch_satellite(cfg["norad"], max_age_h=P.TLE_MAX_AGE_H)
        if sat is None:
            failed.append(cfg["label"])
        else:
            # Prefer the catalog's own name for user-added IDs.
            if cfg["label"].startswith("NORAD ") and getattr(sat, "name", None):
                sat.name = sat.name.strip()
            else:
                sat.name = cfg["label"]
            loaded[sat.name] = sat
    return loaded, failed


def tle_status(sats: dict[str, EarthSatellite]) -> list[dict]:
    """Epoch and age of every loaded TLE — accuracy degrades with age, so this
    is surfaced in the UI rather than assumed fresh."""
    return [{
        "label": label,
        "norad": sat.model.satnum,
        "epoch_utc": sat.epoch.utc_datetime(),
        "age_days": P.tle_age_days(sat),
    } for label, sat in sats.items()]


# Screening

def _shell_km(sat: EarthSatellite) -> tuple[float, float]:
    """(perigee, apogee) geocentric radii from the TLE mean elements."""
    n_rad_s = sat.model.no_kozai / 60.0          # no_kozai is rad/min
    a = (MU_EARTH / n_rad_s**2) ** (1.0 / 3.0)
    e = sat.model.ecco
    return a * (1.0 - e), a * (1.0 + e)


def _shells_overlap(s1: EarthSatellite, s2: EarthSatellite, margin_km=150.0) -> bool:
    """Cheap pair prefilter: two orbits can only come close if their radial
    shells [perigee, apogee] overlap. The margin absorbs the difference
    between TLE mean elements and SGP4 osculating radii (short-period terms,
    tens of km) — deliberately generous so this only ever skips pairs that
    are radially separated by far more than any screening threshold."""
    rp1, ra1 = _shell_km(s1)
    rp2, ra2 = _shell_km(s2)
    return max(rp1, rp2) - min(ra1, ra2) <= margin_km


def _separation_fn(sat1: EarthSatellite, sat2: EarthSatellite, jd0_tt: float):
    """Separation (km) as a function of seconds past jd0_tt, for the refiner."""
    def sep(seconds: float) -> float:
        t = _TS.tt_jd(jd0_tt, seconds / 86400.0)
        return float(np.linalg.norm(sat1.at(t).position.km - sat2.at(t).position.km))
    return sep


def screen(sats: dict[str, EarthSatellite],
           hours: float = WINDOW_HOURS,
           threshold_km: float = THRESHOLD_KM,
           step_s: float = STEP_S) -> list[Conjunction]:
    """Screen every pair in `sats` for close approaches over the next `hours`.

    Method — bracket, gate, refine (not fixed-timestep sampling):
      1. Propagate every object on a shared coarse grid (`step_s`).
      2. For each pair, locate every local minimum of the sampled separation.
      3. Gate: near a close approach the separation is locally
         d(t) ≈ sqrt(d_min² + v_rel²·(t−TCA)²), so a coarse sample can exceed
         the true minimum by at most v_rel·step/2 (the sample is at most half
         a step from TCA). Any sampled minimum below
         threshold + v_rel·step/2 might therefore hide a real event and is
         kept; everything above provably cannot dip under the threshold.
      4. Refine each surviving bracket with bounded Brent minimization
         (scipy.optimize.minimize_scalar) to sub-millisecond TCA.

    Returns events with miss distance < threshold_km, sorted by miss distance.
    Reminder: geometric screening on TLEs — no covariance, no Pc (see module
    docstring).
    """
    labels = list(sats)
    t0 = _TS.now()
    jd0 = t0.tt
    n_steps = max(int(round(hours * 3600.0 / step_s)), 2)
    grid_s = np.linspace(0.0, hours * 3600.0, n_steps + 1)
    times = _TS.tt_jd(jd0, grid_s / 86400.0)

    # One vectorized SGP4 propagation per object (positions + velocities, km, km/s).
    pos, vel = {}, {}
    for label in labels:
        g = sats[label].at(times)
        pos[label] = g.position.km
        vel[label] = g.velocity.km_per_s

    events: list[Conjunction] = []
    for i, l1 in enumerate(labels):
        for l2 in labels[i + 1:]:
            if not _shells_overlap(sats[l1], sats[l2]):
                continue
            d = np.linalg.norm(pos[l1] - pos[l2], axis=0)
            v = np.linalg.norm(vel[l1] - vel[l2], axis=0)

            # Local minima of the sampled separation (window edges included,
            # so an approach right at the boundary is still examined).
            interior = np.where((d[1:-1] <= d[:-2]) & (d[1:-1] <= d[2:]))[0] + 1
            candidates = list(interior)
            if d[0] < d[1]:
                candidates.append(0)
            if d[-1] < d[-2]:
                candidates.append(len(d) - 1)

            sep = _separation_fn(sats[l1], sats[l2], jd0)
            for k in candidates:
                if d[k] > threshold_km + v[k] * step_s / 2.0:
                    continue  # provably cannot dip below the threshold
                lo = grid_s[max(k - 1, 0)]
                hi = grid_s[min(k + 1, len(grid_s) - 1)]
                res = minimize_scalar(sep, bounds=(lo, hi), method="bounded",
                                      options={"xatol": 1e-4})
                if res.fun >= threshold_km:
                    continue
                t_tca = _TS.tt_jd(jd0, res.x / 86400.0)
                g1, g2 = sats[l1].at(t_tca), sats[l2].at(t_tca)
                events.append(Conjunction(
                    obj1=l1, obj2=l2,
                    tca=t_tca.utc_datetime(),
                    miss_km=float(res.fun),
                    rel_speed_km_s=float(np.linalg.norm(
                        g1.velocity.km_per_s - g2.velocity.km_per_s)),
                    tca_jd_tt=jd0 + res.x / 86400.0,
                ))

    # Adjacent brackets around one approach can refine to the same TCA — dedupe.
    events.sort(key=lambda e: (e.obj1, e.obj2, e.tca))
    deduped: list[Conjunction] = []
    for e in events:
        prev = deduped[-1] if deduped else None
        if (prev and prev.obj1 == e.obj1 and prev.obj2 == e.obj2
                and abs((e.tca - prev.tca).total_seconds()) < step_s):
            if e.miss_km < prev.miss_km:
                deduped[-1] = e
            continue
        deduped.append(e)

    deduped.sort(key=lambda e: e.miss_km)
    return deduped


# Encounter geometry (for the relative-motion plot)

def encounter_geometry(sat1: EarthSatellite, sat2: EarthSatellite,
                       tca_jd_tt: float, span_s: float = 600.0, n: int = 241) -> dict:
    """Relative motion of sat2 about sat1 around a TCA, for plotting.

    Positions are expressed in an encounter frame fixed at TCA:
      x  toward sat2 at TCA (so TCA sits at x = miss distance),
      y  along the relative velocity (the direction the encounter sweeps),
      z  completes the right-handed set (out of the encounter plane).
    At a separation minimum the relative position and velocity are
    perpendicular, so x and y are orthogonal by construction.
    """
    offsets = np.linspace(-span_s / 2.0, span_s / 2.0, n)
    times = _TS.tt_jd(tca_jd_tt, offsets / 86400.0)
    r_rel = sat2.at(times).position.km - sat1.at(times).position.km   # (3, n)

    t_tca = _TS.tt_jd(tca_jd_tt)
    r0 = sat2.at(t_tca).position.km - sat1.at(t_tca).position.km
    v0 = sat2.at(t_tca).velocity.km_per_s - sat1.at(t_tca).velocity.km_per_s

    e_y = v0 / np.linalg.norm(v0)
    x0 = r0 - np.dot(r0, e_y) * e_y            # ⊥ component (≈ r0 itself at TCA)
    if np.linalg.norm(x0) < 1e-9:              # degenerate: essentially head-on
        x0 = np.cross(e_y, [0.0, 0.0, 1.0])
    e_x = x0 / np.linalg.norm(x0)
    e_z = np.cross(e_x, e_y)

    frame = np.vstack([e_x, e_y, e_z])         # rows are the frame axes
    xyz = frame @ r_rel                        # (3, n) in encounter frame
    return {
        "offset_s": offsets,
        "sep_km": np.linalg.norm(r_rel, axis=0),
        "x_km": xyz[0], "y_km": xyz[1], "z_km": xyz[2],
    }
