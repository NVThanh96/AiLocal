import re
import uuid
import time
import hashlib
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from backend.core.database import get_db_connection
from backend.modules.security.broker import SecurityBroker
from backend.modules.workspace.manager import WorkspaceManager

MAX_CRAWL_BYTES = 5 * 1024 * 1024  # 5 MB per document limit
CRAWL_TIMEOUT = 15.0

PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|above)\s+instructions?",
    r"(?i)you\s+are\s+now\s+(unrestricted|in\s+developer\s+mode|dan)",
    r"(?i)system\s*:\s*you\s+must",
    r"(?i)new\s+system\s+prompt\s*:"
]

class CrawlEngine:
    """
    Safe Web & Local Knowledge Acquisition Engine:
    - Strict SSRF prevention.
    - Content hash deduplication (SHA-256).
    - Prompt injection sanitization and sandboxing.
    - Source provenance tracking.
    """

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()

    @staticmethod
    def strip_html_tags(raw_html: str) -> str:
        """Simple, dependency-free HTML tag stripper and whitespace normalizer."""
        # Strip script and style blocks
        clean = re.sub(r'(?is)<(script|style).*?>.*?</\1>', ' ', raw_html)
        # Strip html tags
        clean = re.sub(r'<[^<]+?>', ' ', clean)
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    @staticmethod
    def sandbox_untrusted_content(content: str, source_url: str) -> str:
        """
        Sanitize prompt injection attempts and isolate untrusted content
        inside safe structural boundaries.
        """
        sanitized = content
        for pat in PROMPT_INJECTION_PATTERNS:
            sanitized = re.sub(pat, "[BLOCKED_PROMPT_INJECTION]", sanitized)

        # Wrap in unambiguous data boundary
        return (
            f"<untrusted_crawled_content source=\"{source_url}\">\n"
            f"{sanitized}\n"
            f"</untrusted_crawled_content>"
        )

    @classmethod
    async def fetch_web_page(cls, url: str) -> Dict[str, Any]:
        """Safely fetch web page with SSRF checks and byte limits."""
        is_safe, msg = SecurityBroker.validate_network_url(url)
        if not is_safe:
            raise PermissionError(f"SSRF Security Violation: {msg}")

        async with httpx.AsyncClient(timeout=CRAWL_TIMEOUT, follow_redirects=True) as client:
            res = await client.get(url, headers={"User-Agent": "LocalAiAgentWorkspace/1.0"})
            if res.status_code != 200:
                raise ValueError(f"HTTP request returned status {res.status_code}")

            content_bytes = res.content
            if len(content_bytes) > MAX_CRAWL_BYTES:
                raise ValueError(f"Page exceeded maximum size limit ({len(content_bytes)} > {MAX_CRAWL_BYTES})")

            text = res.text
            clean_text = cls.strip_html_tags(text)
            title_match = re.search(r'(?i)<title>(.*?)</title>', text)
            title = title_match.group(1).strip() if title_match else url

            return {
                "url": str(res.url),
                "title": title,
                "clean_text": clean_text,
                "raw_length": len(content_bytes)
            }

    @classmethod
    async def crawl_source(
        cls,
        workspace_id: str,
        workspace_path: str,
        source_type: str,
        target_uri: str
    ) -> Dict[str, Any]:
        """
        Execute full crawl pipeline:
        Fetch -> Extract -> Deduplicate -> Store Document & Provenance -> Index FTS5.
        """
        job_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        provenance_id = str(uuid.uuid4())

        conn = await get_db_connection()
        try:
            # 1. Register crawl job
            await conn.execute("""
                INSERT INTO crawl_jobs (id, workspace_id, source_type, target_url, status)
                VALUES (?, ?, ?, ?, 'RUNNING');
            """, (job_id, workspace_id, source_type, target_uri))
            await conn.commit()

            # 2. Fetch & Extract
            if source_type == "web":
                fetched = await cls.fetch_web_page(target_uri)
                canonical_url = fetched["url"]
                title = fetched["title"]
                raw_text = fetched["clean_text"]
                trust_level = "UNTRUSTED_WEB"
            elif source_type == "local":
                # Safe read local file in workspace
                file_info = WorkspaceManager.read_file(workspace_path, target_uri)
                canonical_url = file_info["path"]
                title = Path(target_uri).name
                raw_text = file_info["content"]
                trust_level = "LOCAL_WORKSPACE"
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            # 3. Deduplication check via SHA-256
            content_hash = cls.compute_hash(raw_text)
            cursor = await conn.execute("""
                SELECT id, canonical_url FROM crawl_documents
                WHERE workspace_id = ? AND content_hash = ?;
            """, (workspace_id, content_hash))
            existing = await cursor.fetchone()

            if existing:
                # Deduplicated: already exists
                await conn.execute("UPDATE crawl_jobs SET status = 'COMPLETED_DUPLICATE' WHERE id = ?;", (job_id,))
                await conn.commit()
                return {
                    "job_id": job_id,
                    "status": "DUPLICATE",
                    "existing_document_id": existing["id"],
                    "canonical_url": canonical_url,
                    "content_hash": content_hash
                }

            # 4. Prompt Injection Defense
            safe_content = cls.sandbox_untrusted_content(raw_text, canonical_url)

            # 5. Store in crawl_documents & source_provenance
            await conn.execute("""
                INSERT INTO crawl_documents (id, job_id, workspace_id, canonical_url, title, content, content_hash, byte_size, trust_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (doc_id, job_id, workspace_id, canonical_url, title, safe_content, content_hash, len(raw_text.encode('utf-8')), trust_level))

            await conn.execute("""
                INSERT INTO source_provenance (id, document_id, source_type, canonical_uri, verified, meta_json)
                VALUES (?, ?, ?, ?, 1, ?);
            """, (provenance_id, doc_id, source_type, canonical_url, json_dumps_safe({"fetched_at": time.time(), "trust": trust_level})))

            # 6. Index into workspace_documents (FTS5) for instant retrieval
            await conn.execute("""
                INSERT INTO workspace_documents (workspace_id, file_path, file_name, content)
                VALUES (?, ?, ?, ?);
            """, (workspace_id, f"crawl://{canonical_url}", title, raw_text))

            # 7. Complete job
            await conn.execute("""
                UPDATE crawl_jobs SET status = 'COMPLETED', documents_count = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (job_id,))
            await conn.commit()

            return {
                "job_id": job_id,
                "document_id": doc_id,
                "status": "COMPLETED",
                "canonical_url": canonical_url,
                "title": title,
                "content_hash": content_hash,
                "trust_level": trust_level,
                "char_count": len(raw_text)
            }
        except Exception as e:
            await conn.execute("UPDATE crawl_jobs SET status = 'FAILED' WHERE id = ?;", (job_id,))
            await conn.commit()
            raise e
        finally:
            await conn.close()

def json_dumps_safe(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str)
