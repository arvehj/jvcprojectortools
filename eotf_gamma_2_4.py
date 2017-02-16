#!/usr/bin/env python3

"""Gamma 2.4 EOTF"""

import math

peak = 100

def L(V):
    """Gamma 2.4"""
    return V ** 2.4
