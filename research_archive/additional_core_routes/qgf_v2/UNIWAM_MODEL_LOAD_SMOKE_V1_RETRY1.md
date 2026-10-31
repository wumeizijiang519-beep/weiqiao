# UniWAM Model-Load Smoke V1 Retry1

The original model-load smoke stopped before model construction because the
asset inventory omitted the official Wan2.2 `config.json`. The failed run and
traceback are retained. Retry1 adds only the fixed-revision 251-byte model
config (SHA256 `d1fea36899d00c2501b836c13ad65af56e2f9529ba622e50886d3f5c3e6c02bc`)
and 309-byte ModelScope `configuration.json` sidecar (SHA256
`b79968dbf190e7f4802d48dbb7e8c3a4d1064f5faf90a44435d86239c3e6198a`).
The corrected asset-manifest SHA256 is
`bcd143682160c3007ee5341ab9a5b91404eedd49eb3a4712615aa99b24ed09df`.

All source, checkpoint, runtime, model configuration, dtype, history-flow
settings, resource limits, and admission criteria from V1 remain unchanged.
PASS still requires the official loader to report `missing=0, unexpected=0`.
No simulator, action, reward, or episode is run.
