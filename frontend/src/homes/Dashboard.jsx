import { useEffect, useState } from "react";
import { GET } from "@utils/Network";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";

import "@styles/dashboard.css";

const useMock = true;

/**
 * CHART MOCK DATA
 */
const issueChartData = [
  { name: "GHG", value: 92 },
  { name: "Safety", value: 81 },
  { name: "Supply", value: 74 },
  { name: "Security", value: 63 },
  { name: "Board", value: 58 },
];

const kpiTrendData = [
  { month: "1월", kpi: 60 },
  { month: "2월", kpi: 65 },
  { month: "3월", kpi: 70 },
  { month: "4월", kpi: 75 },
  { month: "5월", kpi: 78 },
];

const mockKpi = [
  { id: 1, title: "전체 진행률", value: "78%", desc: "+12% 증가", type: "up" },
  { id: 2, title: "완료 이슈 수", value: "128", desc: "+8", type: "up" },
  { id: 3, title: "미대응 규제", value: "14", desc: "우선 대응", type: "down" },
  { id: 4, title: "보고서 완성도", value: "84점", desc: "안정", type: "up" },
];

const mockRegulation = [
  { id: 1, title: "ISSB", desc: "국제 기준", value: "82%" },
  { id: 2, title: "GRI", desc: "글로벌", value: "76%" },
  { id: 3, title: "ESRS", desc: "EU 기준", value: "61%" },
  { id: 4, title: "SASB", desc: "산업 기준", value: "88%" },
];

const mockIssue = [
  { id: 1, rank: "#1", title: "GHG 배출량 관리", score: 92 },
  { id: 2, rank: "#2", title: "산업 안전 대응", score: 81 },
  { id: 3, rank: "#3", title: "협력사 ESG 평가", score: 74 },
  { id: 4, rank: "#4", title: "정보보안 체계", score: 63 },
  { id: 5, rank: "#5", title: "이사회 독립성", score: 58 },
];

const Dashboard = () => {
  const [filter, setFilter] = useState({
    year: "2026",
    domain: "ALL",
    regulation: "ALL",
  });

  const [kpiData, setKpiData] = useState([]);
  const [regulationData, setRegulationData] = useState([]);
  const [issueRankData, setIssueRankData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setIsLoading(true);

    try {
      if (useMock) {
        await new Promise((r) => setTimeout(r, 600));

        setKpiData(mockKpi);
        setRegulationData(mockRegulation);
        setIssueRankData(mockIssue);

        return;
      }

      const [kpi, reg, issue] = await Promise.all([
        GET("skm", "/dashboard/kpi"),
        GET("skm", "/dashboard/regulation"),
        GET("skm", "/dashboard/issues"),
      ]);

      setKpiData(kpi?.data || []);
      setRegulationData(reg?.data || []);
      setIssueRankData(issue?.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilter((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <div id="dashboard_page">
      {/* HEADER */}
      <section className="dashboard-header">
        <div>
          <h1 className="dashboard-title">ESG 공시 대시보드</h1>
          <p className="dashboard-description">
            ESG 공시 진행 현황 및 규제 대응 상태를 모니터링합니다.
          </p>
        </div>

        <div className="dashboard-filter-group">
          <select name="year" value={filter.year} onChange={handleFilterChange}>
            <option value="2026">2026</option>
            <option value="2025">2025</option>
          </select>

          <select name="domain" value={filter.domain} onChange={handleFilterChange}>
            <option value="ALL">전체 도메인</option>
            <option value="E">E</option>
            <option value="S">S</option>
            <option value="G">G</option>
          </select>
        </div>
      </section>

      {/* FILTER */}
      <section className="regulation-filter-section">
        <span className="filter-label">규제 표준</span>

        <select
          name="regulation"
          value={filter.regulation}
          onChange={handleFilterChange}
        >
          <option value="ALL">전체 보기</option>
          <option value="ISSB">ISSB</option>
          <option value="GRI">GRI</option>
          <option value="ESRS">ESRS</option>
          <option value="SASB">SASB</option>
        </select>

        <button className="dashboard-search-btn">조회</button>
      </section>

      {/* KPI */}
      <section className="kpi-grid">
        {isLoading ? (
          <div className="dashboard-loading">loading...</div>
        ) : (
          kpiData.map((item) => (
            <div className="kpi-card" key={item.id}>
              <div className="kpi-title">{item.title}</div>
              <div className="kpi-value">{item.value}</div>
              <div className={`kpi-desc ${item.type}`}>{item.desc}</div>
            </div>
          ))
        )}
      </section>

      {/* MAIN GRID */}
      <section className="dashboard-grid">
        {/* BAR CHART */}
        <div className="dashboard-card large-card">
          <div className="card-header">
            <h3>이슈 그룹 대응률</h3>
            <button>상세보기</button>
          </div>

          <div className="chart-placeholder">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={issueChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#03a94d" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* REGULATION */}
        <div className="dashboard-card">
          <div className="card-header">
            <h3>규제 대응 현황</h3>
          </div>

          <div className="regulation-list">
            {regulationData.map((item) => (
              <div className="regulation-item" key={item.id}>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.desc}</p>
                </div>
                <span>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* BOTTOM GRID */}
      <section className="bottom-grid">
        {/* TOP ISSUE */}
        <div className="dashboard-card">
          <div className="card-header">
            <h3>TOP ISSUE</h3>
          </div>

          <div className="issue-rank-list">
            {issueRankData.map((item) => (
              <div className="issue-item" key={item.id}>
                <span>{item.rank}</span>
                <p>{item.title}</p>
                <strong>{item.score}</strong>
              </div>
            ))}
          </div>
        </div>

        {/* LINE CHART */}
        <div className="dashboard-card">
          <div className="card-header">
            <h3>KPI 변화 추이</h3>
          </div>

          <div className="chart-placeholder">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={kpiTrendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="kpi"
                  stroke="#03a94d"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;