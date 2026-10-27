import os
import json
import datetime
from pathlib import Path
import aiosqlite

CONFIG_PATH = Path("configs/servers_config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
    data_config = json.load(config_file)

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data" if Path("/app/data").exists() else "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
GLOBAL_DB_PATH = DATA_DIR / data_config["global"]["data"]
PRAISE_DB_PATH = DATA_DIR / data_config.get("praise", {}).get("data", "praise_data.db")

ALLOWED_GLOBAL_COLUMNS = {"global_role", "rating"}
ALLOWED_AETHERIAL_COLUMNS = {"local_role", "pass", "wipes"}
DB_TIMEOUT_SECONDS = 30.0


def connect_db(db_path: Path):
    """Создает подключение к базе данных с увеличенным таймаутом для предотвращения блокировок."""
    return aiosqlite.connect(db_path, timeout=DB_TIMEOUT_SECONDS)


async def init_dbs():
    """Инициализация всех баз данных проекта с оптимизацией конкурентного доступа (WAL-режим)."""
    await init_global_db()
    await init_aetherial_db()
    await init_praise_db()



    #
    # ГЛОБАЛЬНАЯ БАЗА ДАННЫХ
    #

async def init_global_db():
    async with connect_db(GLOBAL_DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=30000;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                global_role TEXT DEFAULT NULL,
                rating INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reputations (
                actor_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                last_rated INTEGER DEFAULT 0,
                PRIMARY KEY (actor_id, target_id)
            )
        """)
        await db.commit()


async def get_user_info(user_id: int, info_type: str):
    if info_type not in ALLOWED_GLOBAL_COLUMNS:
        raise ValueError(f"Недопустимое поле: {info_type}")
    async with connect_db(GLOBAL_DB_PATH) as db:
        async with db.execute(
            f"SELECT {info_type} FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]

            await db.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
            )
            await db.commit()
            return None


async def update_user_info(user_id: int, info_type: str, amount):
    if info_type not in ALLOWED_GLOBAL_COLUMNS:
        raise ValueError(f"Недопустимое поле: {info_type}")
    async with connect_db(GLOBAL_DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        await db.execute(
            f"UPDATE users SET {info_type} = ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()



    #
    # AETHERIAL - ЛОКАЛЬНАЯ БАЗА ДАННЫХ
    #

async def init_aetherial_db():
    aetherial_path = DATA_DIR / data_config["aetherial"]["data"]
    async with connect_db(aetherial_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=30000;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                local_role TEXT DEFAULT NULL,
                pass INTEGER DEFAULT 0,
                wipes TEXT DEFAULT NULL
            )
        """)
        await db.commit()


async def get_aetherial_user_info(user_id: int, info_type: str):
    if info_type not in ALLOWED_AETHERIAL_COLUMNS:
        raise ValueError(f"Недопустимое поле: {info_type}")
    aetherial_path = DATA_DIR / data_config["aetherial"]["data"]
    async with connect_db(aetherial_path) as db:
        async with db.execute(
            f"SELECT {info_type} FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]

            await db.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
            )
            await db.commit()
            return 0


async def update_aetherial_user_info(user_id: int, info_type: str, amount):
    if info_type not in ALLOWED_AETHERIAL_COLUMNS:
        raise ValueError(f"Недопустимое поле: {info_type}")
    aetherial_path = DATA_DIR / data_config["aetherial"]["data"]
    async with connect_db(aetherial_path) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        await db.execute(
            f"UPDATE users SET {info_type} = ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()


async def get_aetherial_user_with_role(role: str):
    aetherial_path = DATA_DIR / data_config["aetherial"]["data"]
    async with connect_db(aetherial_path) as db:
        async with db.execute(
            "SELECT user_id FROM users WHERE local_role = ?", (role,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]



    #
    # PRAISE (ПОХВАЛА) - БАЗА ДАННЫХ
    #

def get_start_of_day_msk_timestamp() -> int:
    """Возвращает timestamp начала текущих суток по Московскому времени (00:00:00 MSK)."""
    msk_tz = datetime.timezone(datetime.timedelta(hours=3))
    now = datetime.datetime.now(msk_tz)
    start_of_day = datetime.datetime(now.year, now.month, now.day, tzinfo=msk_tz)
    return int(start_of_day.timestamp())


async def init_praise_db():
    """Инициализация базы данных похвал с индексами и WAL-режимом."""
    async with connect_db(PRAISE_DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA busy_timeout=30000;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS praises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                phrase TEXT DEFAULT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_praises_actor_time ON praises(actor_id, timestamp)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_praises_actor_target ON praises(actor_id, target_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_praises_target ON praises(target_id)
        """)
        await db.commit()


async def check_praise_availability(actor_id: int, target_id: int) -> tuple[bool, str, dict]:
    """Проверяет возможность похвалить пользователя согласно лимитам:
    
    1. Не более 3 разных людей за 1 день (сброс в 00:00 по МСК).
    2. Не более 3 раз за день одного и того же человека.
    3. Минимум 5 минут между похвалами одного и того же человека.
    """
    if actor_id == target_id:
        return False, "Нельзя похвалить самого себя! :)", {}

    start_of_day = get_start_of_day_msk_timestamp()
    now_ts = int(datetime.datetime.now().timestamp())

    async with connect_db(PRAISE_DB_PATH) as db:
        # Уникальные пользователи, которых похвалил актор сегодня
        async with db.execute(
            "SELECT DISTINCT target_id FROM praises WHERE actor_id = ? AND timestamp >= ?",
            (actor_id, start_of_day),
        ) as cursor:
            rows = await cursor.fetchall()
            distinct_targets = {row[0] for row in rows}

        if target_id not in distinct_targets and len(distinct_targets) >= 3:
            return False, "Вы уже похвалили максимальное количество участников за сегодня (3/3). Лимит сбросится в 00:00 по МСК!", {}

        # Сколько раз хвалил именно эту цель сегодня и когда в последний раз
        async with db.execute(
            "SELECT COUNT(*), MAX(timestamp) FROM praises WHERE actor_id = ? AND target_id = ? AND timestamp >= ?",
            (actor_id, target_id, start_of_day),
        ) as cursor:
            row = await cursor.fetchone()
            count_today = row[0] if row else 0
            max_ts = row[1] if row else None

        if count_today >= 3:
            return False, "Вы уже похвалили этого участника 3 раза за сегодня! Лимит похвал для него сбросится в 00:00 по МСК.", {}

        if max_ts is not None and (now_ts - max_ts) < 300:
            remaining = 300 - (now_ts - max_ts)
            mins = remaining // 60
            secs = remaining % 60
            return False, f"Вы недавно хвалили этого участника! Подождите еще **{mins} мин. {secs} сек.** (КД 5 минут).", {}

        new_distinct_count = len(distinct_targets) if target_id in distinct_targets else len(distinct_targets) + 1

        return True, "OK", {
            "today_target_count": count_today + 1,
            "today_distinct_count": new_distinct_count,
        }


async def add_praise(actor_id: int, target_id: int, phrase: str | None = None) -> dict:
    """Записывает похвалу в базу данных и возвращает обновленную статистику."""
    start_of_day = get_start_of_day_msk_timestamp()
    now_ts = int(datetime.datetime.now().timestamp())

    async with connect_db(PRAISE_DB_PATH) as db:
        await db.execute(
            "INSERT INTO praises (actor_id, target_id, timestamp, phrase) VALUES (?, ?, ?, ?)",
            (actor_id, target_id, now_ts, phrase),
        )
        await db.commit()

        # Общее количество полученных похвал целью за все время
        async with db.execute(
            "SELECT COUNT(*) FROM praises WHERE target_id = ?",
            (target_id,),
        ) as cursor:
            row = await cursor.fetchone()
            total_target_praises = row[0] if row else 1

        # Сколько раз похвалил эту цель сегодня
        async with db.execute(
            "SELECT COUNT(*) FROM praises WHERE actor_id = ? AND target_id = ? AND timestamp >= ?",
            (actor_id, target_id, start_of_day),
        ) as cursor:
            row = await cursor.fetchone()
            today_target_count = row[0] if row else 1

        # Сколько уникальных людей похвалил сегодня
        async with db.execute(
            "SELECT COUNT(DISTINCT target_id) FROM praises WHERE actor_id = ? AND timestamp >= ?",
            (actor_id, start_of_day),
        ) as cursor:
            row = await cursor.fetchone()
            today_distinct_count = row[0] if row else 1

        return {
            "total_target_praises": total_target_praises,
            "today_target_count": today_target_count,
            "today_distinct_count": today_distinct_count,
            "timestamp": now_ts,
        }


async def get_user_praise_stats(user_id: int) -> dict:
    """Возвращает статистику похвал пользователя (получено и отдано)."""
    start_of_day = get_start_of_day_msk_timestamp()

    async with connect_db(PRAISE_DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM praises WHERE target_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            total_received = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM praises WHERE actor_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            total_given = row[0] if row else 0

        async with db.execute(
            "SELECT COUNT(*) FROM praises WHERE target_id = ? AND timestamp >= ?",
            (user_id, start_of_day),
        ) as cursor:
            row = await cursor.fetchone()
            today_received = row[0] if row else 0

        async with db.execute(
            "SELECT COUNT(DISTINCT target_id) FROM praises WHERE actor_id = ? AND timestamp >= ?",
            (user_id, start_of_day),
        ) as cursor:
            row = await cursor.fetchone()
            today_distinct = row[0] if row else 0

        return {
            "total_received": total_received,
            "total_given": total_given,
            "today_received": today_received,
            "today_distinct": today_distinct,
        }
