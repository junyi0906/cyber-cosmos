import { Controller, Get, Query, Param } from '@nestjs/common';
import { TimelineService, TimelineFilter } from './timeline.service';

@Controller('api/observatory')
export class TimelineController {
  constructor(private readonly timelineService: TimelineService) {}

  @Get('timeline')
  async getTimeline(
    @Query('startDate') startDate?: string,
    @Query('endDate') endDate?: string,
    @Query('types') types?: string,
    @Query('importance') importance?: string,
    @Query('limit') limit?: string,
  ) {
    const filter: TimelineFilter = {
      startDate: startDate ? parseInt(startDate) : undefined,
      endDate: endDate ? parseInt(endDate) : undefined,
      types: types ? types.split(',') : undefined,
      importance: importance ? importance.split(',') : undefined,
      limit: limit ? parseInt(limit) : 100,
    };

    const events = await this.timelineService.getTimelineEvents(filter);
    return {
      success: true,
      data: events,
      meta: {
        count: events.length,
        filter
      }
    };
  }

  @Get('timeline/major')
  async getMajorEvents(@Query('limit') limit?: string) {
    const events = await this.timelineService.getMajorEvents(
      limit ? parseInt(limit) : 50
    );
    return {
      success: true,
      data: events,
      meta: {
        count: events.length
      }
    };
  }

  @Get('timeline/civilization/:id')
  async getCivilizationTimeline(
    @Param('id') civilizationId: string,
    @Query('limit') limit?: string
  ) {
    const events = await this.timelineService.getEventsByCivilization(
      civilizationId,
      limit ? parseInt(limit) : 100
    );
    return {
      success: true,
      data: events,
      meta: {
        civilizationId,
        count: events.length
      }
    };
  }

  @Get('timeline/statistics')
  async getStatistics() {
    const stats = await this.timelineService.getEventStatistics();
    return {
      success: true,
      data: stats
    };
  }
}