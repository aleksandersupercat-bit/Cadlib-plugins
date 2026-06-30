from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

root = Path(r"C:\pdf_ingest\DTMXtest")
base_dir = root / 'tmp' / 'water_icon_extract' / 'cuix'
out_dir = root / 'Assets' / 'Icons' / 'DTMX' / 'variants'
out_dir.mkdir(parents=True, exist_ok=True)
preview_path = out_dir / 'dtmx_variant_preview.png'

base_files = {
    'edit': 'MS_EDITPIPE32.png',
    'explore': 'MS_EDITVALV32.png',
    'paths': 'MS_PIPE_ROUTE32.png',
    'test': 'MS_WARNING32.png',
}

label_map = {
    'edit': 'Pravka',
    'explore': 'Svoystva',
    'paths': 'Svyazi',
    'test': 'Test',
}

try:
    font = ImageFont.truetype('arial.ttf', 16)
    small_font = ImageFont.truetype('arial.ttf', 12)
    badge_font = ImageFont.truetype('arialbd.ttf', 12)
except Exception:
    font = ImageFont.load_default()
    small_font = ImageFont.load_default()
    badge_font = ImageFont.load_default()


def fit(base):
    img = base.convert('RGBA')
    if img.size != (32, 32):
        img = img.resize((32, 32), Image.LANCZOS)
    return img


def variant1(img):
    img = img.copy()
    d = ImageDraw.Draw(img)
    d.ellipse((20, 0, 31, 11), fill=(0, 168, 255, 255), outline=(255, 255, 255, 230), width=1)
    d.text((23, 1), 'D', font=badge_font, fill=(255, 255, 255, 255))
    return img


def variant2(img):
    img = img.copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 22, 30, 31), radius=4, fill=(14, 92, 175, 235), outline=(185, 230, 255, 255), width=1)
    d.text((8, 23), 'DT', font=small_font, fill=(255, 255, 255, 255))
    return img


def variant3(img):
    img = img.copy()
    glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    pts = [(19, 0), (31, 0), (31, 12)]
    gd.polygon(pts, fill=(0, 205, 160, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(0.6))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=(0, 205, 160, 240), outline=(255, 255, 255, 220))
    d.text((23, 1), '+', font=badge_font, fill=(255, 255, 255, 255))
    return img

variants = [variant1, variant2, variant3]
variant_names = ['v1_badge', 'v2_strip', 'v3_corner']

for key, filename in base_files.items():
    base = fit(Image.open(base_dir / filename))
    for idx, maker in enumerate(variants):
        out = maker(base)
        name = f'{key}_{variant_names[idx]}.png'
        out.save(out_dir / name)
        out.resize((96, 96), Image.NEAREST).save(out_dir / f'{key}_{variant_names[idx]}_96.png')

cols, rows = 3, 4
cell_w, cell_h = 220, 150
sheet = Image.new('RGBA', (cols * cell_w, rows * cell_h), (245, 247, 250, 255))
d = ImageDraw.Draw(sheet)

for r in range(rows):
    for c in range(cols):
        x0, y0 = c * cell_w, r * cell_h
        d.rounded_rectangle((x0 + 8, y0 + 8, x0 + cell_w - 8, y0 + cell_h - 8), radius=16, fill=(255, 255, 255, 255), outline=(210, 218, 230, 255), width=2)

for row_idx, key in enumerate(base_files.keys()):
    for col_idx, vname in enumerate(variant_names):
        img = Image.open(out_dir / f'{key}_{vname}.png').resize((80, 80), Image.NEAREST)
        x0, y0 = col_idx * cell_w, row_idx * cell_h
        sheet.alpha_composite(img, (x0 + 70, y0 + 28))
        title = f"{label_map[key]} / {vname}"
        d.text((x0 + 28, y0 + 116), title, font=small_font, fill=(44, 62, 80, 255))

for col_idx, title in enumerate(['Variant 1', 'Variant 2', 'Variant 3']):
    d.text((col_idx * cell_w + 72, 10), title, font=font, fill=(32, 45, 64, 255))

sheet.save(preview_path)
print('Preview:', preview_path)
for p in sorted(out_dir.glob('*.png')):
    print(p.name)
