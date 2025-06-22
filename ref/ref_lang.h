#pragma once
#include "pb_runtime.h"
#include "utils.h"
extern int64_t counter;
typedef struct Player {
    int64_t hp;
    const char * species;
    int64_t mp;
    int64_t score;
    const char * name;
} Player;
typedef struct Mage {
    Player base;
    const char * power;
    int64_t mp;
} Mage;
int64_t lang_add(int64_t x, int64_t y);
int64_t lang_divide(int64_t x, int64_t y);
int64_t lang_increment(int64_t x, int64_t step);
bool lang_is_even(int64_t n);
void Player____init__(struct Player * self, int64_t hp, int64_t mp);
void Player__heal(struct Player * self, int64_t amount);
const char * Player__get_name(struct Player * self);
const char * Player__get_species_one(struct Player * self);
void Player__add_to_counter(struct Player * self);
void Mage____init__(struct Mage * self, int64_t hp);
void Mage__cast_spell(struct Mage * self, int64_t spell_cost);
void Mage__heal(struct Mage * self, int64_t amount);
