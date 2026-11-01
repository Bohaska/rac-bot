import logging
import os
import asyncio
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(processName)s:%(process)d] %(name)s: %(message)s",
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

# import concurrent.futures
from multiprocessing import Process
from rac_bot import bot
import nationstates_main
from ballsdex_hash import hash_balldex_images
import gradio as gr

# lazy_setup()
"""with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.submit(asyncio.run, autoupdate_grades_habitica(db_client))
    executor.submit(asyncio.run, bot.start(os.getenv('BOT_TOKEN')))"""

def greet(name):
    return "Hello " + name + "!!"

demo = gr.Interface(fn=greet, inputs="text", outputs="text")

def launch_gradio_app():
    demo.launch(server_name="0.0.0.0", server_port=7860) 

def run_bot():
    logger.info("Starting Discord bot process")
    try:
        bot.run(os.environ["BOT_TOKEN"])
    except BaseException:
        logger.exception("Discord bot process terminated unexpectedly")
        raise
    finally:
        logger.warning("Discord bot process exited")


if __name__ == "__main__":
    tasks = []
    # tasks.append(Process(target=hash_balldex_images))
    tasks.append(Process(target=run_bot, name="discord-bot"))
    # tasks.append(Process(target=asyncio.run, args=(nationstates_main.run_all_tasks(),)))
    tasks.append(Process(target=launch_gradio_app, name="gradio"))

    for task in tasks:
        logger.info("Starting child process %s", task.name)
        task.start()

    for task in tasks:
        task.join()
        logger.warning("Child process %s exited with code %s", task.name, task.exitcode)

