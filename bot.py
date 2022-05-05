import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("GiveawayBot")
log.setLevel(logging.DEBUG)

try:
    import uvloop

    uvloop.install()
    log.info("Installed uvloop now enjoy the fastness!")
except (ImportError, ModuleNotFoundError):
    log.info("uvloop not installed, falling back to asyncio")
    pass

from asyncio import run

import asyncpg
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
import os

from sql.easy_sql import EasySQL

bot = commands.Bot(command_prefix="g!", intents=discord.Intents.all())
bot.db = None
bot.remove_command("help")


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user.name)


async def main():
    try:
        async with bot:
            for cog in os.listdir("src"):
                if cog.endswith(".py"):
                    await bot.load_extension(f"src.{cog[:-3]}")
            await bot.load_extension("jishaku")
            bot.db = await EasySQL().connect(
                host=os.environ.get("DB_HOST"),
                database="giveaways",
                user="giveaway_bot",
                password=os.environ["DB_PASS"],
            )
            log.info("Connected to database")
            await bot.db.execute(open("sql/postgres_starter.sql", "r").read())
            await bot.start(os.environ["DISCORD_TOKEN"])
    except KeyboardInterrupt:
        log.fatal("KeyboardInterrupt recieved exitting")
        await bot.db.close()


if __name__ == "__main__":
    run(main())
