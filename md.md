CREATE TABLE `USER_ROLE` (
	`id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '고유ID',
	`user_id` BIGINT(20) NOT NULL COMMENT '회사정보ID',
	`role_id` BIGINT(20) NOT NULL COMMENT '권한 코드ID',
	`company_id` BIGINT(20) NOT NULL COMMENT '사용자ID',
	`created_at` DATETIME NULL DEFAULT current_timestamp() COMMENT '등록일자',
	`updated_at` DATETIME NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정일자',
	`delete_yn` TINYINT(1) NULL DEFAULT '0' COMMENT '삭제여부',
	PRIMARY KEY (`id`) USING BTREE,
	INDEX `FK_UR_USER` (`user_id`) USING BTREE,
	INDEX `FK_UR_ROLE` (`role_id`) USING BTREE,
	CONSTRAINT `FK_UR_ROLE` FOREIGN KEY (`role_id`) REFERENCES `ROLE` (`id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
	CONSTRAINT `FK_UR_USER` FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON UPDATE RESTRICT ON DELETE RESTRICT
)
COMMENT='사용자 권한'
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB
AUTO_INCREMENT=19
;


CREATE TABLE `USER` (
	`id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '고유ID',
	`email` VARCHAR(512) NOT NULL COMMENT '이메일' COLLATE 'utf8mb4_unicode_ci',
	`password` VARCHAR(512) NOT NULL COMMENT '비밀번호' COLLATE 'utf8mb4_unicode_ci',
	`name` VARCHAR(512) NOT NULL COMMENT '이름' COLLATE 'utf8mb4_unicode_ci',
	`agreed` TINYINT(1) NULL DEFAULT '0' COMMENT '이용약관 동의여부',
	`created_at` DATETIME NULL DEFAULT current_timestamp() COMMENT '등록일자',
	`updated_at` DATETIME NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정일자',
	`delete_yn` TINYINT(1) NULL DEFAULT '0' COMMENT '탈퇴여부',
	PRIMARY KEY (`id`) USING BTREE,
	UNIQUE INDEX `UNIQUE KEY` (`email`) USING BTREE COMMENT '무결성'
)
COMMENT='사용자 정보'
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB
AUTO_INCREMENT=17
;


CREATE TABLE `TOKEN` (
	`id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '고유ID',
	`user_id` BIGINT(20) NOT NULL COMMENT '사용자ID',
	`refresh_token` TEXT NOT NULL COMMENT '리프레쉬 토큰' COLLATE 'utf8mb4_unicode_ci',
	`uuid` VARCHAR(100) NOT NULL COMMENT '식별 아이디' COLLATE 'utf8mb4_unicode_ci',
	`created_at` DATETIME NULL DEFAULT current_timestamp() COMMENT '등록일자',
	`updated_at` DATETIME NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정일자',
	`delete_yn` TINYINT(1) NULL DEFAULT '0' COMMENT '삭제여부',
	PRIMARY KEY (`id`) USING BTREE,
	INDEX `FK_TOKEN_USER` (`user_id`) USING BTREE,
	CONSTRAINT `FK_TOKEN_USER` FOREIGN KEY (`user_id`) REFERENCES `USER` (`id`) ON UPDATE RESTRICT ON DELETE RESTRICT
)
COMMENT='로그인 토큰 관리'
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB
AUTO_INCREMENT=126
;


CREATE TABLE `ROLE` (
	`id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '고유ID',
	`role` VARCHAR(100) NOT NULL COMMENT '권한(영문)' COLLATE 'utf8mb4_unicode_ci',
	`name` VARCHAR(100) NULL DEFAULT NULL COMMENT '권한(한글)' COLLATE 'utf8mb4_unicode_ci',
	`created_at` DATETIME NULL DEFAULT current_timestamp() COMMENT '등록일자',
	`updated_at` DATETIME NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정일자',
	`delete_yn` TINYINT(1) NULL DEFAULT '0' COMMENT '삭제여부',
	PRIMARY KEY (`id`) USING BTREE
)
COMMENT='권한 코드'
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB
AUTO_INCREMENT=12
;


CREATE TABLE `CODE_MAP` (
	`id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '고유ID',
	`code_use` BIGINT(20) NOT NULL COMMENT '사용 대상\r\n- 초대정보=> 1\r\n- 협력사관계 => 1,2',
	`code_nm` VARCHAR(20) NOT NULL COMMENT '코드명' COLLATE 'utf8mb4_unicode_ci',
	`created_at` DATETIME NULL DEFAULT current_timestamp() COMMENT '등록일자',
	`updated_at` DATETIME NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정일자',
	`delete_yn` TINYINT(1) NULL DEFAULT '0' COMMENT '삭제여부',
	PRIMARY KEY (`id`) USING BTREE
)
COMMENT='맵핑 공통 테이블'
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB
AUTO_INCREMENT=7
;


CREATE TABLE `INDUSTRY_DETAIL` (
	`id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '고유ID',
	`company_id` BIGINT(20) NOT NULL COMMENT '회사정보ID',
	`industry_id` VARCHAR(50) NOT NULL COMMENT '업종분류코드ID' COLLATE 'utf8mb4_unicode_ci',
	`created_at` DATETIME NULL DEFAULT current_timestamp() COMMENT '등록일자',
	`updated_at` DATETIME NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정일자',
	`delete_yn` TINYINT(1) NULL DEFAULT '0' COMMENT '삭제여부',
	PRIMARY KEY (`id`) USING BTREE,
	INDEX `FK_INDUSTRY_DETAIL_COMPANY` (`company_id`) USING BTREE,
	CONSTRAINT `FK_INDUSTRY_DETAIL_COMPANY` FOREIGN KEY (`company_id`) REFERENCES `COMPANY` (`id`) ON UPDATE NO ACTION ON DELETE NO ACTION
)
COMMENT='업종구분매핑'
COLLATE='utf8mb4_unicode_ci'
ENGINE=InnoDB
AUTO_INCREMENT=6
;
