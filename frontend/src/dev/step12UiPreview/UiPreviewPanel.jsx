import { STEP12_UI_FIXTURE_ENABLED } from '@/dev/step12UiPreview/config';
import { ONBOARDING_SCENARIOS, APPROVAL_SCENARIOS, ROLLUP_SCENARIOS } from '@/dev/step12UiPreview/fixtures';

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
    <div style={{
      position: 'fixed',
      right: '24px',
      bottom: '24px',
      width: '280px',
      background: '#ffffff',
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '16px',
      boxShadow: '0 10px 25px rgba(0,0,0,0.15)',
      zIndex: 9999,
      fontSize: '0.85rem',
      color: '#1e293b'
    }}>
      <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: '#0f172a' }}>Step 12 UI Preview</h3>
      
      <div style={{ marginBottom: '12px' }}>
        <label htmlFor="step12-preview-role" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569', minWidth: '80px' }}>Role</label>
        <select id="step12-preview-role" value={role} onChange={e => onRoleChange?.(e.target.value)} style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
          <option value="ESG 담당자">ESG 담당자</option>
          <option value="부서 담당자">부서 담당자</option>
          <option value="컨설턴트">컨설턴트</option>
          <option value="시스템관리자">시스템 관리자</option>
        </select>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <label htmlFor="step12-preview-onboarding" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569', minWidth: '80px' }}>Onboarding</label>
        <select id="step12-preview-onboarding" value={onboardingScenario} onChange={e => onOnboardingScenarioChange?.(e.target.value)} style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
          <option value={ONBOARDING_SCENARIOS.UNASSIGNED}>담당자 미지정</option>
          <option value={ONBOARDING_SCENARIOS.ASSIGNED}>담당자 지정 완료</option>
          <option value={ONBOARDING_SCENARIOS.INVITE_PENDING}>회원가입 초대 대기</option>
          <option value={ONBOARDING_SCENARIOS.SELF_ASSIGNED}>본인 입력</option>
          <option value={ONBOARDING_SCENARIOS.CONSULTANT_READONLY}>컨설턴트 read-only</option>
          <option value={ONBOARDING_SCENARIOS.DUE_DATE_OVERDUE}>제출 기한 초과</option>
        </select>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <label htmlFor="step12-preview-approval" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569', minWidth: '80px' }}>Approval</label>
        <select id="step12-preview-approval" value={approvalScenario} onChange={e => onApprovalScenarioChange?.(e.target.value)} style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
          <option value={APPROVAL_SCENARIOS.NO_CONSULTANT}>컨설턴트 없음</option>
          <option value={APPROVAL_SCENARIOS.CONSULTANT_PENDING}>컨설턴트 검토 대기</option>
          <option value={APPROVAL_SCENARIOS.REVIEWED}>검토 완료</option>
          <option value={APPROVAL_SCENARIOS.REJECTED}>반려</option>
          <option value={APPROVAL_SCENARIOS.APPROVED}>승인 완료</option>
        </select>
      </div>

      <div>
        <label htmlFor="step12-preview-rollup" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569', minWidth: '80px' }}>Rollup</label>
        <select id="step12-preview-rollup" value={rollupScenario} onChange={e => onRollupScenarioChange?.(e.target.value)} style={{ width: '100%', padding: '4px 8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
          <option value={ROLLUP_SCENARIOS.PARENT_PENDING}>지주사 수집 대기</option>
          <option value={ROLLUP_SCENARIOS.PARENT_READY}>지주사 계산 가능</option>
          <option value={ROLLUP_SCENARIOS.SUB_READY}>자회사 전송 가능</option>
          <option value={ROLLUP_SCENARIOS.SUB_MISSING}>자회사 필수값 누락</option>
        </select>
      </div>
    </div>
  );
};

export default UiPreviewPanel;
