const OnboardingStatCards = ({ stats }) => {
  const total = stats.totalCount || 1;
  const completed = stats.completedCount || 0;
  const inProgress = stats.inProgressCount || 0;
  const notStarted = stats.notStartedCount || 0;

  const getPercent = (count) => Math.round((count / total) * 100);

  return (
    <div className="ob1-stat-cards-inner" style={{ display: 'flex', gap: '24px', background: '#ffffff', padding: '12px 24px', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingRight: '24px' }}>
        <span style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: '600', marginBottom: '4px' }}>전체 지표</span>
        <span style={{ fontSize: '1.25rem', color: '#0f172a', fontWeight: '700' }}>{stats.totalCount || 0}</span>
      </div>
      <div style={{ width: '1px', background: '#e2e8f0' }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '120px', justifyContent: 'center' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
          <span style={{ color: '#64748b', fontWeight: '600' }}>입력 완료</span>
          <span style={{ color: '#16a34a', fontWeight: '700' }}>{completed}</span>
        </div>
        <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${getPercent(completed)}%`, background: '#16a34a' }} />
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '120px', justifyContent: 'center' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
          <span style={{ color: '#64748b', fontWeight: '600' }}>진행 중</span>
          <span style={{ color: '#f97316', fontWeight: '700' }}>{inProgress}</span>
        </div>
        <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${getPercent(inProgress)}%`, background: '#f97316' }} />
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '120px', justifyContent: 'center' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
          <span style={{ color: '#64748b', fontWeight: '600' }}>미입력</span>
          <span style={{ color: '#94a3b8', fontWeight: '700' }}>{notStarted}</span>
        </div>
        <div style={{ height: '4px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${getPercent(notStarted)}%`, background: '#94a3b8' }} />
        </div>
      </div>
    </div>
  );
};

export default OnboardingStatCards;
