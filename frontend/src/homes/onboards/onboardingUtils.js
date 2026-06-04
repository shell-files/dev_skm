export const STRUCTURED_LOOKUP_IDS = new Set(["G0-05__QL0002", "G0-06__QL0001"]);
export const EDITABLE_INPUT_MODES = new Set(["MANUAL_NUMBER", "MANUAL_TEXTAREA", "YEAR_RANGE"]);

export const getAtomicId = (item = {}) => item.atomicMetricId || item.issueId || "";

export const resolveG0InputMode = (item = {}) => {
  const atomicMetricId = getAtomicId(item);
  const dataValueType = String(item.dataValueType || "").trim().toUpperCase();

  if (
    item.atomicDataRole === "DERIVED" ||
    item.rollupRole === "consolidated_result" ||
    /^G0-02__G\d+/.test(atomicMetricId) ||
    atomicMetricId === "G0-03__G0001"
  ) {
    return "ROLLUP_READONLY";
  }

  if (
    STRUCTURED_LOOKUP_IDS.has(atomicMetricId) ||
    item.inputMode === "STRUCTURED_LOOKUP"
  ) {
    return "STRUCTURED_LOOKUP";
  }

  if (item.editableYn === false) {
    return "ROLLUP_READONLY";
  }

  if (item.inputMode) {
    return item.inputMode;
  }

  if (atomicMetricId === "G0-05__QL0001") {
    return "YEAR_RANGE";
  }

  if (
    /^G0-02__Q\d+/.test(atomicMetricId) ||
    /^G0-03__Q\d+/.test(atomicMetricId) ||
    dataValueType === "QUANT" ||
    dataValueType === "NUMBER" ||
    dataValueType === "NUMERIC" ||
    item.dataValueType === "정량"
  ) {
    return "MANUAL_NUMBER";
  }

  return "MANUAL_TEXTAREA";
};

export const isEditableItem = (item) => EDITABLE_INPUT_MODES.has(resolveG0InputMode(item));

export const getInputTypeBadge = (item = {}) => {
  switch (resolveG0InputMode(item)) {
    case "MANUAL_NUMBER":
      return { label: "숫자 입력", cls: "direct" };
    case "MANUAL_TEXTAREA":
      return { label: "서술 입력", cls: "narrative" };
    case "YEAR_RANGE":
      return { label: "기간 입력", cls: "direct" };
    case "STRUCTURED_LOOKUP":
      return { label: "범위 설정", cls: "reference" };
    case "ROLLUP_READONLY":
      return { label: "자동 산출", cls: "reference" };
    default:
      return { label: resolveG0InputMode(item) || "-", cls: "" };
  }
};

export const hasAtomicValue = (item) =>
  (item.valueText !== null && item.valueText !== undefined && item.valueText !== "") ||
  (item.valueNumeric !== null && item.valueNumeric !== undefined);

export const calculateMetricStatus = (subMetrics = []) => {
  const statusTargets = subMetrics.filter((sub) => isEditableItem(sub));
  if (statusTargets.length === 0) {
    const modes = new Set(subMetrics.map((sub) => resolveG0InputMode(sub)));
    if (modes.has("ROLLUP_READONLY")) return { label: "자동 산출", cls: "draft" };
    if (modes.has("STRUCTURED_LOOKUP")) return { label: "범위 설정 필요", cls: "draft" };
    return { label: "조회 전용", cls: "draft" };
  }

  const completed = statusTargets.filter((sub) => hasAtomicValue(sub)).length;
  if (completed === 0) return { label: "미입력", cls: "not-started" };
  if (completed < statusTargets.length) return { label: "진행중", cls: "draft" };
  return { label: "입력 완료", cls: "approved" };
};

export const calculateProfileStats = (items = []) => {
  const editableItems = items.filter((item) => isEditableItem(item));
  const completedCount = editableItems.filter((item) => hasAtomicValue(item)).length;

  return {
    totalCount: items.length,
    completedCount,
    notStartedCount: Math.max(0, editableItems.length - completedCount),
  };
};

export const getStatusInfo = (status) => {
  if (status === "COMPLETED") return { label: "완료", cls: "approved" };
  if (status === "IN_PROGRESS") return { label: "진행중", cls: "not-started" };
  return { label: "미시작", cls: "not-started" };
};
