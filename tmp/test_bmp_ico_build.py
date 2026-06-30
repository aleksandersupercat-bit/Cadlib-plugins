from PIL import Image
from pathlib import Path
p = Path(r"C:\pdf_ingest\DTMXtest\Assets\Icons\DTMX\variants\edit_v1_badge.png")
out = Path(r"C:\pdf_ingest\DTMXtest\tmp\test_bmp_ico.ico")
out.parent.mkdir(parents=True, exist_ok=True)
img = Image.open(p).convert('RGBA')
img.save(out, sizes=[(16,16),(24,24),(32,32)], bitmap_format='bmp')
print(out.exists(), out)
print(out.stat().st_size if out.exists() else 'missing')
