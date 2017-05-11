#!/usr/bin/env python3

"""JVC projector tool menu"""

import math
import os
import sys
import threading
import traceback
from distutils.util import strtobool

sys.path.append(os.path.dirname(__file__))

import eotf
import plot
from jvc_gamma import GammaCurve, Highlight
from jvc_command import(
    JVCCommand, CommandNack, Command, HDMIInputLevel, PictureMode, PowerState, RemoteCode,
    GammaTable, GammaCorrection)

DEBUG_MENU = False

GAMMA_HDR_DEFAULT = {
    'bmax': 100,
    'brefwhite': 25,
    'bsoftclip': {'bmin': 100,
                  'bbase': 25,
                  'scale': 0.4,
                  'hcscale': 0.5},
    'bhardclip': 4000,
    'end_slope': 0.75,
    'clip': 0,
    'clip_gamma': 1,
    'eotf': 'eotf_pq',
    'highlight': None,
    }

GAMMA_BLACK_LEVEL_DARK_TEST = {
    'table': [max(0, 50 - i) for i in range(256)]
    }

GAMMA_BLACK_LEVEL_BRIGHT_TEST = {
    'table': [max(0, 50 - i) if i < 96 else min(i * 4, 1024) for i in range(256)]
    }

GAMMA_PRESETS = [
    ('sdr bt1886', {
        'bmax': 115,
        'brefwhite': 100,
        'bsoftclip': 100,
        'end_slope': 0.98,
        'eotf': 'eotf_bt1886',
        }),
    ('hdr pq', GAMMA_HDR_DEFAULT),
    ('hdr pq 1200', {
        'bmax': 100,
        'brefwhite': 25,
        'bsoftclip': {'bmin': 100,
                      'bbase': 25,
                      'scale': 0.4,
                      'hcscale': 0.5},
        'bhardclip': 1200,
        'end_slope': 0.75,
        'clip': 0,
        'clip_gamma': 1,
        'eotf': 'eotf_pq',
        }),
    ('hdr_hlg 250 sc200', {
        'bmax': 250,
        'brefwhite': 100,
        'bsoftclip': 200,
        'bhardclip': 10000,
        'end_slope': 1,
        'eotf': 'eotf_hlg',
        }),
    ('projector black level dark test', GAMMA_BLACK_LEVEL_DARK_TEST),
    ('projector black level bright test', GAMMA_BLACK_LEVEL_BRIGHT_TEST),
    ]

def input_ask(prompt, allowed):
    """Ask for input until a valid response is given"""
    while True:
        val = input(prompt)
        if val in allowed:
            return val

def input_num(prompt, low, high, numtype=float, data=None):
    """Read a number and its range"""
    for _ in range(5):
        try:
            if data is None:
                strval = input('{} [{},{}]: '.format(prompt, low, high))
            else:
                strval = data
                data = None
            val = numtype(strval)
            strval = None
            if val < low:
                print(val, '<', low)
                continue
            if val > high:
                print(val, '>', high)
                continue
            return val
        except ValueError:
            print('Bad input', strval)

def select_menu_item(prompt, items, cmdindex=0, nameindex=1, maxsplit=0,
                     multiselect=False, cmdsep=None, data=None):
    """Select menu item(s)"""
    readinput = data is None
    if cmdsep is not None:
        multiselect = True
    i = 0
    cmddict = dict()
    for item in items:
        cmd = item[cmdindex] if cmdindex is not None else None
        if cmd is not None:
            assert cmd not in cmddict
        else:
            i += 1
            cmd = str(i)
        cmddict[cmd] = item

        if readinput:
            print('{:<10}'.format(cmd), item[nameindex])

    for _ in range(3):
        try:
            line = (input(prompt) if readinput else data).strip()
            if multiselect:
                cmds = line.split(sep=cmdsep)
            else:
                cmds = [line]

            ret = []
            for cmd in cmds:
                sel, *args = cmd.split(maxsplit=maxsplit)
                item = cmddict[sel]
                if DEBUG_MENU:
                    print('select', sel, item)
                if maxsplit:
                    cmdret = ((item, *args))
                else:
                    assert not args
                    cmdret = item
                ret.append(cmdret)
            if multiselect:
                if DEBUG_MENU:
                    print('return menu items', ret)
                return ret
            assert len(ret) == 1
            return ret[0]
        except ValueError:
            prompt = 'Bad input, try again: '
        except KeyError:
            prompt = 'No such item, try again: '
    raise KeyError

def run_menu_item(name, func, arg):
    """Run the function for a menu item and allow retry on exceptions"""
    try:
        while True:
            try:
                func(arg)
                return None
            except plot.PlotClosed:
                return None
            except Exception as err:
                print(name, 'failed', err)

                res = input_ask('Ignore (i), retry (r) or abort (a): ', {'i', 'r', 'a', 's'})
                if res == 'a':
                    return err
                if res == 'i':
                    return None
                if res == 's':
                    traceback.print_exc()
    except KeyboardInterrupt as err:
        print('Interrupted', err)
        return err

class ExceptionInThread(Exception):
    """Exception info from thread"""
    pass

class MenuThread(threading.Thread):
    """Menu Thread class"""
    def __init__(self, menu):
        threading.Thread.__init__(self)
        self.exception = None
        self.menu = menu

    def run(self):
        try:
            self.menu.run()
        except BaseException as err:
            self.exception = ExceptionInThread(err, sys.exc_info())
        finally:
            try:
                self.menu.plot.close()
            except:
                pass

class Menu():
    """Menu class"""
    def __init__(self):
        """JVC gamma table select, plot, load menu"""
        self.autoplot = 2
        self.autoplot_history = 1
        self.gamma = GammaCurve()
        self.verify = True
        self.plot = None
        self.run_plot_open = False
        self.plot_menu = False
        self.replot = False
        self.adjust_menu_on = False
        self.gammaref = []
        try:
            self.gamma.file_load()
        except FileNotFoundError:
            pass
        except Exception:
            if not strtobool(input('Failed to load gamma curve.\n'
                                   'Ignore error and continue (y/n)? ')):
                raise

        while self.run_plot_open is not None:
            plot_open = self.run_plot_open
            self.run_plot_open = None
            if plot_open:
                self.run_with_plot()
            else:
                self.run()

    def run_with_plot(self):
        """Open plot window and run menu in thread"""
        thread = MenuThread(self)
        self.plot = plot.Plot()
        try:
            thread.start()
            self.plot.run()
        finally:
            thread.join()
            self.plot = None
            if thread.exception is not None:
                raise thread.exception

    def load(self, basename):
        """Load gamma curve from file"""
        self.gamma.file_load(basename)

    def save(self, basename):
        """Save gamma curve to file"""
        self.gamma.file_save(basename)

    def itostr(self, value):
        """Convert gamma table index to input brightness"""
        try:
            p = self.gamma.itop(value)
            if p < 0:
                raise ValueError
            b = self.gamma.eotf.L(p) * self.gamma.eotf.peak
            return '{:.5g} cd/m²'.format(b)
        except:
            return ''

    def preset_gamma_menu_select(self, _):
        """Load gamma curve from build in preset"""
        menu = [(None, name, param) for name, param in GAMMA_PRESETS]
        menu.append(('q', '--abort--', {}))

        _, _, sel = select_menu_item('Select preset: ', menu, cmdindex=0, nameindex=1)
        self.gamma.conf_load(sel)

    def setup_hdr(self, _):
        """HDR setup helper"""
        try:
            with JVCCommand() as jvc:
                try:
                    model = jvc.get(Command.Model)
                    print('Found projector model:', model.name)
                except ValueError:
                    if not strtobool(input('Unknown projector model.\n'
                                           'Ignore and continue (y/n)? ')):
                        raise
                while True:
                    power_state = jvc.get(Command.Power)
                    if power_state != PowerState.LampOn:
                        print('Make sure projector is powered on and ready. Current state is:',
                              power_state.name)
                        res = input('Press enter to retry '
                                    '(or enter "on" to send power on command): ')
                        if res == 'on':
                            if jvc.get(Command.Power) == PowerState.StandBy:
                                jvc.set(Command.Power, PowerState.LampOn)
                            else:
                                print('Not in StandBy, try again')
                        continue
                    input_level = jvc.get(Command.HDMIInputLevel)
                    break
                while True:
                    print('Set "Picture Mode" to the User mode you want to program for HDR')
                    print('Set "Gamma" to "Custom 1", "Custom 2" or "Custom 3"')
                    input('Press enter when ready: ')
                    user_mode = jvc.get(Command.PictureMode)
                    gamma_table = jvc.get(Command.GammaTable)
                    if user_mode not in {PictureMode.User1, PictureMode.User2,
                                         PictureMode.User3, PictureMode.User4,
                                         PictureMode.User5, PictureMode.User6}:
                        print('Invalid "Picture Mode":', user_mode.name)
                        continue
                    if gamma_table not in {GammaTable.Custom1, GammaTable.Custom2,
                                           GammaTable.Custom3}:
                        print('Invalid "Gamma":', gamma_table.name)
                        continue
                    gamma_correction = jvc.get(Command.GammaCorrection)
                    if gamma_correction != GammaCorrection.Import:
                        print('Switching {} from {} to {}'.format(
                            gamma_table.name, gamma_correction.name, GammaCorrection.Import.name))
                        jvc.set(Command.GammaCorrection, GammaCorrection.Import)
                    print('Selected', user_mode.name, gamma_table.name, gamma_correction.name)
                    break

            self.gamma.conf_load(GAMMA_HDR_DEFAULT)
            self.gamma.set_input_level(input_level)

            self.set_source_brightness_contrast()
            self.hdr_contrast_menu()

        except CommandNack as err:
            print('Nack', err)

    def set_source_brightness_contrast(self, _=None):
        """Load a gamma curve to help adjusting brightness and contrast on a source device"""
        gamma = GammaCurve()
        gamma.set_input_level(HDMIInputLevel.Enhanced)
        gamma.bmax = 100
        gamma.brefwhite = 100
        gamma.bsoftclip = 100
        gamma.end_slope = 0
        gamma.highlight = (Highlight.BTB | Highlight.B | Highlight.NB |
                           Highlight.NW | Highlight.W | Highlight.WTW)
        gamma.eotf = eotf.eotf_gamma_2_2

        print('\nDisplay a test pattern where you can clearly identify black and white')
        input('Press enter when ready load test gamma curve: ')
        saved_input_level = None
        try:
            with JVCCommand() as jvc:
                saved_input_level = jvc.get(Command.HDMIInputLevel)
                if saved_input_level != HDMIInputLevel.Enhanced:
                    print('Changing input level from {} to Enhanced'.format(saved_input_level.name))
                    jvc.set(Command.HDMIInputLevel, HDMIInputLevel.Enhanced)
                gamma.write_jvc(jvc, verify=self.verify)
                jvc.set(Command.Contrast, 0)
                jvc.set(Command.Brightness, 0)

            print('Adjust contrast and brightness on your source so black and white turn green')
            input('Press enter when done: ')
        finally:
            if saved_input_level:
                with JVCCommand() as jvc:
                    if saved_input_level != jvc.get(Command.HDMIInputLevel):
                        print('Changing input level from Enhanced to {}'.format(
                            saved_input_level.name))
                        jvc.set(Command.HDMIInputLevel, saved_input_level)
            self.gamma.write(verify=self.verify)

    def contrast_to_brefwhite(self, contrast):
        """Calculate brefwhite (for contrast 0) value based on specified contrast setting"""
        bsc_old = self.gamma.eotf.L(0.5)
        bsc_new = self.gamma.eotf.L(0.5 + 0.5 * int(contrast) / 100)
        brefwhite = self.gamma.brefwhite * bsc_new / bsc_old
        print('Ref white brightness {} -> {} (sc {} -> {}'.format(
            self.gamma.brefwhite, brefwhite, bsc_old, bsc_new))
        self.gamma.brefwhite = brefwhite

    def hdr_contrast_menu(self, _=None, gamma_table_loaded=False):
        """Adjust brightness of reference white by using contrast control on projector"""
        print('After loading a gamma table, use the contrast control on the projector to\n'
              'increase or decrease the brightness of the picture. Large adjustments distorts\n'
              'the gamma curve, so you may have to repeat this step until you only need small\n'
              'adustments\n'
              'When done, leave the contrast at 0')
        while True:
            with JVCCommand() as jvc:
                if gamma_table_loaded:
                    contrast = jvc.get(Command.Contrast)
                    print('Contrast', contrast)
                    if contrast == 0:
                        jvc.set(Command.Remote, RemoteCode.Back)
                        break

                    self.contrast_to_brefwhite(contrast)

                print('Please wait while loading gamma table')
                try:
                    jvc.set(Command.Remote, RemoteCode.Back)
                    self.gamma.write_jvc(jvc, verify=self.verify)
                    jvc.set(Command.Contrast, 0)
                    gamma_table_loaded = True
                    jvc.set(Command.Remote, RemoteCode.PictureAdjust)
                except Exception as err:
                    print('Failed to load gamma table', err)
                    ret = input('Press enter to retry or enter "a" to abort: ')
                    if ret == 'a':
                        return
                    continue
            input('Gamma table ready. Make your adjustments and press enter when ready: ')

    def input_mode_show(self):
        """Return input mode to show in menu"""
        return 'Input Level: {} (Must match Input Signal Menu)'.format(
            self.gamma.get_input_level().name)

    def input_mode_select(self, arg):
        """Select input mode"""
        menu = [(e.name[:2].lower(), e.name, e) for e in HDMIInputLevel]
        _, _, input_level = select_menu_item('Select Input Level: ', menu, data=arg)
        self.gamma.set_input_level(input_level)

    def show_highlight(self):
        """Return highlight flags to show in menu"""
        return 'Highlight regions (current %s)' % self.gamma.highlight

    #@staticmethod
    def select_highlight(self, arg):
        """Select highlight flags"""
        menu = [
            ('c', 'Clear All', Highlight.NONE, True),
            ('a', 'Set All', Highlight.ALL, True),
            ('ta', 'Toggle All', Highlight.ALL, False),
            ('ba', 'AB: Absolute Black AB', Highlight.AB, False),
            ('bb', 'BTB: Blacker-than-black', Highlight.BTB, False),
            ('bi', 'BTBI: Blacker-than-blackin', Highlight.BTBI, False),
            ('b', 'B: Black', Highlight.B, False),
            ('bn', 'NB: Near-black', Highlight.NB, False),
            ('bf', 'F: Flat spots', Highlight.F, False),
            ('sc', 'SC: Soft-clipped', Highlight.SC, False),
            ('sf', 'SCF: Soft-clipped flat spots', Highlight.SCF, False),
            ('hc', 'HC: Hard-clipped', Highlight.HC, False),
            ('wn', 'NW: Near-white', Highlight.NW, False),
            ('wc', 'CW: Hard-clipped to white', Highlight.CW, False),
            ('w', 'W: White (sdr: ref, hdr: peak)', Highlight.W, False),
            ('ww', 'WTW: Whiter-than-white', Highlight.WTW, False),
            ('q', 'Done', None, None),
            ]
        done = bool(arg)
        while True:
            selected = select_menu_item('Toggle: ', menu, multiselect=True, data=arg)
            for _, _, sel, force in selected:
                if sel is None:
                    done = True
                    continue
                if force or self.gamma.highlight is None:
                    self.gamma.highlight = sel
                else:
                    self.gamma.highlight ^= sel
                print('Selected:', self.gamma.highlight)
            if done:
                if self.gamma.highlight is Highlight.NONE:
                    self.gamma.highlight = None
                return

    def eotf_menu_select(self, arg):
        """Select eotf if arg matches a unique entry. Build and run a select menu otherwise"""
        menu = []
        matched = None
        for entry in eotf.eotfs:
            name = entry.__name__
            menu.append((None, name, entry))
            if arg and arg in name:
                matched = entry if matched is None else set()
        if matched:
            self.gamma.eotf = matched
        else:
            _, _, self.gamma.eotf = select_menu_item('Select preset: ', menu)

    def eotf_black_menu_show(self):
        """Return black level compensation in eotf to show in menu"""
        black = getattr(self.gamma.eotf, 'Lb', None)
        if black is not None:
            black = black * self.gamma.bmax
        return 'eotf black compensation: {}'.format(black)

    def eotf_black_menu_select(self, arg):
        """Set black level compensation in eotf"""
        if not hasattr(self.gamma.eotf, 'set_black'):
            print('not available')
        else:
            black = input_num('black level (nits):', 0.0, 5.0, data=arg)
            self.gamma.eotf.set_black(black / self.gamma.bmax)

    def show_softclip(self):
        """Return softclip start value(s) to show in menu"""
        bsoftclip = self.gamma.bsoftclip
        if isinstance(bsoftclip, dict):
            paramstr = ', '.join('{!s}={!r}'.format(key, val) for (key, val) in bsoftclip.items())
        else:
            paramstr = bsoftclip
        return 'Set soft clip start: {} ({})'.format(self.gamma.get_effective_bsoftclip(), paramstr)

    def select_softclip(self, arg):
        """Set softclip start value(s)"""
        if not arg:
            arg = input('enter bsoftclip or bbase bmin scale hcscale: ')
        args = arg.split(' ')
        if len(args) == 1:
            self.gamma.bsoftclip = float(args[0])
        else:
            self.gamma.set_scaled_bsoftclip(*map(float, args))

    def autoplot_clear_enabled(self):
        """Return if plot should auto-clear"""
        return self.autoplot == 2

    def autoplot_enabled(self):
        """Return if curve should be automatically  plotted after changing parameter"""
        return self.autoplot > 0 and self.plot is not None

    def autoplot_show(self):
        """Return auto plot setting to show in menu"""
        return 'Auto plot [0|-1|<n>]: {}'.format(
            ('Off', 'On (Plot only)', 'On (Clear and Plot w/history {})'.format(
                self.autoplot_history))[self.autoplot])

    def autoplot_select(self, arg):
        """Set auto plot state"""
        try:
            autoplot = int(arg)
            if autoplot < 0:
                autoplot = 1
            elif autoplot > 0:
                self.autoplot_history = autoplot
                autoplot = 2
        except:
            autoplot = self.autoplot + 1
        autoplot = autoplot % 3
        if self.autoplot == 2 and autoplot != 2:
            self.plot.clear()
        self.autoplot = autoplot
        if self.autoplot == 2:
            self.replot = True

    zoom_presets = {
        'f': (),
        'u': (2, (0, 1)),
        'ur': (2, (1, 1)),
        'r': (2, (1, 0)),
        'dr': (2, (1, -1)),
        'd': (2, (0, -1)),
        'dl': (2, (-1, -1)),
        'l': (2, (-1, 0)),
        'ul': (2, (-1, -1)),
        'c': (2, (0, 0)),
        'o': (0.5, (0, 0)),
        }
    def plot_zoom_show(self):
        """Create zoom menu entry"""
        return 'Plot zoom [{}]'.format('|'.join(self.zoom_presets.keys()))

    def plot_zoom_select(self, arg):
        """Run zoom menu entry"""
        self.plot.zoom(*self.zoom_presets[arg])
        self.replot = True

    def gammaref_menu(self, arg):
        """Add or remove reference gamma curves plot"""
        if arg is None:
            print('Plotting {} reference tables'.format(len(self.gammaref)))
        elif arg == 'a':
            self.gammaref.append(self.gamma.get_table())
        elif arg == 'c':
            self.gammaref.clear()
        else:
            try:
                subcmd = arg[0]
                i = int(arg[1:])
                if subcmd == 'd':
                    del self.gammaref[i]
                elif subcmd == 'r':
                    self.gammaref[i] = self.gamma.get_table()
                else:
                    raise ValueError
            except Exception as err:
                print('Failed', err)

    def select_plot_menu(self, _):
        """Toggle plot menu"""
        self.plot_menu = not self.plot_menu
        if self.plot_menu and self.plot is None:
            self.run_plot_open = True
            self.replot = True

    def apply_plot_menu(self, menu):
        """Add plot menu entries to menu"""
        if not self.plot_menu:
            menu.append(('p', 'Show plot menu', self.select_plot_menu))
            return

        menu += [
            ('ph', 'Hide plot menu', self.select_plot_menu),
            ('p', 'Plot [s|f]', lambda arg: self.plot.plot(self.gamma.get_table(),
                                                           draw_speed=2 if arg is 's'
                                                           else 128 if arg is 'f' else 16)),
            ('pc', 'Clear plot', lambda arg: self.plot.clear()),
            ('pct', 'Plot clip table', lambda arg: self.plot.plot(
                [y * 1023 for y in self.gamma.cliptable], colors=['orange'])),
            ('psc', 'Plot contrast (-50 - 50)',
             lambda arg: self.plot.plot(self.gamma.get_table(), scale_x=1/(1 + int(arg) / 100))),
            ('pa', self.autoplot_show(), self.autoplot_select),
            ('pz', self.plot_zoom_show(), self.plot_zoom_select),
            ('pr', 'Plot reference curve [a|r<index>|c|d<index>]', self.gammaref_menu),
            ]

    def clear_plot_draw_grid(self):
        """Clear plot and draw grid lines"""
        unlabeled_color = 'gray97'
        vlines = [
            (self.gamma.irefblack, 'Black', 1),
            (self.gamma.ipeakwhite, 'Peak white', 2),
            (self.gamma.ihardclip, 'Hard Clip', 3),
            (self.gamma.isoftclip, 'Soft Clip', 4),
            ]
        vlines += [(round(self.gamma.ptoi((i / 4 - 16) / (235 - 16)) * 4) / 4, '', 0)
                   for i in range(0, 1023, max(1, round(4 * 16 * self.plot.scale)))]
        vlines.sort()

        hlines = [
            (self.gamma.get_effective_bmax(), '', 1),
            (self.gamma.get_effective_bblackout(), 'Black Out\n', 2),
            (self.gamma.get_effective_bsoftclip(), 'Soft Clip\n', 3),
            ]
        hlines += [(round(b, -int(math.floor(math.log10(b)))), '', 0)
                   for b in [10 ** (i / 3) for i in range(-12, 14)]]
        hlines.sort()

        lines = []
        for i, name, priority in vlines:
            if i < 0:
                continue
            line = {
                'pos': i,
                'horizontal': False,
                'label': '{}\n{:.5g}/{:.5g}/{:.5g}\n{}'.format(
                    name,
                    i, 16 + self.gamma.itop(i) * (235 - 16),
                    16 * 4 + self.gamma.itop(i) * (235 - 16) * 4,
                    self.itostr(i)),
                'priority': priority,
                }
            if not name:
                line['color'] = unlabeled_color
            lines.append(line)

        for b, name, priority in hlines:
            try:
                if b <= 0:
                    continue
                l = b / self.gamma.get_effective_bmax()
                o = (l ** (1/2.2)) * 1023
            except ValueError:
                continue

            line = {
                'pos': o,
                'horizontal': True,
                'label': '{}{:.5g} cd/m²\nvirt {:.3g} cd/m²\no: {:.4g}'.format(
                    name, self.gamma.bi_to_bo(b), b, o),
                'priority': priority,
                }
            if not name:
                line['color'] = unlabeled_color
            lines.append(line)

        self.plot.clear(lines=lines)

    def select_gamma_adjust_menu(self, _):
        """Toggle gamma curve adjustments"""
        self.adjust_menu_on = not self.adjust_menu_on

    def apply_adjust_menu(self, menu):
        """Add gamma curve adjustments to menu is enabled"""
        if not self.adjust_menu_on:
            menu += [
                ('ga', 'Adjust gamma curve', self.select_gamma_adjust_menu),
                ]
            return

        if self.gamma.get_effective_bmax() > self.gamma.get_effective_bhardclip():
            print()
            print('Warning, hard clip is set lower than the effective max brightness')
            print()

        def menu_param(cmd, gamma, name, param, low, high):
            """Create menu entry for a paramter"""
            return (cmd, '{}: {}'.format(name, getattr(gamma, param)), None, param, low, high)

        menu += [
            ('ga', 'Hide gamma curve adjust menu', self.select_gamma_adjust_menu),
            ('eo', 'eotf: {}'.format(self.gamma.eotf.__name__), self.eotf_menu_select),
        ]

        if not self.gamma.raw_gamma_table():
            menu += [
                ('il', self.input_mode_show(), self.input_mode_select),
                ('hl', self.show_highlight(), self.select_highlight),
                ('bm', 'Set max brightness: {} (Effective {})'.format(
                    self.gamma.bmax, self.gamma.get_effective_bmax()), None, 'bmax', 10.0, 10000.0),
                ('bs', 'Set brightness scale factor: {}'.format(self.gamma.get_bscale()),
                 lambda arg: self.gamma.set_bscale(float(arg))),
                menu_param('bw', self.gamma, 'Set ref white brightness', 'brefwhite', 1.0, 100.0),
                ('bbi', 'Set black brightness in: {} (Effective {})'.format(
                    self.gamma.bblackin, self.gamma.get_effective_bblack()),
                 None, 'bblackin', 0.0, 5.0),
                ('bbo', 'Set black brightness out: {} (Effective {})'.format(
                    self.gamma.bblack, self.gamma.get_effective_bblackout()),
                 None, 'bblack', 0.0, 5.0),
                ('eb', self.eotf_black_menu_show(), self.eotf_black_menu_select),
                menu_param('bh', self.gamma, 'Set hard clip', 'bhardclip', 0.1, 100000),
                ('sc', self.show_softclip(), self.select_softclip),
                menu_param('se', self.gamma, 'Set end slope', 'end_slope', 0.0, 1.0),
                menu_param('st', self.gamma, 'Set soft clip curve type', 'clip', 0, 1),
                menu_param('sg', self.gamma, 'Set soft clip gamma', 'clip_gamma', 0.0001, 10000.0),
            ]

        self.apply_plot_menu(menu)

        menu += [
            ('bwc', 'Scale ref white brightness from contrast (-50 - 50)',
             self.contrast_to_brefwhite),
            ('Pr', 'Read raw table from projector', lambda _: self.gamma.read()),
            ]

    def run(self):
        """Run menu"""
        gammahist = []

        while True:
            if self.plot and self.plot.closed:
                self.plot_menu = False
                self.run_plot_open = False
                print('Plot window closed')

            if self.run_plot_open is not None:
                return

            self.run_autoplot(gammahist)

            menu = [
                (None, 'Setup HDR', self.setup_hdr),
                (None, 'Set brightness and contrast for source',
                 self.set_source_brightness_contrast),
                (None, 'Load into projector and tune with contrast control', self.hdr_contrast_menu),
                ]

            self.apply_adjust_menu(menu)

            menu += [
                ('lp', 'Load preset gamma curve', self.preset_gamma_menu_select),
                ('lf', 'Load gamma curve from file [confname]', self.load),
                ('Pw', 'Write gamma curve to projector',
                 lambda _: self.gamma.write(verify=self.verify)),
                ('q!', 'Quit and discard changes', lambda _: None),
                ('s', 'Save save current gamma parameters [confname]', self.save),
                ('x', 'Quit and save current gamma parameters [confname]', self.save),
                ]

            for sel, *args in select_menu_item('Select operation: ', menu,
                                               cmdindex=0, nameindex=1, maxsplit=1, cmdsep=';'):
                args = iter(args)
                arg = next(args, None)
                if sel[2]:
                    if run_menu_item(sel[1], sel[2], arg) is not None:
                        break
                    if sel[0] in ('x', 'q!'):
                        return
                else:
                    numtype = float if isinstance(sel[4], float) else int
                    val = input_num(*sel[3:], numtype=numtype, data=arg)
                    if val is not None:
                        self.gamma.set(sel[3], val)
                        self.replot = True

    def run_autoplot(self, gammahist):
        """Perform Auto Plot if enabled"""
        if not self.autoplot_enabled():
            return

        while len(gammahist) > self.autoplot_history + 1:
            gammahist.pop(0)

        table = self.gamma.get_table()
        if len(gammahist) == 0 or table != gammahist[-1] or self.replot:
            self.replot = False
            if len(gammahist) == 0 or table != gammahist[-1]:
                while len(gammahist) > self.autoplot_history:
                    gammahist.pop(0)
            try:
                if self.autoplot_clear_enabled():
                    self.clear_plot_draw_grid()
                    for rtable in self.gammaref:
                        self.plot.plot(rtable, colors=['gray50'], draw_speed=1024)
                    for htable in gammahist:
                        self.plot.plot(htable, colors=['gray70'], draw_speed=1024)
                if len(gammahist) == 0 or table != gammahist[-1]:
                    gammahist.append(table)
                self.plot.plot(table, draw_speed=256)
            except plot.PlotClosed:
                pass

def main():
    """JVC Projector tools main menu"""
    while True:
        try:
            Menu()
            break
        except Exception as err:
            if isinstance(err, ExceptionInThread):
                err, exc = err.args
            else:
                exc = sys.exc_info()
            print(err)
            try:
                if strtobool(input('error occured print stack trace? ')):
                    traceback.print_exception(*exc)
            except:
                pass
            try:
                if not strtobool(input('restart? ')):
                    break
            except:
                break

if __name__ == "__main__":
    main()
