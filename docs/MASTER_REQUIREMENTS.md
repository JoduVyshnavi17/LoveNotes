# NoteMind AI — Master Requirements

## Product boundary
NoteMind AI reconstructs handwritten notes from photos and scanned PDFs, then optionally proposes missing points. It is not an LMS, quiz platform, student management system, or general learning platform.

## Core workflow
1. Register/login securely.
2. Upload one or more JPG/JPEG/PNG/WEBP images or a scanned PDF.
3. Validate file extension, MIME type, signature, and size.
4. Review pages and their order.
5. Preprocess images (orientation, contrast, denoise; deskew best effort).
6. OCR/transcribe each page; preserve raw OCR separately.
7. Show faithful reconstruction with `[unclear]` markers rather than guessing.
8. Optionally create an AI-organized version without introducing unsupported facts.
9. Optionally detect possible gaps at Basic, Detailed, or Comprehensive depth.
10. Keep AI additions separate, visibly labelled, and individually accept/reject/editable.
11. Edit and save notes, retain revisions, and export PDF/DOCX/TXT.

## Modes
- Faithful Reconstruction: source wording and structure take priority.
- AI Enhanced Reconstruction: improve organization and readability without adding facts.
- Complete My Notes: generate cautious suggestions in a separate review queue.

## Suggestion categories
- `explicit_omission`: the source itself signals an omission or unfinished item.
- `potential_gap`: a plausible missing piece, explicitly qualified as uncertain.
- `optional_enrichment`: useful context, not required content.

Every suggestion should include title, content, rationale, evidence excerpt, confidence estimate, and status. Confidence is not a guarantee. Never fabricate references, citations, formulas, or facts.

## Data and security
- Each user can access only their own documents, pages, suggestions, revisions, and exports.
- Store uploads using generated server-side names, never paths supplied by the client.
- Keep API keys on the backend only.
- Use Argon2 password hashing, short-lived signed access tokens, strict CORS, upload limits, and HTTPS in production.
- Allow document archive, restore, and permanent deletion.
