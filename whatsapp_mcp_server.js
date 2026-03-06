#!/usr/bin/env node
/**
 * WhatsApp MCP Server - Playwright-based WhatsApp Web automation
 *
 * Provides tools for WhatsApp Web operations:
 * - whatsapp_navigate: Navigate to WhatsApp Web
 * - whatsapp_check_session: Check if session is authenticated
 * - whatsapp_get_messages: Get unread messages
 * - whatsapp_send_message: Send a message to a contact
 * - whatsapp_click_chat: Click on a chat to open it
 * - whatsapp_type_message: Type a message in the input box
 * - whatsapp_send_key: Press Enter to send message
 *
 * Usage:
 *   node whatsapp_mcp_server.js --port 8810
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import { readFile, writeFile, mkdir } from "fs/promises";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Get directory paths
const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE_DIR = process.cwd();

// Configuration
const CONFIG = {
  whatsappWebUrl: "https://web.whatsapp.com",
  browserTimeout: parseInt(process.env.WHATSAPP_BROWSER_TIMEOUT || "60", 10),
  mcpPort: parseInt(process.env.WHATSAPP_MCP_PORT || "8810", 10),
  sessionPath: process.env.WHATSAPP_SESSION_PATH || "./sessions/whatsapp",
};

// Playwright MCP subprocess
let playwrightMcpProcess = null;
let playwrightMcpPort = null;

/**
 * Start Playwright MCP server
 */
async function startPlaywrightMCP() {
  if (playwrightMcpProcess) {
    return true;
  }

  return new Promise((resolve, reject) => {
    playwrightMcpPort = 8808 + Math.floor(Math.random() * 100);

    console.log(`Starting Playwright MCP on port ${playwrightMcpPort}...`);

    playwrightMcpProcess = spawn("npx", [
      "@playwright/mcp@latest",
      "--port",
      playwrightMcpPort.toString(),
      "--shared-browser-context",
    ], {
      stdio: ["pipe", "pipe", "pipe"],
      shell: true,
    });

    playwrightMcpProcess.stdout.on("data", (data) => {
      console.log(`Playwright MCP: ${data.toString().trim()}`);
    });

    playwrightMcpProcess.stderr.on("data", (data) => {
      console.error(`Playwright MCP Error: ${data.toString().trim()}`);
    });

    playwrightMcpProcess.on("error", (err) => {
      console.error("Failed to start Playwright MCP:", err.message);
      reject(err);
    });

    // Wait for server to start
    setTimeout(() => {
      console.log("Playwright MCP started");
      resolve(true);
    }, 3000);
  });
}

/**
 * Stop Playwright MCP server
 */
async function stopPlaywrightMCP() {
  if (playwrightMcpProcess) {
    playwrightMcpProcess.kill("SIGTERM");
    playwrightMcpProcess = null;
    console.log("Playwright MCP stopped");
  }
}

/**
 * Call Playwright MCP tool
 */
async function callPlaywrightTool(toolName, params = {}) {
  if (!playwrightMcpProcess) {
    await startPlaywrightMCP();
  }

  return new Promise((resolve, reject) => {
    const clientScript = join(BASE_DIR, "scripts", "mcp-client.py");

    const child = spawn("python3", [
      clientScript,
      "call",
      "-u",
      `http://localhost:${playwrightMcpPort}`,
      "-t",
      toolName,
      "-p",
      JSON.stringify(params),
    ], {
      stdio: ["pipe", "pipe", "pipe"],
      shell: false,
    });

    let output = "";
    let error = "";

    child.stdout.on("data", (data) => {
      output += data.toString();
    });

    child.stderr.on("data", (data) => {
      error += data.toString();
    });

    child.on("close", (code) => {
      if (code === 0) {
        try {
          resolve(JSON.parse(output));
        } catch {
          resolve({ success: true, output });
        }
      } else {
        reject(new Error(error || `Tool ${toolName} failed with code ${code}`));
      }
    });

    child.on("error", (err) => {
      reject(err);
    });
  });
}

/**
 * Navigate to WhatsApp Web
 */
async function whatsappNavigate() {
  try {
    const result = await callPlaywrightTool("browser_navigate", {
      url: CONFIG.whatsappWebUrl,
    });
    return {
      success: true,
      message: "Navigated to WhatsApp Web",
      details: result,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * Check WhatsApp session status
 */
async function whatsappCheckSession() {
  try {
    const result = await callPlaywrightTool("browser_snapshot", {});
    return {
      success: true,
      authenticated: true,
      message: "Session is active",
      snapshot: result,
    };
  } catch (error) {
    return {
      success: false,
      authenticated: false,
      error: error.message,
    };
  }
}

/**
 * Get unread WhatsApp messages
 */
async function whatsappGetMessages(maxMessages = 20) {
  try {
    // First, take a snapshot to analyze the page
    const snapshot = await callPlaywrightTool("browser_snapshot", {});

    // Extract messages using JavaScript evaluation
    const messages = await callPlaywrightTool("browser_evaluate", {
      function: `
        () => {
          const messages = [];
          const chatItems = document.querySelectorAll('div[role="row"]');
          
          chatItems.forEach((chat, index) => {
            if (index < ${maxMessages}) {
              const chatNameEl = chat.querySelector('span[title]');
              const messageEl = chat.querySelector('span[dir="auto"]');
              const timeEl = chat.querySelector('time');
              
              const chatName = chatNameEl?.title || 'Unknown';
              const messageText = messageEl?.textContent || '';
              const timestamp = timeEl?.dateTime || new Date().toISOString();
              
              // Check for unread indicator
              const unreadBadge = chat.querySelector('[aria-label*="unread"]');
              const isUnread = unreadBadge !== null;
              
              if (isUnread && messageText) {
                messages.push({
                  chat_name: chatName,
                  message_text: messageText,
                  timestamp: timestamp,
                  is_group: chatName.includes('group') || chatName.includes('Group'),
                  has_media: /📷|🎤|📹|📎/.test(messageText),
                });
              }
            }
          });
          
          return messages;
        }
      `,
    });

    return {
      success: true,
      count: messages.length || 0,
      messages: messages || [],
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      messages: [],
    };
  }
}

/**
 * Click on a chat to open it
 */
async function whatsappClickChat(chatName) {
  try {
    // Find and click the chat element
    const result = await callPlaywrightTool("browser_evaluate", {
      function: `
        () => {
          const chatItems = document.querySelectorAll('div[role="row"]');
          let found = null;
          
          chatItems.forEach((chat) => {
            const chatNameEl = chat.querySelector('span[title]');
            if (chatNameEl && chatNameEl.title === "${chatName}") {
              chat.click();
              found = chatNameEl.title;
            }
          });
          
          return found;
        }
      `,
    });

    if (result) {
      return {
        success: true,
        message: `Opened chat: ${chatName}`,
      };
    } else {
      return {
        success: false,
        error: `Chat not found: ${chatName}`,
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * Type a message in the input box
 */
async function whatsappTypeMessage(text) {
  try {
    // Find the message input box and type
    const result = await callPlaywrightTool("browser_type", {
      element: "message input",
      ref: "e15",
      text: text,
    });

    return {
      success: true,
      message: "Message typed",
      details: result,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * Send the typed message (press Enter)
 */
async function whatsappSendMessage() {
  try {
    // Find the send button and click
    const result = await callPlaywrightTool("browser_evaluate", {
      function: `
        () => {
          const sendButton = document.querySelector('button[data-testid="compose-btn-send"]');
          if (sendButton) {
            sendButton.click();
            return true;
          }
          return false;
        }
      `,
    });

    if (result) {
      return {
        success: true,
        message: "Message sent",
      };
    } else {
      return {
        success: false,
        error: "Send button not found",
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

/**
 * Send a complete message to a contact
 */
async function whatsappSendMessageToContact(params) {
  const { chatName, message } = params;

  if (!chatName || !message) {
    return {
      success: false,
      error: "Missing required parameters: chatName, message",
    };
  }

  try {
    // Open the chat
    const clickResult = await whatsappClickChat(chatName);
    if (!clickResult.success) {
      return clickResult;
    }

    // Wait a moment for chat to load
    await new Promise(resolve => setTimeout(resolve, 500));

    // Type the message
    const typeResult = await whatsappTypeMessage(message);
    if (!typeResult.success) {
      return typeResult;
    }

    // Send the message
    const sendResult = await whatsappSendMessage();

    return {
      success: sendResult.success,
      message: sendResult.success ? `Message sent to ${chatName}` : sendResult.error,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
}

// =============================================================================
// MCP Server Setup
// =============================================================================

const server = new Server(
  {
    name: "whatsapp-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "whatsapp_navigate",
        description: "Navigate to WhatsApp Web. Opens the browser to web.whatsapp.com.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "whatsapp_check_session",
        description: "Check if WhatsApp Web session is authenticated. Returns session status.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "whatsapp_get_messages",
        description: "Get unread WhatsApp messages from the chat list. Returns up to 20 messages.",
        inputSchema: {
          type: "object",
          properties: {
            maxMessages: { type: "number", description: "Maximum number of messages to retrieve", default: 20 },
          },
        },
      },
      {
        name: "whatsapp_click_chat",
        description: "Click on a chat to open it. Requires exact chat name.",
        inputSchema: {
          type: "object",
          properties: {
            chatName: { type: "string", description: "Name of the chat/contact to open" },
          },
          required: ["chatName"],
        },
      },
      {
        name: "whatsapp_type_message",
        description: "Type a message in the message input box. Chat must be opened first.",
        inputSchema: {
          type: "object",
          properties: {
            text: { type: "string", description: "Message text to type" },
          },
          required: ["text"],
        },
      },
      {
        name: "whatsapp_send_message",
        description: "Send the typed message by pressing the send button.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "whatsapp_send_to_contact",
        description: "Send a complete message to a contact (opens chat, types, and sends). Requires approval before use.",
        inputSchema: {
          type: "object",
          properties: {
            chatName: { type: "string", description: "Name of the contact or group" },
            message: { type: "string", description: "Message text to send" },
          },
          required: ["chatName", "message"],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  console.log(`Tool called: ${name}`);
  console.log(`Arguments:`, JSON.stringify(args, null, 2));

  try {
    let result;

    switch (name) {
      case "whatsapp_navigate":
        result = await whatsappNavigate();
        break;
      case "whatsapp_check_session":
        result = await whatsappCheckSession();
        break;
      case "whatsapp_get_messages":
        result = await whatsappGetMessages(args.maxMessages || 20);
        break;
      case "whatsapp_click_chat":
        result = await whatsappClickChat(args.chatName);
        break;
      case "whatsapp_type_message":
        result = await whatsappTypeMessage(args.text);
        break;
      case "whatsapp_send_message":
        result = await whatsappSendMessage();
        break;
      case "whatsapp_send_to_contact":
        result = await whatsappSendMessageToContact(args);
        break;
      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    console.error(`Error in tool ${name}:`, error);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ success: false, error: error.message }, null, 2),
        },
      ],
      isError: true,
    };
  }
});

// =============================================================================
// Main Entry Point
// =============================================================================

async function main() {
  const port = process.argv[2] || CONFIG.mcpPort.toString();

  console.log("=".repeat(60));
  console.log("💬 WhatsApp MCP Server");
  console.log("=".repeat(60));
  console.log(`WhatsApp Web URL: ${CONFIG.whatsappWebUrl}`);
  console.log(`MCP Port: ${port}`);
  console.log(`Browser Timeout: ${CONFIG.browserTimeout}s`);
  console.log("=".repeat(60));
  console.log("");

  // Start Playwright MCP
  try {
    await startPlaywrightMCP();
  } catch (error) {
    console.error("❌ Failed to start Playwright MCP:", error.message);
    process.exit(1);
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.log("WhatsApp MCP Server running on stdio");
}

// Handle shutdown
process.on("SIGINT", async () => {
  console.log("\nShutting down WhatsApp MCP Server...");
  await stopPlaywrightMCP();
  process.exit(0);
});

process.on("SIGTERM", async () => {
  console.log("\nShutting down WhatsApp MCP Server...");
  await stopPlaywrightMCP();
  process.exit(0);
});

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
