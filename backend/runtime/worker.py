"""Run with python -m runtime.worker. One worker replica per deployment."""
import asyncio
import json
import logging
import os
import sys
import time
from config import settings
from services.database import initialize
from runtime import jobs

async def execute(job):
    payload = json.loads(job["payload"])
    env = dict(os.environ, AGENT_NAME=job["kind"], ARIA_JOB_ID=job["id"])
    process = None
    try:
        process = await asyncio.create_subprocess_exec(sys.executable, "-m", "runtime.runner", env=env,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=None,
            limit=2 * 1024 * 1024)
        process.stdin.write(json.dumps(payload).encode())
        await process.stdin.drain()
        process.stdin.close()
        deadline = time.monotonic() + settings.job_timeout_seconds
        result_seen = False
        error_seen = False
        while True:
            if time.monotonic() > deadline: raise TimeoutError("Agent exceeded its execution deadline")
            try: line = await asyncio.wait_for(process.stdout.readline(), timeout=5)
            except asyncio.TimeoutError:
                jobs.heartbeat(job["id"])
                continue
            if not line: break
            jobs.heartbeat(job["id"])
            try: event = json.loads(line)
            except (ValueError, UnicodeDecodeError): continue
            if not isinstance(event, dict) or event.get("type") not in {"progress", "result", "error"}: continue
            jobs.append_event(job["id"], event)
            result_seen |= event["type"] == "result"
            result = event.get("result")
            error_seen |= event["type"] == "error" or (isinstance(result, dict) and
                (bool(result.get("error")) or str(result.get("status", "")).lower() == "failed"))
        code = await asyncio.wait_for(process.wait(), timeout=max(1, deadline - time.monotonic()))
        if code or not result_seen:
            raise RuntimeError("Agent stopped without a complete result; check ERP state before retrying")
        jobs.set_status(job["id"], "failed" if error_seen else "completed")
    except BaseException as exc:
        if process is not None and process.returncode is None:
            process.kill()
            await process.wait()
        jobs.set_status(job["id"], "interrupted")
        jobs.append_event(job["id"], {"type": "error", "error": str(exc) or "Worker stopped"})
        if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError)): raise

async def main():
    initialize()
    if len(settings.service_secret) < 32: raise RuntimeError("Configure SERVICE_SECRET before starting the worker")
    while True:
        jobs.interrupt_stale()
        job = jobs.claim()
        if job: await execute(job)
        else: await asyncio.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
