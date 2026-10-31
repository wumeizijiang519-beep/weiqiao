"""Metadata-only repair for the frozen Causal Signal V2 finalizer."""

import argparse
import hashlib
import json
from pathlib import Path

from causal_signal_v2_metrics import qualify


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--pilot-audit', type=Path, required=True)
    parser.add_argument('--remaining', type=Path, required=True)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--original-finalizer', type=Path, required=True)
    parser.add_argument('--metrics-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    registration = json.loads(args.registration.read_text())
    if sha(args.original_finalizer) != registration['source_sha256']['finalizer']:
        raise RuntimeError('Frozen original finalizer source changed')
    if sha(args.metrics_source) != registration['source_sha256']['metrics']:
        raise RuntimeError('Frozen qualification metrics source changed')
    pilot_path = args.pilot / 'REPORT.json'
    remaining_path = args.remaining / 'REPORT.json'
    pilot = json.loads(pilot_path.read_text())
    remaining = json.loads(remaining_path.read_text())
    audit = json.loads(args.pilot_audit.read_text())
    if (audit.get('status') != 'CAUSAL_SIGNAL_V2_PILOT_PASS' or audit.get('errors') != []
            or audit.get('pilot_report_sha256') != sha(pilot_path)):
        raise RuntimeError('Independent pilot release is not intact')
    if (pilot.get('entry_start'), pilot.get('entry_stop')) != (0, 1):
        raise RuntimeError('Pilot slice changed')
    if (remaining.get('entry_start'), remaining.get('entry_stop')) != (1, 16):
        raise RuntimeError('Remaining slice changed')
    rows = pilot['results'] + remaining['results']
    episodes = [row['episode_id'] for row in rows]
    if len(rows) != 16 or len(set(episodes)) != 16:
        raise RuntimeError('Combined population is not 16 unique groups')
    qualification = qualify(rows)
    result = dict(qualification,
        unavailable_groups=16 - qualification['complete_groups'],
        pilot_report_sha256=sha(pilot_path),
        pilot_audit_sha256=sha(args.pilot_audit),
        remaining_report_sha256=sha(remaining_path),
        population_episode_ids=episodes,
        qgf_efficacy_claim=False,
        metadata_repair='CAUSAL_SIGNAL_V2_FINALIZER_REPAIR_V1',
        original_finalizer_sha256=sha(args.original_finalizer),
        metrics_source_sha256=sha(args.metrics_source),
        results=rows)
    args.output.mkdir(exist_ok=False)
    report_path = args.output / 'REPORT.json'
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output / result['status']).touch()
    (args.output / 'REPORT_SHA256').write_text(sha(report_path) + '  REPORT.json\n')


if __name__ == '__main__':
    main()

