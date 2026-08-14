from pathlib import Path
from factory.config import load_product


def test_product_manifests_parse():
    root = Path(__file__).resolve().parents[1]
    products = [load_product(path) for path in (root / "products").glob("*.toml")]
    assert {p.name for p in products} == {
        "roblox-revenueos-plugin",
        "roblox-skillcity",
        "roblox-qa-autopilot-plugin",
        "roblox-liveops-autopilot-plugin",
    }
    assert all(p.build_commands for p in products)
