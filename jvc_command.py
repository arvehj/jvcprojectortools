#!/usr/bin/env python3

"""JVC projector low level command module"""

from enum import Enum

import dumpdata
import jvc_protocol
from jvc_protocol import CommandNack

class ReadOnly():
    """Common base class for read-only command arguments"""
    pass

class NoVerify():
    """Common base class for command arguments that cannot be read back"""

class WriteOnly(NoVerify):
    """Common base class for write-only command arguments"""
    pass

class BinaryData():
    """Common base class for binary command arguments"""
    pass

class Model(ReadOnly, Enum):
    """Projector model code"""
    DLA_X550R_X5000_XC5890R_RS400 = b'ILAFPJ -- XHP1'
    DLA_XC6890 = b'ILAFPJ -- XHP2'
    DLA_X750R_X7000_XC7890R_RS500_X950R_X9000_RS600_PX1 = b'ILAFPJ -- XHP3'

def s8_bytes_to_list(bstr):
    """Convert 8bit signed bytes to list"""
    return [b if b < 0x80 else b - 0x100 for b in bstr]

def num_to_s8(num):
    """Convert signed number to 8bit (unsigned)"""
    assert -0x80 <= num < 0x80, '{} out of range'.format(num)
    return num & 0xff

def list_to_s8_bytes(numlist):
    """Convert list of signed numbers to 8bit bytes"""
    return bytes(num_to_s8(num) for num in numlist)

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

class Numeric(int):
    """Signed 16 bit values as ascii hex data"""
    def __new__(cls, value):
        if isinstance(value, bytes):
            assert len(value) == 4, '{} is not 4 bytes'.format(value)
            cls.value = value
        else:
            assert -0x8000 <= value <= 0x7fff, '{} out of range'.format(value)
            cls.value = bytes('{:04X}'.format(value & 0xffff), 'ascii')
        num = int(cls.value, 16)
        if num & 0x8000:
            num = num - 0x10000
        return super(Numeric, cls).__new__(cls, num)

class NumericReadOnly(ReadOnly, Numeric):
    """Read only numeric value"""
    pass

class CustomGammaTable(BinaryData, list):
    """Custom gamma table data"""
    def __init__(self, value):
        if isinstance(value, bytes):
            assert len(value) == 512, '{} is not 512 bytes'.format(value)
            self.value = value
        else:
            assert len(value) == 256, '{} does not have 256 entries'.format(value)
            self.value = list_to_le16_bytes(value)

        super(CustomGammaTable, self).__init__(le16_bytes_to_list(self.value))

class PanelAlignment(BinaryData, list):
    """Panel Alignment Data"""
    def __init__(self, value):
        if isinstance(value, bytes):
            assert len(value) == 256, '{} is not 256 bytes'.format(value)
            self.value = value
        else:
            assert len(value) == 256, '{} does not have 256 entries'.format(value)
            self.value = list_to_s8_bytes(value)

        super(PanelAlignment, self).__init__(s8_bytes_to_list(self.value))

class SourceAsk(ReadOnly, Enum):
    """Source Asking State"""
    NoSignalOrOutOfRange = b'0'
    SignalAvailable = b'1'

class Null(WriteOnly, Enum):
    """Null command arg"""
    Null = b''

class RemoteCode(WriteOnly, Enum):
    """Remote codes"""
    Back = b'7303'
    Menu = b'732E'
    PictureAdjust = b'7372'

class PowerState(NoVerify, Enum):
    """Power state"""
    StandBy = b'0' # send/get
    LampOn = b'1' # send/get
    Cooling = b'2' # get
    Starting = b'3' # get
    Error = b'4' # get

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

class ColorTemperature(Enum):
    """Color Temperature Setting"""
    Temp5500K = b'0'
    Temp6500K = b'2'
    Temp7500K = b'4'
    Temp9300K = b'8'
    HighBright = b'9'
    Custom1 = b'A'
    Custom2 = b'B'
    Custom3 = b'C'
    Xenon1 = b'D'
    Xenon2 = b'E'
    Xenon3 = b'F'

class ColorTemperatureCorrection(Enum):
    """Color Temperature Correction Setting"""
    Temp5500K = b'0'
    Temp6500K = b'2'
    Temp7500K = b'4'
    Temp9300K = b'8'
    HighBright = b'9'
    Xenon1 = b'D'
    Xenon2 = b'E'
    Xenon3 = b'F'

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
    Normal = b'00'
    GammaA = b'01'
    GammaB = b'02'
    GammaC = b'03'
    Import = b'04'
    Gamma1_8 = b'05'
    Gamma1_9 = b'06'
    Gamma2_0 = b'07'
    Gamma2_1 = b'08'
    Gamma2_2 = b'09'
    Gamma2_3 = b'0A'
    Gamma2_4 = b'0B'
    Gamma2_5 = b'0C'
    Gamma2_6 = b'0D'
    Film1 = b'0E'
    Film2 = b'0F'
    GammaD = b'14'

class ColorManagement(Enum):
    """Color Management Setting"""
    Off = b'0'
    On = b'1'

class ClearMotionDrive(Enum):
    """Clear Motion Drive Setting"""
    Off = b'0'
    Low = b'3'
    High = b'4'
    InverseTelecine = b'5'

class MotionEnhance(Enum):
    """Motion Enhance Setting"""
    Off = b'0'
    Low = b'1'
    High = b'2'

class LampPower(Enum):
    """Lamp Power Setting"""
    Normal = b'0'
    High = b'1'

class MPCAnalyze(Enum):
    """MPC Analyze Mode"""
    Off = b'0'
    Analyze = b'1'
    AnalyzeEnhance = b'2'
    AnalyzeDynamicContrast = b'3'
    AnalyzeSmoothing = b'4'
    AnalyzeHistogram = b'5'

class EShift4K(Enum):
    """4K e-shift Setting"""
    Off = b'0'
    On = b'1'

class OriginalResolution(Enum):
    """e-shift Original Resolution Setting"""
    Auto = b'0'
    Res1080P = '3'
    Res4K = '4'

class HDMIInputLevel(Enum):
    """HDMI Input Level Setting"""
    Standard = b'0' # 16-235
    Enhanced = b'1' # 0-255
    SuperWhite = b'2' # 16-255
    Auto = b'3'

class HDMIColorSpace(Enum):
    """HDMI Color Space Setting"""
    Auto = b'0'
    YCbCr444 = b'1'
    YCbCr422 = b'2'
    RGB = b'3'

class SourceData(ReadOnly, str):
    """Input Info Source Information"""
    def __new__(cls, value):
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
            }[value]

class DeepColorData(ReadOnly, str):
    """Input Info Deep Color"""
    def __new__(cls, value):
        return {
            b'0': '8 bit',
            b'1': '10 bit',
            b'2': '12 bit',
            }[value]

class ColorSpaceData(ReadOnly, str):
    """Input Info Color Space"""
    def __new__(cls, value):
        return {
            b'0': 'RGB',
            b'1': 'YUV',
            b'2': 'x.v.Color',
            }[value]

class Command(Enum):
    """Command codes (and return types)"""
    Null = b'\0\0', Null # NULL command
    Power = b'PW', PowerState # Power [PoWer]
    Input = b'IP', InputState # Input [InPut]
    Remote = b'RC', RemoteCode # Remote control code through [Remote Code]
    SetupCom = b'SURS' # Initial setup [SetUp] external control compatible command protocol
    SetupIR = b'SURC' # Initial setup [SetUp] IR code
    GammaRed = b'GR', CustomGammaTable # Gamma data (Red) of the Gamma table ”Custom 1/2/3”
    GammaGreen = b'GG', CustomGammaTable # Gamma data (Green) of the Gamma table ”Custom 1/2/3”
    GammaBlue = b'GB', CustomGammaTable # Gamma data (Blue) of the Gamma table ”Custom 1/2/3”
    PanelAlignRed = b'PR', PanelAlignment # Red of Panel Alignment (zone)
    PanelAlignBlue = b'PB', PanelAlignment # Blue of Panel Alignment (zone)
    SourceAsk = b'SC', SourceAsk # Source asking [SourCe]
    Model = b'MD', Model   # Model status asking [MoDel]

    # Picture adjustment [adjustment of Picture] : Picture Adjust
    PictureMode = b'PMPM', PictureMode # Picture Mode switch
    ClearBlack = b'PMAN', ClearBlack # Clear Black
    IntelligentLensAperture = b'PMDI', IntelligentLensAperture # Intelligent Lens Aperture
    ColorProfile = b'PMPR', ColorProfile # Color Profile switch (*1)
    ColorTemperatureTable = b'PMCL', ColorTemperature # Color Temperature table
    ColorTemperatureCorrection = b'PMCC', ColorTemperatureCorrection # Color Temperature Correction
    ColorTemperatureGainRed = b'PMGR', Numeric # Color Temperature Gain (Red) adjustment
    ColorTemperatureGainGreen = b'PMGG', Numeric # Color Temperature Gain (Green) adjustment
    ColorTemperatureGainBlue = b'PMGB', Numeric # Color Temperature Gain (Blue) adjustment
    ColorTemperatureOffsetRed = b'PMOR', Numeric # Color Temperature Offset (Red) adjustment
    ColorTemperatureOffsetGreen = b'PMOG', Numeric # Color Temperature Offset (Green) adjustment
    ColorTemperatureOffsetBlue = b'PMOB', Numeric # Color Temperature Offset (Blue) adjustment
    GammaTable = b'PMGT', GammaTable # Gamma Table switch
    PictureToneWhite = b'PMFW', Numeric # Picture Tone (White) adjustment
    PictureToneRed = b'PMFR', Numeric # Picture Tone (Red) adjustment
    PictureToneGreen = b'PMFG', Numeric # Picture Tone (Green) adjustment
    PictureToneBlue = b'PMFB', Numeric # Picture Tone (Blue) adjustment
    Contrast = b'PMCN', Numeric # Contrast adjustment
    Brightness = b'PMBR', Numeric # Brightness adjustment
    Color = b'PMCO', Numeric # Color adjustment
    Tint = b'PMTI', Numeric # Tint adjustment
    NoiseReduction = b'PMRN', Numeric # NR adjustment
    GammaCorrection = b'PMGC', GammaCorrection # Gamma Correction switch
    PMGammaRed = b'PMDR', CustomGammaTable # Gamma Red data
    PMGammaGreen = b'PMDG', CustomGammaTable # Gamma Green data
    PMGammaBlue = b'PMDB', CustomGammaTable # Gamma Blue data
    BrightLevelWhite = b'PMRW', Numeric # Bright Level White
    BrightLevelRed = b'PMRR', Numeric # Bright Level Red
    BrightLevelGreen = b'PMRG', Numeric # Bright Level Green
    BrightLevelBlue = b'PMRB', Numeric # Bright Level Blue
    DarkLevelWhite = b'PMKW', Numeric # Dark Level White
    DarkLevelRed = b'PMKR', Numeric # Dark Level Red
    DarkLevelGreen = b'PMKG', Numeric # Dark Level Green
    DarkLevelBlue = b'PMKB', Numeric # Dark Level Blue
    ColorManagementTable = b'PMCB', ColorManagement # Color Management table
    AxisPositionRed = b'PMAR', Numeric # Axis Position (Red) adjustment
    AxisPositionYellow = b'PMAY', Numeric # Axis Position (Yellow) adjustment
    AxisPositionGreen = b'PMAG', Numeric # Axis Position (Green) adjustment
    AxisPositionCyan = b'PMAC', Numeric # Axis Position (Cyan) adjustment
    AxisPositionBlue = b'PMAB', Numeric # Axis Position (Blue) adjustment
    AxisPositionMagenta = b'PMAM', Numeric # Axis Position (Magenta) adjustment
    HUERed = b'PMHR', Numeric # HUE (Red) adjustment
    HUEYellow = b'PMHY', Numeric # HUE (Yellow) adjustment
    HUEGreen = b'PMHG', Numeric # HUE (Green) adjustment
    HUECyan = b'PMHC', Numeric # HUE (Cyan) adjustment
    HUEBlue = b'PMHB', Numeric # HUE (Blue) adjustment
    HUEMagenta = b'PMHM', Numeric # HUE (Magenta) adjustment
    SaturationRed = b'PMSR', Numeric # Saturation (Red) adjustment
    SaturationYellow = b'PMSY', Numeric # Saturation (Yellow) adjustment
    SaturationGreen = b'PMSG', Numeric # Saturation (Green) adjustment
    SaturationCyan = b'PMSC', Numeric # Saturation (Cyan) adjustment
    SaturationBlue = b'PMSB', Numeric # Saturation (Blue) adjustment
    SaturationMagenta = b'PMSM', Numeric # Saturation (Magenta) adjustment
    BrightnessRed = b'PMLR', Numeric # Brightness (Red) adjustment
    BrightnessYellow = b'PMLY', Numeric # Brightness (Yellow) adjustment
    BrightnessGreen = b'PMLG', Numeric # Brightness (Green) adjustment
    BrightnessCyan = b'PMLC', Numeric # Brightness (Cyan) adjustment
    BrightnessBlue = b'PMLB', Numeric # Brightness (Blue) adjustment
    BrightnessMagenta = b'PMLM', Numeric # Brightness (Magenta) adjustment
    ClearMotionDrive = b'PMCM', ClearMotionDrive # Clear Motion Drive
    MotionEnhance = b'PMME', MotionEnhance # Motion Enhance
    LensAperture = b'PMLA', Numeric # Lens Aperture
    LampPower = b'PMLP', LampPower # Lamp Power
    MPCAnalyze = b'PMMA', MPCAnalyze # MPC Analyze
    EShift4K = b'PMUS', EShift4K # 4K e-shift
    OriginalResolution = b'PMRP', OriginalResolution # Original Resolution
    Enhance = b'PMEN', Numeric # Enhance
    DynamicContrast = b'PMDY', Numeric # Dynamic Contrast
    Smoothing = b'PMST', Numeric # Smoothing
    NameEditofPictureModeUser1 = b'PMU1' # Name Edit of Picture Mode User1
    NameEditofPictureModeUser2 = b'PMU2' # Name Edit of Picture Mode User2
    NameEditofPictureModeUser3 = b'PMU3' # Name Edit of Picture Mode User3
    NameEditofPictureModeUser4 = b'PMU4' # Name Edit of Picture Mode User4
    NameEditofPictureModeUser5 = b'PMU5' # Name Edit of Picture Mode User5
    NameEditofPictureModeUser6 = b'PMU6' # Name Edit of Picture Mode User6

    # Picture adjustment [adjustment of Picture] : Input Signal
    HDMIInputLevel = b'ISIL', HDMIInputLevel # HDMI Input Level switch
    HDMIColorSpace = b'ISHS', HDMIColorSpace # HDMI Color Space switch
    HDMI2D3D = b'IS3D' # HDMI 2D/3D switch
    HDMI3DPhase = b'IS3P' # HDMI 3D Phase adjustment
    PicturePositionHorizontal = b'ISPH', Numeric # Picture Position (Horizontal) adjustment
    PicturePositionVertical = b'ISPV', Numeric # Picture Position (Vertical) adjustment
    Aspect = b'ISAS' # Aspect switch
    Mask = b'ISMA' # Mask switch
    MaskLeft = b'ISML', Numeric # Mask (Left) adjustment
    MaskRight = b'ISMR', Numeric # Mask (Right) adjustment
    MaskTop = b'ISMT', Numeric # Mask (Top) adjustment
    MaskBottom = b'ISMB', Numeric # Mask (Bottom) adjustment
    FilmMode = b'ISFM' # Film Mode switch
    Parallaxof3Dconversion = b'ISLV', Numeric # Parallax of 3D conversion adjustment
    CrosstalkCancelWhite = b'ISCA', Numeric # Crosstalk Cancel (White) adjustment

    # Picture adjustment [adjustment of Picture] : Installation
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
    PixelAdjustHorizontalRed = b'INXR', Numeric # Pixel Adjust (Horizontal Red) adjustment
    PixelAdjustHorizontalBlue = b'INXB', Numeric # Pixel Adjust (Horizontal Blue) adjustment
    PixelAdjustVerticalRed = b'INYR', Numeric # Pixel Adjust (Vertical Red) adjustment
    PixelAdjustVerticalBlue = b'INYB', Numeric # Pixel Adjust (Vertical Blue) adjustment
    InstallationStyle = b'INIS' # Installation Style switch
    KeystoneVertical = b'INKV', Numeric # Keystone (Vertical) adjustment
    Anamorphic = b'INVS' # Anamorphic switch
    ScreenAdjustData = b'INSA', Numeric # Screen Adjust Data
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

    # Picture adjustment [adjustment of Picture] : Display Setup
    BackColor = b'DSBC' # Back Color switch
    MenuPosition = b'DSMP' # Menu Position switch
    SourceDisplay = b'DSSD' # Source Display switch
    Logo = b'DSLO' # Logo switch
    Language = b'DSLA' # Language switch

    # Picture adjustment [adjustment of Picture] : Function
    Trigger = b'FUTR' # Trigger switch
    OffTimer = b'FUOT' # Off Timer switch
    EcoMode = b'FUEM' # Eco Mode switch
    Control4 = b'FUCF' # Control4

    # Picture adjustment [adjustment of Picture] : Information
    InfoInput = b'IFIN', InputState # Input display
    InfoSource = b'IFIS', SourceData # Source display
    InfoHorizontalResolution = b'IFRH', NumericReadOnly # Horizontal Resolution display
    InfoVerticalResolution = b'IFRV', NumericReadOnly # Vertical Resolution display
    InfoHorizontalFrequency = b'IFFH', NumericReadOnly # Horizontal Frequency display (*4)
    InfoVerticalFrequency = b'IFFV', NumericReadOnly # Vertical Frequency display (*4)
    InfoDeepColor = b'IFDC', DeepColorData # Deep Color display
    InfoColorSpace = b'IFXV', ColorSpaceData # Color space display
    InfoLampTime = b'IFLT', NumericReadOnly # Lamp Time display
    InfoSoftVersion = b'IFSV' # Soft Version Display
    InfoCalibratorInformation = b'IFCI' # Calibrator Information transmission/display (*5)

    PMCalibratorInformation = b'PMCI' # Calibrator Information transmission/display (*5)
    LanSetup = b'LS'   # LAN setup [Lan Setup]

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

    def get(self, cmd):
        """Send reference command and convert response"""
        if isinstance(cmd.value, bytes):
            raise NotImplementedError('Get is not implemented for {}'.format(cmd.name))
        cmdcode, valtype = cmd.value
        if issubclass(valtype, WriteOnly):
            raise TypeError('{} is a write only command'.format(cmd.name))
        try:
            if issubclass(valtype, BinaryData):
                response = self.conn.cmd_ref_bin(cmdcode)
            else:
                response = self.conn.cmd_ref(cmdcode)
            return valtype(response)
        except CommandNack as err:
            raise CommandNack('Get: ' + err.args[0], cmd.name)

    def set(self, cmd, val, verify=True):
        """Send operation command"""
        cmdcode, valtype = cmd.value
        assert not issubclass(valtype, ReadOnly), '{} is a read only command'.format(cmd)
        val = valtype(val)
        assert(isinstance(val, valtype)), '{} is not {}'.format(val, valtype)
        try:
            if issubclass(valtype, BinaryData):
                self.conn.cmd_op(cmdcode, sendrawdata=val.value)
            else:
                self.conn.cmd_op(cmdcode+val.value, acktimeout=5)
        except CommandNack as err:
            raise CommandNack('Set: ' + err.args[0], cmd.name, val)

        if not verify or issubclass(valtype, NoVerify):
            return

        verify_val = self.get(cmd)
        if verify_val != val:
            raise CommandNack('Verify error: ' + cmd.name, val, verify_val)

def main():
    """JVC command class test"""
    print('test jvc command class')
    try:
        with JVCCommand(print_all=False) as jvc:
            jvc.set(Command.Null, Null.Null)
            model = jvc.get(Command.Model)
            print('Model:', model)
            power_state = jvc.get(Command.Power)
            print('Power:', power_state)
            while power_state != PowerState.LampOn:
                print('Projector is not on ({}), most commands will fail'.format(
                    power_state.name))
                res = input('Enter "on" to send power on command, or "i" to ignore: ')
                if res == 'on':
                    try:
                        jvc.set(Command.Power, PowerState.LampOn)
                    except jvc_protocol.CommandNack:
                        print('Failed to set power')
                elif res == 'i':
                    break
                power_state = jvc.get(Command.Power)

            skipped = []
            for command in Command:
                try:
                    res = jvc.get(command)
                    if isinstance(res, list):
                        dumpdata.dumpdata(command.name, '{:4}', res, limit=16)
                    else:
                        print('{}: {!s}'.format(command.name, res))
                except CommandNack as err:
                    print('-{}: {!s}'.format(command.name, err.args[0]))
                except (TypeError, NotImplementedError) as err:
                    skipped.append((command, err))
            for command, err in skipped:
                print('-Skipped {}: {!s}'.format(command.name, err))

            input('Test complete, press enter: ')

    except CommandNack as err:
        print('Nack', err)
    except jvc_protocol.jvc_network.Error as err:
        print('Error', err)

if __name__ == "__main__":
    main()
