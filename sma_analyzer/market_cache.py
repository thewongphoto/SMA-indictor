"""Durable market data. No UI, OS scheduler or network imports.

Dates are ISO exchange-session dates; instants are UTC Unix seconds. These
contracts are shared by desktop and future Android/iOS scheduling adapters.
"""
from contextlib import contextmanager, closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlsplit

from .securities import Security


class MarketCache:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS market_securities (
                    key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS market_search (
                    query TEXT PRIMARY KEY, keys_json TEXT NOT NULL, fetched_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS market_history (
                    key TEXT PRIMARY KEY, fetched_at REAL NOT NULL,
                    revision INTEGER NOT NULL, full_history INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS market_bars (
                    key TEXT NOT NULL, session TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(key,session));
                CREATE TABLE IF NOT EXISTS market_preferences (
                    key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS market_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
                    operation TEXT NOT NULL, symbol TEXT NOT NULL,
                    status TEXT NOT NULL, detail TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runtime_leases (
                    key TEXT PRIMARY KEY, owner TEXT NOT NULL, expires_at REAL NOT NULL);
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(market_operations)")}
            for name, kind in (("request_id","TEXT NOT NULL DEFAULT ''"),
                               ("http_status","INTEGER"), ("duration_ms","REAL"),
                               ("endpoint","TEXT NOT NULL DEFAULT ''")):
                if name not in columns:
                    db.execute(f"ALTER TABLE market_operations ADD COLUMN {name} {kind}")

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            db.execute("PRAGMA busy_timeout=30000")
            with db:
                yield db

    def put_security(self, security):
        with self.connect() as db:
            db.execute("INSERT INTO market_securities VALUES (?,?) ON CONFLICT(key) "
                       "DO UPDATE SET payload=excluded.payload", (security.key, json.dumps(asdict(security))))

    def security(self, key):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM market_securities WHERE key=?", (key,)).fetchone()
        return Security(**json.loads(row[0])) if row else None

    def securities(self):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM market_securities").fetchall()
        return tuple(Security(**json.loads(row[0])) for row in rows)

    def put_search(self, query, securities, now=None):
        for security in securities:
            self.put_security(security)
        with self.connect() as db:
            db.execute("INSERT INTO market_search VALUES (?,?,?) ON CONFLICT(query) DO UPDATE "
                       "SET keys_json=excluded.keys_json,fetched_at=excluded.fetched_at",
                       (query, json.dumps([s.key for s in securities]), time.time() if now is None else now))

    def search(self, query):
        with self.connect() as db:
            row = db.execute("SELECT keys_json FROM market_search WHERE query=?", (query,)).fetchone()
        return tuple(self.security(key) for key in json.loads(row[0])) if row else None

    def history(self, key):
        with self.connect() as db:
            state = db.execute("SELECT fetched_at,revision FROM market_history WHERE key=?", (key,)).fetchone()
            rows = db.execute("SELECT payload FROM market_bars WHERE key=? ORDER BY session", (key,)).fetchall()
        return ([json.loads(row[0]) for row in rows], state[0], state[1]) if state else ([], None, 0)

    def merge_history(self, security, bars, fetched_at, replace=False):
        # Caller validates the entire response before entering this transaction.
        with self.connect() as db:
            db.execute("INSERT INTO market_securities VALUES (?,?) ON CONFLICT(key) DO UPDATE "
                       "SET payload=excluded.payload", (security.key, json.dumps(asdict(security))))
            if replace:
                db.execute("DELETE FROM market_bars WHERE key=?", (security.key,))
            db.executemany("INSERT INTO market_bars VALUES (?,?,?) ON CONFLICT(key,session) "
                           "DO UPDATE SET payload=excluded.payload",
                           [(security.key, bar["date"], json.dumps(bar, allow_nan=False)) for bar in bars])
            db.execute("INSERT INTO market_history VALUES (?,?,1,1) ON CONFLICT(key) DO UPDATE "
                       "SET fetched_at=excluded.fetched_at,revision=revision+1", (security.key, fetched_at))

    def preference(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM market_preferences WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_preference(self, key, value):
        with self.connect() as db:
            db.execute("INSERT INTO market_preferences VALUES (?,?) ON CONFLICT(key) DO UPDATE "
                       "SET payload=excluded.payload", (key, json.dumps(value)))

    def operation(self, operation, symbol, status, detail="", now=None, *,
                  request_id="", http_status=None, duration_ms=None, endpoint=""):
        # Details are controlled summaries, never raw responses or cookies.
        if endpoint:
            parsed = urlsplit(endpoint if "://" in endpoint else "//"+endpoint)
            endpoint = (parsed.hostname or "")+parsed.path
        with self.connect() as db:
            db.execute("INSERT INTO market_operations(at,operation,symbol,status,detail,"
                       "request_id,http_status,duration_ms,endpoint) VALUES (?,?,?,?,?,?,?,?,?)",
                       (time.time() if now is None else now, operation, symbol, status, detail,
                        request_id,http_status,duration_ms,endpoint))

    def operations(self, limit=20):
        with self.connect() as db:
            return db.execute("SELECT at,operation,symbol,status,detail FROM market_operations "
                              "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def diagnostic_events(self, limit=100):
        names = ("at","operation","symbol","status","detail","request_id",
                 "http_status","duration_ms","endpoint")
        with self.connect() as db:
            rows = db.execute("SELECT "+",".join(names)+" FROM market_operations "
                              "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(zip(names,row)) for row in rows]

    def clear_downloads(self):
        # Keep identities, saved parameters, jobs and delivery keys resolvable.
        with self.connect() as db:
            db.execute("DELETE FROM market_bars")
            db.execute("DELETE FROM market_history")
            db.execute("DELETE FROM market_search")

    def lease(self, key, owner, now, duration):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT owner,expires_at FROM runtime_leases WHERE key=?", (key,)).fetchone()
            if row and row[0] != owner and row[1] > now:
                return False
            db.execute("INSERT INTO runtime_leases VALUES (?,?,?) ON CONFLICT(key) DO UPDATE "
                       "SET owner=excluded.owner,expires_at=excluded.expires_at", (key, owner, now + duration))
        return True

    def release_lease(self, key, owner):
        with self.connect() as db:
            db.execute("DELETE FROM runtime_leases WHERE key=? AND owner=?", (key, owner))
