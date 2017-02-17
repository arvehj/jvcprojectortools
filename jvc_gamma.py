#!/usr/bin/env python3

"""JVC projector low level command module"""

import math
import traceback
import turtle
from distutils.util import strtobool

import dumpdata
import eotf
from jvc_command import JVCCommand, CommandNack, Command, PictureMode, GammaTable, GammaCorrection

peak_white_normal = 255 # normal/enhanced
peak_white_super_white = (235 - 16) * (255 / (255 - 16)) # super white
white = peak_white_super_white

def oscale(l):
    oscale1 = 1023
    out_gamma = 1/2.2
    oscale = oscale1
    if l < 0:
        o = 0
    else:
        o = (l ** out_gamma) * oscale
    oi = int(round(o, 0))
    if oi >= oscale1:
        oi = oscale1
    return oi

def get_gamma(bmax=200, bsoftclip=150, bhardclip=10000, end_slope=0.99, clip=0, clip_gamma=1, eotf=eotf.eotf_pq, debug=0):
    global white
    lscale = eotf.peak / bmax
    lsoftclip = bsoftclip / bmax
    lhardclip = bhardclip / bmax
    end_slope = lsoftclip ** (1 / clip_gamma) + (1 - lsoftclip ** (1 / clip_gamma)) * end_slope

    if clip == 1:
        def B(t, P0, P1, Pignore, P2):
            return (1-t)**2*P0 + 2*(1-t)*t*P1 + t**2*P2
    else:
        def B(t, P0, P1, P2, P3):
            return (1-t)**3*P0 + 3*(1-t)**2*t*P1 + 3*(1-t)*t**2*P2+t**3*P3

    def clip(p, l, clip_p, clip_l, clip_gain, ppeak):
        global white
        if (l < lsoftclip):
            return l
        clip_o = clip_l ** (1 / clip_gamma)
        dp = p - clip_p
        t = dp / (255 / white - clip_p)
        Btp = 0
        tl = 0
        th = 1
        sat_o = end_slope
        sat_p = clip_p + (sat_o - clip_o) / clip_gain
        if sat_p > ppeak:
            sat_p = ppeak
            sat_o = (sat_p - clip_p) * clip_gain + clip_o

        while th - tl > 0.00001:
            Btp = B(t, clip_p, sat_p, sat_p, ppeak)
            if Btp < p:
                tl = t
            else:
                th = t
            t = tl + (th - tl) / 2
        Btl = B(t, clip_o, sat_o, sat_o, 1)
        if debug > 2:
            print('{:3.0f}: p {:7.4f}, Btp {:7.4f}, t {:7.4f}, Bt {:7.4f}, clip_p {:7.4f}, sat_p {:7.4f}, clip_l {:7.4f}, clip_gain {:7.4f}'.format(
              p*white, p, Btp, t, Btl, clip_p, sat_p, clip_l, clip_gain))
        return Btl ** clip_gamma

    go = []
    points = [p / white for p in range(256)]
    clip_p = None
    clip_l = None
    clip_gain = None
    hardclip_p = 255 / white
    last_p = None
    for p in points:
        l = eotf.L(p) * lscale
        if l >= lsoftclip and clip_p is None and last_p is not None:
            clip_p = last_p
            clip_l = last_l
            clip_gain = (l ** (1 / clip_gamma) - last_l ** (1 / clip_gamma)) / (p - last_p)
        if l >= lhardclip:
            hardclip_p = p
            break;
        last_l = l
        last_p = p

    lpeak = l = eotf.L(points[-1]) * lscale

    if debug > 0:
        print('lscale {:7.4f}, lsoftclip {:7.4f}, end_slope {:7.4f}, lpeak {:7.4f}'.format(
              lscale, lsoftclip, end_slope, lpeak))
        if clip_p:
            print('clip_p {:7.4f} {:7.1f}, clip_l {:7.4f}'.format(
                  clip_p, clip_p * white, clip_l))

    for p in points:
        l = eotf.L(p) * lscale
        lc = clip(p, l, clip_p, clip_l, clip_gain, hardclip_p)
        oi = oscale(lc)
        if debug > 3:
            print('{:3.0f}: {:4d} {:7.1f} {:7.4f} {:7.4f} {:7.4f} {:7.4f}'.format(
                   p*white,   oi, oscale(l), lc * bmax, l * bmax, clip_p, clip_l))
        go.append(oi)
    return go

def load_gamma(*newgamma):
    if len(newgamma) == 1:
        newgamma = newgamma * 3
    assert len(newgamma) == 3
    with JVCCommand(print_all=False) as jvc:
        try:
            print('Picture mode:', jvc.get_picture_mode())
            old_gamma_table = jvc.get_gamma_table()
            print('Gamma Table:', old_gamma_table)
            assert old_gamma_table in {GammaTable.Custom1,
                                       GammaTable.Custom2,
                                       GammaTable.Custom3}, \
                'Selected gamma table, %s, is not a custom gamma table' % old_gamma_table
            gamma_correction = jvc.get_gamma_correction()
            assert gamma_correction is GammaCorrection.Import, \
                'Correction value for %s is not set to import, %s' % (old_gamma_table, gamma_correction)

            jvc.set_gamma(Command.gammared, newgamma[0])
            jvc.set_gamma(Command.gammagreen, newgamma[1])
            jvc.set_gamma(Command.gammablue, newgamma[2])
        except CommandNack as err:
            print('Nack', err)

def plot(*gamma, colors=['red', 'green', 'blue']):
    """Plot gamma table"""
    if all(x==gamma[0] for x in gamma):
        gamma = gamma[:1]
    turtle.setworldcoordinates(0, 0, 256, 1024)
    turtle.delay(0)
    turtle.color('black')
    for color in range(len(gamma)):
        turtle.setposition(0, 0)
        if len(gamma) == len(colors):
            turtle.color(colors[color])
        turtle.pendown()
        for x, y in zip(range(256), gamma[color]):
            turtle.setposition(x, y)
        turtle.setposition(256, 1024)
        turtle.penup()

def test_gamma_func():
    """JVC gamma test"""
    for e in eotf.eotfs:
        print(e)
        g = [get_gamma(p, eotf=e) for p in (100,200,400)]
        plot(*g)

    plot(get_gamma(50, 1), get_gamma(50),
         get_gamma(100, 1), get_gamma(100),
         get_gamma(200, 1), get_gamma(200),
         get_gamma(400, 1), get_gamma(400),
         get_gamma(800, 1), get_gamma(800),
         get_gamma(1600, 1), get_gamma(1600),
         get_gamma(4000, 1), get_gamma(4000),
         get_gamma(10000, 1),
         colors=['#cccccc', '#666666',
                 '#cccccc', '#888888',
                 '#cccccc', '#666666',
                 '#cccccc', '#888888',
                 '#cccccc', '#666666',
                 '#cccccc', '#888888',
                 '#cccccc', '#666666',
                 '#cccccc'])

def test_read_gamma():
    """JVC gamma test"""
    gamma_tables = []
    with JVCCommand(print_all=False) as jvc:
        old_picture_mode = jvc.get_picture_mode()
        print('Old Picture mode:', old_picture_mode)
        try:
            jvc.set_picture_mode(PictureMode.User6)
            print('New Picture mode:', jvc.get_picture_mode())
            old_gamma_table = jvc.get_gamma_table()
            print('Gamma Table:', old_gamma_table)
            assert old_gamma_table in {GammaTable.Custom1,
                                       GammaTable.Custom2,
                                       GammaTable.Custom3}
            gamma_correction = jvc.get_gamma_correction()
            assert gamma_correction is GammaCorrection.Import

            try:
                for gamma_table in [GammaTable.Custom1,
                                    GammaTable.Custom2,
                                    GammaTable.Custom3]:
                    jvc.set_gamma_table(gamma_table)
                    gamma_correction = jvc.get_gamma_correction()
                    assert gamma_correction is GammaCorrection.Import
                    gamma_red = jvc.get_gamma(Command.gammared)
                    gamma_green = jvc.get_gamma(Command.gammagreen)
                    gamma_blue = jvc.get_gamma(Command.gammablue)
                    gamma_tables.append((gamma_red, gamma_green, gamma_blue))
                    plot(gamma_red, gamma_green, gamma_blue)
            finally:
                jvc.set_gamma_table(old_gamma_table)
        except CommandNack as err:
            print('Nack', err)
        finally:
            jvc.set_picture_mode(old_picture_mode)
            print('Restored Picture mode:', jvc.get_picture_mode())
    return gamma_tables

def gamma_menu():
    """JVC gamma table select, plot, load menu"""
    global white
    while True:
        tables = [
            ('Done', None, 0),
            ('toggle white (current %s)' % ('normal' if white == peak_white_normal else 'super white'), None, 1),
            ('bt1886', get_gamma(100 if white == peak_white_normal else 115, 100, end_slope=.98, eotf=eotf.eotf_bt1886)),
            ('hdr_pq 250 sc200', get_gamma(250, 200, end_slope=1, eotf=eotf.eotf_pq)),
            ('hdr_pq 250 sc150', get_gamma(250, 150, end_slope=1, eotf=eotf.eotf_pq)),
            ('hdr_pq 500 sc300', get_gamma(500, 300, end_slope=1, eotf=eotf.eotf_pq)),
            ('hdr_pq 1000 sc600', get_gamma(1000, 600, end_slope=1, eotf=eotf.eotf_pq)),
            ('hdr_hlg 250 sc200', get_gamma(250, 200, end_slope=1, eotf=eotf.eotf_hlg)),
            ('custom hdr_pq', None, 2),
            ]

        for i,table in enumerate(tables):
            print(i, table[0])
        i = int(input('Select gamma table: '))
        table = tables[i]
        if not table[1]:
            if table[2] == 0:
                break
            if table[2] == 1:
                if white == peak_white_normal:
                    white = peak_white_super_white
                else:
                    white = peak_white_normal
                continue
            table = ( '', get_gamma(bmax=float(input('max brightness: ')),
                                    bsoftclip=float(input('soft clip start brightness: ')),
                                    bhardclip=float(input('hard clip brightness: ')),
                                    end_slope=float(input('clip end slope [0.0-1.0]: ')),
                                    clip=int(input('soft clip method [0,1]: ')),
                                    clip_gamma=float(input('soft clip gamma (e.g. 1): ')),
                                    eotf=eotf.eotf_pq))

        if strtobool(input('Plot ' + table[0] + '? ')):
            plot(table[1])
        if strtobool(input('Load ' + table[0] + '? ')):
            load_gamma(table[1])

def main():
    """JVC gamma test"""
    while True:
        try:
            gamma_menu()
            break
        except Exception as err:
            print(err)
            try:
                if strtobool(input('error occured print stack trace? ')):
                    traceback.print_exc()
            except:
                pass
            try:
                if not strtobool(input('restart? ')):
                    break
            except:
                break
    #test_gamma_func()
    #test_read_gamma()

if __name__ == "__main__":
    main()
