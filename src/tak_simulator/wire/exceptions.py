class DecodeError(Exception):
    field: str | None

    def __init__(self, *args, field: str | None = None):
        super().__init__(args)

        self.field = field
