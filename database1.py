import sqlite3


DB_PATH = "bot.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                refs INTEGER DEFAULT 0,
                referred_by INTEGER,
                status TEXT DEFAULT 'MEHMON',
                pending_deposit INTEGER DEFAULT 0,
                pending_status TEXT,
                first_deposit_done INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS mandatory_channels (channel_id TEXT PRIMARY KEY)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS bonus_channels (channel_id TEXT PRIMARY KEY, bonus INTEGER)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, limit_count INTEGER)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS promo_history (user_id INTEGER, code TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS bonus_history (user_id INTEGER, channel_id TEXT)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_text TEXT,
                status TEXT DEFAULT 'pending'
            )
            """
        )
        conn.commit()


def add_user(user_id: int, referrer_id: int | None = None) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, referred_by) VALUES (?, ?)",
            (user_id, referrer_id),
        )
        conn.commit()


def get_user(user_id: int) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def add_admin(user_id: int) -> None:
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()


def remove_admin(user_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()


def is_admin(user_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None


def set_pending_deposit(user_id: int, amount: int, status: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET pending_deposit = ?, pending_status = ? WHERE user_id = ?",
            (amount, status, user_id),
        )
        conn.commit()


def confirm_deposit(user_id: int) -> sqlite3.Row | None:
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user or user["pending_deposit"] <= 0:
            return None
        conn.execute(
            "UPDATE users SET balance = balance + ?, pending_deposit = 0, pending_status = NULL "
            "WHERE user_id = ?",
            (user["pending_deposit"], user_id),
        )
        conn.commit()
        return user


def mark_first_deposit(user_id: int, status: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET first_deposit_done = 1, status = ?, pending_status = NULL WHERE user_id = ?",
            (status, user_id),
        )
        conn.commit()
