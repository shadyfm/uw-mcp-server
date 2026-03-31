from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os

from tools import register_tools

load_dotenv()

mcp = FastMCP("UW MCP Server")

API_KEY = os.getenv("UW_API_KEY")
BASE_URL = "https://openapi.data.uwaterloo.ca/v3"

register_tools(mcp, API_KEY, BASE_URL)

if __name__ == "__main__":
    mcp.run()
