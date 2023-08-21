import websockets

HOST: str = 'localhost'
PORT: int = 5192

WEBSOCKET_ERRORS: tuple = (
    websockets.ConnectionClosed,
    websockets.ConnectionClosedOK,
    websockets.ConnectionClosedError,
)
