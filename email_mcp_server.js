#!/usr/bin/env node
/**
 * Email MCP Server - Gmail API integration for AI Employee
 * 
 * Provides tools for email operations:
 * - send_email: Send an email via Gmail API
 * - draft_email: Create a draft email
 * - mark_as_read: Mark an email as read
 * - search_email: Search for emails
 * - get_email: Get email details
 * - archive_email: Archive an email
 * - delete_email: Delete an email
 * 
 * Usage:
 *   node email_mcp_server.js --port 8809
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFile, writeFile, mkdir } from "fs/promises";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { google } from "googleapis";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Get directory paths
const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE_DIR = process.cwd();

// Configuration
const CONFIG = {
  credentialsPath: process.env.GMAIL_CREDENTIALS_PATH 
    ? (process.env.GMAIL_CREDENTIALS_PATH.startsWith('.') 
        ? join(BASE_DIR, process.env.GMAIL_CREDENTIALS_PATH)
        : process.env.GMAIL_CREDENTIALS_PATH)
    : join(BASE_DIR, "credentials", "gmail", "credentials.json"),
  tokenPath: process.env.GMAIL_TOKEN_PATH
    ? (process.env.GMAIL_TOKEN_PATH.startsWith('.')
        ? join(BASE_DIR, process.env.GMAIL_TOKEN_PATH)
        : process.env.GMAIL_TOKEN_PATH)
    : join(BASE_DIR, "credentials", "gmail", "token.json"),
  scopes: [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
  ],
};

// OAuth2 client and service cache
let oauth2Client = null;
let gmailService = null;

/**
 * Get or create OAuth2 client
 */
async function getOAuth2Client() {
  if (oauth2Client) {
    return oauth2Client;
  }

  try {
    // Read credentials
    const credentialsContent = await readFile(CONFIG.credentialsPath, "utf-8");
    const credentials = JSON.parse(credentialsContent);

    oauth2Client = new google.auth.OAuth2(
      credentials.client_id,
      credentials.client_secret,
      credentials.redirect_uris[0]
    );

    // Try to load existing token
    try {
      const tokenContent = await readFile(CONFIG.tokenPath, "utf-8");
      const token = JSON.parse(tokenContent);
      oauth2Client.setCredentials(token);
    } catch (err) {
      console.error("No existing token found. Authentication required.");
    }

    return oauth2Client;
  } catch (error) {
    console.error("Error creating OAuth2 client:", error.message);
    throw new Error(`Failed to initialize OAuth2 client: ${error.message}`);
  }
}

/**
 * Get Gmail service
 */
async function getGmailService() {
  if (gmailService) {
    return gmailService;
  }

  const auth = await getOAuth2Client();
  
  // Refresh token if needed
  try {
    const { credentials } = oauth2Client;
    if (credentials.expired || !credentials.access_token) {
      await new Promise((resolve, reject) => {
        oauth2Client.refreshAccessToken((err, tokens) => {
          if (err) reject(err);
          else {
            oauth2Client.setCredentials(tokens);
            saveTokens(tokens);
            resolve(tokens);
          }
        });
      });
    }
  } catch (error) {
    console.error("Token refresh failed:", error.message);
  }

  gmailService = google.gmail({ version: "v1", auth });
  return gmailService;
}

/**
 * Save tokens to file
 */
async function saveTokens(tokens) {
  try {
    const tokenDir = dirname(CONFIG.tokenPath);
    await mkdir(tokenDir, { recursive: true });
    await writeFile(CONFIG.tokenPath, JSON.stringify(tokens, null, 2));
    console.log("Tokens saved successfully");
  } catch (error) {
    console.error("Error saving tokens:", error.message);
  }
}

/**
 * Base64 encode email content
 */
function base64Encode(str) {
  return Buffer.from(str)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/**
 * Create email message
 */
function createEmail(to, subject, body, inReplyTo = null, references = null) {
  const lines = [
    `To: ${to}`,
    `Subject: ${subject}`,
    "Content-Type: text/plain; charset=utf-8",
    "MIME-Version: 1.0",
  ];

  if (inReplyTo) {
    lines.push(`In-Reply-To: ${inReplyTo}`);
  }

  if (references) {
    lines.push(`References: ${references}`);
  }

  lines.push("");
  lines.push(body);

  return base64Encode(lines.join("\n"));
}

/**
 * Parse email headers
 */
function parseHeaders(headers) {
  const headerMap = {};
  for (const header of headers) {
    headerMap[header.name.toLowerCase()] = header.value;
  }
  return headerMap;
}

/**
 * Extract email from From header
 */
function extractEmail(fromHeader) {
  const match = fromHeader.match(/<([^>]+)>/);
  return match ? match[1] : fromHeader.trim();
}

/**
 * Extract name from From header
 */
function extractName(fromHeader) {
  const match = fromHeader.match(/"?([^"<]+)"?\s*</);
  return match ? match[1].trim() : "";
}

/**
 * Extract body from message
 */
function extractBody(fullMsg) {
  const parts = fullMsg.payload?.parts || [];
  
  // Try plain text
  for (const part of parts) {
    if (part.mimeType === "text/plain") {
      const data = part.body?.data;
      if (data) {
        return Buffer.from(data, "base64url").toString("utf-8");
      }
    }
  }

  // Fallback to body
  const bodyData = fullMsg.payload?.body?.data;
  if (bodyData) {
    return Buffer.from(bodyData, "base64url").toString("utf-8");
  }

  // Fallback to HTML (stripped)
  for (const part of parts) {
    if (part.mimeType === "text/html") {
      const data = part.body?.data;
      if (data) {
        const html = Buffer.from(data, "base64url").toString("utf-8");
        return html.replace(/<[^>]+>/g, "");
      }
    }
  }

  return "";
}

// =============================================================================
// Tool Implementations
// =============================================================================

/**
 * Send an email
 */
async function sendEmail(params) {
  const { to, subject, body, inReplyTo, references } = params;

  if (!to || !subject || !body) {
    throw new Error("Missing required parameters: to, subject, body");
  }

  try {
    const service = await getGmailService();
    const raw = createEmail(to, subject, body, inReplyTo, references);

    const response = await service.users.messages.send({
      userId: "me",
      requestBody: { raw },
    });

    return {
      success: true,
      messageId: response.data.id,
      threadId: response.data.threadId,
      message: `Email sent successfully to ${to}`,
    };
  } catch (error) {
    console.error("Error sending email:", error);
    throw new Error(`Failed to send email: ${error.message}`);
  }
}

/**
 * Create a draft email
 */
async function draftEmail(params) {
  const { to, subject, body, inReplyTo, references } = params;

  if (!to || !subject || !body) {
    throw new Error("Missing required parameters: to, subject, body");
  }

  try {
    const service = await getGmailService();
    const raw = createEmail(to, subject, body, inReplyTo, references);

    const response = await service.users.drafts.create({
      userId: "me",
      requestBody: { message: { raw } },
    });

    return {
      success: true,
      draftId: response.data.id,
      messageId: response.data.message.id,
      threadId: response.data.message.threadId,
      message: "Draft created successfully",
    };
  } catch (error) {
    console.error("Error creating draft:", error);
    throw new Error(`Failed to create draft: ${error.message}`);
  }
}

/**
 * Mark an email as read
 */
async function markAsRead(params) {
  const { messageId } = params;

  if (!messageId) {
    throw new Error("Missing required parameter: messageId");
  }

  try {
    const service = await getGmailService();

    await service.users.messages.modify({
      userId: "me",
      id: messageId,
      requestBody: { removeLabelIds: ["UNREAD"] },
    });

    return {
      success: true,
      messageId,
      message: "Email marked as read",
    };
  } catch (error) {
    console.error("Error marking email as read:", error);
    throw new Error(`Failed to mark email as read: ${error.message}`);
  }
}

/**
 * Search for emails
 */
async function searchEmail(params) {
  const { query, maxResults = 10, includeBody = false } = params;

  if (!query) {
    throw new Error("Missing required parameter: query");
  }

  try {
    const service = await getGmailService();

    const response = await service.users.messages.list({
      userId: "me",
      q: query,
      maxResults: Math.min(maxResults, 500),
    });

    const messages = response.data.messages || [];
    const results = [];

    for (const msg of messages) {
      const fullMsg = await service.users.messages.get({
        userId: "me",
        id: msg.id,
        format: "full",
      });

      const headers = parseHeaders(fullMsg.data.payload?.headers || []);
      const emailInfo = {
        messageId: fullMsg.data.id,
        threadId: fullMsg.data.threadId,
        from: headers.from || "Unknown",
        fromEmail: extractEmail(headers.from || ""),
        fromName: extractName(headers.from || ""),
        to: headers.to || "",
        subject: headers.subject || "No Subject",
        date: headers.date || "",
        snippet: fullMsg.data.snippet || "",
        labels: fullMsg.data.labelIds || [],
        isUnread: fullMsg.data.labelIds?.includes("UNREAD") || false,
      };

      if (includeBody) {
        emailInfo.body = extractBody(fullMsg.data);
      }

      results.push(emailInfo);
    }

    return {
      success: true,
      count: results.length,
      messages: results,
    };
  } catch (error) {
    console.error("Error searching emails:", error);
    throw new Error(`Failed to search emails: ${error.message}`);
  }
}

/**
 * Get email details
 */
async function getEmail(params) {
  const { messageId, includeBody = false } = params;

  if (!messageId) {
    throw new Error("Missing required parameter: messageId");
  }

  try {
    const service = await getGmailService();

    const response = await service.users.messages.get({
      userId: "me",
      id: messageId,
      format: "full",
    });

    const headers = parseHeaders(response.data.payload?.headers || []);
    const emailInfo = {
      messageId: response.data.id,
      threadId: response.data.threadId,
      from: headers.from || "Unknown",
      fromEmail: extractEmail(headers.from || ""),
      fromName: extractName(headers.from || ""),
      to: headers.to || "",
      subject: headers.subject || "No Subject",
      date: headers.date || "",
      snippet: response.data.snippet || "",
      labels: response.data.labelIds || [],
      isUnread: response.data.labelIds?.includes("UNREAD") || false,
    };

    if (includeBody) {
      emailInfo.body = extractBody(response.data);
    }

    return { success: true, email: emailInfo };
  } catch (error) {
    console.error("Error getting email:", error);
    throw new Error(`Failed to get email: ${error.message}`);
  }
}

/**
 * Archive an email
 */
async function archiveEmail(params) {
  const { messageId } = params;

  if (!messageId) {
    throw new Error("Missing required parameter: messageId");
  }

  try {
    const service = await getGmailService();

    await service.users.messages.modify({
      userId: "me",
      id: messageId,
      requestBody: { removeLabelIds: ["INBOX"] },
    });

    return {
      success: true,
      messageId,
      message: "Email archived successfully",
    };
  } catch (error) {
    console.error("Error archiving email:", error);
    throw new Error(`Failed to archive email: ${error.message}`);
  }
}

/**
 * Delete an email
 */
async function deleteEmail(params) {
  const { messageId } = params;

  if (!messageId) {
    throw new Error("Missing required parameter: messageId");
  }

  try {
    const service = await getGmailService();

    await service.users.messages.delete({
      userId: "me",
      id: messageId,
    });

    return {
      success: true,
      messageId,
      message: "Email deleted successfully",
    };
  } catch (error) {
    console.error("Error deleting email:", error);
    throw new Error(`Failed to delete email: ${error.message}`);
  }
}

// =============================================================================
// MCP Server Setup
// =============================================================================

const server = new Server(
  {
    name: "email-mcp-server",
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
        name: "send_email",
        description: "Send an email via Gmail API. Requires approval before use.",
        inputSchema: {
          type: "object",
          properties: {
            to: { type: "string", description: "Recipient email address" },
            subject: { type: "string", description: "Email subject" },
            body: { type: "string", description: "Email body text" },
            inReplyTo: { type: "string", description: "Message ID this is replying to" },
            references: { type: "string", description: "References header for threading" },
          },
          required: ["to", "subject", "body"],
        },
      },
      {
        name: "draft_email",
        description: "Create a draft email without sending",
        inputSchema: {
          type: "object",
          properties: {
            to: { type: "string", description: "Recipient email address" },
            subject: { type: "string", description: "Email subject" },
            body: { type: "string", description: "Email body text" },
            inReplyTo: { type: "string", description: "Message ID this is replying to" },
            references: { type: "string", description: "References header for threading" },
          },
          required: ["to", "subject", "body"],
        },
      },
      {
        name: "mark_as_read",
        description: "Mark an email as read",
        inputSchema: {
          type: "object",
          properties: {
            messageId: { type: "string", description: "Gmail message ID" },
          },
          required: ["messageId"],
        },
      },
      {
        name: "search_email",
        description: "Search for emails using Gmail query syntax",
        inputSchema: {
          type: "object",
          properties: {
            query: { type: "string", description: "Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')" },
            maxResults: { type: "number", description: "Maximum number of results (default: 10, max: 500)", default: 10 },
            includeBody: { type: "boolean", description: "Whether to include email body in results", default: false },
          },
          required: ["query"],
        },
      },
      {
        name: "get_email",
        description: "Get details of a specific email by ID",
        inputSchema: {
          type: "object",
          properties: {
            messageId: { type: "string", description: "Gmail message ID" },
            includeBody: { type: "boolean", description: "Whether to include email body", default: false },
          },
          required: ["messageId"],
        },
      },
      {
        name: "archive_email",
        description: "Archive an email (remove from inbox)",
        inputSchema: {
          type: "object",
          properties: {
            messageId: { type: "string", description: "Gmail message ID" },
          },
          required: ["messageId"],
        },
      },
      {
        name: "delete_email",
        description: "Permanently delete an email. Use with caution!",
        inputSchema: {
          type: "object",
          properties: {
            messageId: { type: "string", description: "Gmail message ID" },
          },
          required: ["messageId"],
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
      case "send_email":
        result = await sendEmail(args);
        break;
      case "draft_email":
        result = await draftEmail(args);
        break;
      case "mark_as_read":
        result = await markAsRead(args);
        break;
      case "search_email":
        result = await searchEmail(args);
        break;
      case "get_email":
        result = await getEmail(args);
        break;
      case "archive_email":
        result = await archiveEmail(args);
        break;
      case "delete_email":
        result = await deleteEmail(args);
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
  const port = process.argv[2] || "8809";
  
  console.log("=".repeat(60));
  console.log("📧 Email MCP Server");
  console.log("=".repeat(60));
  console.log(`Credentials: ${CONFIG.credentialsPath}`);
  console.log(`Token: ${CONFIG.tokenPath}`);
  console.log(`Port: ${port}`);
  console.log("=".repeat(60));
  console.log("");

  // Check for credentials
  try {
    await readFile(CONFIG.credentialsPath, "utf-8");
  } catch (error) {
    console.error(`❌ Credentials file not found: ${CONFIG.credentialsPath}`);
    console.log("");
    console.log("📋 Setup Instructions:");
    console.log("1. Go to https://console.cloud.google.com/apis/credentials");
    console.log("2. Create OAuth 2.0 Client ID (Desktop application)");
    console.log("3. Download credentials.json");
    console.log(`4. Save to: ${CONFIG.credentialsPath}`);
    process.exit(1);
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  console.log("Email MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
