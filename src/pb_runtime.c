#include "pb_runtime.h"

/* ------------ PRINT ------------- */

// PRId64 is a format macro from the C standard header <inttypes.h>
void pb_print_int(int64_t x)   { printf("%" PRId64 "\n", x); }
void pb_print_double(double x)
{
    if (x == (int64_t)x) {
        printf("%.1f\n", x);  // 50.0 (preserve .0)
    } else {
        printf("%.15g\n", x); // Python-like float precision
    }
}
void pb_print_str(const char *s){ printf("%s\n", s); }
void pb_print_bool(bool b)     { printf("%s\n", b ? "True" : "False"); }

const char *pb_format_double(double x) {
    static char bufs[4][32];
    static int i = 0;
    i = (i + 1) % 4;

    if (x == (int64_t)x) {
        snprintf(bufs[i], sizeof(bufs[i]), "%.1f", x);  // 50.0 (preserve .0)
    } else {
        snprintf(bufs[i], sizeof(bufs[i]), "%.15g", x); // Python-like float precision
    }

    return bufs[i];
}


/* ------------ ERROR HANDLING ------------- */

// Immediately exit the program with an error message.
// Used for unrecoverable internal or memory-related errors.
void pb_fail(const char *msg) {
    fprintf(stderr, "%s\n", msg);
    exit(EXIT_FAILURE);
}

/* ------------ EXCEPTION SUPPORT ------------- */

PbTryContext *pb_current_try = NULL;             // Top of try context stack
PbException pb_current_exc = {NULL, NULL};       // Current active exception

#define PB_MAX_TRY_DEPTH 256

int pb_try_depth = 0;

// Push a try context onto the stack
void pb_push_try(PbTryContext *ctx) {
    assert(ctx && "Cannot push NULL try context");
    if (++pb_try_depth > PB_MAX_TRY_DEPTH) {
        pb_fail("Maximum try depth exceeded");
    }
    ctx->prev = pb_current_try;
    pb_current_try = ctx;
}

// Pop the top try context
void pb_pop_try(void) {
    assert(pb_current_try && "Try stack underflow");
    pb_current_try = pb_current_try->prev;
    pb_try_depth--;
}

/**
 * Raise a runtime exception of a given type with an optional value.
 *
 * This function triggers non-local control flow using setjmp/longjmp to
 * unwind to the nearest active try-except block. It should only be used
 * for recoverable, language-level exceptions (not internal runtime errors).
 *
 * If no try context is active, the exception is considered uncaught and the
 * program is terminated via pb_fail().
 *
 * @param type   A string identifying the exception type (e.g. "ValueError").
 * @param value  An optional payload (e.g. a string or struct pointer).
 */
void pb_raise(const char *type, void *value) {
    // consider to define known error types as global constants (e.g., extern const char *PB_EXC_IOERROR)
    // const char *PB_EXC_IOERROR = "IOError";
    // const char *PB_EXC_VALUEERROR = "ValueError";
    // and codegen would do: if (strcmp(pb_current_exc.type, PB_EXC_VALUEERROR) == 0)
    pb_current_exc.type = type;
    pb_current_exc.value = value;
    if (pb_current_try) {
        PbTryContext *ctx = pb_current_try;
        pb_current_try = ctx->prev;
        longjmp(ctx->env, 1);
    } else {
        char buf[256];
        snprintf(buf, sizeof(buf), "Uncaught %s", type);
        pb_fail(buf);
    }
}

// Clear the current exception state
void pb_clear_exc(void) {
    pb_current_exc.type = NULL;
    pb_current_exc.value = NULL;
}

// Re-raise the current exception
void pb_reraise(void) {
    if (!pb_current_exc.type) {
        pb_fail("Cannot re-raise: no active exception");
    }
    pb_raise(pb_current_exc.type, pb_current_exc.value);
}

/* ------------ LIST ------------- */

void list_int_grow_if_needed(List_int *lst) {
    if (lst->len >= lst->capacity) {
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY : (lst->capacity * 2);
        int64_t *new_data = (int64_t *)realloc(lst->data, new_capacity * sizeof(int64_t));
        if (!new_data) {
            pb_fail("No memory to resize list[int]");
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
    }
    lst->data[index] = value;
}

int64_t list_int_get(List_int *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[int] index out of bounds");
    }
    return lst->data[index];
}

void list_int_append(List_int *lst, int64_t value) {
    list_int_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

int64_t list_int_pop(List_int *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
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
    }
    lst->data[index] = value;
}

double list_float_get(List_float *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[float] index out of bounds");
    }
    return lst->data[index];
}

void list_float_append(List_float *lst, double value) {
    list_float_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

double list_float_pop(List_float *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
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
    }
    lst->data[index] = value;
}

bool list_bool_get(List_bool *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[bool] index out of bounds");
        abort();
    }
    return lst->data[index];
}

void list_bool_append(List_bool *lst, bool value) {
    list_bool_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

bool list_bool_pop(List_bool *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
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
        printf(lst->data[i] ? "True" : "False");
    }
    printf("]\n");
}


void list_str_grow_if_needed(List_str *lst) {
    if (lst->len >= lst->capacity) {
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY : (lst->capacity * 2);
        const char **new_data = (const char **)realloc(lst->data, new_capacity * sizeof(const char *));
        if (!new_data) {
            pb_fail("No memory to resize list[str]");
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
    }
    lst->data[index] = value;  // assumes value is valid for the lifetime of lst
}

const char* list_str_get(List_str *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_fail("List[str] index out of bounds");
    }
    return lst->data[index];
}

void list_str_append(List_str *lst, const char *value) {
    list_str_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

const char *list_str_pop(List_str *lst) {
    if (lst->len == 0) {
        pb_fail("Pop from empty list");
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
    assert(lst != NULL && "list is NULL");
    assert(lst->data != NULL && "list data is NULL");

    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        const char *s = lst->data[i];
        assert(s != NULL && "list element is NULL");

        if (i > 0) printf(", ");

        bool has_single_quote = strchr(s, '\'') != NULL;
        if (has_single_quote) {
            printf("\"%s\"", s);
        } else {
            printf("'%s'", s);
        }
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
