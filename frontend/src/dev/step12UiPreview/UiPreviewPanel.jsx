import { STEP12_UI_FIXTURE_ENABLED } from "@/dev/step12UiPreview/config";
import {
  APPROVAL_SCENARIOS,
  ONBOARDING_SCENARIOS,
  ROLLUP_SCENARIOS,
} from "@/dev/step12UiPreview/fixtures";

const UiPreviewPanel = ({
  role,
  onboardingScenario,
  approvalScenario,
  rollupScenario,
  onRoleChange,
  onOnboardingScenarioChange,
  onApprovalScenarioChange,
  onRollupScenarioChange,
}) => {
  if (!STEP12_UI_FIXTURE_ENABLED) return null;

  return (
    <div
      style={{
        position: "fixed",
        right: "24px",
        bottom: "24px",
        width: "280px",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
        padding: "16px",
        boxShadow: "0 10px 25px rgba(0,0,0,0.15)",
        zIndex: 9999,
        fontSize: "0.85rem",
        color: "#1e293b",
      }}
    >


      <Field label="Rollup" id="step12-preview-rollup">
        <select
          id="step12-preview-rollup"
          value={rollupScenario}
          onChange={(event) => onRollupScenarioChange?.(event.target.value)}
          style={selectStyle}
        >
          <option value={ROLLUP_SCENARIOS.PARENT_PENDING}>Parent pending</option>
          <option value={ROLLUP_SCENARIOS.PARENT_READY}>Parent ready</option>
          <option value={ROLLUP_SCENARIOS.SUB_READY}>Subsidiary ready</option>
          <option value={ROLLUP_SCENARIOS.SUB_MISSING}>Subsidiary missing inputs</option>
        </select>
      </Field>
    </div>
  );
};

const Field = ({ label, id, children }) => (
  <div style={{ marginBottom: "12px" }}>
    <label htmlFor={id} style={{ fontSize: "0.85rem", fontWeight: 600, color: "#475569" }}>
      {label}
    </label>
    {children}
  </div>
);

const selectStyle = {
  width: "100%",
  padding: "4px 8px",
  borderRadius: "4px",
  border: "1px solid #cbd5e1",
};

export default UiPreviewPanel;
