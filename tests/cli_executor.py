```python
<<<<<<< SEARCH
=======
import logging
from adev.cli_executor import (
    CliExecutor,
    check_input_format,
    parse_args,
    run_command,
)
@pytest.mark.parametrize("args", [
    ("invalid_command", "arg1", "arg2", 42),
    ("balanceOf,ethAddress", "", "", 38)
])
def test_start(capsys, cli_executor, args):
    """Test CLI executor start method"""
    with cli_executor.start(*args) as result:
        if len(args[0].split(',')) < 1 or not args[1]:
            assert result.exception is not None
            return
        logger.info(f"Starting CLI executor...")
        captured = capsys.readouterr()
        stdout, stderr = captured.out, captured.stderr
    assert "error: invalid command" in stderr
    if len(args) > 0:
        assert "error: argument is positional only" in stderr
>>>>>>> REPLACE
```
