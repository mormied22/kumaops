from pathlib import Path
import shutil
import subprocess


def test_upstream_maintenance_dst_virtual_clock(live_source):
    script = Path(__file__).with_name("dst-check.cjs")
    result = subprocess.run(
        [shutil.which("node"), str(script), str(live_source)],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": str(Path(shutil.which("node")).parent), "TZ": "UTC"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("PASS ") == 4
