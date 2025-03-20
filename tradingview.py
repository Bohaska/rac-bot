import aiohttp
import asyncio
import json
import datetime
from enum import Enum
from math import sqrt
import logging

class MarketStatus(Enum):
    # OPEN includes pre-market and post-market
    TRADING = 1
    CLOSED = 2


def format_ws_request(data):
    return f"~m~{len(data)}~m~{data}"


async def get_stock_info(ticker):
    endpoint = f"wss://data.tradingview.com/socket.io/websocket"
    session = aiohttp.ClientSession()
    random_session_id = "qs_PqKEQDeY5hPs"
    async with session.ws_connect(endpoint, origin='https://www.tradingview.com') as ws:
        await ws.receive()
        logging.debug(f"connected to {endpoint}")
        await ws.send_str(format_ws_request('{"m":"set_data_quality","p":["low"]}'))
        await ws.send_str(format_ws_request('{"m":"set_auth_token","p":["unauthorized_user_token"]}'))
        await ws.send_str(format_ws_request('{"m":"set_locale","p":["en","US"]}'))
        await ws.send_str(format_ws_request(f'{{"m":"quote_create_session","p":["{random_session_id}"]}}'))
        # await ws.send_str(format_ws_request(f'{{"m":"quote_set_fields","p":["{random_session_id}","base-currency-logoid","ch","chp","currency-logoid","currency_code","currency_id","base_currency_id","current_session","description","exchange","format","fractional","is_tradable","language","local_description","listed_exchange","logoid","lp","lp_time","minmov","minmove2","original_name","pricescale","pro_name","short_name","type","typespecs","update_mode","volume","variable_tick_size","value_unit_id","ask","bid","fundamentals","high_price","is_tradable","low_price","open_price","prev_close_price","rch","rchp","rtc","rtc_time","status","basic_eps_net_income","beta_1_year","earnings_per_share_basic_ttm","industry","market_cap_basic","price_earnings_ttm","sector","volume","dividends_yield","timezone"]}}'))
        await ws.send_str(format_ws_request(f'{{"m":"quote_add_symbols","p":["{random_session_id}","{ticker}"]}}'))
        await ws.send_str(format_ws_request(f'{{"m":"quote_fast_symbols","p":["{random_session_id}","{ticker}"]}}'))
        logging.debug("sent messages")
        ws_stock_info = await ws.receive()
        logging.debug(ws_stock_info.data)
        await ws.close()
        logging.debug("closed websocket")
        index = 4
        new_stock_info = None
        while new_stock_info is None:
            try:
                stock_info = json.loads(ws_stock_info.data.split("~")[index])["p"][1]
                new_stock_info = {
                    "short_name": stock_info["v"]["short_name"],
                    "name": stock_info["n"],
                    "last_price": stock_info["v"]["lp"],
                    "current_session": MarketStatus.TRADING if stock_info["v"]["current_session"] in ["market", "pre_market", "post_market"] else MarketStatus.CLOSED,
                }
            except KeyError:
                index += 4
        new_stock_info["close_price"] = new_stock_info["last_price"] if new_stock_info["current_session"] == MarketStatus.CLOSED else stock_info["v"]["prev_close_price"]
        new_stock_info["change"] = 0 if new_stock_info["current_session"] == MarketStatus.CLOSED else new_stock_info["last_price"] - new_stock_info["close_price"]
        new_stock_info["change_percent"] = 0 if new_stock_info["current_session"] == MarketStatus.CLOSED else (new_stock_info["last_price"] - new_stock_info["close_price"])/new_stock_info["last_price"] * 100
        return new_stock_info


async def get_technical_rating(ticker, time=None, adjust=None):
    headers = {
        'authority': 'scanner.tradingview.com',
        'accept': 'application/json',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-Hans;q=0.7,zh;q=0.6',
        'cache-control': 'no-cache',
        # 'cookie': 'cookiePrivacyPreferenceBannerProduction=notApplicable; cookiesSettings={"analytics":true,"advertising":true}; device_t=TGdRUEJBOjA.DsY7yfR2BGUIu_pO-s2MDpMczSLpYWQXBZVedEgbwks; sessionid=m4vktjbp6w9tw0noiyy56cu5djsz3b3k; sessionid_sign=v1:7+2774aIu7zFlHqM7hPs01NHuPzTxJGiz40C0U4ofts=; tv_ecuid=61f7b49d-5ff0-460e-a9c6-f4f08384b31e; cachec=61f7b49d-5ff0-460e-a9c6-f4f08384b31e; etg=61f7b49d-5ff0-460e-a9c6-f4f08384b31e; _ga=GA1.1.1541556038.1701929137; _ga_YVVRYGL0E0=GS1.1.1702701849.26.1.1702702103.60.0.0; _sp_id.cf1a=2f870214-eb23-490e-821b-b3632a37c876.1701906159.44.1704694255.1704532038.1ccd4fce-568b-4d9f-8495-4e675b3cb00e',
        'origin': 'https://www.tradingview.com',
        'pragma': 'no-cache',
        'referer': 'https://www.tradingview.com/',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    params = {
        "symbol": ticker,
        "no_404": "true",
    }
    if time is not None:
        params["fields"] = "Recommend.All" + time
    else:
        params["fields"] = "Recommend.All"
    tries = 0
    async with aiohttp.ClientSession() as session:
        logging.debug(f"Getting URL https://scanner.tradingview.com/symbol...")
        while tries < 5:
            try:
                rating = await session.get("https://scanner.tradingview.com/symbol", params=params, headers=headers, timeout=20)
                rating = await rating.json()
                logging.debug(rating)
                rating = list(rating.values())[0]
                adjust = False if adjust is None else adjust

                if adjust:
                    if rating < 0:
                        return sqrt(rating * -1) * -1
                    else:
                        return sqrt(rating)
                else:
                    return rating
            except:
                tries += 1
                if tries >= 5:
                    raise asyncio.exceptions.TimeoutError(f"Failed to fetch info after {tries} tries")