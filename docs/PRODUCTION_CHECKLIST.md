# Production checklist

- [ ] Use PostgreSQL and Alembic migrations; do not rely on `create_all` for schema evolution.
- [ ] Store uploads in private object storage and serve short-lived signed URLs.
- [ ] Add malware scanning/content disarm for uploads.
- [ ] Add refresh-token rotation/revocation, email verification, password reset, and recovery.
- [ ] Add rate limiting, audit events, secure headers, and abuse monitoring.
- [ ] Enforce HTTPS and restrict CORS to the real frontend origin.
- [ ] Configure encrypted backups and test restoration.
- [ ] Move long-running PDF/OCR work to a worker queue with retries/progress.
- [ ] Benchmark OCR on representative handwriting; track CER/WER and page failures.
- [ ] Add image crop/deskew controls and source-region traceability.
- [ ] QA PDF/DOCX exports for Unicode, formulas, tables, and page breaks.
- [ ] Run accessibility, end-to-end, dependency, container, and application security scans.
- [ ] Review privacy notice, retention, account deletion, and vendor data handling.
