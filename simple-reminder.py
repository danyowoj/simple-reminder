from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone

load_dotenv()  # загружаем переменные из .env
TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.all()
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

reminders = []

@app_commands.describe(
    event_id="Выберите событие",
    before="За сколько минут до начала прислать напоминание",
    message="Текст напоминания",
    roles="Роли через запятую (по имени)"
)
@bot.tree.command(name="remind", description="Создать напоминание для мероприятия")
async def remind(
    interaction: discord.Interaction,
    event_id: str,
    before: int,
    message: str = "Не забудьте о событии!",
    roles: str = None
):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    try:
        event = await guild.fetch_scheduled_event(int(event_id))
    except Exception:
        await interaction.followup.send("❌ Событие не найдено.", ephemeral=True)
        return

    reminder_time = event.start_time - timedelta(minutes=before)

    role_ids = []
    if roles:
        role_names = [r.strip() for r in roles.split(",")]
        for name in role_names:
            role = discord.utils.get(guild.roles, name=name)
            if role:
                role_ids.append(role.id)

    reminders.append({
        "event_id": event.id,
        "time": reminder_time,
        "message": message,
        "roles": role_ids,
        "channel": interaction.channel.id
    })

    await interaction.followup.send(
        f"✅ Напоминание для события **{event.name}** создано!\n"
        f"Будет отправлено за {before} мин. до начала.\n"
        f"Роли: {', '.join(roles.split(',')) if roles else '—'}"
    )

# === Проверка напоминаний каждые 60 секунд ===
@tasks.loop(seconds=60)
async def check_reminders():
    now = datetime.now(timezone.utc)
    for reminder in list(reminders):
        if now >= reminder["time"]:
            guild = bot.get_guild(bot.guilds[0].id)
            event = await guild.fetch_scheduled_event(reminder["event_id"])
            channel = bot.get_channel(reminder["channel"])

            if channel and event:
                role_mentions = " ".join(f"<@&{rid}>" for rid in reminder["roles"]) if reminder["roles"] else ""
                await channel.send(
                    f"{reminder['message']}\n"
                    f"{event.url}\n"
                    f"{role_mentions}"
                )

            reminders.remove(reminder)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен!")
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизированы {len(synced)} команд(ы).")
    except Exception as e:
        print(f"Ошибка синхронизации: {e}")

    check_reminders.start()

bot.run(TOKEN)
