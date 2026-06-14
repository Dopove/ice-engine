#ifndef ICE_TYPES_H
#define ICE_TYPES_H

#include <stddef.h>

// Represents a chat message
typedef struct {
    char* role;
    char* content;
} IceMessage;

// Represents a numerical vector (e.g., an embedding)
typedef struct {
    float* data;
    size_t length;
} IceVector;

// Represents an array of strings
typedef struct {
    char** strings;
    size_t count;
} IceStringArray;

// Common function to free string arrays
void rcc_free_string_array(IceStringArray* array);

#endif // ICE_TYPES_H
