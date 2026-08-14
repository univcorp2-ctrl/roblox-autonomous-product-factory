# Roblox Autonomous Product Factory

A release factory designed for the actual goal: **finished, tested, publishable Roblox products with recurring human work driven toward zero**.

It combines the two strongest official automation surfaces now available:

- **Roblox Studio MCP** for real Studio state, DataModel inspection, Luau execution, playtest, console output, screenshots and device/gameplay interaction.
- **Open Cloud Luau Execution + Place Publishing** for headless CI testing and programmatic Saved/Published place uploads.

The structure follows the successful official `Roblox/place-ci-cd-demo` pattern (Rojo -> upload -> headless Luau -> deploy), then adds local Studio MCP QA, bounded polling, quarantine states, and a hard production-publish switch.

## Run locally

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m factory.runner --products products
```

Normal first-run states are explicit rather than misleading:

- `READY_WAITING_STUDIO_MCP` — Studio login/MCP toggle is not yet configured.
- `READY_WAITING_OPEN_CLOUD_CREDENTIALS` — code is built and Studio gate passed, but API key/test IDs are absent.
- `RELEASE_CANDIDATE` — all tests passed and automatic production publish is intentionally disabled.
- `PUBLISHED` — all configured gates passed and `AUTO_PUBLISH=1` promoted the artifact.
- `QUARANTINED_*` — a bounded gate failed; never publish this candidate.

See `docs/AUTONOMY.md` for one-time platform setup and safety constraints.
