import datetime
import logging
import random
import typing

import discord
from discord.ext import commands, tasks

from sql.easy_sql import EasySQL

from .utils.stuffs import random_id


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

    async def setup_hook(self):
        self.log.info("Starting the check giveaways loop")
        self.check_giveaways.start()

    @commands.group()
    async def giveaway(self, ctx: commands.Context) -> None:
        """Giveaway commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    def parse_condition(self, condition: str) -> typing.Optional[typing.Callable]:
        if condition == "everyone":
            return lambda m: True
        elif condition.startswith("invites"):
            invites = int(condition.split(" ")[1])
            return lambda m: m.author.invites >= invites
        elif condition.startswith("role"):
            role = condition.split(" ")[1]
            return lambda m: role in [r.name for r in m.author.roles]
        elif condition.startswith("not role"):
            role = condition.split(" ")[1]
            return lambda m: role not in [r.name for r in m.author.roles]
        elif condition.startswith("account age"):
            age = int(condition.split(" ")[1])
            return lambda m: (datetime.datetime.now() - m.created_at).days >= age
        elif condition.startswith("not account age"):
            age = int(condition.split(" ")[1])
            return lambda m: (datetime.datetime.now() - m.created_at).days < age
        else:
            raise commands.BadArgument(f"Unknown condition: {condition}")

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
            raise commands.BadArgument(
                "Time must be an integer or a string representing a time."
            )
        if channel is None:
            channel = ctx.channel
        if time < datetime.timedelta(seconds=5):
            raise commands.BadArgument("Time must be at least 5 second.")

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
            INSERT INTO giveaways (id, guild_id, channel_id, message_id, title, description, started_at, duration, ended_at, winner_id, conditions, prize)
            VALUES ({random_id(length=10)}, {message.guild.id}, {message.channel.id},{message.message.id}, '{title}', '{description}', {now.timestamp()}, {time.total_seconds()}, '{(now + time).timestamp()}', NULL, {'NULL' if condition is None else condition}, '{prize}')
            """
        )

    @tasks.loop(seconds=5)
    async def check_giveaways(self) -> None:
        """Check giveaways."""
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        giveaways = await self.db.fetch(
            f"SELECT * FROM giveaways WHERE ended_at < {now.timestamp()}"
        )
        for giveaway in giveaways:
            channel = self.bot.get_channel(giveaway["channel_id"])
            if channel is None:
                continue
            message = await channel.fetch_message(giveaway["message_id"])
            if message is None:
                continue
            winner = await message.reactions[0].users().flatten()
            winner = random.choice(winner)
            if winner is None:
                continue
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
                    name="Created by",
                    value=self.bot.get_user(giveaway["guild_id"]).mention,
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
                .set_footer(
                    text=f"Giveaway ended by {self.bot.get_user(giveaway['winner_id']).name}"
                )
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
                return
        message = await self.bot.get_channel(giveaway["channel_id"]).fetch_message(
            giveaway["message_id"]
        )
        if message is None:
            return
        winner = await message.reactions[0].users().flatten()
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
