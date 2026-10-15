"""Resumable upload of the two authorized PPT folders to the user's Quark drive.

Protocol reference: OpenListTeam/OpenList drivers/quark_uc (read 2026-10-11).
The existing account adapter is reused read-only; no credentials are logged.
All writes are constrained to the dedicated 商品发布/PPT资料 directory.
"""
from __future__ import annotations

# Archived workflow: opt in explicitly after reviewing its inputs and side effects.
if __import__("os").environ.get("XIANYU_ENABLE_LEGACY_WORKFLOWS") != "1":
    raise SystemExit("Legacy workflow disabled; set XIANYU_ENABLE_LEGACY_WORKFLOWS=1 only after review.")
import os


import argparse
import base64
import concurrent.futures
import hashlib
import json
import mimetypes
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import formatdate
from pathlib import Path
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.environ.get('XIANYU_LEGACY_PATH_QUARK_PPT_TRANSFER_1', '/path/to/configure'))
from xpan_auto.quark_adapter import QuarkAdapter, QuarkAPIError

ROOT = Path(os.environ.get('XIANYU_LEGACY_PATH_QUARK_PPT_TRANSFER_2', '/path/to/configure'))
RECORD = ROOT / '发布记录/2026-10-11_夸克首次入库'
AUTH = Path(os.environ.get('XIANYU_LEGACY_PATH_QUARK_PPT_TRANSFER_3', '/path/to/configure'))
CLOUD_ROOT = '/商品发布/PPT资料'
OSS_AGENT = 'aliyun-sdk-js/6.6.1 Chrome 98.0.4758.80 on Windows 10 64-bit'
MIME = {'.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.ppsx': 'application/vnd.openxmlformats-officedocument.presentationml.slideshow',
        '.pptm': 'application/vnd.ms-powerpoint.presentation.macroEnabled.12'}


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')


def atomic_json(path, data):
    temp = Path(str(path) + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temp.replace(path)


class Transfer:
    def __init__(self):
        RECORD.mkdir(parents=True, exist_ok=True)
        self.q = QuarkAdapter(cookie_file=AUTH, timeout=35, read_retries=2, min_interval=0)
        self.lock = threading.RLock()
        self.rate_lock = threading.Lock()
        self.last_request = 0.0
        self.folder_file = RECORD / '云盘目录映射.json'
        self.folders = json.loads(self.folder_file.read_text()) if self.folder_file.exists() else {}
        self.folders.setdefault('/', '0')
        self.file_cache = {}
        self.logfile = RECORD / '传输日志.jsonl'
        self.known = {}
        if self.logfile.exists():
            for line in self.logfile.read_text().splitlines():
                row = json.loads(line)
                if row.get('status') in ('verified', 'uploaded'):
                    self.known[row['cloud_path']] = row
        self.stop = threading.Event()

    def req(self, method, endpoint, payload=None, params=None):
        with self.rate_lock:
            remaining = 0.20 - (time.monotonic() - self.last_request)
            if remaining > 0:
                time.sleep(remaining)
            self.last_request = time.monotonic()
        return self.q._request(method, '/1/clouddrive' + endpoint, payload=payload,
                               params=params, mutation=method != 'GET')

    def list_files(self, fid):
        result = []
        page = 1
        while True:
            res = self.req('GET', '/file/sort', params={'pdir_fid': fid, '_page': page,
                '_size': 100, '_fetch_total': 1, '_fetch_sub_dirs': 1,
                '_sort': 'file_type:asc,file_name:asc'})
            part = res.get('data', {}).get('list', [])
            result.extend(part)
            total = int(res.get('metadata', {}).get('_total', len(result)))
            if not part or len(result) >= total:
                return result
            page += 1

    def folder(self, cloud_path):
        cloud_path = '/' + cloud_path.strip('/')
        if not (cloud_path == '/商品发布' or cloud_path == CLOUD_ROOT or cloud_path.startswith(CLOUD_ROOT + '/')):
            raise ValueError('Folder outside authorized scope')
        with self.lock:
            if cloud_path in self.folders:
                return self.folders[cloud_path]
            parent = str(Path(cloud_path).parent)
            parent_id = self.folders.get(parent) or self.folder(parent)
            name = Path(cloud_path).name
            existing = [x for x in self.list_files(parent_id) if x.get('dir') and x['file_name'] == name]
            if len(existing) > 1:
                raise RuntimeError('Ambiguous folder: ' + cloud_path)
            if existing:
                fid = existing[0]['fid']
            else:
                res = self.req('POST', '/file', payload={'pdir_fid': parent_id,
                    'file_name': name, 'dir_path': '', 'dir_init_lock': False})
                fid = res.get('data', {}).get('fid')
                if not fid:
                    raise RuntimeError('Folder create did not return fid')
            self.folders[cloud_path] = fid
            atomic_json(self.folder_file, self.folders)
            return fid

    def append(self, row):
        with self.lock:
            with self.logfile.open('a') as f:
                f.write(json.dumps({'time': now(), **row}, ensure_ascii=False) + '\n')
            if row.get('status') in ('verified', 'uploaded'):
                self.known[row['cloud_path']] = row

    def verify(self, fid, filename, row, *, cached=False):
        if cached:
            with self.lock:
                if fid not in self.file_cache:
                    self.file_cache[fid] = self.list_files(fid)
                files = self.file_cache[fid]
        else:
            files = self.list_files(fid)
        matches = [x for x in files if not x.get('dir') and x.get('file_name') == filename]
        if len(matches) != 1:
            return None
        x = matches[0]
        if int(x.get('size', -1)) != int(row['bytes']):
            raise RuntimeError('Existing file has different size; refusing overwrite')
        # Quark's download metadata md5 is not the file-content MD5. A sample
        # was downloaded and proved byte-identical despite that field differing.
        return {'fid': x['fid'], 'size_verified': True,
                'remote_md5': x.get('md5'), 'remote_sha1': x.get('sha1')}

    def oss_request(self, method, pre, mime, body, params, *, md5=None, callback=None):
        date = formatdate(usegmt=True)
        oss_headers = {'x-oss-date': date, 'x-oss-user-agent': OSS_AGENT}
        if callback:
            oss_headers['x-oss-callback'] = callback
        resource = '/' + pre['bucket'] + '/' + pre['obj_key']
        resource += '?' + '&'.join(k + '=' + str(v) for k, v in sorted(params.items()))
        canonical = ''.join(k + ':' + v + '\n' for k, v in sorted(oss_headers.items()))
        auth_meta = method + '\n' + (md5 or '') + '\n' + mime + '\n' + date + '\n' + canonical + resource
        auth = self.req('POST', '/file/upload/auth', payload={'auth_info': pre['auth_info'],
            'auth_meta': auth_meta, 'task_id': pre['task_id']})['data']['auth_key']
        host = urlsplit(pre['upload_url']).hostname
        if not host or not (host.endswith('.aliyuncs.com') or host.endswith('.quark.cn')):
            raise RuntimeError('Unexpected upload destination domain')
        headers = {'Authorization': auth, 'Content-Type': mime,
                   'Referer': 'https://pan.quark.cn/', **oss_headers}
        if md5:
            headers['Content-MD5'] = md5
        url = 'https://' + pre['bucket'] + '.' + host + '/' + quote(pre['obj_key'], safe='/')
        # Cookie-bearing account headers must never be sent to object storage.
        response = requests.request(method, url, params=params, headers=headers,
                                    data=body, timeout=(20, 180), allow_redirects=False)
        if response.status_code != 200:
            try:
                code = ET.fromstring(response.content).findtext('Code')
            except Exception:
                code = 'unknown'
            raise RuntimeError(f'Object upload HTTP {response.status_code}; code={code}')
        return response

    def upload(self, row, cloud_path, *, phase, rapid_only=False, defer_verify=False):
        if self.stop.is_set():
            return {'status': 'stopped'}
        source = Path(row['source_path'])
        stat = source.stat()
        if stat.st_size != int(row['bytes']) or (row.get('mtime_ns') and stat.st_mtime_ns != int(row['mtime_ns'])):
            raise RuntimeError('Source changed since manifest: ' + str(source))
        parent = self.folder(str(Path(cloud_path).parent))
        filename = Path(cloud_path).name
        previous = self.known.get(cloud_path)
        if previous and previous.get('sha256') == row['sha256']:
            return {**previous, 'resumed': True}
        verified = self.verify(parent, filename, row, cached=defer_verify)
        mode = 'already_present'
        if not verified:
            mime = MIME.get(source.suffix.lower(), mimetypes.guess_type(source.name)[0] or 'application/octet-stream')
            pre_res = self.req('POST', '/file/upload/pre', payload={
                'ccp_hash_update': True, 'dir_name': '', 'file_name': filename,
                'format_type': mime, 'l_created_at': int(stat.st_ctime * 1000),
                'l_updated_at': int(stat.st_mtime * 1000), 'pdir_fid': parent, 'size': stat.st_size})
            pre = pre_res['data']
            hashed = self.req('POST', '/file/update/hash', payload={
                'md5': row['md5'], 'sha1': row['sha1'], 'task_id': pre['task_id']})
            mode = 'rapid' if hashed.get('data', {}).get('finish') else 'multipart'
            if mode == 'multipart':
                if rapid_only:
                    result = {'phase': phase, 'status': 'needs_bytes', 'cloud_path': cloud_path,
                              'source_path': str(source), 'sha256': row['sha256']}
                    self.append(result)
                    return result
                part_size = int(pre_res['metadata']['part_size'])
                etags = []
                with source.open('rb') as f:
                    part = 1
                    while block := f.read(part_size):
                        response = self.oss_request('PUT', pre, mime, block,
                            {'partNumber': part, 'uploadId': pre['upload_id']})
                        etags.append(response.headers['ETag'])
                        part += 1
                xml = ET.Element('CompleteMultipartUpload')
                for i, etag in enumerate(etags, 1):
                    child = ET.SubElement(xml, 'Part')
                    ET.SubElement(child, 'PartNumber').text = str(i)
                    ET.SubElement(child, 'ETag').text = etag
                body = ET.tostring(xml, encoding='utf-8', xml_declaration=True)
                digest = base64.b64encode(hashlib.md5(body).digest()).decode()
                callback = base64.b64encode(json.dumps(pre['callback'], separators=(',', ':')).encode()).decode()
                self.oss_request('POST', pre, 'application/xml', body, {'uploadId': pre['upload_id']},
                                 md5=digest, callback=callback)
                self.req('POST', '/file/upload/finish', payload={'obj_key': pre['obj_key'], 'task_id': pre['task_id']})
            if defer_verify:
                result = {'phase': phase, 'status': 'uploaded', 'cloud_path': cloud_path,
                          'source_path': str(source), 'sha256': row['sha256'],
                          'bytes': int(row['bytes']), 'mode': mode,
                          'fid': hashed.get('data', {}).get('fid') or pre.get('fid')}
                self.append(result)
                return result
            for attempt in range(4):
                verified = self.verify(parent, filename, row)
                if verified:
                    break
                time.sleep(0.7 * (attempt + 1))
            if not verified:
                raise RuntimeError('Upload returned but file not present in target folder')
        result = {'phase': phase, 'status': 'verified', 'cloud_path': cloud_path,
                  'source_path': str(source), 'sha256': row['sha256'], 'bytes': int(row['bytes']),
                  'mode': mode, **verified}
        self.append(result)
        return result

    def audit(self, rows, key, phase):
        grouped = {}
        for row in rows:
            grouped.setdefault(str(Path(row[key]).parent), []).append(row)
        checked = []
        errors = []
        for folder, expected in grouped.items():
            files = self.list_files(self.folder(folder))
            by_name = {}
            for item in files:
                if not item.get('dir'):
                    by_name.setdefault(item['file_name'], []).append(item)
            for row in expected:
                name = Path(row[key]).name
                matches = by_name.get(name, [])
                if len(matches) != 1 or int(matches[0].get('size', -1)) != int(row['bytes']):
                    errors.append({'cloud_path': row[key], 'error': 'missing, duplicate or size mismatch'})
                    continue
                checked.append((row, matches[0]))
        # Directory metadata proves location, unique name, size and file ID.
        # The web download endpoint rejects some large files (23018); it is
        # neither needed for this comparison nor a content-hash verifier.
        # Full byte verification is performed separately on downloadable samples.
        for row, item in checked:
            if item.get('ban'):
                errors.append({'cloud_path': row[key], 'error': 'provider marks file unavailable'})
                continue
            previous = self.known.get(row[key], {})
            self.append({'phase': phase, 'status': 'verified', 'cloud_path': row[key],
                'source_path': row['source_path'], 'sha256': row['sha256'],
                'bytes': int(row['bytes']), 'fid': item['fid'], 'size_verified': True,
                'verification': 'remote_name_size_and_fid',
                'mode': previous.get('mode', 'existing')})
        report = {'checked_at': now(), 'phase': phase, 'expected_files': len(rows),
                  'verified_files': len(rows) - len(errors),
                  'errors': errors, 'complete': not errors,
                  'method': '逐目录文件名、字节数和文件ID对照，并检查云端是否标记不可用；本地MD5与SHA1用于上传校验。此核验不等于全量下载后逐字节比对，全文回读SHA256抽查另记。'}
        atomic_json(RECORD / (phase + '_逐文件核验.json'), report)
        return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, default=RECORD / '本地上传清单.json')
    p.add_argument('--phase', choices=['archive', 'delivery'], default='archive')
    p.add_argument('--limit', type=int)
    p.add_argument('--workers', type=int, default=2)
    args = p.parse_args()
    if args.phase == 'delivery':
        archive_report = RECORD / 'archive_逐文件核验.json'
        report = json.loads(archive_report.read_text()) if archive_report.exists() else {}
        if not report.get('complete') or report.get('expected_files') != 2533:
            raise RuntimeError('源库 2533 个演示文件尚未全部核验，按用户指定顺序暂不整理正式交付目录。')
    raw = json.loads(args.manifest.read_text())
    rows = raw if isinstance(raw, list) else raw.get('files', raw.get('items', []))
    if not rows:
        raise ValueError('Empty upload manifest')
    key = 'archive_cloud_path' if args.phase == 'archive' else 'delivery_cloud_path'
    rows = [r for r in rows if r.get(key)]
    if args.limit:
        rows = rows[:args.limit]
    t = Transfer()
    counts = {'total': len(rows), 'uploaded': 0, 'verified': 0, 'failed': 0, 'rapid': 0, 'multipart': 0, 'resumed': 0}
    started = now()
    status_file = RECORD / (args.phase + '_进度.json')

    def worker(row):
        try:
            return t.upload(row, row[key], phase=args.phase, defer_verify=True)
        except Exception as exc:
            # Avoid serializing request/response bodies or signed upload URLs.
            message = str(exc)[:250] if isinstance(exc, (RuntimeError, ValueError, QuarkAPIError)) else type(exc).__name__
            result = {'phase': args.phase, 'status': 'failed', 'cloud_path': row[key],
                      'source_path': row['source_path'], 'error': message}
            t.append(result)
            return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(worker, row): row for row in rows}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            status = result['status']
            if status in ('verified', 'uploaded'):
                counts['uploaded'] += 1
                if status == 'verified':
                    counts['verified'] += 1
                if result.get('resumed'):
                    counts['resumed'] += 1
                elif result.get('mode') in counts:
                    counts[result['mode']] += 1
            elif status == 'failed':
                counts['failed'] += 1
                print(json.dumps({'error': result}, ensure_ascii=False), flush=True)
                if counts['failed'] >= 5:
                    t.stop.set()
                    for f in futures:
                        f.cancel()
                    break
            atomic_json(status_file, {'phase': args.phase, 'started': started, 'updated': now(), **counts})
            if (counts['uploaded'] + counts['failed']) % 25 == 0:
                print(json.dumps(counts), flush=True)
    if not counts['failed'] and counts['uploaded'] == len(rows):
        time.sleep(2)
        audit = t.audit(rows, key, args.phase)
        counts['verified'] = audit['verified_files']
        counts['failed'] = len(audit['errors'])
    atomic_json(status_file, {'phase': args.phase, 'started': started, 'updated': now(),
                'complete': counts['verified'] == len(rows), **counts})
    print(json.dumps(counts), flush=True)


if __name__ == '__main__':
    main()
