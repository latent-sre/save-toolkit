"""Tag collector module."""


def collect_tags(new_tag: str, bucket: list[str] | None = None) -> list[str]:
    """Collect a new normalized tag into the specified or a new bucket."""
    if bucket is None:
        bucket = []
    bucket.append(new_tag.strip().lower())
    return bucket
