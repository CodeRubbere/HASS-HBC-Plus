#!/usr/bin/env python3
"""Set the HBC+ version for a release (HBC+ v1.3).

  python3 tools/set-version.py 1.4.0                               minor release: every part
  python3 tools/set-version.py 1.3.1 hbc_phase_guard dashboard     patch release: only these parts
  python3 tools/set-version.py 1.3.1 flows                         patch release: only the flows

Parts: 'flows' (all Node-RED files together), 'dashboard', or a package file name
(hbc_phase_guard or hbc_phase_guard.yaml); 'all' = every part. A new major or minor version
always sets every part. hbc_config.yaml is never touched. Run tools/check-versions.py after it,
then write the CHANGELOG and the guides by hand.

What it changes:
  packages   the state of sensor hbc_version_<name>
  flows      const VERSION in every 'HBC+ version' node and in 'HBC+ health'; the EXPECTED_PACKAGES
             list (kept in step with packages/); on a minor release also every tab name
             '<tab> vX.Y', references to it, and 'Part of **HBC+ vX.Y**' / 'HBC+ vX.Y (open the'
  dashboard  the dash constants (header, version card, update card, Versions table), the version in the
             Overview heading 'Status & control (vX.Y.Z)', and the numbers in
             the visibility conditions of the version card and the update card
  manifest   versions.json, written from all of the above
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hbc_versions import (CARD_NUM_RE, CONST_RE, DASH_NUM_RE, DASH_RE, EXPECTED_RE, HEADING_RE, collect,  # noqa: E402
                          dump_flows, flow_files, full_num, load_flows, manifest_text, mm, num, package_names,
                          package_re, read, strings, tab_labels, write)


def main():
    args = sys.argv[1:]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not args or not re.fullmatch(r'\d+\.\d+\.\d+', args[0]):
        sys.exit(__doc__)
    new, parts = args[0], [p[:-5] if p.endswith('.yaml') else p for p in args[1:]] or ['all']
    pk = package_names(root)
    for p in parts:
        if p not in pk + ['flows', 'dashboard', 'all']:
            sys.exit(f'Unknown part: {p}. Parts: flows, dashboard, all, ' + ', '.join(pk))
    cur = collect(root)
    current = max([x for x in cur['packages'].values() if x] +
                  [x for k, x in cur['flows'].items() if 'VERSION' in k] +
                  [x for k, x in cur['dashboard'].items() if k.startswith('dash')],
                  key=lambda v: tuple(int(i) for i in v.split('.')))
    minor = mm(new) != mm(current)
    if minor and parts != ['all']:
        print(f'{current} -> {new} is a new minor version: setting every part.')
    if minor or 'all' in parts:
        parts = pk + ['flows', 'dashboard']
    changed = []
    # packages
    for name in pk:
        if name in parts:
            p = os.path.join(root, 'packages', name + '.yaml')
            s, n = package_re(name).subn(lambda m: m.group(1) + new + m.group(3), read(p))
            if n != 1:
                sys.exit(f'{p}: no (or more than one) sensor hbc_version_{name}')
            write(p, s)
            changed.append(f'packages/{name}.yaml')
    # flows (one part)
    if 'flows' in parts:
        old_mm = mm([x for k, x in cur['flows'].items() if 'VERSION' in k][0])
        for p in flow_files(root):
            data, exact = load_flows(p)
            if not exact:
                sys.exit(f'{p}: writing it back would reformat the file; export it from Node-RED again first')
            subs = [(CONST_RE, lambda m: m.group(1) + new + m.group(3)),
                    (EXPECTED_RE, lambda m: m.group(1) + json.dumps(pk) + m.group(3))]
            pairs = []
            if minor:
                for lab in tab_labels(data):
                    base = re.sub(r' v\d+\.\d+$', '', lab)
                    pairs.append((f'{base} v{old_mm}', f'{base} v{mm(new)}'))
                pairs += [(f'Part of **HBC+ v{old_mm}**', f'Part of **HBC+ v{mm(new)}**'),
                          (f'HBC+ v{old_mm} (open the', f'HBC+ v{mm(new)} (open the')]
            for n in data:
                for k in strings(n):
                    v = n[k]
                    for rx, fn in subs:
                        v = rx.sub(fn, v)
                    for a, b in pairs:
                        v = v.replace(a, b)
                    n[k] = v
            write(p, dump_flows(data))
        changed.append('node-red/*.json')
    # dashboard
    if 'dashboard' in parts:
        p = os.path.join(root, 'dashboards', 'hbc_plus.yaml')
        s = read(p)
        s = DASH_RE.sub(lambda m: m.group(1) + new + m.group(3), s)
        s = CARD_NUM_RE.sub(lambda m: m.group(1) + str(num(new)), s)
        s = DASH_NUM_RE.sub(lambda m: m.group(1) + str(full_num(new)), s)
        s = HEADING_RE.sub(lambda m: m.group(1) + new + m.group(3), s)
        write(p, s)
        changed.append('dashboards/hbc_plus.yaml')
    write(os.path.join(root, 'versions.json'), manifest_text(root))
    changed.append('versions.json')
    print(f'Set {new} in:\n  ' + '\n  '.join(changed))
    print('Next: tools/check-versions.py, then CHANGELOG.md and both user guides (by hand).')


if __name__ == '__main__':
    main()
