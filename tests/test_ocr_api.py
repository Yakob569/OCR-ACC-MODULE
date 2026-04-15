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

