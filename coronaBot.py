#!/usr/bin/env python

import requests
import time
import re
import logging
import threading
import csv
import pathlib
from io import StringIO
from telegram import Bot
from bs4 import BeautifulSoup
from datetime import datetime
from decouple import config, Csv
from telegram.ext import Updater, CommandHandler

# Environment settings (Telegram chat id / API token)
telegramToken = config('token')
mainGroupid = config('main_group')
updateChats = config('chats', cast=Csv())
disabledChats = config('disabled_chats', cast=Csv())

# Logging setup
format = '%(asctime)-15s %(message)s'
logging.basicConfig(format=format, level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

# Starts Bot listener to reply to /commands
def bot_listen():
    updater = Updater(token=telegramToken, use_context=True)
    dispatcher = updater.dispatcher

    # Handler for '/help'
    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)

    # Handler for '/total'
    total_handler = CommandHandler('total', total)
    totaal_handler = CommandHandler('totaal', total)
    dispatcher.add_handler(total_handler)
    dispatcher.add_handler(totaal_handler)

    # The handler will call the gemeente method if the /gemeente command is called
    gemeente_handler = CommandHandler('gemeente', gemeente)
    dispatcher.add_handler(gemeente_handler)

    # Starts polling for commands
    updater.start_polling()

def gemeente(update, context):
    if (str(update.effective_chat.id) not in disabledChats):
        logging.info(f'Replying command "{update.message.text}" from {update.effective_user.first_name}.')
        # Extracts the string after '/gemeente' to retrieve the gemeente to search for
        gemeente = update.message.text.replace('/gemeente','')
        if (gemeente):
            context.bot.sendMessage(chat_id=update.effective_chat.id, text=getGemeente(gemeente.strip()))
        else:
            context.bot.sendMessage(chat_id=update.effective_chat.id, text="Gebruik: /gemeente <naam>")
    else:
        logging.info(f'Skipping update to disbled group {update.effective_chat.title}')

def help(update, context):
    logging.info(f'Replying command "{update.message.text}" from {update.effective_user.first_name}.')
    context.bot.sendMessage(chat_id=update.effective_chat.id,
        text='Gebruik: _/gemeente <naam>_\nbijv: _/gemeente Amsterdam_\n\n_/total_ voor totals',
        parse_mode = "Markdown")

def total(update, context):
    logging.info(f'Replying command "{update.message.text}" from {update.effective_user.first_name}.')
    totalText = f'Total positief getest: {getTotal()}'
    context.bot.sendMessage(chat_id=update.effective_chat.id, text=totalText)

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
            return f'{gemeente} heeft er {line[2]} positief getest'
    return f'kan gemeente {gemeente} niet vinden of er zijn 0 positief getest.'

# Scaps the total number of infected from RIVM
def getTotal():
    url = 'https://www.rivm.nl/nieuws/actuele-informatie-over-coronavirus'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    allH2 = soup.findAll('td')[1]
    pattern = r'\d+'
    return int(re.findall(pattern,str(allH2))[1])

# Saves current totals to a file
def writeToFile(number):
    with open('number.txt', 'w+') as totalsFile:
        totalsFile.write(str(number))

# Reads from the file to check if the number changed
def ReadFromFile():
    if (pathlib.Path('number.txt').exists()):
        with open('number.txt', 'r') as totalsFile:
            return totalsFile.read()
    else:
        return 0

# Declares and starts the listener thread
listener = threading.Thread(target=bot_listen)
listener.daemon = True
listener.start()

bot = Bot(token=telegramToken)

while True:
    oldNumber = int(ReadFromFile())
    # The updates are usually done at around 14:00, so we only poll around that time.
    if datetime.now().hour > 10 and datetime.now().hour < 17:
        number = getTotal()
        if (number != oldNumber):
            diff = int(number) - int(oldNumber)
            oldNumber = number
            logging.info(f'Number changed! New number: {number} (+{diff})')
            bot.setChatTitle(chat_id=mainGroupid, title=f'Corona Updates Nederland - {number} positief getest')
            for chat in updateChats:
                bot.sendMessage(chat_id=chat, text=f'Update: {number} positief getest (+{diff})')
            writeToFile(number)
        else:
            logging.info('Number not changed')
    else:
        logging.info('Will only run between 11h and 16h')

    # We don't need to look for new data every moment, so it will poll every 60 seconds
    time.sleep(60)