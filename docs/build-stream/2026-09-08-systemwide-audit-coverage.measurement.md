# Measurement Sheet (blind — frozen before comparison)

Reviewer: independent background process. Sources: blind pack only.

## M-1 test_files
```
............                                                             [100%]
12 passed in 3.78s
```

## M-2 test_websocket
```
...................                                                      [100%]
19 passed in 3.08s
```

## M-3 scope contracts x3
```
....................................                                     [100%]
36 passed in 0.38s
```

## M-4 pi replacement
```
......................                                                   [100%]
22 passed in 2.30s
```

## M-5 chat
```
.................                                                        [100%]
17 passed in 34.30s
```

## M-6 benchmark
```
pass {'fail': 0, 'na': 0, 'partial': 0, 'pass': 28, 'waived': 0} 100.0
```

## M-7 quarantine guards
126:        status=DocumentStatus.QUARANTINED,
506:                doc.status = DocumentStatus.QUARANTINED
785:    if doc is not None and doc.status == DocumentStatus.QUARANTINED:
870:    if _doc is not None and _doc.status == DocumentStatus.QUARANTINED:

## M-8 display events
664:        result_display = f"**{name}**: {result_text}\n\n"
665:        await queue.put({"type": "content", "text": result_display})
805:        result_display = f"**{name}**: {result_text}\n\n"
806:        await queue.put({"type": "content", "text": result_display})
direct appends of display (expect none):
(none found)

## M-9 new tests in isolation
### test_quarantined_files_are_not_servable
.                                                                        [100%]
1 passed in 2.51s

### test_file_serve_denies_stranger_and_anonymous
.                                                                        [100%]
1 passed in 2.30s

### test_ws_rejects_missing_and_invalid_token
.                                                                        [100%]
1 passed in 2.29s

### test_ws_denies_nonmember_project_with_4003
.                                                                        [100%]
1 passed in 2.45s

### test_relay_rejects_unauthenticated_and_accepts_network_token
.                                                                        [100%]
1 passed in 2.67s

## M-10 ruff on six files
backend/app/api/routes/chat.py:62:1: E402 Module level import not at top of file
backend/app/api/routes/chat.py:63:1: E402 Module level import not at top of file
backend/app/api/routes/chat.py:64:1: E402 Module level import not at top of file
backend/app/api/routes/chat.py:65:1: E402 Module level import not at top of file
backend/app/api/routes/chat.py:66:1: E402 Module level import not at top of file
backend/app/api/routes/chat.py:435:101: E501 Line too long (102 > 100)
backend/app/api/routes/chat.py:544:101: E501 Line too long (112 > 100)
backend/app/api/routes/chat.py:545:101: E501 Line too long (156 > 100)
backend/app/api/routes/chat.py:546:101: E501 Line too long (102 > 100)
backend/app/api/routes/chat.py:711:101: E501 Line too long (175 > 100)
backend/app/api/routes/chat.py:713:101: E501 Line too long (202 > 100)
backend/app/api/routes/chat.py:715:101: E501 Line too long (126 > 100)
backend/app/api/routes/chat.py:849:101: E501 Line too long (175 > 100)
backend/app/api/routes/chat.py:851:101: E501 Line too long (202 > 100)
backend/app/api/routes/chat.py:853:101: E501 Line too long (126 > 100)
Found 15 errors.

## M-11 diff check
CLEAN

## M-12 literal match spot-check
### [await get_active_project_or_404(db, request, scoped_project_id, min_role="researcher"]
backend/app/api/routes/deployments.py

### [source_ids: list[str] | None = None]

### [project_id: str | None = None]
backend/app/core/pi_runtime/model_manager.py
backend/app/core/prompt_rag.py
backend/app/core/context_hierarchy.py
backend/app/core/petals_bridge.py

### [Human approval marks this task Done]
frontend/src/components/kanban/TaskEditor.tsx

## M-13 refutations
### a. quarantined served to viewers (expect 403 in test):
.                                                                        [100%]
1 passed in 2.36s
### d. unauth relay connects (expect 4001 close in test):
.                                                                        [100%]
1 passed in 2.30s

FROZEN: 2026-09-08T00:28:12Z
