-- 智途校园 - chat_messages 表迁移（2026-05-19）
-- 新增 conversation_id 字段，用于对话分组
-- 执行前请先备份数据库

USE ai_learning_system;

-- 1. 添加 conversation_id 字段（varchar(36) 兼容UUID格式）
ALTER TABLE chat_messages 
ADD COLUMN IF NOT EXISTS `conversation_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '对话分组ID（UUID），同一组消息共享一个ID' AFTER `user_id`;

-- 2. 为现有数据生成默认 conversation_id（按6小时窗口+用户分组）
--    将距离不超过6小时的同用户消息归为同一对话
SET @batch_size = 1000;
SET @processed = 0;

REPEAT
    -- 为没有 conversation_id 的消息生成 UUID
    UPDATE chat_messages 
    SET conversation_id = (
        SELECT UUID()
    )
    WHERE conversation_id IS NULL
    AND id IN (
        SELECT id FROM (
            SELECT id FROM chat_messages 
            WHERE conversation_id IS NULL 
            LIMIT @batch_size
        ) AS tmp
    );
    
    SET @processed = @processed + @batch_size;
UNTIL ROW_COUNT() = 0 END REPEAT;

-- 3. 添加索引
ALTER TABLE chat_messages 
ADD INDEX IF NOT EXISTS `idx_conversation_id`(`conversation_id` ASC),
ADD INDEX IF NOT EXISTS `idx_user_conversation`(`user_id` ASC, `conversation_id` ASC);

SELECT '迁移完成' AS status;
SELECT COUNT(DISTINCT conversation_id) AS conversation_count FROM chat_messages;
