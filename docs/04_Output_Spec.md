# Output Spec

## Markdown
- File: `output/brief_YYYY-MM-DD.md`
- Sections:
  - Header (Date, Generated, Total Articles, Model)
  - AI Summary
  - All Articles (grouped by category)

## JSON
- File: `output/brief_YYYY-MM-DD.json`
- Fields:
  - `generated_at`
  - `summary`
  - `article_count`
  - `articles[]`
