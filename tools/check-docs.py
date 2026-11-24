#!/usr/bin/env python3
"""Check that the English and the Dutch user guide are in step, and that the CHANGELOG has the release
(HBC+ v1.3).

  python3 tools/check-docs.py [repo folder]

It cannot judge a translation; it catches a change made in one guide only:
  - the same headings, level by level, in the same order
  - the same number of bullets and numbered steps under each heading
  - the same tables, with the same number of rows
  - a CHANGELOG entry '## [X.Y.Z]' for the version in versions.json
Exit code 0 = in step, 1 = not (every difference is listed, with the line in each guide).
"""
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hbc_versions import manifest, read  # noqa: E402

GUIDES = ('docs/user-guide.en.md', 'docs/gebruikershandleiding.nl.md')


def outline(path):
    """[(heading level, heading text, line, bullets, steps, [table rows])] per section."""
    out, cur, fence = [], None, False
    table = None
    for no, line in enumerate(read(path).split('\n'), 1):
        if line.startswith('```'):
            fence = not fence
            continue
        if fence:
            continue
        m = re.match(r'^(#{1,6}) (.*)', line)
        if m:
            cur = {'level': len(m.group(1)), 'title': m.group(2).strip(), 'line': no,
                   'bullets': 0, 'steps': 0, 'tables': []}
            out.append(cur)
            table = None
            continue
        if cur is None:
            continue
        if line.startswith('|'):
            if table is None:
                table = 0
                cur['tables'].append(0)
            if not re.match(r'^\|[\s:|-]+\|?\s*$', line):
                cur['tables'][-1] += 1
            continue
        table = None
        if re.match(r'^\s*[-*] ', line):
            cur['bullets'] += 1
        elif re.match(r'^\s*\d+\. ', line):
            cur['steps'] += 1
    return out


def check(root):
    en, nl = (outline(os.path.join(root, g)) for g in GUIDES)
    errors = []
    if [s['level'] for s in en] != [s['level'] for s in nl]:
        # find the first heading where they part
        for i, (a, b) in enumerate(zip(en, nl)):
            if a['level'] != b['level']:
                errors.append(f'headings part at EN line {a["line"]} "{a["title"]}" (h{a["level"]}) and '
                              f'NL line {b["line"]} "{b["title"]}" (h{b["level"]})')
                break
        else:
            errors.append(f'EN has {len(en)} headings, NL {len(nl)}')
    for a, b in zip(en, nl):
        if a['level'] != b['level']:
            break
        for what in ('bullets', 'steps', 'tables'):
            if a[what] != b[what]:
                errors.append(f'{what} differ under EN line {a["line"]} "{a["title"]}" ({a[what]}) and '
                              f'NL line {b["line"]} "{b["title"]}" ({b[what]})')
    rel = manifest(root)['release']
    if rel and not re.search(r'^## \[' + re.escape(rel) + r'\]', read(os.path.join(root, 'CHANGELOG.md')), re.M):
        errors.append(f'CHANGELOG.md has no entry "## [{rel}]"')
    return errors


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    errors = check(root)
    if errors:
        print('Guides not in step:')
        for e in errors:
            print('  - ' + e)
        sys.exit(1)
    print('Guides in step (EN/NL), CHANGELOG has the release.')


if __name__ == '__main__':
    main()
