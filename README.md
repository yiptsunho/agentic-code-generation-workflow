# Agentic Code Generation Workflow

## Design
For this take home challenge, I took the concept of a very popular spec driven framework that I really like to use when coding with Cursor. I took the concept of **design.md**, **proposal.md** and **task.md**, which are useful in minimizing hallucinations of LLMs.

## Architecture


## Workflow
1. Parse product specification, convert into detailed specification. Get context from current repo. Decide the approach that suits the current repo. Define the tasks required based on the approach.
2. Review the product specification, check design, approach and tasks to make sure that they are coherent. If not, re-run from 1th step to 3rd step.
3. Ask for human review on design, approach and tasks. If there are any comments, re-run from 1st step to 4th step
4. Implement the tasks, ensure all tasks are done before proceeding.
5. Write test cases, both unit tests and functional tests. Then run the test cases.
6. Determine whether all tasks are done, whether the test coverage is enough, and whether the test cases covered all edge cases. Then verify test results that there are no errors. If not, write down comments and re-run from 6th step to 7th step based on the new comments.
7. Verify that the code change aligns with the design and approach. 
8. Ask for human review of the code change. If there are any comments, re-run from 6th step to 9th step.