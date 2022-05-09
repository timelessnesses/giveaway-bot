import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("GiveawayBot")
log.setLevel(logging.DEBUG)
logging.getLogger("discord").setLevel(logging.CRITICAL)

try:
    import uvloop

    uvloop.install()
    log.info("Installed uvloop now enjoy the fastness!")
except (ImportError, ModuleNotFoundError):
    log.info("uvloop not installed, falling back to asyncio")
    pass

from asyncio import run
from datetime import datetime

import asyncpg
import discord
from discord.ext import commands
from dotenv import load_dotenv
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

load_dotenv()
import os

from sql.easy_sql import EasySQL

bot = commands.Bot(command_prefix="g!", intents=discord.Intents.all())
bot.db = None
bot.start_time = datetime.utcnow()
bot.remove_command("help")
observer = Observer()


class FileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        log.info(f"File changed: {event.src_path}")
        if event.src_path.endswith(".py"):
            log.info("Reloading...")
            path = event.src_path.replace("\\", "/").replace("/", ".")[:-3]
            try:
                run(bot.reload_extension(path))
                log.info(f"Reloaded {path}")
            except Exception as e:
                log.error(f"Failed to reload {path}")


observer.schedule(FileHandler(), path="src", recursive=False)


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user.name)
    await bot.tree.sync()


async def main():
    async with bot:
        bot.db = await EasySQL().connect(
            host=os.environ.get("DB_HOST"),
            database="giveaways",
            user="giveaway_bot",
            password=os.environ["DB_PASS"],
        )
        for cog in os.listdir("src"):
            if cog.endswith(".py"):
                await bot.load_extension(f"src.{cog[:-3]}")
        await bot.load_extension("jishaku")
        log.info("Connected to database")
        await bot.db.execute(open("sql/postgres_starter.sql", "r").read())
        log.info("Loaded starter SQL")
        observer.start()
        await bot.start(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    try:
        run(main())
    except KeyboardInterrupt:
        log.info("Exiting...")
        run(bot.db.close())
        observer.stop()
