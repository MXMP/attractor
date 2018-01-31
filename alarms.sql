CREATE TABLE `alarms` (
    `id` INT(4) UNSIGNED NOT NULL AUTO_INCREMENT,
    `device` CHAR(16) NOT NULL,
    `host` CHAR(16) NOT NULL,
    `metric` CHAR(16) NOT NULL,
    `key` CHAR(16) NOT NULL,
    `value` CHAR(16) NOT NULL,
    `event_code` INT(4) UNSIGNED NOT NULL,
    `event_text` CHAR(128) NOT NULL,
    `datetime` INT(4) UNSIGNED NOT NULL,
    PRIMARY KEY (`id`),
    INDEX `host` (`host`),
    INDEX `metric` (`metric`),
    INDEX `event_code` (`event_code`),
    INDEX `datetime` (`datetime`),
    INDEX `key` (`key`),
    INDEX `value` (`value`)
)
COLLATE='utf8_general_ci'
ENGINE=InnoDB
AUTO_INCREMENT=1197
;
