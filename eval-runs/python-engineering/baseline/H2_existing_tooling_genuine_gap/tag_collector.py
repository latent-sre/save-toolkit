def collect_tags(new_tag: str, bucket: list[str] | None = None) -> list[str]:
    if not isinstance(new_tag, str):
        raise TypeError(f"new_tag must be a str, got {type(new_tag).__name__}")
    if bucket is None:
        bucket = []
    elif not isinstance(bucket, list):
        raise TypeError(f"bucket must be a list, got {type(bucket).__name__}")
    bucket.append(new_tag.strip().lower())
    return bucket
