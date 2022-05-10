import datetime
import enum
import logging
import os
import random
import string
import typing

import discord
from discord.ext import commands, tasks

from sql.easy_sql import EasySQL

from .utils.stuffs import dummy, giveaway_info, random_id


class Status(enum.Enum):
    active = "active"
    ended = "ended"


class Giveaways(commands.Cog):
    """
    A giveaway commands group!
    """

    @property
    def display_emoji(self) -> str:
        return "🎉"

    def __init__(self, bot) -> None:
        self.bot = bot
        self.db = self.bot.db
        self.log = logging.getLogger("GiveawayBot.GiveawayCog")

    @commands.Cog.listener()
    async def on_ready(self):
        self.log.info("Checking old giveaways")
        await self.old_giveaway()
        self.log.info("Starting giveaway task loop")
        self.check_giveaways.start()
        self.log.info("Tasks started")

    def parse_time(
        self, time: typing.Union[datetime.timedelta, int, str]
    ) -> typing.Optional[datetime.timedelta]:
        if isinstance(time, datetime.timedelta):
            return time
        elif isinstance(time, int):
            return datetime.timedelta(seconds=time)
        else:
            if not time.strip(string.ascii_letters).isdigit():
                # likely format error
                badarg = commands.BadArgument(
                    f"{time} is not a valid time.\n"
                    "Valid time formats are:\n"
                    "  - `1s` for 1 seconds\n"
                    "  - `1m` for 1 minutes\n"
                    "  - `1h` for 1 hour\n"
                    "  - `1d` for 1 day\n"
                    "  - `1w` for 1 week\n"
                    "  - `1mo` for 1 month\n"
                    "  - `1y` for 1 year"
                )
                badarg.param = dummy()
                badarg.param.name = "time"
                raise badarg
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
                    "  - `1s` for 1 seconds\n"
                    "  - `1m` for 1 minutes\n"
                    "  - `1h` for 1 hour\n"
                    "  - `1d` for 1 day\n"
                    "  - `1w` for 1 week\n"
                    "  - `1mo` for 1 month\n"
                    "  - `1y` for 1 year"
                )
                badarg.param = dummy()
                badarg.param.name = "time"
                raise badarg
            return time

    @commands.hybrid_group()
    async def giveaway(self, ctx: discord.Interaction) -> None:
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
        ctx: discord.Interaction,
        title: str,
        description: str,
        time: str,
        prize: str,
        channel: typing.Optional[discord.TextChannel] = None,
        *,
        condition: typing.Optional[str] = None,
    ) -> None:
        """Create a giveaway."""
        await ctx.defer()
        setup_db = await EasySQL().connect(
            host=os.environ.get("DB_HOST"),
            database="giveaways",
            user="giveaway_bot",
            password=os.environ["DB_PASS"],
        )
        roles = ctx.author.roles
        role_id = await setup_db.fetch(
            f"SELECT * FROM setup WHERE guild_id = {ctx.guild.id}"
        )
        if not role_id:
            role_id = 0
            await ctx.send(
                embed=discord.Embed(
                    title="Setup",
                    description="Warning: No giveaway role has been set up yet.\n"
                    "You can set it up with `g!giveaway setup`\n"
                    "If you didn't setup the bot every giveaway creation will check if member has a adminstrator permission.",
                    color=discord.Color.yellow(),
                )
            )
        else:
            role_id = role_id[0]["giveaway_role_id"]
        if (
            int(role_id) not in [r.id for r in roles]
            or not ctx.author.guild_permissions.administrator
        ):
            raise commands.MissingPermissions(["NoGiveawayRoleError"])
        await setup_db.close()
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
        id = random_id()
        now = datetime.datetime.now()
        embed.add_field(name="Prize", value=prize)
        embed.add_field(name="Time", value=str(time))
        embed.add_field(name="Channel", value=channel.mention)
        embed.add_field(name="Condition", value=condition if condition else "None")
        embed.add_field(name="ID", value=id)
        embed.add_field(name="Created by", value=ctx.author.mention)
        embed.add_field(name="Created at", value=now.strftime("%d/%m/%Y %H:%M:%S"))
        embed.set_footer(text=f"Giveaway created by {ctx.author.name}")

        message = await channel.send(embed=embed)
        await message.add_reaction("🎉")

        await self.db.execute(
            f"""
            INSERT INTO giveaways (id, owner_id, guild_id, channel_id, message_id, title, description, started_at, duration, ended_at, winner_id, conditions, prize)
            VALUES ({id}, {ctx.author.id},{message.guild.id}, {message.channel.id},{message.id}, '{title}', '{description}', {now.timestamp()}, {time.total_seconds()}, '{(now + time).timestamp()}', NULL, {'NULL' if condition is None else f"'{condition}'"}, '{prize}')
            """
        )
        await ctx.send(
            embed=discord.Embed(
                title="Successfully!",
                description="Everythings works perfectly fine!\n"
                f"Your giveaway message is at {message.jump_url}",
                color=discord.Color.green(),
            )
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
                winner = dummy()
                winner.mention = "No one"
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

    async def old_giveaway(self) -> None:
        """Check entire giveaway see if it expired if it is then forcing the winner."""
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
                winner = dummy()
                winner.mention = "No one"
                winner.id = None
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
    async def end(self, ctx: discord.Interaction, giveaway_id: str) -> None:
        """End a giveaway."""
        await ctx.defer()
        giveaway = await self.db.fetch(
            f"SELECT * FROM giveaways WHERE id = {giveaway_id}"
        )
        if not giveaway:
            badarg = commands.BadArgument("No giveaway with this id.")
            badarg.param = dummy()
            badarg.param.name = "giveaway_id"
            raise badarg
        giveaway = giveaway[0]
        channel = self.bot.get_channel(giveaway["channel_id"])
        if channel is None:
            raise commands.BadArgument(f"No channel with ID {giveaway['channel_id']}.")
        message = await channel.fetch_message(giveaway["message_id"])
        if message is None:
            raise commands.BadArgument(f"No message with ID {giveaway['message_id']}.")
        winner = [user async for user in message.reactions[0].users()]
        winner = random.choice(winner)
        if winner is None:
            winner = dummy()
            winner.mention = "No one"
            winner.id = None
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
                name="Created by",
                value=self.bot.get_user(int(giveaway["owner_id"])).mention,
            )
            .add_field(
                name="Created at",
                value=datetime.datetime.fromtimestamp(giveaway["started_at"]).strftime(
                    "%d/%m/%Y %H:%M:%S"
                ),
            )
            .add_field(name="Ended at", value=now.strftime("%d/%m/%Y %H:%M:%S"))
            .set_footer(text=f"Giveaway ended by {winner.mention}")
        )
        await self.db.execute(
            f"UPDATE giveaways SET ended_at = {now.timestamp()}, winner_id = {winner.id}, duration = {(now-datetime.datetime.fromtimestamp(int(giveaway['started_at']))).total_seconds()} WHERE id = {giveaway['id']}"
        )
        await ctx.send(
            embed=discord.Embed(
                title="Giveaway ended!",
                description=f"Forcefully ended giveaway with a ID of {giveaway['id']} and the winner is {winner.mention}.",
            )
        )

    @giveaway.command()
    async def list_giveaway(
        self, ctx: discord.Interaction, status: Status = "active"
    ) -> None:
        """List giveaways."""
        await ctx.defer()
        if isinstance(status, Status):
            status = status.value
        if status == "active":
            giveaways = await self.db.fetch(
                f"SELECT * FROM giveaways WHERE ended_at > {datetime.datetime.now().timestamp()}"
            )
        elif status == "ended":
            giveaways = await self.db.fetch(
                f"SELECT * FROM giveaways WHERE ended_at < {datetime.datetime.now().timestamp()}"
            )
        else:
            badarg = commands.BadArgument(
                f"Invalid status {status}. Only available options are active and ended."
            )
            badarg.param = dummy()
            badarg.param.name = "status"
            raise badarg
        if not giveaways:
            await ctx.send(
                embed=discord.Embed(
                    title="No giveaways. found with those status",
                    color=discord.Color.red(),
                )
            )
            return
        embed = discord.Embed(
            title=f"{len(giveaways)} giveaways found with status {status}",
            color=discord.Color.blurple(),
        )
        embeds = []
        for giveaway in giveaways:
            embed = discord.Embed(
                title=giveaway["title"],
                description=giveaway["description"],
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Prize", value=giveaway["prize"])
            embed.add_field(name="ID", value=giveaway["id"])
            embed.add_field(
                name="Created by",
                value=self.bot.get_user(giveaway["owner_id"]).mention,
            )
            embed.add_field(
                name="Created at",
                value=datetime.datetime.fromtimestamp(giveaway["started_at"]).strftime(
                    "%d/%m/%Y %H:%M:%S"
                ),
            )
            embed.add_field(
                name="Ended at",
                value=datetime.datetime.fromtimestamp(giveaway["ended_at"]).strftime(
                    "%d/%m/%Y %H:%M:%S"
                ),
            )
            embed.add_field(
                name="Winner",
                value=self.bot.get_user(giveaway["winner_id"]).mention
                if giveaway["winner_id"]
                else "No winner yet.",
            )
            embeds.append(embed)
        await ctx.send(embed=embed)
        if len(embeds) >= 10:  # discord limitation
            for embed in embeds:
                await ctx.send(embed=embed)
                await asyncio.sleep(0.5)
        else:
            await ctx.send(embeds=embeds)

    @giveaway.command()
    async def info(self, ctx: discord.Interaction, giveaway_id: str) -> None:
        """Get info about a giveaway."""
        await ctx.defer()
        giveaway = await self.db.fetch(
            f"SELECT * FROM giveaways WHERE id = '{giveaway_id}'"
        )
        if not giveaway:
            badarg = commands.BadArgument(f"No giveaway with ID {giveaway_id}.")
            badarg.param = dummy()
            badarg.param.name = "giveaway_id"
            raise badarg
        giveaway = giveaway[0]
        channel = self.bot.get_channel(giveaway["channel_id"])
        if channel is None:
            channel = dummy()
            channel.mention = None
        message = await channel.fetch_message(giveaway["message_id"])
        if message is None:
            message = dummy()
            message.jump_url = None
        embed = discord.Embed(
            title=giveaway["title"],
            description=giveaway["description"],
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Prize", value=giveaway["prize"])
        embed.add_field(name="ID", value=giveaway["id"])
        embed.add_field(
            name="Created by",
            value=self.bot.get_user(giveaway["owner_id"]).mention,
        )
        embed.add_field(
            name="Created at",
            value=datetime.datetime.fromtimestamp(giveaway["started_at"]).strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
        )
        embed.add_field(
            name="Ended at",
            value=datetime.datetime.fromtimestamp(giveaway["ended_at"]).strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
        )
        embed.add_field(
            name="Winner", value=self.bot.get_user(giveaway["winner_id"]).mention
        )
        embed.add_field(name="Channel", value=channel.mention)
        embed.add_field(name="Message", value=message.jump_url)
        await ctx.send(embed=embed)

    @giveaway.command()
    @commands.has_permissions(administrator=True)
    async def setup(
        self, ctx: discord.Interaction, giveaway_role: discord.Role
    ) -> None:
        """Setup giveaway role."""
        await ctx.defer()
        setup_db = await EasySQL().connect(
            host=os.environ.get("DB_HOST"),
            database="giveaways",
            user="giveaway_bot",
            password=os.environ["DB_PASS"],
        )
        await setup_db.execute(
            f"INSERT INTO setup(guild_id, giveaway_role_id) VALUES({ctx.guild.id}, {giveaway_role.id})"
        )
        await setup_db.close()
        await ctx.send(
            embed=discord.Embed(
                title="Setup complete",
                description=f"Giveaway role set to {giveaway_role.mention}",
                color=discord.Color.green(),
            )
        )

    @giveaway.command()
    async def wizard(self, ctx: discord.Interaction) -> None:
        """A helper for setting up giveaways."""
        await ctx.defer()
        await ctx.send(
            embed=discord.Embed(
                title="Giveaway Wizard",
                description="This is a wizard for setting up giveaways.\n"
                "You will be asked to provide the following information:\n"
                "1. Title\n"
                "2. Description\n"
                "3. Prize\n"
                "4. Channel (optional (say none or null for not answering))\n"
                "5. Time\n"
                "6. Condition (optional (say none or null for not answering))\n",
            )
        )

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        infos = ["title", "description", "prize", "channel", "time", "condition"]
        data = {}
        for info in infos:
            await ctx.send(
                embed=discord.Embed(
                    title=f"Please provide {info} for giveaway",
                    color=discord.Color.green(),
                )
            )
            msg = await self.bot.wait_for("message", check=check)
            data[info] = msg.content
        if data["channel"].lower() in ("none", "null"):
            data["channel"] = None
        if data["condition"].lower() in ("none", "null"):
            data["condition"] = None
        await ctx.send(
            embed=discord.Embed(
                title="Giveaway setup",
                description="Giveaway setup is complete.",
                color=discord.Color.green(),
            )
        )
        await self.create(
            ctx,
            title=data["title"],
            description=data["description"],
            prize=data["prize"],
            channel=data["channel"],
            time=data["time"],
            condition=data["condition"],
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
                winner = dummy()
                winner.mention = "No one"
            owner = await self.bot.fetch_user(giveaway["owner_id"])
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
                .add_field(name="Created by", value=owner.mention)
                .add_field(name="Created at", value=giveaway["started_at"])
                .set_footer(text=f"Giveaway ended by {message.author.name}"),
            )

            await self.db.execute(
                f"UPDATE giveaways SET winner_id = '{winner.id}' WHERE id = '{giveaway['id']}'"
            )

    @giveaway.command()
    async def modal(self, ctx: discord.Interaction) -> None:
        """
        BETA: Using modal for easier giveaway creation
        """
        await ctx.defer()
        await ctx.interaction.send_modal(giveaway_info())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Giveaways(bot))
