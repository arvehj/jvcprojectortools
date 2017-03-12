#!/usr/bin/env python3

"""JVC projector low level command module"""

import json
import enum
import math
from distutils.util import strtobool

import dumpdata
import eotf
from jvc_command import JVCCommand, Command, GammaTable, GammaCorrection, HDMIInputLevel

HDMI_INPUT_LEVEL_MAP = {
    HDMIInputLevel.Standard: (0, 255),
    HDMIInputLevel.Enhanced: (16, 235),
    HDMIInputLevel.SuperWhite: (0, (235 - 16) * (255 / (255 - 16))),
    }
HDMI_INPUT_LEVEL_RMAP = {ibw: il for il, ibw in HDMI_INPUT_LEVEL_MAP.items()}
HDMI_INPUT_LEVEL_MAP[HDMIInputLevel.Auto] = HDMI_INPUT_LEVEL_MAP[HDMIInputLevel.Standard]

class Highlight(enum.Flag):
    """Highlight flags"""
    NONE = 0
    AB = enum.auto()
    BTB = enum.auto()
    B = enum.auto()
    NB = enum.auto()
    ALLB = AB | BTB | B | NB

    F = enum.auto()
    SC = enum.auto()
    SCF = enum.auto()
    HC = enum.auto()

    NW = enum.auto()
    CW = enum.auto()
    W = enum.auto()
    WTW = enum.auto()
    ALLW = NW | CW | W | WTW

    ALL = ALLB | F | SC | SCF | HC | ALLW

class EOTFRaw:
    """Dummy eotf for raw gamma tables"""
    peak = 100

def basename_to_conf_file_name(basename):
    """Add prefix and suffix to filename"""
    return 'jvc_gamma_{}.conf'.format(basename)

def oscale(l):
    """Convert from 0.0-1.0 in linear gamma to gamma table format (0-1023 gamma 2.2)"""
    omax = 1023
    out_gamma = 1/2.2
    if l < 0:
        o = 0
    else:
        o = (l ** out_gamma) * omax
    oi = int(round(o, 0))
    if oi >= omax:
        oi = omax
    return oi

def write_gamma_curve(jvc, colorcmd, table, verify, retry=1):
    """Write gamma curve for a single color to projector"""
    while True:
        try:
            jvc.set(colorcmd, table)
            if verify:
                if jvc.get(colorcmd) != table:
                    raise Exception('Verify failed', colorcmd)
            break
        except Exception as err:
            print('Failed to send {}, {}'.format(colorcmd.name, err))
            if not retry:
                raise
            retry -= 1
            print('Retry')

class GammaCurve():
    """Gamma curve generation class"""

    def __init__(self):
        self.irefblack, self.ipeakwhite = HDMI_INPUT_LEVEL_MAP[HDMIInputLevel.Standard]
        self.bblack = 0.0
        self.bblackin = 0.0
        self.brefwhite = 100.0
        self.bmax = 100
        self.bsoftclip = None
        self.bhardclip = None
        self.end_slope = 0.75
        self.clip = 0
        self.clip_gamma = 1.0
        self.eotf = eotf.eotf_gamma_2_2
        self.highlight = None
        self.debug = 0
        self.isoftclip = None
        self.ihardclip = None
        self.table = None
        self.cliptable = None

    def raw_gamma_table(self):
        """Return True is gamma table is not generated"""
        return self.eotf is EOTFRaw

    def conf_load(self, conf):
        """Load configuration from dict"""
        conf = conf.copy()
        eotfname = conf.get('eotf')
        table = conf.get('table')
        highlight = conf.get('highlight')

        for eotfentry in eotf.eotfs:
            if eotfname == eotfentry.__name__:
                conf['eotf'] = eotfentry
                break
        else:
            if eotfname:
                print('not found eotf', eotfname)
            if table:
                conf['eotf'] = EOTFRaw
            else:
                conf.pop('eotf', None)

        if highlight:
            _, value = highlight.split('.')
            obj = Highlight.NONE
            for flag in value.split('|'):
                obj |= Highlight[flag]
            conf['highlight'] = obj

        for key, value in conf.items():
            if hasattr(self, key):
                if self.debug:
                    print('Import', key, value)
                setattr(self, key, value)
            else:
                print('Ignore unknown paramter', key, value)

        if not self.raw_gamma_table():
            self.generate_table()
            if table is not None and table != self.table:
                if strtobool(input('Imported table does not match generated table\n'
                                   'Use imported raw table instead (y/n)? ')):
                    self.set_raw_table(table)

    def file_load(self, basename=None):
        """Load configuration from file"""
        if not basename:
            basename = 'active'
        conf_file = basename_to_conf_file_name(basename)
        with open(conf_file, 'r') as file:
            conf = json.load(file)
            self.conf_load(conf)

    def file_save(self, basename=None, save_all_params=False):
        """Save configuration to file"""
        if not basename:
            basename = 'active'
            save_all_params = True
        conf_file = basename_to_conf_file_name(basename)
        raw = self.raw_gamma_table()

        if not raw or save_all_params:
            conf = self.__dict__.copy()
            if raw:
                del conf['eotf']
            else:
                conf['eotf'] = self.eotf.__name__
            if conf['highlight'] is not None:
                conf['highlight'] = str(conf['highlight'])
        else:
            conf = dict()
            conf['table'] = self.table

        with open(conf_file, 'w') as file:
            json.dump(conf, file, indent=2)
        print('Saved gamma data to', conf_file)

    def set(self, param, val):
        """Set parameter and regenerate gamma table"""
        assert hasattr(self, param), 'Unknown gamma curve parameter {}'.format(param)
        setattr(self, param, val)
        self.generate_table()

    def set_input_level(self, input_level):
        """Set irefblack and ipeakwhite from hdmi input level and regenerate gamma table"""
        self.irefblack, self.ipeakwhite = HDMI_INPUT_LEVEL_MAP[input_level]
        self.generate_table()

    def get_input_level(self):
        """Get hdmi inputlevel from irefblack and ipeakwhite"""
        return HDMI_INPUT_LEVEL_RMAP[self.irefblack, self.ipeakwhite]

    def get_bscale(self):
        """Return brigthness scale factor"""
        return 100 / self.brefwhite

    def bo_to_bi(self, bo):
        """Convert from output/measured brightness to input/virtual brightness"""
        return bo * self.get_bscale()

    def bi_to_bo(self, bi):
        """Convert from input/virtual brightness to output/measured brightness"""
        return bi / self.get_bscale()

    def get_effective_bmax(self):
        """Compute virtual bmax from absolute bmax and brefwhite"""
        return self.bo_to_bi(self.bmax)

    def get_effective_bblackout(self):
        """Compute virtual bblack out from absolute bblack and brefwhite"""
        return self.bo_to_bi(self.bblack)

    def get_effective_bblack(self):
        """Compute virtual bblack from absolute bblack and brefwhite"""
        return self.get_effective_bblackout() - self.bblackin

    def set_scaled_bsoftclip(self, bbase, bmin, scale, hcscale=math.inf):
        """Set paramters scale bsoftclip based on bmax"""
        self.bsoftclip = {'bbase': bbase,
                          'bmin': bmin,
                          'scale': scale,
                          'hcscale': hcscale}

    def get_effective_bhardclip(self):
        """Return bhardclip or infinite is it is not set"""
        return math.inf if self.bhardclip is None else self.bhardclip

    def get_effective_bsoftclip(self):
        """Return bsoftclip or compute it from paramters and effective bmax"""
        bsoftclip = self.bsoftclip
        if bsoftclip is None:
            return math.inf
        if isinstance(bsoftclip, dict):
            bmax = self.get_effective_bmax()
            bhardclip = self.get_effective_bhardclip()
            bmin = bsoftclip.get('bmin', 0)
            base = bsoftclip.get('bbase', 0)
            scale = bsoftclip.get('scale', 0)
            hcscale = bsoftclip.get('hcscale', math.inf)
            bsoftclip = max(bmin,
                            base + (bmax - base) * scale,
                            max(0, bmax - (bhardclip - bmax) * hcscale))
        return bsoftclip

    def itop(self, i):
        """Convert gamma table index to EOTF input value"""
        if i is None:
            return None
        return (i - self.irefblack) / (self.ipeakwhite - self.irefblack)

    def ptoi(self, p):
        """Convert EOTF input value to gamma table index"""
        if p is None:
            return None
        return self.irefblack + p * (self.ipeakwhite - self.irefblack)

    def generate_table(self):
        """Generate gamma table"""
        bblack = self.get_effective_bblack()
        bmax = self.get_effective_bmax()
        bsoftclip = self.get_effective_bsoftclip()
        bhardclip = self.bhardclip
        end_slope = self.end_slope
        clip_gamma = self.clip_gamma
        eotf = self.eotf
        highlight = self.highlight
        debug = self.debug

        lblack = bblack / bmax
        lscale = eotf.peak / bmax * (1 - lblack)
        lsoftclip = bsoftclip / bmax
        lhardclip = math.inf if bhardclip is None else bhardclip / bmax
        if lsoftclip > lhardclip:
            lsoftclip = math.inf
        end_slope = lsoftclip ** (1 / clip_gamma) + (1 - lsoftclip ** (1 / clip_gamma)) * end_slope

        def ptol(p):
            """Apply EOTF and add black offset"""
            return eotf.L(p) * lscale + lblack if p > 0 else 0

        if self.clip == 1:
            def B(t, P0, P1, _, P2):
                """Quadratic Bézier curve func accepting Cubic Bézier curve args (by ignoring P2)"""
                return (1-t)**2*P0 + 2*(1-t)*t*P1 + t**2*P2
        else:
            def B(t, P0, P1, P2, P3):
                """Cubic Bézier curve func"""
                return (1-t)**3*P0 + 3*(1-t)**2*t*P1 + 3*(1-t)*t**2*P2+t**3*P3

        def clip(p, l, clip_p, clip_l, clip_gain, ppeak):
            """Apply soft clip curve to a single point"""
            if l < lsoftclip or clip_l is None:
                return l
            clip_o = clip_l ** (1 / clip_gamma)
            dp = p - clip_p
            t = dp / (self.itop(255) - clip_p)
            Btp = 0
            tl = 0
            th = 1
            sat_o = end_slope
            sat_p = clip_p + (sat_o - clip_o) / clip_gain
            peak_o = 1
            if clip_p + (1 - clip_o) / clip_gain > ppeak:
                sat_p = ppeak
                sat_o = (sat_p - clip_p) * clip_gain + clip_o
                peak_o = sat_o

            while th - tl > 0.00001:
                Btp = B(t, clip_p, sat_p, sat_p, ppeak)
                if Btp < p:
                    tl = t
                else:
                    th = t
                t = tl + (th - tl) / 2
            Btl = B(t, clip_o, sat_o, sat_o, peak_o)
            if debug > 2:
                print('{:3.0f}: p {:7.4f}, Btp {:7.4f}, t {:7.4f}, '
                      'Bt {:7.4f}, clip_p {:7.4f}, sat_p {:7.4f}, '
                      'clip_l {:7.4f}, clip_gain {:7.4f}'.format(
                          self.ptoi(p), p, Btp, t, Btl, clip_p, sat_p, clip_l, clip_gain))
            return Btl ** clip_gamma

        points = list(map(self.itop, range(256)))
        clip_p = math.inf
        clip_l = math.inf
        clip_gain = None
        hardclip_p = self.itop(256) #??
        last_p = None
        for p in points:
            l = ptol(p)
            if l >= lsoftclip and clip_p is math.inf and last_p is not None and l > last_l:
                clip_p = last_p
                clip_l = last_l
                clip_gain = (l ** (1 / clip_gamma) - last_l ** (1 / clip_gamma)) / (p - last_p)
            if l >= lhardclip:
                hardclip_p = p
                break
            last_l = l
            last_p = p

        lpeak = l = eotf.L(points[-1]) * lscale

        if debug > 0:
            print('lscale {:7.4f}, lsoftclip {:7.4f}, end_slope {:7.4f}, lpeak {:7.4f}'.format(
                lscale, lsoftclip, end_slope, lpeak))
            if clip_p:
                print('clip_p {:7.4f} {:7.1f}, clip_l {:7.4f}'.format(
                    clip_p, self.ptoi(clip_p), clip_l))

        go = []
        cliptable = []
        for p in points:
            l = ptol(p)
            lc = min(clip(p, l, clip_p, clip_l, clip_gain, hardclip_p), lhardclip)
            cliptable.append(lc / l if l else 1 if lc <= 0 else 0)
            oi = oscale(lc)
            if debug > 3:
                print('{:3.0f}: {:4d} {:7.1f} {:7.4f} {:7.4f} {:7.4f} {:7.4f}'.format(
                    self.ptoi(p), oi, oscale(l), lc * bmax, l * bmax, clip_p, clip_l))
            go.append(oi)

        self.isoftclip = self.ptoi(clip_p)
        self.ihardclip = self.ptoi(hardclip_p)
        self.cliptable = cliptable

        if not highlight:
            self.table = go
            return

        gorgb = [[], [], []]
        lastgop = None
        for gi, gop in enumerate(go):
            if gi == self.irefblack and Highlight.B in highlight:
                rgb = [0, 255, 0] # show black as dark green
            elif gi == 0 and Highlight.AB in highlight:
                rgb = [255, 0, 0] # absolute black as dark red
            elif gi < self.irefblack and Highlight.BTB in highlight:
                rgb = [255, 127, 0] # blacker-than-black as dark orange
            elif round(self.ipeakwhite) == gi and Highlight.W in highlight:
                rgb = [0, 1023, 0] # show peak/ref white as green
            elif gi > self.ipeakwhite and Highlight.WTW in highlight:
                rgb = [gop, 0, 0] # show whiter-than-white as red
            elif points[gi] > hardclip_p and Highlight.HC in highlight:
                rgb = [gop, round(gop/8), 0] # show hard clipped white as red-red-orange
            elif gop == 1023 and Highlight.CW in highlight:
                rgb = [gop, round(gop/4), 0] # show clipped white as red-orange
            elif points[gi] > clip_p and gop == lastgop and Highlight.SCF in highlight:
                rgb = [gop, round(gop / 2), 0] # show flat soft clip region as orange
            elif points[gi] > clip_p and Highlight.SC in highlight:
                rgb = [gop, round(gop*0.75), 0] # show steeper soft clip region as yellow
            elif gop == lastgop and Highlight.F in highlight:
                rgb = [255, 127, gop] # show flat spot as dark orange
            elif gi < self.irefblack + 16 and Highlight.NB in highlight:
                rgb = [255 + gop, 255 + gop, gop] # show near black as dark yellow (brown)
            elif gi > self.ipeakwhite - 16 and Highlight.NW in highlight:
                rgb = [gop, gop, 0] # show near-white as yellow
            else:
                rgb = [gop, gop, gop]
            for i, goc in enumerate(gorgb):
                goc.append(rgb[i])
            lastgop = gop

        self.table = gorgb
        return

    def set_raw_table(self, table):
        """Use raw gamma table instead of generated table"""
        self.eotf = EOTFRaw
        self.table = table

    def get_table(self):
        """Generate and return gamma table"""
        if not self.raw_gamma_table():
            self.generate_table()
        return self.table

    def write_jvc(self, jvc, verify=False):
        """Write gamma table to projector"""
        newgamma = self.get_table()
        if len(newgamma) != 3:
            newgamma = [newgamma, newgamma, newgamma]

        print('Picture mode:', jvc.get(Command.PictureMode).name)
        old_gamma_table = jvc.get(Command.GammaTable)
        print('Gamma Table:', old_gamma_table.name)
        assert old_gamma_table in {GammaTable.Custom1,
                                   GammaTable.Custom2,
                                   GammaTable.Custom3}, \
            'Selected gamma table, %s, is not a custom gamma table' % old_gamma_table.name
        gamma_correction = jvc.get(Command.GammaCorrection)
        assert gamma_correction is GammaCorrection.Import, \
            'Correction value for %s is not set to import, %s' % (
                old_gamma_table.name, gamma_correction.name)

        for colorcmd, table in zip([Command.PMGammaRed, Command.PMGammaGreen, Command.PMGammaBlue],
                                   newgamma):
            write_gamma_curve(jvc=jvc, colorcmd=colorcmd, table=table, verify=verify)

        self.file_save(basename='written-{}'.format(old_gamma_table.name), save_all_params=False)

    def write(self, verify=False):
        """Connect to projector and write gamma table"""
        with JVCCommand() as jvc:
            self.write_jvc(jvc, verify=verify)

    def read_jvc(self, jvc):
        """Read gamma table from projector"""
        gamma_correction = jvc.get(Command.GammaCorrection)
        assert gamma_correction is GammaCorrection.Import, \
               'Gamma correction must be set to Import not {}'.format(gamma_correction)
        gamma_red = jvc.get(Command.GammaRed)
        gamma_green = jvc.get(Command.GammaGreen)
        gamma_blue = jvc.get(Command.GammaBlue)
        if gamma_red == gamma_green == gamma_blue:
            self.set_raw_table(gamma_red)
        self.set_raw_table((gamma_red, gamma_green, gamma_blue))

    def read(self):
        """Connect to projector and read gamma table"""
        with JVCCommand() as jvc:
            self.read_jvc(jvc)

def test_match(name, table, expected):
    """Test if generated gamma curve matches expected result"""
    passed = table == expected
    print('Test {} {}'.format(name, 'PASSED' if passed else 'FAILED'))
    if passed:
        return
    if not isinstance(expected, list):
        print('Got {}, Expected {}, Error {}'.format(table, expected, table-expected))
        return
    dumpdata.dumpdata('Got:      ', '{:4}', table, limit=16)
    dumpdata.dumpdata('Expected: ', '{:4}', expected, limit=16)
    dumpdata.dumpdata('Error:    ', '{:4}', [a - b for a, b in zip(table, expected)], limit=16)

def main():
    """JVC gamma test"""
    gamma = GammaCurve()
    test_match('Default', gamma.get_table(), [round(i / 255 * 1023) for i in range(256)])

    gamma.bhardclip = 100 * 0.5 ** 2.2
    test_match('ohardclip 512', gamma.get_table(),
               [round(min(i / 255 * 1023, 512)) for i in range(256)])

    gamma.bhardclip = None
    gamma.brefwhite = 100 * (511/1023) ** 2.2
    test_match('irefwhite 511/4', gamma.get_table(), [round(i / 255 * 511) for i in range(256)])

    gamma.brefwhite = 100 * (2047/1023) ** 2.2
    test_match('irefwhite 2047/4', gamma.get_table(),
               [min(1023, round(i / 255 * 2047)) for i in range(256)])

    bbase = 100 * (511/1023) ** 2.2
    gamma.set_scaled_bsoftclip(bbase=bbase, bmin=bbase, scale=0)
    test_match('get_effective_bsoftclip scale 0', gamma.get_effective_bsoftclip(), bbase)

    gamma.set_scaled_bsoftclip(bbase=bbase, bmin=bbase, scale=1)
    test_match('get_effective_bsoftclip scale 1',
               gamma.get_effective_bsoftclip(), gamma.get_effective_bmax())

    gamma.set_scaled_bsoftclip(bbase=bbase, bmin=bbase, scale=0.5)
    test_match('get_effective_bsoftclip scale 0.5',
               gamma.get_effective_bsoftclip(), bbase + (gamma.get_effective_bmax() - bbase) / 2)

    gamma.bhardclip = 100 * (132/255) ** 2.2
    gamma.bsoftclip = 100 * (120/255) ** 2.2

    test_match('Softclip', gamma.get_table(),
               [round(i / 255 * 2047) for i in range(123)] +
               [986, 993, 1000, 1005, 1009, 1013, 1016, 1018, 1021] + [1023 for i in range(124)])

if __name__ == "__main__":
    main()
