import pymysql

conn = pymysql.connect(host='localhost', user='root', password='123456', database='ai_learning_system')
cursor = conn.cursor()

# 查看当前表结构
cursor.execute("DESCRIBE user_profiles")
columns = [row[0] for row in cursor.fetchall()]
print(f"当前字段: {columns}")

# 需要新增的字段
additions = [
    ("grade", "VARCHAR(5) DEFAULT '' COMMENT '年级: 大一/大二/大三/大四'"),
    ("target_industry", "VARCHAR(50) DEFAULT '' COMMENT '意向行业'"),
    ("job_style", "VARCHAR(20) DEFAULT '' COMMENT '求职倾向: 稳定型/进取型/未确定'"),
    ("certificates", "TEXT DEFAULT NULL COMMENT '证书列表(JSON数组)'"),
]

for col_name, col_def in additions:
    if col_name not in columns:
        cursor.execute(f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_def}")
        print(f"  + 新增字段: {col_name}")
    else:
        print(f"  = 字段已存在: {col_name}")

# 修改 education 字段长度
try:
    cursor.execute("ALTER TABLE user_profiles MODIFY COLUMN education VARCHAR(10) DEFAULT '专科' COMMENT '学历: 专科/本科'")
    print("  ~ 修改字段: education → VARCHAR(10)")
except Exception as e:
    print(f"  ! education 修改失败: {e}")

# 删除 graduation_year（如果存在）
if "graduation_year" in columns:
    cursor.execute("ALTER TABLE user_profiles DROP COLUMN graduation_year")
    print("  - 删除字段: graduation_year")
else:
    print("  = graduation_year 不存在，跳过")

conn.commit()

# 验证最终结构
cursor.execute("DESCRIBE user_profiles")
print("\n最终字段:")
for row in cursor.fetchall():
    print(f"  {row[0]:20s} {row[1]:30s} {row[2] or 'NULL':8s} {row[3] or ''}")

cursor.close()
conn.close()
print("\n迁移完成!")
