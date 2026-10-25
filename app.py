"""Project 1 - Cloud-Based Task Management System (Flask + SQLite + REST API)."""
import json
import os
import sqlite3

from flask import Flask, g, jsonify, render_template, request

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DATABASE", os.path.join(BASE, "tasks.db"))

app = Flask(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'Medium',
    status TEXT NOT NULL DEFAULT 'todo',
    due_date TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""
PRIORITIES = ("Low", "Medium", "High")
STATUSES = ("todo", "doing", "done")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the table and load sample data the first time the app runs."""
    with sqlite3.connect(DB) as con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            with open(os.path.join(BASE, "sample_data", "tasks.json"), encoding="utf-8") as f:
                for t in json.load(f):
                    con.execute(
                        "INSERT INTO tasks (title, description, priority, status, due_date) VALUES (?,?,?,?,?)",
                        (t["title"], t["description"], t["priority"], t["status"], t["due_date"]),
                    )


@app.context_processor
def inject():
    return dict(app_title="Cloud Task Manager", nav=[("index", "Board")])


def clean(data, partial=False):
    """Validate JSON from the browser. Returns (values, error)."""
    out = {}
    if "title" in data or not partial:
        title = str(data.get("title", "")).strip()
        if not title:
            return None, "Title is required."
        out["title"] = title[:120]
    if "description" in data:
        out["description"] = str(data["description"]).strip()[:500]
    if "priority" in data:
        if data["priority"] not in PRIORITIES:
            return None, "Priority must be Low, Medium or High."
        out["priority"] = data["priority"]
    if "status" in data:
        if data["status"] not in STATUSES:
            return None, "Invalid status."
        out["status"] = data["status"]
    if "due_date" in data:
        out["due_date"] = str(data["due_date"])[:10]
    return out, None


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/tasks")
def list_tasks():
    rows = get_db().execute(
        "SELECT * FROM tasks ORDER BY CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, due_date"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/tasks")
def create_task():
    values, err = clean(request.get_json(silent=True) or {})
    if err:
        return jsonify(error=err), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (title, description, priority, status, due_date) VALUES (?,?,?,?,?)",
        (values["title"], values.get("description", ""), values.get("priority", "Medium"),
         values.get("status", "todo"), values.get("due_date", "")),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.put("/api/tasks/<int:task_id>")
def update_task(task_id):
    values, err = clean(request.get_json(silent=True) or {}, partial=True)
    if err:
        return jsonify(error=err), 400
    if not values:
        return jsonify(error="Nothing to update."), 400
    db = get_db()
    if db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is None:
        return jsonify(error="Task not found."), 404
    sets = ", ".join(f"{k}=?" for k in values)  # keys come from clean(), never from the user
    db.execute(f"UPDATE tasks SET {sets} WHERE id=?", (*values.values(), task_id))
    db.commit()
    return jsonify(dict(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()))


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    db = get_db()
    cur = db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="Task not found."), 404
    return jsonify(ok=True)


init_db()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
