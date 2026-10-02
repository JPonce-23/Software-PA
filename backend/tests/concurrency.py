"""Observe exact PostgreSQL workers rather than global blocked-session counts."""

from contextvars import ContextVar
import threading
import time

from sqlalchemy import event, text

from app.database import engine


_worker = ContextVar("qa_postgresql_worker", default=None)


class PostgreSQLWorkers:
    def __init__(self):
        self.pids = {}
        self.statements = {}
        self.condition = threading.Condition()

    def __enter__(self):
        event.listen(engine, "before_cursor_execute", self.capture)
        return self

    def __exit__(self, *_):
        event.remove(engine, "before_cursor_execute", self.capture)

    def capture(self, connection, cursor, statement, parameters, context, many):
        worker = _worker.get()
        if worker is None or "sesion_usuario" in statement:
            return
        # The callback runs immediately before execution, including a lock wait.
        if not any(fragment in statement for fragment in (
            "FOR ", "INSERT INTO usuario_proyecto", "UPDATE proyecto ", "UPDATE usuario ",
            "pg_advisory_xact_lock",
        )):
            return
        pid = connection.connection.driver_connection.get_backend_pid()
        with self.condition:
            self.pids[worker] = pid
            self.statements.setdefault(worker, []).append(statement)
            self.condition.notify_all()

    def run(self, name, function, *args, **kwargs):
        token = _worker.set(name)
        try:
            return function(*args, **kwargs)
        finally:
            _worker.reset(token)

    def wait_pids(self, names, timeout=10):
        with self.condition:
            assert self.condition.wait_for(
                lambda: all(name in self.pids for name in names), timeout
            ), f"No se identificaron los trabajadores {names}"
            return [self.pids[name] for name in names]


def workers_are_blocked(observer, worker_pids, blocker_pids):
    rows = observer.execute(
        text("SELECT pid, pg_blocking_pids(pid) FROM pg_stat_activity WHERE pid = ANY(:pids)"),
        {"pids": list(worker_pids)},
    ).all()
    # A queued worker can wait on another worker behind the original blocker.
    waiting = {pid: set(blockers) for pid, blockers in rows}
    roots = set(blocker_pids)

    def reaches_root(pid, visited):
        if pid in roots:
            return True
        if pid in visited:
            return False
        return any(reaches_root(blocker, visited | {pid}) for blocker in waiting.get(pid, ()))

    return len(rows) == len(worker_pids) and all(reaches_root(pid, set()) for pid in worker_pids)


def wait_for_blocked_workers(worker_pids, blocker_pids, timeout=10):
    deadline = time.monotonic() + timeout
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as observer:
        while time.monotonic() < deadline:
            if workers_are_blocked(observer, worker_pids, blocker_pids):
                return
            time.sleep(0.02)
    raise AssertionError(f"Los PID {worker_pids} no esperan a los bloqueadores {blocker_pids}")
