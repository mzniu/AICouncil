# Highlights — 1.1.0 (2026-01-05)

## Key Features

1. 👹 **Devil's Advocate — Closed-loop challenge mechanism**
   - The Devil's Advocate issues structured challenges and blind-spot lists during decomposition and after each round summary, labeled by severity (Critical / Warning / Minor).
   - The `Leader` must explicitly respond in subsequent summaries; a final-round forced revision is triggered when critical issues are present.

2. 🔄 **User-driven report revision & versioning**
   - A floating "💬 Revision Feedback" panel allows users to submit modification requests directly from the report view.
   - The system backs up the original report as `report_v0.html` before the first revision; subsequent revisions are saved as `report_v1.html`, `report_v2.html`, etc. A version selector is available in the report header for easy comparison and rollback.
   - A `Report Auditor` agent analyzes feedback, drafts suggested revisions, and supports one-click apply & preview.

## Quick usage

1. Generate a report as usual.
2. Open the bottom "💬 Revision Feedback" panel and submit your requested changes.
3. Review the suggested revision and click "Apply Revision" to update the report, or switch back to `report_v0.html` if you prefer the original.

---
See `CHANGELOG.md` and `RELEASE_NOTES.md` for details.