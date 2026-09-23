import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")

            db.execute("CREATE TABLE IF NOT EXISTS practice (report_id INTEGER NOT NULL, question_index INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(report_id,question_index))")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, report):
        record = {**report, "created_at": datetime.now(timezone.utc).isoformat()}
        with self.connect() as db:
            cursor = db.execute("INSERT INTO reports(created_at,payload) VALUES (?,?)",
                                (record["created_at"], json.dumps(record, ensure_ascii=False)))
            record["id"] = cursor.lastrowid
        return record

    def get(self, report_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM reports WHERE id=?", (report_id,)).fetchone()
        return {**json.loads(row[0]), "id": report_id} if row else None

    def list(self, limit=20, offset=0):
        with self.connect() as db:
            rows = db.execute("SELECT id,payload FROM reports ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [{**json.loads(row[1]), "id": row[0]} for row in rows]

    def save_practice(self, report_id, question_index, payload):
        with self.connect() as db:
            db.execute(
                'INSERT INTO practice(report_id,question_index,payload) VALUES (?,?,?) '
                'ON CONFLICT(report_id,question_index) DO UPDATE SET payload=excluded.payload',
                (report_id, question_index, json.dumps(payload, ensure_ascii=False)))
        return payload

    def practices(self, report_id):
        with self.connect() as db:
            rows = db.execute('SELECT question_index,payload FROM practice WHERE report_id=? ORDER BY question_index',
                              (report_id,)).fetchall()
        return [{**json.loads(row[1]), 'question_index': row[0]} for row in rows]
