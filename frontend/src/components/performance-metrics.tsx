import React from 'react';

interface PerformanceMetric {
  name: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
}

interface PerformanceMetricsProps {
  metrics: PerformanceMetric[];
}

export function PerformanceMetrics({ metrics }: PerformanceMetricsProps) {
  return (
    <div className="w-full">
      <h3 className="text-xs font-semibold text-slate-200 mb-2">Performans Metrikleri</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {metrics.map((metric, index) => (
          <div 
            key={index} 
            className="bg-slate-900/30 border border-border rounded-lg p-2.5"
          >
            <div className="flex items-baseline justify-between">
              <span className="text-[10px] text-slate-400">{metric.name}</span>
              {metric.trend && (
                <span className={`text-[8px] ${
                  metric.trend === 'up' ? 'text-green-400' : 
                  metric.trend === 'down' ? 'text-red-400' : 'text-slate-400'
                }`}>
                  {metric.trend === 'up' ? '↗' : metric.trend === 'down' ? '↘' : '→'}
                </span>
              )}
            </div>
            <div className="text-sm font-medium text-slate-100 mt-1">
              {metric.value}{metric.unit && <span className="text-xs text-slate-400 ml-1">{metric.unit}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}