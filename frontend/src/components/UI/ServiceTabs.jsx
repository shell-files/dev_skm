import React from 'react';
import '@styles/ServiceTabs.css';

const services = [
  { id: 'disclosure', label: '공시', icon: '📝' },
  { id: 'carbon', label: '탄소관리', icon: '🌿' },
  { id: 'supply', label: '공급망 관리', icon: '🤝' }
];

const ServiceTabs = ({ activeService, onServiceChange }) => {
  return (
    <div className="service-select-wrapper">
      <select 
        className="service-select"
        value={activeService}
        onChange={(e) => onServiceChange(e.target.value)}
      >
        {services.map((service) => (
          <option key={service.id} value={service.id}>
            {service.icon} {service.label}
          </option>
        ))}
      </select>
      <div className="select-arrow">
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
          <path d="M1 1L5 5L9 1" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </div>
  );
};

export default ServiceTabs;
