<<<<<<< HEAD
/**
 * PageHeader.jsx
 * 레이어: Component (UI)
 * 역할: 페이지 상단 타이틀과 아이콘을 표시하는 공통 헤더 컴포넌트.
 */
=======
>>>>>>> origin/skm_test
import React from "react";
import "@styles/PageHeader.css";

const getSvgIcon = (iconClass) => {
  if (iconClass === "bi-diagram-3-fill") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16">
        <path fillRule="evenodd" d="M6 3.5A1.5 1.5 0 0 1 7.5 2h1A1.5 1.5 0 0 1 10 3.5v1A1.5 1.5 0 0 1 8.5 6v1H14a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0V8h-5v.5a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 2 7h5.5V6A1.5 1.5 0 0 1 6 4.5zm-6 8A1.5 1.5 0 0 1 1.5 10h1A1.5 1.5 0 0 1 4 11.5v1A1.5 1.5 0 0 1 2.5 14h-1A1.5 1.5 0 0 1 0 12.5zm6 0A1.5 1.5 0 0 1 7.5 10h1a1.5 1.5 0 0 1 1.5 1.5v1A1.5 1.5 0 0 1 8.5 14h-1A1.5 1.5 0 0 1 6 12.5zm6 0a1.5 1.5 0 0 1 1.5-1.5h1a1.5 1.5 0 0 1 1.5 1.5v1a1.5 1.5 0 0 1-1.5 1.5h-1a1.5 1.5 0 0 1-1.5-1.5z"/>
      </svg>
    );
  }
  if (iconClass === "bi-chat-left-text-fill") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16">
        <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4.414a1 1 0 0 0-.707.293L.854 15.146A.5.5 0 0 1 0 14.793zm3.5 1a.5.5 0 0 0 0 1h9a.5.5 0 0 0 0-1zm0 2.5a.5.5 0 0 0 0 1h9a.5.5 0 0 0 0-1zm0 2.5a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1z"/>
      </svg>
    );
  }
  if (iconClass === "bi-leaf-fill") {
    // Bootstrap Icons leaf-fill (correct path from official source)
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16">
        <path d="M9.543.826a.5.5 0 0 1 .366.18C12.3 3.9 12 8.42 8.5 10.5c-.524.306-1.133.494-1.707.614a6.4 6.4 0 0 0 .05-.39c.042-.53.017-1.06-.063-1.58C8.604 8.56 9.2 7.83 9.52 6.9c.456-1.3.388-2.74-.195-3.994a8 8 0 0 0-.42-.773A8 8 0 0 1 9.543.826"/>
        <path d="M6.758 10.5C4.423 11.753 1.585 11.394 0 9.5c2.033 0 3.788-.386 5.12-1.26a6 6 0 0 1-.12-.74C3.212 8.476 1.51 8.5 0 7.5c1.5-2 4.31-2.293 6.045-1.344A5.3 5.3 0 0 1 7.5 3.5C7.5 1.57 5.93 0 4 0 2.07 0 .5 1.57.5 3.5c0 .463.09.907.256 1.31C.266 5.286.076 5.83 0 6.5c1.49-.58 3.2-.63 4.92-.16a5.3 5.3 0 0 0-.014.41A3.5 3.5 0 0 0 4 6.5c-1.93 0-3.5 1.57-3.5 3.5C.5 11.88 1.62 13 3 13c1.46 0 2.72-.88 3.28-2.14.16.53.37 1.05.64 1.53C5.52 13.62 3.43 14.5 1 14.5v1C4 15.5 6.47 14.33 7.72 12.4q.38.065.78.1c-.52.49-1.22.84-2 1.03C9.93 14.07 12 12.04 12 9.5c0-.24-.016-.475-.046-.705C10.94 9.44 9.35 10.3 7.58 10.5z"/>
      </svg>
    );
  }
  if (iconClass === "bi-building-fill") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16">
        <path d="M3 0a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h3v-3.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V16h3a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1zm1 2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3 0a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5M4 5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM7.5 5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5m2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zM4.5 8h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5m2.5.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5zm3.5-.5h1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-1a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5"/>
      </svg>
    );
  }
  return null;
};

const PageHeader = ({ category, title, description, iconClass }) => {
  return (
    <div className="skm-page-title-content">
      <div className="skm-page-title-icon-wrapper">
        <div className="skm-page-title-bar"></div>
        <div className="skm-page-title-circle">
          {getSvgIcon(iconClass)}
        </div>
      </div>
      <div className="skm-page-title-text">
        <div className="skm-page-title-category">{category}</div>
        <h1 className="skm-page-title-heading">{title}</h1>
        {description && (
          <div className="skm-page-title-description">{description}</div>
        )}
      </div>
    </div>
  );
};

export default PageHeader;
