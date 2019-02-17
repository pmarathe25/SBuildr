#include "factorial.hpp"

int factorial(int n) {
    int acc = 1;
    for (int i = 1; i <= n; ++i) {
        acc *= i;
    }
    return acc;
}
