import os
import discord
import datetime
import asyncio
from replit import db
from discord.ext import tasks
from server import keep_alive

intent = discord.Intents.default()
intent.members = True
intent.message_content = True

client = discord.Client(intents=intent)


@client.event
async def on_ready():
  check_reminder.start()
  print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
  server_id = str(message.guild.id)

  if message.author == client.user:
    return

  if message.content.startswith('$c'):
    channel = message.channel

    # Get task description
    await channel.send('What is your task description?')
    msg1 = await client.wait_for('message')

    # Add task description with empty member list to database
    task = str(msg1.content)
    if not db.get(server_id):
      db[server_id] = [{
        "task": task,
        "members": [],
        "timechange": 0,
        "endtime": datetime.datetime.utcnow().isoformat(),
        "channel_id": channel.id
      }]
    else:
      db[server_id].append({
        "task": task,
        "members": [],
        "timechange": 0,
        "endtime": datetime.datetime.utcnow().isoformat(),
        "channel_id": channel.id
      })

    # Verify scheduled reminders
    await channel.send(
      f'Your task is {task}! How often do you want this task to swap people? Please respond in days.'
    )

    msg = await client.wait_for('message')

    try:
      updated_time = datetime.datetime.now() + datetime.timedelta(days=int(msg.content))
      db[server_id][len(db[server_id]) - 1]["endtime"] = updated_time.isoformat()
      db[server_id][len(db[server_id]) - 1]["timechange"] = int(msg.content)
    except:
      await channel.send("You did not provide an integer number of days")

    # Ask for first member
    await channel.send(
      "What member do you want to add to the rotation swap first?")

    # Add member to database and prompt for another member
    loop = True
    while (loop == True):
      msg = await client.wait_for('message')
      try:
        db[server_id][len(db[server_id]) - 1]["members"].append(f"<@{msg.mentions[0].id}>")
      except:
        await channel.send("You didn't mention a person")

      await channel.send(
        f'Added @{msg.mentions[0].name}#{msg.mentions[0].discriminator}! \n {gen_member_list(db[server_id][len(db[server_id]) - 1]["members"])} \n Do you want to add anyone else? (Y or N)'
      )
      msg = await client.wait_for('message')
      if (msg.content == "N" or msg.content == "n"):
        await channel.send("Great!")
        loop = False
        break
      else:
        await channel.send("Who do you want to add?")

  if message.content.startswith('$list'):
    await message.channel.send(gen_task_list(server_id))


@tasks.loop(seconds=60)
async def check_reminder():
  print("Update")
  keys = db.keys()
  for key in keys:
    tasks = db[key]
    for task in tasks:
      if (datetime.datetime.fromisoformat(task['endtime']) <= datetime.datetime.now()):
        channel = client.get_channel(int(task['channel_id']))
        await channel.send(
          f"The task *{task['task']}* has been swapped to {task['members'][0]}"
        )
        task['members'].append(task['members'][0])
        task['members'].remove(0)

        newtime = datetime.datetime.now() + datetime.timedelta(days=int(task['timechange']))
        task['endtime'] = newtime.isoformat()


def gen_member_list(memberlist):
  res = "Current members:"
  for member in memberlist:
    res += f"{member} "
  return res


def gen_task_list(server_id):
  res = "*Tasks: *"
  counter = 1
  if not db.get(server_id):
    return "You have no tasks for this server!"
  for task in db[server_id]:
    res += f"\nTask {counter}: {task['task']}"
    res += "\n" + gen_member_list(task['members'])
    counter += 1
  return res

@check_reminder.before_loop
async def before_check_reminder():
  print("Starting job")

keep_alive()
client.run(os.environ['TOKEN'])
