"""One bounded child per comparison; formulas and external references never execute."""
import json
import multiprocessing as mp
import os

from .compare import compare_documents, validate_policy
from .models import MAX_FILE_BYTES, MAX_RESULT_BYTES, WORKER_SECONDS, AuditError


def _child(send, before, before_name, after, after_name, options):
    try:
        if os.name == "posix":
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        from .readers import read_document
        policy = validate_policy(options)
        b = read_document(before, before_name, policy["before"])
        a = read_document(after, after_name, policy["after"])
        report = compare_documents(b, a, policy)
        payload = json.dumps({"report": report}, ensure_ascii=True, allow_nan=False).encode("utf-8")
        if len(payload) > MAX_RESULT_BYTES:
            raise AuditError("Report exceeds16MiB; reduce input/scope")
    except Exception as exc:
        payload = json.dumps({"error": f"{type(exc).__name__}: {str(exc)[:1000]}"}, ensure_ascii=True).encode()
    try:
        send.send_bytes(payload)
    finally:
        send.close()


def audit_bytes(before, before_name, after, after_name, options=None):
    """Return an evidence report or raise ValueError. No local paths or writes accepted."""
    if not isinstance(before, bytes) or not isinstance(after, bytes):
        raise AuditError("Input content must be bytes")
    if len(before) > MAX_FILE_BYTES or len(after) > MAX_FILE_BYTES:
        raise AuditError("Input exceeds5MiB/file")
    if any(not isinstance(name, str) or len(name) > 256 for name in (before_name, after_name)):
        raise AuditError("Invalid input file name")
    policy = validate_policy(options)
    context = mp.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(send, before, before_name, after, after_name, policy), daemon=True)
    try:
        process.start(); send.close()
        if not receive.poll(WORKER_SECONDS):
            raise AuditError("Comparison exceeded30seconds; no fidelity conclusion")
        try:
            payload = receive.recv_bytes(MAX_RESULT_BYTES)
        except (EOFError, OSError) as exc:
            raise AuditError("Worker failed or exceeded result limit; no conclusion") from exc
        result = json.loads(payload)
        if "error" in result:
            raise AuditError(result["error"])
        return result["report"]
    finally:
        receive.close(); send.close()
        if process.pid is not None:
            process.join(0.2)
            if process.is_alive():
                process.terminate(); process.join(2)
            if process.is_alive():
                process.kill(); process.join()
