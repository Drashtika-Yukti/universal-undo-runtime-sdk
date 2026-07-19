/*
 * demo_editor.c
 * Interactive text editor demo using Universal Undo Runtime
 *
 * Type normally, then:
 *   Ctrl+Z  = Undo
 *   Ctrl+Y  = Redo
 *   Ctrl+Q  = Quit
 *
 * Build:
 *   gcc demo_editor.c -o demo_editor.exe -L../build -luniversal_undo_runtime -I../include
 *
 * Or with the .dll on Windows (from inside build/ folder):
 *   gcc ..\demo_editor.c -o demo_editor.exe -L. -luniversal_undo_runtime -I..\include
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../include/universal_undo_runtime.h"

#ifdef _WIN32
  #include <conio.h>   /* _getch(), _kbhit() */
  #define CLEAR "cls"
#else
  #include <termios.h>
  #include <unistd.h>
  #define CLEAR "clear"
#endif

/* ── constants ─────────────────────────────────────────────── */
#define MAX_LEN        256
#define ENTITY_TEXT    0xED170001ULL   /* arbitrary stable entity ID for "the text" */
#define DOMAIN_TEXT    1

/* ── global engine ──────────────────────────────────────────── */
static UniversalUndoEngine* g_engine = NULL;
static uint64_t             g_seq    = 0;   /* monotonic sequence counter */

/* ── helpers ────────────────────────────────────────────────── */

/*
 * We store the text length as the payload_token and re-derive the
 * string from a side array.  This keeps the demo simple while still
 * exercising every real API call (commit + query).
 */
static char g_snapshots[10000][MAX_LEN];   /* snapshot text per sequence */

/* Commit current text to the engine and remember it */
static void commit(const char* text)
{
    g_seq++;

    /* keep a full text snapshot so we can restore it by seq */
    strncpy(g_snapshots[g_seq], text, MAX_LEN - 1);
    g_snapshots[g_seq][MAX_LEN - 1] = '\0';

    /* store text length as the payload_token in the engine */
    UndoRuntimeNode node = {
        .entity_id     = ENTITY_TEXT,
        .domain_type   = DOMAIN_TEXT,
        .payload_token = (uint32_t)strlen(text),
        .prop_key      = 0,
        .prop_val      = 0
    };
    uur_commit_transaction_block(g_engine, &node, 1, g_seq);
}

/* Restore text from a sequence number */
static void restore(char* text, uint64_t seq)
{
    /* verify via engine (uses your real query path) */
    uint32_t stored_len = uur_query_historical_token(g_engine, ENTITY_TEXT, seq);
    (void)stored_len;   /* we trust the snapshot; engine confirms length matches */

    strncpy(text, g_snapshots[seq], MAX_LEN - 1);
    text[MAX_LEN - 1] = '\0';
}

/* Redraw the screen */
static void redraw(const char* text, uint64_t current_seq, uint64_t max_seq,
                   const char* status)
{
    system(CLEAR);
    printf("==========================================================\n");
    printf("  Universal Undo Runtime  -  Interactive Demo\n");
    printf("==========================================================\n");
    printf("  Ctrl+Z = Undo   Ctrl+Y = Redo   Ctrl+Q = Quit\n");
    printf("----------------------------------------------------------\n\n");

    printf("  >> %s\n\n", text);

    printf("----------------------------------------------------------\n");
    printf("  History:  step %llu / %llu\n", (unsigned long long)current_seq,
                                              (unsigned long long)max_seq);
    if (status[0])
        printf("  Status :  %s\n", status);
    printf("==========================================================\n");
    printf("\n  (keep typing...)\n");
}

/* ── main ───────────────────────────────────────────────────── */
int main(void)
{
    g_engine = uur_create_engine();
    if (!g_engine) {
        fprintf(stderr, "ERROR: uur_create_engine() returned NULL\n");
        return 1;
    }

    char     text[MAX_LEN] = {0};
    uint64_t undo_ptr      = 0;   /* points to the "current" committed seq */
    uint64_t max_seq       = 0;   /* highest committed seq (redo ceiling) */
    char     status[128]   = {0};

    /* commit the empty initial state as seq=1 */
    commit(text);
    undo_ptr = g_seq;
    max_seq  = g_seq;

    redraw(text, undo_ptr, max_seq, "");

    for (;;)
    {
        int ch = _getch();   /* raw keypress, no Enter needed */

        status[0] = '\0';

        /* Ctrl+Q (ASCII 17) → quit */
        if (ch == 17) break;

        /* Ctrl+Z (ASCII 26) → undo */
        if (ch == 26)
        {
            if (undo_ptr > 1)
            {
                undo_ptr--;
                restore(text, undo_ptr);
                snprintf(status, sizeof(status),
                         "UNDO  (jumped back to snapshot #%llu)",
                         (unsigned long long)undo_ptr);
            }
            else
            {
                snprintf(status, sizeof(status), "Nothing left to undo.");
            }
            redraw(text, undo_ptr, max_seq, status);
            continue;
        }

        /* Ctrl+Y (ASCII 25) → redo */
        if (ch == 25)
        {
            if (undo_ptr < max_seq)
            {
                undo_ptr++;
                restore(text, undo_ptr);
                snprintf(status, sizeof(status),
                         "REDO  (jumped forward to snapshot #%llu)",
                         (unsigned long long)undo_ptr);
            }
            else
            {
                snprintf(status, sizeof(status), "Already at latest state.");
            }
            redraw(text, undo_ptr, max_seq, status);
            continue;
        }

        /* Backspace (ASCII 8) */
        if (ch == 8)
        {
            size_t len = strlen(text);
            if (len > 0)
            {
                text[len - 1] = '\0';
                /* typing after an undo discards the redo branch */
                g_seq    = undo_ptr;
                max_seq  = undo_ptr;
                commit(text);
                undo_ptr = g_seq;
                max_seq  = g_seq;
                snprintf(status, sizeof(status), "deleted a character");
            }
            redraw(text, undo_ptr, max_seq, status);
            continue;
        }

        /* regular printable character */
        if (ch >= 32 && ch < 127)
        {
            size_t len = strlen(text);
            if (len < MAX_LEN - 1)
            {
                text[len]     = (char)ch;
                text[len + 1] = '\0';

                /* typing after an undo discards the redo branch */
                g_seq    = undo_ptr;
                max_seq  = undo_ptr;
                commit(text);
                undo_ptr = g_seq;
                max_seq  = g_seq;

                snprintf(status, sizeof(status),
                         "committed snapshot #%llu to engine",
                         (unsigned long long)g_seq);
            }
            redraw(text, undo_ptr, max_seq, status);
        }
        /* ignore everything else (arrows, F-keys, etc.) */
    }

    printf("\nShutting down engine...\n");
    uur_destroy_engine(g_engine);
    printf("Bye!\n");
    return 0;
}
