import sqlite3
import time
from pathlib import Path
from typing import Optional

class DatabaseLogger:
    """
    Класс для логирования взаимодействий пользователя с RAG-ассистентом в SQLite.
    """

    def __init__(self, db_path: str = "logs.db"):
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self) -> None:
        """Создает таблицу для логов, если она еще не существует."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    query TEXT,
                    response TEXT,
                    source TEXT,
                    from_cache BOOLEAN DEFAULT 0,
                    response_time_ms INTEGER,
                    status TEXT DEFAULT 'success'
                )
            """)
            conn.commit()

    def log_interaction(
        self,
        user_id: int,
        query: str,
        response: str,
        source: str = "rag",
        from_cache: bool = False,
        response_time_ms: int = 0,
        status: str = "success"
    ) -> None:
        """Записывает одно взаимодействие в базу данных."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO interactions (user_id, query, response, source, from_cache, response_time_ms, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, query, response, source, from_cache, response_time_ms, status))
                conn.commit()
        except Exception as e:
            print(f"Ошибка записи в лог: {e}")

    def get_stats(self) -> dict:
        """Возвращает базовую статистику по логам."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM interactions")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(response_time_ms) FROM interactions WHERE status = 'success'")
            avg_time_row = cursor.fetchone()
            avg_time = avg_time_row[0] if avg_time_row[0] else 0
            
            return {
                "total_interactions": total,
                "avg_response_time_ms": round(avg_time, 2)
            }
