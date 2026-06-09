

def requireRollupResponseBatchContext(cycle: dict, batchId: Optional[int]) -> None:
    cycleType = str(cycle.get("cycle_type") or "").strip().upper()
    if cycleType != CYCLE_TYPE_ROLLUP_RESPONSE:
        return
    
    if batchId is None:
        err = ValueError("batchId is required for ROLLUP_RESPONSE")
        err.statusCode = 409
        raise err

    if (
        cycle.get("parent_rollup_batch_id") is None
        or int(cycle["parent_rollup_batch_id"]) != int(batchId)
    ):
        err = ValueError("ROLLUP_RESPONSE batch context mismatch")
        err.statusCode = 409
        raise err
