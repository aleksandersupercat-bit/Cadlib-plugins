from pathlib import Path
from PIL import Image, ImageDraw

root = Path(r"C:\pdf_ingest\DTMXtest")
cuix = root / 'tmp' / 'water_icon_extract' / 'cuix'
out = root / 'Assets' / 'Icons' / 'DTMX' / 'ultraclean'
out.mkdir(parents=True, exist_ok=True)

# base 16x16 palette-like icons from WATER
base_names = {
    'edit': 'MStudioPipelineSettings.png',
    'explore': 'MStudioInlineSettings.png',
    'paths': 'Connector.png',
    'test': 'WarningToUse16.png',
}

# palette close to native UI accents
ACCENT_BLUE = (39, 141, 233, 255)
ACCENT_GREEN = (46, 199, 150, 255)
ACCENT_ORANGE = (255, 166, 0, 255)
ACCENT_RED = (237, 83, 63, 255)
WHITE = (255,255,255,255)


def binarize_alpha(img):
    img = img.convert('RGBA')
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r,g,b,a = px[x,y]
            px[x,y] = (r,g,b,255 if a >= 128 else 0)
    return img


def add_corner_square(img, color, letter=None):
    img = binarize_alpha(img)
    d = ImageDraw.Draw(img)
    d.rectangle((11, 1, 15, 5), fill=color)
    d.line((11,1,15,1), fill=WHITE)
    d.line((11,1,11,5), fill=WHITE)
    if letter == 'E':
        d.point((12,2), fill=WHITE); d.point((13,2), fill=WHITE); d.point((14,2), fill=WHITE)
        d.point((12,3), fill=WHITE); d.point((13,3), fill=WHITE)
        d.point((12,4), fill=WHITE); d.point((13,4), fill=WHITE); d.point((14,4), fill=WHITE)
    elif letter == 'S':
        d.point((12,2), fill=WHITE); d.point((13,2), fill=WHITE); d.point((14,2), fill=WHITE)
        d.point((12,3), fill=WHITE); d.point((13,3), fill=WHITE)
        d.point((13,4), fill=WHITE); d.point((14,4), fill=WHITE)
    elif letter == 'L':
        d.point((12,2), fill=WHITE); d.point((12,3), fill=WHITE); d.point((12,4), fill=WHITE); d.point((13,4), fill=WHITE); d.point((14,4), fill=WHITE)
    elif letter == 'T':
        d.point((12,2), fill=WHITE); d.point((13,2), fill=WHITE); d.point((14,2), fill=WHITE); d.point((13,3), fill=WHITE); d.point((13,4), fill=WHITE)
    return img


def add_bottom_bar(img, color, two=False):
    img = binarize_alpha(img)
    d = ImageDraw.Draw(img)
    d.rectangle((2, 11, 13, 15), fill=color)
    d.line((2,11,13,11), fill=WHITE)
    d.line((2,11,2,15), fill=WHITE)
    if two:
        d.point((5,12), fill=WHITE); d.point((6,12), fill=WHITE)
        d.point((5,13), fill=WHITE); d.point((8,12), fill=WHITE); d.point((9,12), fill=WHITE)
        d.point((8,13), fill=WHITE)
    else:
        d.point((5,12), fill=WHITE); d.point((6,12), fill=WHITE); d.point((7,12), fill=WHITE)
        d.point((6,13), fill=WHITE)
    return img

# ultra-clean set: one simple marker per icon
recipes = {
    'edit': lambda img: add_corner_square(img, ACCENT_BLUE, 'E'),
    'explore': lambda img: add_corner_square(img, ACCENT_GREEN, 'S'),
    'paths': lambda img: add_corner_square(img, ACCENT_ORANGE, 'L'),
    'test': lambda img: add_bottom_bar(img, ACCENT_RED, two=False),
}

for key, file in base_names.items():
    base = Image.open(cuix / file)
    img16 = recipes[key](base)
    img16.save(out / f'{key}_16.png')
    img24 = img16.resize((24,24), Image.NEAREST)
    img24.save(out / f'{key}_24.png')
    img32 = img16.resize((32,32), Image.NEAREST)
    img32.save(out / f'{key}_32.png')
    print('saved', key)
