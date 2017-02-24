#!/usr/bin/env python3

"""JVC projector low level command module"""

from enum import Enum
import traceback

import dumpdata
import jvc_protocol
from jvc_protocol import CommandNack

def le16_bytes_to_list(bstr):
    """Convert 16bit little-endian bytes to list"""
    i = iter(bstr)
    return [lb + 256*next(i) for lb in i]

def le16_split(table):
    """Split table entries 16bit little-endian byte pairs"""
    for val in table:
        assert not val >> 16
        yield val % 256
        yield int(val / 256)

def list_to_le16_bytes(table):
    """Convert list to 16bit little-endian bytes"""
    return bytes(le16_split(table))

class Command(Enum):
    """Command codes"""
    null = b'\0\0' # NULL command
    power = b'PW'   # Power [PoWer]
    input = b'IP'   # Input [InPut]
    remote = b'RC'   # Remote control code through [Remote Code]
    setup = b'SU'   # Initial setup [SetUp]
    gammared = b'GR'   # Gamma data (Red) of the Gamma table ”Custom 1/2/3” [Gamma Red]
    gammagreen = b'GG'   # Gamma data (Green) of the Gamma table ”Custom 1/2/3” [Gamma Green]
    gammablue = b'GB'   # Gamma data (Blue) of the Gamma table ”Custom 1/2/3” [Gamma Blue]
    panelalignred = b'PR'   # Red of Panel Alignment (zone)  
    panelalignblue = b'PB'   # Blue of Panel Alignment (zone)  
    sourceask = b'SC'   # Source asking [SourCe] - 
    model = b'MD'   # Model status asking [MoDel] - 

    # Picture adjustment [adjustment of Picture] : Picture Adjust  
    PictureMode = b'PMPM' # Picture Mode switch
    ClearBlack = b'PMAN' # Clear Black
    IntelligentLensAperture = b'PMDI' # Intelligent Lens Aperture
    ColorProfile = b'PMPR' # Color Profile switch (*1)
    ColorTemperatureTable = b'PMCL' # Color Temperature table switch
    ColorTemperatureCorrection = b'PMCC' # Color Temperature Correction switch
    ColorTemperatureGainRed = b'PMGR' # Color Temperature Gain (Red) adjustment
    ColorTemperatureGainGreen = b'PMGG' # Color Temperature Gain (Green) adjustment
    ColorTemperatureGainBlue = b'PMGB' # Color Temperature Gain (Blue) adjustment
    ColorTemperatureOffsetRed = b'PMOR' # Color Temperature Offset (Red) adjustment
    ColorTemperatureOffsetGreen = b'PMOG' # Color Temperature Offset (Green) adjustment
    ColorTemperatureOffsetBlue = b'PMOB' # Color Temperature Offset (Blue) adjustment
    GammaTable = b'PMGT' # Gamma Table switch
    PictureToneWhite = b'PMFW' # Picture Tone (White) adjustment
    PictureToneRed = b'PMFR' # Picture Tone (Red) adjustment
    PictureToneGreen = b'PMFG' # Picture Tone (Green) adjustment
    PictureToneBlue = b'PMFB' # Picture Tone (Blue) adjustment
    Contrast = b'PMCN' # Contrast adjustment
    Brightness = b'PMBR' # Brightness adjustment
    Color = b'PMCO' # Color adjustment
    Tint = b'PMTI' # Tint adjustment
    NoiseReduction = b'PMRN' # NR adjustment
    GammaCorrection = b'PMGC' # Gamma Correction switch
    GammaRed = b'PMDR' # Gamma Red data
    GammaGreen = b'PMDG' # Gamma Green data
    GammaBlue = b'PMDB' # Gamma Blue data
    BrightLevelWhite = b'PMRW' # Bright Level White
    BrightLevelRed = b'PMRR' # Bright Level Red
    BrightLevelGreen = b'PMRG' # Bright Level Green
    BrightLevelBlue = b'PMRB' # Bright Level Blue
    DarkLevelWhite = b'PMKW' # Dark Level White
    DarkLevelRed = b'PMKR' # Dark Level Red
    DarkLevelGreen = b'PMKG' # Dark Level Green
    DarkLevelBlue = b'PMKB' # Dark Level Blue
    ColorManagementTable = b'PMCB' # Color Management table
    AxisPositionRed = b'PMAR' # Axis Position (Red) adjustment
    AxisPositionYellow = b'PMAY' # Axis Position (Yellow) adjustment
    AxisPositionGreen = b'PMAG' # Axis Position (Green) adjustment
    AxisPositionCyan = b'PMAC' # Axis Position (Cyan) adjustment
    AxisPositionBlue = b'PMAB' # Axis Position (Blue) adjustment
    AxisPositionMagenta = b'PMAM' # Axis Position (Magenta) adjustment
    HUERed = b'PMHR' # HUE (Red) adjustment
    HUEYellow = b'PMHY' # HUE (Yellow) adjustment
    HUEGreen = b'PMHG' # HUE (Green) adjustment
    HUECyan = b'PMHC' # HUE (Cyan) adjustment
    HUEBlue = b'PMHB' # HUE (Blue) adjustment
    HUEMagenta = b'PMHM' # HUE (Magenta) adjustment
    SATURATIONRed = b'PMSR' # SATURATION (Red) adjustment
    SATURATIONYellow = b'PMSY' # SATURATION (Yellow) adjustment
    SATURATIONGreen = b'PMSG' # SATURATION (Green) adjustment
    SATURATIONCyan = b'PMSC' # SATURATION (Cyan) adjustment
    SATURATIONBlue = b'PMSB' # SATURATION (Blue) adjustment
    SATURATIONMagenta = b'PMSM' # SATURATION (Magenta) adjustment
    BRIGHTNESSRed = b'PMLR' # BRIGHTNESS (Red) adjustment
    BRIGHTNESSYellow = b'PMLY' # BRIGHTNESS (Yellow) adjustment
    BRIGHTNESSGreen = b'PMLG' # BRIGHTNESS (Green) adjustment
    BRIGHTNESSCyan = b'PMLC' # BRIGHTNESS (Cyan) adjustment
    BRIGHTNESSBlue = b'PMLB' # BRIGHTNESS (Blue) adjustment
    BRIGHTNESSMagenta = b'PMLM' # BRIGHTNESS (Magenta) adjustment
    ClearMotionDrive = b'PMCM' # Clear Motion Drive
    MotionEnhance = b'PMME' # Motion Enhance
    LensAperture = b'PMLA' # Lens Aperture
    LampPower = b'PMLP' # Lamp Power
    MPCAnalyze = b'PMMA' # MPC Analyze
    EShift4K = b'PMUS' # 4K e-shift
    OriginalResolution = b'PMRP' # Original Resolution
    Enhance = b'PMEN' # Enhance
    DynamicContrast = b'PMDY' # Dynamic Contrast
    Smoothing = b'PMST' # Smoothing
    NameEditofPictureModeUser1 = b'PMU1' # Name Edit of Picture Mode User1
    NameEditofPictureModeUser2 = b'PMU2' # Name Edit of Picture Mode User2
    NameEditofPictureModeUser3 = b'PMU3' # Name Edit of Picture Mode User3
    NameEditofPictureModeUser4 = b'PMU4' # Name Edit of Picture Mode User4
    NameEditofPictureModeUser5 = b'PMU5' # Name Edit of Picture Mode User5
    NameEditofPictureModeUser6 = b'PMU6' # Name Edit of Picture Mode User6

    # Picture adjustment [adjustment of Picture] : Input Signal  
    HDMIInputLevel = b'ISIL' # HDMI Input Level switch
    HDMIColorSpace = b'ISHS' # HDMI Color Space switch
    HDMI2D3D = b'IS3D' # HDMI 2D/3D switch
    HDMI3DPhase = b'IS3P' # HDMI 3D Phase adjustment
    PicturePositionHorizontal = b'ISPH' # Picture Position (Horizontal) adjustment
    PicturePositionVertical = b'ISPV' # Picture Position (Vertical) adjustment
    Aspect = b'ISAS' # Aspect switch
    Mask = b'ISMA' # Mask switch
    MaskLeft = b'ISML' # Mask (Left) adjustment
    MaskRight = b'ISMR' # Mask (Right) adjustment
    MaskTop = b'ISMT' # Mask (Top) adjustment
    MaskBottom = b'ISMB' # Mask (Bottom) adjustment
    FilmMode = b'ISFM' # Film Mode switch
    Parallaxof3Dconversion = b'ISLV' # Parallax of 3D conversion adjustment
    CrosstalkCancelWhite = b'ISCA' # Crosstalk Cancel (White) adjustment

    # Picture adjustment [adjustment of Picture] : Installation  
    FocusNear = b'INFN' # Focus Near adjustment (*3)
    FocusFar = b'INFF' # Focus Far adjustment (*3)
    ZoomTele = b'INZT' # Zoom Tele adjustment (*3)
    ZoomWide = b'INZW' # Zoom Wide adjustment (*3)
    ShiftLeft = b'INSL' # Shift Left adjustment (*3)
    ShiftRight = b'INSR' # Shift Right adjustment (*3)
    ShiftUp = b'INSU' # Shift Up adjustment (*3)
    ShiftDown = b'INSD' # Shift Down adjustment (*3)
    LensCover = b'INCV' # Lens Cover switch
    ImagePattern = b'INIP' # Image Pattern switch
    LensLock = b'INLL' # Lens Lock switch
    PixelAdjustHorizontalRed = b'INXR' # Pixel Adjust (Horizontal Red) adjustment
    PixelAdjustHorizontalBlue = b'INXB' # Pixel Adjust (Horizontal Blue) adjustment
    PixelAdjustVerticalRed = b'INYR' # Pixel Adjust (Vertical Red) adjustment
    PixelAdjustVerticalBlue = b'INYB' # Pixel Adjust (Vertical Blue) adjustment
    InstallationStyle = b'INIS' # Installation Style switch
    KeystoneVertical = b'INKV' # Keystone (Vertical) adjustment
    Anamorphic = b'INVS' # Anamorphic switch
    ScreenAdjustData = b'INSA' # Screen Adjust Data
    ScreenAdjust = b'INSC' # Screen Adjust switch
    PanelAlignment = b'INPA' # Panel Alignment switch
    StoreLensmemory = b'INMS' # Store Lens memory
    LoadLensmemory = b'INML' # Load Lens memory
    NameEditofLensMemory1 = b'INM1' # Name Edit of Lens Memory 1
    NameEditofLensMemory2 = b'INM2' # Name Edit of Lens Memory 2
    NameEditofLensMemory3 = b'INM3' # Name Edit of Lens Memory 3
    NameEditofLensMemory4 = b'INM4' # Name Edit of Lens Memory 4
    NameEditofLensMemory5 = b'INM5' # Name Edit of Lens Memory 5
    NameEditofLensMemory6 = b'INM6' # Name Edit of Lens Memory 6
    NameEditofLensMemory7 = b'INM7' # Name Edit of Lens Memory 7
    NameEditofLensMemory8 = b'INM8' # Name Edit of Lens Memory 8
    NameEditofLensMemory9 = b'INM9' # Name Edit of Lens Memory 9
    NameEditofLensMemory10 = b'INMA' # Name Edit of Lens Memory 10
    FocusNear1Shot = b'IN1N' # Focus Near adjustment (1 shot)(*3)
    FocusFar1Shot = b'IN1F' # Focus Far adjustment (1 shot) (*3)
    ZoomTele1Shot = b'IN1T' # Zoom Tele adjustment (1 shot) (*3)
    ZoomWide1Shot = b'IN1W' # Zoom Wide adjustment (1 shot) (*3)
    ShiftLeft1Shot = b'IN1L' # Shift Left adjustment (1 shot) (*3)
    ShiftRight1Shot = b'IN1R' # Shift Right adjustment (1 shot) (*3)
    ShiftUp1Shot = b'IN1U' # Shift Up adjustment (1 shot) (*3)
    ShiftDown1Shot = b'IN1D' # Shift Down adjustment (1 shot) (*3)
    HighAltitudeMode = b'INHA' # High Altitude mode switch

    # Picture adjustment [adjustment of Picture] : Display Setup  
    BackColor = b'DSBC' # Back Color switch
    MenuPosition = b'DSMP' # Menu Position switch
    SourceDisplay = b'DSSD' # Source Display switch
    Logo = b'DSLO' # Logo switch
    Language = b'DSLA' # Language switch

    # Picture adjustment [adjustment of Picture] : Function  
    Trigger = b'FUTR' # Trigger switch
    OffTimer = b'FUOT' # Off Timer switch
    EcoMode = b'FUEM' # Eco Mode switch
    Control4 = b'FUCF' # Control4

    # Picture adjustment [adjustment of Picture] : Information - 
    InfoInput = b'IFIN' # Input display
    InfoSource = b'IFIS' # Source display
    InfoHorizontalResolution = b'IFRH' # Horizontal Resolution display
    InfoVerticalResolution = b'IFRV' # Vertical Resolution display
    InfoHorizontalFrequency = b'IFFH' # Horizontal Frequency display (*4)
    InfoVerticalFrequency = b'IFFV' # Vertical Frequency display (*4)
    InfoDeepColor = b'IFDC' # Deep Color display
    InfoColorSpace = b'IFXV' # Color space display
    InfoLampTime = b'IFLT' # Lamp Time display
    InfoSoftVersion = b'IFSV' # Soft Version Display
    InfoCalibratorInformation = b'IFCI' # Calibrator Information transmission/display (*5)

    PMCalibratorInformation = b'PMCI' # Calibrator Information transmission/display (*5)
    lansetup = b'LS'   # LAN setup [Lan Setup]

class PowerState(Enum):
    """Power state"""
    StandBy = b'0'
    LampOn = b'1'
    Cooling = b'2'
    Reserved = b'3'
    Error = b'4'

class InputState(Enum):
    """Input state"""
    HDMI1 = b'6'
    HDMI2 = b'7'

class PictureMode(Enum):
    """Picture mode"""
    Film = b'00'
    Cinema = b'01'
    Animation = b'02'
    Natural = b'03'
    THX = b'06'
    User1 = b'0C'
    User2 = b'0D'
    User3 = b'0E'
    User4 = b'0F'
    User5 = b'10'
    User6 = b'11'

class ClearBlack(Enum):
    """Clear Black Setting"""
    Off = b'0'
    Low = b'1'
    High = b'2'

class IntelligentLensAperture(Enum):
    """Intelligent Lens Aperture Setting"""
    Off = b'0'
    Auto1 = b'1'
    Auto2 = b'2'

class ColorProfile(Enum):
    """Color Profile"""
    Off = b'00'
    Film1 = b'01'
    Film2 = b'02'
    Standard = b'03'
    Cinema1 = b'04'
    Cinema2 = b'05'
    Anime1 = b'06'
    Anime2 = b'07'
    Video = b'08'
    xvColor = b'09'
    Cinema3D = b'0C'
    THX = b'0D'
    Custom1 = b'0E'
    Custom2 = b'0F'
    Custom3 = b'10'
    Custom4 = b'11'
    Custom5 = b'12'
    Film3 = b'13'
    Video3D = b'14'
    Animation3D = b'15'
    Film3D = b'1E'
    THX3D = b'20'
    Reference = b'21'
    Custom6 = b'22'

class GammaTable(Enum):
    """Gamma Table Setting"""
    Normal = b'0'
    GammaA = b'1'
    GammaB = b'2'
    GammaC = b'3'
    Custom1 = b'4'
    Custom2 = b'5'
    Custom3 = b'6'
    GammaD = b'7'
    Film1 = b'A'
    Film2 = b'B'

class GammaCorrection(Enum):
    """Gamma Correction Setting"""
    Normal = b'0'
    GammaA = b'1'
    GammaB = b'2'
    GammaC = b'3'
    Import = b'4'
    Gamma1_8 = b'5'
    Gamma1_9 = b'6'
    Gamma2_0 = b'7'
    Gamma2_1 = b'8'
    Gamma2_2 = b'9'
    Gamma2_3 = b'A'
    Gamma2_4 = b'B'
    Gamma2_5 = b'C'
    Gamma2_6 = b'D'
    Film1 = b'E'
    Film2 = b'F'
    #GammaD = b'14'

class JVCCommand:
    """JVC projector low level command processing class"""
    def __init__(self, print_cmd_send=False, print_cmd_res=False, print_all=False, **args):
        self.print_cmd_send = print_cmd_send or print_all
        self.print_cmd_res = print_cmd_res or print_all
        self.print_cmd_bin_res = print_all
        self.conn = jvc_protocol.JVCConnection(print_all=print_all, **args)

    def __enter__(self):
        self.conn.__enter__()
        return self

    def __exit__(self, exception, value, traceback):
        self.conn.__exit__(exception, value, traceback)

    def cmd_op(self, cmd, arg=b'', **kwargs):
        """Send operation command"""
        self.conn.cmd_op(cmd.value+arg, **kwargs)

    def cmd_ref(self, cmd, arg=b'', **kwargs):
        """Send reference command"""
        return self.conn.cmd_ref(cmd.value+arg, **kwargs)

    def cmd_ref_bin(self, cmd, arg=b'', **kwargs):
        """Send reference command and retrieve binary response"""
        return self.conn.cmd_ref_bin(cmd.value+arg, **kwargs)

    def null_op(self):
        """Send null operation command"""
        self.cmd_op(Command.null)

    def set_power(self, power_on):
        """Set Power State"""
        self.cmd_op(Command.power, {False: b'0', True: b'1'}[power_on])

    def get_power(self):
        """Get Power State"""
        res = self.cmd_ref(Command.power)
        return PowerState(res)

    def set_input(self, port):
        """Select input"""
        self.cmd_op(Command.input, port.value, acktimeout=10)

    def get_input(self):
        """Get Power State"""
        res = self.cmd_ref(Command.input)
        return InputState(res)

    def send_remote_code(self, remote_code):
        """Send remote code"""
        self.cmd_op(Command.remote, bytes('{:04x}'.format(remote_code), 'ascii'))

    #skip setup commands

    def set_gamma(self, channel, table):
        """Upload gamma table"""
        assert channel in {Command.gammared,
                           Command.gammagreen,
                           Command.gammablue,
                           Command.GammaRed,
                           Command.GammaGreen,
                           Command.GammaBlue,
                          }
        assert len(table) == 256
        self.cmd_op(channel, sendrawdata=list_to_le16_bytes(table))

    def get_gamma(self, channel):
        """Read gamma table"""
        assert channel in {Command.gammared,
                           Command.gammagreen,
                           Command.gammablue,
                           Command.GammaRed,
                           Command.GammaGreen,
                           Command.GammaBlue,
                          }
        return le16_bytes_to_list(self.cmd_ref_bin(channel))

    def get_model(self):
        """Get model number"""
        return self.cmd_ref(Command.model)

    def set_picture_mode(self, mode):
        """Get picture mode"""
        assert isinstance(mode, PictureMode)
        self.cmd_op(Command.PictureMode, mode.value, acktimeout=10)

    def get_picture_mode(self):
        """Get picture mode"""
        return PictureMode(self.cmd_ref(Command.PictureMode))

    def get_clear_black(self):
        """Get Clear Black"""
        return ClearBlack(self.cmd_ref(Command.ClearBlack))

    def get_gamma_table(self):
        """Get Gamma Table"""
        return GammaTable(self.cmd_ref(Command.GammaTable))

    def set_gamma_table(self, gamma_table):
        """Set Gamma Table"""
        assert isinstance(gamma_table, GammaTable)
        self.cmd_op(Command.GammaTable, gamma_table.value, acktimeout=30)

    def get_gamma_correction(self):
        """Get Gamma Correction"""
        return GammaCorrection(self.cmd_ref(Command.GammaCorrection))

    def get_info_input(self):
        """Get Info Input"""
        return InputState(self.cmd_ref(Command.InfoInput))

    def get_info_source(self):
        """Get Info Source"""
        source = self.cmd_ref(Command.InfoSource)
        try:
            return {
                b'02': '480p',
                b'03': '576p',
                b'04': '720p50',
                b'05': '720p60',
                b'06': '1080i50',
                b'07': '1080i60',
                b'08': '1080p24',
                b'09': '1080p50',
                b'0A': '1080p60',
                b'0B': 'No Signal',
                b'0C': '720p 3D',
                b'0D': '1080i 3D',
                b'0E': '1080p 3D',
                b'10': '4K(4096)60',
                b'11': '4K(4096)50',
                b'12': '4K(4096)30',
                b'13': '4K(4096)25',
                b'14': '4K(4096)24',
                b'15': '4K(3840)60',
                b'16': '4K(3840)50',
                b'17': '4K(3840)30',
                b'18': '4K(3840)25',
                b'19': '4K(3840)24',
                }[source]
        except:
            return source

    def get_info_deep_color(self):
        """Get Info Deep Color"""
        return {
            b'0': '8 bit',
            b'1': '10 bit',
            b'2': '12 bit',
            }[self.cmd_ref(Command.InfoDeepColor)]

    def get_info_color_space(self):
        """Get Info Color Space"""
        return {
            b'0': 'RGB',
            b'1': 'YUV',
            b'2': 'x.v.Color',
            }[self.cmd_ref(Command.InfoColorSpace)]

def main():
    """JVC command class test"""
    print('test jvc command class')
    try:
        with JVCCommand(print_all=False) as jvc:
            jvc.null_op()
            model = jvc.get_model()
            print('Model:', model)
            power_state = jvc.get_power()
            print('Power:', power_state)
            if power_state == PowerState.StandBy:
                try:
                    jvc.set_power(False)
                except jvc_protocol.CommandNack:
                    print('Failed to set power')
                print('Power:', jvc.get_power())
            try:
                inputport = jvc.get_input()
                print('Input', inputport)
                #jvc.set_input(inputport) # slow
                #inputport = jvc.get_input()
                #print('Input', inputport)
            except jvc_protocol.CommandNack:
                print('Failed to get/set input')

            try:
                print(jvc.get_info_input())
                print('Source:', jvc.get_info_source())
                print('Deep Color:', jvc.get_info_deep_color())
                print('Color Space:', jvc.get_info_color_space())

                #jvc.send_remote_code(0x7374) #info

                print(jvc.get_picture_mode())
                print(jvc.get_gamma_table())
                print(jvc.get_gamma_correction())
            except:
                print('a command failed:')
                traceback.print_exc()

            try:
                gamma_red = jvc.get_gamma(Command.gammared)
                dumpdata.dumpdata('  Gamma Red:', '{:4d}', gamma_red, limit=16)
            except jvc_protocol.CommandNack:
                print('Failed to get gamma')
    except CommandNack as err:
        print('Nack', err)
    except jvc_protocol.jvc_network.Error as err:
        print('Error', err)

if __name__ == "__main__":
    main()
