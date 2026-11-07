
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from ..config import settings


def preprocess(path: str) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image = ImageOps.exif_transpose(image)
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.2)
    return image.filter(ImageFilter.MedianFilter(size=3))


def transcribe(path: str) -> str:
    provider = settings.ocr_provider.lower()
    image = preprocess(path)

    if provider == "tesseract":
        try:
            import pytesseract

            if settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

            return pytesseract.image_to_string(
                image, lang=settings.ocr_language
            ).strip()

        except Exception as exc:
            raise RuntimeError(
                f"Tesseract OCR failed. Install Tesseract and configure "
                f"TESSERACT_CMD if needed: {exc}"
            )

    if provider == "gemini_vision":
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is required for gemini_vision OCR"
            )

        import io
        from google import genai

        buf = io.BytesIO()
        image.save(buf, format="PNG")

        client = genai.Client(api_key=settings.gemini_api_key)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                """
                Detect the language and script, then transcribe in that
                same language. Do not translate.

                Transcribe this handwritten page faithfully.
                Preserve wording, headings, bullets, equations and spelling.
                Do not complete missing words or change the author's meaning.
                Mark unreadable spans as [unclear].
                Return only the transcription.
                """,
                genai.types.Part.from_bytes(
                    data=buf.getvalue(),
                    mime_type="image/png"
                )
            ]
        )

        return response.text or ""

    raise RuntimeError(f"Unsupported OCR_PROVIDER: {provider}")
