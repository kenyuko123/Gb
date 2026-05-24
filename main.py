import os
import asyncio
import logging
import google.generativeai as genai
from fbchat import Client
from fbchat.models import Message, ThreadType

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("KenyukoBot")

# Cấu hình Gemini
genai.configure(api_key="AIzaSyAgoGWtjz6WAvvnjNK20AzX7NvoJXyU4tw")
model = genai.GenerativeModel('gemini-1.5-flash')

# THÔNG TIN ĐÃ NHÚNG SẴN (KHÔNG CẦN NHẬP LẠI)
MY_PROMPT = "Bạn là 1 wibu chính hiệu, nói chuyện cực kì cute, hay dùng các từ như uwu, owo, nhe, ne, nha, xưng hô là em - anh/bạn."
COOKIES = [
    {"key": "datr", "value": "Qo0RamV9_izHd8CF7L_XtF4b", "domain": "facebook.com", "path": "/"},
    {"key": "c_user", "value": "61561912502451", "domain": "facebook.com", "path": "/"},
    {"key": "xs", "value": "7%3AG1PWw91GK4Ev3Q%3A2%3A1779613393%3A-1%3A-1%3A%3AAcxPlAnijzXDR_oG3OYBOIgwPIwS85aWhdpBC72AsA", "domain": "facebook.com", "path": "/"},
    {"key": "fr", "value": "1HXVXlkEjG15GKqU2.AWcf0iNfcM4wwqccQgd37yGsP360hzqIh657cpb7c90CZ74tPf4.BqEr7X..AAA.0.0.BqEsFv.AWe2_Y5Hv28__W8AKRccMkltHRM", "domain": "facebook.com", "path": "/"}
]

class Bot(Client):
    async def on_message(self, author_id=None, message_object=None, thread_id=None, thread_type=ThreadType.USER, **kwargs):
        if author_id == self.uid or not message_object.text: return
        
        try:
            # Gửi tin nhắn đến Gemini
            chat = model.start_chat(history=[])
            response = await asyncio.to_thread(chat.send_message, f"{MY_PROMPT}\n\nNgười dùng: {message_object.text}")
            
            # Phản hồi lại Facebook
            await self.send(Message(text=response.text), thread_id=thread_id, thread_type=thread_type)
            logger.info(f"Đã trả lời: {response.text[:20]}...")
        except Exception as e:
            logger.error(f"Lỗi AI: {e}")

async def main():
    print("--- KENYUKO BOT WIBU ĐANG KHỞI ĐỘNG ---")
    try:
        bot = Bot()
        await bot.start_listing_with_cookies(COOKIES)
        print("Bot đã kết nối thành công! Đang lắng nghe tin nhắn...")
        await bot.listen()
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        print("Có vẻ Cookie đã hết hạn hoặc bị thay đổi, hãy lấy lại cookie mới.")

if __name__ == "__main__":
    asyncio.run(main())
    
