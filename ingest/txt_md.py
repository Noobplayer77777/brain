def parse_txt(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    return [{"page_no": 1, "text": text}]
