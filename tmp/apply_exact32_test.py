from PIL import Image
from pathlib import Path
root = Path(r"C:\pdf_ingest\DTMXtest")
src = root / 'tmp' / 'water_icon_extract' / 'cuix'
dst = root / 'DtmxMenuRes' / 'res'
map = {
    'MS_EDITPIPE32.png':'dtmx_edit.ico',
    'MS_EDITVALV32.png':'dtmx_explore.ico',
    'MS_PIPE_ROUTE32.png':'dtmx_paths.ico',
    'MS_WARNING32.png':'dtmx_ping.ico',
}
for s,d in map.items():
    img = Image.open(src / s).convert('RGBA')
    img.save(dst / d, sizes=[(32,32)], bitmap_format='bmp')
    print(s, '->', d)
