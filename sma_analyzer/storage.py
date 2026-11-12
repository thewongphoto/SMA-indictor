"""Small parameterized SQLite store. No service, ORM, or global connection."""
from dataclasses import dataclass, asdict
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3
import json

from .notifications import NotificationSettings, validate_email

from .settings import DATA_VERSION
from .line_names import normalize_name, sma_label
from .palette import COLOR_CHOICES


@dataclass(frozen=True)
class SavedLine:
    id: int
    counter: str
    scenario: str
    period: int
    target_frequency: int
    visible: bool
    push_enabled: bool = True
    email_enabled: bool = False
    custom_name: str = ""
    # Per-line signal types (0.14.1). Each also needs its global Settings type
    # and the line's phone switch. Upgrades default On, so behaviour is kept.
    alert_buy: bool = True
    alert_monitor: bool = True
    alert_start: bool = True

    def alert_enabled(self, kind):
        return {"buy": self.alert_buy, "monitor": self.alert_monitor,
                "monitor_start": self.alert_start}[kind]

    @property
    def display_name(self):
        return self.custom_name or sma_label(self.period)


ALERT_COLUMNS = ("alert_buy", "alert_monitor", "alert_start")
ALERT_KIND_COLUMNS = {"buy": "alert_buy", "monitor": "alert_monitor", "monitor_start": "alert_start"}
LINE_COLUMNS = ("id,counter,scenario,period,target_frequency,visible,push_enabled,email_enabled,custom_name,"
                + ",".join(ALERT_COLUMNS))


def _line(row):
    return SavedLine(*row[:5], *map(bool, row[5:8]), row[8], *map(bool, row[9:12]))


class LineStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            # The UI and a native daily worker may open an upgraded database
            # together. Serialize schema inspection and additive migrations.
            connection.execute("BEGIN IMMEDIATE")
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
                    default = 1 if name == "push_enabled" else 0
                    connection.execute(f"ALTER TABLE saved_lines ADD COLUMN {name} INTEGER NOT NULL DEFAULT {default} CHECK({name} IN (0,1))")
            connection.execute("""CREATE TABLE IF NOT EXISTS unsaved_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT, counter TEXT NOT NULL,
                scenario TEXT NOT NULL, period INTEGER NOT NULL, target_frequency INTEGER NOT NULL,
                visible INTEGER NOT NULL, push_enabled INTEGER NOT NULL, email_enabled INTEGER NOT NULL,
                data_version INTEGER NOT NULL)""")
            for table in ("saved_lines","unsaved_lines"):
                columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
                if "custom_name" not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN custom_name TEXT NOT NULL DEFAULT ''")
                for name in ALERT_COLUMNS:
                    if name not in columns:
                        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} INTEGER NOT NULL DEFAULT 1 CHECK({name} IN (0,1))")
            connection.execute("CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS deliveries (event_key TEXT PRIMARY KEY)")
            connection.execute("""CREATE TABLE IF NOT EXISTS notification_runs (
                region TEXT NOT NULL, due_at INTEGER NOT NULL, started_at REAL NOT NULL,
                status TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', completed_at REAL,
                PRIMARY KEY(region,due_at))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS sma_colors (
                counter TEXT NOT NULL, scenario TEXT NOT NULL, period INTEGER NOT NULL,
                color_index INTEGER NOT NULL, PRIMARY KEY(counter,scenario,period))""")
            color_columns={row[1] for row in connection.execute("PRAGMA table_info(sma_colors)")}
            if "custom_color" not in color_columns:
                connection.execute("ALTER TABLE sma_colors ADD COLUMN custom_color INTEGER "
                                   "CHECK(custom_color IS NULL OR custom_color BETWEEN 0 AND 11)")
            connection.execute("""CREATE TABLE IF NOT EXISTS analysis_choices (
                counter TEXT NOT NULL, scenario TEXT NOT NULL, target INTEGER NOT NULL,
                fingerprint TEXT NOT NULL, period INTEGER NOT NULL,
                PRIMARY KEY(counter,scenario,target,fingerprint))""")
            # Upgrade in original save order; the first saved period stays amber.
            rows = connection.execute("SELECT counter,scenario,period FROM saved_lines ORDER BY id").fetchall()
            for counter,scenario,period in rows:
                self._allocate_color(connection,counter,scenario,period)

    @contextmanager
    def _connect(self):
        # sqlite's transaction context commits/rolls back but does not close itself.
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                yield connection

    def list_lines(self, counter: str, scenario: str) -> list[SavedLine]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {LINE_COLUMNS} "
                "FROM saved_lines WHERE counter=? AND scenario=? AND data_version=? ORDER BY id",
                (counter, scenario, DATA_VERSION),
            ).fetchall()
        return [_line(row) for row in rows]

    def list_all_lines(self) -> list[SavedLine]:
        """Landing-page library: all counters/scenarios, including hidden lines."""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {LINE_COLUMNS} "
                "FROM saved_lines WHERE data_version=? ORDER BY counter,scenario,id",
                (DATA_VERSION,),
            ).fetchall()
        return [_line(row) for row in rows]

    def get_line(self, line_id: int) -> SavedLine:
        line = next((line for line in self.list_all_lines() if line.id == line_id), None)
        if line is None:
            raise ValueError("This SMA is no longer saved. Choose another saved line.")
        return line

    def save(self, counter: str, scenario: str, period: int, target: int) -> None:
        with self._connect() as connection:
            self._allocate_color(connection,counter,scenario,period)
            archived = connection.execute("SELECT custom_name,push_enabled,"+",".join(ALERT_COLUMNS)+
                " FROM unsaved_lines WHERE counter=? AND scenario=? "
                "AND period=? AND target_frequency=? AND data_version=?",(counter,scenario,period,target,DATA_VERSION)).fetchone()
            connection.execute(
                "INSERT INTO saved_lines(counter, scenario, period, target_frequency, data_version,custom_name,push_enabled,"
                + ",".join(ALERT_COLUMNS) + ") "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(counter, scenario, period, target_frequency, "
                "data_version) DO NOTHING",
                (counter, scenario, period, target, DATA_VERSION, *(archived or ("", 1, 1, 1, 1))),
            )

            connection.execute("DELETE FROM unsaved_lines WHERE counter=? AND scenario=? AND period=? "
                               "AND target_frequency=? AND data_version=?",
                               (counter, scenario, period, target, DATA_VERSION))

    def set_visible(self, line_id: int, visible: bool) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE saved_lines SET visible=? WHERE id=?", (int(visible), line_id))

    def rename(self,line_id,name):
        name = normalize_name(name)
        with self._connect() as connection:
            changed = connection.execute("UPDATE saved_lines SET custom_name=? WHERE id=?",(name,line_id)).rowcount
            if not changed:
                raise ValueError("This SMA is no longer saved.")
        return name

    def delete(self, line_id: int) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT counter,scenario,period,target_frequency,visible,push_enabled,email_enabled,custom_name,"
                + ",".join(ALERT_COLUMNS) + ",data_version FROM saved_lines WHERE id=?", (line_id,)).fetchone()
            if row is None:
                return
            connection.execute("DELETE FROM unsaved_lines WHERE counter=? AND scenario=? AND period=? "
                               "AND target_frequency=? AND data_version=?", (*row[:4], row[-1]))
            connection.execute("INSERT INTO unsaved_lines(counter,scenario,period,target_frequency,visible,"
                               "push_enabled,email_enabled,custom_name," + ",".join(ALERT_COLUMNS) +
                               ",data_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
            connection.execute("DELETE FROM unsaved_lines WHERE id NOT IN "
                               "(SELECT id FROM unsaved_lines ORDER BY id DESC LIMIT 10)")
            connection.execute("DELETE FROM saved_lines WHERE id=?", (line_id,))

    def recent_unsaved(self) -> list[SavedLine]:
        """Most recent 10 unique unsaved configurations, across counters/scenarios."""
        with self._connect() as connection:
            rows = connection.execute(f"SELECT {LINE_COLUMNS} FROM unsaved_lines "
                                      "WHERE data_version=? ORDER BY id DESC", (DATA_VERSION,)).fetchall()
        return [_line(row) for row in rows]

    def restore(self, history_id: int):
        with self._connect() as connection:
            row = connection.execute("SELECT counter,scenario,period,target_frequency,visible,push_enabled,"
                                     "email_enabled,custom_name," + ",".join(ALERT_COLUMNS) +
                                     ",data_version FROM unsaved_lines WHERE id=? AND data_version=?",
                                     (history_id, DATA_VERSION)).fetchone()
            if row is None:
                raise ValueError("This unsaved line is no longer in the last 10 entries.")
            if row[6] and not self.notification_settings().email:
                raise ValueError("Save your email address in Settings before restoring an email-enabled line.")
            connection.execute("INSERT INTO saved_lines(counter,scenario,period,target_frequency,visible,"
                               "push_enabled,email_enabled,custom_name," + ",".join(ALERT_COLUMNS) +
                               ",data_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
                               "ON CONFLICT(counter,scenario,period,target_frequency,data_version) DO NOTHING", row)
            connection.execute("DELETE FROM unsaved_lines WHERE id=?", (history_id,))
            self._allocate_color(connection,*row[:3])

    @staticmethod
    def _allocate_color(connection,counter,scenario,period):
        row = connection.execute("SELECT color_index FROM sma_colors WHERE counter=? AND scenario=? AND period=?",
                                 (counter,scenario,period)).fetchone()
        if row:
            return row[0]
        index = connection.execute("SELECT COALESCE(MAX(color_index),-1)+1 FROM sma_colors "
                                   "WHERE counter=? AND scenario=?", (counter,scenario)).fetchone()[0]
        connection.execute("INSERT INTO sma_colors(counter,scenario,period,color_index) VALUES (?,?,?,?)",
                           (counter,scenario,period,index))
        return index

    def color_index(self,counter,scenario,period):
        with self._connect() as connection:
            row = connection.execute("SELECT color_index,custom_color FROM sma_colors WHERE counter=? AND scenario=? AND period=?",
                                     (counter,scenario,period)).fetchone()
            if row:
                return -row[1]-1 if row[1] is not None else row[0]
            return connection.execute("SELECT COALESCE(MAX(color_index),-1)+1 FROM sma_colors "
                                      "WHERE counter=? AND scenario=?", (counter,scenario)).fetchone()[0]

    def set_color(self,line_id,choice):
        if isinstance(choice,bool) or not isinstance(choice,int) or not 0<=choice<len(COLOR_CHOICES):
            raise ValueError("Choose one of the 12 SMA colours.")
        with self._connect() as connection:
            row=connection.execute("SELECT counter,scenario,period FROM saved_lines WHERE id=? AND data_version=?",
                                   (line_id,DATA_VERSION)).fetchone()
            if row is None:
                raise ValueError("This SMA is no longer saved.")
            self._allocate_color(connection,*row)
            connection.execute("UPDATE sma_colors SET custom_color=? WHERE counter=? AND scenario=? AND period=?",
                               (choice,*row))

    def cache_choice(self,counter,scenario,target,fingerprint,period):
        with self._connect() as connection:
            connection.execute("INSERT INTO analysis_choices VALUES (?,?,?,?,?) ON CONFLICT "
                               "(counter,scenario,target,fingerprint) DO UPDATE SET period=excluded.period",
                               (counter,scenario,target,fingerprint,period))

    def cached_choice(self,counter,scenario,target,fingerprint):
        with self._connect() as connection:
            row = connection.execute("SELECT period FROM analysis_choices WHERE counter=? AND scenario=? "
                                     "AND target=? AND fingerprint=?", (counter,scenario,target,fingerprint)).fetchone()
        return row[0] if row else None

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

    def set_line_alert(self, line_id: int, kind: str, enabled: bool):
        """Turn one signal type on/off for one saved line; identity is unchanged."""
        column = ALERT_KIND_COLUMNS.get(kind)
        if column is None:
            raise ValueError("Choose Buy signal or an Impending buy signal type.")
        with self._connect() as connection:
            if not connection.execute(f"UPDATE saved_lines SET {column}=? WHERE id=?", (int(bool(enabled)), line_id)).rowcount:
                raise ValueError("This SMA is no longer saved.")

    def was_delivered(self, key: str) -> bool:
        with self._connect() as connection:
            return connection.execute("SELECT 1 FROM deliveries WHERE event_key=?", (key,)).fetchone() is not None

    def record_delivery(self, key: str):
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO deliveries(event_key) VALUES (?)", (key,))

    def claim_notification_run(self,region,due_at,now):
        with self._connect() as connection:
            return bool(connection.execute("INSERT OR IGNORE INTO notification_runs "
                "(region,due_at,started_at,status) VALUES (?,?,?,'running')",(region,int(due_at),now)).rowcount)

    def finish_notification_run(self,region,due_at,now,status,detail):
        with self._connect() as connection:
            connection.execute("UPDATE notification_runs SET completed_at=?,status=?,detail=? WHERE region=? AND due_at=?",
                               (now,status,detail,region,int(due_at)))
