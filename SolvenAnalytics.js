// import React, { useState } from 'react';
// import axios from 'axios';
// import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
// import './SolvenAnalytics.css';

// const SolvenAnalytics = () => {
//     const [file, setFile] = useState(null);
//     const [analysisResult, setAnalysisResult] = useState(null);
//     const [isLoading, setIsLoading] = useState(false);
//     const [error, setError] = useState('');

//     const handleFileChange = (e) => {
//         setFile(e.target.files[0]);
//         setAnalysisResult(null);
//         setError('');
//     };

//     const handleAnalyze = async () => {
//         if (!file) {
//             setError('Please select a file to analyze.');
//             return;
//         }

//         setIsLoading(true);
//         setError('');
//         setAnalysisResult(null);

//         const formData = new FormData();
//         formData.append('file', file);

//         try {
//             const token = localStorage.getItem('token');
//             const response = await axios.post('http://localhost:8000/api/analytics/analyze/', formData, {
//                 headers: {
//                     'Content-Type': 'multipart/form-data',
//                     'Authorization': token ? `Token ${token}` : ''
//                 }
//             });

//             setAnalysisResult(response.data);

//         } catch (err) {
//             setError('Failed to analyze the data. The AI system might be offline or the file format is incorrect.');
//             console.error(err);
//         } finally {
//             setIsLoading(false);
//         }
//     };

//     const renderChart = (chart, index) => {
//         const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];
//         switch (chart.type) {
//             case 'bar':
//                 return (
//                     <ResponsiveContainer width="100%" height={300}>
//                         <BarChart data={chart.data}>
//                             <CartesianGrid strokeDasharray="3 3" />
//                             <XAxis dataKey="name" />
//                             <YAxis />
//                             <Tooltip />
//                             <Legend />
//                             <Bar dataKey={chart.dataKey} fill="#8884d8" />
//                         </BarChart>
//                     </ResponsiveContainer>
//                 );
//             case 'line':
//                 return (
//                     <ResponsiveContainer width="100%" height={300}>
//                         <LineChart data={chart.data}>
//                             <CartesianGrid strokeDasharray="3 3" />
//                             <XAxis dataKey="name" />
//                             <YAxis />
//                             <Tooltip />
//                             <Legend />
//                             <Line type="monotone" dataKey={chart.dataKey} stroke="#82ca9d" />
//                             {chart.dataKey2 && <Line type="monotone" dataKey={chart.dataKey2} stroke="#ffc658" />}
//                         </LineChart>
//                     </ResponsiveContainer>
//                 );
//             case 'pie':
//                 return (
//                     <ResponsiveContainer width="100%" height={300}>
//                         <PieChart>
//                             <Pie data={chart.data} dataKey={chart.dataKey} nameKey="name" cx="50%" cy="50%" outerRadius={100} fill="#8884d8" label>
//                                 {chart.data.map((entry, idx) => <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />)}
//                             </Pie>
//                             <Tooltip />
//                             <Legend />
//                         </PieChart>
//                     </ResponsiveContainer>
//                 );
//             default:
//                 return <p>Unsupported chart type</p>;
//         }
//     };

//     return (
//         <div className="solven-analytics-container">
//             <header className="analytics-header">
//                 <h1>Solven Data Analytics</h1>
//                 <p>Upload an Excel or CSV file to get AI-powered insights and visualizations.</p>
//             </header>

//             <div className="upload-section">
//                 <input type="file" id="file-upload" accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel" onChange={handleFileChange} />
//                 <label htmlFor="file-upload" className="file-upload-label">
//                     {file ? file.name : 'Choose a file...'}
//                 </label>
//                 <button onClick={handleAnalyze} disabled={isLoading}>
//                     {isLoading ? 'Analyzing...' : 'Analyze Data'}
//                 </button>
//             </div>

//             {error && <div className="error-message">{error}</div>}

//             {isLoading && (
//                 <div className="loading-container">
//                     <div className="spinner"></div>
//                     <p>Our AI is analyzing your data... Please wait.</p>
//                 </div>
//             )}

//             {analysisResult && (
//                 <div className="results-container">
//                     <section className="kpi-section">
//                         <h2>Key Performance Indicators</h2>
//                         <div className="kpi-grid">
//                             {analysisResult.kpis.map((kpi, index) => (
//                                 <div key={index} className="kpi-card">
//                                     <h3>{kpi.title}</h3>
//                                     <p className="kpi-value">{kpi.value}</p>
//                                     <p className={`kpi-change ${kpi.change.startsWith('+') ? 'positive' : 'negative'}`}>{kpi.change}</p>
//                                 </div>
//                             ))}
//                         </div>
//                     </section>

//                     <section className="charts-section">
//                         <h2>Visualizations</h2>
//                         <div className="charts-grid">
//                             {analysisResult.charts.map((chart, index) => (
//                                 <div key={index} className="chart-card">
//                                     <h3>{chart.title}</h3>
//                                     {renderChart(chart, index)}
//                                 </div>
//                             ))}
//                         </div>
//                     </section>

//                     <section className="table-section">
//                         <h2>Data Columns Overview</h2>
//                         <div className="table-wrapper">
//                             <table>
//                                 <thead>
//                                     <tr>
//                                         {analysisResult.columns.map((col, index) => (
//                                             <th key={index}>{col.header}</th>
//                                         ))}
//                                     </tr>
//                                 </thead>
//                                 <tbody>
//                                     {analysisResult.tableData.map((row, rowIndex) => (
//                                         <tr key={rowIndex}>
//                                             {analysisResult.columns.map((col, colIndex) => (
//                                                 <td key={colIndex}>{row[col.accessor]}</td>
//                                             ))}
//                                         </tr>
//                                     ))}
//                                 </tbody>
//                             </table>
//                         </div>
//                     </section>
//                 </div>
//             )}
//         </div>
//     );
// };

// export default SolvenAnalytics;