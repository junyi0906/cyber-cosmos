import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Timeline, DataSet } from 'vis-timeline/standalone';
import 'vis-timeline/styles/vis-timeline-graph2d.css';

interface TimelineEvent {
  id: string;
  title: string;
  content: string;
  start: number;
  end?: number;
  type: string;
  importance: 'low' | 'medium' | 'high' | 'critical';
  participants?: string[];
  location?: { x: number; y: number };
  metadata?: Record<string, unknown>;
}

interface TimelineFilter {
  startDate?: number;
  endDate?: number;
  types?: string[];
  importance?: string[];
  limit?: number;
}

interface EventStatistics {
  total: number;
  byType: Record<string, number>;
  byImportance: Record<string, number>;
  byCycle: { cycle: number; count: number }[];
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  war: '#e74c3c',
  diplomacy: '#3498db',
  trade: '#2ecc71',
  discovery: '#9b59b6',
  catastrophe: '#e67e22',
  alliance: '#1abc9c',
  collapse: '#c0392b',
  expansion: '#27ae60',
  technology: '#8e44ad',
  default: '#95a5a6',
};

const IMPORTANCE_STYLES: Record<string, { borderWidth: number; fontSize: string }> = {
  critical: { borderWidth: 4, fontSize: '14px' },
  high: { borderWidth: 3, fontSize: '13px' },
  medium: { borderWidth: 2, fontSize: '12px' },
  low: { borderWidth: 1, fontSize: '11px' },
};

const TimelineView: React.FC = () => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const timelineInstance = useRef<Timeline | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [statistics, setStatistics] = useState<EventStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null);
  const [filter, setFilter] = useState<TimelineFilter>({ limit: 200 });
  const [availableTypes, setAvailableTypes] = useState<string[]>([]);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filter.startDate) params.append('startDate', filter.startDate.toString());
      if (filter.endDate) params.append('endDate', filter.endDate.toString());
      if (filter.types?.length) params.append('types', filter.types.join(','));
      if (filter.importance?.length) params.append('importance', filter.importance.join(','));
      if (filter.limit) params.append('limit', filter.limit.toString());

      const response = await fetch(`/api/observatory/timeline?${params}`);
      const result = await response.json();

      if (result.success) {
        setEvents(result.data);
      } else {
        throw new Error(result.message || 'Failed to fetch timeline events');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [filter]);

  const fetchStatistics = useCallback(async () => {
    try {
      const response = await fetch('/api/observatory/timeline/statistics');
      const result = await response.json();
      if (result.success) {
        setStatistics(result.data);
        setAvailableTypes(Object.keys(result.data.byType));
      }
    } catch (err) {
      console.error('Failed to fetch statistics:', err);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
    fetchStatistics();
  }, [fetchEvents, fetchStatistics]);

  useEffect(() => {
    if (!timelineRef.current || events.length === 0) return;

    const items = new DataSet(
      events.map(event => {
        const style = IMPORTANCE_STYLES[event.importance] || IMPORTANCE_STYLES.medium;
        const color = EVENT_TYPE_COLORS[event.type] || EVENT_TYPE_COLORS.default;

        return {
          id: event.id,
          content: event.title,
          start: event.start,
          end: event.end,
          type: event.end ? 'range' : 'point',
          className: `timeline-event-${event.importance}`,
          style: `
            background-color: ${color};
            border-color: ${color};
            border-width: ${style.borderWidth}px;
            font-size: ${style.fontSize};
          `,
          data: event,
        };
      })
    );

    const options = {
      width: '100%',
      height: '400px',
      margin: {
        item: 10,
        axis: 5,
      },
      stack: true,
      stackSubgroups: true,
      orientation: {
        axis: 'top',
        item: 'top',
      },
      zoomMin: 1,
      zoomMax: 10000,
      locale: 'zh-CN',
      format: {
        minorLabels: {
          millisecond: 'SSS',
          second: 's',
          minute: 'HH:mm',
          hour: 'HH:mm',
          weekday: 'ddd D',
          day: 'D',
          week: 'w',
          month: 'MMM',
          year: 'YYYY',
        },
        majorLabels: {
          millisecond: 'HH:mm:ss',
          second: 'D MMMM HH:mm',
          minute: 'ddd D MMMM',
          hour: 'ddd D MMMM',
          weekday: 'MMMM YYYY',
          day: 'MMMM YYYY',
          week: 'MMMM YYYY',
          month: 'YYYY',
          year: '',
        },
      },
      tooltip: {
        followMouse: true,
        overflowMethod: 'cap',
        template: (data: { data: TimelineEvent }) => {
          const event = data.data;
          return `
            <div class="timeline-tooltip">
              <div class="tooltip-title">${event.title}</div>
              <div class="tooltip-type">类型: ${event.type}</div>
              <div class="tooltip-importance">重要性: ${event.importance}</div>
              <div class="tooltip-cycle">周期: ${event.start}${event.end ? ` - ${event.end}` : ''}</div>
              ${event.participants?.length ? `<div class="tooltip-participants">参与者: ${event.participants.length} 个文明</div>` : ''}
            </div>
          `;
        },
      },
    };

    if (timelineInstance.current) {
      timelineInstance.current.destroy();
    }

    timelineInstance.current = new Timeline(timelineRef.current, items, options);

    timelineInstance.current.on('select', (properties: { items: string[] }) => {
      if (properties.items.length > 0) {
        const selectedId = properties.items[0];
        const event = events.find(e => e.id === selectedId);
        setSelectedEvent(event || null);
      } else {
        setSelectedEvent(null);
      }
    });

    return () => {
      if (timelineInstance.current) {
        timelineInstance.current.destroy();
        timelineInstance.current = null;
      }
    };
  }, [events]);

  const handleTypeFilter = (type: string, checked: boolean) => {
    setFilter(prev => ({
      ...prev,
      types: checked
        ? [...(prev.types || []), type]
        : (prev.types || []).filter(t => t !== type),
    }));
  };

  const handleImportanceFilter = (importance: string, checked: boolean) => {
    setFilter(prev => ({
      ...prev,
      importance: checked
        ? [...(prev.importance || []), importance]
        : (prev.importance || []).filter(i => i !== importance),
    }));
  };

  const handleZoomToFit = () => {
    if (timelineInstance.current) {
      timelineInstance.current.fit();
    }
  };

  const handleZoomIn = () => {
    if (timelineInstance.current) {
      timelineInstance.current.zoomIn(0.5);
    }
  };

  const handleZoomOut = () => {
    if (timelineInstance.current) {
      timelineInstance.current.zoomOut(0.5);
    }
  };

  return (
    <div className="timeline-view">
      <div className="timeline-header">
        <h2>宇宙演化时间线</h2>
        <div className="timeline-controls">
          <button onClick={handleZoomToFit} title="适应视图">
            ⊡
          </button>
          <button onClick={handleZoomIn} title="放大">
            +
          </button>
          <button onClick={handleZoomOut} title="缩小">
            −
          </button>
        </div>
      </div>

      <div className="timeline-filters">
        <div className="filter-group">
          <h4>事件类型</h4>
          <div className="filter-options">
            {availableTypes.map(type => (
              <label key={type} className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={filter.types?.includes(type) || false}
                  onChange={(e) => handleTypeFilter(type, e