from healthcheck import run as healthcheck_run
# Запуск HTTP-сервера для Uptime-пингов
healthcheck_run()

import os
import asyncio
import logging
from html import escape
import textwrap

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton as KB,
    InlineKeyboardMarkup as KBM,
    BotCommand
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ADMIN_IDS = {int(i) for i in os.getenv("ADMIN_IDS").split(",")}
GIFT_URL = os.getenv("GIFT_URL")
IMAGE_DIR = os.path.join(os.getcwd(), "images")

# Text constants
WELCOME_TEMPLATE = (
    "Привет, <b>{name}</b>! 👋\n\n"
    "Меня зовут Полина, я помогаю экспертам и предпринимателям упаковывать суть бизнеса"
    " в аккуратный и заметный формат.\n\n"
    "В этом боте я собрала полезные материалы, которые помогут вам прокачать упаковку своего бизнеса.\n\n"
    "В меню ниже забирайте материалы и знакомьтесь с услугами!👇"
)

GIFT_TEMPLATE = (
    "<b>{name}</b>, я подготовила подарок гайд <u><b><i>«Как с помощью продуманной упаковки привлекать подписчиков и клиентов».</i></b></u>\n\n"
    "✨<b><u><i>Что найдёте в гайде:</i></u></b>\n"
    "— разбор, что такое упаковка и зачем она нужна;\n"
    "— структуру сайта и соцсетей, которая понятна с первого экрана;\n"
    "— типовые ошибки, мешающие упаковке работать;\n"
    "— наглядную схему воронки продаж: от интереса до заявки;\n"
    "— финальный чек-лист, помогающий выявить слабые места.\n\n"
    "<b><u><i>Переходите по кнопке, чтобы читать гайд</i></u></b> 👇"
)

SUBSCRIBE_PROMPT = "Сначала подпишитесь на канал 👇"
COURSE_TEXT = "⚡️ Мини-курс стартует скоро. Не выключайте уведомления в боте, чтобы не пропустить запуск!"

SERVICES_HEADER = "<b>Чем могу быть полезна:</b>\n"
SERVICES_ITEMS = [
    "➡️ Лендинги и многостраничные сайты на Tilda / Taplink",
    "➡️ Редизайн и развитие существующих сайтов",
    "➡️ Сайты-визитки для экспертов и компаниям",
    "➡️ Дизайн и верстка приглашений на любые мероприятия",
    "➡️ Инфографика и презентации для бизнеса",
    "➡️ Оформление и ведение Pinterest-профилей",
]
SERVICES_FOOTER = (
    "\n\n<i>Свяжитесь со мной в личных сообщениях @Polina_Alex — обсудим, как лучше представить ваш проект.</i>"
)

# Keyboards
inline_main_kb = KBM(inline_keyboard=[
    [KB(text="🎁 Подарок", callback_data="gift")],
    [KB(text="📚 Мини-курс", callback_data="course")],
    [KB(text="💼 Услуги", callback_data="services")]
])

gift_kb = KBM(inline_keyboard=[
    [KB(text="🎁 Скачать гайд", callback_data="download_guide")]
])

subscribe_kb = KBM(inline_keyboard=[
    [KB(text="🔗 Подписаться", url="https://t.me/+TcE_ofokV6RjM2Qy")],
    [KB(text="✅ Готово", callback_data="check_sub")]
])

# Configure bot
logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# Database functions
from database import add_user, get_all_ids, inc_stat, get_stats

# Helper: check channel subscription
async def is_member(uid: int) -> bool:
    member = await bot.get_chat_member(CHANNEL_ID, uid)
    return member.status in ("member", "administrator", "creator")

# /start
@dp.message(F.text == "/start")
async def cmd_start(m: Message):
    add_user(m.from_user.id)
    inc_stat("start")
    name = escape(m.from_user.first_name or m.from_user.username or "друг")
    caption = WELCOME_TEMPLATE.format(name=name)
    await m.answer_photo(
        photo=FSInputFile(os.path.join(IMAGE_DIR, "welcome.jpg")),
        caption=caption,
        reply_markup=inline_main_kb
    )

# Unified gift flow
async def send_gift_message(target, name):
    caption = GIFT_TEMPLATE.format(name=name)
    await target.answer_photo(
        photo=FSInputFile(os.path.join(IMAGE_DIR, "gift.jpg")),
        caption=caption,
        reply_markup=gift_kb
    )

async def send_subscribe_prompt(target):
    await target.answer_photo(
        photo=FSInputFile(os.path.join(IMAGE_DIR, "subscribe.jpg")),
        caption=SUBSCRIBE_PROMPT,
        reply_markup=subscribe_kb
    )

@dp.callback_query(F.data.in_(["gift", "check_sub"]))
async def gift_flow(c: CallbackQuery):
    await c.answer()
    inc_stat("gift_clicked")
    name = escape(c.from_user.first_name or c.from_user.username or "друг")
    if await is_member(c.from_user.id):
        inc_stat("gift_sent")
        await send_gift_message(c.message, name)
    else:
        await send_subscribe_prompt(c.message)

@dp.message(F.text == "/gift")
async def cmd_gift(m: Message):
    inc_stat("gift_clicked")
    name = escape(m.from_user.first_name or m.from_user.username or "друг")
    if await is_member(m.from_user.id):
        inc_stat("gift_sent")
        await send_gift_message(m, name)
    else:
        await send_subscribe_prompt(m)

# Download guide
@dp.callback_query(F.data == "download_guide")
async def download_guide(c: CallbackQuery):
    await c.answer()
    inc_stat("guide_downloaded")
    link_text = f"<a href=\"{GIFT_URL}\">ССЫЛКА НА ГАЙД</a>"
    await c.message.answer(
        "По ссылке вас ждёт мой гайд о том, как с помощью продуманной упаковки привлекать подписчиков и клиентов.\n\n" +
        f"{link_text}\n" * 3 +
        "\n<b>Забирайте и держите под рукой ⚡️</b>",
        disable_web_page_preview=True
    )

# Course handlers
async def send_course(target):
    await target.answer_photo(
        photo=FSInputFile(os.path.join(IMAGE_DIR, "course.jpg")),
        caption=COURSE_TEXT
    )

@dp.callback_query(F.data == "course")
async def course_cb(c: CallbackQuery):
    await c.answer()
    inc_stat("course_clicked")
    await send_course(c.message)

@dp.message(F.text == "/course")
async def cmd_course(m: Message):
    inc_stat("course_clicked")
    await send_course(m)

# Services handlers
async def format_services_text():
    items = "\n".join(SERVICES_ITEMS)
    return f"{SERVICES_HEADER}\n{items}{SERVICES_FOOTER}"

async def send_services(target):
    text = format_services_text()
    await target.answer_photo(
        photo=FSInputFile(os.path.join(IMAGE_DIR, "services.jpg")),
        caption=text
    )

@dp.callback_query(F.data == "services")
async def services_cb(c: CallbackQuery):
    await c.answer()
    inc_stat("services_clicked")
    await send_services(c.message)

@dp.message(F.text == "/services")
async def cmd_services(m: Message):
    inc_stat("services_clicked")
    await send_services(m)

# Stats
@dp.message(F.text == "/stats")
async def stats(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        return
    data = get_stats()
    report = ["<b>Статистика бота:</b>\n"] + [f"{event}: {count}" for event, count in data.items()]
    await m.answer("\n".join(report))

# Broadcast FSM
class Announce(StatesGroup):
    wait = State()

@dp.message(F.text.startswith("/announce"))
async def ask_announce(m: Message, state: FSMContext):
    if m.from_user.id not in ADMIN_IDS:
        return
    await m.answer("Пришлите одно сообщение-шаблон. /cancel — отменить.")
    await state.set_state(Announce.wait)

@dp.message(Announce.wait)
async def do_broadcast(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Рассылаю…")
    ok = err = 0
    for uid in get_all_ids():
        try:
            await m.copy_to(uid)
            ok += 1
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except TelegramForbiddenError:
            err += 1
        except Exception:
            err += 1
    await m.answer(f"✅ {ok} доставлено, ❌ {err} не удалось")

@dp.message(F.text.lower() == "/cancel")
async def cancel(m: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await m.answer("Отменено.")

# === ChannelMessage FSM for custom channel posts ===
class ChannelMessage(StatesGroup):
    wait = State()

@dp.message(F.text == "/chanel_massage")
async def ask_channel_message(m: Message, state: FSMContext):
    if m.from_user.id not in ADMIN_IDS:
        return
    await m.answer("Пришлите текст, который нужно опубликовать в канале. /cancel — отменить.")
    await state.set_state(ChannelMessage.wait)

@dp.message(ChannelMessage.wait)
async def send_channel_message(m: Message, state: FSMContext):
    text = m.text
    await state.clear()
    bot_user = await bot.get_me()
    bot_url = f"https://t.me/{bot_user.username}"
    kb = KBM(inline_keyboard=[
        [KB(text="🎁 Подарок", url=bot_url)]
    ])
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        reply_markup=kb
    )
    await m.answer("✅ Ваше сообщение отправлено в канал.")

# Startup and main
def register_commands():
    return [
        BotCommand(command="start", description="Запустить бота и показать главное меню"),
        BotCommand(command="gift", description="Получить подарок-гайд"),
        BotCommand(command="course", description="Узнать о мини-курсе"),
        BotCommand(command="services", description="Узнать об услугах")
    ]

async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(register_commands())

async def main():
    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        from database import engine
        engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
