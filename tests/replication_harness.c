/**
 * replication_harness.c
 * =====================
 * Phase 5 foundation test: uur_pop_replication_frame
 * Location: tests/replication_harness.c
 *
 * Build: cmake --build build --config Release
 * Run:   ./build/replication_harness_test.exe
 *
 * What this proves:
 *   Every commit into the engine ALSO enqueues a RawUndoOp into the
 *   replication queue.  uur_pop_replication_frame drains that queue
 *   one frame at a time.  A network layer, file writer, or message
 *   queue can consume these frames and replay them on another machine.
 */

#include <stdio.h>
#include <assert.h>
#include <string.h>
#include "../include/universal_undo_runtime.h"

static int passed = 0;
static int failed = 0;

static void check(const char* label, int ok) {
    if (ok) { printf("  \xE2\x9C\x93  %s\n", label); passed++; }
    else     { printf("  \xE2\x9C\x97  %s  [FAIL]\n", label); failed++; }
}

int main(void) {
    printf("\n============================================================\n");
    printf("  Universal Undo Runtime  -  Phase 5 Replication Frame Test\n");
    printf("============================================================\n\n");

    UniversalUndoEngine* engine = uur_create_engine();
    assert(engine != NULL);

    /* [ 1 ] Queue is empty on fresh engine */
    printf("[ 1 ] Fresh engine has empty replication queue\n");
    UndoReplicationFrame frame;
    memset(&frame, 0, sizeof(frame));
    bool got = uur_pop_replication_frame(engine, &frame);
    check("pop on empty queue returns false", got == false);

    /* [ 2 ] Commit produces replication frames */
    printf("\n[ 2 ] Commit enqueues replication frames\n");
    UndoRuntimeNode node = { 0xABC00001ULL, 1, 77777, 0, 0 };
    uur_commit_transaction_block(engine, &node, 1, 200);

    got = uur_pop_replication_frame(engine, &frame);
    check("frame available after commit",          got == true);
    check("frame entity_id matches",               frame.entity_id == 0xABC00001ULL);
    check("frame sequence_id matches",             frame.sequence_id == 200);
    check("frame payload_token matches",           frame.payload_token == 77777);
    check("frame domain_type matches",             frame.domain_type == 1);
    check("frame op_type is upsert (0)",           frame.op_type == 0);

    /* [ 3 ] Queue drains correctly — no phantom frames */
    printf("\n[ 3 ] Queue empty after draining\n");
    got = uur_pop_replication_frame(engine, &frame);
    check("queue empty after one pop", got == false);

    /* [ 4 ] Multiple commits produce multiple frames in order */
    printf("\n[ 4 ] Multiple commits — frames arrive in commit order\n");
    UndoRuntimeNode n1 = { 0xABC00002ULL, 1, 11111, 0, 0 };
    UndoRuntimeNode n2 = { 0xABC00003ULL, 1, 22222, 0, 0 };
    UndoRuntimeNode n3 = { 0xABC00004ULL, 1, 33333, 0, 0 };
    uur_commit_transaction_block(engine, &n1, 1, 301);
    uur_commit_transaction_block(engine, &n2, 1, 302);
    uur_commit_transaction_block(engine, &n3, 1, 303);

    UndoReplicationFrame f1, f2, f3;
    bool g1 = uur_pop_replication_frame(engine, &f1);
    bool g2 = uur_pop_replication_frame(engine, &f2);
    bool g3 = uur_pop_replication_frame(engine, &f3);

    check("frame 1 available",             g1 == true);
    check("frame 2 available",             g2 == true);
    check("frame 3 available",             g3 == true);
    check("frame 1 payload = 11111",       f1.payload_token == 11111);
    check("frame 2 payload = 22222",       f2.payload_token == 22222);
    check("frame 3 payload = 33333",       f3.payload_token == 33333);

    /* [ 5 ] Tagged commits also produce replication frames */
    printf("\n[ 5 ] Tagged commit (Phase 3) also enqueues replication frames\n");
    UndoRuntimeNode tn = { 0xABC00005ULL, 1, 55555, 0, 0 };
    uur_commit_tagged(engine, &tn, 1, 400, "milestone:phase5 test");

    /* tagged_commit calls uur_commit_transaction_block internally,
       which enqueues frames; the tag sentinel also enqueues one.
       At minimum one frame must be present. */
    int frame_count = 0;
    while (uur_pop_replication_frame(engine, &frame)) frame_count++;
    check("tagged commit produces >= 1 replication frame", frame_count >= 1);

    /* [ 6 ] NULL safety */
    printf("\n[ 6 ] NULL safety\n");
    bool null_result = uur_pop_replication_frame(NULL, &frame);
    check("NULL engine returns false",   null_result == false);
    null_result = uur_pop_replication_frame(engine, NULL);
    check("NULL out_frame returns false", null_result == false);

    uur_destroy_engine_tagged(engine);

    /* Summary */
    printf("\n============================================================\n");
    printf("  %d/%d checks passed\n", passed, passed + failed);
    if (failed == 0)
        printf("  PHASE 5 FOUNDATION: ALL TESTS PASSED  \xE2\x9C\x93\n");
    else
        printf("  %d FAILED  \xE2\x9C\x97\n", failed);
    printf("============================================================\n\n");

    return failed > 0 ? 1 : 0;
}
