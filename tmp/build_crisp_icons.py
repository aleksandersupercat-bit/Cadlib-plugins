from pathlib import Path
from PIL import Image, ImageDraw

root = Path(r"C:\pdf_ingest\DTMXtest")
cuix = root / 'tmp' / 'water_icon_extract' / 'cuix'
out = root / 'Assets' / 'Icons' / 'DTMX' / 'variants_crisp'
out.mkdir(parents=True, exist_ok=True)

bases = {
    'edit': 'MStudioPipelineSettings.png',
    'explore': 'MStudioInlineSettings.png',
    'paths': 'Connector.png',
    'test': 'WarningToUse16.png',
}

# crisp, binary-alpha overlays

def force_binary_alpha(img):
    rgba = img.convert('RGBA')
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r,g,b,a = px[x,y]
            px[x,y] = (r,g,b,255 if a >= 128 else 0)
    return rgba


def add_edit(img):
    img = force_binary_alpha(img)
    d = ImageDraw.Draw(img)
    d.rectangle((11,1,15,5), fill=(0,170,255,255))
    d.point((12,2), fill=(255,255,255,255))
    d.point((13,3), fill=(255,255,255,255))
    d.point((14,4), fill=(255,255,255,255))
    return img


def add_explore(img):
    img = force_binary_alpha(img)
    d = ImageDraw.Draw(img)
    d.polygon([(10,0),(15,0),(15,5)], fill=(0,200,140,255))
    d.line((11,1,14,1), fill=(255,255,255,255), width=1)
    d.line((13,1,14,2), fill=(255,255,255,255), width=1)
    return img


def add_paths(img):
    img = force_binary_alpha(img)
    d = ImageDraw.Draw(img)
    d.rectangle((11,1,15,5), fill=(0,170,255,255))
    d.rectangle((12,2,14,4), fill=(255,255,255,255))
    return img


def add_test(img):
    img = force_binary_alpha(img)
    d = ImageDraw.Draw(img)
    d.rectangle((2,11,13,15), fill=(0,110,210,255))
    d.rectangle((4,12,11,14), fill=(255,255,255,255))
    return img

makers = {
    'edit': add_edit,
    'explore': add_explore,
    'paths': add_paths,
    'test': add_test,
}

for key, name in bases.items():
    img = Image.open(cuix / name)
    out_img = makers[key](img)
    out_img.save(out / f'{key}_crisp16.png')
    out_img.resize((32,32), Image.NEAREST).save(out / f'{key}_crisp32.png')
    print('saved', key)
