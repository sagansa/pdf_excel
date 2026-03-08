import re

# Read the file
with open('backend/services/report_service.py', 'r') as f:
    content = f.read()

# Replace 5 consecutive lines of coretax_clause assignments with just 1
duplicate_assignment = re.compile(
    r'(    coretax_clause = _coretax_filter_clause\(report_type, \'m\'\)\n){2,}',
    re.MULTILINE
)
content = duplicate_assignment.sub(r'\1', content)

# Write it back
with open('backend/services/report_service.py', 'w') as f:
    f.write(content)
