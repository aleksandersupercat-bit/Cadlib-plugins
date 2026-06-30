from PIL import Image
from pathlib import Path
root = Path(r"C:\pdf_ingest\DTMXtest")
src = root / 'Assets' / 'Icons' / 'DTMX' / 'ultraclean'
dst = root / 'DtmxMenuRes' / 'res'
map = {
    'edit':'dtmx_edit.ico',
    'explore':'dtmx_explore.ico',
    'paths':'dtmx_paths.ico',
    'test':'dtmx_ping.ico',
}
for key, ico_name in map.items():
    img16 = Image.open(src / f'{key}_16.png').convert('RGBA')
    # build exact multi-size set from prepared files
    sizes = []
    for sz in (16,24,32):
        sizes.append(Image.open(src / f'{key}_{sz}.png').convert('RGBA'))
    # save from 32 image with explicit sizes; bitmap_format makes DIB frames
    sizes[-1].save(dst / ico_name, sizes=[(16,16),(24,24),(32,32)], bitmap_format='bmp')
    print(key, '->', ico_name)
