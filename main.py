import os
import sqlite3
from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

DB_PATH = os.path.join(os.path.dirname(__file__), "finance.db")

app = FastAPI(title="Home Finance & Utilities Hub", version="1.0.0")

# Standard Utility Tariffs (Configurable defaults)
TARIFFS = {
    "elec_day": 5.40,    # руб / кВт⋅ч
    "elec_night": 2.80,  # руб / кВт⋅ч
    "cold_water": 45.20, # руб / м³
    "hot_water": 195.50, # руб / м³
    "gas": 7.80,         # руб / м³
    "internet": 650.0,   # руб фиксированный
    "heating": 2100.0    # руб фиксированный
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utility_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_month TEXT NOT NULL UNIQUE, -- YYYY-MM
            elec_day_val REAL NOT NULL,
            elec_night_val REAL NOT NULL,
            cold_water_val REAL NOT NULL,
            hot_water_val REAL NOT NULL,
            gas_val REAL NOT NULL,
            elec_day_cost REAL NOT NULL,
            elec_night_cost REAL NOT NULL,
            cold_water_cost REAL NOT NULL,
            hot_water_cost REAL NOT NULL,
            gas_cost REAL NOT NULL,
            fixed_internet REAL NOT NULL,
            fixed_heating REAL NOT NULL,
            total_bill REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL, -- EXPENSE or INCOME
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            tx_date TEXT NOT NULL, -- YYYY-MM-DD
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL NOT NULL DEFAULT 0.0,
            deadline_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed initial sample data if empty
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] == 0:
        txs = [
            ("INCOME", "Зарплата / Фриланс", 145000.0, "Основной доход", "2026-11-05"),
            ("EXPENSE", "Продукты питания", 8450.0, "Закупка в гипермаркете на неделю", "2026-11-07"),
            ("EXPENSE", "Железо сервера", 12400.0, "ECC DDR4 64GB для HP ProLiant DL360", "2026-11-10"),
            ("EXPENSE", "Коммунальные услуги", 6850.0, "Оплата квитанции за прошлый месяц", "2026-11-12"),
            ("EXPENSE", "Здоровье и аптека", 2150.0, "Витамины и лекарства", "2026-11-14"),
            ("EXPENSE", "Транспорт и бензин", 3200.0, "Заправка АИ-95", "2026-11-16")
        ]
        cursor.executemany("INSERT INTO transactions (type, category, amount, note, tx_date) VALUES (?, ?, ?, ?, ?)", txs)

        goals = [
            ("HP ProLiant DL360 Gen9 10GbE SFP+ Upgrade", 28000.0, 19500.0, "2026-12-31"),
            ("NVMe SSD Enterprise Cache Array (2TB)", 35000.0, 14000.0, "2027-02-15"),
            ("Резервный фонд семьи (Подушка безопасности)", 150000.0, 95000.0, "2027-06-01")
        ]
        cursor.executemany("INSERT INTO savings_goals (title, target_amount, current_amount, deadline_date) VALUES (?, ?, ?, ?)", goals)

        # Baseline utility reading for previous month
        cursor.execute("""
            INSERT INTO utility_readings (
                period_month, elec_day_val, elec_night_val, cold_water_val, hot_water_val, gas_val,
                elec_day_cost, elec_night_cost, cold_water_cost, hot_water_cost, gas_cost,
                fixed_internet, fixed_heating, total_bill
            ) VALUES ('2026-10', 1420.0, 680.0, 115.0, 64.0, 210.0, 810.0, 336.0, 361.6, 782.0, 78.0, 650.0, 2100.0, 5117.6)
        """)

    conn.commit()
    conn.close()

init_db()

class UtilityReadingCreate(BaseModel):
    period_month: str # YYYY-MM
    elec_day_val: float
    elec_night_val: float
    cold_water_val: float
    hot_water_val: float
    gas_val: float

class TransactionCreate(BaseModel):
    type: str # EXPENSE or INCOME
    category: str
    amount: float
    note: Optional[str] = ""
    tx_date: str # YYYY-MM-DD

class GoalCreate(BaseModel):
    title: str
    target_amount: float
    deadline_date: Optional[str] = ""

class GoalContribute(BaseModel):
    amount: float

@app.get("/api/utilities")
def get_utility_readings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utility_readings ORDER BY period_month DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"readings": rows, "tariffs": TARIFFS}

@app.post("/api/utilities")
def record_utility_reading(u: UtilityReadingCreate):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get latest reading prior to this month to compute delta
    cursor.execute("SELECT * FROM utility_readings ORDER BY period_month DESC LIMIT 1")
    prev = cursor.fetchone()

    delta_elec_day = max(0.0, u.elec_day_val - (prev["elec_day_val"] if prev else u.elec_day_val - 150))
    delta_elec_night = max(0.0, u.elec_night_val - (prev["elec_night_val"] if prev else u.elec_night_val - 80))
    delta_cold = max(0.0, u.cold_water_val - (prev["cold_water_val"] if prev else u.cold_water_val - 8))
    delta_hot = max(0.0, u.hot_water_val - (prev["hot_water_val"] if prev else u.hot_water_val - 4))
    delta_gas = max(0.0, u.gas_val - (prev["gas_val"] if prev else u.gas_val - 12))

    c_elec_d = round(delta_elec_day * TARIFFS["elec_day"], 2)
    c_elec_n = round(delta_elec_night * TARIFFS["elec_night"], 2)
    c_cold = round(delta_cold * TARIFFS["cold_water"], 2)
    c_hot = round(delta_hot * TARIFFS["hot_water"], 2)
    c_gas = round(delta_gas * TARIFFS["gas"], 2)

    total_bill = round(c_elec_d + c_elec_n + c_cold + c_hot + c_gas + TARIFFS["internet"] + TARIFFS["heating"], 2)

    cursor.execute("""
        INSERT INTO utility_readings (
            period_month, elec_day_val, elec_night_val, cold_water_val, hot_water_val, gas_val,
            elec_day_cost, elec_night_cost, cold_water_cost, hot_water_cost, gas_cost,
            fixed_internet, fixed_heating, total_bill
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(period_month) DO UPDATE SET
            elec_day_val = excluded.elec_day_val,
            elec_night_val = excluded.elec_night_val,
            cold_water_val = excluded.cold_water_val,
            hot_water_val = excluded.hot_water_val,
            gas_val = excluded.gas_val,
            total_bill = excluded.total_bill
    """, (
        u.period_month, u.elec_day_val, u.elec_night_val, u.cold_water_val, u.hot_water_val, u.gas_val,
        c_elec_d, c_elec_n, c_cold, c_hot, c_gas, TARIFFS["internet"], TARIFFS["heating"], total_bill
    ))

    conn.commit()
    conn.close()
    return {"status": "saved", "total_bill": total_bill}

@app.get("/api/transactions")
def get_transactions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY tx_date DESC, id DESC LIMIT 50")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"transactions": rows}

@app.post("/api/transactions")
def add_transaction(tx: TransactionCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (type, category, amount, note, tx_date)
        VALUES (?, ?, ?, ?, ?)
    """, (tx.type.upper(), tx.category, tx.amount, tx.note, tx.tx_date))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "created", "id": new_id}

@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/api/goals")
def get_goals():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM savings_goals ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for g in rows:
        target = g["target_amount"]
        cur = g["current_amount"]
        g["progress_pct"] = min(100, round((cur / target) * 100, 1)) if target > 0 else 0

    return {"goals": rows}

@app.post("/api/goals")
def create_goal(g: GoalCreate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO savings_goals (title, target_amount, deadline_date)
        VALUES (?, ?, ?)
    """, (g.title, g.target_amount, g.deadline_date))
    gid = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "created", "id": gid}

@app.post("/api/goals/{goal_id}/contribute")
def contribute_to_goal(goal_id: int, c: GoalContribute):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE savings_goals SET current_amount = current_amount + ? WHERE id = ?", (c.amount, goal_id))
    cursor.execute("SELECT current_amount, target_amount FROM savings_goals WHERE id = ?", (goal_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {"status": "updated", "current_amount": row[0], "target_amount": row[1]}

@app.get("/api/summary")
def get_summary():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'INCOME'")
    income = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'EXPENSE'")
    expense = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(current_amount), 0) FROM savings_goals")
    saved = cursor.fetchone()[0]

    cursor.execute("SELECT total_bill FROM utility_readings ORDER BY period_month DESC LIMIT 1")
    last_bill_row = cursor.fetchone()
    last_bill = last_bill_row[0] if last_bill_row else 0.0

    conn.close()
    return {
        "total_income": income,
        "total_expense": expense,
        "net_balance": income - expense,
        "total_saved_goals": saved,
        "latest_utility_bill": last_bill
    }

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))
