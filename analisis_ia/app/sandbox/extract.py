import re


def extract_python_code(markdown_text: str) -> list[str]:
    pattern = r"```python\s*(.*?)```"
    return [block.strip() for block in re.findall(pattern, markdown_text, re.DOTALL)]
