import datetime
import logging
import typing

import discord
from discord.ext import commands

from sql.easy_sql import EasySQL


class Giveaways(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.db = self.bot.db
        self.log = logging.getLogger("GiveawayBot.GiveawayCog")

    def parse_time(
        self, time: typing.Union[datetime.timedelta, int]
    ) -> typing.Optional[datetime.timedelta]:
        if isinstance(time, datetime.timedelta):
            return time
        elif isinstance(time, int):
            return datetime.timedelta(seconds=time)
        else:
            return None

    @commands.group()
    async def giveaway(self, ctx: commands.Context) -> None:
        """Giveaway commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @giveaway.command()
    async def create(
        self,
        ctx: commands.Context,
        title: str,
        description: str,
        time: typing.Union[int, str],
        prize: str,
    ) -> None:
        """Create a giveaway."""
        time = self.parse_time(time)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
