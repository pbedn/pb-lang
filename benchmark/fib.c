#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>

int64_t fib(int64_t n) {
	if (n <= 2)
		return 1;
	else
        return fib(n - 1) + fib(n - 2);
}

int main() {
    printf("%" PRId64 "\n", fib(38));
    return 0;
}
