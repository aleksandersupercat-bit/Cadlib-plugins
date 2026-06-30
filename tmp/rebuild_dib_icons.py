from PIL import Image
from pathlib import Path
root = Path(r"C:\pdf_ingest\DTMXtest")
src = root / 'Assets' / 'Icons' / 'DTMX' / 'variants'
dst = root / 'DtmxMenuRes' / 'res'
map = {
    'edit_v1_badge.png':'dtmx_edit.ico',
    'explore_v3_corner.png':'dtmx_explore.ico',
    'paths_v1_badge.png':'dtmx_paths.ico',
    'test_v2_strip.png':'dtmx_ping.ico',
}
for s,d in map.items():
    img = Image.open(src / s).convert('RGBA')
    img.save(dst / d, sizes=[(16,16),(24,24),(32,32)], bitmap_format='bmp')
    print(s, '->', d, (dst/d).stat().st_size)
