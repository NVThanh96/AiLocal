from enum import Enum
from typing import List, Dict
from pydantic import BaseModel, Field

class DomainId(str, Enum):
    RESEARCH = "research"
    DESIGN = "design"
    FINANCE = "finance"
    CEO_STRATEGY = "ceo_strategy"
    MARKETING = "marketing"
    MEDIA = "media"
    TRANSLATION = "translation"
    BROWSER_AUTOMATION = "browser_automation"

class DomainCapabilityManifest(BaseModel):
    domain_id: DomainId
    name: str
    description: str
    version: str = "1.0.0"
    required_permissions: List[str]
    tools: List[str]
    acceptance_criteria: List[str]
    risk_assessment: str  # LOW, MEDIUM, HIGH
    license_type: str  # MIT, Apache-2.0, BSD

CORE_DOMAIN_MANIFESTS: Dict[DomainId, DomainCapabilityManifest] = {
    DomainId.RESEARCH: DomainCapabilityManifest(
        domain_id=DomainId.RESEARCH,
        name="Research & Technical Discovery",
        description="Deep source retrieval, academic/factual synthesis, cross-verification, and citation tracking.",
        required_permissions=["workspace.read", "network.fetch"],
        tools=["academic_search", "citation_extractor", "provenance_validator"],
        acceptance_criteria=[
            "Source claims must cite verified URL or file hash",
            "Zero ungrounded speculation; clear distinction between fact and inference"
        ],
        risk_assessment="LOW",
        license_type="MIT"
    ),
    DomainId.DESIGN: DomainCapabilityManifest(
        domain_id=DomainId.DESIGN,
        name="Design & UI Architecture",
        description="Tailwind design tokens, component architecture, responsive layouts, and WCAG accessibility audits.",
        required_permissions=["workspace.read", "workspace.write"],
        tools=["tailwind_token_generator", "layout_specifier", "a11y_contrast_checker"],
        acceptance_criteria=[
            "Design tokens conform to WCAG 2.1 AA accessibility contrast rules",
            "Responsive layout specs cover both mobile (9:16) and desktop (16:9)"
        ],
        risk_assessment="LOW",
        license_type="MIT"
    ),
    DomainId.FINANCE: DomainCapabilityManifest(
        domain_id=DomainId.FINANCE,
        name="Finance & Cost Economics",
        description="Local double-entry ledger calculation, ROI modeling, unit economics analysis, and zero cloud cost governance.",
        required_permissions=["workspace.read"],
        tools=["ledger_calculator", "roi_estimator", "unit_economics_audit"],
        acceptance_criteria=[
            "Financial computations pass double-entry verification check",
            "Zero external financial data transmission"
        ],
        risk_assessment="MEDIUM",
        license_type="Apache-2.0"
    ),
    DomainId.CEO_STRATEGY: DomainCapabilityManifest(
        domain_id=DomainId.CEO_STRATEGY,
        name="Executive Strategy & Governance",
        description="OKR breakdown, decision matrices, SWOT/risk evaluations, and milestone roadmapping.",
        required_permissions=["workspace.read"],
        tools=["okr_decomposer", "decision_matrix", "swot_risk_analyzer"],
        acceptance_criteria=[
            "Strategies map directly to actionable acceptance criteria",
            "Risk matrix identifies clear mitigation and rollback triggers"
        ],
        risk_assessment="LOW",
        license_type="MIT"
    ),
    DomainId.MARKETING: DomainCapabilityManifest(
        domain_id=DomainId.MARKETING,
        name="Affiliate & Growth Marketing",
        description="Viral hook generation, audience persona alignment, SEO keyword density audits, and AI buzzword purging.",
        required_permissions=["workspace.read", "workspace.write"],
        tools=["hook_synthesizer", "seo_keyword_density", "audience_persona_adapter"],
        acceptance_criteria=[
            "Hooks must achieve retention hook benchmarks",
            "Strict auto-block of banned AI words (tapestry, delve, utilize, testament)"
        ],
        risk_assessment="LOW",
        license_type="MIT"
    ),
    DomainId.MEDIA: DomainCapabilityManifest(
        domain_id=DomainId.MEDIA,
        name="Media & Video Production",
        description="Short-form video formatting (1080x1920, 60fps), ComfyUI workflow manifests, Whisper SRT subtitling, and dynamic ducking.",
        required_permissions=["workspace.read", "workspace.write", "media.generate"],
        tools=["comfyui_pipeline_builder", "vertical_reframe_9_16", "whisper_srt_generator", "ffmpeg_encoder"],
        acceptance_criteria=[
            "Output specs adhere to 1080x1920 60fps H.264/AAC standard",
            "Zero silent audio tracks and zero out-of-sync captions"
        ],
        risk_assessment="HIGH",
        license_type="MIT"
    ),
    DomainId.TRANSLATION: DomainCapabilityManifest(
        domain_id=DomainId.TRANSLATION,
        name="Localization & Cultural Nuance",
        description="Multi-language localization, glossary alignment, cultural idiom adaptation, and back-translation verification.",
        required_permissions=["workspace.read"],
        tools=["glossary_aligner", "cultural_nuance_verifier", "bidirectional_backtranslator"],
        acceptance_criteria=[
            "Technical terms match project terminology glossary 100%",
            "Back-translation score above 0.95 semantic similarity"
        ],
        risk_assessment="LOW",
        license_type="MIT"
    ),
    DomainId.BROWSER_AUTOMATION: DomainCapabilityManifest(
        domain_id=DomainId.BROWSER_AUTOMATION,
        name="Advanced Browser Automation",
        description="Headless Playwright workflows, visual regression snapshot capture, and anti-bot/credential safe interaction.",
        required_permissions=["workspace.read", "browser.navigate", "browser.interact"],
        tools=["playwright_script_generator", "dom_selector_audit", "snapshot_verifier"],
        acceptance_criteria=[
            "Headless browser runs in strict isolated temporary profile",
            "Zero credential or session cookie leakage"
        ],
        risk_assessment="HIGH",
        license_type="Apache-2.0"
    )
}
