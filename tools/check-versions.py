#!/usr/bin/env python3
"""Check that every HBC+ version in this repository is consistent (HBC+ v1.3).

  python3 tools/check-versions.py [--tag vX.Y.Z] [repo folder]

Rules:
  - Within a part every place agrees: all VERSION constants and tab names of the flows, all
    numbers of the dashboard. Tab names and the dashboard header carry major.minor only.
  - Across parts major.minor is the same. A patch release only bumps the parts it changed, so
    patch numbers may differ between parts.
  - EXPECTED_PACKAGES in 'HBC+ health' lists exactly the package files in packages/.
  - Every tab is identical in node-red/hbc-plus-all-flows.json and in its own file.
  - versions.json (the release manifest) matches the files.
  - With --tag: the newest version in the repository equals the tag (v prefix optional).
Exit code 0 = consistent, 1 = not (every problem is listed).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hbc_versions import (check_flow_files, collect, full_num, key, manifest_text, mm, num,  # noqa: E402
                          package_names, read)


def check(root, tag=None):
    v = collect(root)
    errors, parts = [], {}
    # packages: every file has its own version
    for name, ver in v['packages'].items():
        if ver is None:
            errors.append(f'packages/{name}.yaml: no sensor hbc_version_{name}')
        else:
            parts[f'{name}.yaml'] = ver
    # flows: one part, every place the same
    fl = {k: x for k, x in v['flows'].items() if 'VERSION' in k}
    tabs = {k: x for k, x in v['flows'].items() if ' tab ' in k}
    exp = {k: x for k, x in v['flows'].items() if k.endswith('EXPECTED_PACKAGES')}
    if not fl:
        errors.append('node-red: no VERSION constants found')
    elif len(set(fl.values())) > 1:
        errors.append('node-red: VERSION differs: ' + ', '.join(f'{k} = {x}' for k, x in fl.items()
                                                               if x != max(fl.values(), key=key)))
    else:
        flows = next(iter(fl.values()))
        parts['node-red flows'] = flows
        for k, x in tabs.items():
            if x != mm(flows):
                errors.append(f'node-red: {k} should end in v{mm(flows)}')
    for k, x in exp.items():
        if x != package_names(root):
            errors.append(f'node-red: {k} = {x}, packages/ has {package_names(root)}')
    if not exp:
        errors.append("node-red: no EXPECTED_PACKAGES in 'HBC+ health'")
    # the fixed package list in sensor.hbc_package_version (hbc_control.yaml)
    lists = v.get('package_lists') or []
    if not lists:
        errors.append('packages/hbc_control.yaml: no hbc_packages list in sensor.hbc_package_version')
    for x in lists:
        if x != package_names(root):
            errors.append(f'packages/hbc_control.yaml: hbc_packages = {x}, packages/ has {package_names(root)}')
    # dashboard: one part
    d = v['dashboard']
    dash = sorted({x for k, x in d.items() if k.startswith('dash')})
    if len(dash) != 1:
        errors.append(f'dashboard: dash constants {dash or "missing"} (need one value)')
    else:
        dash = dash[0]
        parts['dashboard'] = dash
        for k, x in d.items():
            if k.startswith('version card') and x != num(dash):
                errors.append(f'dashboard: {k} = {x}, should be {num(dash)}')
            if k.startswith('release range') and x != (num(dash) - 1, num(dash) + 1):
                errors.append(f'dashboard: {k} = above {x[0]} / below {x[1]}, should be '
                              f'above {num(dash) - 1} / below {num(dash) + 1}')
            if k.startswith('update card') and x != full_num(dash):
                errors.append(f'dashboard: {k} = {x}, should be {full_num(dash)}')
    # across parts
    if parts:
        mms = sorted({mm(x) for x in parts.values()}, key=key)
        if len(mms) > 1:
            errors.append('major.minor differs between parts: ' + ', '.join(
                f'{p} {x}' for p, x in parts.items() if mm(x) != mms[-1]) + f' (newest {mms[-1]})')
    # every tab identical in hbc-plus-all-flows.json and in its own file
    errors += check_flow_files(root)
    # versions.json = what the files say
    mp = os.path.join(root, 'versions.json')
    if not os.path.exists(mp):
        errors.append('versions.json missing (tools/set-version.py writes it)')
    elif read(mp) != manifest_text(root):
        errors.append('versions.json does not match the files: run tools/set-version.py, or write it with '
                      'python3 -c "import sys; sys.path.insert(0, \'tools\'); import hbc_versions as h; '
                      'print(h.manifest_text(\'.\'), end=\'\')" > versions.json')
    newest = max(parts.values(), key=key) if parts else None
    if tag and newest and tag.lstrip('vV') != newest:
        errors.append(f'tag {tag} does not match the newest version in the repository ({newest})')
    return parts, newest, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', nargs='?', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument('--tag')
    a = ap.parse_args()
    parts, newest, errors = check(a.root, a.tag)
    w = max([len(p) for p in parts] + [4])
    for p, x in sorted(parts.items(), key=lambda i: (i[0][0] == 'h', i[0])):
        print(f'  {p:<{w}}  {x}')
    print(f'  {"HBC+":<{w}}  {newest}  (newest)')
    if errors:
        print('\nNot consistent:')
        for e in errors:
            print('  - ' + e)
        sys.exit(1)
    print('\nConsistent.')


if __name__ == '__main__':
    main()
