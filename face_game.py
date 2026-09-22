import math
import random

import pyxel
from typesafe_sdk import Choice, TypeSafeClient

WIDTH, HEIGHT = 200, 200

# ============================================================
# ロボットの各パーツの位置・サイズ
# ============================================================
FRAME_X, FRAME_Y, FRAME_W, FRAME_H = 50, 50, 100, 95
SCREEN_X, SCREEN_Y, SCREEN_W, SCREEN_H = 62, 62, 76, 60
EYE_L = (83, 90)
EYE_R = (117, 90)
MOUTH_X, MOUTH_Y = 100, 108
BODY_RECT = (65, 157, 70, 33)

# ============================================================
# 入力欄(画面下部)の位置・サイズ
# ============================================================
INPUT_X, INPUT_Y, INPUT_W, INPUT_H = 10, 168, WIDTH - 20, 16
INPUT_MAX_CHARS = 42


# ---------------------------------------------------------------------------
# キーボード入力 -> 文字 の変換テーブル
# Pyxelのキー定数はSDLのキーコードをそのまま使っており、印字可能なキーは
# シフト無しのASCIIコードと一致するため、押されたキーのコード自体を
# そのまま文字として使える(例: pyxel.KEY_A == ord("a"))。
# ---------------------------------------------------------------------------
SHIFT_DIGIT_SYMBOLS = {
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
    "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
}
SHIFT_SYMBOL_MAP = {
    "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|",
    ";": ":", "'": '"', ",": "<", ".": ">", "/": "?", "`": "~",
}
TYPABLE_KEYS = (
    list(range(pyxel.KEY_A, pyxel.KEY_Z + 1))
    + list(range(pyxel.KEY_0, pyxel.KEY_9 + 1))
    + [
        pyxel.KEY_SPACE,
        pyxel.KEY_QUOTE,
        pyxel.KEY_COMMA,
        pyxel.KEY_PERIOD,
        pyxel.KEY_SLASH,
        pyxel.KEY_MINUS,
        pyxel.KEY_EQUALS,
        pyxel.KEY_SEMICOLON,
        pyxel.KEY_LEFTBRACKET,
        pyxel.KEY_RIGHTBRACKET,
        pyxel.KEY_BACKSLASH,
        pyxel.KEY_BACKQUOTE,
    ]
)


def _char_for_key(key, shift):
    """押されたキー(コード)を、シフト状態に応じた1文字に変換する。"""
    ch = chr(key)
    if ch.isalpha():
        return ch.upper() if shift else ch
    if shift:
        if ch in SHIFT_DIGIT_SYMBOLS:
            return SHIFT_DIGIT_SYMBOLS[ch]
        if ch in SHIFT_SYMBOL_MAP:
            return SHIFT_SYMBOL_MAP[ch]
    return ch


# ---------------------------------------------------------------------------
# Jev への問い合わせ
# ---------------------------------------------------------------------------
REACTIONS = ("smile", "angry", "cry", "lol", "nod")


REACTION_TO_EXPR = {
    "smile": "joy",
    "angry": "anger",
    "cry": "sorrow",
    "lol": "fun",
    "nod": "normal",
}

REACTION_CRITERIA = {
    "smile": "The message is a compliment or something happy, positive and gentle.",
    "angry": "The message is a complaint, criticism, or something negative and aggressive.",
    "cry": "The message is sad or difficult news, something that evokes sympathy.",
    "lol": (
        "The message is a very funny story, a strong joke, or a gag - "
        "something that would make someone burst out laughing."
    ),
    "nod": (
        "The message doesn't fit any of the above - ordinary conversation, "
        "a question, or a plain statement of fact."
    ),
}


class JevJudge:
    """入力された言葉を Jev (TypeSafe AI) に判定してもらうクラス。"""

    def __init__(self):
        self.client = None
        try:
            # TypeSafeClient は環境変数 TYPESAFE_API_KEY を自動的に読み込み、
            # デフォルトで model="jev-latest" を使用する。
            self.client = TypeSafeClient()
        except Exception as e:  # noqa: BLE001 - 起動時に落とさず警告のみ表示
            print(f"[warning] Failed to initialize TypeSafeClient: {e}")
            print("          Check that the TYPESAFE_API_KEY environment variable is set.")

    def judge(self, text: str) -> str:
        """話しかけられた言葉から反応(表情)のキーを返す。失敗時は 'nod'。"""
        if self.client is None or not text.strip():
            return "nod"
        try:
            response = self.client.system_one(
                state=text,
                questions={
                    "reaction": Choice(
                        instructions=(
                            "Decide which facial expression this character should react "
                            "with, based on what was just said to it."
                        ),
                        criteria=REACTION_CRITERIA,
                    )
                },
            )
            choice = response.answers["reaction"].choice
            if choice in REACTIONS:
                return choice
        except Exception as e:  # noqa: BLE001 - 通信失敗などはnodにフォールバック
            print(f"[warning] Failed to reach Jev: {e}")
        return "nod"


# ---------------------------------------------------------------------------
# ゲーム本体
# ---------------------------------------------------------------------------


class RobotFaceApp:
    NOD_FRAMES = 24
    SHAKE_FRAMES = 36

    def __init__(self):
        self.judge = JevJudge()

        self.reaction = "nod"
        self.expr = "normal"
        self.busy = False

        # ---- 入力欄(1画面完結の英語テキスト入力)まわりの状態 ----
        self.mode = "idle"  # "idle" or "typing"
        self.input_buffer = ""
        # -------------------------------------------------------

        # ---- モーション用タイマー ----
        self.nod_timer = 0
        self.shake_timer = 0
        # -----------------------------------------------------------

        self._print_intro()

        # quit_key はこちらで手動管理するので無効化しておく
        # (入力中にESCを押した時にゲームごと終了してしまうのを防ぐため)
        # display_scale を指定しないと、Pyxelが画面サイズに合わせて自動で
        # 大きく拡大してしまう(環境によってはほぼフルスクリーン相当になる)ため、
        # ここで明示的に小さめの倍率を指定している。
        # 200x200 x2 = 400x400 のウィンドウになる。もっと小さくしたい場合は
        # display_scale=1 (200x200) に、逆に大きくしたい場合は 3 や 4 に変更してください。
        pyxel.init(
            WIDTH,
            HEIGHT,
            title="Talk to the Robot - Jev",
            fps=30,
            quit_key=pyxel.KEY_NONE,
            display_scale=2,
        )
        pyxel.run(self.update, self.draw)

    def _print_intro(self):
        print("=" * 44)
        print(" Talk to the Robot - a Jev-powered face-change game")
        print(" SPACE / ENTER : start typing to the robot")
        print(" ENTER (while typing) : send it")
        print(" ESC (while typing)   : cancel")
        print(" Q or ESC (while idle): quit")
        print("=" * 44)

    def update(self):
        if self.mode == "idle":
            self._update_idle()
        else:
            self._update_typing()

        if self.nod_timer > 0:
            self.nod_timer -= 1
        if self.shake_timer > 0:
            self.shake_timer -= 1

    def _update_idle(self):
        if pyxel.btnp(pyxel.KEY_Q) or pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()
            return
        if not self.busy and (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)):
            self.mode = "typing"
            self.input_buffer = ""

    def _update_typing(self):
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_KP_ENTER):
            self._submit_typing()
            return
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.mode = "idle"
            self.input_buffer = ""
            return
        if pyxel.btnp(pyxel.KEY_BACKSPACE, hold=15, repeat=3):
            self.input_buffer = self.input_buffer[:-1]

        shift = (
            pyxel.btn(pyxel.KEY_SHIFT)
            or pyxel.btn(pyxel.KEY_LSHIFT)
            or pyxel.btn(pyxel.KEY_RSHIFT)
        )
        for key in TYPABLE_KEYS:
            if pyxel.btnp(key, hold=15, repeat=3) and len(self.input_buffer) < INPUT_MAX_CHARS:
                self.input_buffer += _char_for_key(key, shift)

    def _submit_typing(self):
        text = self.input_buffer.strip()
        self.mode = "idle"
        self.input_buffer = ""
        self._apply_reaction(text)

    def _apply_reaction(self, text):
        reaction = self.judge.judge(text) if text else "nod"
        print(f"-> reaction: {reaction}")
        self.reaction = reaction
        self.expr = REACTION_TO_EXPR.get(reaction, "normal")

        self.nod_timer = 0
        self.shake_timer = 0
        if reaction == "nod":
            self.nod_timer = self.NOD_FRAMES
        elif reaction == "lol":
            self.shake_timer = self.SHAKE_FRAMES

    def draw(self):
        pyxel.cls(pyxel.COLOR_WHITE)

        ox, oy = self._get_offset()
        pyxel.camera(-ox, -oy)
        self.draw_robot()
        pyxel.camera()

        if self.mode == "typing":
            self._draw_input_box()
        else:
            pyxel.text(6, 6, "SPACE/ENTER: talk to the robot", pyxel.COLOR_BLACK)
            pyxel.text(6, 15, "Q/ESC: quit", pyxel.COLOR_BLACK)
            pyxel.text(6, HEIGHT - 12, f"Reaction: {self.reaction.capitalize()}", pyxel.COLOR_BLACK)

    def _draw_input_box(self):
        pyxel.rect(INPUT_X, INPUT_Y, INPUT_W, INPUT_H, pyxel.COLOR_WHITE)
        pyxel.rectb(INPUT_X, INPUT_Y, INPUT_W, INPUT_H, pyxel.COLOR_GRAY)

        pyxel.text(INPUT_X, INPUT_Y - 10, "Type a message, then ENTER (ESC to cancel):", pyxel.COLOR_BLACK)

        shown = self.input_buffer
        max_visible = (INPUT_W - 8) // pyxel.FONT_WIDTH
        if len(shown) > max_visible:
            shown = shown[-max_visible:]
        cursor = "_" if (pyxel.frame_count // 15) % 2 == 0 else " "
        pyxel.text(INPUT_X + 4, INPUT_Y + 5, shown + cursor, pyxel.COLOR_BLACK)

    def _get_offset(self):
        """うなずき/震えのオフセットを計算する。"""
        if self.nod_timer > 0:
            t = self.NOD_FRAMES - self.nod_timer
            return 0, int(3 * math.sin(t * 0.9))
        if self.shake_timer > 0:
            return random.randint(-2, 2), random.randint(-2, 2)
        return 0, 0

    def draw_robot(self):
        expr = self.expr

        # ---- アンテナ ----
        pyxel.line(100, 50, 100, 32, pyxel.COLOR_GRAY)
        pyxel.circ(100, 30, 4, pyxel.COLOR_RED if expr == "anger" else pyxel.COLOR_GRAY)

        # ---- 頭部フレーム(筐体) ----
        pyxel.rect(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, pyxel.COLOR_WHITE)
        pyxel.rectb(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, pyxel.COLOR_GRAY)

        # ---- 画面(黒っぽい液晶部分) ----
        pyxel.rect(SCREEN_X, SCREEN_Y, SCREEN_W, SCREEN_H, pyxel.COLOR_NAVY)
        pyxel.rectb(SCREEN_X, SCREEN_Y, SCREEN_W, SCREEN_H, pyxel.COLOR_BLACK)

        # ---- ベゼル下のスピーカー穴 ----
        for hx in (78, 100, 122):
            pyxel.circ(hx, 133, 2, pyxel.COLOR_GRAY)

        # ---- 首・本体(ボディ) ----
        pyxel.rect(90, 145, 20, 12, pyxel.COLOR_GRAY)
        body_col = pyxel.COLOR_PINK if expr == "anger" else pyxel.COLOR_WHITE
        pyxel.rect(*BODY_RECT, body_col)
        pyxel.rectb(*BODY_RECT, pyxel.COLOR_GRAY)
        for hx in (80, 100, 120):
            pyxel.circ(hx, 173, 3, pyxel.COLOR_GRAY)
        pyxel.circ(74, 184, 3, pyxel.COLOR_GREEN)

        # ---- 表情(画面の中身) ----
        if expr == "sorrow":
            self.draw_eyes_sorrow()
            self.draw_mouth_sad()
            self.draw_tears()

        elif expr == "anger":
            self.draw_eyebrows_angry()
            self.draw_eyes_normal()
            self.draw_mouth_angry()

        elif expr == "fun":
            self.draw_eyes_happy()
            self.draw_mouth_laugh()

        elif expr == "joy":
            self.draw_sparkle()
            self.draw_eyes_happy()
            self.draw_mouth_smile()

        else:
            self.draw_eyes_normal()
            self.draw_mouth_normal()

    # ---------------- 目(LED) ----------------
    def draw_eyes_normal(self):
        pyxel.circ(*EYE_L, 4, pyxel.COLOR_CYAN)
        pyxel.circ(*EYE_R, 4, pyxel.COLOR_CYAN)

    def draw_eyes_sorrow(self):
        lx, ly = EYE_L
        rx, ry = EYE_R

        # 困り眉
        pyxel.line(lx - 6, ly - 9, lx + 5, ly - 6, pyxel.COLOR_CYAN)
        pyxel.line(rx - 5, ry - 6, rx + 6, ry - 9, pyxel.COLOR_CYAN)

        # への字の目
        pyxel.line(lx - 4, ly - 2, lx, ly + 3, pyxel.COLOR_CYAN)
        pyxel.line(lx, ly + 3, lx + 4, ly - 2, pyxel.COLOR_CYAN)
        pyxel.line(rx - 4, ry - 2, rx, ry + 3, pyxel.COLOR_CYAN)
        pyxel.line(rx, ry + 3, rx + 4, ry - 2, pyxel.COLOR_CYAN)

    def draw_eyes_happy(self):
        # にっこり閉じ目(アーチ)
        lx, ly = EYE_L
        rx, ry = EYE_R
        pyxel.line(lx - 5, ly, lx, ly - 4, pyxel.COLOR_CYAN)
        pyxel.line(lx, ly - 4, lx + 5, ly, pyxel.COLOR_CYAN)
        pyxel.line(rx - 5, ry, rx, ry - 4, pyxel.COLOR_CYAN)
        pyxel.line(rx, ry - 4, rx + 5, ry, pyxel.COLOR_CYAN)

    def draw_tears(self):
        lx, ly = EYE_L
        rx, ry = EYE_R
        pyxel.tri(lx - 2, ly + 6, lx + 2, ly + 6, lx, ly + 14, pyxel.COLOR_LIGHT_BLUE)
        pyxel.tri(rx - 2, ry + 6, rx + 2, ry + 6, rx, ry + 14, pyxel.COLOR_LIGHT_BLUE)

    # ---------------- 眉(怒) ----------------
    def draw_eyebrows_angry(self):
        lx, ly = EYE_L
        rx, ry = EYE_R
        pyxel.line(lx - 8, ly - 12, lx + 6, ly - 6, pyxel.COLOR_RED)
        pyxel.line(rx - 6, ry - 6, rx + 8, ry - 12, pyxel.COLOR_RED)

    # ---------------- 喜(キラキラ) ----------------
    def draw_sparkle(self):
        x, y = 128, 40
        pyxel.line(x - 5, y, x + 5, y, pyxel.COLOR_YELLOW)
        pyxel.line(x, y - 5, x, y + 5, pyxel.COLOR_YELLOW)

    # ---------------- 口(LED) ----------------
    def draw_mouth_normal(self):
        pyxel.line(MOUTH_X - 8, MOUTH_Y, MOUTH_X + 8, MOUTH_Y, pyxel.COLOR_CYAN)

    def draw_mouth_sad(self):
        pyxel.line(MOUTH_X - 8, MOUTH_Y + 4, MOUTH_X, MOUTH_Y - 2, pyxel.COLOR_CYAN)
        pyxel.line(MOUTH_X, MOUTH_Y - 2, MOUTH_X + 8, MOUTH_Y + 4, pyxel.COLOR_CYAN)

    def draw_mouth_angry(self):
        pyxel.rect(MOUTH_X - 9, MOUTH_Y - 2, 18, 5, pyxel.COLOR_RED)
        for i in range(3):
            gx = MOUTH_X - 9 + i * 6
            pyxel.line(gx, MOUTH_Y - 2, gx, MOUTH_Y + 2, pyxel.COLOR_NAVY)

    def draw_mouth_laugh(self):
        pyxel.elli(MOUTH_X - 10, MOUTH_Y - 2, 20, 12, pyxel.COLOR_CYAN)
        pyxel.elli(MOUTH_X - 7, MOUTH_Y - 5, 14, 6, pyxel.COLOR_NAVY)

    def draw_mouth_smile(self):
        pyxel.line(MOUTH_X - 9, MOUTH_Y - 2, MOUTH_X - 4, MOUTH_Y + 4, pyxel.COLOR_CYAN)
        pyxel.line(MOUTH_X - 4, MOUTH_Y + 4, MOUTH_X + 4, MOUTH_Y + 4, pyxel.COLOR_CYAN)
        pyxel.line(MOUTH_X + 4, MOUTH_Y + 4, MOUTH_X + 9, MOUTH_Y - 2, pyxel.COLOR_CYAN)


def main():
    RobotFaceApp()


if __name__ == "__main__":
    main()