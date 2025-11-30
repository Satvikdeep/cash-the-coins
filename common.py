# common.py
import json

# Network Constants
HOST = '127.0.0.1'
PORT = 5555
BUF_SIZE = 4096

# Game Constants
SCREEN_WIDTH = 700
SCREEN_HEIGHT = 800
TARGET_FPS = 60
MAX_COINS = 15

# Sizes
PLAYER_SIZE = 40
COIN_SIZE = 20
COIN_RADIUS = COIN_SIZE//2

# Colors (R, G, B) ---
BLUE = (139, 218, 255)    # P1
WHITE = (255, 255, 255)   # P2
BLACK = (0, 0, 0)


# Coin Types
COIN_DARK = (16, 99, 255)
COIN_PASTEL = (4, 212, 244)
COIN_LIGHT = (188, 236, 255)


COIN_TYPES = {
    0: {"val": 5, "color": COIN_LIGHT},
    1: {"val": 10,  "color": COIN_PASTEL},
    2: {"val": 20,  "color": COIN_DARK}
}


KEY_TYPE = "t"
KEY_ID = "id"
KEY_DATA = "d"

# Message Types
MSG_CONNECT = "con"
MSG_INPUT = "inp"
MSG_STATE = "st"

# Input Commands
CMD_UP = "u"
CMD_DOWN = "d"
CMD_LEFT = "l"
CMD_RIGHT = "r"
CMD_RESET = "rst"
CMD_DASH = "dash"

# Helpers
def to_json(data):
    return json.dumps(data).encode('utf-8')

def from_json(data):
    try:
        return json.loads(data.decode('utf-8'))
    except:
        return None