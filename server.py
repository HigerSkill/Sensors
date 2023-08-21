import asyncio
import json

from websockets.legacy.server import WebSocketServerProtocol
from websockets.server import serve

from constants import HOST, PORT


class Server:
    """Get all messages from sensor's Agent and send to clients which have subscriptions."""
    def __init__(self, host: str, port: str | int) -> None:
        self.host: str = host
        self.port: int = int(port)
        self.clients: dict = {}

    async def route(self, ws: WebSocketServerProtocol, raw_message: str):
        """Route WS messages for different events."""
        try:
            message: dict = json.loads(raw_message)
        except json.JSONDecodeError:
            return

        event: str = message.get('event')
        data: dict = message.get('data') if message.get('data') else {}

        sensor_id: str = data.get('sensor_id')

        if event == 'subscribe_sensor':
            # Save WS and set of sensor's ids
            if ws in self.clients:
                self.clients[ws].add(data['sensor_id'])
            else:
                self.clients[ws] = {sensor_id}
            await ws.send(raw_message)
        elif event == 'unsubscribe_sensor':
            # Remove sensor's id
            if ws in self.clients:
                self.clients[ws].remove(sensor_id)
            await ws.send(raw_message)
        elif event == 'sensor_connection_status':
            # Check sensor connected to particular client
            answer: dict = {
                'event': 'sensor_connection_status',
                'data': {
                    'sensor_id': sensor_id,
                    'connected': sensor_id in self.clients.get('ws')
                }
            }
            await ws.send(json.dumps(answer))
        elif event == 'new_sensor_data':
            # Get sensor's data and send to all clients which have subscription
            for client, client_sensors in self.clients.items():
                if sensor_id in client_sensors:
                    await client.send(raw_message)
        elif event == 'agent_connect':
            # Set subscriptions to all sensors for Agent
            self.clients[ws] = set(data['sensors'])
            await ws.send(raw_message)
        elif event == 'ping':
            answer: dict = {'event': 'pong', 'data': {}}
            await ws.send(json.dumps(answer))
        else:
            await ws.send(raw_message)

    async def handle(self, ws: WebSocketServerProtocol):
        async for message in ws:
            print(message)
            await self.route(ws, message)

    async def connect(self):
        async with serve(self.handle, self.host, self.port):
            await asyncio.Future()


if __name__ == "__main__":
    server = Server(HOST, PORT)
    asyncio.run(server.connect())
