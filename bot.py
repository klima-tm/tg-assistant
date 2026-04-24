from dotenv import load_dotenv
import os
import requests
import telebot
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
PERSONA_FILE = BASE_DIR / "persona.txt"
MEMORY_FILE = BASE_DIR / "memory.json"
MESSAGES_FILE = BASE_DIR / "messages.json"

load_dotenv(ENV_FILE)

with open(PERSONA_FILE, "r") as f:
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
    with open(MESSAGES_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def load_memory():
    if os.path.exists(MEMORY_FILE): 
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(histories):
    temp_file = MEMORY_FILE.with_suffix(".json.tmp")
    with open(temp_file, "w") as f:
        json.dump(histories, f, indent=2, ensure_ascii=False)
    temp_file.replace(MEMORY_FILE)

def save_readable_log(user_id, username):
    user_id = str(user_id)
    if user_id not in conversation_histories:
        return
    
    user_data = conversation_histories[user_id]
    filename = BASE_DIR / f"logs/{user_id}_{username or 'unknown'}.txt"
    filename.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"USER: {username}\n")
        f.write(f"ID: {user_id}\n")
        f.write("=" * 40 + "\n\n")
        
        if user_data.get("facts"):
            f.write("KEY FACTS:\n")
            for fact_group in user_data["facts"]:
                for fact in str(fact_group).splitlines():
                    fact = fact.strip()
                    if fact:
                        f.write(f"{fact}\n")
            f.write("\n" + "=" * 40 + "\n\n")
        
        f.write("FULL MESSAGE HISTORY:\n\n")
        for msg in user_data.get("all_messages", user_data["messages"]):
            role = "You" if msg["role"] == "user" else "Klima"
            f.write(f"{role}: {msg['content']}\n\n")

conversation_histories = load_memory()

MAX_MESSAGES_BEFORE_COMPRESSION = 8
MESSAGES_TO_KEEP = 4

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
        conversation_histories[user_id] = {"facts": [], "messages": [], "all_messages": []}
    
    user_data = conversation_histories[user_id]
    if "all_messages" not in user_data:
        user_data["all_messages"] = list(user_data["messages"])
    user_data["messages"].append({"role": "user", "content": question})
    user_data["all_messages"].append({"role": "user", "content": question})
    
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
    user_data["all_messages"].append({"role": "assistant", "content": reply})
    save_memory(conversation_histories)
    return reply

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    log_message(username, user_text)
    response = ask_claude(user_id, user_text)
    save_readable_log(user_id, username)
    bot.reply_to(message, response)

print("Bot is running...")
bot.polling()