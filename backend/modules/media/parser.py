import os
import re
import json
import base64
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
import pypdf

class MediaParser:
    """
    Multimodal & Document analysis engine.
    Extracts text, metadata, frames, and structured insights from Images, Videos, PDFs, and Documents.
    """

    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
    VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
    AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
    DOC_EXTS = {
        ".pdf", ".txt", ".md", ".json", ".csv", ".tsv", ".py", ".ts", ".js", 
        ".tsx", ".jsx", ".html", ".css", ".xml", ".yaml", ".yml", ".sql", 
        ".log", ".env", ".toml", ".rs", ".go", ".java", ".cpp", ".c", ".h"
    }

    @classmethod
    def get_file_type(cls, ext: str) -> str:
        ext = ext.lower()
        if ext in cls.IMAGE_EXTS:
            return "image"
        if ext in cls.VIDEO_EXTS:
            return "video"
        if ext in cls.AUDIO_EXTS:
            return "audio"
        if ext in cls.DOC_EXTS:
            return "document"
        return "file"

    @classmethod
    async def analyze_file(cls, file_path: Path, original_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts deep multimodal insights, previews, and text from the given file.
        """
        filename = original_filename or file_path.name
        ext = file_path.suffix.lower()
        file_type = cls.get_file_type(ext)
        file_size = file_path.stat().st_size

        result: Dict[str, Any] = {
            "file_name": filename,
            "file_type": file_type,
            "extension": ext,
            "file_size": file_size,
            "file_size_human": cls._format_file_size(file_size),
            "preview_url": None,
            "metadata": {},
            "extracted_text": "",
            "summary": ""
        }

        try:
            if file_type == "image":
                await cls._analyze_image(file_path, result)
            elif file_type == "video":
                await cls._analyze_video(file_path, result)
            elif file_type == "document":
                await cls._analyze_document(file_path, ext, result)
            elif file_type == "audio":
                await cls._analyze_audio(file_path, result)
            else:
                # Fallback binary or generic file
                result["summary"] = f"Tệp nhị phân {filename} ({result['file_size_human']})"
                result["extracted_text"] = f"[Tệp nhị phân: {filename}, kích thước: {result['file_size_human']}]"
        except Exception as e:
            result["summary"] = f"Lỗi phân tích tệp {filename}: {str(e)}"
            result["extracted_text"] = f"[Lỗi trích xuất tệp {filename}: {str(e)}]"

        return result

    @classmethod
    async def _analyze_image(cls, file_path: Path, result: Dict[str, Any]) -> None:
        loop = asyncio.get_running_loop()

        def _read_image():
            with Image.open(file_path) as img:
                w, h = img.size
                fmt = img.format or "PNG"
                mode = img.mode
                
                # Make small thumbnail for preview URL
                thumb = img.copy()
                thumb.thumbnail((400, 400))
                import io
                buf = io.BytesIO()
                # Save as JPEG or PNG
                save_fmt = "JPEG" if mode == "RGB" else "PNG"
                if mode in ("RGBA", "P") and save_fmt == "JPEG":
                    thumb = thumb.convert("RGB")
                thumb.save(buf, format="JPEG" if save_fmt == "JPEG" else "PNG", quality=85)
                buf.seek(0)
                b64_data = base64.b64encode(buf.read()).decode("utf-8")
                mime = "image/jpeg" if save_fmt == "JPEG" else "image/png"
                preview_data_url = f"data:{mime};base64,{b64_data}"

                return w, h, fmt, mode, preview_data_url

        w, h, fmt, mode, preview_url = await loop.run_in_executor(None, _read_image)

        aspect_ratio = f"{w}:{h}"
        if w > h:
            orientation = "Ngang (Landscape 16:9 / Photo)"
        elif h > w:
            orientation = "Dọc (Portrait 9:16 / Mobile)"
        else:
            orientation = "Vuông (Square 1:1)"

        result["preview_url"] = preview_url
        result["metadata"] = {
            "width": w,
            "height": h,
            "format": fmt,
            "mode": mode,
            "orientation": orientation,
            "aspect_ratio": aspect_ratio
        }
        result["summary"] = f"Hình ảnh {fmt} ({w}x{h} px, {orientation}, {result['file_size_human']})"
        result["extracted_text"] = (
            f"[THÔNG TIN HÌNH ẢNH: {result['file_name']}]\n"
            f"- Kích thước: {w} x {h} pixels ({orientation})\n"
            f"- Định dạng: {fmt} (Hệ màu: {mode})\n"
            f"- Dung lượng: {result['file_size_human']}\n"
            f"- Xem trước: Đã tải lên và đính kèm vào phiên hội thoại."
        )

    @classmethod
    async def _analyze_video(cls, file_path: Path, result: Dict[str, Any]) -> None:
        loop = asyncio.get_running_loop()

        # 1. Use ffprobe to extract technical parameters
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(file_path)
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *probe_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()

        video_info = {}
        duration = 0.0
        width = 0
        height = 0
        v_codec = "unknown"
        a_codec = "none"
        fps = "unknown"
        bitrate_kbps = 0

        if proc.returncode == 0 and stdout:
            try:
                data = json.loads(stdout.decode("utf-8", errors="ignore"))
                fmt = data.get("format", {})
                duration = float(fmt.get("duration", 0.0))
                bitrate_kbps = int(fmt.get("bit_rate", 0)) // 1000

                for stream in data.get("streams", []):
                    if stream.get("codec_type") == "video" and not width:
                        width = int(stream.get("width", 0))
                        height = int(stream.get("height", 0))
                        v_codec = stream.get("codec_name", "unknown")
                        fps_eval = stream.get("r_frame_rate", "30/1")
                        if "/" in fps_eval:
                            num, den = fps_eval.split("/")
                            if float(den) > 0:
                                fps = f"{round(float(num) / float(den), 2)} fps"
                            else:
                                fps = fps_eval
                        else:
                            fps = f"{fps_eval} fps"
                    elif stream.get("codec_type") == "audio" and a_codec == "none":
                        a_codec = stream.get("codec_name", "unknown")
            except Exception:
                pass

        # 2. Extract representative keyframe thumbnail with ffmpeg
        thumb_path = file_path.parent / f"{file_path.stem}_thumb.jpg"
        seek_pos = "00:00:01" if duration > 2.0 else "00:00:00"
        extract_cmd = [
            "ffmpeg", "-y", "-ss", seek_pos,
            "-i", str(file_path),
            "-vframes", "1",
            "-vf", "scale=480:-1",
            "-q:v", "3",
            str(thumb_path)
        ]
        
        try:
            thumb_proc = await asyncio.create_subprocess_exec(
                *extract_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await thumb_proc.communicate()

            if thumb_path.exists():
                with open(thumb_path, "rb") as f:
                    b64_thumb = base64.b64encode(f.read()).decode("utf-8")
                    result["preview_url"] = f"data:image/jpeg;base64,{b64_thumb}"
                # Clean up temp file
                thumb_path.unlink(missing_ok=True)
        except Exception:
            pass

        # Orientation & social platform compliance
        if width and height:
            if height > width:
                platform_compliance = "Khung hình dọc (9:16) — Tối ưu cho TikTok, YouTube Shorts, Reels"
            elif width > height:
                platform_compliance = "Khung hình ngang (16:9) — Tối ưu cho YouTube ngang, Desktop Video"
            else:
                platform_compliance = "Khung hình vuông (1:1) — Phù hợp Instagram feed"
        else:
            platform_compliance = "Chưa rõ tỷ lệ khung hình"

        duration_formatted = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{duration:.1f}s"

        result["metadata"] = {
            "duration": duration,
            "duration_formatted": duration_formatted,
            "width": width,
            "height": height,
            "video_codec": v_codec,
            "audio_codec": a_codec,
            "fps": fps,
            "bitrate_kbps": bitrate_kbps,
            "platform_compliance": platform_compliance
        }
        result["summary"] = f"Video {v_codec.upper()} ({width}x{height}, {duration_formatted}, {fps}, {result['file_size_human']})"
        result["extracted_text"] = (
            f"[THÔNG SỐ KỸ THUẬT VIDEO: {result['file_name']}]\n"
            f"- Thời lượng: {duration_formatted} ({duration:.2f} giây)\n"
            f"- Độ phân giải: {width} x {height} px ({platform_compliance})\n"
            f"- Codec Video: {v_codec} | Audio: {a_codec}\n"
            f"- Tốc độ khung hình: {fps} | Bitrate: {bitrate_kbps} kbps\n"
            f"- Dung lượng tệp: {result['file_size_human']}\n"
            f"- Tình trạng: Đã trích xuất keyframe và kiểm toán thông số kỹ thuật sẵn sàng phân tích nội dung."
        )

    @classmethod
    async def _analyze_document(cls, file_path: Path, ext: str, result: Dict[str, Any]) -> None:
        loop = asyncio.get_running_loop()

        if ext == ".pdf":
            def _read_pdf():
                reader = pypdf.PdfReader(str(file_path))
                total_pages = len(reader.pages)
                extracted_pages = []
                # Read up to first 30 pages to prevent token bloat
                max_pages = min(total_pages, 30)
                for idx in range(max_pages):
                    page = reader.pages[idx]
                    txt = page.extract_text() or ""
                    if txt.strip():
                        extracted_pages.append(f"--- [Trang {idx + 1}/{total_pages}] ---\n{txt.strip()}")
                
                joined_text = "\n\n".join(extracted_pages)
                title = reader.metadata.title if reader.metadata and reader.metadata.title else file_path.name
                return total_pages, title, joined_text

            total_pages, title, full_text = await loop.run_in_executor(None, _read_pdf)
            char_count = len(full_text)
            
            result["metadata"] = {
                "pages": total_pages,
                "title": title,
                "char_count": char_count
            }
            result["summary"] = f"Tài liệu PDF: {title} ({total_pages} trang, {result['file_size_human']})"
            result["extracted_text"] = (
                f"[NỘI DUNG TÀI LIỆU PDF: {result['file_name']} — {total_pages} trang]\n\n"
                f"{full_text[:40000]}"
                + ("\n\n[...Nội dung còn lại đã được rút gọn...]" if char_count > 40000 else "")
            )

        elif ext in {".csv", ".tsv"}:
            def _read_csv():
                delimiter = "\t" if ext == ".tsv" else ","
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [f.readline().strip() for _ in range(50)]
                lines = [l for l in lines if l]
                headers = lines[0].split(delimiter) if lines else []
                return len(lines), headers, "\n".join(lines[:30])

            row_sample_count, headers, preview = await loop.run_in_executor(None, _read_csv)
            result["metadata"] = {
                "headers": headers,
                "header_count": len(headers)
            }
            result["summary"] = f"Bảng dữ liệu {ext.upper()} ({len(headers)} cột, {result['file_size_human']})"
            result["extracted_text"] = (
                f"[BẢNG DỮ LIỆU {ext.upper()}: {result['file_name']}]\n"
                f"- Các cột ({len(headers)}): {', '.join(headers[:15])}\n"
                f"- Xem trước dữ liệu:\n{preview}"
            )

        else:
            # Code, markdown, json, txt
            def _read_text():
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                lines = content.splitlines()
                return len(lines), content

            line_count, content = await loop.run_in_executor(None, _read_text)
            result["metadata"] = {
                "lines": line_count,
                "char_count": len(content)
            }
            result["summary"] = f"Tệp văn bản/mã nguồn {ext} ({line_count} dòng, {result['file_size_human']})"
            result["extracted_text"] = (
                f"[TỆP TÀI LIỆU/MÃ NGUỒN: {result['file_name']} ({line_count} dòng)]\n\n"
                f"{content[:35000]}"
                + ("\n\n[...Đã rút gọn bớt phần sau do vượt giới hạn context...]" if len(content) > 35000 else "")
            )

    @classmethod
    async def _analyze_audio(cls, file_path: Path, result: Dict[str, Any]) -> None:
        # Use ffprobe for audio specs
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(file_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *probe_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()

        duration = 0.0
        codec = "unknown"
        sample_rate = "unknown"
        channels = 1

        if proc.returncode == 0 and stdout:
            try:
                data = json.loads(stdout.decode("utf-8", errors="ignore"))
                fmt = data.get("format", {})
                duration = float(fmt.get("duration", 0.0))
                for s in data.get("streams", []):
                    if s.get("codec_type") == "audio":
                        codec = s.get("codec_name", "unknown")
                        sample_rate = f"{s.get('sample_rate', 'unknown')} Hz"
                        channels = int(s.get("channels", 1))
                        break
            except Exception:
                pass

        duration_formatted = f"{int(duration // 60)}m {int(duration % 60)}s" if duration >= 60 else f"{duration:.1f}s"
        result["metadata"] = {
            "duration": duration,
            "codec": codec,
            "sample_rate": sample_rate,
            "channels": channels
        }
        result["summary"] = f"Tệp âm thanh {codec.upper()} ({duration_formatted}, {sample_rate}, {result['file_size_human']})"
        result["extracted_text"] = (
            f"[THÔNG SỐ ÂM THANH: {result['file_name']}]\n"
            f"- Thời lượng: {duration_formatted} ({duration:.2f}s)\n"
            f"- Codec: {codec} | Tần số mẫu: {sample_rate} | Kênh: {channels}\n"
            f"- Dung lượng: {result['file_size_human']}"
        )

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
