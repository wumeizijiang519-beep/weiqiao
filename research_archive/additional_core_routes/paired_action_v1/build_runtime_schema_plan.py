"""Turn the zero-action object inventory into an explicit coverage worklist."""
import argparse
import collections
import hashlib
import json
from pathlib import Path


STATIC_NATIVE = {'xml.etree.ElementTree.Element'}
PHYSICS_NATIVE = {'mujoco._structs.MjData', 'mujoco._structs.MjModel'}
RENDER_NATIVE = {'mujoco._structs.MjvCamera', 'mujoco._render.MjrContext',
                 'mujoco._structs.MjvPerturb', 'mujoco._structs.MjvScene',
                 'mujoco._structs.MjvOption'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(record):
    if 'alias_of' in record:
        return 'alias_identity'
    kind = record['type']
    if kind.startswith(('OpenGL._opaque.', 'ctypes.')):
        return 'renderer_rebuild_and_raster_verifier_required'
    if kind in STATIC_NATIVE:
        return 'static_xml_sha_and_identity'
    if kind in PHYSICS_NATIVE:
        return 'native_physics_adapter_required'
    if kind in RENDER_NATIVE:
        return 'renderer_rebuild_and_raster_verifier_required'
    if record.get('callback'):
        return 'callback_identity_and_closure_required'
    if kind == 'numpy.ndarray':
        return 'mutable_array_exact_bytes'
    if 'fields' in record:
        return 'exact_python_object_schema'
    if kind in ('builtins.dict', 'collections.OrderedDict', 'builtins.list',
                'builtins.tuple'):
        return 'container_alias_preserving'
    if kind in ('builtins.function', 'builtins.method'):
        return 'callback_identity_and_closure_required'
    if record.get('requires_manual_coverage'):
        return 'UNHANDLED_FAIL_CLOSED'
    return 'observed_immutable_or_inventory_leaf'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--objects', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    objects = json.loads(args.objects.read_text())
    runtime_report = json.loads(args.report.read_text())
    rows = [dict(record, coverage_class=classify(record)) for record in objects]
    classes = collections.Counter(row['coverage_class'] for row in rows)
    types = {}
    for row in rows:
        item = types.setdefault(row['type'], {'count': 0, 'classes': set(),
                                               'field_sets': set(), 'examples': []})
        item['count'] += 1
        item['classes'].add(row['coverage_class'])
        if 'fields' in row:
            item['field_sets'].add(tuple(row['fields']))
        if len(item['examples']) < 3:
            item['examples'].append(row['path'])
    type_manifest = {}
    for name, item in sorted(types.items()):
        type_manifest[name] = {'count': item['count'], 'classes': sorted(item['classes']),
                               'field_sets': [list(x) for x in sorted(item['field_sets'])],
                               'examples': item['examples']}
    unhandled = [row for row in rows if row['coverage_class'] == 'UNHANDLED_FAIL_CLOSED']
    status = ('SCHEMA_PLAN_COMPLETE_IMPLEMENTATION_NOT_ADMITTED'
              if not unhandled else 'SCHEMA_PLAN_HAS_UNHANDLED_FAIL_CLOSED')
    result = {'status': status, 'records': len(rows), 'class_counts': dict(sorted(classes.items())),
              'type_manifest': type_manifest, 'unhandled': unhandled,
              'source_inventory_sha256': sha(args.objects),
              'runtime_report_sha256': sha(args.report),
              'builder_sha256': sha(Path(__file__)),
              'dynamic_restore_passed': False, 'robot_actions': 0,
              'limitations': ['Classification is not serialization implementation',
                              'Renderer rebuild needs exact future raster A-B-A verification',
                              'MjModel static identity and MjData integration state require separate adapters']}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({'status': status, 'records': len(rows),
                      'classes': result['class_counts'], 'unhandled': len(unhandled)}))


if __name__ == '__main__':
    main()
