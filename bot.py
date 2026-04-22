from dotenv import load_dotenv
import os
import requests
import telebot
import json
from datetime import datetime

load_dotenv()

with open("persona.txt", "r") as f:
    PERSONA = f.read()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def log_message(user, text):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "from": user,
        "message": text
    }
    with open("messages.json", "a") as f:
        f.write(json.dumps(entry) + "\n")

MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE): 
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(histories):
    with open(MEMORY_FILE, "w") as f:
        json.dump(histories, f, indent=2, ensure_ascii=False)

conversation_histories = load_memory()

MAX_MESSAGES_BEFORE_COMPRESSION = 40
MESSAGES_TO_KEEP = 30

def compress_history(old_messages):
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 500,
            "system": "You compress conversation history into key facts about the user. Output a concise bulleted list of facts: who they are, what they want, what was discussed, any commitments made. Be specific and brief.",
            "messages": [
                {"role": "user", "content": f"Summarize these messages into key facts:\n\n{json.dumps(old_messages)}"}
            ]
        }
    )
    return response.json()["content"][0]["text"]

def ask_claude(user_id, question):
    user_id = str(user_id)
    
    if user_id not in conversation_histories:
        conversation_histories[user_id] = {"facts": [], "messages": []}
    
    user_data = conversation_histories[user_id]
    user_data["messages"].append({"role": "user", "content": question})
    
    if len(user_data["messages"]) > MAX_MESSAGES_BEFORE_COMPRESSION:
        old = user_data["messages"][:-MESSAGES_TO_KEEP]
        new_facts = compress_history(old)
        user_data["facts"].append(new_facts)
        user_data["messages"] = user_data["messages"][-MESSAGES_TO_KEEP:]
    
    system_prompt = PERSONA
    if user_data["facts"]:
        system_prompt += "\n\nKNOWN FACTS ABOUT THIS USER:\n" + "\n".join(user_data["facts"])
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "cache_control": {"type": "ephemeral"},
            "system": system_prompt,
            "messages": user_data["messages"]
        }
    )
    
    data = response.json()
    reply = data["content"][0]["text"]
    
    user_data["messages"].append({"role": "assistant", "content": reply})
    save_memory(conversation_histories)
    return reply

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    log_message(username, user_text)
    response = ask_claude(user_id, user_text)
    bot.reply_to(message, response)

print("Bot is running...")
bot.polling()