"""Compare current native and browser builder observations, not source text."""
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    native = json.loads((root / "artifacts/ui-flow-smoke.json").read_text())
    browsers = json.loads((root / "artifacts/builder-web/flow-review.json").read_text())
    assert native["passed"], "Run the native builder reference successfully first."
    reference = native["builder_reference"]
    assert reference, "Native report has no current builder observations."
    assert set(browsers) == {"chromium", "webkit"}, "Review both browser engines."
    for name, observed in browsers.items():
        assert observed["passed"], name
        for key, value in reference.items():
            assert observed[key] == value, (name, key, value, observed[key])
    print("PASS: current native/Chromium/WebKit builder observations agree on selected heading, default/preset targets, same-screen selection and no eager calculation.")


if __name__ == "__main__":
    main()
