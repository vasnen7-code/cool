-- =====================================================================
-- W GAME - FULL DATABASE SCHEMA (MySQL 8+)
-- Import this file completely before running the application.
-- Uses InnoDB + utf8mb4 everywhere for full unicode + FK + transaction support.
-- =====================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `wgame` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `wgame`;

-- ---------------------------------------------------------------------
-- USERS & AUTH
-- ---------------------------------------------------------------------
CREATE TABLE `users` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(20) NOT NULL,
  `telegram_id` BIGINT UNSIGNED NULL COMMENT 'Telegram user id, used for OTP verification via the bot',
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('user','admin') NOT NULL DEFAULT 'user',
  `is_banned` TINYINT(1) NOT NULL DEFAULT 0,
  `ban_reason` VARCHAR(255) NULL,
  `w_balance` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `gems` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `crowns` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `current_world_id` BIGINT UNSIGNED NULL,
  `active_character_id` BIGINT UNSIGNED NULL,
  `active_animal_id` BIGINT UNSIGNED NULL,
  `rebirth_count` INT UNSIGNED NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login_at` DATETIME NULL,
  `last_collect_at` DATETIME NULL COMMENT 'last timestamp auto-production was calculated from',
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `uq_users_telegram_id` (`telegram_id`),
  INDEX `idx_users_role` (`role`),
  INDEX `idx_users_banned` (`is_banned`)
) ENGINE=InnoDB;

-- رموز التحقق (OTP) المُرسلة عبر بوت تيليجرام، تُستخدم للتسجيل واستعادة كلمة المرور
CREATE TABLE `otp_codes` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `telegram_id` BIGINT UNSIGNED NOT NULL,
  `purpose` ENUM('register','reset_password') NOT NULL,
  `code` CHAR(5) NOT NULL,
  `used` TINYINT(1) NOT NULL DEFAULT 0,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_otp_telegram` (`telegram_id`,`purpose`,`used`,`expires_at`)
) ENGINE=InnoDB;

CREATE TABLE `remember_tokens` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `selector` VARCHAR(24) NOT NULL,
  `token_hash` VARCHAR(255) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_selector` (`selector`),
  CONSTRAINT `fk_remember_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `password_resets` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `token_hash` VARCHAR(255) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `used` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_reset_user` (`user_id`),
  CONSTRAINT `fk_reset_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- BUILDINGS / UPGRADES (Head, Skull, Robot, Ghost, Wizard, Factory, Castle, Space Station, Black Hole)
-- production_type:
--   click_bonus  -> adds to the W gained per manual click (e.g. Head)
--   auto_second  -> produces W automatically every second on its own, independent stream (Skull, Robot, ...)
-- ---------------------------------------------------------------------
CREATE TABLE `buildings_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `description` VARCHAR(255) NULL,
  `production_type` ENUM('click_bonus','auto_second') NOT NULL,
  `base_price` DECIMAL(38,2) NOT NULL,
  `price_growth` DECIMAL(6,4) NOT NULL DEFAULT 1.15 COMMENT 'price multiplier per level',
  `base_production` DECIMAL(38,4) NOT NULL COMMENT 'W produced per level (click bonus or per-second)',
  `image` VARCHAR(255) NULL,
  `unlock_world_id` BIGINT UNSIGNED NULL,
  `sort_order` INT NOT NULL DEFAULT 0,
  UNIQUE KEY `uq_building_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_buildings` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `building_id` BIGINT UNSIGNED NOT NULL,
  `level` INT UNSIGNED NOT NULL DEFAULT 0,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_user_building` (`user_id`,`building_id`),
  CONSTRAINT `fk_ub_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ub_building` FOREIGN KEY (`building_id`) REFERENCES `buildings_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- GEMS: chance config (used on every collection event: click / robot tick / auto-click tick / skull tick)
-- ---------------------------------------------------------------------
CREATE TABLE `gem_drop_rules` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `source` ENUM('click','robot','auto_click','skull','other_auto') NOT NULL,
  `drop_chance_percent` DECIMAL(6,3) NOT NULL DEFAULT 1.000,
  `min_amount` INT UNSIGNED NOT NULL DEFAULT 1,
  `max_amount` INT UNSIGNED NOT NULL DEFAULT 3,
  UNIQUE KEY `uq_gem_source` (`source`)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- SHOP (all temporary boosts only, no permanent multipliers)
-- ---------------------------------------------------------------------
CREATE TABLE `shop_items` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `description` VARCHAR(255) NULL,
  `effect_type` ENUM('multiplier_x2','multiplier_x5','auto_click','production_speed','luck_boost','discount','critical_boost') NOT NULL,
  `effect_value` DECIMAL(10,4) NOT NULL,
  `duration_seconds` INT UNSIGNED NOT NULL,
  `price_w` DECIMAL(38,2) NULL,
  `price_gems` BIGINT UNSIGNED NULL,
  `image` VARCHAR(255) NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY `uq_shop_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_active_boosts` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `shop_item_id` BIGINT UNSIGNED NOT NULL,
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` DATETIME NOT NULL,
  INDEX `idx_boost_user_active` (`user_id`,`expires_at`),
  CONSTRAINT `fk_boost_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_boost_item` FOREIGN KEY (`shop_item_id`) REFERENCES `shop_items`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- BOXES (Wooden, Silver, Golden, Diamond, Legendary, Celestial)
-- ---------------------------------------------------------------------
CREATE TABLE `boxes_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `tier` TINYINT UNSIGNED NOT NULL COMMENT '1=Wooden ... 6=Celestial',
  `price_w` DECIMAL(38,2) NULL,
  `price_gems` BIGINT UNSIGNED NULL,
  `image` VARCHAR(255) NULL,
  UNIQUE KEY `uq_box_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `box_rewards` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `box_id` BIGINT UNSIGNED NOT NULL,
  `reward_type` ENUM('w','gems','crown','character','animal','shop_item') NOT NULL,
  `reward_ref_id` BIGINT UNSIGNED NULL COMMENT 'FK depending on reward_type (character/animal/shop item id)',
  `min_amount` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `max_amount` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `weight` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT 'higher = more likely',
  CONSTRAINT `fk_boxreward_box` FOREIGN KEY (`box_id`) REFERENCES `boxes_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `user_box_openings` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `box_id` BIGINT UNSIGNED NOT NULL,
  `reward_type` VARCHAR(30) NOT NULL,
  `amount` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `opened_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_opening_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_opening_box` FOREIGN KEY (`box_id`) REFERENCES `boxes_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- CHARACTERS & ANIMALS
-- ---------------------------------------------------------------------
CREATE TABLE `characters_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `skill_description` VARCHAR(255) NULL,
  `skill_type` ENUM('click_multiplier','auto_multiplier','gem_luck','critical_boost','discount') NOT NULL,
  `skill_value` DECIMAL(10,4) NOT NULL,
  `image` VARCHAR(255) NULL,
  `price_w` DECIMAL(38,2) NULL,
  `price_gems` BIGINT UNSIGNED NULL,
  UNIQUE KEY `uq_character_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_characters` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `character_id` BIGINT UNSIGNED NOT NULL,
  `unlocked_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_user_character` (`user_id`,`character_id`),
  CONSTRAINT `fk_uc_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_uc_character` FOREIGN KEY (`character_id`) REFERENCES `characters_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `animals_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `bonus_description` VARCHAR(255) NULL,
  `bonus_type` ENUM('click_multiplier','auto_multiplier','gem_luck','critical_boost') NOT NULL,
  `bonus_value` DECIMAL(10,4) NOT NULL,
  `image` VARCHAR(255) NULL,
  `price_w` DECIMAL(38,2) NULL,
  `price_gems` BIGINT UNSIGNED NULL,
  UNIQUE KEY `uq_animal_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_animals` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `animal_id` BIGINT UNSIGNED NOT NULL,
  `unlocked_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_user_animal` (`user_id`,`animal_id`),
  CONSTRAINT `fk_ua_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ua_animal` FOREIGN KEY (`animal_id`) REFERENCES `animals_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- WORLDS
-- ---------------------------------------------------------------------
CREATE TABLE `worlds_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `unlock_w_required` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `image` VARCHAR(255) NULL,
  `sort_order` INT NOT NULL DEFAULT 0,
  UNIQUE KEY `uq_world_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_worlds` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `world_id` BIGINT UNSIGNED NOT NULL,
  `unlocked_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_user_world` (`user_id`,`world_id`),
  CONSTRAINT `fk_uw_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_uw_world` FOREIGN KEY (`world_id`) REFERENCES `worlds_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

ALTER TABLE `users` ADD CONSTRAINT `fk_user_current_world` FOREIGN KEY (`current_world_id`) REFERENCES `worlds_catalog`(`id`) ON DELETE SET NULL;
ALTER TABLE `users` ADD CONSTRAINT `fk_user_active_character` FOREIGN KEY (`active_character_id`) REFERENCES `characters_catalog`(`id`) ON DELETE SET NULL;
ALTER TABLE `users` ADD CONSTRAINT `fk_user_active_animal` FOREIGN KEY (`active_animal_id`) REFERENCES `animals_catalog`(`id`) ON DELETE SET NULL;

-- ---------------------------------------------------------------------
-- BOSSES
-- ---------------------------------------------------------------------
CREATE TABLE `bosses_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `world_id` BIGINT UNSIGNED NULL,
  `max_health` BIGINT UNSIGNED NOT NULL,
  `spawn_interval_seconds` INT UNSIGNED NOT NULL DEFAULT 3600,
  `fight_duration_seconds` INT UNSIGNED NOT NULL DEFAULT 300,
  `reward_w` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `reward_gems` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `image` VARCHAR(255) NULL,
  UNIQUE KEY `uq_boss_key` (`key_name`),
  CONSTRAINT `fk_boss_world` FOREIGN KEY (`world_id`) REFERENCES `worlds_catalog`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `boss_spawns` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `boss_id` BIGINT UNSIGNED NOT NULL,
  `current_health` BIGINT UNSIGNED NOT NULL,
  `spawned_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `expires_at` DATETIME NOT NULL,
  `defeated_at` DATETIME NULL,
  CONSTRAINT `fk_spawn_boss` FOREIGN KEY (`boss_id`) REFERENCES `bosses_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `boss_damage_log` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `spawn_id` BIGINT UNSIGNED NOT NULL,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `damage` BIGINT UNSIGNED NOT NULL,
  `dealt_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_boss_damage_spawn_user` (`spawn_id`,`user_id`),
  CONSTRAINT `fk_damage_spawn` FOREIGN KEY (`spawn_id`) REFERENCES `boss_spawns`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_damage_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- QUESTS & ACHIEVEMENTS
-- ---------------------------------------------------------------------
CREATE TABLE `quests_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `title_ar` VARCHAR(150) NOT NULL,
  `description` VARCHAR(255) NULL,
  `type` ENUM('daily','weekly','main') NOT NULL,
  `goal_type` ENUM('clicks','w_earned','upgrades_bought','boxes_opened','bosses_defeated') NOT NULL,
  `goal_amount` BIGINT UNSIGNED NOT NULL,
  `reward_w` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `reward_gems` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `reward_crown` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY `uq_quest_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_quests` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `quest_id` BIGINT UNSIGNED NOT NULL,
  `progress` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `is_completed` TINYINT(1) NOT NULL DEFAULT 0,
  `completed_at` DATETIME NULL,
  `period_start` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_user_quest_period` (`user_id`,`quest_id`,`period_start`),
  CONSTRAINT `fk_uq_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_uq_quest` FOREIGN KEY (`quest_id`) REFERENCES `quests_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `achievements_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `title_ar` VARCHAR(150) NOT NULL,
  `description` VARCHAR(255) NULL,
  `goal_type` ENUM('clicks','w_earned','upgrades_bought','boxes_opened','bosses_defeated','rebirths') NOT NULL,
  `goal_amount` BIGINT UNSIGNED NOT NULL,
  `reward_w` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `reward_gems` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  UNIQUE KEY `uq_achievement_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_achievements` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `achievement_id` BIGINT UNSIGNED NOT NULL,
  `progress` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `is_completed` TINYINT(1) NOT NULL DEFAULT 0,
  `completed_at` DATETIME NULL,
  UNIQUE KEY `uq_user_achievement` (`user_id`,`achievement_id`),
  CONSTRAINT `fk_uac_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_uac_achievement` FOREIGN KEY (`achievement_id`) REFERENCES `achievements_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- WHEEL OF FORTUNE
-- ---------------------------------------------------------------------
CREATE TABLE `wheel_prizes` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `label_ar` VARCHAR(100) NOT NULL,
  `prize_type` ENUM('w','gems','crown','shop_item') NOT NULL,
  `min_amount` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `max_amount` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `weight` INT UNSIGNED NOT NULL DEFAULT 1,
  `image` VARCHAR(255) NULL,
  UNIQUE KEY `uq_wheel_key` (`key_name`)
) ENGINE=InnoDB;

CREATE TABLE `user_wheel_spins` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `prize_id` BIGINT UNSIGNED NOT NULL,
  `amount` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `spun_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `next_spin_at` DATETIME NOT NULL,
  CONSTRAINT `fk_spin_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_spin_prize` FOREIGN KEY (`prize_id`) REFERENCES `wheel_prizes`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- EVENTS
-- ---------------------------------------------------------------------
CREATE TABLE `events_catalog` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `key_name` VARCHAR(50) NOT NULL,
  `name_ar` VARCHAR(100) NOT NULL,
  `type` ENUM('w_rain','golden_ghost','meteor','secret_portal','weekly','seasonal') NOT NULL,
  `starts_at` DATETIME NOT NULL,
  `ends_at` DATETIME NOT NULL,
  `config_json` JSON NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_by_admin_id` BIGINT UNSIGNED NULL,
  UNIQUE KEY `uq_event_key` (`key_name`),
  CONSTRAINT `fk_event_admin` FOREIGN KEY (`created_by_admin_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE `user_event_participation` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `event_id` BIGINT UNSIGNED NOT NULL,
  `reward_claimed` TINYINT(1) NOT NULL DEFAULT 0,
  `claimed_at` DATETIME NULL,
  UNIQUE KEY `uq_user_event` (`user_id`,`event_id`),
  CONSTRAINT `fk_uep_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_uep_event` FOREIGN KEY (`event_id`) REFERENCES `events_catalog`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- STATS
-- ---------------------------------------------------------------------
CREATE TABLE `user_stats` (
  `user_id` BIGINT UNSIGNED PRIMARY KEY,
  `total_clicks` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `total_w_earned` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `total_w_from_click` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `total_w_from_robot` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `total_w_from_auto_click` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `total_w_from_skull` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `total_gems_earned` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `total_playtime_seconds` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `total_upgrades_bought` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `total_rebirths` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `total_boxes_opened` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `total_bosses_defeated` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  CONSTRAINT `fk_stats_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- NOTIFICATIONS & GIFTS
-- ---------------------------------------------------------------------
CREATE TABLE `notifications` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT UNSIGNED NULL COMMENT 'NULL = broadcast to all users',
  `title` VARCHAR(150) NOT NULL,
  `message` VARCHAR(500) NOT NULL,
  `is_read` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_notif_user` (`user_id`),
  CONSTRAINT `fk_notif_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `gifts` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `title` VARCHAR(150) NOT NULL,
  `message` VARCHAR(500) NULL,
  `reward_w` DECIMAL(38,2) NOT NULL DEFAULT 0,
  `reward_gems` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `reward_crown` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `target` ENUM('all','specific') NOT NULL DEFAULT 'all',
  `target_user_id` BIGINT UNSIGNED NULL,
  `sent_by_admin_id` BIGINT UNSIGNED NOT NULL,
  `sent_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_gift_target_user` FOREIGN KEY (`target_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_gift_admin` FOREIGN KEY (`sent_by_admin_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `user_gift_claims` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `gift_id` BIGINT UNSIGNED NOT NULL,
  `user_id` BIGINT UNSIGNED NOT NULL,
  `claimed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_gift_user` (`gift_id`,`user_id`),
  CONSTRAINT `fk_claim_gift` FOREIGN KEY (`gift_id`) REFERENCES `gifts`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_claim_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- ADMIN LOGS, SETTINGS, BACKUPS
-- ---------------------------------------------------------------------
CREATE TABLE `admin_logs` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `admin_id` BIGINT UNSIGNED NOT NULL,
  `action` VARCHAR(100) NOT NULL,
  `target_type` VARCHAR(50) NULL,
  `target_id` BIGINT UNSIGNED NULL,
  `details` VARCHAR(500) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_adminlog_admin` (`admin_id`),
  CONSTRAINT `fk_adminlog_admin` FOREIGN KEY (`admin_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE `game_settings` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `setting_key` VARCHAR(100) NOT NULL,
  `setting_value` VARCHAR(500) NOT NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_setting_key` (`setting_key`)
) ENGINE=InnoDB;

CREATE TABLE `backups` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `filename` VARCHAR(255) NOT NULL,
  `created_by_admin_id` BIGINT UNSIGNED NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `fk_backup_admin` FOREIGN KEY (`created_by_admin_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- SEED DATA (Phase 1 essentials)
-- =====================================================================

-- Default admin account (username: Hasnen / password: Hasnen1@@1)
-- Password hash generated with Python's werkzeug generate_password_hash (pbkdf2:sha256)
-- IMPORTANT: change this password after first login in production.
INSERT INTO `users` (`username`,`password_hash`,`role`,`w_balance`,`gems`,`crowns`,`last_collect_at`)
VALUES ('Hasnen', '__ADMIN_PASSWORD_HASH__', 'admin', 0, 0, 0, NOW());

INSERT INTO `user_stats` (`user_id`) VALUES (LAST_INSERT_ID());

-- Buildings (Phase 1 core: Head = click bonus, Robot & Skull = auto/sec, others as placeholders for later phases)
INSERT INTO `buildings_catalog` (`key_name`,`name_ar`,`description`,`production_type`,`base_price`,`price_growth`,`base_production`,`sort_order`) VALUES
('head','الرأس','يزيد W لكل ضغطة ويتغيّر شكله مع التطوير','click_bonus', 10, 1.15, 1, 1),
('skull','الجمجمة','تجمع W تلقائياً كل ثانية','auto_second', 25, 1.15, 1, 2),
('robot','روبوت','ينتج W تلقائياً بشكل مستقل عن الجمجمة والضغط','auto_second', 100, 1.17, 3, 3),
('ghost','شبح','ينتج W تلقائياً','auto_second', 500, 1.18, 8, 4),
('wizard','ساحر','ينتج W تلقائياً','auto_second', 2500, 1.19, 25, 5),
('factory','مصنع','ينتج W تلقائياً','auto_second', 12000, 1.20, 80, 6),
('castle','قلعة','ينتج W تلقائياً','auto_second', 60000, 1.21, 260, 7),
('space_station','محطة فضائية','ينتج W تلقائياً','auto_second', 300000, 1.22, 900, 8),
('black_hole','ثقب أسود','ينتج W تلقائياً','auto_second', 1500000, 1.23, 3200, 9);

-- Gem drop rules per collection source (percent chance per collection event)
INSERT INTO `gem_drop_rules` (`source`,`drop_chance_percent`,`min_amount`,`max_amount`) VALUES
('click', 2.000, 1, 2),
('robot', 1.000, 1, 3),
('skull', 1.000, 1, 2),
('auto_click', 1.500, 1, 2),
('other_auto', 0.500, 1, 1);

-- Core game settings
INSERT INTO `game_settings` (`setting_key`,`setting_value`) VALUES
('critical_chance_percent','5'),
('critical_multiplier','3'),
('maintenance_mode','0');
