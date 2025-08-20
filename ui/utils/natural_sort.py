import re

def natural_sort_key(text: str):
    """返回用于自然排序的键：按字母不区分大小写，数字按数值比较。
    例如：['a1', 'a2', 'a10'] -> 自然顺序
    """
    s = text or ""
    parts = re.split(r"(\d+)", s)
    key = []
    for part in parts:
        if part.isdigit():
            key.append((1, int(part)))
        else:
            key.append((0, part.lower()))
    return tuple(key)



