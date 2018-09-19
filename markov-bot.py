print('------')
print("Logging in now...")
import discord
import asyncio

import sqlite3, copy, random, traceback, collections, urllib.request, urllib, json, sys, time, configparser
config = configparser.ConfigParser()
config.read('config.cfg')

bot_key = config['DEFAULT']['BOT_KEY']
bot_name = config['DEFAULT']['BOT_NAME']
bot_prefix = config['DEFAULT']['BOT_PREFIX']
bot_trainning_channels = config['DEFAULT']['BOT_TRAINNING_CHANNELS'].split(",")

train_in_all = "*" in bot_trainning_channels

sys.path.append(".")
import mask
con = sqlite3.connect("markov.db")
con.execute("CREATE TABLE IF NOT EXISTS main (key TEXT, value TEXT, count INTEGER);")
con.execute("CREATE INDEX IF NOT EXISTS the_index ON main (key, value)")
con.execute("CREATE TABLE IF NOT EXISTS poll_users (user INT, vote INT);")
con.execute("CREATE TABLE IF NOT EXISTS poll_options (id INT, option TEXT);")

client = discord.Client()

def allowed(x):
  if x == "🛑": return False
  if x == ":octagonal_sign:": return False
  if x[0] == "<" and x[1] == "@": return False
  if x == (bot_prefix + bot_name): return False
  return True

def make_ok(x):
  return [x for x in x if allowed(x)]

def markov_add(m):
  words = m.split()
  words = make_ok(words)
  for i in range(len(words) - 1):
    exists = con.execute("SELECT count FROM main WHERE key = ? AND value = ?", [words[i], words[i + 1]]).fetchall()
    if len(exists) == 0:
      con.execute("INSERT INTO main (key, value, count) VALUES (?, ?, ?)", [words[i], words[i + 1], 1])
    else:
      con.execute("UPDATE main SET count = count + 1 WHERE key = ? AND value = ?", [words[i], words[i + 1]])
  con.commit()

def random_word():
  #return con.execute("SELECT key FROM main ORDER BY RANDOM() LIMIT 1;").fetchone()[0]
  count = con.execute("SELECT COUNT(*) FROM main").fetchone()[0]
  index = random.randint(0, count)
  return con.execute("SELECT key FROM main LIMIT 1 OFFSET " + str(index)).fetchone()[0]

async def react(message, success):
  emoji = "✅" if success else "❎"
  if message.channel.permissions_for(message.server.me).add_reactions:
    print("Permission to react, reacting")
    try:
      await client.add_reaction(message, emoji)
    except:
      await client.send_message(message.channel, "Failed to react with " + emoji)
      await client.send_message(message.channel, "```" + traceback.format_exc() + "```")
  else:
    print("No permission to react, sending message")
    client.send_message(message.channel, "No permission to react with " + emoji);
def make_message(arg = False):
  message = []
  debug = arg == "debug"
  #debug = True
  word = False;
  length = 20
  if arg:
    try:
      arg = int(arg)
      length = min(arg, 300)
      print("Set length to arg " + str(length))
    except:
      word = arg
      print("Set initial word to arg " + word)
  if not word: word = random_word()
  for x in range(length):
    message.append(word)
    try:
      words = con.execute("SELECT value, count FROM main WHERE key = ?", [word]).fetchall()
      words = [[x[0]] * int(x[1]) for x in words]
      flattened = []
      for x in words: flattened += x;
      word = random.choice(flattened)
    except:
      print(traceback.format_exc())
      print("failed to find next word for " + word)
      if debug: message.append(":octagonal_sign:")
      word = random_word();
  message = make_ok(message)
  return " ".join(message)

def get_percents(word):
  words = con.execute("SELECT value, count FROM main WHERE key = ?", [word]).fetchall()
  if len(words) == 0: return "Never seen that word before"
  words = [[x[0], int(x[1])] for x in words]
  total = sum([x[1] for x in words])
  words.sort(key = lambda x: x[1], reverse = True)
  print(words[:10])
  message = []
  for block in words:
    if len(message) > 10: break
    message.append(block[0] + ": " + str(float(block[1] * 100)/total)[:4] + "%")
  return ", ".join(message) + "\nWord seen " + str(total) + " time" + ("s" if total != 1 else "")

def top(limit):
  if limit < 1:
    limit = 10
  elif limit > 50:
    limit = 50
  words = con.execute("SELECT key, SUM(count) FROM main GROUP BY key ORDER BY SUM(count) DESC LIMIT ?", [limit])
  message = ""
  i=1
  for word in words:
    message += str(i) + ") \"" + word[0] + "\" seen " + str(word[1]) + " times\n"
    i += 1
  return message
  
@client.event
async def on_ready():
  print('Logged in as')
  print(client.user.name)
  print(client.user.id)
  print('------')

@client.event
async def on_message(message):
  start = time.time()
  #print("Author: ", message.author, type(message.author))
  #print("Channel: ", message.channel, type(message.channel))
  if (message.author.bot):
    print("DISCARDING BOT MESSAGE FROM ", message.author)
    return
  if type(message.channel) == discord.channel.PrivateChannel:
    print("DISCARDING PRIVATE MESSAGE FROM", message.author)
    return
  if "markov-bot" in str(message.author) or "MikuBot" in str(message.author):
    print("Discarding self message")
    return
  print("Got message on channel ", message.channel, "from author", message.author, ":", message.content)
  split = message.content.split()
  if len(split) == 0: return
  if split[0] in ["?femboy", "?tomboy"]:
    if "welcome-center" in str(message.channel):
      await client.send_message(message.server.get_channel('308342435430400012'), "Welcome <@" +str(message.author.id) + ">!");
  elif split[0] == (bot_prefix + "help"):
    await client.send_message(message.channel, "Commands: `" + bot_prefix + bot_name + "` - Generates random text based on collected probabilities\n`" + bot_prefix + bot_name + "<starting word>` - Generates starting from a particular word\n`" + bot_prefix + bot_name + " <limit>` - Generates random text with the given length\n`" + bot_prefix + "percents <word>` - Shows statistics on the given word\n`" + bot_prefix + "mask <message>` - Misspells some text\n`" + bot_prefix + "mask10 <message>` - Misspells some text 10 times\n`"+ bot_prefix + " <message>` - Comment that will not be processed by the bot\n`")
  elif split[0] == (bot_prefix + bot_name):
    await client.send_typing(message.channel)
    args = message.content.split()
    arg = False
    if len(args) > 1:
      arg = args[1]
    print("Sending")
    await client.send_message(message.channel, make_message(arg))
  elif split[0] == (bot_prefix + "percents") and len(split) > 1:
    percents = get_percents(split[1])
    await client.send_message(message.channel, percents)
  elif split[0] == (bot_prefix + "top"):
    if len(split) > 1 and str.isdigit(split[1]):
      mess = top(int(split[1]))
    else:
      mess = top(10)
    await client.send_message(message.channel, mess)
  elif split[0] == (bot_prefix + "mask"):
    await client.send_message(message.channel, mask.mask(" ".join(split[1:])))
  elif split[0] == (bot_prefix + "mask10"):
    msg = []
    curr = mask.mask(" ".join(split[1:]))
    for i in range(10):
      msg.append(curr)
      curr = mask.mask(curr)
    await client.send_message(message.channel, "\n".join(msg))
  elif (message.content.startswith(bot_prefix)):
    print("DISCARDING COMMENT MESSAGE FROM ", message.author)
    return
  elif train_in_all or message.channel.id in bot_trainning_channels:
    markov_add(message.content);
  else:
    print("DISCARDING MESSAGE OUTSIDE TRAINNING CHANNELS FROM", message.author)
  print("Took " + str(time.time() - start) + " seconds to process message of " + str(len(split)) + " words");

client.run(bot_key)
