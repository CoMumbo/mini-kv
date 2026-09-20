class ProtocolError(Exception):
    """Raised when a client sends something we can't parse."""


def parse(line: str) -> tuple[str, list[str]]:
    """Turn 'SET foo bar' into ('SET', ['foo', 'bar'])."""
    parts = line.strip().split()
    if not parts:
        raise ProtocolError("empty command")
    return parts[0].upper(), parts[1:]


def encode(value) -> str:
    """Format a Python value as a wire response (with trailing newline)."""
    if value is None:
        return "(nil)\n"
    if isinstance(value, bool):
        return ("1\n" if value else "0\n")
    if isinstance(value, list):
        return (" ".join(value) if value else "") + "\n"
    return f"{value}\n"