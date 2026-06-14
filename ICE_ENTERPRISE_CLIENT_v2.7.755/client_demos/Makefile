# ==============================================================================
# DOPOVE ICE (v2.7.755) - STAFF-ENGINEER DX LAUNCHER
# ==============================================================================
.PHONY: help setup install-py install-node

help:
	@echo "🎓 ICE DEVELOPER EXPERIENCE (DX) LAUNCHER"
	@echo "--------------------------------------------------------"
	@echo "Usage: make <command>"
	@echo ""
	@echo "Setup:"
	@echo "  make setup                - Installs all Python and Node.js dependencies for the demos."
	@echo ""
	@echo "Python Native SDK Demos:"
	@echo "  make py-chat              - Run 01_basic_memory_chat.py"
	@echo "  make py-ingest            - Run 02_multimodal_ingest.py"
	@echo "  make py-agent             - Run 03_agentic_tool_calling.py"
	@echo "  make py-config            - Run 04_enterprise_customization.py"
	@echo "  make py-rot               - Run 05_anti_context_rot.py"
	@echo "  make py-isolation         - Run 06_session_isolation.py"
	@echo "  make py-api               - Run the full FastAPI Server (python_api/main.py)"
	@echo "  make py-cli               - Run the Terminal Agent (python_cli/cli_agent.py)"
	@echo ""
	@echo "Node.js Thin Client Demos:"
	@echo "  make node-chat            - Run 01_session_manager_chat.ts"
	@echo "  make node-agent           - Run 02_agentic_workflow.ts"
	@echo "  make node-config          - Run 03_enterprise_config.ts"
	@echo "  make node-rot             - Run 04_anti_context_rot.ts"
	@echo "  make node-isolation       - Run 05_session_isolation.ts"
	@echo "  make node-api             - Run the full Express Server (node_api/src/server.ts)"
	@echo "  make node-cli             - Run the Terminal Agent (node_cli/cliAgent.ts)"
	@echo ""
	@echo "Session Management Demos (Python):"
	@echo "  make py-session-http      - Run Stateless HTTP Header Demo"
	@echo "  make py-session-jwt       - Run Secure JWT/Cookie Demo"
	@echo "  make py-session-ws        - Run Stateful WebSocket Demo"
	@echo "--------------------------------------------------------"

setup: install-py install-node
	@echo "✅ All dependencies installed successfully!"

install-py:
	@echo "🐍 Installing Python Dependencies..."
	pip install -r requirements.txt --break-system-packages

install-node:
	@echo "🌐 Installing Node.js Dependencies..."
	npm install

# --- Python Demos ---
py-chat:
	python3 python/01_basic_memory_chat.py

py-ingest:
	python3 python/02_multimodal_ingest.py

py-agent:
	python3 python/03_agentic_tool_calling.py

py-config:
	python3 python/04_enterprise_customization.py

py-rot:
	python3 python/05_anti_context_rot.py

py-isolation:
	python3 python/06_session_isolation.py

py-adv-agent:
	python3 python/07_advanced_tool_calling.py

py-mcp:
	python3 python/08_mcp_integration.py

py-ollama-demo:
	PYTHONPATH=.. python3 python/ollama_ice_demo.py

py-api:
	python3 python_api/main.py

py-enterprise-api:
	PYTHONPATH=../:. python3 -m app.main

py-cli:
	python3 python_cli/cli_agent.py

# --- Engineering Proofs ---
py-proof-attention:
	PYTHONPATH=.. python3 proofs/01_attention_focus_proof.py

# --- Node Demos ---
node-chat:
	npm run demo:node-chat

node-agent:
	npm run demo:node-agent

node-config:
	npm run demo:node-config

node-rot:
	npm run demo:node-rot

node-isolation:
	npm run demo:node-isolation

node-adv-agent:
	npm run demo:node-adv-agent

node-mcp:
	npm run demo:node-mcp

node-api:
	npm run demo:node-api

node-cli:
	npm run demo:node-cli

# --- Session Mgmt (Python) ---
py-session-http:
	python3 session_mgmt/python/01_http_headers.py

py-session-jwt:
	python3 session_mgmt/python/02_jwt_cookies.py

py-session-ws:
	python3 session_mgmt/python/03_websocket_stream.py
