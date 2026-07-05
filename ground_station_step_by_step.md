# Relocatable Satellite Ground Station — Step-by-Step Guide

Your master walkthrough, in order. Reflects the decisions we've locked in.

---

## What you're building (one breath)

A location-aware tool that predicts when satellites pass over wherever you are and
shows you where to look — and, with a ~$50 radio dongle, actually pulls down live
weather-satellite images of Earth that you capture yourself. It follows you between
Canberra and Ann Arbor (opposite hemispheres), which is both a practical need and a
genuinely distinctive portfolio story.

## Decisions locked in

- **Project:** satellite pass predictor + ground station (software core, optional receive leg).
- **Locations:** Canberra and Ann Arbor — designed location-aware, not hardcoded.
- **Editor:** VS Code with a per-project virtual environment (portable across machines).
- **Targets:** Meteor-M2-3 / M2-4 (LRPT, ~137 MHz). The old NOAA APT satellites are
  decommissioned as of 2025 — most online tutorials still point at them; you won't.
- **Decoder:** SatDump (modern all-in-one).
- **Legal:** receiving needs no license (you only listen). No rocketry/explosives issues.

## The portfolio angle (why this stands out)

This isn't an untapped commercial market — good free tools exist. Your edge is **currency**:
the 2025 NOAA shutdown made most beginner content obsolete, so a clean, correct,
*current* build with your own captured images fills a real gap in what applicants produce.
Lean into that in your write-up.

---

## SETUP (do once)

1. **Install VS Code**, then the official **Python extension** (Microsoft).
2. **Make a project folder**, e.g. `ground-station/`, and open it in VS Code
   (File → Open Folder).
3. **Create a virtual environment** in the VS Code terminal:
   ```
   python3 -m venv .venv
   ```
   Accept VS Code's prompt to use it (or pick it via "Python: Select Interpreter").
4. **Install dependencies** into that environment:
   ```
   pip install skyfield
   pip freeze > requirements.txt
   ```
   `requirements.txt` lets you recreate the exact setup on your other machine.
5. **Start version control now:** create a GitHub repo and commit from day one
   (add a `.gitignore` that excludes `.venv/` and the cached `*.tle` files).

---

## PHASE 0 — ISS predictor for both stations  ✅ DONE

You already have `iss_passes.py`. Drop it in the folder and run it (▶ or
`python3 iss_passes.py`). It fetches the ISS's live orbit and prints its next passes
over Canberra and Ann Arbor in each one's correct local time.

- The `STATIONS` dict at the top is the location-aware core — adding a place is one line.
- It prints the TLE's age; stale orbit data is the #1 cause of wrong predictions.

**Done check:** you see a list of upcoming ISS passes for both cities with peak
elevation and look direction.

---

## PHASE 1 — Generalize to any satellite (Weeks 1–2 from here)

Turn the ISS-only script into a real engine.

- Track **any satellite by name / NORAD ID**, not just the ISS.
- Add the live weather birds: **Meteor-M2-3 and Meteor-M2-4**.
- For each pass compute AOS, LOS, peak elevation, peak azimuth, duration.
- **Filter for good passes** (peak elevation > ~20–30°) — low passes decode poorly.
- Keep timezones correct per station (you already handle this with `zoneinfo`).

**Concept to actually learn here:** how an orbit (in an Earth-centered frame) becomes an
azimuth/elevation "look angle" from your backyard. This is the heart of the project and
great interview material.

**Done check:** given a satellite + a station, you get a clean, filtered pass schedule.

---

## PHASE 2 — Dashboard (Weeks 3–5)

Make it a tool, not a script — this is the most portfolio-visible part.

- Use **Streamlit** (pure Python, fastest path). Upgrade path if you want web cred:
  FastAPI + a small JS frontend (note the choice in your README).
- Build:
  - a **location dropdown** (Canberra / Ann Arbor / …),
  - an **upcoming-pass table**,
  - a **polar sky plot** of a selected pass (where to point in the sky),
  - a **live "where is it now" map** with ground track.
- Auto-refresh TLEs so predictions stay accurate.

**Done check:** pick a location, see live positions + upcoming passes update for it.

---

## PHASE 3 — The receive leg (Weeks 6–9) — the "wow"

Turn predictions into an image you captured.

1. Buy the hardware (see list below). Build the V-dipole from the kit antenna
   (two elements ~½ m, in a ~120° "V"); place it outdoors with a clear sky view.
2. Install **SatDump** (use a current build — it updates often).
3. **Check the current Meteor frequency/mode that day** (usradioguy.com / rtl-sdr.com) —
   Meteor settings change (e.g. 72k vs 80k, 137.1 vs 137.9 MHz).
4. Use your predictor (or SatDump's tracker) to catch a **high-elevation** Meteor pass.
   Set gain manually (~25–30 dB), start recording a couple of minutes before AOS.
5. Let SatDump decode it into an image.

**Done check:** a decoded Meteor LRPT image — your own capture of Earth from space.

*Expect your first pass or two to fail (noise, low elevation, wrong mode). Diagnosing
that is the impressive part, not a setback.*

---

## PHASE 4 — Integration & stretch (Weeks 9–11)

Pick what excites you; one done well beats three half-built.

- **Close the loop:** dashboard flags the best upcoming pass → compare *predicted* vs
  *actual* timing.
- **Georeference** your captured image (coastlines/borders overlay) and show it in the dashboard.
- **Both-hemisphere comparison:** capture from +42° and −35° latitude in the same year —
  your signature story.
- Stretch targets: ISS SSTV events; GOES / L-band (needs a dish — advanced).

---

## PACKAGING (ongoing; final push at the end)

This is what converts the build into interviews.

- **GitHub repo** with a real README: what it does, dashboard screenshots, and a
  **gallery of images you received**.
- **Engineering-judgment paragraph:** state plainly that you targeted Meteor LRPT because
  NOAA APT is decommissioned — with sources. This single paragraph signals maturity.
- **Predicted-vs-actual** comparison for a real pass.
- **A 60–90s demo video / GIF** of the dashboard tracking + an image decoding.

---

## Parts to buy (only when you reach Phase 3)

Software phases (0–2): **$0** — laptop only.

Receive leg (~AUD 50–110), from Core Electronics / Little Bird:
- **RTL-SDR Blog V4 starter kit** (~$45–60) — SDR + multipurpose dipole (use as 137 MHz V-dipole).
- *(Optional)* **137 MHz SAW-filtered LNA** (~$40) — only if you're in an RF-noisy spot.
- Short coax (RG-58), a non-metallic mast/tripod, a clear sky view.

The hardware is carry-on portable — the same setup works in Ann Arbor.

---

## Realistic timeline

- Software core (Phases 0–2): ~5 weeks at 5–8 hrs/week → a complete, presentable project.
- Add the receive leg (Phases 3–4): ~10–11 weeks total.
- A demoable "Solid" version exists well before the end.

## Honest expectations

- A naive multi-location project breaks on **time zones** — you've already handled this; keep it that way.
- **TLE freshness** matters; refresh before relying on a prediction.
- Reception depends on physics you don't control: clear sky, low RF noise, decent elevation.
  Some captures will be noisy or fail. That's the hobby, not a bug.

---

## Your next step right now

**Phase 1.** Generalize `iss_passes.py` to take a satellite (by name / NORAD ID),
add Meteor-M2-3 and M2-4, and filter for passes above ~25° elevation.
