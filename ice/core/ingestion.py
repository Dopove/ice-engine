import os
import logging
import asyncio
import json
from typing import List, Optional
from raganything import RAGAnything, RAGAnythingConfig
from .episodic import EpisodicManager
from .storage import StorageManager
from tqdm.asyncio import tqdm

logger = logging.getLogger("ice_ingestion_pipeline")

class IngestionPipeline:
    """
    Bridges the RAG-Anything multimodal pipeline with ICE's episodic memory.
    Ensures that ingested documents are paged into the same tenant/user context.
    V3.0.0 Update: Now supports recursive directory ingestion, S3 Storage Backends, 
    and Deep Multimodal Configuration.
    """
    def __init__(self, episodic: EpisodicManager, embedder): # Added embedder
        self.episodic = episodic
        self.embedder = embedder # Store embedder
        self.config = self._load_multimodal_config()
        self.enable_compliance = os.getenv("ICE_RAG_ENABLE_COMPLIANCE", "false").lower() == "true"
        self.redaction_level = os.getenv("ICE_RAG_COMPLIANCE_LEVEL", "standard")

    def _load_multimodal_config(self) -> RAGAnythingConfig:
        """
        Loads deep customization options for the multimodal pipeline.
        Clients can provide a JSON config file via ICE_RAG_CONFIG_FILE for granular control
        over OCR resolution, table extraction strategies, etc.
        """
        config_path = os.getenv("ICE_RAG_CONFIG_FILE")
        base_config = {
            "parser": os.getenv("ICE_RAG_PARSER", "docling"),
            "enable_image_processing": os.getenv("ICE_RAG_ENABLE_IMAGES", "true").lower() == "true",
            "enable_table_processing": os.getenv("ICE_RAG_ENABLE_TABLES", "true").lower() == "true",
            "enable_equation_processing": os.getenv("ICE_RAG_ENABLE_EQUATIONS", "true").lower() == "true",
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    deep_config = json.load(f)
                    base_config.update(deep_config)
                logger.info(f"RAG-ICE BRIDGE: Loaded deep multimodal config from {config_path}")
            except Exception as e:
                logger.error(f"RAG-ICE BRIDGE: Failed to load ICE_RAG_CONFIG_FILE ({config_path}): {e}")

        # Instantiate config allowing kwargs expansion if RAGAnything supports it natively
        # Fallback to manual assignment if validation strictness prevents kwargs
        config = RAGAnythingConfig(
            parser=base_config.get("parser"),
            enable_image_processing=base_config.get("enable_image_processing"),
            enable_table_processing=base_config.get("enable_table_processing"),
            enable_equation_processing=base_config.get("enable_equation_processing")
        )
        
        # Dynamically inject advanced settings into the config object if they were in the JSON
        for k, v in base_config.items():
            if not hasattr(config, k):
                setattr(config, k, v)
                
        return config

    async def _parse_local_text_file(self, file_path: str) -> List[dict]:
        """
        Parses a simple text file locally with manual chunking to avoid OOM errors.
        """
        chunk_size = int(os.getenv("ICE_CHUNK_SIZE", "8000"))
        overlap = int(os.getenv("ICE_CHUNK_OVERLAP", "500"))
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append({"text": text[start:end], "type": "text", "page_num": None})
            start += chunk_size - overlap
            if start >= len(text):
                break
        return chunks

    async def _apply_compliance_masking(self, content_list: list) -> list:
        # (Implementation remains the same)
        if not self.enable_compliance: return content_list
        # ... (rest of the function)
        return content_list

    async def ingest_document(self, tenant_id: str, user_id: str, file_path: str):
        """Legacy entrypoint. Maps to ingest_path for backwards compatibility."""
        return await self.ingest_path(tenant_id, user_id, file_path)

    async def ingest_path(self, tenant_id: str, user_id: str, path: str):
        """
        Detects if path is a file or directory (Local or S3) and processes it accordingly.
        """
        if not StorageManager.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")

        if StorageManager.is_dir(path):
            return await self.ingest_directory(tenant_id, user_id, path)
        else:
            return await self.ingest_single_file(tenant_id, user_id, path)

    async def ingest_directory(self, tenant_id: str, user_id: str, dir_path: str):
        """
        Recursively ingests all supported files within a directory (Local or S3).
        """
        logger.info(f"RAG-ICE BRIDGE: Starting directory ingestion for {dir_path}")
        
        files_to_process = StorageManager.list_files(dir_path)

        if not files_to_process:
            logger.warning(f"No files found in directory: {dir_path}")
            return 0
            
        logger.info(f"RAG-ICE BRIDGE: Found {len(files_to_process)} files. Processing...")
        
        total_chunks = 0
        for file_path in tqdm(files_to_process, desc=f"Ingesting {os.path.basename(dir_path.rstrip('/'))}"):
             total_chunks += await self.ingest_single_file(tenant_id, user_id, file_path)

        logger.info(f"RAG-ICE BRIDGE: Completed ingestion of {len(files_to_process)} files. Total chunks: {total_chunks}")
        return total_chunks

    async def ingest_single_file(self, tenant_id: str, user_id: str, file_path: str):
        """
        Parses a single document (Local or S3) using RAG-Anything and pushes chunks into ICE episodic ledger.
        """
        SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md", ".json", ".csv", ".py", ".c", ".cpp", ".java", ".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".h", ".ts", ".js", ".go", ".rs"}
        ext = os.path.splitext(file_path)[1].lower()
        if ext and ext not in SUPPORTED_EXTENSIONS:
            logger.warning(f"RAG-ICE BRIDGE: Skipping unsupported file format '{ext}' in {file_path}.")
            return 0 

        # Use a temporary directory for file operations, automatically cleaned up
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. Fetch file to local sandbox if it's remote (S3)
                local_file_path = StorageManager.fetch_to_local(file_path, temp_dir)
                # 2. Parse Data
                if self.config.parser == "local" and ext in [".txt", ".md", ".json", ".csv", ".py", ".c", ".cpp", ".java", ".h", ".ts", ".js", ".go", ".rs"]:
                    raw_chunks = await self._parse_local_text_file(local_file_path)
                else:
                    rag = RAGAnything(
                        llm_model_func=lambda x: "dummy", 
                        embedding_func=lambda x: [0.0]*384,
                        config=self.config
                    )
                    if hasattr(rag, 'config'):
                        rag.config.working_dir = temp_dir
                    
                    # We need to correctly parse the document and get chunks
                    raw_chunks = await rag.parse_document(local_file_path)
                    
                # Apply compliance masking if enabled
                content_list = await self._apply_compliance_masking(raw_chunks)
                
                for i, chunk in enumerate(content_list):
                    content = chunk.get("text", "") or str(chunk)
                    # Generate embedding for the chunk
                    embedding = await self.embedder.embed_async(content) # Use the embedder's async method
                    metadata = {"source": file_path, "type": chunk.get("type", "text"), "rag_ingest": True, "page": chunk.get("page_num")}
                    
                    await self.episodic.save_message(
                        tenant_id=tenant_id,
                        session_id="rag-ingest-global", 
                        role="system",
                        content=f"[DOC_CHUNK]: {content}",
                        user_id=user_id,
                        metadata=metadata,
                        embedding=embedding, # Pass the embedding
                    )
                
                logger.info(f"RAG-ICE BRIDGE: Ingested {len(content_list)} chunks from {file_path}")
                return len(content_list)
                
            except Exception as e:
                logger.error(f"RAG-ICE BRIDGE: Failed to ingest {file_path}: {str(e)}")
                return 0
            # TemporaryDirectory handles cleanup automatically
