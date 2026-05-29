import React, { useState, useEffect } from 'react';
import '@styles/onboardingModal.css';

import ModalHeader from './ModalHeader';
import ContextSummaryPanel from './ContextSummaryPanel';
import EvidencePanel from './EvidencePanel';
import ValidationPreviewPanel from './ValidationPreviewPanel';
import ModalFooterActions from './ModalFooterActions';

// 동적 패널
import DirectInputPanel from './panels/DirectInputPanel';
import CalculationInputPanel from './panels/CalculationInputPanel';
import NarrativeInputPanel from './panels/NarrativeInputPanel';
import ReferenceInputPanel from './panels/ReferenceInputPanel';
import MixedInputPanel from './panels/MixedInputPanel';

export default function OnboardingModalShell({
  isOpen,
  onClose,
  metricItem,
  subMetrics,
  onSaveAndSubmit,
  modalType = 'MIXED' // 기본적으로 혼합형으로 설정, 향후 로직으로 동적 분기
}) {
  const [atomicValues, setAtomicValues] = useState({});
  const [atomicFiles, setAtomicFiles] = useState({});

  useEffect(() => {
    if (!metricItem || !subMetrics) return;
    const initialValues = {};
    const initialFiles = {};

    subMetrics.forEach(sub => {
      initialValues[sub.atomicMetricId || sub.issueId] = sub.valueText || sub.valueNumeric || sub.value || '';
      initialFiles[sub.atomicMetricId || sub.issueId] = sub.evidenceFileName ? { name: sub.evidenceFileName } : null;
    });

    setAtomicValues(initialValues);
    setAtomicFiles(initialFiles);
  }, [metricItem, subMetrics]);

  const handleInputChange = (id, value) => {
    setAtomicValues(prev => ({ ...prev, [id]: value }));
  };

  const handleFileChange = (id, file) => {
    setAtomicFiles(prev => ({ ...prev, [id]: file }));
  };

  const handleSaveDraft = () => {
    if (onSaveAndSubmit) {
      onSaveAndSubmit(atomicValues, atomicFiles, 'DRAFT');
    }
  };

  const handleSubmit = () => {
    if (onSaveAndSubmit) {
      onSaveAndSubmit(atomicValues, atomicFiles, 'SUBMITTED');
    }
  };

  if (!isOpen || !metricItem || !subMetrics) return null;

  // Render dynamic panel based on type
  const renderDynamicPanel = () => {
    switch (modalType) {
      case 'DIRECT':
        return <DirectInputPanel subMetrics={subMetrics} atomicValues={atomicValues} onChange={handleInputChange} />;
      case 'CALCULATION':
        return <CalculationInputPanel subMetrics={subMetrics} atomicValues={atomicValues} onChange={handleInputChange} />;
      case 'NARRATIVE':
        return <NarrativeInputPanel subMetrics={subMetrics} atomicValues={atomicValues} onChange={handleInputChange} />;
      case 'REFERENCE':
        return <ReferenceInputPanel subMetrics={subMetrics} atomicValues={atomicValues} onChange={handleInputChange} />;
      case 'MIXED':
      default:
        return <MixedInputPanel subMetrics={subMetrics} atomicValues={atomicValues} onChange={handleInputChange} />;
    }
  };

  return (
    <div className="ob-modal-overlay" onClick={onClose}>
      <div className="ob-modal-shell" onClick={(e) => e.stopPropagation()}>
        <ModalHeader metricItem={metricItem} />
        
        <div className="ob-modal-body-layout">
          {/* Left Panel: 70% */}
          <div className="ob-modal-left-panel">
            <ContextSummaryPanel metricItem={metricItem} />
            {renderDynamicPanel()}
          </div>

          {/* Right Panel: 30% */}
          <div className="ob-modal-right-panel">
            <EvidencePanel 
              subMetrics={subMetrics} 
              atomicFiles={atomicFiles} 
              onFileChange={handleFileChange} 
            />
            <ValidationPreviewPanel 
              subMetrics={subMetrics} 
              atomicValues={atomicValues} 
            />
          </div>
        </div>

        <ModalFooterActions 
          onClose={onClose} 
          onSaveDraft={handleSaveDraft} 
          onSubmit={handleSubmit} 
        />
      </div>
    </div>
  );
}
