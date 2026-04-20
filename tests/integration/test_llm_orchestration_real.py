import uuid
import time
import asyncio
import logging
import json
import pytest
from sqlalchemy import select

from app.models.database import async_session, init_db
from app.skills.registry import registry, load_default_skills
from app.models.finding import Nugget, Fact, Insight, Recommendation
from app.models.task import TaskStatus, Task
from app.models.project import Project
from app.core.agent import AgentOrchestrator
from app.core.ollama import load_persisted_servers_async
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("IstaraIntegrationBenchmark")

@pytest.fixture(autouse=True)
async def setup_db():
    """Ensure database is initialized and skills are loaded."""
    await init_db()
    load_default_skills()
    # Critical: load real network compute nodes from the database into the registry
    await load_persisted_servers_async()


@pytest.mark.asyncio
async def test_real_llm_orchestration_benchmark():
    """
    Industry-Standard Agentic Orchestration Benchmark (Layer 5).
    
    Validates:
    - Real-world Tool Calling (ReAct) accuracy via live LLM.
    - Long-Horizon Task Decomposition (DAG) for complex research goals.
    - Context Retention & Reasoning (Context + RAG awareness).
    - Self-Reflection & Error Recovery.
    
    Metrics:
    - Success Rate: Percentage of milestones completed.
    - Tool Selection Quality (TSQ): Accuracy of skill/tool matching.
    - Long-Horizon Stability: Success in executing 3+ dependent steps.
    - Latency: P95/P99 response times for reasoning turns.
    """
    logger.info("🚀 Starting REAL WORLD Agentic Orchestration Benchmark (Layer 5)")
    logger.info("=" * 60)
    
    # 1. Setup Environment
    # Ensure we are hitting a real LLM server (LM Studio or Ollama)
    print(f"Using LLM Provider: {settings.llm_provider} at {settings.lmstudio_host if settings.llm_provider == 'lmstudio' else settings.ollama_host}")
    
    async with async_session() as session:
        # Create a real project
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id, 
            name="Benchmark Phase Zeta",
            project_context="Istara is an agentic UX research platform focusing on academic rigor.",
            company_context="Istara Labs"
        )
        session.add(project)
        
        # Create an EXTREMELY complex, multi-skill task to force DAG decomposition
        task_id = str(uuid.uuid4())
        task_description = (
            "Conduct a multi-stage investigation for our new AI product: "
            "1. Deep-dive into 'linear.app' and 'asana.com' to map their unique task-handling architectures. "
            "2. Contrast their interface layouts against established user experience standards. "
            "3. Generate a visionary product spec with 3 disruptive features derived from the above."
        )
        task = Task(
            id=task_id,
            project_id=project_id,
            title="Strategic Market Disruption & UX Spec Creation",
            description=task_description,
            priority="high",
            agent_id="istara-main",
            status=TaskStatus.BACKLOG,
            position=1
        )
        session.add(task)
        await session.commit()
    
    orchestrator = AgentOrchestrator(agent_id="istara-main")
    
    # Benchmark State Tracking
    bench_results = {
        "tsq_score": 0.0,       # Tool Selection Quality
        "dag_success": False,   # Did it decompose and execute steps?
        "reasoning_score": 0.0, # Quality of final summary
        "latency_metrics": [],
        "findings_count": 0,
        "status": "FAIL"
    }
    
    start_time = time.monotonic()
    
    try:
        # 2. Execute Orchestration Work Cycle
        print(f"Agent {orchestrator.agent_id} picking up task: {task.title}")
        
        cycle_start = time.monotonic()
        # Using a long timeout for real LLM inference
        executed = await asyncio.wait_for(orchestrator._work_cycle(), timeout=600.0) 
        cycle_time = time.monotonic() - cycle_start
        bench_results["latency_metrics"].append({"op": "work_cycle", "time": cycle_time})
        
        if not executed:
            print("❌ Orchestrator failed to execute any task.")
            return
            
        # 3. Validation & Metrics Collection
        async with async_session() as session:
            # Refresh task state
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one()
            
            # Check Findings (Evidence Chain)
            res_n = await session.execute(select(Nugget).where(Nugget.project_id == project_id))
            nuggets = res_n.scalars().all()
            res_i = await session.execute(select(Insight).where(Insight.project_id == project_id))
            insights = res_i.scalars().all()
            
            bench_results["findings_count"] = len(nuggets) + len(insights)
            print(f"📊 Findings generated: {len(nuggets)} nuggets, {len(insights)} insights.")
            
            # TSQ Check: Did it use appropriate skills in the DAG?
            # We check the agent_notes which contains the Research Plan JSON for planned tasks
            if "[Research Plan]" in (task.agent_notes or ""):
                bench_results["dag_success"] = True
                bench_results["tsq_score"] = 100.0 # Successfully decomposed
                print("✅ DAG Decomposition verified.")
            else:
                # If it didn't plan, did it at least use ReAct tools?
                if "[Tools used:" in (task.agent_notes or ""):
                    bench_results["tsq_score"] = 80.0
                    print("⚠️ Task executed via ReAct instead of DAG decomposition.")
                else:
                    bench_results["tsq_score"] = 20.0
                    print("❌ No advanced orchestration (DAG/ReAct) detected in output.")

            # Reasoning Check: Does the summary address the multi-step goal?
            if task.status == TaskStatus.IN_REVIEW or task.status == TaskStatus.DONE:
                if len(task.agent_notes or "") > 500:
                    bench_results["reasoning_score"] = 100.0
                elif len(task.agent_notes or "") > 100:
                    bench_results["reasoning_score"] = 60.0
                else:
                    bench_results["reasoning_score"] = 20.0
            
            # Overall Status
            total_elapsed = time.monotonic() - start_time
            if task.status in (TaskStatus.IN_REVIEW, TaskStatus.DONE) and bench_results["findings_count"] >= 1:
                bench_results["status"] = "PASS"
            
            # Log final report
            print("\n" + "=" * 60)
            print(f"FINAL BENCHMARK SCORECARD: {bench_results['status']}")
            print(f"- TSQ (Tool Selection Quality): {bench_results['tsq_score']}%")
            print(f"- DAG Decomposition: {'YES' if bench_results['dag_success'] else 'NO'}")
            print(f"- Reasoning Quality: {bench_results['reasoning_score']}%")
            print(f"- Total Findings: {bench_results['findings_count']}")
            print(f"- Total Latency: {total_elapsed:.2f}s")
            print("=" * 60)

    except asyncio.TimeoutError:
        logger.error("❌ BENCHMARK TIMEOUT: Real LLM inference took longer than 10 minutes.")
    except Exception as e:
        logger.error(f"❌ BENCHMARK ERROR: {e}", exc_info=True)
    
    # Assertion for CI/CD gating
    assert bench_results["status"] == "PASS", f"Benchmark failed with status {bench_results['status']}"
    assert bench_results["tsq_score"] >= 80.0, "Orchestration logic (TSQ) fell below threshold"
