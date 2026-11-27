"""Shared helpers for tools/check-versions.py and tools/set-version.py (HBC+ version check, v1.3).

Where HBC+ keeps its version, per part:
  packages   packages/hbc_<name>.yaml        sensor 'HBC version hbc_<name>'   state: "X.Y.Z"
             (not hbc_config.yaml: that file is the user's own)
  flows      node-red/*.json                 const VERSION = 'X.Y.Z' (every 'HBC+ version' node and
                                             'HBC+ health'), tab names '<tab> vX.Y', and the
                                             EXPECTED_PACKAGES list in 'HBC+ health'
  dashboard  dashboards/hbc_plus.yaml        {%- set dash = 'X.Y.Z' -%} in every card that needs it (the
                                             header, the version card, the update card, the Versions
                                             table), the Overview heading 'Status & control (vX.Y.Z)',
                                             and the numbers in two visibility conditions:
                                             sensor.hbc_release_number (major x 100 + minor) and
                                             sensor.hbc_release_dashboard_number (major x 10000 +
                                             minor x 100 + patch); a card shown for exactly this
                                             release uses the range above: N-1 / below: N+1
  manifest   versions.json                   every part and its version; Home Assistant reads it from
                                             GitHub at the release tag (update check)
Only the Python standard library is used, so the scripts also run in a GitHub Action.
"""
import json
import os
import re

VER = r'\d+\.\d+\.\d+'


def mm(v):
    return '.'.join(str(v).split('.')[:2])


def key(v):
    return tuple(int(x) for x in str(v).split('.'))


def num(v):
    a, b = (int(x) for x in str(v).split('.')[:2])
    return a * 100 + b


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def package_names(root):
    d = os.path.join(root, 'packages')
    return sorted(f[:-5] for f in os.listdir(d)
                  if f.startswith('hbc_') and f.endswith('.yaml') and f != 'hbc_config.yaml')


def package_re(name):
    return re.compile(r'(unique_id: hbc_version_' + re.escape(name) +
                      r'\n(?:[ \t]+[^\n]*\n)*?[ \t]+state: ")(' + VER + r')(")')


def flow_files(root):
    d = os.path.join(root, 'node-red')
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.json'))


CONST_RE = re.compile(r"(const VERSION = ')(" + VER + r")(';)")
EXPECTED_RE = re.compile(r'(const EXPECTED_PACKAGES = )(\[[^\]]*\])(;)')
PKG_LIST_RE = re.compile(r'(\{%- set hbc_packages = )(\[[^\]]*\])( -%\})')   # hbc_control.yaml, sensor.hbc_package_version
DASH_RE = re.compile(r"(\{%-? set dash = ')(" + VER + r")(' -?%\})")
CARD_NUM_RE = re.compile(r'(entity: sensor\.hbc_release_number\n\s+(?:below|above): )(\d+)(?!\d|\n\s+below:)')
# 'Exactly this release' (sensor.hbc_release_number = N): above: N-1 / below: N+1
CARD_RANGE_RE = re.compile(r'(entity: sensor\.hbc_release_number\n\s+above: )(\d+)(\n\s+below: )(\d+)')
HEADING_RE = re.compile(r'(heading: Status & control \(v)(' + VER + r')(\)\n)')
DASH_NUM_RE = re.compile(r'(entity: sensor\.hbc_release_dashboard_number\n\s+above: )(\d+)')


def full_num(v):
    a, b, c = (int(x) for x in str(v).split('.'))
    return a * 10000 + b * 100 + c


def load_flows(path):
    """A Node-RED export as a list of nodes, and whether writing it back keeps the file byte for byte."""
    raw = read(path)
    data = json.loads(raw)
    return data, dump_flows(data) == raw


def dump_flows(data):
    return json.dumps(data, indent=4, ensure_ascii=False)


def strings(node):
    """The text fields of a node that can carry code or a version."""
    return [k for k, v in node.items() if isinstance(v, str)]


def tab_labels(data):
    return [n.get('label', '') for n in data if isinstance(n, dict) and n.get('type') == 'tab']


def collect(root):
    """Every version HBC+ carries, as {part: {place: version}}."""
    out = {'packages': {}, 'flows': {}, 'dashboard': {}}
    for name in package_names(root):
        m = package_re(name).search(read(os.path.join(root, 'packages', name + '.yaml')))
        out['packages'][name] = m.group(2) if m else None
    for p in flow_files(root):
        data, _ = load_flows(p)
        f = os.path.basename(p)
        i = 0
        for n in data:
            for k in strings(n):
                for m in CONST_RE.finditer(n[k]):
                    i += 1
                    out['flows'][f'{f} VERSION #{i}'] = m.group(2)
                m = EXPECTED_RE.search(n[k])
                if m:
                    out['flows'][f'{f} EXPECTED_PACKAGES'] = json.loads(m.group(2))
        for lab in tab_labels(data):
            m = re.search(r' v(\d+\.\d+)$', lab)
            out['flows'][f'{f} tab "{lab}"'] = m.group(1) if m else None
    out['package_lists'] = [json.loads(m.group(2)) for m in PKG_LIST_RE.finditer(
        read(os.path.join(root, 'packages', 'hbc_control.yaml')))]
    s = read(os.path.join(root, 'dashboards', 'hbc_plus.yaml'))
    for i, m in enumerate(DASH_RE.finditer(s)):
        out['dashboard'][f'dash constant #{i + 1}'] = m.group(2)
    for i, m in enumerate(CARD_NUM_RE.finditer(s)):
        out['dashboard'][f'version card number #{i + 1}'] = int(m.group(2))
    for i, m in enumerate(CARD_RANGE_RE.finditer(s)):
        out['dashboard'][f'release range #{i + 1}'] = (int(m.group(2)), int(m.group(4)))
    for i, m in enumerate(DASH_NUM_RE.finditer(s)):
        out['dashboard'][f'update card number #{i + 1}'] = int(m.group(2))
    for i, m in enumerate(HEADING_RE.finditer(s)):
        out['dashboard'][f'dash heading #{i + 1}'] = m.group(2)
    return out


def parts(root):
    """{part: version} as a release ships it: each package file, 'flows' and 'dashboard'.
    None for a part whose places disagree (tools/check-versions.py says where)."""
    v = collect(root)
    out = {}
    fl = {x for k, x in v['flows'].items() if 'VERSION' in k}
    out['flows'] = fl.pop() if len(fl) == 1 else None
    da = {x for k, x in v['dashboard'].items() if k.startswith('dash')}
    out['dashboard'] = da.pop() if len(da) == 1 else None
    out.update(v['packages'])
    return out


def manifest(root):
    """The content of versions.json."""
    p = parts(root)
    ok = [x for x in p.values() if x]
    return {'release': max(ok, key=key) if ok else None,
            'parts': {k: p[k] for k in sorted(p, key=lambda k: (k.startswith('hbc_'), k))}}


def manifest_text(root):
    return json.dumps(manifest(root), indent=2) + '\n'


def check_flow_files(root):
    """Every tab sits in hbc-plus-all-flows.json and in its own file under node-red/; both must hold the same
    nodes. Node-RED's 'global-config' export nodes are ignored: every export writes its own."""
    errors = []
    d = os.path.join(root, 'node-red')
    allp = os.path.join(d, 'hbc-plus-all-flows.json')
    if not os.path.exists(allp):
        return ['node-red: hbc-plus-all-flows.json missing']
    allf = [n for n in json.loads(read(allp)) if n.get('type') != 'global-config']
    by_id = {n['id']: n for n in allf}
    tabs = {n['id']: n.get('label', '') for n in allf if n.get('type') == 'tab'}
    seen = {}
    for p in flow_files(root):
        f = os.path.basename(p)
        if f == 'hbc-plus-all-flows.json':
            continue
        nodes = [n for n in json.loads(read(p)) if n.get('type') != 'global-config']
        tids = [n['id'] for n in nodes if n.get('type') == 'tab']
        for t in tids:
            if t in seen:
                errors.append(f'node-red: tab {tabs.get(t, t)!r} is in {seen[t]} and in {f}')
            seen[t] = f
        ids = {n['id'] for n in nodes}
        for n in nodes:
            if n['id'] not in by_id:
                errors.append(f'node-red/{f}: node {n.get("name") or n["type"]} ({n["id"]}) is not in hbc-plus-all-flows.json')
            elif n != by_id[n['id']]:
                errors.append(f'node-red/{f}: node {n.get("name") or n["type"]} ({n["id"]}) differs from hbc-plus-all-flows.json')
        for n in allf:
            if n.get('z') in tids and n['id'] not in ids:
                errors.append(f'node-red/{f}: node {n.get("name") or n["type"]} ({n["id"]}) of hbc-plus-all-flows.json is missing')
    for t, lab in tabs.items():
        if t not in seen:
            errors.append(f'node-red: tab {lab!r} has no file of its own')
    return errors


# Files a user copies from a release, and the part each belongs to (None = no version of its own)
def part_of(path):
    if path.startswith('packages/hbc_') and path.endswith('.yaml') and path != 'packages/hbc_config.yaml':
        return path[len('packages/'):-5]
    if path == 'packages/hbc_config.yaml':
        return 'hbc_config (yours: compare by hand)'
    if path.startswith('node-red/') and path.endswith('.json') and '/examples/' not in path:
        return 'flows'
    if path == 'dashboards/hbc_plus.yaml':
        return 'dashboard'
    if path.startswith('www/hbc-plus/'):
        return 'www'
    return None
