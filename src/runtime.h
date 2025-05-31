#ifndef PB_RUNTIME_H
#define PB_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>

// Failure helper
static inline void pb_fail(const char *msg) {
    fprintf(stderr, "%s\n", msg);
    exit(EXIT_FAILURE);
}

// List of int
typedef struct {
    int64_t len;
    int64_t *data;
} List_int;

// Dict[str, int]
typedef struct {
    const char *key;
    int64_t value;
} Pair_str_int;

typedef struct {
    int64_t len;
    Pair_str_int *data;
} Dict_str_int;

// Print helpers
static inline void pb_print_int(int64_t x)   { printf("%lld\n", x); }
static inline void pb_print_double(double x) { printf("%f\n", x); }
static inline void pb_print_str(const char *s){ printf("%s\n", s); }
static inline void pb_print_bool(bool b)     { printf("%s\n", b ? "True" : "False"); }

// Dict lookup helper
static inline int64_t pb_dict_get(Dict_str_int d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return 0;
}

#endif // PB_RUNTIME_H
