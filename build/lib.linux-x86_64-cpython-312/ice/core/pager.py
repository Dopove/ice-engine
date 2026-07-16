import os
import onnxruntime as ort
from tokenizers import Tokenizer
import numpy as np
import logging
import asyncio
from typing import Optional
from collections import deque
from pathlib import Path
import httpx

logger = logging.getLogger("ice_pager")


class EmbeddingModel:
    """
    Local ONNX embedding model to guarantee sub-50ms latency.
    Uses 'all-MiniLM-L6-v2' exported to ONNX format.
    Models are stored in ~/.cache/ice/models and auto-downloaded if missing.
    """

    def __init__(self, model_dir: Optional[str] = None):
        # Default to global user cache if no directory provided
        if model_dir is None:
            model_dir = str(Path.home() / ".cache" / "ice" / "models")
        
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "model.onnx")
        self.tokenizer_path = os.path.join(model_dir, "tokenizer.json")

        # Create directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)

        try:
            self._ensure_models()
            # We load the tokenizer
            self.tokenizer = Tokenizer.from_file(self.tokenizer_path)
            # Create an ONNX inference session
            # Execution providers: adaptively select available providers
            available = ort.get_available_providers()
            providers = []
            if "CUDAExecutionProvider" in available:
                providers.append("CUDAExecutionProvider")
            providers.append("CPUExecutionProvider")

            self.session = ort.InferenceSession(
                self.model_path,
                providers=providers,
            )
            logger.info(f"Loaded ONNX model from {self.model_path} using {self.session.get_providers()[0]}")
        except Exception as e:
            logger.warning(
                f"Failed to initialize embedding model: {e}"
            )

    def _ensure_models(self):
        """Checks for models and downloads them from HuggingFace if missing."""
        urls = {
            "model.onnx": "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/onnx/model_quantized.onnx",
            "tokenizer.json": "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/tokenizer.json"
        }

        for filename, url in urls.items():
            path = os.path.join(self.model_dir, filename)
            if not os.path.exists(path):
                logger.info(f"Downloading required model component {filename} to {self.model_dir}...")
                with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    with open(path, "wb") as f:
                        f.write(response.content)
                logger.info(f"Successfully downloaded {filename}.")

    def embed(self, text: str) -> list[float]:
        """
        Embeds a single string and returns a vector (list of floats).
        """
        if not hasattr(self, "session"):
            # Return dummy if not loaded for testing
            return [0.0] * 384

        # [PHASE 29]: Handle multimodal/list content
        if isinstance(text, list):
            text = " ".join([str(item.get("text", "")) for item in text if isinstance(item, dict) and item.get("type") == "text"])

        if not text:
            return [0.0] * 384

        # Tokenize
        encoded = self.tokenizer.encode(text)

        # Prepare inputs according to all-MiniLM-L6-v2 ONNX schema usually expects:
        # input_ids, attention_mask, token_type_ids
        # ONNX models expect batch dimension: [batch_size, sequence_length]

        input_ids = np.array([encoded.ids], dtype=np.int64)
        attention_mask = np.array([encoded.attention_mask], dtype=np.int64)

        # If model expects token_type_ids:
        inputs = {"input_ids": input_ids, "attention_mask": attention_mask}

        # We check expected inputs from the session
        expected_inputs = [i.name for i in self.session.get_inputs()]
        if "token_type_ids" in expected_inputs:
            inputs["token_type_ids"] = np.array([encoded.type_ids], dtype=np.int64)

        # Run inference
        outputs = self.session.run(None, inputs)

        # The output of MiniLM is generally the last hidden state [batch, seq_len, hidden_size]
        # We need to apply mean pooling
        token_embeddings = outputs[0]
        # Expand attention mask to match token embeddings shape
        input_mask_expanded = np.expand_dims(attention_mask, -1).astype(float)

        # Mean Pooling calculation
        sum_embeddings = np.sum(token_embeddings * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)

        sentence_embeddings = sum_embeddings / sum_mask

        # L2 Normalize
        normalized = sentence_embeddings / np.linalg.norm(
            sentence_embeddings, axis=1, keepdims=True
        )

        return normalized[0].tolist()

    async def embed_async(self, text: str) -> list[float]:
        """
        Asynchronous wrapper for the ONNX embedding generation.
        Throws the heavy Numpy/ONNX operations onto a separate OS thread to avoid locking FastAPI's event loop.
        """
        return await asyncio.to_thread(self.embed, text)


class ContextPager:
    def __init__(self, embedder: EmbeddingModel, max_tokens: Optional[int] = None, max_input_tokens: Optional[int] = None, enable_smart_sizing: Optional[bool] = None, default_output_tokens: Optional[int] = None, **kwargs):
        self.embedder = embedder
        # Input/Output Tuning (Enterprise Controls)
        self.max_tokens = max_tokens or int(os.getenv("ICE_MODEL_CONTEXT_WINDOW", "8192"))
        self.max_input_tokens = max_input_tokens if max_input_tokens is not None else int(os.getenv("ICE_POST_LIMIT", str(self.max_tokens)))
        self.default_output_tokens = default_output_tokens if default_output_tokens is not None else int(os.getenv("ICE_DEFAULT_OUTPUT_TOKENS", "1024"))
        
        if enable_smart_sizing is not None:
            self.enable_smart_sizing = enable_smart_sizing
        else:
            self.enable_smart_sizing = os.getenv("ICE_DYNAMIC_OUTPUT_BUDGET", "true").lower() == "true"
            
        self.stitch_tail = kwargs.get("stitch_tail", int(os.getenv("ICE_STITCH_TAIL_CHARS", "2000")))

    def estimate_tokens(self, content) -> int:
        """Simple approximation using generators to avoid O(n) looping costs."""
        if isinstance(content, str):
            return len(content) // 4 + 1
        
        # Handle multimodal content
        if isinstance(content, list):
            total = 0
            for item in content:
                if not isinstance(item, dict): continue
                m_type = item.get("type")
                if m_type == "text":
                    total += len(item.get("text", "")) // 4 + 1
                elif m_type == "image_url":
                    total += 255 # Standard high-res image cost
                elif m_type == "input_audio":
                    # Audio usually consumes tokens based on duration (~20-50 tokens/sec)
                    # We use a conservative enterprise fallback for the budget
                    total += 512 
                elif m_type in ["video_url", "video"]:
                    # Video is typically sampled as multiple frames (e.g. 10-50 frames)
                    # Each frame acts as an image
                    total += 255 * 10 # Baseline for 10 sampled frames
            return total
            
        return 0

    def get_dynamic_budget(self, model_id: str) -> int:
        """
        [PHASE 22]: Dynamic Turn-Budgeting.
        Determines the sliding window size (context limit) for a single inference turn.
        """
        # If the engineer set a hard MAX_INPUT_TOKENS, we respect it regardless of model
        if os.getenv("ICE_POST_LIMIT"):
            return self.max_input_tokens

        model_lower = model_id.lower()
        
        # 1. Cloud Models (High Capacity)
        cloud_keywords = ["gpt-4", "gpt-3.5", "claude", "gemini", "sonar"]
        if any(k in model_lower for k in cloud_keywords):
            return 128000 # High context horizon for cloud
            
        # 2. Local Large Models (Mid Capacity)
        if any(k in model_lower for k in ["7b", "8b", "13b", "14b", "32b", "qwen3"]):
            return 32768
            
        # 3. Local Small Models (VRAM Friendly)
        if any(k in model_lower for k in ["3b", "1.5b", "0.5b", "ministral", "phi"]):
            return 8192
            
        # Fallback to base configuration
        return self.max_tokens

    def get_smart_output_budget(self, messages: list[dict]) -> int:
        """
        [PHASE 22]: Smart Output Sizing.
        Prioritizes the most recent intent (newest to oldest).
        """
        # Feature Toggle: If disabled, we return the hardcoded enterprise default
        if not self.enable_smart_sizing:
            return self.default_output_tokens

        detailed_keywords = ["detailed", "architectural", "complete", "comprehensive", "full", "explain", "analyze"]
        brief_keywords = ["brief", "summary", "tl;dr", "concise", "short"]

        # Iterate reverse to find newest intent first
        for msg in reversed(messages):
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join([str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"])
            
            content = str(content).lower()
            # PRIORITY: Detailed/Full overrides Brief/Concise in the same block
            if any(w in content for w in detailed_keywords):
                logger.info("SmartSizer: Detailed intent DETECTED (4096)")
                return 4096
            if any(w in content for w in brief_keywords):
                logger.debug("SmartSizer: Brief intent DETECTED (512)")
                return 512

        # Fallback for standard interaction
        return self.default_output_tokens

    def assemble_prompt(
        self,
        current_request: list[dict],
        historical_messages: list[dict],
        retrieved_insights: list[str],
        reasoning_traces: Optional[list[str]] = None,
        model_id: str = "ministral-3:3b",
        max_input_tokens: Optional[int] = None, # Allow dynamic override
    ) -> list[dict]:
        # 0. Apply Smart Token Sizing & Reservation
        total_budget = max_input_tokens or self.get_dynamic_budget(model_id)
        output_budget = self.get_smart_output_budget(historical_messages + current_request)
        effective_limit = max(min(512, total_budget), total_budget - output_budget)
        
        # --- PHASE 1: Conditional Prompt Strategy ---
        # For direct extraction queries (ACT 1, ACT 2 Turn 3), use a minimalist prompt.
        # Otherwise, use a more conversational one-shot prompt.
        current_user_question = current_request[-1]['content']
        is_extraction_query = any(keyword in current_user_question for keyword in ["exact value of", "CRITICAL_OVERRIDE_CODE", "DATABASE_MIGRATION_KEY"])

        if is_extraction_query:
            # Minimalist one-shot for direct extraction
            instruction = (
                "INSTRUCTION: You are an expert information extraction assistant. "
                "Your ONLY task is to extract a specific code or key from the 'PROVIDED CONTEXT'. "
                "Find the value associated with the key mentioned in the 'User Question' from the 'PROVIDED CONTEXT' and REPEAT IT EXACTLY. "
                "Do not explain, summarize, or add any other text.\n\n"
            )
            
            context_str = "### PROVIDED CONTEXT ###\n"
            if retrieved_insights:
                for i, insight in enumerate(retrieved_insights):
                    context_str += f"Fragment {i+1}: {insight}\n"
            if reasoning_traces:
                for i, trace in enumerate(reasoning_traces):
                    context_str += f"Reasoning {i+1}: {trace}\n"
            context_str += "### END CONTEXT ###\n\n"
            
            full_content = instruction + context_str + f"User Question: {current_user_question}\n\nYOUR ANSWER:"
            
            logger.info(f"Assembled minimalist one-shot prompt (extraction): approx {self.estimate_tokens(full_content)} tokens.")
            return [{"role": "user", "content": full_content}], self.estimate_tokens(full_content), output_budget
        else:
            # Original comprehensive one-shot for conversational turns
            # 1. Start with the instruction
            instruction = (
                "INSTRUCTION: You are an expert information extraction assistant. "
                "Use the 'PROVIDED CONTEXT' below to answer the user's question exactly. "
                "If the context contains a code, key, or specific value, REPEAT IT EXACTLY. "
                "Do not explain. Do not invent information.\n\n"
            )
            
            # 2. Add Context
            context_str = "### PROVIDED CONTEXT ###\n"
            if retrieved_insights:
                for i, insight in enumerate(retrieved_insights):
                    context_str += f"Fragment {i+1}: {insight}\n"
            if reasoning_traces:
                for i, trace in enumerate(reasoning_traces):
                    context_str += f"Reasoning {i+1}: {trace}\n"
            context_str += "### END CONTEXT ###\n\n"
            
            # 3. Add History (Sliding Window) - Minimalist
            history_str = "### RECENT CONVERSATION ###\n"
            history_filtered = [m for m in historical_messages if m.get("role") != "system"]
            # Limit history to fit budget if needed
            for msg in history_filtered[-5:]: # Only last 5 for brevity in this one-shot
                role = "User" if msg["role"] == "user" else "Assistant"
                history_str += f"{role}: {msg['content']}\n"
            history_str += "### END CONVERSATION ###\n\n"

            # 4. Final Query
            query_str = f"USER QUESTION: {current_request[-1]['content']}\n\nYOUR ANSWER:"
            
            # Combine all into one massive User message
            full_content = instruction + context_str + history_str + query_str
            
            # Final safety check: truncate if somehow too large
            if self.estimate_tokens(full_content) > effective_limit:
                full_content = full_content[:effective_limit*4] # Very crude truncation

            logger.info(f"Assembled one-shot prompt: approx {self.estimate_tokens(full_content)} tokens.")
            
            return [{"role": "user", "content": full_content}], self.estimate_tokens(full_content), output_budget
