# UW MCP Server

A Model Context Protocol (MCP) server that connects Claude to the University of Waterloo's Open Data API, letting you explore courses and build conflict-free schedules through natural conversation.

## Features

- Browse UW subjects, courses, and terms
- Get class schedules for individual courses
- Find conflict-free schedule combinations across multiple courses
- Schedules ranked by quality: fewer days on campus, minimal gaps between classes, later start times

## Setup

### Prerequisites
- Python 3.10+
- Claude Desktop or Claude Code

### Steps

1. Clone the repo:
   ```bash
   git clone https://github.com/your-username/uw-mcp-server.git
   cd uw-mcp-server
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Get an API key from [UWaterloo Open Data](https://openapi.data.uwaterloo.ca).

4. Create a `.env` file in the project root:
   ```
   UW_API_KEY=your_api_key_here
   ```

5. Add the server to Claude:

   **Claude Code:**
   ```bash
   claude mcp add uw-mcp-server python /absolute/path/to/uw-mcp-server/main.py
   ```

   **Claude Desktop** — add to `~/.claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "uw-mcp-server": {
         "command": "python",
         "args": ["/absolute/path/to/uw-mcp-server/main.py"]
       }
     }
   }
   ```

## Example Queries

- "What CS courses are available this term?"
- "Build me a conflict-free schedule with CS 246 and MATH 239"
- "Find me a schedule with no Friday classes"
- "What sections of ECE 222 are available for Winter 2026?"
- "Show me all undergraduate STAT courses this term"

## Tools Reference

| Tool | Description |
|------|-------------|
| `list_subjects` | List all UW subjects, optionally filtered by a search query |
| `list_terms` | List terms, filterable by year, season, or active status |
| `list_courses` | List courses for a given term and subject, optionally filtered by level |
| `get_course_details` | Get detailed information about a specific course |
| `get_class_schedule` | Get the full class schedule for a single course |
| `find_valid_schedules` | Find conflict-free schedule combinations for 2 or more courses |

## Limitations

- Only the current and recently published terms have class schedule data available — older terms will return no results
- The UWaterloo exam schedule API is currently unreliable, so exam conflict detection is not supported
