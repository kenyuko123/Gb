import asyncio
import json
import logging
from fbchat import Client, State
from fbchat.models import Message, ThreadType
import google.generativeai as genai

# Cấu hình
logging.basicConfig(level=logging.INFO)
genai.configure(api_key="AIzaSyAgoGWtjz6WAvvnjNK20AzX7NvoJXyU4tw")
model = genai.GenerativeModel('gemini-1.5-flash')

# COOKIE CỦA BẠN (Dán trực tiếp vào đây)
COOKIES = [
    {"key": "datr", "value": "Q9gSaii6UWMoP5VWEjGVV4F_", "domain": "facebook.com", "path": "/"},
    {"key": "c_user", "value": "61561912502451", "domain": "facebook.com", "path": "/"},
    {"key": "xs", "value": "6%3AqD7n78JOHhGvvw%3A2%3A1779619936%3A-1%3A-1%3A%3AAcx-YPLm5Z02omKAkW6YBVOryvDpsPpWQ4wTLt4ODw", "domain": "facebook.com", "path": "/"},
    {"key": "fr", "value": "10L4GzWfeCe9fBOhp.AWdz5jpT_8v3yH_ZbrU_FGEMMlAS2DLIlU6gYSHoG3vBhYMbwaY.BqEthl..AAA.0.0.BqEthl.AWd30436II1nK7lHAuSAzk371U0", "domain": "facebook.com", "path": "/"}
]

# PROMPT
MY_PROMPT = "Bạn là 1 wibu chính hiệu, nói chuyện cực kì cute, hay dùng các từ như uwu, owo, nhe, ne, nha, xưng hô là em - anh/bạn."

class WibuBot(Client):
    async def on_message(self, author_id=None, message_object=None, thread_id=None, thread_type=ThreadType.USER, **kwargs):
        if author_id == self.uid or not message_object.text: return
        
        # AI xử lý
        try:
            chat = model.start_chat(history=[])
            resp = await asyncio.to_thread(chat.send_message, f"{MY_PROMPT}\n\nNgười dùng: {message_object.text}")
            await self.send(Message(text=resp.text), thread_id=thread_id, thread_type=thread_type)
        except Exception as e:
            print(f"Lỗi AI: {e}")

async def main():
    try:
        # Sử dụng State để load trực tiếp cookie mà không qua login password
        state = State.from_cookies(COOKIES)
        bot = WibuBot(session=state)
        print("--- BOT ĐÃ SẴN SÀNG (WIBU MODE) ---")
        await bot.listen()
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        print("Mẹo: Cookie này có thể đã bị Facebook chặn do truy cập từ IP của Replit.")

if __name__ == "__main__":
    asyncio.run(main())
