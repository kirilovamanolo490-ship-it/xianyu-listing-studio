"""Preview candidate career templates using disposable copies only."""

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")

import json,shutil
from pathlib import Path
import curate_ppt_visuals as renderer

ROOT=Path(__file__).resolve().parents[1]/'发布记录/2026-10-13_二次整理'
NUMBERS=[371,372,373,375,376,377,378,380,382,383,384,385,388,411,412,419,446,456,458,459,463,465,774,782,473,485,526,559,567,603,608,619,622,743,748,749]
if __name__=='__main__':
    a=json.loads((ROOT/'职业规划内容盘点.json').read_text())
    (ROOT/'ooxml_dossier.json').write_text(json.dumps(a,ensure_ascii=False))
    shutil.copy2(ROOT.parent/'2026-10-13_分类整理/screening-fonts.conf',ROOT/'screening-fonts.conf')
    renderer.ROOT=ROOT;renderer.OUT=ROOT/'内页筛选';renderer.OUT.mkdir(exist_ok=True);renderer.NUMBERS=NUMBERS
    renderer.main()
