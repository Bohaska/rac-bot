import logging
import time
import aiohttp
import asyncio
import aiosqlite

logging.basicConfig(
    filename="logs.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
)


async def manage_ratelimit(response: aiohttp.ClientResponse):
    if int(response.headers["RateLimit-Remaining"]) < 10:
        sleep_time = int(response.headers["RateLimit-Reset"])
        logging.info(f"Pausing server for {sleep_time} seconds to avoid rate-limits.")
        print(f"Pausing server for {sleep_time} seconds to avoid rate-limits.")
        time.sleep(sleep_time)
        logging.info(
            f"Resumed server after sleeping for {sleep_time} seconds to avoid rate-limits."
        )
        print(f"Resumed server after sleeping for {sleep_time} seconds to avoid rate-limits.")


async def ping(
        nation: str,
        ns_session: aiohttp.ClientSession,
):
    logging.info(f"Pinging nation {nation}...")
    api_url = f"https://www.nationstates.net/cgi-bin/api.cgi"
    params = {
        "nation": nation,
        "q": "ping",
    }
    ns_session = aiohttp.ClientSession(headers=ns_session.headers)
    async with ns_session.get(api_url, params=params) as response:
        if response.status == 200:
            logging.info(f"Pinged nation {nation} successfully.")
            print(f"Pinged nation {nation} successfully.")
        else:
            logging.error(
                f"Pinging failed with error code {response.status}"
            )
            print(f"Pinging failed with error code {response.status}")
        await manage_ratelimit(response)
    return


async def time_to_next_ping(nation: str):
    timestamp = time.time() + 43200
    next_ping_time = 43210
    con = await aiosqlite.connect("nationstates_preserve.db")
    cursor = await con.execute(
        "SELECT name FROM sqlite_master WHERE name='next_ping_time'"
    )
    table = await cursor.fetchone()
    if table is None:
        await con.execute("CREATE TABLE next_ping_time(nation, timestamp)")
    data = (nation, timestamp)
    await con.execute("DELETE FROM next_ping_time WHERE nation = ?", (nation,))
    await con.commit()
    await con.execute("""INSERT INTO next_ping_time VALUES(?, ?)""", data)
    await con.commit()
    await con.close()
    return next_ping_time


async def startup_ratelimit(nation, wait_time):
    print(
        f"""Nation {nation} prepared. 
        Sleeping for {wait_time} seconds before starting to avoid rate limits..."""
    )
    logging.info(
        f"""Nation {nation} prepared. 
        Sleeping for {wait_time} seconds before starting to avoid rate limits..."""
    )
    await asyncio.sleep(wait_time)
    print(
        f"""Nation {nation} has woke up and will be kept alive until the end of time!"""
    )
    logging.info(
        f"""Nation {nation} has woke up and will be kept alive until the end of time!"""
    )


async def ns_preserve(
        nation, password, user_agent, wait_time: int
):
    await startup_ratelimit(nation, wait_time)
    while True:
        headers = {
            "X-Password": password,
            "User-Agent": user_agent + " Nationstates Preserve v0.0.1-alpha",
        }
        await ping(
            nation,
            aiohttp.ClientSession(headers=headers),
        )
        next_ping_time = await time_to_next_ping(nation)
        logging.info(
            f"Nation {nation} sleeping {next_ping_time} seconds until next ping..."
        )
        print(f"Nation {nation} sleeping {next_ping_time} seconds until next ping...")
        await asyncio.sleep(next_ping_time)
