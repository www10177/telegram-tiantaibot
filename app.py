# -*- coding: UTF-8 -*-
import zipfile
import asyncio
from telegram import Bot, Update
from telegram.ext import Application
from http import HTTPStatus

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

import requests
import logging
import os
from datetime import datetime,date,timezone,timedelta
import re
import json
from dotenv import load_dotenv

currencies = []
crypto={}

class WebhookUpdate:
    """Simple dataclass to wrap a custom update type"""

    user_id: int
    payload: str

def load_currencies():
    global currencies 
    with open('currencies.json','r') as f:
        data = json.load(f)
    for  key,value in data['results'].items():
        currencies.append((value['id'],value['currencyName']))
    currencies.sort(key=lambda x : x[1])
        

def load_crypto():
    global crypto
    with open('crypto.json','r') as f:
        data = json.load(f)
    for d in data:
        crypto[d['symbol']] = d['id']

def load_setting():
    global setting 
    with open('setting.json','r') as f:
        setting= json.load(f)


# class FilterUUNS(BaseFilter):
#     def filter(self,message):
#         if 'uu' in message.text.lower() and 'ns' in message.text.lower():
#             return True
#         elif '26' in message.text.lower() and 'ns' in message.text.lower():
#             return True
#         else:
#             return False
# class Filterlinch(BaseFilter):
#     def filter(self,message):
#         if 'linch' in message.text.lower() :
#             return True
#         else:
#             return False

# class FilterCurrency(BaseFilter):
#     def filter(self,message):
#         text = message.text
#         if text.strip().startswith('/q'):
#             result= re.search('/q\s*(\d+[\d.]*)\s*([a-zA-z]{3})',text) # serach for currency string
#         else :
#             result= re.search('\$\s*(\d+[\d.]*)\s*([a-zA-z]{3})',text) # serach for currency string

#         if result is None:
#             return False
#         else:
#             if result.group(2).upper() in [i[0] for i in currencies]:
#                 return True
#             else:
#                 return False

def convertCurrencies(update,context):
    text = context.message.text

    if text.strip().startswith('/q'):
        result= re.search('/q\s*(\d+[\d.]*)\s*([a-zA-z]{3})',text) # serach for currency string
    else :
        result= re.search('\$\s*(\d+[\d.]*)\s*([a-zA-z]{3})',text) # serach for currency string
    currency = (result.group(2)).lower()
    url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/{currency}.json"
    print(url)
    json = requests.get(url).json()
    ori_price = float(result.group(1))
    converted_price = float(json[currency]['twd']) *ori_price 

    back = '${:.2f} {}= ${:.2f} TWD'.format(ori_price,result.group(2).upper(),converted_price)
    print(back)
    context.message.reply_text(back)


def commonCurrencies(update,context):
    text = context.message.text
    currencies = ['usd','jpy','cny','try']

    url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/twd.json"
    json = requests.get(url).json()
    back = ''
    for currency in currencies:
        price = 1/json['twd'][currency]
        back += f'$1{currency.upper()} = {price:.2f}TWD\n'
    context.message.reply_text(back)




def echo(upddte,context):
    context.message.reply_text('Hello World!!')

def thesis(update,context):
    tz = timezone(timedelta(hours=8))
    deadline= datetime(2022,1,31,0,0,0,tzinfo=tz)
    now = datetime.now(tz)
    remains = deadline - now
    back = """Deadline : `%s`\nNow : `%s`\n\-\-\-\n*REMAINS : `%s`*"""%(str(deadline),str(now),str(remains))
    context.message.reply_markdown_v2(back)


def eth_price(update,context):
    ticket = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=twd%2Cusd%2Ccny&include_24hr_change=true')
    json = ticket.json()
    price_list=json['ethereum']
    back = u'  ETH價格 : \n  ${twd}TWD\n= ${usd}USD\n= ${cny}RMB\n24hr_change_rate : {usd_24h_change:+.2f}%'.format(**price_list)
    print(back)
    context.message.reply_text(back)


def check_price(update,context,user):
    cryptos={
        'ethereum':'ETH',
        'bitcoin':'BTC',
        'smooth-love-potion':'SLP',
        'samoyedcoin':'SAMO',
        'msol':'MSOL',
        #'marinade':'MNDE',
        #'shoebill-coin':'SHBL',
        #'larix':'LARIX',
        'binancecoin':'BNB',
        'crypto-com-chain':'CRO',
        #'cryptomines-eternal':'ETL',
        'solana':'SOL',
        'raydium':'RAY',
        'iota':'MIOTA',
        # 'bonfida':'FIDA',
        'cardano':'ADA',
        #'babyswap' : 'BABY',
        'axie-infinity':'AXS',
        'tezos':"XTZ",

        
        # 'orca':'ORCA',
        # 'uniswap':'UNI',
             }
    url='https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd&include_24hr_change=true&ids='
    url += ','.join([i for i,_ in cryptos.items()])
    ticket = requests.get(url)
    json = ticket.json()
    back = ''
    result = []
    print(url)
    print(json)
    sol = json['solana']['usd']
    for name, data in json.items():
        print(name,data)
        result.append([cryptos[name],data['usd'],int(10**6*data['usd']/sol),data['usd_24h_change']])
    result.sort(reverse=True,key=lambda x: x[-1])
    for r in result:
        back += u'{} : ${}USD={:6d}e-6sol, {:+.2f}%\n'.format(*r)

    back += '='*10+'\n'
    msol = json['msol']['usd']
    eth= json['ethereum']['usd']
    msol_supply = setting[user]['msol_supply']
    weth_supply = setting[user]['weth_supply']
    borrow= setting[user]['usd_borrow']
    back += f"MSOL : {msol_supply}=${msol_supply*msol:.2f}, ETH : {weth_supply}=${eth*weth_supply:.2f}\nUSD : -{borrow}\n"
    borrow_limit= 0.7*msol_supply*msol+0.8*weth_supply*eth
    borrow_rate = borrow/borrow_limit
    back += f"borrow rate = {100*borrow_rate:3.2f}%, borrow_limit: {borrow_limit}\n"
    print(back)
    context.message.reply_text(back)

def Rist_price(update,context):
    check_price(update,context,'rist')

def Eathon_price(update,context):
    check_price(update,context,'eathon')
def OuO_price(update,context):
    url='https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd%2Ceth&include_24hr_change=true&ids='
    cryptos={
        'bitcoin':'BTC',
        'ethereum':'ETH',
        'solana':'SOL',
        'smooth-love-potion':'SLP',
        'axie-infinity':'AXS',
        'uniswap':'UNI',
        # 'step-finance':'STEP',
        # 'binancecoin':'BNB',
             }

    url += ','.join([i for i,_ in cryptos.items()])
    ticket = requests.get(url)
    json = ticket.json()
    back = ''
    result = []
    print(url)
    print(json)
    for name, data in json.items():
        print(name,data)
        result.append([cryptos[name],data['usd'],data['eth'],data['usd_24h_change']])
    result.sort(reverse=True,key=lambda x: x[-1])
    # print(result)
    for r in result:
        back += u'{} : ${}USD={:.6f}eth, {:+.2f}%\n'.format(*r)
    print(back)
    context.message.reply_text(back)

def crypto_exchange(update,context):
    coin = context.message.text.split(' ')[-1]
    coin = coin.lower()
    if coin not in crypto:
        context.message.reply_text('Not Found\nFull Raw List :https://api.coingecko.com/api/v3/coins/list')
        return
    print(crypto)
    coin = crypto[coin]
    print(coin)
    ticket = requests.get('https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies=twd%2Cusd%2Ccny&include_24hr_change=true'.format(coin))
    json = ticket.json()
    price_list=json[coin]
    print(price_list)
    back = '   {} Price : \n'.format(coin)+u'${twd}TWD\n= ${usd}USD\n= ${cny}RMB\n24hr_change_rate : {usd_24h_change:+.2f}%'.format(**price_list)
    print(back)
    context.message.reply_text(back)



def eth_defender(update,context):
    back = u'  ETH價格 : \n  $???TWD\n= $???USD\n= $???RMB\n此功能暫時暫停以免有人玻璃心碎'
    print(back)
    context.message.reply_text(back)

def eth_defender(update,context):
    back = u'  ETH價格 : \n  $???TWD\n= $???USD\n= $???RMB\n此功能暫時暫停以免有人玻璃心碎'
    print(back)
    context.message.reply_text(back)

def show_currencies(update,context):
    back = 'Usage: $xxx(USD|JPY.....)\n'
    for i in currencies:
        back += '{0[0]} : {0[1]} \n'.format(i)
    context.message.reply_text(back)

def UUNS(update,context):
    #firstdate = datetime.fromtimestamp(1580478240)#2020-01-31 21:44 UTC+8
    firstdate = datetime.fromtimestamp(1594787460)#2020-07-15 12:31 UTC+8
    uudays= datetime.now()-firstdate
    #sisdays = datetime.now() - datetime.fromtimestamp(1593090240) # 2020-05-25 21:04 UTC+8
    lindays = 165-uudays.days
    back = 'ㄏUU都買都%d天ㄌ\n你他媽只剩%d天可以存錢ㄌ'% (uudays.days,lindays)
    print(back)
    context.message.reply_text(back)


def linch(update,context):
    #firstdate = datetime.fromtimestamp(1580478240)#2020-01-31 21:44 UTC+8
    enddate = datetime.fromtimestamp(1649433600)#2022-04-09 00:00:00 UTC+8
    days= enddate - datetime.now()
    #sisdays = datetime.now() - datetime.fromtimestamp(1593090240) # 2020-05-25 21:04 UTC+8
    #back = 'ㄏUU都買都%d天ㄌ\n你他媽只剩%d天可以存錢ㄌ'% (uudays.days,lindays)
    back = f'linch {days.days} 天後敢不敢打電動'
    back = f'linch  哪時候才敢打電動?????'
    print(back)
    context.message.reply_text(back)

def setup_leverage(update,context):
    try : 
        text = context.message.text.split(' ')[-1]
        user,msol,weth,usd = text.split(',')
        user = user.lower()
        setting[user]['msol_supply'] = float(msol)
        setting[user]['weth_supply'] = float(weth)
        setting[user]['usd_borrow'] = float(usd)
        with open('setting.json','w') as fp:
            json.dump(setting,fp)
        context.message.reply_text(str(setting[user]))
    except Exception as e:
        print(e)
        msg  = '/leverage user,msol_supply_amount,eth_supply_amouny,usd_borrow'
        context.message.reply_text(msg)

def sticker(bot,update):
    zip_filename = "%s.zip" % update.message.sticker.set_name.encode('ascii', 'ignore')
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for sticker in bot.getStickerSet(update.message.sticker.set_name).stickers:

            # don't hate me for my freedom
            # emoji_int = int( "".join( re.findall( r'\d+', sticker.emoji.encode( 'ascii', 'xmlcharrefreplace'))))

            file_name = "_%s.webp" % ( sticker.file_id)
            new_file = bot.getFile(sticker.file_id)
            new_file.download(file_name)
            zipf.write(file_name)
            os.remove(file_name)

    update.message.reply_text("Sticker set %s saved." % zip_filename)
    with open(zip_filename, 'rb') as f:
      update.message.reply_document(f)
    os.remove(zip_filename)


async def main():
    load_dotenv()
#     logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     bot_name = os.environ['BOT_NAME']
#     updater = Updater(token=os.environ['TOKEN'])

#     load_currencies()
#     load_crypto()
#     load_setting()

#     #Add Commands
#     dp = updater.dispatcher
# #    dp.add_handler(CommandHandler("price",eth_defender))#Fake eth price
#     dp.add_handler(CommandHandler("price",eth_price))
# #    dp.add_handler(CommandHandler("QAQ",thesis))
#     dp.add_handler(CommandHandler("OuO",OuO_price))
#     dp.add_handler(CommandHandler("Rist",Rist_price))
#     dp.add_handler(CommandHandler("Eathon",Eathon_price))
#     dp.add_handler(CommandHandler("leverage",setup_leverage))
#     dp.add_handler(CommandHandler("crypto",crypto_exchange))
#     dp.add_handler(CommandHandler("cur",commonCurrencies))
#     dp.add_handler(CommandHandler("ftx",lambda update,context : context.message.reply_text('6rLrWAL2g8G6jDvDmp2wZcs36My5VUD5PGUKVn5xHuC3')))
# #    dp.add_handler(MessageHandler(Filters.sticker,sticker))
# #    filter_uuns = FilterUUNS()
# #    dp.add_handler(MessageHandler(Filters.text & filter_uuns,UUNS))
#     filter_linch= Filterlinch()
#     dp.add_handler(MessageHandler(Filters.text & filter_linch,linch)) 

#     dp.add_handler(CommandHandler("show_currencies",show_currencies))
#     filter_currencies = FilterCurrency()
#     dp.add_handler(MessageHandler(Filters.text & filter_currencies,convertCurrencies))

    
#     #Start Webhook
#     url_path = ''.join(os.environ['URL'].strip('https://').split('/')[1:])
#     updater.start_webhook(listen=os.environ('IP'),port=int(os.environ['PORT']),url_path=url_path)
#     updater.bot.set_webhook(url=os.environ['URL'], 
#                          certificate=open(os.environ['CERT_FILE_PATH'],'rb'))

    env = os.environ
    app = Application.builder().token(env['TOKEN']).build()
    await app.bot.set_webhook(url=env['URL'], allowed_updates=Update.ALL_TYPES)
    # Set up webserver
    async def handler(request: Request) -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        # logging.debug(await request.json())
        print("<< ", await request.json())
        await app.update_queue.put(
            Update.de_json(data=await request.json(), bot=app.bot)
        )
        return Response()

    async def custom_updates(request: Request) -> PlainTextResponse:
        """
        Handle incoming webhook updates by also putting them into the `update_queue` if
        the required parameters were passed correctly.
        """
        try:
            user_id = int(request.query_params["user_id"])
            payload = request.query_params["payload"]
        except KeyError:
            return PlainTextResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content="Please pass both `user_id` and `payload` as query parameters.",
            )
        except ValueError:
            return PlainTextResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content="The `user_id` must be a string!",
            )

        await app.update_queue.put(WebhookUpdate(user_id=user_id, payload=payload))
        return PlainTextResponse("Thank you for the submission! It's being forwarded.")

    async def health(_: Request) -> PlainTextResponse:
        """For the health endpoint, reply with a simple plain text message."""
        return PlainTextResponse(content="The bot is still running fine :)")

    route = '/'+''.join(os.environ['URL'].strip('https://').split('/')[1:])
    starlette_app = Starlette(
        routes=[
            Route(route, handler, methods=["POST"]),
            Route("/healthcheck", health, methods=["GET"]),
            Route("/submitpayload", custom_updates, methods=["POST", "GET"]),
        ]
    )
    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=starlette_app,
            port=int(env['PORT']),
            use_colors=False,
            host=env['IP'],
        )
    )

    # Run application and webserver together
    async with app:
        await app.start()
        await webserver.serve()
        await app.stop()

    # updater = Application(bot=bot)
    # updater.run_webhook(listen=env['IP'], port=int(env['PORT']),secret_token=env['TOKEN'],key=env['CERT_KEY'], cert = env['CERT_PEM'],webhook_url=env['URL'])

if __name__ == "__main__":
    # logging.basicConfig(filename='tianai.log',encoding='utf-8',level=logging.DEBUG)
    asyncio.run(main())
