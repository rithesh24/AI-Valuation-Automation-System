class PromptBuilder:
    def build_prompt(self, extracted_data: dict, easr_data: dict | None) -> str:
        raise NotImplementedError
