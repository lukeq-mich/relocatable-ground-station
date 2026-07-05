# Satellite Pass Predictor + Ground Station — Build Plan

**Goal:** A two-part project that (a) predicts when satellites pass over Canberra and visualises it in a clean dashboard, and (b) optionally receives a real weather-satellite image with your own hardware. The portfolio outcome is a GitHub repo plus actual satellite imagery *you* captured.

**Target timeline:** Software-only version ~6 weeks at 5–8 hrs/week; add the receive leg for ~10–12 weeks total. A genuinely complete, presentable version exists much earlier than that.

**Why this fits you:** Software-leaning, no rocketry/explosives law, no launch-day dependency, and a fast path to a finished result. The orbital-mechanics and RF/DSP skills it builds map directly onto space-systems and ground-segment roles.

**Guiding principle:** The software half is a complete project on its own. The hardware half is the "wow" — a weather image of Australia you received yourself — but it's optional. Ship the predictor first.

---

## What "done" looks like at each level

| Level | What it does | Recruiter read |
|-------|-------------|----------------|
| MVP | Predicts upcoming passes of a chosen satellite over your location | "Understands orbital propagation & coordinate frames" |
| Solid | Plus an interactive dashboard: pass table, sky-track plot, live position map | "Can turn orbital data into a real tool" |
| Impressive | Plus a real decoded Meteor LRPT image captured with your own SDR, georeferenced | "Built an end-to-end ground station — serious space-systems signal" |

You do NOT need all three to land an internship. The "Solid" software version is already a strong piece.

---

## A note on the current satellite situation (read this first)

- The old **NOAA APT** satellites (NOAA-15, -18, -19) are all **decommissioned as of 2025** — APT is dead. Ignore any tutorial built around them (most older ones are).
- The current beginner target is **Meteor-M2 LRPT** (digital, ~137 MHz) — specifically **Meteor-M2-3 and Meteor-M2-4**.
- **Frequencies and modes for the Meteor satellites change fairly often** (e.g. 72k vs 80k LRPT modes, 137.1 vs 137.9 MHz). Always check current status the day of a pass — usradioguy.com and rtl-sdr.com track this.
- Other targets once you're comfortable: **ISS SSTV** (occasional event-based image broadcasts), and **GOES / L-band HRPT** (geostationary or higher-res, needs a dish — a stretch).

Calling out this obsolescence in your README is a feature, not a footnote: it shows judgment.

---

## Bill of materials (rough AUD)

Suppliers: Core Electronics, Little Bird Electronics.

**Software-only path: $0.** Everything in Phases 0–2 needs only a laptop and free software.

**Receive leg (optional, ~$50–110):**
- RTL-SDR Blog V4 starter kit (~$45–60) — includes the SDR dongle and a multipurpose telescopic dipole you configure as a 137 MHz V-dipole. This is the standard beginner recommendation.
- (Optional) 137 MHz SAW-filtered LNA (~$40) — worth it if you're in an RF-noisy area; cuts interference from FM stations. Try without it first.
- Coax (RG-58, keep it short) and a non-metallic mast/tripod — a few dollars / household items.
- A clear view of the sky (a balcony, backyard, or rooftop). Antenna placement matters more than the dongle.

---

## Phase 0 — Setup & first prediction (Week 1)

Pure software. Get one satellite's passes printing for your location.

- Set up a Python environment. Install **Skyfield** (modern, well-documented orbital library).
- Pull current **TLEs** (two-line element sets — the standard orbit format) from **Celestrak**.
- Compute the next several **ISS** passes over Canberra: rise time, set time, peak elevation, azimuth. (ISS is the easy first target — bright, frequent, well-known.)

**Milestone:** Run a script → see the next 5 ISS passes over your location with times and max elevation.

*Resources:* Skyfield documentation (Brandon Rhodes); Celestrak (TS Kelso) for TLEs.

---

## Phase 1 — Pass prediction engine (Weeks 2–3)

Generalise it into a real tool.

- Accept any satellite by name / NORAD catalog ID.
- For each pass compute AOS (acquisition of signal), LOS (loss of signal), max elevation, azimuth at peak, and duration.
- Filter for "good" passes (e.g. max elevation > 20–30°) — low passes give poor reception.
- Handle your local timezone correctly (AEST/AEDT) — a classic bug source.
- Add the currently-active weather satellites (Meteor-M2-3, M2-4) to your tracked list.

**Milestone:** Given a satellite + your location, output a clean, timezone-correct pass schedule.

*Concept to learn here (great interview material):* coordinate frames — how an orbit in an Earth-centered inertial frame becomes an azimuth/elevation "look angle" from your backyard. Understanding this transformation is what separates "used a library" from "understands the problem."

---

## Phase 2 — Visualization / dashboard (Weeks 4–6)

This is what makes it a *tool* rather than a script, and it's the most portfolio-visible part.

- Build an interactive dashboard. Fastest path for you: **Streamlit** (pure Python, no JavaScript needed). If you want stronger web cred, a **FastAPI + small JS frontend** is the upgrade path — mention that choice in your README.
- Core components:
  - Upcoming-pass table for your tracked satellites.
  - A **polar sky plot** showing the azimuth/elevation track of a selected pass (where to look in the sky).
  - A **live "where is it now" map** with the satellite's current position and ground track.
- Keep TLEs auto-refreshing from Celestrak so predictions stay accurate.

**Milestone:** An interactive dashboard showing live satellite positions and upcoming passes for Canberra.

*Resources:* Streamlit docs; Plotly (for the maps and polar plots).

---

## Phase 3 — The receive leg (Weeks 7–10) — the "wow"

Turn predictions into an actual image you captured.

- Get the RTL-SDR kit; build the V-dipole from the included antenna (two elements ~½ m each, set in a ~120° "V").
- Install **SatDump** (the modern all-in-one: it records, demodulates, decodes, tracks, and applies Doppler correction). Use a current build; the project updates very frequently.
- Use your own predictor (or SatDump's tracker) to catch a high-elevation **Meteor-M2 LRPT** pass. Check the current frequency/mode that day before you go outside.
- Decode the pass into an image.

**Milestone:** A decoded Meteor LRPT weather image — your own capture of Australia from space.

*Reality check:* your first pass may fail (noise, wrong gain, low elevation, wrong mode). That's normal — this is the part where persistence shows. Set gain manually (~25–30 dB to start), aim for passes above ~20° elevation, and start recording a couple of minutes before AOS.

*Resources:* SatDump (GitHub); the dereksgc YouTube satellite-reception series; usradioguy.com and rtl-sdr.com for current Meteor settings.

---

## Phase 4 — Integration & stretch (Weeks 10–12)

Pick what excites you; one done well beats three half-built.

- **Close the loop:** have your dashboard schedule/flag the best upcoming Meteor pass, then compare your *predicted* pass against the *actual* received signal timing.
- **Georeference your image:** overlay coastlines/borders on your captured image (SatDump can output map-projected products) and display it in your dashboard.
- **Doppler visualisation:** plot the frequency shift across a pass and explain it.
- **Expand targets:** catch an ISS SSTV event, or attempt GOES/L-band (needs a dish — genuinely advanced).

**Milestone:** An end-to-end "ground station" that predicts, captures, and displays imagery.

---

## Documentation & portfolio packaging (ongoing; final push at the end)

This is what converts the project into interviews.

- **GitHub repo** with a real README: what it does, screenshots of the dashboard, and a **gallery of weather images you received**.
- **Engineering-judgment section:** explicitly note that you targeted Meteor LRPT because the NOAA APT satellites are decommissioned — and link your sources. This single paragraph signals maturity.
- **Predicted-vs-actual** comparison for a real pass.
- **A short demo video / GIF** of the dashboard tracking a satellite and an image decoding.
- Optional: a write-up of one hard problem (timezone bug, coordinate transform, a failed pass you diagnosed).

---

## Legal & practical (Australia / ACT)

- **Receiving is legal and needs no license** — you only listen, never transmit. This sidesteps the entire rocketry/explosives issue that complicated the other project.
- General etiquette: these weather broadcasts are open and meant to be received. Don't rebroadcast or share the contents of communications that aren't intended for the public (not relevant to weather sats, but good practice).
- The only real constraints are physical: a clear sky view and local RF noise. An outdoor antenna beats an expensive receiver indoors every time.

---

## How this maps to what recruiters want

- **Orbital propagation, TLEs, coordinate frames (ECI → topocentric az/el)** → astrodynamics, mission operations, space systems.
- **SDR / RF / basic DSP (sampling, demodulation, Doppler)** → ground-segment and communications roles.
- **Python, APIs, data visualisation, a deployable dashboard** → universal across every aerospace team.
- **Working against the current real-world state of the constellation** → engineering judgment, the thing coursework rarely demonstrates.

---

## First three concrete steps

1. Set up a Python environment and install Skyfield; get the next ISS passes over Canberra printing today.
2. Create a GitHub repo now (even empty) and commit from day one so progress is visible.
3. Decide your dashboard stack (Streamlit for speed) and whether you'll do the receive leg — if yes, price an RTL-SDR Blog V4 kit at Core Electronics.
