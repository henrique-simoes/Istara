import asyncio
import httpx
import os
import time
import json
from pathlib import Path

API_BASE = "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[2]
ADMIN_PASSWORD_ENV_FILES = (
    ROOT / ".env.local",
    ROOT / "backend" / ".env.local",
)


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


async def main():
    print("🚀 Starting Long-Horizon Orchestration Benchmark...")
    
    # 1. Get Admin Token
    admin_pass = os.getenv("ADMIN_PASSWORD", "").strip()
    if not admin_pass:
        try:
            admin_pass = load_admin_password()
        except RuntimeError as exc:
            print(f"❌ {exc}")
            return
        
    async with httpx.AsyncClient(timeout=300) as client:
        print("🔐 Authenticating...")
        login_res = await client.post(f"{API_BASE}/api/auth/login", json={"username": "admin", "password": admin_pass})
        if login_res.status_code != 200:
            print(f"❌ Auth failed: {login_res.text}")
            return
            
        token = login_res.json().get("token") or login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create Project
        print("📁 Creating Project...")
        proj_res = await client.post(
            f"{API_BASE}/api/projects", 
            json={
                "name": "[BENCHMARK] Long-Horizon Stress Test",
                "company_context": "Global HealthTech specializing in remote patient monitoring."
            },
            headers=headers
        )
        project_id = proj_res.json()["id"]
        print(f"✅ Project created: {project_id}")
        
        # 3. Upload Documents
        print("📄 Uploading Documents...")
        docs = [
            ("interview_p1.txt", "Patient reports difficulty with login sync. 'It takes too long to see my data.'"),
            ("interview_p2.txt", "Patient Marcus loves the medication tracker but hates the font size."),
            ("competitor_audit.md", "Competitor HealthSync has 2-tap login and 14pt minimum font."),
            ("survey_results.csv", "user_id,satisfaction,speed\n101,4,slow\n102,5,fast"),
            ("internal_spec.pdf", "Our current technical debt prevents sub-1s data hydration.")
        ]
        
        for name, content in docs:
            files = {"file": (name, content.encode('utf-8'), "text/plain")}
            await client.post(f"{API_BASE}/api/files/upload/{project_id}", files=files, headers=headers)
        print(f"✅ Uploaded {len(docs)} documents.")
        
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
            "message": prompt
        }
        
        print("⏳ Waiting for SSE stream (this will log all agent actions & tool calls)...")
        print("-" * 50)
        
        start_time = time.time()
        tool_calls = 0
        total_tokens = 0
        
        async with client.stream("POST", f"{API_BASE}/api/chat", json=chat_req, headers=headers) as response:
            if response.status_code != 200:
                body = await response.aread()
                print(f"❌ Chat failed with status {response.status_code}: {body.decode()}")
            else:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "tool_calls" in data:
                                for tc in data["tool_calls"]:
                                    fn = tc.get("function", {})
                                    name = fn.get("name", "unknown")
                                    args = fn.get("arguments", "{}")
                                    print(f"\n🛠️  [NATIVE TOOL CALL] {name}\n   Args: {args}")
                                    tool_calls += 1
                            elif "content" in data:
                                content = data["content"]
                                print(content, end="", flush=True)
                                if "[Tool:" in content:
                                    tool_calls += 1
                                total_tokens += 1
                        except json.JSONDecodeError:
                            pass
        
        elapsed = time.time() - start_time
        print("\n" + "-" * 50)
        print(f"✅ Chat completed in {elapsed:.2f}s. Tool calls: {tool_calls}")
        
        # 5. Check Orchestrator State (Tasks spawned)
        print("\n📋 Checking Task Queue (DeepPlanning Validation)...")
        tasks_res = await client.get(f"{API_BASE}/api/tasks?project_id={project_id}", headers=headers)
        tasks_data = tasks_res.json()
        tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("tasks", [])
        print(f"Total tasks spawned: {len(tasks)}")
        for t in tasks:
            print(f"  - [{t.get('status')}] {t.get('title')} (Skill: {t.get('skill_name', 'auto')})")
            
        # 6. Check A2A Messages
        print("\n🤖 Checking A2A Inter-Agent Communication...")
        a2a_res = await client.get(f"{API_BASE}/api/agents/a2a/log?limit=20", headers=headers)
        a2a_data = a2a_res.json()
        messages = a2a_data if isinstance(a2a_data, list) else a2a_data.get("messages", [])
        proj_messages = [m for m in messages if m.get("project_id") == project_id]
        print(f"Total A2A messages: {len(proj_messages)}")
        for m in proj_messages:
            print(f"  - {m.get('from_agent_id')} -> {m.get('to_agent_id')} [{m.get('message_type')}]: {m.get('content')[:100]}...")
            
        # 7. Check JSON Parse Metrics
        print("\n📊 Checking JSON Success Metrics...")
        metrics_res = await client.get(f"{API_BASE}/api/metrics/{project_id}/model-intelligence", headers=headers)
        leaderboard = metrics_res.json().get("leaderboard", [])
        for l in leaderboard:
            print(f"  - Model: {l.get('model_name')} | Skill: {l.get('skill_name')} | JSON Success: {l.get('json_parse_success_rate')*100 if l.get('json_parse_success_rate') is not None else 'N/A'}% | Executions: {l.get('executions')}")

if __name__ == "__main__":
    asyncio.run(main())
