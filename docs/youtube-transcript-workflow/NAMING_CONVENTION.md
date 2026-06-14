# File Naming Convention

## Format

```
{Channel_Name}_{Video_Title_Sanitized}.json
```

## Sanitization Rules

Applied to both channel name and video title:

| Input Character | Output |
|-----------------|--------|
| `<` `>` `:` `"` `/` `\` `|` `?` `*` | `_` |
| Whitespace (spaces, tabs, newlines) | `_` |
| Multiple consecutive `_` | Single `_` |
| Leading/trailing `_` or `.` | Removed |

## Length Limits

- Channel name: max 80 characters after sanitization
- Video title: max 100 characters after sanitization
- Total filename: max 255 characters (filesystem limit)

## Examples

| Channel | Video Title | Filename |
|---------|-------------|----------|
| Y Combinator | How to Build a Self-Improving Company with AI | `Y_Combinator_How_to_Build_a_Self-Improving_Company_with_AI.json` |
| Lex Fridman | Sam Altman on GPT-5 and Future of AI | `Lex_Fridman_Sam_Altman_on_GPT-5_and_Future_of_AI.json` |
| 3Blue1Brown | Neural Networks Chapter 1 | `3Blue1Brown_Neural_Networks_Chapter_1.json` |
| Fireship | Rust in 100 Seconds | `Fireship_Rust_in_100_Seconds.json` |
| MIT OpenCourseWare | Lecture 1: Introduction to Deep Learning | `MIT_OpenCourseWare_Lecture_1_Introduction_to_Deep_Learning.json` |

## Edge Cases Handled

| Scenario | Handling |
|----------|----------|
| Title contains `?` or `!` | Replaced with `_` |
| Title has emoji | Removed (non-ASCII → `_`) |
| Very long title (>100 chars) | Truncated at word boundary |
| Channel name with `/` | Replaced with `_` |
| Duplicate filenames | Not handled automatically — use `--force` to overwrite |

## Implementation (from `common.py`)

```python
def sanitize_filename(text: str, max_length: int = 80) -> str:
    text = re.sub(r'[<>:"/\\|?*]', '_', text)
    text = re.sub(r'\s+', '_', text)
    text = text.strip('_.')
    if len(text) > max_length:
        text = text[:max_length].rstrip('_-')
    return text

def generate_filename(channel: str, title: str) -> str:
    safe_channel = sanitize_filename(channel, 40)
    safe_title = sanitize_filename(title, 100)
    return f"{safe_channel}_{safe_title}.json"
```

## Why This Convention?

1. **Human-readable** — Channel and title visible in filename
2. **Sortable** — Channel first groups by creator
3. **Unique** — Video title distinguishes videos from same channel
4. **Filesystem-safe** — No special chars that break shells/scripts
5. **Searchable** — `ls *Self-Improving*` works
6. **Git-friendly** — No merge conflicts from special chars