#!/usr/bin/env python
# -*- coding: utf-8 -*-
# copy from https://github.com/aneasystone/selenium-test/blob/master/12-slider-captcha.py
# thanks to aneasystone for his great work
import math
from typing import List, Tuple

import numpy as np


# https://github.com/gdsmith/jquery.easing/blob/master/jquery.easing.js
def ease_in_quad(x):
    return x * x


def ease_out_quad(x):
    return 1 - (1 - x) * (1 - x)


def ease_out_quart(x):
    return 1 - pow(1 - x, 4)


def ease_out_expo(x):
    if x == 1:
        return 1
    else:
        return 1 - pow(2, -10 * x)


def ease_out_bounce(x):
    n1 = 7.5625
    d1 = 2.75
    if x < 1 / d1:
        return n1 * x * x
    elif x < 2 / d1:
        x -= 1.5 / d1
        return n1 * x * x + 0.75
    elif x < 2.5 / d1:
        x -= 2.25 / d1
        return n1 * x * x + 0.9375
    else:
        x -= 2.625 / d1
        return n1 * x * x + 0.984375


def ease_out_elastic(x):
    if x == 0:
        return 0
    elif x == 1:
        return 1
    else:
        c4 = (2 * math.pi) / 3
        return pow(2, -10 * x) * math.sin((x * 10 - 0.75) * c4) + 1


def get_tracks(distance, seconds, ease_func) -> Tuple[List[int], List[int]]:
    tracks = [0]
    offsets = [0]
    for t in np.arange(0.0, seconds, 0.1):
        ease = globals()[ease_func]
        offset = round(ease(t / seconds) * distance)
        tracks.append(offset - offsets[-1])
        offsets.append(offset)
    return offsets, tracks


if __name__ == '__main__':
    o, tl = get_tracks(129, 3, "ease_out_expo")
    print(tl)
