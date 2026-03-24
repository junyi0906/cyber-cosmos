import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Event } from '../events/entities/event.entity';

export interface TimelineEvent {
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

export interface TimelineFilter {
  startDate?: number;
  endDate?: number;
  types?: string[];
  importance?: string[];
  limit?: number;
}

@Injectable()
export class TimelineService {
  constructor(
    @InjectRepository(Event)
    private eventRepository: Repository<Event>,
  ) {}

  async getTimelineEvents(filter: TimelineFilter = {}): Promise<TimelineEvent[]> {
    const {
      startDate,
      endDate,
      types,
      importance,
      limit = 100
    } = filter;

    const queryBuilder = this.eventRepository.createQueryBuilder('event');

    queryBuilder.orderBy('event.cycle', 'ASC');

    if (startDate !== undefined) {
      queryBuilder.andWhere('event.cycle >= :startDate', { startDate });
    }

    if (endDate !== undefined) {
      queryBuilder.andWhere('event.cycle <= :endDate', { endDate });
    }

    if (types && types.length > 0) {
      queryBuilder.andWhere('event.type IN (:...types)', { types });
    }

    if (importance && importance.length > 0) {
      queryBuilder.andWhere('event.importance IN (:...importance)', { importance });
    }

    queryBuilder.take(limit);

    const events = await queryBuilder.getMany();

    return events.map(event => this.mapToTimelineEvent(event));
  }

  async getMajorEvents(limit: number = 50): Promise<TimelineEvent[]> {
    const events = await this.eventRepository
      .createQueryBuilder('event')
      .where('event.importance IN (:...importanceLevels)', {
        importanceLevels: ['high', 'critical']
      })
      .orderBy('event.cycle', 'ASC')
      .take(limit)
      .getMany();

    return events.map(event => this.mapToTimelineEvent(event));
  }

  async getEventsByCivilization(civilizationId: string, limit: number = 100): Promise<TimelineEvent[]> {
    const events = await this.eventRepository
      .createQueryBuilder('event')
      .where(':civilizationId = ANY(event.participants)', { civilizationId })
      .orderBy('event.cycle', 'ASC')
      .take(limit)
      .getMany();

    return events.map(event => this.mapToTimelineEvent(event));
  }

  async getEventStatistics(): Promise<{
    total: number;
    byType: Record<string, number>;
    byImportance: Record<string, number>;
    byCycle: { cycle: number; count: number }[];
  }> {
    const total = await this.eventRepository.count();

    const byTypeResult = await this.eventRepository
      .createQueryBuilder('event')
      .select('event.type', 'type')
      .addSelect('COUNT(*)', 'count')
      .groupBy('event.type')
      .getRawMany();

    const byType: Record<string, number> = {};
    byTypeResult.forEach(item => {
      byType[item.type] = parseInt(item.count);
    });

    const byImportanceResult = await this.eventRepository
      .createQueryBuilder('event')
      .select('event.importance', 'importance')
      .addSelect('COUNT(*)', 'count')
      .groupBy('event.importance')
      .getRawMany();

    const byImportance: Record<string, number> = {};
    byImportanceResult.forEach(item => {
      byImportance[item.importance] = parseInt(item.count);
    });

    const byCycleResult = await this.eventRepository
      .createQueryBuilder('event')
      .select('event.cycle', 'cycle')
      .addSelect('COUNT(*)', 'count')
      .groupBy('event.cycle')
      .orderBy('event.cycle', 'ASC')
      .getRawMany();

    const byCycle = byCycleResult.map(item => ({
      cycle: item.cycle,
      count: parseInt(item.count)
    }));

    return { total, byType, byImportance, byCycle };
  }

  private mapToTimelineEvent(event: Event): TimelineEvent {
    return {
      id: event.id,
      title: event.title,
      content: event.description || event.title,
      start: event.cycle,
      end: event.endCycle,
      type: event.type,
      importance: event.importance as 'low' | 'medium' | 'high' | 'critical',
      participants: event.participants,
      location: event.location,
      metadata: event.metadata
    };
  }
}