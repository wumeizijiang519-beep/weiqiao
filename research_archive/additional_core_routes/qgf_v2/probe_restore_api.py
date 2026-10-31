"""Inspect installed SAPIEN restore interfaces without creating an environment."""
import json
from pathlib import Path
import sys
import sapien
import sapien.core as core


def describe(owner):
    return {name: str(getattr(owner, name).__doc__)[:2500]
            for name in dir(owner) if any(word in name.lower()
                                         for word in ('pack', 'unpack', 'state'))}


report = {'sapien': getattr(sapien, '__version__', 'unknown'),
          'scene': describe(core.Scene),
          'physx_cpu': describe(sapien.physx.PhysxCpuSystem),
          'status': 'API inventory only, no restore parity claim'}
path = Path(sys.argv[1])
if path.exists():
    raise FileExistsError(path)
path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
