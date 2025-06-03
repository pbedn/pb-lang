#ifndef PB_RUNTIME_H
#define PB_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>

/* ------------ PRINT ------------- */

static inline void pb_print_int(int64_t x)   { printf("%lld\n", x); }
static inline void pb_print_double(double x) { printf("%f\n", x); }
static inline void pb_print_str(const char *s){ printf("%s\n", s); }
static inline void pb_print_bool(bool b)     { printf("%s\n", b ? "True" : "False"); }

/* ------------ ERROR HANDLING ------------- */

inline void pb_fail(const char *msg) {
    fprintf(stderr, "%s\n", msg);
    exit(EXIT_FAILURE);
}

/* ------------ LIST ------------- */
typedef struct {
    int64_t len;
    int64_t capacity;
    int64_t *data;
} List_int;

typedef struct {
    int64_t len;
    int64_t capacity;
    double *data;
} List_float;

typedef struct {
    int64_t len;
    int64_t capacity;
    bool *data;
} List_bool;

typedef struct {
    int64_t len;
    int64_t capacity;
    const char **data;
} List_str;

#define INITIAL_LIST_CAPACITY 4

inline void list_int_grow_if_needed(List_int *lst) {
    if (lst->len >= lst->capacity) {
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY : (lst->capacity * 2);
        int64_t *new_data = (int64_t *)realloc(lst->data, new_capacity * sizeof(int64_t));
        if (!new_data) {
            pb_fail("No memory to resize list[int]");
            abort();
        }
        lst->data = new_data;
        lst->capacity = new_capacity;
    }
}

inline void list_int_init(List_int *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

inline void list_int_append(List_int *lst, int64_t value) {
    list_int_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

inline int64_t list_int_pop(List_int *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

inline bool list_int_remove(List_int *lst, int64_t value) {
    for (int64_t i = 0; i < lst->len; ++i) {
        if (lst->data[i] == value) {
            /* Move elements to the left */
            for (int64_t j = i; j + 1 < lst->len; ++j) {
                lst->data[j] = lst->data[j + 1];
            }
            lst->len--;
            return true;
        }
    }
    return false;
}

inline void list_int_free(List_int *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

inline void list_float_grow_if_needed(List_float *lst) {
    if (lst->len >= lst->capacity) {
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY : (lst->capacity * 2);
        double *new_data = (double *)realloc(lst->data, new_capacity * sizeof(double));
        if (!new_data) {
            pb_fail("No memory to resize list[float]");
            abort();
        }
        lst->data = new_data;
        lst->capacity = new_capacity;
    }
}

inline void list_float_init(List_float *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

inline void list_float_append(List_float *lst, double value) {
    list_float_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

inline double list_float_pop(List_float *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

inline bool list_float_remove(List_float *lst, double value) {
    for (int64_t i = 0; i < lst->len; ++i) {
        if (lst->data[i] == value) {
            /* Move elements to the left */
            for (int64_t j = i; j + 1 < lst->len; ++j) {
                lst->data[j] = lst->data[j + 1];
            }
            lst->len--;
            return true;
        }
    }
    return false;
}

inline void list_float_free(List_float *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

inline void list_bool_grow_if_needed(List_bool *lst) {
    if (lst->len >= lst->capacity) {
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY : (lst->capacity * 2);
        bool *new_data = (bool *)realloc(lst->data, new_capacity * sizeof(bool));
        if (!new_data) {
            pb_fail("No memory to resize list[bool]");
            abort();
        }
        lst->data = new_data;
        lst->capacity = new_capacity;
    }
}

inline void list_bool_init(List_bool *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

inline void list_bool_append(List_bool *lst, bool value) {
    list_bool_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

inline bool list_bool_pop(List_bool *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

inline bool list_bool_remove(List_bool *lst, bool value) {
    for (int64_t i = 0; i < lst->len; ++i) {
        if (lst->data[i] == value) {
            /* Move elements to the left */
            for (int64_t j = i; j + 1 < lst->len; ++j) {
                lst->data[j] = lst->data[j + 1];
            }
            lst->len--;
            return true;
        }
    }
    return false;
}

inline void list_bool_free(List_bool *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

inline void list_str_grow_if_needed(List_str *lst) {
    if (lst->len >= lst->capacity) {
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY : (lst->capacity * 2);
        const char **new_data = (const char **)realloc(lst->data, new_capacity * sizeof(const char *));
        if (!new_data) {
            pb_fail("No memory to resize list[str]");
            abort();
        }
        lst->data = new_data;
        lst->capacity = new_capacity;
    }
}

inline void list_str_init(List_str *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

inline void list_str_append(List_str *lst, const char *value) {
    list_str_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

inline const char *list_str_pop(List_str *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

inline bool list_str_remove(List_str *lst, const char *value) {
    for (int64_t i = 0; i < lst->len; ++i) {
        if (strcmp(lst->data[i], value) == 0) {
            /* Move elements to the left */
            for (int64_t j = i; j + 1 < lst->len; ++j) {
                lst->data[j] = lst->data[j + 1];
            }
            lst->len--;
            return true;
        }
    }
    return false;
}

inline void list_str_free(List_str *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

/* ------------ DICT ------------- */

// Dict[str, int]
typedef struct {
    const char *key;
    int64_t value;
} Pair_str_int;

typedef struct {
    int64_t len;
    Pair_str_int *data;
} Dict_str_int;

// Dict[str, float]
typedef struct {
    const char *key;
    double value;
} Pair_str_float;

typedef struct {
    int64_t len;
    Pair_str_float *data;
} Dict_str_float;

// Dict[str, bool]
typedef struct {
    const char *key;
    bool value;
} Pair_str_bool;

typedef struct {
    int64_t len;
    Pair_str_bool *data;
} Dict_str_bool;

// Dict[str, str]
typedef struct {
    const char *key;
    const char *value;
} Pair_str_str;

typedef struct {
    int64_t len;
    Pair_str_str *data;
} Dict_str_str;

// Dict lookup helpers
inline int64_t pb_dict_get_str_int(Dict_str_int d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return 0;
}

inline const char* pb_dict_get_str_str(Dict_str_str d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return "";
}

inline double pb_dict_get_str_float(Dict_str_float d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return 0.0;
}

inline bool pb_dict_get_str_bool(Dict_str_bool d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return false;
}


#endif // PB_RUNTIME_H
