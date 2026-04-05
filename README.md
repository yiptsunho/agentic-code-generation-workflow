# Agentic Code Generation Workflow

## Design
For this take home challenge, I took the concept of a very popular spec driven framework that I really like to use when coding with Cursor. I took the concept of **design.md**, **proposal.md** and **task.md**, which are useful in minimizing hallucinations of LLMs.
// TODO
mention choice of LLM, choice of agent architecture, choice of temperature

## Architecture


## Workflow
1. Parse product specification, convert into detailed specification.
2. Get context from current repo. Decide the approach that suits the current repo. Define the tasks required based on the approach.
3. Review the product specification, check design, approach and tasks to make sure that they are coherent. If not, re-run from 1st step to 2nd step.
4. Ask for human review on design, approach and tasks. If there are any comments, re-run from 1st step to 4th step
5. Implement the tasks, ensure all tasks are done before proceeding. 
6. Review code change to make sure all tasks are implemented correctly and aligned with design and approach. If not, re-run 5th step. 
7. Write test cases, both unit tests and functional tests. Then run the test cases. If test cases reveal bugs in code change, re-run 5th to 6th step. 
8. Determine whether all tasks are done, whether the test coverage is enough, and whether the test cases covered all edge cases. Then verify test results that there are no errors. If not, re-run from 5th step to 7th step based on the new comments. 
9. Ask for human review of the code change. If there are any comments, re-run from 5th step to 8th step.