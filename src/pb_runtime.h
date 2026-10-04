#ifndef PB_RUNTIME_H
#define PB_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>
#include <inttypes.h>
#include <assert.h>

/* PB allocations live until explicit release or process shutdown. Value
 * container copies may share their backing storage; generated code never
 * frees a local merely because its lexical scope ends. */
void *pb_alloc(size_t size);
void pb_release(void *ptr);
void pb_memory_cleanup(void);
const char *pb_string_copy(const char *value);
const char *pb_str_concat(const char *a, const char *b);
const char *pb_string_char(const char *value, int64_t index);
void pb_print_begin(void);
void pb_print_end(void);

/* ------------ PRINT ------------- */

void pb_print_int(int64_t x);    
void pb_print_double(double x);  
void pb_print_str(const char *s);
void pb_print_bool(bool b);      

const char *pb_format_double(double x);
const char *pb_format_int(int64_t x);
const char *pb_format_hex(int64_t x);

/* ------------ ERROR HANDLING ------------- */

void pb_fail(const char *msg);

/* ------------ EXCEPTIONS ------------- */

#include <setjmp.h>
#include <assert.h>

/* PB unwinds plain C frames itself. MinGW's SEH frame unwinding can use an
 * invalid establisher frame in optimized code; a null frame requests the
 * register/stack restore that PB needs, without native SEH unwinding. */
#if defined(__MINGW32__) && defined(__x86_64__)
#define pb_setjmp(env) _setjmp((env), NULL)
#else
#define pb_setjmp(env) setjmp(env)
#endif

typedef struct {
    const char *type;
    void *value;
    bool is_message;
} PbException;

typedef struct PbTryContext {
    jmp_buf env;
    struct PbTryContext *prev;
} PbTryContext;

extern PbTryContext *pb_current_try;
extern PbException pb_current_exc;

void pb_push_try(PbTryContext *ctx);
void pb_pop_try(void);

/* Raise a simple exception whose payload is a C string.*/
void pb_raise_msg(const char *type, const char *msg);

/* Raise an “exception object”.                                       *
 * The object must have ‘const char *msg’ as its first field.          */
void pb_raise_obj(const char *type, void *obj);

void pb_clear_exc(void);
void pb_reraise(void);
bool pb_exception_matches(const char *type);
const char *pb_exception_message(void);
void pb_register_exception(const char *type, const char *base);

/* ------------ FILE ------------- */

typedef struct {
    FILE *handle;
} PbFile;

PbFile pb_open(const char *path, const char *mode);
const char *pb_file_read(PbFile f);
void pb_file_write(PbFile f, const char *s);
void pb_file_close(PbFile f);

/* ------------ LIST ------------- */

/* Generic list declaration helper. */
#define PB_DECLARE_LIST(Name, CType)         \
    typedef struct {                        \
        int64_t len;                        \
        int64_t capacity;                   \
        CType *data;                        \
    } List_##Name;

/* Built-in list specializations */
PB_DECLARE_LIST(int, int64_t)
PB_DECLARE_LIST(float, double)
PB_DECLARE_LIST(bool, bool)
PB_DECLARE_LIST(str, const char *)

/* Generic set declaration helper. */
#define PB_DECLARE_SET(Name, CType)          \
    typedef struct {                        \
        int64_t len;                        \
        int64_t capacity;                   \
        CType *data;                        \
    } Set_##Name;

/* Built-in set specializations */
PB_DECLARE_SET(int, int64_t)
PB_DECLARE_SET(float, double)
PB_DECLARE_SET(bool, bool)
PB_DECLARE_SET(str, const char *)

#define INITIAL_LIST_CAPACITY 4

/* Generic list method declarations */
#define PB_DECLARE_LIST_FUNCS(Name, CType)                             \
    void list_##Name##_grow_if_needed(List_##Name *lst);               \
    void list_##Name##_init(List_##Name *lst);                         \
    void list_##Name##_set(List_##Name *lst, int64_t index, CType value); \
    CType list_##Name##_get(List_##Name *lst, int64_t index);          \
    void list_##Name##_append(List_##Name *lst, CType value);          \
    CType list_##Name##_pop(List_##Name *lst);                         \
    bool list_##Name##_remove(List_##Name *lst, CType value);          \
    void list_##Name##_free(List_##Name *lst);                         \
    void list_##Name##_print(const List_##Name *lst);

PB_DECLARE_LIST_FUNCS(int, int64_t)
PB_DECLARE_LIST_FUNCS(float, double)
PB_DECLARE_LIST_FUNCS(bool, bool)
PB_DECLARE_LIST_FUNCS(str, const char *)

void set_int_print(const Set_int *s);
void set_float_print(const Set_float *s);
void set_bool_print(const Set_bool *s);
void set_str_print(const Set_str *s);

/* ------------ DICT ------------- */

/* Generic dict declaration helper. */
#define PB_DECLARE_DICT(Name, CType)          \
    typedef struct {                         \
        const char *key;                     \
        CType value;                         \
    } Pair_str_##Name;                       \
    typedef struct {                         \
        int64_t len;                         \
        Pair_str_##Name *data;               \
    } Dict_str_##Name;

/* Built-in dict specializations */
PB_DECLARE_DICT(int, int64_t)
PB_DECLARE_DICT(float, double)
PB_DECLARE_DICT(bool, bool)
PB_DECLARE_DICT(str, const char *)

// Dict lookup helpers
int64_t pb_dict_get_str_int(Dict_str_int d, const char *key);

const char* pb_dict_get_str_str(Dict_str_str d, const char *key);

double pb_dict_get_str_float(Dict_str_float d, const char *key);

bool pb_dict_get_str_bool(Dict_str_bool d, const char *key);


List_int list_int_copy(List_int value);
List_float list_float_copy(List_float value);
List_bool list_bool_copy(List_bool value);
List_str list_str_copy(List_str value);
int64_t pb_string_length(const char *value);
void pb_dict_set_str_int(Dict_str_int dict, const char *key, int64_t value);
Set_int set_int_copy(Set_int value);
Dict_str_int dict_str_int_copy(Dict_str_int value);
void pb_dict_set_str_float(Dict_str_float dict, const char *key, double value);
Set_float set_float_copy(Set_float value);
Dict_str_float dict_str_float_copy(Dict_str_float value);
void pb_dict_set_str_bool(Dict_str_bool dict, const char *key, bool value);
Set_bool set_bool_copy(Set_bool value);
Dict_str_bool dict_str_bool_copy(Dict_str_bool value);
void pb_dict_set_str_str(Dict_str_str dict, const char *key, const char * value);
Set_str set_str_copy(Set_str value);
Dict_str_str dict_str_str_copy(Dict_str_str value);
void dict_str_int_print(const Dict_str_int *dict);
void dict_str_float_print(const Dict_str_float *dict);
void dict_str_bool_print(const Dict_str_bool *dict);
void dict_str_str_print(const Dict_str_str *dict);
#endif // PB_RUNTIME_H
