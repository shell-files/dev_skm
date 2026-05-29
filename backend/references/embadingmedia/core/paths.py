from pathlib import Path

# =========================
# ROOT
# =========================

baseDir = Path(__file__).resolve().parent.parent

outputDir = baseDir / "output"

csvDir = outputDir / "csv"
jsonlDir = outputDir / "jsonl"
errorDir = outputDir / "errors"
embeddingDir = outputDir / "embeddings"

# 폴더 자동 생성
for directory in [
    csvDir,
    jsonlDir,
    errorDir,
    embeddingDir
]:
    directory.mkdir(parents=True, exist_ok=True)

# =========================
# 파일 경로
# =========================

trainCsv = csvDir / "esgAiTrainingDataset.csv"

trainJsonl = jsonlDir / "esgAiTrainingDataset.jsonl"

# processedJsonl = jsonlDir / "t_processed_esg_chunks.jsonl"
processedJsonl = jsonlDir / "processedEsgChunks.jsonl"

embeddedJsonl = embeddingDir / "embeddedEsgChunks.jsonl"

similarityJsonl = embeddingDir / "similarityResults.jsonl"

subissueVectorJsonl = embeddingDir / "subissueVectors.jsonl"

errorCsv = errorDir / "errors.csv"