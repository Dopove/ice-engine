#ifndef ICE_PAGER_H
#define ICE_PAGER_H

#include "ice_types.h"

// Represents the final assembled prompt to be sent to the LLM
typedef struct {
    IceMessage* messages;
    size_t count;
    size_t total_tokens;
} AssembledPrompt;

/**
 * @brief Assembles a context-aware prompt from various memory sources.
 *
 * This is the core function of the ContextPager. It takes historical messages,
 * retrieved RAG insights, and active reasoning traces, then assembles them
 * into a final prompt that respects the model's token limit.
 *
 * @param current_req An array of IceMessage structs for the current user request.
 * @param req_count The number of messages in current_req.
 * @param history An array of historical IceMessage structs.
 * @param hist_count The number of messages in history.
 * @param insights An array of strings representing retrieved RAG insights.
 * @param traces An array of strings representing active reasoning traces.
 * @param model_id The ID of the target LLM (e.g., "gpt-4o").
 * @param max_tokens The maximum token limit for the final assembled prompt.
 * @return A pointer to an AssembledPrompt struct. The caller is responsible for
 *         calling rcc_free_assembled_prompt to release memory.
 */
AssembledPrompt* rcc_assemble_prompt(
    IceMessage* current_req,
    size_t req_count,
    IceMessage* history,
    size_t hist_count,
    IceStringArray* insights,
    IceStringArray* traces,
    const char* model_id,
    int max_tokens
);

/**
 * @brief Frees the memory allocated for an AssembledPrompt struct.
 *
 * @param prompt A pointer to the AssembledPrompt struct to be freed.
 */
void rcc_free_assembled_prompt(AssembledPrompt* prompt);

#endif // ICE_PAGER_H
