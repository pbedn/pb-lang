#include <stdio.h>
#include <stdbool.h>

int counter = 100;
int add(int x, int y) {
    int result = (x + y);
    printf("%s\n", "Adding numbers:");
    printf("%d\n", result);
    return result;
}

bool is_even(int n) {
    if (((n % 2) == 0)) {
        return true;
    }
    else {
        return false;
    }
}

int main() {
    printf("%s\n", "=== Global Variable Before Update ===");
    printf("%d\n", counter);
    counter = 200;  // global update
    printf("%s\n", "=== Global Variable After Update ===");
    printf("%d\n", counter);
    printf("%s\n", "=== Function Call ===");
    int total = add(10, 5);
    printf("%s\n", "=== Handle Float/Double ===");
    double threshold = 50.0;
    printf("%f\n", threshold);
    printf("%s\n", "=== If/Else ===");
    if (is_even(total)) {
        printf("%s\n", "Total is even");
    }
    else {
        printf("%s\n", "Total is odd");
    }
    printf("%s\n", "=== While Loop ===");
    int loop_counter = 0;
    while ((loop_counter < 3)) {
        printf("%d\n", loop_counter);
        loop_counter = (loop_counter + 1);
    }
    printf("%s\n", "=== For Loop with range(0, 3) ===");
    for (int i = 0; i < 3; i++) {
        printf("%d\n", i);
    }
    printf("%s\n", "=== For Loop with range(2) ===");
    for (int j = 0; j < 2; j++) {
        printf("%d\n", j);
    }
    printf("%s\n", "=== Break and Continue ===");
    for (int k = 0; k < 5; k++) {
        if ((k == 2)) {
            continue;
        }
        if ((k == 4)) {
            break;
        }
        printf("%d\n", k);
    }
    printf("%s\n", "=== List and Indexing ===");
    int numbers[] = { 100, 200, 300 };
    int first_number = numbers[0];
    int second_number = numbers[1];
    printf("%d\n", first_number);
    printf("%d\n", second_number);
    printf("%s\n", "=== Boolean Literals ===");
    bool x = true;
    bool y = false;
    if ((x && (!y))) {
        printf("%s\n", "x is True and y is False");
    }
    printf("%s\n", "=== Boolean List and Indexing ===");
    bool flags[] = { true, false, true };
    bool first_flag = flags[0];
    bool second_flag = flags[1];
    printf("%s\n", first_flag ? "true" : "false");
    printf("%s\n", second_flag ? "true" : "false");
    printf("%s\n", "=== If/Elif/Else ===");
    int n = 5;
    if ((n == 0)) {
        printf("%s\n", "zero");
    }
    else {
        if ((n == 5)) {
            printf("%s\n", "five");
        }
        else {
            printf("%s\n", "other");
        }
    }
    printf("%s\n", "=== Pass Statement ===");
    if (true) {
        // pass
    }
    printf("%s\n", "Pass block completed");
    printf("%s\n", "=== Is / Is Not Operators ===");
    int a = 10;
    int b = 10;
    if ((a == b)) {
        printf("%s\n", "a is b");
    }
    if ((a != 20)) {
        printf("%s\n", "a is not 20");
    }
    printf("%s\n", "=== Augmented Assignment ===");
    int m = 5;
    printf("%d\n", m);
    m += 3;
    printf("%d\n", m);
    m -= 2;
    printf("%d\n", m);
    m *= 4;
    printf("%d\n", m);
    m /= 2;
    printf("%d\n", m);
    m %= 3;
    printf("%d\n", m);
    return 0;
}
