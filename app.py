import os, webbrowser
from datetime import datetime
from threading import Timer
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

# ─────────────────────────────────────────────────────────────────────────────
# DB CONFIG  (same schema for all, different MySQL users)
# ─────────────────────────────────────────────────────────────────────────────
BASE_DB_CONFIG = {
    "host": "localhost",
    "database": "Disaster_relief2",
}

# UI login accounts → map to MySQL user + password + role
#  - Username/password here are what you type in the LOGIN FORM
#  - db_user/db_pass are the actual MySQL instances you created
LOGIN_ACCOUNTS = {
    "admin": {
        "password": "admin123",
        "role": "Admin",
        "db_user": "admin_user",
        "db_pass": "admin123",
    },
    "volunteer1": {
        "password": "vol123",
        "role": "Operator",
        "db_user": "operator_user",
        "db_pass": "op123",
    },
    "viewer1": {
        "password": "view123",
        "role": "Viewer",
        "db_user": "viewer_user",
        "db_pass": "view123",
    },
}

# Fallback user (only used BEFORE login, e.g. to show login page safely)
ROOT_FALLBACK = {"user": "root", "password": "Geethika@2006"}

SECRET_KEY = os.environ.get("FLASK_SECRET", "dev-secret")

# Map tabs -> (table name, primary key, ordered columns)
TABLES = {
    "Disaster": ("Disaster", "DisasterID",
        ["DisasterID","Type","Severity","StartDate","EndDate","City","District","State"]),
    "ReliefCamp": ("ReliefCamp", "CampID",
        ["CampID","Name","Village","Taluk","District","State","Capacity","CampStatus","OpenDate","CloseDate","DisasterID"]),
    "Volunteer": ("Volunteer", "VolunteerID",
        ["VolunteerID","Name","Phone","Availability"]),
    "Victim": ("Victim", "VictimID",
        ["VictimID","Name","Age","Gender","Village","Taluk","District","State","CampID"]),
    "Resource": ("Resource", "ResourceID",
        ["ResourceID","Category","ItemName","Unit"]),
    "Stocked_At": ("Stocked_At", ("CampID","ResourceID"),
        ["CampID","ResourceID","CurrentQty","ReorderLevel"]),
    "AssignedTo": ("AssignedTo", ("CampID","VolunteerID","Date"),
        ["CampID","VolunteerID","Date"]),
    "AidDistribution": ("AidDistribution", ("VolunteerID","VictimID","ResourceID","DistDate"),
        ["VolunteerID","VictimID","ResourceID","DistDate","Qty"]),
}

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# Navbar / layout helper
@app.context_processor
def inject_nav():
    role = session.get("role")
    can_crud = (role == "Admin")
    tabs = list(TABLES.keys()) if can_crud else []  # only Admin sees CRUD tabs
    return {
        "role": role,
        "can_crud": can_crud,
        "tabs": tabs,
        "db_user": session.get("db_user"),
    }

# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────
def _conn_creds():
    """
    Use the MySQL user stored in the session.
    Before login, fall back to root.
    """
    user = session.get("db_user", ROOT_FALLBACK["user"])
    password = session.get("db_pass", ROOT_FALLBACK["password"])
    return {
        "host": BASE_DB_CONFIG["host"],
        "database": BASE_DB_CONFIG["database"],
        "user": user,
        "password": password,
    }

def get_conn():
    return mysql.connector.connect(**_conn_creds())

def query_dicts(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def execute(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    cur.close(); conn.close()

def scalar(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    row = cur.fetchone()
    cur.close(); conn.close()
    return None if row is None else row[0]

def call_proc(name, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.callproc(name, params or ())
    out = []
    for r in cur.stored_results():
        out.extend(r.fetchall())
    conn.commit()
    cur.close(); conn.close()
    return out

# ─────────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────────
def login_required(role=None, any_of:tuple|list|None=None):
    """
    If role is given → require exact role; if any_of is given → require in set.
    """
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            if "db_user" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            current = session.get("role")
            if role and current != role:
                flash("Unauthorized access!", "danger")
                return redirect(url_for("index"))
            if any_of and current not in any_of:
                flash("Unauthorized access!", "danger")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return inner
    return wrapper

# ─────────────────────────────────────────────────────────────────────────────
# Login / Logout  → uses REAL MySQL users via mapping
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        account = LOGIN_ACCOUNTS.get(username)
        if not account or password != account["password"]:
            flash("Invalid username or password!", "danger")
            return render_template("login.html")

        # Double-check that this mapped MySQL user actually works
        db_user = account["db_user"]
        db_pass = account["db_pass"]
        try:
            test_conn = mysql.connector.connect(
                host=BASE_DB_CONFIG["host"],
                database=BASE_DB_CONFIG["database"],
                user=db_user,
                password=db_pass,
            )
            test_conn.close()
        except mysql.connector.Error as e:
            flash(f"MySQL login failed for '{db_user}': {e}", "danger")
            return render_template("login.html")

        # Store into session
        session.clear()
        session["db_user"] = db_user
        session["db_pass"] = db_pass
        session["role"]    = account["role"]

        flash(
            f"Welcome {account['role']}! "
            f"Connected as MySQL user: {db_user}",
            "success",
        )
        return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ─────────────────────────────────────────────────────────────────────────────
# Home dashboard
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
@login_required()
def index():
    stats = {
        "camps":      scalar("SELECT COUNT(*) FROM ReliefCamp"),
        "volunteers": scalar("SELECT COUNT(*) FROM Volunteer"),
        "victims":    scalar("SELECT COUNT(*) FROM Victim"),
        "aid_rows":   scalar("SELECT COUNT(*) FROM AidDistribution"),
    }
    recent_aid = query_dicts("""
        SELECT a.DistDate AS Date, vol.Name AS Volunteer, vic.Name AS Victim,
               r.ItemName AS Resource, a.Qty, vic.CampID
        FROM AidDistribution a
        JOIN Volunteer vol ON vol.VolunteerID = a.VolunteerID
        JOIN Victim    vic ON vic.VictimID    = a.VictimID
        JOIN Resource  r   ON r.ResourceID    = a.ResourceID
        ORDER BY a.DistDate DESC, a.VictimID ASC
        LIMIT 10
    """)
    return render_template("index.html", stats=stats, recent_aid=recent_aid)

# ─────────────────────────────────────────────────────────────────────────────
# CRUD (Admin only)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/crud/<string:tab>", methods=["GET", "POST"])
@login_required(role="Admin")
def crud_list(tab):
    if tab not in TABLES:
        flash("Unknown tab.", "danger")
        return redirect(url_for("index"))

    table, pk, cols = TABLES[tab]
    action = request.form.get("action")

    if action in {"add", "update", "delete"}:
        try:
            form_vals = {c: (request.form.get(c) or None) for c in cols}

            if action == "add":
                placeholders = ", ".join(["%s"] * len(cols))
                col_list = ", ".join(cols)
                sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
                execute(sql, [form_vals[c] for c in cols])
                flash("Row added.", "success")

            elif action == "update":
                if isinstance(pk, tuple):
                    flash("Composite keys not supported for update.", "warning")
                else:
                    set_list = ", ".join([f"{c}=%s" for c in cols if c != pk])
                    sql = f"UPDATE {table} SET {set_list} WHERE {pk}=%s"
                    params = [form_vals[c] for c in cols if c != pk] + [form_vals[pk]]
                    execute(sql, params)
                    flash("Row updated.", "success")

            elif action == "delete":
                if isinstance(pk, tuple):
                    where = " AND ".join([f"{k}=%s" for k in pk])
                    sql = f"DELETE FROM {table} WHERE {where}"
                    execute(sql, [form_vals[k] for k in pk])
                else:
                    execute(f"DELETE FROM {table} WHERE {pk}=%s", (form_vals[pk],))
                flash("Row deleted.", "success")

        except Exception as e:
            flash(f"{action.capitalize()} failed: {e}", "danger")

        return redirect(url_for("crud_list", tab=tab))

    rows = query_dicts(f"SELECT {', '.join(cols)} FROM {table}")
    return render_template("crud_list.html", tab=tab, table=table, pk=pk, cols=cols, rows=rows)

# ─────────────────────────────────────────────────────────────────────────────
# DB Operations (Admin + Operator)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/dbops", methods=["GET", "POST"])
@login_required(any_of=("Admin", "Operator"))
def dbops():
    notice = None

    def _val(name, cast=int):
        v = (request.form.get(name) or "").strip()
        if v == "":
            return None
        return cast(v) if cast is not None else v

    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        try:
            if action == "distribute":
                vol_id = _val("volunteer_id")
                vic_id = _val("victim_id")
                res_id = _val("resource_id")
                qty    = _val("qty")
                date_s = _val("date", cast=None)
                call_proc("DistributeAid", [vol_id, vic_id, res_id, qty, date_s])
                notice = "✅ Aid distributed successfully."

            elif action == "assign_volunteer":
                camp_id = _val("assign_camp_id")
                vol_id  = _val("assign_volunteer_id")
                date_s  = _val("assign_date", cast=None)
                call_proc("assign_volunteer", [camp_id, vol_id, date_s])
                notice = "✅ Volunteer assigned."

            elif action == "occ":
                camp_id = _val("occ_camp_id")
                pct = scalar("SELECT camp_occupancy_for(%s)", (camp_id,))
                notice = f"ℹ️ Occupancy for camp {camp_id}: {pct}%"

            elif action == "count_victims":
                camp_id = _val("count_camp_id")
                cnt = scalar("SELECT CountVictimsInCamp(%s)", (camp_id,))
                notice = f"ℹ️ Victims in camp {camp_id}: {cnt}"

            elif action == "trig_before":
                vol_id = _val("trig_volunteer_id")
                vic_id = _val("trig_victim_id")
                res_id = _val("trig_resource_id")
                date_s = _val("trig_date", cast=None)
                call_proc("DistributeAid", [vol_id, vic_id, res_id, -5, date_s])
                notice = "❗ Tried negative qty (BEFORE INSERT should block)."

            elif action == "trig_after_insert":
                vol_id = _val("trig_volunteer_id")
                vic_id = _val("trig_victim_id")
                res_id = _val("trig_resource_id")
                qty    = _val("trig_qty")
                date_s = _val("trig_date", cast=None)
                call_proc("DistributeAid", [vol_id, vic_id, res_id, qty, date_s])
                notice = "✅ Valid insert done (AFTER INSERT should decrement stock)."

            elif action == "trig_after_delete":
                vol_id = _val("trig_volunteer_id")
                vic_id = _val("trig_victim_id")
                res_id = _val("trig_resource_id")
                execute("""
                    DELETE FROM AidDistribution
                    WHERE VolunteerID=%s AND VictimID=%s AND ResourceID=%s
                    ORDER BY DistDate DESC
                    LIMIT 1
                """, (vol_id, vic_id, res_id))
                notice = "✅ One recent row deleted (AFTER DELETE should restore stock)."

            else:
                notice = "Unknown action."
        except Exception as e:
            notice = f"❌ Operation failed: {e}"

    return render_template("dbops.html", notice=notice)

# ─────────────────────────────────────────────────────────────────────────────
# Queries (all roles)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/queries", methods=["GET", "POST"])
@login_required(any_of=("Admin", "Operator", "Viewer"))
def queries():
    nested_rows = None
    join_rows   = None
    agg_rows    = None
    notice      = None

    def f(name):
        return (request.form.get(name) or "").strip()

    if request.method == "POST":
        action = f("action")
        try:
            if action == "nested":
                camp_id  = f("nested_camp")
                the_date = f("nested_date")
                sql = """
                WITH per_victim AS (
                  SELECT a.VictimID, SUM(a.Qty) AS total_qty
                  FROM AidDistribution a
                  JOIN Victim v ON v.VictimID = a.VictimID
                  WHERE v.CampID = %s AND a.DistDate = %s
                  GROUP BY a.VictimID
                ),
                av AS (SELECT AVG(total_qty) AS avg_total FROM per_victim)
                SELECT pv.VictimID,
                       vic.Name AS Name,
                       pv.total_qty
                FROM per_victim pv
                JOIN Victim vic ON vic.VictimID = pv.VictimID
                JOIN av
                WHERE pv.total_qty > av.avg_total
                ORDER BY pv.total_qty DESC;
                """
                nested_rows = query_dicts(sql, (camp_id, the_date))

            elif action == "join":
                d_from = f("join_from")
                d_to   = f("join_to")
                camp   = f("join_camp")
                where  = "a.DistDate BETWEEN %s AND %s"
                params = [d_from, d_to]
                if camp:
                    where += " AND vic.CampID = %s"
                    params.append(camp)
                sql = f"""
                SELECT a.DistDate AS Date,
                       vol.Name   AS Volunteer,
                       vic.Name   AS Victim,
                       r.ItemName AS Resource,
                       a.Qty,
                       vic.CampID AS CampID
                FROM AidDistribution a
                JOIN Volunteer vol ON vol.VolunteerID = a.VolunteerID
                JOIN Victim    vic ON vic.VictimID    = a.VictimID
                JOIN Resource  r   ON r.ResourceID    = a.ResourceID
                WHERE {where}
                ORDER BY a.DistDate, vic.VictimID, r.ItemName;
                """
                join_rows = query_dicts(sql, tuple(params))

            elif action == "aggregate":
                camp_id = f("agg_camp")
                d_from  = f("agg_from")
                d_to    = f("agg_to")
                sql = """
                SELECT r.ItemName AS Resource, SUM(a.Qty) AS TotalQty
                FROM AidDistribution a
                JOIN Victim   v ON v.VictimID   = a.VictimID
                JOIN Resource r ON r.ResourceID = a.ResourceID
                WHERE v.CampID = %s AND a.DistDate BETWEEN %s AND %s
                GROUP BY r.ItemName
                ORDER BY r.ItemName;
                """
                agg_rows = query_dicts(sql, (camp_id, d_from, d_to))
        except Exception as e:
            notice = f"❌ Query failed: {e}"

    return render_template(
        "queries.html",
        nested_rows=nested_rows,
        join_rows=join_rows,
        agg_rows=agg_rows,
        notice=notice,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Auto-launch browser
# ─────────────────────────────────────────────────────────────────────────────
def _open_browser():
    try:
        webbrowser.get("chrome").open("http://127.0.0.1:5000/", new=2)
    except Exception:
        webbrowser.open("http://127.0.0.1:5000/", new=2)

if __name__ == "__main__":
    Timer(0.6, _open_browser).start()
    app.run(debug=True)
