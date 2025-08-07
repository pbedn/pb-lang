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

const char *pb_format_hex(int64_t x) {
    static char bufs[4][32];
    static int i = 0;
    i = (i + 1) % 4;

    if (x < 0) {
        uint32_t val = (uint32_t)(-x);
        snprintf(bufs[i], sizeof(bufs[i]), "-0x%08" PRIx32, val);
    } else {
        uint32_t val = (uint32_t)x;
        snprintf(bufs[i], sizeof(bufs[i]), "0x%08" PRIx32, val);
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

/* Utility equality helpers used by generic list macros */
#define PB_EQ(a, b) ((a) == (b))
#define PB_STR_EQ(a, b) (strcmp((a), (b)) == 0)

/* Generic list method implementations */
#define PB_DEFINE_LIST_METHODS(Name, CType, TypeStr, EQ)                              \
void list_##Name##_grow_if_needed(List_##Name *lst) {                                \
    if (lst->len >= lst->capacity) {                                                 \
        int64_t new_capacity = (lst->capacity == 0) ? INITIAL_LIST_CAPACITY          \
                                                   : (lst->capacity * 2);            \
        CType *new_data;                                                             \
        if (lst->capacity == 0 && lst->data != NULL) {                               \
            new_data = (CType *)malloc(new_capacity * sizeof(CType));                \
            if (!new_data) {                                                         \
                char buf[128];                                                       \
                snprintf(buf, sizeof(buf),                                            \
                    "Failed to allocate memory while growing list[%s]: old capacity = %" PRId64, \
                    TypeStr, lst->capacity);                                         \
                pb_fail(buf);                                                        \
            }                                                                        \
            memcpy(new_data, lst->data, lst->len * sizeof(CType));                   \
        } else {                                                                     \
            new_data = (CType *)realloc(lst->data, new_capacity * sizeof(CType));    \
            if (!new_data) {                                                         \
                char buf[128];                                                       \
                snprintf(buf, sizeof(buf),                                            \
                    "Failed to allocate memory while growing list[%s]: old capacity = %" PRId64, \
                    TypeStr, lst->capacity);                                         \
                pb_fail(buf);                                                        \
            }                                                                        \
        }                                                                            \
        lst->data = new_data;                                                        \
        lst->capacity = new_capacity;                                                \
    }                                                                                \
}                                                                                    \
void list_##Name##_init(List_##Name *lst) {                                          \
    lst->len = 0;                                                                    \
    lst->capacity = 0;                                                               \
    lst->data = NULL;                                                                \
}                                                                                    \
void list_##Name##_set(List_##Name *lst, int64_t index, CType value) {               \
    if (index < 0 || index >= lst->len) {                                            \
        pb_index_error(TypeStr, "set", index, lst->len, lst);                       \
    } else {                                                                         \
        lst->data[index] = value;                                                    \
    }                                                                                \
}                                                                                    \
CType list_##Name##_get(List_##Name *lst, int64_t index) {                           \
    if (index < 0 || index >= lst->len) {                                            \
        pb_index_error(TypeStr, "get", index, lst->len, lst);                       \
    }                                                                                \
    return lst->data[index];                                                         \
}                                                                                    \
void list_##Name##_append(List_##Name *lst, CType value) {                           \
    list_##Name##_grow_if_needed(lst);                                               \
    lst->data[lst->len++] = value;                                                   \
}                                                                                    \
CType list_##Name##_pop(List_##Name *lst) {                                          \
    if (lst->len == 0) {                                                             \
        char buf[128];                                                               \
        snprintf(buf, sizeof(buf), "Cannot pop from empty list");                   \
        pb_fail(buf);                                                                \
    }                                                                                \
    return lst->data[--lst->len];                                                    \
}                                                                                    \
bool list_##Name##_remove(List_##Name *lst, CType value) {                           \
    for (int64_t i = 0; i < lst->len; ++i) {                                         \
        if (EQ(lst->data[i], value)) {                                               \
            for (int64_t j = i; j + 1 < lst->len; ++j) {                              \
                lst->data[j] = lst->data[j + 1];                                      \
            }                                                                        \
            lst->len--;                                                              \
            return true;                                                             \
        }                                                                            \
    }                                                                                \
    return false;                                                                    \
}                                                                                    \
void list_##Name##_free(List_##Name *lst) {                                          \
    if (lst->data) {                                                                 \
        free(lst->data);                                                             \
        lst->data = NULL;                                                            \
    }                                                                                \
    lst->len = 0;                                                                    \
    lst->capacity = 0;                                                               \
}

PB_DEFINE_LIST_METHODS(int, int64_t, "int", PB_EQ)
PB_DEFINE_LIST_METHODS(float, double, "float", PB_EQ)
PB_DEFINE_LIST_METHODS(bool, bool, "bool", PB_EQ)
PB_DEFINE_LIST_METHODS(str, const char *, "str", PB_STR_EQ)

void list_int_print(const List_int *lst) {
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf("%" PRId64, lst->data[i]);
    }
    printf("]\n");
}

void list_float_print(const List_float *lst) {
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        double x = lst->data[i];
        if (x == (int64_t)x) {
            printf("%.1f", x);  // 50.0 (preserve .0)
        } else {
            printf("%.15g", x); // Python-like float precision
        }
    }
    printf("]\n");
}

void list_bool_print(const List_bool *lst) {
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf(lst->data[i] ? "True" : "False");
    }
    printf("]\n");
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
