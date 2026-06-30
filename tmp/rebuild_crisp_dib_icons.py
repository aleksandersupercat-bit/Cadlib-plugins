from PIL import Image
from pathlib import Path
root = Path(r"C:\pdf_ingest\DTMXtest")
src = root / 'Assets' / 'Icons' / 'DTMX' / 'variants_crisp'
dst = root / 'DtmxMenuRes' / 'res'
map = {
    'edit_crisp16.png':'dtmx_edit.ico',
    'explore_crisp16.png':'dtmx_explore.ico',
    'paths_crisp16.png':'dtmx_paths.ico',
    'test_crisp16.png':'dtmx_ping.ico',
}
for s,d in map.items():
    img = Image.open(src / s).convert('RGBA')
    img.save(dst / d, sizes=[(16,16),(24,24),(32,32)], bitmap_format='bmp')
    print(s, '->', d)
