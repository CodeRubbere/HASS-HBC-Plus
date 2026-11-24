#!/usr/bin/env python3
"""List what a release changed for users, and refuse a changed part without a new version (HBC+ v1.3).

  python3 tools/release-files.py [--from TAG] [--to REF] [--markdown]

--from defaults to the newest tag before --to (default HEAD). Prints the user-facing files that changed,
grouped by part, with the version each part had and has now. Exit code 1 when a part changed but kept its
version, or a part's version went up without a change in its files (a bump by mistake is harmless but
confusing, so it is listed as a warning only). --markdown prints the list as release notes
('Files to copy'). The GitHub Action uses it for the draft release.
"""
import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
import io

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hbc_versions import key, part_of, parts  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*a):
    return subprocess.run(['git', '-C', ROOT, *a], check=True, capture_output=True, text=True).stdout


def parts_at(ref):
    """{part: version} of a git ref; empty for a release older than per-part versions."""
    with tempfile.TemporaryDirectory() as tmp:
        data = subprocess.run(['git', '-C', ROOT, 'archive', ref, 'packages', 'node-red', 'dashboards'],
                              check=True, capture_output=True).stdout
        tarfile.open(fileobj=io.BytesIO(data)).extractall(tmp)
        try:
            return parts(tmp)
        except Exception:
            return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--from', dest='frm')
    ap.add_argument('--to', default='HEAD')
    ap.add_argument('--markdown', action='store_true')
    a = ap.parse_args()
    frm = a.frm
    if not frm:
        try:
            frm = git('describe', '--tags', '--abbrev=0', f'{a.to}^').strip()
        except subprocess.CalledProcessError:
            print('### Files to copy\n\nFirst release: copy every file.' if a.markdown
                  else f'No tag before {a.to}: nothing to compare with.')
            return
    changed = [l for l in git('diff', '--name-only', frm, a.to).splitlines() if part_of(l)]
    before, now = parts_at(frm), parts_at(a.to)
    groups = {}
    for f in changed:
        groups.setdefault(part_of(f), []).append(f)
    errors, warnings = [], []
    for part, files in groups.items():
        if part in now and now[part] and before.get(part) and key(now[part]) <= key(before[part]):
            errors.append(f'{part} changed ({", ".join(files)}) but kept version {now[part]}: '
                          f'run tools/set-version.py <new version> {part}')
    for part, v in now.items():
        if v and before.get(part) and key(v) > key(before[part]) and part not in groups:
            warnings.append(f'{part}: version {before[part]} -> {v} without a change in its files')
    if a.markdown:
        newest = max((x for x in now.values() if x), key=key, default='?')
        print(f'### Files to copy ({frm} → v{newest})\n')
        if not groups:
            print('No files for Home Assistant or Node-RED changed.')
        for part, files in sorted(groups.items(), key=lambda i: i[0]):
            v = f' — {before.get(part) or "new"} → {now.get(part)}' if part in now else ''
            what = {'flows': 'Node-RED flows: delete every HBC+ tab, import `node-red/hbc-plus-all-flows.json`, deploy',
                    'dashboard': 'Dashboard: paste `dashboards/hbc_plus.yaml` again',
                    'www': 'Logo: copy `www/hbc-plus/` again'}.get(part)
            if what:
                print(f'- {what}{v}')
            else:
                print(f'- `{files[0]}`{v}')
    else:
        print(f'Changed for users since {frm}:')
        for part, files in sorted(groups.items(), key=lambda i: i[0]):
            print(f'  {part}: {before.get(part) or "-"} -> {now.get(part) or "-"}   ({len(files)} file(s))')
        for w in warnings:
            print('  warning: ' + w)
    if errors:
        print('\nNot consistent:', file=sys.stderr)
        for e in errors:
            print('  - ' + e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
