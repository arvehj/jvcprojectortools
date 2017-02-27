# JVC Projector Tools

Scripts to send commands 2015 model JVC D-ILA Projectors.

## Prerequisites
- Python [3.6](https://www.python.org/downloads/release/python-360/) or [later](https://www.python.org/downloads/) installed
- Network connected JVC projector

## Tools

### jvc_gamma.py
Run to get a menu that lets you generate and load custom gamma curves. Or call load_gamma from the python shell to load other gamma curves.

#### Parameters for "custom hdr_pq" menu entry
- "max brightness" is the peak brightness your projector can reach.
- "reference white" is how bright you want a 100 nit reference white to be. Lowering this value will make the image darker and increasing it will make the image brighter.
- "soft clip start brightness" is the brightness where the curve will stop following the eotf curve and start a soft clip curve.
- "hard clip brightness" is where the soft clip curve ends.
- "clip end slope" moves the angle of the curve at the end point from horizontal (1) to pointing at the soft clip start point (0).
- "soft clip method" selects between a cubic Bézier curve (0) and quadratic Bézier curve (1).
- "soft clip gamma" selects the gamma to draw the soft clip curve in.

Select toggle white in the menu to match the input level setting in the projector settings you plan to use.
