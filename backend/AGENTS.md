# Agent Management

## Overview
The `startup.py` script automatically discovers and manages all agent files in the `app/agents/` directory.

## How It Works

### Agent Discovery
- All files matching the pattern `*_agent.py` in `app/agents/` are automatically detected
- Agents are started in alphabetical order
- Each agent runs in its own process with its own process group

### Environment Variables
- `load_dotenv(override=True)` ensures fresh environment variables are loaded each time
- All agents inherit the environment variables from the parent process
- Update `.env` and restart `startup.py` to apply changes

### Agent Lifecycle

#### Starting Agents
```bash
python3 startup.py
```

This will:
1. Load environment variables from `.env`
2. Discover all `*_agent.py` files
3. Start each agent as a subprocess
4. Start the Flask server

#### Stopping Agents
When you stop the server (Ctrl+C or SIGTERM), all agents are automatically stopped:
1. Graceful SIGTERM sent to each agent's process group (5s timeout)
2. Force SIGKILL if agent doesn't respond
3. Clean exit confirmation for each agent

## Adding New Agents

### Naming Convention
Name your agent files with the `_agent.py` suffix:
- `code_agent.py` ✅
- `document_agent.py` ✅
- `analysis_agent.py` ✅
- `helper.py` ❌ (won't be auto-started)

### Agent Template
```python
from uagents import Agent, Context
import os

# Create agent
my_agent = Agent(
    name="my_agent",
    seed="my_agent_seed_phrase",
    port=8002,  # Use unique port
    endpoint=[f"http://127.0.0.1:8002/submit"]
)

@my_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"My Agent started on port 8002")

if __name__ == "__main__":
    my_agent.run()
```

### Port Management
- Assign unique ports to each agent (8001, 8002, 8003, etc.)
- Store port numbers in `.env` for configurability:
  ```
  CODE_AGENT_PORT=8001
  DOCUMENT_AGENT_PORT=8002
  ```

## Current Agents
- `code_agent.py` - Code generation agent (port 8001)

## Troubleshooting

### Agent Won't Stop
If an agent process becomes unresponsive:
```bash
# Find the PID
lsof -nP -iTCP:8001 -sTCP:LISTEN

# Force kill
kill -9 <PID>
```

### Environment Variables Not Updating
- Ensure you restart `startup.py` completely
- Check that `.env` file is in the `backend/` directory
- Verify no cached processes are running on agent ports

### Agent Fails to Start
- Check agent logs in terminal output
- Verify the agent file has `if __name__ == "__main__": agent.run()`
- Ensure all dependencies are installed
- Check for port conflicts

## Best Practices

1. **Single Responsibility**: Each agent should handle one specific domain
2. **Error Handling**: Implement try-catch in agent endpoints
3. **Logging**: Use `ctx.logger` for consistent logging
4. **Graceful Shutdown**: Agents should handle cleanup on exit
5. **Testing**: Test agents individually before integrating
