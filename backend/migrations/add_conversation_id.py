# 智途校园 - 数据库迁移：为 chat_messages 表添加 conversation_id 字段
import asyncio
import aiomysql

# 数据库配置（与 config.py 保持一致）
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",  # 根据实际配置修改
    "db": "ai_learning_system",
    "charset": "utf8mb4",
}


async def migrate():
    conn = await aiomysql.connect(**DB_CONFIG)
    async with conn.cursor() as cur:
        # 检查字段是否已存在
        await cur.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'chat_messages' AND COLUMN_NAME = 'conversation_id'
        """, (DB_CONFIG["db"],))
        
        if await cur.fetchone():
            print("✓ conversation_id 字段已存在，跳过迁移")
        else:
            # 添加字段
            await cur.execute("""
                ALTER TABLE chat_messages 
                ADD COLUMN conversation_id VARCHAR(36) NULL AFTER user_id,
                ADD INDEX idx_conversation_id (conversation_id),
                ADD INDEX idx_user_conversation (user_id, conversation_id)
            """)
            await conn.commit()
            print("✓ 成功添加 conversation_id 字段及索引")
        
        # 确保 user_id 有索引（加速查询）
        await cur.execute("""
            SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'chat_messages' AND INDEX_NAME = 'idx_user_id'
        """, (DB_CONFIG["db"],))
        if not await cur.fetchone():
            await cur.execute("ALTER TABLE chat_messages ADD INDEX idx_user_id (user_id)")
            await conn.commit()
            print("✓ 添加 user_id 索引")
    
    conn.close()
    print("迁移完成")


if __name__ == "__main__":
    asyncio.run(migrate())
