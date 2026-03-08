#!/usr/bin/env node
/**
 * Accounting MCP Server - Odoo ERP Integration
 *
 * Provides tools for accounting operations via Odoo:
 * - create_invoice: Create a new customer invoice
 * - get_balance_sheet: Retrieve balance sheet summary
 * - get_revenue_summary: Get revenue by period
 * - record_payment: Record a payment for an invoice
 * - get_invoices: List invoices with filtering
 * - get_outstanding_invoices: Get unpaid invoices
 * - create_partner: Create a new customer/vendor
 * - get_financial_summary: Get overall financial health
 *
 * Usage:
 *   node accounting_mcp_server.js --port 8811
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "child_process";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Configuration
const CONFIG = {
  odooUrl: process.env.ODOO_BASE_URL || "http://localhost:8069",
  odooDb: process.env.ODOO_DB_NAME || "odoo",
  odooUsername: process.env.ODOO_USERNAME || "admin",
  odooPassword: process.env.ODOO_PASSWORD || "",
  odooApiKey: process.env.ODOO_API_KEY || "",
};

// Python subprocess for Odoo operations
let pythonProcess = null;
let isInitialized = false;

/**
 * Initialize Python bridge for Odoo operations
 */
async function initializePythonBridge() {
  if (isInitialized) return true;

  try {
    // Verify Odoo client module is available
    const { execSync } = await import("child_process");
    execSync("python -c 'from modules.accounting.odoo_client import OdooClient'", {
      stdio: "ignore",
      cwd: process.cwd()
    });
    isInitialized = true;
    console.log("Python Odoo bridge initialized");
    return true;
  } catch (error) {
    console.error("Failed to initialize Python bridge:", error.message);
    return false;
  }
}

/**
 * Execute Python function and return result
 */
async function executePythonFunction(functionName, args = {}) {
  return new Promise((resolve, reject) => {
    const pythonCode = `
import json
import sys
import os
sys.path.insert(0, os.getcwd())

from modules.accounting.odoo_client import OdooClient

try:
    client = OdooClient(
        base_url="${CONFIG.odooUrl}",
        db_name="${CONFIG.odooDb}",
        username="${CONFIG.odooUsername}",
        password="${CONFIG.odooPassword}",
        api_key="${CONFIG.odooApiKey}"
    )
    client.authenticate()
    
    # Execute the requested function
    result = client.${functionName}(**${JSON.stringify(args)})
    print(json.dumps({"success": True, "result": result}, default=str))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
finally:
    client.close()
`;

    const python = spawn("python", ["-c", pythonCode], {
      cwd: process.cwd(),
      env: process.env
    });

    let output = "";
    let errorOutput = "";

    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      errorOutput += data.toString();
    });

    python.on("close", (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(output.trim());
          resolve(result);
        } catch (e) {
          resolve({ success: true, result: output.trim() });
        }
      } else {
        reject(new Error(errorOutput || `Python exited with code ${code}`));
      }
    });
  });
}

// =============================================================================
// Tool Implementations
// =============================================================================

/**
 * Create a new invoice
 */
async function createInvoice(params) {
  const { partnerId, invoiceType = "out_invoice", lines = [], invoiceDate, paymentTermId, narration } = params;

  if (!partnerId) {
    throw new Error("Missing required parameter: partnerId");
  }

  return executePythonFunction("create_invoice", {
    partner_id: partnerId,
    invoice_type: invoiceType,
    lines: lines,
    invoice_date: invoiceDate,
    payment_term_id: paymentTermId,
    narration: narration
  });
}

/**
 * Get balance sheet
 */
async function getBalanceSheet(params = {}) {
  const { date } = params;
  return executePythonFunction("get_balance_sheet", { date });
}

/**
 * Get revenue summary
 */
async function getRevenueSummary(params = {}) {
  const { period = "month", limit = 12 } = params;
  return executePythonFunction("get_revenue_summary", { period, limit });
}

/**
 * Record a payment
 */
async function recordPayment(params) {
  const { invoiceId, amount, paymentDate, paymentMethod, paymentReference } = params;

  if (!invoiceId || !amount) {
    throw new Error("Missing required parameters: invoiceId, amount");
  }

  return executePythonFunction("register_payment", {
    invoice_id: invoiceId,
    amount: amount,
    payment_date: paymentDate,
    payment_method: paymentMethod,
    payment_reference: paymentReference
  });
}

/**
 * Get invoices list
 */
async function getInvoices(params = {}) {
  const { domain = [], limit = 100, offset = 0, fields } = params;
  return executePythonFunction("get_invoices", { domain, limit, offset, fields });
}

/**
 * Get outstanding invoices
 */
async function getOutstandingInvoices(params = {}) {
  const { partnerId, limit = 100 } = params;
  return executePythonFunction("get_outstanding_invoices", { 
    partner_id: partnerId, 
    limit 
  });
}

/**
 * Create a new partner
 */
async function createPartner(params) {
  const { name, email, phone, vat, isCustomer = true, isSupplier = false, street, city, countryId } = params;

  if (!name) {
    throw new Error("Missing required parameter: name");
  }

  return executePythonFunction("create_partner", {
    name,
    email,
    phone,
    vat,
    is_customer: isCustomer,
    is_supplier: isSupplier,
    street,
    city,
    country_id: countryId
  });
}

/**
 * Get financial summary
 */
async function getFinancialSummary(params = {}) {
  try {
    const [balanceSheet, revenueSummary, outstandingInvoices] = await Promise.all([
      getBalanceSheet({}),
      getRevenueSummary({ period: "month", limit: 6 }),
      getOutstandingInvoices({ limit: 50 })
    ]);

    return {
      success: true,
      result: {
        balance_sheet: balanceSheet.result,
        revenue_summary: revenueSummary.result,
        outstanding_invoices: {
          count: outstandingInvoices.result?.length || 0,
          total: outstandingInvoices.result?.reduce((sum, inv) => sum + (inv.amount_total || 0), 0) || 0
        },
        generated_at: new Date().toISOString()
      }
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

// =============================================================================
// MCP Server Setup
// =============================================================================

const server = new Server(
  {
    name: "accounting-mcp-server",
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
        name: "create_invoice",
        description: "Create a new customer invoice in Odoo. Requires approval before use.",
        inputSchema: {
          type: "object",
          properties: {
            partnerId: { 
              type: "number", 
              description: "Customer/partner ID in Odoo" 
            },
            invoiceType: { 
              type: "string", 
              description: "Invoice type: out_invoice, out_refund, in_invoice, in_refund",
              default: "out_invoice"
            },
            lines: { 
              type: "array", 
              description: "Invoice line items",
              items: {
                type: "object",
                properties: {
                  product_id: { type: "number", description: "Product ID" },
                  name: { type: "string", description: "Line description" },
                  quantity: { type: "number", description: "Quantity", default: 1 },
                  price_unit: { type: "number", description: "Unit price", default: 0 }
                }
              }
            },
            invoiceDate: { 
              type: "string", 
              description: "Invoice date (YYYY-MM-DD)",
              default: "today"
            },
            paymentTermId: { 
              type: "number", 
              description: "Payment term ID" 
            },
            narration: { 
              type: "string", 
              description: "Additional notes" 
            }
          },
          required: ["partnerId"],
        },
      },
      {
        name: "get_balance_sheet",
        description: "Retrieve balance sheet summary from Odoo",
        inputSchema: {
          type: "object",
          properties: {
            date: { 
              type: "string", 
              description: "Report date (YYYY-MM-DD), defaults to today" 
            }
          }
        }
      },
      {
        name: "get_revenue_summary",
        description: "Get revenue summary grouped by period",
        inputSchema: {
          type: "object",
          properties: {
            period: { 
              type: "string", 
              description: "Period type: day, week, month, year",
              default: "month"
            },
            limit: { 
              type: "number", 
              description: "Number of periods to include",
              default: 12
            }
          }
        }
      },
      {
        name: "record_payment",
        description: "Record a payment for an invoice. Requires approval before use.",
        inputSchema: {
          type: "object",
          properties: {
            invoiceId: { 
              type: "number", 
              description: "Invoice ID to pay" 
            },
            amount: { 
              type: "number", 
              description: "Payment amount" 
            },
            paymentDate: { 
              type: "string", 
              description: "Payment date (YYYY-MM-DD)",
              default: "today"
            },
            paymentMethod: { 
              type: "string", 
              description: "Payment method name" 
            },
            paymentReference: { 
              type: "string", 
              description: "Payment reference/note" 
            }
          },
          required: ["invoiceId", "amount"],
        },
      },
      {
        name: "get_invoices",
        description: "List invoices with optional filtering",
        inputSchema: {
          type: "object",
          properties: {
            domain: { 
              type: "array", 
              description: "Odoo domain filter",
              default: []
            },
            limit: { 
              type: "number", 
              description: "Maximum records",
              default: 100
            },
            offset: { 
              type: "number", 
              description: "Record offset",
              default: 0
            },
            fields: { 
              type: "array", 
              description: "Specific fields to retrieve"
            }
          }
        }
      },
      {
        name: "get_outstanding_invoices",
        description: "Get unpaid/partially paid invoices",
        inputSchema: {
          type: "object",
          properties: {
            partnerId: { 
              type: "number", 
              description: "Filter by partner ID" 
            },
            limit: { 
              type: "number", 
              description: "Maximum records",
              default: 100
            }
          }
        }
      },
      {
        name: "create_partner",
        description: "Create a new customer or vendor partner",
        inputSchema: {
          type: "object",
          properties: {
            name: { 
              type: "string", 
              description: "Partner name" 
            },
            email: { 
              type: "string", 
              description: "Email address" 
            },
            phone: { 
              type: "string", 
              description: "Phone number" 
            },
            vat: { 
              type: "string", 
              description: "VAT number" 
            },
            isCustomer: { 
              type: "boolean", 
              description: "Is a customer",
              default: true
            },
            isSupplier: { 
              type: "boolean", 
              description: "Is a supplier",
              default: false
            },
            street: { 
              type: "string", 
              description: "Street address" 
            },
            city: { 
              type: "string", 
              description: "City" 
            },
            countryId: { 
              type: "number", 
              description: "Country ID" 
            }
          },
          required: ["name"],
        },
      },
      {
        name: "get_financial_summary",
        description: "Get comprehensive financial summary including balance sheet, revenue, and outstanding invoices",
        inputSchema: {
          type: "object",
          properties: {}
        }
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
    // Initialize Python bridge if needed
    await initializePythonBridge();

    let result;

    switch (name) {
      case "create_invoice":
        result = await createInvoice(args);
        break;
      case "get_balance_sheet":
        result = await getBalanceSheet(args);
        break;
      case "get_revenue_summary":
        result = await getRevenueSummary(args);
        break;
      case "record_payment":
        result = await recordPayment(args);
        break;
      case "get_invoices":
        result = await getInvoices(args);
        break;
      case "get_outstanding_invoices":
        result = await getOutstandingInvoices(args);
        break;
      case "create_partner":
        result = await createPartner(args);
        break;
      case "get_financial_summary":
        result = await getFinancialSummary(args);
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
  const port = process.argv[2] || "8811";

  console.log("=".repeat(60));
  console.log("💰 Accounting MCP Server");
  console.log("=".repeat(60));
  console.log(`Odoo URL: ${CONFIG.odooUrl}`);
  console.log(`Database: ${CONFIG.odooDb}`);
  console.log(`Username: ${CONFIG.odooUsername}`);
  console.log(`Port: ${port}`);
  console.log("=".repeat(60));
  console.log("");

  // Check for Odoo configuration
  if (!CONFIG.odooPassword && !CONFIG.odooApiKey) {
    console.warn("⚠️  Warning: No Odoo password or API key configured");
    console.log("Set ODOO_PASSWORD or ODOO_API_KEY in .env file");
  }

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.log("Accounting MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
