import disnake

from disnake.ext import commands


class EconomyCog(commands.Cog):
    """Модуль экономической системы бота."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot



    @commands.slash_command(
        name="balance",
        description="Посмотреть свой баланс или баланс другого пользователя"
    )
    async def balance(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member|None = None
    ):
        pass





def setup(bot: commands.Bot):
    bot.add_cog(EconomyCog(bot))