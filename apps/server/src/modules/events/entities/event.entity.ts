import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
} from 'typeorm';

@Entity('events')
export class Event {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  title: string;

  @Column({ type: 'text', nullable: true })
  description: string;

  @Column()
  type: string;

  @Column({ default: 'medium' })
  importance: string;

  @Column({ type: 'int' })
  cycle: number;

  @Column({ type: 'int', nullable: true })
  endCycle: number;

  @Column({ type: 'simple-array', nullable: true })
  participants: string[];

  @Column({ type: 'jsonb', nullable: true })
  location: { x: number; y: number };

  @Column({ type: 'jsonb', nullable: true })
  metadata: Record<string, unknown>;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}