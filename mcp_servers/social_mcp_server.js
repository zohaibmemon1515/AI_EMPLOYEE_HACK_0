#!/usr/bin/env node
/**
 * Social Media MCP Server - Multi-Platform Social Media Integration
 *
 * Provides tools for social media operations across platforms:
 * - publish_facebook: Publish post to Facebook
 * - publish_instagram: Publish post to Instagram
 * - publish_twitter: Publish tweet
 * - schedule_post: Schedule a post for later
 * - get_engagement_metrics: Get metrics for a post
 * - get_recent_posts: Get recent posts from platform
 * - generate_content: Generate post content suggestions
 * - get_social_summary: Get performance summary
 *
 * Usage:
 *   node social_mcp_server.js --port 8812
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
  facebook: {
    pageAccessToken: process.env.FACEBOOK_PAGE_ACCESS_TOKEN || "",
    pageId: process.env.FACEBOOK_PAGE_ID || ""
  },
  instagram: {
    businessAccountId: process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID || "",
    accessToken: process.env.INSTAGRAM_ACCESS_TOKEN || ""
  },
  twitter: {
    apiKey: process.env.TWITTER_API_KEY || "",
    apiSecret: process.env.TWITTER_API_SECRET || "",
    accessToken: process.env.TWITTER_ACCESS_TOKEN || "",
    accessTokenSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET || "",
    bearerToken: process.env.TWITTER_BEARER_TOKEN || ""
  }
};

// Python subprocess cache
let pythonProcess = null;

/**
 * Execute Python function and return result
 */
async function executePythonFunction(modulePath, functionName, args = {}) {
  return new Promise((resolve, reject) => {
    const pythonCode = `
import json
import sys
import os
sys.path.insert(0, os.getcwd())

from ${modulePath.replace(/\//g, '.')} import ${functionName.charAt(0).toUpperCase() + functionName.slice(1)}

try:
    # Initialize the agent/class
    if "${functionName}" === "FacebookAgent":
        from ${modulePath.replace(/\//g, '.')} import FacebookAgent
        agent = FacebookAgent()
        result = {"configured": agent.is_configured}
    elif "${functionName}" === "InstagramAgent":
        from ${modulePath.replace(/\//g, '.')} import InstagramAgent
        agent = InstagramAgent()
        result = {"configured": agent.is_configured}
    elif "${functionName}" === "TwitterAgent":
        from ${modulePath.replace(/\//g, '.')} import TwitterAgent
        agent = TwitterAgent()
        result = {"configured": agent.is_configured}
    else:
        result = {"error": "Unknown function"}
    
    print(json.dumps({"success": True, "result": result}, default=str))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
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

/**
 * Execute social media operation via Python module
 */
async function executeSocialOperation(operation, params) {
  const pythonCode = `
import json
import sys
import os
from datetime import datetime, timedelta
sys.path.insert(0, os.getcwd())

operation = "${operation}"
params = ${JSON.stringify(params)}

try:
    result = {"success": False, "error": "Unknown operation"}
    
    if operation == "publish_facebook":
        from modules.social.facebook_agent import FacebookAgent
        agent = FacebookAgent()
        if not agent.is_configured:
            result = {"success": False, "error": "Facebook not configured"}
        else:
            post = agent.publish_post(
                message=params.get("message", ""),
                link=params.get("link"),
                image_url=params.get("image_url"),
                scheduled_time=params.get("scheduled_time")
            )
            result = {
                "success": True,
                "post_id": post.post_id,
                "platform": "facebook"
            }
    
    elif operation == "publish_instagram":
        from modules.social.instagram_agent import InstagramAgent
        agent = InstagramAgent()
        if not agent.is_configured:
            result = {"success": False, "error": "Instagram not configured"}
        else:
            post = agent.publish_post(
                image_url=params.get("image_url", ""),
                caption=params.get("caption", "")
            )
            result = {
                "success": True,
                "media_id": post.media_id,
                "platform": "instagram"
            }
    
    elif operation == "publish_twitter":
        from modules.social.twitter_agent import TwitterAgent
        agent = TwitterAgent()
        if not agent.is_configured:
            result = {"success": False, "error": "Twitter not configured"}
        else:
            tweet = agent.publish_tweet(
                text=params.get("text", ""),
                media_urls=params.get("media_urls", [])
            )
            result = {
                "success": True,
                "tweet_id": tweet.tweet_id,
                "platform": "twitter"
            }
    
    elif operation == "get_facebook_metrics":
        from modules.social.facebook_agent import FacebookAgent
        agent = FacebookAgent()
        if agent.is_configured:
            metrics = agent.get_engagement_metrics(params.get("post_id"))
            result = {
                "success": True,
                "metrics": {
                    "likes": metrics.likes,
                    "comments": metrics.comments,
                    "shares": metrics.shares,
                    "engagement_rate": metrics.engagement_rate
                }
            }
        else:
            result = {"success": False, "error": "Facebook not configured"}
    
    elif operation == "get_instagram_metrics":
        from modules.social.instagram_agent import InstagramAgent
        agent = InstagramAgent()
        if agent.is_configured:
            metrics = agent.get_engagement_metrics(params.get("media_id"))
            result = {
                "success": True,
                "metrics": {
                    "likes": metrics.likes,
                    "comments": metrics.comments,
                    "saves": metrics.saves,
                    "reach": metrics.reach,
                    "engagement_rate": metrics.engagement_rate
                }
            }
        else:
            result = {"success": False, "error": "Instagram not configured"}
    
    elif operation == "get_twitter_metrics":
        from modules.social.twitter_agent import TwitterAgent
        agent = TwitterAgent()
        if agent.is_configured:
            metrics = agent.get_tweet_metrics(params.get("tweet_id"))
            result = {
                "success": True,
                "metrics": {
                    "likes": metrics.likes,
                    "retweets": metrics.retweets,
                    "replies": metrics.replies,
                    "quotes": metrics.quotes
                }
            }
        else:
            result = {"success": False, "error": "Twitter not configured"}
    
    elif operation == "get_recent_posts":
        platform = params.get("platform", "facebook")
        limit = params.get("limit", 5)
        
        if platform == "facebook":
            from modules.social.facebook_agent import FacebookAgent
            agent = FacebookAgent()
            if agent.is_configured:
                posts = agent.get_recent_posts(limit)
                result = {"success": True, "posts": posts}
            else:
                result = {"success": False, "error": "Facebook not configured"}
        elif platform == "instagram":
            from modules.social.instagram_agent import InstagramAgent
            agent = InstagramAgent()
            if agent.is_configured:
                posts = agent.get_recent_media(limit)
                result = {"success": True, "posts": posts}
            else:
                result = {"success": False, "error": "Instagram not configured"}
        elif platform == "twitter":
            from modules.social.twitter_agent import TwitterAgent
            agent = TwitterAgent()
            if agent.is_configured:
                posts = agent.get_recent_tweets(limit)
                result = {"success": True, "posts": posts}
            else:
                result = {"success": False, "error": "Twitter not configured"}
    
    elif operation == "generate_content":
        platform = params.get("platform", "facebook")
        post_type = params.get("post_type", "educational")
        topic = params.get("topic", "")
        
        if platform == "facebook":
            from modules.social.facebook_agent import FacebookAgent
            agent = FacebookAgent()
            content = agent.generate_post_content(post_type, topic)
        elif platform == "twitter":
            from modules.social.twitter_agent import TwitterAgent
            agent = TwitterAgent()
            content = agent.generate_tweet_content(post_type, topic)
        elif platform == "instagram":
            from modules.social.instagram_agent import InstagramAgent
            agent = InstagramAgent()
            content = {
                "post_type": post_type,
                "topic": topic,
                "suggested_hashtags": agent.generate_hashtags(topic)
            }
        
        result = {"success": True, "content": content}
    
    elif operation == "get_social_summary":
        from pathlib import Path
        from modules.social.social_summary import SocialSummaryGenerator
        vault_path = Path(params.get("vault_path", "./Vault"))
        generator = SocialSummaryGenerator(vault_path)
        summary = generator.generate_weekly_summary()
        result = {
            "success": True,
            "summary": summary.to_dict()
        }
    
    elif operation == "schedule_post":
        from pathlib import Path
        from modules.social.social_scheduler import SocialScheduler
        vault_path = Path(params.get("vault_path", "./Vault"))
        scheduler = SocialScheduler(vault_path)
        
        scheduled_time = None
        if params.get("scheduled_time"):
            scheduled_time = datetime.fromisoformat(params.get("scheduled_time"))
        
        post = scheduler.schedule_post(
            platform=params.get("platform", "facebook"),
            content=params.get("content", ""),
            scheduled_time=scheduled_time,
            post_type=params.get("post_type", "educational"),
            media_urls=params.get("media_urls", []),
            hashtags=params.get("hashtags", [])
        )
        result = {
            "success": True,
            "post_id": post.post_id,
            "scheduled_time": post.scheduled_time
        }
    
    print(json.dumps(result, default=str))
    
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
`;

    return new Promise((resolve, reject) => {
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

async function publishFacebook(params) {
  return executeSocialOperation("publish_facebook", params);
}

async function publishInstagram(params) {
  return executeSocialOperation("publish_instagram", params);
}

async function publishTwitter(params) {
  return executeSocialOperation("publish_twitter", params);
}

async function schedulePost(params) {
  return executeSocialOperation("schedule_post", params);
}

async function getEngagementMetrics(params) {
  const { platform, postId } = params;
  
  if (platform === "facebook") {
    return executeSocialOperation("get_facebook_metrics", { post_id: postId });
  } else if (platform === "instagram") {
    return executeSocialOperation("get_instagram_metrics", { media_id: postId });
  } else if (platform === "twitter") {
    return executeSocialOperation("get_twitter_metrics", { tweet_id: postId });
  }
  
  return { success: false, error: "Unknown platform" };
}

async function getRecentPosts(params) {
  return executeSocialOperation("get_recent_posts", params);
}

async function generateContent(params) {
  return executeSocialOperation("generate_content", params);
}

async function getSocialSummary(params) {
  return executeSocialOperation("get_social_summary", params);
}

// =============================================================================
// MCP Server Setup
// =============================================================================

const server = new Server(
  {
    name: "social-mcp-server",
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
        name: "publish_facebook",
        description: "Publish a post to Facebook page. Requires approval before use.",
        inputSchema: {
          type: "object",
          properties: {
            message: { type: "string", description: "Post message/content" },
            link: { type: "string", description: "Link to share" },
            image_url: { type: "string", description: "Image URL to attach" },
            scheduled_time: { type: "string", description: "ISO 8601 datetime for scheduling" }
          },
          required: ["message"]
        }
      },
      {
        name: "publish_instagram",
        description: "Publish a post to Instagram. Requires approval before use.",
        inputSchema: {
          type: "object",
          properties: {
            image_url: { type: "string", description: "Image URL to publish" },
            caption: { type: "string", description: "Post caption" }
          },
          required: ["image_url", "caption"]
        }
      },
      {
        name: "publish_twitter",
        description: "Publish a tweet. Requires approval before use.",
        inputSchema: {
          type: "object",
          properties: {
            text: { type: "string", description: "Tweet text (max 280 chars)", maxLength: 280 },
            media_urls: { type: "array", description: "Media URLs to attach", items: { type: "string" } }
          },
          required: ["text"]
        }
      },
      {
        name: "schedule_post",
        description: "Schedule a post for later publishing",
        inputSchema: {
          type: "object",
          properties: {
            platform: { type: "string", description: "Target platform", enum: ["facebook", "instagram", "twitter"] },
            content: { type: "string", description: "Post content" },
            scheduled_time: { type: "string", description: "ISO 8601 datetime" },
            post_type: { type: "string", description: "Post type", enum: ["educational", "case_study", "sales_cta", "engagement"] },
            media_urls: { type: "array", description: "Media URLs", items: { type: "string" } },
            hashtags: { type: "array", description: "Hashtags", items: { type: "string" } }
          },
          required: ["platform", "content", "scheduled_time"]
        }
      },
      {
        name: "get_engagement_metrics",
        description: "Get engagement metrics for a post",
        inputSchema: {
          type: "object",
          properties: {
            platform: { type: "string", description: "Platform", enum: ["facebook", "instagram", "twitter"] },
            postId: { type: "string", description: "Post/Media/Tweet ID" }
          },
          required: ["platform", "postId"]
        }
      },
      {
        name: "get_recent_posts",
        description: "Get recent posts from a platform",
        inputSchema: {
          type: "object",
          properties: {
            platform: { type: "string", description: "Platform", enum: ["facebook", "instagram", "twitter"] },
            limit: { type: "number", description: "Number of posts", default: 5 }
          },
          required: ["platform"]
        }
      },
      {
        name: "generate_content",
        description: "Generate post content suggestions",
        inputSchema: {
          type: "object",
          properties: {
            platform: { type: "string", description: "Platform", enum: ["facebook", "instagram", "twitter"] },
            post_type: { type: "string", description: "Post type", enum: ["educational", "case_study", "sales_cta", "engagement"] },
            topic: { type: "string", description: "Topic for the post" }
          },
          required: ["platform", "post_type"]
        }
      },
      {
        name: "get_social_summary",
        description: "Get weekly social media performance summary",
        inputSchema: {
          type: "object",
          properties: {
            vault_path: { type: "string", description: "Path to Obsidian vault" }
          }
        }
      }
    ]
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
      case "publish_facebook":
        result = await publishFacebook(args);
        break;
      case "publish_instagram":
        result = await publishInstagram(args);
        break;
      case "publish_twitter":
        result = await publishTwitter(args);
        break;
      case "schedule_post":
        result = await schedulePost(args);
        break;
      case "get_engagement_metrics":
        result = await getEngagementMetrics(args);
        break;
      case "get_recent_posts":
        result = await getRecentPosts(args);
        break;
      case "generate_content":
        result = await generateContent(args);
        break;
      case "get_social_summary":
        result = await getSocialSummary(args);
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
  const port = process.argv[2] || "8812";

  console.log("=".repeat(60));
  console.log("📱 Social Media MCP Server");
  console.log("=".repeat(60));
  console.log(`Facebook Configured: ${!!CONFIG.facebook.pageAccessToken}`);
  console.log(`Instagram Configured: ${!!CONFIG.instagram.businessAccountId}`);
  console.log(`Twitter Configured: ${!!CONFIG.twitter.bearerToken}`);
  console.log(`Port: ${port}`);
  console.log("=".repeat(60));
  console.log("");

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.log("Social MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
