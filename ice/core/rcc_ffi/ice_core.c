#include <string.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>

#define ASIMOV_MALLOC malloc
#define ASIMOV_FREE free

typedef struct {
    char* role;
    char* content;
} IceMessage;

typedef struct {
    float* data;
    size_t length;
} IceVector;

typedef struct {
    char** strings;
    size_t count;
} IceStringArray;

typedef struct {
    IceMessage* messages;
    size_t count;
    size_t total_tokens;
} AssembledPrompt;

void rcc_free_string_array(IceStringArray* array) {
    if (!array) return;
    if (array->strings) {
        for (size_t i = 0; i < array->count; i++) {
            if (array->strings[i]) ASIMOV_FREE(array->strings[i]);
        }
        ASIMOV_FREE(array->strings);
    }
    ASIMOV_FREE(array);
}

void rcc_free_assembled_prompt(AssembledPrompt* prompt) {
    if (!prompt) return;
    if (prompt->messages) {
        for (size_t i = 0; i < prompt->count; i++) {
            if (prompt->messages[i].role) ASIMOV_FREE(prompt->messages[i].role);
            if (prompt->messages[i].content) ASIMOV_FREE(prompt->messages[i].content);
        }
        ASIMOV_FREE(prompt->messages);
    }
    ASIMOV_FREE(prompt);
}

AssembledPrompt* rcc_assemble_prompt(
    IceMessage* historical_messages, size_t historical_count,
    IceMessage* current_request, size_t request_count,
    IceStringArray* retrieved_insights, IceStringArray* reasoning_traces,
    const char* model_id, int max_input_tokens
) {
    size_t total_capacity = historical_count + request_count; 
    if (retrieved_insights && retrieved_insights->strings) total_capacity += retrieved_insights->count;
    if (reasoning_traces && reasoning_traces->strings) total_capacity += reasoning_traces->count;
    if (total_capacity == 0) total_capacity = 1; 

    AssembledPrompt* prompt = (AssembledPrompt*)ASIMOV_MALLOC(sizeof(AssembledPrompt));
    if (!prompt) {
        return NULL;
    }
    
    prompt->messages = (IceMessage*)ASIMOV_MALLOC(total_capacity * sizeof(IceMessage));
    if (!prompt->messages) {
        ASIMOV_FREE(prompt);
        return NULL;
    }
    prompt->count = 0;
    prompt->total_tokens = 0;

    // 1. Add historical messages
    if (historical_messages) {
        for (size_t i = 0; i < historical_count; i++) {
            prompt->messages[prompt->count].role = strdup(historical_messages[i].role ? historical_messages[i].role : "unknown");
            if (!prompt->messages[prompt->count].role) {
                return NULL;
            }
            
            prompt->messages[prompt->count].content = strdup(historical_messages[i].content ? historical_messages[i].content : "");
            if (!prompt->messages[prompt->count].content) {
                return NULL;
            }
            prompt->total_tokens += (strlen(prompt->messages[prompt->count].content) / 4) + 1;
            prompt->count++;
        }
    }

    // 2. Add current request
    if (current_request) {
        for (size_t i = 0; i < request_count; i++) {
            prompt->messages[prompt->count].role = strdup(current_request[i].role ? current_request[i].role : "user");
            if (!prompt->messages[prompt->count].role) {
                return NULL;
            }

            prompt->messages[prompt->count].content = strdup(current_request[i].content ? current_request[i].content : "");
            if (!prompt->messages[prompt->count].content) {
                return NULL;
            }

            prompt->total_tokens += (strlen(prompt->messages[prompt->count].content) / 4) + 1;
          prompt->count++;
        }
    }
    
    return prompt;
}

int rcc_save_message(
    const char* tenant_id, const char* session_id, 
    const char* role, const char* content, const char* user_id
) {
    return 0;
}

IceStringArray* rcc_search_episodic(
    const char* tenant_id, IceVector* query_vector, 
    const char* session_id, const char* user_id, int limit
) {
    return NULL;
}

int rcc_ingest_document(
    const char* tenant_id, const char* user_id, const char* file_path
) {
    return 0;
}
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int value;
} DummyStruct;

DummyStruct* rcc_test_return() {
    DummyStruct* ptr = (DummyStruct*)malloc(sizeof(DummyStruct));
    if (ptr) ptr->value = 42;
    return ptr;
}
