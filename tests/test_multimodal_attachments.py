import io
import pytest
from pathlib import Path
from PIL import Image
import pypdf
from fastapi.testclient import TestClient
from backend.main import app
from backend.modules.media.parser import MediaParser

client = TestClient(app)

@pytest.mark.asyncio
async def test_media_parser_image_analysis(tmp_path: Path):
    """Verify MediaParser extracts dimensions, format, and preview for an image."""
    test_img = tmp_path / "test_sample.png"
    img = Image.new("RGB", (320, 240), color="blue")
    img.save(test_img)

    result = await MediaParser.analyze_file(test_img, "test_sample.png")
    assert result["file_type"] == "image"
    assert result["metadata"]["width"] == 320
    assert result["metadata"]["height"] == 240
    assert result["metadata"]["orientation"] == "Ngang (Landscape 16:9 / Photo)"
    assert result["preview_url"] is not None
    assert result["preview_url"].startswith("data:image/")

@pytest.mark.asyncio
async def test_media_parser_document_analysis(tmp_path: Path):
    """Verify MediaParser extracts text and lines from documents."""
    test_doc = tmp_path / "architecture_notes.md"
    content = "# Project Architecture\n- Module 1: Core\n- Module 2: UI\n- Grounded Citations: Active"
    test_doc.write_text(content, encoding="utf-8")

    result = await MediaParser.analyze_file(test_doc, "architecture_notes.md")
    assert result["file_type"] == "document"
    assert "Module 1: Core" in result["extracted_text"]
    assert result["metadata"]["lines"] == 4

@pytest.mark.asyncio
async def test_media_parser_pdf_analysis(tmp_path: Path):
    """Verify MediaParser parses PDF pages and text."""
    test_pdf = tmp_path / "specification.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(test_pdf, "wb") as f:
        writer.write(f)

    result = await MediaParser.analyze_file(test_pdf, "specification.pdf")
    assert result["file_type"] == "document"
    assert result["metadata"]["pages"] == 1

def test_api_upload_and_chat_with_attachments(tmp_path: Path):
    """Test full upload API and sending chat message with attachment."""
    # 1. Create a dummy image in memory
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color="green")
    img.save(buf, format="JPEG")
    buf.seek(0)

    # 2. Upload via API
    upload_res = client.post(
        "/api/v1/chat/upload",
        files={"file": ("photo.jpg", buf, "image/jpeg")},
        data={"workspace_id": "test_upload_ws"}
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["status"] == "success"
    attachment = upload_data["attachment"]
    assert attachment["file_type"] == "image"
    assert attachment["metadata"]["width"] == 100
    assert attachment["metadata"]["height"] == 100

    # 3. Create a conversation
    conv_res = client.post("/api/v1/chat/conversation", json={
        "workspace_id": "test_upload_ws",
        "title": "Multimodal Chat Test"
    })
    assert conv_res.status_code == 200
    conv_id = conv_res.json()["conversation"]["id"]

    # 4. Send message with the attachment using mock adapter
    msg_res = client.post("/api/v1/chat/message", json={
        "conversation_id": conv_id,
        "content": "Hãy phân tích hình ảnh này giúp tôi",
        "use_mock": True,
        "attachments": [attachment]
    })
    assert msg_res.status_code == 200
    res_data = msg_res.json()["response"]
    assert res_data["role"] == "assistant"
    assert "MOCK ASSISTANT RESPONSE" in res_data["content"]

    # 5. Retrieve messages and verify attachment is persisted in history
    hist_res = client.get(f"/api/v1/chat/messages?conversation_id={conv_id}")
    assert hist_res.status_code == 200
    messages = hist_res.json()["messages"]
    user_msg = next(m for m in messages if m["role"] == "user")
    assert len(user_msg["attachments"]) == 1
    assert user_msg["attachments"][0]["file_name"] == "photo.jpg"

    # Clean up
    client.delete(f"/api/v1/chat/conversation/{conv_id}")
