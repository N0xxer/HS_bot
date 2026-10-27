import json
import os
import subprocess
import sys
from pathlib import Path

import disnake
from disnake.ext import commands

CONFIG_PATH = Path("configs/bot_config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
    bot_config = json.load(config_file)


class DeveloperCog(commands.Cog):
    """Модуль управления ботом для разработчика и общая информация."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="about",
        description="Информация о боте и разработчике",
    )
    async def about(self, inter: disnake.ApplicationCommandInteraction):
        """Выводит краткую сводку о проекте."""
        info_text = "### Информация о боте"
        developer = f"Разработчик: <@{bot_config['developer']['id']}> ({bot_config['developer']['name']})"
        ping = f"🏓 **Пинг:** {round(self.bot.latency * 1000)}ms"

        message = disnake.ui.Container(
            disnake.ui.TextDisplay(content=info_text),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(content=developer),
            disnake.ui.TextDisplay(content=ping),
            disnake.ui.Separator(),
        )
        await inter.response.send_message(components=message)

    async def cog_autocomplete(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        cogs = [ext.replace("cogs.", "") for ext in self.bot.extensions.keys()]
        filtered_cogs = [
            cog for cog in cogs if user_input.lower() in cog.lower()
        ]
        return filtered_cogs[:25]

    @commands.slash_command(
        name="reload",
        description="[DEV] Перезагрузить конкретный cog (Только для владельца)",
    )
    @commands.is_owner()
    async def reload_cog(
        self,
        inter: disnake.ApplicationCommandInteraction,
        cog_name: str = commands.Param(autocomplete=cog_autocomplete),
    ):
        try:
            formatted_name = (
                cog_name if cog_name.startswith("cogs.") else f"cogs.{cog_name}"
            )

            self.bot.reload_extension(formatted_name)
            await inter.response.send_message(
                f"✅ Модуль `{formatted_name}` успешно перезагружен!",
                ephemeral=True,
            )
        except Exception as e:
            await inter.response.send_message(
                f"❌ Ошибка при перезагрузке `{cog_name}`:\n```{e}```",
                ephemeral=True,
            )

    @commands.slash_command(
        name="restart",
        description="[DEV] Полная перезагрузка бота (Только для владельца)",
    )
    @commands.is_owner()
    async def restart_bot(self, inter: disnake.ApplicationCommandInteraction):
        """Безопасный перезапуск бота с корректным закрытием сессий и соединений."""
        await inter.response.send_message("🔄 Перезапуск бота...", ephemeral=True)

        try:
            await self.bot.close()
        except Exception:
            pass

        if sys.platform == "win32":
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)

    async def cog_slash_command_error(
        self, inter: disnake.ApplicationCommandInteraction, error: Exception
    ):
        """Обработчик ошибок для команд разработчика."""
        if isinstance(error, commands.NotOwner):
            await inter.response.send_message(
                "⛔ У вас нет прав для использования этой команды. Доступ разрешен только владельцу бота.",
                ephemeral=True,
            )
        else:
            await inter.response.send_message(
                f"❌ Произошла ошибка при выполнении команды:\n```{error}```",
                ephemeral=True,
            )


def setup(bot: commands.Bot):
    bot.add_cog(DeveloperCog(bot))
