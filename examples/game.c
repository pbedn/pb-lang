#include "game.h"

// #define DEV_MODE

int main(void) {
    SearchAndSetResourceDir("resources");

    SetTraceLogLevel( LOG_ALL );
    SetConfigFlags( FLAG_VSYNC_HINT | FLAG_MSAA_4X_HINT);
    InitWindow(screenWidth, screenHeight, "Pong Game");
    SetTargetFPS(60);

    InitAudioDevice();
    Sound sn_beep = LoadSound("sounds/ping_pong_8bit_beeep.ogg");
    Sound sn_peep = LoadSound("sounds/ping_pong_8bit_peeeeeep.ogg");
    Sound sn_plop = LoadSound("sounds/ping_pong_8bit_plop.ogg");

    GameState state = {
        .leftScore = 0,
        .rightScore = 0,
        .isPaused = false,
        .currentScene = MAIN_MENU,
        .prevScene = 0,
        .sounds = {.top = sn_beep, .edge = sn_peep, .hit = sn_plop},
        .aiPlayer = true,
    };

    SetExitKey(KEY_NULL);
    bool exitWindow = false;    // Flag to set window to exit

#ifdef DEV_MODE
    state.currentScene = PREGAME;
#endif

    Paddle leftPaddle = {{50, (int)((screenHeight / 2)) - (PADDLE_HEIGHT / 2), PADDLE_WIDTH, PADDLE_HEIGHT}, 500.0f};
    Paddle rightPaddle = {{screenWidth - 50 - PADDLE_WIDTH, (int)((screenHeight / 2)) - (PADDLE_HEIGHT / 2), PADDLE_WIDTH, PADDLE_HEIGHT}, 500.0f};
    Ball ball = {(Vector2){(int)(screenWidth / 2),(int)( screenHeight / 2)}, (Vector2){1.0f, 1.0f}, BALL_SPEED}; // Direction normalized

    ResetBall(&ball); // Initial reset

    while (!exitWindow) {
        if (WindowShouldClose() || IsKeyPressed(KEY_ESCAPE)) {
            state.prevScene = state.currentScene;
            state.currentScene = EXIT_WINDOW;
        }

        if (state.currentScene == EXIT_WINDOW) {
            if (IsKeyPressed(KEY_Y)) exitWindow = true;
            else if (IsKeyPressed(KEY_N)) state.currentScene = state.prevScene;
        }

        switch (state.currentScene) {
            case MAIN_MENU:
                if (IsKeyPressed(KEY_ENTER)) {
                    state.currentScene = PREGAME;

                    state.aiPlayer = true;
                }
                else if (IsKeyPressed(KEY_SPACE)) {
                    state.currentScene = GAME;
                    state.aiPlayer = false;
                }
                else if (IsKeyPressed(KEY_ESCAPE)) {
                    CloseWindow();
                }
                break;
            case PREGAME:
                if (IsKeyPressed(KEY_SPACE) or IsKeyPressed(KEY_ENTER)
                    or IsKeyPressed(KEY_W) or IsKeyPressed(KEY_UP)
                    or IsKeyPressed(KEY_S) or IsKeyPressed(KEY_DOWN))
                    state.currentScene = GAME;
                break;
            case GAME:
                if (!state.isPaused)
                    GameLogic(&leftPaddle, &rightPaddle, &ball, &state);
                if (IsKeyPressed(KEY_P)) {
                    state.isPaused = !state.isPaused;
                }
                break;
            case GAME_OVER:
                ball.speed = 0.0f;
                if (IsKeyPressed(KEY_R)) {
                    state.leftScore = 0;
                    state.rightScore = 0;
                    ResetBall(&ball);
                    state.currentScene = GAME;
                }
                else if (IsKeyPressed(KEY_M)) {
                    state.currentScene = MAIN_MENU;
                }
                break;
            default: break;
        }

        BeginDrawing();
        switch (state.currentScene) {
            case EXIT_WINDOW:
                ClearBackground(DARKGRAY);
                char * exit_str = "Are you sure you want to exit program? [Y/N]";
                DrawText(exit_str, GetScreenWidth() / 2 - MeasureText(exit_str, 30) / 2, GetScreenHeight() / 2, 30, RAYWHITE);
                break;
            case MAIN_MENU:
                ClearBackground(DARKGRAY);
                Font defaultFont = GetFontDefault();
                Vector2 origin = { 0, 0 };
                float rotation = 0.0f; // No rotation
                float fontSize = 40.0f; // Normal size
                float spacing = 2.0f;
                DrawTextPro(defaultFont, "PONG!", (Vector2){GetScreenWidth() / 2 - MeasureText("PONG!", fontSize) / 2, GetScreenHeight() / 2 - 80}, origin, rotation, fontSize, spacing, RAYWHITE);
                DrawTextPro(defaultFont, "Play with AI (press Enter)", (Vector2){GetScreenWidth() / 2 - MeasureText("Play with AI (press 1)", 20) / 2, GetScreenHeight() / 2}, origin, rotation, 20, spacing, RAYWHITE);
                DrawTextPro(defaultFont, "Local Two Player (press Space)", (Vector2){GetScreenWidth() / 2 - MeasureText("Play with AI (press 1)", 20) / 2, GetScreenHeight() / 2 + 40}, origin, rotation, 20, spacing, RAYWHITE);
                DrawTextPro(defaultFont, "Exit (Press Escape)", (Vector2){GetScreenWidth() / 2 - MeasureText("Play with AI (press 1)", 20) / 2, GetScreenHeight() / 2 + 80}, origin, rotation, 20, spacing, RAYWHITE);
                break;
            case PREGAME:
                ClearBackground(DARKGRAY);
                DrawRectangleRec(leftPaddle.rect, LIGHTGRAY);
                DrawRectangleRec(rightPaddle.rect, LIGHTGRAY);
                DrawDashedLine(LIGHTGRAY);
                DrawText(TextFormat("%d", state.leftScore), screenWidth / 4, 20, 80, LIGHTGRAY);
                DrawText(TextFormat("%d", state.rightScore), 3 * screenWidth / 4, 20, 80, LIGHTGRAY);
                DrawText(TextFormat("Press to start game."), (screenWidth / 2) - (screenWidth / 4), screenHeight / 3, 60, RAYWHITE);
                break;
            case GAME:
                ClearBackground(DARKGRAY);
                DrawRectangleRec(leftPaddle.rect, RAYWHITE);
                DrawRectangleRec(rightPaddle.rect, RAYWHITE);
                DrawCircleV(ball.position, BALL_SIZE / 2, RAYWHITE);
                DrawDashedLine(RAYWHITE);
                DrawText(TextFormat("%d", state.leftScore), screenWidth / 4, 20, 80, RAYWHITE);
                DrawText(TextFormat("%d", state.rightScore), 3 * screenWidth / 4, 20, 80, RAYWHITE);
                if (state.isPaused) {
                    ClearBackground(DARKGRAY);
                    DrawRectangleRec(leftPaddle.rect, LIGHTGRAY);
                    DrawRectangleRec(rightPaddle.rect, LIGHTGRAY);
                    DrawDashedLine(LIGHTGRAY);
                    DrawText(TextFormat("Paused."), GetScreenWidth() / 2 - MeasureText("Paused", 60) / 2, screenHeight / 2, 60, RED);
                    break;
                }
                break;
            case GAME_OVER:
                ClearBackground(DARKGRAY);
                DrawRectangleRec(leftPaddle.rect, LIGHTGRAY);
                DrawRectangleRec(rightPaddle.rect, LIGHTGRAY);
                DrawDashedLine(LIGHTGRAY);
                DrawText(TextFormat("%d", state.leftScore), screenWidth / 4, 20, 80, LIGHTGRAY);
                DrawText(TextFormat("%d", state.rightScore), 3 * screenWidth / 4, 20, 80, LIGHTGRAY);
                DrawText(TextFormat("Press R to restart game."), (screenWidth / 2) - (screenWidth / 4), screenHeight / 2, 60, RAYWHITE);
                break;
            }
        EndDrawing();
    }

    // De-Initialization
    UnloadSound(sn_beep);
    UnloadSound(sn_peep);
    UnloadSound(sn_plop);
    CloseAudioDevice();     // Close audio device
    CloseWindow(); // Close window and OpenGL context

    return 0;
}

void GameLogic(Paddle *leftPaddle, Paddle *rightPaddle, Ball *ball, GameState *state) {
    if (state->aiPlayer) {
        if(ball->direction.x > 0) {
        // If the ball is moving away from the left paddle
        // Move the paddle slowly towards the center of the screen
        float centerY = (screenHeight - leftPaddle->rect.height) / 2;
        float distanceToCenter = centerY - (leftPaddle->rect.y + leftPaddle->rect.height / 2);

        if (fabs(distanceToCenter) > 10.0f) { // Only move if the distance is significant
            if (distanceToCenter > 0) {
                leftPaddle->rect.y += (leftPaddle->speed) * GetFrameTime(); // Move down slowly
            } else {
                leftPaddle->rect.y -= (leftPaddle->speed) * GetFrameTime(); // Move up slowly
            }
        }
        else {
            leftPaddle = leftPaddle;
        }
        } else {

            // Calculate the target position based on the ball's position
            float targetY = ball->position.y;

            // Calculate the distance to the target position
            float distance = targetY - (leftPaddle->rect.y + leftPaddle->rect.height / 2);

            // Move the paddle towards the ball's position
            if (fabs(distance) > 1.0f) { // Only move if the distance is significant
                if (distance > 0) {
                    leftPaddle->rect.y += leftPaddle->speed * GetFrameTime(); // Move down
                } else {
                    leftPaddle->rect.y -= leftPaddle->speed * GetFrameTime(); // Move up
                }
            }

            // Clamp the paddle's position to stay within the game boundaries
            if (leftPaddle->rect.y < 0) {
                leftPaddle->rect.y = 0;
            } else if (leftPaddle->rect.y > screenWidth - leftPaddle->rect.height) {
                leftPaddle->rect.y = screenHeight - leftPaddle->rect.height;
            }
        }

        // Extended Player Input
        if ((IsKeyDown(KEY_W) || IsKeyDown(KEY_UP)) && rightPaddle->rect.y > 0) {
            rightPaddle->rect.y -= rightPaddle->speed * GetFrameTime();
        }
        if ((IsKeyDown(KEY_S) || IsKeyDown(KEY_DOWN)) && rightPaddle->rect.y < screenHeight - PADDLE_HEIGHT) {
            rightPaddle->rect.y += rightPaddle->speed * GetFrameTime();
        }
    } else {
        // Two PlayerInput
        if (IsKeyDown(KEY_W) && leftPaddle->rect.y > 0) {
            leftPaddle->rect.y -= leftPaddle->speed * GetFrameTime();
        }
        if (IsKeyDown(KEY_S) && leftPaddle->rect.y < screenHeight - PADDLE_HEIGHT) {
            leftPaddle->rect.y += leftPaddle->speed * GetFrameTime();
        }
        if (IsKeyDown(KEY_UP) && rightPaddle->rect.y > 0) {
            rightPaddle->rect.y -= rightPaddle->speed * GetFrameTime();
        }
        if (IsKeyDown(KEY_DOWN) && rightPaddle->rect.y < screenHeight - PADDLE_HEIGHT) {
            rightPaddle->rect.y += rightPaddle->speed * GetFrameTime();
        }
    }

    // Update ball position
    ball->position.x += ball->direction.x * ball->speed * GetFrameTime();
    ball->position.y += ball->direction.y * ball->speed * GetFrameTime();

    // Ball collision with top and bottom
    if (ball->position.y <= 0 || ball->position.y >= screenHeight - BALL_SIZE) {
        ball->direction.y *= -1; // Reverse Y direction
        PlaySound(state->sounds.top);
    }

    // Ball collision with paddles
    if (CheckCollisionCircleRec(ball->position, BALL_SIZE / 2, leftPaddle->rect) || 
        CheckCollisionCircleRec(ball->position, BALL_SIZE / 2, rightPaddle->rect)) {
        ball->direction.x *= -1; // Reverse X direction
        ball->speed += BALL_SPEED / 10.0;
        PlaySound(state->sounds.hit);
    }

    // Scoring
    if (ball->position.x < 0) {
        PlaySound(state->sounds.edge);
        state->rightScore++; // Right player scores
        ResetBall(ball);
    }
    if (ball->position.x > screenWidth) {
        PlaySound(state->sounds.edge);
        state->leftScore++;  // Left player scores
        ResetBall(ball);
    }

    if (state->leftScore == WIN_SCORE or state->rightScore == WIN_SCORE)
        state->currentScene = GAME_OVER;

    // TraceLog(LOG_DEBUG, "After Update: x: %f, y: %f", ball->direction.x, ball->direction.y);
}

void ResetBall(Ball *ball) {
    ball->position = (Vector2){(int)(screenWidth / 2),(int)( screenHeight / 2)};
    ball->direction.x = (GetRandomValue(0, 1) == 0) ? 1.0f : -1.0f; // Randomize initial direction
    ball->direction.y = (GetRandomValue(-1, 1) < 0) ? 1.0f : -1.0f; // Randomize initial vertical direction
    ball->speed = BALL_SPEED;
}

void DrawDashedLine(Color color) {
    Vector2 start = { (int)(screenWidth / 2), 0 };
    Vector2 end = { (int)(screenWidth / 2), screenHeight };
    float dashLength = 10.0f;
    float gapLength = 5.0f;
    Vector2 direction = Vector2Subtract(end, start);
    float length = Vector2Length(direction);
    direction = Vector2Normalize(direction);

    float totalLength = 0.0f;
    while (totalLength < length) {
        // Calculate the start and end points of the dash
        Vector2 dashStart = Vector2Add(start, Vector2Scale(direction, totalLength));
        Vector2 dashEnd = Vector2Add(dashStart, Vector2Scale(direction, dashLength));

        // Draw the dash
        DrawLineEx(dashStart, dashEnd, 5, color);

        // Move the total length by the dash length and gap length
        totalLength += dashLength + gapLength;
    }
}
