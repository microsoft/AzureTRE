def parse_bool(val: str) -> bool:
    """Convert a string representation of a boolean to a bool."""
    val = val.lower()
    if val in ('true', 't', 'yes', 'y', 'on', '1'):
        return True
    elif val in ('false', 'f', 'no', 'n', 'off', '0'):
        return False
    raise ValueError(f"Invalid boolean value: {val}")
