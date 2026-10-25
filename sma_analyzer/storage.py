"""Small parameterized SQLite store. No service, ORM, or global connection."""
from dataclasses import dataclass
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3

from .settings import DATA_VERSION


@dataclass(frozen=True)
class SavedLine:
    id: int
    counter: str
    scenario: str
    period: int
    target_frequency: int
    visible: bool


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

    @contextmanager
    def _connect(self):
        # sqlite's transaction context commits/rolls back but does not close itself.
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                yield connection

    def list_lines(self, counter: str, scenario: str) -> list[SavedLine]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, counter, scenario, period, target_frequency, visible "
                "FROM saved_lines WHERE counter=? AND scenario=? AND data_version=? ORDER BY id",
                (counter, scenario, DATA_VERSION),
            ).fetchall()
        return [SavedLine(*row[:5], bool(row[5])) for row in rows]

    def save(self, counter: str, scenario: str, period: int, target: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO saved_lines(counter, scenario, period, target_frequency, data_version) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(counter, scenario, period, target_frequency, "
                "data_version) DO NOTHING",
                (counter, scenario, period, target, DATA_VERSION),
            )

    def set_visible(self, line_id: int, visible: bool) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE saved_lines SET visible=? WHERE id=?", (int(visible), line_id))

    def delete(self, line_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM saved_lines WHERE id=?", (line_id,))
