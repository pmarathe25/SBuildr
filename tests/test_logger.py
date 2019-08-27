from sbuildr.logger import G_LOGGER, SBuildrException

import pytest

class TestLogger(object):
    def test_critical_raises_exception(self):
        with pytest.raises(SBuildrException) as exc:
            message = "A test message"
            G_LOGGER.critical(message)
        assert exc.match(message)
