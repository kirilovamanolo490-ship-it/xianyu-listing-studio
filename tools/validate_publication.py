"""Read-only checks for the public documentation and unchanged case assets."""
from pathlib import Path
import ast
import hashlib
import json
import re
from urllib.parse import unquote, urlsplit
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', 'apps', '__pycache__', 'node_modules', 'local-data', 'output'}

def public_files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and not any(x in EXCLUDED for x in p.relative_to(ROOT).parts))

def main():
    errors = []
    image_count = 0
    links = 0
    for slug in ('career-planning', 'innovation-startup'):
        case = ROOT / 'cases' / slug
        manifest = json.loads((case / 'manifest.json').read_text())
        rows = manifest['images']
        if [r['position'] for r in rows] != list(range(1, 10)):
            errors.append(f'{slug}: expected exactly nine ordered images')
        expected_files = {r['file'] for r in rows}
        if {str(p.relative_to(case)) for p in (case / 'images').iterdir()} != expected_files:
            errors.append(f'{slug}: image directory differs from manifest')
        for row in rows:
            p = case / row['file']
            data = p.read_bytes()
            if hashlib.sha256(data).hexdigest() != row['sha256'] or len(data) != row['bytes']:
                errors.append(f'{p.relative_to(ROOT)}: checksum or byte count differs')
            with Image.open(p) as image:
                expected_size = (1800, 1800) if row['position'] == 1 else (1800, 2400)
                if image.size != expected_size or image.size != (row['width'], row['height']) or image.format != 'JPEG':
                    errors.append(f'{p.relative_to(ROOT)}: dimensions or format differ')
                image.verify()
            image_count += 1
        if manifest['publication_status'] != 'materials_ready_not_verified_live':
            errors.append(f'{slug}: status needs a new evidence review')
    forbidden_names = {'admin-credentials.json', 'browser-state.json', '.secret_encryption.key'}
    forbidden_suffixes = {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.ppt', '.pptx', '.pptm', '.ppsx', '.zip'}
    sensitive_patterns = [r'gh[pousr]_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{30,}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', r'https?://pan\.quark\.cn/s/[A-Za-z0-9]+', r'/[U]sers/[^/\s]+/']
    files = public_files()
    for p in files:
        rel = p.relative_to(ROOT)
        if p.name in forbidden_names or p.suffix.lower() in forbidden_suffixes or '-private.' in p.name:
            errors.append(f'{rel}: disallowed private/source file')
        if p.suffix == '.jpg':
            continue
        try:
            text = p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            errors.append(f'{rel}: unexpected binary file')
            continue
        if p.suffix == '.py':
            ast.parse(text, filename=str(rel))
        for pattern in sensitive_patterns:
            if re.search(pattern, text):
                errors.append(f'{rel}: potentially private literal requires review')
        if p.suffix == '.md':
            targets = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text)
            targets += re.findall(r'(?:src|href)="([^"]+)"', text)
            for target in targets:
                target = target.split(' "', 1)[0].strip('<>')
                parts = urlsplit(target)
                if parts.scheme or target.startswith('#'):
                    continue
                dest = (p.parent / unquote(parts.path)).resolve()
                if not dest.is_relative_to(ROOT) or not dest.exists():
                    errors.append(f'{rel}: missing local target {target}')
                links += 1
    report = {'status': 'passed' if not errors else 'failed', 'files_checked': len(files), 'images_checked': image_count, 'local_links_checked': links, 'errors': errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
