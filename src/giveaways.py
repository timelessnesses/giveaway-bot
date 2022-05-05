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

    def parse_args(self, args: str) -> dict:
        try:
            args = args.split(",")
            args = [arg.split("=") for arg in args]
            for arg in args:
                if arg[1].lower() in ("true", "false"):
                    arg[1] = arg[1].lower() == "true"
                elif arg[1].isdigit():
                    arg[1] = int(arg[1])
                elif arg[1].lower() in ("none", "null"):
                    arg[1] = None
                else:
                    raise commands.errors.BadArgument(
                        f"Invalid value for argument {arg[0]}"
                    )
            return dict(args)
        except Exception as e:
            raise commands.errors.BadArgument(f"Invalid arguments: {args}")
            self.log.fatal(e)

    @commands.command(name="giveaway", aliases=["gw"])
    async def giveaway(self, ctx, *, args) -> None:
        try:
            args = self.parse_args(args)
        except commands.errors.BadArgument as e:
            await ctx.send(
                embed=discord.Embed(
                    title="Looks like you gave me something wrong here",
                    description="This is how command argument parsing works:\n"
                    "If you want value to be text you don't need to put single or double quote wrap around argument like\n"
                    "`title=Hello world!`\n"
                    "If you want value to be number you also don't need to put single or double quote like\n"
                    "`time=20`\n"
                    "If you want value to be yes or no (aka boolean) please use true or false (not case sensitive) like\n"
                    "`wizard=true`\n"
                    "If you want to stack argument together split them with `,` like\n"
                    "`title=Hello world!,time=20,wizard=true`\n (spacing is optional)",
                    color=discord.Color.red(),
                )
            )
            return
        if args.get("wizard") == True:
            await self.wizard(ctx, args)
            return
        await self.manual(ctx, args)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
