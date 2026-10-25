def collect_tags(new_tag: str, bucket: list[str] | None = None) -> list[str]:
    if bucket is None:
        bucket = []
    bucket.append(new_tag.strip().lower())
    return bucket
