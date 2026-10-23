"""Build a deterministic production archive for RK17-0105..0132."""
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'production/RK17-0105_0132_READY'
OUTPUT=ROOT/'production/RK17-0105_0132_READY.zip'
files=sorted((p for p in SOURCE.rglob('*') if p.is_file()),key=lambda p:p.as_posix())
with zipfile.ZipFile(OUTPUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for path in files:
        info=zipfile.ZipInfo((Path('RK17-0105_0132_READY')/path.relative_to(SOURCE)).as_posix(),date_time=(1980,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644<<16
        archive.writestr(info,path.read_bytes(),compresslevel=9)
print(f'{OUTPUT.name}: {len(files)} files')
