#!/usr/bin/env python3

"""Hybrid Log Gamma EOTF"""

import math

peak = 1000

a = 0.17883277
b = 0.02372241
c = 1.00429347

Lw = 1000

gamma = 1.2 + 0.42 * math.log10(Lw / 1000)

def L(N):
    """HLG[0:1] EOTF"""

    if N <= 1 / 2:
        E = N ** 2 / 3
    else:
        E = math.exp((N - c) / a) + b
    
    return E**(gamma-1)*E

def main():
    """Hybrid Log Gamma test"""
    for i in range(11):
        i = i / 10
        print('L * 1000', i, L(i) * 1000)

if __name__ == "__main__":
    main()
