-- 智途校园 - user_profiles 表迁移（2026-04-22）
-- 新增字段适配全专业用户画像

USE ai_learning_system;

-- 1. 新增基础信息字段
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS grade VARCHAR(5) DEFAULT '' COMMENT '年级: 大一/大二/大三/大四';

-- 2. 新增职业方向字段
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS target_industry VARCHAR(50) DEFAULT '' COMMENT '意向行业';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS job_style VARCHAR(20) DEFAULT '' COMMENT '求职倾向: 稳定型/进取型/未确定';

-- 3. 新增能力画像字段
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS certificates TEXT DEFAULT NULL COMMENT '证书列表(JSON数组)';

-- 4. 修改 education 字段类型（缩小到10字符）
ALTER TABLE user_profiles MODIFY COLUMN education VARCHAR(10) DEFAULT '专科' COMMENT '学历: 专科/本科';

-- 5. 修改 upgrade_intent 字段类型（Integer → TINYINT(1) 即 Boolean）
ALTER TABLE user_profiles MODIFY COLUMN upgrade_intent TINYINT(1) DEFAULT 0 COMMENT '是否有升学意愿';

-- 6. 删除 graduation_year 字段（不再需要）
ALTER TABLE user_profiles DROP COLUMN IF EXISTS graduation_year;

SELECT '迁移完成' AS status;
