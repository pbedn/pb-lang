#include "pb_runtime.h"

typedef struct PbAllocation {
    void *ptr;
    struct PbAllocation *next;
} PbAllocation;
typedef struct PbExceptionType {
    const char *type;
    const char *base;
    struct PbExceptionType *next;
} PbExceptionType;
static PbExceptionType *pb_exception_types = NULL;


static PbAllocation *pb_allocations = NULL;
static bool pb_cleanup_registered = false;

void pb_memory_cleanup(void) {
    pb_exception_types = NULL;
    while (pb_allocations) {
        PbAllocation *allocation = pb_allocations;
        pb_allocations = allocation->next;
        free(allocation->ptr);
        free(allocation);
    }
}

void *pb_alloc(size_t size) {
    if (!pb_cleanup_registered) {
        if (atexit(pb_memory_cleanup) != 0) pb_fail("Cannot register memory cleanup");
        pb_cleanup_registered = true;
    }
    void *ptr = malloc(size ? size : 1);
    PbAllocation *allocation = malloc(sizeof(*allocation));
    if (!ptr || !allocation) pb_fail("Out of memory");
    allocation->ptr = ptr;
    allocation->next = pb_allocations;
    pb_allocations = allocation;
    return ptr;
}

void pb_release(void *ptr) {
    PbAllocation **link = &pb_allocations;
    while (*link) {
        if ((*link)->ptr == ptr) {
            PbAllocation *allocation = *link;
            *link = allocation->next;
            free(ptr);
            free(allocation);
            return;
        }
        link = &(*link)->next;
    }
    /* Borrowed storage, including C stack arrays, is never freed here. */
}

const char *pb_string_copy(const char *value) {
    size_t size = strlen(value) + 1;
    char *copy = pb_alloc(size);
    memcpy(copy, value, size);
    return copy;
}

const char *pb_str_concat(const char *a, const char *b) {
    size_t a_len = strlen(a), b_len = strlen(b);
    if (b_len > SIZE_MAX - a_len - 1) pb_fail("String too large");
    char *result = pb_alloc(a_len + b_len + 1);
    memcpy(result, a, a_len);
    memcpy(result + a_len, b, b_len + 1);
    return result;
}

const char *pb_string_char(const char *value, int64_t index) {
    const unsigned char *p = (const unsigned char *)value;
    for (int64_t i = 0; i < index && *p; i++) {
        p++;
        while ((*p & 0xc0) == 0x80) p++;
    }
    const unsigned char *end = p;
    if (*end) {
        end++;
        while ((*end & 0xc0) == 0x80) end++;
    }
    size_t length = (size_t)(end - p);
    char *result = pb_alloc(length + 1);
    memcpy(result, p, length);
    result[length] = '\0';
    return result;
}

static bool pb_inline_print = false;
static bool pb_print_first = true;
void pb_print_begin(void) { pb_inline_print = true; pb_print_first = true; }
void pb_print_end(void) { putchar('\n'); pb_inline_print = false; }
static void pb_print_prefix(void) {
    if (pb_inline_print && !pb_print_first) putchar(' ');
    pb_print_first = false;
}
static void pb_print_suffix(void) { if (!pb_inline_print) putchar('\n'); }

/* Utility: portable strdup replacement */
static char *pb_strdup(const char *s) {
    size_t len = strlen(s);
    char *copy = pb_alloc(len + 1);
    if (!copy) {
        pb_fail("Out of memory in pb_strdup");
    }
    memcpy(copy, s, len + 1);
    return copy;
}

/* ------------ PRINT ------------- */

// PRId64 is a format macro from the C standard header <inttypes.h>
void pb_print_int(int64_t x)   { pb_print_prefix(); printf("%" PRId64, x); pb_print_suffix(); }
void pb_print_double(double x)
{
    pb_print_prefix();
    if (x == (int64_t)x) {
        printf("%.1f", x);
    } else {
        printf("%.15g", x);
    }
    pb_print_suffix();
}
void pb_print_str(const char *s){ pb_print_prefix(); printf("%s", s); pb_print_suffix(); }
void pb_print_bool(bool b)     { pb_print_str(b ? "True" : "False"); }

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
PbException pb_current_exc = {NULL, NULL, false};

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
    pb_current_exc.is_message = true;

    if (pb_current_try) {
        PbTryContext *ctx = pb_current_try;
        pb_current_try    = ctx->prev;
        pb_try_depth--;
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
    pb_current_exc.is_message = false;

    if (pb_current_try) {
        PbTryContext *ctx = pb_current_try;
        pb_current_try    = ctx->prev;
        pb_try_depth--;
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
    pb_current_exc.is_message = false;
}

// Re-raise the current exception
void pb_reraise(void) {
    if (!pb_current_exc.type) {
        pb_fail("Cannot re-raise: no active exception");
    }
    if (pb_current_exc.is_message)
        pb_raise_msg(pb_current_exc.type, pb_current_exc.value);
    else
        pb_raise_obj(pb_current_exc.type, pb_current_exc.value);
}

void pb_register_exception(const char *type, const char *base) {
    for (PbExceptionType *item = pb_exception_types; item; item = item->next)
        if (strcmp(item->type, type) == 0) return;
    PbExceptionType *item = pb_alloc(sizeof(*item));
    item->type = type;
    item->base = base;
    item->next = pb_exception_types;
    pb_exception_types = item;
}

bool pb_exception_matches(const char *type) {
    const char *current = pb_current_exc.type;
    for (int depth = 0; current && depth < 256; depth++) {
        if (strcmp(current, type) == 0) return true;
        const char *base = NULL;
        for (PbExceptionType *item = pb_exception_types; item; item = item->next)
            if (strcmp(item->type, current) == 0) { base = item->base; break; }
        if (!base) {
            if (strcmp(current, "BaseException") == 0) return false;
            base = strcmp(current, "Exception") == 0 ? "BaseException" : "Exception";
        }
        current = base;
    }
    return false;
}

const char *pb_exception_message(void) {
    if (pb_current_exc.is_message) return (const char *)pb_current_exc.value;
    return pb_current_exc.value ? *(const char **)pb_current_exc.value : "";
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
    char *buf = pb_alloc((size_t)size + 1);
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
        if (new_capacity <= lst->len) new_capacity = lst->len + 1;                  \
        CType *new_data = pb_alloc((size_t)new_capacity * sizeof(CType));           \
        if (lst->data) memcpy(new_data, lst->data, (size_t)lst->len * sizeof(CType)); \
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
        pb_release(lst->data);                                                             \
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
    pb_print_prefix();
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf("%" PRId64, lst->data[i]);
    }
    printf("]");
    pb_print_suffix();
}

void list_float_print(const List_float *lst) {
    pb_print_prefix();
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
    printf("]");
    pb_print_suffix();
}

void list_bool_print(const List_bool *lst) {
    pb_print_prefix();
    printf("[");
    for (int64_t i = 0; i < lst->len; ++i) {
        if (i > 0) printf(", ");
        printf(lst->data[i] ? "True" : "False");
    }
    printf("]");
    pb_print_suffix();
}

void list_str_print(const List_str *lst) {
    assert(lst != NULL && "list is NULL");
    assert(lst->data != NULL && "list data is NULL");

    pb_print_prefix();
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
    printf("]");
    pb_print_suffix();
}

void set_int_print(const Set_int *s) {
    pb_print_prefix();
    printf("{");
    for (int64_t i = 0; i < s->len; ++i) {
        if (i > 0) printf(", ");
        printf("%" PRId64, s->data[i]);
    }
    printf("}");
    pb_print_suffix();
}

void set_float_print(const Set_float *s) {
    pb_print_prefix();
    printf("{");
    for (int64_t i = 0; i < s->len; ++i) {
        if (i > 0) printf(", ");
        printf("%g", s->data[i]);
    }
    printf("}");
    pb_print_suffix();
}

void set_bool_print(const Set_bool *s) {
    pb_print_prefix();
    printf("{");
    for (int64_t i = 0; i < s->len; ++i) {
        if (i > 0) printf(", ");
        printf(s->data[i] ? "True" : "False");
    }
    printf("}");
    pb_print_suffix();
}

void set_str_print(const Set_str *s) {
    pb_print_prefix();
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
    printf("}");
    pb_print_suffix();
}


/* Updating dictionaries is supported for existing keys. Insertion needs a
 * separate mutable dictionary representation and remains a planned feature. */
#define PB_DEFINE_DICT_METHODS(Name, CType, Default) \
CType pb_dict_get_str_##Name(Dict_str_##Name dict, const char *key) { \
    for (int64_t i = 0; i < dict.len; i++) \
        if (strcmp(dict.data[i].key, key) == 0) return dict.data[i].value; \
    pb_raise_msg("KeyError", pb_string_copy(key)); \
    return Default; \
} \
void pb_dict_set_str_##Name(Dict_str_##Name dict, const char *key, CType value) { \
    for (int64_t i = 0; i < dict.len; i++) \
        if (strcmp(dict.data[i].key, key) == 0) { dict.data[i].value = value; return; } \
    pb_raise_msg("KeyError", pb_string_copy(key)); \
}
PB_DEFINE_DICT_METHODS(int, int64_t, 0)
PB_DEFINE_DICT_METHODS(float, double, 0.0)
PB_DEFINE_DICT_METHODS(bool, bool, false)
PB_DEFINE_DICT_METHODS(str, const char *, "")

#define PB_DEFINE_LIST_COPY(Name, CType) \
List_##Name list_##Name##_copy(List_##Name value) { \
    if (value.len == 0) return (List_##Name){0}; \
    CType *data = pb_alloc((size_t)value.len * sizeof(CType)); \
    memcpy(data, value.data, (size_t)value.len * sizeof(CType)); \
    return (List_##Name){value.len, value.len, data}; \
}
PB_DEFINE_LIST_COPY(int, int64_t)
PB_DEFINE_LIST_COPY(float, double)
PB_DEFINE_LIST_COPY(bool, bool)
PB_DEFINE_LIST_COPY(str, const char *)

int64_t pb_string_length(const char *value) {
    int64_t length = 0;
    for (const unsigned char *p = (const unsigned char *)value; *p; p++)
        if ((*p & 0xc0) != 0x80) length++;
    return length;
}

#define PB_DEFINE_CONTAINER_COPY(Name, CType) \
Set_##Name set_##Name##_copy(Set_##Name value) { \
    CType *data = pb_alloc((size_t)value.len * sizeof(CType)); \
    memcpy(data, value.data, (size_t)value.len * sizeof(CType)); \
    return (Set_##Name){value.len, value.len, data}; \
} \
Dict_str_##Name dict_str_##Name##_copy(Dict_str_##Name value) { \
    Pair_str_##Name *data = pb_alloc((size_t)value.len * sizeof(*data)); \
    memcpy(data, value.data, (size_t)value.len * sizeof(*data)); \
    for (int64_t i = 0; i < value.len; i++) data[i].key = pb_string_copy(data[i].key); \
    return (Dict_str_##Name){value.len, data}; \
}
PB_DEFINE_CONTAINER_COPY(int, int64_t)
PB_DEFINE_CONTAINER_COPY(float, double)
PB_DEFINE_CONTAINER_COPY(bool, bool)
PB_DEFINE_CONTAINER_COPY(str, const char *)

#define PB_DEFINE_DICT_PRINT(Name, PrintValue) \
void dict_str_##Name##_print(const Dict_str_##Name *dict) { \
    pb_print_prefix(); \
    putchar('{'); \
    for (int64_t i = 0; i < dict->len; i++) { \
        if (i) printf(", "); \
        printf("'%s': ", dict->data[i].key); \
        PrintValue; \
    } \
    putchar('}'); \
    pb_print_suffix(); \
}
PB_DEFINE_DICT_PRINT(int, printf("%" PRId64, dict->data[i].value))
PB_DEFINE_DICT_PRINT(float, printf("%s", pb_format_double(dict->data[i].value)))
PB_DEFINE_DICT_PRINT(bool, printf("%s", dict->data[i].value ? "True" : "False"))
PB_DEFINE_DICT_PRINT(str, printf("'%s'", dict->data[i].value))
