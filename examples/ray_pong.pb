# ---------------------------------------------------------------------------
#  RAYLIB‑BASED “PONG” — PB LANGUAGE PORT                                   
#  Requires: raylib native module bindings + SearchAndSetResourceDir helper  
# ---------------------------------------------------------------------------

# --- Native‑module imports --------------------------------------------------
from raylib import (
    # window / timing
    InitWindow, CloseWindow, SetTargetFPS, WindowShouldClose, GetFrameTime,
    SetConfigFlags, SetTraceLogLevel, GetScreenWidth, GetScreenHeight,
    FLAG_VSYNC_HINT, FLAG_MSAA_4X_HINT, LOG_ALL,
    # input
    IsKeyPressed, IsKeyDown, SetExitKey,
    KEY_NULL, KEY_ESCAPE, KEY_ENTER, KEY_SPACE, KEY_W, KEY_S, KEY_R, KEY_P, KEY_M,
    KEY_UP, KEY_DOWN, KEY_Y, KEY_N,
    # drawing primitives
    BeginDrawing, EndDrawing, ClearBackground, DrawRectangleRec, DrawCircleV,
    DrawText, DrawTextPro, DrawLineEx, MeasureText, GetFontDefault,
    # colours
    Color, DARKGRAY, LIGHTGRAY, RAYWHITE, RED,
    # audio
    Sound, make_Sound,
    InitAudioDevice, CloseAudioDevice, LoadSound, UnloadSound, PlaySound,
    # geometry and math helpers
    Rectangle, Vector2, Vector2Add, Vector2Subtract,
    Vector2Normalize, Vector2Scale, Vector2Length,
    make_Vector2, make_Rectangle,
    # utils
    CheckCollisionCircleRec, GetRandomValue
)

# --- Constants --------------------------------------------------------------
SCREEN_WIDTH:  int   = 1280
SCREEN_HEIGHT: int   =  720

PADDLE_WIDTH:  int   =   15
PADDLE_HEIGHT: int   =  150
BALL_SIZE:     int   =   18
BALL_SPEED:    float = 400.0
WIN_SCORE:     int   =   10

# --- Helper constructors ----------------------------------------------------
def make_vec2(x: float, y: float) -> Vector2:
    return make_Vector2(x, y)

def make_rect(x: float, y: float, width: float, height: float) -> Rectangle:
    return make_Rectangle(x, y, width, height)

# --- Simple “enum” replacement ---------------------------------------------
class Scene:
    MAIN_MENU:  int = 1
    PRE_GAME:   int = 2
    GAME:       int = 3
    GAME_OVER:  int = 4
    EXIT_WINDOW:int = 5

# --- Data classes -----------------------------------------------------------
class Paddle:
    rect:  Rectangle
    speed: float

    def __init__(self) -> None:
        self.rect = make_rect(0.0, 0.0, 0.0, 0.0)
        self.speed = 0.0

class Ball:
    position:  Vector2
    direction: Vector2
    speed:     float

    def __init__(self) -> None:
        self.position = make_vec2(0.0, 0.0)
        self.direction = make_vec2(0.0, 0.0)
        self.speed = 0.0

class Sounds:
    hit:  Sound
    edge: Sound
    top:  Sound

    def __init__(self) -> None:
        self.hit = make_Sound()
        self.edge = make_Sound()
        self.top = make_Sound()

class GameState:
    leftScore:   int
    rightScore:  int
    isPaused:    bool
    currentScene:int    # uses Scene.<CONST> values
    prevScene:   int
    sounds:      Sounds
    aiPlayer:    bool

    def __init__(self) -> None:
        self.leftScore = 0
        self.rightScore = 0
        self.isPaused = False
        self.currentScene = 0
        self.prevScene = 0
        self.sounds = Sounds()
        self.aiPlayer = False

def make_paddle(x: int, y: int, speed: float = 500.0) -> Paddle:
    p: Paddle = Paddle()           # zero initialised struct
    p.rect = make_rect(float(x), float(y), float(PADDLE_WIDTH), float(PADDLE_HEIGHT))
    p.speed = speed
    return p

def make_ball() -> Ball:
    b: Ball = Ball()
    b.position  = make_vec2(float(SCREEN_WIDTH) / 2, float(SCREEN_HEIGHT) / 2)
    b.direction = make_vec2(1.0, 1.0)
    b.speed     = BALL_SPEED
    return b

def make_sounds(hit: Sound, edge: Sound, top: Sound) -> Sounds:
    s: Sounds = Sounds()
    s.hit  = hit
    s.edge = edge
    s.top  = top
    return s

def make_game_state(beep: Sound, peep: Sound, plop: Sound) -> GameState:
    gs: GameState = GameState()   # allocate
    gs.leftScore    = 0
    gs.rightScore   = 0
    gs.isPaused     = False
    gs.currentScene = Scene.MAIN_MENU
    gs.prevScene    = Scene.MAIN_MENU
    gs.sounds       = make_sounds(plop, peep, beep)
    gs.aiPlayer     = True
    return gs

def reset_ball(ball: Ball):
    """Re‑centre the ball and randomise serve direction."""
    ball.position = make_vec2(float(SCREEN_WIDTH) / 2, float(SCREEN_HEIGHT) / 2)
    if GetRandomValue(0, 1) == 0:
        ball.direction.x = 1.0
    else:
        ball.direction.x = -1.0
    if GetRandomValue(0, 1) == 0:
        ball.direction.y = 1.0
    else:
        ball.direction.y = -1.0
    ball.speed = BALL_SPEED

def game_logic(lp: Paddle, rp: Paddle, ball: Ball, st: GameState):
    """Update paddles, ball physics, scoring and sounds."""

    # ---- Paddle control ----------------------------------------------------
    if st.aiPlayer:
        # --- Simple AI for left paddle --------------------------------------
        if ball.direction.x > 0:
            # Ball moving away: drift to centre
            centre_y = (SCREEN_HEIGHT - lp.rect.height) / 2
            delta    = centre_y - (lp.rect.y + lp.rect.height / 2)
            if abs(delta) > 10.0:
                if delta > 0:
                    lp.rect.y += lp.speed * GetFrameTime()
                else:
                    lp.rect.y += -lp.speed * GetFrameTime()
        else:
            # Track the ball
            target = ball.position.y
            delta  = target - (lp.rect.y + lp.rect.height / 2)
            if abs(delta) > 1.0:
                if delta > 0:
                    lp.rect.y += lp.speed * GetFrameTime()
                else:
                    lp.rect.y += -lp.speed * GetFrameTime()

        # Bounds clamp
        if lp.rect.y < 0:
            lp.rect.y = 0
        elif lp.rect.y > SCREEN_HEIGHT - lp.rect.height:
            lp.rect.y = SCREEN_HEIGHT - lp.rect.height

        # ---- Human controls for right paddle -------------------------------
        if (IsKeyDown(KEY_W) or IsKeyDown(KEY_UP)) and rp.rect.y > 0:
            rp.rect.y -= rp.speed * GetFrameTime()
        if (IsKeyDown(KEY_S) or IsKeyDown(KEY_DOWN)) and rp.rect.y < SCREEN_HEIGHT - PADDLE_HEIGHT:
            rp.rect.y += rp.speed * GetFrameTime()

    else:
        # Two‑player: WASD vs arrow keys
        if IsKeyDown(KEY_W) and lp.rect.y > 0:
            lp.rect.y -= lp.speed * GetFrameTime()
        if IsKeyDown(KEY_S) and lp.rect.y < SCREEN_HEIGHT - PADDLE_HEIGHT:
            lp.rect.y += lp.speed * GetFrameTime()
        if IsKeyDown(KEY_UP) and rp.rect.y > 0:
            rp.rect.y -= rp.speed * GetFrameTime()
        if IsKeyDown(KEY_DOWN) and rp.rect.y < SCREEN_HEIGHT - PADDLE_HEIGHT:
            rp.rect.y += rp.speed * GetFrameTime()

    # ---- Ball movement -----------------------------------------------------
    ball.position.x += ball.direction.x * ball.speed * GetFrameTime()
    ball.position.y += ball.direction.y * ball.speed * GetFrameTime()

    # Top / bottom collision
    if ball.position.y <= 0 or ball.position.y >= SCREEN_HEIGHT - BALL_SIZE:
        ball.direction.y *= -1
        PlaySound(st.sounds.top)

    # Paddle collision
    if (
        CheckCollisionCircleRec(ball.position, BALL_SIZE / 2, lp.rect) or
        CheckCollisionCircleRec(ball.position, BALL_SIZE / 2, rp.rect)
    ):
        ball.direction.x *= -1
        ball.speed += BALL_SPEED / 10.0
        PlaySound(st.sounds.hit)

    # Scoring
    if ball.position.x < 0:
        st.rightScore += 1
        PlaySound(st.sounds.edge)
        reset_ball(ball)
    elif ball.position.x > SCREEN_WIDTH:
        st.leftScore += 1
        PlaySound(st.sounds.edge)
        reset_ball(ball)

    # Win condition
    if st.leftScore == WIN_SCORE or st.rightScore == WIN_SCORE:
        st.currentScene = Scene.GAME_OVER

def draw_dashed_line(col: Color):
    """Vertical dashed centre line."""
    start = make_vec2(float(SCREEN_WIDTH) / 2, 0.0)
    end   = make_vec2(float(SCREEN_WIDTH) / 2, float(SCREEN_HEIGHT))
    dash = 10.0
    gap = 5.0
    direction = Vector2Normalize(Vector2Subtract(end, start))
    length    = Vector2Length(Vector2Subtract(end, start))
    offset: float = 0.0

    while offset < length:
        seg_start = Vector2Add(start, Vector2Scale(direction, offset))
        seg_end   = Vector2Add(seg_start, Vector2Scale(direction, dash))
        DrawLineEx(seg_start, seg_end, 5, col)
        offset += dash + gap

# ---------------------------------------------------------------------------
#  MAIN ENTRY
# ---------------------------------------------------------------------------
def main() -> int:
    # SearchAndSetResourceDir("resources")        # helper from your tooling
    SetTraceLogLevel(LOG_ALL)
    SetConfigFlags(FLAG_VSYNC_HINT)
    SetConfigFlags(FLAG_MSAA_4X_HINT)
    InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "Pong Game — PB")
    SetTargetFPS(60)

    # ----- Audio ------------------------------------------------------------
    InitAudioDevice()
    sn_beep: Sound = LoadSound("sounds/ping_pong_8bit_beeep.ogg")
    sn_peep: Sound = LoadSound("sounds/ping_pong_8bit_peeeeeep.ogg")
    sn_plop: Sound = LoadSound("sounds/ping_pong_8bit_plop.ogg")

    # ----- Game‑state initialisation ---------------------------------------
    state: GameState = make_game_state(sn_beep, sn_peep, sn_plop)

    SetExitKey(KEY_NULL)            # we handle ESC manually
    exit_window: bool = False

    left:  Paddle = make_paddle(
        50,
        (SCREEN_HEIGHT // 2) - (PADDLE_HEIGHT // 2)
    )
    right: Paddle = make_paddle(
        SCREEN_WIDTH - 50 - PADDLE_WIDTH,
        (SCREEN_HEIGHT // 2) - (PADDLE_HEIGHT // 2)
    )
    
    ball: Ball = make_ball()
    reset_ball(ball)

    # ----- Main loop --------------------------------------------------------
    while not exit_window:
        # -- high‑level scene switching keys --------------------------------
        if WindowShouldClose() or IsKeyPressed(KEY_ESCAPE):
            state.prevScene    = state.currentScene
            state.currentScene = Scene.EXIT_WINDOW

        if state.currentScene == Scene.EXIT_WINDOW:
            if IsKeyPressed(KEY_Y):
                exit_window = True
            elif IsKeyPressed(KEY_N):
                state.currentScene = state.prevScene

        # -- Scene‑specific logic -------------------------------------------
        if state.currentScene == Scene.MAIN_MENU:
            if IsKeyPressed(KEY_ENTER):
                state.currentScene = Scene.PRE_GAME
                state.aiPlayer = True
            elif IsKeyPressed(KEY_SPACE):
                state.currentScene = Scene.GAME
                state.aiPlayer = False

        elif state.currentScene == Scene.PRE_GAME:
            if (
                IsKeyPressed(KEY_SPACE) or IsKeyPressed(KEY_ENTER)
                or IsKeyPressed(KEY_W) or IsKeyPressed(KEY_UP)
                or IsKeyPressed(KEY_S) or IsKeyPressed(KEY_DOWN)
            ):
                state.currentScene = Scene.GAME

        elif state.currentScene == Scene.GAME:
            if not state.isPaused:
                game_logic(left, right, ball, state)
            if IsKeyPressed(KEY_P):
                state.isPaused = not state.isPaused

        elif state.currentScene == Scene.GAME_OVER:
            ball.speed = 0.0
            if IsKeyPressed(KEY_R):
                state.leftScore = 0
                state.rightScore = 0
                reset_ball(ball)
                state.currentScene = Scene.GAME
            elif IsKeyPressed(KEY_M):
                state.currentScene = Scene.MAIN_MENU

            # no default: PB enforces exhaustiveness on match

        # -- Rendering -------------------------------------------------------
        BeginDrawing()
        if state.currentScene == Scene.EXIT_WINDOW:
            ClearBackground(DARKGRAY)
            msg = "Are you sure you want to exit? [Y/N]"
            DrawText(
                msg,
                GetScreenWidth() // 2 - MeasureText(msg, 30) // 2,
                GetScreenHeight() // 2,
                30,
                RAYWHITE
            )

        elif state.currentScene == Scene.MAIN_MENU:
            ClearBackground(DARKGRAY)
            font = GetFontDefault()
            origin = make_vec2(0.0, 0.0)

            pos = make_vec2(
                float(SCREEN_WIDTH) / 2 - float(MeasureText("PONG!", 40)) / 2,
                float(SCREEN_HEIGHT) / 2 - 80.0
            )
            DrawTextPro(font, "PONG!", pos, origin, 0.0, 40, 2, RAYWHITE)

            pos = make_vec2(
                float(SCREEN_WIDTH) / 2 - float(MeasureText("Play with AI (Enter)", 20)) / 2,
                float(SCREEN_HEIGHT) / 2
            )
            DrawTextPro(font, "Play with AI (Enter)", pos, origin, 0.0, 20, 2, RAYWHITE)

            pos = make_vec2(
                float(SCREEN_WIDTH) / 2 - float(MeasureText("Local Two‑Player (Space)", 20)) / 2,
                float(SCREEN_HEIGHT) / 2 + 40.0
            )
            DrawTextPro(font, "Local Two‑Player (Space)", pos, origin, 0.0, 20, 2, RAYWHITE)

            pos = make_vec2(
                float(SCREEN_WIDTH) / 2 - float(MeasureText("Exit (Esc)", 20)) / 2,
                float(SCREEN_HEIGHT) / 2 + 80.0
            )
            DrawTextPro(font, "Exit (Esc)", pos, origin, 0.0, 20, 2, RAYWHITE)

        elif state.currentScene == Scene.PRE_GAME:
            ClearBackground(DARKGRAY)
            DrawRectangleRec(left.rect,  LIGHTGRAY)
            DrawRectangleRec(right.rect, LIGHTGRAY)
            draw_dashed_line(LIGHTGRAY)
            DrawText(f"{state.leftScore}", SCREEN_WIDTH // 4,       20, 80, LIGHTGRAY)
            DrawText(f"{state.rightScore}", 3 * SCREEN_WIDTH // 4, 20, 80, LIGHTGRAY)
            DrawText(
                "Press any paddle key to start",
                SCREEN_WIDTH // 2 - SCREEN_WIDTH // 4,
                SCREEN_HEIGHT // 3,
                50,
                RAYWHITE
            )

        elif state.currentScene == Scene.GAME:
            ClearBackground(DARKGRAY)
            DrawRectangleRec(left.rect,  RAYWHITE)
            DrawRectangleRec(right.rect, RAYWHITE)
            DrawCircleV(ball.position, BALL_SIZE // 2, RAYWHITE)
            draw_dashed_line(RAYWHITE)
            DrawText(f"{state.leftScore}",  SCREEN_WIDTH // 4,       20, 80, RAYWHITE)
            DrawText(f"{state.rightScore}", 3 * SCREEN_WIDTH // 4, 20, 80, RAYWHITE)
            if state.isPaused:
                DrawText(
                    "Paused",
                    SCREEN_WIDTH // 2 - MeasureText("Paused", 60) // 2,
                    SCREEN_HEIGHT // 2,
                    60,
                    RED
                )

        elif state.currentScene == Scene.GAME_OVER:
            ClearBackground(DARKGRAY)
            DrawRectangleRec(left.rect,  LIGHTGRAY)
            DrawRectangleRec(right.rect, LIGHTGRAY)
            draw_dashed_line(LIGHTGRAY)
            DrawText(f"{state.leftScore}",  SCREEN_WIDTH // 4,       20, 80, LIGHTGRAY)
            DrawText(f"{state.rightScore}", 3 * SCREEN_WIDTH // 4, 20, 80, LIGHTGRAY)
            DrawText(
                "Press R to restart or M for menu",
                SCREEN_WIDTH // 2 - SCREEN_WIDTH // 4,
                SCREEN_HEIGHT // 2,
                50,
                RAYWHITE
            )

        EndDrawing()

    # ----- Clean‑up ---------------------------------------------------------
    UnloadSound(sn_beep)
    UnloadSound(sn_peep)
    UnloadSound(sn_plop)
    CloseAudioDevice()
    CloseWindow()
    return 0

# ---------------------------------------------------------------------------
#  Execute immediately when run as main programme
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
