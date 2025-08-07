#include <math.h>
#include <iso646.h>
#include <stdbool.h>

#include "raylib.h"
#include "raymath.h"
#include "resource_dir.h"

#define PADDLE_WIDTH 15
#define PADDLE_HEIGHT 150
#define BALL_SIZE 18
#define BALL_SPEED 400.0f
#define WIN_SCORE 10

typedef struct Paddle {
    Rectangle rect;
    float speed;
} Paddle;

typedef struct Ball {
    Vector2 position;
    Vector2 direction;
    float speed;
} Ball;

typedef struct {
    Sound hit;
    Sound edge;
    Sound top;
} Sounds;

typedef enum {
    MAIN_MENU,
    PREGAME,
    GAME,
    GAME_OVER,
    EXIT_WINDOW
} Scene;

typedef struct {
    int leftScore;
    int rightScore;
    bool isPaused;
    Scene currentScene;
    Scene prevScene;
    Sounds sounds;
    bool aiPlayer;
} GameState;

const int screenWidth = 1280;
const int screenHeight = 720;

void GameLogic(Paddle *leftPaddle, Paddle *rightPaddle, Ball *ball, GameState *state);
void ResetBall(Ball *ball);
void DrawDashedLine(Color color);
void DrawMainMenu();
void DrawGame();
void DrawGameOver();
