import logging
import os
import asyncio
# import concurrent.futures
from multiprocessing import Process
from rac_bot import bot
import nationstates_main
from ballsdex_hash import hash_balldex_images
import gradio as gr


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# lazy_setup()
"""with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.submit(asyncio.run, autoupdate_grades_habitica(db_client))
    executor.submit(asyncio.run, bot.start(os.getenv('BOT_TOKEN')))"""

def greet(name):
    return "Hello " + name + "!!"

demo = gr.Interface(fn=greet, inputs="text", outputs="text")

tasks = []
# tasks.append(Process(target=hash_balldex_images))
tasks.append(Process(target=bot.run, args=(os.getenv('BOT_TOKEN'),)))
# tasks.append(Process(target=asyncio.run, args=(nationstates_main.run_all_tasks(),)))
tasks.append(Process(target=demo.launch))

for task in tasks:
    task.start()
# bet_users.start()
for task in tasks:
    task.join()
# bet_users.join()

