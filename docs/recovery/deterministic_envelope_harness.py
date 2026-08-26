"""
Deterministic AI Envelope Execution & Verification Harness
System Standard for RAE Task Runners (Staci, BEAN, Nimbus)
"""

import sys
import subprocess
import time
import json
import urllib.request
from typing import Callable, Any, Optional

from credential_config import require_kernel_api_key

class DeterministicEnvelope:
    def __init__(self, agent_id: str, kernel_url: str = "https://rae-kernel.fly.dev", api_key: Optional[str] = None):
        self.agent_id = agent_id
        self.kernel_url = kernel_url
        self.api_key = require_kernel_api_key(api_key)

    def execute_task(self, task_id: str, command: list[str], verifier_fn: Optional[Callable[[str], bool]] = None) -> dict:
        """
        Executes command inside a strict deterministic envelope.
        Checks process exit code, stdout artifacts, and reports verified telemetry.
        """
        start_time = time.time()
        print(f"[{self.agent_id}] Executing Task '{task_id}': {' '.join(command)}")

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            duration_ms = int((time.time() - start_time) * 1000)

            # Verification Check 1: Exit Code
            if result.returncode != 0:
                print(f"[{self.agent_id}] ERROR: Process exited with non-zero code {result.returncode}")
                return self._report_failure(task_id, f"Non-zero exit code {result.returncode}", result.stderr)

            # Verification Check 2: Custom Verifier Heuristic
            if verifier_fn and not verifier_fn(result.stdout):
                print(f"[{self.agent_id}] ERROR: Verification heuristic failed on output")
                return self._report_failure(task_id, "Verification heuristic failed", result.stdout)

            print(f"[{self.agent_id}] SUCCESS: Task '{task_id}' verified in {duration_ms}ms")
            receipt = {
                "status": "COMPLETED",
                "task_id": task_id,
                "agent_id": self.agent_id,
                "exit_code": 0,
                "duration_ms": duration_ms,
                "stdout_snippet": result.stdout[:200].strip()
            }
            self._send_telemetry("task.completed", receipt)
            return receipt

        except subprocess.TimeoutExpired:
            print(f"[{self.agent_id}] ERROR: Task execution timed out after 120s")
            return self._report_failure(task_id, "Timeout after 120s", "")
        except Exception as e:
            print(f"[{self.agent_id}] ERROR: Execution exception: {e}")
            return self._report_failure(task_id, f"Exception: {str(e)}", "")

    def _report_failure(self, task_id: str, reason: str, details: str) -> dict:
        failure_receipt = {
            "status": "FAILED",
            "task_id": task_id,
            "agent_id": self.agent_id,
            "reason": reason,
            "details_snippet": details[:200].strip()
        }
        self._send_telemetry("task.failed", failure_receipt)
        return failure_receipt

    def _send_telemetry(self, event_type: str, payload: dict):
        url = f"{self.kernel_url}/v1/events"
        event_data = {
            "type": event_type,
            "source": self.agent_id,
            "tenant_id": "default",
            "deduplication_key": f"{self.agent_id}_{payload.get('task_id', 'evt')}_{int(time.time())}",
            "payload": payload
        }
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(event_data).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req) as resp:
                print(f"[{self.agent_id}] Telemetry sent: {event_type} (HTTP {resp.status})")
        except Exception as e:
            print(f"[{self.agent_id}] Telemetry send warning: {e}")

if __name__ == "__main__":
    print("Testing Deterministic AI Envelope Harness...")
    envelope = DeterministicEnvelope(agent_id="staci-core-runner")
    
    # Test 1: Successful command execution
    res1 = envelope.execute_task("TEST-TASK-001", [sys.executable, "-c", "print('Hello RAE Verification')"])
    assert res1["status"] == "COMPLETED"
    
    # Test 2: Failing command execution
    res2 = envelope.execute_task("TEST-TASK-002", [sys.executable, "-c", "import sys; sys.exit(1)"])
    assert res2["status"] == "FAILED"
    
    print("Deterministic AI Envelope Verification Passed All Assertions!")
