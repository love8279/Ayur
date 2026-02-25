import os
import telebot
import requests
from dotenv import load_dotenv

load_dotenv()

# Config from Environment Variables
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

BASE_URL = "https://server2.qik.ai/app"
HEADERS = {"Content-Type": "text/plain"}
APP_ID = "shbjnnhfcp"
BUILD_CONFIG_ID = "kZF05Q6YgV"

user_data = {}

def call_api(endpoint, data):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.post(url, headers=HEADERS, json=data)
    return response.json()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 **Ayur Guide Extractor**\n\nCommands:\n/login [Phone]\n/otp [OTP]\n/batches - List courses\n/extract [No.] - Get links")

@bot.message_handler(commands=['login'])
def handle_login(message):
    try:
        phone = message.text.split()[1]
        data = {
            "phone": phone,
            "_ApplicationId": APP_ID,
            "_ClientVersion": "js6.1.1",
            "_InstallationId": "4f7cb273-0d5a-4802-8a92-e022215ef5c7"
        }
        call_api("functions/SendOTPv2", data)
        user_data[message.chat.id] = {"phone": phone}
        bot.reply_to(message, "✅ OTP bhej diya gaya hai. Ab `/otp 123456` format mein bhejein.")
    except:
        bot.reply_to(message, "❌ Format: `/login 7845125689`")

@bot.message_handler(commands=['otp'])
def handle_otp(message):
    try:
        otp = message.text.split()[1]
        chat_id = message.chat.id
        phone = user_data[chat_id]['phone']
        data = {
            "phone": phone, "otp": otp,
            "_ApplicationId": APP_ID, "_ClientVersion": "js6.1.1",
            "_InstallationId": "4f7cb273-0d5a-4802-8a92-e022215ef5c7"
        }
        res = call_api("functions/AuthenticationV2", data)
        user_data[chat_id]['token'] = res["result"][0]["sessionToken"]
        bot.reply_to(message, "✅ Login Successful! Use /batches.")
    except:
        bot.reply_to(message, "❌ OTP galat hai.")

@bot.message_handler(commands=['batches'])
def list_batches(message):
    chat_id = message.chat.id
    token = user_data.get(chat_id, {}).get('token')
    if not token: return bot.reply_to(message, "Pehle /login karein.")

    where = {"AppId": {"__type": "Pointer", "className": "elearning_BuildConfig", "objectId": BUILD_CONFIG_ID}, "IsDeleted": {"$ne": True}}
    data = {"where": where, "limit": 50, "_method": "GET", "_ApplicationId": APP_ID, "_SessionToken": token}
    
    batches = call_api("classes/elearning_Course", data)["results"]
    user_data[chat_id]['batches'] = batches
    
    msg = "📚 **Available Batches:**\n"
    for i, b in enumerate(batches):
        msg += f"{i+1}. {b['CourseTitle']}\n"
    bot.reply_to(message, msg + "\nExtract karne ke liye `/extract 1` type karein.")

@bot.message_handler(commands=['extract'])
def extract_data(message):
    chat_id = message.chat.id
    try:
        idx = int(message.text.split()[1]) - 1
        selected = user_data[chat_id]['batches'][idx]
        token = user_data[chat_id]['token']
        
        bot.reply_to(message, f"⏳ {selected['CourseTitle']} extract ho raha hai...")
        
        # Get Videos & PDFs
        common_where = {"AppId": {"__type": "Pointer", "className": "elearning_BuildConfig", "objectId": BUILD_CONFIG_ID}, "CoursePtr": {"__type": "Pointer", "className": "elearning_Course", "objectId": selected["objectId"]}}
        
        vid_data = {"where": {**common_where, "Type": {"$in": ["Original"]}, "IsDeleted": {"$ne": True}}, "_method": "GET", "_ApplicationId": APP_ID, "_SessionToken": token}
        pdf_data = {"where": {**common_where, "FileType": {"$in": ["pdf", "PDF", "png", "JPG", "jpeg"]}}, "_method": "GET", "_ApplicationId": APP_ID, "_SessionToken": token}
        
        videos = call_api("classes/elearning_Videos", vid_data)["results"]
        pdfs = call_api("classes/elearning_CourseMaterial", pdf_data)["results"]
        
        filename = f"{selected['CourseTitle'].replace(' ', '_')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for v in videos: f.write(f"VIDEO: {v['VideoName']} -> {v['OriginalFileURL']}\n")
            for p in pdfs: f.write(f"PDF: {p['Name']} -> {p['Link']}\n")
        
        with open(filename, 'rb') as f:
            bot.send_document(chat_id, f, caption=f"✅ Total: {len(videos)+len(pdfs)} links extracted.")
        os.remove(filename)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

bot.polling()
  
