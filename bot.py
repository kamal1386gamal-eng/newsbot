import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = "@Spark_news_tel"
ALLOWED_USERS = [8293164271]

bot = Bot(token=TOKEN)
dp = Dispatcher()

state = {}

def allowed(user_id: int):
    return user_id in ALLOWED_USERS

# ─────────────── دریافت فوروارد (فقط عکس/ویدیو) ───────────────
@dp.message((F.forward_from | F.forward_from_chat) & (F.photo | F.video))
async def forward_handler(msg: types.Message):
    if not allowed(msg.from_user.id):
        return

    user_id = msg.from_user.id
    # ذخیره پیام اصلی و کپشن اولیه (اگه وجود داشت)
    state[user_id] = {
        "msg": msg,
        "caption": msg.caption or ""
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تایید", callback_data="confirm_direct"),
            InlineKeyboardButton(text="✏️ ویرایش", callback_data="edit_caption")
        ]
    ])
    await msg.answer("📥 فوروارد دریافت شد. می‌خوای مستقیماً تایید کنی یا کپشن رو ویرایش کنی؟", reply_markup=kb)


# ─────────────── مدیریت دکمه‌ها ───────────────
@dp.callback_query()
async def callback_handler(call: types.CallbackQuery):
    if not allowed(call.from_user.id):
        await call.answer("⛔ دسترسی نداری", show_alert=True)
        return
    await call.answer()

    user_id = call.from_user.id
    if user_id not in state:
        await call.message.edit_text("⛔ داده‌ای پیدا نشد")
        return

    data = state[user_id]

    # ── تایید مستقیم (همون کپشن اصلی) ──
    if call.data == "confirm_direct":
        final_text = (data["caption"] + "\n\n" + CHANNEL) if data["caption"] else CHANNEL
        try:
            if data["msg"].photo:
                await bot.send_photo(CHANNEL, data["msg"].photo[-1].file_id, caption=final_text)
            elif data["msg"].video:
                await bot.send_video(CHANNEL, data["msg"].video.file_id, caption=final_text)
            await bot.send_message(user_id, "✅ پست با موفقیت در کانال منتشر شد")
        except Exception as e:
            await bot.send_message(user_id, f"❌ خطا در انتشار: {e}")
        else:
            try:
                await call.message.delete()   # حذف پیام دکمه‌دار
            except Exception:
                pass
        finally:
            state.pop(user_id, None)
        return

    # ── درخواست ویرایش کپشن (مرحله اول) ──
    if call.data == "edit_caption":
        data["caption"] = None  # منتظر کپشن جدید
        await call.message.edit_text("✏️ کپشن جدید را بفرست")
        return

    # ── تایید در پیش‌نمایش ──
    if call.data == "publish_preview":
        final_text = data["caption"] + "\n\n" + CHANNEL if data["caption"] else CHANNEL
        try:
            if data["msg"].photo:
                await bot.send_photo(CHANNEL, data["msg"].photo[-1].file_id, caption=final_text)
            elif data["msg"].video:
                await bot.send_video(CHANNEL, data["msg"].video.file_id, caption=final_text)
            await bot.send_message(user_id, "✅ پست با موفقیت در کانال منتشر شد")
        except Exception as e:
            await bot.send_message(user_id, f"❌ خطا در انتشار: {e}")
        else:
            # حذف پیام پیش‌نمایش
            try:
                await call.message.delete()
            except Exception:
                pass
        finally:
            state.pop(user_id, None)
        return

    # ── دکمه ویرایش در پیش‌نمایش → برگشت به درخواست کپشن ──
    if call.data == "edit_caption_again":
        # حذف پیام پیش‌نمایش
        try:
            await call.message.delete()
        except Exception:
            pass
        data["caption"] = None
        await bot.send_message(user_id, "✏️ کپشن جدید را بفرست")
        return


# ─────────────── دریافت کپشن جدید ───────────────
@dp.message()
async def caption_handler(msg: types.Message):
    if not allowed(msg.from_user.id):
        return

    user_id = msg.from_user.id
    if user_id not in state or state[user_id]["caption"] is not None:
        return   # فقط وقتی پردازش کنیم که caption=None باشد

    # ذخیره کپشن جدید
    state[user_id]["caption"] = msg.text.strip()
    original = state[user_id]["msg"]
    preview_caption = state[user_id]["caption"] + "\n\n" + CHANNEL

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تایید", callback_data="publish_preview"),
            InlineKeyboardButton(text="✏️ ویرایش", callback_data="edit_caption_again")
        ]
    ])

    # حذف پیام متنی کاربر (اختیاری)
    try:
        await msg.delete()
    except Exception:
        pass

    # ارسال پیش‌نمایش
    try:
        if original.photo:
            await bot.send_photo(user_id, original.photo[-1].file_id, caption=preview_caption, reply_markup=kb)
        elif original.video:
            await bot.send_video(user_id, original.video.file_id, caption=preview_caption, reply_markup=kb)
    except Exception as e:
        await bot.send_message(user_id, f"❌ خطا در ساخت پیش‌نمایش: {e}")
        state.pop(user_id, None)


# ─────────────── اجرا ───────────────
async def main():
    print("🤖 Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
