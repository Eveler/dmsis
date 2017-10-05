# -*- coding: utf-8 -*-

import logging
from logging import INFO

from mfc_integration.direct_int import Integration


__author__ = 'Савенко_МЮ'


def setup():
    """
    Setup the integration process
    """

    logging.basicConfig(level=INFO, format='%(asctime)s %(module)s(%(lineno)d): %(levelname)s: %(message)s')
    logging.root.name = "integration"
    # from logging import DEBUG, WARNING, CRITICAL, ERROR
    # logging.addLevelName(DEBUG, "debug")
    # logging.addLevelName(INFO, "info")
    # logging.addLevelName(WARNING, "warn")
    # logging.addLevelName(WARNING, "warning")
    # logging.addLevelName(ERROR, "error")
    # logging.addLevelName(CRITICAL, "critical")

    integration = Integration()
    integration.run()
