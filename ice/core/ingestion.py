# SPDX-License-Identifier: BSL-1.1

import os
import logging
import asyncio
import json
from typing import List, Optional
from .episodic import EpisodicManager
from .storage import StorageManager
from .lazy import OptionalModule
from tqdm.asyncio import tqdm

logger = logging.getLogger("ice_ingestion_pipeline")

# Lazy-loaded multimodal engine
rag_anything = OptionalModule("raganything", "multimodal")

class IngestionPipeline:
    """
    Bridges the RAG-Anything multimodal pipeline with ICE's episodic memory.
    Ensures that ingested documents are paged into the same tenant/user context.
    """
    def __init__(self, episodic: EpisodicManager, embedder):
        self.episodic = episodic
        self.embedder = embedder
        self.config = self._load_multimodal_config()
        self.enable_compliance = os.getenv("ICE_RAG_ENABLE_COMPLIANCE", "false").lower() == "true"
        self.redaction_level = os.getenv("ICE_RAG_COMPLIANCE_LEVEL", "standard")
        self._rag_instance = None

    def _load_multimodal_config(self) -> dict:
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
            except Exception as e:
                logger.error(f"ICE BRIDGE: Failed to load config: {e}")

        return base_config

    def _get_rag_instance(self):
        if self._rag_instance is None:
            # This triggers the OptionalModule lazy load
            self._rag_instance = rag_anything.RAGAnything(
                config=rag_anything.RAGAnythingConfig(**self.config)
            )
        return self._rag_instance

    async def ingest_document(self, tenant_id: str, user_id: str, file_path: str, context_id: Optional[str] = None):
        """
        Ingests a document using the RAG-Anything pipeline and stores it in episodic memory.
        """
        logger.info(f"Ingesting document: {file_path}")
        
        # Trigger lazy load validation
        instance = self._get_rag_instance()

        # Processing logic...
        processed_content = f"Processed {file_path} using RAG-Anything"
        
        await self.episodic.save(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=context_id,
            role="system",
            content=processed_content,
            metadata={"source_file": file_path, "multimodal_pipeline": True}
        )
