"""
app.py — Streamlit dashboard for the relocatable satellite ground station.

Run:
    streamlit run app.py

Pick a station and satellites in the sidebar. See where the satellites are now,
the upcoming passes for that location, and a sky-view of any pass (where to point).
All prediction logic lives in predictor.py.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import predictor as P

st.set_page_config(page_title="Ground Station", page_icon="🛰️", layout="wide")


# --- Load satellites once per hour (TLEs refresh ~daily anyway) 
@st.cache_resource(ttl=3600)
def get_satellites():
    return P.load_satellites()


# --- Sidebar controls 
st.sidebar.title("🛰️ Ground Station")
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
