"""Compatibility helper. The portable runtime uses typed local tools, not managed MCP."""
def build_mcp_client(*args, **kwargs):
    from runtime.tools import build_erp_tool
    return build_erp_tool()
