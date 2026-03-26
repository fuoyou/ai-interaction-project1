"""课程知识库分类 ID 与 biz_category.id / 课件 course_id 对齐，师生端共用同一资料池。"""


def normalize_kb_category_id(value) -> str:
    """
    统一为去空白字符串，避免 5 / "5" / " 5 " 与列表、检索不一致。
    空值、null、undefined 等均视为无分类。
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() in ("null", "undefined", "none"):
        return ""
    return s
