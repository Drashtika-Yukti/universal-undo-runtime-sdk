#include <stdio.h>
#include <assert.h>
#include "../include/universal_undo_runtime.h"

int main(void) {
    printf("[ABI_CHECK] Initializing Universal_undo_runtime core via headless C-ABI gateway...\n");
    UniversalUndoEngine* engine = uur_create_engine();
    assert(engine != NULL);

    UndoRuntimeNode tx_node = { 85501, 1, 99221, 4001, 5001 };

    printf("[ABI_CHECK] Shipping transaction frame at Sequence 100...\n");
    uur_commit_transaction_block(engine, &tx_node, 1, 100);

    printf("[ABI_CHECK] Testing point-in-time query resolution logic...\n");
    uint32_t retrieved_val = uur_query_historical_token(engine, 85501, 100);
    printf("  [ABI_CHECK] Retrieved Token Payload: %u (Expected: 99221)\n", retrieved_val);
    assert(retrieved_val == 99221);

    printf("[ABI_CHECK] Shutting down workspace engine runtime execution context...\n");
    uur_destroy_engine(engine);
    
    printf("\n>>> ABI GATEWAY ISOLATION: PASSED NATIVELY <<<\n");
    return 0;
}
