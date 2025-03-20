import asyncio
import random
import aiohttp
import logging
import os
import time
from constants import API_ENDPOINT, banned_markets, BOT_USERS, SMART_USERS  # , IGNORED_MARKET_GROUPS
import json
import tradingview


async def get_markets(limit: int):
    session = aiohttp.ClientSession()
    if limit <= 20:
        tries = 0
        async with session:
            logging.debug(f"Getting URL {API_ENDPOINT}markets...")
            while tries < 5:
                try:
                    markets = await session.get(API_ENDPOINT + "markets", params={"limit": limit}, timeout=10)
                    markets = await markets.json()
                    logging.debug(f"Done")
                    return markets
                except asyncio.exceptions.TimeoutError:
                    tries += 1
        raise asyncio.exceptions.TimeoutError(f"Failed to fetch info after {tries} tries")
    elif limit > 20:
        async with session:
            logging.debug(f"Getting URL {API_ENDPOINT}markets...")
            markets = await session.get(API_ENDPOINT + "markets", params={"limit": 20}, timeout=10)
            markets = await markets.json()
            all_markets = markets
            limit -= 20
            last_market = markets[-1]
            while limit > 0:
                markets = await session.get(API_ENDPOINT + "markets", params={"limit": 20, "before": last_market["id"]},
                                            timeout=10)
                markets = await markets.json()
                last_market = markets[-1]
                all_markets += markets
                limit -= 20
        logging.debug(f"Done")
        return all_markets


async def search_markets(query, topic=None, creator=None, contract_type=None, sort=None):
    session = aiohttp.ClientSession()
    tries = 0
    params = {"term": query}
    if topic is not None:
        params["topicSlug"] = topic
    if creator is not None:
        params["creatorId"] = creator
    if contract_type is not None:
        params["contractType"] = contract_type
    if sort is not None:
        params["sort"] = sort
    async with session:
        logging.debug(f"Getting URL {API_ENDPOINT}search-markets...")
        while tries < 5:
            try:
                markets = await session.get(API_ENDPOINT + "search-markets", params=params, timeout=10)
                markets = await markets.json()
                logging.debug(f"Done")
                return markets
            except asyncio.exceptions.TimeoutError:
                tries += 1
    raise asyncio.exceptions.TimeoutError(f"Failed to fetch info after {tries} tries")


async def search_stock_markets(query, option_name):
    market = await search_markets(query, creator="OEbsAczmbBc4Sl1bacYZNPJLLLc2", contract_type="MULTIPLE_CHOICE",
                                  sort="close-date")
    logging.info(market)
    market = market[0]
    market = await get_market(market['id'])
    for answer in market['answers']:
        if answer['text'] == option_name:
            answer['closeTime'] = market['closeTime']
            return answer


async def get_market(market_id: str):
    session = aiohttp.ClientSession()
    tries = 0
    async with session:
        logging.debug(f"Getting URL {API_ENDPOINT}market/{market_id}...")
        while tries < 5:
            try:
                market = await session.get(API_ENDPOINT + "market/" + market_id, timeout=10)
                market = await market.json()
                logging.debug(f"Done")
                return market
            except asyncio.exceptions.TimeoutError:
                tries += 1
    raise asyncio.exceptions.TimeoutError(f"Failed to fetch info after {tries} tries")


async def get_market_by_url(market_url: str):
    session = aiohttp.ClientSession()
    tries = 0
    slug = market_url.split("/")[-1].split("?")[0]
    async with session:
        logging.debug(f"Getting URL {API_ENDPOINT}slug/{slug}...")
        while tries < 5:
            try:
                market = await session.get(API_ENDPOINT + "slug/" + slug, timeout=10)
                market = await market.json()
                logging.debug(f"Done")
                return market
            except asyncio.exceptions.TimeoutError:
                tries += 1
    raise asyncio.exceptions.TimeoutError(f"Failed to fetch info after {tries} tries")


async def get_market_positions(market_id: str):
    session = aiohttp.ClientSession()
    tries = 0
    async with session:
        logging.debug(f"Getting URL {API_ENDPOINT}market/{market_id}/positions...")
        while tries < 5:
            try:
                positions = await session.get(API_ENDPOINT + "market/" + market_id + "/positions", timeout=10)
                positions = await positions.json()
                logging.debug(f"Done")
                return positions
            except asyncio.exceptions.TimeoutError:
                tries += 1
    raise asyncio.exceptions.TimeoutError(f"Failed to fetch info after {tries} tries")


async def bet_market(api_key, market_id, outcome, amount, limit_prob=None, expires_at=None, answer_id=None):
    # outcome can be "YES" or "NO"
    json_data = {
        "amount": amount,
        "contractId": market_id,
        "outcome": outcome
    }
    if limit_prob is not None:
        json_data["limitProb"] = limit_prob
        if expires_at is not None:
            json_data["expiresAt"] = expires_at
        else:
            json_data["expiresAt"] = 1
    if answer_id is not None:
        json_data['answerId'] = answer_id
    session = aiohttp.ClientSession()
    async with session:
        logging.debug(f"Making bet amount {amount} on outcome {outcome} in market {market_id}...")
        bet = await session.post(
            API_ENDPOINT + "bet",
            json=json_data,
            headers={"Authorization": f"Key {api_key}"}
        )
        logging.debug(f"Done")
    bet = await bet.json()
    return bet


async def close_market(api_key, market_id, close_time=None):
    if close_time is None:
        json_data = None
    else:
        json_data = {"closeTime": close_time}
    session = aiohttp.ClientSession()
    async with session:
        logging.debug(f"Closing {market_id}...")
        bet = await session.post(
            API_ENDPOINT + "market/" + market_id + "/close",
            json=json_data,
            headers={"Authorization": f"Key {api_key}"}
        )
        logging.debug(f"Done")
    return


def market_agreement(positions, outcome: str):
    logging.info(f"Checking for agreement among all traders...")
    consensus = {"YES": "hasNoShares", "NO": "hasYesShares"}
    for position in positions:
        if position[consensus[outcome]] is True and not position["userUsername"] in BOT_USERS:
            return False
        if position["userUsername"] == "ArkPoint":
            return False
    else:
        return True


async def bet_market_agreement(market, api_key, bet_per_market, min_traders, max_traders):
    min_liquidity = 50 + min_traders * 20
    max_liquidity = 50 + max_traders * 20
    if min_liquidity <= market["totalLiquidity"] <= max_liquidity:
        positions = await get_market_positions(market["id"])
        if market["probability"] < 0.47:
            agreement = market_agreement(positions, "NO")
            if agreement is False:
                logging.info(f"Skipping market {market['url']}, not unanimous agreement.")
                return 0
            elif agreement is True:
                await bet_market(api_key, market["id"], "NO", bet_per_market)
                logging.info(f"Bet M{bet_per_market} on NO in market {market['url']}")
                return bet_per_market
        elif market["probability"] > 0.53:
            agreement = market_agreement(positions, "YES")
            if agreement is False:
                logging.info(f"Skipping market {market['url']}, not unanimous agreement.")
                return 0
            elif agreement is True:
                await bet_market(api_key, market["id"], "YES", bet_per_market)
                logging.info(f"Bet M{bet_per_market} on YES in market {market['url']}")
                return bet_per_market
        else:
            logging.info(f"Skipping market {market['url']}, probability is between 47% and 53%")
            return 0
    else:
        logging.info(f"Skipping market {market['url']}, liquidity is at {market['totalLiquidity']}")
        return 0


async def market_criteria(market, time_horizon):
    if not market["creatorUsername"] in banned_markets and market["isResolved"] is False \
            and market["closeTime"] / 1000 < time.time() + time_horizon and not 0.47 < market["probability"] < 0.53:
        """groups = await get_market(market["id"])
        groups = groups["groupSlugs"]
        for group in groups:
            if group in IGNORED_MARKET_GROUPS:
                logging.info(f"Skipping market {market['url']}, in group {group}.")
                return False"""
        logging.info(f"Market {market['url']} passed criteria.")
        return True
    else:
        if market["creatorUsername"] in banned_markets:
            logging.info(f"Skipping market {market['url']}, user {market['creatorUsername']} created it.")
        elif market["isResolved"] is True:
            logging.info(f"Skipping market {market['url']}, already resolved.")
        elif market["closeTime"] >= time.time() + time_horizon:
            logging.info(f"Skipping market {market['url']}, resolution date too far away")
        elif 0.47 < market["probability"] < 0.53:
            logging.info(f"Skipping market {market['url']}, probability is between 47% and 53%")
        return False


async def agreement_bot(api_key: str, bet_per_market: int, budget: int, search_limit: int, time_horizon: int,
                        min_traders: int, max_traders: int):
    logging.info(f"Searching for {search_limit} markets...")
    markets = await get_markets(search_limit)
    spent_money = 0
    for market in markets:
        logging.info(f"Analyzing market {market['url']}...")
        if spent_money < budget:
            try:
                if market["outcomeType"] == "BINARY":
                    market_bet = await market_criteria(market, time_horizon)
                    if market_bet is True:
                        bet = await bet_market_agreement(market, api_key, bet_per_market, min_traders, max_traders)
                        if bet is not None:
                            spent_money += bet
                else:
                    logging.info(f"Skipping market {market['url']}, not a binary market")
            except asyncio.exceptions.TimeoutError:
                logging.info(f"Skipping market {market['url']}, timed out on a request")
        else:
            logging.info(f"Spent M{spent_money}, entire budget of M{budget}")
            return
    logging.info(f"Spent M{spent_money} out of M{budget} budget")
    return


async def momentum_bot(api_key: str, bet_per_market: int, budget: int, search_limit: int, time_horizon: int,
                       wait_interval: int, min_traders: int, max_traders: int, start_wait_time: int):
    logging.info(f"Waiting {start_wait_time:,} seconds before starting...")
    await asyncio.sleep(start_wait_time)
    while True:
        logging.info("Starting momentum bot...")
        await agreement_bot(api_key, bet_per_market, budget, search_limit, time_horizon, min_traders, max_traders)
        logging.info("Bets made.")
        multiplier = random.randint(90, 110) / 100
        logging.info(f"Sleeping for {wait_interval * multiplier} seconds...")
        await asyncio.sleep(wait_interval * multiplier)


async def close_random_time(api_key: str, lower_bound: int, higher_bound: int, market_url: str):
    random_time = random.randint(lower_bound, higher_bound)
    now_time = time.time()
    market = await get_market_by_url(market_url)
    print(f"Market slug: {market['id']}")
    logging.info(f"Selected random time {random_time} for market {market_url}."
                 f"\nSleeping {random_time - now_time} seconds...")
    if random_time > now_time:
        await asyncio.sleep(random_time - now_time)
    await close_market(api_key, market["id"])
    return


async def get_live_bets(supbase_api_key, bot_api_key):
    endpoint = f"wss://pxidrgkatumlvfqaxcll.supabase.co/realtime/v1/websocket?apikey={supbase_api_key}&vsn=1.0.0"
    payload_1 = {"topic": "realtime:contract_bets", "event": "phx_join", "payload": {
        "config": {"broadcast": {"ack": False, "self": False}, "presence": {"key": ""},
                   "postgres_changes": [{"event": "*", "schema": "public", "table": "contract_bets"}]}}, "ref": "1",
                 "join_ref": "1"}
    payload_2 = {"topic": "realtime:contract_bets", "event": "access_token", "payload": {
        "access_token": supbase_api_key},
                 "ref": "6", "join_ref": "1"}
    session = aiohttp.ClientSession()
    async with session.ws_connect(endpoint) as ws:
        await ws.send_json(payload_1)
        await ws.send_json(payload_2)
        async for msg in ws:
            bet = json.loads(msg.data)
            if bet["event"] == "postgres_changes":
                if bet["payload"]["data"]["record"]["amount"] >= 20 and bet["payload"]["data"]["record"][
                    "user_id"] in SMART_USERS:
                    if random.randint(0, 1):
                        await bet_market(bot_api_key, bet["payload"]["data"]["record"]["contract_id"],
                                         bet["payload"]["data"]["record"]["outcome"], random.randint(5, 10))


async def bet_stock_movement(market_name, answer_name, ticker, bot_api_key, confidence=None, bet_amount=None, sensitivity=None):
    confidence = 30 if confidence is None else confidence
    bet_amount = 100 if bet_amount is None else bet_amount
    sensitivity = 1 if sensitivity is None else sensitivity
    market = await search_stock_markets(market_name, answer_name)
    logging.info(market)
    rating = await tradingview.get_technical_rating(ticker, adjust=True)
    stock_info = await tradingview.get_stock_info(ticker)
    logging.info(f"Change percent: {stock_info['change_percent']}\nRating: {rating}")
    bet_prob = max(min(
        round(50 + stock_info['change_percent'] * 50 / sensitivity + rating * confidence), 80), 20) / 100
    if abs(bet_prob - market['probability']) > 0.03 and (market['closeTime'] / 1000) - time.time() < 60 * 60 * 22:
        if bet_prob > market['probability']:
            if stock_info['change_percent'] > -2 and market['probability'] > 0.25:
                logging.info('Betting YES on market...')
                bet = await bet_market(bot_api_key, market['contractId'], "YES", bet_amount, bet_prob,
                                       expires_at=int(time.time()) * 1000 + 60000, answer_id=market['id'])
                logging.info('Bet YES on market')
                logging.debug(str(bet))
        else:
            if stock_info['change_percent'] < 2 and market['probability'] < 0.75:
                logging.info('Betting NO on market...')
                bet = await bet_market(bot_api_key, market['contractId'], "NO", bet_amount, bet_prob,
                                       expires_at=int(time.time()) * 1000 + 60000, answer_id=market['id'])
                logging.info('Bet NO on market')
                logging.debug(str(bet))


def bet_stock_markets():
    api_key = os.getenv('API_KEY')
    bet_amount = int(os.getenv('BET_PER_MARKET'))
    while True:
        tasks = []
        tasks.append(
            bet_stock_movement("US Stocks: How Will Each Of These US Indices Close On", "Russell 2000 : Higher^",
                               "TVC:RUT", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("US Stocks: How Will Each Of These US Indices Close On", "S&P 500 : Higher^",
                               "SP:SPX", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("US Stocks: How Will Each Of These US Indices Close On", "Dow Jones : Higher^",
                               "TVC:DJI", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("US Stocks: How Will Each Of These US Indices Close On", "Nasdaq : Higher^",
                               "NASDAQ:IXIC", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("US Stocks: How Will Each Of These US Indices Close On", "VIX : Higher^",
                               "TVC:VIX", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("European Stocks: How Will Each Of These Indices Close On", "CAC 40 : Higher^",
                               "TVC:CAC40", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("European Stocks: How Will Each Of These Indices Close On", "DAX : Higher^",
                               "XETR:DAX", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("European Stocks: How Will Each Of These Indices Close On", "EURO STOXX 50 : Higher^",
                               "TVC:SX5E", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("European Stocks: How Will Each Of These Indices Close On", "FTSE 100 : Higher^",
                               "TVC:UKX", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("European Stocks: How Will Each Of These Indices Close On", "IBEX 35 : Higher^",
                               "TVC:IBEX35", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("European Stocks: How Will Each Of These Indices Close On", "SMI : Higher^",
                               "SIX:SMI", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("Asian Stocks: How Will Each Of These Indices Close On",
                               "BSE SENSEX (SENSEX) : Higher^",
                               "BSE:SENSEX", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("Asian Stocks: How Will Each Of These Indices Close On",
                               "Hang Seng Index (HSI) : Higher^",
                               "HSI:HSI", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("Asian Stocks: How Will Each Of These Indices Close On",
                               "Nikkei 225 (NI225) : Higher^",
                               "TVC:NI225", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("Asian Stocks: How Will Each Of These Indices Close On",
                               "NIFTY 50 (NIFTY_50) : Higher^",
                               "NSE:NIFTY", api_key, bet_amount=bet_amount))
        tasks.append(
            bet_stock_movement("Asian Stocks: How Will Each Of These Indices Close On",
                               "SSE Composite Index (000001) : Higher^",
                               "SSE:000001", api_key, bet_amount=bet_amount))
        for task in tasks:
            asyncio.run(task)
        time.sleep(60 * 10)


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
API_KEY = os.getenv('API_KEY')
BUDGET = int(os.getenv('BUDGET'))
SEARCH_LIMIT = int(os.getenv('SEARCH_LIMIT'))
TIME_HORIZON = int(os.getenv('TIME_HORIZON'))
WAIT_INTERVAL = int(os.getenv('WAIT_INTERVAL'))
MIN_TRADERS = int(os.getenv('MIN_TRADERS'))
MAX_TRADERS = int(os.getenv('MAX_TRADERS'))
WAIT_TIME = int(os.getenv('WAIT_TIME'))
HUMAN_API_KEY = os.getenv('HUMAN_API_KEY')
HIGHER_BOUND = int(os.getenv('HIGHER_BOUND'))
LOWER_BOUND = HIGHER_BOUND - 86400
RANDOM_MARKET_CLOSE_ID = os.getenv('MARKET_ID')
SUPBASE_API_KEY = os.getenv('SUPBASE_API_KEY')


async def main():
    while True:
        try:
            logging.info("Starting Manifold processes...")
            """await asyncio.gather(
                momentum_bot(
                    API_KEY,
                    BET_PER_MARKET,
                    BUDGET,
                    SEARCH_LIMIT,
                    TIME_HORIZON,
                    WAIT_INTERVAL,
                    MIN_TRADERS,
                    MAX_TRADERS,
                    WAIT_TIME,
                ),
                close_random_time(
                    HUMAN_API_KEY,
                    LOWER_BOUND,
                    HIGHER_BOUND,
                    RANDOM_MARKET_CLOSE_ID,
                )
            )"""
            await bet_stock_markets()
        except Exception:
            pass


async def bet_users():
    logging.info("Live-betting on users...")
    while True:
        try:
            await get_live_bets(
                SUPBASE_API_KEY,
                API_KEY,
            )
        except Exception:
            pass
