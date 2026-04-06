"""
ai.play MCP engine
Connects to MCP servers via HTTP/SSE and exposes their tools to the AI.
"""

import json
import threading
import urllib.request
import urllib.parse

class MCPTool:
    def __init__(self, name, description, input_schema):
        self.name        = name
        self.description = description
        self.schema      = input_schema

    def __repr__(self):
        return f"MCPTool({self.name!r})"


class MCPConnection:
    def __init__(self, url):
        self.url   = url.rstrip('/')
        self.tools = {}
        self._connected = False

    def connect(self):
        """Connect to MCP server and fetch available tools."""
        try:
            # Try standard MCP tools/list endpoint
            req = urllib.request.Request(
                f"{self.url}/tools/list",
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())

            for tool in data.get('tools', []):
                t = MCPTool(
                    name         = tool.get('name', ''),
                    description  = tool.get('description', ''),
                    input_schema = tool.get('inputSchema', {})
                )
                self.tools[t.name] = t

            self._connected = True
            return True

        except Exception as e:
            print(f"[ai.play] MCP connection failed ({self.url}): {e}")
            return False

    def call(self, tool_name, arguments=None):
        """Call an MCP tool and return the result."""
        if not self._connected:
            return None
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found on {self.url}"

        try:
            payload = json.dumps({
                'name': tool_name,
                'arguments': arguments or {}
            }).encode()

            req = urllib.request.Request(
                f"{self.url}/tools/call",
                data    = payload,
                headers = {'Content-Type': 'application/json'},
                method  = 'POST'
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())

            # Extract text content from MCP response
            content = data.get('content', [])
            parts = []
            for item in content:
                if item.get('type') == 'text':
                    parts.append(item.get('text', ''))
            return '\n'.join(parts) if parts else str(data)

        except Exception as e:
            return f"MCP tool error: {e}"

    def get_tools_description(self):
        """Return a string describing all available tools for training injection."""
        if not self.tools:
            return ""
        lines = ["Available MCP tools:"]
        for name, tool in self.tools.items():
            lines.append(f"  {name}: {tool.description}")
        return '\n'.join(lines)


class MCPEngine:
    def __init__(self):
        self.connections = {}   # url -> MCPConnection

    def connect(self, url):
        conn = MCPConnection(url)
        ok = conn.connect()
        if ok:
            self.connections[url] = conn
            print(f"[ai.play] MCP: connected to {url} ({len(conn.tools)} tools)")
            for name, tool in conn.tools.items():
                print(f"[ai.play]   tool: {name} — {tool.description[:60]}")
        return conn if ok else None

    def call(self, tool_name, arguments=None):
        """Call a tool from any connected server."""
        for conn in self.connections.values():
            if tool_name in conn.tools:
                return conn.call(tool_name, arguments)
        return f"Tool '{tool_name}' not found in any connected MCP server."

    def get_all_tools(self):
        """Return all tools from all connections."""
        all_tools = {}
        for conn in self.connections.values():
            all_tools.update(conn.tools)
        return all_tools

    def inject_training_pairs(self):
        """Return training pairs describing available tools."""
        pairs = []
        for conn in self.connections.values():
            for name, tool in conn.tools.items():
                pairs.append({
                    'question': f"use the {name} tool",
                    'answer':   f"I can use the {name} tool: {tool.description}"
                })
                pairs.append({
                    'question': f"what does {name} do",
                    'answer':   tool.description
                })
        return pairs
