WIDTH = 1100
HEIGHT = 760
BOARD_SIZE = 640
PANEL_WIDTH = WIDTH - BOARD_SIZE
SQUARE = BOARD_SIZE // 8
FPS = 60

LIGHT = (236, 236, 210)
DARK = (118, 150, 86)
BG = (31, 33, 43)
PANEL_BG = (38, 40, 52)
PANEL_ALT = (47, 50, 66)
CARD_BG = (55, 58, 74)
TEXT = (240, 240, 245)
MUTED = (170, 174, 188)
ACCENT = (105, 196, 114)
SELECT = (246, 205, 87)
MOVE_DOT = (80, 160, 255)
CAPTURE = (220, 70, 70)
CHECK = (255, 110, 110)
BUTTON = (72, 96, 140)
BUTTON_ALT = (90, 90, 110)
BUTTON_DANGER = (176, 58, 58)
BUTTON_OK = (76, 175, 80)
BUTTON_WARN = (255, 160, 0)
ANALYSIS_WHITE = (90, 120, 190)
ANALYSIS_BLACK = (125, 88, 155)

PIECE_VALUES = {
    1: 100,
    2: 320,
    3: 330,
    4: 500,
    5: 900,
    6: 0,
}

DIFFICULTIES = {
    "EASY": {"depth": 2, "think_time": 0.45},
    "MEDIUM": {"depth": 4, "think_time": 1.35},
    "HARD": {"depth": 6, "think_time": 3.6},
}

TIME_CONTROLS = {
    "2 MIN": 120,
    "5 MIN": 300,
    "10 MIN": 600,
}

GAME_MODES = {
    "PLAYER VS MACHINE": "pvm",
    "MACHINE VS MACHINE": "mvm",
}

PROMOTION_PIECES = [5, 4, 3, 2]

UNICODE_PIECES = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}
