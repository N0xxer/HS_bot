"""Пользовательский модуль системы бота.

Основной модуль для работы с пользователями бота.
"""

import disnake
from disnake.ext import commands

from functions.db_helpers import get_user_info


class UsersCog(commands.Cog):
    """Пользовательский класс системы бота."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="profile",
        description="Посмотреть свой профиль или профиль другого пользователя",
    )
    async def profile(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member | None = None,
    ):
        target = member or inter.author
        role = await get_user_info(target.id, "global_role") or "Пользователь"
        rating = await get_user_info(target.id, "rating") or 0

        embed = disnake.Embed(
            title=f"Профиль: {target.display_name}",
            description=(
                f"**Глобальная роль**: {role}\n"
                f"**Рейтинг**: {rating}"
            ),
            color=disnake.Color.blue(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await inter.response.send_message(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(UsersCog(bot))
