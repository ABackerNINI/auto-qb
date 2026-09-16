> 版本: 12.3.0 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Opening Images with Different File Inputs

Source: https://github.com/python-pillow/pillow/blob/main/docs/reference/open_files.rst

Demonstrates equivalent ways to open an image file using Pillow with a filename, a Path object, a file-like object, or a BytesIO object.

```python
from PIL import Image
import io
import pathlib

with Image.open("test.jpg") as im:
    ...
```

```python
with Image.open(pathlib.Path("test.jpg")) as im2:
    ...
```

```python
with open("test.jpg", "rb") as f:
    im3 = Image.open(f)
    ...
```

```python
with open("test.jpg", "rb") as f:
    im4 = Image.open(io.BytesIO(f.read()))
    ...
```

--------------------------------

### Convert image modes

Source: https://github.com/python-pillow/pillow/blob/main/docs/handbook/tutorial.rst

Change pixel representations using the convert method. Direct conversion is supported between most modes and 'L' or 'RGB'.

```python
from PIL import Image

with Image.open("hopper.ppm") as im:
    im = im.convert("L")
```

--------------------------------

### Combine translucent color with RGB image using RGBA mode

Source: https://github.com/python-pillow/pillow/blob/main/docs/reference/ImageDraw.rst

Shows how to combine a translucent color with an RGB image by initializing ImageDraw with 'RGBA' mode. This allows the alpha channel of the drawing color to affect the resulting pixel color.

```python
from PIL import Image, ImageDraw
im = Image.new("RGB", (1, 1), (255, 0, 0))
d = ImageDraw.Draw(im, "RGBA")
d.rectangle((0, 0, 1, 1), (0, 255, 0, 127))
assert im.getpixel((0, 0)) == (128, 127, 0)
```

--------------------------------

### Create image thumbnails

Source: https://github.com/python-pillow/pillow/blob/main/docs/reference/Image.rst

Iterates through all JPEG files in the current directory and saves a 128x128 thumbnail for each while preserving aspect ratio.

```python
from PIL import Image
import glob, os

size = 128, 128

for infile in glob.glob("*.jpg"):
    file, ext = os.path.splitext(infile)
    with Image.open(infile) as im:
        im.thumbnail(size)
        im.save(file + ".thumbnail", "JPEG")
```

--------------------------------

### Thumbnail with LANCZOS on RGBA

Source: https://github.com/python-pillow/pillow/blob/main/src/PIL/IcoImagePlugin.py

Resizes an RGBA image in-place to fit within the given size while preserving aspect ratio, using LANCZOS resampling. This is from ICO saving code where frames are thumbnailed to a requested icon size.

```python
frame = provided_im.copy()
frame.thumbnail(size, Image.Resampling.LANCZOS, reducing_gap=None)
```