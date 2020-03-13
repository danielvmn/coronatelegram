#!/usr/bin/env python

import requests
import time
import re
import logging
import threading
import csv
from io import StringIO
from telegram import Bot
from bs4 import BeautifulSoup
from datetime import datetime
from decouple import config
from telegram.ext import Updater, CommandHandler

telegramToken = config('token')
chatid = config('chat')

format = '%(message)s'
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

def bot_listen():
    updater = Updater(token=telegramToken, use_context=True)
    dispatcher = updater.dispatcher
    gemeente_handler = CommandHandler('gemeente', gemeente)
    dispatcher.add_handler(gemeente_handler)
    updater.start_polling()

def gemeente(update, context):
    logging.info(f'Replying command "{update.message.text}".')
    gemeente = update.message.text.replace("/gemeente","")
    context.bot.sendMessage(chat_id=update.effective_chat.id, text=getStad(gemeente.strip()))

def getStad(gemeente):
    url='https://www.rivm.nl/coronavirus-kaart-van-nederland'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csvFromHtml = soup.find(id='csvData').string
    csvFile = StringIO(csvFromHtml)
    csvReader = csv.reader(csvFile, delimiter=';')
    for line in csvReader:
        if line and line[0].casefold() == gemeente.casefold():
            return f'{gemeente} heeft er {line[2]} besmet'
    return 'Kun niet deze Stad vinden'

def getNumber():
    url = 'https://www.rivm.nl/nieuws/actuele-informatie-over-coronavirus'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    allH2 = soup.findAll('td')[1]
    pattern = r'\d+'
    return int(re.findall(pattern,str(allH2))[1])

bot = Bot(token=telegramToken)
oldNumber = 0

listener = threading.Thread(target=bot_listen)
listener.daemon = True
listener.start()

while True:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if datetime.now().hour > 11 and datetime.now().hour < 16:
        number = getNumber()
        if (number != oldNumber):
            oldNumber = number
            logging.info(f'{now}: Number changed!')
            bot.sendMessage(chat_id=chatid, text=f'Update: {number} positief getest')
            bot.setChatTitle(chat_id=chatid, title=f'Corona Updates Nederland - {number} positief getest')
        else:
            logging.info(f'{now}: Number not changed')
    else:
        logging.info(f'{now}: Will only run between 12 and 3pm')

    time.sleep(60)