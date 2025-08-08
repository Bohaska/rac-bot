import aiohttp
import nextcord
from nextcord import Interaction, SlashOption, Intents, Message, ButtonStyle, Embed, Colour, Permissions, Member, \
    AllowedMentions, Role, errors, Attachment, VoiceChannel, File
from nextcord.ext import commands
from nextcord.ui import View, Button, TextInput, Modal
import logging
from datetime import datetime, timezone, timedelta
from json.decoder import JSONDecodeError

import ballsdex_hash
import nation_name_generator as markov
import os
import math
import re
import random
import string
import asyncio
import functools
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
# from dontuserepl import lazy_setup
from thefuzz import fuzz
from PIL import Image, ImageOps
from pymongo.errors import DuplicateKeyError
from better_view import AutoDisableView
import json
from ballsdex_hash import check_balldex_image
import soccer


load_dotenv()
RAC_SERVER_ID = 793104002224488481
OWNER_ID = 813757881723519026  # bohaska's id
uri = os.getenv('DB_URL')
bot_colour = Colour.from_rgb(131, 28, 193)
BALLSDEX_ID = 999736048596816014
SPAWN_PING_ROLE = 1221319179836330064
RARE_SPAWN_PING_ROLE = 1222110020674781184
ball_exists = False
MAP_CHANNELS = {
    "Teremia": 1401857132076339220,
    "Ninoia": 1401857169325948958,
}
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/131.0.2903.86",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/116.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/116.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Vivaldi/7.0.3495.29",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/131.0.2903.86",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/116.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Vivaldi/7.0.3495.29",
]

db_client = AsyncIOMotorClient(uri)

# Transition at midnight UTC between July 27 and July 28, 2025
RAC_TRANSITION_DATETIME = datetime(2025, 7, 28, 0, 0, 0, tzinfo=timezone.utc)

# Special case start for RAC year 4092
RAC_4092_START = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
RAC_4092_END = datetime(2025, 7, 28, 0, 0, 0, tzinfo=timezone.utc)

def is_leap_year(date_time):
    return not date_time.year % 400 or not date_time.year % 4 and date_time.year % 100


def get_rac_time(now_time=None):
    if not now_time:
        now_time = datetime.now(timezone.utc)

    if now_time < RAC_4092_START:
        # Legacy: 1 RAC year per month
        rac_year = (now_time.year - 2023) * 12 + 4061 + now_time.month
        rac_year_start = datetime(rac_year, 1, 1, tzinfo=timezone.utc)

        month_to_day = [None, 31, 29 if is_leap_year(now_time) else 28, 31, 30, 31,
                        30, 31, 31, 30, 31, 30, 31]
        days_in_year = 366 if is_leap_year(rac_year_start) else 365

        hours = now_time.hour + now_time.minute / 60 + now_time.second / 3600
        rac_days = ((((now_time.day - 1) * 24) + hours) / (month_to_day[now_time.month] * 24)) * days_in_year

        return rac_year_start + timedelta(days=rac_days)

    elif now_time < RAC_TRANSITION_DATETIME:
        # Special case: RAC year 4092 is from July 1 to July 27
        rac_year_start = datetime(4092, 1, 1, tzinfo=timezone.utc)
        total_seconds = (now_time - RAC_4092_START).total_seconds()
        fraction = total_seconds / (27 * 24 * 60 * 60)  # 27 days in RAC year 4092

        days_in_year = 366 if is_leap_year(rac_year_start) else 365
        return rac_year_start + timedelta(days=fraction * days_in_year)

    else:
        # New system: 1 RAC year every 2 weeks (14 days)
        base_rac_year = 4093
        base_irl = RAC_TRANSITION_DATETIME

        delta_days = (now_time - base_irl).days
        extra_seconds = (now_time - base_irl).seconds

        rac_years_passed = delta_days // 14
        remainder_days = (delta_days % 14) + (extra_seconds / (24 * 60 * 60))
        rac_year = base_rac_year + rac_years_passed
        rac_year_start = datetime(rac_year, 1, 1, tzinfo=timezone.utc)

        days_in_year = 366 if is_leap_year(rac_year_start) else 365
        rac_days = (remainder_days / 14) * days_in_year

        return rac_year_start + timedelta(days=rac_days)


def get_irl_time(rac_time: datetime):
    if rac_time.year < 4092:
        # Legacy: 1 RAC year per month
        irl_year = math.floor((rac_time.year - 4061) / 12) + 2023
        irl_month = (rac_time.year - 4061) % 12
        if irl_month == 0:
            irl_month = 12
            irl_year -= 1

        base = datetime(rac_time.year, 1, 1, tzinfo=timezone.utc)
        days_passed = (rac_time - base).total_seconds()

        month_to_day = [0, 31, 29 if is_leap_year(datetime(irl_year, 1, 1)) else 28, 31, 30, 31,
                        30, 31, 31, 30, 31, 30, 31]
        days_in_month = month_to_day[irl_month]
        days_in_year = 366 if is_leap_year(base) else 365

        percentage = days_passed / (days_in_year * 24 * 3600)
        delta = timedelta(days=percentage * days_in_month)

        return datetime(irl_year, irl_month, 1, tzinfo=timezone.utc) + delta

    elif rac_time.year == 4092:
        # Special RAC year 4092: map July 1–27
        base = datetime(4092, 1, 1, tzinfo=timezone.utc)
        days_passed = (rac_time - base).total_seconds()
        days_in_year = 366 if is_leap_year(base) else 365

        percentage = days_passed / (days_in_year * 24 * 3600)
        delta = timedelta(days=percentage * 27)

        return RAC_4092_START + delta

    else:
        # New system: 1 RAC year every 14 days starting from 2025-07-28
        base_rac_year = 4093
        base_irl = RAC_TRANSITION_DATETIME

        rac_years_passed = rac_time.year - base_rac_year
        base_rac_start = datetime(rac_time.year, 1, 1, tzinfo=timezone.utc)
        days_in_year = 366 if is_leap_year(base_rac_start) else 365

        fraction = (rac_time - base_rac_start).total_seconds() / (days_in_year * 24 * 3600)
        irl_offset = timedelta(days=(rac_years_passed * 14) + fraction * 14)

        return base_irl + irl_offset


def format_time(date_time, am_pm, prettyprint):
    if am_pm == "AM/PM" and prettyprint == "Pretty print":
        return date_time.strftime("%A %B %-d, %-I:%M %p, %Y")
    elif am_pm == "AM/PM":
        return date_time.strftime("%Y-%m-%d %I:%M %p")
    elif prettyprint == "Pretty print":
        return date_time.strftime("%A %B %-d, %-H:%M, %Y")
    else:
        return date_time.strftime("%Y-%m-%d %H:%M")


def format_large_number(number: int):
    # If the number is bigger than a trillion
    if number >= 1000000000000:
        # If the number is bigger than a hundred trillion
        number = number / 1000000000000
        if number >= 100:
            return f"{int(number)} trillion"
        # If the number is smaller than a hundred trillion
        else:
            return f"{number:.2f} trillion"
    # If the number is bigger than a billion
    elif number >= 1000000000:
        # If the number is bigger than a hundred billion
        number = number / 1000000000
        if number >= 100:
            return f"{int(number)} billion"
        else:
            return f"{number:.2f} billion"
    # A million
    elif number >= 1000000:
        number = number / 1000000
        if number >= 100:
            return f"{int(number)} million"
        else:
            return f"{number:.2f} million"
    # A thousand
    elif number >= 1000:
        number = number / 1000
        if number >= 100:
            return f"{int(number)} thousand"
        else:
            return f"{number:.2f} thousand"
    else:
        return str(number)


async def upload_image(url):
    session = aiohttp.ClientSession()
    params = {"key": os.getenv("IMGBB_API_KEY"), "image": url}
    async with session:
        url_image = await session.post("https://api.imgbb.com/1/upload", params=params)
    url = await url_image.json()
    url = url["data"]["url"]
    return url


def read_message(msg: Message):
    full_msg = msg.content
    if msg.embeds:
        for embed in msg.embeds:
            full_msg += f"\n\n# {embed.title}\n\n{embed.description}"
    return full_msg


async def get_message_from_link(message_link):
    pattern = r"^https://discord\.com/channels/\d+/\d+/\d+$"
    if bool(re.match(pattern, message_link)):
        new_link = message_link.split("/")
        server = await bot.fetch_guild(int(new_link[4]))
        channel = await server.fetch_channel(int(new_link[5]))
        link_message = await channel.fetch_message(int(new_link[6]))
    else:
        raise ValueError("That is not a valid Discord message link.")
    return link_message


bot = commands.Bot(intents=Intents(guilds=True, members=True, message_content=True, messages=True))


@bot.slash_command(
    description="Gets the time in RAC.",
    force_global=True)
async def time(interaction: Interaction):
    pass


@bot.slash_command(
    description="Detect whether a text was written by an AI.",
    force_global=True)
async def detect_ai(interaction: Interaction):
    pass


"""@bot.slash_command(
    description="Talk to an AI",
    force_global=True
)
async def talk_to_ai(interaction: Interaction):
    pass"""


@bot.slash_command(
    description="Gamenight commands",
    force_global=True,
    default_member_permissions=Permissions(manage_roles=True)
)
async def game_night(interaction: Interaction):
    pass


@bot.slash_command(
    description="Country info lookup",
    force_global=True)
async def country(interaction: Interaction):
    pass


@bot.slash_command(
    description="Manage your cell bank",
    force_global=True)
async def cells(interaction: Interaction):
    pass


@bot.slash_command(
    force_global=True)
async def map(interaction: Interaction):
    pass


@time.subcommand(
    description="Gets the current time in RAC.", )
async def now(interaction: Interaction,
              am_pm: str = SlashOption(description="Use AM/PM format or not?",
                                       choices=("AM/PM", "24 hour"),
                                       default="24 hour"),
              prettyprint: str = SlashOption(description="Print the raw time or make it look nice?",
                                             choices=("Pretty print", "Raw time"),
                                             default="Raw time")):
    await interaction.response.defer()
    irl_unix_timestamp = int(datetime.now(tz=timezone.utc).timestamp())
    rac_time = format_time(get_rac_time(), am_pm, prettyprint)
    time_message = f"{rac_time}\n<t:{irl_unix_timestamp}:f>\n<t:{irl_unix_timestamp}:R>"
    await interaction.followup.send(time_message)


@time.subcommand(
    description="Gets the time in RAC from an IRL date. Input hour, minute and timezone for more accurate dates.")
async def custom(interaction: Interaction,
                 year: int = SlashOption(
                     description="The year of the IRL date you want to convert to RAC time.",
                     min_value=1,
                     max_value=9999,
                     required=True),
                 month: int = SlashOption(
                     description="The month of the IRL date you want to convert to RAC time.",
                     choices={"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                              "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
                              "December": 12},
                     required=True),
                 day: int = SlashOption(
                     description="The day of the IRL date you want to convert to RAC time.",
                     min_value=1,
                     max_value=31,
                     required=True),
                 hour: int = SlashOption(
                     description="The hour of the IRL date you want to convert to RAC time."
                                 " Must be given in 24 hour format.",
                     min_value=0,
                     max_value=23,
                     default=0),
                 minute: int = SlashOption(
                     description="The minute of the IRL date you want to convert to RAC time.",
                     min_value=0,
                     max_value=59,
                     default=0),
                 user_timezone: int = SlashOption(
                     description="Timezone offset from GMT/UTC. E.g. GMT +1 -> 1, GMT -2 -> -2.",
                     min_value=-12,
                     max_value=12,
                     default=0),
                 am_pm: str = SlashOption(description="Use AM/PM format or not?",
                                          choices=("AM/PM", "24 hour"),
                                          default="24 hour"),
                 prettyprint: str = SlashOption(description="Print the raw time or make it look nice?",
                                                choices=("Pretty print", "Raw time"),
                                                default="Raw time")):
    await interaction.response.defer()
    if year % 4 == 0:
        """A leap year"""
        """month_to_day index represents the month, the value represents the number of days past."""
        month_to_day = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    else:
        """Not a leap year"""
        month_to_day = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month_to_day[month] < day:
        await interaction.followup.send(content="The day must be smaller than the number of days"
                                                " in that month.",
                                        ephemeral=True)
    else:
        current_time = datetime(year=year, month=month, day=day, hour=hour, minute=minute,
                                tzinfo=timezone.utc)
        delta = timedelta(hours=user_timezone)
        current_time -= delta
        try:
            rac_time = get_rac_time(current_time)
        except ValueError:
            await interaction.followup.send(content="Sorry, we don't support RAC years smaller than 1 or bigger"
                                                    " than 9999 yet.")
            return
        irl_unix_timestamp = int(current_time.timestamp())
        rac_time = format_time(rac_time, am_pm, prettyprint)
        time_message = f"{rac_time}\n<t:{irl_unix_timestamp}:R>"
        await interaction.followup.send(time_message)


@time.subcommand(
    description="Gets the IRL time from a RAC date.")
async def rac_to_irl(interaction: Interaction,
                     year: int = SlashOption(
                         description="The year of the RAC date you want to convert to IRL time.",
                         min_value=1,
                         max_value=9999,
                         required=True),
                     month: int = SlashOption(
                         description="The month of the RAC date you want to convert to IRL time.",
                         choices={"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                                  "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
                                  "December": 12},
                         required=True),
                     day: int = SlashOption(
                         description="The day of the RAC date you want to convert to IRL time.",
                         min_value=1,
                         max_value=31,
                         required=True),
                     hour: int = SlashOption(
                         description="The hour of the RAC date you want to convert to IRL time."
                                     " Must be given in 24 hour format.",
                         min_value=0,
                         max_value=23,
                         default=0),
                     minute: int = SlashOption(
                         description="The minute of the RAC date you want to convert to IRL time.",
                         min_value=0,
                         max_value=59,
                         default=0),
                     am_pm: str = SlashOption(description="Use AM/PM format or not?",
                                              choices=("AM/PM", "24 hour"),
                                              default="24 hour"),
                     prettyprint: str = SlashOption(description="Print the raw time or make it look nice?",
                                                    choices=("Pretty print", "Raw time"),
                                                    default="Raw time")):
    await interaction.response.defer()
    if year % 4 == 0:
        """A leap year"""
        """month_to_day index represents the month, the value represents the number of days past."""
        month_to_day = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    else:
        """Not a leap year"""
        month_to_day = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month_to_day[month] < day:
        await interaction.followup.send(content="The day must be smaller than the number of days"
                                                " in that month.",
                                        ephemeral=True)
    else:
        rac_time = datetime(year=year, month=month, day=day, hour=hour, minute=minute,
                            tzinfo=timezone.utc)
        try:
            irl_time = get_irl_time(rac_time)
        except ValueError:
            await interaction.followup.send(content="Sorry, we don't support years smaller than 1 or bigger"
                                                    " than 9999 yet.",
                                            ephemeral=True)
            return
        unix_timestamp = int(irl_time.timestamp())
        irl_time = format_time(irl_time, am_pm, prettyprint)
        time_message = f"{irl_time}\n<t:{unix_timestamp}:f>\n<t:{unix_timestamp}:R>"
        await interaction.followup.send(time_message)


@time.subcommand(
    description="Gets the time in RAC from a message link. Uses message creation date.")
async def message(interaction: Interaction,
                  link: str = SlashOption(
                      description="The link of the message.",
                      required=True),
                  am_pm: str = SlashOption(description="Use AM/PM format or not?",
                                           choices=("AM/PM", "24 hour"),
                                           default="24 hour"),
                  prettyprint: str = SlashOption(description="Print the raw time or make it look nice?",
                                                 choices=("Pretty print", "Raw time"),
                                                 default="Raw time")):
    await interaction.response.defer()
    try:
        user_message = await get_message_from_link(link)
        rac_time = get_rac_time(user_message.created_at)
        irl_unix_timestamp = int(user_message.created_at.timestamp())
        rac_time = format_time(rac_time, am_pm, prettyprint)
        time_message = f"Message link: {user_message.jump_url}\n{rac_time}\n<t:{irl_unix_timestamp}:R>"
        await interaction.followup.send(time_message)
    except (errors.NotFound, ValueError):
        await interaction.followup.send(content="We couldn't find the message. Did you put a message link?",
                                        ephemeral=True)


@bot.message_command(name="Get RAC time")
async def command_rac_time(interaction: Interaction, sent_message: Message):
    await interaction.response.defer()
    rac_time_a = get_rac_time(sent_message.created_at)
    irl_unix_timestamp = int(sent_message.created_at.timestamp())
    rac_time_a = rac_time_a.strftime("%A %B %-d, %-H:%M, %Y")
    time_message = f"Message link: {sent_message.jump_url}\n{rac_time_a}\n<t:{irl_unix_timestamp}:R>"
    await interaction.followup.send(time_message)


def generate_random_string(length=32):
    characters = string.ascii_lowercase + string.digits  # Lowercase letters + numbers
    return ''.join(random.choices(characters, k=length))

def generate_random_uuid():
    characters = string.hexdigits.lower()  # 0-9 and a-f
    u = ''.join(random.choices(characters, k=44))  # Generate 44 hex characters
    return f"{u[:12]}-{u[12:24]}-{u[24:30]}-{u[30:36]}-{u[36:]}"  # Format like example


async def pangram_ai_csrf_token(session_id):
    cookies = {
        'sessionid': session_id,
    }

    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://www.pangram.com',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://www.pangram.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }

    session = aiohttp.ClientSession()
    async with session:
        resp = await session.get('https://web.pangram.com/api/accounts/get-csrf/', cookies=cookies, headers=headers)
    resp = await resp.json(content_type=None)
    return resp["csrfToken"]


async def pangram_detection_api(input_text, session_id, csrf_token):
    cookies = {
        'sessionid': session_id,
    }

    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        # 'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token,
        'Origin': 'https://www.pangram.com',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://www.pangram.com/',
        # 'Cookie': 'sessionid=nvghx1am2ae0yfnif8sdoi0ncgoq87p8',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Priority': 'u=0',
    }

    json_data = {
        'text': input_text,
        'source': 'product',
        'logging': False,
        'distinctId': f'$device:{generate_random_uuid()}',
    }

    session = aiohttp.ClientSession()
    async with session:
        resp = await session.post('https://web.pangram.com/api/classify-text-sliding-window/', cookies=cookies, headers=headers, json=json_data)
    resp = await resp.json(content_type=None)
    return resp


async def pangram_detect_ai_text(input_text):
    session_id = generate_random_string()
    csrf_token = await pangram_ai_csrf_token(session_id)
    ai_detection_resp = await pangram_detection_api(input_text, session_id, csrf_token)
    return ai_detection_resp


async def pangram_detect_ai_message(input_text):
    ai_detection = await pangram_detect_ai_text(input_text)
    llm_model = ""
    max_key = max(ai_detection["llm_prediction"], key=ai_detection["llm_prediction"].get)
    if ai_detection["llm_prediction"][max_key] > 0.2:
        llm_model = f"Most likely AI model: {max_key} ({ai_detection['llm_prediction'][max_key] * 100:.2f}%)\n"
    ai_keywords = ""
    if ai_detection["ngram"]["keywords"]:
        ai_keywords = "Suspicious keywords:"
        for keyword in ai_detection["ngram"]["keywords"]:
            ai_keywords += f"\n{keyword['keyword']}: **{int(float(keyword['frequency']))}x** more likely in AI text"
        ai_keywords = ai_keywords.strip()
    followup_text = f"""### {ai_detection["prediction"]}
Estimated likelihood of AI/GPT text: {ai_detection["ai_likelihood"] * 100:.2f}%
Estimated portion of AI/GPT text: {ai_detection["fraction_ai_content"] * 100:.2f}%
{llm_model}
{ai_keywords}"""
    return followup_text


async def ai_detection_api(input_text):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-Hans;q=0.7,zh;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'https://www.zerogpt.com',
        'Pragma': 'no-cache',
        'Referer': 'https://www.zerogpt.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/110.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }
    api_url = "https://api.zerogpt.com/api/detect/detectText"
    session = aiohttp.ClientSession()
    async with session:
        ai_result = await session.post(api_url, json={"input_text": input_text}, headers=headers)
    ai_result = await ai_result.json(content_type=None)
    result_texts = {100: "Your text is human written", 87: "Your text is most likely human written",
                    0: "Your text is AI/GPT generated", 12: "Most of your text is AI/GPT generated",
                    62: "Your text is likely human written, may include parts generated by AI/GPT",
                    75: "Your text is most likely human written, may include parts generated by AI/GPT",
                    25: "Your text is most likely AI/GPT generated", 37: "Your text is likely generated by AI/GPT",
                    50: "Your text contains mixed signals, with some parts generated by AI/GPT"}
    is_human = result_texts[int(float(ai_result["data"]["isHuman"]))]
    result = {
        "human_comment": is_human,
        "ai_sentences": ai_result["data"]["h"],
        "additional_feedback": ai_result["data"]["additional_feedback"],
        "ai_percentage": ai_result["data"]["fakePercentage"]
    }
    return result


@detect_ai.subcommand(description="Checks a piece of text to see whether it was written by an AI.")
async def text(interaction: Interaction,
               analyze_text: str = SlashOption(
                   description="The text you want to analyse",
                   required=True,
                   name="text")):
    await interaction.response.defer()
    try:
        followup_text = await pangram_detect_ai_message(analyze_text)
        await interaction.followup.send(content=followup_text, allowed_mentions=AllowedMentions.none())
    except JSONDecodeError:
        await interaction.followup.send(content="The AI text detection server failed to respond.")


@detect_ai.subcommand(description="Checks a Discord message to see whether it was written by an AI.")
async def message(interaction: Interaction,
                  link: str = SlashOption(
                      description="The message link you want to analyse",
                      required=True)):
    await interaction.response.defer()
    try:
        user_message = await get_message_from_link(link)
    except Exception:
        await interaction.followup.send(content="An error occurred while fetching the Discord message link.")
        return
    try:
        ai_detection = await pangram_detect_ai_message(user_message.clean_content)
        followup_text = f"""Message link: {link}
{ai_detection}"""
        await interaction.followup.send(content=followup_text, allowed_mentions=AllowedMentions.none())
    except JSONDecodeError:
        await interaction.followup.send(content="The AI text detection server failed to respond.")


@bot.message_command(name="Analyze message for AI writing")
async def message(interaction: Interaction, message: Message):
    await interaction.response.defer()
    try:
        ai_detection = await pangram_detect_ai_message(message.clean_content)
        followup_text = f"""Message link: {message.jump_url}
{ai_detection}"""
        await interaction.followup.send(content=followup_text, allowed_mentions=AllowedMentions.none())
    except JSONDecodeError:
        await interaction.followup.send(content="The AI text detection server failed to respond.")


@bot.event
async def on_message(message: nextcord.Message):
    global ball_exists
    if message.author.id == bot.user.id:
        return
    if message.channel.id == 1004795268073541774 and message.author.id == 1004808899431497823 and len(
            message.clean_content) >= 400:
        try:
            ai_detection = await pangram_detect_ai_text(message.clean_content)
        except:
            return
        if ai_detection["ai_likelihood"] >= 0.5:
            followup_text = f"""Hey

Why does your post have {ai_detection["ai_likelihood"] * 100:.2f}% AI text according to my AI text detector?

Kind regards,
<@{OWNER_ID}>
"""
            await message.channel.send(followup_text, reference=message, allowed_mentions=AllowedMentions.all())
            await message.add_reaction("🔴")
        elif ai_detection["ai_likelihood"] >= 0.25:
            await message.add_reaction("🟡")
        else:
            await message.add_reaction("🟢")
    elif message.author.id == OWNER_ID and "hey rac bot" in message.clean_content:
        if message.reference is not None:
            await message.delete()
            reference_message = await get_message_from_link(message.reference.jump_url)
            await message.channel.send(f"Hey {reference_message.author.mention}, nice to meet you!",
                                       reference=reference_message, allowed_mentions=AllowedMentions.all())
        else:
            await message.channel.send(f"Hey <@{OWNER_ID}>, nice to meet you!", reference=message,
                                       allowed_mentions=AllowedMentions.all())
    elif message.author.id == OWNER_ID and "rac:" in message.content[:4]:
        await message.delete()
        if message.reference is not None:
            reference_message = await get_message_from_link(message.reference.jump_url)
            await message.channel.send(message.content[4:],
                                       reference=reference_message, allowed_mentions=AllowedMentions.all())
        else:
            await message.channel.send(message.content[4:], allowed_mentions=AllowedMentions.all())
    elif message.author.id == OWNER_ID and "list servers" == message.content:
        guild_message = "# Guilds\n"
        async for guild in bot.fetch_guilds(limit=100):
            guild_message += guild.name
            invites = await guild.invites()
            if invites:
                guild_message += " Invite:" + invites[0].url + "\n"
        await message.channel.send(guild_message, reference=message)
    elif message.author.id == BALLSDEX_ID and message.guild.id == RAC_SERVER_ID:
        global ball_exists
        if message.content == "A wild countryball appeared!":
            ball_exists = True
            ballsdex_image = "ballsdex_" + str(message.id)
            await message.attachments[0].save(ballsdex_image)
            ball_name = check_balldex_image(ballsdex_image)
            os.remove(ballsdex_image)
            await asyncio.sleep(120)
            with open("rare_countryballs.txt", "r") as rare_countryballs:
                rare_countryballs_list = rare_countryballs.read().splitlines()
            text_message = f"<@&{SPAWN_PING_ROLE}>\nBallsdex spawned a countryball!"
            if ball_exists:
                if ball_name:
                    text_message += f"\nCatch name: ```{ball_name}```"
                    if ball_name in rare_countryballs_list:
                        text_message = f"<@&{RARE_SPAWN_PING_ROLE}> " + text_message
                await message.channel.send(text_message, reference=message, allowed_mentions=AllowedMentions.all())
        elif "You caught" in message.content:
            ball_exists = False
            initial_ball_message = await get_message_from_link(message.reference.jump_url)
            ball_name = re.findall(r'\*\*(.*?)!\*\*', message.content)[0]
            image_path = "ballsdex/" + ball_name + ".png"
            await initial_ball_message.attachments[0].save(image_path)
            if not check_balldex_image(image_path) == ball_name:
                image_hash = ballsdex_hash.hash_image(image_path)
                with open(ballsdex_hash.JSON_PATH, "r") as json_file:
                    hash_dict = json.load(json_file)
                hash_dict[image_hash] = ball_name
                with open(ballsdex_hash.JSON_PATH, 'w') as write_file:
                    json.dump(hash_dict, write_file)
            os.remove(image_path)
    elif message.channel.id in MAP_CHANNELS.values():
        map_attachment = None
        for attachment in message.attachments:
            if attachment.filename[-4:] == ".map":
                map_attachment = attachment
        if map_attachment is not None:
            # start parsing the map
            map_filename = f"azgaar_map_{message.id}"
            map_text = await get_attachment(map_attachment, map_filename)
            map_lines = combine_svg(map_text)
            state_info = json.loads(map_lines[14])
            settings = map_lines[1].split("|")
            map_name = settings[20]
            thread_name = map_name + " " + format_date(datetime.now()) + " map discussion"
            thread = await message.create_thread(name=thread_name)
            new_state_info = []
            for state in state_info:
                try:
                    if state.get("removed") is not True:
                        new_state_info.append(
                            {
                                'name': state['name'],
                                'cells': state['cells'],
                                'map_name': map_name,
                            }
                        )
                except KeyError:
                    pass
            new_state_info.sort(key=lambda state: state['cells'], reverse=True)
            new_state_info = paginate_list(new_state_info)
            view = PaginatedView(new_state_info, state_cells_embed, save_button=False)
            embed = state_cells_embed(new_state_info, 0)
            # finally done
            message_text = "New map just dropped!"
            if "ping" in message.content:
                message_text = "<@&832161270932308010> New map just dropped!"
            await thread.send(message_text, view=view, embed=embed,
                              allowed_mentions=AllowedMentions.all())
    if message.interaction:
        if message.interaction.name == "bump" and message.author.id == 302050872383242240:
            collection = db_client.bump_tracking.balance
            existing_bank = await collection.find_one({"_id": str(message.interaction.user.id)})
            additional_message = ""
            if existing_bank is not None:
                balance = existing_bank["balance"]
                history_entry = {
                    "time": int(datetime.now().timestamp()),
                    "change": 1,
                    "new_balance": balance + 1,
                    "user_id": str(bot.user.id),
                    "reason": f"Bumped RAC. See {message.jump_url}"
                }
                existing_bank["history"].append(history_entry)
                updates = {
                    "balance": balance + 1,
                    "history": existing_bank["history"],
                }
                await collection.update_one({"_id": str(message.interaction.user.id)}, {"$set": updates})
                bumps_not_redeemed = existing_bank["balance"] + 1 - (existing_bank["cells_withdrawn"] * 3)
                cells_not_redeemed = int(bumps_not_redeemed / 3)
                if cells_not_redeemed > 0:
                    additional_message = f"\n\nYou can redeem {cells_not_redeemed} cells. " \
                                         f"Use the {withdraw.get_mention()} command to redeem your cells"
            else:
                bump_bank_setup = {
                    "_id": str(message.interaction.user.id),
                    "balance": 1,
                    "cells_withdrawn": 0,
                    "history": [
                        {
                            "time": int(datetime.now().timestamp()),
                            "change": 1,
                            "new_balance": 1,
                            "user_id": str(bot.user.id),
                            "reason": f"Bumped RAC. See {message.jump_url}"
                        },
                    ],
                }
                await collection.insert_one(bump_bank_setup)
            existing_bank = await collection.find_one({"_id": str(message.interaction.user.id)})
            existing_bank["history"].sort(key=lambda x: x["time"], reverse=True)
            history = paginate_list(existing_bank["history"])
            balance_view = BankBalanceViewer(0, existing_bank["balance"], history, message.interaction.user,
                                             currency="bumps")
            balance_embed = format_balance_embed(balance_view)
            msg = await message.channel.send(
                content=f"Added your bump!" + additional_message,
                embed=balance_embed,
                view=balance_view,
                reference=message,
            )


@bot.slash_command(
    description="View bump history.",
    force_global=True)
async def bump_bank(interaction: Interaction):
    pass


@bump_bank.subcommand(
    name="view",
    description="View a bump bank"
)
async def view(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The person whose bump bank you want to view.",
            required=False,
            default=None
        ),
):
    await interaction.response.defer()
    if user is None:
        user = interaction.user
    db = db_client.bump_tracking
    collection = db.balance
    existing_bank = await collection.find_one({"_id": str(user.id)})
    if existing_bank is None:
        await interaction.followup.send(f"{user.mention} does not have a bump bank. "
                                        f"Bump this server at least once to get one!")
        return
    existing_bank["history"].sort(key=lambda x: x["time"], reverse=True)
    history = paginate_list(existing_bank["history"])
    balance_view = BankBalanceViewer(0, existing_bank["balance"], history, user, currency="bumps")
    balance_embed = format_balance_embed(balance_view)
    msg = await interaction.followup.send(
        embed=balance_embed,
        view=balance_view
    )
    balance_view.init_interaction(interaction, msg.id)


@bump_bank.subcommand(
    name="withdraw",
    description="Convert your bumps into cells. 3 bumps = 1 cell."
)
async def withdraw(
        interaction: Interaction,
):
    await interaction.response.defer()
    user = interaction.user
    bump_db = db_client.bump_tracking.balance
    cells_db = db_client.cells.balance
    bump_bank = await bump_db.find_one({"_id": str(user.id)})
    cell_bank = await cells_db.find_one({"_id": str(user.id)})
    if bump_bank is None:
        await interaction.followup.send(f"You don't have a bump bank. "
                                        f"Bump this server at least once to get one!")
        return
    if cell_bank is None:
        await interaction.followup.send(f"You don't have a cell bank yet.\n\n"
                                        f"To set up a cell bank, use the {bank_setup.get_mention(guild=None)} command.")
        return
    bumps_not_redeemed = bump_bank["balance"] - (bump_bank["cells_withdrawn"] * 3)
    cells_not_redeemed = int(bumps_not_redeemed / 3)
    if cells_not_redeemed == 0:
        await interaction.followup.send(f"You're {3-bumps_not_redeemed} bumps away from getting a cell. Bump more!\n"
                                        f"In the past, you've redeemed a total of {bump_bank['cells_withdrawn']} cells!")
        return
    balance = cell_bank["balance"]
    history_entry = {
        "time": int(datetime.now().timestamp()),
        "change": cells_not_redeemed,
        "new_balance": balance + cells_not_redeemed,
        "user_id": str(bot.user.id),
        "reason": f"Transferred {cells_not_redeemed} cells from bumping."
    }
    cell_bank["history"].append(history_entry)
    cell_bank["balance"] += cells_not_redeemed
    cell_updates = {
        "balance": balance + cells_not_redeemed,
        "history": cell_bank["history"],
    }
    bump_updates = {
        "cells_withdrawn": bump_bank["cells_withdrawn"] + cells_not_redeemed
    }
    await cells_db.update_one({"_id": str(user.id)}, {"$set": cell_updates})
    await bump_db.update_one({"_id": str(user.id)}, {"$set": bump_updates})
    cell_bank["history"].sort(key=lambda x: x["time"], reverse=True)
    history = paginate_list(cell_bank["history"])
    balance_view = BankBalanceViewer(0, cell_bank["balance"], history, user)
    balance_embed = format_balance_embed(balance_view)
    msg = await interaction.followup.send(
        f"Transferred {cells_not_redeemed} cells from bumping! You've earned a total of {bump_bank['cells_withdrawn'] + cells_not_redeemed} from bumping.",
        embed=balance_embed,
        view=balance_view,
    )
    balance_view.init_interaction(interaction, msg.id)


def nation_name_embed(nation_name_list: list, index: int):
    return Embed(title="Here's your new random nation name!", description=nation_name_list[index],
                 colour=Colour.random(seed=nation_name_list[index].encode("utf-8"))).set_footer(
        text=f"{index + 1}/{len(nation_name_list)}")


class LeftButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Previous", row=1)

    async def callback(self, interaction: Interaction):
        index = self.view.index
        if self.view.index != 0:
            self.view.index = index - 1
        else:
            self.view.index = len(self.view.item_list) - 1
        embed = self.view.page_function(self.view.item_list, self.view.index)
        await interaction.response.edit_message(embed=embed)


class SaveButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.grey, label="Save", row=2, emoji="💾")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        embed = self.view.page_function(self.view.item_list, self.view.index)
        await interaction.followup.send(embed=embed)


class RightButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Next", row=1)

    async def callback(self, interaction: Interaction):
        index = self.view.index
        if index + 1 == len(self.view.item_list):
            self.view.index = 0
        else:
            self.view.index = index + 1
        embed = self.view.page_function(self.view.item_list, self.view.index)
        await interaction.response.edit_message(embed=embed)


class JumpInput(TextInput):
    def __init__(self, max_len: int):
        super().__init__(label="Jump", max_length=max_len, min_length=1,
                         placeholder="The page number you want to jump to", required=True)


class JumpModal(Modal):
    def __init__(self, item_list: list, index: int, page_function):
        super().__init__(title="Jump", timeout=600)
        self.item_list = item_list
        self.index = index
        self.add_item(JumpInput(len(str(index))))
        self.page_function = page_function

    async def callback(self, interaction: Interaction):
        try:
            page = int(self.children[0].value) - 1
        except ValueError:
            embed = self.page_function(self.item_list, self.index)
            await interaction.response.edit_message(embed=embed)
            return
        if page < 0:
            page = 0
        if page < len(self.item_list):
            self.index = page
        embed = self.page_function(self.item_list, self.index)
        await interaction.response.edit_message(embed=embed)
        return


class JumpButton(Button):
    def __init__(self, item_list: list):
        super().__init__(style=ButtonStyle.grey, label="Jump", row=1, emoji="⏩")
        self.item_list = item_list

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(JumpModal(self.item_list, self.view.index, self.view.page_function))


class PaginatedView(AutoDisableView):
    def __init__(self, item_list, page_function, save_button=None):
        super().__init__()
        self.index = 0
        self.add_item(LeftButton())
        self.add_item(JumpButton(item_list))
        if save_button is None or save_button is True:
            self.add_item(SaveButton())
        self.add_item(RightButton())
        self.message = None
        self.timeout = 7200
        self.item_list = item_list
        self.page_function = page_function


@bot.slash_command(
    description="Generates random country names",
    force_global=True)
async def random_country_names(
        interaction: Interaction,
        amount: int = SlashOption(
            description="Amount of country names you want",
            min_value=1,
            max_value=100,
            default=10)

):
    await interaction.response.defer()
    nation_name_list = await markov.generate_country_names(amount)
    view = PaginatedView(nation_name_list, nation_name_embed)
    embed = nation_name_embed(nation_name_list, 0)
    sent_message = await interaction.followup.send(embed=embed, view=view)
    view.init_interaction(interaction, sent_message.id)
    view.message = sent_message


@bot.slash_command(
    description="Adds roles to new users",
    force_global=True,
    default_member_permissions=Permissions(manage_roles=True)
)
async def welcome(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The member you want to add roles to"
        ),
        type: str = SlashOption(
            description="What the member signed up as",
            choices=["Country", "Company", "Rebellion", "Spectator"],
            required=True, ),

):
    await interaction.response.defer()
    await interaction.guild.fetch_roles()
    add_role_ids = {
        "Country": [interaction.guild.get_role(793413695567822859)],
        "Company": [interaction.guild.get_role(1071947885035388988)],
        "Rebellion": [interaction.guild.get_role(1038842003024252990)],
        "Spectator": [interaction.guild.get_role(794075195173240863)],
    }
    remove_role_ids = [
        interaction.guild.get_role(793366797306167316),  # Diaspora
        interaction.guild.get_role(794075195173240863),
    ]
    if user.bot:
        await interaction.followup.send(f"You can't add roles to bots.")
    elif any(role in add_role_ids[type] for role in user.roles):
        await interaction.followup.send(f"That guy already has roles.")
    else:
        for role in add_role_ids[type]:
            await user.add_roles(role)
        if not type == "Spectator":
            for role in remove_role_ids:
                await user.remove_roles(role)
        else:
            await user.remove_roles(interaction.guild.get_role(793366797306167316))
        await interaction.followup.send(f"Successfully added roles to user {user.mention}")


@bot.slash_command(
    description="Adds planet info to new users",
    force_global=True,
    default_member_permissions=Permissions(manage_roles=True)
)
async def planet(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The member you want to add roles to"
        ),
        type: str = SlashOption(
            description="Location of the nation. Include colonies but exclude trading posts.",
            choices=["Cheaugy", "Nivalis", "Aethenos"],
            required=True, ),

):
    await interaction.response.defer()
    await interaction.guild.fetch_roles()
    add_role_ids = {
        "Cheaugy": interaction.guild.get_role(1168139509339267072),
        "Nivalis": interaction.guild.get_role(1199302330525421639),
        "Aethenos": interaction.guild.get_role(1168139620861620224),
    }
    if user.bot:
        await interaction.followup.send(f"You can't add roles to bots.")
    elif any(role.id == add_role_ids[type].id for role in user.roles):
        # Check whether the user already has a role.
        await interaction.followup.send(f"That user already has that role.")
    else:
        await user.add_roles(add_role_ids[type])
        await interaction.followup.send(f"Successfully added roles to user {user.mention}")


@game_night.subcommand(
    description="Ban people from game-nights"
)
async def ban(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The bastard who ruined your gamenight"
        ),
):
    await interaction.response.defer()
    await interaction.guild.fetch_roles()
    ban_role = interaction.guild.get_role(1123429247592181831)
    if user.bot:
        await interaction.followup.send(f"You can't ban bots.")
    elif any(ban_role == role for role in user.roles):
        # Check whether the user already is banned.
        await interaction.followup.send(f"That guy is already banned.")
    else:
        await user.add_roles(ban_role)
        await interaction.followup.send(f"Successfully banned user {user.mention} from game-nights.")


@game_night.subcommand(
    description="Unban people from game-nights",
)
async def unban(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The bastard who ruined your gamenight"
        ),
):
    await interaction.response.defer()
    await interaction.guild.fetch_roles()
    ban_role = interaction.guild.get_role(1123429247592181831)
    if any(ban_role == role for role in user.roles):
        # Check whether the user already is banned.
        await user.remove_roles(ban_role)
        await interaction.followup.send(f"Successfully unbanned user {user.mention} from game-nights.")
    else:
        await interaction.followup.send(f"That guy is not banned.")


@bot.slash_command(
    description="Abusing Chairs commands",
    force_global=True)
async def chairs(interaction: Interaction):
    pass


@chairs.subcommand(
    description="Set a new round of Abusing Chairs."
)
async def new_round(
        interaction: Interaction,
        members: str = SlashOption(
            description="List of people who can play in Abusing Chairs",
            required=True)):
    await interaction.response.defer()
    if not interaction.user.id == OWNER_ID and not interaction.user.id == 804771379471712266:
        await interaction.followup.send("You are not the event organiser of Abusing Chairs.")
        return
    else:
        user_ids = re.findall(r'<@(.*?)>', members)
        db = db_client.abusing_chairs
        collection = db.chairs
        await collection.delete_many({})
        chair_members = []
        for member in user_ids:
            chair_members.append({"_id": str(member), "seat": 0})
        await collection.insert_many(chair_members)
        await interaction.followup.send("Successfully set up a new round of Abusing Chairs.")


@chairs.subcommand(
    description="Select a chair in Abusing Chairs"
)
async def select_chair(
        interaction: Interaction,
        seat: int = SlashOption(
            description="The number seat you want to sit in",
            required=True,
            min_value=1)):
    await interaction.response.defer(ephemeral=True)
    db = db_client.abusing_chairs
    collection = db.chairs
    members = []
    async for row in collection.find({}):
        members.append(row["_id"])
    if str(interaction.user.id) in members:
        if seat < len(members):
            await collection.update_one({"_id": str(interaction.user.id)}, {"$set": {"seat": seat}})
            await interaction.followup.send(f"Successfully selected seat {seat}.", ephemeral=True)
        else:
            await interaction.followup.send(f"That seat doesn't exist. There are only {len(members) - 1} seats.",
                                            ephemeral=True)
    else:
        await interaction.followup.send(f"You are not in Abusing Chairs.", ephemeral=True)


@chairs.subcommand(
    description="See what chair you chose. If you're Lankakabei, it shows what everyone chose."
)
async def view_chairs(
        interaction: Interaction,
        format: str = SlashOption(
            description="Put the text in a codeblock or not? Only applies to Lankakabei.",
            choices=["Codeblock", "None"],
            default="None",
            required=False)
):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.id == OWNER_ID and not interaction.user.id == 804771379471712266:
        db = db_client.abusing_chairs
        collection = db.chairs
        selected_chairs = []
        async for chair in collection.find({}):
            selected_chairs.append(chair)
        members = [row["_id"] for row in selected_chairs]
        if str(interaction.user.id) in members:
            for person in selected_chairs:
                if person["_id"] == interaction.user.id:
                    if person["seat"]:
                        await interaction.followup.send(f"Your seat: {person['seat']}")
                    else:
                        await interaction.followup.send(
                            f"You haven't selected a seat yet. There are {len(members) - 1} "
                            f"seats to choose from.")
        else:
            await interaction.followup.send(f"You are not in Abusing Chairs.", ephemeral=True)
        return
    else:
        db = db_client.abusing_chairs
        collection = db.chairs
        if format == "Codeblock":
            chair_message = "```\n"
        else:
            chair_message = ''
        selected_chairs = []
        async for chair in collection.find({}):
            selected_chairs.append(chair)
        for chair in range(1, len(selected_chairs)):
            chair_people = []
            for member in selected_chairs:
                if member["seat"] == chair:
                    chair_people.append(member)
            if len(chair_people) == 0:
                chair_message += f"⬜ Seat {chair}:\n"
            elif len(chair_people) == 1:
                chair_message += f"🟩 Seat {chair}: <@{chair_people[0]['_id']}>\n"
            else:
                chair_message += f"🟥 Seat {chair}: <@{chair_people[0]['_id']}>"
                for person in chair_people[1:]:
                    chair_message += f", <@{person['_id']}>"
                chair_message += "\n"
        if format == "Codeblock":
            chair_message += "```\n"
        unselected = []
        for member in selected_chairs:
            if member["seat"] == 0:
                unselected.append(member)
        if unselected:
            chair_message += f"## Remaining\n"
            for member in unselected:
                chair_message += f"<@{member['_id']}>\n"
        await interaction.followup.send(f"# Seats\n{chair_message}", ephemeral=True)


@bot.slash_command(
    description="Country Brawl commands",
    force_global=True)
async def brawl(interaction: Interaction):
    pass


@brawl.subcommand(
    description="Start a round of Country Brawl"
)
async def new_round(
        interaction: Interaction,
        members: str = SlashOption(
            description="List of people who will play in Country Brawl",
            required=True)):
    await interaction.response.defer()
    if not interaction.user.id == OWNER_ID:
        await interaction.followup.send("You are not the event organiser of Country Brawl.")
        return
    else:
        user_ids = re.findall(r'<@(.*?)>', members)
        db = db_client.country_brawl
        collection = db.members
        await collection.delete_many({})
        members = [{"_id": str(member), "target": None} for member in user_ids]
        await collection.insert_many(members)
        await interaction.followup.send("Successfully set up a new round of Country Brawl.")


@brawl.subcommand(
    description="Select a person to attack in Country Brawl"
)
async def attack(
        interaction: Interaction,
        person: Member = SlashOption(
            description="Your unlucky victim"
        ), ):
    await interaction.response.defer(ephemeral=True)
    db = db_client.country_brawl
    collection = db.members
    members = []
    async for row in collection.find({}):
        members.append(row["_id"])
    if str(interaction.user.id) in members:
        if str(person.id) in members:
            await collection.update_one({"_id": str(interaction.user.id)}, {"$set": {"target": str(person.id)}})
            await interaction.followup.send(f"Successfully targeted {str(person.mention)}.", ephemeral=True)
        else:
            await interaction.followup.send(f"That person is not in Country Brawl", ephemeral=True)
    else:
        await interaction.followup.send(f"You are not in Country Brawl.", ephemeral=True)


@brawl.subcommand(
    description="See who you targeted. If you're Lankakabei, it shows who everyone targeted."
)
async def view_brawl(
        interaction: Interaction,
        format: str = SlashOption(
            description="Put the text in a codeblock or not? Only applies to Lankakabei.",
            choices=["Codeblock", "None"],
            default="None",
            required=False)
):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.id == OWNER_ID:
        db = db_client.country_brawl
        collection = db.members
        user_target = await collection.find_one({"_id": str(interaction.user.id)})
        if user_target is None:
            await interaction.followup.send(f"You are not in Country Brawl.", ephemeral=True)
            return
        if user_target["target"]:
            await interaction.followup.send(f"Your target: <@{user_target['target']}>")
        else:
            user_ids = [user['_id'] async for user in collection.find({})]
            user_string = ""
            for user in user_ids:
                user_string += f"<@{user}>\n"
            await interaction.followup.send(
                f"You haven't selected a target yet. Here is a list of all possible targets:\n\n"
                + user_string)
        return
    else:
        db = db_client.country_brawl
        collection = db.members
        if format == "Codeblock":
            chair_message = "```\n"
        else:
            chair_message = ''
        users = [user async for user in collection.find({})]
        for victim in users:
            attackers = []
            for attacker in users:
                if attacker['target'] == victim['_id']:
                    attackers.append(attacker)
            if len(attackers) == 1:
                chair_message += "💀 "
            else:
                chair_message += "❤️ "
            chair_message += f"<@{victim['_id']}>"
            if len(attackers) > 0:
                chair_message += f" 🗡️ "
                for attacker in attackers:
                    chair_message += f"<@{attacker['_id']}>, "
                chair_message = chair_message[:-2]
            chair_message += "\n"
        unselected = []
        for member in users:
            if member["target"] is None:
                unselected.append(member)
        if unselected:
            chair_message += f"## Hasn't submitted\n"
            for member in unselected:
                chair_message += f"<@{member['_id']}>\n"
        if format == "Codeblock":
            chair_message += "```\n"
        await interaction.followup.send(f"# Results\n{chair_message}", ephemeral=True)


@bot.slash_command(
    description="Lists all members who have a particular role",
    force_global=True,
    default_member_permissions=Permissions(manage_roles=True)
)
async def rolelist(
        interaction: Interaction,
        role: Role = SlashOption(
            description="The role you want to list members for"
        ),
):
    await interaction.response.defer()
    await interaction.guild.fetch_roles()
    msg = ""
    for member in role.members:
        if len(msg) + len(member.mention) < 4095:
            msg += member.mention
            msg += "\n"
        else:
            embed = Embed(title=f"Members with {role.name} role", description=msg,
                          colour=role.colour)
            sent_message = await interaction.followup.send(embed=embed, allowed_mentions=AllowedMentions.none())
            msg = f"{member.mention}\n"
    embed = Embed(title=f"Members with {role.name} role", description=msg,
                  colour=role.colour)
    await interaction.followup.send(embed=embed, allowed_mentions=AllowedMentions.none())


@bot.slash_command(
    description="Times out a member. Allows you to set the time more precisely",
    force_global=True,
    default_member_permissions=Permissions(moderate_members=True)
)
async def timeout(
        interaction: Interaction,
        bad_user: Member = SlashOption(
            description="The person who will get trolled by mods."
        ),
        day: int = SlashOption(
            description="How many days you want to mute them for.",
            min_value=0,
            max_value=28,
            default=0),
        hour: int = SlashOption(
            description="How many hours you want to mute them for.",
            min_value=0,
            max_value=23,
            default=0),
        minute: int = SlashOption(
            description="How many minutes you want to mute them for.",
            min_value=0,
            max_value=59,
            default=0),
        second: int = SlashOption(
            description="I'm not sure why you would need to be this specific tbh.",
            min_value=0,
            max_value=59,
            default=0),
):
    await interaction.response.defer()
    if day or hour or minute or second:
        if interaction.user.top_role > bad_user.top_role:
            if timedelta(days=day, hours=hour, minutes=minute, seconds=second) > timedelta(days=28):
                await interaction.followup.send("Timeout length too long.")
            elif not interaction.guild.me.top_role > bad_user.top_role:
                await interaction.followup.send(
                    "RAC Bot doesn't have the necessary permissions to timeout said member.")
            else:
                await bad_user.timeout(
                    timedelta(days=day, hours=hour, minutes=minute, seconds=second),
                    reason=f"Timed out by user {str(interaction.user)}"
                )
                await interaction.followup.send(f"Successfully timed out {bad_user.mention}")
        else:
            await interaction.followup.send("You can't timeout higher-ranking members.")
    else:
        await interaction.followup.send("You need to input a timeout duration.")


def compare_string_score(test_string, match_string):
    return fuzz.partial_token_sort_ratio(test_string.lower(), match_string.lower())


async def country_search(interaction: Interaction, common_name: str):
    db = db_client.rac_wiki
    collection = db.countries
    countries = []
    async for entry in collection.find({}, ["_id", "alternate_names", "official_name", "owner"]):
        countries.append(entry)
    if not common_name:
        # send the full autocomplete list
        autocomplete_countries = [row["_id"] for row in countries]
        await interaction.response.send_autocomplete(autocomplete_countries[:25])
        return
    # send a list of the nearest matches from the list of countries
    autocomplete_countries = []
    for row in countries:
        country_score = compare_string_score(common_name, row["_id"])
        if row["alternate_names"]:
            for alt_name in row["alternate_names"]:
                if compare_string_score(common_name, alt_name) > country_score:
                    country_score = compare_string_score(common_name, alt_name)
        if row["official_name"]:
            if compare_string_score(common_name, row["official_name"]) > country_score:
                country_score = compare_string_score(common_name, row["official_name"])
        if row["owner"]:
            if compare_string_score(common_name, row["owner"]) == 100:
                country_score = 100
        if country_score > 70:
            autocomplete_countries.append([row["_id"], country_score])
    autocomplete_countries.sort(key=lambda country_scores: country_scores[1], reverse=True)
    autocomplete_countries = [row[0] for row in autocomplete_countries]
    await interaction.response.send_autocomplete(autocomplete_countries[:25])


async def fetch_country_embed(common_name, db_client):
    db = db_client.rac_wiki
    collection = db.countries
    country_dict = await collection.find_one({"_id": common_name})
    if country_dict is None:
        return None
    fields = [
        ("Common name", country_dict["_id"]),
        ("Official name", country_dict["official_name"]),
        ("Alternate names", country_dict["alternate_names"]),
        ("Emoji", country_dict["emoji"]),
        ("Capital", country_dict["capital"]),
        ("Owner", country_dict["owner"]),
        ("Leader", country_dict["leader"]),
        ("Languages", country_dict["language"]),
        ("Unions", country_dict["unions"]),
        ("GDP", country_dict["gdp"]),
        ("Population", country_dict["population"]),
        ("Founding date", country_dict["founding_date"]),
        ("End date", country_dict["end_date"])
    ]
    if country_dict["colour"]:
        colour = Colour(int(country_dict["colour"][1:], 16))
    else:
        colour = None
    country_embed = Embed(title=common_name, colour=colour, description=country_dict["description"])
    if country_dict["flag_url"] and not country_dict["flag_url"] == "None":
        country_embed.set_image(country_dict["flag_url"])
    for field in fields:
        if field[1] or field[1] == 0:
            if field[0] == "GDP":
                gdp = format_large_number(field[1])
                country_embed = country_embed.add_field(name=field[0], value=f"${gdp} cellen")
            elif field[0] == "Population":
                population = format_large_number(field[1])
                country_embed = country_embed.add_field(name=field[0], value=population)
            elif field[0] == "Alternate names" and not field[1] == "None":
                alternate_name_text = ""
                for name in field[1]:
                    alternate_name_text += ", " + name
                country_embed = country_embed.add_field(name=field[0], value=alternate_name_text[2:])
            else:
                country_embed = country_embed.add_field(name=field[0], value=field[1])
    if country_dict["map_url"] and not country_dict["map_url"] == "None":
        country_embed = [country_embed, Embed(title="Map", colour=colour).set_image(country_dict["map_url"])]
    return country_embed


@country.subcommand(
    description="Add a country into the database.",
)
async def add(
        interaction: Interaction,
        common_name: str = SlashOption(
            description="The common name for the nation.",
            required=True
        ),
        official_name: str = SlashOption(
            description="The official name for the nation.",
            default=None,
            required=False
        ),
        alternate_names: str = SlashOption(
            description="Other names used for this nation. Separate names with commas.",
            default=None,
            required=False
        ),
        emoji: str = SlashOption(
            description="The flag emoji of the nation.",
            default=None,
            required=False
        ),
        capital: str = SlashOption(
            description="The capital of the nation.",
            default=None,
            required=False
        ),
        owner: str = SlashOption(
            description="The owner(s) of the nation.",
            default=None,
            required=False
        ),
        leader: str = SlashOption(
            description="The leader of the nation IRP.",
            default=None,
            required=False
        ),
        language: str = SlashOption(
            description="The official language(s) of the nation.",
            default=None,
            required=False
        ),
        unions: str = SlashOption(
            description="The union(s) the nation is in.",
            default=None,
            required=False
        ),
        gdp: int = SlashOption(
            description="The GDP of the nation.",
            default=None,
            required=False
        ),
        population: int = SlashOption(
            description="The population of the nation.",
            default=None,
            required=False
        ),
        founding_date: str = SlashOption(
            description="The RAC date the nation was founded on.",
            default=None,
            required=False
        ),
        end_date: str = SlashOption(
            description="The RAC date the nation ended on. If the nation still exists, leave blank.",
            default=None,
            required=False
        ),
        description: str = SlashOption(
            description="Describe what the nation is like to a newbie. (Multiple) message links work!",
            default=None,
            required=False
        ),
        colour: str = SlashOption(
            description="The hex code of the nation's colour. Used for colouring embeds.",
            default=None,
            required=False
        ),
        flag: Attachment = SlashOption(
            description="The flag of the nation.",
            default=None,
            required=False
        ),
        map_image: Attachment = SlashOption(
            description="A map of the nation.",
            default=None,
            required=False
        ),
):
    await interaction.response.defer()
    new_description = ""
    if description:
        for message_check in description.split():
            try:
                link_message = await get_message_from_link(message_check)
                new_description += link_message.content + "\n\n"
            except ValueError:
                new_description += message_check
                new_description += " "
    db = db_client.rac_wiki
    collection = db.countries
    existing_country = await collection.count_documents({"_id": common_name})
    if existing_country == 1:
        await interaction.followup.send(f"There already exists a country with the same common name {common_name}.\n\n"
                                        f"To edit a country, use the ``/country edit`` command.")
        return
    if flag:
        flag = await upload_image(str(flag))
    if map_image:
        map_image = await upload_image(str(map_image))
    if colour:
        try:
            Colour(int(colour, 16))
            colour = "#" + colour
        except ValueError:
            try:
                Colour(int(colour[1:], 16))
            except ValueError:
                colour = None
                await interaction.followup.send(f"Invalid value for colour.")
    if alternate_names:
        alternate_names = alternate_names.split(",")
        new_alternate_names = []
        for name in alternate_names:
            new_alternate_names.append(name.strip())
        alternate_names = new_alternate_names
    await collection.insert_one(
        {
            "_id": common_name,
            "official_name": official_name,
            "alternate_names": alternate_names,
            "emoji": emoji,
            "capital": capital,
            "owner": owner,
            "leader": leader,
            "language": language,
            "unions": unions,
            "gdp": gdp,
            "population": population,
            "founding_date": founding_date,
            "end_date": end_date,
            "description": new_description,
            "colour": colour,
            "flag_url": flag,
            "map_url": map_image,
        }
    )
    country_embed = await fetch_country_embed(common_name, db_client)
    if country_embed is None:
        await interaction.followup.send(f"Failed to add country to database.")
        return
    if type(country_embed) == list:
        await interaction.followup.send(f"Successfully added country {common_name}", embeds=country_embed,
                                        allowed_mentions=AllowedMentions.none())
    else:
        await interaction.followup.send(f"Successfully added country {common_name}", embed=country_embed,
                                        allowed_mentions=AllowedMentions.none())


@country.subcommand(
    description="Edit a country's entry in the database. Use the emoji ❌ to delete an attribute.",
)
async def edit(
        interaction: Interaction,
        common_name: str = SlashOption(
            description="The common name of the nation you want to edit.",
            required=True,
            autocomplete_callback=country_search
        ),
        new_common_name: str = SlashOption(
            description="The new common name of the nation you want to edit, if needed. Cannot be deleted.",
            default=None,
            required=False
        ),
        official_name: str = SlashOption(
            description="The official name for the nation.",
            default=None,
            required=False
        ),
        alternate_names: str = SlashOption(
            description="Other names used for this nation. Separate names with commas.",
            default=None,
            required=False
        ),
        emoji: str = SlashOption(
            description="The flag emoji of the nation.",
            default=None,
            required=False
        ),
        capital: str = SlashOption(
            description="The capital of the nation.",
            default=None,
            required=False
        ),
        owner: str = SlashOption(
            description="The owner(s) of the nation.",
            default=None,
            required=False
        ),
        leader: str = SlashOption(
            description="The leader of the nation IRP.",
            default=None,
            required=False
        ),
        language: str = SlashOption(
            description="The official language(s) of the nation.",
            default=None,
            required=False
        ),
        unions: str = SlashOption(
            description="The union(s) the nation is in.",
            default=None,
            required=False
        ),
        gdp: int = SlashOption(
            description="The GDP of the nation.",
            default=None,
            required=False
        ),
        population: int = SlashOption(
            description="The population of the nation.",
            default=None,
            required=False
        ),
        founding_date: str = SlashOption(
            description="The RAC date the nation was founded on.",
            default=None,
            required=False
        ),
        end_date: str = SlashOption(
            description="The RAC date the nation ended on. If the nation still exists, leave blank.",
            default=None,
            required=False
        ),
        description: str = SlashOption(
            description="Describe what the nation is like to a newbie. (Multiple) message links work!",
            default=None,
            required=False
        ),
        colour: str = SlashOption(
            description="The hex code of the nation's colour. Used for colouring embeds.",
            default=None,
            required=False
        ),
        flag: Attachment = SlashOption(
            description="The flag of the nation.",
            default=None,
            required=False
        ),
        map_image: Attachment = SlashOption(
            description="A map of the nation.",
            default=None,
            required=False
        ),
):
    await interaction.response.defer()
    new_description = ""
    if description:
        for message_check in description.split():
            try:
                link_message = await get_message_from_link(message_check)
                new_description += link_message.content + "\n\n"
            except ValueError:
                new_description += message_check
                new_description += " "
    description = new_description
    db = db_client.rac_wiki
    collection = db.countries
    existing_country = await collection.count_documents({"_id": common_name})
    if existing_country == 0:
        await interaction.followup.send(f"Could not find country {common_name}. "
                                        f"Use ``/country add`` to add this country into the database.")
        return
    if alternate_names and not alternate_names == "❌":
        alternate_names = alternate_names.split(",")
        new_alternate_names = []
        for name in alternate_names:
            new_alternate_names.append(name.strip())
    if colour:
        try:
            Colour(int(colour, 16))
            colour = "#" + colour
        except ValueError:
            try:
                Colour(int(colour[1:], 16))
            except ValueError:
                colour = None
                await interaction.followup.send(f"Invalid value for colour.")
    if not flag:
        flag = ""
    if not map_image:
        map_image = ""
    if flag:
        flag = await upload_image(str(flag))
    if map_image:
        map_image = await upload_image(str(map_image))
    fields = (
        (official_name, "official_name"),
        (alternate_names, "alternate_names"),
        (emoji, "emoji"),
        (capital, "capital"),
        (owner, "owner"),
        (leader, "leader"),
        (language, "language"),
        (unions, "unions"),
        (gdp, "gdp"),
        (population, "population"),
        (founding_date, "founding_date"),
        (end_date, "end_date"),
        (description, "description"),
        (colour, "colour"),
        (flag, "flag_url"),
        (map_image, "map_url"),
    )
    updates = {}
    for field in fields:
        if field[0] or field[0] == 0 and not field[0] == "None":
            if field[0] == "❌" and not field[1] == "_id":
                updates[field[1]] = None
            else:
                updates[field[1]] = field[0]
    if new_common_name:
        original_country = await collection.find_one({"_id": common_name})
        original_country["_id"] = new_common_name
        await collection.insert_one(original_country)
        await collection.update_one({"_id": new_common_name}, {"$set": updates})
        await collection.delete_one({"_id": common_name})
        country_embed = await fetch_country_embed(new_common_name, db_client)
    else:
        await collection.update_one({"_id": common_name}, {"$set": updates})
        country_embed = await fetch_country_embed(common_name, db_client)
    if country_embed is None:
        await interaction.followup.send(f"Could not find country {common_name}. "
                                        f"Use ``/country add`` to add this country into the database.")
        return
    if type(country_embed) == list:
        await interaction.followup.send(f"Successfully updated info for country {common_name}", embeds=country_embed,
                                        allowed_mentions=AllowedMentions.none())
    else:
        await interaction.followup.send(f"Successfully updated info for country {common_name}", embed=country_embed,
                                        allowed_mentions=AllowedMentions.none())


@country.subcommand(
    description="See a country's entry in the database.",
)
async def view(
        interaction: Interaction,
        common_name: str = SlashOption(
            description="The common name of the nation you want to view.",
            required=True,
            autocomplete_callback=country_search
        ),
):
    await interaction.response.defer()
    country_embed = await fetch_country_embed(common_name, db_client)
    if country_embed is None:
        await interaction.followup.send(f"Could not find country {common_name}. "
                                        f"Use ``/country add`` to add this country into the database.")
        return
    if type(country_embed) == list:
        await interaction.followup.send(embeds=country_embed, allowed_mentions=AllowedMentions.none())
    else:
        await interaction.followup.send(embed=country_embed, allowed_mentions=AllowedMentions.none())


def format_bank_history(history: list[dict], currency: str = None):
    if currency is None:
        currency = "cells"
    history_text = ""
    for entry in history:
        if entry['change'] > 0:
            history_text += f"## +{entry['change']} {currency}\n" \
                            f"Change: {entry['new_balance'] - entry['change']} {currency} " \
                            f"-> {entry['new_balance']} {currency}\n" \
                            f"User: <@{entry['user_id']}>\n" \
                            f"Time: <t:{entry['time']}:R>\n" \
                            f"Reason: {entry['reason']}\n"
        else:
            history_text += f"## {entry['change']} cells\n" \
                            f"Change: {entry['new_balance'] - entry['change']} {currency} " \
                            f"-> {entry['new_balance']} {currency}\n" \
                            f"User: <@{entry['user_id']}>\n" \
                            f"Time: <t:{entry['time']}:R>\n" \
                            f"Reason: {entry['reason']}\n"
    return history_text


def format_history_embed(view: View):
    currency = "cells" if view.currency is None else view.currency
    history_text = format_bank_history(view.history[view.index], currency)
    history_embed = Embed(
        title=f"{currency[:-1].capitalize()} Bank History",
        description=history_text,
        colour=view.bank_owner.colour
    ).set_footer(text=f"{view.index + 1}/{len(view.history)}")
    user_avatar = None if view.bank_owner.avatar is None else view.bank_owner.avatar.url
    if view.bank_owner.discriminator == "0":
        history_embed = history_embed.set_author(name=view.bank_owner.name, icon_url=user_avatar)
    else:
        history_embed = history_embed.set_author(name=f"{view.bank_owner.name}#{view.bank_owner.discriminator}",
                                                 icon_url=user_avatar)
    return history_embed


def format_balance_embed(view: View):
    currency = "cells" if view.currency is None else view.currency
    balance_embed = Embed(
        title=f"{currency[:-1].capitalize()} Bank Balance",
        description=f"{view.balance} {currency}",
        colour=view.bank_owner.colour
    )
    user_avatar = None if view.bank_owner.avatar is None else view.bank_owner.avatar.url
    if view.bank_owner.discriminator == "0":
        balance_embed = balance_embed.set_author(name=view.bank_owner.name, icon_url=user_avatar)
    else:
        balance_embed = balance_embed.set_author(name=f"{view.bank_owner.name}#{view.bank_owner.discriminator}",
                                                 icon_url=user_avatar)
    return balance_embed


class HistoryLeftButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Previous", row=1)

    async def callback(self, interaction: Interaction):
        if self.view.index != 0:
            self.view.index -= 1
        else:
            self.view.index = len(self.view.history) - 1
        embed = format_history_embed(self.view)
        await interaction.response.edit_message(embed=embed)


class HistoryRightButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Next", row=1)

    async def callback(self, interaction: Interaction):
        if len(self.view.history) - 1 == self.view.index:
            self.view.index = 0
        else:
            self.view.index = self.view.index + 1
        embed = format_history_embed(self.view)
        await interaction.response.edit_message(embed=embed)


class HistoryToBalanceButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.grey, label="View Balance", row=2, emoji="💵")

    async def callback(self, interaction: Interaction):
        balance_view = BankBalanceViewer(self.view.index, self.view.balance, self.view.history, self.view.bank_owner)
        balance_embed = format_balance_embed(self.view)
        await interaction.response.edit_message(embed=balance_embed, view=balance_view)
        balance_view.init_interaction(interaction)


class BalanceToHistoryButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="View History", row=1, emoji="📜")

    async def callback(self, interaction: Interaction):
        history_view = BankHistoryViewer(self.view.index, self.view.balance, self.view.history, self.view.bank_owner,
                                         self.view.currency)
        history_embed = format_history_embed(self.view)
        await interaction.response.edit_message(embed=history_embed, view=history_view)
        history_view.init_interaction(interaction)


class BankHistoryViewer(AutoDisableView):
    def __init__(self, index, balance, history, bank_owner: Member, currency: str = None):
        super().__init__()
        self.index = index
        self.add_item(HistoryLeftButton())
        self.add_item(HistoryRightButton())
        self.add_item(HistoryToBalanceButton())
        self.message = None
        self.timeout = 3600
        self.balance = balance
        self.history = history
        self.bank_owner = bank_owner
        self.currency = currency


class BankBalanceViewer(AutoDisableView):
    def __init__(self, index, balance, history, bank_owner: Member, currency: str = None):
        super().__init__()
        self.index = index
        self.add_item(BalanceToHistoryButton())
        self.message = None
        self.timeout = 3600
        self.balance = balance
        self.history = history
        self.bank_owner = bank_owner
        self.currency = currency


def paginate_list(array: list, entries_per_page: int = None):
    if entries_per_page is None:
        entries_per_page = 10
    ten_array = []
    newer_array = []
    for entry in array:
        ten_array.append(entry)
        if len(ten_array) == entries_per_page:
            newer_array.append(ten_array)
            ten_array = []
    if ten_array:
        newer_array.append(ten_array)
    return newer_array


@cells.subcommand(
    description="Set up your cell bank.",
)
async def bank_setup(
        interaction: Interaction,
        cells: int = SlashOption(
            description="The number of cells you have.",
            required=True,
            min_value=0,
        ),
):
    await interaction.response.defer()
    db = db_client.cells
    collection = db.balance
    existing_bank = await collection.count_documents({"_id": str(interaction.user.id)})
    if existing_bank == 1:
        await interaction.followup.send(f"You already have set up your cell bank.\n\n"
                                        f"To edit your cell bank, "
                                        f"use the {add.get_mention(guild=None)} or the {remove.get_mention(guild=None)}"
                                        f" command.\n"
                                        f"To view your cell bank, use the {view.get_mention(guild=None)} command.")
        return
    cell_bank_setup = {
        "_id": str(interaction.user.id),
        "balance": cells,
        "history": [
            {
                "time": int(datetime.now().timestamp()),
                "change": cells,
                "new_balance": cells,
                "user_id": str(interaction.user.id),
                "reason": f"Set up cell bank with initial balance of {cells} cells"
            },
        ],
    }
    await collection.insert_one(cell_bank_setup)
    bank = await collection.find_one({"_id": str(interaction.user.id)})
    bank["history"].sort(key=lambda x: x["time"], reverse=True)
    history = paginate_list(bank["history"])
    balance_view = BankBalanceViewer(0, bank["balance"], history, interaction.user)
    balance_embed = format_balance_embed(balance_view)
    msg = await interaction.followup.send(
        content=f"Successfully set up cell bank for {interaction.user.mention}",
        embed=balance_embed,
        view=balance_view
    )
    balance_view.init_interaction(interaction, msg.id)


@cells.subcommand(
    description="View a cell bank.",
)
async def view(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The person whose cell bank you want to view.",
            required=False,
            default=None
        ),
):
    await interaction.response.defer()
    if user is None:
        user = interaction.user
    db = db_client.cells
    collection = db.balance
    existing_bank = await collection.find_one({"_id": str(user.id)})
    if existing_bank is None:
        await interaction.followup.send(f"{user.mention} has not set up their cell bank yet.\n\n"
                                        f"To set up a cell bank, use the {bank_setup.get_mention(guild=None)} command.")
        return
    existing_bank["history"].sort(key=lambda x: x["time"], reverse=True)
    history = paginate_list(existing_bank["history"])
    balance_view = BankBalanceViewer(0, existing_bank["balance"], history, user)
    balance_embed = format_balance_embed(balance_view)
    msg = await interaction.followup.send(
        embed=balance_embed,
        view=balance_view
    )
    balance_view.init_interaction(interaction, msg.id)


@cells.subcommand(
    description="Add cells to a cell bank.",
)
async def add(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The person you want to add cells to.",
            required=True,
        ),
        cells: int = SlashOption(
            description="The number of cells you want to add.",
            required=True,
            min_value=1,
        ),
        reason: str = SlashOption(
            description="Why you added these cells.",
            required=True,
        ),
):
    await interaction.response.defer()
    db = db_client.cells
    collection = db.balance
    bank = await collection.find_one({"_id": str(user.id)})
    if bank is None:
        cell_bank_setup = {
            "_id": str(user.id),
            "balance": cells,
            "history": [
                {
                    "time": int(datetime.now().timestamp()),
                    "change": cells,
                    "new_balance": cells,
                    "user_id": str(interaction.user.id),
                    "reason": f"Set up cell bank with initial balance of {cells} cells. (Created via /add command)"
                },
            ],
        }
        await collection.insert_one(cell_bank_setup)
        bank = await collection.find_one({"_id": str(user.id)})
        bank["history"].sort(key=lambda x: x["time"], reverse=True)
        history = paginate_list(bank["history"])
        balance_view = BankBalanceViewer(0, bank["balance"], history, user)
        balance_embed = format_balance_embed(balance_view)
        msg = await interaction.followup.send(
            content=f"Created new cell bank. Successfully added {cells} cells to {user.mention}'s cell bank.",
            embed=balance_embed,
            view=balance_view
        )
        balance_view.init_interaction(interaction, msg.id)
        return
    else:
        balance = bank["balance"]
    history_entry = {
        "time": int(datetime.now().timestamp()),
        "change": cells,
        "new_balance": balance + cells,
        "user_id": str(interaction.user.id),
        "reason": reason
    }
    bank["history"].append(history_entry)
    updates = {
        "balance": balance + cells,
        "history": bank["history"],
    }
    await collection.update_one({"_id": str(user.id)}, {"$set": updates})
    existing_bank = await collection.find_one({"_id": str(user.id)})
    existing_bank["history"].sort(key=lambda x: x["time"], reverse=True)
    history = paginate_list(existing_bank["history"])
    balance_view = BankBalanceViewer(0, existing_bank["balance"], history, user)
    balance_embed = format_balance_embed(balance_view)
    msg = await interaction.followup.send(
        content=f"Successfully added {cells} cells to {user.mention}'s cell bank",
        embed=balance_embed,
        view=balance_view,
        allowed_mentions=AllowedMentions(everyone=False, roles=False, users=[user]),
    )
    balance_view.init_interaction(interaction, msg.id)


@cells.subcommand(
    description="Remove cells from a cell bank.",
)
async def remove(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The person you want to remove cells from.",
            required=True,
        ),
        cells: int = SlashOption(
            description="The number of cells you want to remove.",
            required=True,
            min_value=1,
        ),
        reason: str = SlashOption(
            description="Why you removed these cells.",
            required=True,
        ),
):
    await interaction.response.defer()
    db = db_client.cells
    collection = db.balance
    bank = await collection.find_one({"_id": str(user.id)})
    if bank is None:
        await interaction.followup.send(f"{user.mention} has not set up their cell bank yet.\n\n"
                                        f"To set up a cell bank, use the {bank_setup.get_mention(guild=None)} command.")
        return
    balance = bank["balance"]
    if balance - cells < 0:
        await interaction.followup.send(f"That would put {user.mention} into debt. They only have {balance} cells.")
        return
    history_entry = {
        "time": int(datetime.now().timestamp()),
        "change": -cells,
        "new_balance": balance - cells,
        "user_id": str(interaction.user.id),
        "reason": reason
    }
    bank["history"].append(history_entry)
    updates = {
        "balance": balance - cells,
        "history": bank["history"],
    }
    await collection.update_one({"_id": str(user.id)}, {"$set": updates})
    existing_bank = await collection.find_one({"_id": str(user.id)})
    existing_bank["history"].sort(key=lambda x: x["time"], reverse=True)
    history = paginate_list(existing_bank["history"])
    balance_view = BankBalanceViewer(0, existing_bank["balance"], history, user)
    balance_embed = format_balance_embed(balance_view)
    msg = await interaction.followup.send(
        content=f"Successfully removed {cells} cells from {user.mention}'s cell bank",
        embed=balance_embed,
        view=balance_view,
        allowed_mentions=AllowedMentions(everyone=False, roles=False, users=[user]),
    )
    balance_view.init_interaction(interaction, msg.id)


@cells.subcommand(
    description="Transfer cells to another person's cell bank.",
)
async def transfer(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The person you want to send cells to.",
            required=True,
        ),
        cells: int = SlashOption(
            description="The number of cells you want to send.",
            required=True,
            min_value=1,
        ),
        reason: str = SlashOption(
            description="Why you sent these cells.",
            required=True,
        ),
):
    await interaction.response.defer()
    if user.id == interaction.user.id:
        await interaction.followup.send("You can't transfer cells to yourself!")
        return
    db = db_client.cells
    collection = db.balance
    send_bank = await collection.find_one({"_id": str(interaction.user.id)})
    receive_bank = await collection.find_one({"_id": str(user.id)})
    if send_bank is None:
        await interaction.followup.send(f"You have not set up your cell bank yet.\n\n"
                                        f"To set up a cell bank, use the {bank_setup.get_mention(guild=None)} command.")
        return
    if receive_bank is None:
        await interaction.followup.send(f"{user.mention} has not set up their cell bank yet.\n\n"
                                        f"To set up a cell bank, use the {bank_setup.get_mention(guild=None)} command.")
        return
    transaction_time = int(datetime.now().timestamp())
    send_balance = send_bank["balance"]
    if send_balance - cells < 0:
        await interaction.followup.send(f"You can't just go into debt. You only have {send_balance} cells.")
        return
    send_history_entry = {
        "time": transaction_time,
        "change": -cells,
        "new_balance": send_balance - cells,
        "user_id": str(interaction.user.id),
        "reason": f"Transaction of {cells} cells to {user.mention}\n\nReason: " + reason
    }
    send_bank["history"].append(send_history_entry)
    send_updates = {
        "balance": send_balance - cells,
        "history": send_bank["history"],
    }
    receive_balance = receive_bank["balance"]
    receive_history_entry = {
        "time": transaction_time,
        "change": cells,
        "new_balance": receive_balance + cells,
        "user_id": str(interaction.user.id),
        "reason": f"Transaction of {cells} cells from {interaction.user.mention}\n\nReason: " + reason
    }
    receive_bank["history"].append(receive_history_entry)
    receive_updates = {
        "balance": receive_balance + cells,
        "history": receive_bank["history"],
    }
    await collection.update_one({"_id": str(user.id)}, {"$set": receive_updates})
    await collection.update_one({"_id": str(interaction.user.id)}, {"$set": send_updates})
    existing_bank = await collection.find_one({"_id": str(user.id)})
    existing_bank["history"].sort(key=lambda x: x["time"], reverse=True)
    history = paginate_list(existing_bank["history"])
    balance_view = BankBalanceViewer(0, existing_bank["balance"], history, user)
    balance_embed = format_balance_embed(balance_view)
    msg = await interaction.followup.send(
        content=f"Successfully transferred {cells} cells to {user.mention}'s cell bank. You now have {send_balance - cells} cells.",
        embed=balance_embed,
        view=balance_view,
        allowed_mentions=AllowedMentions(everyone=False, roles=False, users=[user]),
    )
    balance_view.init_interaction(interaction, msg.id)


def format_date(date: datetime):
    if date.day % 10 == 1 and date.day != 11:
        return date.strftime("%b. %-dst, %Y")
    elif date.day % 10 == 2 and date.day != 12:
        return date.strftime("%b. %-dnd, %Y")
    elif date.day % 10 == 3 and date.day != 13:
        return date.strftime("%b. %-drd, %Y")
    else:
        return date.strftime("%b. %-dth, %Y")


async def update_time_channel():
    while True:
        loop = asyncio.get_event_loop()
        rac_time = await loop.run_in_executor(None, functools.partial(get_rac_time))
        new_date = await loop.run_in_executor(None, functools.partial(format_date, date=rac_time))
        db = db_client.settings
        collection = db.settings
        time_channel_id = await collection.find_one({"_id": "rac_time_channel"})
        enabled_list = await collection.find_one({"_id": "rac_time_autoupdate"})
        print(enabled_list)
        for server_id in enabled_list["value"]:
            server = bot.get_guild(int(server_id))
            time_channel = server.get_channel(time_channel_id["value"][server_id])
            if enabled_list["value"][server_id] and time_channel:
                await time_channel.edit(name=new_date)
        next_rac_day = datetime(year=rac_time.year, month=rac_time.month, day=rac_time.day, tzinfo=timezone.utc)
        next_rac_day += timedelta(days=1)
        irl_next_day = await loop.run_in_executor(None, functools.partial(get_irl_time, rac_time=next_rac_day))
        wait_time = 2 * 60 * 60
        await asyncio.sleep(wait_time + 10)


@bot.event
async def on_ready():
    # announcements = await bot.fetch_channel(815665892498866207)
    # await announcements.send("FYI, you will be timeout for 1 hour automatically if you say the R word or any of its derivatives. \nYou can try it yourself if you don't believe me.", reference=announcements.get_partial_message(1205670816486924378))
    await update_time_channel()


@time.subcommand(
    description="Enable/disable RAC bot auto-updating the RAC time in a voice channel."
)
async def auto_update(
        interaction: Interaction,
        setting: str = SlashOption(
            description="Enable or disable RAC Bot to show the current time in a channel?",
            choices=["Enable", "Disable"],
            default="None",
            required=True,
        ),

):
    await interaction.response.defer()
    if interaction.user.guild_permissions.manage_guild:
        db = db_client.settings
        collection = db.settings
        setting = {"Enable": True, "Disable": False}[setting]
        await collection.update_one({"_id": "rac_time_autoupdate"},
                                    {"$set": {f"value.{interaction.guild_id}": setting}})
        if setting:
            await interaction.followup.send("Successfully enabled auto-updating time.")
        else:
            await interaction.followup.send("Successfully disabled auto-updating time.")
    else:
        await interaction.followup.send("Excuse me, only the *right* people can change this setting.")


@time.subcommand(
    description="If RAC bot is not updating the time, try this."
)
async def fix_channel(
        interaction: Interaction,
):
    await interaction.response.defer()
    await interaction.followup.send(
        "Started to update time channel. It should be working in a minute. If not, contact Lankakabei.")
    await update_time_channel()


async def fetch_inspirobot(xmas: bool = None):
    if xmas is None:
        xmas = False
    api_url = "https://inspirobot.me/api"
    session = aiohttp.ClientSession()
    async with session:
        if xmas:
            inspirobot_image = await session.get(api_url, params={"generate": "true", "season": "xmas"})
        else:
            inspirobot_image = await session.get(api_url, params={"generate": "true", })
    inspirobot_image = await inspirobot_image.text()
    logging.info(inspirobot_image)
    return inspirobot_image


def inspirobot_embed(quote_list, index):
    return Embed(title="Here's your new inspirational quote!", colour=Colour.from_rgb(93, 188, 58)) \
        .set_image(quote_list[index]) \
        .set_footer(text=f"{index + 1}/{len(quote_list)}")


class InspirobotLeftButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Previous", row=1)

    async def callback(self, interaction: Interaction):
        index = self.view.index
        if self.view.index != 0:
            self.view.index = index - 1
        else:
            self.view.index = len(self.view.inspirobot_list) - 1
        embed = inspirobot_embed(self.view.inspirobot_list, self.view.index)
        await interaction.response.edit_message(embed=embed)


class InspirobotSaveButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.grey, label="Save", row=2, emoji="💾")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        embed = inspirobot_embed(self.view.inspirobot_list, self.view.index)
        await interaction.followup.send(embed=embed)


class InspirobotRightButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Next", row=1)

    async def callback(self, interaction: Interaction):
        index = self.view.index
        if index + 1 == len(self.view.inspirobot_list):
            self.view.inspirobot_list.append(await fetch_inspirobot(self.view.xmas))
        self.view.index = index + 1
        embed = inspirobot_embed(self.view.inspirobot_list, self.view.index)
        await interaction.response.edit_message(embed=embed)


class InspirobotJumpInput(TextInput):
    def __init__(self, max_len: int):
        super().__init__(label="Jump", max_length=max_len, min_length=1,
                         placeholder="The page number you want to jump to", required=True)


class InspirobotJumpModal(Modal):
    def __init__(self, inspirobot_list: list, index: int):
        super().__init__(title="Jump", timeout=600)
        self.inspirobot_list = inspirobot_list
        self.index = index
        self.add_item(JumpInput(len(str(index))))

    async def callback(self, interaction: Interaction):
        try:
            page = int(self.children[0].value) - 1
        except ValueError:
            embed = inspirobot_embed(self.inspirobot_list, self.index)
            await interaction.response.edit_message(embed=embed)
            return
        if page < 0:
            page = 0
        if page < len(self.inspirobot_list):
            self.index = page
        embed = inspirobot_embed(self.inspirobot_list, self.index)
        await interaction.response.edit_message(embed=embed)
        return


class InspirobotJumpButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.grey, label="Jump", row=1, emoji="⏩")

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(InspirobotJumpModal(self.view.inspirobot_list, self.view.index))


class InspirobotPreview(AutoDisableView):
    def __init__(self, inspirobot_list, xmas):
        super().__init__()
        self.index = 0
        self.add_item(InspirobotLeftButton())
        self.add_item(InspirobotJumpButton())
        self.add_item(InspirobotSaveButton())
        self.add_item(InspirobotRightButton())
        self.message = None
        self.timeout = 3600
        self.inspirobot_list = inspirobot_list
        self.xmas = xmas


@bot.slash_command(description="Get inspiring quotes from Inspirobot")
async def inspirobot(
        interaction: Interaction,
        xmas: str = SlashOption(
            description="Enable or disable Inspirobot's Xmas mode",
            choices=["Xmas", "Normal"],
            default="Normal",
            required=False,
        ),
):
    await interaction.response.defer()
    xmas = {"Xmas": True, "Normal": False}[xmas]
    inspirobot_quote = await fetch_inspirobot(xmas)
    message_view = InspirobotPreview([inspirobot_quote], xmas)
    embed = inspirobot_embed(message_view.inspirobot_list, 0)
    sent_message = await interaction.followup.send(embed=embed, view=message_view)
    message_view.message = sent_message
    message_view.init_interaction(interaction, sent_message.id)


def crop_image(image_path, mask_path, output_path, fit_mask_ratio=None, crop_area=None):
    # Open the image and mask
    image = Image.open(image_path).convert("RGBA")
    mask = Image.open(mask_path).convert("RGBA")  # Open mask with alpha channel

    centering_dict = {
        'centre': (0.5, 0.5),
        'left': (0.0, 0.0),
        'right': (1.0, 1.0),
    }

    if fit_mask_ratio is True:
        if crop_area:
            resized_image = ImageOps.fit(image, mask.size, centering=centering_dict[crop_area])
        else:
            # Resize the image to match the mask
            resized_image = image.resize(mask.size)
    else:
        # Resize the mask to fit the image's proportions, shrink image
        resized_image = image.resize((int(image.width * mask.height / image.height), mask.height))
        mask = mask.resize(resized_image.size)

    # Create a new image with RGBA mode
    cropped_image = Image.new("RGBA", resized_image.size)

    # Composite the resized image and the mask
    cropped_image = Image.composite(resized_image, cropped_image, mask)

    # Save the final cropped image as PNG
    cropped_image.save(output_path, "PNG")


@bot.slash_command(description="Crop regular flags into Discord emoji flags")
async def crop_flag(
        interaction: Interaction,
        flag: Attachment = SlashOption(
            description="The flag image",
            required=True
        ),
        file_name: str = SlashOption(
            description="The new file name of the flag",
            default="cropped_flag.png",
            required=False,
        ),
        ratio_proportion: str = SlashOption(
            description="Shrink flag to default ratio or keep ratio?",
            choices=("Use default ratio", "Keep ratio"),
            default="Use default ratio",
            required=False,
        ),
        crop_area: str = SlashOption(
            description="Should flag be shrinked or cropped, and which part should be kept?",
            choices=("Shrink", "Crop centre", "Crop left", "Crop right"),
            default="Shrink",
            required=False,
        ),
):
    await interaction.response.defer()
    if "image" not in flag.content_type:
        await interaction.followup.send("That's not an image. Please send images only.")
        return
    await flag.save(f"flag_{interaction.id}")
    if ratio_proportion == "Use default ratio":
        crop_area_dict = {
            "Shrink": False,
            "Crop centre": "centre",
            "Crop left": "left",
            "Crop right": "right",
        }
        if crop_area:
            crop_image(f"flag_{interaction.id}", "flag_cropping_mask.png", f"cropped_{interaction.id}.png", True,
                       crop_area_dict[crop_area])
        else:
            crop_image(f"flag_{interaction.id}", "flag_cropping_mask.png", f"cropped_{interaction.id}.png", True)
    else:
        crop_image(f"flag_{interaction.id}", "flag_cropping_mask.png", f"cropped_{interaction.id}.png", False)
    new_attachment = File(f"cropped_{interaction.id}.png", file_name)
    await interaction.followup.send(f"Here's your cropped flag!", file=new_attachment)
    os.remove(f"cropped_{interaction.id}.png")
    os.remove(f"flag_{interaction.id}")


def format_time_bank_history(history: list[dict]):
    print(history)
    history_text = ""
    for entry in history:
        print(entry)
        history_text += f"## +{entry['seconds']} seconds\n" \
                        f"Change: {entry['new_balance'] - entry['seconds']} seconds " \
                        f"-> {entry['new_balance']} seconds\n" \
                        f"User: <@{entry['user']}>\n" \
                        f"Time: <t:{entry['collect_time']}:R>\n"
    return history_text


async def collect_time(interaction: Interaction):
    await interaction.response.defer()
    collect_time = datetime.now(tz=timezone.utc)
    db = db_client.time_is_money
    setting_collection = db.game
    user_id = str(interaction.user.id)
    signups_open = await setting_collection.find_one({"_id": "signups_open"})
    end_date = await setting_collection.find_one({"_id": "end_date"})
    try:
        if signups_open["value"] is False and collect_time < datetime.fromtimestamp(end_date["value"], tz=timezone.utc):
            member_collection = db.member
            members = member_collection.find({})
            members = {d['_id']: {k: v for k, v in d.items() if k != '_id'} async for d in members}
            if user_id in members.keys():
                last_collect_time = await setting_collection.find_one({"_id": "last_collect_time"})
                collect_seconds = int(collect_time.timestamp() - last_collect_time["value"])
                if collect_seconds <= 4:
                    await interaction.followup.send(
                        f"{interaction.user.mention} You didn't collect more than 5 seconds? Try again.")
                else:
                    if collect_seconds >= 60:
                        collect_seconds *= 2
                        if collect_seconds >= 600:
                            collect_seconds *= 2
                            msg_text = f"{interaction.user.mention} Collected {collect_seconds} seconds. " \
                                       f"(+{int(collect_seconds / 4 * 3)} seconds for 10 minute 4x bonus.)"
                        else:
                            msg_text = f"{interaction.user.mention} Collected {collect_seconds} seconds. " \
                                   f"(+{int(collect_seconds / 2)} seconds for 1 minute 2x bonus.)"
                    else:
                        msg_text = f"{interaction.user.mention} Collected {collect_seconds} seconds."
                    msg_text += f" <t:{int(collect_time.timestamp())}:R>"
                    await setting_collection.update_one({"_id": "last_collect_time"},
                                                        {"$set": {"value": int(collect_time.timestamp())}})
                    member_balance = await member_collection.find_one({"_id": user_id}, projection={"seconds": True})
                    time_collection = {"user": user_id, "collect_time": int(collect_time.timestamp()),
                                       "seconds": collect_seconds,
                                       "new_balance": collect_seconds + member_balance["seconds"]}
                    await setting_collection.update_one({"_id": "collections"}, {"$push": {"value": time_collection}})
                    await member_collection.update_one({"_id": user_id}, {"$push": {"collections": time_collection},
                                                                          "$inc": {"seconds": collect_seconds}})
                    member_info = await member_collection.find_one({"_id": user_id}, projection=["seconds"])
                    # history = paginate_list(member_info["collections"])
                    balance_view = TimeBalanceViewer(0, member_info["seconds"], bank_owner=interaction.user)
                    balance_embed = format_time_balance_embed(balance_view)
                    msg = await interaction.followup.send(
                        msg_text,
                        embed=balance_embed,
                        view=balance_view,
                    )
            else:
                await interaction.followup.send(f"{interaction.user.mention} You are not in Time is Money.")
        else:
            await interaction.followup.send(f"{interaction.user.mention} Time is Money is not currently running.")
    except KeyError:
        await interaction.followup.send(f"{interaction.user.mention} Time is Money is not currently running.")


def format_time_history_embed(view: View):
    history_text = format_time_bank_history(view.history[view.index])
    if view.bank_owner is not None:
        history_embed = Embed(
            title=f"Time Collection History",
            description=history_text,
            colour=view.bank_owner.colour
        ).set_footer(text=f"{view.index + 1}/{len(view.history)}")
        user_avatar = None if view.bank_owner.avatar is None else view.bank_owner.avatar.url
        if view.bank_owner.discriminator == "0":
            history_embed = history_embed.set_author(name=view.bank_owner.name, icon_url=user_avatar)
        else:
            history_embed = history_embed.set_author(name=f"{view.bank_owner.name}#{view.bank_owner.discriminator}",
                                                     icon_url=user_avatar)
    else:
        history_embed = Embed(
            title=f"Time Collection History",
            description=history_text,
            colour=bot_colour
        ).set_footer(text=f"{view.index + 1}/{len(view.history)}")
    return history_embed


def format_time_balance_embed(view: View):
    if view.bank_owner is not None:
        balance_embed = Embed(
            title=f"Time Balance",
            description=f"{view.balance} seconds",
            colour=view.bank_owner.colour
        )
        user_avatar = None if view.bank_owner.avatar is None else view.bank_owner.avatar.url
        if view.bank_owner.discriminator == "0":
            balance_embed = balance_embed.set_author(name=view.bank_owner.name, icon_url=user_avatar)
        else:
            balance_embed = balance_embed.set_author(name=f"{view.bank_owner.name}#{view.bank_owner.discriminator}",
                                                     icon_url=user_avatar)
    else:
        leaderboard_text = ""
        ranking = 1
        for member in view.member_balances:
            leaderboard_text += f"{ranking}. <@{member['_id']}>: {member['seconds']} seconds\n"
            ranking += 1
        balance_embed = Embed(
            title=f"Leaderboard",
            description=leaderboard_text,
            colour=bot_colour
        )
    return balance_embed


class TimeHistoryLeftButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Previous", row=1)

    async def callback(self, interaction: Interaction):
        if self.view.index != 0:
            self.view.index -= 1
        else:
            self.view.index = len(self.view.history) - 1
        embed = format_time_history_embed(self.view)
        await interaction.response.edit_message(embed=embed)


class TimeHistoryRightButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="Next", row=1)

    async def callback(self, interaction: Interaction):
        if len(self.view.history) - 1 == self.view.index:
            self.view.index = 0
        else:
            self.view.index = self.view.index + 1
        embed = format_time_history_embed(self.view)
        await interaction.response.edit_message(embed=embed)


class TimeHistoryToBalanceButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.grey, label="View Balance", row=2, emoji="💵")

    async def callback(self, interaction: Interaction):
        balance_view = TimeBalanceViewer(self.view.index, self.view.balance, self.view.history, self.view.bank_owner,
                                         self.view.member_balances)
        balance_embed = format_time_balance_embed(self.view)
        await interaction.response.edit_message(embed=balance_embed, view=balance_view)
        balance_view.init_interaction(interaction)


class TimeBalanceToHistoryButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.blurple, label="View History", row=1, emoji="📜")

    async def callback(self, interaction: Interaction):
        history_view = TimeBankHistoryViewer(self.view.index, self.view.balance, self.view.history,
                                             self.view.bank_owner, self.view.member_balances)
        history_embed = format_time_history_embed(self.view)
        await interaction.response.edit_message(embed=history_embed, view=history_view)
        history_view.init_interaction(interaction)


class TimeCollect(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.green, label="Collect Again", row=1, emoji="🧺")

    async def callback(self, interaction: Interaction):
        await collect_time(interaction)


class TimeBankHistoryViewer(AutoDisableView):
    def __init__(self, index, balance, history, bank_owner: Member = None, member_balances=None):
        super().__init__()
        self.index = index
        self.add_item(TimeHistoryLeftButton())
        self.add_item(TimeHistoryRightButton())
        self.add_item(TimeHistoryToBalanceButton())
        self.message = None
        self.timeout = 3600
        self.balance = balance
        self.history = history
        self.bank_owner = bank_owner
        self.member_balances = member_balances


class TimeBalanceViewer(AutoDisableView):
    def __init__(self, index, balance, history=None, bank_owner: Member = None, member_balances=None):
        super().__init__()
        self.index = index
        self.add_item(TimeCollect())
        self.message = None
        self.timeout = 3600
        self.balance = balance
        self.bank_owner = bank_owner
        self.member_balances = member_balances
        if history is not None:
            self.history = history
            self.add_item(TimeBalanceToHistoryButton())


@bot.slash_command(
    description="Time is Money commands",
    force_global=True)
async def seconds(interaction: Interaction):
    pass


@seconds.subcommand(
    description="Open signups for a new round of Time is Money"
)
async def setup(
        interaction: Interaction
):
    await interaction.response.defer()
    if not interaction.user.id == OWNER_ID:
        await interaction.followup.send("You are not the event organiser of Time is Money.")
        return
    else:
        db = db_client.time_is_money
        setting_collection = db.game
        member_collection = db.member
        await setting_collection.update_one({"_id": "signups_open"}, {"$set": {"value": True}}, upsert=True)
        await member_collection.delete_many({})
        await interaction.followup.send(f"Time is Money is now open for signups.")


@seconds.subcommand(
    description="Signup for a new round of Time is Money."
)
async def signup(
        interaction: Interaction,
):
    await interaction.response.defer()
    db = db_client.time_is_money
    setting_collection = db.game
    start_game = await setting_collection.find_one({"_id": "signups_open"})
    if start_game is not None and start_game["value"] is True:
        collection = db.member
        signup = {"_id": str(interaction.user.id), "seconds": 0, "collections": []}
        try:
            await collection.insert_one(signup)
            await interaction.followup.send(f"Successfully signed up {interaction.user.mention} for Time is Money.")
        except DuplicateKeyError:
            await interaction.followup.send(f"You already signed up for Time is Money.")
    else:
        await interaction.followup.send(f"Time is Money is not accepting new signups.")


@seconds.subcommand(
    description="End signups and start the game"
)
async def start(
        interaction: Interaction,
        end_date: int = SlashOption(
            description="End date of Time is Money, in Unix time format",
            required=True,
        ),
):
    await interaction.response.defer()
    now_time = int(datetime.now(tz=timezone.utc).timestamp())
    if not interaction.user.id == OWNER_ID:
        await interaction.followup.send("You are not the event organiser of Time is Money.")
        return
    else:
        db = db_client.time_is_money
        setting_collection = db.game
        await setting_collection.update_one({"_id": "signups_open"}, {"$set": {"value": False}})
        await setting_collection.update_one({"_id": "end_date"}, {"$set": {"value": end_date}}, upsert=True)
        await setting_collection.update_one({"_id": "last_collect_time"}, {"$set": {"value": now_time}}, upsert=True)
        await setting_collection.update_one({"_id": "collections"}, {"$set": {"value": []}}, upsert=True)
        await setting_collection.update_one({"_id": "start_time"}, {"$set": {"value": now_time}}, upsert=True)
        await interaction.followup.send("Done starting a new season of Time is Money!")
        member_collection = db.member
        members = member_collection.find({})
        member_message = ""
        async for member in members:
            member_message += f"<@{member['_id']}> "
        member_message = f"""{member_message}

Time is Money has started! It will end <t:{end_date}:R>.

To collect time, use the {time_collect.get_mention()} command.

You get the amount of seconds that passed between the last person's collection and your collection.

For example, if I collected some time, then you used the command 5 minutes after I collected time, then you'll earn 300 seconds.

Whoever ends up with the most seconds wins!
"""
        await interaction.followup.send(member_message, allowed_mentions=AllowedMentions.all())


@seconds.subcommand(
    name="collect",
    description="Collect some time.",
)
async def time_collect(
        interaction: Interaction,
):
    await collect_time(interaction)


@seconds.subcommand(
    description="View other people's, or everyone's, collected time."
)
async def view_balance(
        interaction: Interaction,
        user: Member = SlashOption(
            description="The user you want to check. Leave this blank to see everyone's time collecting.",
            required=False,
        )
):
    await interaction.response.defer()
    db = db_client.time_is_money
    if user is None:
        setting_collection = db.game
        collecting_history = await setting_collection.find_one({"_id": "collections"})
        collecting_history = paginate_list(collecting_history["value"])
        start_time = await setting_collection.find_one({"_id": "start_time"})
        last_collect_time = await setting_collection.find_one({"_id": "last_collect_time"})
        balance = last_collect_time["value"] - start_time["value"]
        member_collection = db.member
        member_cursor = member_collection.find({})
        member_balances = []
        async for member in member_cursor:
            member_balances.append(member)
        member_balances = sorted(member_balances, key=lambda d: d['seconds'], reverse=True)
        balance_view = TimeBalanceViewer(0, balance, history=collecting_history, member_balances=member_balances)
        balance_embed = format_time_balance_embed(balance_view)
        msg = await interaction.followup.send(
            embed=balance_embed,
            view=balance_view,
        )
        balance_view.init_interaction(interaction, msg.id)
    else:
        member_collection = db.member
        user_id = str(user.id)
        member_balance = await member_collection.find_one({"_id": user_id})
        if member_balance is not None:
            member_history = paginate_list(member_balance["collections"])
            balance_view = TimeBalanceViewer(0, member_balance["seconds"], history=member_history, bank_owner=user)
            balance_embed = format_time_balance_embed(balance_view)
            msg = await interaction.followup.send(
                embed=balance_embed,
                view=balance_view,
            )
            balance_view.init_interaction(interaction, msg.id)
        else:
            await interaction.followup.send("That user is not in Time is Money.")


@cells.subcommand(
    name="formula",
    description="See how many cells you can keep from Dalesia/Ceveulius over to the new planets.",
)
async def formula(
        interaction: Interaction,
        cells: int = SlashOption(
            description="The total number of cells you have, including those in your cell bank and those already claimed.",
            min_value=1,
        )
):
    await interaction.response.defer()
    new_cells = int(cells - ((cells - 64 + abs(cells - 64)) / 4) - ((cells - 192 + abs(cells - 192)) / 8) - (
            (cells - 448 + abs(cells - 448)) / 16) - ((cells - 960 + abs(cells - 960)) / 32))
    await interaction.followup.send(f"You would be able to keep {new_cells} cells when moving over from Cevdal")


@time.subcommand(
    description="Sets the channel for auto-updating the time."
)
async def channel(
        interaction: Interaction,
        channel: VoiceChannel = SlashOption(
            description="Enable or disable RAC Bot to show the current time in a channel?",
            required=True,
        ),
):
    await interaction.response.defer()
    if interaction.user.guild_permissions.manage_guild:
        db = db_client.settings
        collection = db.settings
        await collection.update_one({"_id": "rac_time_channel"},
                                    {"$set": {f"value.{interaction.guild_id}": channel.id}})
        loop = asyncio.get_event_loop()
        rac_time = await loop.run_in_executor(None, functools.partial(get_rac_time))
        new_date = await loop.run_in_executor(None, functools.partial(format_date, date=rac_time))
        await channel.edit(name=new_date)
        await interaction.followup.send(f"Successfully changed time channel to {channel.mention}")
    else:
        await interaction.followup.send("Sorry, but losers can't change this setting.")


async def generate_ai_image(prompt, size):
    glif_id = {
        "Square": "clsy8mkyu00008fjsr5tyzxy0",
        "Wide": "clsxzqjts0008rrxs68zw8xdh",
        "Tall": "clsy8rwn0000cj1ncxryy9rd0",
    }
    GLIF_API_KEY = os.getenv('GLIF_API_KEY')
    headers = {
        "Authorization": "Bearer " + GLIF_API_KEY,
    }
    payload = {
        "inputs": [prompt]
    }
    glif_url = "https://simple-api.glif.app/" + glif_id[size]
    async with aiohttp.ClientSession() as session:
        image = await session.post(glif_url, headers=headers, json=payload)
        image = await image.json()
    return image


@bot.slash_command(
    description="Generate AI images. Uses OpenAI's Dalle-3 image generator.",
    force_global=True)
async def ai_image(
        interaction: Interaction,
        prompt: str = SlashOption(
            description="The prompt to give the AI. For flags, mention 'an svg flag' in your prompt for better results.",
            required=True,
        ),
        size: str = SlashOption(
            description="The size of image you want.",
            choices=["Square", "Wide", "Tall"],
            default="Square"),
):
    await interaction.response.defer()
    image = await generate_ai_image(prompt, size)
    error_message = f"Something went wrong. Try again a few times. If the image's still not producing, it could be that your prompt was moderated, rate limits or just plain bad luck. \n\nHere's the response from the API:\n\n```json\n{image}\n```"
    try:
        logging.info(image)
        image_url = image['output']
        if image_url is None:
            await interaction.followup.send(error_message)
        else:
            result_embed = Embed(title="Here's your new AI image!", colour=bot_colour)
            result_embed.set_image(image_url)
            await interaction.followup.send('', embed=result_embed)
    except KeyError:
        await interaction.followup.send(error_message)


async def get_attachment(attachment, name):
    await attachment.save(name)
    file = open(name, "r")
    file_text = file.read()
    file.close()
    os.remove(name)
    return file_text


def combine_svg(map_text):
    map_lines = map_text.split("\n")
    start_line = None
    end_line = None
    for line_index in range(len(map_lines)):
        if '<svg id="map"' == map_lines[line_index][:13]:
            start_line = line_index
        if "</svg>" == map_lines[line_index][-6:]:
            end_line = line_index
        if start_line is not None and end_line is not None:
            break
    svg_lines = map_lines[start_line + 1:end_line + 1]
    original_svg = map_lines[start_line]
    for line in svg_lines:
        original_svg += "\n" + line
    map_lines[start_line] = original_svg
    del map_lines[start_line + 1:end_line + 1]
    return map_lines


def parse_map(map_text):
    map_lines = combine_svg(map_text)
    state_info = json.loads(map_lines[14])
    settings = map_lines[1].split("|")
    map_name = settings[20]
    distance_unit = settings[0]
    pixel_to_unit = float(settings[1])
    azgaar_map = {
        "name": map_name,
        "settings": settings,
        "distance_unit": distance_unit,
        "pixel_to_unit": pixel_to_unit,
        "states": state_info,
    }
    return azgaar_map


def find_map_attachment(discord_message: Message):
    for attachment in discord_message.attachments:
        if attachment.filename[-4:] == ".map":
            return attachment
    return


async def find_map_in_command(planet, azgaar_map, message_link, interaction):
    if planet:
        planet_channel = await bot.fetch_channel(planet)
        async for planet_message in planet_channel.history(limit=50):
            map_attachment = find_map_attachment(planet_message)
            if map_attachment is not None:
                return map_attachment
    if azgaar_map is None:
        if message_link is None:
            await interaction.followup.send("Please put either an Azgaar map file or a link to a message.")
            return
        else:
            try:
                link_message = await get_message_from_link(message_link)
                map_attachment = find_map_attachment(link_message)
                if map_attachment is None:
                    await interaction.followup.send(f"That message at {message_link} doesn't have a .map attachment.")
                    return
                else:
                    return map_attachment
            except ValueError:
                await interaction.followup.send("That message link is invalid. Please put a valid link to a message.")
                return
    else:
        if not azgaar_map.filename[-4:] == ".map":
            await interaction.followup.send("Please use an Azgaar map file.")
            return
        else:
            return azgaar_map


def state_cells_embed(state_list: list, index: int):
    leaderboard = "## Map: " + state_list[index][0]['map_name'] + "\n\n"
    start_ranking = index * 10 + 1
    for state_index in range(len(state_list[index])):
        leaderboard += f"{start_ranking + state_index}. {state_list[index][state_index]['name']}: {state_list[index][state_index]['cells']:,} cells\n"
    return Embed(title="States by cell amount", description=leaderboard,
                 colour=bot_colour).set_footer(
        text=f"{index + 1}/{len(state_list)}")


@map.subcommand(
    description="Shows the amount of cells each nation has. Don't use more than one option.",
)
async def state_cells(
        interaction: Interaction,
        planet: str = SlashOption(
            description="The planet you want to check.",
            choices=list(MAP_CHANNELS.keys()),
            required=False,
        ),
        azgaar_map: Attachment = SlashOption(
            description="The map file.",
            required=False
        ),
        message_link: str = SlashOption(
            description="A message with a .map attachment.",
            required=False),
):
    await interaction.response.defer()
    if planet:
        planet = MAP_CHANNELS[planet]
    map_attachment = await find_map_in_command(planet, azgaar_map, message_link, interaction)
    if map_attachment is None:
        return
    map_filename = f"azgaar_map_{interaction.id}"
    map_text = await get_attachment(map_attachment, map_filename)
    parsed_map = parse_map(map_text)
    new_state_info = []
    for state in parsed_map["states"]:
        try:
            if state.get("removed") is not True:
                new_state_info.append(
                    {
                        'name': state['name'],
                        'cells': state['cells'],
                        'map_name': parsed_map["name"],
                    }
                )
        except KeyError:
            pass
    new_state_info.sort(key=lambda state: state['cells'], reverse=True)
    new_state_info = paginate_list(new_state_info)
    view = PaginatedView(new_state_info, state_cells_embed, save_button=False)
    embed = state_cells_embed(new_state_info, 0)
    sent_message = await interaction.followup.send(embed=embed, view=view)
    view.init_interaction(interaction, sent_message.id)
    view.message = sent_message


def state_areas_embed(state_list: list, index: int):
    leaderboard = "## Map: " + state_list[index][0]['map_name'] + "\n\n"
    start_ranking = index * 10 + 1
    for state_index in range(len(state_list[index])):
        leaderboard += f"{start_ranking + state_index}. {state_list[index][state_index]['name']}: {state_list[index][state_index]['area']:,} {state_list[index][state_index]['unit']}²\n"
    return Embed(title="States by area", description=leaderboard,
                 colour=bot_colour).set_footer(
        text=f"{index + 1}/{len(state_list)}")


@map.subcommand(
    description="Shows the total area of each nation. Don't use more than one option.",
)
async def state_areas(
        interaction: Interaction,
        planet: str = SlashOption(
            description="The planet you want to check.",
            choices=list(MAP_CHANNELS.keys()),
            required=False,
        ),
        azgaar_map: Attachment = SlashOption(
            description="The map file.",
            required=False
        ),
        message_link: str = SlashOption(
            description="A message with a .map attachment.",
            required=False),
):
    await interaction.response.defer()
    if planet:
        planet = MAP_CHANNELS[planet]
    map_attachment = await find_map_in_command(planet, azgaar_map, message_link, interaction)
    if map_attachment is None:
        return
    map_filename = f"azgaar_map_{interaction.id}"
    map_text = await get_attachment(map_attachment, map_filename)
    parsed_map = parse_map(map_text)
    new_state_info = []
    for state in parsed_map["states"]:
        try:
            if state.get("removed") is not True:
                new_state_info.append(
                    {
                        'name': state['name'],
                        'area': int(state['area'] * parsed_map["pixel_to_unit"] ** 2),
                        'unit': parsed_map["distance_unit"],
                        'map_name': parsed_map["name"],
                    }
                )
        except KeyError:
            pass
    new_state_info.sort(key=lambda state: state['area'], reverse=True)
    new_state_info = paginate_list(new_state_info)
    view = PaginatedView(new_state_info, state_areas_embed, save_button=False)
    embed = state_areas_embed(new_state_info, 0)
    sent_message = await interaction.followup.send(embed=embed, view=view)
    view.init_interaction(interaction, sent_message.id)
    view.message = sent_message


@bot.slash_command(
    description="Show all RAC bot commands",
    force_global=True
)
async def commands(interaction: Interaction):
    await interaction.response.defer()
    response_text = ""
    for command in bot.get_application_commands():
        try:
            response_text += "- "
            response_text += command.get_mention()
            response_text += "\n"
        except AttributeError:
            continue
        try:
            for subcommand in command.children.values():
                response_text += " - "
                response_text += subcommand.get_mention()
                response_text += "\n"
        except AttributeError:
            continue

    response_embed = Embed(colour=bot_colour, title="RAC Bot Commands", description=response_text)
    await interaction.followup.send(embed=response_embed)


@bot.slash_command(
    description="Identify the Ballsdex ball based on message link",
    force_global=True,
)
async def ballsdex_identify(
        interaction: Interaction,
        message_link: str = SlashOption(
            description="A message with a Ballsdex image.",
            required=True)
):
    await interaction.response.defer()
    try:
        link_message = await get_message_from_link(message_link)
        if link_message.attachments is None:
            await interaction.followup.send(f"That message at {message_link} doesn't have an attachment.")
            return
        map_attachment = link_message.attachments[0]
    except ValueError:
        await interaction.followup.send("That message link is invalid. Please put a valid link to a message.")
        return
    ballsdex_image = "ballsdex_" + str(link_message.id)
    await map_attachment.save(ballsdex_image)
    ball_name = check_balldex_image(ballsdex_image)
    os.remove(ballsdex_image)
    rare_countryballs = open("rare_countryballs.txt", "r")
    rare_countryballs_list = rare_countryballs.read().splitlines()
    rare_countryballs.close()
    text_message = "I don't know what ball this is."
    if ball_name:
        text_message = f"Catch name: ```{ball_name}```"
        if ball_name in rare_countryballs_list:
            text_message += f"\nThis is a rare countryball."
    await interaction.followup.send(text_message)


async def parse_players(team_name: str, team_list: str, interaction: Interaction):
    players = []
    team_list += "\n"
    goalies = re.findall(r"Goalie: (.*)\n", team_list) + re.findall(r"Goalkeeper: (.*)\n", team_list)
    defenders = re.findall(r"Defender: (.*)\n", team_list)
    midfielders = re.findall(r"Mid: (.*)\n", team_list) + re.findall(r"Midfielder: (.*)\n", team_list)
    attackers = re.findall(r"Attacker: (.*)\n", team_list) + re.findall(r"Forward: (.*)\n", team_list)
    player_count = len(goalies) + len(defenders) + len(midfielders) + len(attackers)
    if not len(goalies) == 1:
        await interaction.followup.send(f"{team_name} has {len(players)} goalkeepers. You can only have 1.")
        raise ValueError(f"{team_name} has {len(players)} goalkeepers. You can only have 1.")
    if len(defenders) == 0:
        await interaction.followup.send(f"{team_name} doesn't have a defender. You need at least 1.")
        raise ValueError(f"{team_name} doesn't have a defender. You need at least 1.")
    if len(midfielders) == 0:
        await interaction.followup.send(f"{team_name} doesn't have a midfielder. You need at least 1.")
        raise ValueError(f"{team_name} doesn't have a midfielder. You need at least 1.")
    if len(attackers) == 0:
        await interaction.followup.send(f"{team_name} doesn't have a attacker. You need at least 1.")
        raise ValueError(f"{team_name} doesn't have a attacker. You need at least 1.")
    if not player_count == 11:
        await interaction.followup.send(f"{team_name} has {player_count} players. You need exactly 11.")
        raise ValueError(f"{team_name} has {player_count} players. You need exactly 11.")
    for player in goalies:
        players.append(soccer.Player(player, soccer.PlayerPosition.GOALKEEPER))
    for player in defenders:
        players.append(soccer.Player(player, soccer.PlayerPosition.DEFENDER))
    for player in midfielders:
        players.append(soccer.Player(player, soccer.PlayerPosition.MIDFIELDER))
    for player in attackers:
        players.append(soccer.Player(player, soccer.PlayerPosition.FORWARD))
    return players


def team_summary(team: soccer.Team, opposing_team: soccer.Team):
    yellow_cards = len(tuple(filter(lambda card: card.colour == soccer.CardColour.YELLOW, team.cards)))
    red_cards = len(tuple(filter(lambda card: card.colour == soccer.CardColour.RED, team.cards)))
    return f"""⚽ Shots: {team.shots}
🎯 Shots on Target: {team.shots_on_target}
🧤 Saves: {opposing_team.shots_on_target - opposing_team.goals}
🦵 Possession: {team.possession}%
😈 Fouls: {team.fouls}
🟨 Yellow cards: {yellow_cards}
🟥 Red cards: {red_cards}"""


def match_event_summary(match_events: list[soccer.Card]):
    event_text = ""
    for event in match_events:
        if type(event) == soccer.Card:
            if event.colour == soccer.CardColour.YELLOW:
                event_text += f"🟨 {event.player} {str(event.time)}\n"
            else:
                event_text += f"🟥 {event.player} {str(event.time)}\n"
        elif type(event) == soccer.Shot:
            event_text += f"⚽ {event.player} {str(event.time)}\n"
            if event.assister is not None:
                event_text += f"👟️ {event.assister}\n"
    return event_text


def penalty_summary(penalty_events: list[soccer.Shot]):
    event_text = ""
    for event in penalty_events:
        if event.goal:
            event_text += f"⚽ {event.player}\n"
        else:
            event_text += f"🥅 {event.player}\n"
    return event_text


def match_embed(team1: soccer.Team, team2: soccer.Team):
    rac_time = get_rac_time()
    team1_match_events = team1.goal_objects + team1.cards
    team2_match_events = team2.goal_objects + team2.cards
    team1_match_events.sort(key=lambda event: event.time)
    team2_match_events.sort(key=lambda event: event.time)
    if team1.first_leg_goals is not None:
        score = f"{team1.goals - team1.first_leg_goals}-{team2.goals - team2.first_leg_goals} ({team1.goals}-{team2.goals} on aggregate)"
    else:
        score = f"{team1.goals}-{team2.goals}"
    if team1.goals > team2.goals:
        msg_text = f"{team1.name} defeats {team2.name} " + score + "!"
    elif team1.goals < team2.goals:
        msg_text = f"{team2.name} defeats {team1.name} " + score + "!"
    else:
        msg_text = f"{team1.name} draws with {team2.name} " + score + "!"
    if team1.first_leg_goals is not None:
        match_embed_msg = Embed(colour=bot_colour, title=f"{team1.name} {team1.goals - team1.first_leg_goals}-{team2.goals - team2.first_leg_goals} ({team1.goals}-{team2.goals} agg.) {team2.name}", timestamp=rac_time)
    else:
        match_embed_msg = Embed(colour=bot_colour, title=f"{team1.name} {score} {team2.name}", timestamp=rac_time)
    match_embed_msg.add_field(name=team1.name, value=team_summary(team1, team2))
    match_embed_msg.add_field(name=team2.name, value=team_summary(team2, team1))
    events_embed = Embed(colour=bot_colour, timestamp=rac_time)
    events_embed.add_field(name="Events", value=match_event_summary(team1_match_events))
    events_embed.add_field(name="Events", value=match_event_summary(team2_match_events))
    return msg_text, match_embed_msg, events_embed


def penalty_match_embed(team1: soccer.Team, team2: soccer.Team):
    rac_time = get_rac_time()
    team1_match_events = team1.goal_objects + team1.cards
    team2_match_events = team2.goal_objects + team2.cards
    team1_match_events.sort(key=lambda event: event.time)
    team2_match_events.sort(key=lambda event: event.time)
    score = f"{team1.goals}-{team2.goals} ({team1.shootout_goals}-{team2.shootout_goals} on penalties)"
    if team1.shootout_goals > team2.shootout_goals:
        msg_text = f"{team1.name} defeats {team2.name} " + score + "!"
    elif team1.shootout_goals < team2.shootout_goals:
        msg_text = f"{team2.name} defeats {team1.name} " + score + "!"
    else:
        msg_text = f"{team2.name} draws with {team1.name} " + score + "!\n(If you see this, a bug has happened.)"
    match_embed_msg = Embed(colour=bot_colour, title=f"{team1.name} {team1.goals}-{team2.goals} (pen {team1.shootout_goals}-{team2.shootout_goals}) {team2.name}", timestamp=rac_time)
    match_embed_msg.add_field(name=team1.name, value=team_summary(team1, team2))
    match_embed_msg.add_field(name=team2.name, value=team_summary(team2, team1))
    events_embed = Embed(colour=bot_colour, timestamp=rac_time)
    events_embed.add_field(name="Events", value=match_event_summary(team1_match_events))
    events_embed.add_field(name="Events", value=match_event_summary(team2_match_events))
    penalty_embed = Embed(colour=bot_colour,timestamp=rac_time)
    penalty_embed.add_field(name="Penalties", value=penalty_summary(team1.penalty_objects))
    penalty_embed.add_field(name="Penalties", value=penalty_summary(team2.penalty_objects))
    return msg_text, match_embed_msg, events_embed, penalty_embed


def debug_team(team: soccer.Team):
    return f"""Relative strength: {team.relative_strength}
Average fouls per 90 minutes: {team.potential_fouls}
Average shots per 90 minutes: {team.potential_shots}
Shot accuracy: {team.shot_accuracy * 100:.0f}%"""


def debug_embed(team1: soccer.Team, team2: soccer.Team):
    debug_embed_msg = Embed(colour=bot_colour, title=f"Debug info")
    debug_embed_msg.add_field(name=team1.name, value=debug_team(team1))
    debug_embed_msg.add_field(name=team2.name, value=debug_team(team2))
    return debug_embed_msg


def player_list(team: soccer.Team):
    match_sheet = ""
    for player in team.players:
        if player.position == soccer.PlayerPosition.FORWARD:
            match_sheet += "Attacker: "
        elif player.position == soccer.PlayerPosition.MIDFIELDER:
            match_sheet += "Midfielder: "
        elif player.position == soccer.PlayerPosition.DEFENDER:
            match_sheet += "Defender: "
        elif player.position == soccer.PlayerPosition.GOALKEEPER:
            match_sheet += "Goalkeeper: "
        match_sheet += player.name
        match_sheet += "\n"
    return match_sheet


def missed_shot_desc(shot: soccer.Shot):
    weights = {
        f"{shot.player}'s shot goes wide of goal.": 1,
        f"{shot.player}'s shot flies high into the stands.": 1,
        f"{shot.player}'s shot is blocked by {shot.blocker} and deflected away from goal.": 1,
        f"{shot.player}'s shot bounces off the crossbar.": 0.5,
    }
    return soccer.random_picker(weights)


@bot.slash_command(
    description="Simulate a soccer match. A clone of http://scoresim.ilya.online",
    force_global=True,
    name="football",
    name_localizations={
        "en-US": "soccer",
    }
)
async def soccer_cmd(
        interaction: Interaction,
        team1_name: str = SlashOption(
            description="Name of the first team.",
            required=True),
        team2_name: str = SlashOption(
            description="Name of the second team.",
            required=True),
        real_time: str = SlashOption(
            description="Decide whether to have instant results or real_time play.",
            required=False,
            choices=("Instant results", "Real-time"),
            default="Instant results",
        ),
        extra_time: str = SlashOption(
            description="Should extra time be played in case of a draw?",
            required=False,
            choices=("Extra time", "No extra time"),
            default="No extra time",
        ),
        penalties: str = SlashOption(
            description="Should a penalty shootout be played in case of a draw?",
            required=False,
            choices=("Penalty shootout", "No penalty shootout"),
            default="No penalty shootout",
        ),
        team1_players: str = SlashOption(
            description="Player list of team 1 (message link). See pins in #sports-stadium for format.",
            required=False,
            default="",
        ),
        team2_players: str = SlashOption(
            description="Player list of team 2 (message link). See pins in #sports-stadium for format.",
            required=False,
            default="",
        ),
        relative_strength: str = SlashOption(
            description="Relative strength of both teams. Don't use this with individual strength.",
            choices=tuple(soccer.Team.STRENGTHS.keys()),
            required=False,
            default="Team 1 and Team 2 equal in class",
        ),
        team1_strength: int = SlashOption(
            description="Relative strength of team 1. 50 is equal, 60 is stronger, 40 is weaker.",
            required=False,
            default=50,
            min_value=1,
            max_value=100,
        ),
        team2_strength: int = SlashOption(
            description="Relative strength of team 2. 50 is equal, 60 is stronger, 40 is weaker.",
            required=False,
            default=50,
            min_value=1,
            max_value=100,
        ),
        team1_morale: str = SlashOption(
            description="Morale of team 1",
            choices=tuple(soccer.Team.MORALES.keys()),
            required=False,
            default="Average",
        ),
        team2_morale: str = SlashOption(
            description="Morale of team 2",
            choices=tuple(soccer.Team.MORALES.keys()),
            required=False,
            default="Average",
        ),
        team1_support: str = SlashOption(
            description="Crowd support of team 1",
            choices=tuple(soccer.Team.CROWD_SUPPORTS.keys()),
            required=False,
            default="No support",
        ),
        team2_support: str = SlashOption(
            description="Crowd support of team 2",
            choices=tuple(soccer.Team.CROWD_SUPPORTS.keys()),
            required=False,
            default="No support",
        ),
        team1_tactic: str = SlashOption(
            description="Tactic of team 1",
            choices=tuple(soccer.Team.TACTICS.keys()),
            required=False,
            default="Attacking (recommended)",
        ),
        team2_tactic: str = SlashOption(
            description="Tactic of team 2",
            choices=tuple(soccer.Team.TACTICS.keys()),
            required=False,
            default="Attacking (recommended)",
        ),
        team1_score: int = SlashOption(
            description="Earlier score of team 1 in this first leg.",
            required=False,
            default=None,
            min_value=0,
            max_value=100,
        ),
        team2_score: int = SlashOption(
            description="Earlier score of team 2 in this first leg.",
            required=False,
            default=None,
            min_value=0,
            max_value=100,
        ),
        shot_highlights: str = SlashOption(
            description="Choose shots that should be sent as events.",
            choices=("All shots", "Shots on target"),
            required=False,
            default="Shots on target",
        ),
        minute_length: int = SlashOption(
            description="How long a simulated minute is, in seconds. Default is 5.",
            required=False,
            default=5,
            min_value=1,
            max_value=60,
        ),
        debug: str = SlashOption(
            description="Shows some important debug info.",
            choices=("True", "False"),
            required=False,
            default="False",
        ),
):
    await interaction.response.defer()
    message_channel: nextcord.TextChannel = interaction.channel
    extra_time = True if extra_time == "Extra time" else False
    real_time = True if real_time == "Real-time" else False
    penalties = True if penalties == "Penalty shootout" else False
    team1_colour = Colour.from_rgb(229, 45, 45)
    team2_colour = Colour.from_rgb(45, 45, 229)
    if team1_strength == team2_strength == 50:
        team1_strength = soccer.Team.STRENGTHS[relative_strength]
        team2_strength = 100 - team1_strength
    else:
        pass
    if team1_players:
        try:
            team1_players = await get_message_from_link(team1_players)
            team1_players = team1_players.content
        except ValueError:
            await interaction.followup.send(
                "Team 1 players is not a valid message link. Please send a Discord message link.")
            return
        try:
            team1_players = await parse_players(team1_name, team1_players, interaction)
        except ValueError:
            return
    else:
        team1_players = soccer.default_players()
    if team2_players:
        try:
            team2_players = await get_message_from_link(team2_players)
            team2_players = team2_players.content
        except ValueError:
            await interaction.followup.send(
                "Team 2 players is not a valid message link. Please send a Discord message link.")
            return
        try:
            team2_players = await parse_players(team2_name, team2_players, interaction)
        except ValueError:
            return
    else:
        team2_players = soccer.default_players()
    team1 = soccer.Team(
        team1_name,
        team1_players,
        relative_strength=team1_strength,
        morale=team1_morale,
        crowd_support=team1_support,
        tactic=team1_tactic,
        opponent_tactic=team2_tactic,
        goals=team1_score if team1_score is not None and team2_score is not None else None
    )
    team2 = soccer.Team(
        team2_name,
        team2_players,
        relative_strength=team2_strength,
        morale=team2_morale,
        crowd_support=team2_support,
        tactic=team2_tactic,
        opponent_tactic=team1_tactic,
        goals=team2_score if team1_score is not None and team2_score is not None else None
    )
    match_start_message = None
    async for team1, team2, match_time, minute_events in soccer.start_match(team1, team2, extra_time=extra_time):
        if real_time:
            if match_time.minute == 1:
                match_start_embed = Embed(colour=bot_colour, title=f"📢 Match starts",
                                          description=f"{team1.name} vs {team2.name} has started!\n"
                                                      f"Note: Delete this message to stop the game.")
                match_start_embed.add_field(name=team1.name, value=player_list(team1))
                match_start_embed.add_field(name=team2.name, value=player_list(team2))
                match_start_message = await interaction.followup.send(embed=match_start_embed)
            if match_time.minute == 46 and match_time.half == soccer.Half.SECOND_HALF:
                half_time_embed = Embed(colour=bot_colour, title=f"⏱️ Play recommences {str(match_time)}",
                                        description="Half time has ended.")
                await message_channel.send(embed=half_time_embed, reference=match_start_message)
            if match_time.minute == 91 and match_time.half == soccer.Half.EXTRA_TIME:
                extra_time_embed = Embed(colour=bot_colour, title=f"⏱️ Play recommences {str(match_time)}",
                                        description=f"5 minute short break has ended.")
                await message_channel.send(embed=extra_time_embed, reference=match_start_message)
            await asyncio.sleep(minute_length)
            if minute_events:
                async with message_channel.typing():
                    await asyncio.sleep(5)
                    for event in minute_events:
                        event_colour = team1_colour if event.team == team1_name else team2_colour
                        if type(event) == soccer.Shot:
                            if shot_highlights == "All shots":
                                event_embed = Embed(colour=event_colour, title=f"🎯 Shot {str(match_time)}",
                                                    description=f"{event.player} of {event.team} shoots "
                                                                f"{'after a pass by ' + event.assister if event.assister is not None else ''}...")
                                await message_channel.send(embed=event_embed, reference=match_start_message)
                                await asyncio.sleep(5)
                                if event.goal is True:
                                    event_embed = Embed(colour=event_colour, title=f"⚽ Goal! {str(match_time)}",
                                                        description=f"""## {team1.name} {team1.goals}-{team2.goals} {team2.name}
                                            {event.player} scores for {event.team}!""")
                                elif event.on_target is True:
                                    event_embed = Embed(colour=event_colour, title=f"🧤 Saved {str(match_time)}",
                                                        description=f"""{event.player}'s shot was saved.""")
                                else:
                                    event_embed = Embed(colour=event_colour, title=f"❌ Missed {str(match_time)}",
                                                        description=missed_shot_desc(event))
                                await message_channel.send(embed=event_embed, reference=match_start_message)
                            else:
                                if event.on_target:
                                    event_embed = Embed(colour=event_colour, title=f"🎯 Shot {str(match_time)}",
                                                        description=f"{event.player} of {event.team} shoots on target "
                                                                    f"{'after a pass by ' + event.assister if event.assister is not None else ''}...")
                                    await message_channel.send(embed=event_embed, reference=match_start_message)
                                    await asyncio.sleep(5)
                                    if event.goal is True:
                                        event_embed = Embed(colour=event_colour, title=f"⚽ Goal! {str(match_time)}",
                                                            description=f"""## {team1.name} {team1.goals}-{team2.goals} {team2.name}
            {event.player} scores for {event.team}!""")
                                    else:
                                        event_embed = Embed(colour=event_colour, title=f"🧤 Saved {str(match_time)}",
                                                            description=f"""{event.player}'s shot was saved.""")
                                    await message_channel.send(embed=event_embed, reference=match_start_message)
                        elif type(event) == soccer.Card:
                            if event.colour == soccer.CardColour.YELLOW:
                                event_embed = Embed(colour=event_colour, title=f"🟨 Yellow card {str(match_time)}",
                                                    description=f"{event.player} of {event.team} given a yellow card for a foul.")
                            elif event.colour == soccer.CardColour.RED:
                                event_embed = Embed(colour=event_colour, title=f"🟥 Red card! {str(match_time)}",
                                                    description=f"{event.player} of {event.team} has been given a red card and is sent off!")
                            await message_channel.send(embed=event_embed, reference=match_start_message)
            if match_time.minute == 45:
                half_time_embed = Embed(colour=bot_colour, title=f"⏱️ Half time {str(match_time)}",
                                        description=f"Half time. Play will recommence in 15 minutes "
                                                    f"({int(minute_length * 15 / 60)} minutes and {(minute_length * 15) % 60} seconds IRL)...")
                await message_channel.send(embed=half_time_embed, reference=match_start_message)
                await asyncio.sleep(minute_length * 15)
            if match_time.minute == 90 and match_time.half == soccer.Half.EXTRA_TIME:
                extra_time_embed = Embed(colour=bot_colour, title=f"⏱️ Extra time {str(match_time)}",
                                        description=f"{team1.name} and {team2.name} are still tied.\nExtra time will start in 5 minutes "
                                                    f"({int(minute_length * 5 / 60)} minutes and {(minute_length * 5) % 60} seconds IRL)...")
                await message_channel.send(embed=extra_time_embed, reference=match_start_message)
                await asyncio.sleep(minute_length * 5)
        else:
            pass
    if penalties and team1.goals == team2.goals:
        if real_time:
            penalty_start_embed = Embed(colour=bot_colour, title=f"🥅️ Penalties",
                                        description=f"{team1.name} and {team2.name} are still tied"
                                                    f"\nA penalty shootout will be played. "
                                                    f"\nPreparing for 3 minutes "
                                                    f"({int(minute_length * 3 / 60)} minutes and {(minute_length * 3) % 60} seconds IRL)...")
            await message_channel.send(embed=penalty_start_embed, reference=match_start_message)
            await asyncio.sleep(minute_length * 3 - 10)
            penalty_start_embed = Embed(colour=bot_colour, title=f"⏱️ Penalties",
                                        description=f"Penalties are starting now...")
            await message_channel.send(embed=penalty_start_embed, reference=match_start_message)
            await asyncio.sleep(10)
        async for penalty_shot, team1, team2 in soccer.penalty_shootout(team1, team2):
            if real_time:
                async with message_channel.typing():
                    start_embed = Embed(colour=bot_colour, title=f"🏃 Penalty starting...",
                                        description=f"""{penalty_shot.player} is taking his penalty for {penalty_shot.team}...""")
                    await message_channel.send(embed=start_embed, reference=match_start_message)
                    await asyncio.sleep(5)
                if penalty_shot.goal is True:
                    penalty_embed = Embed(colour=bot_colour, title=f"⚽ Goal!",
                                          description=f"""## {team1.name} {team1.shootout_goals}-{team2.shootout_goals} {team2.name}
                {penalty_shot.player} scores a penalty for {penalty_shot.team}!""")
                else:
                    penalty_embed = Embed(colour=bot_colour, title=f"🧤 Saved",
                                          description=f"""{penalty_shot.player}'s penalty for {penalty_shot.team} was saved.""")
                await message_channel.send(embed=penalty_embed, reference=match_start_message)
            else:
                pass
        msg_text, match_embed_msg, events_embed, penalty_embed = penalty_match_embed(team1, team2)
        embeds = [match_embed_msg, events_embed, penalty_embed]
    else:
        msg_text, match_embed_msg, events_embed = match_embed(team1, team2)
        embeds = [match_embed_msg, events_embed]
    if debug == "True":
        embeds.append(debug_embed(team1, team2))
    if match_start_message:
        await message_channel.send(msg_text, embeds=embeds, reference=match_start_message)
    else:
        await interaction.followup.send(msg_text, embeds=embeds)
