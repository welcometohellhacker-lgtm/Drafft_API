class NarrationService:
    def build_script(self, title: str, hook: str, cta_text: str | None = None) -> str:
        parts = [hook, title]
        if cta_text:
            parts.append(cta_text)
        return ". ".join(part for part in parts if part)
