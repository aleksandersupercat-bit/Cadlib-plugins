from PIL import Image
from pathlib import Path
root = Path(r"C:\pdf_ingest\DTMXtest")
src = root / 'Assets' / 'Icons' / 'DTMX' / 'ultraclean'
dst = root / 'DtmxMenuRes' / 'res'
map = {
    'edit_16.png':'dtmx_edit.ico',
    'explore_16.png':'dtmx_explore.ico',
    'paths_16.png':'dtmx_paths.ico',
    'test_16.png':'dtmx_ping.ico',
}
for s,d in map.items():
    img = Image.open(src / s).convert('RGBA')
    # single-frame 16x16 DIB ICO, mirroring SDK style
    img.save(dst / d, sizes=[(16,16)], bitmap_format='bmp')
    print(s, '->', d)
