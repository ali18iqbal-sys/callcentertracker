"""
target_page.py — Target Setup UI
"""

import streamlit as st
from datetime import date
from app.core.targets import (
    load_targets,
    save_targets,
    calculate_monthly_target,
)


def render():
    st.title("🎯 Target Setup")
    st.caption("Set daily call targets — monthly target will auto-calculate")
    
    st.divider()
    
    targets = load_targets()
    daily = targets.get("daily_targets", {})
    
    # ═══ MONTH SELECTOR ═══
    today = date.today()
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        year = st.number_input("Year", min_value=2024, max_value=2030, value=today.year, step=1)
    with col_m2:
        month = st.number_input("Month", min_value=1, max_value=12, value=today.month, step=1)
    
    st.divider()
    
    # ═══ DAILY TARGETS ═══
    st.subheader("📅 Daily Call Targets")
    st.caption("Define call target for each day type")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        weekday = st.number_input(
            "Weekday (Mon-Fri)",
            min_value=0, max_value=10000,
            value=int(daily.get("weekday", 500)),
            step=50,
        )
    with c2:
        saturday = st.number_input(
            "Saturday",
            min_value=0, max_value=10000,
            value=int(daily.get("saturday", 400)),
            step=50,
        )
    with c3:
        sunday = st.number_input(
            "Sunday",
            min_value=0, max_value=10000,
            value=int(daily.get("sunday", 200)),
            step=50,
        )
    with c4:
        holiday = st.number_input(
            "Holiday",
            min_value=0, max_value=10000,
            value=int(daily.get("holiday", 100)),
            step=50,
        )
    
    # ═══ AUTO CALCULATION ═══
    daily_targets = {
        "weekday": weekday,
        "saturday": saturday,
        "sunday": sunday,
        "holiday": holiday,
    }
    
    monthly = calculate_monthly_target(daily_targets, year=int(year), month=int(month))
    
    st.divider()
    st.subheader("📊 Monthly Target (Auto-Calculated)")
    
    # Breakdown table
    import pandas as pd
    breakdown = pd.DataFrame([
        {"Day Type": "Weekdays (Mon-Fri)", **monthly["weekdays"]},
        {"Day Type": "Saturdays",          **monthly["saturdays"]},
        {"Day Type": "Sundays",            **monthly["sundays"]},
        {"Day Type": "Holidays",           **monthly["holidays"]},
    ]).rename(columns={"days": "Days", "per_day": "Per Day", "total": "Total"})
    
    st.dataframe(breakdown, use_container_width=True, hide_index=True)
    
    # Total metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("📆 Total Days", monthly["days_in_month"])
    c2.metric("🎯 Monthly Target", f"{monthly['total_target']:,} calls")
    c3.metric("📊 Weighted Avg/Day", f"{monthly['weighted_avg']} calls")
    
    st.divider()
    
    # ═══ TEAM TARGETS ═══
    st.subheader("👥 Team-wise Targets (Optional)")
    st.caption("Leave empty if team-wise targets not required")
    
    team_targets = targets.get("team_targets", {}).copy()
    
    num_teams = st.number_input(
        "How many teams?",
        min_value=0, max_value=20,
        value=len(team_targets) if team_targets else 0,
        step=1,
        key="num_teams",
    )
    
    if num_teams > 0:
        cols = st.columns(min(num_teams, 3))
        new_team_targets = {}
        existing_teams = list(team_targets.keys())
        
        for i in range(num_teams):
            col = cols[i % 3]
            default_name = existing_teams[i] if i < len(existing_teams) else f"T{i+1}"
            default_val = team_targets.get(default_name, 0)
            
            with col:
                team_name = st.text_input(f"Team {i+1} naam", value=default_name, key=f"team_name_{i}")
                team_val = st.number_input(f"Team Target", min_value=0, value=int(default_val), step=50, key=f"team_val_{i}")
                if team_name:
                    new_team_targets[team_name] = team_val
        
        team_targets = new_team_targets
    
    st.divider()
    
    # ═══ DIALER TARGETS ═══
    st.subheader("📱 Dialer-wise Targets (Optional)")
    
    dialer_targets = targets.get("dialer_targets", {}).copy()
    
    num_dialers = st.number_input(
        "How many dialers?",
        min_value=0, max_value=30,
        value=len(dialer_targets) if dialer_targets else 0,
        step=1,
        key="num_dialers",
    )
    
    if num_dialers > 0:
        cols = st.columns(min(num_dialers, 3))
        new_dialer_targets = {}
        existing_dialers = list(dialer_targets.keys())
        
        for i in range(num_dialers):
            col = cols[i % 3]
            default_name = existing_dialers[i] if i < len(existing_dialers) else f"D{i+1}"
            default_val = dialer_targets.get(default_name, 0)
            
            with col:
                dialer_name = st.text_input(f"Dialer {i+1} naam", value=default_name, key=f"dialer_name_{i}")
                dialer_val = st.number_input(f"Dialer Target", min_value=0, value=int(default_val), step=50, key=f"dialer_val_{i}")
                if dialer_name:
                    new_dialer_targets[dialer_name] = dialer_val
        
        dialer_targets = new_dialer_targets
    
    st.divider()
    
    # ═══ SAVE BUTTON ═══
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("💾 Save All Targets", type="primary", use_container_width=True):
            new_targets = {
                "daily_targets": daily_targets,
                "team_targets": team_targets,
                "dialer_targets": dialer_targets,
            }
            save_targets(new_targets)
            st.success("✅ Targets saved successfully!")
            st.balloons()