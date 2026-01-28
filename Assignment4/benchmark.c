#include <stdio.h>
#include <stdint.h>

int main() {
    volatile int sum = 0;
    for (int i = 0; i < 1000; i++) {
        if (i & 1) sum += i;     // branch + integer
        else      sum -= i;
    }
    printf("%d\n", sum);
    return 0;
}
