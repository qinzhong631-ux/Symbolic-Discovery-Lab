import subprocess
import sys


def test_experiment_import_does_not_initialize_torch_before_julia():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import symbolic_discovery.experiments; assert 'torch' not in sys.modules",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
