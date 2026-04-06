path = r'd:\Programing\OVOSHI\backend\vkbot\views.py'
with open(path, encoding='utf-8') as f:
    text = f.read()
start = text.find('def _parse_age_input(raw: str) -> int | None | object:')
end = text.find('\ndef _apply_profile_field', start)
if start == -1 or end == -1:
    raise SystemExit(f'markers fail start={start} end={end}')
replacement = """def _parse_age_input(raw: str) -> tuple[str, int | None]:
    \"\"\"('clear', None) | ('bad', None) | ('ok', возраст).\"\"\"
    s = (raw or '').strip()
    if s in ('-', '\u2014'):
        return ('clear', None)
    try:
        v = int(s)
    except ValueError:
        return ('bad', None)
    if 5 <= v <= 120:
        return ('ok', v)
    return ('bad', None)
"""
text = text[:start] + replacement + text[end:]
with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('ok')
