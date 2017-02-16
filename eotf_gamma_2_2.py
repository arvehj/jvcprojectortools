#!/usr/bin/env python3

"""Gamma 2.2 EOTF"""

import math

peak = 100

def L(V):
    """Gamma 2.2"""
    return V ** 2.2
