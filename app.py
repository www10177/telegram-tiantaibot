# -*- coding: UTF-8 -*-
import time
import zipfile
import asyncio
from telegram import Bot, Update, ReplyKeyboardMarkup,ReplyKeyboardRemove
from telegram.constants import ChatType
from telegram.ext import Application,CommandHandler
from http import HTTPStatus
from typing import Optional
from binance.um_futures import UMFutures
from binance.spot import Spot
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

import requests
import logging
import sys
import os
from datetime import datetime,date,timezone,timedelta
import re
import json
from dotenv import load_dotenv
import urllib

currencies = []
crypto={}
bnb_symbol = set()
bnb_um_client_www = None 
bnb_spot_client_www = None 
bnb_um_client_eason = None 
bnb_spot_client_eason = None 
logger = logging.getLogger(__name__)

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
 
#Deprecated       
# async def WIF(update:Update,context)->None:
#     r= await asyncio.to_thread(requests.get, f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol=WIFUSDT")
#     binance= r.json()
#     b_price, last_rate, next_rate = float(binance["markPrice"]), float(binance['lastFundingRate']), float(binance['nextFundingTime'])
    
#     r= await asyncio.to_thread(requests.get, f"https://price.jup.ag/v4/price?ids=EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm&vsToken=USDT")
#     j_price= r.json()['data']['EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm']['price']
#     rate_diff = next_rate - last_rate
#     price_diff = (j_price - b_price ) / b_price
#     diff_mark= '🟢' if price_diff> 0 else "🔴"
#     holdings = 806
#     replied = (f"Binance : {b_price:.4f}\n"
#                f"Jupiter :  {j_price:.4f}\n"
#                f"{diff_mark}PriceDiff: {100*price_diff:+.2f}%, Funding:{100*last_rate:.4f}%\n"
#                f"⚡${holdings*b_price*last_rate:.3f}⚡"
#             #    f"{last_rate:.2f}  "#🔜{next_rate:.2f} ,{rate_mark}{rate_diff:+.2f}  "
#     )
#     await update.message.reply_text(replied)

async def check_binance_USDM_position(update:Update, context):
    replied = ""
    username = update.message.from_user.username  
    if username == 'www10177'  or username == 'eathon1214':
        if update.message.from_user.username == 'www10177':
            bnb_um_client = bnb_um_client_www
        else :
            bnb_um_client = bnb_um_client_eason
            
        holdings = [pos for pos in bnb_um_client.get_position_risk() if float(pos['positionAmt']) != 0.0]
        startTime= 1000*(int(time.time()) - 3600*24)#yesterday in milli epoch time
        income = bnb_um_client.get_income_history(startTime=startTime,limit=300,incomeType='FUNDING_FEE')
        for pos in holdings:
            symbol = pos['symbol']
            value = float(pos['unRealizedProfit'])
            r= await asyncio.to_thread(requests.get, f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}")
            fundRate = float(r.json()['lastFundingRate'])
            value_mark= '🟢' if value> 0 else "🔴"
            to_str = lambda x : f"{float(x):.3f}"
            replied  += f"{value_mark}[{pos['symbol']}@{to_str(pos['positionAmt'])}]: ${value:.3f}\n"
            replied += f"{value_mark}Now:{to_str(pos['markPrice'])}, Liq:{to_str(pos['liquidationPrice'])}\n"
            rate_mark= '🟢' if fundRate> 0 else "🔴"
            replied  += f"{rate_mark}Fund:{100*fundRate:.4f}% "+f"⚡${abs(float(pos['positionAmt']))*float(pos['markPrice'])*fundRate:.3f}⚡\n"
            price_sum = 0
            for row in income :
                if row['symbol'] == symbol :
                    replied += time.strftime("%H:%M", time.localtime(row['time']/1000)) # ms to second
                    replied += f"[{row['incomeType'][:4]}]: {row['income']} {row['asset']}\n"
                    price_sum += float(row['income'])
            replied += f'Summation : {price_sum:.2f}\n'
            
            replied += '-----\n' 
    else :
        replied += "Private Command.\nPlease Contact @www10177 for more info. "
    logger.debug(replied)
    await update.message.reply_text(replied)
    
async def margin(update:Update, context):
    replied = ""
    username = update.message.from_user.username  
    print(username)
    print(username == 'www10177')
    if username == 'www10177'  or username == 'eathon1214':
        if update.message.from_user.username == 'www10177':
            bnb_spot_client = bnb_spot_client_www
        else :
            bnb_spot_client = bnb_spot_client_eason
        data = bnb_spot_client.margin_account()
        replied = f"Level:{float(data['marginLevel']):.2f}\n"
        assets = [item['asset'] for item in data['userAssets'] if item['borrowed'] != '0' ]
        rates = bnb_spot_client.get_a_future_hourly_interest_rate(assets=','.join(assets),isIsolated=False)
        rates ={item['asset'] : float(item['nextHourlyInterestRate']) for item in rates}
        for item in data['userAssets']:
            if item['borrowed'] != '0' :
                replied += f"{item['asset']} : {item['borrowed']}/ 4hour rate: {100*4*rates[item['asset']]:.4f}% \n" 
        print(replied)
    else :
        replied += "Private Command.\nPlease Contact @www10177 for more info. "
    logger.debug(replied)
    await update.message.reply_text(replied)

def init() : 
    load_dotenv()
    global bnb_symbol,bnb_um_client_www,bnb_spot_client_www
    global bnb_um_client_eason,bnb_spot_client_eason
    bnb_symbol.update(get_all_binance_symbol())
    bnb_um_client_www = UMFutures(key = os.environ['BNB_KEY_WWW'], secret=os.environ['BNB_SECRET_WWW'])
    bnb_spot_client_www = Spot( api_key = os.environ['BNB_KEY_WWW'], api_secret=os.environ['BNB_SECRET_WWW'])
    bnb_um_client_eason = UMFutures(key = os.environ['BNB_KEY_EASON'], secret=os.environ['BNB_SECRET_EASON'])
    bnb_spot_client_eason = Spot( api_key = os.environ['BNB_KEY_EASON'], api_secret=os.environ['BNB_SECRET_EASON'])

def get_all_binance_symbol()->list[str]:
    result=  requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
    return [symbol['symbol'] for symbol in result['symbols']]
        

async def bnb_spot_quote(queries:list[str],base:str) -> dict[str, tuple[float]]:
    global bnb_symbol
    pairs = [q+base if q+base in bnb_symbol else None for q in queries ]
    query_string = ",".join(['"'+ pair + '"' for pair in pairs if pair is not None])
    query_string = urllib.parse.quote(query_string)
    logger.debug(f"https://api.binance.com/api/v3/ticker/24hr?symbols=[{query_string}]")
    r= await asyncio.to_thread(requests.get, f"https://api.binance.com/api/v3/ticker/24hr?symbols=[{query_string}]")
    r = r.json()
    logger.debug(r)
    get = lambda item: (float(item['lastPrice']), float(item['priceChangePercent']))
    return {item['symbol']: get(item) for item in r}

async def get_crypto_wishlist(update:Update,context)->None:
    # Hard encoded wishlist now
    logger.debug("ENTERED get_crypto_wishlist")
    wishlist = ['BTC','ETH','SOL','NEAR','BNB','WIF','W']
    baseSymbol = "USDT"
    result = await bnb_spot_quote(wishlist,baseSymbol)
    replied = ""
    for symbol, (price,percent) in result.items():
        percent_mark= '🟢' if percent> 0 else "🔴"
        replied += f"{percent_mark}{symbol.replace(baseSymbol,'')}: *`{price:.1f}`*U, *`{percent:+.1f}`*%\n" 
    logger.debug(replied)
    await update.message.reply_markdown_v2(replied)

#Deprecated    
# async def call_online(update:Update,context)->None:
#     logger.debug("+"*20)
#     if update.effective_chat.type != ChatType.SUPERGROUP :
#         update.message.reply_text("Please add bot into group and elevate it as admin.")
#     else :
#         print(update.chat_member)
        
#     logger.debug("+"*20)
#     pass
async def start(update: Update, context ) -> int:
    reply_keyboard = [["/Price"], ["/Position"], ['/Margin']]

    await update.message.reply_text(
        "Hi, this is a personal bot built by @www10177", 
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=False, input_field_placeholder="Select Command..", is_persistent=True
        ),
    )
    return 0
    
    
    



async def main():

    env = os.environ
    # logger.debug(env)
    app = Application.builder().token(env['TOKEN']).build()
    app.add_handler(CommandHandler("price",get_crypto_wishlist))
    # app.add_handler(CommandHandler("WIF",WIF))
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("margin",margin))
    # app.add_handler(CommandHandler("up",call_online))
    app.add_handler(CommandHandler("position",check_binance_USDM_position))
    #app.add_handler(CommandHandler("crypto",crypto_exchange))
    # app.add_handler(CommandHandler("OuO",OuO_price))
    # app.add_handler(CommandHandler("cur",commonCurrencies))
    

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

    route = '/'
    starlette_app = Starlette( routes=[
            Route(f"{route}", handler, methods=["POST"]),
            Route(f"{route}/", handler, methods=["POST"]),
            Route(f"{route}/healthcheck", health, methods=["GET"]),
            Route(f"{route}/submitpayload", custom_updates, methods=["POST", "GET"]),
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

def setup_logger():
    # this is just to make the output look nice
    # formatter = logging.Formatter(fmt="%(asctime)s %(name)s.%(levelname)s: %(message)s", datefmt="%Y.%m.%d %H:%M:%S")
    formatter = logging.Formatter(fmt="[%(name)s_%(levelname)s]: %(message)s", datefmt="%Y.%m.%d %H:%M:%S")

    # this logs to stdout and I think it is flushed immediately
    syshandler = logging.StreamHandler(stream=sys.stdout)
    syshandler.setFormatter(formatter)
    logger.addHandler(syshandler)

    logger.setLevel(logging.DEBUG)
    logger.debug('logger init')


if __name__ == "__main__":
    # logging.basicConfig(filename='tianai.log',encoding='utf-8',level=logging.DEBUG)
    init()
    load_currencies()
    load_crypto()
    load_setting()
    setup_logger()
    asyncio.run(main())
