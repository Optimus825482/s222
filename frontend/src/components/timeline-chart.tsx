import React from 'react';
import { format } from 'date-fns';
import { tr } from 'date-fns/locale';

interface TimelineEvent {
  id: string;
  timestamp: Date;
  eventType: string;
  content: string;
  agent: string;
}

interface TimelineChartProps {
  events: TimelineEvent[];
}

export function TimelineChart({ events }: TimelineChartProps) {
  if (events.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-slate-500">Henüz zaman çizelgesi verisi yok</p>
      </div>
    );
  }

  // Zaman dilimi hesaplamaları
  const sortedEvents = [...events].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  const startTime = sortedEvents[0].timestamp;
  const endTime = sortedEvents[sortedEvents.length - 1].timestamp;
  const durationMs = endTime.getTime() - startTime.getTime();

  // Zaman çizelgesi yüksekliğini ayarla
  const timelineHeight = Math.max(200, events.length * 30);

  return (
    <div className="w-full">
      <div className="mb-2">
        <h3 className="text-xs font-semibold text-slate-200 mb-2">Zaman Çizelgesi</h3>
        <div className="text-xs text-slate-400">
          {format(startTime, 'HH:mm:ss', { locale: tr })} - {format(endTime, 'HH:mm:ss', { locale: tr })}
        </div>
      </div>
      
      <div 
        className="relative w-full bg-slate-900/30 border border-border rounded-lg p-3 overflow-x-auto"
        style={{ height: `${timelineHeight}px` }}
      >
        {/* Zaman ölçeği */}
        <div className="absolute top-0 left-0 right-0 h-6 border-b border-slate-700 flex items-center">
          <div className="absolute left-0 text-[10px] text-slate-400">0s</div>
          <div className="absolute left-1/4 text-[10px] text-slate-400">
            {durationMs > 0 ? `${(durationMs / 4000).toFixed(1)}s` : '0s'}
          </div>
          <div className="absolute left-1/2 text-[10px] text-slate-400">
            {durationMs > 0 ? `${(durationMs / 2000).toFixed(1)}s` : '0s'}
          </div>
          <div className="absolute left-3/4 text-[10px] text-slate-400">
            {durationMs > 0 ? `${(3 * durationMs / 4000).toFixed(1)}s` : '0s'}
          </div>
          <div className="absolute right-0 text-[10px] text-slate-400">
            {durationMs > 0 ? `${(durationMs / 1000).toFixed(1)}s` : '0s'}
          </div>
        </div>

        {/* Olay çizgileri */}
        <div className="relative pt-6">
          {sortedEvents.map((event, index) => {
            const elapsed = event.timestamp.getTime() - startTime.getTime();
            const positionPercent = durationMs > 0 ? (elapsed / durationMs) * 100 : 0;
            
            // Renk kodlaması
            let bgColor = 'bg-blue-500';
            if (event.eventType.includes('error')) bgColor = 'bg-red-500';
            else if (event.eventType.includes('complete')) bgColor = 'bg-green-500';
            else if (event.eventType.includes('start')) bgColor = 'bg-yellow-500';
            else if (event.eventType.includes('think')) bgColor = 'bg-purple-500';
            else if (event.eventType.includes('search')) bgColor = 'bg-indigo-500';
            
            return (
              <div 
                key={event.id}
                className="absolute w-2 h-2 rounded-full"
                style={{
                  top: `${positionPercent}%`,
                  left: '10%',
                  transform: 'translateY(-50%)',
                }}
              >
                <div className={`${bgColor} w-2 h-2 rounded-full animate-pulse`} />
              </div>
            );
          })}
          
          {/* Ana çizgi */}
          <div 
            className="absolute w-0.5 bg-gradient-to-b from-cyan-400 to-transparent"
            style={{
              left: '10%',
              top: '24px',
              height: `calc(100% - 24px)`,
            }}
          />
        </div>

        {/* Olay detayları */}
        <div className="ml-20 mt-[-24px]">
          {sortedEvents.map((event, index) => {
            const elapsed = event.timestamp.getTime() - startTime.getTime();
            const positionPercent = durationMs > 0 ? (elapsed / durationMs) * 100 : 0;
            
            return (
              <div 
                key={event.id}
                className="absolute left-0 right-0 text-xs"
                style={{ top: `${positionPercent}%`, transform: 'translateY(-50%)' }}
              >
                <div className="flex items-center gap-2 bg-slate-800/60 px-2 py-1 rounded border border-slate-700">
                  <span className="text-cyan-300 font-medium">{event.agent}</span>
                  <span className="text-slate-300 truncate flex-1">{event.content.substring(0, 60)}{event.content.length > 60 ? '...' : ''}</span>
                  <span className="text-slate-500">{format(event.timestamp, 'HH:mm:ss.SSS', { locale: tr })}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}