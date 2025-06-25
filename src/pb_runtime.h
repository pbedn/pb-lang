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

void list_int_grow_if_needed(List_int *lst);
void list_int_init(List_int *lst);
void list_int_set(List_int *lst, int64_t index, int64_t value);
int64_t list_int_get(List_int *lst, int64_t index);
void list_int_append(List_int *lst, int64_t value);
int64_t list_int_pop(List_int *lst);
bool list_int_remove(List_int *lst, int64_t value);
void list_int_free(List_int *lst);
void list_int_print(const List_int *lst);

void list_float_grow_if_needed(List_float *lst);
void list_float_init(List_float *lst);
void list_float_set(List_float *lst, int64_t index, double value);
double list_float_get(List_float *lst, int64_t index);
void list_float_append(List_float *lst, double value);
double list_float_pop(List_float *lst);
bool list_float_remove(List_float *lst, double value);
void list_float_free(List_float *lst);
void list_float_print(const List_float *lst);

void list_bool_grow_if_needed(List_bool *lst);
void list_bool_init(List_bool *lst);
void list_bool_set(List_bool *lst, int64_t index, bool value);
bool list_bool_get(List_bool *lst, int64_t index);
void list_bool_append(List_bool *lst, bool value);
bool list_bool_pop(List_bool *lst);
bool list_bool_remove(List_bool *lst, bool value);
void list_bool_free(List_bool *lst);
void list_bool_print(const List_bool *lst);

void list_str_grow_if_needed(List_str *lst);
void list_str_init(List_str *lst);
void list_str_set(List_str *lst, int64_t index, const char *value);
const char* list_str_get(List_str *lst, int64_t index);
void list_str_append(List_str *lst, const char *value);
const char *list_str_pop(List_str *lst);
bool list_str_remove(List_str *lst, const char *value);
void list_str_free(List_str *lst);
void list_str_print(const List_str *lst);

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
