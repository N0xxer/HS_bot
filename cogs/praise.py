"""Модуль системы похвалы пользователей.

Позволяет хвалить участников через текстовые команды
('похвалить @пользователь', 'tip @пользователь' или ответ на сообщение),
а также слэш-команды, с соблюдением суточных лимитов и КД.
Фразы и настройки загружаются из configs/praise_phrases.json.
"""

import json
import random
import re
from pathlib import Path

import disnake
from disnake.ext import commands

from functions.db_helpers import (
    add_praise,
    check_praise_availability,
    get_user_praise_stats,
)

BOT_CONFIG_PATH = Path("configs/bot_config.json")
with open(BOT_CONFIG_PATH, "r", encoding="utf-8") as f:
    bot_config = json.load(f)

PRAISE_PHRASES_PATH = Path("configs/praise_phrases.json")

PRAISE_COLOR = bot_config.get("colors", {}).get("succes", 10079334)
ERROR_COLOR = bot_config.get("colors", {}).get("error", 13395558)
INFO_COLOR = bot_config.get("colors", {}).get("info", 6737100)


def load_praise_config() -> dict:
    """Загружает фразы и параметры оформления из JSON-конфига."""
    default_config = {
        "title": "✨ ПОХВАЛА ПОЛЬЗОВАТЕЛЯ",
        "phrases": [
            "Отличная работа!",
            "Так держать!",
            "Красиво сыграно!",
            "Ты лучший!",
            "Спасибо за помощь и поддержку!",
            "Идеальное исполнение!",
        ],
    }
    if PRAISE_PHRASES_PATH.exists():
        try:
            with open(PRAISE_PHRASES_PATH, "r", encoding="utf-8") as pf:
                return json.load(pf)
        except Exception:
            return default_config
    return default_config


class PraiseCog(commands.Cog):
    """Модуль системы похвалы."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Регулярное выражение для поиска команд 'похвалить' и 'tip' с игнорированием регистра
        self.tip_regex = re.compile(
            r"^(?:похвалить|tip)(?:\s+([\s\S]*))?$",
            re.IGNORECASE,
        )

    def _extract_phrase(
        self,
        raw_comment: str | None,
        mentions: list[disnake.User | disnake.Member],
        phrases: list[str],
    ) -> str:
        """Извлекает комментарий пользователя или выбирает случайную фразу из конфига."""
        if not raw_comment:
            return random.choice(phrases) if phrases else "Отличная работа!"

        cleaned = raw_comment
        for user in mentions:
            cleaned = cleaned.replace(f"<@{user.id}>", "").replace(f"<@!{user.id}>", "")
        cleaned = cleaned.strip()

        if cleaned:
            return cleaned[:150]
        return random.choice(phrases) if phrases else "Отличная работа!"

    def _build_praise_embed(
        self,
        actor: disnake.User | disnake.Member,
        target: disnake.User | disnake.Member,
        phrase: str,
        stats: dict,
    ) -> disnake.Embed:
        """Формирует стилизованный Embed похвалы."""
        cfg = load_praise_config()
        title = cfg.get("title", "✨ ПОХВАЛА ПОЛЬЗОВАТЕЛЯ")

        embed = disnake.Embed(
            title=title,
            description=(
                f"{actor.mention} поощряет {target.mention}!\n\n"
                f"💬 **«{phrase}»**\n\n"
                f"🏆 Всего похвал у **{target.display_name}**: **{stats['total_target_praises']}**\n"
                f"📊 Ваш лимит на сегодня: **{stats['today_distinct_count']}/3** участников | "
                f"Этому участнику: **{stats['today_target_count']}/3**"
            ),
            color=PRAISE_COLOR,
        )

        embed.set_author(
            name=f"{actor.display_name} похвалил(а) {target.display_name}",
            icon_url=actor.display_avatar.url,
        )

        embed.set_thumbnail(url=target.display_avatar.url)
        return embed

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """Обработка текстовых триггеров 'похвалить @пользователь' и 'tip @пользователь'."""
        if message.author.bot or not message.guild:
            return

        content = message.content.strip()
        match = self.tip_regex.match(content)
        if not match:
            return

        raw_remainder = match.group(1)
        target: disnake.User | disnake.Member | None = None

        # 1. Если есть прямое упоминание в сообщении
        if message.mentions:
            for mentioned_user in message.mentions:
                if self.bot.user and mentioned_user.id != self.bot.user.id:
                    target = mentioned_user
                    break

        # 2. Если упоминания нет, но сообщение является ответом (Reply)
        if not target and message.reference and message.reference.message_id:
            try:
                if message.reference.resolved and isinstance(message.reference.resolved, disnake.Message):
                    target = message.reference.resolved.author
                else:
                    ref_msg = await message.channel.fetch_message(message.reference.message_id)
                    target = ref_msg.author
            except Exception:
                target = None

        # Если цель не определена
        if not target:
            embed_help = disnake.Embed(
                title="ℹ️ Как похвалить участника",
                description=(
                    "Используйте команду с упоминанием участника:\n"
                    "• `похвалить @пользователь [сообщение]`\n"
                    "• `tip @пользователь [сообщение]`\n\n"
                    "Или ответьте на его сообщение словом `похвалить` или `tip`!"
                ),
                color=INFO_COLOR,
            )
            await message.reply(embed=embed_help, delete_after=15)
            return

        # Проверка: бот
        if target.bot:
            await message.reply("🤖 Боты не принимают похвалу! Похвалите живого участника.")
            return

        # Проверка лимитов и КД
        can_praise, error_reason, _ = await check_praise_availability(message.author.id, target.id)
        if not can_praise:
            embed_err = disnake.Embed(
                title="⏳ Ограничение похвалы",
                description=error_reason,
                color=ERROR_COLOR,
            )
            await message.reply(embed=embed_err)
            return

        cfg = load_praise_config()
        phrase = self._extract_phrase(raw_remainder, message.mentions, cfg.get("phrases", []))
        stats = await add_praise(message.author.id, target.id, phrase)
        embed = self._build_praise_embed(message.author, target, phrase, stats)
        await message.reply(embed=embed)

    @commands.slash_command(
        name="tip",
        description="Похвалить участника (до 3 участников в день)",
    )
    async def tip_command(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member = commands.Param(description="Кого вы хотите похвалить"),
        phrase: str | None = commands.Param(default=None, description="Ваш комментарий или похвала (опционально)"),
    ):
        """Слэш-команда похвалы пользователя."""
        if member.bot:
            await inter.response.send_message(
                "🤖 Боты не принимают похвалу! Похвалите живого участника.",
                ephemeral=True,
            )
            return

        can_praise, error_reason, _ = await check_praise_availability(inter.author.id, member.id)
        if not can_praise:
            embed_err = disnake.Embed(
                title="⏳ Ограничение похвалы",
                description=error_reason,
                color=ERROR_COLOR,
            )
            await inter.response.send_message(embed=embed_err, ephemeral=True)
            return

        cfg = load_praise_config()
        phrases_list = cfg.get("phrases", [])
        default_phrase = random.choice(phrases_list) if phrases_list else "Отличная работа!"
        selected_phrase = phrase.strip()[:150] if phrase and phrase.strip() else default_phrase

        stats = await add_praise(inter.author.id, member.id, selected_phrase)
        embed = self._build_praise_embed(inter.author, member, selected_phrase, stats)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(
        name="praise",
        description="Показать текущие настройки и фразы системы похвалы",
    )
    async def praise_main(
        self,
        inter: disnake.ApplicationCommandInteraction,
    ):
        pass

    @praise_main.sub_command(
        name="stats",
        description="Посмотреть статистику похвал (получено и отдано)",
    )
    async def praise_stats(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member | None = commands.Param(default=None, description="Пользователь для просмотра статистики"),
    ):
        """Просмотр статистики похвал."""
        target = member or inter.author
        stats = await get_user_praise_stats(target.id)

        embed = disnake.Embed(
            title=f"📊 Статистика похвал: {target.display_name}",
            description=(
                f"📥 **Получено похвал всего**: `{stats['total_received']}`\n"
                f"🌟 **Получено сегодня**: `{stats['today_received']}`\n\n"
                f"📤 **Отдано похвал всего**: `{stats['total_given']}`\n"
                f"👥 **Похвалено участников сегодня**: `{stats['today_distinct']}/3`"
            ),
            color=PRAISE_COLOR,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text="Лимиты обновляются каждый день в 00:00 по МСК")
        await inter.response.send_message(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(PraiseCog(bot))
