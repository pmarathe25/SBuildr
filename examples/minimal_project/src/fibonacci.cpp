#include "fibonacci.hpp"
#ifdef S_DEBUG
#include <iostream>
#endif

int fibonacci(int n) {
    int prev2 = 0;
    int prev1 = 1;
    int acc = (n == 1) ? 1 : 0;
    for (int i = 2; i <= n; ++i) {
        prev2 = prev1;
        acc += prev1;
        prev1 = acc;
#ifdef S_DEBUG
        std::cout << "Fib[" << i << "] = " << acc << ", prev2 = " << prev2 << ", prev1 = " << prev1 << std::endl;
#endif
    }
    return acc;
}
