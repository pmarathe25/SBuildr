// This file uses libmath.so from minimal_project
#include "doubleDep.hpp"

void reallyDoNothing() {
    doNothing(); // This comes from the single_dependency project
}
