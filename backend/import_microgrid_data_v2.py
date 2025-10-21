"""
导入微网格测试数据 - 只导入CREATE TABLE和INSERT语句
"""
import pymysql
import re

DB_HOST = '10.10.20.10'
DB_PORT = 24406
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_NAME = 'microgrid'

print(f"连接到数据库 {DB_HOST}:{DB_PORT}/{DB_NAME}")

# 连接数据库
conn = pymysql.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset='utf8mb4',
    local_infile=True
)

cursor = conn.cursor()

print("读取SQL文件...")
with open('/data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

print(f"SQL文件大小: {len(sql_content)} 字符")

# 删除注释行
lines = []
for line in sql_content.split('\n'):
    # 删除行尾注释
    if '--' in line:
        # 检查是否在字符串中
        parts = line.split('--')
        if len(parts) > 1:
            line = parts[0]
    line = line.strip()
    if line and not line.startswith('--'):
        lines.append(line)

sql_content = ' '.join(lines)

# 改进的语句分割
statements = []
current = []
paren_count = 0
in_string = False
string_char = None
i = 0

while i < len(sql_content):
    char = sql_content[i]
    
    # 处理字符串
    if not in_string:
        if char in ("'", '"'):
            in_string = True
            string_char = char
        elif char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        elif char == ';' and paren_count == 0:
            current.append(char)
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue
    else:
        if char == string_char:
            # 检查是否是转义的引号
            if i + 1 < len(sql_content) and sql_content[i+1] == string_char:
                current.append(char)
                i += 1
                current.append(sql_content[i])
                i += 1
                continue
            else:
                in_string = False
                string_char = None
    
    current.append(char)
    i += 1

# 添加最后一条语句
if current:
    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)

# 过滤只保留CREATE TABLE和INSERT语句
filtered_statements = []
for stmt in statements:
    stmt_upper = stmt.upper()
    if stmt_upper.startswith('CREATE TABLE') or stmt_upper.startswith('INSERT INTO'):
        filtered_statements.append(stmt)
    elif stmt_upper.startswith('DROP TABLE'):
        # 保留DROP TABLE但将其设为可选
        filtered_statements.append(stmt)

print(f"解析出 {len(statements)} 条语句，过滤后保留 {len(filtered_statements)} 条")

print("\n开始执行SQL语句...")
success_count = 0
error_count = 0
created_tables = []
insert_count = 0

for i, statement in enumerate(filtered_statements, 1):
    try:
        if statement.strip():
            cursor.execute(statement)
            conn.commit()
            success_count += 1
            
            stmt_upper = statement.upper()
            if stmt_upper.startswith('CREATE TABLE'):
                table_match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\S+)', statement, re.IGNORECASE)
                if table_match:
                    table_name = table_match.group(1)
                    created_tables.append(table_name)
                    print(f"  ✅ 创建表: {table_name}")
            elif stmt_upper.startswith('INSERT INTO'):
                insert_count += 1
                if insert_count % 50 == 0:
                    print(f"  已插入 {insert_count} 批数据...")
                    
    except Exception as e:
        error_count += 1
        error_msg = str(e)
        
        # 忽略"表已存在"的错误
        if '1050' in error_msg:  # Table already exists
            stmt_upper = statement.upper()
            if stmt_upper.startswith('CREATE TABLE'):
                table_match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\S+)', statement, re.IGNORECASE)
                if table_match:
                    print(f"  ⚠️  表已存在: {table_match.group(1)}")
        elif '1062' in error_msg:  # Duplicate entry
            pass  # 忽略重复键错误
        else:
            # 打印其他错误（限制数量）
            if error_count <= 10:
                print(f"\n  ❌ 错误 {i}: {error_msg[:150]}")
                print(f"     SQL: {statement[:100]}...")

print(f"\n" + "=" * 80)
print(f"✅ 成功执行: {success_count} 条")
print(f"❌ 失败: {error_count} 条")
print(f"📊 创建表: {len(created_tables)} 个")
print(f"📊 插入数据: {insert_count} 批")

# 查看导入后的表
print("\n" + "=" * 80)
print("导入后的表列表:")
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()
for table in tables:
    table_name = table[0]
    try:
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count} 行")
    except:
        print(f"  - {table_name}: 无法查询")

cursor.close()
conn.close()

print("\n✅ 数据导入完成!")

