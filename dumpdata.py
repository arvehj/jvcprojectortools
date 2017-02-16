#!/usr/bin/env python3

"""Dump formatted data with limited number of items per line"""

import itertools

def dumpdata(prefix, formatstr, data, limit=32):
    """Dump formatted data with limited number of items per line"""
    i = iter(data)
    line = list(itertools.islice(i, limit))
    if not line:
        print(prefix, 'No data')
    while line:
        print(prefix, ' '.join(formatstr.format(c) for c in line))
        line = list(itertools.islice(i, limit))
        prefix = ' ' * len(prefix)

if __name__ == "__main__":
    dumpdata('test 1-50:', '{:2d}', range(50), limit=10)
    dumpdata('test no data:', '{:2d}', range(0), limit=10)
