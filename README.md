# Telegram Invest Bot (aiogram)

This bot uses polling mode and stores data in a local SQLite database (`bot.db`).

## ✅ PythonAnywhere quick start

1. **Upload project** to PythonAnywhere (or clone the repo).
2. Create a virtualenv and install deps:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Set environment variables** (in the PythonAnywhere dashboard or in a `.bashrc` for your task):

```bash
export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
export ADMIN_ID="123456789"  # main admin Telegram ID
export CARD_NUMBER="5614..."
export CARD_HOLDER="Ism Familiya"
export MIN_WITHDRAW="15000"
export FIRST_DEPOSIT_BONUS="0"
```

4. **Run the bot** from the console (or create an Always-on task):

```bash
source venv/bin/activate
python main.py
```

## Notes

- `ADMIN_ID` is the main owner. You can add extra admins from the Admin Panel.
- The database file is `bot.db` in the project directory.
- If you use Always-on Tasks, make sure the working directory is the project root.

