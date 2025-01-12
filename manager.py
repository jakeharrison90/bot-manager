from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
import os
import shlex
import subprocess
import time
import psutil
from time import perf_counter

# Telegram bot API details
api_id = 21169722
api_hash = "99190a46eadbfbb4a857215c5cc4637e"
bot_token = "8094419090:AAGgGQH7i9-0cRZ-xvP76U6QOrHtf5fJQPA"

# Your Telegram user IDs to send notifications
admin_user_ids = [6387028671, 6816341239, 6204011131]  # Replace with actual admin user IDs

# Password for non-admin access
user_password = "11223344"
authorized_users = {}  # Dictionary to store user_id and authorization time

# Pyrogram client
app = Client("bot_manager", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Directory containing bot subdirectories
BOTS_DIR = "/home/container"
processes = {}

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Detect bots dynamically
def detect_bots():
    bots = {}
    if os.path.exists(BOTS_DIR):
        for item in os.listdir(BOTS_DIR):
            bot_path = os.path.join(BOTS_DIR, item, "main.py")
            if os.path.isfile(bot_path):
                bots[item] = bot_path
    logging.info(f"Detected bots: {list(bots.keys())}")
    return bots

BOTS = detect_bots()

# Helper functions for bot management
def install_missing_modules(bot_path):
    try:
        subprocess.run(["pip", "install", "-r", os.path.join(os.path.dirname(bot_path), "requirements.txt")], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Installed missing modules for {bot_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install missing modules for {bot_path}: {e}")

def start_bot(bot_name):
    bot_path = BOTS.get(bot_name)
    if not bot_path:
        return f"<b>Bot '{bot_name}' not found!</b>"
    if bot_name in processes:
        return f"Bot '{bot_name}' is already running!"
    logging.info(f"Starting bot '{bot_name}'")
    install_missing_modules(bot_path)
    log_file = f"/home/container/{bot_name}_log.txt"
    with open(log_file, "w") as log:
        process = subprocess.Popen(["python3", bot_path], stdout=log, stderr=log)
        process.start_time = time.time()
        processes[bot_name] = process
    logging.info(f"Bot '{bot_name}' started")
    return f"Bot '{bot_name}' started."

def stop_bot(bot_name):
    process = processes.get(bot_name)
    if process:
        logging.info(f"Stopping bot '{bot_name}'")
        process.terminate()
        processes.pop(bot_name, None)
        logging.info(f"Bot '{bot_name}' stopped")
        return f"Bot '{bot_name}' stopped."
    return f"Bot '{bot_name}' is not running."

def get_logs(bot_name):
    log_file = f"/home/container/{bot_name}_log.txt"
    if os.path.exists(log_file):
        with open(log_file, "r") as log:
            return f"<b>Logs for {bot_name}:</b>\n<pre>{log.read()[-4000:]}</pre>"
    return "<b>No logs found.</b>"

def update_bot(bot_name):
    bot_path = os.path.dirname(BOTS.get(bot_name, ""))
    if not bot_path or not os.path.isdir(bot_path):
        return f"<b>Bot '{bot_name}' not found!</b>"
    try:
        logging.info(f"Updating bot '{bot_name}'")
        subprocess.run(["git", "-C", bot_path, "pull"], check=True, text=True, stdout=subprocess.PIPE)
        logging.info(f"Bot '{bot_name}' updated successfully")
        return f"Bot '{bot_name}' updated successfully."
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update bot '{bot_name}': {e}")
        return f"Failed to update bot '{bot_name}': {e}"

def bot_status():
    status = []
    for bot_name in BOTS:
        process = processes.get(bot_name)
        status.append(f"<b>{bot_name}:</b> {'<code>Running</code>' if process and process.poll() is None else '<code>Stopped</code>'}")
    return "\n".join(status)

def calculate_uptime(process):
    if process and process.poll() is None:
        uptime_seconds = time.time() - process.start_time
        return time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
    return "N/A"

def get_server_details():
    uptime = subprocess.check_output("uptime", shell=True).decode().strip()
    disk_usage = subprocess.check_output("df -h /", shell=True).decode().strip()
    memory = psutil.virtual_memory()
    ram_usage = f"RAM Usage: {memory.used / (1024 ** 3):.2f} GB / {memory.total / (1024 ** 3):.2f} GB ({memory.percent}%)"
    cpu_load = f"CPU Load: {psutil.cpu_percent()}%"
    bot_details = []
    for bot_name, process in processes.items():
        bot_status = "Running" if process.poll() is None else "Stopped"
        bot_uptime = calculate_uptime(process) if bot_status == "Running" else "N/A"
        bot_details.append(f"{bot_name}: {bot_status} | Uptime: {bot_uptime}")
    return f"<b>Server Uptime:</b>\n<pre>{uptime}</pre>\n\n<b>Disk Usage:</b>\n<pre>{disk_usage}</pre>\n\n<b>{ram_usage}</b>\n<b>{cpu_load}</b>\n\n" + "\n".join(bot_details)

def clone_repo(repo_url):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    clone_path = os.path.join(BOTS_DIR, repo_name)
    if os.path.exists(clone_path):
        return f"<b>Repository '{repo_name}' already exists.</b>"
    try:
        logging.info(f"Cloning repository '{repo_name}'")
        subprocess.run(["git", "clone", repo_url, clone_path], check=True, text=True, stdout=subprocess.PIPE)
        BOTS[repo_name] = os.path.join(clone_path, "main.py")
        logging.info(f"Repository '{repo_name}' cloned successfully")
        return f"<b>Repository '{repo_name}' cloned successfully.</b>"
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to clone repository '{repo_name}': {e}")
        return f"<b>Failed to clone repository '{repo_name}': {e}</b>"

# Helper function to check authorization
def is_authorized(user_id):
    # Admins are always authorized
    if user_id in admin_user_ids:
        return True
    # Check if user is in authorized_users and if the authorization is still valid
    if user_id in authorized_users:
        auth_time = authorized_users[user_id]
        if time.time() - auth_time < 3600:  # Authorization valid for 1 hour
            return True
        else:
            # Remove expired authorization
            authorized_users.pop(user_id, None)
    return False

# Inline keyboards
@app.on_message(filters.command("start") & filters.private)
async def start(_, message: Message):
    if not is_authorized(message.from_user.id):
        return await message.reply("<b>Unauthorized! This command is for authorized users only.</b>")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("My Bots", callback_data="my_bots"),
         InlineKeyboardButton("Status", callback_data="status")]
    ])
    await message.reply("<b>Welcome! Choose an option:</b>", reply_markup=keyboard)

@app.on_message(filters.command("shell") & filters.private)
async def shell_command(_, message: Message):
    if not is_authorized(message.from_user.id):
        return await message.reply("<b>Unauthorized! This command is for authorized users only.</b>")
    if len(message.command) < 2:
        return await message.reply("<b>Specify the shell command after /shell.</b>")
    cmd_text = message.text.split(maxsplit=1)[1]
    cmd_args = shlex.split(cmd_text)
    try:
        cmd_obj = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as e:
        return await message.reply(f"<b>Error starting command:</b>\n<code>{str(e)}</code>")
    char = "#" if os.getuid() == 0 else "$"
    text = f"<b>{char}</b> <code>{cmd_text}</code>\n\n<b>Running...</b>"
    sent_message = await message.reply(text)
    try:
        start_time = perf_counter()
        stdout, stderr = cmd_obj.communicate(timeout=60)
        stop_time = perf_counter()
        text = f"<b>{char}</b> <code>{cmd_text}</code>\n\n"
        if stdout:
            text += f"<b>Output:</b>\n<pre>{stdout}</pre>\n\n"
        if stderr:
            text += f"<b>Error:</b>\n<pre>{stderr}</pre>\n\n"
        if not stdout and not stderr:
            text += "No output was produced."
        text += f"<b>Completed in {round(stop_time - start_time, 5)} seconds with code {cmd_obj.returncode}</b>"
    except subprocess.TimeoutExpired:
        cmd_obj.kill()
        text += "\n\n<b>Timeout expired (60 seconds)</b>"
    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            await sent_message.edit_text(text[i:i + 4096])
    else:
        await sent_message.edit_text(text)
    cmd_obj.kill()

@app.on_message(filters.command("clone") & filters.private)
async def clone_command(_, message: Message):
    if not is_authorized(message.from_user.id):
        return await message.reply("<b>Unauthorized! This command is for authorized users only.</b>")
    if len(message.command) < 2:
        return await message.reply("<b>Specify the repository URL after /clone.</b>")
    repo_url = message.text.split(maxsplit=1)[1]
    result = clone_repo(repo_url)
    await message.reply(result)

@app.on_message(filters.text & filters.private)
async def password_listener(_, message: Message):
    if message.text.strip() == user_password:
        authorized_users[message.from_user.id] = time.time()
        await message.reply("<b>Password accepted. Temporary access granted for 1 hour.</b>")
        await message.delete()


@app.on_callback_query()
async def callback_handler(client, callback_query):
    if not is_authorized(callback_query.from_user.id):
        return await callback_query.answer("<b>Unauthorized! This action is for authorized users only.</b>", show_alert=True)
    data = callback_query.data
    if data == "my_bots":
        bot_buttons = [[InlineKeyboardButton(bot_name, callback_data=f"bot_{bot_name}")]
                       for bot_name in BOTS]
        bot_buttons.append([InlineKeyboardButton("Back", callback_data="back")])
        await callback_query.message.edit("<b>Select a bot:</b>", reply_markup=InlineKeyboardMarkup(bot_buttons))
    elif data.startswith("bot_"):
        bot_name = data.split("_", 1)[1]
        action_buttons = [
            [InlineKeyboardButton("Start", callback_data=f"start_{bot_name}"),
             InlineKeyboardButton("Stop", callback_data=f"stop_{bot_name}")],
            [InlineKeyboardButton("Logs", callback_data=f"logs_{bot_name}"),
             InlineKeyboardButton("Update", callback_data=f"update_{bot_name}")],
            [InlineKeyboardButton("Back", callback_data="my_bots")]
        ]
        await callback_query.message.edit(f"<b>Actions for {bot_name}:</b>", reply_markup=InlineKeyboardMarkup(action_buttons))
    elif data == "status":
        server_details = get_server_details()
        await callback_query.message.edit(f"<b>Status:</b>\n\n{server_details}")
    elif data.startswith("start_"):
        bot_name = data.split("_", 1)[1]
        result = start_bot(bot_name)
        await callback_query.answer(result, show_alert=True)
    elif data.startswith("stop_"):
        bot_name = data.split("_", 1)[1]
        result = stop_bot(bot_name)
        await callback_query.answer(result, show_alert=True)
    elif data.startswith("logs_"):
        bot_name = data.split("_", 1)[1]
        logs = get_logs(bot_name)
        await callback_query.message.reply(logs)
    elif data.startswith("update_"):
        bot_name = data.split("_", 1)[1]
        result = update_bot(bot_name)
        await callback_query.answer(result, show_alert=True)
    elif data == "back":
        main_menu = InlineKeyboardMarkup([
            [InlineKeyboardButton("My Bots", callback_data="my_bots"),
             InlineKeyboardButton("Status", callback_data="status")]
        ])
        await callback_query.message.edit("<b>Welcome! Choose an option:</b>", reply_markup=main_menu)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Bot manager started. Use Telegram commands to interact.")
    for bot_name in BOTS:
        start_bot(bot_name)
    app.run()
