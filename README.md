# An agent that uses Clickup tools provided to perform any task

## Purpose

# Introduction
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

By following these workflows, the ClickUp AI Agent will efficiently and effectively manage interactions and facilitate task management processes.

## MCP Servers

The agent uses tools from these Arcade MCP Servers:

- Clickup

## Human-in-the-Loop Confirmation

The following tools require human confirmation before execution:

- `Clickup_CreateTask`
- `Clickup_CreateTaskComment`
- `Clickup_CreateTaskCommentReply`
- `Clickup_UpdateTask`
- `Clickup_UpdateTaskAssignees`
- `Clickup_UpdateTaskComment`


## Getting Started

1. Install dependencies:
    ```bash
    bun install
    ```

2. Set your environment variables:

    Copy the `.env.example` file to create a new `.env` file, and fill in the environment variables.
    ```bash
    cp .env.example .env
    ```

3. Run the agent:
    ```bash
    bun run main.ts
    ```