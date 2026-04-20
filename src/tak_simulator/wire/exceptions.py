class CodecError(Exception):
    field: str | None

    def __init__(self, *args, field: str | None = None):
        super().__init__(args)

        self.field = field


class DecodeError(CodecError):
    """Raised when decoding a CoT message fails due to missing required fields.

    Raised for missing required fields: uid, type, how, time, start, stale, lat, lon.
    """

    pass


class EncodeError(CodecError):
    """Raised when encoding a CoT message fails due to missing required fields.

    Raised for missing required fields: uid, type, how, send_time, start_time,
    stale_time, point (with lat/lon).
    """

    pass
