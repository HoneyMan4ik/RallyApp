import os
import random
import pandas as pd
import streamlit as st
import snowflake.connector


st.set_page_config(page_title="Bootcamp Rally", layout="centered")
st.title("Bootcamp Rally")


def _read_creds():
    try:
        return {
            "account": st.secrets.get("SNOWFLAKE_ACCOUNT", ""),
            "user": st.secrets.get("SNOWFLAKE_USER", ""),
            "password": st.secrets.get("SNOWFLAKE_PASSWORD", ""),
            "role": st.secrets.get("SNOWFLAKE_ROLE", ""),
            "warehouse": st.secrets.get("SNOWFLAKE_WAREHOUSE", ""),
            "database": st.secrets.get("SNOWFLAKE_DATABASE", "BOOTCAMP_RALLY"),
            "schema": st.secrets.get("SNOWFLAKE_SCHEMA", "APP"),
            "host": st.secrets.get("SNOWFLAKE_HOST", ""),
        }
    except Exception:
        pass

    return {
        "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
        "user": os.getenv("SNOWFLAKE_USER", ""),
        "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
        "role": os.getenv("SNOWFLAKE_ROLE", ""),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", ""),
        "database": os.getenv("SNOWFLAKE_DATABASE", "BOOTCAMP_RALLY"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "APP"),
        "host": os.getenv("SNOWFLAKE_HOST", ""),
    }


def get_conn():
    c = _read_creds()
    kwargs = dict(
        user=c.get("user"),
        password=c.get("password"),
        role=(c.get("role") or None),
        warehouse=(c.get("warehouse") or None),
        database=(c.get("database") or "BOOTCAMP_RALLY"),
        schema=(c.get("schema") or "APP"),
        autocommit=True,
    )
    host = (c.get("host") or "").strip()
    if host:
        kwargs["host"] = host
    else:
        kwargs["account"] = c.get("account")
    return snowflake.connector.connect(**kwargs)

def sql(query: str, params: tuple | None = None) -> pd.DataFrame | None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if query.strip().lower().startswith("select"):
            cols = [c[0] for c in cur.description]
            return pd.DataFrame([dict(zip(cols, r)) for r in cur.fetchall()])
        return None

def load_teams() -> pd.DataFrame:
    return sql("SELECT TEAM_ID, TEAM_NAME, MEMBERS, BUDGET FROM APP.TEAMS ORDER BY TEAM_ID")

def load_cars() -> pd.DataFrame:
    return sql(
        """
        SELECT c.CAR_ID, c.CAR_NAME, c.TEAM_ID, t.TEAM_NAME,
               c.MAX_SPEED, c.ACCELERATION, c.HANDLING, c.RELIABILITY
        FROM APP.CARS c JOIN APP.TEAMS t ON c.TEAM_ID = t.TEAM_ID
        ORDER BY c.CAR_ID
        """
    )

creds_now = _read_creds()
READY = bool((creds_now.get("host") or creds_now.get("account")) and creds_now.get("user") and creds_now.get("password"))
if not READY:
    st.info("Set Snowflake credentials via environment variables or Streamlit secrets. Required: SNOWFLAKE_HOST or SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD. Optional: SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA.")
    st.stop()

st.subheader("Teams")
col1, col2, col3 = st.columns(3)
with col1:
    team_name = st.text_input("Team name")
with col2:
    members = st.text_input("Members (comma separated)")
with col3:
    budget = st.number_input("Starting budget", min_value=0.0, value=5000.0, step=500.0)

if st.button("Add Team") and team_name:
    try:
        sql("INSERT INTO APP.TEAMS (TEAM_NAME, MEMBERS, BUDGET) VALUES (%s, %s, %s)", (team_name, members, float(budget)))
        st.success("Team added")
    except Exception as e:
        st.error(str(e))
st.dataframe(load_teams())

st.subheader("Cars")
teams_df = load_teams()
team_map = {f"{r.TEAM_NAME} (#{int(r.TEAM_ID)})": int(r.TEAM_ID) for _, r in teams_df.iterrows()} if not teams_df.empty else {}

car_name = st.text_input("Car name")
team_choice = st.selectbox("Assign to team", list(team_map.keys()) or ["No teams yet"])

cc1, cc2, cc3, cc4 = st.columns(4)
with cc1:
    max_speed = st.number_input("Max speed", min_value=120.0, max_value=400.0, value=230.0)
with cc2:
    acc = st.number_input("Acceleration", min_value=1.0, max_value=100.0, value=85.0)
with cc3:
    handling = st.number_input("Handling", min_value=1.0, max_value=100.0, value=80.0)
with cc4:
    reliability = st.number_input("Reliability", min_value=1.0, max_value=100.0, value=90.0)

if st.button("Add Car") and team_map:
    try:
        sql(
            "INSERT INTO APP.CARS (TEAM_ID, CAR_NAME, MAX_SPEED, ACCELERATION, HANDLING, RELIABILITY) VALUES (%s,%s,%s,%s,%s,%s)",
            (team_map.get(team_choice, 0), car_name, float(max_speed), float(acc), float(handling), float(reliability)),
        )
        st.success("Car added")
    except Exception as e:
        st.error(str(e))
st.dataframe(load_cars())

st.subheader("Start Race")
distance_km = st.number_input("Distance (km)", min_value=10.0, max_value=1000.0, value=100.0)
fee = st.number_input("Participation fee (USD)", min_value=0.0, value=1000.0)


def simulate_time(dist: float, vmax: float, a: float, h: float, r: float) -> float:
    base_speed = vmax * (0.6 + 0.4 * (a / 100))
    control = 1 + (h - 50) / 300
    rel = 1 + (50 - r) / 250
    noise = random.uniform(0.96, 1.04)
    hours = (dist / max(base_speed, 1.0)) * rel / max(control, 0.7)
    return hours * 3600 * noise


if st.button("Start race!"):
    cars = load_cars()
    teams = load_teams().set_index("TEAM_ID")

    if cars.empty:
        st.warning("No cars to race.")
    else:
        budgets = dict(zip(teams.index.astype(int), teams.BUDGET.astype(float)))
        participants = []
        for _, row in cars.iterrows():
            tid = int(row.TEAM_ID)
            if budgets.get(tid, 0.0) >= float(fee):
                budgets[tid] -= float(fee)
                participants.append((int(row.CAR_ID), tid))

        if not participants:
            st.warning("No team can afford the fee.")
        else:
            prize_pool = float(fee) * len(participants)
            results = []
            for car_id, team_id in participants:
                car = cars[cars.CAR_ID == car_id].iloc[0]
                t = simulate_time(distance_km, float(car.MAX_SPEED), float(car.ACCELERATION), float(car.HANDLING), float(car.RELIABILITY))
                results.append((car_id, team_id, t))

            results.sort(key=lambda x: x[2])

            payouts = [0.60, 0.30, 0.10]
            table = []
            for pos, (car_id, team_id, t) in enumerate(results, start=1):
                payout = prize_pool * (payouts[pos - 1] if pos <= 3 else 0.0)
                budgets[team_id] += payout
                car_name = cars.loc[cars.CAR_ID == car_id, "CAR_NAME"].values[0]
                team_name = teams.loc[team_id, "TEAM_NAME"]
                table.append({"Position": pos, "Car": car_name, "Team": team_name, "Time (s)": round(t, 2), "Payout": round(payout, 2)})

            for team_id, new_budget in budgets.items():
                sql("UPDATE APP.TEAMS SET BUDGET = %s WHERE TEAM_ID = %s", (float(new_budget), int(team_id)))

            st.success("Race finished!")
            st.dataframe(pd.DataFrame(table))

