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

# Environment settings (Telegram chat id / API token)
telegramToken = config('token')
chatid = config('chat')

# Logging setup
format = '%(message)s'
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

# Starts Bot listener to reply to /commands
def bot_listen():
    updater = Updater(token=telegramToken, use_context=True)
    dispatcher = updater.dispatcher
    # The handler will call the gemeente method if the /gemeente command is called
    gemeente_handler = CommandHandler('gemeente', gemeente)
    dispatcher.add_handler(gemeente_handler)
    # Starts polling for commands
    updater.start_polling()

def gemeente(update, context):
    logging.info(f'Replying command "{update.message.text}".')
    # Extracts the string after '/gemeente' to retrieve the gemeente to search for
    gemeente = update.message.text.replace("/gemeente","")
    context.bot.sendMessage(chat_id=update.effective_chat.id, text=getGemeente(gemeente.strip()))

# Scraps the CSV data from RIVM
def getGemeente(gemeente):
    url='https://www.rivm.nl/coronavirus-kaart-van-nederland'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csvFromHtml = soup.find(id='csvData').string
    csvFile = StringIO(csvFromHtml)
    csvReader = csv.reader(csvFile, delimiter=';')
    for line in csvReader:
        if line and line[0].casefold() == gemeente.casefold():
            return f'{gemeente} heeft er {line[2]} besmet'
    return f'kan gemeente {gemeente} niet vinden'

# Scaps the total number of infected from RIVM
def getNumber():
    url = 'https://www.rivm.nl/nieuws/actuele-informatie-over-coronavirus'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    allH2 = soup.findAll('td')[1]
    pattern = r'\d+'
    return int(re.findall(pattern,str(allH2))[1])

# Declares and starts the listener thread
listener = threading.Thread(target=bot_listen)
listener.daemon = True
listener.start()

bot = Bot(token=telegramToken)

oldNumber = 0

while True:
    # The updates are usually done at around 14:00, so we only poll around that time.
    if datetime.now().hour > 11 and datetime.now().hour < 16:
        number = getNumber()
        if (number != oldNumber):
            oldNumber = number
            logging.info('Number changed!')
            bot.sendMessage(chat_id=chatid, text=f'Update: {number} positief getest')
            bot.setChatTitle(chat_id=chatid, title=f'Corona Updates Nederland - {number} positief getest')
        else:
            logging.info('Number not changed')
    else:
        logging.info('Will only run between 12h and 15h')

    # We don't need to look for new data every moment, so it will poll every 60 seconds
    time.sleep(60)