"""Модуль сервера SOON."""

import disnake
from disnake.ext import commands


class SOONCog(commands.Cog):
    """Модуль сервера SOON."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot


def setup(bot: commands.Bot):
    bot.add_cog(SOONCog(bot))
