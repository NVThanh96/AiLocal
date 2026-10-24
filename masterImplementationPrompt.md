# MASTER IMPLEMENTATION PROMPT

# LOCAL AI AGENT WORKSPACE — LOCAL-FIRST MULTI-AGENT PLATFORM

## VAI TRÒ CỦA BẠN

Bạn là Principal Software Architect, Senior Full-Stack Engineer, AI Agent Engineer, Data Engineer, Security Engineer, DevOps Engineer và QA Automation Engineer.

Nhiệm vụ của bạn là PHÂN TÍCH, THIẾT KẾ, XÂY DỰNG, KIỂM THỬ và HOÀN THIỆN một ứng dụng Local AI Agent Workspace trên Windows 11.

Sản phẩm hướng đến trải nghiệm tương tự coding agent desktop: người dùng chọn thư mục, trò chuyện với AI, giao nhiệm vụ bằng ngôn ngữ tự nhiên và yêu cầu hệ thống thực hiện công việc thực tế trong phạm vi được cấp quyền.

Không chỉ tạo giao diện demo. Mục tiêu là một ứng dụng có backend thật, database thật, model adapter thật, task queue thật, tool execution có kiểm soát và quy trình kiểm thử có bằng chứng.

---

# PHẦN I — BỐI CẢNH VÀ RÀNG BUỘC

## 1. Cấu hình máy

* OS: Windows 11.
* GPU: NVIDIA RTX 2070 desktop, 8 GB VRAM.
* RAM: 32 GB DDR4 3200 MHz.
* SSD: còn trống tối thiểu khoảng 200 GB.
* Ưu tiên local-first.
* Ưu tiên phần mềm miễn phí, giấy phép minh bạch, không bắt buộc trả phí dịch vụ AI.
* Không được mặc định người dùng cho phép tải lên hoặc gửi dữ liệu ra ngoài máy.

Trước khi cài đặt, hãy khảo sát phần cứng, driver, môi trường và phiên bản công cụ thực tế.

Không giả định mọi model hoặc công cụ đều tương thích chỉ vì có hỗ trợ NVIDIA nói chung.

## 2. Mục tiêu sản phẩm

Hệ thống cần hỗ trợ:

1. Chọn, mở và quản lý workspace.
2. Chat với AI dựa trên nội dung thực tế trong workspace.
3. Phân tích yêu cầu, phát hiện điểm mơ hồ và hỏi lại người dùng.
4. Lập kế hoạch có các bước, dependency và tiêu chí nghiệm thu.
5. Giao nhiệm vụ cho agent chuyên môn.
6. Quản lý hàng đợi và giới hạn tài nguyên.
7. Crawl dữ liệu từ nguồn được phép.
8. Phân tích website, repository, tài liệu, database và dữ liệu người dùng.
9. Ghi nguồn gốc dữ liệu và kiểm chứng kết quả.
10. Thực thi file operations, terminal commands và các tool được cấp quyền.
11. Chạy test, debug và kiểm tra hồi quy.
12. Lưu Project Memory, Knowledge Memory, Error Memory và Execution Logs.
13. Hỗ trợ skill registry, MCP registry và permission manager.
14. Tự động dọn artifact debug tạm sau 7 ngày.
15. Tạo báo cáo cuối cùng dựa trên kết quả thực tế.
16. Có thể mở rộng sang Development, Research, CEO/Strategy, Finance, Design, Affiliate, Marketing, Translation, Image, Video, Audio và Security.

Không triển khai tất cả domain cùng lúc. Ưu tiên xây dựng lõi có thể mở rộng mà không phải viết lại.

---

# PHẦN II — QUY TẮC LÀM VIỆC BẮT BUỘC

## 3. Audit trước khi coding

Bước đầu tiên là khảo sát môi trường và source hiện có.

Nếu repository đã tồn tại:

* Đọc cấu trúc thư mục.
* Đọc README, tài liệu kiến trúc, manifest và cấu hình.
* Kiểm tra entrypoint, module, database, API và test.
* Xác định phần đã hoạt động, phần chưa hoàn thiện, lỗi, dependency trùng và các rủi ro.
* Tái sử dụng logic tốt hiện có.
* Không viết lại toàn bộ chỉ để thay đổi phong cách kiến trúc.
* Không xóa, di chuyển hoặc ghi đè dữ liệu hiện hữu khi chưa được phép.

Nếu là repository mới:

* Xác minh thư mục thực tế.
* Tạo kiến trúc tối thiểu và tài liệu quyết định.
* Chỉ tạo các module cần cho giai đoạn đang thực hiện.

Không khẳng định đã đọc hoặc kiểm tra file nếu chưa thực sự truy cập file đó.

## 4. Không đoán mò — Requirement Clarification Gate

Xây dựng một Requirement Intelligence Engine độc lập.

Mọi yêu cầu mới phải trải qua quy trình:

### Bước A — Parse

Trích xuất:

* Mục tiêu chính.
* Kết quả mong muốn.
* Workspace và phạm vi tác động.
* Đối tượng, dữ liệu và hệ thống liên quan.
* Các ràng buộc.
* Điều kiện nghiệm thu.
* Những hành động bị cấm.
* Mức độ rủi ro.

### Bước B — Gather Evidence

Trước khi hỏi người dùng, kiểm tra các thông tin có thể tự xác minh bằng quyền hiện có:

* File và cấu hình trong workspace.
* Lịch sử hội thoại liên quan.
* Tài liệu dự án.
* Error Memory.
* Các nguồn crawl đã được phép.
* Trạng thái thực tế của tool và môi trường.

Phải phân biệt dữ kiện được xác minh với suy luận của model.

### Bước C — Assess Ambiguity

Phân loại mỗi yêu cầu:

* READY: đủ rõ để thực hiện.
* NEEDS_CLARIFICATION: thiếu thông tin ảnh hưởng đáng kể đến kết quả.
* NEEDS_APPROVAL: đã hiểu nhưng cần phê duyệt hành động.
* BLOCKED: thiếu quyền, dữ liệu hoặc điều kiện tiên quyết.
* UNSUPPORTED: không có công cụ hoặc năng lực phù hợp.

Không dùng một confidence score do LLM tự khai báo làm bằng chứng duy nhất rằng yêu cầu đã rõ.

### Bước D — Ask Targeted Questions

Khi cần làm rõ, hiển thị:

1. Điều AI đã hiểu.
2. Những dữ kiện đã xác minh.
3. Những điểm còn chưa rõ.
4. Vì sao chúng ảnh hưởng đến kết quả.
5. Câu hỏi ngắn gọn, cụ thể.
6. Các phương án đề xuất khi hữu ích.
7. Hành động sẽ bị tạm dừng trong lúc chờ câu trả lời.

Ưu tiên gom các câu hỏi liên quan thành một lượt, nhưng không tạo bảng hỏi dài nếu chỉ thiếu một thông tin thiết yếu.

Không hỏi lại những điều đã có bằng chứng trong workspace.

Không tự bịa giá trị mặc định cho những thông tin quyết định như phạm vi xóa dữ liệu, môi trường production, ngân sách thật hoặc quyền gửi dữ liệu ra ngoài.

Có thể dùng giả định an toàn, có thể đảo ngược cho những lựa chọn kỹ thuật nhỏ. Phải ghi rõ giả định và cho người dùng biết.

### Bước E — Freeze Task Specification

Sau khi đủ thông tin, tạo Task Specification bất biến theo phiên bản, gồm:

* task_id.
* yêu cầu gốc.
* yêu cầu đã chuẩn hóa.
* dữ kiện và nguồn.
* giả định được chấp thuận.
* câu hỏi đã giải quyết.
* phạm vi được phép thay đổi.
* đầu ra mong muốn.
* acceptance criteria.
* rủi ro và quyền yêu cầu.
* các điều kiện dừng.

Nếu người dùng thay đổi yêu cầu, tạo phiên bản mới và đánh giá lại dependency.

Không tự mở rộng phạm vi chỉ vì agent cho rằng sẽ tốt hơn.

## 5. Không báo cáo thành công khi chưa xác minh

* Không bịa kết quả test.
* Không bịa nguồn crawl.
* Không bịa file đã thay đổi.
* Không đánh dấu task completed chỉ dựa trên lời tự nhận của agent.
* Phải lưu exit code, test result, artifact hoặc bằng chứng phù hợp.
* Phân biệt rõ completed, completed_with_warnings, failed, blocked và awaiting_approval.
* Nếu không thể xác minh, phải nói rõ chưa xác minh.

---

# PHẦN III — KIẾN TRÚC CÔNG NGHỆ

## 6. Stack mặc định

Đánh giá tính tương thích rồi sử dụng:

* Desktop: Tauri + React + TypeScript.
* Backend: Python + FastAPI.
* Local LLM adapter: Ollama.
* Primary model ban đầu: Qwen3 4B, nếu benchmark xác nhận phù hợp.
* Coding model tùy chọn: Qwen2.5-Coder 7B, chỉ tải khi cần.
* Workflow: task engine rõ ràng, có thể dùng LangGraph cho workflow phức tạp.
* Database: SQLite + FTS5.
* Embeddings và vector retrieval: chỉ bổ sung khi có nhu cầu đo được.
* Version control: Git.
* Testing: pytest, Playwright và công cụ phù hợp với workspace.
* Media processing: adapter riêng cho FFmpeg, OCR và image tools khi triển khai domain media.

Không phụ thuộc vào một model duy nhất.

Tạo Model Adapter interface để có thể đổi runtime hoặc model mà không phải sửa business logic.

Không mặc định phải dùng LangGraph cho mọi thao tác. CRUD, file operations và các tác vụ xác định phải được thực hiện bằng code thông thường khi phù hợp.

## 7. Cấu trúc module

Tổ chức theo domain, dependency hướng vào core interfaces.

Các module logic:

* app_shell.
* workspace_manager.
* requirement_intelligence.
* conversation_manager.
* task_specification.
* orchestrator.
* task_queue.
* agent_registry.
* skill_registry.
* model_registry.
* tool_registry.
* crawl_engine.
* source_provenance.
* research_engine.
* permission_manager.
* execution_broker.
* sandbox_manager.
* project_memory.
* knowledge_memory.
* error_memory.
* audit_logger.
* evaluation_engine.
* retention_manager.

Không bắt buộc tạo tất cả thành package riêng nếu chưa cần. Không tạo file trùng lặp hoặc module rỗng chỉ để khớp sơ đồ.

---

# PHẦN IV — CRAWL & KNOWLEDGE ACQUISITION ENGINE

## 8. Mục tiêu

Xây dựng crawler có thể thu thập, chuẩn hóa, kiểm tra, lập chỉ mục và truy xuất dữ liệu từ nguồn được phép.

Crawler phải tách biệt với agent quyết định và tool execution.

## 9. Các connector

Triển khai theo thứ tự:

1. Local filesystem.
2. HTTP/HTTPS public web.
3. API connector.
4. Git repository.
5. PDF và tài liệu văn phòng.
6. Browser automation cho trang cần JavaScript khi thực sự cần.
7. Các connector khác thông qua plugin hoặc adapter.

Không triển khai scraper đặc thù cho mọi website trong MVP.

## 10. Crawl pipeline

Mỗi job phải thực hiện:

1. Discover sources.
2. Validate scope and permission.
3. Fetch.
4. Extract.
5. Normalize.
6. Deduplicate.
7. Validate content quality.
8. Store source provenance.
9. Index.
10. Produce research report.

Mỗi tài liệu cần metadata thích hợp:

* source_id.
* source_type.
* canonical_url hoặc file path.
* title.
* fetched_at.
* published_at nếu có bằng chứng.
* content_hash.
* parser_version.
* crawl_job_id.
* source trust classification.
* license/usage notes nếu xác định được.
* verification status.
* lỗi hoặc giới hạn thu thập.

Không bịa ngày xuất bản, giấy phép hoặc tác giả.

## 11. Crawl safety

* Tuân thủ điều khoản sử dụng và các quy tắc truy cập áp dụng.
* Tôn trọng robots.txt và giới hạn tốc độ phù hợp.
* Ưu tiên API chính thức.
* Có timeout, retry giới hạn, backoff và rate limit.
* Giới hạn bytes tải về, redirect, độ sâu crawl và số trang.
* Chặn SSRF, localhost, private IP, link-local và cloud metadata.
* Kiểm tra redirect và đích kết nối, không chỉ kiểm tra URL đầu tiên.
* Không vượt CAPTCHA, paywall hoặc cơ chế kiểm soát truy cập.
* Không tự gửi cookie, credential hoặc file nội bộ đến website.
* Không chạy JavaScript hoặc executable lấy từ nguồn crawl.
* Nội dung crawl phải được coi là untrusted input.
* Chống prompt injection bằng cách phân tách rõ system instructions và retrieved content.
* Không cho retrieved content tự cấp quyền hoặc tự kích hoạt tool.

## 12. Source verification

Hệ thống phải phân biệt:

* Raw source.
* Extracted content.
* Model interpretation.
* Verified facts.
* Conflicting claims.
* Unknown information.

Mỗi kết luận quan trọng cần trỏ về source document và vị trí hỗ trợ khi khả thi.

Với nghiên cứu cần độ tin cậy cao, tìm nhiều nguồn độc lập. Không coi nhiều trang sao chép cùng một nguồn là nhiều nguồn độc lập.

Nếu không có đủ nguồn, ghi rõ chưa đủ bằng chứng thay vì tự lấp khoảng trống.

## 13. Crawl storage và incremental updates

* SQLite lưu metadata, job state và provenance.
* File nội dung lớn lưu trong thư mục dữ liệu được quản lý.
* FTS5 phục vụ full-text search.
* Hash để phát hiện nội dung thay đổi.
* Deduplication theo content hash và canonical source.
* Crawl có thể tiếp tục sau gián đoạn.
* Retry không tạo bản ghi trùng.
* Có giới hạn dung lượng và chính sách retention.
* Không tự động tải toàn bộ website nếu chưa có giới hạn phạm vi.

---

# PHẦN V — TASK INTELLIGENCE VÀ ORCHESTRATION

## 14. Task Specification Schema

Mỗi task cần có schema dữ liệu được kiểm tra bằng code, tối thiểu:

* task_id.
* workspace_id.
* request_version.
* status.
* goal.
* scope.
* constraints.
* verified_facts.
* assumptions.
* unresolved_questions.
* approved_assumptions.
* source_refs.
* acceptance_criteria.
* risk_level.
* required_permissions.
* dependencies.
* assigned_agent.
* resource_budget.
* created_at / updated_at.
* execution_evidence.
* final_report.

Không lưu toàn bộ trạng thái quan trọng chỉ trong chat text.

## 15. Planner

Planner phải:

1. Đọc Task Specification đã được chấp thuận.
2. Xác định dependency và thứ tự thực hiện.
3. Chia thành task nhỏ, có đầu ra kiểm chứng được.
4. Chọn specialist phù hợp.
5. Ước lượng tài nguyên và giới hạn concurrency.
6. Xác định điểm cần phê duyệt.
7. Xác định điều kiện dừng và phương án phục hồi.
8. Lưu kế hoạch có phiên bản.

Không giao việc cho agent chỉ dựa vào tên gọi. Agent phải có capability, tool permissions và acceptance criteria phù hợp.

## 16. Task queue

Hỗ trợ:

* queued.
* planning.
* awaiting_clarification.
* awaiting_approval.
* ready.
* running.
* blocked.
* retrying.
* verifying.
* completed.
* completed_with_warnings.
* failed.
* cancelled.

Có dependency tracking, timeout, retry limit, cancellation, checkpoint và resource budgets.

Không cho hai agent cùng ghi một file nếu chưa có file lock, branch riêng hoặc cơ chế merge an toàn.

Khi một task phụ thất bại, đánh giá ảnh hưởng đến dependency trước khi tiếp tục.

Không retry vô hạn và không lặp lại hành động có side effect mà không kiểm tra idempotency.

## 17. Multi-Agent

Xây dựng các vai trò ban đầu:

* Orchestrator.
* Research Agent.
* Development Agent.
* QA Agent.
* Security Reviewer.

Các agent này có thể dùng chung model.

Không tạo process hoặc model riêng cho từng vai trò nếu không cần thiết.

Agent phải trả về kết quả có cấu trúc, source references khi cần, trạng thái, file changes, tool calls, test evidence và unresolved issues.

Không để agent tự ý tăng quyền của chính nó.

---

# PHẦN VI — MEMORY, ERROR INTELLIGENCE VÀ LOG RETENTION

## 18. Memory layers

Project Memory:

* Kiến trúc và cấu trúc workspace.
* Quy tắc code.
* Quyết định và ràng buộc.
* Trạng thái dự án đã xác minh.

Knowledge Memory:

* Skill đã kiểm chứng.
* Quy trình.
* Tài liệu có nguồn.
* Các bài học có phạm vi áp dụng rõ ràng.

Error Memory:

* Môi trường và bước tái hiện.
* Error signature.
* Root cause hoặc trạng thái chưa xác định.
* Các cách xử lý đã thử.
* Patch và regression test.
* Kết quả xác minh.
* Phạm vi áp dụng và giới hạn.

Execution Logs:

* Task và agent.
* Tool call.
* Timestamp.
* Exit code.
* File changes.
* Error và retry.
* Test results.
* Approval decisions.

## 19. Chống lặp lỗi

Trước khi xử lý lỗi:

1. Chuẩn hóa thông báo lỗi.
2. Tìm lỗi tương tự theo signature và ngữ cảnh.
3. Kiểm tra giải pháp cũ có còn phù hợp với phiên bản hiện tại không.
4. Xác định test cần chạy.
5. Không áp dụng máy móc giải pháp cũ nếu môi trường đã thay đổi.

Sau khi xử lý:

1. Xác nhận nguyên nhân bằng chứng.
2. Chạy regression test.
3. Lưu kết quả.
4. Chỉ nâng cấp thành verified lesson khi có đủ bằng chứng.
5. Nếu giải pháp thất bại, lưu trạng thái thất bại để tránh lặp lại.

## 20. Retention

Mặc định:

* Artifact debug tạm: 7 ngày.
* Verbose execution logs: 7 ngày.
* Temporary crawl artifacts: 7 ngày.
* Verified lessons: lưu lâu dài.
* Project decisions: lưu lâu dài.
* Audit metadata: theo chính sách riêng.
* Secrets: không ghi vào log.

Cleanup phải có dry-run, báo cáo dự kiến xóa, allowlist các thư mục do ứng dụng quản lý và kiểm thử đường dẫn.

Không bao giờ áp dụng retention cleanup lên workspace người dùng.

---

# PHẦN VII — SECURITY VÀ EXECUTION BROKER

## 21. Permission model

Tách quyền:

* workspace.read.
* workspace.write.
* workspace.delete.
* terminal.execute.
* network.fetch.
* browser.navigate.
* browser.interact.
* package.install.
* external_data_transfer.
* database.modify.
* media.generate.
* publishing.execute.

Mỗi tool khai báo permission requirements.

Không dùng một boolean allow_all để cấp mọi quyền.

## 22. Execution Broker

Tất cả thao tác có side effect phải đi qua broker.

Broker cần:

* Kiểm tra schema input.
* Kiểm tra quyền.
* Chuẩn hóa đường dẫn.
* Kiểm tra workspace boundary.
* Giới hạn timeout và resource budget.
* Ghi audit event.
* Yêu cầu approval khi cần.
* Thu thập kết quả và exit code.
* Hỗ trợ cancellation.
* Không ghi secret vào log.

Không thực thi shell command bằng cách nối chuỗi input do LLM tạo với lệnh hệ thống.

Ưu tiên command templates, argument arrays và executable allowlist.

## 23. Sandbox

Đánh giá WSL2 hoặc sandbox tương thích với Windows.

Không coi WSL2 mặc định là sandbox an toàn tuyệt đối.

Phải kiểm tra filesystem mounts, network access, process permissions và quyền truy cập dữ liệu Windows.

Nếu không có sandbox phù hợp, disable hoặc giới hạn những tác vụ code không đáng tin cậy. Không âm thầm chuyển sang chạy unrestricted trên host.

## 24. Approval rules

Yêu cầu phê duyệt rõ ràng trước:

* Xóa dữ liệu quan trọng.
* Thay đổi schema database.
* Thao tác production.
* Cài phần mềm hoặc package chưa được duyệt.
* Gửi file hoặc nội dung riêng tư ra ngoài.
* Thay đổi security settings.
* Publish, mua hàng hoặc thực hiện giao dịch.
* Các thao tác không thể dễ dàng khôi phục.

Không diễn giải im lặng hoặc việc tiếp tục chat là chấp thuận.

---

# PHẦN VIII — GIAO DIỆN

## 25. Các màn hình cần có theo giai đoạn

MVP:

1. Workspace selector.
2. Chat workspace.
3. Task plan and clarification.
4. Task queue.
5. File diff and approval.
6. Execution log.
7. Settings for model and permissions.

Sau MVP:
8. Crawl jobs and sources.
9. Research results with source provenance.
10. Memory and error history.
11. Agent and skill registry.
12. MCP and connector management.
13. Evaluation dashboard.
14. Media workflows.

Không tạo nút chỉ để trang trí.

Mỗi nút phải gọi chức năng thực tế, có loading state, error state và feedback phù hợp.

Không giả lập task progress hoặc test results.

---

# PHẦN IX — ROADMAP TRIỂN KHAI

## Phase 0 — Audit và kế hoạch

* Khảo sát source và môi trường.
* Kiểm tra giấy phép.
* Chốt kiến trúc và dependency.
* Xây acceptance criteria.
* Tạo baseline test.

Chỉ chuyển phase khi audit report và kế hoạch được xác minh.

## Phase 1 — Workspace + Local Chat

* Desktop shell.
* FastAPI.
* Ollama adapter.
* Workspace manager.
* Read-only file search.
* Conversation persistence.

Acceptance:

* Chat chạy local.
* Đọc đúng file.
* Trả lời có bằng chứng.
* Không sửa file khi chưa được yêu cầu.

## Phase 2 — Requirement Intelligence

* Structured task specification.
* Ambiguity classification.
* Clarification UI.
* Approval flow.
* Versioned requirements.

Acceptance:

* Test các yêu cầu rõ, mơ hồ, nguy hiểm và thiếu quyền.
* Không tự thực hiện tác vụ nguy hiểm.
* Không hỏi lại thông tin có thể tự xác minh.

## Phase 3 — Safe Execution

* Execution Broker.
* File operations.
* Diff, checkpoint, rollback.
* Terminal sandbox.
* Task queue và audit.

Acceptance:

* Thay đổi được kiểm soát.
* Có thể rollback.
* Chặn được các bài test path traversal và command injection đã định nghĩa.

## Phase 4 — Crawl Engine

* Local file connector.
* HTTP connector.
* API connector.
* Provenance và deduplication.
* Source verification.
* Research report.

Acceptance:

* Dữ liệu truy xuất được nguồn.
* Có timeout và giới hạn crawl.
* Chặn được các bài test SSRF đã định nghĩa.
* Không làm theo prompt injection trong dữ liệu crawl.

## Phase 5 — Development + QA + Memory

* Coding agent.
* Test runner.
* Error Memory.
* Regression test.
* Cleanup.

Acceptance:

* Sửa được lỗi tái hiện được.
* Báo cáo đúng kết quả test.
* Không ghi nhận giải pháp chưa xác minh là tri thức đã kiểm chứng.

## Phase 6 — Orchestrator + Multi-Agent

* Dependency planning.
* Agent registry.
* Queue scheduling.
* Checkpoint/resume.
* Resource limits.
* Agent coordination.

Acceptance:

* Nhiệm vụ nhiều bước hoạt động ổn định.
* Không mất trạng thái khi restart.
* Không có concurrent writes gây hỏng dữ liệu trong test suite.

## Phase 7 — Domain expansion

Bổ sung lần lượt:

* Research.
* Design.
* Finance.
* CEO/Strategy.
* Affiliate/Marketing.
* Image/Video/Audio.
* Translation.
* Advanced browser automation.

Mỗi domain có capability manifest, permission requirements, benchmark và acceptance tests riêng.

---

# PHẦN X — LICENSE, COST VÀ DEPENDENCY AUDIT

## 26. License governance

Trước khi thêm dependency, kiểm tra:

* Repository chính thức.
* Giấy phép code.
* Giấy phép model weights.
* Giấy phép dataset và tài nguyên tải về.
* Điều khoản thương mại.
* Dependency bắc cầu.
* Plugin và MCP server.
* Yêu cầu attribution hoặc phân phối license text.

Tạo:

* dependency manifest.
* license inventory.
* model inventory.
* nguồn tải chính thức.
* phiên bản đã pin.
* ghi chú rủi ro giấy phép.

Không khẳng định miễn phí hoặc được phép thương mại nếu chưa có bằng chứng.

## 27. Chi phí

Ưu tiên cấu hình không cần dịch vụ trả phí bắt buộc.

Đo:

* Disk usage.
* RAM và VRAM.
* Model latency.
* Crawl throughput.
* Test duration.
* CPU/GPU utilization.

Không tự mua dịch vụ, gọi API tính phí hoặc gửi dữ liệu ra ngoài.

---

# PHẦN XI — QUY TRÌNH LÀM VIỆC VỚI ANTIGRAVITY

## 28. Cách thực thi

Không xây toàn bộ dự án trong một lượt.

Ở mỗi phase:

1. Đọc tài liệu và source liên quan.
2. Xác định đúng phạm vi.
3. Nêu kế hoạch file sẽ thêm/sửa.
4. Nêu rủi ro và dependency.
5. Triển khai một nhóm chức năng nhỏ.
6. Chạy test thực tế.
7. Sửa lỗi do thay đổi gây ra.
8. Chạy lại regression tests.
9. Đánh giá bảo mật và giấy phép liên quan.
10. Cập nhật tài liệu.
11. Báo cáo kết quả và điều kiện còn thiếu.
12. Chỉ tiếp tục phase tiếp theo khi phase hiện tại đạt acceptance criteria.

Nếu thiếu thông tin quyết định, hỏi người dùng trước khi triển khai.

Nếu gặp lỗi môi trường, báo lỗi và cung cấp chẩn đoán; không tự ý thay đổi cấu hình hệ thống nguy hiểm.

Không giả lập kết quả để vượt qua test.

Không tạo hàng loạt file placeholder hoặc module trùng lặp.

Không tự ý commit, push, publish, upload hoặc xóa dữ liệu.

## 29. Bằng chứng bàn giao

Sau mỗi phase, cung cấp:

* Các file đã thêm/sửa.
* Lý do thay đổi.
* Lệnh test thực tế đã chạy.
* Kết quả và exit code.
* Test chưa chạy và nguyên nhân.
* Lỗi còn tồn tại.
* Rủi ro đã xử lý.
* Rủi ro chưa xử lý.
* Dependency và giấy phép mới.
* Cách khởi động.
* Cách rollback.
* Acceptance checklist.

## 30. BẮT ĐẦU NGAY

Chỉ thực hiện Phase 0 trước.

Không vội coding toàn bộ hệ thống.

Khảo sát môi trường và repository thực tế, kiểm tra các yêu cầu hiện có, xác định các rủi ro và khoảng trống kiến trúc, sau đó đưa ra báo cáo audit cùng kế hoạch triển khai theo từng phase.

Nếu có thông tin quyết định chưa thể xác minh bằng source hoặc môi trường, hãy hỏi người dùng bằng các câu hỏi ngắn gọn và cụ thể.

Kết thúc Phase 0 bằng một báo cáo có bằng chứng, danh sách file dự kiến thay đổi, dependency dự kiến và tiêu chí nghiệm thu Phase 1.

Chờ xác nhận trước khi bắt đầu Phase 1 nếu việc chuyển tiếp làm phát sinh thay đổi đáng kể về phạm vi, quyền hoặc dependency.
