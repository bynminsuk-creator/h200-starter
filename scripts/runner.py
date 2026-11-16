"""Run a job with an idle watchdog and retain a small, bounded result archive."""
import argparse
import datetime
import json
import math
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path


def stop(proc):
    if proc.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        proc.kill()
    proc.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-seconds", type=float, default=float(os.getenv("WATCHDOG_SECONDS", "2400")))
    parser.add_argument("--max-seconds", type=float, default=float(os.getenv("MAX_SECONDS", "3600")))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not all(math.isfinite(v) and v > 0 for v in (args.idle_seconds, args.max_seconds)):
        parser.error("Supply a command and positive watchdog limits.")
    root = Path(os.getenv("OUTPUT_ROOT", "/app/output/h200-starter"))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output = root / stamp
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(RUN_OUTPUT_DIR=str(output.resolve()), PYTHONUNBUFFERED="1")
    started = time.monotonic()
    last_output = started
    exit_code = 1
    reason = "launch_error"
    proc = None
    print(f"[start] output={output}; idle={args.idle_seconds:g}s; max={args.max_seconds:g}s", flush=True)
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env=env, start_new_session=(os.name == "posix"))
        events = queue.Queue(maxsize=128)

        def read_output():
            try:
                while True:
                    chunk = os.read(proc.stdout.fileno(), 4096)
                    if not chunk:
                        break
                    events.put(chunk)
            finally:
                events.put(None)

        threading.Thread(target=read_output, daemon=True).start()
        log_bytes = 0
        shown_bytes = 0
        output_closed = False
        with (output / "run.log").open("wb") as log:
            while True:
                now = time.monotonic()
                if now - started >= args.max_seconds or now - last_output >= args.idle_seconds:
                    reason = "deadline" if now - started >= args.max_seconds else "idle_timeout"
                    exit_code = 124
                    stop(proc)
                    print(f"\n[watchdog] {reason}", flush=True)
                    break
                try:
                    chunk = events.get(timeout=0.1)
                except queue.Empty:
                    if output_closed and proc.poll() is not None:
                        exit_code = proc.returncode
                        reason = "completed" if exit_code == 0 else "command_failed"
                        break
                    continue
                if chunk is None:
                    output_closed = True
                    # A process may close stdout and continue running; keep enforcing limits.
                    if proc.poll() is not None:
                        exit_code = proc.returncode
                        reason = "completed" if exit_code == 0 else "command_failed"
                        break
                    continue
                if chunk.strip():
                    last_output = time.monotonic()
                saved = chunk[:max(0, 8 * 1024**2 - log_bytes)]
                log.write(saved)
                log_bytes += len(saved)
                shown = chunk[:max(0, 12000 - shown_bytes)]
                if shown:
                    print(shown.decode("utf-8", errors="replace"), end="", flush=True)
                    shown_bytes += len(shown)
            if log_bytes >= 8 * 1024**2:
                print("\n[log] run.log truncated at 8 MiB", flush=True)
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", flush=True)
        reason = f"{type(exc).__name__}: {exc}"
    finally:
        if proc is not None:
            stop(proc)
        summary = {"status": "passed" if exit_code == 0 else "failed", "exit_code": exit_code,
                   "reason": reason, "elapsed_seconds": round(time.monotonic() - started, 3)}
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        files = [p for p in output.rglob("*") if p.is_file() and not p.is_symlink()]
        # Avoid copying large model/data directories into the archive by accident.
        if sum(p.stat().st_size for p in files) <= 100 * 1024**2:
            with zipfile.ZipFile(output / "results.zip", "w", zipfile.ZIP_DEFLATED) as archive:
                for path in files:
                    archive.write(path, str(path.relative_to(output)))
            print(f"\n[result] {output / 'results.zip'}", flush=True)
        else:
            print(f"\n[result] Archive skipped: results exceed 100 MiB; request files in {output}", flush=True)
        print("[summary] " + json.dumps(summary), flush=True)
    return exit_code if exit_code >= 0 else 128 - exit_code


if __name__ == "__main__":
    sys.exit(main())
