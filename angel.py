import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from discord import app_commands

from nlp import parse_command
from sheet import add_task, mark_task_complete, get_tasks_due_today

# Load environment
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Discord setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Slash command: Add or complete task
@bot.tree.command(name="task", description="Add or complete a task using natural language")
@app_commands.describe(message="e.g. Add buy milk by Friday")
async def task(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    parsed = parse_command(message)
    action, name, due_date = parsed.get("action"), parsed.get("name"), parsed.get("due_date")

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

# Slash command: View tasks due today
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


# Reminder: 2-day advance ping
@tasks.loop(hours=1)
async def check_tasks():
    target = (datetime.today() + timedelta(days=2)).strftime("%Y-%m-%d")
    tasks_due = get_tasks_due_today()

    for task in tasks_due:
        if task["due_date"] == target:
            user = await bot.fetch_user(int(task["user_id"]))
            await user.send(f"⏳ Reminder: '{task['name']}' is due in 2 days ({target})!")

# On bot ready
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🟢 Logged in as {bot.user}")
    check_tasks.start()

bot.run(DISCORD_TOKEN)
