from datetime import datetime
import os
import re

import telebot
from telebot import types
from dotenv import load_dotenv

from telegram_logic.router import new_data


load_dotenv()

token  =  os.getenv("TELEGRAM_API_TOKEN")
bot = telebot.TeleBot(token)


@bot.message_handler(content_types=['text'], func=lambda message: not message.text.startswith('/'))
def catch_message(message):
    status = new_data(message.from_user.id, message.text, 'text', datetime.now().isoformat())
    if status:
        bot.reply_to(message, "Text received!")
    else:
        bot.reply_to(message, "Failed to receive the text.\nTry again later!")


# @bot.message_handler(content_types=['voice', 'audio'])
# def catch_audio(message):
#     # Get file ID for voice or standard audio
#     file_id = message.voice.file_id if message.voice else message.audio.file_id
    
#     # Retrieve file info from Telegram servers
#     file_info = bot.get_file(file_id)
        
#     bot.reply_to(message, "Audio caught successfully!")


# @bot.message_handler(content_types=['photo'])
# def catch_image(message):
#     # Get file ID for the image
#     file_id = message.photo[-1].file_id  # Get the largest image
    
#     # Retrieve file info from Telegram servers
#     file_info = bot.get_file(file_id)
        
#     bot.reply_to(message, "Photo caught successfully!")


# @bot.message_handler(content_types=['video'])
# def catch_video(message):
#     # Get file ID for the video
#     file_id = message.video.file_id

#     # Retrieve file info from Telegram servers
#     file_info = bot.get_file(file_id)
        
#     bot.reply_to(message, "Video caught successfully!")



# Start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome to the bot!")

    



def run_bot():
    bot.polling(none_stop=True)

run_bot()