import random
import string
import discord


def random_id(length: int = 10) -> str:
    """Generate a random string."""
    return "".join([random.choice(string.digits) for _ in range(length)])


class dummy:
    pass


class giveaway_info(discord.ui.Modal, title="Giveaway infos"):
    label = discord.ui.TextInput(label="Giveaway label", placeholder="Giveaway label")
    description = discord.ui.TextInput(
        label="Giveaway description", placeholder="Giveaway description"
    )
    time = discord.ui.TextInput(label="Giveaway time", placeholder="Giveaway time")
    prize = discord.ui.TextInput(label="Giveaway prize", placeholder="Giveaway prize")
    channel = discord.ui.TextInput(
        label="Giveaway channel", placeholder="Giveaway channel"
    )
    condition = discord.ui.TextInput(
        label="Giveaway condition", placeholder="Giveaway condition"
    )

    async def on_submit(self, interaction: discord.Interaction):
        ctx = await interaction.client.get_context(interaction)
        await ctx.invoke(
            ctx.bot.get_command("giveaway create"),
            title=self.label.value,
            description=self.description.value,
            time=self.time.value,
            prize=self.prize.value,
            channel=self.channel.value,
            condition=self.condition.value,
        )
