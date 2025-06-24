#include "lang.h"
int64_t counter = 100;
int64_t Player_hp = 100;
const char * Player_species = "Human";
const char * Mage_power = "fire";
void Player____init__(struct Player * self, int64_t hp, int64_t mp)
{
    (void)self;
    (void)hp;
    (void)mp;
    char __fbuf[256];
    (void)__fbuf;
    self->hp = hp;
    self->mp = mp;
    self->score = 0;
    self->name = "Hero";
}
void Player__heal(struct Player * self, int64_t amount)
{
    (void)self;
    (void)amount;
    char __fbuf[256];
    (void)__fbuf;
    self->hp += amount;
}
const char * Player__get_name(struct Player * self)
{
    (void)self;
    char __fbuf[256];
    (void)__fbuf;
    return self->name;
}
const char * Player__get_species_one(struct Player * self)
{
    (void)self;
    char __fbuf[256];
    (void)__fbuf;
    return Player_species;
}
void Player__add_to_counter(struct Player * self)
{
    (void)self;
    char __fbuf[256];
    (void)__fbuf;
    /* global counter */
    counter += self->hp;
}
void Mage____init__(struct Mage * self, int64_t hp)
{
    (void)self;
    (void)hp;
    char __fbuf[256];
    (void)__fbuf;
    Player____init__((struct Player *)self, hp, 150);
    self->mp = 200;
}
void Mage__cast_spell(struct Mage * self, int64_t spell_cost)
{
    (void)self;
    (void)spell_cost;
    char __fbuf[256];
    (void)__fbuf;
    if ((self->mp >= spell_cost)) {
        pb_print_str("Spell cast!");
        self->mp -= spell_cost;
    }
    else  {
        pb_print_str("Not enough mana");
    }
}
void Mage__heal(struct Mage * self, int64_t amount)
{
    (void)self;
    (void)amount;
    char __fbuf[256];
    (void)__fbuf;
    self->base.hp += amount;
    self->mp += (amount / 2);
}
static inline void Mage__add_to_counter(
    struct Mage * self) {
    Player__add_to_counter((struct Player *)self);
}
static inline const char * Mage__get_name(
    struct Mage * self) {
    return Player__get_name((struct Player *)self);
}
static inline const char * Mage__get_species_one(
    struct Mage * self) {
    return Player__get_species_one((struct Player *)self);
}
int64_t lang_add(int64_t x, int64_t y)
{
    (void)x;
    (void)y;
    char __fbuf[256];
    (void)__fbuf;
    int64_t result = (x + y);
    pb_print_str("Adding numbers:");
    pb_print_int(result);
    return result;
}
int64_t lang_divide(int64_t x, int64_t y)
{
    (void)x;
    (void)y;
    char __fbuf[256];
    (void)__fbuf;
    if ((y == 0)) {
        pb_raise_msg("RuntimeError", "division by zero");
    }
    return (x / y);
}
int64_t lang_increment(int64_t x, int64_t step)
{
    (void)x;
    (void)step;
    char __fbuf[256];
    (void)__fbuf;
    return (x + step);
}
bool lang_is_even(int64_t n)
{
    (void)n;
    char __fbuf[256];
    (void)__fbuf;
    if (((n % 2) == 0)) {
        return true;
    }
    else  {
        return false;
    }
}
int main(void)
{
    char __fbuf[256];
    (void)__fbuf;
    pb_print_str("=== F-String Interpolation ===");
    int64_t value = 42;
    const char * name = "Alice";
    pb_print_str((snprintf(__fbuf, 256, "Value is %lld", value), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Hello, %s!", name), __fbuf));
    pb_print_str("=== Global Variable===");
    /* global counter */
    pb_print_str((snprintf(__fbuf, 256, "Before Update: %lld", counter), __fbuf));
    counter = 200;
    pb_print_str((snprintf(__fbuf, 256, "After Update: %lld", counter), __fbuf));
    pb_print_str("=== Function Call ===");
    int64_t total = lang_add(10, 5);
    int64_t divided = lang_divide(10, 5);
    pb_print_str("=== Function with Default Argument ===");
    int64_t a = lang_increment(5, 1);
    int64_t b = lang_increment(5, 3);
    pb_print_int(a);
    pb_print_int(b);
    pb_print_str("=== Assert Statement ===");
    int64_t abc = 10;
    int64_t efg = 10;
    if(!((abc == efg))) pb_fail("Assertion failed");
    pb_print_str("Assertion passed");
    pb_print_str("=== Handle Float/Double ===");
    double threshold = 50.0;
    pb_print_double(threshold);
    pb_print_str("=== If/Else ===");
    if (lang_is_even(total)) {
        pb_print_str("Total is even");
    }
    else  {
        pb_print_str("Total is odd");
    }
    pb_print_str("=== While Loop ===");
    int64_t loop_counter = 0;
    while ((loop_counter < 3)) {
        pb_print_int(loop_counter);
        loop_counter = (loop_counter + 1);
    }
    pb_print_str("=== For Loop with range(0, 3) ===");
    for (int64_t i = 0; i < 3; ++i) {
        pb_print_int(i);
    }
    pb_print_str("=== For Loop with range(2) ===");
    for (int64_t j = 0; j < 2; ++j) {
        pb_print_int(j);
    }
    pb_print_str("=== Break and Continue ===");
    for (int64_t k = 0; k < 5; ++k) {
        if ((k == 2)) {
        continue;
    }
        if ((k == 4)) {
        break;
    }
        pb_print_int(k);
    }
    pb_print_str("=== List and Indexing ===");
    int64_t __tmp_list_1[] = {100, 200, 300};
    List_int numbers = (List_int){ .len=3, .data=__tmp_list_1 };
    int64_t first_number = list_int_get(&numbers, 0);
    pb_print_int(first_number);
    pb_print_int(list_int_get(&numbers, 0));
    list_int_print(&numbers);
    int64_t __tmp_list_2[1] = {0};
    List_int arr_int_empty = (List_int){ .len=0, .data=__tmp_list_2 };
    const char * __tmp_list_3[1] = {0};
    List_str arr_str_empty = (List_str){ .len=0, .data=__tmp_list_3 };
    bool __tmp_list_4[1] = {0};
    List_bool arr_bool_empty = (List_bool){ .len=0, .data=__tmp_list_4 };
    double __tmp_list_5[] = {1.1, 2.2, 3.3};
    List_float arr_float_init = (List_float){ .len=3, .data=__tmp_list_5 };
    const char * __tmp_list_6[] = {"abc", "def"};
    List_str arr_str_init = (List_str){ .len=2, .data=__tmp_list_6 };
    bool __tmp_list_7[] = {true, false};
    List_bool arr_bool_init = (List_bool){ .len=2, .data=__tmp_list_7 };
    pb_print_double(list_float_get(&arr_float_init, 0));
    list_float_print(&arr_float_init);
    pb_print_str(list_str_get(&arr_str_init, 0));
    list_str_print(&arr_str_init);
    pb_print_bool(list_bool_get(&arr_bool_init, 0));
    list_bool_print(&arr_bool_init);
    list_float_set(&arr_float_init, 0, 100.101);
    list_str_set(&arr_str_init, 0, "some string");
    list_bool_set(&arr_bool_init, 0, false);
    list_float_print(&arr_float_init);
    list_str_print(&arr_str_init);
    list_bool_print(&arr_bool_init);
    pb_print_str("=== List Operations ===");
    pb_print_str("=== Dict Literal and Access ===");
    Pair_str_int __tmp_dict_1[] = {{"volume", 10}, {"brightness", 75}};
    Dict_str_int settings = (Dict_str_int){ .len=2, .data=__tmp_dict_1 };
    pb_print_int(pb_dict_get_str_int(settings, "volume"));
    pb_print_int(pb_dict_get_str_int(settings, "brightness"));
    Pair_str_str __tmp_dict_2[] = {{"a", "sth here"}, {"b", "and here"}};
    Dict_str_str map_str = (Dict_str_str){ .len=2, .data=__tmp_dict_2 };
    pb_print_str(pb_dict_get_str_str(map_str, "a"));
    pb_print_str(pb_dict_get_str_str(map_str, "b"));
    pb_print_str("=== Try / Except / Raise ===");
    PbTryContext __exc_ctx_1;
    pb_push_try(&__exc_ctx_1);
    int __exc_flag_1 = setjmp(__exc_ctx_1.env);
    bool __exc_handled_1 = false;
    if (__exc_flag_1 == 0) {
        int64_t result = lang_divide(10, 0);
        pb_print_int(result);
    pb_pop_try();
    } else {
        if (strcmp(pb_current_exc.type, "RuntimeError") == 0) {
            pb_print_str("Caught division by zero");
            pb_clear_exc();
            __exc_handled_1 = true;
        }
        else {
            pb_reraise();
        }
    }
    if (__exc_flag_1 && !__exc_handled_1) pb_reraise();
    pb_print_str("=== Boolean Literals ===");
    bool x = true;
    bool y = false;
    if ((x && !(y))) {
        pb_print_str("x is True and y is False");
    }
    pb_print_str("=== If/Elif/Else ===");
    int64_t n = 5;
    if ((n == 0)) {
        pb_print_str("zero");
    }
    else if ((n == 5)) {
        pb_print_str("five");
    }
    else  {
        pb_print_str("other");
    }
    pb_print_str("=== Pass Statement ===");
    if (true) {
        ;  // pass
    }
    pb_print_str("Pass block completed");
    pb_print_str("=== Is / Is Not Operators ===");
    int64_t aa = 10;
    int64_t bb = 10;
    if ((aa == bb)) {
        pb_print_str("a is b");
    }
    if ((aa != 20)) {
        pb_print_str("a is not 20");
    }
    pb_print_str("=== Augmented Assignment ===");
    int64_t m = 5;
    pb_print_int(m);
    m += 3;
    pb_print_int(m);
    m -= 2;
    pb_print_int(m);
    m *= 4;
    pb_print_int(m);
    m /= 2;
    pb_print_int(m);
    m %= 3;
    pb_print_int(m);
    double mm = 5.0;
    mm /= 2;
    pb_print_double(mm);
    pb_print_str("=== Explicit Type Conversion ===");
    int64_t i = 10;
    double f = (double)(i);
    pb_print_str((snprintf(__fbuf, 256, "i: %lld, f: %s", i, pb_format_double(f)), __fbuf));
    double f2 = 3.5;
    int64_t i2 = (int64_t)(f2);
    pb_print_str((snprintf(__fbuf, 256, "f2: %s, i2: %lld", pb_format_double(f2), i2), __fbuf));
    pb_print_str("=== Class Instantiation and Methods ===");
    struct Player __tmp_player_2;
    Player____init__(&__tmp_player_2, 110, 150);
    struct Player * player = &__tmp_player_2;
    pb_print_str((snprintf(__fbuf, 256, "player.hp: %lld", player->hp), __fbuf));
    pb_print_str("Healing player by 50...");
    Player__heal(player, 50);
    pb_print_int(player->hp);
    pb_print_str("Adding player's hp to global counter...");
    Player__add_to_counter(player);
    pb_print_str("Updated counter:");
    pb_print_int(counter);
    pb_print_str("=== Class vs Instance Variables ===");
    struct Player __tmp_player_3;
    Player____init__(&__tmp_player_3, 1234, 150);
    struct Player * player1 = &__tmp_player_3;
    struct Player __tmp_player_4;
    Player____init__(&__tmp_player_4, 5678, 150);
    struct Player * player2 = &__tmp_player_4;
    player1->score = 100;
    pb_print_str((snprintf(__fbuf, 256, "Player1 score: %lld", player1->score), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Player2 score (should be default): %lld", player2->score), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Player class species: %s", Player_species), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Species from player1 (via class attribute): %s", Player__get_species_one(player1)), __fbuf));
    player1->hp = 777;
    pb_print_str((snprintf(__fbuf, 256, "Player1.hp (instance attribute): %lld", player1->hp), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Player2.hp (instance attribute): %lld", player2->hp), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Player.hp (class attribute): %lld", Player_hp), __fbuf));
    pb_print_str("Directly setting player.hp to 999");
    player->hp = 999;
    pb_print_int(player->hp);
    pb_print_str("=== Inheritance: Mage Subclass ===");
    struct Mage __tmp_mage_5;
    Mage____init__(&__tmp_mage_5, 120);
    struct Mage * mage = &__tmp_mage_5;
    pb_print_str((snprintf(__fbuf, 256, "Mage name: %s", Mage__get_name(mage)), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Mage HP: %lld", mage->base.hp), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "Mage MP: %lld", mage->mp), __fbuf));
    pb_print_str("Mage casts a spell costing 20 mana...");
    Mage__cast_spell(mage, 20);
    pb_print_str((snprintf(__fbuf, 256, "Remaining MP: %lld", mage->mp), __fbuf));
    pb_print_str("Mage takes damage and heals...");
    mage->base.hp -= 30;
    mage->mp -= 10;
    pb_print_str((snprintf(__fbuf, 256, "HP after damage: %lld", mage->base.hp), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "MP after damage: %lld", mage->mp), __fbuf));
    Mage__heal(mage, 40);
    pb_print_str((snprintf(__fbuf, 256, "HP after healing: %lld", mage->base.hp), __fbuf));
    pb_print_str((snprintf(__fbuf, 256, "MP after healing: %lld", mage->mp), __fbuf));
    return 0;
}
