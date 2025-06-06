#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>
#include <inttypes.h>

#include "pb_runtime.h"

/* ------------ PRINT ------------- */

// PRId64 is a format macro from the C standard header <inttypes.h>
void pb_print_int(int64_t x)   { printf("%" PRId64 "\n", x); }
void pb_print_double(double x) { printf("%f\n", x); }
void pb_print_str(const char *s){ printf("%s\n", s); }
void pb_print_bool(bool b)     { printf("%s\n", b ? "True" : "False"); }

/* ------------ ERROR HANDLING ------------- */

void pb_fail(const char *msg) {
    fprintf(stderr, "%s\n", msg);
    exit(EXIT_FAILURE);
}

/* ------------ LIST ------------- */

void list_int_grow_if_needed(List_int *lst) {
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

void list_int_init(List_int *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

void list_int_set(List_int *lst, int64_t index, int64_t value) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[int] assignment index out of bounds");
        abort();
    }
    lst->data[index] = value;
}
void list_int_append(List_int *lst, int64_t value) {
    list_int_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

int64_t list_int_pop(List_int *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

bool list_int_remove(List_int *lst, int64_t value) {
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

void list_int_free(List_int *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

void list_int_print(const List_int *lst) {
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf("%" PRId64, lst->data[i]);
    }
    printf("]\n");
}


void list_float_grow_if_needed(List_float *lst) {
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

void list_float_init(List_float *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

void list_float_set(List_float *lst, int64_t index, double value) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[float] assignment index out of bounds");
        abort();
    }
    lst->data[index] = value;
}
void list_float_append(List_float *lst, double value) {
    list_float_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

double list_float_pop(List_float *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

bool list_float_remove(List_float *lst, double value) {
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

void list_float_free(List_float *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

void list_float_print(const List_float *lst) {
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf("%g", lst->data[i]);
    }
    printf("]\n");
}


void list_bool_grow_if_needed(List_bool *lst) {
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

void list_bool_init(List_bool *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

void list_bool_set(List_bool *lst, int64_t index, bool value) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[bool] assignment index out of bounds");
        abort();
    }
    lst->data[index] = value;
}
void list_bool_append(List_bool *lst, bool value) {
    list_bool_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

bool list_bool_pop(List_bool *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

bool list_bool_remove(List_bool *lst, bool value) {
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

void list_bool_free(List_bool *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

void list_bool_print(const List_bool *lst) {
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf(lst->data[i] ? "true" : "false");
    }
    printf("]\n");
}


void list_str_grow_if_needed(List_str *lst) {
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

void list_str_init(List_str *lst) {
    lst->len = 0;
    lst->capacity = 0;
    lst->data = NULL;
}

void list_str_set(List_str *lst, int64_t index, const char *value) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[str] assignment index out of bounds");
        abort();
    }
    lst->data[index] = value;  // assumes value is valid for the lifetime of lst
}
void list_str_append(List_str *lst, const char *value) {
    list_str_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

const char *list_str_pop(List_str *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
        abort();
    }
    return lst->data[--lst->len];
}

bool list_str_remove(List_str *lst, const char *value) {
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

void list_str_free(List_str *lst) {
    if (lst->data) {
        free(lst->data);
        lst->data = NULL;
    }
    lst->len = 0;
    lst->capacity = 0;
}

void list_str_print(const List_str *lst) {
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf("\"%s\"", lst->data[i]);
    }
    printf("]\n");
}

/* ------------ DICT ------------- */

int64_t pb_dict_get_str_int(Dict_str_int d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return 0;
}

const char* pb_dict_get_str_str(Dict_str_str d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return "";
}

double pb_dict_get_str_float(Dict_str_float d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return 0.0;
}

bool pb_dict_get_str_bool(Dict_str_bool d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    pb_fail("Key not found in dict");
    return false;
}
