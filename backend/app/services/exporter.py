from pathlib import Path
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from docx import Document as DocxDocument

def export(title: str, faithful: str, enhanced: str, additions: list[str], fmt: str, folder: str) -> str:
    Path(folder).mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_")[:60] or "notes"
    path = str(Path(folder) / f"{stem}.{fmt}")
    sections = [("Faithful reconstruction", faithful), ("AI-organized notes", enhanced), ("Accepted AI additions (separate from source)", "\n\n".join(additions))]
    if fmt == "txt":
        Path(path).write_text(f"{title}\n\n" + "\n\n".join(h+"\n"+t for h,t in sections), encoding="utf-8")
    elif fmt == "docx":
        doc = DocxDocument(); doc.add_heading(title, 0)
        for heading, body in sections:
            doc.add_heading(heading, 1)
            for line in body.splitlines(): doc.add_paragraph(line)
        doc.save(path)
    elif fmt == "pdf":
        styles=getSampleStyleSheet(); story=[Paragraph(title,styles["Title"]),Spacer(1,12)]
        for heading,body in sections:
            story.append(Paragraph(heading,styles["Heading1"]))
            for line in body.splitlines():
                safe=line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                story.extend([Paragraph(safe or " ",styles["BodyText"]),Spacer(1,4)])
        SimpleDocTemplate(path,pagesize=A4).build(story)
    else: raise ValueError("Unsupported format")
    return path
