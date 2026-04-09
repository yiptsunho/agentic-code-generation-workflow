## Table of Contents
* [How to run](#how-to-run)
* [Stack](#stack)
* [Design](#design)
* [Architecture](#architecture)
* [Workflow](#workflow)
* [Optimization Techniques Applied](#optimization-techniques-applied)
* [Tradeoff](#tradeoff)
* [Changes made to boilerplate](#changes-made-to-boilerplate)

## How to run

### Setup
```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate

uv sync
# or
pip install -r requirements.txt
```
Put your OPENAI_API_KEY in .env
```bash
OPENAI_API_KEY=
```
### Run locally
```bash
python run_local.py --spec-file spec.txt
```

### Alternative: Run in LangSmith
LangSmith provides an interactive UI to visualize the agent, to monitor its activity at real time, and to understand token usage at every node. However, it requires a `LANGSMITH_API_KEY`, you can sign up [here](https://docs.langchain.com/langsmith/create-account-api-key#create-an-account-and-api-key).
Put your LANGSMITH_API_KEY in .env
```bash
LANGSMITH_API_KEY=
```
```bash
langgraph dev
```

### Rollback changes in boilerplate
Use the rollback script to reset `frontend/` to Git `HEAD` and remove `frontend/node_modules`.

macOS/Linux (bash):
```bash
./scripts/rollback_frontend.sh --clean-untracked
```

## Stack
| Stack             | Choice                                                             | Remarks                                                                                                                                                                                                                                                                                                                                                                                                                |
|:------------------|:-------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| LLM               | gpt-4o-mini & gpt-5.4-mini                                         | I didn't choose the most powerful coding-specialized models such as gemini-3.1-pro, claude-opus-4-6 and claude-sonnet-4-6, because of cost optimization. GPT-5.4-mini offers a perfect tradeoff between cost and performance. I also want to showcase that with the right workflow and agentic patterns, coupled with good context management and prompt engineering, even small models are capable of agentic coding. |
| Agentic framework | LangChain & LangGraph                                              | LangGraph offers a sweet middle-ground between control and flexibility, while LangChain offers the ability to quickly switch between LLM models and prebuilt agent patterns. I also find LangSmith very useful in debugging and optimization due to its tracing capability.                                                                                                                                            |
| Tooling           | skills, limited file system operations and limited shell execution | Limited file system operations and limited shell execution within the boilerplate for security reasons. Skills are provided to LLM to maintain best practices of React 19, Typescript, MUI, etc.                                                                                                                                                                                                                       |

## Design Inspiration
For this take home challenge, I took inspiration of [OpenSpec](https://github.com/Fission-AI/OpenSpec), a very popular spec-driven framework that I really like to use when coding with Cursor. I took the concepts of **design.md**, **approach.md** and **task.md** from this framework, which are useful in minimizing hallucinations of LLMs and ensure that LLMs stay coherent the whole time.

## Architecture
<table width="100%">
  <thead>
    <tr>
      <th></th>
      <th width="40%">Graph</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Main Graph</td>
      <td width="40%"><img src="./static/main_graph.png"/></td>
      <td>The main graph has a plan-gate loop: it parses raw specs into detailed specs, runs a tool-using planning node to explore the repo and produce <code>repo_context/design/approach/task</code>, then sends that plan to <code>review_plan</code>. If the reviewer rejects it, the graph goes back to <code>plan</code> with feedback; if approved, it enters the implementation subgraph.</td>
    </tr>
    <tr>
      <td>Implementation</td>
      <td width="40%"><img src="./static/subgraph_2.png"/></td>
      <td>The implementation subgraph runs as a controlled loop: it first splits checklist items into app tasks vs test tasks, iterates <code>implement_app</code> until typecheck passes, then iterates <code>implement_tests</code> until typecheck passes, and runs <code>run_test</code>. Failed tests are classified as <code>test_only</code>, <code>app_logic</code>, or <code>mixed_or_unclear</code> to route to <code>fix_test_cases</code> or back to <code>implement_app</code> work; after repeated failures, a retry limit sends flow to review. <code>review_implementation</code> then chooses whether to end or route back to the most useful next node, with guardrails to prevent invalid loops.</td>
    </tr>
  </tbody>
</table>

This agent is designed as a **multi-stage LangGraph workflow** that separates planning, implementation, testing, and review.  
The main goal is to keep generation quality high while staying deterministic enough for repeated runs.

Core architecture principles:

1. **Plan before code**
   - The agent first converts raw specs into detailed requirements.
   - It explores the repository with restricted tools (`list_directory`, `read_file`) to gather grounded context.
   - It produces a structured plan (`repo_context`, `design`, `approach`, `task`) before implementation starts.

2. **Self-review gate before implementation**
   - A dedicated plan-review node acts as an evaluator ("LLM-as-judge").
   - If the plan is weak or inconsistent, the graph routes back to planning.
   - This loop reduces implementation drift caused by vague specs.

3. **Implementation as a controlled subgraph**
   - Coding is split into app implementation, test implementation, test execution, and review.
   - The subgraph uses conditional routing to decide whether to keep coding, fix tests, or finish.
   - This keeps each node focused on a single responsibility.

4. **Quality gates and bounded retries**
   - Each coding phase enforces `npm run typecheck`.
   - Test execution is routed by failure category (`test_only`, `app_logic`, `mixed_or_unclear`).
   - Retry count is bounded (`RUN_TEST_FAILURE_LIMIT`) to prevent infinite loops.

5. **Skill-augmented tool usage**
   - The agent loads task-specific skills (explore/app/test) to keep outputs aligned with React + TypeScript best practices.
   - Shell execution is restricted to a small allowed command set for safety and reproducibility.

6. **Post-run structured validation**
   - After coding nodes, a structured summarization step extracts:
     - implementation summary
     - files touched
     - final typecheck status
   - This creates clean state handoff between nodes and supports reliable final review.

In short: the architecture combines **ReAct-style exploration/coding**, **evaluator-optimizer loops**, and **policy-based routing** to improve correctness, reduce hallucination, and keep execution governed.

## Optimization Techniques Applied

The following optimizations were implemented to improve token efficiency, latency, and reliability while preserving agent behavior.

1. **Context Window Optimization**
    - _truncate_text function is heavily used in implement_app, implement_test and fix_test_cases, where most tokens are consumed

2. **State-to-prompt Compression**
   - _format_exploration_transcript helps compress exploration transcript during planning stage

3. **Execution guardrails via middleware budgets**
    - ToolCallLimitMiddleware, ModelCallLimitMiddleware and RECURSION_LIMIT are used in all ReAct patterns, including plan, implement_app, implement_test and fix_test_cases

4. **Conditional edge routing by error category**
    - LLM-as-classifier + routing policy in run_test and should_route_after_test route to the corresponding nodes based on failure category, rather than uniform retry

5. **Circuit breaker / bounded retry policy**
    - RUN_TEST_FAILURE_LIMIT serves as the circuit breaker, avoid infinite retry cycles and force LLM review decisions after repeated failures

6. **Structured observation extraction from tool outputs**
    - Parsing vitest result in JSON improves downstream routing and reduces noisy, unstructured logs

7. **Tool gating**
    - Restricting shell actions to only `npm install`, `npm run typecheck`, `npm run test` and `npm run dev` to boilerplate only. Avoiding file system operations on unnecessary directory (node_modules).

## Tradeoff
1. We can definitely use a more powerful model for this project to speed up each run, such as gemini-3.1-pro, claude-opus-4-6 and claude-sonnet-4-6. I used gpt-5.4-mini and gpt-4o-mini because of cost optimization.
2. The workflow design may seem a little bit too much for this project. However, I try to mimic real-life situation with this workflow, like addressing vague product specifications, dealing with complex codebases, and upholding high quality standard.
3. I introduced the best practices of React 19, Typescript, Vite, Apollo Client, GraphQL and vitest to LLMs through skills, therefore this agent may use more time and tokens compared to others. It may not make a huge difference in code quality in this project, but introducing these best practices to LLMs is key in real-life situations.
4. For demo purpose, I did not introduce human-in-the-loop in this agent because I don't want to confuse the reviewers with a really complex workflow. But in reality, human-in-the-loop is definitely required, especially before the implementation. 

## Changes made to boilerplate
In order to better parse the vitest results into LLM, I changed the test command from `vitest run` to `vitest run --reporter=json --outputFile=.tmp/vitest.json`. It significantly reduces the context while increasing readability because it has a predictable format.

## What worked well and what I would improve
### What worked well
1. The **plan -> review -> implement** structure consistently translated vague requirements into actionable execution. This significantly reduced spec drift and improved implementation coherence.
2. The planning stage combines repository exploration with structured outputs (`repo_context`, `design`, `approach`, `task`), which made implementation more grounded in real code patterns instead of assumptions.
3. The explicit plan-review gate created a practical quality checkpoint before writing code, catching weak plans early and preventing expensive downstream rework.
4. Splitting implementation into focused nodes (`implement_app`, `implement_tests`, `run_test`, `fix_test_cases`) improved modularity: each node has a clear responsibility, and failures are easier to isolate and fix.
5. Conditional routing based on test-failure type (`test_only`, `app_logic`, `mixed_or_unclear`) enabled smarter recovery paths than uniform retries, which improved both reliability and turnaround time.
6. Bounded retries plus deterministic guardrails made the system robust in failure scenarios: it avoids infinite loops while still preserving opportunities for targeted recovery.
7. Structured post-run summaries (files touched, validation results, implementation summary) improved traceability and created cleaner handoffs between nodes.
8. Constraining tool access and command usage improved safety and reproducibility, making behavior more predictable across repeated runs.
9. Skill-augmented prompts (React/TypeScript/testing best practices) increased output quality while keeping the workflow adaptable to real frontend engineering conventions.
10. Overall, the architecture achieved a strong balance between **quality, control, and cost**: it demonstrates that smaller models can still deliver useful agentic coding outcomes when workflow design is strong.

### What I would improve with more time
1. Currently, this agent lacks an interactive UI. I wanted to create a fancier cli tool but I was running short of time.
2. Add a lightweight **human-in-the-loop checkpoint** before implementation (and optionally before final completion) so reviewers can approve or adjust plan decisions earlier. 
3. Expand automated evaluation with benchmark tasks and trace-level metrics (first-pass success rate, retries per stage, token/latency per node) to quantify quality and cost tradeoffs.
4. Introduce optional model-routing per stage (small model for parsing/routing, stronger model for hard coding turns) to further improve cost-performance efficiency.
5. I ran into a rate limit once out of more than 150 runs, LangChain does have built-in support for model rate limits, however I didn't want to introduce breaking changes at last minute.