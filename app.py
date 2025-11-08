import os, webbrowser
from datetime import datetime
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

# ---------------- Config ----------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Geethika@2006",
    "database": "Disaster_relief2",
}
SECRET_KEY = os.environ.get("FLASK_SECRET", "dev-secret")

# Map tabs -> (table name, primary key, ordered columns)
TABLES = {
    "Disaster":      ("Disaster", "DisasterID",
                      ["DisasterID","Type","Severity","StartDate","EndDate","City","District","State"]),
    "ReliefCamp":    ("ReliefCamp", "CampID",
                      ["CampID","Name","Village","Taluk","District","State","Capacity","CampStatus","OpenDate","CloseDate","DisasterID"]),
    "Volunteer":     ("Volunteer", "VolunteerID",
                      ["VolunteerID","Name","Phone","Availability"]),
    "Victim":        ("Victim", "VictimID",
                      ["VictimID","Name","Age","Gender","Village","Taluk","District","State","CampID"]),
    "Resource":      ("Resource", "ResourceID",
                      ["ResourceID","Category","ItemName","Unit"]),
    "Stocked_At":    ("Stocked_At", ("CampID","ResourceID"),
                      ["CampID","ResourceID","CurrentQty","ReorderLevel"]),
    "AssignedTo":    ("AssignedTo", ("CampID","VolunteerID","Date"),
                      ["CampID","VolunteerID","Date"]),
    "AidDistribution": ("AidDistribution", ("VolunteerID","VictimID","ResourceID","DistDate"),
                        ["VolunteerID","VictimID","ResourceID","DistDate","Qty"]),
}

# --------------- App & DB helpers ---------------
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

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

# ---- small helpers for trigger demo ----
def victim_camp(victim_id):
    """Return CampID for a victim (or None)."""
    return scalar("SELECT CampID FROM Victim WHERE VictimID=%s", (victim_id,))

def stock_qty(camp_id, resource_id):
    """Return current stock qty for a camp+resource (or None)."""
    return scalar(
        "SELECT CurrentQty FROM Stocked_At WHERE CampID=%s AND ResourceID=%s",
        (camp_id, resource_id),
    )

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

# ---------------- Home dashboard ----------------
@app.get("/")
def index():
    stats = {
        "camps": scalar("SELECT COUNT(*) FROM ReliefCamp"),
        "volunteers": scalar("SELECT COUNT(*) FROM Volunteer"),
        "victims": scalar("SELECT COUNT(*) FROM Victim"),
        "aid_rows": scalar("SELECT COUNT(*) FROM AidDistribution"),
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
    return render_template("index.html", stats=stats, recent_aid=recent_aid, tabs=TABLES.keys())

# ---------------- Generic CRUD pages ----------------
@app.route("/crud/<string:tab>", methods=["GET", "POST"])
def crud_list(tab):
    if tab not in TABLES:
        flash("Unknown tab.", "danger")
        return redirect(url_for("index"))
    table, pk, cols = TABLES[tab]

    # Handle Add/Update/Delete
    action = request.form.get("action")
    if action in {"add","update","delete"}:
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
                    flash("Update is not supported for composite keys. Delete & re-add.", "warning")
                else:
                    if not form_vals.get(pk):
                        flash(f"Provide {pk} to update.", "danger")
                    else:
                        set_list = ", ".join([f"{c}=%s" for c in cols if c != pk])
                        sql = f"UPDATE {table} SET {set_list} WHERE {pk}=%s"
                        params = [form_vals[c] for c in cols if c != pk] + [form_vals[pk]]
                        execute(sql, params)
                        flash("Row updated.", "success")

            elif action == "delete":
                if isinstance(pk, tuple):
                    if not all(form_vals.get(k) for k in pk):
                        flash(f"Need keys {pk} to delete.", "danger")
                    else:
                        where = " AND ".join([f"{k}=%s" for k in pk])
                        sql = f"DELETE FROM {table} WHERE {where}"
                        execute(sql, [form_vals[k] for k in pk])
                        flash("Row deleted.", "success")
                else:
                    if not form_vals.get(pk):
                        flash(f"Provide {pk} to delete.", "danger")
                    else:
                        execute(f"DELETE FROM {table} WHERE {pk}=%s", (form_vals[pk],))
                        flash("Row deleted.", "success")

        except Exception as e:
            flash(f"{action.capitalize()} failed: {e}", "danger")

        return redirect(url_for("crud_list", tab=tab))

    # GET: show table
    rows = query_dicts(f"SELECT {', '.join(cols)} FROM {table}")
    return render_template("crud_list.html",
                           tab=tab, table=table, pk=pk, cols=cols, rows=rows, tabs=TABLES.keys())

# ---------------- DB Operations ----------------
@app.route("/dbops", methods=["GET", "POST"])
def dbops():
    if request.method == "POST":
        action = request.form.get("action", "")

        # Stored procedure: DistributeAid(vol, vic, res, qty, date)
        if action == "distribute":
            try:
                call_proc("DistributeAid", (
                    request.form.get("d_vol","").strip(),
                    request.form.get("d_vic","").strip(),
                    request.form.get("d_res","").strip(),
                    request.form.get("d_qty","").strip(),
                    request.form.get("d_date","").strip() or None
                ))
                flash("DistributeAid() executed.", "success")
            except Exception as e:
                flash(f"DistributeAid error: {e}", "danger")

        # Stored procedure: assign_volunteer(camp, vol, date)
        elif action == "assign":
            try:
                call_proc("assign_volunteer", (
                    request.form.get("a_camp","").strip(),
                    request.form.get("a_vol","").strip(),
                    request.form.get("a_date","").strip() or today_str()
                ))
                flash("assign_volunteer() executed.", "success")
            except Exception as e:
                flash(f"assign_volunteer error: {e}", "danger")

        # Scalar function: camp_occupancy_for(campID INT)
        elif action == "occ_for":
            camp = request.form.get("occ_camp","").strip()
            if not camp:
                flash("Please enter a Camp ID for occupancy.", "danger")
            else:
                try:
                    pct = scalar("SELECT camp_occupancy_for(%s)", (camp,))
                    if pct is None:
                        flash(f"No data to compute occupancy for Camp {camp}.", "warning")
                    else:
                        flash(f"camp_occupancy_for({camp}) = {pct}%", "info")
                except Exception as e:
                    flash(f"camp_occupancy_for error: {e}", "danger")

        # Scalar function: CountVictimsInCamp(campID INT)
        elif action == "count":
            camp = request.form.get("c_camp","").strip()
            if not camp:
                flash("Please enter a Camp ID.", "danger")
            else:
                try:
                    cnt = scalar("SELECT CountVictimsInCamp(%s)", (camp,))
                    flash(f"Victims in Camp {camp}: {cnt}", "info")
                except Exception as e:
                    flash(f"CountVictimsInCamp error: {e}", "danger")

        # ---- Trigger demo 1: BEFORE INSERT blocks negative qty ----
        elif action == "trg_neg":
            v  = (request.form.get("t_vol")  or "201").strip()
            vc = (request.form.get("t_vic")  or "301").strip()
            r  = (request.form.get("t_res")  or "401").strip()
            d  = (request.form.get("t_date") or today_str()).strip()

            try:
                execute(
                    "INSERT INTO AidDistribution (VolunteerID, VictimID, ResourceID, DistDate, Qty) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (v, vc, r, d, -5)
                )
                flash("Unexpected: negative quantity insert was not blocked.", "warning")
            except Exception as e:
                flash(f"BEFORE INSERT trigger blocked negative qty as expected. Error: {e}", "success")

        # ---- Trigger demo 2: AFTER INSERT decrements stock ----
        elif action == "trg_ok":
            v  = (request.form.get("t_vol")  or "201").strip()
            vc = (request.form.get("t_vic")  or "301").strip()
            r  = (request.form.get("t_res")  or "401").strip()
            q  = int(request.form.get("t_qty") or "4")
            d  = (request.form.get("t_date") or today_str()).strip()

            camp_id = victim_camp(vc)
            if not camp_id:
                flash("Victim not found or not assigned to a camp.", "danger")
            else:
                before = stock_qty(camp_id, r)
                try:
                    execute(
                        "INSERT INTO AidDistribution (VolunteerID, VictimID, ResourceID, DistDate, Qty) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (v, vc, r, d, q)
                    )
                    after = stock_qty(camp_id, r)
                    flash(
                        f"AFTER INSERT trigger executed. Stock for Camp {camp_id}, Resource {r}: {before} → {after}",
                        "info"
                    )
                except Exception as e:
                    flash(f"Valid insert failed: {e}", "danger")

        # ---- Trigger demo 3: AFTER DELETE restores stock ----
        elif action == "trg_del":
            v  = (request.form.get("t_vol")  or "201").strip()
            vc = (request.form.get("t_vic")  or "301").strip()
            r  = (request.form.get("t_res")  or "401").strip()
            d  = (request.form.get("t_date") or today_str()).strip()

            camp_id = victim_camp(vc)
            if not camp_id:
                flash("Victim not found or not assigned to a camp.", "danger")
            else:
                before = stock_qty(camp_id, r)
                try:
                    execute(
                        "DELETE FROM AidDistribution "
                        "WHERE VolunteerID=%s AND VictimID=%s AND ResourceID=%s AND DistDate=%s",
                        (v, vc, r, d)
                    )
                    after = stock_qty(camp_id, r)
                    flash(
                        f"AFTER DELETE trigger executed. Stock for Camp {camp_id}, Resource {r}: {before} → {after}",
                        "info"
                    )
                except Exception as e:
                    flash(f"Delete failed: {e}", "danger")

    return render_template("dbops.html", tabs=TABLES.keys())

# ---------------- Queries ----------------
@app.route("/queries", methods=["GET", "POST"])
def queries():
    nested_rows = join_rows = agg_rows = None
    action = request.form.get("action", "")

    if action == "nested":
        camp = request.form.get("nested_camp","").strip()
        day  = request.form.get("nested_date","").strip()
        if camp and day:
            sql = """
            SELECT v.VictimID, v.Name, SUM(a.Qty) AS total_qty
            FROM AidDistribution a
            JOIN Victim v ON v.VictimID = a.VictimID
            WHERE v.CampID = %s AND a.DistDate = %s
            GROUP BY v.VictimID, v.Name
            HAVING SUM(a.Qty) >
                   (
                     SELECT AVG(t.total_per_victim)
                     FROM (
                       SELECT SUM(a2.Qty) AS total_per_victim
                       FROM AidDistribution a2
                       JOIN Victim v2 ON v2.VictimID = a2.VictimID
                       WHERE v2.CampID = %s AND a2.DistDate = %s
                       GROUP BY a2.VictimID
                     ) t
                   )
            ORDER BY total_qty DESC
            """
            nested_rows = query_dicts(sql, (camp, day, camp, day))
            if not nested_rows:
                flash("No one above camp average for that date/camp.", "warning")
        else:
            flash("Provide Camp ID and Date.", "danger")

    elif action == "join":
        d1 = request.form.get("join_from","").strip()
        d2 = request.form.get("join_to","").strip()
        camp = request.form.get("join_camp","").strip()
        if d1 and d2:
            sql = """
            SELECT a.DistDate AS Date,
                   vol.Name AS Volunteer,
                   vic.Name AS Victim,
                   r.ItemName AS Resource,
                   a.Qty,
                   vic.CampID
            FROM AidDistribution a
            JOIN Volunteer vol ON vol.VolunteerID = a.VolunteerID
            JOIN Victim    vic ON vic.VictimID    = a.VictimID
            JOIN Resource  r   ON r.ResourceID    = a.ResourceID
            WHERE a.DistDate BETWEEN %s AND %s
            """
            params = [d1, d2]
            if camp:
                sql += " AND vic.CampID = %s"
                params.append(camp)
            sql += " ORDER BY a.DistDate, Volunteer, Victim"
            join_rows = query_dicts(sql, params)
            if not join_rows:
                flash("No rows in window.", "warning")
        else:
            flash("Provide From and To dates.", "danger")

    elif action == "aggregate":
        camp = request.form.get("agg_camp","").strip()
        d1   = request.form.get("agg_from","").strip()
        d2   = request.form.get("agg_to","").strip()
        if camp and d1 and d2:
            sql = """
            SELECT r.ItemName AS Resource, SUM(a.Qty) AS TotalQty
            FROM AidDistribution a
            JOIN Victim v ON v.VictimID = a.VictimID
            JOIN Resource r ON r.ResourceID = a.ResourceID
            WHERE v.CampID = %s AND a.DistDate BETWEEN %s AND %s
            GROUP BY r.ItemName
            ORDER BY TotalQty DESC
            """
            agg_rows = query_dicts(sql, (camp, d1, d2))
            if not agg_rows:
                flash("No distributions for that camp/date range.", "warning")
        else:
            flash("Provide Camp ID, From, To.", "danger")

    return render_template("queries.html",
                           nested_rows=nested_rows, join_rows=join_rows, agg_rows=agg_rows,
                           tabs=TABLES.keys())

# --------- Auto-open in browser (Chrome if available) ----------
def _open_browser():
    url = "http://127.0.0.1:5000/"
    try:
        webbrowser.get("chrome").open(url, new=2)
    except Exception:
        webbrowser.open(url, new=2)

if __name__ == "__main__":
    Timer(0.6, _open_browser).start()
    app.run(debug=True)
