import communication
import threading
import traceback
import aiohttp
import asyncio
import discord
import random
import json
import os
import re

PRINT_EXCEPTIONS = True
PRINT_NEW_CLIENT = True
PRINT_CLIENT_DIS = True
PRINT_REC_PACKET = True

class DiscordClient(discord.Client):
	priv_channel = int(os.getenv("FSOL_PRIVATE_CHANNEL"))
	fsol_guild = 462275923354451970
	announcements = 462291973236195342
	small_announcements = 507904657696358413
	announcements_cache = []
	small_announcements_cache = []

	async def api_check_ping(self):
		channel = self.get_guild(self.fsol_guild).get_channel(self.priv_channel)

		msg = await channel.send("Ping!")
		await msg.edit(content="Pong!")

		msg = await channel.fetch_message(msg.id)
		return int((msg.edited_at - msg.created_at).total_seconds() * 1000)

	async def api_has_role(self, user, search, obj):
		guild = self.get_guild(self.fsol_guild)

		try:
			member = await guild.fetch_member(user)
		except:
			return False

		if search == "id":
			obj = int(obj)
			for role in member.roles:
				if role.id == obj:
					return True

		elif search == "name":
			for role in member.roles:
				if role.name == obj:
					return True

		return False

	def api_readable_message(self, message):
		attachments = []
		message_content = message.content.replace("&", "&amp;").replace("<", "&lt;")
		message_content = re.sub(
			r"(?i)(\s|^)(?:&lt;)?(https?:\/\/\S+\.\S{2}\S*?)(?:>)?(\s|$)",
			r'\1<a href="\2" target="_blank">\2</a>\3',
			message_content
		)
		message_content = message_content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>").replace(
			"@everyone", '<span class="ping">@everyone</span>'
		).replace(
			"@here", '<span class="ping">@here</span>'
		)

		for member in message.mentions:
			message_content = message_content.replace(
				f"&lt;@{member.id}>", f'<span class="ping">@{member.name}#{member.discriminator}</span>'
			).replace(
				f"&lt;@!{member.id}>", f'<span class="ping">@{member.name}#{member.discriminator}</span>'
			)

		index = -1
		for _channel in message.channel_mentions:
			if _channel.category is None:
				message_content = message_content.replace(
					f"&lt;#{_channel.id}>", f'<span class="ping">#{_channel.name}</span>'
				)
			else:
				index += 1
				l = len(_channel.name)
				message_content = message_content.replace(
					f"&lt;#{_channel.id}>",
					f'<div style="display:inline;"> \
						<span class="ping ping-channel" shows="ping-{index}">#{_channel.name}</span> \
						<div id="ping-{index}" style="margin-left:-{l/2}rem;" class="hidden ping-info">{_channel.category.name}</div> \
					</div>'
				)

		for role in message.role_mentions:
			rgb_color = role.color.value if role.color.value > 0 else 7506394
			rgb_color = str((rgb_color >> 16) & 255) + ", " + str((rgb_color >> 8) & 255) + ", " + str(rgb_color & 255)
			message_content = message_content.replace(
				f"&lt;@&amp;{role.id}>",
				f'<span onmouseover="this.style.backgroundColor = \'rgba({rgb_color}, .3)\';" \
				onmouseout="this.style.backgroundColor = \'rgba({rgb_color}, .1)\';" \
				style="background-color:rgba({rgb_color}, .1);color:rgb({rgb_color});">@{role.name}</span>'
			)

		for png_emoji_name, png_emoji_id in re.findall(r"<:(.+?):(\d+?)>", message.content):
			message_content = message_content.replace(
				f"&lt;:{png_emoji_name}:{png_emoji_id}>",
				f'<img src="https://cdn.discordapp.com/emojis/{png_emoji_id}.png?size=32" style="max-width:1em;height:auto;">'
			)

		for gif_emoji_name, gif_emoji_id in re.findall(r"<a:(.+?):(\d+?)>", message.content):
			message_content = message_content.replace(
				f"&lt;a:{gif_emoji_name}:{gif_emoji_id}>",
				f'<img src="https://cdn.discordapp.com/emojis/{gif_emoji_id}.gif?size=32" style="max-width:1em;height:auto;">'
			)

		for attachment in message.attachments:
			if getattr(attachment, "width", None) is not None:
				attachments.append(attachment.url)

		message_content = re.sub(r"`([^`]+?)`", r'<code class="inline">\1</code>', message_content)
		message_content = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', message_content)
		message_content = re.sub(r"__(.+?)__", r'<u>\1</u>', message_content)
		message_content = re.sub(r"~~(.+?)~~", r'<s>\1</s>', message_content)
		message_content = re.sub(r"(_|\*)(.+?)\1", r'<em>\2</em>', message_content)

		return {
			"author": message.author.name + "#" + message.author.discriminator,
			"color": message.author.color.value if message.author.color.value > 0 else 16777215,
			"avatar": (f"embed/avatars/{int(message.author.discriminator) % 5}.png"
				if message.author.avatar is None else
			f"avatars/{message.author.id}/{message.author.avatar}.png"),
			"timestamp": int(((message.id >> 22) + 1420070400000) / 1000),
			"message": message_content,
			"attachments": attachments
		}

	async def api_fetch_messages(self, channel, page, quantity=10, all_pages=False):
		quantity = 100 if quantity > 100 else 1 if quantity < 1 else quantity

		messages = []
		count = 0
		async for message in channel.history(limit=(page + 1) * quantity, oldest_first=False):
			count += 1

			if all_pages or count > page * quantity:
				messages.append(self.api_readable_message(message))

		return messages

	async def load_announcements(self):
		self.announcements_cache = await self.api_fetch_messages(self.get_channel(self.announcements), 9, quantity=10, all_pages=True)
		print("[DISCORD] Cached #announcements. Caching #small-announcements messages...")
		self.small_announcements_cache = await self.api_fetch_messages(self.get_channel(self.small_announcements), 9, quantity=10, all_pages=True)

	async def on_message(self, message):
		if message.channel.id == self.announcements:
			self.announcements_cache.insert(0, self.api_readable_message(message))
			if len(self.announcements_cache) > 100:
				self.announcements_cache.pop()

		elif message.channel.id == self.small_announcements:
			self.small_announcements_cache.insert(0, self.api_readable_message(message))
			if len(self.small_announcements_cache) > 100:
				self.small_announcements_cache.pop()

	async def on_ready(self):
		print("[DISCORD] Ready")

		print("[DISCORD] Caching #announcement messages...")
		await self.load_announcements()
		print("[DISCORD] Cached #small-announcements")

		threading.Thread(target=server.loop.run_forever).start()

class SocketClient:
	endpoint_key = os.getenv("FSOL_BOLO_ENDPOINT_KEY")
	session = None

	def __init__(self, io):
		self.io = io

	async def add_user_info(self, result, user):
		result[str(user.id)] = {
			"name": user.name + "#" + user.discriminator,
			"color": user.color.value if user.color.value > 0 else 16777215,
			"avatar": f"embed/avatars/{int(user.discriminator) % 5}.png" if user.avatar is None else f"avatars/{user.id}/{user.avatar}.png",
		}

	async def on_received(self, packet):
		if packet["type"] == "bot_state":
			return {
				"discord_ping": await swait(discord.api_check_ping()),
				"result": "success"
			}

		elif packet["type"] == "user_roles":
			user = int(packet["user"])

			guild = discord.get_guild(discord.fsol_guild)
			member = guild.get_member(user)
			if member is None:
				try:
					member = await swait(guild.fetch_member(user))
				except:
					member = None

			result = {"color": 16777215, "role_colors": [], "role_names": [], "role_ids": [], "in_server": False, "success": True}
			if member is None:
				return result
			result["in_server"] = True
			result["color"] = member.color.value if member.color.value > 0 else 16777215
			for role in member.roles:
				result["role_colors"].append([role.name, role.color.value if role.color.value > 0 else 16777215])
				result["role_names"].append(role.name)
				result["role_ids"].append(str(role.id))

			return result

		elif packet["type"] == "get_user_info":
			guild = discord.get_guild(discord.fsol_guild)
			result = {"success": True}
			futures = []
			checked = []

			for user in packet["users"]:
				user = int(user)
				if user in checked:
					continue
				checked.append(user)
				member = guild.get_member(user)
				if member is None:
					futures.append([await promise(guild.fetch_member(user)), user])
					continue

				await self.add_user_info(result, member)

			for future in futures:
				try:
					member = future[0].result()
				except:
					result[str(future[1])] = None
					continue

				await self.add_user_info(result, member)

			return result

		elif packet["type"] == "fetch_announcements":
			channel = discord.small_announcements_cache if packet["small"] else discord.announcements_cache
			return {
				"messages": channel[packet["page"] * 10:(packet["page"] + 1) * 10],
				"success": True
			}

		elif packet["type"] == "get_member_profiles_quantity":
			quantity = 0

			try:
				async with self.session.get(f"http://discbotdb.000webhostapp.com/get?k={self.endpoint_key}&f=b_memberprofiles") as resp:
					endpoint = json.loads(await resp.text())

					for key, value in endpoint.copy().items():
						if len(value) != 0 and key != "545376143365373996":
							quantity += 1
			except asyncio.TimeoutError:
				return {"error": "Endpoint timed out.", "success": False}

			return {
				"quantity": quantity,
				"success": True
			}

		elif packet["type"] == "get_member_profiles":
			try:
				async with self.session.get(f"http://discbotdb.000webhostapp.com/get?k={self.endpoint_key}&f=b_memberprofiles") as resp:
					endpoint = json.loads(await resp.text())

					for key, value in endpoint.copy().items():
						if len(value) == 0 or key == "545376143365373996": # did you know that D_shades has a Modulo profile? lol
							del endpoint[key]
							continue

						if isinstance(value, (list, tuple)):
							endpoint[key] = {str(index + 1): subvalue for index, subvalue in enumerate(value)}
			except asyncio.TimeoutError:
				return {"error": "Endpoint timed out.", "success": False}

			result = {"users": {}, "success": True}
			guild = discord.get_guild(discord.fsol_guild)
			futures = []

			if isinstance(packet["users"], int):
				items = []
				keys = list(endpoint.keys())
				length = len(keys)

				for iteration in range(min(len(endpoint), packet["users"])): # We make sure that we don't keep choosing random values from an empty list!
					length -= 1
					key = keys.pop(random.randint(0, length))
					items.append((key, endpoint.pop(key)))

				for user, value in items:
					user = int(user)

					result["users"][str(user)] = value

					member = guild.get_member(user)
					if member is None:
						futures.append([await promise(guild.fetch_member(user)), user])
						continue

					value["discord"] = {
						"name": member.name + "#" + member.discriminator,
						"color": member.color.value if member.color.value > 0 else 16777215,
						"avatar": f"embed/avatars/{int(member.discriminator) % 5}.png" if member.avatar is None else f"avatars/{member.id}/{member.avatar}.png",
						"roles": [],
						"is_mod": False
					}
					for role in member.roles:
						if role.id == 585148219395276801:
							value["discord"]["is_mod"] = True
						value["discord"]["roles"].append([role.name, role.color.value if role.color.value > 0 else 16777215])

			elif isinstance(packet["users"], float):
				page = int(packet["users"])
				start, end = 10 * page, 10 * (page + 1)
				index = 0
				for user, value in endpoint.items():
					if index >= start and index < end:
						user = int(user)

						result["users"][str(user)] = endpoint[str(user)]

						member = guild.get_member(int(user))
						if member is None:
							futures.append([await promise(guild.fetch_member(user)), user])
							continue

						value["discord"] = {
							"name": member.name + "#" + member.discriminator,
							"color": member.color.value if member.color.value > 0 else 16777215,
							"avatar": f"embed/avatars/{int(member.discriminator) % 5}.png" if member.avatar is None else f"avatars/{member.id}/{member.avatar}.png",
							"roles": [],
							"is_mod": False
						}
						for role in member.roles:
							if role.id == 585148219395276801:
								value["discord"]["is_mod"] = True
							value["discord"]["roles"].append([role.name, role.color.value if role.color.value > 0 else 16777215])

					index += 1

			else:
				for user in packet["users"]:
					user = int(user)
					user_str = str(user)
					if user_str in endpoint:
						result["users"][user_str] = endpoint[user_str]
						value = result["users"][user_str]

						member = guild.get_member(user)
						if member is None:
							futures.append([await promise(guild.fetch_member(user)), user])
							continue

						value["discord"] = {
							"name": member.name + "#" + member.discriminator,
							"color": member.color.value if member.color.value > 0 else 16777215,
							"avatar": f"embed/avatars/{int(member.discriminator) % 5}.png" if member.avatar is None else f"avatars/{member.id}/{member.avatar}.png",
							"roles": [],
							"is_mod": False
						}
						for role in member.roles:
							if role.id == 585148219395276801:
								value["discord"]["is_mod"] = True
							value["discord"]["roles"].append([role.name, role.color.value if role.color.value > 0 else 16777215])

					else:
						result["users"][user] = None

			for future in futures:
				try:
					member = future[0].result()
				except:
					result["users"][str(future[1])] = None
					continue

				result["users"][future[1]]["discord"] = {
					"name": member.name + "#" + member.discriminator,
					"color": member.color.value if member.color.value > 0 else 16777215,
					"avatar": f"embed/avatars/{int(member.discriminator) % 5}.png" if member.avatar is None else f"avatars/{member.id}/{member.avatar}.png",
					"roles": [],
					"is_mod": False
				}
				for role in member.roles:
					if role.id == 585148219395276801:
						result["users"][future[1]]["discord"]["is_mod"] = True
					result["users"][future[1]]["discord"]["roles"].append([role.name, role.color.value if role.color.value > 0 else 16777215])

			return result

		return {"success": False, "error": "Packet type not found"}

	async def start(self):
		address = self.io.writer.get_extra_info("peername")
		if PRINT_NEW_CLIENT:
			print("New client", address)

		while self.io.open:
			packet = await self.io.read()

			if packet:
				if PRINT_REC_PACKET:
					print("Received packet", address, packet)

				try:
					result = await self.on_received(packet)

				except:
					if PRINT_EXCEPTIONS:
						print("Ignoring exception on packet", address, packet)
						traceback.print_exc()

					result = {"type": packet["type"], "success": False}

				else:
					if isinstance(result, dict):
						result["type"] = packet["type"]

					else:
						result = {"type": packet["type"], "success": True}

				if not await self.io.write(result):
					break
			else:
				break

		if PRINT_CLIENT_DIS:
			print("Client disconnection", address)

async def promise(coro):
	return asyncio.run_coroutine_threadsafe(coro, discord.loop)
async def swait(coro):
	return promise(coro).result()

if __name__ == "__main__":
	discord = DiscordClient(loop=asyncio.get_event_loop())

	server = communication.Server(SocketClient, "0.0.0.0", 5654, loop=asyncio.new_event_loop())
	timeout = aiohttp.ClientTimeout(total=2)
	SocketClient.session = aiohttp.ClientSession(timeout=timeout, loop=server.loop)
	server.loop.create_task(server.start())

	try:
		print("[DISCORD] Turning on...")
		discord.run(os.getenv("FSOL_DISCORD_TOKEN"))
	except KeyboardInterrupt:
		pass
	except Exception:
		traceback.print_exc()

	try:
		server.loop.call_soon_threadsafe(server.loop.stop)
	except:
		pass