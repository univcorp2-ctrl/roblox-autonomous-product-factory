# Autonomy model

The factory is intentionally deterministic at release time. Market/creative systems may propose work, but no proposal can publish unless the artifact passes the same bounded gates.

## Pipeline

1. Sync the product repository to the exact tracked branch.
2. Run static checks and deterministic build commands.
3. Connect directly to Roblox Studio's built-in MCP server through `%LOCALAPPDATA%\\Roblox\\mcp.bat`.
4. Require Studio state/tree/Luau/playtest/console/screenshot capabilities and run an Edit-DataModel smoke call.
5. Upload the artifact to a **test place** as `Saved` through Open Cloud.
6. Execute a product-owned Luau smoke suite headlessly on that exact saved version.
7. Poll at most three times, ten seconds apart. A slow or ambiguous test is quarantined; it is never assumed successful.
8. With `AUTO_PUBLISH=1`, upload the same artifact to the production place as `Published` only after configured gates pass.
9. Persist machine-readable release state for monitoring/repair.

## Required one-time platform setup

These are platform identity/credential gates, not recurring operations:

- Sign into Roblox Studio.
- Assistant -> Manage MCP Servers -> Enable Studio as MCP server.
- Create an Open Cloud API key in Creator Dashboard and store it as a machine/GitHub secret, never source code. Required scopes: place publishing plus Luau execution read/write for the chosen test/production universes.
- Create an isolated Roblox test place and set test/production universe/place IDs as environment or repository variables.
- Complete Creator Store seller identity/tax onboarding before USD listings can go live.

After these are configured, normal build/test/release execution needs no human input.

## Failure policy

- Build fail: quarantine immediately.
- MCP unavailable: keep artifact ready but do not publish when visual QA is required.
- Open Cloud mutation: verify by consuming the returned version/task and its terminal status; never assume a 2xx response means a mutation had correct scope.
- Three non-terminal Luau polls: quarantine.
- No external ad/Robux spend is permitted from this factory.
- No bot visits, fake engagement, fake reviews, captcha bypass or player automation for economic rewards.
