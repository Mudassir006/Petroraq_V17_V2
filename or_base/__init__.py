import logging

# Keep or_base minimal and focused on utilities required by attendance modules.
from . import helper
from . import controllers
from . import models

_logger = logging.getLogger(__name__)
_logger.info("or_base loaded in minimal compatibility mode.")