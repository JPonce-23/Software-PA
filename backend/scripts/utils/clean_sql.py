with open('/run/media/mann/HDD/Users/lopez/Software-PA/backend/db/migrations/001_init_schema.sql', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the exact end of the dashboard view
end_marker = "LEFT JOIN AgrupacionLiberada al ON al.id_tramo_nucleo = v.id_tramo_nucleo;\n"
end_index = content.find(end_marker)

if end_index != -1:
    clean_content = content[:end_index + len(end_marker)]
    with open('/run/media/mann/HDD/Users/lopez/Software-PA/backend/db/migrations/001_init_schema.sql', 'w', encoding='utf-8') as f:
        f.write(clean_content)
    print("Cleaned successfully.")
else:
    print("End marker not found.")
