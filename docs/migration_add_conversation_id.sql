USE ai_learning_system;

-- 添加字段（如果已存在会报错，可忽略）
ALTER TABLE chat_messages 
ADD COLUMN `conversation_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '对话分组ID（UUID）' AFTER `user_id`;

-- 生成默认 conversation_id
UPDATE chat_messages 
SET conversation_id = UUID()
WHERE conversation_id IS NULL;

-- 添加索引
ALTER TABLE chat_messages ADD INDEX `idx_conversation_id`(`conversation_id`);
ALTER TABLE chat_messages ADD INDEX `idx_user_conversation`(`user_id`, `conversation_id`);

SELECT '迁移完成' AS status;
SELECT COUNT(DISTINCT conversation_id) AS conversation_count FROM chat_messages;