import re

with open(r'd:\ProjectDepi\job-trends-pipeline\src\serving\dashboard\app.py', encoding='utf-8') as f:
    content = f.read()

# Count occurrences
count = content.count('#a855f7')
print(f'Old gradient color occurrences: {count}')

# Replace the inline style in all h1 page title elements
old_style = (
    "background: linear-gradient(135deg, #a855f7 0%, #ec4899 50%, #00f2fe 100%); "
    "-webkit-background-clip: text; -webkit-text-fill-color: transparent; "
    "font-weight: 800; font-size: 2.8rem; margin-bottom: 0px; "
    "font-family:\\'Outfit\\', sans-serif;"
)
new_style = (
    "font-weight: 800; font-size: 2.2rem; margin-bottom: 0px; "
    "font-family: \\'Inter\\', sans-serif; color: #0f172a; letter-spacing: -0.03em;"
)

content_new = content.replace(old_style, new_style)
replacements = content.count(old_style)
print(f'Exact string replacements: {replacements}')

with open(r'd:\ProjectDepi\job-trends-pipeline\src\serving\dashboard\app.py', 'w', encoding='utf-8') as f:
    f.write(content_new)

print('Done.')
