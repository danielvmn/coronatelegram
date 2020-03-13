#!/usr/bin/env python

import requests
import time
import re
from telegram import Bot
from bs4 import BeautifulSoup
from datetime import datetime
from decouple import config

def getNumber():
    url = 'https://www.rivm.nl/nieuws/actuele-informatie-over-coronavirus'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    allH2 = soup.findAll('td')[1]
    pattern = r'\d+'
    return int(re.findall(pattern,str(allH2))[1])

telegramToken = config('token')
chatid = -352217135
bot = Bot(token=telegramToken)
oldNumber = 0

while True:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if datetime.now().hour > 11 and datetime.now().hour < 16:
        number = getNumber()
        if (number != oldNumber):
            oldNumber = number
            print(f'{now}: Number changed!')
            bot.sendMessage(chat_id=chatid, text=f'New Number: {number}')
            bot.setChatTitle(chat_id=chatid, title=f'Corona Updates - {number}')
        else:
            print(f'{now}: Number not changed')
    else:
        print(f'{now}: Will only run between 12 and 3pm')

    time.sleep(60)