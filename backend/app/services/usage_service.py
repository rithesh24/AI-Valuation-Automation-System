class UsageService:
    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        raise NotImplementedError

    def get_monthly_usage(self) -> dict:
        raise NotImplementedError
