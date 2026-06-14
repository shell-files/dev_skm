CREATE TABLE IF NOT EXISTS ESG_DMA_SURVEY_TARGET (
  id BIGINT NOT NULL AUTO_INCREMENT,
  esg_materiality_run_id BIGINT NOT NULL,
  respondent_group VARCHAR(30) NOT NULL,
  target_count INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  delete_yn TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_dma_survey_target_run_group (
    esg_materiality_run_id,
    respondent_group
  ),
  KEY idx_dma_survey_target_run (
    esg_materiality_run_id,
    delete_yn
  ),
  CONSTRAINT fk_dma_survey_target_run
    FOREIGN KEY (esg_materiality_run_id)
    REFERENCES ESG_MATERIALITY_RUN(id),
  CONSTRAINT chk_dma_survey_target_group
    CHECK (respondent_group IN ('employee', 'management', 'external')),
  CONSTRAINT chk_dma_survey_target_count
    CHECK (target_count >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='DMA survey target response counts by respondent group';
