from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from database import add_admin, confirm_deposit, get_db, is_admin, mark_first_deposit, remove_admin

router = Router()


class AdminStates(StatesGroup):
    wait_broadcast = State()
    wait_mand_add = State()
    wait_mand_del = State()
    wait_bonus_add = State()
    wait_bonus_del = State()
    wait_promo_add = State()
    wait_promo_del = State()
    wait_confirm_deposit = State()
    wait_confirm_withdraw = State()
    wait_add_admin = State()
    wait_del_admin = State()


def has_admin_access(user_id: int) -> bool:
    return user_id == config.ADMIN_ID or is_admin(user_id)


admin_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Majburiy kanallar", callback_data="admin_mandatory")],
        [InlineKeyboardButton(text="🎁 Bonus kanallar", callback_data="admin_bonus")],
        [InlineKeyboardButton(text="💳 Depozitlar", callback_data="admin_deposits")],
        [InlineKeyboardButton(text="💸 Pul yechish", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="🏷 Promokodlar", callback_data="admin_promos")],
        [InlineKeyboardButton(text="👤 Adminlar", callback_data="admin_staff")],
        [InlineKeyboardButton(text="📣 Reklama yuborish", callback_data="admin_broadcast")],
    ]
)


@router.message(Command("admin"))
async def admin_panel(msg: Message) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    await msg.answer(
        "🛠 <b>ADMIN PANEL</b>\n\nBoshqaruv bo‘limini tanlang 👇",
        reply_markup=admin_kb,
        parse_mode="HTML",
    )


@router.message(F.text == "🛠 Admin panel")
async def admin_panel_button(msg: Message) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    await admin_panel(msg)


@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    db = get_db()
    u_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_bal = db.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
    total_pending = (
        db.execute("SELECT SUM(pending_deposit) FROM users").fetchone()[0] or 0
    )
    text = (
        "📊 <b>STATISTIKA</b>\n\n"
        f"👥 Foydalanuvchilar: {u_count}\n"
        f"💰 Jami balanslar: {total_bal:,} so'm\n"
        f"⏳ Kutilayotgan depozitlar: {total_pending:,} so'm"
    )
    await call.message.edit_text(text, reply_markup=admin_kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_mandatory")
async def mandatory_list(call: CallbackQuery) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    db = get_db()
    rows = db.execute("SELECT * FROM mandatory_channels").fetchall()
    text = "📢 <b>Majburiy kanallar:</b>\n\n"
    for r in rows:
        text += f"• <code>{r['channel_id']}</code>\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="mand_add")],
            [InlineKeyboardButton(text="➖ Kanal o'chirish", callback_data="mand_del")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "mand_add")
async def add_mand_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_mand_add)
    await call.message.answer("➕ Kanal username yuboring (masalan: @kanal):")


@router.callback_query(F.data == "mand_del")
async def del_mand_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_mand_del)
    await call.message.answer("➖ O'chiriladigan kanal username yuboring (masalan: @kanal):")


@router.message(AdminStates.wait_mand_add)
async def add_mand(msg: Message, state: FSMContext) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    ch_id = msg.text.strip()
    db = get_db()
    db.execute("INSERT OR REPLACE INTO mandatory_channels VALUES (?)", (ch_id,))
    db.commit()
    await state.clear()
    await msg.answer(f"✅ {ch_id} qo'shildi.", reply_markup=admin_kb)


@router.message(AdminStates.wait_mand_del)
async def del_mand(msg: Message, state: FSMContext) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    ch_id = msg.text.strip()
    db = get_db()
    db.execute("DELETE FROM mandatory_channels WHERE channel_id=?", (ch_id,))
    db.commit()
    await state.clear()
    await msg.answer(f"🗑 {ch_id} o'chirildi.", reply_markup=admin_kb)


@router.callback_query(F.data == "admin_bonus")
async def bonus_list(call: CallbackQuery) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    db = get_db()
    rows = db.execute("SELECT * FROM bonus_channels").fetchall()
    text = "🎁 <b>Bonus kanallar:</b>\n\n"
    for r in rows:
        text += f"• {r['channel_id']} ({r['bonus']} so'm)\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Bonus kanal qo'shish", callback_data="bonus_add")],
            [InlineKeyboardButton(text="➖ Bonus kanal o'chirish", callback_data="bonus_del")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "bonus_add")
async def add_bonus_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_bonus_add)
    await call.message.answer("➕ Format: @kanal 500")


@router.callback_query(F.data == "bonus_del")
async def del_bonus_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_bonus_del)
    await call.message.answer("➖ O'chiriladigan kanal username yuboring (masalan: @kanal):")


@router.message(AdminStates.wait_bonus_add)
async def add_bonus_cmd(msg: Message, state: FSMContext) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❌ Format: @kanal 500")
        return
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO bonus_channels VALUES (?, ?)",
        (args[0], int(args[1])),
    )
    db.commit()
    await state.clear()
    await msg.answer(f"✅ {args[0]} ({args[1]} so'm) qo'shildi.", reply_markup=admin_kb)


@router.message(AdminStates.wait_bonus_del)
async def del_bonus_cmd(msg: Message, state: FSMContext) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    ch_id = msg.text.strip()
    db = get_db()
    db.execute("DELETE FROM bonus_channels WHERE channel_id=?", (ch_id,))
    db.commit()
    await state.clear()
    await msg.answer(f"🗑 {ch_id} o'chirildi.", reply_markup=admin_kb)


@router.callback_query(F.data == "admin_promos")
async def promo_list(call: CallbackQuery) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    db = get_db()
    rows = db.execute("SELECT * FROM promos").fetchall()
    text = "🏷 <b>Promokodlar:</b>\n\n"
    for r in rows:
        text += f"• <code>{r['code']}</code> | {r['amount']} so'm | {r['limit_count']} ta\n"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Promokod qo'shish", callback_data="promo_add")],
            [InlineKeyboardButton(text="➖ Promokod o'chirish", callback_data="promo_del")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "promo_add")
async def add_promo_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_promo_add)
    await call.message.answer("➕ Format: CODE SUMMA LIMIT")


@router.callback_query(F.data == "promo_del")
async def del_promo_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_promo_del)
    await call.message.answer("➖ O'chiriladigan promokod nomini yuboring:")


@router.message(AdminStates.wait_promo_add)
async def add_promo_cmd(msg: Message, state: FSMContext) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) < 3:
        await msg.answer("❌ Format: CODE SUMMA LIMIT")
        return
    db = get_db()
    db.execute(
        "INSERT INTO promos VALUES (?, ?, ?)",
        (args[0], int(args[1]), int(args[2])),
    )
    db.commit()
    await state.clear()
    await msg.answer(f"✅ Promokod {args[0]} yaratildi.", reply_markup=admin_kb)


@router.message(AdminStates.wait_promo_del)
async def del_promo_cmd(msg: Message, state: FSMContext) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    code = msg.text.strip()
    db = get_db()
    db.execute("DELETE FROM promos WHERE code = ?", (code,))
    db.commit()
    await state.clear()
    await msg.answer(f"🗑 Promokod {code} o'chirildi.", reply_markup=admin_kb)


@router.callback_query(F.data == "admin_deposits")
async def dep_list(call: CallbackQuery) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    db = get_db()
    rows = db.execute(
        "SELECT user_id, pending_deposit, pending_status FROM users WHERE pending_deposit > 0"
    ).fetchall()
    text = "💳 <b>Depozitlar:</b>\n"

    if not rows:
        await call.message.edit_text("Bo'sh", reply_markup=admin_kb, parse_mode="HTML")
        return

    for r in rows:
        text += (
            f"\n🆔 <code>{r['user_id']}</code> | {r['pending_deposit']} so'm"
            f"\nTarif: {r['pending_status']}\n"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="deposit_confirm_start")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "deposit_confirm_start")
async def confirm_deposit_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_confirm_deposit)
    await call.message.answer("✅ Tasdiqlash uchun foydalanuvchi ID yuboring:")


@router.callback_query(F.data.startswith("adm_ok_"))
async def confirm_deposit_callback(call: CallbackQuery, bot: Bot) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    user_id = int(call.data.split("_")[2])
    user = confirm_deposit(user_id)
    if not user:
        await call.answer("❌ Depozit topilmadi.", show_alert=True)
        return

    if user["first_deposit_done"] == 0 and user["pending_status"]:
        status = user["pending_status"]
        ref_bonus = config.TARIFFS[status]["ref_bonus"]
        db = get_db()
        if user["referred_by"]:
            db.execute(
                "UPDATE users SET balance = balance + ?, refs = refs + 1 WHERE user_id = ?",
                (ref_bonus, user["referred_by"]),
            )
        if config.FIRST_DEPOSIT_BONUS > 0:
            db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (config.FIRST_DEPOSIT_BONUS, user_id),
            )
        db.commit()
        mark_first_deposit(user_id, status)

    await call.message.edit_caption("✅ Depozit tasdiqlandi.")
    await bot.send_message(user_id, "✅ Depozitingiz tasdiqlandi, balansingiz yangilandi.")


@router.callback_query(F.data == "admin_withdraws")
async def with_list(call: CallbackQuery) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    db = get_db()
    rows = db.execute(
        "SELECT id, user_id, amount, card_text FROM withdrawals WHERE status = 'pending'"
    ).fetchall()
    text = "💸 <b>Yechish so'rovlari:</b>\n"

    if not rows:
        await call.message.edit_text("Bo'sh", reply_markup=admin_kb, parse_mode="HTML")
        return

    for r in rows:
        text += (
            f"\n🆔 <code>{r['user_id']}</code> | {r['amount']} so'm"
            f"\nKarta: {r['card_text']}\n"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="withdraw_confirm_start")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "withdraw_confirm_start")
async def confirm_withdraw_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_confirm_withdraw)
    await call.message.answer("✅ Tasdiqlash uchun so'rov ID yuboring:")


@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_broadcast)
    await call.message.answer("📣 Reklama xabarini yuboring (Rasm, Video yoki Matn):")


@router.message(AdminStates.wait_broadcast)
async def broadcast_finish(msg: Message, state: FSMContext, bot: Bot) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    db = get_db()
    users = db.execute("SELECT user_id FROM users").fetchall()
    count = 0
    for u in users:
        try:
            await msg.copy_to(u[0])
            count += 1
        except Exception:
            continue
    await state.clear()
    await msg.answer(f"✅ {count} kishiga yuborildi.", reply_markup=admin_kb)


@router.callback_query(F.data == "admin_staff")
async def admin_staff(call: CallbackQuery) -> None:
    if not has_admin_access(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q.", show_alert=True)
        return
    db = get_db()
    rows = db.execute("SELECT user_id FROM admins").fetchall()
    text = "👤 <b>Adminlar ro'yxati:</b>\n\n"
    for r in rows:
        text += f"• <code>{r['user_id']}</code>\n"
    if not rows:
        text += "Hozircha qo'shimcha admin yo'q.\n"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admin_add")],
            [InlineKeyboardButton(text="➖ Admin o'chirish", callback_data="admin_del")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back")],
        ]
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "admin_add")
async def admin_add_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("❌ Faqat asosiy admin.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_add_admin)
    await call.message.answer("➕ Admin qilinadigan foydalanuvchi ID yuboring:")


@router.callback_query(F.data == "admin_del")
async def admin_del_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user.id != config.ADMIN_ID:
        await call.answer("❌ Faqat asosiy admin.", show_alert=True)
        return
    await state.set_state(AdminStates.wait_del_admin)
    await call.message.answer("➖ Adminlikdan olinadigan foydalanuvchi ID yuboring:")


@router.message(AdminStates.wait_add_admin)
async def admin_add_finish(msg: Message, state: FSMContext) -> None:
    if msg.from_user.id != config.ADMIN_ID:
        return
    if not msg.text.isdigit():
        await msg.answer("❌ Foydalanuvchi ID raqam bo'lishi kerak.")
        return
    add_admin(int(msg.text))
    await state.clear()
    await msg.answer("✅ Admin qo'shildi.", reply_markup=admin_kb)


@router.message(AdminStates.wait_del_admin)
async def admin_del_finish(msg: Message, state: FSMContext) -> None:
    if msg.from_user.id != config.ADMIN_ID:
        return
    if not msg.text.isdigit():
        await msg.answer("❌ Foydalanuvchi ID raqam bo'lishi kerak.")
        return
    remove_admin(int(msg.text))
    await state.clear()
    await msg.answer("🗑 Admin o'chirildi.", reply_markup=admin_kb)


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery, state: FSMContext) -> None:
    if not has_admin_access(call.from_user.id):
        return
    await state.clear()
    await call.message.edit_text(
        "🛠 <b>ADMIN PANEL</b>\n\nBoshqaruv bo‘limini tanlang 👇",
        reply_markup=admin_kb,
        parse_mode="HTML",
    )


@router.message(AdminStates.wait_confirm_deposit)
async def confirm_deposit_cmd(msg: Message, state: FSMContext, bot: Bot) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    if not msg.text.isdigit():
        await msg.answer("❌ Foydalanuvchi ID raqam bo'lishi kerak.")
        return
    user_id = int(msg.text)
    user = confirm_deposit(user_id)
    if not user:
        await msg.answer("❌ Depozit topilmadi.")
        return

    if user["first_deposit_done"] == 0 and user["pending_status"]:
        status = user["pending_status"]
        ref_bonus = config.TARIFFS[status]["ref_bonus"]
        db = get_db()
        if user["referred_by"]:
            db.execute(
                "UPDATE users SET balance = balance + ?, refs = refs + 1 WHERE user_id = ?",
                (ref_bonus, user["referred_by"]),
            )
        if config.FIRST_DEPOSIT_BONUS > 0:
            db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (config.FIRST_DEPOSIT_BONUS, user_id),
            )
        db.commit()
        mark_first_deposit(user_id, status)

    await state.clear()
    await msg.answer("✅ Depozit tasdiqlandi.", reply_markup=admin_kb)
    await bot.send_message(user_id, "✅ Depozitingiz tasdiqlandi, balansingiz yangilandi.")


@router.message(AdminStates.wait_confirm_withdraw)
async def confirm_withdraw_cmd(msg: Message, state: FSMContext, bot: Bot) -> None:
    if not has_admin_access(msg.from_user.id):
        return
    if not msg.text.isdigit():
        await msg.answer("❌ So'rov ID raqam bo'lishi kerak.")
        return
    req_id = int(msg.text)
    db = get_db()
    row = db.execute(
        "SELECT id, user_id, amount FROM withdrawals WHERE id = ? AND status = 'pending'",
        (req_id,),
    ).fetchone()
    if not row:
        await msg.answer("❌ So'rov topilmadi.")
        return
    db.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (row["amount"], row["user_id"]),
    )
    db.execute("UPDATE withdrawals SET status = 'done' WHERE id = ?", (req_id,))
    db.commit()
    await state.clear()
    await msg.answer("✅ Pul yechish tasdiqlandi.", reply_markup=admin_kb)
    await bot.send_message(row["user_id"], "✅ Pul yechish so'rovingiz tasdiqlandi.")
