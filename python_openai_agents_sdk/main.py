from agents import (Agent, Runner, AgentHooks, Tool, RunContextWrapper,
                    TResponseInputItem,)
from functools import partial
from arcadepy import AsyncArcade
from agents_arcade import get_arcade_tools
from typing import Any
from human_in_the_loop import (UserDeniedToolCall,
                               confirm_tool_usage,
                               auth_tool)

import globals


class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self,
                       context: RunContextWrapper,
                       agent: Agent) -> None:
        self.event_counter += 1
        print(f"### ({self.display_name}) {
              self.event_counter}: Agent {agent.name} started")

    async def on_end(self,
                     context: RunContextWrapper,
                     agent: Agent,
                     output: Any) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended with output {output}"
                agent.name} ended"
        )

    async def on_handoff(self,
                         context: RunContextWrapper,
                         agent: Agent,
                         source: Agent) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                source.name} handed off to {agent.name}"
        )

    async def on_tool_start(self,
                            context: RunContextWrapper,
                            agent: Agent,
                            tool: Tool) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}:"
            f" Agent {agent.name} started tool {tool.name}"
            f" with context: {context.context}"
        )

    async def on_tool_end(self,
                          context: RunContextWrapper,
                          agent: Agent,
                          tool: Tool,
                          result: str) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended tool {tool.name} with result {result}"
                agent.name} ended tool {tool.name}"
        )


async def main():

    context = {
        "user_id": os.getenv("ARCADE_USER_ID"),
    }

    client = AsyncArcade()

    arcade_tools = await get_arcade_tools(
        client, toolkits=["Clickup"]
    )

    for tool in arcade_tools:
        # - human in the loop
        if tool.name in ENFORCE_HUMAN_CONFIRMATION:
            tool.on_invoke_tool = partial(
                confirm_tool_usage,
                tool_name=tool.name,
                callback=tool.on_invoke_tool,
            )
        # - auth
        await auth_tool(client, tool.name, user_id=context["user_id"])

    agent = Agent(
        name="",
        instructions="# Introduction
Welcome to the ClickUp AI Agent! This agent is designed to assist users in managing their tasks, comments, and team interactions within ClickUp. By leveraging a set of specialized tools, the agent can help create tasks, add comments, update lists, and provide insights into your ClickUp workspace efficiently.

# Instructions
The agent will follow predefined workflows to accomplish user requests related to task management and team collaboration. It will utilize various ClickUp tools based on the needs of the user, ensuring a seamless interaction. The agent will analyze user prompts, determine the required workflows, and orchestrate the appropriate tool calls in a logical sequence.

# Workflows

## Workflow 1: Create a New Task
1. **Identify the List ID**: Use `Clickup_FuzzySearchListsByName` to obtain the target list where the task will be created.
2. **Create the Task**: Use `Clickup_CreateTask` to create a new task in the identified list, utilizing any optional metadata provided by the user.

## Workflow 2: Add a Comment to a Task
1. **Identify the Task ID**: Use `Clickup_FuzzySearchTasksByName` to locate the task that requires a comment.
2. **Create the Comment**: Use `Clickup_CreateTaskComment` to add the comment to the identified task.

## Workflow 3: Update an Existing Task
1. **Identify the Task ID**: Use `Clickup_FuzzySearchTasksByName` to locate the task needing an update.
2. **Update the Task**: Use `Clickup_UpdateTask` to modify the desired fields of the task.

## Workflow 4: Retrieve Task Insights
1. **Identify the Workspace ID**: Use `Clickup_WhoAmI` to get access to available workspaces.
2. **Gather Insights**: Use `Clickup_GetWorkspaceInsights` to retrieve an overview of tasks and team performance in the identified workspace.

## Workflow 5: Search for Team Members
1. **Identify the Workspace ID**: Use `Clickup_WhoAmI` to get access to available workspaces.
2. **Search Members**: Use `Clickup_FuzzySearchMembersByName` to find a specific team member in the identified workspace.

## Workflow 6: Get Lists Within a Folder
1. **Identify the Folder ID**: Use `Clickup_FuzzySearchFoldersByName` to find the folder.
2. **Retrieve Lists**: Use `Clickup_GetListsForFolder` to get the task lists contained within that folder.

## Workflow 7: Update Comment on a Task
1. **Identify the Comment ID**: Use `Clickup_GetTaskComments` to retrieve comments and identify the specific comment for updating.
2. **Update the Comment**: Use `Clickup_UpdateTaskComment` to make changes to the selected comment on the task.

By following these workflows, the ClickUp AI Agent will efficiently and effectively manage interactions and facilitate task management processes.",
        model=os.environ["OPENAI_MODEL"],
        tools=arcade_tools,
        hooks=CustomAgentHooks(display_name="")
    )

    # initialize the conversation
    history: list[TResponseInputItem] = []
    # run the loop!
    while True:
        prompt = input("You: ")
        if prompt.lower() == "exit":
            break
        history.append({"role": "user", "content": prompt})
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=history,
                context=context
            )
            history = result.to_input_list()
            print(result.final_output)
        except UserDeniedToolCall as e:
            history.extend([
                {"role": "assistant",
                 "content": f"Please confirm the call to {e.tool_name}"},
                {"role": "user",
                 "content": "I changed my mind, please don't do it!"},
                {"role": "assistant",
                 "content": f"Sure, I cancelled the call to {e.tool_name}."
                 " What else can I do for you today?"
                 },
            ])
            print(history[-1]["content"])

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())