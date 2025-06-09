import asyncio
from .mcp_server import mcp_run


def main():
    asyncio.run(mcp_run())