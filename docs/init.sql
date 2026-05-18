-- ============================================================
-- 智途校园 — 数据库初始化脚本
-- 数据库: ai_learning_system
-- MySQL 8.0+
-- 字符集: utf8mb4
-- ============================================================

-- 如果数据库已存在则先删除（谨慎使用）
-- DROP DATABASE IF EXISTS ai_learning_system;
-- CREATE DATABASE ai_learning_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE ai_learning_system;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ==================== 用户表 ====================
CREATE TABLE IF NOT EXISTS users (
    id              BIGINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    username        VARCHAR(50)        NOT NULL,
    password_hash   VARCHAR(255)       NOT NULL,
    email           VARCHAR(100)       NULL         DEFAULT NULL,
    name            VARCHAR(50)        NULL         DEFAULT NULL,
    student_id      VARCHAR(20)        NULL         DEFAULT NULL,
    created_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_username (username),
    UNIQUE KEY uk_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户主表';

-- ==================== 用户画像表 ====================
CREATE TABLE IF NOT EXISTS user_profiles (
    id              BIGINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         BIGINT UNSIGNED    NOT NULL,
    major           VARCHAR(100)       NOT NULL      DEFAULT '',
    target_job      VARCHAR(100)       NOT NULL      DEFAULT '',
    skills          JSON               NULL         DEFAULT NULL COMMENT '技能列表，如["Python","MySQL"]',
    graduation_year INT                NULL         DEFAULT NULL COMMENT '预计毕业年份',
    education       VARCHAR(20)        NOT NULL      DEFAULT '大专' COMMENT '中专/大专/本科/硕士',
    upgrade_intent  TINYINT(1)         NOT NULL      DEFAULT 0 COMMENT '是否有升本/考研意向',
    created_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_profiles_user_id (user_id),
    CONSTRAINT fk_user_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户画像表';

-- ==================== 学习规划表 ====================
CREATE TABLE IF NOT EXISTS learning_plans (
    id              BIGINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         BIGINT UNSIGNED    NOT NULL,
    title           VARCHAR(200)       NOT NULL,
    content         JSON               NOT NULL      COMMENT '规划详情，含stages/projects/resources等',
    status          ENUM('draft', 'confirmed', 'archived') NOT NULL DEFAULT 'draft' COMMENT '草稿/已确认/已归档',
    created_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_learning_plans_user_id (user_id),
    CONSTRAINT fk_learning_plans_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学习规划表';

-- ==================== 每日任务表 ====================
CREATE TABLE IF NOT EXISTS daily_tasks (
    id              BIGINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         BIGINT UNSIGNED    NOT NULL,
    plan_id         BIGINT UNSIGNED    NULL         DEFAULT NULL COMMENT '关联规划，可独立于规划存在',
    content         VARCHAR(500)       NOT NULL,
    status          ENUM('pending', 'completed', 'skipped') NOT NULL DEFAULT 'pending',
    task_date       DATE               NOT NULL,
    completed_at    DATETIME           NULL         DEFAULT NULL,
    created_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_daily_tasks_user_date (user_id, task_date),
    KEY idx_daily_tasks_plan_id (plan_id),
    CONSTRAINT fk_daily_tasks_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_daily_tasks_plan FOREIGN KEY (plan_id) REFERENCES learning_plans (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日任务表';

-- ==================== 简历表 ====================
CREATE TABLE IF NOT EXISTS resumes (
    id              BIGINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         BIGINT UNSIGNED    NOT NULL,
    title           VARCHAR(200)       NOT NULL      DEFAULT '我的简历',
    content         JSON               NOT NULL      COMMENT '简历结构化数据，含basic/skills/experience/summary等',
    created_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_resumes_user_id (user_id),
    CONSTRAINT fk_resumes_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历表';

-- ==================== 积分记录表 ====================
CREATE TABLE IF NOT EXISTS points (
    id              BIGINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         BIGINT UNSIGNED    NOT NULL,
    amount          INT                NOT NULL      DEFAULT 0 COMMENT '积分变动值，正数加分负数扣分',
    reason          VARCHAR(500)       NOT NULL      COMMENT '积分变动原因',
    source          VARCHAR(50)        NOT NULL      DEFAULT 'other' COMMENT '来源: task/plan/resume/sign_in/other',
    created_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_points_user_id (user_id),
    CONSTRAINT fk_points_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='积分记录表';

-- ==================== 对话历史表 ====================
CREATE TABLE IF NOT EXISTS chat_messages (
    id              BIGINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id         BIGINT UNSIGNED    NOT NULL,
    role            ENUM('user', 'assistant') NOT NULL,
    content         TEXT               NOT NULL,
    intent          VARCHAR(50)        NULL         DEFAULT NULL COMMENT '使用的工具key，如generate_plan',
    confirm_id      VARCHAR(36)        NULL         DEFAULT NULL COMMENT '待确认项UUID',
    confirm_data    JSON               NULL         DEFAULT NULL COMMENT '确认用的临时数据（如规划的草稿）',
    created_at      DATETIME           NULL         DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_chat_messages_user_created (user_id, created_at DESC),
    KEY idx_chat_messages_confirm_id (confirm_id),
    CONSTRAINT fk_chat_messages_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史表';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 初始数据（可选）
-- ============================================================

-- 积分来源枚举说明（供代码使用，不建表）:
-- task      - 完成每日任务      +10
-- plan      - 创建学习规划      +20
-- resume    - 生成简历          +15
-- sign_in   - 每日签到          +5
-- other     - 其他              动态
