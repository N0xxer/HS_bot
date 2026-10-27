"""Модуль сервера Aetherial

Команды для сервера Aetherial.
"""

import json
from pathlib import Path

import disnake
from disnake.ext import commands

from functions.db_helpers import (
    get_aetherial_user_info,
    get_aetherial_user_with_role,
    update_aetherial_user_info,
)

SERVERS_CONFIG_PATH = Path("configs/servers_config.json")
with open(SERVERS_CONFIG_PATH, "r", encoding="utf-8") as f:
    server_config = json.load(f)

BOT_CONFIG_PATH = Path("configs/bot_config.json")
with open(BOT_CONFIG_PATH, "r", encoding="utf-8") as f:
    bot_config = json.load(f)

AETHERIAL_NAME = server_config.get("aetherial", {}).get("name", "Aetherial")


class AetherialCog(commands.Cog):
    """Модуль сервера Aetherial
    
    Команды для сервера Aetherial.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="aetherial",
        description=f"Команда для сервера {AETHERIAL_NAME}",
    )
    async def aetherial(
        self, 
        inter: disnake.ApplicationCommandInteraction,
    ):
        pass

    # INFO

    @aetherial.sub_command(
        name="info",
        description=f"Получить информацию о сервере {AETHERIAL_NAME}",
    )
    async def aetherial_info(
        self, 
        inter: disnake.ApplicationCommandInteraction,
    ):
        description = server_config.get("aetherial", {}).get("description", "")
        heads = await get_aetherial_user_with_role("head_of_project")
        if not heads:
            heads = await get_aetherial_user_with_role("head")

        mentions = [f"<@{uid}>" for uid in heads]
        head_mention = " ".join(mentions) if mentions else "Не назначен"

        message = disnake.ui.Container(
            disnake.ui.TextDisplay(content=f"## {AETHERIAL_NAME}"),
            disnake.ui.TextDisplay(content=f"**Описание**: {description}"),
            disnake.ui.TextDisplay(content=f"**Глава Проекта**: {head_mention}"),
        )

        await inter.response.send_message(components=message)

    # PROFILE

    @aetherial.sub_command(
        name="profile",
        description=f"Получить информацию о профиле пользователя на сервере {AETHERIAL_NAME}",
    )
    async def aetherial_profile(
        self, 
        inter: disnake.ApplicationCommandInteraction,
    ):
        user_id = inter.user.id

        local_role = await get_aetherial_user_info(user_id, "local_role") or "ПУСТО"
        
        pass_data = await get_aetherial_user_info(user_id, "pass")
        has_pass = "Отсутствует" if pass_data == 0 else "Есть"

        wipes = await get_aetherial_user_info(user_id, "wipes") or "ПУСТО"

        message = disnake.Embed(
            title=f"Профиль пользователя {inter.user.display_name}",
            description=(
                f"**Локальная роль**: {local_role}\n"
                f"**Пропуск**: {has_pass}\n"
                f"**Вайпы**: {wipes}"
            ),
            color=bot_config.get("colors", {}).get("info", 6737100),
        )

        await inter.response.send_message(embed=message)


def setup(bot: commands.Bot):
    bot.add_cog(AetherialCog(bot))
