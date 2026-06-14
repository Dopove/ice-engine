import asyncio
import os
import subprocess
from ice.sdk import init
import sys
sys.path.append(os.path.dirname(__file__))
from ui import UI

# --- Configuration ---
LINUX_KERNEL_DIR = "linux"
REPO_URL = "https://github.com/torvalds/linux.git"
NEEDLE_FILE = "init/main.c"
NEEDLE_QUESTION = f"In the Linux Kernel source code, what is the purpose of the `NR_CPUS` configuration parameter as described in the comments of the `{NEEDLE_FILE}` file?"

async def run_ollama_demo():
    UI.header("ICE + Ollama: The Linux Kernel Needle Demo")
    print(f"{UI.YELLOW}Goal:{UI.RESET} Prove a small, local SLM can answer a hyper-specific question from a massive codebase (the Linux Kernel) using ICE's virtual memory.")
    print(f"{UI.CYAN}Requirement:{UI.RESET} A running Ollama instance with a model like `llama3.2:3b` and the ICE Docker stack (`docker compose up -d`).
")

    # --- Phase 1: Ingestion ---
    UI.step("Phase 1: Ingestion of the Linux Kernel Source Code")
    if not os.path.exists(LINUX_KERNEL_DIR):
        UI.system(f"Linux Kernel source not found. Cloning from {REPO_URL}...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", REPO_URL, LINUX_KERNEL_DIR], check=True)
            UI.system("✅ Git clone complete.")
        except subprocess.CalledProcessError as e:
            UI.error(f"Failed to clone Linux kernel: {e}")
            return
    else:
        UI.system(f"Found existing Linux Kernel source in ./{LINUX_KERNEL_DIR}/")

    UI.system("Booting live ICE Kernel...")
    ice_client = await init() # Use default settings for local infra

    # Check if ingestion has already been done for this session to avoid re-doing it
    # A real app might use a database flag, here we'll use a simple file marker.
    ingestion_marker = ".ice_ingestion_complete"
    if not os.path.exists(ingestion_marker):
        UI.system("Beginning one-time ingestion of the entire Linux Kernel into ICE's memory.")
        print("(This will take a significant amount of time depending on your hardware, but only needs to be done once.)")
        try:
            await ice_client.ingest(
                file_path=LINUX_KERNEL_DIR, # Ingest the entire directory
                session_id="linux_kernel_source",
                x_user_id="kernel_researcher"
            )
            with open(ingestion_marker, "w") as f:
                f.write("done")
            UI.success("Linux Kernel ingestion complete. The knowledge is now permanent.")
        except Exception as e:
            UI.error(f"An error occurred during ingestion: {e}")
            return
    else:
        UI.system("Kernel has already been ingested. Proceeding to query.")


    # --- Phase 2: The Needle-in-a-Haystack Query ---
    UI.step("
Phase 2: The Needle-in-a-Haystack Query")
    UI.system("Using a local Ollama model to answer a hyper-specific question...")
    UI.user(NEEDLE_QUESTION)
    
    await UI.simulate_processing(3, "ICE performing vector search across millions of code fragments")
    
    try:
        response = await ice_client.chat.completions.create(
            model="llama3.2:3b", # IMPORTANT: Assumes user has this model in Ollama
            messages=[{"role": "user", "content": NEEDLE_QUESTION}],
            x_session_id="linux_kernel_source",
            x_user_id="kernel_researcher"
        )
        
        content = response['choices'][0]['message']['content']
        UI.agent(f"Answer from local SLM: {content}")
        
        # Verification
        if "number of CPUs" in content.lower() and "nr_cpus" in content.lower():
            UI.success("Verification PASSED: The small local model correctly answered the question using the context provided by ICE.")
        else:
            UI.error("Verification FAILED: The model's answer did not seem to contain the correct information.")

    except Exception as e:
        UI.error(f"An error occurred during the query: {e}")
        UI.system("Is your Ollama server running and do you have the 'llama3.2:3b' model pulled? (`ollama run llama3.2:3b`)")


if __name__ == "__main__":
    # Check for git
    if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
        UI.error("`git` command not found. Please install Git to run this demo.")
    else:
        asyncio.run(run_ollama_demo())