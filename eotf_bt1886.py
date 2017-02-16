#!/usr/bin/env python3

"""ITU-R BT.1886 EOTF"""

import math

peak = 100

gamma = 2.4

Lw = 1
#Lb = Lw/50000
#Lb = Lw/2600000
Lb = Lw/20000
a = (Lw ** (1/gamma) - Lb ** (1/gamma)) ** gamma
b = Lb ** (1/gamma) / (Lw ** (1/gamma) - Lb ** (1 /gamma))

Vc = 0.35
a1 = 2.6
a2 = 3.0
k = Lw / (1 + b) ** a1

def L1(V):
    """ITU-R BT.1886 EOTF"""
    if V < Vc:
        return k * (Vc + b) ** (a1 - a2) * (V + b) ** a2
    else:
        return k * (V + b) ** a1

def L(V):
    """ITU-R BT.1886 EOTF"""
    if V <= 0:
        return 0
    return a * max(V + b, 0) ** gamma

def main():
    """ITU-R BT.1886 test"""
    print('a', a)
    print('b', b)
    for i in range(11):
        i = i / 10
        print('L * 100', i, L(i) * 100, L2(i) * 100, i ** 2.4 * 100)

if __name__ == "__main__":
    main()
