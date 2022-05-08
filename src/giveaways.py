import datetime
import logging
import random
import typing

import discord
from discord.ext import commands, tasks

from sql.easy_sql import EasySQL

from .utils.stuffs import random_id, dummy


class Giveaways(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.db = self.bot.db
        self.log = logging.getLogger("GiveawayBot.GiveawayCog")

    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info("Starting giveaway task loop")
        self.check_giveaways.start()

    def parse_time(
        self, time: typing.Union[datetime.timedelta, int, str]
    ) -> typing.Optional[datetime.timedelta]:
        if isinstance(time, datetime.timedelta):
            return time
        elif isinstance(time, int):
            return datetime.timedelta(seconds=time)
        else:
            if time.endswith("s"):
                time = datetime.timedelta(seconds=int(time[:-1]))
            elif time.endswith("m"):
                time = datetime.timedelta(minutes=int(time[:-1]))
            elif time.endswith("h"):
                time = datetime.timedelta(hours=int(time[:-1]))
            elif time.endswith("d"):
                time = datetime.timedelta(days=int(time[:-1]))
            elif time.endswith("w"):
                time = datetime.timedelta(weeks=int(time[:-1]))
            elif time.endswith("mo"):
                time = datetime.timedelta(days=int(time[:-2]) * 30)
            elif time.endswith("y"):
                time = datetime.timedelta(days=int(time[:-1]) * 365)
            else:
                badarg = commands.BadArgument(
                    f"{time} is not a valid time.\n"
                    "Valid time formats are:\n"
                    "  - `1s`\n"
                    "  - `1m`\n"
                    "  - `1h`\n"
                    "  - `1d`\n"
                    "  - `1w`\n"
                    "  - `1mo`\n"
                    "  - `1y`\n"
                )
                badarg.param = dummy()
                badarg.param.name = "time"
                raise badarg
            return time

    @commands.group()
    async def giveaway(self, ctx: commands.Context) -> None:
        """Giveaway commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    def parse_condition(self, condition: str) -> typing.Optional[typing.Callable]:
        if condition == "everyone":
            return lambda m: True
        elif condition.startswith("role"):
            role = condition.split(" ")[1]
            return lambda m: role in [r.id for r in m.roles]
        elif condition.startswith("not role"):
            role = condition.split(" ")[1]
            return lambda m: role not in [r.name for r in m.roles]
        elif condition.startswith("account age"):
            age = int(condition.split(" ")[1])
            return lambda m: (datetime.datetime.now() - m.created_at).days >= age
        elif condition.startswith("not account age"):
            age = int(condition.split(" ")[1])
            return lambda m: (datetime.datetime.now() - m.created_at).days < age
        else:
            badarg = commands.BadArgument(f"{condition} is not a valid condition.\n")
            badarg.param = dummy()
            badarg.param.name = "condition"
            raise badarg

    @giveaway.command()
    async def create(
        self,
        ctx: commands.Context,
        title: str,
        description: str,
        time: typing.Union[int, str],
        prize: str,
        channel: typing.Optional[discord.TextChannel] = None,
        *,
        condition: typing.Optional[str] = None,
    ) -> None:
        """Create a giveaway."""
        time = self.parse_time(time)
        if time is None:
            badarg = commands.BadArgument(
                "Time must be an integer or a string representing a time."
            )
            badarg.param = dummy()
            badarg.param.name = "time"
            raise badarg
        if channel is None:
            channel = ctx.channel
        if time < datetime.timedelta(seconds=5):
            badarg = commands.BadArgument("Time must be at least 5 second.")
            badarg.param = dummy()
            badarg.param.name = "time"
            raise badarg

        if condition is not None:
            condition_func = self.parse_condition(condition)

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blurple(),
        )
        now = datetime.datetime.now()
        embed.add_field(name="Prize", value=prize)
        embed.add_field(name="Time", value=str(time))
        embed.add_field(name="Channel", value=channel.mention)
        embed.add_field(name="Condition", value=condition if condition else "None")
        embed.add_field(name="ID", value=random_id())
        embed.add_field(name="Created by", value=ctx.author.mention)
        embed.add_field(name="Created at", value=now.strftime("%d/%m/%Y %H:%M:%S"))
        embed.set_footer(text=f"Giveaway created by {ctx.author.name}")

        message = await channel.send(embed=embed)
        await message.add_reaction("🎉")

        await self.db.execute(
            f"""
            INSERT INTO giveaways (id, owner_id, guild_id, channel_id, message_id, title, description, started_at, duration, ended_at, winner_id, conditions, prize)
            VALUES ({random_id(length=10)}, {ctx.author.id},{message.guild.id}, {message.channel.id},{message.id}, '{title}', '{description}', {now.timestamp()}, {time.total_seconds()}, '{(now + time).timestamp()}', NULL, {'NULL' if condition is None else f"'{condition}'"}, '{prize}')
            """
        )

    @tasks.loop(seconds=1)
    async def check_giveaways(self) -> None:
        """Check giveaways."""
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        giveaways = await self.db.fetch(
            f"SELECT * FROM giveaways WHERE ended_at < {now.timestamp()} AND winner_id IS NULL"
        )
        for giveaway in giveaways:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if channel is None:
                continue
            message = await channel.fetch_message(giveaway["message_id"])
            if message is None:
                continue
            winner = [member async for member in message.reactions[0].users()]
            winner.remove(self.bot.user)
            winner = random.choice(winner)
            if winner is None:
                continue
            await message.edit(
                content=f"{winner.mention} won the giveaway!",
                embed=discord.Embed(
                    title=giveaway["title"],
                    description=giveaway["description"],
                    color=discord.Color.blurple(),
                )
                .add_field(name="Prize", value=giveaway["prize"])
                .add_field(name="Winner", value=winner.mention)
                .add_field(name="ID", value=giveaway["id"])
                .add_field(
                    name="Created by",
                    value=self.bot.get_user(int(giveaway["owner_id"])).mention,
                )
                .add_field(
                    name="Created at",
                    value=datetime.datetime.fromtimestamp(
                        giveaway["started_at"]
                    ).strftime("%d/%m/%Y %H:%M:%S"),
                )
                .add_field(
                    name="Ended at",
                    value=datetime.datetime.fromtimestamp(
                        giveaway["ended_at"]
                    ).strftime("%d/%m/%Y %H:%M:%S"),
                )
                .set_footer(text=f"Giveaway ended by {winner.mention}"),
            )
            await self.db.execute(
                f"UPDATE giveaways SET ended_at = {now.timestamp()}, winner_id = {winner.id} WHERE id = {giveaway['id']}"
            )

    @giveaway.command()
    async def end(self, ctx: commands.Context, giveaway_id: str) -> None:
        """End a giveaway."""
        giveaway = await self.db.fetch(
            f"SELECT * FROM giveaways WHERE id = '{giveaway_id}'"
        )
        if not giveaway:
            raise commands.BadArgument(f"No giveaway with ID {giveaway_id}.")
        giveaway = giveaway[0]
        channel = self.bot.get_channel(giveaway["channel_id"])
        if channel is None:
            raise commands.BadArgument(f"No channel with ID {giveaway['channel_id']}.")
        message = await channel.fetch_message(giveaway["message_id"])
        if message is None:
            raise commands.BadArgument(f"No message with ID {giveaway['message_id']}.")
        winner = await message.reactions[0].users().flatten()
        winner = random.choice(winner)
        if winner is None:
            raise commands.BadArgument("No winner.")
        now = datetime.datetime.now()
        await message.edit(
            embed=discord.Embed(
                title=giveaway["title"],
                description=giveaway["description"],
                color=discord.Color.blurple(),
            )
            .add_field(name="Prize", value=giveaway["prize"])
            .add_field(name="Winner", value=winner.mention)
            .add_field(name="ID", value=giveaway["id"])
            .add_field(
                name="Created by", value=self.bot.get_user(giveaway["guild_id"]).mention
            )
            .add_field(
                name="Created at",
                value=datetime.datetime.fromtimestamp(giveaway["started_at"]).strftime(
                    "%d/%m/%Y %H:%M:%S"
                ),
            )
            .add_field(name="Ended at", value=now.strftime("%d/%m/%Y %H:%M:%S"))
            .set_footer(
                text=f"Giveaway ended by {self.bot.get_user(giveaway['winner_id']).name}"
            )
        )
        await self.db.execute(
            f"UPDATE giveaways SET ended_at = {now.timestamp()}, winner_id = {winner.id}, time = {(now-datetime.timedelta(seconds=giveaway['time'])).total_seconds()} WHERE id = {giveaway['id']}"
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        """Reaction add event."""
        if payload.emoji.name != "🎉":
            return
        giveaway = await self.db.fetch(
            f"SELECT * FROM giveaways WHERE message_id = '{payload.message_id}'"
        )
        if not giveaway:
            return
        giveaway = giveaway[0]
        if giveaway["winner_id"] is not None:
            return
        if giveaway["conditions"] is not None:
            condition_func = self.parse_condition(giveaway["conditions"])
            if not condition_func(payload.member):
                await payload.member.send(
                    embed=discord.Embed(
                        title="You don't meet the conditions!",
                        description=giveaway["conditions"],
                        color=discord.Color.red(),
                    )
                )
                channel = self.bot.get_channel(giveaway["channel_id"])
                if channel is None:
                    return
                message = await channel.fetch_message(giveaway["message_id"])
                if message is None:
                    return
                await message.remove_reaction(payload.emoji, payload.member)
                return

        if (
            datetime.datetime.fromtimestamp(giveaway["ended_at"])
            <= datetime.datetime.now()
        ):
            message = await self.bot.get_channel(giveaway["channel_id"]).fetch_message(
                giveaway["message_id"]
            )
            if message is None:
                return
            winner = [member async for member in message.reactions[0].users()]
            winner.remove(self.bot.user)
            winner = random.choice(winner)
            if winner is None:
                return
            await message.edit(
                embed=discord.Embed(
                    title=giveaway["title"],
                    description=giveaway["description"],
                    color=discord.Color.blurple(),
                )
                .add_field(name="Prize", value=giveaway["prize"])
                .add_field(name="Winner", value=winner.mention)
                .add_field(name="ID", value=giveaway["id"])
                .add_field(name="Created by", value=message.author.mention)
                .add_field(name="Created at", value=giveaway["started_at"])
                .set_footer(text=f"Giveaway ended by {message.author.name}")
            )

            await self.db.execute(
                f"UPDATE giveaways SET winner_id = '{winner.id}' WHERE id = '{giveaway['id']}'"
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
