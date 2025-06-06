#ifndef PB_RUNTIME_H
#define PB_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>

/* ------------ PRINT ------------- */

void pb_print_int(int64_t x);    
void pb_print_double(double x);  
void pb_print_str(const char *s);
void pb_print_bool(bool b);      

/* ------------ ERROR HANDLING ------------- */

void pb_fail(const char *msg);

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

void list_int_grow_if_needed(List_int *lst);
void list_int_init(List_int *lst);
void list_int_set(List_int *lst, int64_t index, int64_t value);
void list_int_append(List_int *lst, int64_t value);
int64_t list_int_pop(List_int *lst);
bool list_int_remove(List_int *lst, int64_t value);
void list_int_free(List_int *lst);
void list_int_print(const List_int *lst);

void list_float_grow_if_needed(List_float *lst);
void list_float_init(List_float *lst);
void list_float_set(List_float *lst, int64_t index, double value);
void list_float_append(List_float *lst, double value);
double list_float_pop(List_float *lst);
bool list_float_remove(List_float *lst, double value);
void list_float_free(List_float *lst);
void list_float_print(const List_float *lst);

void list_bool_grow_if_needed(List_bool *lst);
void list_bool_init(List_bool *lst);
void list_bool_set(List_bool *lst, int64_t index, bool value);
void list_bool_append(List_bool *lst, bool value);
bool list_bool_pop(List_bool *lst);
bool list_bool_remove(List_bool *lst, bool value);
void list_bool_free(List_bool *lst);
void list_bool_print(const List_bool *lst);

void list_str_grow_if_needed(List_str *lst);
void list_str_init(List_str *lst);
void list_str_set(List_str *lst, int64_t index, const char *value);
void list_str_append(List_str *lst, const char *value);
const char *list_str_pop(List_str *lst);
bool list_str_remove(List_str *lst, const char *value);
void list_str_free(List_str *lst);
void list_str_print(const List_str *lst);

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
int64_t pb_dict_get_str_int(Dict_str_int d, const char *key);

const char* pb_dict_get_str_str(Dict_str_str d, const char *key);

double pb_dict_get_str_float(Dict_str_float d, const char *key);

bool pb_dict_get_str_bool(Dict_str_bool d, const char *key);


#endif // PB_RUNTIME_H
