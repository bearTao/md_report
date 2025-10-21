"""
导入微网格测试数据
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
    charset='utf8mb4'
)

cursor = conn.cursor()

print("读取SQL文件...")
with open('/data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

print(f"SQL文件大小: {len(sql_content)} 字符")

# 删除注释和空行
lines = sql_content.split('\n')
clean_lines = []
for line in lines:
    # 移除行内注释
    if '--' in line:
        line = line[:line.index('--')]
    line = line.strip()
    if line:
        clean_lines.append(line)

sql_content = '\n'.join(clean_lines)

# 使用更智能的方式分割SQL语句
# 寻找完整的语句（以;结尾，但不是在字符串内）
statements = []
current_statement = []
in_string = False
string_char = None

for char in sql_content:
    if not in_string:
        if char in ('"', "'"):
            in_string = True
            string_char = char
        elif char == ';':
            current_statement.append(char)
            stmt = ''.join(current_statement).strip()
            if stmt:
                statements.append(stmt)
            current_statement = []
            continue
    else:
        if char == string_char:
            in_string = False
            string_char = None
    
    current_statement.append(char)

# 添加最后一条语句（如果有）
if current_statement:
    stmt = ''.join(current_statement).strip()
    if stmt:
        statements.append(stmt)

print(f"解析出 {len(statements)} 条SQL语句")

print("\n开始执行SQL语句...")
success_count = 0
error_count = 0
error_details = []

for i, statement in enumerate(statements, 1):
    try:
        if statement.strip():
            cursor.execute(statement)
            conn.commit()
            success_count += 1
            
            # 显示进度
            if i % 100 == 0:
                print(f"  已执行 {i}/{len(statements)} 条语句 (成功: {success_count}, 失败: {error_count})")
            
            # 显示CREATE TABLE
            if statement.upper().startswith('CREATE TABLE'):
                table_match = re.search(r'CREATE TABLE\s+(\S+)', statement, re.IGNORECASE)
                if table_match:
                    print(f"  ✅ 创建表: {table_match.group(1)}")
                    
    except Exception as e:
        error_count += 1
        error_msg = str(e)
        
        # 忽略"表已存在"的错误
        if '1050' not in error_msg:  # 1050 = Table already exists
            if len(error_details) < 10:  # 只保留前10个错误
                error_details.append({
                    'index': i,
                    'error': error_msg[:200],
                    'statement': statement[:100]
                })

print(f"\n" + "=" * 80)
print(f"✅ 成功执行: {success_count} 条")
print(f"❌ 失败: {error_count} 条")

if error_details:
    print(f"\n前{len(error_details)}个错误详情:")
    for detail in error_details:
        print(f"\n  语句 {detail['index']}:")
        print(f"    SQL: {detail['statement']}...")
        print(f"    错误: {detail['error']}")

# 查看导入后的表
print("\n" + "=" * 80)
print("导入后的表列表:")
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
    count = cursor.fetchone()[0]
    print(f"  - {table[0]}: {count} 行")

cursor.close()
conn.close()

print("\n✅ 数据导入完成!")

