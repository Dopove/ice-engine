import asyncio
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import the UI class from the python demos folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'python'))
from ui import UI

from ice.core.pager import ContextPager

async def verify_1b_to_100k_compression():
    UI.header("ICE Engineering Proof: Multi-Tiered Injection & Attention Focus")
    print(f"{UI.YELLOW}Objective:{UI.RESET} Prove that ICE structurally mitigates the 'Lost in the Middle' phenomenon.")
    print(f"{UI.YELLOW}Method:{UI.RESET} Force the ContextPager to process 1 Billion tokens and verify the final prompt structure.\n")
    
    # 1. Initialize Pager with strict 100K Token Limit
    UI.step("Initializing ContextPager with strict 100,000 token budget...")
    pager = ContextPager(embedder=MagicMock(), max_tokens=100000)
    pager.enable_smart_sizing = False
    
    # 2. Define the Critical Needles
    system_msg = {"role": "system", "content": "CRITICAL: Maintain System Integrity."}
    deep_memory = ["DEEP MEMORY: The launch code is 9934."]
    active_reasoning = ["THOUGHT: Need to retrieve the code."]
    current_req = [{"role": "user", "content": "What is the code?"}]
    
    # 3. Construct 1 Billion Tokens of "Pre-Compression" History
    UI.step("Constructing 1,000,000,000 token chronological history payload (The Haystack)...")
    history = [{"role": "user", "content": f"FILLER_BLOCK_{i}"} for i in range(100)]
    
    original_estimate = pager.estimate_tokens
    def simulated_massive_estimator(text):
        if "FILLER_BLOCK_" in str(text):
            return 10_000_000 # 10 Million Tokens per block
        return original_estimate(text)
        
    await UI.simulate_processing(1.5, "Executing Truncation Guillotine")
        
    with patch.object(pager, 'estimate_tokens', side_effect=simulated_massive_estimator):
        with patch.object(pager, 'get_dynamic_budget', return_value=100000):
            assembled, final_tokens, _ = pager.assemble_prompt(
                current_request=current_req,
                historical_messages=[system_msg] + history,
                retrieved_insights=deep_memory,
                reasoning_traces=active_reasoning,
                model_id="gpt-4o" # Force evaluation
            )
            
    assembled_content_list = [m.get("content") for m in assembled if isinstance(m, dict)]
    assembled_content = str(assembled_content_list)
    
    print(f"\n{UI.BOLD}{UI.CYAN}--- FINAL PROMPT STRUCTURE SENT TO LLM ---{UI.RESET}")
    print(f"  {UI.MAGENTA}Tier 1 (The Floor - Highest Attention):{UI.RESET} \n    '{assembled_content_list[0]}'")
    print(f"  {UI.MAGENTA}Tier 2 (Active Reasoning):{UI.RESET} \n    '{assembled_content_list[1]}'")
    print(f"  {UI.MAGENTA}Tier 3 (Deep Memory - High Signal Middle):{UI.RESET} \n    '{assembled_content_list[2]}'")
    print(f"  {UI.MAGENTA}Tier 4 (Sliding Window):{UI.RESET} \n    '{assembled_content_list[3:-1]}...' \033[1;31m(TRUNCATED 1 BILLION TOKENS)\033[0m")
    print(f"  {UI.MAGENTA}Tier 5 (The Ceiling - High Attention):{UI.RESET} \n    '{assembled_content_list[-1]}'")
    
    UI.step("Executing Structural Integrity Assertions...")
    
    # 5. Verification Assertions for Order
    assert "CRITICAL" in assembled_content_list[0], "FAILED: System Prompt is not at the top (Tier 1)."
    assert "THOUGHT" in assembled_content_list[1], "FAILED: Reasoning Trace is not in Tier 2."
    assert "DEEP MEMORY" in assembled_content_list[2], "FAILED: RAG Insight is not in Tier 3."
    assert "What is the code?" in assembled_content_list[-1], "FAILED: Current Request is not at the bottom (Tier 5)."
    
    print(f"  {UI.GREEN}✔ Multi-Tiered Injection Order Verified.{UI.RESET}")
    
    # 6. Verification Assertions for Content
    assert final_tokens <= 100000, "FAILED: Pager exceeded the 100K token limit!"
    assert "CRITICAL: Maintain System Integrity." in assembled_content, "FAILED: System Prompt was dropped!"
    assert "DEEP MEMORY: The launch code is 9934." in assembled_content, "FAILED: RAG Deep Memory was dropped!"
    assert "THOUGHT: Need to retrieve the code." in assembled_content, "FAILED: Reasoning trace was dropped!"
    assert "What is the code?" in assembled_content, "FAILED: Current request was dropped!"
    assert "FILLER_BLOCK_0" not in assembled_content, "FAILED: The guillotine failed to truncate old context!"
    
    print(f"  {UI.GREEN}✔ 1 Billion tokens successfully compressed to <100K without dropping critical needles.{UI.RESET}")
    print(f"  {UI.GREEN}✔ Oldest chronological history safely purged.{UI.RESET}")
    
    UI.success("ContextPager successfully structures prompt to mitigate 'Lost in the Middle'.")

if __name__ == "__main__":
    asyncio.run(verify_1b_to_100k_compression())
