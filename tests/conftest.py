```python
<<<<<<< SEARCH
=======
import subprocess
from contextlib import suppress
# Configure logger
import logging
logger = logging.getLogger(__name__)
@pytest.fixture
def cli_executor(mocker):
    """A fixture providing a mock CLI executor"""
    with suppress(Exception):
        return mocker.patch('adev.cli_executorCliExecutor')
@pytest.fixture
def base():
    """Return the base class for testing"""
    from .cli import CliExecutor
    return CliExecutor()
>>>>>>> REPLACE
```
