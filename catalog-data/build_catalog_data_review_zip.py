"""Build the portable catalog-data review archive with deterministic metadata."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'catalog-data'
OUTPUT = ROOT / 'catalog-data-v1.0-review.zip'
EXCLUDED = {'__pycache__'}

files = [p for p in DATA.rglob('*') if p.is_file() and not any(part in EXCLUDED for part in p.parts)]
with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(files, key=lambda p: p.as_posix()):
        relative = path.relative_to(ROOT).as_posix()
        info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, path.read_bytes(), compresslevel=9)
print(f'{OUTPUT.name}: {len(files)} files')
