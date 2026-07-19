#pragma once
#include <stdint.h>
#include <stdbool.h>

/**
 * @file universal_undo_runtime.h
 * @brief Public language-agnostic C-ABI for the Universal Undo Runtime engine layer.
 */

typedef struct UniversalUndoEngine UniversalUndoEngine;

typedef struct {
    uint64_t entity_id;
    uint8_t domain_type;
    uint32_t payload_token;
    uint32_t prop_key;
    uint32_t prop_val;
} UndoRuntimeNode;

#ifdef __cplusplus
extern "C" {
#endif

UniversalUndoEngine* uur_create_engine(void);
void uur_destroy_engine(UniversalUndoEngine* engine);
void uur_commit_transaction_block(UniversalUndoEngine* engine, const UndoRuntimeNode* nodes, size_t node_count, uint64_t sequence_id);
uint32_t uur_query_historical_token(UniversalUndoEngine* engine, uint64_t entity_id, uint64_t sequence_id);

#ifdef __cplusplus
}
#endif
