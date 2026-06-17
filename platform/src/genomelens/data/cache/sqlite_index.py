"""小型 SQLite cache index(缓存索引)，预留给后续 fingerprint(指纹) 复用"""

# region import
from __future__ import annotations

import sqlite3
from pathlib import Path

# endregion


def initialize_cache(path: str | Path) -> Path:
    """按需创建缓存数据库 schema(结构)"""

    db_path = Path(path).expanduser().resolve(strict=False)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        # 当前只保留最小 fingerprints 表，为后续缓存复用/跳过重复计算预留位置。
        con.execute(
            "CREATE TABLE IF NOT EXISTS fingerprints ("
            "key TEXT PRIMARY KEY, "
            "value TEXT NOT NULL, "
            "updated_at TEXT NOT NULL"
            ")"
        )
    return db_path
