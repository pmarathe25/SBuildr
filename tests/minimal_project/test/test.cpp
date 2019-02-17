// External - build system shouldn't care about these.
#include <iostream>
// Internal dependencies
#include "fibonacci.hpp"
#include "factorial.hpp"

int main() {
    std::cout << "5! is " << factorial(5) << '\n';
    std::cout << "The 1st element of the Fibonacci sequence is " << fibonacci(0) << '\n';
    std::cout << "The 2nd element of the Fibonacci sequence is " << fibonacci(1) << '\n';
    return 0;
}
