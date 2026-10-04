#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>

int main() {
    int64_t s = 0;
    for (int i = 0; i < 50000000; i++) {
        s += (i % 10) * (i / 3);
    }
    printf("%" PRId64 "\n", s);
    return 0;
}
