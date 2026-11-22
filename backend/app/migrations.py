from uuid import uuid4

from sqlalchemy import text

from app.database import engine


def ensure_current_schema():
    """Kurulumda mevcut SQLite dosyasına eğitim için gerekli küçük alan eklerini uygular."""
    with engine.begin() as connection:
        table_names = {
            row[0]
            for row in connection.execute(text(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ))
        }

        if "users" in table_names:
            user_columns = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(users)"))
            }
            if "password_hash" not in user_columns:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"
                ))
            if "is_verified" not in user_columns:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0"
                ))

        for table_name in ("users", "shops", "orders"):
            if table_name not in table_names:
                continue
            columns = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info({table_name})"))
            }
            if "public_id" not in columns:
                connection.execute(text(
                    f"ALTER TABLE {table_name} ADD COLUMN public_id VARCHAR(36)"
                ))
            rows = connection.execute(
                text(f"SELECT id FROM {table_name} WHERE public_id IS NULL")
            ).fetchall()
            for (record_id,) in rows:
                connection.execute(
                    text(f"UPDATE {table_name} SET public_id = :public_id WHERE id = :id"),
                    {"public_id": str(uuid4()), "id": record_id},
                )
