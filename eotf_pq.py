#!/usr/bin/env python3

"""SMPTE ST 2084 EOTF"""

peak = 10000

m1 = 2610 / 4096 / 4
m2 = 2523 / 4096 * 128
c1 = 3424 / 4096
c2 = 2413 / 4096 * 32
c3 = 2392 / 4096 * 32

def L(N):
    """SMPTE ST 2084 EOTF"""
    if N == 0:
        return 0

    N_1_m2 = N ** (1/m2)
    return ((N_1_m2 - c1) / (c2 - c3 * N_1_m2)) ** (1 / m1)

def main():
    """SMPTE ST 2084 EOTF test"""
    print('m1', m1)
    print('m2', m2)
    print('c1', c1)
    print('c2', c2)
    print('c3', c3)
    for i in range(11):
        i = i / 10
        print('L * 10000', i, L(i) * 10000)

if __name__ == "__main__":
    main()
