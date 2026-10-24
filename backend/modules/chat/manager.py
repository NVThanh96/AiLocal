import re
import uuid
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from backend.core.database import get_db_connection
from backend.modules.workspace.manager import WorkspaceManager
from backend.modules.model.adapter import BaseModelAdapter

SYSTEM_INSTRUCTION = """Bạn là Antigravity Local AI Assistant - Trợ lý kỹ sư phần mềm AI cục bộ chạy trực tiếp trên máy tính Windows của người dùng.

CÁC NGUYÊN TẮC CỐT LÕI (CORE PRINCIPLES):
1. ĐỒNG NHẤT NGÔN NGỮ (LANGUAGE CONSISTENCY):
   - Luôn luôn nhận diện và phản hồi bằng ĐÚNG NGÔN NGỮ mà người dùng đang sử dụng.
   - Khi người dùng hỏi bằng TIẾNG VIỆT, bạn BẮT BUỘC PHẢI TRẢ LỜI 100% HOÀN TOÀN BẰNG TIẾNG VIỆT (trừ các thuật ngữ kỹ thuật, tên biến, tên hàm, đường dẫn tệp và mã nguồn).
   - Tuyệt đối KHÔNG tự ý chuyển sang tiếng Anh khi người dùng hỏi bằng tiếng Việt!
   - Khi người dùng hỏi bằng tiếng Anh (English), hãy trả lời bằng tiếng Anh.

2. NGUYÊN TẮC BẰNG CHỨNG (STRICT GROUNDING & ANTI-HALLUCINATION):
   - Mọi câu trả lời về mã nguồn, cấu hình, kiến trúc phải dựa trên bằng chứng thực tế từ workspace được cung cấp.
   - Tuyệt đối không suy đoán mò mẫm hay bịa đặt tệp, hàm, cấu trúc không tồn tại.
   - Nếu workspace thiếu thông tin, hãy nêu rõ ràng bằng tiếng Việt: "Chưa đủ dữ liệu/bằng chứng trong workspace để khẳng định." và hướng dẫn người dùng cung cấp thêm tệp hoặc đường dẫn cần thiết.

3. TRÌNH BÀY CHUYÊN NGHIỆP:
   - Sử dụng định dạng Markdown chuẩn: tiêu đề rõ ràng, danh sách gạch đầu dòng, khối code có định danh ngôn ngữ (python, typescript, bash...).
"""

class ChatManager:
    """Orchestrates multi-turn conversations, SQLite persistence, and workspace grounding."""

    @classmethod
    async def create_conversation(cls, workspace_id: str, title: str = "New Chat") -> Dict[str, Any]:
        conv_id = str(uuid.uuid4())
        conn = await get_db_connection()
        try:
            await conn.execute("""
                INSERT INTO conversations (id, workspace_id, title)
                VALUES (?, ?, ?);
            """, (conv_id, workspace_id, title))
            await conn.commit()
            return {"id": conv_id, "workspace_id": workspace_id, "title": title}
        finally:
            await conn.close()

    @classmethod
    async def get_history(cls, workspace_id: str) -> List[Dict[str, Any]]:
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("""
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE workspace_id = ?
                ORDER BY updated_at DESC;
            """, (workspace_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    @classmethod
    async def update_conversation_title(cls, conversation_id: str, title: str) -> bool:
        """Update a conversation title."""
        conn = await get_db_connection()
        try:
            cursor = await conn.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (title.strip(), conversation_id)
            )
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()

    @classmethod
    async def delete_conversation(cls, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conn = await get_db_connection()
        try:
            await conn.execute("DELETE FROM messages WHERE conversation_id = ?;", (conversation_id,))
            cursor = await conn.execute("DELETE FROM conversations WHERE id = ?;", (conversation_id,))
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()

    @classmethod
    async def clear_workspace_conversations(cls, workspace_id: str) -> int:
        """Delete all conversations and messages for a given workspace."""
        conn = await get_db_connection()
        try:
            # Delete messages first
            await conn.execute("""
                DELETE FROM messages WHERE conversation_id IN (
                    SELECT id FROM conversations WHERE workspace_id = ?
                );
            """, (workspace_id,))
            cursor = await conn.execute("DELETE FROM conversations WHERE workspace_id = ?;", (workspace_id,))
            await conn.commit()
            return cursor.rowcount
        finally:
            await conn.close()

    @classmethod
    async def delete_conversations_batch(cls, conversation_ids: List[str]) -> int:
        """Batch delete multiple conversations and their messages in one transaction."""
        if not conversation_ids:
            return 0
        conn = await get_db_connection()
        try:
            placeholders = ",".join("?" for _ in conversation_ids)
            await conn.execute(f"DELETE FROM messages WHERE conversation_id IN ({placeholders});", conversation_ids)
            cursor = await conn.execute(f"DELETE FROM conversations WHERE id IN ({placeholders});", conversation_ids)
            await conn.commit()
            return cursor.rowcount
        finally:
            await conn.close()

    @classmethod
    async def get_messages(cls, conversation_id: str) -> List[Dict[str, Any]]:
        conn = await get_db_connection()
        try:
            cursor = await conn.execute("""
                SELECT id, role, content, sources_json, attachments_json, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC;
            """, (conversation_id,))
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "sources": json.loads(row["sources_json"]) if row["sources_json"] else [],
                    "attachments": json.loads(row["attachments_json"]) if "attachments_json" in row.keys() and row["attachments_json"] else [],
                    "created_at": row["created_at"]
                }
                for row in rows
            ]
        finally:
            await conn.close()

    @staticmethod
    def is_vietnamese(text: str) -> bool:
        """Accurately detect whether a text is in Vietnamese."""
        if not text:
            return False
        vietnamese_chars = set(
            "àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
            "ÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
        )
        if any(c in vietnamese_chars for c in text):
            return True
        vn_words = {
            "toi", "ban", "kiem", "tra", "toan", "an", "nguon", "chay", "sua", 
            "giup", "lam", "sao", "the", "nao", "o", "dau", "co", "khong", "du", "an", "tep"
        }
        words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
        return len(words.intersection(vn_words)) >= 2

    @classmethod
    async def process_user_message(
        cls,
        conversation_id: str,
        user_prompt: str,
        adapter: BaseModelAdapter,
        model: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes user query with workspace context grounding, multimodal attachments, and persists conversation.
        """
        conn = await get_db_connection()
        try:
            # 1. Lookup conversation to get workspace_id
            cursor = await conn.execute("SELECT workspace_id FROM conversations WHERE id = ?;", (conversation_id,))
            conv = await cursor.fetchone()
            if not conv:
                raise ValueError(f"Conversation '{conversation_id}' not found.")
            workspace_id = conv["workspace_id"]

            # 2. Retrieve grounded evidence from workspace FTS5
            grounded_docs = []
            try:
                import re
                words = re.findall(r'[\w]+', user_prompt)
                valid_words = [w for w in words if len(w) >= 3][:6]
                if valid_words:
                    fts_query = " OR ".join([f'"{w}"' for w in valid_words])
                    grounded_docs = await WorkspaceManager.search_workspace(workspace_id, fts_query, limit=4)
            except Exception:
                pass

            # 2b. Architecture & Mindmap grounding boost
            is_arch_query = any(k in user_prompt.lower() for k in [
                "mindmap", "kiến trúc", "kien truc", "tổng quan", "tong quan", 
                "architecture", "cấu trúc", "cau truc", "sơ đồ", "so do", "dự án", "du an"
            ])
            if is_arch_query:
                try:
                    arch_cursor = await conn.execute("""
                        SELECT file_path, file_name, snippet(workspace_documents, 3, '<mark>', '</mark>', '...', 15) as match_snippet
                        FROM workspace_documents
                        WHERE workspace_id = ? AND (file_name LIKE '%mindmap%' OR file_path LIKE '%mindmap%' OR file_name LIKE '%report%')
                          AND file_path NOT LIKE 'storage/%'
                        LIMIT 2;
                    """, (workspace_id,))
                    arch_rows = await arch_cursor.fetchall()
                    for r in arch_rows:
                        clean_path = r["file_path"].replace("\\", "/")
                        if not any(d["file_path"] == clean_path for d in grounded_docs):
                            grounded_docs.insert(0, {
                                "file_path": clean_path,
                                "file_name": r["file_name"],
                                "snippet": r["match_snippet"] or "Tài liệu kiến trúc tổng quan hệ thống (docs/mindmap.md)",
                                "score": 0.0
                            })
                except Exception:
                    pass

            # 3. Store user message in SQLite with attachments
            user_msg_id = str(uuid.uuid4())
            attachments_json = json.dumps(attachments or [])
            await conn.execute("""
                INSERT INTO messages (id, conversation_id, role, content, sources_json, attachments_json)
                VALUES (?, ?, 'user', ?, '[]', ?);
            """, (user_msg_id, conversation_id, user_prompt, attachments_json))
            await conn.commit()

            # 4. Assemble messages for LLM adapter
            # 4. Assemble messages for LLM adapter
            from backend.modules.skills.manager import skill_manager
            skills_instructions = await skill_manager.get_active_skills_instructions(workspace_id)
            
            is_vn = cls.is_vietnamese(user_prompt)

            history = await cls.get_messages(conversation_id)
            messages_payload = [{"role": "system", "content": SYSTEM_INSTRUCTION}]

            if is_vn:
                messages_payload.append({
                    "role": "system",
                    "content": "CHỈ THỊ BẮT BUỘC VỀ NGÔN NGỮ (LANGUAGE DIRECTIVE): Người dùng đang hỏi bằng TIẾNG VIỆT. Bạn BẮT BUỘC PHẢI TRẢ LỜI 100% HOÀN TOÀN BẰNG TIẾNG VIỆT tự nhiên, rành mạch, chuẩn xác (chỉ giữ nguyên tên biến, tên hàm, đường dẫn file hoặc cú pháp code). TUYỆT ĐỐI KHÔNG TRẢ LỜI BẰNG TIẾNG ANH."
                })

            if skills_instructions:
                messages_payload.append({"role": "system", "content": skills_instructions})
            
            if grounded_docs:
                if is_vn:
                    evidence_text = "Các tệp tham chiếu đã được kiểm chứng từ workspace (Strict Grounding):\n"
                else:
                    evidence_text = "Verified workspace file references (Strict Grounding):\n"
                for doc in grounded_docs:
                    evidence_text += f"- File: {doc['file_path']}\n  Snippet: {doc['snippet']}\n"
                messages_payload.append({"role": "system", "content": evidence_text})

            # 4b. Inject Multimodal & Document Attachments Context
            if attachments:
                attachment_text = "=== TỆP TÀI LIỆU & ĐA PHƯƠNG TIỆN ĐƯỢC ĐÍNH KÈM (USER ATTACHMENTS CONTEXT) ===\n"
                for att in attachments:
                    fname = att.get("file_name", "Tệp đính kèm")
                    ftype = att.get("file_type", "file").upper()
                    fsize = att.get("file_size_human", "")
                    summary = att.get("summary", "")
                    text = att.get("extracted_text", "")
                    attachment_text += f"\n--- [TỆP ĐÍNH KÈM: {fname} ({ftype}, {fsize})] ---\n"
                    if summary:
                        attachment_text += f"Tóm tắt phân tích sơ bộ: {summary}\n"
                    if text:
                        attachment_text += f"Chi tiết nội dung/thông số kỹ thuật:\n{text}\n"
                attachment_text += "\n===============================================================================\n"
                attachment_text += "Hãy phân tích kỹ các tệp đính kèm ở trên và kết hợp với câu hỏi của người dùng để đưa ra câu trả lời sâu sắc, chính xác, khách quan."
                messages_payload.append({"role": "system", "content": attachment_text})

            for m in history:
                messages_payload.append({"role": m["role"], "content": m["content"]})

            if is_vn:
                messages_payload.append({
                    "role": "system",
                    "content": "NHẮC NHỞ QUAN TRỌNG: Hãy trả lời câu hỏi trên bằng TIẾNG VIỆT tự nhiên và chuẩn xác."
                })

            # 5. Generate assistant response
            assistant_reply = await adapter.generate_response(messages_payload, model=model)

            # 6. Store assistant message in SQLite
            assistant_msg_id = str(uuid.uuid4())
            sources_json = json.dumps(grounded_docs)
            await conn.execute("""
                INSERT INTO messages (id, conversation_id, role, content, sources_json, attachments_json)
                VALUES (?, ?, 'assistant', ?, ?, '[]');
            """, (assistant_msg_id, conversation_id, assistant_reply, sources_json))
            
            # Update conversation timestamp
            await conn.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (conversation_id,))
            await conn.commit()

            return {
                "message_id": assistant_msg_id,
                "role": "assistant",
                "content": assistant_reply,
                "sources": grounded_docs,
                "attachments": []
            }
        finally:
            await conn.close()
