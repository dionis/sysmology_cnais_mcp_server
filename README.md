# sysmology_cnais_mcp_server
A MCP server for get generative AI information about sismology from Cuba's Cenais institute

## Installation

We use [`uv`](https://docs.astral.sh/uv/) for fast Python dependency management.

```bash
# Clone the repository
git clone <repository-url>
cd sysmology_cnais_mcp_server

# Install dependencies and create the virtual environment
uv sync
```

## Usage

You can run the MCP server directly using `uv`:

```bash
# Start the MCP server using uv
uv run python server.py
```

Or configure your MCP client (like Claude Desktop) to start it:

```json
{
  "mcpServers": {
    "sysmology_cnais": {
      "command": "uv",
      "args": [
        "--directory",
        "path/to/sysmology_cnais_mcp_server",
        "run",
        "server.py"
      ]
    }
  }
}
```

## Configuration

Edit the `config.py` wrapper or the dotfiles to configure the server:

```python
# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_user',
    'password': 'your_password',
    'database': 'your_database'
}
```

## Development

This server uses [FastMCP](https://github.com/modelcontextprotocol/python-sdk) wrapper for rapid tool development and serving.

### Adding New Tools

To add a new tool, define a standard Python function and use the `@mcp.tool()` decorator. FastMCP handles the Pydantic schemas by inspecting the function signatures and docstrings.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Sysmology CNAIS")

@mcp.tool()
def get_sismic_event(region: str) -> str:
    """Get recent sismology events for a given region.
    
    Args:
        region: The geographical region in Cuba
    """
    # Fetch from Cenais API / DB
    return f"Recent events in {region}..."

# To run the server via stdio
if __name__ == "__main__":
    mcp.run()
```

Launch the inspector:
``` bash
    npx @modelcontextprotocol/inspector uv run research_server.py

```
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

For questions or support, please open an issue or contact the maintainers.
