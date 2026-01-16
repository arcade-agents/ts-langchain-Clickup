from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from human_in_the_loop import auth_tool, confirm_tool_usage

import os

load_dotenv(override=True)


async def main():
    app_name = "my_agent"
    user_id = os.getenv("ARCADE_USER_ID")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    agent_tools = await get_arcade_tools(
        client, toolkits=["Clickup"]
    )

    for tool in agent_tools:
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="# Introduction
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
        description="An agent that uses Clickup tools provided to perform any task",
        tools=agent_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())