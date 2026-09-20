#ifndef JOCKY_WORKER_H
#define JOCKY_WORKER_H
#include "jocky/runtime.h"
/* Agent-owned child only: the parent authenticates and hashes compiler artifacts
 * before launch. Requests travel over inherited pipes, never a network listener. */
int jocky_worker_run(uint32_t (*entry)(jocky_context *));
#endif
