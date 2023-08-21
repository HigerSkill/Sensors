import asyncio
import json
import uuid
from threading import Thread
from typing import Callable

import websockets

from constants import HOST, PORT, WEBSOCKET_ERRORS


class Client(Thread):
    """Get messages from sensors and subscribe to particular ones."""
    def __init__(self, host: str, port: str | int) -> None:
        Thread.__init__(self, daemon=True)

        self.q = asyncio.Queue(maxsize=0)
        self.host: str = host
        self.port: int = int(port)
        self.run: Thread | None = None
        self.callbacks: dict = {}
        self.sensors: set = set()

    async def __run(self):
        async for ws in websockets.connect(f'ws://{self.host}:{self.port}'):
            try:
                while True:
                    if not self.q.empty():
                        item = self.q.get_nowait()
                        await ws.send(json.dumps(item))

                    raw_message: str = await ws.recv()
                    message: dict = json.loads(raw_message)
                    event: str = message.get('event')

                    print(message)

                    if event == 'new_sensor_data':
                        data: dict = message.get('data', {})
                        sensor_id: str = data.get('sensor_id')
                        sensor_readings: str = data.get('sensor_readings')

                        if sensor_id in self.callbacks:
                            for callback, args in self.callbacks[sensor_id]:
                                callback(sensor_id, sensor_readings, *args)
            except WEBSOCKET_ERRORS:
                # try to reconnect
                # TODO: It seems can be done better
                await self.__reconnect()
                continue

    async def __reconnect(self):
        """Send connect message and subscribe to sensors again."""
        reconnect_messages: list = [
            {
                'event': 'Client connect',
                'data': {
                    'client_name': str(uuid.uuid4())
                },
            },
        ]
        reconnect_messages.extend([
            {'event': 'subscribe_sensor', 'data': {'sensor_id': sensor_id}} for sensor_id in self.sensors
        ])

        for msg in reconnect_messages:
            # Send to queue
            await self.q.put(msg)

    def __run_event_loop(self):
        """Create event loop and run."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self.__run())
        loop.close()

    def connect(self):
        self.run = Thread(target=self.__run_event_loop, daemon=True)
        message: dict = {
            'event': 'Client connect',
            'data': {
                'client_name': str(uuid.uuid4())
            },
        }

        asyncio.run(self.q.put(message))
        self.run.start()

    def disconnect(self):
        message: dict = {
            'event': 'Client disconnect',
            'data': {},
        }

        asyncio.run(self.q.put(message))
        self.run.join()

    def subscribe(self, sensor_id: str):
        message: dict = {
            'event': 'subscribe_sensor',
            'data': {
                'sensor_id': sensor_id,
            }
        }

        self.sensors.add(sensor_id)

        asyncio.run(self.q.put(message))

    def unsubscribe(self, sensor_id: str):
        message: dict = {
            'event': 'unsubscribe_sensor',
            'data': {
                'sensor_id': sensor_id,
            }
        }

        self.sensors.remove(sensor_id)

        asyncio.run(self.q.put(message))

    def connection_status(self, sensor_id: str):
        message: dict = {
            'event': 'sensor_connection_status',
            'data': {
                'sensor_id': sensor_id
            }
        }

        asyncio.run(self.q.put(message))

    def register_callback(self, sensor_id: str, callback: Callable, args: tuple = None):
        """Register callback when client get message."""
        data_callback: list = self.callbacks.get(sensor_id, [])
        data_callback.append((callback, args))
        self.callbacks[sensor_id] = data_callback

    def remove_callback(self, sensor_id: str):
        """Register callback when client get message."""
        self.callbacks.pop(sensor_id)


def callback_sensor(sensor_id: str, sensor_reading: str, my_arg1: str):
    print(f'Callback: {sensor_id} - {sensor_reading}, {my_arg1}')


if __name__ == "__main__":
    client = Client(HOST, PORT)
    client.connect()
    client.subscribe('S1')
    client.register_callback('S1', callback_sensor, args=('test', ))

    asyncio.run(asyncio.sleep(100))

    client.disconnect()
