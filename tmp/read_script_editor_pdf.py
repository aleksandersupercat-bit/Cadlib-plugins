from pathlib import Path
pdf = Path(r"C:\Users\atsarkov\Desktop\ModelStudio\Редактор скриптов.pdf")
try:
    from pypdf import PdfReader
except Exception as e:
    print('IMPORT_ERROR', e)
    raise SystemExit(0)
reader = PdfReader(str(pdf))
for i, p in enumerate(reader.pages[:30]):
    try:
        t = p.extract_text() or ''
    except Exception:
        t = ''
    low = t.lower()
    if any(k in low for k in ['c#','vb.net','visual studio','.net','scripted','редактор скриптов']):
        print(f'--- PAGE {i+1} ---')
        print(t[:4000])
