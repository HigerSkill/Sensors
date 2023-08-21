import asyncio
import json
import random

import websockets

from constants import HOST, PORT


class Sensor:
    """Generate dummy data like real sensor."""
    def __init__(self, sensor_id: str):
        self.sensor_id = sensor_id

    async def get_data(self):
        return {
            'event': 'new_sensor_data',
            'data': {
                'sensor_id': self.sensor_id,
                'sensor_readings': 'some_data',
            }
        }


class AgentSensors:
    """External device, which collects various info from sensors."""
    def __init__(self, host: str, port: str | int):
        self.connection = None
        self.host = host
        self.port = int(port)

    async def run(self, sensors: list[Sensor]):
        async with websockets.connect(f'ws://{self.host}:{self.port}') as ws:
            # Send message on connect
            connect_message: dict = {
                'event': 'agent_connect',
                'data': {
                    'sensors': [s.sensor_id for s in sensors]
                }
            }
            await ws.send(json.dumps(connect_message))
            print(await ws.recv())

            while True:
                # Send data from sensors every 3 secs.
                await asyncio.sleep(3)
                sensor_index: int = random.randint(0, len(sensors)-1)
                sensor_data: dict = await sensors[sensor_index].get_data()
                await ws.send(json.dumps(sensor_data))

                print(await ws.recv())


async def run_agent():
    sensors: list[Sensor] = [Sensor(f'S{i}') for i in range(3)]

    agent = AgentSensors(HOST, PORT)
    await agent.run(sensors)


if __name__ == '__main__':
    asyncio.run(run_agent())

