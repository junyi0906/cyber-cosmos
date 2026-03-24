import { Injectable, Logger } from '@nestjs/common';
import { OnEvent } from '@nestjs/event-emitter';

// 天气类型枚举
export enum WeatherType {
  STORM = 'STORM',       // 资源风暴
  DARKNESS = 'DARKNESS', // 黑暗波动
  MATTER = 'MATTER',     // 暗物质浪潮
  CALM = 'CALM',         // 平静期
}

// 天气效果定义接口
export interface WeatherEffect {
  type: WeatherType;
  name: string;
  description: string;
  productionModifier: number;   // 产量修正（百分比）
  visionModifier: number;       // 视野修正（百分比）
  techSpeedModifier: number;    // 科技速度修正（百分比）
  tradeRiskModifier: number;    // 贸易风险修正（百分比）
  energyConsumptionModifier: number; // 能量消耗修正（百分比）
}

// 文明属性接口
export interface CivilizationAttributes {
  id: string;
  name: string;
  baseProduction: number;       // 基础产量
  baseVision: number;           // 基础视野
  baseTechSpeed: number;        // 基础科技速度
  baseTradeRisk: number;        // 基础贸易风险
  baseEnergyConsumption: number; // 基础能量消耗
  
  currentProduction: number;    // 当前产量
  currentVision: number;        // 当前视野
  currentTechSpeed: number;     // 当前科技速度
  currentTradeRisk: number;     // 当前贸易风险
  currentEnergyConsumption: number; // 当前能量消耗
  
  activeEffects: Map<WeatherType, WeatherEffect>; // 活跃的天气效果
}

// 受影响星区接口
export interface AffectedSector {
  id: string;
  name: string;
  civilizationIds: string[];
  coordinates: { x: number; y: number; z: number };
}

// 天气事件接口
export interface WeatherEvent {
  type: WeatherType;
  affectedSectors: AffectedSector[];
  startTime: number;
  duration: number;
  intensity: number;
}

// 预定义的天气效果配置
const WEATHER_EFFECTS_CONFIG: Record<WeatherType, WeatherEffect> = {
  [WeatherType.STORM]: {
    type: WeatherType.STORM,
    name: '资源风暴',
    description: '宇宙能量激增，采矿效率大幅提升，但航线风险增加',
    productionModifier: 0.5,      // +50% 产量
    visionModifier: 0,            // 视野不变
    techSpeedModifier: 0,         // 科技速度不变
    tradeRiskModifier: 0.3,       // +30% 贸易风险
    energyConsumptionModifier: 0, // 能量消耗不变
  },
  [WeatherType.DARKNESS]: {
    type: WeatherType.DARKNESS,
    name: '黑暗波动',
    description: '神秘的黑暗力量笼罩星区，视野受限，外交信任度衰减加速',
    productionModifier: 0,        // 产量不变
    visionModifier: -0.3,         // -30% 视野
    techSpeedModifier: 0,         // 科技速度不变
    tradeRiskModifier: 0.1,       // +10% 贸易风险
    energyConsumptionModifier: 0, // 能量消耗不变
  },
  [WeatherType.MATTER]: {
    type: WeatherType.MATTER,
    name: '暗物质浪潮',
    description: '暗物质浪潮席卷宇宙，科研速度提升，但能量消耗增加',
    productionModifier: 0,        // 产量不变
    visionModifier: 0,            // 视野不变
    techSpeedModifier: 0.2,       // +20% 科技速度
    tradeRiskModifier: 0,         // 贸易风险不变
    energyConsumptionModifier: 1.0, // +100% 能量消耗（翻倍）
  },
  [WeatherType.CALM]: {
    type: WeatherType.CALM,
    name: '平静期',
    description: '宇宙处于平静状态，一切正常',
    productionModifier: 0,
    visionModifier: 0,
    techSpeedModifier: 0,
    tradeRiskModifier: 0,
    energyConsumptionModifier: 0,
  },
};

@Injectable()
export class EffectsService {
  private readonly logger = new Logger(EffectsService.name);
  
  // 存储所有文明的属性状态
  private civilizationAttributes: Map<string, CivilizationAttributes> = new Map();
  
  // 存储每个星区当前受到的天气影响
  private sectorWeatherEffects: Map<string, Set<WeatherType>> = new Map();
  
  // 当前活跃的天气事件
  private activeWeatherEvents: Map<string, WeatherEvent> = new Map();

  /**
   * 获取天气效果配置
   */
  getWeatherEffectConfig(type: WeatherType): WeatherEffect {
    return { ...WEATHER_EFFECTS_CONFIG[type] };
  }

  /**
   * 获取所有天气效果配置
   */
  getAllWeatherEffectConfigs(): Record<WeatherType, WeatherEffect> {
    return { ...WEATHER_EFFECTS_CONFIG };
  }

  /**
   * 注册或更新文明
   */
  registerCivilization(civilization: {
    id: string;
    name: string;
    baseProduction: number;
    baseVision: number;
    baseTechSpeed: number;
    baseTradeRisk?: number;
    baseEnergyConsumption?: number;
  }): CivilizationAttributes {
    const existingAttrs = this.civilizationAttributes.get(civilization.id);
    
    const attrs: CivilizationAttributes = {
      id: civilization.id,
      name: civilization.name,
      baseProduction: civilization.baseProduction,
      baseVision: civilization.baseVision,
      baseTechSpeed: civilization.baseTechSpeed,
      baseTradeRisk: civilization.baseTradeRisk ?? 0,
      baseEnergyConsumption: civilization.baseEnergyConsumption ?? 1,
      currentProduction: civilization.baseProduction,
      currentVision: civilization.baseVision,
      currentTechSpeed: civilization.baseTechSpeed,
      currentTradeRisk: civilization.baseTradeRisk ?? 0,
      currentEnergyConsumption: civilization.baseEnergyConsumption ?? 1,
      activeEffects: existingAttrs?.activeEffects ?? new Map(),
    };

    this.civilizationAttributes.set(civilization.id, attrs);
    
    // 如果有活跃效果，重新计算
    if (attrs.activeEffects.size > 0) {
      this.recalculateAttributes(civilization.id);
    }

    this.logger.log(`Registered civilization: ${civilization.name} (${civilization.id})`);
    return this.getCivilizationAttributes(civilization.id)!;
  }

  /**
   * 获取文明属性
   */
  getCivilizationAttributes(civilizationId: string): CivilizationAttributes | undefined {
    const attrs = this.civilizationAttributes.get(civilizationId);
    if (!attrs) return undefined;
    return { ...attrs, activeEffects: new Map(attrs.activeEffects) };
  }

  /**
   * 应用天气效果到受影响星区的文明
   */
  applyWeatherEffects(
    weatherType: WeatherType,
    affectedSectors: AffectedSector[],
    intensity: number = 1.0
  ): {
    affectedCivilizations: string[];
    effects: WeatherEffect;
  } {
    const effectConfig = this.getWeatherEffectConfig(weatherType);
    const affectedCivilizations: string[] = [];

    // 根据强度调整效果
    const scaledEffect: WeatherEffect = {
      ...effectConfig,
      productionModifier: effectConfig.productionModifier * intensity,
      visionModifier: effectConfig