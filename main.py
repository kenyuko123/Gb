import os
import sys
import json
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import google.generativeai as genai
from fbchat import Client
from fbchat.models import Message, ThreadType

# ==============================================================================
# 1. HỆ THỐNG GHI NHẬT KÝ (LOGGING)
# ==============================================================================
log_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("KenyukoGeminiBot")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler('bot_system.log', maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# ==============================================================================
# 2. CẤU HÌNH API GEMINI
# ==============================================================================
GEMINI_API_KEY = "AIzaSyAgoGWtjz6WAvvnjNK20AzX7NvoJXyU4tw"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==============================================================================
# 3. QUẢN LÝ CẤU HÌNH (CONFIG MANAGER)
# ==============================================================================
CONFIG_FILE = "bot_config.json"

def load_config():
    default = {
        "systemPrompt": "Bạn là một AI thông minh, hãy trả lời ngắn gọn, thân thiện và lịch sự bằng tiếng Việt.",
        "appState": "",
        "conversationHistory": {}
    }
    if not os.path.exists(CONFIG_FILE):
        return default
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

config = load_config()

def save_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# ==============================================================================
# 4. LÕI AI GEMINI
# ==============================================================================
async def get_ai_response(thread_id, user_message):
    try:
        chat = model.start_chat(history=[])
        full_prompt = f"{config['systemPrompt']}\n\nNgười dùng: {user_message}"
        response = await asyncio.to_thread(chat.send_message, full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Lỗi AI: {e}")
        return "Xin lỗi, mình đang gặp sự cố kết nối AI."

# ==============================================================================
# 5. LÕI BOT FACEBOOK
# ==============================================================================
class RobustFacebookBot(Client):
    async def on_message(self, author_id=None, message_object=None, thread_id=None, thread_type=ThreadType.USER, **kwargs):
        if author_id == self.uid or not message_object.text:
            return
        
        logger.info(f"Nhận tin từ {author_id}: {message_object.text}")
        try:
            await self.set_typing_status(True, thread_id=thread_id, thread_type=thread_type)
            reply = await get_ai_response(thread_id, message_object.text)
            await self.send(Message(text=reply), thread_id=thread_id, thread_type=thread_type)
        except Exception as e:
            logger.error(f"Lỗi gửi tin: {e}")
        finally:
            await self.set_typing_status(False, thread_id=thread_id, thread_type=thread_type)

# ==============================================================================
# 6. MENU ĐIỀU KHIỂN
# ==============================================================================
async def run_bot():
    if not config["appState"]:
        print("LỖI: AppState trống! Hãy chọn [2] để nhập.")
        return
    try:
        cookies = json.loads(config["appState"])
        bot = RobustFacebookBot()
        await bot.start_listing_with_cookies(cookies)
        print("Bot đang chạy... (Nhấn Ctrl+C để dừng)")
        await bot.listen()
    except Exception as e:
        print(f"Lỗi đăng nhập: {e}")

async def main():
    while True:
        print("\n=== KENYUKO BOT MENU ===")
        print("[1] Cài Prompt AI")
        print("[2] Nhập AppState (Dán chuỗi cookie vào đây)")
        print("[3] Chạy Bot")
        print("[4] Thoát")
        choice = input("Chọn: ")
        
        if choice == '1':
            config["systemPrompt"] = input("Nhập Prompt mới: ")
            save_config()
        elif choice == '2':
            # Nhận chuỗi từ người dùng và kiểm tra ngay
            raw_cookie = input("Dán toàn bộ chuỗi AppState (từ [ đến ]): ").strip()
            try:
                json.loads(raw_cookie) # Kiểm tra định dạng JSON
                config["appState"] = raw_cookie
                save_config()
                print("Lưu AppState thành công!")
            except:
                print("LỖI: Chuỗi bạn dán không phải là định dạng JSON hợp lệ.")
        elif choice == '3':
            await run_bot()
            break
        elif choice == '4':
            sys.exit()

if __name__ == "__main__":
    asyncio.run(main())
