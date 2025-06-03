import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz
import discord
from discord.ext import commands, tasks
from discord import app_commands

from nlp import parse_command
from sheet import (
    add_task,
    mark_task_complete,
    get_tasks_due_today,
    get_all_tasks,
    edit_task,
    delete_task,
    set_user_timezone,
    get_user_timezone,
)

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Setup Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.tree.command(name="task", description="Add or complete a task using natural language")
@app_commands.describe(message="e.g. Add math review by Friday every week #school")
async def task(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    parsed = parse_command(message)

    action = parsed.get("action")
    name = parsed.get("name")
    due_date = parsed.get("due_date")
    recurrence = parsed.get("recurrence", "")
    priority = parsed.get("priority", "")

    if action == "add":
        if not name or not due_date:
            await interaction.followup.send("⚠️ Please include a task name and due date.")
            return
        add_task(str(interaction.user.id), name, due_date, recurrence, priority)
        rec_msg = f" (recurs {recurrence})" if recurrence else ""
        pri_msg = f" [#{priority}]" if priority else ""
        await interaction.followup.send(f"✅ Task added: '{name}' due {due_date}{rec_msg}{pri_msg}")
    elif action == "complete":
        if not name:
            await interaction.followup.send("⚠️ Please specify the task to mark complete.")
            return
        mark_task_complete(str(interaction.user.id), name)
        await interaction.followup.send(f"✅ Marked complete: '{name}'")
    else:
        await interaction.followup.send("❌ Couldn't understand your command. Try again.")


@bot.tree.command(name="tasks", description="See your tasks due today")
async def view_tasks(interaction: discord.Interaction):
    await interaction.response.defer()
    rows = get_tasks_due_today()
    user_tasks = [t for t in rows if t["user_id"] == str(interaction.user.id)]

    if not user_tasks:
        await interaction.followup.send("📭 You have no tasks due today.")
    else:
        formatted = "\n".join([
            f"• {t['name']} — 🏷 {t.get('priority', '')}" if t.get("priority") else f"• {t['name']}"
            for t in user_tasks
        ])
        await interaction.followup.send(f"📋 Tasks due today:\n{formatted}")


@bot.tree.command(name="all_tasks", description="See all your tasks (due and completed)")
async def all_tasks(interaction: discord.Interaction):
    await interaction.response.defer()
    rows = get_all_tasks()
    user_tasks = [t for t in rows if t["user_id"] == str(interaction.user.id)]

    if not user_tasks:
        await interaction.followup.send("🗂️ You have no tasks recorded.")
    else:
        formatted = "\n".join([
            f"• {t['name']} — Due: {t['due_date']} — ✅ Done: {t.get('complete', 'no')} — 🔁 {t.get('recurrence', '')} — 🏷 {t.get('priority', '')}"
            for t in user_tasks
        ])
        await interaction.followup.send(f"🗂️ All your tasks:\n{formatted}")


@bot.tree.command(name="add_today", description="Add a task due today")
@app_commands.describe(name="Task name due today")
async def add_today(interaction: discord.Interaction, name: str):
    user_tz = get_user_timezone(str(interaction.user.id))
    local_today = datetime.now(pytz.timezone(user_tz)).strftime("%Y-%m-%d")
    add_task(str(interaction.user.id), name, local_today)
    await interaction.response.send_message(f"✅ Task '{name}' added for today!")


@bot.tree.command(name="edit_task", description="Edit the name or due date of an existing task")
@app_commands.describe(
    original_name="The current name of the task",
    new_name="New name (optional)",
    new_due_date="New due date (optional, YYYY-MM-DD)"
)
async def edit_task_cmd(interaction: discord.Interaction, original_name: str, new_name: str = None, new_due_date: str = None):
    if not new_name and not new_due_date:
        await interaction.response.send_message("⚠️ Provide at least a new name or new due date.")
        return

    if new_due_date:
        try:
            datetime.strptime(new_due_date, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("❌ Invalid date format. Use YYYY-MM-DD.")
            return

    success = edit_task(str(interaction.user.id), original_name, new_name, new_due_date)
    if success:
        changes = []
        if new_name: changes.append(f"name → '{new_name}'")
        if new_due_date: changes.append(f"due → {new_due_date}")
        await interaction.response.send_message(f"✅ Task updated: {', '.join(changes)}")
    else:
        await interaction.response.send_message("❌ Task not found.")


@bot.tree.command(name="delete_task", description="Delete a task by name")
@app_commands.describe(name="The exact name of the task to delete")
async def delete_task_cmd(interaction: discord.Interaction, name: str):
    success = delete_task(str(interaction.user.id), name)
    if success:
        await interaction.response.send_message(f"🗑️ Deleted task: '{name}'")
    else:
        await interaction.response.send_message("❌ Task not found. Make sure the name is exactly correct.")


@bot.tree.command(name="set_timezone", description="Set your time zone (e.g., Asia/Singapore)")
@app_commands.describe(tz="Your time zone, e.g., Asia/Singapore")
async def set_timezone(interaction: discord.Interaction, tz: str):
    if tz not in pytz.all_timezones:
        await interaction.response.send_message("❌ Invalid time zone. Use a valid one like `Asia/Singapore`.")
        return
    set_user_timezone(str(interaction.user.id), tz)
    await interaction.response.send_message(f"✅ Time zone set to `{tz}`.")


@bot.tree.command(name="ping_me", description="Test if the bot can ping you")
async def ping_me(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! {interaction.user.mention}", ephemeral=True)
    try:
        await interaction.user.send("🔔 This is a DM ping test from the bot.")
    except Exception as e:
        await interaction.followup.send("❌ I couldn't DM you. Check your privacy settings.")
        print(f"DM error: {e}")


@tasks.loop(hours=1)
async def check_tasks():
    all_tasks = get_all_tasks()
    users = {}

    for task in all_tasks:
        if task.get("complete", "").lower() == "yes":
            continue

        user_id = task.get("user_id", "")
        name = task.get("name", "")
        due_date = task.get("due_date", "")
        recurrence = task.get("recurrence", "")
        priority = task.get("priority", "")

        try:
            tz = get_user_timezone(user_id)
            now = datetime.now(pytz.timezone(tz))
            today = now.strftime("%Y-%m-%d")
            tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

            if due_date in {today, tomorrow}:
                if user_id not in users:
                    users[user_id] = {"today": [], "tomorrow": []}
                users[user_id]["today" if due_date == today else "tomorrow"].append((name, priority, recurrence, due_date))

                if due_date == today and recurrence in {"daily", "weekly"}:
                    next_due = datetime.strptime(due_date, "%Y-%m-%d") + (
                        timedelta(days=1) if recurrence == "daily" else timedelta(weeks=1)
                    )
                    add_task(user_id, name, next_due.strftime("%Y-%m-%d"), recurrence, priority)

        except Exception as e:
            print(f"Reminder error for user {user_id}: {e}")

    # Send daily digests
    for user_id, grouped in users.items():
        try:
            user = await bot.fetch_user(int(user_id))
            embed = discord.Embed(title="🗓️ Task Digest", color=0x00b0f4)
            if grouped["today"]:
                embed.add_field(
                    name="✅ Tasks Due Today",
                    value="\n".join([f"• {n} {'🏷️ ' + p if p else ''}" for n, p, _, _ in grouped["today"]]),
                    inline=False
                )
            if grouped["tomorrow"]:
                embed.add_field(
                    name="🔔 Due Tomorrow",
                    value="\n".join([f"• {n} {'🏷️ ' + p if p else ''}" for n, p, _, _ in grouped["tomorrow"]]),
                    inline=False
                )
            await user.send(embed=embed)
        except Exception as e:
            print(f"Could not DM user {user_id}: {e}")


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"🟢 Logged in as {bot.user} — Synced {len(synced)} slash commands.")
    check_tasks.start()


bot.run(DISCORD_TOKEN)
