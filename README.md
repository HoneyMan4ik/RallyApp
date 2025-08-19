## Bootcamp Rally Racing Management App (Snowflake + Python + Streamlit)

This project implements a simple management and race simulation app that connects to a Snowflake data warehouse.

### What you get
- A tiny Streamlit app that connects to your Snowflake and lets you:
  - Add teams and cars
  - Run a simple 100km race that charges a fee and pays prizes to top 3
  - Budgets update in the `TEAMS` table

### Quickstart

1) Python setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) Set credentials

Copy `env.example` to `.env` (or load variables in your shell):

```bash
cp env.example .env
```

Fill in your Snowflake values. If deploying to Streamlit Cloud, you can instead use a `secrets.toml` with the same keys.

3) Run the app

```bash
streamlit run app/app.py
```

Open the provided URL. In this simplified app you can add teams/cars and run a single 100km race that updates team budgets. That's it.

### Snowflake objects (you already created these)
- Database: `BOOTCAMP_RALLY`; Schema: `APP`
- Tables used by the app: `TEAMS`, `CARS`

### Simulation rules (simplified)
- All cars with teams and sufficient budget join the race
- Each car pays the participation fee from its team budget
- Results depend on car characteristics with small randomness
- Prize pool = fee × number_of_entries; Payout split: 1st 60%, 2nd 30%, 3rd 10%
- Budgets are updated; races and results are persisted

### Tip
If you deploy or share, prefer setting credentials via Streamlit `secrets`.


