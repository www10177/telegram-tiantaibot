# -*- coding: UTF-8 -*-
import zipfile
import asyncio
from telegram import Bot, Update
from telegram.ext import Application,CommandHandler
from http import HTTPStatus
from typing import Optional

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

def init() : 
    global bnb_symbol
    bnb_symbol.update(get_all_binance_symbol())

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
    wishlist = ['BTC','ETH','SOL','NEAR','BNB']
    baseSymbol = "USDT"
    result = await bnb_spot_quote(wishlist,baseSymbol)
    replied = ""
    for symbol, (price,percent) in result.items():
        percent_mark= '🟢' if percent> 0 else "🔴"
        replied += f"{percent_mark}{symbol.replace(baseSymbol,'')}: *`{price:.1f}`*U, *`{percent:+.1f}`*%\n" 
    logger.debug(replied)
    await update.message.reply_markdown_v2(replied)
    
async def WIF(update:Update,context)->None:
    r= await asyncio.to_thread(requests.get, f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol=WIFUSDT")
    binance= r.json()
    b_price, last_rate, next_rate = float(binance["markPrice"]), float(binance['lastFundingRate']), float(binance['nextFundingTime'])
    
    r= await asyncio.to_thread(requests.get, f"https://price.jup.ag/v4/price?ids=EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm&vsToken=USDT")
    j_price= r.json()['data']['EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm']['price']
    rate_diff = next_rate - last_rate
    price_diff = (j_price - b_price ) / b_price
    diff_mark= '🟢' if price_diff> 0 else "🔴"
    holdings = 806
    replied = (f"Binance : {b_price:.4f}\n"
               f"Jupiter :  {j_price:.4f}\n"
               f"{diff_mark}PriceDiff: {100*price_diff:+.2f}%, Funding:{100*last_rate:.4f}%\n"
               f"⚡${holdings*b_price*last_rate:.3f}⚡"
            #    f"{last_rate:.2f}  "#🔜{next_rate:.2f} ,{rate_mark}{rate_diff:+.2f}  "
    )
    await update.message.reply_text(replied)
    
    
    


def show_currencies(update,context):
    back = 'Usage: $xxx(USD|JPY.....)\n'
    for i in currencies:
        back += '{0[0]} : {0[1]} \n'.format(i)

async def main():
    load_dotenv()

    env = os.environ
    # logger.debug(env)
    app = Application.builder().token(env['TOKEN']).build()
    app.add_handler(CommandHandler("price",get_crypto_wishlist))
    app.add_handler(CommandHandler("WIF",WIF))
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

    route = '/'+''.join(os.environ['URL'].strip('https://').split('/')[1:])
    starlette_app = Starlette( routes=[
            Route(route, handler, methods=["POST"]),
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
