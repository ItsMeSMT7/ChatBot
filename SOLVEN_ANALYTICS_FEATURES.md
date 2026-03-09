# Solven Analytics — Feature Documentation

## 1. Overview
**Solven Analytics** is an AI-powered Business Intelligence engine embedded within the platform. It autonomously ingests structured datasets (CSV, Excel), performs a 9-phase analytical pipeline, and generates executive-grade KPIs, insights, and visualizations without manual user intervention.

---

## 2. File Structure

The feature is distributed across the backend (Django/Python) and frontend (React).

```text
P Square/
├── backend/
│   └── api/
│       ├── analytics_views.py  # API Endpoint & File Handling
│       ├── rag.py              # Core AI Analysis Pipeline (9 Phases)
│       └── ollama_service.py   # LLM Interface (Ollama)
│
└── frontend/
    └── src/
        ├── SolvenAnalytics.js  # React UI Component
        └── SolvenAnalytics.css # Component Styling
```

---

## 3. Libraries & Dependencies

### Backend (Python/Django)
| Library | Purpose |
| :--- | :--- |
| **`pandas`** | High-performance data manipulation, profiling, and aggregation. |
| **`numpy`** | Numerical computing support for Pandas. |
| **`openpyxl`** | Reading Excel (`.xlsx`) files. |
| **`djangorestframework`** | Handling API requests and file uploads. |
| **`requests`** | Communicating with the local Ollama LLM instance. |

### Frontend (React)
| Library | Purpose |
| :--- | :--- |
| **`axios`** | Making HTTP POST requests to the backend API. |
| **`recharts`** | Rendering responsive, composable charts (Bar, Line, Pie, Area). |

---

## 4. Operational Pipeline (The 9 Phases)

The system executes the following phases sequentially in `rag.py`:

1.  **Data Profiling:** Scans schema, data types, and calculates statistics (Pandas).
2.  **KPI Generation:** AI suggests 10-20 potential KPIs based on the profile.
3.  **KPI Prioritization:** AI selects the top 5 most strategic KPIs.
4.  **Formula Engineering:** AI defines how to calculate these KPIs.
5.  **Computation:** System computes values using Pandas based on AI definitions.
6.  **Chart Ideation:** AI suggests 10+ visualization concepts.
7.  **Chart Selection:** AI selects the top 6 most impactful charts.
8.  **Chart Data Generation:** System aggregates data for the selected charts (Pandas).
9.  **Consolidation:** AI generates final business insights and packages the JSON response.

---

## 5. Detailed File Breakdown

### A. Core Analysis Engine (`backend/api/rag.py`)
This is the brain of the operation. It orchestrates the LLM and Pandas to analyze data.

```python
import json
import pandas as pd
import datetime
import traceback
from api.ollama_service import generate_response

def _safe_json_loads(json_str):
    """Helper to parse JSON from LLM response."""
    try:
        cleaned = json_str.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
        return json.loads(cleaned)
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        return {}

def _phase_1_data_profiling(df):
    """Generates a statistical profile of the dataset for the AI."""
    numeric_stats = {}
    for col in df.select_dtypes(include=['number']).columns:
        try:
            numeric_stats[col] = {
                "sum": float(df[col].sum()) if pd.notnull(df[col].sum()) else 0,
                "mean": float(df[col].mean()) if pd.notnull(df[col].mean()) else 0,
                "min": float(df[col].min()) if pd.notnull(df[col].min()) else 0,
                "max": float(df[col].max()) if pd.notnull(df[col].max()) else 0,
                "count": int(df[col].count())
            }
        except:
            continue

    profile_summary = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": list(df.columns),
        "dtypes": {k: str(v) for k, v in df.dtypes.items()},
        "sample": df.head(3).to_dict(orient='records'),
        "numeric_stats": numeric_stats
    }
    
    prompt = f"""
    You are the Solven Analytics Data Profiling Engine.
    Analyze this dataset profile and return a JSON object following the 'dataset_profile' schema.
    Classify each column into exactly one role: METRIC, DIMENSION, TEMPORAL, or IDENTIFIER.
    
    Dataset Profile:
    {json.dumps(profile_summary, indent=2, default=str)}
    """
    response = generate_response(prompt)
    return _safe_json_loads(response)

def _phase_2_kpi_generation(profile, numeric_stats):
    """Asks AI to generate potential KPIs."""
    prompt = f"""
    Generate 10-20 meaningful, data-supported Key Performance Indicators (KPIs).
    Dataset Profile: {json.dumps(profile, indent=2)}
    """
    response = generate_response(prompt)
    return _safe_json_loads(response)

def _phase_3_kpi_prioritization(generated_kpis):
    """Asks AI to select the top 5 KPIs."""
    prompt = f"""
    Select the Top 5 most impactful KPIs from the list below.
    Generated KPIs: {json.dumps(generated_kpis, indent=2)}
    """
    response = generate_response(prompt)
    return _safe_json_loads(response)

def _phase_4_5_formula_and_output(selected_kpis, df, numeric_stats):
    """Asks AI to compute KPI values using pre-calculated stats."""
    prompt = f"""
    For each of the selected Top 5 KPIs, provide the computation logic and the calculated value.
    Use these NUMERIC STATS: {json.dumps(numeric_stats, indent=2)}
    """
    response = generate_response(prompt)
    return _safe_json_loads(response)

def _phase_6_7_8_chart_generation(profile, kpis):
    """Asks AI to design charts."""
    prompt = f"""
    Generate 6 high-impact visualizations based on the dataset profile and KPIs.
    KPIs: {json.dumps(kpis, indent=2)}
    """
    response = generate_response(prompt)
    return _safe_json_loads(response)

def _generate_chart_data(df, chart_spec):
    """Executes Pandas aggregations to get actual data for charts."""
    x_col = chart_spec.get("x_axis", {}).get("column")
    y_col = chart_spec.get("y_axis", {}).get("column")
    
    if not x_col or not y_col: return []
    
    # Group by X and aggregate Y
    grouped = df.groupby(x_col)[y_col].sum().reset_index()
    grouped.columns = ['name', 'value']
    
    if chart_spec.get("sort_order") == "descending":
        grouped = grouped.sort_values('value', ascending=False)
        
    return grouped.head(15).to_dict(orient='records')

def _phase_9_consolidated_output(profile, kpis, charts):
    """Asks AI for final insights and packages the response."""
    prompt = f"""
    Synthesize the final executive summary based on the analysis.
    KPIs: {json.dumps(kpis, indent=2)}
    Charts: {json.dumps(charts, indent=2)}
    """
    response = generate_response(prompt)
    insights = _safe_json_loads(response)
    
    return {
        "solven_analytics_output": {
            "version": "2.0",
            "dataset_summary": profile.get("dataset_profile", {}),
            "kpis": kpis.get("kpis", []),
            "charts": charts.get("charts", []),
            "key_business_insights": insights.get("key_business_insights", []),
            "data_quality_notes": insights.get("data_quality_notes", [])
        }
    }

def run_solven_analytics_pipeline(dataset_path):
    """Main entry point called by the View."""
    # Load Data
    if dataset_path.endswith('.csv'):
        df = pd.read_csv(dataset_path)
    else:
        df = pd.read_excel(dataset_path)

    # Pre-calculate stats
    numeric_stats = {} # ... (calculation logic)

    # Execute Pipeline
    profile_data = _phase_1_data_profiling(df)
    all_kpis = _phase_2_kpi_generation(profile_data, numeric_stats)
    top_kpis = _phase_3_kpi_prioritization(all_kpis)
    final_kpis = _phase_4_5_formula_and_output(top_kpis, df, numeric_stats)
    final_charts = _phase_6_7_8_chart_generation(profile_data, final_kpis)
    
    # Generate Data for Charts
    for chart in final_charts.get('charts', []):
        chart['data'] = _generate_chart_data(df, chart)
    
    return _phase_9_consolidated_output(profile_data, final_kpis, final_charts)
```

### B. API View (`backend/api/analytics_views.py`)
Handles the HTTP request, file upload, and triggers the pipeline.

```python
import os
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from .rag import run_solven_analytics_pipeline

class AnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Save temp file
        ext = os.path.splitext(file_obj.name)[1].lower()
        temp_filename = f"temp_{uuid.uuid4()}{ext}"
        file_path = default_storage.save(temp_filename, file_obj)
        full_path = default_storage.path(file_path)

        try:
            # 2. Run Pipeline
            analysis_result = run_solven_analytics_pipeline(full_path)
            
            if "error" in analysis_result:
                return Response(analysis_result, status=status.HTTP_400_BAD_REQUEST)
            
            return Response(analysis_result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        finally:
            # 3. Cleanup
            if os.path.exists(full_path):
                os.remove(full_path)
```

### C. Frontend Component (`frontend/src/SolvenAnalytics.js`)
Handles file selection, API calls, and rendering the dashboard.

```javascript
import React, { useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import './SolvenAnalytics.css';

const SolvenAnalytics = () => {
    const [file, setFile] = useState(null);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
        setAnalysisResult(null);
        setError('');
    };

    const handleAnalyze = async () => {
        if (!file) {
            setError('Please select a file to analyze.');
            return;
        }
        setIsLoading(true);
        setError('');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const token = localStorage.getItem('token');
            const response = await axios.post('http://localhost:8000/api/analytics/analyze/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'Authorization': token ? `Token ${token}` : ''
                }
            });
            // The backend returns the result in 'solven_analytics_output'
            setAnalysisResult(response.data.solven_analytics_output);
        } catch (err) {
            setError('Failed to analyze data.');
        } finally {
            setIsLoading(false);
        }
    };

    const renderChart = (chart, index) => {
        const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];
        const dataKey = "value";
        const nameKey = "name";

        switch (chart.chart_type) {
            case 'bar':
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={chart.data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey={nameKey} />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey={dataKey} fill="#8884d8" />
                        </BarChart>
                    </ResponsiveContainer>
                );
            case 'line':
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={chart.data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey={nameKey} />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line type="monotone" dataKey={dataKey} stroke="#82ca9d" />
                        </LineChart>
                    </ResponsiveContainer>
                );
            case 'pie':
            case 'donut':
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie data={chart.data} dataKey={dataKey} nameKey={nameKey} cx="50%" cy="50%" outerRadius={100} fill="#8884d8" label>
                                {chart.data.map((entry, idx) => <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />)}
                            </Pie>
                            <Tooltip />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                );
            case 'area':
                 return (
                    <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={chart.data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey={nameKey} />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Area type="monotone" dataKey={dataKey} stroke="#8884d8" fill="#8884d8" />
                        </AreaChart>
                    </ResponsiveContainer>
                );
            default:
                return <p>Unsupported chart type: {chart.chart_type}</p>;
        }
    };

    return (
        <div className="solven-analytics-container">
            <header className="analytics-header">
                <h1>Solven Data Analytics</h1>
                <p>Upload an Excel or CSV file to get AI-powered insights.</p>
            </header>

            <div className="upload-section">
                <input type="file" id="file-upload" onChange={handleFileChange} />
                <label htmlFor="file-upload" className="file-upload-label">
                    {file ? file.name : 'Choose a file...'}
                </label>
                <button onClick={handleAnalyze} disabled={isLoading}>
                    {isLoading ? 'Analyzing...' : 'Analyze Data'}
                </button>
            </div>

            {error && <div className="error-message">{error}</div>}
            {isLoading && <div className="loading-container"><div className="spinner"></div></div>}

            {analysisResult && (
                <div className="results-container">
                    {/* KPIs */}
                    <section className="kpi-section">
                        <h2>Key Performance Indicators</h2>
                        <div className="kpi-grid">
                            {analysisResult.kpis && analysisResult.kpis.map((kpi, index) => (
                                <div key={index} className="kpi-card">
                                    <h3>{kpi.kpi_name}</h3>
                                    <p className="kpi-value">{kpi.kpi_value}</p>
                                    <p className={`kpi-insight ${kpi.trend_direction}`}>{kpi.business_insight}</p>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Charts */}
                    <section className="charts-section">
                        <h2>Visualizations</h2>
                        <div className="charts-grid">
                            {analysisResult.charts && analysisResult.charts.map((chart, index) => (
                                <div key={index} className="chart-card">
                                    <h3>{chart.title}</h3>
                                    {renderChart(chart, index)}
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Insights */}
                    <section className="insights-section">
                        <h2>Key Business Insights</h2>
                        <div className="insights-list">
                            {analysisResult.key_business_insights && analysisResult.key_business_insights.map((insight, index) => (
                                <div key={index} className="insight-card">
                                    <span className={`impact-level ${insight.impact_level?.toLowerCase()}`}>{insight.impact_level}</span>
                                    <h4>{insight.insight}</h4>
                                    <p><strong>Recommended Action:</strong> {insight.recommended_action}</p>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>
            )}
        </div>
    );
};

export default SolvenAnalytics;
```

### D. Styling (`frontend/src/SolvenAnalytics.css`)
Provides the layout for the dashboard.

```css
.solven-analytics-container {
    padding: 2rem;
    background-color: #f4f7fa;
    font-family: 'Segoe UI', sans-serif;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
}

.kpi-card {
    background-color: #fff;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    text-align: center;
}

.kpi-value {
    font-size: 2rem;
    font-weight: bold;
    color: #1a2c4e;
}

.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
}

.chart-card {
    background-color: #fff;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.insight-card {
    background-color: #fff;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border-left: 5px solid #007bff;
    border-radius: 4px;
}

.impact-level.high { background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.impact-level.medium { background-color: #ffc107; color: black; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
```

---

## 6. Data Flow Explanation

1.  **User Action:** The user selects a CSV/Excel file in the React frontend and clicks "Analyze Data".
2.  **Request:** `SolvenAnalytics.js` sends a `POST` request with the file to `http://localhost:8000/api/analytics/analyze/`.
3.  **Reception:** `AnalyticsView` (Django) receives the file and saves it temporarily to disk.
4.  **Pipeline Trigger:** `AnalyticsView` calls `run_solven_analytics_pipeline(file_path)`.
5.  **Processing (Backend):**
    *   **Pandas** loads the file into a DataFrame.
    *   **Pandas** calculates raw statistics (sums, means, null counts).
    *   **Ollama (LLM)** is prompted with these stats to identify the schema (Phase 1).
    *   **Ollama** suggests KPIs (Phase 2) and prioritizes them (Phase 3).
    *   **Ollama** determines the values/formulas for the KPIs using the pre-calculated stats (Phase 4/5).
    *   **Ollama** suggests chart configurations (Phase 6/7).
    *   **Pandas** executes the aggregations (groupby, sum, count) required for the selected charts (Phase 8).
    *   **Ollama** generates a final executive summary (Phase 9).
6.  **Response:** The consolidated JSON object is returned to the frontend.
7.  **Rendering:**
    *   React updates the state with the JSON data.
    *   KPI cards are rendered.
    *   `Recharts` components (`BarChart`, `LineChart`, etc.) are dynamically generated based on the `chart_type` and `data` returned.
    *   Insights are displayed in a list.
```

<!--
[PROMPT_SUGGESTION]How do I add a new chart type (e.g., Scatter Plot) to the frontend rendering logic?[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Can you explain how the backend handles large datasets to avoid timeouts?[/PROMPT_SUGGESTION]
