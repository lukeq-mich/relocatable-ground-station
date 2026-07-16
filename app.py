"""
app.py — Streamlit dashboard for the relocatable satellite ground station.

Run:
    streamlit run app.py

Two modes, switched in the sidebar:
  Pass prediction        pick a station and satellites; see where they are now,
                         upcoming passes, and a sky-view of any pass.
  Conjunction screening  screen tracked objects + debris for close approaches.
All prediction logic lives in predictor.py; screening in conjunctions.py.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import conjunctions as C
import predictor as P

st.set_page_config(page_title="Ground Station", page_icon="🛰️", layout="wide")


# --- Load satellites once per hour (TLEs refresh ~daily anyway)
@st.cache_resource(ttl=3600)
def get_satellites():
    return P.load_satellites()


@st.cache_resource(ttl=3600)
def get_screening_set(extra: tuple[int, ...]):
    return C.load_screening_set(extra)


# Screening takes a few seconds; cache on the inputs that actually change the
# result (window, threshold, and which TLEs — via their epochs — were used).
@st.cache_data(ttl=3600, show_spinner="Screening all object pairs…")
def run_screen(_sats, tle_fingerprint, hours, threshold_km):
    return C.screen(_sats, hours=hours, threshold_km=threshold_km)


# --- Sidebar controls
st.sidebar.title("🛰️ Ground Station")
mode = st.sidebar.radio("Mode", ["Pass prediction", "Conjunction screening"])


# --- Conjunction screening view (engine in conjunctions.py)
if mode == "Conjunction screening":
    hours = st.sidebar.slider("Screening window (hours)", 12, 96, int(C.WINDOW_HOURS),
                              help="How far ahead to propagate. TLE error grows by "
                                   "~km/day, so much beyond 72 h the geometry is noise.")
    threshold = st.sidebar.slider("Miss-distance threshold (km)", 1.0, 50.0,
                                  C.THRESHOLD_KM, step=0.5,
                                  help="Flag pairs that come closer than this. "
                                       "TLE positions are only good to ~1 km.")
    extra_raw = st.sidebar.text_input("Extra NORAD IDs (comma-separated)", "",
                                      help="Screen additional objects — find catalog "
                                           "numbers at celestrak.org.")
    if st.sidebar.button("🔄 Refresh data"):
        get_screening_set.clear()
        run_screen.clear()
        st.rerun()

    extra, bad = [], []
    for tok in extra_raw.replace(";", ",").split(","):
        tok = tok.strip()
        if tok.isdigit():
            extra.append(int(tok))
        elif tok:
            bad.append(tok)
    if bad:
        st.sidebar.warning("Ignored (not NORAD numbers): " + ", ".join(bad))

    sats, failed = get_screening_set(tuple(sorted(set(extra))))
    if failed:
        st.sidebar.warning("Couldn't load: " + ", ".join(failed) +
                           " — objects decay or drop out of the catalog; "
                           "verify IDs at celestrak.org.")
    if len(sats) < 2:
        st.error("Fewer than two objects loaded — nothing to screen. "
                 "Check your connection, then Refresh.")
        st.stop()

    st.title("Conjunction screening")
    st.caption(f"{len(sats)} objects · all-pairs geometric screen over the next "
               f"{hours} h · flagging approaches under {threshold:g} km. "
               f"This is TLE-based screening, **not** collision-probability "
               f"analysis — see Methodology below.")

    # TLE freshness — screening is only as good as its inputs, so this is
    # always shown, never assumed.
    st.subheader("TLE freshness")
    status = C.tle_status(sats)
    df_tle = pd.DataFrame([{
        "Object": r["label"],
        "NORAD": r["norad"],
        "Epoch (UTC)": r["epoch_utc"].strftime("%Y-%m-%d %H:%M"),
        "Age (days)": round(r["age_days"], 1),
    } for r in status]).sort_values("Age (days)", ascending=False)
    st.dataframe(df_tle, use_container_width=True, hide_index=True)
    oldest = max(r["age_days"] for r in status)
    if oldest > 7:
        st.warning(f"Oldest TLE is {oldest:.1f} days old — position error grows "
                   f"by roughly a km or more per day past epoch, so treat miss "
                   f"distances from stale TLEs as order-of-magnitude only.")

    # --- Events table
    st.subheader("Conjunction events")
    fingerprint = tuple(sorted((s.model.satnum, s.epoch.tt) for s in sats.values()))
    events = run_screen(sats, fingerprint, float(hours), float(threshold))

    if not events:
        st.info(f"No pair comes within {threshold:g} km in the next {hours} h. "
                "With a small curated object set that is the expected result — "
                "operational screens run against the full ~30 000-object catalog. "
                "Raise the threshold or add objects to see the pipeline fire.")
    else:
        sort_by = st.radio("Sort by", ["Miss distance", "Time of closest approach"],
                           horizontal=True)
        show = sorted(events, key=lambda e: e.tca) \
            if sort_by == "Time of closest approach" else events
        df_ev = pd.DataFrame([{
            "Pair": e.pair,
            "TCA (UTC)": e.tca.strftime("%a %d %b %H:%M:%S"),
            "Miss distance (km)": round(e.miss_km, 2),
            "Relative speed (km/s)": round(e.rel_speed_km_s, 2),
        } for e in show])
        st.dataframe(df_ev, use_container_width=True, hide_index=True)

        # --- Relative motion around a selected event
        st.subheader("Encounter geometry")
        labels = [f"{e.pair} · {e.tca:%a %d %b %H:%M:%S} UTC · {e.miss_km:.2f} km"
                  for e in show]
        idx = st.selectbox("Choose an event", range(len(show)),
                           format_func=lambda i: labels[i])
        ev = show[idx]
        g = C.encounter_geometry(sats[ev.obj1], sats[ev.obj2], ev.tca_jd_tt)
        mid = len(g["offset_s"]) // 2

        col_sep, col_rel = st.columns(2)
        with col_sep:
            fig_sep = go.Figure()
            fig_sep.add_trace(go.Scatter(x=g["offset_s"] / 60.0, y=g["sep_km"],
                                         mode="lines", line=dict(width=2)))
            fig_sep.add_trace(go.Scatter(
                x=[0], y=[ev.miss_km], mode="markers+text",
                text=["TCA"], textposition="top center",
                marker=dict(size=11, color="#ff6a00")))
            fig_sep.update_layout(
                height=430, margin=dict(l=0, r=0, t=30, b=0), showlegend=False,
                title="Separation vs time", xaxis_title="minutes from TCA",
                yaxis_title="separation (km)", yaxis_type="log")
            st.plotly_chart(fig_sep, use_container_width=True)
        with col_rel:
            fig_rel = go.Figure()
            fig_rel.add_trace(go.Scatter3d(
                x=g["y_km"], y=g["x_km"], z=g["z_km"],
                mode="lines", line=dict(width=4), name=ev.obj2))
            fig_rel.add_trace(go.Scatter3d(
                x=[g["y_km"][mid]], y=[g["x_km"][mid]], z=[g["z_km"][mid]],
                mode="markers+text", text=["TCA"], textposition="top center",
                marker=dict(size=6, color="#ff6a00")))
            fig_rel.add_trace(go.Scatter3d(
                x=[0], y=[0], z=[0], mode="markers+text",
                text=[ev.obj1], textposition="bottom center",
                marker=dict(size=5, symbol="diamond")))
            fig_rel.update_layout(
                height=430, margin=dict(l=0, r=0, t=30, b=0), showlegend=False,
                title=f"{ev.obj2} relative to {ev.obj1}",
                scene=dict(xaxis_title="along relative velocity (km)",
                           yaxis_title="miss direction (km)",
                           zaxis_title="out of plane (km)",
                           aspectmode="cube"))
            st.plotly_chart(fig_rel, use_container_width=True)
        st.caption(f"Frame is centred on {ev.obj1} and fixed at TCA. Note the axes "
                   f"are not to equal scale: the fly-by spans thousands of km along "
                   f"the relative velocity, while the miss distance is "
                   f"{ev.miss_km:.2f} km at {ev.rel_speed_km_s:.1f} km/s.")

    # --- Methodology & limitations — the honest part; always shown.
    st.subheader("Methodology & limitations")
    st.markdown("""
**What this does.** All loaded objects are propagated with SGP4 from CelesTrak
TLEs over the screening window. Every pair whose radial shells (perigee–apogee,
+150 km margin) overlap is sampled on a 60 s grid; each local minimum of the
pairwise separation is kept if it could possibly dip under the threshold
(sampled minimum < threshold + v·Δt/2 — near TCA, separation is locally
√(d² + v²t²), so a coarse sample overstates the true minimum by at most
v·Δt/2), then refined by bounded Brent minimization to sub-millisecond TCA.
Close approaches **between** grid samples are therefore not missed; the grid
only brackets, it never decides.

**What this does not do.** This is *geometric screening on TLEs*, not
conjunction assessment:

- **TLE accuracy** — TLE/SGP4 state vectors carry position errors of order
  1 km at epoch, growing roughly km/day (worse at low altitude and around high
  solar activity). A reported 3 km miss is statistically indistinguishable
  from 0 km, or from 8 km. TLE ages are shown above for exactly this reason.
- **No covariance, no collision probability.** Operational SSA (CSpOC, ESA,
  commercial providers) propagates full state covariance and computes a
  probability of collision (Pc) via Foster, Alfano, or similar methods, using
  owner/operator ephemerides far more accurate than TLEs. Nothing here
  estimates Pc, and no output of this tool should be read as one.
- **No maneuvers** — a station-keeping burn or avoidance maneuver invalidates
  a TLE immediately; SGP4 extrapolates the pre-burn orbit without complaint.
- **Catalog coverage** — only the objects listed above are screened
  (configurable, ~a dozen by default). The tracked catalog is ~30 000 objects;
  absence of an event here says nothing about the real environment.
- **Assumptions** — 72 h default window (bounded by TLE error growth), 5 km
  default threshold (demo-scale; operational screening volumes differ by
  regime and are defined in Pc or radial/in-track/cross-track terms, not a
  single sphere).

**Bottom line:** an event flagged here means "two cataloged orbits pass close
enough to be worth a look with better data" — never "collision predicted".
A clean screen certifies nothing.
""")
    st.stop()


station = st.sidebar.selectbox("Location", list(P.STATIONS.keys()))

sats_all, failed = get_satellites()
if failed:
    st.sidebar.warning("Couldn't load: " + ", ".join(failed) +
                       " (check the NORAD IDs or your connection).")
if not sats_all:
    st.error("No satellites loaded — check your internet connection, then Refresh.")
    st.stop()

chosen = st.sidebar.multiselect("Satellites", list(sats_all.keys()),
                                default=list(sats_all.keys()))
days = st.sidebar.slider("Days ahead", 1, 7, 3)
min_elev = st.sidebar.slider("Min peak elevation (°)", 0, 60, 25,
                             help="Higher passes give better reception. ~25° is a good target.")
if st.sidebar.button("🔄 Refresh data"):
    get_satellites.clear()
    st.rerun()

sats = {k: v for k, v in sats_all.items() if k in chosen}

s = P.STATIONS[station]
st.title(f"Passes over {station}")
st.caption(f"{s['lat']:.3f}, {s['lon']:.3f} · {s['tz']} · tracking {len(sats)} satellite(s)")

if sats:
    ages = [f"{lbl}: {P.tle_age_days(sat):+.1f}d" for lbl, sat in sats.items()]
    st.caption("TLE age — " + " · ".join(ages) +
               "  (refresh if any are more than a few days old)")


# --- Live positions map
st.subheader("Where they are now")

fig_map = go.Figure()
# station marker
fig_map.add_trace(go.Scattergeo(
    lon=[s["lon"]], lat=[s["lat"]], mode="markers+text",
    text=[station], textposition="top center",
    marker=dict(size=9, symbol="star", color="#ff6a00"), name=station,
))
for lbl, sat in sats.items():
    gt = P.ground_track(sat)
    fig_map.add_trace(go.Scattergeo(
        lon=gt["lon"], lat=gt["lat"], mode="lines",
        line=dict(width=1, dash="dot"), name=f"{lbl} track", showlegend=False,
    ))
    cp = P.current_position(sat)
    fig_map.add_trace(go.Scattergeo(
        lon=[cp["lon"]], lat=[cp["lat"]], mode="markers+text",
        text=[lbl], textposition="top center",
        marker=dict(size=8), name=lbl,
    ))
fig_map.update_layout(
    height=430, margin=dict(l=0, r=0, t=10, b=0),
    geo=dict(projection_type="natural earth", showland=True,
             landcolor="#1e2a1e", oceancolor="#0c1622", showocean=True,
             showcountries=True, countrycolor="#33475b", bgcolor="rgba(0,0,0,0)"),
    legend=dict(orientation="h", y=-0.05),
)
st.plotly_chart(fig_map, use_container_width=True)


# --- Upcoming passes table
st.subheader("Upcoming passes")

passes = P.upcoming_passes(sats, station, days=days, min_elevation=min_elev)
if not passes:
    st.info("No passes above the elevation threshold in this window. "
            "Try more days or a lower threshold.")
else:
    df = pd.DataFrame([{
        "Satellite": p.satellite,
        "Date": p.rise.strftime("%a %d %b"),
        "Rise": p.rise.strftime("%H:%M"),
        "Peak": p.peak.strftime("%H:%M"),
        "Set": p.set.strftime("%H:%M"),
        "Peak elev": f"{p.peak_elevation:.0f}°",
        "Look": p.peak_direction,
        "Duration": f"{p.duration_min:.0f} min",
    } for p in passes])
    st.dataframe(df, use_container_width=True, hide_index=True)


# --- Sky view of a selected pass
st.subheader("Sky view — where to point")

if passes:
    labels = [f"{p.satellite} · {p.rise:%a %H:%M} · peak {p.peak_elevation:.0f}° {p.peak_direction}"
              for p in passes]
    idx = st.selectbox("Choose a pass", range(len(passes)), format_func=lambda i: labels[i])
    p = passes[idx]

    # Sky plot: N at top, clockwise; zenith (90°) at centre, horizon (0°) at edge.
    r = [90 - e for e in p.track_el]          # radius = 90 - elevation
    fig_sky = go.Figure()
    fig_sky.add_trace(go.Scatterpolar(
        r=r, theta=p.track_az, mode="lines+markers",
        line=dict(width=2), name="track",
    ))
    fig_sky.add_trace(go.Scatterpolar(
        r=[90 - p.peak_elevation], theta=[p.peak_azimuth], mode="markers+text",
        text=["peak"], textposition="top center",
        marker=dict(size=11, color="#ff6a00"), name="peak",
    ))
    fig_sky.update_layout(
        height=430, margin=dict(l=40, r=40, t=20, b=20), showlegend=False,
        polar=dict(
            angularaxis=dict(rotation=90, direction="clockwise",
                             tickmode="array",
                             tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                             ticktext=["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            radialaxis=dict(range=[0, 90], tickmode="array",
                            tickvals=[0, 30, 60, 90],
                            ticktext=["90°", "60°", "30°", "0°"]),
        ),
    )
    st.plotly_chart(fig_sky, use_container_width=True)
    st.caption(f"Centre = straight up (90°), edge = horizon (0°). "
               f"This pass peaks at {p.peak_elevation:.0f}° to the {p.peak_direction}.")
