import logging
from unittest.mock import patch

import celery_app


def test_after_setup_logger_hook_calls_init_logging():
    with patch("celery_app.init_logging") as init_logging:
        celery_app._attach_otlp_log_handler()

    init_logging.assert_called_once_with("worker")


def test_handler_attached_via_after_setup_logger_survives_celerys_own_bootstrap():
    # Regression test for Celery's worker_hijack_root_logger default: it
    # clears every handler already on the root logger before adding its own,
    # so a handler attached at plain import time would be wiped the moment
    # the worker process actually starts. Attaching via the after_setup_logger
    # signal (what _attach_otlp_log_handler does) must survive that reset.
    root_logger = logging.getLogger()
    sentinel = logging.NullHandler()

    def add_sentinel(**_kwargs):
        root_logger.addHandler(sentinel)

    celery_app.after_setup_logger.connect(add_sentinel)
    try:
        celery_app.app.log.setup_logging_subsystem(loglevel="INFO")
        assert sentinel in root_logger.handlers
    finally:
        celery_app.after_setup_logger.disconnect(add_sentinel)
        root_logger.removeHandler(sentinel)
