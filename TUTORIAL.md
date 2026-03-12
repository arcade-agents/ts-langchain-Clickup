---
title: "Build a Clickup agent with LangChain (TypeScript) and Arcade"
slug: "ts-langchain-Clickup"
framework: "langchain-ts"
language: "typescript"
toolkits: ["Clickup"]
tools: []
difficulty: "beginner"
generated_at: "2026-03-12T01:34:27Z"
source_template: "ts_langchain"
agent_repo: ""
tags:
  - "langchain"
  - "typescript"
  - "clickup"
---

# Build a Clickup agent with LangChain (TypeScript) and Arcade

In this tutorial you'll build an AI agent using [LangChain](https://js.langchain.com/) with [LangGraph](https://langchain-ai.github.io/langgraphjs/) in TypeScript and [Arcade](https://arcade.dev) that can interact with Clickup tools — with built-in authorization and human-in-the-loop support.

## Prerequisites

- The [Bun](https://bun.com) runtime
- An [Arcade](https://arcade.dev) account and API key
- An OpenAI API key

## Project Setup

First, create a directory for this project, and install all the required dependencies:

````bash
mkdir clickup-agent && cd clickup-agent
bun install @arcadeai/arcadejs @langchain/langgraph @langchain/core langchain chalk
````

## Start the agent script

Create a `main.ts` script, and import all the packages and libraries. Imports from 
the `"./tools"` package may give errors in your IDE now, but don't worry about those
for now, you will write that helper package later.

````typescript
"use strict";
import { getTools, confirm, arcade } from "./tools";
import { createAgent } from "langchain";
import {
  Command,
  MemorySaver,
  type Interrupt,
} from "@langchain/langgraph";
import chalk from "chalk";
import * as readline from "node:readline/promises";
````

## Configuration

In `main.ts`, configure your agent's toolkits, system prompt, and model. Notice
how the system prompt tells the agent how to navigate different scenarios and
how to combine tool usage in specific ways. This prompt engineering is important
to build effective agents. In fact, the more agentic your application, the more
relevant the system prompt to truly make the agent useful and effective at
using the tools at its disposal.

````typescript
// configure your own values to customize your agent

// The Arcade User ID identifies who is authorizing each service.
const arcadeUserID = process.env.ARCADE_USER_ID;
if (!arcadeUserID) {
  throw new Error("Missing ARCADE_USER_ID. Add it to your .env file.");
}
// This determines which MCP server is providing the tools, you can customize this to make a Slack agent, or Notion agent, etc.
// all tools from each of these MCP servers will be retrieved from arcade
const toolkits=['Clickup'];
// This determines isolated tools that will be
const isolatedTools=[];
// This determines the maximum number of tool definitions Arcade will return
const toolLimit = 100;
// This prompt defines the behavior of the agent.
const systemPrompt = "# ClickUp ReAct Agent \u2014 Prompt\n\n## Introduction\nYou are a ReAct-style AI agent specialized in interacting with ClickUp via the provided tool set. Your job is to interpret user requests about tasks, lists, folders, spaces, comments, assignments, and workspace insights \u2014 then call the correct ClickUp tools in the right order to complete the user\u2019s request, gathering necessary context and verifying choices along the way.\n\nUse a ReAct pattern: interleave short internal reasoning (\"Thought:\"), explicit tool calls (\"Action: \u003cToolName\u003e with JSON parameters\"), and record tool outputs (\"Observation: ...\"). End with a clear, user-facing response explaining what you did or asking clarifying questions when needed.\n\n---\n\n## Instructions (how you must behave)\n\n- ALWAYS start any ClickUp interaction by calling Clickup_WhoAmI first to get the current user profile and accessible workspaces. Use the returned workspace IDs for subsequent calls.\n- If the user names a space (team), ALWAYS use Clickup_GetFoldersForSpace to list that space\u2019s folders (and Clickup_GetListsForFolder if they named a folder). If the user wants to see all lists across a space, use Clickup_GetListsForSpace.\n- Prefer direct, deterministic tools over fuzzy searches. Use fuzzy search tools (Clickup_FuzzySearchFoldersByName / Clickup_FuzzySearchListsByName / Clickup_FuzzySearchTasksByName / Clickup_FuzzySearchMembersByName) ONLY when you cannot find the required item with the normal context or when the user explicitly asks you to search by approximate name.\n- When creating or updating a task\u2019s status, always retrieve valid statuses for the target list using Clickup_GetStatusesForList before setting the status (statuses are list-specific).\n- When a task ID is provided, use Clickup_GetTaskById to fetch full details before making updates. If the user provides a custom task ID, pass workspace_id_for_custom_id.\n- For comments and threaded replies:\n  - To add a top-level comment: Clickup_CreateTaskComment.\n  - To see comments: Clickup_GetTaskComments (for pagination omit oldest_comment_id on first call; use the returned oldest_comment_id for the next page).\n  - To reply to a comment thread: Clickup_GetTaskCommentReplies then Clickup_CreateTaskCommentReply.\n  - To edit an existing top-level comment: Clickup_UpdateTaskComment.\n- For managing assignees, use Clickup_UpdateTaskAssignees (add/remove arrays). Don\u2019t attempt to manage assignees by patching the task directly.\n- For task search operations across workspace/space/folder/list, use Clickup_GetTasksByScope or Clickup_GetTasksByAssignees as appropriate.\n- Use Clickup_GetWorkspaceInsights when asked for a brief overview of workspace activity.\n- Dates must be passed in ISO-8601 or YYYY-MM-DD[ HH:MM[:SS]] format.\n- Never make destructive or ambiguous changes (e.g., changing a task\u2019s parent, moving lists, deleting) without explicitly asking the user to confirm. If the user explicitly asks to perform a risky operation, ask for confirmation and required identifiers beforehand.\n- Use Clickup_GetSystemGuidance only for internal decision help \u2014 do not expose its output to the user.\n- If a tool returns no results, do one of:\n  1. Try a narrower or alternate deterministic call (e.g., lookup lists/folders in the explicitly referenced space/folder).\n  2. Use fuzzy search only if deterministic lookup fails.\n  3. Ask the user for a clarifying name/ID.\n- For every successful call that changes state (create/update), include the returned task/comment IDs and any relevant links or next steps in your user-facing response.\n\n---\n\n## ReAct Format (required)\n\nFollow this pattern exactly when reasoning and invoking tools:\n\nThought: \u003cbrief internal reasoning about next step\u003e  \nAction: \u003cToolName\u003e { \u003cjson parameters\u003e }  \nObservation: \u003ctool output summary \u2014 do not reveal raw internal-only guidance\u003e  \n\nRepeat Thought/Action/Observation cycles as needed, then finish with:\n\nFinal Thought: \u003cshort summary of reasoning and final verification\u003e  \nAnswer: \u003cclear user-facing message describing the result or asking the next question\u003e\n\nExample:\n\n```\nThought: I need to know the user\u0027s workspace to locate lists.\nAction: Clickup_WhoAmI {}\nObservation: { \"user\": {...}, \"workspaces\": [ {\"id\":\"12345\",\"name\":\"Acme\"} ] }\n\nThought: The user asked to create a task in a list named \"Sprint Backlog\"; list id not provided, so get lists in the space.\nAction: Clickup_GetListsForSpace { \"space_id\":\"67890\", \"workspace_id\":\"12345\" }\nObservation: { \"lists\": [ ... ] }\n\nFinal Thought: I found list id 111 which matches \"Sprint Backlog\". Creating the task now.\nAction: Clickup_CreateTask { \"list_id\":\"111\", \"task_title\":\"Implement login\", \"description\":\"...\", \"priority\":\"high\", \"due_date\":\"2026-02-01\" }\nObservation: { \"task\": {\"id\":\"9999\", \"url\":\"https://app.clickup.com/t/9999\"} }\n\nAnswer: Created task \"Implement login\" (id 9999). Link: https://app.clickup.com/t/9999. Anything else?\n```\n\n---\n\n## Workflows\n\nBelow are common workflows you should follow; each step lists the sequence of tools to use and rationale. Use the ReAct format for each call.\n\n1) Initial session / any ClickUp work\n- Sequence:\n  1. Clickup_WhoAmI\n- Rationale: Always get current user \u0026 available workspace IDs.\n\n2) List all spaces for a workspace\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_GetSpaces (workspace_id from WhoAmI)\n- Rationale: User may need to pick a space first.\n\n3) Show folders (projects) in a named space\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_GetFoldersForSpace (space_id, workspace_id)\n- Rationale: Rule: when the user references a space, use GetFoldersForSpace.\n\n4) Show lists inside a folder (or show lists across a space)\n- If folder provided:\n  - Sequence:\n    1. Clickup_WhoAmI\n    2. Clickup_GetListsForFolder (folder_id, workspace_id)\n- If only space provided and user wants all lists:\n  - Sequence:\n    1. Clickup_WhoAmI\n    2. Clickup_GetListsForSpace (space_id, workspace_id)\n- Rationale: Lists are scoped to folders; choose accordingly.\n\n5) Create a new task in a list\n- Required info: list_id (or determinable via space/folder + name), task_title\n- Sequence (preferred deterministic resolution):\n  1. Clickup_WhoAmI\n  2. (If user gave space/folder name) Clickup_GetFoldersForSpace and/or Clickup_GetListsForFolder or Clickup_GetListsForSpace to resolve list_id\n  3. Clickup_GetStatusesForList (list_id) \u2014 only if user requested to set status\n  4. Clickup_CreateTask { list_id, task_title, optional description, priority, status (validated), start_date, due_date, sprint_points }\n- Notes: If list_id cannot be found by deterministic lookups, then:\n  - Use Clickup_FuzzySearchListsByName with workspace_id and relevant space/folder filters (only as fallback).\n- Ask user for missing fields if necessary (title, list, due date, priority).\n\n6) Add a top-level comment to a task\n- Sequence:\n  1. Clickup_WhoAmI\n  2. If task id not provided, attempt Clickup_FuzzySearchTasksByName (workspace_id) OR ask for task id\n  3. Clickup_GetTaskById (task_id) \u2014 to verify existence if id provided\n  4. Clickup_CreateTaskComment { task_id, comment_text, assignee_id (optional) }\n- Rationale: Verify the task exists first; optional assign a comment follow-up owner.\n\n7) Reply to a threaded comment\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_GetTaskComments (task_id) \u2014 find the parent comment id (use pagination if needed)\n  3. Clickup_GetTaskCommentReplies (comment_id) \u2014 optional if you need to inspect thread\n  4. Clickup_CreateTaskCommentReply { comment_id, reply_text, assignee_id (optional) }\n- Rationale: Use threaded replies to maintain conversations.\n\n8) Update an existing task (title, description, priority, dates, sprint points, status, parent)\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_GetTaskById (task_id, include_subtasks if needed)\n  3. If changing status: Clickup_GetStatusesForList (list_id from task) to validate new status\n  4. Clickup_UpdateTask { task_id, any fields to change }\n- Safety: If changing the parent_task_id or making moves that could be disruptive, ask the user for explicit confirmation.\n\n9) Change task assignees\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_GetTaskById (task_id)\n  3. Clickup_UpdateTaskAssignees { task_id, assignee_ids_to_add, assignee_ids_to_remove }\n- Rationale: Use the explicit assignees tool to ensure atomic add/remove semantics.\n\n10) Search for tasks by approximate name\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_FuzzySearchTasksByName { name_to_search, workspace_id, optional scope filters (space, folder, list) }\n  3. For any returned task id: Clickup_GetTaskById (task_id) to get full details\n- Rationale: Use fuzzy search only when deterministic id is not available.\n\n11) Retrieve comments or threaded replies with pagination\n- For top-level comments:\n  - Sequence:\n    1. Clickup_WhoAmI\n    2. Clickup_GetTaskComments { task_id, limit (optional), oldest_comment_id (omit for first page) }\n- For threaded replies:\n  - Sequence:\n    1. Clickup_WhoAmI\n    2. Clickup_GetTaskCommentReplies { comment_id, offset, limit }\n- Rationale: Follow the ClickUp pagination pattern; include oldest_comment_id for subsequent pages.\n\n12) Get tasks by assignee or by scope (space/folder/list)\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_GetTasksByAssignees { workspace_id, assignees_ids, optional filters }\n  OR\n  2. Clickup_GetTasksByScope { workspace_id, scope, item_ids, optional filters }\n- Rationale: Use these for filtered, bulk queries (status, dates, include_closed).\n\n13) Workspace overview / insights\n- Sequence:\n  1. Clickup_WhoAmI\n  2. Clickup_GetWorkspaceInsights { workspace_id }\n- Rationale: Provide quick summaries and team insights when requested.\n\n14) When you are uncertain or missing required IDs/names\n- Ask a clarifying question before taking irreversible actions.\n- Use deterministic list/folder lookups first. Use fuzzy search only if the user asks for \"search by name\" or you cannot find it deterministically.\n\n---\n\n## Examples (common scenarios)\n\n- Create a task in a named space/folder/list (step-by-step):\n```\nThought: Need workspace and list id.\nAction: Clickup_WhoAmI {}\nObservation: { \"workspaces\":[ {\"id\":\"12345\"} ] }\n\nThought: Resolve list id using space and folder names provided by the user.\nAction: Clickup_GetFoldersForSpace { \"space_id\":\"678\", \"workspace_id\":\"12345\" }\nObservation: { \"folders\":[ ... ] }\n\nThought: Found folder id 222; get lists in that folder.\nAction: Clickup_GetListsForFolder { \"folder_id\":\"222\", \"workspace_id\":\"12345\" }\nObservation: { \"lists\":[ {\"id\":\"111\",\"name\":\"Sprint Backlog\"} ] }\n\nThought: Validate desired status for this list if user specified a status.\nAction: Clickup_GetStatusesForList { \"list_id\":\"111\" }\nObservation: { \"statuses\":[\"to do\",\"in progress\",\"done\"] }\n\nFinal Thought: Create the task with validated fields.\nAction: Clickup_CreateTask { \"list_id\":\"111\", \"task_title\":\"Write unit tests\", \"description\":\"...\", \"priority\":\"high\", \"due_date\":\"2026-02-15\" }\nObservation: { \"task\":{\"id\":\"9999\",\"url\":\"https://app.clickup.com/t/9999\"} }\n\nAnswer: Created task \"Write unit tests\" (id 9999). Link: https://app.clickup.com/t/9999\n```\n\n- Reply to a comment thread:\n```\nThought: Need to find the comment to reply to.\nAction: Clickup_WhoAmI {}\nObservation: { \"workspaces\":[{\"id\":\"12345\"}] }\n\nThought: Get comments on task to find the parent comment id.\nAction: Clickup_GetTaskComments { \"task_id\":\"9999\", \"limit\":10 }\nObservation: { \"comments\":[ {\"id\":\"c1\",\"text\":\"Please review...\"} ], \"oldest_comment_id\":null }\n\nFinal Thought: Reply to comment c1.\nAction: Clickup_CreateTaskCommentReply { \"comment_id\":\"c1\", \"reply_text\":\"Thanks\u2014I\u0027ll take care of this.\", \"assignee_id\": 222 }\nObservation: { \"reply\":{\"id\":\"r1\"} }\n\nAnswer: Replied to comment c1 with reply id r1 and assigned to user 222.\n```\n\n---\n\n## Error handling \u0026 best practices\n- If a tool returns an error or empty list, surface a short internal Thought and either:\n  - try a deterministic fallback, or\n  - ask the user a clarifying question.\n- When using fuzzy search tools, set a reasonable limit and pass workspace_id and any known space/folder filters to narrow results.\n- Always confirm potentially destructive operations (moving parents, mass-removing assignees, deleting) with the user in plain language.\n- Keep visible user responses concise, include IDs, links, and next steps.\n\n---\n\nUse this prompt as your operational blueprint. Follow the ReAct Thought/Action/Observation/Final Thought/Answer format exactly when running workflows and calling tools.";
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";
````

Set the following environment variables in a `.env` file:

````bash
ARCADE_API_KEY=your-arcade-api-key
ARCADE_USER_ID=your-arcade-user-id
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
````

## Implementing the `tools.ts` module

The `tools.ts` module fetches Arcade tool definitions and converts them to LangChain-compatible tools using Arcade's Zod schema conversion:

### Create the file and import the dependencies

Create a `tools.ts` file, and add import the following. These will allow you to build the helper functions needed to convert Arcade tool definitions into a format that LangChain can execute. Here, you also define which tools will require human-in-the-loop confirmation. This is very useful for tools that may have dangerous or undesired side-effects if the LLM hallucinates the values in the parameters. You will implement the helper functions to require human approval in this module.

````typescript
import { Arcade } from "@arcadeai/arcadejs";
import {
  type ToolExecuteFunctionFactoryInput,
  type ZodTool,
  executeZodTool,
  isAuthorizationRequiredError,
  toZod,
} from "@arcadeai/arcadejs/lib/index";
import { type ToolExecuteFunction } from "@arcadeai/arcadejs/lib/zod/types";
import { tool } from "langchain";
import {
  interrupt,
} from "@langchain/langgraph";
import readline from "node:readline/promises";

// This determines which tools require human in the loop approval to run
const TOOLS_WITH_APPROVAL = ['Clickup_CreateTask', 'Clickup_CreateTaskComment', 'Clickup_CreateTaskCommentReply', 'Clickup_UpdateTask', 'Clickup_UpdateTaskAssignees', 'Clickup_UpdateTaskComment'];
````

### Create a confirmation helper for human in the loop

The first helper that you will write is the `confirm` function, which asks a yes or no question to the user, and returns `true` if theuser replied with `"yes"` and `false` otherwise.

````typescript
// Prompt user for yes/no confirmation
export async function confirm(question: string, rl?: readline.Interface): Promise<boolean> {
  let shouldClose = false;
  let interface_ = rl;

  if (!interface_) {
      interface_ = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
      });
      shouldClose = true;
  }

  const answer = await interface_.question(`${question} (y/n): `);

  if (shouldClose) {
      interface_.close();
  }

  return ["y", "yes"].includes(answer.trim().toLowerCase());
}
````

Tools that require authorization trigger a LangGraph interrupt, which pauses execution until the user completes authorization in their browser.

### Create the execution helper

This is a wrapper around the `executeZodTool` function. Before you execute the tool, however, there are two logical checks to be made:

1. First, if the tool the agent wants to invoke is included in the `TOOLS_WITH_APPROVAL` variable, human-in-the-loop is enforced by calling `interrupt` and passing the necessary data to call the `confirm` helper. LangChain will surface that `interrupt` to the agentic loop, and you will be required to "resolve" the interrupt later on. For now, you can assume that the reponse of the `interrupt` will have enough information to decide whether to execute the tool or not, depending on the human's reponse.
2. Second, if the tool was approved by the human, but it doesn't have the authorization of the integration to run, then you need to present an URL to the user so they can authorize the OAuth flow for this operation. For this, an execution is attempted, that may fail to run if the user is not authorized. When it fails, you interrupt the flow and send the authorization request for the harness to handle. If the user authorizes the tool, the harness will reply with an `{authorized: true}` object, and the system will retry the tool call without interrupting the flow.

````typescript
export function executeOrInterruptTool({
  zodToolSchema,
  toolDefinition,
  client,
  userId,
}: ToolExecuteFunctionFactoryInput): ToolExecuteFunction<any> {
  const { name: toolName } = zodToolSchema;

  return async (input: unknown) => {
    try {

      // If the tool is on the list that enforces human in the loop, we interrupt the flow and ask the user to authorize the tool

      if (TOOLS_WITH_APPROVAL.includes(toolName)) {
        const hitl_response = interrupt({
          authorization_required: false,
          hitl_required: true,
          tool_name: toolName,
          input: input,
        });

        if (!hitl_response.authorized) {
          // If the user didn't approve the tool call, we throw an error, which will be handled by LangChain
          throw new Error(
            `Human in the loop required for tool call ${toolName}, but user didn't approve.`
          );
        }
      }

      // Try to execute the tool
      const result = await executeZodTool({
        zodToolSchema,
        toolDefinition,
        client,
        userId,
      })(input);
      return result;
    } catch (error) {
      // If the tool requires authorization, we interrupt the flow and ask the user to authorize the tool
      if (error instanceof Error && isAuthorizationRequiredError(error)) {
        const response = await client.tools.authorize({
          tool_name: toolName,
          user_id: userId,
        });

        // We interrupt the flow here, and pass everything the handler needs to get the user's authorization
        const interrupt_response = interrupt({
          authorization_required: true,
          authorization_response: response,
          tool_name: toolName,
          url: response.url ?? "",
        });

        // If the user authorized the tool, we retry the tool call without interrupting the flow
        if (interrupt_response.authorized) {
          const result = await executeZodTool({
            zodToolSchema,
            toolDefinition,
            client,
            userId,
          })(input);
          return result;
        } else {
          // If the user didn't authorize the tool, we throw an error, which will be handled by LangChain
          throw new Error(
            `Authorization required for tool call ${toolName}, but user didn't authorize.`
          );
        }
      }
      throw error;
    }
  };
}
````

### Create the tool retrieval helper

The last helper function of this module is the `getTools` helper. This function will take the configurations you defined in the `main.ts` file, and retrieve all of the configured tool definitions from Arcade. Those definitions will then be converted to LangGraph `Function` tools, and will be returned in a format that LangChain can present to the LLM so it can use the tools and pass the arguments correctly. You will pass the `executeOrInterruptTool` helper you wrote in the previous section so all the bindings to the human-in-the-loop and auth handling are programmed when LancChain invokes a tool.


````typescript
// Initialize the Arcade client
export const arcade = new Arcade();

export type GetToolsProps = {
  arcade: Arcade;
  toolkits?: string[];
  tools?: string[];
  userId: string;
  limit?: number;
}


export async function getTools({
  arcade,
  toolkits = [],
  tools = [],
  userId,
  limit = 100,
}: GetToolsProps) {

  if (toolkits.length === 0 && tools.length === 0) {
      throw new Error("At least one tool or toolkit must be provided");
  }

  // Todo(Mateo): Add pagination support
  const from_toolkits = await Promise.all(toolkits.map(async (tkitName) => {
      const definitions = await arcade.tools.list({
          toolkit: tkitName,
          limit: limit
      });
      return definitions.items;
  }));

  const from_tools = await Promise.all(tools.map(async (toolName) => {
      return await arcade.tools.get(toolName);
  }));

  const all_tools = [...from_toolkits.flat(), ...from_tools];
  const unique_tools = Array.from(
      new Map(all_tools.map(tool => [tool.qualified_name, tool])).values()
  );

  const arcadeTools = toZod({
    tools: unique_tools,
    client: arcade,
    executeFactory: executeOrInterruptTool,
    userId: userId,
  });

  // Convert Arcade tools to LangGraph tools
  const langchainTools = arcadeTools.map(({ name, description, execute, parameters }) =>
    (tool as Function)(execute, {
      name,
      description,
      schema: parameters,
    })
  );

  return langchainTools;
}
````

## Building the Agent

Back on the `main.ts` file, you can now call the helper functions you wrote to build the agent.

### Retrieve the configured tools

Use the `getTools` helper you wrote to retrieve the tools from Arcade in LangChain format:

````typescript
const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});
````

### Write an interrupt handler

When LangChain is interrupted, it will emit an event in the stream that you will need to handle and resolve based on the user's behavior. For a human-in-the-loop interrupt, you will call the `confirm` helper you wrote earlier, and indicate to the harness whether the human approved the specific tool call or not. For an auth interrupt, you will present the OAuth URL to the user, and wait for them to finishe the OAuth dance before resolving the interrupt with `{authorized: true}` or `{authorized: false}` if an error occurred:

````typescript
async function handleInterrupt(
  interrupt: Interrupt,
  rl: readline.Interface
): Promise<{ authorized: boolean }> {
  const value = interrupt.value;
  const authorization_required = value.authorization_required;
  const hitl_required = value.hitl_required;
  if (authorization_required) {
    const tool_name = value.tool_name;
    const authorization_response = value.authorization_response;
    console.log("⚙️: Authorization required for tool call", tool_name);
    console.log(
      "⚙️: Please authorize in your browser",
      authorization_response.url
    );
    console.log("⚙️: Waiting for you to complete authorization...");
    try {
      await arcade.auth.waitForCompletion(authorization_response.id);
      console.log("⚙️: Authorization granted. Resuming execution...");
      return { authorized: true };
    } catch (error) {
      console.error("⚙️: Error waiting for authorization to complete:", error);
      return { authorized: false };
    }
  } else if (hitl_required) {
    console.log("⚙️: Human in the loop required for tool call", value.tool_name);
    console.log("⚙️: Please approve the tool call", value.input);
    const approved = await confirm("Do you approve this tool call?", rl);
    return { authorized: approved };
  }
  return { authorized: false };
}
````

### Create an Agent instance

Here you create the agent using the `createAgent` function. You pass the system prompt, the model, the tools, and the checkpointer. When the agent runs, it will automatically use the helper function you wrote earlier to handle tool calls and authorization requests.

````typescript
const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});
````

### Write the invoke helper

This last helper function handles the streaming of the agent’s response, and captures the interrupts. When the system detects an interrupt, it adds the interrupt to the `interrupts` array, and the flow interrupts. If there are no interrupts, it will just stream the agent’s to your console.

````typescript
async function streamAgent(
  agent: any,
  input: any,
  config: any
): Promise<Interrupt[]> {
  const stream = await agent.stream(input, {
    ...config,
    streamMode: "updates",
  });
  const interrupts: Interrupt[] = [];

  for await (const chunk of stream) {
    if (chunk.__interrupt__) {
      interrupts.push(...(chunk.__interrupt__ as Interrupt[]));
      continue;
    }
    for (const update of Object.values(chunk)) {
      for (const msg of (update as any)?.messages ?? []) {
        console.log("🤖: ", msg.toFormattedString());
      }
    }
  }

  return interrupts;
}
````

### Write the main function

Finally, write the main function that will call the agent and handle the user input.

Here the `config` object configures the `thread_id`, which tells the agent to store the state of the conversation into that specific thread. Like any typical agent loop, you:

1. Capture the user input
2. Stream the agent's response
3. Handle any authorization interrupts
4. Resume the agent after authorization
5. Handle any errors
6. Exit the loop if the user wants to quit

````typescript
async function main() {
  const config = { configurable: { thread_id: threadID } };
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log(chalk.green("Welcome to the chatbot! Type 'exit' to quit."));
  while (true) {
    const input = await rl.question("> ");
    if (input.toLowerCase() === "exit") {
      break;
    }
    rl.pause();

    try {
      let agentInput: any = {
        messages: [{ role: "user", content: input }],
      };

      // Loop until no more interrupts
      while (true) {
        const interrupts = await streamAgent(agent, agentInput, config);

        if (interrupts.length === 0) {
          break; // No more interrupts, we're done
        }

        // Handle all interrupts
        const decisions: any[] = [];
        for (const interrupt of interrupts) {
          decisions.push(await handleInterrupt(interrupt, rl));
        }

        // Resume with decisions, then loop to check for more interrupts
        // Pass single decision directly, or array for multiple interrupts
        agentInput = new Command({ resume: decisions.length === 1 ? decisions[0] : decisions });
      }
    } catch (error) {
      console.error(error);
    }

    rl.resume();
  }
  console.log(chalk.red("👋 Bye..."));
  process.exit(0);
}

// Run the main function
main().catch((err) => console.error(err));
````

## Running the Agent

### Run the agent

```bash
bun run main.ts
```

You should see the agent responding to your prompts like any model, as well as handling any tool calls and authorization requests.

## Next Steps

- Clone the [repository](https://github.com/arcade-agents/ts-langchain-Clickup) and run it
- Add more toolkits to the `toolkits` array to expand capabilities
- Customize the `systemPrompt` to specialize the agent's behavior
- Explore the [Arcade documentation](https://docs.arcade.dev) for available toolkits

