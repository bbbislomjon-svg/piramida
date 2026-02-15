from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

import config
from database import add_user, get_db, get_user, is_admin, set_pending_deposit

router = Router()


class UserStates(StatesGroup):
    wait_screenshot = State()
    wait_withdraw_card = State()
    wait_promo_code = State()


def build_main_kb(show_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="💎 Tarif rejalarini tanlash")],
        [KeyboardButton(text="👤 Shaxsiy kabinet"), KeyboardButton(text="🎁 Bonuslar")],
        [KeyboardButton(text="👥 Referal tizimi"), KeyboardButton(text="💸 Pul yechib olish")],
        [KeyboardButton(text="🏷 Promokod ishlatish"), KeyboardButton(text="ℹ️ Qo'llab-quvvatlash")],
    ]
    if show_admin:
        keyboard.append([KeyboardButton(text="🛠 Admin panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


async def check_sub(bot: Bot, user_id: int) -> bool:
    db = get_db()
    channels = db.execute("SELECT channel_id FROM mandatory_channels").fetchall()
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch[0], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            continue
    return True


@router.message(Command("start"))
async def start(msg: Message, bot: Bot) -> None:
    args = msg.text.split()
    ref_id = None
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id == msg.from_user.id:
            ref_id = None
    add_user(msg.from_user.id, ref_id)

    if not await check_sub(bot, msg.from_user.id):
        db = get_db()
        channels = db.execute("SELECT channel_id FROM mandatory_channels").fetchall()
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        for ch in channels:
            kb.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text="Kanalga o'tish",
                        url=f"https://t.me/{ch[0].replace('@', '')}",
                    )
                ]
            )
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")]
        )
        await msg.answer(
            "❌ Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=kb
        )
        return

    show_admin = msg.from_user.id == config.ADMIN_ID or is_admin(msg.from_user.id)
    await msg.answer(
        "<b>Assalomu alaykum!</b>\n"
        "Investitsiya botiga xush kelibsiz. Quyidagi menyudan foydalaning:",
        reply_markup=build_main_kb(show_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "check_subscription")
async def check_callback(call: CallbackQuery, bot: Bot) -> None:
    if await check_sub(bot, call.from_user.id):
        await call.message.delete()
        show_admin = call.from_user.id == config.ADMIN_ID or is_admin(call.from_user.id)
        await call.message.answer(
            "✅ Raxmat! Endi botdan foydalanishingiz mumkin.",
            reply_markup=build_main_kb(show_admin),
        )
    else:
        await call.answer("❌ Hali hamma kanallarga a'zo emassiz!", show_alert=True)


@router.message(F.text == "🎁 Bonuslar")
async def bonus_menu(msg: Message) -> None:
    db = get_db()
    channels = db.execute("SELECT * FROM bonus_channels").fetchall()
    if not channels:
        await msg.answer("Hozircha bonusli kanallar yo'q.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = "🎁 <b>Kanallarga obuna bo'ling va bonus oling:</b>\n\n"

    for ch in channels:
        text += f"• {ch['channel_id']} — {ch['bonus']} so'm\n"

        kb.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"A'zo bo'lish ({ch['channel_id']})",
                    url=f"https://t.me/{ch['channel_id'].replace('@', '')}",
                )
            ]
        )
        kb.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="💰 Bonusni olish",
                    callback_data=f"getbonus_{ch['channel_id']}_{ch['bonus']}",
                )
            ]
        )

    await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("getbonus_"))
async def get_bonus(call: CallbackQuery, bot: Bot) -> None:
    _, ch_id, amount = call.data.split("_")
    db = get_db()
    cur = db.cursor()
    used = cur.execute(
        "SELECT * FROM bonus_history WHERE user_id=? AND channel_id=?",
        (call.from_user.id, ch_id),
    ).fetchone()
    if used:
        await call.answer("❌ Bu kanal uchun bonus olgansiz!", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(ch_id, call.from_user.id)
        if member.status not in ["left", "kicked"]:
            cur.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (int(amount), call.from_user.id),
            )
            cur.execute(
                "INSERT INTO bonus_history VALUES (?, ?)",
                (call.from_user.id, ch_id),
            )
            db.commit()
            await call.message.answer(
                f"✅ Tabriklaymiz! {int(amount):,} so'm balansingizga qo'shildi."
            )
        else:
            await call.answer("❌ Avval kanalga a'zo bo'ling!", show_alert=True)
    except Exception:
        await call.answer("Xatolik! Bot bu kanalda admin emas.")


@router.message(F.text == "💎 Tarif rejalarini tanlash")
async def tariffs(msg: Message) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="BASIC (10k)", callback_data="buy_BASIC")],
            [InlineKeyboardButton(text="PRO (20k)", callback_data="buy_PRO")],
            [InlineKeyboardButton(text="ELITE (35k)", callback_data="buy_ELITE")],
        ]
    )
    await msg.answer(
        "📊 <b>Mavjud tariflar:</b>\n\n"
        "BASIC: 10,000 so'm\n"
        "PRO: 20,000 so'm\n"
        "ELITE: 35,000 so'm",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("buy_"))
async def buy(call: CallbackQuery, state: FSMContext) -> None:
    status = call.data.split("_")[1]
    amount = config.TARIFFS[status]["amount"]
    await state.update_data(status=status, amount=amount)
    await state.set_state(UserStates.wait_screenshot)
    await call.message.answer(
        "💳 <b>To'lov turi:</b> {status}\n"
        "💰 <b>Summa:</b> {amount:,} so'm\n\n"
        "Karta: <code>{card}</code>\n"
        "Ism: {holder}\n\n"
        "To'lov chekini (rasm) yuboring.".format(
            status=status,
            amount=amount,
            card=config.CARD_NUMBER,
            holder=config.CARD_HOLDER,
        ),
        parse_mode="HTML",
    )


@router.message(UserStates.wait_screenshot, F.photo)
async def check_sent(msg: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    set_pending_deposit(msg.from_user.id, data["amount"], data["status"])

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"adm_ok_{msg.from_user.id}",
                )
            ]
        ]
    )
    await bot.send_photo(
        config.ADMIN_ID,
        photo=msg.photo[-1].file_id,
        caption=(
            "🔔 <b>Yangi depozit!</b>\n"
            f"ID: <code>{msg.from_user.id}</code>\n"
            f"Tarif: {data['status']}\n"
            f"Summa: {data['amount']:,}"
        ),
        reply_markup=kb,
        parse_mode="HTML",
    )
    await state.clear()
    await msg.answer("✅ Raxmat! To'lov cheki yuborildi. Admin tasdiqlashini kuting.")


@router.message(F.text == "👤 Shaxsiy kabinet")
async def cabinet(msg: Message) -> None:
    u = get_user(msg.from_user.id)
    text = (
        f"👤 <b>Foydalanuvchi:</b> {msg.from_user.full_name}\n"
        f"🆔 ID: <code>{msg.from_user.id}</code>\n\n"
        f"💰 Balans: <b>{u['balance']:,} so'm</b>\n"
        f"💎 Status: <b>{u['status']}</b>\n"
        f"👥 Referallar: <b>{u['refs']} ta</b>"
    )
    await msg.answer(text, parse_mode="HTML")


@router.message(F.text == "🏷 Promokod ishlatish")
async def promo_info(msg: Message, state: FSMContext) -> None:
    await state.set_state(UserStates.wait_promo_code)
    await msg.answer(
        "🏷 Promokodingizni yuboring (masalan: WELCOME5)",
        parse_mode="HTML",
    )


@router.message(Command("promo"))
async def promo_use(msg: Message) -> None:
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❌ Xato! <code>/promo KOD</code> ko'rinishida yozing.")
        return
    code = args[1]
    await apply_promo(msg, code)


@router.message(UserStates.wait_promo_code)
async def promo_use_text(msg: Message, state: FSMContext) -> None:
    code = msg.text.strip()
    await apply_promo(msg, code)
    await state.clear()


async def apply_promo(msg: Message, code: str) -> None:
    db = get_db()
    cur = db.cursor()
    promo = cur.execute("SELECT * FROM promos WHERE code = ?", (code,)).fetchone()
    used = cur.execute(
        "SELECT * FROM promo_history WHERE user_id=? AND code=?",
        (msg.from_user.id, code),
    ).fetchone()

    if promo and not used and promo["limit_count"] > 0:
        cur.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (promo["amount"], msg.from_user.id),
        )
        cur.execute(
            "UPDATE promos SET limit_count = limit_count - 1 WHERE code = ?",
            (code,),
        )
        cur.execute("INSERT INTO promo_history VALUES (?, ?)", (msg.from_user.id, code))
        db.commit()
        await msg.answer(
            f"✅ Tabriklaymiz! Balansingizga {promo['amount']:,} so'm qo'shildi."
        )
    else:
        await msg.answer(
            "❌ Promokod xato, muddati tugagan yoki siz allaqachon ishlatgansiz."
        )


@router.message(F.text == "💸 Pul yechib olish")
async def withdraw(msg: Message, state: FSMContext) -> None:
    u = get_user(msg.from_user.id)
    if u["balance"] < config.MIN_WITHDRAW:
        await msg.answer(
            "❌ Balansingizda yetarli mablag' yo'q.\n"
            f"Minimal: {config.MIN_WITHDRAW:,} so'm"
        )
        return
    await state.set_state(UserStates.wait_withdraw_card)
    await msg.answer("💳 Pul o'tkaziladigan karta raqami va ismingizni yuboring:")


@router.message(UserStates.wait_withdraw_card)
async def withdraw_card(msg: Message, state: FSMContext, bot: Bot) -> None:
    u = get_user(msg.from_user.id)
    db = get_db()
    db.execute(
        "INSERT INTO withdrawals (user_id, amount, card_text) VALUES (?, ?, ?)",
        (msg.from_user.id, u["balance"], msg.text),
    )
    db.commit()
    text = (
        "💸 <b>Yangi yechish so'rovi!</b>\n\n"
        f"ID: <code>{msg.from_user.id}</code>\n"
        f"Summa: {u['balance']:,} so'm\n"
        f"Karta: {msg.text}\n\n"
        "Tasdiqlash uchun admin panelga kiring."
    )
    await bot.send_message(config.ADMIN_ID, text, parse_mode="HTML")
    await state.clear()
    await msg.answer("✅ So'rovingiz yuborildi. Tez orada pul o'tkazib beriladi.")


@router.message(F.text == "👥 Referal tizimi")
async def ref_link(msg: Message) -> None:
    u = get_user(msg.from_user.id)
    if u["status"] == "MEHMON":
        await msg.answer(
            "❌ Referal havola olish uchun avval kamida 1 marta sarmoya kiritishingiz kerak."
        )
        return
    bot_info = await msg.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={msg.from_user.id}"
    await msg.answer(
        "👥 <b>Sizning referal havolangiz:</b>\n\n"
        f"{link}\n\n"
        "Har bir investitsiya qilgan do'stingiz uchun bonus oling!",
        parse_mode="HTML",
    )


@router.message(F.text == "ℹ️ Qo'llab-quvvatlash")
async def support(msg: Message) -> None:
    await msg.answer("❓ Savollar bo'yicha adminga murojaat qiling: @admin_username")
