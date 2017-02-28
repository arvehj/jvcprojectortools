# JVC Projector Tools

Scripts to send commands 2015 model JVC D-ILA Projectors.

## Prerequisites
- Python [3.6](https://www.python.org/downloads/release/python-360/) or [later](https://www.python.org/downloads/) installed
- Network connected JVC projector

## Quick start
Run menu.py, enter "1" for "Setup HDR" and follow the on-screen instructions.

### Main menu
The menu lists the commands you can enter on the left and a description on the right. Some commands accepts optional arguments. These arguments are listed as [argument] in the description. Multiple commands can be run if separated by ";"

#### Setup HDR
This menu checks your setup and configures a HDR gamma curve that you can tune the brightness of.

#### Set brightness and contrast for source
Run only the source brightness/contrast check from Setup HDR.

#### Load into projector and tune with contrast control
Adjust the brightness of the current gamma curve using the contrast control on the projector.

#### Adjust gamma curve
Enables menu options to adjust the gamma curve.

#### Load preset gamma curve
Select a preset gamma curve.
- hdr pq - HDR gamma curve for content up to 4000nits
- hdr pq 1200 - HDR gamma curve for content up to 1000nits

#### Load gamma curve from file [confname]
Loads a saved gamma curve from a file. If you don't specify a confname the gamma curve loaded at startup will be used.

#### Write gamma curve to projector
Sends the gamma curve to the projector. (Also saves a backup to a file)

#### Quit and discard changes
Quit the menu without saving any changes to the config file.

#### Save save current gamma parameters [confname]
Saves the gamma curve to a file. If you don't specify a confname the gamma curve will be saved to a file that gets loaded on startup.

#### Quit and save current gamma parameters [confname]
Save the gamma curve and quit.

#### Parameters for gamma curve
- "max brightness" is the peak brightness your projector can reach.
- "reference white" is how bright you want a 100 nit reference white to be. Lowering this value will make the image darker and increasing it will make the image brighter.
- "soft clip start brightness" is the brightness where the curve will stop following the eotf curve and start a soft clip curve.
- "hard clip brightness" is where the soft clip curve ends.
- "clip end slope" moves the angle of the curve at the end point from horizontal (1) to pointing at the soft clip start point (0).
- "soft clip method" selects between a cubic Bézier curve (0) and quadratic Bézier curve (1).
- "soft clip gamma" selects the gamma to draw the soft clip curve in.

Select toggle white in the menu to match the input level setting in the projector settings you plan to use.
