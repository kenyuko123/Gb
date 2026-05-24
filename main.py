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
# 1. HỆ THỐNG GHI NHẬT KÝ (LOGGING SYSTEM)
# ==============================================================================
log_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s: %(message)s')
logger = logging.getLogger("KenyukoGeminiBot")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler('bot_system.log', maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# ==============================================================================
# 2. CẤU HÌNH GEMINI & QUẢN LÝ CẤU HÌNH
# ==============================================================================
CONFIG_FILE = "bot_config.json"
genai.configure(api_key="AIzaSyAgoGWtjz6WAvvnjNK20AzX7NvoJXyU4tw")
model = genai.GenerativeModel('gemini-1.5-flash')

DEFAULT_CONFIG = {
    "systemPrompt": "Bạn là một AI thông minh, hãy trả lời ngắn gọn, thân thiện và lịch sự bằng tiếng Việt.",
    "appState": "",
    "conversationHistory": {}
}

class ConfigManager:
    def __init__(self, filename):
        self.filename = filename
        self.config = self.load()

    def load(self):
        if not os.path.exists(self.filename):
            self.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return DEFAULT_CONFIG

    def save(self, data=None):
        if data is not None: self.config = data
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    def update_prompt(self, new_prompt):
        self.config["systemPrompt"] = new_prompt
        self.save()

config_mgr = ConfigManager(CONFIG_FILE)

# ==============================================================================
# 3. LÕI AI GEMINI
# ==============================================================================
async def get_ai_response(thread_id, user_message):
    try:
        chat = model.start_chat(history=[])
        full_prompt = f"{config_mgr.config['systemPrompt']}\n\nNgười dùng: {user_message}"
        response = await asyncio.to_thread(chat.send_message, full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"Lỗi Gemini AI: {e}")
        return "Xin lỗi, hiện tại não bộ AI đang gặp sự cố. Vui lòng thử lại sau!"

# ==============================================================================
# 4. LÕI KẾT NỐI FACEBOOK
# ==============================================================================
class RobustFacebookBot(Client):
    async def on_message(self, author_id=None, message_object=None, thread_id=None, thread_type=ThreadType.USER, **kwargs):
        if author_id == self.uid or not message_object.text:
            return

        logger.info(f"[*] Nhận tin nhắn từ [ID:{author_id}]: {message_object.text}")

        try:
            await self.mark_as_read(thread_id)
            await self.set_typing_status(True, thread_id=thread_id, thread_type=thread_type)
            ai_reply = await get_ai_response(thread_id, message_object.text)
            await self.send(Message(text=ai_reply), thread_id=thread_id, thread_type=thread_type)
        except Exception as e:
            logger.error(f"Lỗi xử lý tin nhắn: {e}")
        finally:
            await self.set_typing_status(False, thread_id=thread_id, thread_type=thread_type)

# ==============================================================================
# 5. GIAO DIỆN MENU
# ==============================================================================
async def start_bot_engine():
    if not config_mgr.config["appState"]:
        print("LỖI: Bạn chưa nhập AppState (Cookie)!")
        return
        
    try:
        cookies = json.loads(config_mgr.config["appState"])
        bot = RobustFacebookBot()
        await bot.start_listing_with_cookies(cookies)
        logger.info("Bot đang trực tuyến!")
        await bot.listen()
    except Exception as e:
        logger.critical(f"Lỗi khởi động: {e}")

async def main_menu():
    while True:
        print("\n--- KENYUKO GEMINI BOT ---")
        print("[1] Cấu hình tính cách / System Prompt")
        print("[2] Nhập AppState (Cookie)")
        print("[3] Bắt đầu chạy Bot")
        print("[4] Thoát")
        
        choice = input(">> Lựa chọn: ")
        if choice == '1':
            config_mgr.update_prompt(input("Nhập Prompt mới: "))
        elif choice == '2':
            config_mgr.config["appState"] = input("Dán AppState vào đây: ").strip()
            config_mgr.save()
        elif choice == '3':
            await start_bot_engine()
            break
        elif choice == '4':
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main_menu())
        
