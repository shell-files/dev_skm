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



    <>
    </>
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
