# JVC Projector Tools

Scripts to send commands 2015 model JVC D-ILA Projectors.

## Prerequisites
- Python [3.6](https://www.python.org/downloads/release/python-360/) or [later](https://www.python.org/downloads/) installed
- Network connected JVC projector

## Quick start
Run menu.py, enter "1" for "Setup HDR" and follow the on-screen instructions.

## Main Menu
The menu lists the commands you can enter on the left and a description on the right. Some commands accepts optional arguments. These arguments are listed as [argument] in the description. Multiple commands can be run if separated by ";"

### Setup HDR
This menu checks your setup and configures a HDR gamma curve that you can tune the brightness of.

### Set brightness and contrast for source
Run only the source brightness/contrast check from Setup HDR. This loads a special gamma table that will add color near the correct black and white input signals. When the source input level is correct black will be dark green and white will be bright green. If black appears red-brown it is too dark, and if it appears yellow-brown it is too bright. If white appears yellow it is too dark and if it appears red it is too bright. The brightness and contrast controls on you source may affect both white and black so you may need switch between them several times to get both black and white at the correct level.

### Load into projector and tune with contrast control
Adjust the brightness of the current gamma curve using the contrast control on the projector. This starts by writing the current gamma curve to the projector. You can then make the image brighter or darker with the contrast control on the projector. The contrast control distorts the gamma curve, so the contrast you select is used to generate a new curve. The new curve will have a similar brightness for non-highlight content (below the soft-clip point). If you make large adjustment you may need to repeat the process. When done leave the contrast at 0 and hit enter.

### Adjust gamma curve
Enables menu options to adjust the gamma curve.

### Load preset gamma curve
Select a preset gamma curve.
- hdr pq - HDR gamma curve for content up to 4000nits
- hdr pq 1200 - HDR gamma curve for content up to 1200nits

### Load gamma curve from file [confname]
Loads a saved gamma curve from a file. If you don't specify a confname the gamma curve loaded at start-up will be used.

### Write gamma curve to projector
Sends the gamma curve to the projector. (Also saves a backup to a file)

### Quit and discard changes
Quit the menu without saving any changes to the config file.

### Save save current gamma parameters [confname]
Saves the gamma curve to a file. If you don't specify a confname the gamma curve will be saved to a file that gets loaded on start-up.

### Quit and save current gamma parameters [confname]
Save the gamma curve and quit.

## Gamma Curve Adjust Menu

### eotf
Select electro-optical transfer function to use. To select the most common hdr function enter "eo eotf_pq". Enter "eo" to get a menu of all supported functions.
- eotf_bt1886 - SDR eotf with black level compensation
- eotf_hlg - HDR Hybrid Log-Gamma eotf defined by ITU-R BT.2100-0
- eotf_pq - HDR Perceptual Quantization eotf defined by ITU-R BT.2100-0
- eotf_gamma_2_2 - SDR gamma 2.2
- eotf_gamma_2_4 - SDR gamma 2.4

### Input Level
Select input level to generate gamma curves for. This should match the setting in the projector if the source uses standard video levels. Setup HDR should have configured this, but if you load a curve that does not match your setup you can fix to match here.

### Highlight regions
Highlight input signals by changing the color. Enter "hl" to get a menu of options to select one by one or enter the same options after the "hl". For instance, enter:
- "hl c sc hc" to highlight soft-clipped and hard-clipped areas of the picture.
- "hl c b" to turn a black input signal dark green and allow you to check if the brightness setting for your source is correct (assuming the projectors brightness is set to 0).

### Set max brightness
Use this to set the peak brightness your projector can reach. The first number shown is the number you enter. The second number is a "virtual" brightness scaled by the reference white setting.

### Set brightness scale factor
Sets reference white based on a scale factor. Lowering this value will make the image brighter and increasing it will make the image darker.

### Set ref white brightness
Sets how bright you want a 100 nit reference white input signal to be. Lowering this value will make the image darker and increasing it will make the image brighter.

### Set black brightness in
Subtracts an offset from all input values. This is useful if the source content is using an elevated black level.

### Set black brightness out
Adds an offset to all non-black output values. This is useful if the projector crushes near-black values to black.

### eotf black compensation
Experimental, not saved. Set the black level for EOTFs that support it (currently eotf_bt1886 only).

### Set hard clip
Set the input brightness where the soft clip curve ends and all output values are the same. This should be set higher than the effective value shown in "Set max brightness" or the max brightness will not be reached. 

### Set soft clip start
Set the input brightness where the curve will stop following the eotf curve and start a soft clip curve. This can be set to a fixed value, or it can be calculated based on a set of values. The soft-clip start value needs to be lower than the effective value shown in "Set max brightness" or there will be no room for a curve.

### Set end slope
Set to a value between 0 and 1 to shape the soft-clip curve. The angle of the curve at the end point can move from horizontal (1) to pointing at the soft-clip start point (0). The curve a the start of the soft-clip start point always points in the same direction as the eotf curve at that point, but as the end-slope value gets smaller this part of the curve gets less and less weight.

### Set soft clip curve type
Selects between a cubic Bézier curve (0) and quadratic Bézier curve (1). 0 gives more weight to the angle at the start and end points, and will deviate less from the eotf curve at the start.

### Set soft clip gamma
Selects the gamma to draw the soft clip curve in.

### Show plot menu
Enable menu entries to plot the gamma curve.

### Scale ref white brightness from contrast
Adjust reference white to match a the contrast setting on the projector. For instance "bwc 10" will make reference white brighter by the same amount as changing the contrast setting on the projector from 0 to 10.

### Read raw table from projector
Reads the currently selected custom gamma table from the projector. This "raw" table can be plotted and saved, but it cannot be adjusted.

## Plot Menu

### Hide plot menu
Hide plot menu entries. If auto-plot is enabled it will stay enabled.

### Plot
Plot the current gamma curve.
- "p" - Plot at normal speed.
- "p f" - Fast plot.
- "p s" - Slow plot. Can be used to slow down the plot, and make it easier to see which curve is the current curve, if the current plot has many curves on it.

### Clear plot
Clears the plot area

### Plot clip table
Plots a curve that shows how much the input signal is getting clipped.

### Plot contrast
Plots the current curve with a contrast adjustment. Can be used with "Scale ref white brightness from contrast" to see how the contrast control on the projector distorts the gamma curve (e.g. "pa 0; pc; psc 20; bwc 20; p")

### Auto plot
Select plot mode.
- "pa 0" selects manual plot mode.
- "pa -1" plots every change to the gamma table on top of the existing plot.
- "pa 1" clears the plot area and plots every change to the gamma with the old curve in gray. This mode also adds vertical lines for the soft-clip start point, hard-clip point, peak-white and black.

### Plot zoom
Zoom plot area.
- "pz f" shows the full plot area.
- "pz u" zooms in on the upper center area of the current plot area.
- "pz ur" zooms in on the upper right corner of the current plot area, etc.
- "pz o" zooms out one level.

### Plot reference curve
Add or remove a reference curve to plot in the auto-clear plot mode.
- "pr a" adds the current gamma curve.
- "pr r0" replaces the first reference curve with the current gamma curve.
- "pr c" removes all reference curves.
- "pr d0" removes the first reference curve.
