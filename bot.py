"""
COUPLE APP — TELEGRAM BOT @DEPigeon_bot
"""

import html
import logging
import random
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, db as rtdb, firestore as fs

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ══════════════════════════════════════════════════════
# КОНФІГ
# ══════════════════════════════════════════════════════

BOT_TOKEN     = "8623560197:AAEbQS9-YebAcBeALCjhDLEcjYCBh7GLvkU"
BOT_USERNAME  = "DEPigeon_bot"
BOT_LINK      = "https://t.me/DEPigeon_bot"
FIREBASE_CRED = "serviceAccountKey.json"
FIREBASE_DB   = "https://couple-love-counter-9f6b6-default-rtdb.europe-west1.firebasedatabase.app"
SITE_URL      = "https://couple-love-counter-9f6b6.web.app"

# Telegram ID → роль
USERS = {
    875702362:  "admin",
    5115747973: "user2",
    7946038126: "user2",
}

# Псевдоніми по ролі
NICKNAMES = {
    "admin": "Старик 👴",
    "user2": "Малыш ❤️",
}

TILE_LABELS = {
    "status": "сколько дней",
    "send": "сказать приятное",
    "milestones": "наши даты",
    "site": "открыть сайт",
    "home": "главное",
    "help": "помощь",
    "test": "проверить",
}
CANCEL_LABEL = "отмена"
WAITING_MESSAGE = "waiting_message"
WAITING_MILESTONES = "waiting_milestones"

# Firebase UID → роль
FIREBASE_UID_TO_ROLE = {
    "m1DE4N6Ajwbqah6NWwunOsQQpYl2": "admin",
    "V6ApzXINNNglmDCIFr6bvVciZXv2": "user2",
}

ROLE_LINKS = {
    "admin": f"{SITE_URL}?role=admin",
    "user2": f"{SITE_URL}?role=user2",
}

REMINDER_TEXTS = [
    "вечер — хорошее время сказать, что любишь\n\n{name1} и {name2}, вы вместе уже {days} дней",
    "эй, рядом есть человек, который любит тебя\n\nу вас уже {days} дней вместе",
    "тихий вечер. напиши {partner} что-нибудь тёплое\n\n{name1} и {name2} — {days} дней",
    "иногда хватает одного сообщения, чтобы стало тепло\n\nнапиши {partner}\n\n{days} дней вместе",
    "ты кому-то очень нужен\n\n{name1} и {name2} — уже {days} дней",
    "как прошёл день? расскажи {partner}\n\nвы вместе {days} дней",
    "маленькие слова делают большую любовь\n\nскажи что-то приятное {partner} сегодня",
    "не откладывай тёплые слова\n\n{partner} ждёт\n\n{days} дней вместе",
    "ты уже говорил сегодня, что любишь?\n\nесли нет — самое время\n\n{name1} и {name2} — {days} дней",
    "дом там, где твой человек\n\nнапомни {partner}, что они — твой дом",
    "любовь — это каждый день по чуть-чуть\n\nсегодня можно написать {partner}",
    "ты думал о {partner} сегодня?\n\nдай знать\n\n{days} дней вместе",
    "вы команда\n\n{days} дней вместе — поддержите друг друга сегодня",
    "настоящая любовь — редкость\n\n{name1} и {name2} знают это уже {days} дней",
    "вечерний чай лучше с тёплым словом\n\nотправь {partner} свою любовь",
    "маленькое «скучаю» много значит\n\nнапиши {partner}",
    "ваш огонь горит уже {days} дней\n\nподдержи его — напиши {partner}",
    "хороший вечер — когда сказал «люблю»\n\n{name1} и {name2} — {days} дней",
    "{partner} любит тебя. ты любишь {partner}\n\nскажи об этом\n\n{days} дней вместе",
    "просто напоминание: вы рядом, и это уже много\n\n{days} дней",
]

ANNIVERSARY_TEXTS = [
    "{days} дней вместе\n\n{name1} и {name2}, посмотрите — столько всего уже было",
    "особая дата\n\n{days} дней — {name1} и {name2} вместе",
    "{days} дней\n\nэто не просто цифра. это {days} утр рядом\n\nс праздником, {name1} и {name2}",
    "{days} дней вместе\n\n{name1} и {name2}, вы создали что-то своё",
    "{days} дней любви\n\nесли бы каждый день был цветком — у вас уже целый сад",
    "{days} дней\n\nхороший повод сказать друг другу что-то особенное",
    "особый день\n\n{days} дней, когда вы выбираете друг друга\n\n{name1} и {name2}",
    "{days} дней\n\nмногие мечтают о таком. вы живёте этим",
    "{name1} и {name2} — {days} дней\n\nпродолжайте в том же духе",
    "{days} дней вместе\n\nсколько рассветов вы уже встретили?\n\nс праздником",
    "{days} дней — {days} поводов любить\n\n{name1} и {name2}, вы молодцы",
    "{days} дней вместе\n\nваша история — самая тёплая, что я знаю",
    "юбилей — {days} дней\n\n{name1} и {name2}, настоящая любовь существует",
    "{days} дней — огонь не гаснет\n\n{name1} и {name2}, с праздником",
    "{days} дней\n\nвы идёте одной дорогой\n\n{name1} и {name2}",
    "{days} дней\n\nкаждый день разный, но вы всегда вместе",
    "{days} дней приключений\n\n{name1} и {name2}, ваш путь только начинается",
    "{days} дней — столько «люблю»\n\nдаже если не все вслух — вы чувствовали это",
    "внимание — {days} дней\n\n{name1} и {name2} отмечают особую дату",
    "{days} дней вместе — это путешествие\n\nи лучшее в нём — что вы рядом",
]

# ══════════════════════════════════════════════════════
# ЛОГУВАННЯ
# ══════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
# FIREBASE INIT
# ══════════════════════════════════════════════════════

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CRED)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB})
    return rtdb.reference("/couple"), fs.client()

ref_couple, fs_client = init_firebase()

# ══════════════════════════════════════════════════════
# FIREBASE HELPERS
# ══════════════════════════════════════════════════════

def get_data() -> dict:
    return ref_couple.get() or {}

def get_names() -> tuple:
    return NICKNAMES["admin"], NICKNAMES["user2"]

def esc(text: str) -> str:
    return html.escape(str(text))

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("назад в меню", callback_data="menu_home")]])

def tile_keyboard(role: str) -> ReplyKeyboardMarkup:
    """Плиточное меню под полем ввода."""
    rows = [
        [KeyboardButton(TILE_LABELS["status"]), KeyboardButton(TILE_LABELS["send"])],
        [KeyboardButton(TILE_LABELS["milestones"]), KeyboardButton(TILE_LABELS["site"])],
        [KeyboardButton(TILE_LABELS["home"]), KeyboardButton(TILE_LABELS["help"])],
    ]
    if role == "admin":
        rows.append([KeyboardButton(TILE_LABELS["test"])])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)

def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(CANCEL_LABEL)]], resize_keyboard=True)

def main_menu_keyboard(role: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(TILE_LABELS["status"], callback_data="menu_status"),
            InlineKeyboardButton(TILE_LABELS["send"], callback_data="menu_send"),
        ],
        [
            InlineKeyboardButton(TILE_LABELS["milestones"], callback_data="menu_milestones"),
            InlineKeyboardButton(TILE_LABELS["site"], url=ROLE_LINKS[role]),
        ],
        [InlineKeyboardButton(TILE_LABELS["help"], callback_data="menu_help")],
    ]
    if role == "admin":
        rows.append([InlineKeyboardButton(TILE_LABELS["test"], callback_data="menu_test")])
    return InlineKeyboardMarkup(rows)

def test_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("напоминание", callback_data="test_reminder")],
        [InlineKeyboardButton("юбилей", callback_data="test_anniversary")],
        [InlineKeyboardButton("сообщение с сайта", callback_data="test_site_msg")],
        [InlineKeyboardButton("назад в меню", callback_data="menu_home")],
    ])

def build_welcome(role: str) -> str:
    nick = NICKNAMES[role]
    partner = NICKNAMES["user2"] if role == "admin" else NICKNAMES["admin"]
    days = get_days()
    name1, name2 = get_names()
    milestones = get_milestones()
    next_ms = next((m for m in milestones if m > days), milestones[-1])
    days_left = next_ms - days
    return (
        f"привет, {nick}\n\n"
        f"{name1} и {name2}\n"
        f"вместе уже {days:,} дней\n"
        f"до {next_ms} — ещё {days_left}\n\n"
        f"рядом {partner} — выбирай, что хочешь"
    )

def format_status_text() -> str:
    name1, name2 = get_names()
    days = get_days()
    milestones = get_milestones()
    next_ms = next((m for m in milestones if m > days), milestones[-1])
    days_left = next_ms - days
    years = days // 365
    months = (days % 365) // 30
    rem = days % 30
    pct_1000 = min(100, round(days / 10))
    ms_list = ", ".join(str(m) for m in milestones[:8])
    return (
        f"{name1} и {name2}\n\n"
        f"вместе {days:,} дней\n"
        f"это {years} лет, {months} мес и {rem} дн\n\n"
        f"следующая дата — {next_ms} дней\n"
        f"осталось {days_left}\n\n"
        f"до тысячи дней — {pct_1000}%\n"
        f"наши даты: {ms_list}…"
    )

def format_milestones_text(role: str) -> str:
    current = get_milestones()
    ms_str = ", ".join(str(m) for m in current)
    days = get_days()
    next_ms = next((m for m in current if m > days), current[-1])
    days_left = next_ms - days
    header = "наши даты" if role != "admin" else "наши даты — можешь менять"
    body = (
        f"{header}\n\n"
        f"{ms_str}\n\n"
        f"до {next_ms} дней — ещё {days_left}\n\n"
    )
    if role == "admin":
        body += "список можно поменять кнопками ниже"
    else:
        body += "в каждую такую дату — маленький праздник"
    return body

def milestones_keyboard(role: str) -> InlineKeyboardMarkup | None:
    if role != "admin":
        return back_keyboard()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("изменить даты", callback_data="edit_milestones")],
        [InlineKeyboardButton("вернуть как было", callback_data="reset_milestones")],
        [InlineKeyboardButton("назад в меню", callback_data="menu_home")],
    ])

def format_help_text(role: str) -> str:
    admin_extra = (
        "\n\nдля тебя ещё есть кнопка «проверить» — "
        "чтобы посмотреть, как работают напоминания"
    ) if role == "admin" else ""
    nick = NICKNAMES[role]
    return (
        f"{nick}, вот что тут есть:\n\n"
        f"кнопки внизу — самый простой способ\n"
        f"«{TILE_LABELS['send']}» — написать слова, просто текст\n"
        f"«{TILE_LABELS['status']}» — сколько дней вместе\n"
        f"«{TILE_LABELS['milestones']}» — важные даты\n"
        f"[сайт]({ROLE_LINKS[role]}) · [бот]({BOT_LINK})"
        f"{admin_extra}"
    )

def get_milestones() -> list:
    """Читає список вех з Firebase (або дефолт)."""
    data = get_data()
    saved = data.get("milestones")
    if saved and isinstance(saved, list):
        return sorted([int(x) for x in saved if str(x).isdigit()])
    return [50, 100, 150, 200, 365, 500, 730, 1000, 1825, 3650]

def get_days() -> int:
    start_str = get_data().get("startDate", "2026-06-01")
    d = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - d).days

def get_tg_ids() -> dict:
    result = {"admin": [], "user2": []}
    for uid, role in USERS.items():
        result[role].append(uid)
    return result

def get_pending_notifications() -> list:
    try:
        docs = (
            fs_client.collection("notifications")
            .where("sent", "==", False)
            .limit(20)
            .get()
        )
        return [(doc.id, doc.to_dict()) for doc in docs]
    except Exception as e:
        log.warning(f"Firestore read error: {e}")
        return []

def mark_sent(doc_id: str):
    try:
        fs_client.collection("notifications").document(doc_id).update({"sent": True})
    except Exception as e:
        log.warning(f"mark_sent error: {e}")

def format_reminder(days: int, name1: str, name2: str, role: str) -> str:
    """Вибирає випадковий текст нагадування і форматує його."""
    partner = name2 if role == "admin" else name1
    template = random.choice(REMINDER_TEXTS)
    return template.format(name1=name1, name2=name2, days=days, partner=partner)

def format_anniversary(days: int, name1: str, name2: str) -> str:
    """Вибирає текст ювілею — визначено hash(days) щоб обидва отримали однаковий."""
    idx = days % len(ANNIVERSARY_TEXTS)
    template = ANNIVERSARY_TEXTS[idx]
    return template.format(name1=name1, name2=name2, days=days)

# ══════════════════════════════════════════════════════
# CONVERSATION STATE (для /setmilestones)
# ══════════════════════════════════════════════════════
WAITING_MILESTONES = 1

# ══════════════════════════════════════════════════════
# КОМАНДИ
# ══════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    role  = USERS.get(tg_id)

    if not role:
        await update.message.reply_text(
            f"привет. тебя тут пока нет в списке\n\n"
            f"скинь этот номер тому, кто настраивал: {tg_id}"
        )
        return

    await update.message.reply_text(
        build_welcome(role),
        reply_markup=tile_keyboard(role),
    )
    await update.message.reply_text(
        "или нажми кнопки в сообщении выше",
        reply_markup=main_menu_keyboard(role),
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    role = USERS.get(tg_id)
    if not role:
        return

    await update.message.reply_text(
        format_status_text(),
        reply_markup=back_keyboard(),
    )


def clear_waiting(ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.pop(WAITING_MESSAGE, None)
    ctx.user_data.pop(WAITING_MILESTONES, None)


async def prompt_send_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, role: str):
    """Ждём текст сообщения — без /send."""
    clear_waiting(ctx)
    ctx.user_data[WAITING_MESSAGE] = True
    partner = NICKNAMES["user2"] if role == "admin" else NICKNAMES["admin"]
    text = (
        f"напиши что-нибудь тёплое для {partner}\n\n"
        f"«{CANCEL_LABEL}» — если передумал"
    )
    msg = update.message or update.callback_query.message
    await msg.reply_text(text, reply_markup=cancel_keyboard())


async def deliver_love_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE, role: str, text: str):
    from_name = NICKNAMES[role]
    to_role = "user2" if role == "admin" else "admin"
    to_nick = NICKNAMES[to_role]

    try:
        fs_client.collection("notifications").add({
            "fromUID": role,
            "fromName": from_name,
            "text": text,
            "timestamp": fs.SERVER_TIMESTAMP,
            "toUID": to_role,
            "sent": True,
            "type": "telegram_message",
        })
    except Exception as e:
        log.warning(f"Firestore write error: {e}")

    tg_ids = get_tg_ids()
    sent_count = 0
    for cid in tg_ids.get(to_role, []):
        try:
            await ctx.bot.send_message(
                chat_id=cid,
                text=f"от {from_name}:\n\n{text}",
            )
            sent_count += 1
        except Exception as e:
            log.warning(f"Send to {cid} failed: {e}")

    clear_waiting(ctx)
    if sent_count > 0:
        await update.message.reply_text(
            f"отправил {to_nick}",
            reply_markup=tile_keyboard(role),
        )
    else:
        await update.message.reply_text(
            f"{to_nick} ещё не открывал бота — сохранил на сайте",
            reply_markup=tile_keyboard(role),
        )


async def cmd_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    role = USERS.get(tg_id)
    if not role:
        return

    if not ctx.args:
        await prompt_send_message(update, ctx, role)
        return

    await deliver_love_message(update, ctx, role, " ".join(ctx.args))


async def cmd_milestones(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    role  = USERS.get(tg_id)
    if not role:
        return

    kb = milestones_keyboard(role)
    await update.message.reply_text(
        format_milestones_text(role),
        reply_markup=kb,
    )


async def cmd_test(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    if USERS.get(tg_id) != "admin":
        await update.message.reply_text("это только для тебя, старик")
        return

    await update.message.reply_text(
        "что проверим?",
        reply_markup=test_menu_keyboard(),
    )


def strip_md(text: str) -> str:
    """Убирает разметку Markdown для обычной отправки."""
    return text.replace("*", "").replace("_", "").replace("`", "")


async def send_plain(bot, chat_id: int, text: str) -> bool:
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        log.warning(f"send_plain → {chat_id}: {e}")
        return False


async def reply_test_result(query, text: str):
    kb = test_menu_keyboard()
    try:
        await query.edit_message_text(text, reply_markup=kb)
    except Exception as e:
        log.warning(f"edit_message_text failed: {e}")
        await query.message.reply_text(text, reply_markup=kb)


async def handle_test_callback(query, data: str):
    name1, name2 = get_names()
    days = get_days()
    tg_ids = get_tg_ids()
    all_ids = tg_ids.get("admin", []) + tg_ids.get("user2", [])

    try:
        if data == "test_reminder":
            sent, errors = 0, 0
            for recipient_role, ids in tg_ids.items():
                text = strip_md(format_reminder(days, name1, name2, recipient_role))
                note = "\n\n(тестовое сообщение)"
                for cid in ids:
                    if await send_plain(query.bot, cid, text + note):
                        sent += 1
                    else:
                        errors += 1
            msg = f"напоминание ушло {sent} раз"
            if errors:
                msg += f"\nне дошло: {errors}"
            await reply_test_result(query, msg)
            return

        if data == "test_anniversary":
            text = strip_md(format_anniversary(days, name1, name2))
            note = "\n\n(тестовое сообщение)"
            sent = sum(1 for cid in all_ids if await send_plain(query.bot, cid, text + note))
            await reply_test_result(query, f"юбилейное сообщение ушло {sent} раз")
            return

        if data == "test_site_msg":
            admin_uid = next(k for k, v in FIREBASE_UID_TO_ROLE.items() if v == "admin")
            user2_uid = next(k for k, v in FIREBASE_UID_TO_ROLE.items() if v == "user2")
            test_text = "тестовое слово с сайта"
            doc_ref = fs_client.collection("notifications").document()
            doc_ref.set({
                "fromUID": admin_uid,
                "fromName": name1,
                "text": test_text,
                "timestamp": fs.SERVER_TIMESTAMP,
                "toUID": user2_uid,
                "sent": False,
                "type": "manual",
            })
            msg = f"от {name1}:\n\n{test_text}"
            sent = sum(
                1 for cid in tg_ids.get("user2", [])
                if await send_plain(query.bot, cid, msg)
            )
            mark_sent(doc_ref.id)
            await reply_test_result(
                query,
                f"тест с сайта — дошло {sent} раз",
            )
    except Exception as e:
        log.exception(f"handle_test_callback {data}: {e}")
        await reply_test_result(query, f"не вышло: {e}")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    role = USERS.get(tg_id)
    if not role:
        return

    await update.message.reply_text(
        format_help_text(role),
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=back_keyboard()
    )


# ══════════════════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════════════════

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tg_id = query.from_user.id
    role = USERS.get(tg_id)
    if not role:
        await query.edit_message_text("тебя тут пока нет")
        return

    data = query.data

    # ── Меню для всех ─────────────────────────────────
    if data == "menu_home":
        await query.edit_message_text(
            build_welcome(role),
            reply_markup=main_menu_keyboard(role),
        )
        return

    if data == "menu_status":
        await query.edit_message_text(
            format_status_text(),
            reply_markup=back_keyboard(),
        )
        return

    if data == "menu_milestones":
        await query.edit_message_text(
            format_milestones_text(role),
            reply_markup=milestones_keyboard(role),
        )
        return

    if data == "menu_help":
        await query.edit_message_text(
            format_help_text(role),
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=back_keyboard()
        )
        return

    if data == "menu_send":
        await prompt_send_message(update, ctx, role)
        return

    if data == "menu_test":
        if role != "admin":
            await query.answer("только для старика", show_alert=True)
            return
        await query.edit_message_text(
            "что проверим?",
            reply_markup=test_menu_keyboard(),
        )
        return

    if data in ("test_reminder", "test_anniversary", "test_site_msg"):
        if role != "admin":
            await query.answer("только для старика", show_alert=True)
            return
        await handle_test_callback(query, data)
        return

    if role != "admin":
        await query.answer("только для старика", show_alert=True)
        return

    if data == "edit_milestones":
        current = get_milestones()
        ms_str = ", ".join(str(m) for m in current)
        await query.edit_message_text(
            f"сейчас так: {ms_str}\n\n"
            f"пришли новый список через запятую\n"
            f"например: 50, 100, 365, 1000\n\n"
            f"«{CANCEL_LABEL}» — отмена"
        )
        ctx.user_data[WAITING_MILESTONES] = True
        ctx.user_data.pop(WAITING_MESSAGE, None)
        await query.message.reply_text(
            f"жду список. «{CANCEL_LABEL}» — отмена",
            reply_markup=cancel_keyboard(),
        )

    if data == "reset_milestones":
        default = [50, 100, 150, 200, 365, 500, 730, 1000, 1825, 3650]
        try:
            ref_couple.child("milestones").set(default)
            await query.edit_message_text(
                f"вернул как было:\n{', '.join(str(m) for m in default)}\n\n"
                "на сайте тоже обновится"
            )
        except Exception as e:
            await query.edit_message_text(f"не вышло: {e}")


async def handle_tile_press(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Плиточные кнопки под полем ввода."""
    tg_id = update.effective_user.id
    role = USERS.get(tg_id)
    if not role:
        return

    text = (update.message.text or "").strip()

    if text == CANCEL_LABEL:
        clear_waiting(ctx)
        await update.message.reply_text("ладно, отменил", reply_markup=tile_keyboard(role))
        return

    tile_actions = {
        TILE_LABELS["status"]: lambda: cmd_status(update, ctx),
        TILE_LABELS["send"]: lambda: prompt_send_message(update, ctx, role),
        TILE_LABELS["milestones"]: lambda: cmd_milestones(update, ctx),
        TILE_LABELS["help"]: lambda: cmd_help(update, ctx),
        TILE_LABELS["test"]: lambda: cmd_test(update, ctx),
        TILE_LABELS["home"]: lambda: update.message.reply_text(
            build_welcome(role),
            reply_markup=main_menu_keyboard(role),
        ),
    }

    if text in tile_actions:
        clear_waiting(ctx)
        result = tile_actions[text]()
        if result is not None:
            await result
        return

    if text == TILE_LABELS["site"]:
        clear_waiting(ctx)
        await update.message.reply_text(
            f"наш сайт:\n{ROLE_LINKS[role]}",
            disable_web_page_preview=False,
            reply_markup=back_keyboard(),
        )
        return

    if ctx.user_data.get(WAITING_MILESTONES):
        await handle_milestones_input(update, ctx)
        return

    if ctx.user_data.get(WAITING_MESSAGE):
        if not text:
            await update.message.reply_text("напиши хоть пару слов")
            return
        await deliver_love_message(update, ctx, role, text)
        return


async def handle_milestones_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Обробляє введений список вех."""
    tg_id = update.effective_user.id
    role = USERS.get(tg_id)
    if role != "admin":
        return

    text = update.message.text.strip()
    try:
        parts = [p.strip() for p in text.replace(";", ",").split(",")]
        milestones = sorted(list(set(int(p) for p in parts if p.isdigit() and 0 < int(p) <= 100000)))
        if len(milestones) < 2:
            await update.message.reply_text(
                f"нужно хотя бы две даты. попробуй ещё или «{CANCEL_LABEL}»"
            )
            return

        # Зберігаємо в Firebase — сайт і бот читають звідси
        ref_couple.child("milestones").set(milestones)

        ctx.user_data[WAITING_MILESTONES] = False
        ms_str = ", ".join(str(m) for m in milestones)
        await update.message.reply_text(
            f"готово:\n{ms_str}\n\nна сайте тоже обновится",
            reply_markup=tile_keyboard(role),
        )
    except ValueError:
        await update.message.reply_text(
            f"не понял. напиши числа через запятую\n"
            f"например: 50, 100, 365\n\nили «{CANCEL_LABEL}»"
        )


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    role = USERS.get(tg_id)
    clear_waiting(ctx)
    await update.message.reply_text(
        "ладно, отменил",
        reply_markup=tile_keyboard(role) if role else None,
    )


# ══════════════════════════════════════════════════════
# ФОНОВИЙ POLLING FIRESTORE (сайт → Telegram)
# ══════════════════════════════════════════════════════

async def job_poll_firestore(app: Application):
    pending = get_pending_notifications()
    if not pending:
        return

    tg_ids = get_tg_ids()

    for doc_id, notif in pending:
        to_role   = notif.get("toUID", "")
        from_name = notif.get("fromName", "Кто-то")
        text      = notif.get("text", "")
        ntype     = notif.get("type", "manual")

        # Конвертуємо Firebase UID → роль
        resolved_role = None
        if to_role in ("admin", "user2"):
            resolved_role = to_role
        elif to_role in FIREBASE_UID_TO_ROLE:
            resolved_role = FIREBASE_UID_TO_ROLE[to_role]
        else:
            log.warning(f"Невідомий toUID '{to_role}' у doc {doc_id}, пропускаємо")
            mark_sent(doc_id)
            continue

        recipients = tg_ids.get(resolved_role, [])

        if ntype == "auto_anniversary":
            days_val = notif.get("days", get_days())
            name1, name2 = get_names()
            msg = format_anniversary(days_val, name1, name2)
        elif ntype == "telegram_message":
            mark_sent(doc_id)
            continue
        else:
            msg = f"от {from_name}:\n\n{text}"

        for cid in recipients:
            try:
                await app.bot.send_message(chat_id=cid, text=msg)
                log.info(f"✅ Доставлено → {cid} (doc: {doc_id})")
            except Exception as e:
                log.warning(f"Send failed {cid}: {e}")

        mark_sent(doc_id)


# ══════════════════════════════════════════════════════
# ЩОДЕННЕ НАГАДУВАННЯ
# ══════════════════════════════════════════════════════

async def job_daily_reminder(app: Application):
    data = get_data()
    t    = data.get("settings", {}).get("dailyReminderTime", "20:00")
    try:
        h, m = map(int, t.split(":"))
    except Exception:
        return

    now = datetime.now(timezone.utc)
    if now.hour != h or now.minute != m:
        return

    today = now.date().isoformat()
    last  = rtdb.reference("couple/lastReminderDate").get()
    if last == today:
        return
    rtdb.reference("couple/lastReminderDate").set(today)

    name1, name2 = get_names()
    days = get_days()
    tg_ids = get_tg_ids()

    # Кожному — персоналізований текст
    for role, ids in tg_ids.items():
        text = format_reminder(days, name1, name2, role)
        for cid in ids:
            try:
                await app.bot.send_message(chat_id=cid, text=text)
            except Exception as e:
                log.warning(f"Daily reminder → {cid}: {e}")


# ══════════════════════════════════════════════════════
# ЮВІЛЕЇ
# ══════════════════════════════════════════════════════

async def job_anniversary(app: Application):
    days      = get_days()
    special   = set(get_milestones())
    if days not in special:
        return

    name1, name2 = get_names()
    text = format_anniversary(days, name1, name2)

    tg_ids = get_tg_ids()
    for role_ids in tg_ids.values():
        for cid in role_ids:
            try:
                await app.bot.send_message(chat_id=cid, text=text)
            except Exception as e:
                log.warning(f"Anniversary → {cid}: {e}")


# ══════════════════════════════════════════════════════
# ПЛАНУВАЛЬНИК
# ══════════════════════════════════════════════════════

def setup_scheduler(application: Application):
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(job_poll_firestore, "interval", seconds=15, args=[application], id="poll_firestore")
    scheduler.add_job(job_daily_reminder, "interval", minutes=1,  args=[application], id="daily_reminder")
    scheduler.add_job(job_anniversary,    "cron", hour=10, minute=0, args=[application], id="anniversary")
    scheduler.start()
    log.info("⏰ Scheduler started")
    return scheduler


# ══════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════

def main():
    log.info(f"🤖 Starting @{BOT_USERNAME}...")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start",      cmd_start))
    application.add_handler(CommandHandler("status",     cmd_status))
    application.add_handler(CommandHandler("send",       cmd_send))
    application.add_handler(CommandHandler("milestones", cmd_milestones))
    application.add_handler(CommandHandler("test",       cmd_test))
    application.add_handler(CommandHandler("help",       cmd_help))
    application.add_handler(CommandHandler("cancel",     cmd_cancel))
    application.add_handler(CallbackQueryHandler(callback_handler))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=list(USERS.keys())),
        handle_tile_press,
    ))

    setup_scheduler(application)
    log.info("✅ Bot is running.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()