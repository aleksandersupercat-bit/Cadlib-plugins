from pathlib import Path
from PIL import Image, ImageDraw

root = Path(r"C:\pdf_ingest\DTMXtest")
cuix = root / 'tmp' / 'water_icon_extract' / 'cuix'
out = root / 'Assets' / 'Icons' / 'DTMX' / 'large32'
out.mkdir(parents=True, exist_ok=True)

bases = {
    'edit': 'MS_EDITPIPE32.png',
    'explore': 'MS_EDITVALV32.png',
    'paths': 'MS_PIPE_ROUTE32.png',
    'test': 'MS_WARNING32.png',
}

ACCENT_BLUE = (39,141,233,255)
ACCENT_GREEN = (46,199,150,255)
ACCENT_ORANGE = (255,166,0,255)
ACCENT_RED = (237,83,63,255)
WHITE = (255,255,255,255)


def bin_alpha(img):
    img = img.convert('RGBA')
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r,g,b,a = px[x,y]
            px[x,y] = (r,g,b,255 if a >= 128 else 0)
    return img


def badge(draw, box, color, glyph=''):
    x1,y1,x2,y2 = box
    draw.rounded_rectangle(box, radius=2, fill=color)
    draw.line((x1+1,y1+1,x2-1,y1+1), fill=WHITE, width=1)
    draw.line((x1+1,y1+1,x1+1,y2-1), fill=WHITE, width=1)
    if glyph == 'E':
        draw.line((x1+3,y1+3,x2-3,y1+3), fill=WHITE, width=1)
        draw.line((x1+3,y1+6,x2-5,y1+6), fill=WHITE, width=1)
        draw.line((x1+3,y1+9,x2-3,y1+9), fill=WHITE, width=1)
        draw.line((x1+3,y1+3,x1+3,y1+9), fill=WHITE, width=1)
    elif glyph == 'S':
        draw.line((x1+3,y1+3,x2-3,y1+3), fill=WHITE, width=1)
        draw.line((x1+3,y1+6,x2-4,y1+6), fill=WHITE, width=1)
        draw.line((x1+4,y1+9,x2-3,y1+9), fill=WHITE, width=1)
        draw.point((x1+3,y1+4), fill=WHITE)
        draw.point((x2-3,y1+8), fill=WHITE)
    elif glyph == 'L':
        draw.line((x1+4,y1+3,x1+4,y1+9), fill=WHITE, width=1)
        draw.line((x1+4,y1+9,x2-3,y1+9), fill=WHITE, width=1)
    elif glyph == 'T':
        draw.line((x1+3,y1+3,x2-3,y1+3), fill=WHITE, width=1)
        draw.line((x1+7,y1+3,x1+7,y1+9), fill=WHITE, width=1)


def make_edit(img):
    img = bin_alpha(img)
    d = ImageDraw.Draw(img)
    badge(d, (20,2,30,12), ACCENT_BLUE, 'E')
    return img


def make_explore(img):
    img = bin_alpha(img)
    d = ImageDraw.Draw(img)
    badge(d, (20,2,30,12), ACCENT_GREEN, 'S')
    return img


def make_paths(img):
    img = bin_alpha(img)
    d = ImageDraw.Draw(img)
    badge(d, (20,2,30,12), ACCENT_ORANGE, 'L')
    return img


def make_test(img):
    img = bin_alpha(img)
    d = ImageDraw.Draw(img)
    badge(d, (2,20,12,30), ACCENT_RED, 'T')
    return img

makers = {
    'edit': make_edit,
    'explore': make_explore,
    'paths': make_paths,
    'test': make_test,
}

for key, file in bases.items():
    base = Image.open(cuix / file)
    img32 = makers[key](base)
    img32.save(out / f'{key}_32.png')
    img24 = img32.resize((24,24), Image.LANCZOS)
    img24 = bin_alpha(img24)
    img24.save(out / f'{key}_24.png')
    img16 = img32.resize((16,16), Image.LANCZOS)
    img16 = bin_alpha(img16)
    img16.save(out / f'{key}_16.png')
    print('saved', key)
