import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from discord import app_commands

from nlp import parse_command
from sheet import add_task, mark_task_complete, get_tasks_due_today, get_all_tasks

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Set up Discord bot intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Slash command: Add or complete task using natural language
@bot.tree.command(name="task", description="Add or complete a task using natural language")
@app_commands.describe(message="e.g. Add buy milk by Friday")
async def task(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    parsed = parse_command(message)
    action = parsed.get("action")
    name = parsed.get("name")
    due_date = parsed.get("due_date")

    if action == "add":
        if not due_date:
            await interaction.followup.send("⚠️ Please specify a due date.")
            return
        add_task(interaction.user.id, name, due_date)
        await interaction.followup.send(f"✅ Task added: '{name}' due {due_date}")
    elif action == "complete":
        mark_task_complete(interaction.user.id, name)
        await interaction.followup.send(f"✅ Marked complete: '{name}'")
    else:
        await interaction.followup.send("❌ Could not understand the command. Try again!")

# Slash command: List today's tasks
@bot.tree.command(name="tasks", description="See tasks due today")
async def view_tasks(interaction: discord.Interaction):
    await interaction.response.defer()
    rows = get_tasks_due_today()
    user_tasks = [t for t in rows if t["user_id"] == str(interaction.user.id)]

    if not user_tasks:
        await interaction.followup.send("📭 You have no tasks due today.")
    else:
        formatted = "\n".join([f"• {t['name']}" for t in user_tasks])
        await interaction.followup.send(f"📋 Tasks due today:\n{formatted}")

# Slash command: See all tasks
@bot.tree.command(name="all_tasks", description="See all your tasks (due and completed)")
async def all_tasks(interaction: discord.Interaction):
    await interaction.response.defer()
    rows = get_all_tasks()
    all_user_tasks = [t for t in rows if t["user_id"] == str(interaction.user.id)]

    if not all_user_tasks:
        await interaction.followup.send("🗂️ You have no tasks recorded.")
    else:
        formatted = "\n".join([
            f"• {t['name']} — Due: {t['due_date']} — ✅ Done: {t['complete']}"
            for t in all_user_tasks
        ])
        await interaction.followup.send(f"🗂️ All your tasks:\n{formatted}")

# Slash command: Add task due today
@bot.tree.command(name="add_today", description="Add a task due today")
@app_commands.describe(name="Task name due today")
async def add_today(interaction: discord.Interaction, name: str):
    today = datetime.today().strftime("%Y-%m-%d")
    add_task(interaction.user.id, name, today)
    await interaction.response.send_message(f"✅ Task '{name}' added for today!")

# Periodic reminder for tasks due today and tomorrow
@tasks.loop(hours=1)
async def check_tasks():
    today = datetime.today().strftime("%Y-%m-%d")
    tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    all_tasks = get_all_tasks()

    for task in all_tasks:
        if task["complete"].lower() == "yes":
            continue

        due_date = task["due_date"]
        name = task["name"]
        user_id = task["user_id"]

        try:
            user = await bot.fetch_user(int(user_id))
            if due_date == today:
                await user.send(f"📅 Reminder: '{name}' is **due today**!")
            elif due_date == tomorrow:
                await user.send(f"🔔 Heads up: '{name}' is due **tomorrow**!")
        except Exception as e:
            print(f"Error sending reminder to user {user_id}: {e}")

# On bot ready
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🟢 Logged in as {bot.user}")
    check_tasks.start()

# Run the bot
bot.run(DISCORD_TOKEN)
