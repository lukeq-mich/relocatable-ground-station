# Relocatable Satellite Ground Station  [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://luke-ground-station.streamlit.app/)  [Github](https://github.com/lukeq-mich/relocatable-ground-station)

*A portable ground station for tracking weather satellites from anywhere — currently deployed in Canberra and Ann Arbor.*



![Dashboard screenshot](docs/dashboard.png)
<!-- Replace docs/dashboard.png with a real screenshot of the running dashboard.
     A recruiter skims — this image does more work than any paragraph here. -->

Predicts satellite passes over any of your ground stations and shows where to point —
built location-aware so it follows you between sites (e.g. Canberra ↔ Ann Arbor).
Tracks the ISS and the live **Meteor-M2** weather satellites, with a live map,
an upcoming-pass table, and a sky-view plot of any pass.

## Why this project

Most beginner guides to receiving weather-satellite imagery target the NOAA APT
satellites — but **all of those (NOAA-15, -18, -19) were decommissioned in 2025**,
so the majority of existing tutorials are now obsolete. This project targets the
**current** constellation instead: the Russian Meteor-M2 satellites, which broadcast
higher-quality digital LRPT imagery at ~137 MHz.

It's also built **location-aware from the ground up**: the observer site is
configuration, not a hardcoded assumption, so the same code predicts passes from
+42° latitude (Michigan) and −35° latitude (Australia) in the same year — opposite
hemispheres, same tool.

## What it does

- **Live map** — where each tracked satellite is right now, with a short forward ground track.
- **Upcoming passes** — a time-sorted table for the selected station, in correct local time.
- **Sky view** — a polar plot of any pass (centre = overhead, edge = horizon) showing exactly where to point.
- **Multi-station** — switch locations from a dropdown; add new ones in one line of config.
- **Conjunction screening** — a second mode that screens the tracked satellites
  against a configurable set of debris and neighbouring spacecraft for close
  approaches (see below).

## Conjunction screening (SSA mode)

Switch the sidebar to **Conjunction screening** to screen all loaded objects —
the tracked satellites plus a curated set of debris-event remnants and large
derelicts in the same altitude shells (Fengyun-1C, Cosmos-2251/Iridium-33,
Envisat, the retired NOAA birds, …), plus any NORAD IDs you type in — for
close approaches over the next 72 h (configurable).

**How the screening works** (`conjunctions.py`): every object is propagated
with SGP4; pairs whose perigee–apogee shells can't come near each other are
skipped; the rest are sampled on a 60 s grid, and every local minimum of the
pairwise separation that could possibly dip under the threshold (sampled
minimum < threshold + v·Δt/2 — the provable bound on how much a coarse sample
can overstate the true minimum) is refined with bounded Brent minimization
(`scipy.optimize`) to a sub-millisecond time of closest approach. Close
approaches *between* grid samples are therefore not missed: the grid only
brackets candidates, the optimizer finds the actual minimum. Each flagged
event reports the pair, TCA, miss distance, and relative speed, with a
separation-vs-time plot and a 3-D relative-trajectory view of the encounter.

**What it is not.** This is *geometric screening on TLEs*, not operational
conjunction assessment, and the app says so on the page (Methodology &
limitations):

- TLE/SGP4 state vectors carry position errors of order **1 km at epoch,
  growing roughly km/day** — a 3 km computed miss is indistinguishable from
  0 km. Every TLE's epoch and age are shown in the app, because catalogs
  churn: objects decay, get re-designated, or drop out of tracking (load
  failures are reported, not hidden).
- There is **no covariance propagation and no probability of collision (Pc)**.
  Operational SSA systems (CSpOC, ESA, commercial) compute Pc with methods
  like Foster or Alfano from owner/operator ephemerides far more accurate
  than TLEs. Nothing here should be read as a collision prediction — a
  flagged event means "worth a look with better data", and a clean screen
  certifies nothing.
- Maneuvers are not modeled, and only the configured objects are screened —
  the real catalog is ~30 000 objects.

## Files

- `predictor.py` — the pass engine: loads TLEs, finds passes, computes look angles
  and live positions. No UI; import it from anywhere.
- `conjunctions.py` — the screening engine: TLE caching with age tracking,
  all-pairs close-approach search, encounter geometry. No UI either.
- `app.py` — the Streamlit dashboard (both modes).
- `iss_passes.py` — the original minimal CLI (ISS-only). Optional starting point.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then pick a location and satellites in the sidebar.

## Configure

Edit the two dicts at the top of `predictor.py`:

- `STATIONS` — add a place with lat/lon/elevation and an IANA timezone.
- `SATELLITES` — add a satellite by NORAD catalog number (verify IDs at celestrak.org).

For screening, `DEBRIS_OBJECTS` at the top of `conjunctions.py` lists the
default screening set (same `{label, norad}` shape), and extra NORAD IDs can
be added at runtime from the sidebar.

## How it works (the interesting parts)

- **Orbit propagation** from TLEs (two-line element sets) via SGP4.
- **Coordinate transform** from an Earth-centred inertial frame to a local
  azimuth/elevation "look angle" — the heart of turning an orbit into "point there".
- **Timezone-correct** multi-site scheduling using `zoneinfo` (handles DST on both
  hemispheres' opposite calendars).
- **Close-approach search** that brackets every local minimum of pairwise
  separation on a coarse grid, gates each with a provable can't-miss bound,
  then polishes it with bounded scalar minimization — screen-then-refine,
  not naive fixed-timestep sampling.

## Roadmap

- **Next:** hardware "receive leg" — an RTL-SDR dongle + SatDump to capture real
  Meteor-M2 LRPT imagery, scheduled from this predictor's pass times.
- Georeferenced image overlays and predicted-vs-actual pass comparison.

## Notes

- TLEs are cached locally and re-downloaded ~daily; the dashboard shows their age.
- "Min peak elevation" ~25° is a good target — low passes decode poorly.

## License

MIT — see [LICENSE](LICENSE).
