def collect_tags(new_tag: str, bucket: list[str] | None = None) -> list[str]:
    if not isinstance(new_tag, str):
        raise TypeError(f"new_tag must be a str, got {type(new_tag).__name__}")
    if bucket is None:
        target_bucket: list[str] = []
    elif isinstance(bucket, list):
        target_bucket = bucket
    else:
        raise TypeError(f"bucket must be a list or None, got {type(bucket).__name__}")
    target_bucket.append(new_tag.strip().lower())
    return target_bucket
