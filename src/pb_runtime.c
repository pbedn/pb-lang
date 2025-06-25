#include "pb_runtime.h"

/* Utility: portable strdup replacement */
static char *pb_strdup(const char *s) {
    size_t len = strlen(s);
    char *copy = malloc(len + 1);
    if (!copy) {
        pb_fail("Out of memory in pb_strdup");
    }
    memcpy(copy, s, len + 1);
    return copy;
}

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

const char *pb_format_int(int64_t x) {
    static char bufs[4][32];
    static int i = 0;
    i = (i + 1) % 4;

    snprintf(bufs[i], sizeof(bufs[i]), "%" PRId64, x);
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

void pb_raise_msg(const char *type, const char *msg)
{
    pb_current_exc.type  = type;
    pb_current_exc.value = (void *)msg;       /* stored only for re-raise */

    if (pb_current_try) {
        PbTryContext *ctx = pb_current_try;
        pb_current_try    = ctx->prev;
        longjmp(ctx->env, 1);
    }

    /* Uncaught ⇒ abort the program with a readable message */
    char buf[512];
    snprintf(buf, sizeof(buf), "%s: %s", type, msg);
    pb_fail(buf);                             /* pb_fail must not return */
}

void pb_raise_obj(const char *type, void *obj)
{
    pb_current_exc.type  = type;
    pb_current_exc.value = obj;

    if (pb_current_try) {
        PbTryContext *ctx = pb_current_try;
        pb_current_try    = ctx->prev;
        longjmp(ctx->env, 1);
    }

    /* Uncaught ⇒ fetch msg from the struct’s first slot */
    const char *msg = obj ? *((const char **)obj) : NULL;

    char buf[512];
    if (msg)
        snprintf(buf, sizeof(buf), "%s: %s", type, msg);
    else
        snprintf(buf, sizeof(buf), "Uncaught exception of type %s", type);

    pb_fail(buf);
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
// void pb_raise(const char *type, void *value) {
//     // consider to define known error types as global constants (e.g., extern const char *PB_EXC_IOERROR)
//     // const char *PB_EXC_IOERROR = "IOError";
//     // const char *PB_EXC_VALUEERROR = "ValueError";
//     // and codegen would do: if (strcmp(pb_current_exc.type, PB_EXC_VALUEERROR) == 0)
//     pb_current_exc.type = type;
//     pb_current_exc.value = value;
//     if (pb_current_try) {
//         PbTryContext *ctx = pb_current_try;
//         pb_current_try = ctx->prev;
//         longjmp(ctx->env, 1);
//     } else {
//         const char *msg = NULL;

//         /* Heuristic: if value looks like a C string, treat it as such   */
//         if (value && strlen((const char *)value) < 256)
//             msg = (const char *)value;

//         /* Otherwise, assume an Exception-like struct whose first field
//            is a const char *msg and read it through a generic pointer    */
//         else if (value)
//             msg = *((const char **)value);

//         if (msg) {
//             char buf[512];
//             snprintf(buf, sizeof(buf), "%s: %s", type, msg);
//             pb_fail(buf);
//         } else {
//             char buf[256];
//             snprintf(buf, sizeof(buf), "Uncaught exception of type %s", type);
//             pb_fail(buf);
//         }
//     }
// }

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
    pb_raise_obj(pb_current_exc.type, pb_current_exc.value);
}

/* ------------ FILE ------------- */

PbFile pb_open(const char *path, const char *mode) {
    FILE *fp = fopen(path, mode);
    if (!fp) {
        char buf[256];
        snprintf(buf, sizeof(buf), "Failed to open file %s", path);
        pb_fail(buf);
    }
    PbFile f = {fp};
    return f;
}

const char *pb_file_read(PbFile f) {
    fseek(f.handle, 0, SEEK_END);
    long size = ftell(f.handle);
    fseek(f.handle, 0, SEEK_SET);
    char *buf = malloc(size + 1);
    if (!buf) pb_fail("Out of memory in pb_file_read");
    size_t n = fread(buf, 1, size, f.handle);
    buf[n] = '\0';
    return buf;
}

void pb_file_write(PbFile f, const char *s) {
    if (fputs(s, f.handle) == EOF) {
        pb_fail("Failed to write file");
    }
}

void pb_file_close(PbFile f) {
    fclose(f.handle);
}

void pb_index_error(const char *type, const char *op, int64_t index, int64_t len, void *ptr) {
    char buf[256];
    if (strcmp(op, "get") == 0) {
        snprintf(buf, sizeof(buf),
            "cannot get index %" PRId64 " from list[%s] of length %" PRId64 " (valid range: 0 to %" PRId64 ")",
            index, type, len, len > 0 ? len - 1 : -1
        );
    } else if (strcmp(op, "set") == 0) {
        snprintf(buf, sizeof(buf),
            "cannot assign to index %" PRId64 " in list[%s] of length %" PRId64 " (valid range: 0 to %" PRId64 ")",
            index, type, len, len > 0 ? len - 1 : -1
        );
    } else {
        snprintf(buf, sizeof(buf),
            "invalid access to index %" PRId64 " in list[%s] of length %" PRId64,
            index, type, len
        );
    }
    pb_raise_msg("IndexError", pb_strdup(buf));
}

/* ------------ LIST ------------- */

void list_int_grow_if_needed(List_int *lst) {
    if (lst->len >= lst->capacity) {
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY : (lst->capacity * 2);
        int64_t *new_data = (int64_t *)realloc(lst->data, new_capacity * sizeof(int64_t));
        if (!new_data) {
            char buf[128];
            snprintf(buf, sizeof(buf),
                "Failed to allocate memory while growing list[%s]: old capacity = %" PRId64,
                "int", lst->capacity);
            pb_fail(buf);
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
    if (index < 0 || index > lst->len) {
        pb_index_error("int", "set", index, lst->len, lst);
    } else if (index == lst->len) {
        list_int_append(lst, value);
    } else {
        lst->data[index] = value;
    }
}


int64_t list_int_get(List_int *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_index_error("int", "get", index, lst->len, lst);
    }
    return lst->data[index];
}

void list_int_append(List_int *lst, int64_t value) {
    list_int_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

int64_t list_int_pop(List_int *lst) {
    if (lst->len == 0) {
        char buf[128];
        snprintf(buf, sizeof(buf), "Cannot pop from empty list");
        pb_fail(buf);
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
            char buf[128];
            snprintf(buf, sizeof(buf),
                "Failed to allocate memory while growing list[%s]: old capacity = %" PRId64, "int", lst->capacity);
            pb_fail(buf);
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
    if (index < 0 || index > lst->len) {
        pb_index_error("float", "set", index, lst->len, lst);
    } else if (index == lst->len) {
        list_float_append(lst, value);
    } else {
        lst->data[index] = value;
    }
}

double list_float_get(List_float *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_index_error("float", "get", index, lst->len, lst);
    }
    return lst->data[index];
}

void list_float_append(List_float *lst, double value) {
    list_float_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

double list_float_pop(List_float *lst) {
    if (lst->len == 0) {
        char buf[128];
        snprintf(buf, sizeof(buf), "Cannot pop from empty list");
        pb_fail(buf);
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
            char buf[128];
            snprintf(buf, sizeof(buf),
                "Failed to allocate memory while growing list[%s]: old capacity = %" PRId64, "int", lst->capacity);
            pb_fail(buf);
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
    if (index < 0 || index > lst->len) {
        pb_index_error("bool", "set", index, lst->len, lst);
    } else if (index == lst->len) {
        list_bool_append(lst, value);
    } else {
        lst->data[index] = value;
    }
}

bool list_bool_get(List_bool *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_index_error("bool", "get", index, lst->len, lst);
    }
    return lst->data[index];
}

void list_bool_append(List_bool *lst, bool value) {
    list_bool_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

bool list_bool_pop(List_bool *lst) {
    if (lst->len == 0) {
        char buf[128];
        snprintf(buf, sizeof(buf), "Cannot pop from empty list");
        pb_fail(buf);
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
            char buf[128];
            snprintf(buf, sizeof(buf),
                "Failed to allocate memory while growing list[%s]: old capacity = %" PRId64, "int", lst->capacity);
            pb_fail(buf);
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
    if (index < 0 || index > lst->len) {
        pb_index_error("str", "set", index, lst->len, lst);
    } else if (index == lst->len) {
        list_str_append(lst, value);
    } else {
        lst->data[index] = value;  // assumes value is valid for the lifetime of lst
    }
}

const char* list_str_get(List_str *lst, int64_t index) {
    if (index < 0 || index >= lst->len) {
        pb_index_error("str", "get", index, lst->len, lst);
    }
    return lst->data[index];
}

void list_str_append(List_str *lst, const char *value) {
    list_str_grow_if_needed(lst);
    lst->data[lst->len++] = value;
}

const char *list_str_pop(List_str *lst) {
    if (lst->len == 0) {
        char buf[128];
        snprintf(buf, sizeof(buf), "Cannot pop from empty list");
        pb_fail(buf);
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

void set_int_print(const Set_int *s) {
    printf("{");
    for (int64_t i = 0; i < s->len; ++i) {
        if (i > 0) printf(", ");
        printf("%" PRId64, s->data[i]);
    }
    printf("}\n");
}

void set_float_print(const Set_float *s) {
    printf("{");
    for (int64_t i = 0; i < s->len; ++i) {
        if (i > 0) printf(", ");
        printf("%g", s->data[i]);
    }
    printf("}\n");
}

void set_bool_print(const Set_bool *s) {
    printf("{");
    for (int64_t i = 0; i < s->len; ++i) {
        if (i > 0) printf(", ");
        printf(s->data[i] ? "True" : "False");
    }
    printf("}\n");
}

void set_str_print(const Set_str *s) {
    printf("{");
    for (int64_t i = 0; i < s->len; ++i) {
        const char *str = s->data[i];
        if (i > 0) printf(", ");
        bool has_single_quote = strchr(str, '\'') != NULL;
        if (has_single_quote) {
            printf("\"%s\"", str);
        } else {
            printf("'%s'", str);
        }
    }
    printf("}\n");
}


/* ------------ DICT ------------- */

int64_t pb_dict_get_str_int(Dict_str_int d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    char buf[128];
    snprintf(buf, sizeof(buf),
        "Key '%s' not found in dict[%s]", key, "str->int");
    pb_fail(buf);
    return 0;
}

const char* pb_dict_get_str_str(Dict_str_str d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    char buf[128];
    snprintf(buf, sizeof(buf),
        "Key '%s' not found in dict[%s]", key, "str->str");
    pb_fail(buf);
    return "";
}

double pb_dict_get_str_float(Dict_str_float d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    char buf[128];
    snprintf(buf, sizeof(buf),
        "Key '%s' not found in dict[%s]", key, "str->float");
    pb_fail(buf);
    return 0.0;
}

bool pb_dict_get_str_bool(Dict_str_bool d, const char *key) {
    for (int64_t i = 0; i < d.len; ++i) {
        if (strcmp(d.data[i].key, key) == 0) return d.data[i].value;
    }
    char buf[128];
    snprintf(buf, sizeof(buf),
        "Key '%s' not found in dict[%s]", key, "str->bool");
    pb_fail(buf);
    return false;
}
