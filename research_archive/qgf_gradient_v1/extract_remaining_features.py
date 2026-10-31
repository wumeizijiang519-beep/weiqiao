"""Registered remaining-feature extraction; inherit pilot blocks without re-encoding."""

import argparse
import json
from pathlib import Path
import time
import traceback

import numpy as np

from corpus_reader import certified_population, checked_json, sha
from feature_corpus import persist_episode
from feature_publication import inherit_pilot, publish_index


REQUIRED_SOURCES = {'extract_remaining_features.py', 'feature_publication.py', 'feature_corpus.py', 'corpus_reader.py',
                    'rl_corpus.py', 'training_data.py', 'features.py', 'wam_runtime.py',
                    'core.py', 'data_contract.py', 'audit_current_features.py'}


def validate_registration(registration):
    if registration['stage'] != 'REMAINING_FIXED_286_FEATURE_EXTRACTION':
        raise ValueError('Only the fixed remaining286 extraction is registered here')
    if registration['episode_ids'] != [f'train_{i:04d}' for i in range(2, 288)]:
        raise ValueError('Cost pilot must not choose episodes by outcomes')
    if not 1 <= registration['hard_gpu_seconds'] <= 5400:
        raise ValueError('Extraction hard limit exceeds5400GPU seconds')
    if set(registration['source_sha256']) != REQUIRED_SOURCES:
        raise ValueError('Incomplete registered extraction dependency inventory')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    validate_registration(registration)
    code = Path(__file__).parent
    for name, expected in registration['source_sha256'].items():
        if sha(code / name) != expected:
            raise ValueError('Registered source changed: ' + name)
    population = certified_population(registration['dataset_result'], registration['dataset_sha256'])
    report = checked_json(registration['encoder_report'], registration['encoder_report_sha256'])
    if (report['status'] != 'CURRENT_FEATURE_ENCODER_AUDIT_PASS'
            or report['dataset_result_sha256'] != registration['dataset_sha256']
            or report['features_source_sha256'] != sha(code / 'features.py')
            or report['feature_spec']['future_frames'] != 0):
        raise ValueError('Current-only encoder qualification missing')
    supplement = checked_json(registration['resource_cost_supplement'], registration['resource_cost_sha256'])
    if supplement['resource_gpu_seconds'] != 738:
        raise ValueError('Resource failure accounting changed')
    if registration['critic_phase_gpu_seconds_spent'] + registration['hard_gpu_seconds'] > .8 * 8 * 3600:
        raise ValueError('Feature/critic phase budget reserve insufficient')
    run = Path(registration['run_directory'])
    if run.exists():
        raise ValueError('Registered run already exists; no silent re-extraction')
    run.mkdir(parents=True)
    started = time.monotonic()
    try:
        # Imports and model construction happen only after every data/source gate.
        import torch
        from audit_current_features import buffer_hashes
        from data_contract import capture_rng, restore_rng, rng_hash
        from features import CurrentWamFeatures
        from wam_runtime import load_wam

        pilot = checked_json(registration['pilot_report'], registration['pilot_report_sha256'])
        if (pilot['status'] != 'FIRST_TWO_FEATURE_COST_PILOT_COMPLETE_NOT_FULL_CORPUS'
                or pilot['dataset_result_sha256'] != registration['dataset_sha256']
                or pilot['encoder_report_sha256'] != registration['encoder_report_sha256']):
            raise ValueError('Pilot provenance changed')
        pilot['run_directory'] = registration['pilot_run_directory']
        inherited = inherit_pilot(run, pilot, population, report['feature_spec']['feature_dimension'])
        cfg, model, processor = load_wam(run)
        before_buffers = buffer_hashes(model)
        encoder = CurrentWamFeatures(model, processor, cfg)
        records = list(inherited)

        def encode(observation, instruction, remaining):
            if time.monotonic() - started >= registration['hard_gpu_seconds']:
                raise RuntimeError('Registered feature pilot time budget exhausted')
            before = capture_rng()
            result = encoder(observation, instruction, remaining)
            if rng_hash(capture_rng()) != rng_hash(before):
                restore_rng(before)
                raise RuntimeError('Encoder changed caller RNG')
            return result

        for name in registration['episode_ids']:
            record = persist_episode(run / 'blocks', population[name], encode,
                                     synchronize=torch.cuda.synchronize)
            if record['feature_dimension'] != report['feature_spec']['feature_dimension']:
                raise RuntimeError('Audited encoder dimension changed')
            records.append(record)
            print(name, record['observation_count'], time.monotonic() - started, flush=True)
        if (buffer_hashes(model) != before_buffers
                or any(p.requires_grad or p.grad is not None for p in model.parameters())):
            raise RuntimeError('Frozen WAM state/gradient contract changed')
        publish_index(run, records, population, report['feature_spec']['feature_dimension'],
                      registration['dataset_sha256'], registration['encoder_report'],
                      registration['encoder_report_sha256'])
        timings = [t for row in records for t in row['encode_seconds']]
        result = dict(status='FEATURE_CORPUS_EXTRACTED_PENDING_INDEPENDENT_AUDIT',
                      dataset_result_sha256=registration['dataset_sha256'],
                      encoder_report_sha256=registration['encoder_report_sha256'],
                      registration_sha256=sha(args.registration), episodes=records,
                      wall_seconds=time.monotonic() - started,
                      encode_p90_seconds=float(np.quantile(timings, .9)),
                      encoder_feature_spec=encoder.spec,
                      peak_cuda_bytes=torch.cuda.max_memory_allocated(),
                      full_corpus_admitted=False, critic_trained=False)
        (run / 'REPORT.json').write_text(json.dumps(result, indent=2))
        (run / 'FEATURE_EXTRACTION_COMPLETE').touch()
        print(json.dumps(result), flush=True)
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
