# Open-Source Model Rocket Flight Computer — Build Plan

**Goal:** A finished, well-documented flight computer + analysis pipeline that records a real rocket flight and turns the raw data into clean engineering results. The portfolio outcome is a GitHub repo a recruiter can open and immediately understand.

**Target timeline:** ~16 weeks at 5–8 hrs/week (~4 months). Realistic for an early undergrad. Adjust freely — the phases matter more than the dates.

**Guiding principle:** Ship the smallest working version first, then layer ambition on top. A device that simply *logs and plots a flight* is already a complete project. Everything after that is upside.

---

## What "done" looks like at each level

| Level | What it does | Recruiter read |
|-------|-------------|----------------|
| MVP | Logs altitude + acceleration to a file during flight | "Can interface sensors and capture real data" |
| Solid | Plus a Python pipeline computing apogee, max velocity, max-G, with event detection | "Understands flight data analysis" |
| Impressive | Plus EITHER sensor-fusion state estimation OR live telemetry to a ground station | "Touches real GNC / comms — this is serious" |

You do **not** need all three to land an internship. A polished "Solid" beats a half-built "Impressive."

---

## Bill of materials (rough AUD, Australian suppliers)

Suppliers: Core Electronics, Little Bird Electronics, Pakronics. Buy MVP parts first; don't buy stretch-goal parts until you reach that phase.

**MVP core (~$60–90)**
- Raspberry Pi Pico 2 (RP2350) — ~$8–15. Cheap, beginner-friendly, runs MicroPython.
- Barometer: BMP280 (~$8) to start, or BMP390 (~$25–30) for better altitude resolution.
- IMU: MPU-6050 (~$10) is fine for MVP. (BNO055 ~$50 does onboard fusion — tempting, but doing fusion yourself teaches more; consider it only as a stretch.)
- microSD breakout (~$6) OR just use the Pico's onboard flash for the MVP.
- Power: small LiPo + TP4056 USB charger (~$12 total), or a simple AA/9V pack to start.
- Breadboard, jumper wires, header pins (~$15–20).

**Stretch add-ons (only if you go there)**
- 2× RFM95W LoRa breakouts (~$20 each) for telemetry + ground station.
- Perfboard / protoboard to solder a flight-hardened version (~$5).

**Rocketry (~$70–110)**
- Estes beginner kit (~$40–60) + launch gear, OR use club launch gear (recommended).
- Motors: bought through your club once you're a member (see Safety & Legal).

---

## Phase 0 — Setup & first sensor read (Weeks 1–2)

Get the toolchain working and prove you can talk to a sensor. This is where most beginners stall, so keep the win small.

- Flash MicroPython onto the Pico; get an LED blinking from your editor (Thonny).
- Wire up the barometer over I2C and print a pressure reading.
- Convert pressure → altitude using the barometric formula; sanity-check by walking up a flight of stairs.

**Milestone:** Terminal prints live altitude that changes when you move the board vertically.

*Resources:* "Get Started with MicroPython on Raspberry Pi Pico" (official Raspberry Pi book), the Core Electronics Pico tutorials, your sensor's datasheet (learn to read these early — it's a real engineering skill).

---

## Phase 1 — Logging MVP (Weeks 3–5)

Make it record a flight to a file, untethered from your laptop.

- Add the IMU; read acceleration and angular rate.
- Combine sensors into a timestamped log line (time, pressure/altitude, accel x/y/z).
- Write the log to onboard flash or microSD at a fixed rate (start ~50 Hz).
- Add a simple "armed" state: button or power-on delay, an LED status, and a clean file-per-flight scheme.
- Bench-test "flights": drop tests onto a cushion, elevator rides, swinging it on a string.

**Milestone:** Power it on, do a test motion, power off, and pull a complete data file off the device.

---

## Phase 2 — Analysis pipeline (Weeks 6–8)

This is the half that makes it look like *aerospace* rather than a gadget.

- Python script (NumPy + Matplotlib) that parses your log file.
- Plot altitude, acceleration, and derived velocity vs. time.
- Compute key flight metrics: apogee, max velocity, max-G, time-to-apogee.
- Velocity two ways and compare: integrate acceleration vs. differentiate altitude. Discuss why they disagree (drift vs. noise) — that discussion is gold in an interview.
- Auto-detect flight events: liftoff (accel spike), burnout, apogee (velocity zero-crossing / altitude peak), landing.

**Milestone:** Run one command on a data file → get a labelled flight plot and a printed summary.

*Resources:* NumPy/Matplotlib docs; the free "Python Data Science Handbook" (VanderPlas). Use OpenRocket (free) to simulate your rocket+motor and predict apogee — a great independent check against what your device measured.

---

## Phase 3 — First real flight (Weeks 9–11)

- Join a club (see Safety & Legal) and attend a launch day.
- Build/finish a rocket with a payload bay big enough for your board + battery.
- Fly a low-power motor (A–C to start), recover, and pull the data.
- Run your pipeline on real flight data. Expect surprises — vibration, the parachute-deploy jolt, sensor saturation. Document them.

**Milestone:** A real flight plot with annotated liftoff, apogee, and landing, cross-checked against your OpenRocket prediction.

---

## Phase 4 — Pick ONE stretch goal (Weeks 12–16)

Choose the one that excites you more. Doing one well beats starting both.

**Option A — State estimation (the GNC path).**
Fuse barometer + accelerometer for a better altitude/velocity estimate than either alone.
- Start with a complementary filter (a weighted blend — surprisingly effective and easy to grasp).
- Then implement a 1-D Kalman filter for altitude/velocity. This is *the* signal that you understand the maths behind navigation.
- *Resources:* "Kalman and Bayesian Filters in Python" (rlabbe, free on GitHub) — the best beginner Kalman resource that exists.

**Option B — Telemetry + ground station (the comms path).**
Downlink live data so you can watch the flight in real time.
- Add a LoRa radio to the rocket and a second one on a receiver hooked to your laptop.
- Build a live dashboard (Python + a simple plotting loop) showing altitude/velocity during flight.
- Handle dropped packets gracefully — radios are noisy, and showing you thought about that is the point.

**Milestone:** Either a filtered apogee estimate noticeably cleaner than raw data (A), or a live flight you watched on a dashboard (B).

---

## Documentation & portfolio packaging (ongoing; final push Weeks 15–16)

This is what actually converts the project into interviews — treat it as a deliverable, not an afterthought.

- **GitHub repo** with a real README: what it does, a photo/GIF of it working, the wiring, the BOM, how to run it.
- **Engineering decisions section:** why this sensor, why this filter, what you'd do differently. Recruiters read *judgment*, not just code.
- **Results:** your real flight plots, the apogee number, the OpenRocket comparison.
- **A 60–90s demo video** of a flight and the resulting plot. This single thing dramatically raises response rates.
- Optional: a short write-up / blog post telling the story of one hard bug you fixed.

---

## Safety & Legal (ACT-based — read before buying motors)

- **The whole build is fine to do at home in the ACT.** Phases 0–3 (firmware, wiring, bench testing, analysis) involve no motors, so there's no legal constraint on any of it. Only the powered launch is affected.
- **Motors are the catch in the ACT:** there are currently no authorised rocket motors in the ACT, so possessing/storing/transporting them at home is effectively illegal. Don't buy or keep motors in the ACT.
- **The fix is the local club.** The Canberra Rocketry Group (CRG) is built for ACT flyers but launches in NSW: low/medium-power launches run the first Sunday of each month at Yass, NSW (~1 hr from Canberra); high-power at Ardlethan, NSW. Most members are Canberra-based.
- **At a NSW launch,** motors up to ~62.5 g propellant (≈ "G" class, ≤ ~320 Ns) need no individual permit — plenty for this project. Stay low-power (A–G).
- **Sort motors through the club and use them at the NSW site** rather than bringing them back across the border. Confirm the exact current arrangement with CRG when you join — their range officers handle this routinely.
- **Under 18:** you may not be able to buy motors directly; the club / guardian route solves this.
- Your board is a passive data logger, not a flight controller that triggers anything. Keep it that way until you're experienced — don't wire it to ejection charges.

---

## How this maps to what recruiters want

- **I2C/SPI sensor interfacing** → embedded systems roles.
- **Sensor fusion / Kalman filtering** → guidance, navigation & control (GNC).
- **Flight data analysis & signal processing** → flight test / data roles.
- **Python, NumPy, Matplotlib, Git** → universal across every aerospace team.
- **Spotting a market gap and finishing a real build** → the maturity signal that separates you from coursework-only applicants.

---

## First three concrete steps

1. Order the MVP parts (Pico + BMP280 + MPU-6050 + breadboard).
2. Look up the Canberra Rocketry Group, note their first-Sunday Yass launch, and email them about joining as an ACT-based beginner.
3. Set up a GitHub repo *today*, even empty — commit from day one so your progress is visible.
