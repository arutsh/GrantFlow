from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import celery_app


def test_disabled_flag_skips_signal_registration(monkeypatch):
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    with (
        patch.object(celery_app.task_prerun, "connect") as prerun_connect,
        patch.object(celery_app.task_postrun, "connect") as postrun_connect,
        patch.object(celery_app.task_failure, "connect") as failure_connect,
    ):
        celery_app._register_observability_signal_handlers()

    prerun_connect.assert_not_called()
    postrun_connect.assert_not_called()
    failure_connect.assert_not_called()


def test_enabled_registers_all_three_signal_handlers(monkeypatch):
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)

    with (
        patch.object(celery_app.task_prerun, "connect") as prerun_connect,
        patch.object(celery_app.task_postrun, "connect") as postrun_connect,
        patch.object(celery_app.task_failure, "connect") as failure_connect,
    ):
        celery_app._register_observability_signal_handlers()

    prerun_connect.assert_called_once_with(celery_app._start_task_span)
    postrun_connect.assert_called_once_with(celery_app._end_task_span)
    failure_connect.assert_called_once_with(celery_app._record_task_failure)


class TestTaskSpanLifecycle:
    def setup_method(self):
        celery_app._task_context.clear()

    def teardown_method(self):
        celery_app._task_context.clear()

    def test_successful_task_increments_success_counter(self):
        mock_span = MagicMock()
        mock_counter = MagicMock()
        task = SimpleNamespace(name="tasks.debug.ping")

        with (
            patch.object(
                celery_app, "_tracer", MagicMock(start_span=MagicMock(return_value=mock_span))
            ),
            patch.object(celery_app, "_task_counter", mock_counter),
        ):
            celery_app._start_task_span(task_id="task-1", task=task)
            celery_app._end_task_span(task_id="task-1")

        mock_span.set_status.assert_called_once()
        status_arg = mock_span.set_status.call_args[0][0]
        assert status_arg.status_code.name == "OK"
        mock_span.end.assert_called_once()
        mock_counter.add.assert_called_once_with(
            1, {"task_name": "tasks.debug.ping", "status": "success"}
        )
        assert "task-1" not in celery_app._task_context

    def test_failing_task_increments_failure_counter_and_records_exception(self):
        mock_span = MagicMock()
        mock_counter = MagicMock()
        task = SimpleNamespace(name="tasks.users.send_verification_email")
        exc = ValueError("boom")

        with (
            patch.object(
                celery_app, "_tracer", MagicMock(start_span=MagicMock(return_value=mock_span))
            ),
            patch.object(celery_app, "_task_counter", mock_counter),
        ):
            celery_app._start_task_span(task_id="task-2", task=task)
            celery_app._record_task_failure(task_id="task-2", exception=exc)
            celery_app._end_task_span(task_id="task-2")

        mock_span.record_exception.assert_called_once_with(exc)
        error_status_arg = mock_span.set_status.call_args_list[0][0][0]
        assert error_status_arg.status_code.name == "ERROR"
        # _end_task_span must not overwrite the ERROR status with OK.
        assert mock_span.set_status.call_count == 1
        mock_counter.add.assert_called_once_with(
            1, {"task_name": "tasks.users.send_verification_email", "status": "failure"}
        )
        assert "task-2" not in celery_app._task_context

    def test_postrun_without_matching_prerun_is_a_noop(self):
        mock_counter = MagicMock()
        with patch.object(celery_app, "_task_counter", mock_counter):
            celery_app._end_task_span(task_id="unknown-task")

        mock_counter.add.assert_not_called()
