```python
<<<<<<< SEARCH
=======
import doctest
from adev.cli import (
    Cli,
    main
)
def test_basic_cli():
    """Test basic CLI behavior"""
    # Test empty command line
    result = subprocess.run(
        ["Python", "-m", "adev.cli"],
        check=False)
    assert result.returncode == 0
    # Test help message
    result = subprocess.run(
        ["Python", "-m", "adev.cli"] + ["--help"], 
        check=False)
    assert "--help" in result.stdout.strip().lower()
def test_basic_cli_help(subprocess_check):
    """Test basic CLI with --help flag"""
    from adev.cli import main
    # Verify help message is printed
    captured_output = subprocess_check(
        ["Python", "-m", "adev.cli"], ["--help"])
    assert "--help" in captured_output.stdout.strip().lower()
>>>>>>> REPLACE
```
