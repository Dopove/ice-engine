#ifndef ICE_EPISODIC_H
#define ICE_EPISODIC_H

#include "ice_types.h"

/**
 * @brief Saves a message to the episodic ledger.
 * 
 * @param tenant_id The tenant's unique identifier.
 * @param session_id The unique ID for the conversation thread.
 * @param role The role of the message sender (e.g., "user", "assistant").
 * @param content The text content of the message.
 * @param user_id The user's unique identifier.
 * @return 0 on success, non-zero on failure.
 */
int rcc_save_message(
    const char* tenant_id,
    const char* session_id,
    const char* role,
    const char* content,
    const char* user_id
);

/**
 * @brief Searches the episodic ledger for relevant context.
 * 
 * @param tenant_id The tenant's unique identifier.
 * @param query_vec A pointer to the vector representation of the search query.
 * @param session_id The unique ID for the conversation thread.
 * @param user_id The user's unique identifier.
 * @param limit The maximum number of results to return.
 * @return A pointer to an IceStringArray containing the retrieved text chunks.
 *         The caller is responsible for freeing this with rcc_free_string_array.
 */
IceStringArray* rcc_search_episodic(
    const char* tenant_id,
    IceVector* query_vec,
    const char* session_id,
    const char* user_id,
    int limit
);

#endif // ICE_EPISODIC_H
