```python
<<<<<<< SEARCH
=======
import unittest
from adev.utils import (
    get_input,
    set_input,
    parse_input,
)
class TestInputFunctions(unittest.TestCase):
    def test_parse_input(self):
        """Test input parsing function"""
        # Valid JSON input
        assert isinstance(parse_input('[{"a": 1}, {"b": 2}]'), list)
        # Invalid format, returns None
        result = parse_input('invalid')
        assert result is None
>>>>>>> REPLACE
```
