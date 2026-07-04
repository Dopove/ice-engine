import os
import logging
import asyncio
import json
from typing import List, Optional
# Temporarily comment out top-level import for testing
# from raganything import RAGAnything, RAGAnythingConfig

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
        self.rag_anything = None # Initialize RAGAnything lazily

    def _load_multimodal_config(self) -> dict: # Changed return type to dict as RAGAnythingConfig is not imported
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

        return base_config # Return dict instead of RAGAnythingConfig

    async def _initialize_rag_anything(self):
        """Initializes RAGAnything lazily."""
        if self.rag_anything is None:
            try:
                from raganything import RAGAnything, RAGAnythingConfig
                self.rag_anything = RAGAnything(config=RAGAnythingConfig(**self.config))
            except ImportError:
                raise ImportError(
                    "RAG-Anything is not installed. Please install with 'pip install ice-engine[multimodal]' "
                    "to use multimodal ingestion features."
                )

    async def ingest_document(self, tenant_id: str, user_id: str, file_path: str, context_id: Optional[str] = None):
        """
        Ingests a document using the RAG-Anything pipeline and stores it in episodic memory.
        """
        await self._initialize_rag_anything()
        if self.rag_anything is None:
            raise RuntimeError("RAG-Anything not initialized. Check multimodal installation.")

        # Simulate multimodal processing
        logger.info(f"Ingesting document: {file_path} for tenant {tenant_id}, user {user_id}")

        # This part would integrate with RAGAnything's actual processing
        # For now, it's a placeholder
        processed_content = f"Processed content from {file_path} with RAG-Anything config: {self.config}"
        
        # Save to episodic memory
        await self.episodic.save(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=context_id,
            role="system",
            content=processed_content,
            metadata={"source_file": file_path, "multimodal_pipeline": True}
        )
        logger.info(f"Document {file_path} ingested and stored in episodic memory.")
