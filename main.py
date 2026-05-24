import asyncio
import logging
import google.generativeai as genai
from fbchat import Client
from fbchat.models import Message, ThreadType

# --- CẤU HÌNH CỐ ĐỊNH ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("KenyukoBot")

# API KEY
genai.configure(api_key="AIzaSyAgoGWtjz6WAvvnjNK20AzX7NvoJXyU4tw")
model = genai.GenerativeModel('gemini-1.5-flash')

# PROMPT
MY_PROMPT = "Bạn là 1 wibu chính hiệu, nói chuyện cực kì cute, hay dùng các từ như uwu, owo, nhe, ne, nha, xưng hô là em - anh/bạn."

# COOKIES (Thông tin tài khoản của bạn)
COOKIES = [
    {"key": "datr", "value": "Qo0RamV9_izHd8CF7L_XtF4b", "domain": "facebook.com", "path": "/"},
    {"key": "c_user", "value": "61561912502451", "domain": "facebook.com", "path": "/"},
    {"key": "xs", "value": "7%3AG1PWw91GK4Ev3Q%3A2%3A1779613393%3A-1%3A-1%3A%3AAcxPlAnijzXDR_oG3OYBOIgwPIwS85aWhdpBC72AsA", "domain": "facebook.com", "path": "/"},
    {"key": "fr", "value": "1HXVXlkEjG15GKqU2.AWcf0iNfcM4wwqccQgd37yGsP360hzqIh657cpb7c90CZ74tPf4.BqEr7X..AAA.0.0.BqEsFv.AWe2_Y5Hv28__W8AKRccMkltHRM", "domain": "facebook.com", "path": "/"}
]

# --- LÕI BOT ---
class Bot(Client):
    async def on_message(self, author_id=None, message_object=None, thread_id=None, thread_type=ThreadType.USER, **kwargs):
        # Bỏ qua nếu là tin nhắn của chính mình hoặc tin nhắn trống
        if author_id == self.uid or not message_object.text: return
        
        try:
            logger.info(f"Đang nhận tin nhắn từ {author_id}...")
            chat = model.start_chat(history=[])
            # Gửi yêu cầu tới Gemini
            response = await asyncio.to_thread(chat.send_message, f"{MY_PROMPT}\n\nNgười dùng: {message_object.text}")
            
            # Gửi phản hồi lại Facebook
            await self.send(Message(text=response.text), thread_id=thread_id, thread_type=thread_type)
            logger.info("Đã trả lời thành công.")
        except Exception as e:
            logger.error(f"Lỗi khi xử lý tin nhắn: {e}")

async def main():
    print("--- KENYUKO BOT WIBU ĐANG CHẠY ---")
    try:
        bot = Bot()
        # Đăng nhập bằng cookie đã nhúng
        await bot.start_listing_with_cookies(COOKIES)
        print("Bot đã kết nối. Đang chờ tin nhắn...")
        await bot.listen()
    except Exception as e:
        print(f"Lỗi khởi động: {e}")
        print("Vui lòng kiểm tra lại Cookie. Nếu vẫn lỗi, hãy lấy lại cookie mới trên trình duyệt.")

if __name__ == "__main__":
    asyncio.run(main())
    
