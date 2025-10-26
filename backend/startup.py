import os
import sys
import signal
import atexit
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import time

agent_processes = []


def _stop_all_agents():
    """Best-effort termination of all agent subprocesses (and their children)."""
    global agent_processes
    if not agent_processes:
        return
    
    print("🛑 Stopping all agent processes...")
    for agent_info in agent_processes:
        agent_name = agent_info.get("name", "unknown")
        process = agent_info.get("process")
        if not process:
            continue
        
        try:
            # Try graceful SIGTERM to the process group first
            if hasattr(os, "getpgid"):
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except Exception:
                    process.terminate()
            else:
                process.terminate()

            try:
                process.wait(timeout=5)
                print(f"  ✅ Stopped {agent_name}")
            except Exception:
                # Force kill if it didn't stop
                if hasattr(os, "getpgid"):
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except Exception:
                        pass
                try:
                    process.kill()
                    print(f"  ⚠️  Force killed {agent_name}")
                except Exception:
                    pass
                try:
                    process.wait(timeout=2)
                except Exception:
                    pass
        except Exception as e:
            print(f"  ❌ Error stopping {agent_name}: {e}")
    
    agent_processes = []


def _handle_signal(signum, frame):
    print(f"\n🛑 Caught signal {signum}. Stopping services...")
    _stop_all_agents()
    # Propagate the signal to allow Flask process to stop if running
    try:
        sys.exit(0)
    except SystemExit:
        return


def main():
    # Load environment variables from .env file
    # Force override=True to reload changed variables
    load_dotenv(override=True)
    print("✅ Environment variables loaded successfully.")

    # Get the port number from environment variables or default to 8000
    port = os.getenv("FLASK_PORT", "8000")
    
    # Discover and start all agent files in app/agents/
    agents_dir = Path("app/agents")
    agent_files = sorted(agents_dir.glob("*_agent.py"))
    
    if not agent_files:
        print("⚠️  No agent files found in app/agents/")
    else:
        print(f"🤖 Starting {len(agent_files)} agent(s)...")
        
        global agent_processes
        for agent_file in agent_files:
            agent_name = agent_file.stem.replace("_", " ").title()
            
            # Start agent in its own process group so we can terminate the group
            kwargs = {}
            if hasattr(os, "setsid"):
                kwargs["preexec_fn"] = os.setsid  # macOS/Linux
            
            try:
                process = subprocess.Popen(
                    ["python3", str(agent_file)],
                    stdout=None,  # inherit stdout
                    stderr=None,  # inherit stderr
                    env={**os.environ},  # Pass fresh environment
                    **kwargs,
                )
                agent_processes.append({
                    "name": agent_name,
                    "file": str(agent_file),
                    "process": process
                })
                print(f"  ✅ Started {agent_name} (PID: {process.pid})")
            except Exception as e:
                print(f"  ❌ Failed to start {agent_name}: {e}")
        
        time.sleep(2)  # Give agents time to start
        print(f"✅ All agents started")
    

    # Start the Flask server (this will block)
    print(f"🚀 Starting Flask server on port {port}...")
    # Ensure cleanup on process exit and on signals
    atexit.register(_stop_all_agents)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        subprocess.run(["python3", "wsgi.py"])
    finally:
        # Cleanup all agent processes when Flask stops
        _stop_all_agents()

if __name__ == "__main__":
    main()
