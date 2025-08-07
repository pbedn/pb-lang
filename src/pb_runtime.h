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

typedef struct {
    const char *type;
    void *value;
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


#endif // PB_RUNTIME_H
