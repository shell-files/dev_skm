import React, { useRef, useState, useEffect } from 'react';
import "@styles/TabButton.css";

/**
 * TabButton.jsx
 * 
 * 1. CategoryTabs: 상단 메인 카테고리 탭 (슬라이더 애니메이션 포함)
 * 2. SubTabs: 하위 이슈그룹 탭 (폴더 형태, 도메인별 테마 지원)
 */

// ── 1. 메인 카테고리 탭 ──
export const CategoryTabs = ({ 
  tabs,          // Array of strings or objects { label, value }
  activeTab,     // Current active value
  onTabChange,   // Change handler
  className = "" 
}) => {
  const tabsRef = useRef([]);
  const [sliderStyle, setSliderStyle] = useState({});

  useEffect(() => {
    const values = tabs.map(t => typeof t === 'object' ? t.value : t);
    const idx = values.indexOf(activeTab);
    const target = tabsRef.current[idx];
    
    if (target) {
      setSliderStyle({
        left: `${target.offsetLeft}px`,
        width: `${target.offsetWidth}px`,
      });
    }
  }, [activeTab, tabs]);

  return (
    <div className={`ob-cat-tabs ${className}`}>
      <div className="ob-tab-slider" style={sliderStyle} />
      {tabs.map((tab, i) => {
        const label = typeof tab === 'object' ? tab.label : tab;
        const value = typeof tab === 'object' ? tab.value : tab;
        const isActive = activeTab === value;

        return (
          <button
            key={value}
            ref={el => tabsRef.current[i] = el}
            type="button"
            className={`ob-cat-tab ${isActive ? "active" : ""}`}
            onClick={() => onTabChange(value)}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};

// ── 2. 하위/이슈그룹 탭 ──
export const SubTabs = ({ 
  tabs,            // Array of strings or objects { label, value }
  activeTab,       // Current active value or array of values
  onTabChange,     // Change handler
  categoryTheme,   // 'E', 'S', 'G', '경영일반' 등 CSS 테마 클래스용
  className = "" 
}) => {
  const isSelected = (value) => {
    if (Array.isArray(activeTab)) return activeTab.includes(value);
    return activeTab === value;
  };

  return (
    <div className={`sr-ig-tabs ${className}`}>
      {tabs.map(tab => {
        const label = typeof tab === 'object' ? tab.label : tab;
        const value = typeof tab === 'object' ? tab.value : tab;
        const isActive = isSelected(value);

        return (
          <button
            key={value}
            type="button"
            className={`sr-ig-tab ${isActive ? `active sr-theme-${categoryTheme}` : ""}`}
            onClick={() => onTabChange(value)}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
};

// Default export as a combined object if needed
const TabButton = {
  Category: CategoryTabs,
  Sub: SubTabs
};

export default TabButton;