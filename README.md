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
python -m venv .venv
source .venv/bin/activate

uv sync
# or
pip install -r requirements.txt
```
### Run locally
```bash
python run_local.py --spec-file spec.txt
```

### Alternative: Run in LangSmith
LangSmith provides an interactive UI to visualize the agent, to monitor its activity at real time, and to understand token usage at every node. However, it requires a `LANGSMITH_API_KEY`, you can sign up [here](https://docs.langchain.com/langsmith/create-account-api-key#create-an-account-and-api-key).
```bash
langgraph dev
```

### Rollback changes in boilerplate
This bash script with the option `--clean-untracked` will roll back all changes and remove node_modules folder
```bash
./scripts/rollback_frontend.sh --clean-untracked
```

## Stack
| Stack             | Choice                                                             | Remarks                                                                                                                                                                                                                                                                                                                                                                                                                |
|:------------------|:-------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| LLM               | gpt-4o-mini & gpt-5.4-mini                                         | I didn't choose the most powerful coding-specialized models such as gemini-3.1-pro, claude-opus-4-6 and claude-sonnet-4-6, because of cost optimization. GPT-5.4-mini offers a perfect tradeoff between cost and performance. I also want to showcase that with the right workflow and agentic patterns, coupled with good context management and prompt engineering, even small models are capable of agentic coding. |
| Agentic framework | LangChain & LangGraph                                              | LangGraph offers a sweet middle-ground between control and flexibility, while LangChain offers the ability to quickly switch between LLM models and prebuilt agent patterns. I also find LangSmith very useful in debugging and optimization due to its tracing capability.                                                                                                                                            |
| Tooling           | skills, limited file system operations and limited shell execution | Limited file system operations and limited shell execution within the boilerplate for security reasons. Skills are provided to LLM to maintain best practices of React 19, Typescript, MUI, etc.                                                                                                                                                                                                                       |

## Design
For this take home challenge, I took inspiration of [OpenSpec](https://github.com/Fission-AI/OpenSpec), a very popular spec-driven framework that I really like to use when coding with Cursor. I took the concepts of **design.md**, **approach.md** and **task.md** from this framework, which are useful in minimizing hallucinations of LLMs and ensure that LLMs stay coherent the whole time.

## Architecture
**Multi-stage self-validation**, **LLM-as-judge**, **skills pattern** and **tool use** throughout the whole workflow allows this agent to produce high-quality code without sacrificing governance and flexibility.

|                           | Graph                                               | Description                                                                                                                                                                                                                                                                                                                                                                                                                |
|:--------------------------|:----------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Main Graph                | <img src="./static/main_graph.png" height="30%">    | The main graph uses a **ReAct pattern** in the planning stage to make sure the agent gets enough context from the frontend repository with available tools. It also uses an **evaluator-optimizer pattern** to validate the plan.                                                                                                                                                                                          |
| Subgraph (Implementation) | ![Subgraph (implementation)](static/subgraph_2.png) | Inside the implementation stage, both implement_app and implement_test use the **ReAct pattern** and has its **own evaluator** to make sure all requirements are met before moving on to the next stage. On test errors, run_test node routes to implement_app or fix_test_cases based on the error type. review_implementation ensures all tasks are done and the test coverage is enough before completing the workflow. |

[//]: # (| Subgraph &#40;plan&#41;           | ![Subgraph &#40;plan&#41;]&#40;./static/subgraph_1.png&#41;      
### Evaluator
                                                                                                                                                                                                                                                                                                                                                          | Inside the planning stage, the LLM model is given maximum flexibility to explore the repository while being restricted to read only access, limited tool call and limited iteration. |)


## Workflow
1. Parse product specification, convert into detailed specification.
2. Get context from current repo. Decide the approach that suits the current repo. Define the tasks required based on the approach.
3. Review the product specification, check design, approach and tasks to make sure that they are coherent. If not, re-run from step 2.
4. Implement tasks (except test cases), ensure all tasks are done and type check passed before proceeding.
5. Implement test cases, ensure type check passed before proceeding. 
6. Run test cases. If there is any error, determine whether there is a bug in the code or test cases, then route back to step 5 or step 6. 
7. Determine whether all tasks are done, and whether the test coverage is enough.

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