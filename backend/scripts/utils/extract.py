import re
import os

with open('/run/media/mann/HDD/Users/lopez/Software-PA/docs/docs-alfredo/specs/sistema-seguimiento-liberacion-derechos/design-mod.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The core schema is roughly between line 566 and 1900.
# In the actual file it goes until the end of the vw_dashboard_liberacion view.
content = "".join(lines[566:2000])

sql_blocks = re.findall(r'```sql\n(.*?)\n```', content, re.DOTALL)

os.makedirs('/run/media/mann/HDD/Users/lopez/Software-PA/backend/db/migrations', exist_ok=True)
output_path = '/run/media/mann/HDD/Users/lopez/Software-PA/backend/db/migrations/001_init_schema.sql'

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("-- Migración Inicial: Esquema Base y Lógica Geoespacial\n\n")
    # Some constraints might be documented as separate blocks, let's just append them.
    for block in sql_blocks:
        f.write(block + '\n\n')

print(f'Extracted {len(sql_blocks)} SQL blocks to {output_path}')
