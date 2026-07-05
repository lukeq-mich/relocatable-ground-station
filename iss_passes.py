#!/usr/bin/env python3
"""
Phase 0 — ISS pass predictor for multiple ground stations.

Prints the next visible passes of the ISS over each of your stations,
in that station's correct local time. Location-aware from the start:
add a new station to the STATIONS dict and everything else just works.

Setup (once):
    pip install skyfield

Run:
    python3 iss_passes.py

Concepts this touches (good to understand, not just run):
  - TLE: a "two-line element set", the standard text format describing a
    satellite's orbit at a moment in time (its "epoch"). It slowly goes
    stale, so we re-download it.
  - Az/El (azimuth/elevation): where to LOOK from your spot on the ground.
    Elevation = height above the horizon (0 = horizon, 90 = straight up).
    Azimuth = compass direction (0 = North, 90 = East, ...).
  - AOS / LOS: Acquisition / Loss Of Signal -- when the satellite rises above
    and sinks below your horizon. The window when you could see/hear it.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from skyfield.api import load, wgs84

# CONFIG -- your ground stations. Add as many as you like.
#   latlon(latitude_deg, longitude_deg, elevation_m)
#   tz: an IANA timezone name (handles daylight saving automatically)

STATIONS = {
    "Canberra": {
        "site": wgs84.latlon(-35.2809, 149.1300, elevation_m=577),
        "tz": ZoneInfo("Australia/Sydney"),
    },
    "Ann Arbor": {
        "site": wgs84.latlon(42.2808, -83.7430, elevation_m=256),
        "tz": ZoneInfo("America/Detroit"),
    },
}

# ISS catalog number is 25544. Celestrak serves its current TLE here:
TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle"
TLE_CACHE = "iss.tle"      # local cache filename

DAYS_AHEAD = 3             # how far ahead to look
NUM_PASSES = 5             # passes to show per station
MIN_PEAK_ELEVATION = 10    # degrees; skip low passes that barely clear the horizon
HORIZON = 10               # degrees; altitude that counts as "risen"

ts = load.timescale()


def load_satellite():
    """Download (and cache) the ISS TLE, returning a Skyfield satellite."""
    # reload=True re-downloads if the cached file is older than ~1 day.
    sats = load.tle_file(TLE_URL, filename=TLE_CACHE, reload=True)
    by_number = {s.model.satnum: s for s in sats}
    return by_number.get(25544, sats[0])


def compass(azimuth_deg):
    """Turn an azimuth in degrees into a 16-point compass direction."""
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return points[round(azimuth_deg / 22.5) % 16]


def upcoming_passes(sat, site, days, horizon):
    """Return a list of complete passes, each as {rise, peak, set} Skyfield times."""
    t0 = ts.now()
    t1 = ts.from_datetime(t0.utc_datetime() + timedelta(days=days))
    # find_events returns interleaved rise(0), culminate(1), set(2) events.
    times, events = sat.find_events(site, t0, t1, altitude_degrees=horizon)

    passes, current = [], {}
    for t, event in zip(times, events):
        if event == 0:        # rise
            current = {"rise": t}
        elif event == 1:      # culminate (highest point)
            current["peak"] = t
        elif event == 2:      # set
            current["set"] = t
            if "rise" in current and "peak" in current:
                passes.append(current)
            current = {}
    return passes


def peak_look_angle(sat, site, peak_time):
    """Elevation and azimuth of the satellite at its highest point in the pass."""
    alt, az, _distance = (sat - site).at(peak_time).altaz()
    return alt.degrees, az.degrees


def main():
    sat = load_satellite()

    # Report how fresh the orbit data is -- old TLEs give bad predictions.
    age_days = ts.now() - sat.epoch
    print(f"Satellite: {sat.name}")
    print(f"TLE epoch age: {age_days:.1f} days "
          f"({'fresh' if abs(age_days) < 7 else 'consider refreshing'})")

    for name, cfg in STATIONS.items():
        site, tz = cfg["site"], cfg["tz"]
        print(f"\n=== {name} -- next ISS passes (local time) ===")

        shown = 0
        for p in upcoming_passes(sat, site, DAYS_AHEAD, HORIZON):
            elev, az = peak_look_angle(sat, site, p["peak"])
            if elev < MIN_PEAK_ELEVATION:
                continue

            rise = p["rise"].astimezone(tz)
            sett = p["set"].astimezone(tz)
            duration_min = (sett - rise).total_seconds() / 60

            print(f"  {rise:%a %d %b  %H:%M}  ->  {sett:%H:%M}   "
                  f"peak {elev:4.0f} deg to the {compass(az):3}   "
                  f"({duration_min:.0f} min)")

            shown += 1
            if shown >= NUM_PASSES:
                break

        if shown == 0:
            print("  (no good passes in the window -- try increasing DAYS_AHEAD)")


if __name__ == "__main__":
    main()
