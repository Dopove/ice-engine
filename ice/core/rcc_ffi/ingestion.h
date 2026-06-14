#ifndef ICE_INGESTION_H
#define ICE_INGESTION_H

#include "ice_types.h"

/**
 * @brief Ingests a document or directory into the system.
 * 
 * @param tenant_id The tenant's unique identifier.
 * @param user_id The user's unique identifier.
 * @param file_path The path to the document or directory to ingest.
 * @return The number of chunks ingested on success, negative on failure.
 */
int rcc_ingest_document(
    const char* tenant_id,
    const char* user_id,
    const char* file_path
);

#endif // ICE_INGESTION_H
