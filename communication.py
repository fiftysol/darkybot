import asyncio
import struct
import json
import os

class IOClient:
	def __init__(self, reader, writer):
		self.reader, self.writer = reader, writer
		self.open = True

	async def write(self, data):
		if self.open:
			try:
				if not data["success"] and "error" not in data:
					data["error"] = "Unknown"
				packet = json.dumps(data).encode()

				self.writer.write(struct.pack("!L", len(packet)) + packet)
				await self.writer.drain()
				return True

			except:
				self.close()

	async def read(self):
		if self.open:
			try:
				length = struct.unpack("!L", await self.reader.read(4))
				packet = await self.reader.read(length[0])

				data = json.loads(packet)
				if "type" in data:
					return data
				self.close()

			except:
				return self.close()

	def close(self):
		self.open = False
		try:
			self.writer.close()
		except:
			pass

class Server:
	start = None

	def __init__(self, client_handler, ip, port, loop=None):
		self.loop = loop or asyncio.get_event_loop()

		self.client_handler = client_handler
		self._start = asyncio.start_server(self.handle_client, ip, port, loop=loop)

	async def start(self):
		print("[SOCKET] Turning on...")
		await self._start
		print("[SOCKET] Ready")

	async def handle_client(self, reader, writer):
		io = IOClient(reader, writer)

		packet = await io.read()
		if not (packet and packet["type"] == "handshake" and "token" in packet and packet["token"] == os.getenv("FSOL_BOT_SOCKET_TOKEN")):
			await io.write({"type": "handshake", "success": False})
			return io.close()
		await io.write({"type": "handshake", "success": True})

		await self.client_handler(io).start()