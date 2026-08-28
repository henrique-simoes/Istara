import asyncio
import httpx
import os
import time
import json
from collections import Counter
from pathlib import Path
from typing import Any

API_BASE = os.environ.get("ISTARA_API_URL", "http://localhost:8000")
# Agentic core under test (CF-SPEC-1 Phase 5). A live benchmark must name the
# engine explicitly; accepting the dispatcher default makes its result
# impossible to attribute when settings or operator flags change.
ENGINE = os.environ.get("ISTARA_LONG_HORIZON_ENGINE", "").strip().lower() or None
SUPPORTED_ENGINES = frozenset({"legacy", "pi"})
ROOT = Path(__file__).resolve().parents[2]
ADMIN_PASSWORD_ENV_FILES = (
    ROOT / ".env.local",
    ROOT / "backend" / ".env.local",
)


class BenchmarkFailure(RuntimeError):
    """A transport or semantic failure that must make the benchmark non-zero."""


def _require_explicit_engine() -> str:
    """Require a supported engine before creating any benchmark side effects."""
    if ENGINE == "legacy":
        return "legacy"
    if ENGINE == "pi":
        return "pi"
    if ENGINE not in SUPPORTED_ENGINES:
        configured = "<unset>" if ENGINE is None else "<unsupported>"
        raise BenchmarkFailure(
            "long-horizon benchmark requires ISTARA_LONG_HORIZON_ENGINE=legacy "
            f"or pi; got {configured!r}"
        )
    raise AssertionError("unreachable engine validation branch")


def _require_status(response: httpx.Response, operation: str, *expected: int) -> None:
    """Fail closed when an API call is not one of its documented success statuses."""
    accepted = expected or (200,)
    if response.status_code not in accepted:
        body = response.text[:500].replace("\n", " ")
        raise BenchmarkFailure(
            f"{operation} failed with HTTP {response.status_code}: {body or '<empty body>'}"
        )


def _json_payload(response: httpx.Response, operation: str) -> Any:
    """Decode a successful API response, preserving the operation in failures."""
    try:
        return response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise BenchmarkFailure(f"{operation} returned invalid JSON") from exc


def _tool_call_count(events: list[dict]) -> int:
    """Count canonical SSE tool-call events exactly once (never text markers)."""
    return sum(1 for event in events if event.get("type") == "tool_call")


def _require_done_tool_contract(
    events: list[dict],
    operation: str,
    *,
    required_tools: tuple[str, ...] = (),
    require_tool_result: bool = False,
) -> dict:
    """Require the terminal SSE event to account for every executed tool call.

    A streamed answer can look successful even when the model only *mentions* a
    tool.  The chat route's terminal ``done.tools_used`` list is the route-level
    execution receipt, so the benchmark compares it with canonical ``tool_call``
    events and optionally requires a specific tool for the scenario.  Pi's
    governed path can also prove the causal chain: call -> redacted authority
    receipt -> later model content.  The receipt has no raw tool output.
    """
    done_events = [event for event in events if event.get("type") == "done"]
    if not done_events:
        raise BenchmarkFailure(f"{operation} ended without a terminal done event")
    done = done_events[-1]
    tools_used = done.get("tools_used")
    if not isinstance(tools_used, list) or any(not isinstance(name, str) or not name.strip() for name in tools_used):
        raise BenchmarkFailure(f"{operation} terminal done event has no valid tools_used receipt")

    called_tools = [
        event.get("tool")
        for event in events
        if event.get("type") == "tool_call" and isinstance(event.get("tool"), str)
    ]
    missing = Counter(called_tools) - Counter(tools_used)
    if missing:
        names = ", ".join(sorted(missing))
        raise BenchmarkFailure(
            f"{operation} terminal done event does not report executed tool(s): {names}"
        )
    missing_required = [tool for tool in required_tools if tool not in tools_used]
    if missing_required:
        raise BenchmarkFailure(
            f"{operation} did not report required executed tool(s): {', '.join(missing_required)}"
        )
    if require_tool_result and called_tools:
        calls = [
            (index, event)
            for index, event in enumerate(events)
            if event.get("type") == "tool_call" and isinstance(event.get("tool"), str)
        ]
        receipts = [
            (index, event)
            for index, event in enumerate(events)
            if event.get("type") == "tool_result"
        ]
        receipt_indexes: list[int] = []
        for call_index, call in calls:
            call_id = call.get("tool_call_id")
            matching = [
                (receipt_index, receipt)
                for receipt_index, receipt in receipts
                if receipt_index > call_index
                and receipt.get("tool") == call.get("tool")
                and receipt.get("tool_call_id") == call_id
            ]
            if not isinstance(call_id, str) or not call_id or not matching:
                raise BenchmarkFailure(
                    f"{operation} tool call {call.get('tool')!r} has no matching tool-result receipt"
                )
            receipt_indexes.append(matching[0][0])
        final_receipt = max(receipt_indexes)
        if not any(
            index > final_receipt and event.get("type") == "chunk" and event.get("content")
            for index, event in enumerate(events)
        ):
            raise BenchmarkFailure(f"{operation} has no model response after tool-result receipt")
    return done


def _require_persisted_tasks(payload: Any, project_id: str) -> list[dict]:
    """Require at least one non-empty task persisted under the benchmark project."""
    tasks = payload if isinstance(payload, list) else payload.get("tasks", []) if isinstance(payload, dict) else []
    if not tasks:
        raise BenchmarkFailure("task queue contains no persisted tasks after create_task")
    if not all(isinstance(task, dict) for task in tasks):
        raise BenchmarkFailure("task queue contains a non-object task")
    for task in tasks:
        if task.get("project_id") != project_id:
            raise BenchmarkFailure("task queue returned a task outside the benchmark project")
        if not isinstance(task.get("id"), str) or not task["id"].strip():
            raise BenchmarkFailure("persisted task has no id")
        if not isinstance(task.get("title"), str) or not task["title"].strip():
            raise BenchmarkFailure("persisted task has no title")
    return tasks


def _require_usage_ledger(
    payload: Any,
    *,
    expected_engine: str | None = None,
    expected_session_id: str | None = None,
    expected_task_id: str | None = None,
    min_rows: int = 2,
    min_turns: int = 2,
    require_route_provenance: bool = False,
) -> dict:
    """Require per-dispatch rows proving the turns' causal identity.

    The baseline oracle checks session and engine continuity. Live acceptance
    additionally enables route provenance so every successful receipt has a
    unique id, model/endpoint identity, and an explicit task binding. Keeping
    that stricter mode opt-in preserves small unit fixtures while ensuring the
    Docker workload cannot pass on aggregate counters alone.
    """
    if not isinstance(payload, dict):
        raise BenchmarkFailure("chat usage endpoint returned a non-object payload")
    if expected_engine not in SUPPORTED_ENGINES:
        configured = expected_engine or "<unset>"
        raise BenchmarkFailure(
            "chat usage validation requires an explicit expected engine "
            f"(legacy or pi); got {configured!r}"
        )
    if not isinstance(expected_session_id, str) or not expected_session_id.strip():
        raise BenchmarkFailure("chat usage validation requires the benchmark session id")
    try:
        row_count = int(payload.get("row_count") or 0)
        turns = int(payload.get("turns") or 0)
        total_tokens = int(payload.get("total_tokens") or 0)
    except (TypeError, ValueError) as exc:
        raise BenchmarkFailure("chat usage endpoint returned non-numeric ledger totals") from exc
    if row_count < min_rows:
        raise BenchmarkFailure(
            f"chat usage ledger contains fewer than {min_rows} recorded row(s): {row_count}"
        )
    if turns < min_turns:
        raise BenchmarkFailure(
            f"chat usage ledger contains fewer than {min_turns} recorded turn(s): {turns}"
        )
    if total_tokens <= 0:
        raise BenchmarkFailure("chat usage ledger contains no positive token total")
    _require_chat_dispatch_rows(
        payload,
        row_count,
        expected_engine,
        expected_session_id,
        min_rows,
        expected_task_id=expected_task_id,
        require_route_provenance=require_route_provenance,
    )
    latest = payload.get("latest")
    if not isinstance(latest, dict) or not isinstance(latest.get("engine"), str) or not latest["engine"].strip():
        raise BenchmarkFailure("chat usage ledger has no effective engine provenance")
    if latest["engine"].strip().lower() != expected_engine:
        raise BenchmarkFailure(
            f"chat usage ledger engine {latest['engine']!r} does not match requested {expected_engine!r}"
        )
    return payload


def _require_chat_dispatch_rows(
    payload: dict,
    row_count: int,
    expected_engine: str,
    expected_session_id: str,
    min_rows: int,
    *,
    expected_task_id: str | None = None,
    require_route_provenance: bool = False,
) -> None:
    """Require complete content-free identity rows for the chat turns."""
    rows = payload.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise BenchmarkFailure("chat usage ledger has no per-dispatch identity rows")
    if len(rows) != row_count:
        raise BenchmarkFailure(
            f"chat usage ledger row_count {row_count} disagrees with identity rows {len(rows)}"
        )
    chat_rows = [row for row in rows if row.get("purpose") == "chat_turn"]
    if len(chat_rows) < min_rows:
        raise BenchmarkFailure(
            f"chat usage ledger contains fewer than {min_rows} chat-turn row(s): {len(chat_rows)}"
        )
    mismatched = [
        row.get("engine")
        for row in chat_rows
        if not isinstance(row.get("engine"), str)
        or row["engine"].strip().lower() != expected_engine
    ]
    if mismatched:
        raise BenchmarkFailure(
            f"chat usage ledger chat-turn engine(s) {mismatched!r} do not all match "
            f"requested {expected_engine!r}"
        )
    missing_session = [
        row.get("session_id")
        for row in chat_rows
        if row.get("session_id") != expected_session_id
    ]
    if missing_session:
        raise BenchmarkFailure(
            "chat usage ledger chat-turn session id(s) do not all match the benchmark session"
        )
    if expected_task_id is not None:
        mismatched_tasks = [
            row.get("task_id")
            for row in chat_rows
            if row.get("task_id") != expected_task_id
        ]
        if mismatched_tasks:
            raise BenchmarkFailure(
                "chat usage ledger chat-turn task id(s) do not all match the benchmark task"
            )
    if require_route_provenance:
        receipt_ids = [row.get("id") for row in chat_rows]
        if any(
            not isinstance(receipt_id, str) or not receipt_id.strip()
            for receipt_id in receipt_ids
        ):
            raise BenchmarkFailure("chat usage ledger has a missing dispatch receipt id")
        if len(set(receipt_ids)) != len(receipt_ids):
            raise BenchmarkFailure("chat usage ledger does not contain unique receipt ids")
        incomplete = [
            row
            for row in chat_rows
            if row.get("outcome") != "success"
            or not isinstance(row.get("model"), str)
            or not row["model"].strip()
            or not isinstance(row.get("endpoint_id"), str)
            or not row["endpoint_id"].strip()
        ]
        if incomplete:
            raise BenchmarkFailure(
                "chat usage ledger does not contain successful route-provenanced receipts"
            )


def _require_session_id(payload: Any) -> str:
    session_id = payload.get("id") if isinstance(payload, dict) else None
    if not isinstance(session_id, str) or not session_id.strip():
        raise BenchmarkFailure("session creation returned no session id")
    return session_id


def _require_history_continuity(history_payload: Any, first: str, second: str) -> None:
    """Require the persisted transcript to contain both complete user/assistant turns."""
    messages = history_payload if isinstance(history_payload, list) else []
    if len(messages) < 4:
        raise BenchmarkFailure(
            f"chat history contains {len(messages)} messages; expected two persisted turns"
        )
    if not all(isinstance(message, dict) for message in messages[-4:]):
        raise BenchmarkFailure("chat history contains a non-object message")
    roles_and_content = [(m.get("role"), m.get("content")) for m in messages[-4:]]
    expected = [("user", first), ("assistant", None), ("user", second), ("assistant", None)]
    for index, ((role, content), (expected_role, expected_content)) in enumerate(
        zip(roles_and_content, expected), start=1
    ):
        if role != expected_role or (
            expected_content is not None and content != expected_content
        ):
            raise BenchmarkFailure(
                f"chat history continuity mismatch at message {index}: "
                f"got role={role!r} content={content!r}"
            )
        if expected_content is None and (
            not isinstance(content, str) or not content.strip()
        ):
            raise BenchmarkFailure(f"chat history message {index} has no assistant content")


async def _consume_chat_stream(response: httpx.Response, operation: str) -> list[dict]:
    """Parse one chat SSE response and require a terminal successful done event."""
    if response.status_code != 200:
        body = (await response.aread()).decode(errors="replace")[:500].replace("\n", " ")
        raise BenchmarkFailure(
            f"{operation} failed with HTTP {response.status_code}: {body or '<empty body>'}"
        )

    events: list[dict] = []
    async for line in response.aiter_lines():
        if not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        try:
            event = json.loads(data_str)
        except json.JSONDecodeError as exc:
            raise BenchmarkFailure(f"{operation} emitted malformed SSE JSON") from exc
        if not isinstance(event, dict):
            raise BenchmarkFailure(f"{operation} emitted a non-object SSE event")
        events.append(event)

    errors = [event for event in events if event.get("type") in {"error", "aborted"}]
    if errors:
        detail = errors[-1].get("detail") or errors[-1].get("error") or errors[-1]
        raise BenchmarkFailure(f"{operation} emitted terminal error: {detail}")
    done_events = [event for event in events if event.get("type") == "done"]
    if not done_events or not done_events[-1].get("message_id"):
        raise BenchmarkFailure(f"{operation} ended without a persisted assistant message")
    return events


def _parse_admin_password(raw_line: str) -> str:
    line = raw_line.strip()
    if line.startswith("export "):
        line = line[len("export "):].strip()
    if not line.startswith("ADMIN_PASSWORD="):
        return ""
    value = line.split("=", 1)[1].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def load_admin_password() -> str:
    for path in ADMIN_PASSWORD_ENV_FILES:
        if not path.exists() or not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            file_password = _parse_admin_password(raw_line)
            if file_password:
                return file_password

    raise RuntimeError(
        "Long-horizon benchmark requires ADMIN_PASSWORD in the environment "
        "or a gitignored .env.local file."
    )


def extract_total_tokens(events: list[dict]) -> int | None:
    """Return provider-reported total tokens from a chat SSE stream, or None if absent.

    The authoritative source of token accounting is the agentic usage ledger
    (``agentic_usage_rows``, master plan §5.5); the SSE stream is not a token meter. This
    reader takes provider-reported ``usage`` when the stream carries it and otherwise
    returns None — it never counts streamed content chunks as tokens (benchmark task B0-3:
    the prior ``total_tokens += 1`` per-chunk bug fabricated a nonsense token figure).
    """
    total: int | None = None
    for event in events:
        usage = event.get("usage") if isinstance(event, dict) else None
        if isinstance(usage, dict):
            value = usage.get("total_tokens", usage.get("totalTokens"))
            if value is not None:
                total = int(value)
    return total


BENCHMARK_DOCUMENTS = (
    ("interview_p1.txt", "Patient reports difficulty with login sync. 'It takes too long to see my data.'"),
    ("interview_p2.txt", "Patient Marcus loves the medication tracker but hates the font size."),
    ("competitor_audit.md", "Competitor HealthSync has 2-tap login and 14pt minimum font."),
    ("survey_results.csv", "user_id,satisfaction,speed\\n101,4,slow\\n102,5,fast"),
    ("internal_spec.pdf", "Our current technical debt prevents sub-1s data hydration."),
)


async def _create_project_and_session(client: httpx.AsyncClient, headers: dict[str, str]) -> tuple[str, str]:
    print("📁 Creating Project...")
    project_res = await client.post(
        f"{API_BASE}/api/projects",
        json={
            "name": "[BENCHMARK] Long-Horizon Stress Test",
            "company_context": "Global HealthTech specializing in remote patient monitoring.",
        },
        headers=headers,
    )
    _require_status(project_res, "project creation", 200, 201)
    project_payload = _json_payload(project_res, "project creation")
    project_id = project_payload.get("id") if isinstance(project_payload, dict) else None
    if not isinstance(project_id, str) or not project_id.strip():
        raise BenchmarkFailure("project creation returned no project id")
    print(f"✅ Project created: {project_id}")

    print("🧵 Creating a dedicated chat session...")
    session_res = await client.post(
        f"{API_BASE}/api/sessions",
        json={"project_id": project_id, "title": "Long-Horizon Stress Test"},
        headers=headers,
    )
    _require_status(session_res, "chat session creation", 200, 201)
    session_id = _require_session_id(_json_payload(session_res, "chat session creation"))
    print(f"✅ Chat session created: {session_id}")
    return project_id, session_id


async def _create_benchmark_task(
    client: httpx.AsyncClient, headers: dict[str, str], project_id: str
) -> str:
    """Create the causal task anchor shared by both long-horizon chat turns."""
    task_res = await client.post(
        f"{API_BASE}/api/tasks",
        json={
            "project_id": project_id,
            "title": "Long-horizon research spine benchmark",
            "description": (
                "Anchor task for proving that both bounded chat turns share one "
                "project-scoped execution and usage lineage."
            ),
        },
        headers=headers,
    )
    _require_status(task_res, "benchmark task creation", 200, 201)
    task_payload = _json_payload(task_res, "benchmark task creation")
    task_id = task_payload.get("id") if isinstance(task_payload, dict) else None
    if not isinstance(task_id, str) or not task_id.strip():
        raise BenchmarkFailure("benchmark task creation returned no task id")
    print(f"✅ Benchmark task anchor created: {task_id}")
    return task_id


async def _upload_documents(
    client: httpx.AsyncClient, headers: dict[str, str], project_id: str
) -> None:
    print("📄 Uploading Documents...")
    for name, content in BENCHMARK_DOCUMENTS:
        files = {"file": (name, content.encode("utf-8"), "text/plain")}
        upload_res = await client.post(
            f"{API_BASE}/api/files/upload/{project_id}", files=files, headers=headers
        )
        _require_status(upload_res, f"upload {name}", 200, 201, 202)
    print(f"✅ Uploaded {len(BENCHMARK_DOCUMENTS)} documents.")


async def _run_chat_turn(
    client: httpx.AsyncClient,
    request_payload: dict[str, str],
    headers: dict[str, str],
    operation: str,
) -> tuple[list[dict], float]:
    started = time.time()
    async with client.stream(
        "POST", f"{API_BASE}/api/chat", json=request_payload, headers=headers
    ) as response:
        events = await _consume_chat_stream(response, operation)
    return events, time.time() - started


def _print_tool_events(events: list[dict]) -> None:
    for event in events:
        if event.get("type") == "tool_call":
            print(
                f"\n🛠️  [TOOL CALL] {event.get('tool', 'unknown')}\n"
                f"   Args: {json.dumps(event.get('params', {}), sort_keys=True)}"
            )
        elif event.get("type") == "chunk":
            print(event.get("content", ""), end="", flush=True)


async def _run_benchmark() -> None:
    print("🚀 Starting Long-Horizon Orchestration Benchmark...")
    engine = _require_explicit_engine()

    # 1. Get Admin Token
    admin_pass = os.getenv("ADMIN_PASSWORD", "").strip()
    if not admin_pass:
        try:
            admin_pass = load_admin_password()
        except RuntimeError as exc:
            raise BenchmarkFailure(str(exc)) from exc

    async with httpx.AsyncClient(timeout=300) as client:
        print("🔐 Authenticating...")
        login_res = await client.post(f"{API_BASE}/api/auth/login", json={"username": "admin", "password": admin_pass})
        _require_status(login_res, "admin login")

        login_payload = _json_payload(login_res, "admin login")
        token = login_payload.get("token") or login_payload.get("access_token")
        if not isinstance(token, str) or not token.strip():
            raise BenchmarkFailure("admin login returned no access token")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Project and session; then upload source material.
        project_id, session_id = await _create_project_and_session(client, headers)
        benchmark_task_id = await _create_benchmark_task(client, headers, project_id)
        await _upload_documents(client, headers, project_id)

        # 4. Send Complex Chat Request
        print("\n💬 Sending Complex Long-Horizon Prompt...")
        prompt = (
            "I need a comprehensive analysis. Cross-reference the patient complaints about speed "
            "with our competitor audit and technical specs. Propose a journey map that solves this. "
            "IMPORTANT: You MUST use the create_task tool IMMEDIATELY to create specific tasks for each step "
            "of your proposed research plan (e.g., 'Thematic Analysis', 'Journey Mapping') before you finish responding. Do not ask for permission."
        )

        chat_req = {
            "project_id": project_id,
            "session_id": session_id,
            "task_id": benchmark_task_id,
            "message": prompt
        }

        chat_headers = dict(headers)
        chat_headers["x-istara-agent-engine"] = engine

        print("⏳ Waiting for SSE stream (this will log all agent actions & tool calls)...")
        print("-" * 50)

        stream_events: list[dict] = []
        stream_events, elapsed = await _run_chat_turn(
            client, chat_req, chat_headers, "first long-horizon chat turn"
        )
        _print_tool_events(stream_events)
        first_done = _require_done_tool_contract(
            stream_events,
            "first long-horizon chat turn",
            required_tools=("create_task",),
            require_tool_result=engine == "pi",
        )
        print(f"✅ First terminal receipt: tools_used={first_done['tools_used']}")
        # Token accounting comes from provider-reported usage (or the usage ledger),
        # never from a streamed-chunk count (benchmark task B0-3).
        total_tokens = extract_total_tokens(stream_events)
        tokens_label = total_tokens if total_tokens is not None else "n/a (see agentic usage ledger)"
        first_tool_calls = _tool_call_count(stream_events)
        if first_tool_calls < 1:
            raise BenchmarkFailure(
                "first long-horizon chat turn completed without an executed tool-call event"
            )
        print("\n" + "-" * 50)
        print(
            f"✅ First chat turn completed in {elapsed:.2f}s. Tool calls: "
            f"{first_tool_calls}. Provider tokens: {tokens_label}"
        )

        print("\n💬 Sending a second turn over the same persisted session...")
        second_message = (
            "Continue from the plan you just created. Summarize the next research step and "
            "identify which persisted task should be executed first."
        )
        second_req = {
            "project_id": project_id,
            "session_id": session_id,
            "task_id": benchmark_task_id,
            "message": second_message,
        }
        second_events, second_elapsed = await _run_chat_turn(
            client, second_req, chat_headers, "second long-horizon chat turn"
        )
        _print_tool_events(second_events)
        second_done = _require_done_tool_contract(
            second_events, "second long-horizon chat turn"
        )
        print(f"✅ Second terminal receipt: tools_used={second_done['tools_used']}")
        second_tokens = extract_total_tokens(second_events)
        print(
            f"\n✅ Second chat turn completed in {second_elapsed:.2f}s. "
            f"Tool calls: {_tool_call_count(second_events)}. Provider tokens: "
            f"{second_tokens if second_tokens is not None else 'n/a (see agentic usage ledger)'}"
        )

        history_res = await client.get(
            f"{API_BASE}/api/chat/history/{project_id}",
            params={"session_id": session_id, "limit": 50},
            headers=headers,
        )
        _require_status(history_res, "persisted chat history")
        history_payload = _json_payload(history_res, "persisted chat history")
        _require_history_continuity(history_payload, prompt, second_message)
        print("✅ Persisted history contains both complete user/assistant turns.")

        # 5. Check Orchestrator State (Tasks spawned)
        print("\n📋 Checking Task Queue (DeepPlanning Validation)...")
        tasks_res = await client.get(f"{API_BASE}/api/tasks?project_id={project_id}", headers=headers)
        _require_status(tasks_res, "task queue inspection")
        tasks_data = _json_payload(tasks_res, "task queue inspection")
        tasks = _require_persisted_tasks(tasks_data, project_id)
        if not any(task.get("id") == benchmark_task_id for task in tasks):
            raise BenchmarkFailure(
                "task queue does not contain the benchmark task anchor used by both turns"
            )
        print(f"Total tasks spawned: {len(tasks)}")
        for t in tasks:
            print(f"  - [{t.get('status')}] {t.get('title')} (Skill: {t.get('skill_name', 'auto')})")

        # 6. Check A2A Messages
        print("\n🤖 Checking A2A Inter-Agent Communication...")
        a2a_res = await client.get(
            f"{API_BASE}/api/agents/a2a/log?limit=20&project_id={project_id}",
            headers=headers,
        )
        _require_status(a2a_res, "A2A log inspection")
        a2a_data = _json_payload(a2a_res, "A2A log inspection")
        messages = a2a_data if isinstance(a2a_data, list) else a2a_data.get("messages", [])
        proj_messages = [m for m in messages if m.get("project_id") == project_id]
        print(f"Total A2A messages: {len(proj_messages)}")
        for m in proj_messages:
            print(f"  - {m.get('from_agent_id')} -> {m.get('to_agent_id')} [{m.get('message_type')}]: {m.get('content')[:100]}...")

        # 7. Check JSON Parse Metrics
        print("\n📊 Checking JSON Success Metrics...")
        metrics_res = await client.get(f"{API_BASE}/api/metrics/{project_id}/model-intelligence", headers=headers)
        _require_status(metrics_res, "model-intelligence metrics inspection")
        metrics_payload = _json_payload(metrics_res, "model-intelligence metrics inspection")
        leaderboard = metrics_payload.get("leaderboard", []) if isinstance(metrics_payload, dict) else []
        for entry in leaderboard:
            print(f"  - Model: {entry.get('model_name')} | Skill: {entry.get('skill_name')} | JSON Success: {entry.get('json_parse_success_rate')*100 if entry.get('json_parse_success_rate') is not None else 'N/A'}% | Executions: {entry.get('executions')}")

        usage_res = await client.get(
            f"{API_BASE}/api/chat/usage/{project_id}",
            params={"session_id": session_id},
            headers=headers,
        )
        _require_status(usage_res, "chat usage ledger inspection")
        usage_payload = _require_usage_ledger(
            _json_payload(usage_res, "chat usage ledger inspection"),
            expected_engine=engine,
            expected_session_id=session_id,
            expected_task_id=benchmark_task_id,
            require_route_provenance=True,
        )
        print(
            "✅ Usage ledger proves both turns: "
            f"rows={usage_payload['row_count']} turns={usage_payload['turns']} "
            f"tokens={usage_payload['total_tokens']} engine={usage_payload['latest']['engine']}"
        )


async def main() -> int:
    try:
        await _run_benchmark()
    except (BenchmarkFailure, httpx.HTTPError) as exc:
        print(f"❌ Benchmark failed closed: {exc}")
        return 1
    except Exception as exc:
        print(f"❌ Benchmark failed closed with unexpected error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
