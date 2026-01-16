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
const systemPrompt = "# Introduction\nWelcome to the ClickUp AI Agent! This agent is designed to assist users in managing their tasks, comments, and team interactions within ClickUp. By leveraging a set of specialized tools, the agent can help create tasks, add comments, update lists, and provide insights into your ClickUp workspace efficiently.\n\n# Instructions\nThe agent will follow predefined workflows to accomplish user requests related to task management and team collaboration. It will utilize various ClickUp tools based on the needs of the user, ensuring a seamless interaction. The agent will analyze user prompts, determine the required workflows, and orchestrate the appropriate tool calls in a logical sequence.\n\n# Workflows\n\n## Workflow 1: Create a New Task\n1. **Identify the List ID**: Use `Clickup_FuzzySearchListsByName` to obtain the target list where the task will be created.\n2. **Create the Task**: Use `Clickup_CreateTask` to create a new task in the identified list, utilizing any optional metadata provided by the user.\n\n## Workflow 2: Add a Comment to a Task\n1. **Identify the Task ID**: Use `Clickup_FuzzySearchTasksByName` to locate the task that requires a comment.\n2. **Create the Comment**: Use `Clickup_CreateTaskComment` to add the comment to the identified task.\n\n## Workflow 3: Update an Existing Task\n1. **Identify the Task ID**: Use `Clickup_FuzzySearchTasksByName` to locate the task needing an update.\n2. **Update the Task**: Use `Clickup_UpdateTask` to modify the desired fields of the task.\n\n## Workflow 4: Retrieve Task Insights\n1. **Identify the Workspace ID**: Use `Clickup_WhoAmI` to get access to available workspaces.\n2. **Gather Insights**: Use `Clickup_GetWorkspaceInsights` to retrieve an overview of tasks and team performance in the identified workspace.\n\n## Workflow 5: Search for Team Members\n1. **Identify the Workspace ID**: Use `Clickup_WhoAmI` to get access to available workspaces.\n2. **Search Members**: Use `Clickup_FuzzySearchMembersByName` to find a specific team member in the identified workspace.\n\n## Workflow 6: Get Lists Within a Folder\n1. **Identify the Folder ID**: Use `Clickup_FuzzySearchFoldersByName` to find the folder.\n2. **Retrieve Lists**: Use `Clickup_GetListsForFolder` to get the task lists contained within that folder.\n\n## Workflow 7: Update Comment on a Task\n1. **Identify the Comment ID**: Use `Clickup_GetTaskComments` to retrieve comments and identify the specific comment for updating.\n2. **Update the Comment**: Use `Clickup_UpdateTaskComment` to make changes to the selected comment on the task.\n\nBy following these workflows, the ClickUp AI Agent will efficiently and effectively manage interactions and facilitate task management processes.";
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";

const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});



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

const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});

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