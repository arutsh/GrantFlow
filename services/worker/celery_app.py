from celery import Celery
from celery.schedules import crontab
from celery.signals import after_setup_logger, task_failure, task_postrun, task_prerun
from config import settings
from opentelemetry import context as otel_context
from opentelemetry import metrics as otel_metrics
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from shared.observability import init_logging, init_observability, is_observability_disabled

init_observability("worker")


@after_setup_logger.connect
def _attach_otlp_log_handler(**_kwargs):
    # Celery's own logging bootstrap (celery.app.log.Logging.setup, invoked
    # when the worker/beat process starts) clears every handler already on
    # the root logger by default (worker_hijack_root_logger=True) before
    # adding its own console handler — a handler attached at plain import
    # time would be wiped the moment the process actually starts. This
    # signal fires right after that bootstrap completes, so attaching here
    # instead lands on top of Celery's own handler rather than under it.
    init_logging("worker")


_tracer = trace.get_tracer("worker")
_task_counter = otel_metrics.get_meter("worker").create_counter(
    "worker.tasks",
    description="Count of Celery task executions, by task name and status",
)

# Per-task-id state bridging the prerun -> (optional) failure -> postrun
# signal sequence, since a span/context started on prerun can only be
# ended/detached once postrun fires for the same task_id.
_task_context: dict[str, dict] = {}


def _start_task_span(task_id=None, task=None, **_kwargs):
    task_name = task.name if task is not None else "unknown"
    span = _tracer.start_span(task_name)
    token = otel_context.attach(trace.set_span_in_context(span))
    _task_context[task_id] = {
        "span": span,
        "token": token,
        "task_name": task_name,
        "failed": False,
    }


def _record_task_failure(task_id=None, exception=None, **_kwargs):
    entry = _task_context.get(task_id)
    if entry is None:
        return
    entry["failed"] = True
    span = entry["span"]
    span.set_status(Status(StatusCode.ERROR, str(exception)))
    if exception is not None:
        span.record_exception(exception)


def _end_task_span(task_id=None, **_kwargs):
    entry = _task_context.pop(task_id, None)
    if entry is None:
        return
    span = entry["span"]
    if not entry["failed"]:
        span.set_status(Status(StatusCode.OK))
    span.end()
    otel_context.detach(entry["token"])
    _task_counter.add(
        1,
        {"task_name": entry["task_name"], "status": "failure" if entry["failed"] else "success"},
    )


def _register_observability_signal_handlers() -> None:
    if is_observability_disabled():
        return
    task_prerun.connect(_start_task_span)
    task_postrun.connect(_end_task_span)
    task_failure.connect(_record_task_failure)


_register_observability_signal_handlers()

app = Celery(
    "grandflow_worker",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=[
        "tasks.ai.cleanup_sessions",
        "tasks.debug.ping",
        "tasks.users.send_verification_email",
        "tasks.users.send_invite_email",
        "tasks.users.send_password_reset_email",
        "tasks.feedback.post_notification",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "tasks.ai.*": {"queue": "ai"},
        "tasks.budget.*": {"queue": "budget"},
        "tasks.users.*": {"queue": "users"},
        "tasks.debug.*": {"queue": "ai"},
        "tasks.feedback.*": {"queue": "feedback"},
    },
    beat_schedule={
        "cleanup-ai-sessions-daily": {
            "task": "tasks.ai.cleanup_sessions",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
