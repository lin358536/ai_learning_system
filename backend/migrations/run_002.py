import pymysql

conn = pymysql.connect(host='localhost', user='root', password='123456', database='ai_learning_system')
cursor = conn.cursor()

# 查看 users 表当前字段
cursor.execute("DESCRIBE users")
columns = [row[0] for row in cursor.fetchall()]
print(f"users 表当前字段: {columns}")

# 新增 avatar_url 字段
if "avatar_url" not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255) DEFAULT NULL COMMENT '用户头像URL'")
    print("  + 新增字段: avatar_url")
else:
    print("  = avatar_url 字段已存在，跳过")

conn.commit()

# 验证最终结构
cursor.execute("DESCRIBE users")
print("\nusers 表最终字段:")
for row in cursor.fetchall():
    print(f"  {row[0]:20s} {row[1]:30s} {row[2] or 'NULL':8s} {row[3] or ''}")

cursor.close()
conn.close()
print("\n迁移完成!")
