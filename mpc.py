import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useDropzone } from 'react-dropzone';

// --- Global URLs for CDN Libraries ---
const LIBRARIES = {
    xlsx: 'https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js',
    plotly: 'https://cdn.plot.ly/plotly-latest.min.js',
    agGrid: 'https://cdn.jsdelivr.net/npm/ag-grid-community/dist/ag-grid-community.min.js',
    agGridReact: 'https://cdn.jsdelivr.net/npm/ag-grid-react/ag-grid-react.min.js',
    agGridCss: 'https://cdn.jsdelivr.net/npm/ag-grid-community/styles/ag-grid.css',
    agGridTheme: 'https://cdn.jsdelivr.net/npm/ag-grid-community/styles/ag-theme-alpine.css',
};

// --- Helper functions to load scripts and CSS dynamically ---
const loadScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.body.appendChild(script);
});

const loadCss = (href) => new Promise((resolve, reject) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.onload = resolve;
    link.onerror = () => reject(new Error(`Failed to load CSS: ${href}`));
    document.head.appendChild(link);
});

// --- MPC Data (as provided) ---
const mpcDataStore = [
    { date: '2025-06-06', meeting: 'June 2025', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY26)', gdpForecast: '7.2% (FY26)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2025-04-04', meeting: 'April 2025', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY26)', gdpForecast: '7.0% (FY26)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2025-02-07', meeting: 'February 2025', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY25)', gdpForecast: '7.0% (FY25)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2024-12-06', meeting: 'December 2024', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY25)', gdpForecast: '7.0% (FY25)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2024-10-09', meeting: 'October 2024', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY25)', gdpForecast: '7.0% (FY25)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2024-08-08', meeting: 'August 2024', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY25)', gdpForecast: '7.0% (FY25)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2024-06-07', meeting: 'June 2024', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY25)', gdpForecast: '7.2% (FY25)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2024-04-05', meeting: 'April 2024', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '4.5% (FY25)', gdpForecast: '7.0% (FY25)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2024-02-08', meeting: 'February 2024', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '5.4% (FY24)', gdpForecast: '7.3% (FY24)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2023-12-08', meeting: 'December 2023', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '5.4% (FY24)', gdpForecast: '7.0% (FY24)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2023-10-06', meeting: 'October 2023', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '5.4% (FY24)', gdpForecast: '6.5% (FY24)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2023-08-10', meeting: 'August 2023', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '5.4% (FY24)', gdpForecast: '6.5% (FY24)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2023-06-08', meeting: 'June 2023', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '5.1% (FY24)', gdpForecast: '6.5% (FY24)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2023-04-06', meeting: 'April 2023', repoRate: '6.50% (Unchanged)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '5.2% (FY24)', gdpForecast: '6.5% (FY24)', msfRate: '6.75%', sdfRate: '6.25%' },
    { date: '2023-02-08', meeting: 'February 2023', repoRate: '6.50% (Increased by 25 bps from 6.25%)', revRepoRate: '3.35% (Fixed)', stance: 'Withdrawal of accommodation', cpiForecast: '6.5% (FY23)', gdpForecast: '7.0% (FY23)', msfRate: '6.75%', sdfRate: '6.25%' },
];

// --- UI Components ---
const PlotlyChart = ({ data, mpcData, onMpcClick }) => {
    const chartRef = useRef(null);

    useEffect(() => {
        const chartDiv = chartRef.current;
        if (!data || !chartDiv || !window.Plotly) return;

        if (data.length === 0) {
            window.Plotly.purge(chartDiv);
            return;
        }

        const trace = {
            x: data.map(d => d.date),
            y: data.map(d => d.value),
            type: 'scatter',
            mode: 'lines+markers',
            name: 'DV01',
            marker: { color: '#22d3ee', size: 6 },
            line: { width: 2 }
        };

        const mpcShapes = mpcData.map(mpc => ({
            type: 'line', x0: mpc.date, x1: mpc.date, y0: 0, y1: 1, yref: 'paper',
            line: { color: 'rgba(255, 165, 0, 0.6)', width: 2, dash: 'dot' }
        }));
        
        const mpcAnnotations = mpcData.map(mpc => ({
            x: mpc.date, y: 1.05, yref: 'paper', text: 'MPC', hovertext: mpc.meeting, showarrow: false,
            font: { color: 'orange', size: 10 }, xanchor: 'center', yanchor: 'bottom',
        }));

        const layout = {
            title: `DV01 Time Series: ${data[0]?.assetClass} - ${data[0]?.tenor}`,
            plot_bgcolor: '#1f2937', paper_bgcolor: '#1f2937', font: { color: '#d1d5db' },
            xaxis: { gridcolor: '#374151', title: 'Date' }, yaxis: { gridcolor: '#374151', title: 'DV01 (£k)' },
            shapes: mpcShapes, annotations: mpcAnnotations, showlegend: true,
            legend: { x: 0.01, y: 0.99, bgcolor: 'rgba(31,41,55,0.5)' },
            margin: { l: 60, r: 30, b: 50, t: 50, pad: 4 }, hovermode: 'x unified'
        };
        
        window.Plotly.react(chartDiv, [trace], layout, { responsive: true });

        const handleClick = (event) => {
            if (event.points) {
                const point = event.points[0];
                const clickedDate = point.x.split(' ')[0]; // Handle date formatting from plotly
                const matchingMpc = mpcData.find(mpc => mpc.date === clickedDate);
                if (matchingMpc) {
                    onMpcClick(matchingMpc);
                }
            }
        };

        chartDiv.on('plotly_click', handleClick);

        return () => {
            if (chartDiv.removeAllListeners) {
                chartDiv.removeAllListeners('plotly_click');
            }
        };

    }, [data, mpcData, onMpcClick]);

    if (!data || data.length === 0) {
        return <div className="w-full h-full flex items-center justify-center text-gray-500">Select an Asset Class and Tenor to view the chart.</div>;
    }

    return <div ref={chartRef} style={{ width: '100%', height: '100%' }} />;
};

const MpcDetailsPanel = ({ meetingData, onClose }) => {
    if (!meetingData) {
        return (
            <div className="p-4 text-center text-gray-400">
                <p>Click an 'MPC' marker on the chart to view detailed policy decisions for that date.</p>
            </div>
        );
    }

    const DetailItem = ({ label, value }) => (
        <div className="py-2 border-b border-gray-700">
            <p className="text-sm text-cyan-400">{label}</p>
            <p className="font-semibold">{value}</p>
        </div>
    );

    return (
        <div className="p-4 bg-gray-800 rounded-lg h-full overflow-y-auto relative">
            <button onClick={onClose} className="absolute top-2 right-2 text-gray-400 hover:text-white">&times;</button>
            <h3 className="text-xl font-bold text-white mb-4 border-b-2 border-cyan-500 pb-2">{meetingData.meeting} Summary</h3>
            <DetailItem label="Repo Rate" value={meetingData.repoRate} />
            <DetailItem label="Reverse Repo Rate" value={meetingData.revRepoRate} />
            <DetailItem label="Stance" value={meetingData.stance} />
            <DetailItem label="CPI Inflation Forecast" value={meetingData.cpiForecast} />
            <DetailItem label="GDP Growth Forecast" value={meetingData.gdpForecast} />
            <DetailItem label="MSF Rate" value={meetingData.msfRate} />
            <DetailItem label="SDF Rate" value={meetingData.sdfRate} />
        </div>
    );
};

// --- Data Processing ---
const parseDateFromFileName = (fileName) => {
    const match = fileName.match(/(\d{4})\.(\d{2})\.(\d{2})/);
    if (!match) return null;
    const [, year, month, day] = match;
    return new Date(Date.UTC(year, month - 1, day));
};

const processFile = (file, XLSX) => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const workbook = XLSX.read(e.target.result, { type: 'binary' });
            const sheetName = 'Trade_Desk_Data';
            if (!workbook.SheetNames.includes(sheetName)) return resolve(null);
            
            const worksheet = workbook.Sheets[sheetName];
            const json = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
            const date = parseDateFromFileName(file.name);
            if (!date) return resolve(null);

            const assetClasses = json[5]?.slice(3, 15) || [];
            const records = [];

            const processTable = (startRow, metric) => {
                const data = json.slice(startRow, startRow + 9);
                data.forEach(row => {
                    const tenor = row[2];
                    if (!tenor || tenor === 'Total') return;
                    assetClasses.forEach((asset, i) => {
                        const value = parseFloat(row[i + 3]) || 0;
                        records.push({
                            date, tenor, assetClass: asset, metric, value,
                            id: `${date.toISOString()}-${tenor}-${asset}-${metric}`
                        });
                    });
                });
            };

            processTable(6, 'DV01');
            processTable(16, 'Change DV01');
            resolve(records);
        } catch (error) {
            reject(error);
        }
    };
    reader.onerror = (err) => reject(err);
    reader.readAsBinaryString(file);
});

// --- Main Application ---
function RiskApp() {
    const [riskData, setRiskData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [selectedAssetClass, setSelectedAssetClass] = useState('');
    const [selectedTenor, setSelectedTenor] = useState('');
    const [selectedMpcMeeting, setSelectedMpcMeeting] = useState(null);

    const { AgGridReact } = window.agGrid;

    const onDrop = useCallback(async (acceptedFiles) => {
        setLoading(true);
        setProgress(0);
        setSelectedMpcMeeting(null);
        const allData = [];
        for (const [index, file] of acceptedFiles.entries()) {
            if (file.name.startsWith('risk_data_In_') && file.name.endsWith('.xlsx')) {
                 try {
                    const records = await processFile(file, window.XLSX);
                    if(records) allData.push(...records);
                } catch (error) {
                    console.error(`Could not process file ${file.name}:`, error);
                }
            }
            setProgress(Math.round(((index + 1) / acceptedFiles.length) * 100));
        }

        setRiskData(allData);
        setLoading(false);
        if (allData.length > 0) {
            const assetClasses = [...new Set(allData.map(d => d.assetClass))].sort();
            const tenorOrder = ['<=1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '>=15Y'];
            const tenors = [...new Set(allData.map(d => d.tenor))].sort((a, b) => tenorOrder.indexOf(a) - tenorOrder.indexOf(b));
            setSelectedAssetClass(assetClasses[0] || '');
            setSelectedTenor(tenors[0] || '');
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, noClick: true });

    const assetClasses = useMemo(() => [...new Set(riskData.map(d => d.assetClass))].sort(), [riskData]);
    const tenors = useMemo(() => {
        const tenorOrder = ['<=1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '>=15Y'];
        return [...new Set(riskData.map(d => d.tenor))].sort((a, b) => tenorOrder.indexOf(a) - tenorOrder.indexOf(b));
    }, [riskData]);

    const filteredChartData = useMemo(() => riskData
        .filter(d => d.assetClass === selectedAssetClass && d.tenor === selectedTenor && d.metric === 'DV01')
        .sort((a, b) => a.date - b.date), [riskData, selectedAssetClass, selectedTenor]);

    const columnDefs = useMemo(() => [
        { field: 'date', headerName: 'Date', valueFormatter: p => p.value.toLocaleDateString('en-GB'), sort: 'asc' },
        { field: 'tenor', headerName: 'Tenor', filter: true },
        { field: 'assetClass', headerName: 'Asset Class', filter: true },
        { field: 'metric', headerName: 'Metric', filter: true },
        { field: 'value', headerName: 'Value (£k)', filter: 'agNumberColumnFilter' }
    ], []);

    return (
        <div {...getRootProps({ className: 'w-full h-screen bg-gray-900 text-white p-4 flex flex-col font-sans' })}>
            <input {...getInputProps()} webkitdirectory="" directory="" />
            <header className="mb-4 flex-shrink-0">
                <h1 className="text-3xl font-bold text-cyan-400">Financial Risk & MPC Analysis Portal</h1>
                <p className="text-gray-400">Drag & drop your 'Risk_data' folder. Click MPC markers on the chart for policy details.</p>
            </header>

            {riskData.length === 0 && !loading && (
                 <div className="flex-grow flex items-center justify-center border-4 border-dashed border-gray-600 rounded-xl transition-all duration-300 hover:border-cyan-400 hover:bg-gray-800">
                    <div className="text-center p-8"><h2 className="mt-2 text-xl font-semibold">{isDragActive ? "Release to drop folder" : "Drop 'Risk_data' folder here"}</h2></div>
                </div>
            )}
            {loading && <div className="flex-grow flex items-center justify-center"><div className="text-center"><p className="text-2xl mb-4">Processing...</p><p>{progress}%</p></div></div>}

            {riskData.length > 0 && !loading && (
                <main className="flex-grow grid grid-cols-1 lg:grid-cols-3 gap-4 overflow-hidden">
                    <div className="lg:col-span-2 bg-gray-800 p-4 rounded-xl flex flex-col">
                        <div className="flex space-x-4 mb-4 flex-shrink-0">
                            <div className="flex-1">
                                <label htmlFor="asset-class" className="block text-sm font-medium text-gray-300">Asset Class</label>
                                <select id="asset-class" value={selectedAssetClass} onChange={e => setSelectedAssetClass(e.target.value)} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-600 bg-gray-700 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500 sm:text-sm rounded-md">
                                    {assetClasses.map(ac => <option key={ac}>{ac}</option>)}
                                </select>
                            </div>
                            <div className="flex-1">
                                 <label htmlFor="tenor" className="block text-sm font-medium text-gray-300">Tenor</label>
                                <select id="tenor" value={selectedTenor} onChange={e => setSelectedTenor(e.target.value)} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-600 bg-gray-700 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500 sm:text-sm rounded-md">
                                    {tenors.map(t => <option key={t}>{t}</option>)}
                                </select>
                            </div>
                        </div>
                        <div className="flex-grow min-h-0">
                           <PlotlyChart data={filteredChartData} mpcData={mpcDataStore} onMpcClick={setSelectedMpcMeeting} />
                        </div>
                    </div>
                    <div className="bg-gray-800 rounded-xl flex flex-col">
                        <div className="flex-grow p-4 min-h-0">
                            <MpcDetailsPanel meetingData={selectedMpcMeeting} onClose={() => setSelectedMpcMeeting(null)} />
                        </div>
                        <div className="flex-grow p-4 min-h-0 ag-theme-alpine-dark">
                           <AgGridReact rowData={riskData} columnDefs={columnDefs} defaultColDef={{ sortable: true, resizable: true, filter: true }} getRowId={params => params.data.id} />
                        </div>
                    </div>
                </main>
            )}
        </div>
    );
}

// --- App Wrapper to Load Dependencies ---
export default function App() {
    const [loaded, setLoaded] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadDependencies = async () => {
            try {
                await Promise.all([loadCss(LIBRARIES.agGridCss), loadCss(LIBRARIES.agGridTheme)]);
                await Promise.all([loadScript(LIBRARIES.xlsx), loadScript(LIBRARIES.plotly), loadScript(LIBRARIES.agGrid)]);
                await loadScript(LIBRARIES.agGridReact);
                setLoaded(true);
            } catch (err) {
                setError(err.message);
            }
        };
        loadDependencies();
    }, []);

    if (error) return <div className="w-full h-screen bg-red-900 text-white flex items-center justify-center p-4"><p>{error}</p></div>;
    if (!loaded) return <div className="w-full h-screen bg-gray-900 text-white flex items-center justify-center"><p className="text-xl animate-pulse">Loading Analysis Environment...</p></div>;

    return <RiskApp />;
}
