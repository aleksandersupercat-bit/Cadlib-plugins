from PIL import Image
from pathlib import Path
root = Path(r"C:\pdf_ingest\DTMXtest")
src = root / 'Assets' / 'Icons' / 'DTMX' / 'large32'
dst = root / 'DtmxMenuRes' / 'res'
map = {
    'edit':'dtmx_edit.ico',
    'explore':'dtmx_explore.ico',
    'paths':'dtmx_paths.ico',
    'test':'dtmx_ping.ico',
}
for key, ico_name in map.items():
    img32 = Image.open(src / f'{key}_32.png').convert('RGBA')
    img32.save(dst / ico_name, sizes=[(16,16),(24,24),(32,32)], bitmap_format='bmp')
    print(key, '->', ico_name)
