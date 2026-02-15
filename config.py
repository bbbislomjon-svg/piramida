import os


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    if not value.isdigit():
        raise ValueError(f"{name} must be an integer.")
    return int(value)


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required. Set it in environment variables.")

ADMIN_ID = _get_env_int("ADMIN_ID", 0)

CARD_NUMBER = os.getenv("CARD_NUMBER", "5614681621153729")
CARD_HOLDER = os.getenv("CARD_HOLDER", "Bafoyev.I")

MIN_WITHDRAW = _get_env_int("MIN_WITHDRAW", 15000)
FIRST_DEPOSIT_BONUS = _get_env_int("FIRST_DEPOSIT_BONUS", 0)

TARIFFS = {
    "BASIC": {"amount": 10000, "ref_bonus": 1000},
    "PRO": {"amount": 20000, "ref_bonus": 2500},
    "ELITE": {"amount": 35000, "ref_bonus": 3200},
}
