
from pathlib import Path
from uuid import uuid4
import io

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from PIL import Image
import fitz

from .config import settings
from .database import Base, engine, get_db
from .models import User, Document, Page, Suggestion, Revision
from .schemas import RegisterIn, LoginIn, TokenOut, UserOut
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from .services.ocr import transcribe
from .services.notes_ai import (
    enhance,
    complete_notes,
    suggestions,
    study_aids
)
from .services.exporter import export


Path(settings.upload_dir).resolve().mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LoveNotes",
    version="2.2.0",
    description="Handwritten notes reconstruction and AI-assisted study tools"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"]
)


@app.get("/")
def root():
    return {
        "name": "LoveNotes",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

@app.post("/api/auth/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(400, "Passwords do not match")

    if data.purpose not in {
        "student",
        "teacher",
        "professional",
        "personal learning",
        "other"
    }:
        raise HTTPException(400, "Choose a valid purpose")

    email = data.email.lower()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        purpose=data.purpose,
        education_level=data.education_level.strip()
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_access_token(str(user.id)),
        "user": user
    }


@app.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.email == data.email.lower()
    ).first()

    if not user or not verify_password(
        data.password, user.password_hash
    ):
        raise HTTPException(401, "Incorrect email or password")

    return {
        "access_token": create_access_token(str(user.id)),
        "user": user
    }


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# --------------------------------------------------
# DOCUMENT ACCESS AND SERIALIZATION
# --------------------------------------------------

def owned(doc_id: int, user: User, db: Session) -> Document:
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.owner_id == user.id
    ).first()

    if not doc:
        raise HTTPException(404, "Document not found")

    return doc


def serialize(doc: Document):
    return {
        "id": doc.id,
        "title": doc.title,
        "original_filename": doc.original_filename,
        "archived": doc.archived,
        "created_at": doc.created_at.isoformat(),

        "pages": [
            {
                "id": p.id,
                "page_number": p.page_number,
                "raw_ocr": p.raw_ocr,
                "faithful_text": p.faithful_text,
                "enhanced_text": p.enhanced_text,
                "complete_text": p.complete_text,
                "rotation": p.rotation,
                "detected_language": p.detected_language
            }
            for p in doc.pages
        ],

        "suggestions": [
            {
                "id": s.id,
                "category": s.category,
                "title": s.title,
                "content": s.content,
                "rationale": s.rationale,
                "evidence": s.evidence,
                "confidence": s.confidence,
                "status": s.status
            }
            for s in doc.suggestions
        ]
    }


# --------------------------------------------------
# UPLOAD DOCUMENTS
# --------------------------------------------------

@app.post("/api/documents/upload")
async def upload(
    files: list[UploadFile] = File(...),
    title: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not files or len(files) > 20:
        raise HTTPException(400, "Upload 1–20 files")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    total = 0
    prepared = []

    for f in files:
        name = Path(f.filename or "upload").name
        ext = Path(name).suffix.lower()
        data = await f.read()
        total += len(data)

        if total > max_bytes:
            raise HTTPException(
                413,
                f"Combined upload limit is {settings.max_upload_mb} MB"
            )

        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
            raise HTTPException(
                415,
                "Supported files: JPG, PNG, WEBP, PDF"
            )

        if ext == ".pdf":
            if not data.startswith(b"%PDF-"):
                raise HTTPException(400, "Invalid PDF signature")

        elif ext in {".jpg", ".jpeg"}:
            if not data.startswith(b"\xff\xd8\xff"):
                raise HTTPException(400, "Invalid JPEG signature")

        elif ext == ".png":
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise HTTPException(400, "Invalid PNG signature")

        elif ext == ".webp":
            if not (
                data[:4] == b"RIFF"
                and data[8:12] == b"WEBP"
            ):
                raise HTTPException(400, "Invalid WEBP signature")

        prepared.append((name, ext, data))

    doc = Document(
        owner_id=user.id,
        title=(title or Path(prepared[0][0]).stem)[:255],
        original_filename=", ".join(
            x[0] for x in prepared
        )[:500]
    )

    db.add(doc)
    db.flush()

    page_num = 1
    folder = Path(settings.upload_dir).resolve()

    for name, ext, data in prepared:

        if ext == ".pdf":
            try:
                pdf = fitz.open(stream=data, filetype="pdf")
            except Exception:
                raise HTTPException(400, "Could not read PDF")

            if len(pdf) > 30:
                raise HTTPException(
                    400,
                    "Maximum 30 PDF pages per file"
                )

            for pdf_page in pdf:
                pix = pdf_page.get_pixmap(
                    matrix=fitz.Matrix(1.6, 1.6),
                    alpha=False
                )

                dest = folder / f"{uuid4().hex}.png"
                pix.save(dest)

                db.add(
                    Page(
                        document_id=doc.id,
                        page_number=page_num,
                        stored_path=str(dest),
                        mime_type="image/png"
                    )
                )

                page_num += 1

        else:
            try:
                Image.open(io.BytesIO(data)).verify()
            except Exception:
                raise HTTPException(
                    400,
                    f"{name} is not a valid image"
                )

            dest = folder / f"{uuid4().hex}{ext}"
            dest.write_bytes(data)

            db.add(
                Page(
                    document_id=doc.id,
                    page_number=page_num,
                    stored_path=str(dest),
                    mime_type="image/" + ext.lstrip(".")
                )
            )

            page_num += 1

    db.commit()
    db.refresh(doc)

    return serialize(doc)


# --------------------------------------------------
# DOCUMENT LIST AND SEARCH
# --------------------------------------------------

@app.get("/api/documents")
def list_documents(
    include_archived: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Document).filter(
        Document.owner_id == user.id
    )

    if not include_archived:
        q = q.filter(Document.archived.is_(False))

    return [
        {
            "id": d.id,
            "title": d.title,
            "original_filename": d.original_filename,
            "archived": d.archived,
            "created_at": d.created_at.isoformat(),
            "page_count": len(d.pages)
        }
        for d in q.order_by(
            Document.updated_at.desc()
        ).all()
    ]


@app.get("/api/documents/search")
def search(
    q: str = Query(min_length=1, max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    term = f"%{q.strip()}%"

    docs = db.query(Document).filter(
        Document.owner_id == user.id,
        Document.title.ilike(term)
    ).all()

    return [
        {"id": d.id, "title": d.title}
        for d in docs
    ]


@app.get("/api/documents/{doc_id}")
def get_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return serialize(owned(doc_id, user, db))


# --------------------------------------------------
# PROCESS NOTES: THREE INDEPENDENT WORKFLOWS
# --------------------------------------------------

@app.post("/api/documents/{doc_id}/process")
def process(
    doc_id: int,
    mode: str = "faithful",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if mode not in {"faithful", "enhanced", "complete"}:
        raise HTTPException(400, "Invalid mode")

    doc = owned(doc_id, user, db)

    for page in doc.pages:
        try:
            raw = transcribe(page.stored_path)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc))

        page.raw_ocr = raw

        page.detected_language = (
            "AI-detected"
            if settings.ocr_provider == "gemini_vision"
            else settings.ocr_language
        )

        page.faithful_text = (
            raw if raw.strip()
            else "[No text recognized. Review this source page manually.]"
        )

        if not raw.strip():
            if mode == "enhanced":
                page.enhanced_text = page.faithful_text

            elif mode == "complete":
                page.complete_text = page.faithful_text

            continue

        if mode == "enhanced":
            try:
                page.enhanced_text = enhance(
                    page.faithful_text,
                    page.detected_language
                )
            except Exception as exc:
                raise HTTPException(
                    503,
                    f"AI enhancement failed: {exc}"
                )

        elif mode == "complete":
            try:
                page.complete_text = complete_notes(
                    page.faithful_text
                )
            except Exception as exc:
                raise HTTPException(
                    503,
                    f"Notes completion failed: {exc}"
                )

    db.commit()

    if mode == "complete":
        source = "\n\n".join(
            p.faithful_text for p in doc.pages
        )

        try:
            items = suggestions(
                source,
                purpose=doc.owner.purpose
            )
        except Exception as exc:
            raise HTTPException(
                503,
                f"Suggestions failed: {exc}"
            )

        db.query(Suggestion).filter(
            Suggestion.document_id == doc.id,
            Suggestion.status == "pending"
        ).delete(synchronize_session=False)

        for item in items:
            db.add(
                Suggestion(
                    document_id=doc.id,
                    **item
                )
            )

        db.commit()

    db.refresh(doc)

    return serialize(doc)


# --------------------------------------------------
# SAVE ALL THREE NOTE VERSIONS
# --------------------------------------------------

@app.patch("/api/documents/{doc_id}/content")
def save_content(
    doc_id: int,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = owned(doc_id, user, db)

    if not doc.pages:
        raise HTTPException(400, "No pages")

    marker = "\n\n--- PAGE BREAK ---\n\n"

    # Preserve the previous versions before editing.
    db.add(
        Revision(
            document_id=doc.id,
            snapshot={
                "pages": [
                    {
                        "id": p.id,
                        "faithful_text": p.faithful_text,
                        "enhanced_text": p.enhanced_text,
                        "complete_text": p.complete_text
                    }
                    for p in doc.pages
                ]
            }
        )
    )

    faithful_parts = data.get(
        "faithful_text", ""
    ).split(marker)

    enhanced_parts = data.get(
        "enhanced_text", ""
    ).split(marker)

    complete_parts = data.get(
        "complete_text", ""
    ).split(marker)

    for index, page in enumerate(doc.pages):
        if "faithful_text" in data:
            page.faithful_text = (
                faithful_parts[index]
                if index < len(faithful_parts)
                else ""
            )

        if "enhanced_text" in data:
            page.enhanced_text = (
                enhanced_parts[index]
                if index < len(enhanced_parts)
                else ""
            )

        if "complete_text" in data:
            page.complete_text = (
                complete_parts[index]
                if index < len(complete_parts)
                else ""
            )

    db.commit()

    return {"saved": True}


# --------------------------------------------------
# OPTIONAL AI SUGGESTIONS
# --------------------------------------------------

@app.post("/api/documents/{doc_id}/suggestions")
def make_suggestions(
    doc_id: int,
    depth: str = "detailed",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if depth not in {"basic", "detailed", "comprehensive"}:
        raise HTTPException(400, "Invalid depth")

    doc = owned(doc_id, user, db)

    source = "\n\n".join(
        p.faithful_text for p in doc.pages
    )

    if not source.strip():
        raise HTTPException(400, "Process document first")

    try:
        items = suggestions(
            source,
            depth,
            purpose=user.purpose
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

    db.query(Suggestion).filter(
        Suggestion.document_id == doc.id,
        Suggestion.status == "pending"
    ).delete(synchronize_session=False)

    for item in items:
        db.add(
            Suggestion(
                document_id=doc.id,
                **item
            )
        )

    db.commit()
    db.refresh(doc)

    return serialize(doc)["suggestions"]


@app.patch("/api/suggestions/{suggestion_id}")
def update_suggestion(
    suggestion_id: int,
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item = db.query(Suggestion).join(Document).filter(
        Suggestion.id == suggestion_id,
        Document.owner_id == user.id
    ).first()

    if not item:
        raise HTTPException(404, "Suggestion not found")

    if payload.get("status") not in {
        None, "pending", "accepted", "rejected"
    }:
        raise HTTPException(400, "Invalid status")

    for key in ("status", "title", "content"):
        if key in payload and payload[key] is not None:
            setattr(item, key, payload[key])

    db.commit()

    return {
        "id": item.id,
        "status": item.status,
        "title": item.title,
        "content": item.content
    }


# --------------------------------------------------
# PAGE MANAGEMENT
# --------------------------------------------------

@app.post("/api/documents/{doc_id}/pages/reorder")
def reorder_pages(
    doc_id: int,
    page_ids: list[int],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = owned(doc_id, user, db)
    mapping = {p.id: p for p in doc.pages}

    if len(page_ids) != len(mapping) or set(page_ids) != set(mapping):
        raise HTTPException(
            400,
            "Supply every page ID exactly once"
        )

    for i, pid in enumerate(page_ids, 1):
        mapping[pid].page_number = i

    db.commit()

    return {"saved": True}


@app.post("/api/documents/{doc_id}/archive")
def archive(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = owned(doc_id, user, db)
    doc.archived = True
    db.commit()

    return {"archived": True}


@app.post("/api/documents/{doc_id}/restore")
def restore(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = owned(doc_id, user, db)
    doc.archived = False
    db.commit()

    return {"archived": False}


@app.delete("/api/documents/{doc_id}")
def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = owned(doc_id, user, db)

    for page in doc.pages:
        Path(page.stored_path).unlink(missing_ok=True)

    db.delete(doc)
    db.commit()

    return {"deleted": True}


# --------------------------------------------------
# EXPORT NOTES
# --------------------------------------------------

@app.post("/api/documents/{doc_id}/export")
def export_document(
    doc_id: int,
    format: str = "pdf",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if format not in {"pdf", "docx", "txt"}:
        raise HTTPException(
            400,
            "format must be pdf, docx, or txt"
        )

    doc = owned(doc_id, user, db)

    faithful = "\n\n".join(
        p.faithful_text for p in doc.pages
    )

    enhanced_text = "\n\n".join(
        p.enhanced_text for p in doc.pages
    )

    additions = [
        s.content
        for s in doc.suggestions
        if s.status == "accepted"
    ]

    folder = str(
        Path(settings.upload_dir).resolve().parent / "exports"
    )

    path = export(
        doc.title,
        faithful,
        enhanced_text,
        additions,
        format,
        folder
    )

    media = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain"
    }[format]

    return FileResponse(
        path,
        filename=Path(path).name,
        media_type=media
    )


# --------------------------------------------------
# STUDY SUMMARY AND PRACTICE QUIZ
# --------------------------------------------------

@app.post("/api/documents/{doc_id}/study-aids/{kind}")
def generate_study_aid(
    doc_id: int,
    kind: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from .models import StudyMaterial

    doc = owned(doc_id, user, db)

    if kind not in {"summary", "quiz"}:
        raise HTTPException(
            400,
            "Kind must be summary or quiz"
        )

    source = "\n\n".join(
        p.faithful_text for p in doc.pages
    )

    if not source.strip():
        raise HTTPException(
            400,
            "Process document first"
        )

    try:
        content = study_aids(source, kind)
    except Exception as exc:
        raise HTTPException(
            503,
            f"Could not generate study aid: {exc}"
        )

    item = StudyMaterial(
        document_id=doc.id,
        kind=kind,
        content=content
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "kind": item.kind,
        "content": item.content,
        "created_at": item.created_at.isoformat()
    }


@app.get("/api/documents/{doc_id}/study-aids")
def list_study_aids(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from .models import StudyMaterial

    doc = owned(doc_id, user, db)

    items = db.query(StudyMaterial).filter(
        StudyMaterial.document_id == doc.id
    ).order_by(
        StudyMaterial.created_at.desc()
    ).all()

    return [
        {
            "id": item.id,
            "kind": item.kind,
            "content": item.content,
            "created_at": item.created_at.isoformat()
        }
        for item in items
    ]


# --------------------------------------------------
# SOURCE PAGE IMAGE
# --------------------------------------------------

@app.get("/api/pages/{page_id}/image")
def page_image(
    page_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    page = db.query(Page).join(Document).filter(
        Page.id == page_id,
        Document.owner_id == user.id
    ).first()

    if not page:
        raise HTTPException(404, "Page not found")

    path = Path(page.stored_path)

    if not path.exists():
        raise HTTPException(
            404,
            "Source image unavailable"
        )

    return FileResponse(
        path,
        media_type=page.mime_type
    )


# --------------------------------------------------
# REVISION HISTORY
# --------------------------------------------------

@app.get("/api/documents/{doc_id}/revisions")
def revisions(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = owned(doc_id, user, db)

    return [
        {
            "id": revision.id,
            "created_at": revision.created_at.isoformat(),
            "snapshot": revision.snapshot
        }
        for revision in doc.revisions
    ]
