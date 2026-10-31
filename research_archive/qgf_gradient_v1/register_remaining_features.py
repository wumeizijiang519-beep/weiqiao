"""Freeze fixed remaining286 extraction from measured pilot and I/O costs."""

import json
from pathlib import Path
import subprocess

from corpus_reader import certified_population, checked_json, sha
from extract_remaining_features import REQUIRED_SOURCES, validate_registration


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
dataset = CODE / 'training288_v2_remaining/DATASET_RESULT.json'
dataset_sha = 'baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87'
population = certified_population(dataset, dataset_sha)
encoder_path = ROOT / 'runs/qgf_gradient_encoder_audit_v1_retry1/audit/REPORT.json'
encoder_sha = 'f5d5d2317b6c4cec4a9a59f9a173ee5f9c377967dc7ca012ca4b6738b20d1b0a'
encoder = checked_json(encoder_path, encoder_sha)
pilot_root = ROOT / 'runs/qgf_gradient_feature_cost_pilot_v1'
pilot = json.loads((pilot_root / 'REPORT.json').read_text())
if (encoder['status'] != 'CURRENT_FEATURE_ENCODER_AUDIT_PASS'
        or pilot['status'] != 'FIRST_TWO_FEATURE_COST_PILOT_COMPLETE_NOT_FULL_CORPUS'
        or pilot['dataset_result_sha256'] != dataset_sha
        or pilot['encoder_report_sha256'] != encoder_sha):
    raise RuntimeError('Actual encoder or pilot not qualified')
accounting = subprocess.check_output(['sacct', '-j', '1593640.337,1593640.338,1593640.339',
    '-n', '-P', '--format=JobID,State,ExitCode,ElapsedRaw'], text=True)
expected = {'1593640.337': ('FAILED', '1:0', 439),
            '1593640.338': ('COMPLETED', '0:0', 370),
            '1593640.339': ('COMPLETED', '0:0', 356)}
seen = set()
for line in accounting.splitlines():
    fields = line.split('|')
    if fields[0] in expected:
        if fields[0] in seen or (fields[1], fields[2], int(fields[3])) != expected[fields[0]]:
            raise RuntimeError('Feature phase accounting changed')
        seen.add(fields[0])
if seen != set(expected):
    raise RuntimeError('Incomplete feature phase accounting')
io_path = CODE / 'FEATURE_IO_BENCHMARK.json'
io = json.loads(io_path.read_text())
ids = [f'train_{i:04d}' for i in range(2, 288)]
observations = sum(population[name]['replans'] + 1 for name in ids)
forecast = 600 + 1.5 * observations * (pilot['encode_p90_seconds'] + io['p90_seconds']) + 80 + 120
hard, spent = 5400, sum(value[2] for value in expected.values())
if forecast > hard or spent + 5520 > .8 * 8 * 3600:
    raise RuntimeError('Measured extraction forecast/budget reserve insufficient')
supplement = CODE / 'RESOURCE_COST_SUPPLEMENT.json'
if sha(supplement) != '0defbb9a0a5eaa01ad076b8abe19fbaf0a563665fb8de9dd2c63f4fa25594c65':
    raise RuntimeError('Resource failure accounting changed')
registration = dict(stage='REMAINING_FIXED_286_FEATURE_EXTRACTION',
    dataset_result=str(dataset), dataset_sha256=dataset_sha,
    encoder_report=str(encoder_path), encoder_report_sha256=encoder_sha,
    resource_cost_supplement=str(supplement), resource_cost_sha256=sha(supplement),
    source_sha256={name: sha(CODE / name) for name in REQUIRED_SOURCES},
    pilot_report=str(pilot_root / 'REPORT.json'), pilot_report_sha256=sha(pilot_root / 'REPORT.json'),
    pilot_run_directory=str(pilot_root), episode_ids=ids,
    run_directory=str(ROOT / 'runs/qgf_gradient_feature_remaining286_v1'),
    hard_gpu_seconds=hard, slurm_hard_seconds=5520,
    critic_phase_gpu_seconds_spent=spent, cumulative_gpu_seconds_before_launch=34710 + spent,
    remaining_observations=observations, measured_encoder_p90_seconds=pilot['encode_p90_seconds'],
    io_benchmark_sha256=sha(io_path), measured_sample_io_p90_seconds=io['p90_seconds'],
    forecast_gpu_seconds=forecast, forecast_safety_multiplier=1.5,
    forecast_fixed_load_allowance_seconds=600, forecast_prompt_allowance_seconds=80,
    forecast_publication_allowance_seconds=120,
    forecast_caveat='I/O sample14fixed initial observations; not a guarantee of whole-stage p90',
    no_reencode_first_two=True, no_critic_fit=True, full_index_requires_independent_audit=True)
validate_registration(registration)
output = CODE / 'REMAINING_FEATURES_REGISTRATION.json'
with output.open('x') as stream:
    json.dump(registration, stream, indent=2)
print(json.dumps({key: registration[key] for key in
    ('remaining_observations', 'forecast_gpu_seconds', 'hard_gpu_seconds',
     'critic_phase_gpu_seconds_spent', 'cumulative_gpu_seconds_before_launch')}), flush=True)
