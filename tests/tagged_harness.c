/**
 * tagged_harness.c
 * ================
 * Phase 3 ABI test for uur_commit_tagged and uur_query_tag.
 * Location: tests/tagged_harness.c
 *
 * Build: cmake --build build --config Release
 * Run:   ./build/tagged_harness_test.exe
 */

#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "../include/universal_undo_runtime.h"

static int passed = 0;
static int failed = 0;

static void check(const char* label, int ok) {
    if (ok) {
        printf("  \xE2\x9C\x93  %s\n", label);
        passed++;
    } else {
        printf("  \xE2\x9C\x97  %s\n", label);
        failed++;
    }
}

int main(void) {
    printf("\n============================================================\n");
    printf("  Universal Undo Runtime  -  Phase 3 Tagged Commit Test\n");
    printf("============================================================\n\n");

    UniversalUndoEngine* engine = uur_create_engine();
    assert(engine != NULL);

    UndoRuntimeNode node = { 0xABCD0001ULL, 1, 42000, 0, 0 };

    /* [ 1 ] Commit without tag — uur_query_tag should return NULL */
    printf("[ 1 ] Untagged commit\n");
    uur_commit_transaction_block(engine, &node, 1, 10);
    const char* t = uur_query_tag(engine, 10);
    check("query_tag on untagged seq returns NULL", t == NULL);

    /* [ 2 ] Commit with a tag — tag should be retrievable */
    printf("\n[ 2 ] Tagged commit - function milestone\n");
    node.payload_token = 43000;
    uur_commit_tagged(engine, &node, 1, 20, "function:calculate_total created");
    t = uur_query_tag(engine, 20);
    check("tag is not NULL",              t != NULL);
    check("tag string matches",           t && strcmp(t, "function:calculate_total created") == 0);

    /* [ 3 ] Different sequence, different tag */
    printf("\n[ 3 ] Tagged commit - package milestone\n");
    node.payload_token = 44000;
    uur_commit_tagged(engine, &node, 1, 30, "package:numpy added");
    t = uur_query_tag(engine, 30);
    check("tag is not NULL",              t != NULL);
    check("tag string matches",           t && strcmp(t, "package:numpy added") == 0);

    /* [ 4 ] Original sequence tag is still intact */
    printf("\n[ 4 ] Previous tag still intact\n");
    t = uur_query_tag(engine, 20);
    check("seq 20 tag still readable",    t && strcmp(t, "function:calculate_total created") == 0);

    /* [ 5 ] Untagged sequence still returns NULL */
    printf("\n[ 5 ] Untagged sequence still NULL\n");
    t = uur_query_tag(engine, 10);
    check("seq 10 still NULL",            t == NULL);

    /* [ 6 ] NULL tag passed to uur_commit_tagged — behaves like normal commit */
    printf("\n[ 6 ] NULL tag == normal commit\n");
    node.payload_token = 45000;
    uur_commit_tagged(engine, &node, 1, 40, NULL);
    t = uur_query_tag(engine, 40);
    check("NULL tag produces NULL query", t == NULL);

    /* [ 7 ] Historical token still works after tagged commits */
    printf("\n[ 7 ] Historical token query unaffected\n");
    uint32_t tok = uur_query_historical_token(engine, 0xABCD0001ULL, 20);
    check("historical token still readable (> 0)", tok > 0);

    /* Done */
    uur_destroy_engine_tagged(engine);

    printf("\n============================================================\n");
    printf("  %d/%d checks passed\n", passed, passed + failed);
    if (failed == 0)
        printf("  PHASE 3 ABI: ALL TESTS PASSED  \xE2\x9C\x93\n");
    else
        printf("  %d FAILED  \xE2\x9C\x97\n", failed);
    printf("============================================================\n\n");

    return failed > 0 ? 1 : 0;
}
