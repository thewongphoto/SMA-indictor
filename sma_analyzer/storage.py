"""Small parameterized SQLite store. No service, ORM, or global connection."""
from dataclasses import dataclass, asdict
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3
import json

from .notifications import NotificationSettings, validate_email

from .settings import DATA_VERSION


@dataclass(frozen=True)
class SavedLine:
    id: int
    counter: str
    scenario: str
    period: int
    target_frequency: int
    visible: bool
    push_enabled: bool = False
    email_enabled: bool = False


class LineStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS saved_lines (
                    id INTEGER PRIMARY KEY,
                    counter TEXT NOT NULL,
                    scenario TEXT NOT NULL,
                    period INTEGER NOT NULL CHECK(period >= 2),
                    target_frequency INTEGER NOT NULL CHECK(target_frequency > 0),
                    visible INTEGER NOT NULL DEFAULT 1 CHECK(visible IN (0, 1)),
                    data_version INTEGER NOT NULL,
                    UNIQUE(counter, scenario, period, target_frequency, data_version)
                )
            """)

            # Additive migration preserves saved parameters and visibility.
            columns = {row[1] for row in connection.execute("PRAGMA table_info(saved_lines)")}
            for name in ("push_enabled", "email_enabled"):
                if name not in columns:
                    connection.execute(f"ALTER TABLE saved_lines ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0 CHECK({name} IN (0,1))")
            connection.execute("""CREATE TABLE IF NOT EXISTS unsaved_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT, counter TEXT NOT NULL,
                scenario TEXT NOT NULL, period INTEGER NOT NULL, target_frequency INTEGER NOT NULL,
                visible INTEGER NOT NULL, push_enabled INTEGER NOT NULL, email_enabled INTEGER NOT NULL,
                data_version INTEGER NOT NULL)""")
            connection.execute("CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS deliveries (event_key TEXT PRIMARY KEY)")

    @contextmanager
    def _connect(self):
        # sqlite's transaction context commits/rolls back but does not close itself.
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                yield connection

    def list_lines(self, counter: str, scenario: str) -> list[SavedLine]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, counter, scenario, period, target_frequency, visible, push_enabled, email_enabled "
                "FROM saved_lines WHERE counter=? AND scenario=? AND data_version=? ORDER BY id",
                (counter, scenario, DATA_VERSION),
            ).fetchall()
        return [SavedLine(*row[:5], *map(bool, row[5:])) for row in rows]

    def save(self, counter: str, scenario: str, period: int, target: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO saved_lines(counter, scenario, period, target_frequency, data_version) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(counter, scenario, period, target_frequency, "
                "data_version) DO NOTHING",
                (counter, scenario, period, target, DATA_VERSION),
            )

            connection.execute("DELETE FROM unsaved_lines WHERE counter=? AND scenario=? AND period=? "
                               "AND target_frequency=? AND data_version=?",
                               (counter, scenario, period, target, DATA_VERSION))

    def set_visible(self, line_id: int, visible: bool) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE saved_lines SET visible=? WHERE id=?", (int(visible), line_id))

    def delete(self, line_id: int) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT counter,scenario,period,target_frequency,visible,push_enabled,email_enabled,data_version "
                "FROM saved_lines WHERE id=?", (line_id,)).fetchone()
            if row is None:
                return
            connection.execute("DELETE FROM unsaved_lines WHERE counter=? AND scenario=? AND period=? "
                               "AND target_frequency=? AND data_version=?", (*row[:4], row[-1]))
            connection.execute("INSERT INTO unsaved_lines(counter,scenario,period,target_frequency,visible,"
                               "push_enabled,email_enabled,data_version) VALUES (?,?,?,?,?,?,?,?)", row)
            connection.execute("DELETE FROM unsaved_lines WHERE id NOT IN "
                               "(SELECT id FROM unsaved_lines ORDER BY id DESC LIMIT 10)")
            connection.execute("DELETE FROM saved_lines WHERE id=?", (line_id,))

    def recent_unsaved(self) -> list[SavedLine]:
        """Most recent 10 unique unsaved configurations, across counters/scenarios."""
        with self._connect() as connection:
            rows = connection.execute("SELECT id,counter,scenario,period,target_frequency,visible,"
                                      "push_enabled,email_enabled FROM unsaved_lines "
                                      "WHERE data_version=? ORDER BY id DESC", (DATA_VERSION,)).fetchall()
        return [SavedLine(*row[:5], *map(bool, row[5:])) for row in rows]

    def restore(self, history_id: int):
        with self._connect() as connection:
            row = connection.execute("SELECT counter,scenario,period,target_frequency,visible,push_enabled,"
                                     "email_enabled,data_version FROM unsaved_lines WHERE id=? AND data_version=?",
                                     (history_id, DATA_VERSION)).fetchone()
            if row is None:
                raise ValueError("This unsaved line is no longer in the last 10 entries.")
            if row[6] and not self.notification_settings().email:
                raise ValueError("Save your email address in Settings before restoring an email-enabled line.")
            connection.execute("INSERT INTO saved_lines(counter,scenario,period,target_frequency,visible,"
                               "push_enabled,email_enabled,data_version) VALUES (?,?,?,?,?,?,?,?) "
                               "ON CONFLICT(counter,scenario,period,target_frequency,data_version) DO NOTHING", row)
            connection.execute("DELETE FROM unsaved_lines WHERE id=?", (history_id,))

    def notification_settings(self) -> NotificationSettings:
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM preferences WHERE key='notifications'").fetchone()
        return NotificationSettings(**json.loads(row[0])) if row else NotificationSettings()

    def save_notification_settings(self, settings: NotificationSettings):
        email = validate_email(settings.email)
        with self._connect() as connection:
            if not email and connection.execute("SELECT 1 FROM saved_lines WHERE email_enabled=1 LIMIT 1").fetchone():
                raise ValueError("Turn off email for all saved SMA lines before clearing your email address.")
            values = asdict(settings)
            values["email"] = email
            connection.execute("INSERT INTO preferences(key,value) VALUES ('notifications',?) "
                               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(values),))

    def set_notifications(self, line_id: int, channel: str, enabled: bool):
        if channel not in ("phone", "email"):
            raise ValueError("Choose phone or email notifications.")
        if channel == "email" and enabled and not self.notification_settings().email:
            raise ValueError("Save your email address in Settings before enabling email notifications.")
        column = "push_enabled" if channel == "phone" else "email_enabled"
        with self._connect() as connection:
            connection.execute(f"UPDATE saved_lines SET {column}=? WHERE id=?", (int(enabled), line_id))

    def was_delivered(self, key: str) -> bool:
        with self._connect() as connection:
            return connection.execute("SELECT 1 FROM deliveries WHERE event_key=?", (key,)).fetchone() is not None

    def record_delivery(self, key: str):
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO deliveries(event_key) VALUES (?)", (key,))
