from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_extract_rejects_non_image_upload() -> None:
    response = client.post(
        "/api/v1/ocr/extract",
        files={"file": ("note.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only image uploads are supported."


def test_extract_supports_debug_flag() -> None:
    response = client.post(
        "/api/v1/ocr/extract?debug=true",
        files={"file": ("tiny.png", b"not really an image", "image/png")},
    )

    assert response.status_code == 400
