from nationstates_ai import ns_ai_bot
from nationstates_preserve import ns_preserve
import asyncio
import logging
import json
import aiosqlite
import time
import os
import sys

logging.basicConfig(
    filename="logs.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
)

USER_AGENT = os.environ.get("USER_AGENT", "i.didnt.set.a.user.agent@disappointed.sad AI Issue Answering")
"""User agents need to include a form of contacting you as per NS API rules."""
try:
    HF_API_TOKEN = os.environ["HF_API_TOKEN"]
except KeyError:
    print("Input your Huggingface API token into your .env file under the name of HF_API_TOKEN.")
    sys.exit(0)
API_URL = os.environ.get("API_URL", "https://api-inference.huggingface.co/models/distilbert-base-cased-distilled-squad")
try:
    AI_NATIONS = json.loads(os.environ["AI_NATIONS"])
except KeyError:
    print("Input your Nationstates nations into your .env file under the name of NATIONS. "
          "See an example .env file at https://github.com/Bohaska/nationstates_ai/blob/main/.env.")
    sys.exit(0)
try:
    AI_NATIONSTATES_PASSWORDS = json.loads(os.environ["AI_NATIONSTATES_PASSWORDS"])
except KeyError:
    print("Input your Nationstates passwords into your .env file under the name of NATIONSTATES_PASSWORDS. "
          "See an example .env file at https://github.com/Bohaska/nationstates_ai/blob/main/.env.")
    sys.exit(0)
try:
    AI_PROMPTS = json.loads(os.environ["AI_PROMPTS"])
except KeyError:
    print("Input the prompts for your nations into your .env file under the name of PROMPTS. "
          "See an example .env file at https://github.com/Bohaska/nationstates_ai/blob/main/.env.")
    sys.exit(0)
try:
    PING_NATIONS = json.loads(os.environ["PING_NATIONS"])
except KeyError:
    print("Input your Nationstates nations into your .env file under the name of NATIONS. "
          "See an example .env file at https://github.com/Bohaska/nationstates_ai/blob/main/.env.")
    sys.exit(0)
try:
    PING_NATIONSTATES_PASSWORDS = json.loads(os.environ["PING_NATIONSTATES_PASSWORDS"])
except KeyError:
    print("Input your Nationstates passwords into your .env file under the name of NATIONSTATES_PASSWORDS. "
          "See an example .env file at https://github.com/Bohaska/nationstates_ai/blob/main/.env.")
    sys.exit(0)


async def get_ai_coroutines(
        user_agent, hf_api_token, api_url, ns_passwords, nations, prompts
):
    con = await aiosqlite.connect("nationstates_ai.db")
    ns_ai_coroutines = []
    counter = 0
    for index in range(len(ns_passwords)):
        cursor = await con.execute("SELECT name FROM sqlite_master WHERE name='next_issue_time'")
        table = await cursor.fetchone()
        if table is not None:
            cursor = await con.execute(
                "SELECT timestamp FROM next_issue_time WHERE nation = ?",
                (nations[index],),
            )
            timestamp = await cursor.fetchone()
            if timestamp is not None:
                if timestamp[0] > time.time():
                    ns_ai_coroutines.append(
                        ns_ai_bot(
                            nations[index],
                            ns_passwords[index],
                            {"Authorization": f"Bearer {hf_api_token}"},
                            api_url,
                            prompts[index],
                            user_agent,
                            timestamp[0] - time.time() + 10,
                        )
                    )
                else:
                    ns_ai_coroutines.append(
                        ns_ai_bot(
                            nations[index],
                            ns_passwords[index],
                            {"Authorization": f"Bearer {hf_api_token}"},
                            api_url,
                            prompts[index],
                            user_agent,
                            counter * 10,
                        )
                    )
                    counter += 1
            else:
                ns_ai_coroutines.append(
                    ns_ai_bot(
                        nations[index],
                        ns_passwords[index],
                        {"Authorization": f"Bearer {hf_api_token}"},
                        api_url,
                        prompts[index],
                        user_agent,
                        counter * 10,
                    )
                )
                counter += 1
        else:
            ns_ai_coroutines.append(
                ns_ai_bot(
                    nations[index],
                    ns_passwords[index],
                    {"Authorization": f"Bearer {hf_api_token}"},
                    api_url,
                    prompts[index],
                    user_agent,
                    counter * 10,
                )
            )
            counter += 1
    await con.close()
    return ns_ai_coroutines


async def get_ping_coroutines(
        user_agent, nations, ns_passwords
):
    con = await aiosqlite.connect("nationstates_preserve.db")
    ns_coroutines = []
    counter = 0
    for index in range(len(ns_passwords)):
        cursor = await con.execute("SELECT name FROM sqlite_master WHERE name='next_ping_time'")
        table = await cursor.fetchone()
        if table is not None:
            cursor = await con.execute(
                "SELECT timestamp FROM next_ping_time WHERE nation = ?",
                (nations[index],),
            )
            timestamp = await cursor.fetchone()
            if timestamp is not None:
                if timestamp[0] > time.time():
                    ns_coroutines.append(
                        ns_preserve(
                            nations[index],
                            ns_passwords[index],
                            user_agent,
                            timestamp[0] - time.time() + 10,
                        )
                    )
                else:
                    ns_coroutines.append(
                        ns_preserve(
                            nations[index],
                            ns_passwords[index],
                            user_agent,
                            counter * 10,
                        )
                    )
                    counter += 1
            else:
                ns_coroutines.append(
                    ns_preserve(
                        nations[index],
                        ns_passwords[index],
                        user_agent,
                        counter * 10,
                    )
                )
                counter += 1
        else:
            ns_coroutines.append(
                ns_preserve(
                    nations[index],
                    ns_passwords[index],
                    user_agent,
                    counter * 10,
                )
            )
            counter += 1
    await con.close()
    return ns_coroutines


async def run_all_tasks():
    while True:
        try:
            ai_coroutines = await get_ai_coroutines(USER_AGENT, HF_API_TOKEN, API_URL, AI_NATIONSTATES_PASSWORDS, AI_NATIONS,
                                                    AI_PROMPTS)
            ping_coroutines = await get_ping_coroutines(USER_AGENT, PING_NATIONS, PING_NATIONSTATES_PASSWORDS)
            all_tasks = ai_coroutines + ping_coroutines
            thing = await asyncio.gather(*all_tasks)
            return thing
        except Exception:
            pass