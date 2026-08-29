import re
from pathlib import Path

import celery_app

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"
TASK_DECORATOR_RE = re.compile(r"@app\.task\b")


def _task_modules_on_disk() -> set[str]:
    """Every tasks/<pkg>/<file>.py that actually defines a Celery task
    (decorated with @app.task), as its dotted module path."""
    modules = set()
    for path in TASKS_DIR.glob("*/*.py"):
        if path.name in ("__init__.py",):
            continue
        if TASK_DECORATOR_RE.search(path.read_text()):
            modules.add(f"tasks.{path.parent.name}.{path.stem}")
    return modules


def test_every_task_module_on_disk_is_in_the_celery_include_list():
    """A task missing from celery_app.py's include list never loads in the real worker."""
    on_disk = _task_modules_on_disk()
    registered = set(celery_app.app.conf.include)
    missing = on_disk - registered
    assert not missing, f"Not registered in celery_app.py's include list: {missing}"
