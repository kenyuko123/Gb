import os
import sys
import json
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from fbchat import Client
from fbchat.models import Message, ThreadType
from anthropic import Anthropic

# ==============================================================================
# 1. HỆ THỐNG GHI NHẬT KÝ (LOGGING SYSTEM) - "CỰC CHẮC"
# Đảm bảo lưu lại mọi lỗi hệ thống vào file log để theo dõi, không bị crash ngang
# ==============================================================================
log_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s: %(message)s')

# Ghi log ra màn hình
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Ghi log ra file (tối đa 5MB/file, giữ lại 2 file cũ để chống đầy bộ nhớ)
file_handler = RotatingFileHandler('bot_system.log', maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
file_handler.setFormatter(log_formatter)

logger = logging.getLogger("KenyukoAIBot")
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# ==============================================================================
# 2. HỆ THỐNG QUẢN LÝ CẤU HÌNH (CONFIGURATION MANAGER)
# ==============================================================================
CONFIG_FILE = "bot_config.json"

# Nạp sẵn AppState từ trước để tránh lỗi nếu người dùng không biết lấy
PRE_LOADED_COOKIE = [
    {"key": "c_user", "value": "61561912502451", "domain": "facebook.com", "path": "/"},
    {"key": "xs", "value": "29:RWKF6EWH0AFbfQ:2:1779535282:-1:-1::Acx_p8_RA_D4l22BS5ZtTBnp4cg44_Q9sEYE_qpmKg", "domain": "facebook.com", "path": "/"},
    {"key": "datr", "value": "Qo0RamV9_izHd8CF7L_XtF4b", "domain": "facebook.com", "path": "/"},
    {"key": "fr", "value": "1mQuWEMKaVPiRKVkR.AWd_7HaOkfd7iTi4VWc_Gp1vP9rXQ3eGErq7sOzNlGosRX2tDYI.BqEaAA..AAA.0.0.BqEaAA.AWdxrlj4ZIPH7c07s6dVH4Z0Fc4", "domain": "facebook.com", "path": "/"}
]

DEFAULT_CONFIG = {
    "systemPrompt": "Bạn là một AI thông minh, hãy trả lời ngắn gọn, thân thiện và lịch sự bằng tiếng Việt.",
    "appState": json.dumps(PRE_LOADED_COOKIE),
    "conversationHistory": {}
}

class ConfigManager:
    def __init__(self, filename):
        self.filename = filename
        self.config = self.load()

    def load(self):
        if not os.path.exists(self.filename):
            logger.info("Không tìm thấy file cấu hình, đang tạo mới...")
            self.save(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Đảm bảo cấu hình không bị thiếu key quan trọng
                for key in DEFAULT_CONFIG:
                    if key not in data:
                        data[key] = DEFAULT_CONFIG[key]
                return data
        except Exception as e:
            logger.error(f"Lỗi đọc file cấu hình, dùng cấu hình mặc định: {e}")
            return DEFAULT_CONFIG

    def save(self, data=None):
        if data is not None:
            self.config = data
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")

    def update_prompt(self, new_prompt):
        self.config["systemPrompt"] = new_prompt
        self.save()
        logger.info("Đã cập nhật System Prompt thành công!")

config_mgr = ConfigManager(CONFIG_FILE)

# ==============================================================================
# 3. LÕI XỬ LÝ AI CLAUDE TÍCH HỢP BẢO VỆ (AI CORE WRAPPER)
# ==============================================================================
# Ưu tiên lấy API key từ biến môi trường để bảo mật, nếu không có thì gán mặc định (NÊN ĐỔI)
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "SK_YOUR_ANTHROPIC_API_KEY_HERE")
anthropic_client = Anthropic(api_key=API_KEY)

async def get_ai_response(thread_id, user_message):
    try:
        # Cắt tỉa bộ nhớ: Chỉ giữ lại 8 tin nhắn gần nhất để tránh tràn RAM và tiết kiệm Token
        history = config_mgr.config["conversationHistory"].get(str(thread_id), [])[-8:]
        history.append({"role": "user", "content": user_message})

        # Xử lý bất đồng bộ tránh làm đơ bot
        response = await asyncio.to_thread(
            anthropic_client.messages.create,
            model="claude-3-haiku-20240307",
            max_tokens=800,
            system=config_mgr.config["systemPrompt"],
            messages=history
        )
        
        ai_reply = response.content[0].text
        history.append({"role": "assistant", "content": ai_reply})
        
        # Cập nhật lại bộ nhớ
        config_mgr.config["conversationHistory"][str(thread_id)] = history
        config_mgr.save()
        
        return ai_reply
    except Exception as e:
        logger.error(f"Lỗi từ Claude AI API: {e}")
        return "Xin lỗi, hiện tại não bộ AI đang gặp chút sự cố kết nối. Vui lòng thử lại sau vài phút nhé!"

# ==============================================================================
# 4. LÕI KẾT NỐI FACEBOOK (FACEBOOK CLIENT BOT)
# ==============================================================================
class RobustFacebookBot(Client):
    async def on_message(self, mid=None, author_id=None, message_object=None, thread_id=None, thread_type=ThreadType.USER, **kwargs):
        # Chặn tự reply chính mình (Loop vô tận)
        if author_id == self.uid:
            return

        user_text = message_object.text
        if not user_text:
            return

        logger.info(f"[*] Nhận tin nhắn từ [ID:{author_id}] tại [Thread:{thread_id}]: {user_text}")

        # Try/Except toàn cục cho mỗi tin nhắn để đảm bảo 1 tin nhắn lỗi không làm chết cả bot
        try:
            # Tạo cảm giác giống người thật: Đã xem và Đang gõ chữ
            await self.mark_as_read(thread_id)
            await self.set_typing_status(True, thread_id=thread_id, thread_type=thread_type)

            # Gọi AI xử lý
            ai_reply = await get_ai_response(thread_id, user_text)

            # Phản hồi khách hàng
            await self.send(Message(text=ai_reply), thread_id=thread_id, thread_type=thread_type)
            logger.info(f"[+] Phản hồi thành công cho [Thread:{thread_id}]")

        except Exception as e:
            logger.error(f"Lỗi nghiêm trọng khi xử lý tin nhắn của thread {thread_id}: {e}")
        finally:
            # Bắt buộc phải tắt trạng thái typing dù code chạy thành công hay lỗi
            try:
                await self.set_typing_status(False, thread_id=thread_id, thread_type=thread_type)
            except:
                pass

# ==============================================================================
# 5. GIAO DIỆN TƯƠNG TÁC DÒNG LỆNH (CLI MENU) - THEO YÊU CẦU NGƯỜI DÙNG
# ==============================================================================
async def start_bot_engine():
    logger.info("Đang khởi động động cơ kết nối Facebook...")
    try:
        cookies = json.loads(config_mgr.config["appState"])
        bot = RobustFacebookBot()
        
        await bot.start_listing_with_cookies(cookies)
        logger.info("==================================================")
        logger.info("   [THÀNH CÔNG] BOT KENYUKO ĐANG TRỰC TUYẾN !   ")
        logger.info("   (Nhấn Ctrl + C để dừng hệ thống an toàn)       ")
        logger.info("==================================================")
        
        # Bắt đầu vòng lặp lắng nghe tin nhắn mãi mãi
        await bot.listen()
    except Exception as e:
        logger.critical(f"Không thể khởi động Bot. Sai AppState hoặc tài khoản bị khóa: {e}")
        sys.exit(1)

def clear_screen():
    # Tự động xóa màn hình cho gọn tùy theo hệ điều hành (Windows hoặc Termux/Linux)
    os.system('cls' if os.name == 'nt' else 'clear')

async def main_menu():
    clear_screen()
    while True:
        print("\n" + "="*50)
        print("          KENYUKO AI MESSENGER BOT v1.0          ")
        print("="*50)
        print(f"[*] Prompt hiện tại: '{config_mgr.config['systemPrompt'][:45]}...'")
        print("-"*50)
        print("Vui lòng chọn chức năng hệ thống:")
        print("   [1] Cấu hình tính cách / System Prompt cho AI")
        print("   [2] Bắt đầu chạy Bot")
        print("   [3] Thoát chương trình")
        print("="*50)
        
        try:
            choice = input(">> Nhập lựa chọn của bạn (1/2/3): ").strip()
        except KeyboardInterrupt:
            print("\nĐã ép buộc thoát.")
            sys.exit(0)
            
        if choice == '1':
            print("\n[HƯỚNG DẪN]: Nhập tính cách bạn muốn AI đóng vai (VD: Bạn là một cô gái vui tính, xưng hô là em và anh...).")
            new_prompt = input(">> Nhập System Prompt mới: ").strip()
            if new_prompt:
                config_mgr.update_prompt(new_prompt)
                print("\n[OK] Đã lưu Prompt vào cơ sở dữ liệu!")
                await asyncio.sleep(1)
                clear_screen()
            else:
                print("\n[LỖI] Bạn chưa nhập gì cả. Hủy thao tác.")
                
        elif choice == '2':
            clear_screen()
            # Bắt đầu luồng chạy ngầm của bot
            await start_bot_engine()
            break
            
        elif choice == '3':
            print("Đang dọn dẹp hệ thống... Tạm biệt!")
            sys.exit(0)
        else:
            print("\n[LỖI] Lựa chọn không hợp lệ, vui lòng nhập 1, 2 hoặc 3.")

# ==============================================================================
# 6. KHỞI ĐỘNG HỆ THỐNG CÙNG ASYNCIO
# ==============================================================================
if __name__ == "__main__":
    try:
        # Tương thích với môi trường Windows nếu chạy local
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        logger.info("Hệ thống đã được tắt thủ công bởi người dùng (Ctrl+C).")
        sys.exit(0)
    except Exception as fatal_error:
        logger.critical(f"Sụp đổ hệ thống không xác định: {fatal_error}")
        sys.exit(1)
        