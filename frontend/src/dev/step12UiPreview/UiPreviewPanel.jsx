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
      <h3 style={{ margin: "0 0 12px 0", fontSize: "1rem", color: "#0f172a" }}>
        Step 12 UI Preview
      </h3>

      <Field label="Role" id="step12-preview-role">
        <select
          id="step12-preview-role"
          value={role}
          onChange={(event) => onRoleChange?.(event.target.value)}
          style={selectStyle}
        >
          <option value="ESG_MANAGER">ESG manager</option>
          <option value="ASSIGNEE">Assignee</option>
          <option value="CONSULTANT">Consultant</option>
          <option value="ADMIN">Admin</option>
        </select>
      </Field>

      <Field label="Onboarding" id="step12-preview-onboarding">
        <select
          id="step12-preview-onboarding"
          value={onboardingScenario}
          onChange={(event) => onOnboardingScenarioChange?.(event.target.value)}
          style={selectStyle}
        >
          <option value={ONBOARDING_SCENARIOS.UNASSIGNED}>Unassigned</option>
          <option value={ONBOARDING_SCENARIOS.ASSIGNED}>Assigned</option>
          <option value={ONBOARDING_SCENARIOS.INVITE_PENDING}>Invite pending</option>
          <option value={ONBOARDING_SCENARIOS.SELF_ASSIGNED}>Self assigned</option>
          <option value={ONBOARDING_SCENARIOS.CONSULTANT_READONLY}>Consultant read-only</option>
          <option value={ONBOARDING_SCENARIOS.DUE_DATE_OVERDUE}>Due date overdue</option>
        </select>
      </Field>

      <Field label="Approval" id="step12-preview-approval">
        <select
          id="step12-preview-approval"
          value={approvalScenario}
          onChange={(event) => onApprovalScenarioChange?.(event.target.value)}
          style={selectStyle}
        >
          <option value={APPROVAL_SCENARIOS.NO_CONSULTANT}>No consultant</option>
          <option value={APPROVAL_SCENARIOS.CONSULTANT_PENDING}>Consultant pending</option>
          <option value={APPROVAL_SCENARIOS.REVIEWED}>Reviewed</option>
          <option value={APPROVAL_SCENARIOS.REJECTED}>Rejected</option>
          <option value={APPROVAL_SCENARIOS.APPROVED}>Approved</option>
        </select>
      </Field>

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
