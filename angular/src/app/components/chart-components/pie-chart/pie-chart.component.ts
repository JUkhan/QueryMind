import { Component, input, output, model, OnInit, ChangeDetectionStrategy, effect, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgChartsModule } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';
import { DashboardService } from '../../../services/dashboard.service';

@Component({
  selector: 'app-pie-chart',
  standalone: true,
  imports: [CommonModule, NgChartsModule],
  templateUrl: './pie-chart.component.html',
  styleUrls: ['./pie-chart.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PieChartComponent implements OnInit {
  // Model signals for two-way binding
  readonly data = model<any[]>([]);
  readonly columns = model<string[]>([]);

  // Regular inputs
  readonly id = input<any>();
  readonly title = input<string>('Pie Chart');
  readonly query = input<string>();
  readonly type = input<string>();
  readonly isQueryEditable = input<boolean>();
  readonly json_config = input<any>();

  // Signal outputs
  readonly onRemove = output<any>();
  readonly onEdit = output<{ id: any, title: string }>();
  readonly onColumnsChange = output<string[]>();
  readonly onToggleQueryEditable = output<void>();

  private cdr = inject(ChangeDetectorRef);

  constructor(private dashboardService: DashboardService) {
    // React to data changes
    effect(() => {
      const data = this.data();
      const columns = this.columns();
      const type = this.type();
      if (data || columns || type) {
        this.updateChartData();
      }
    });

    // React to config changes
    effect(() => {
      const config = this.json_config();
      if (config?.chart) {
        this.applyChartConfig(config.chart);
        this.cdr.markForCheck();
      }
    });
  }
  public pieChartData: ChartConfiguration['data'] = {
    datasets: [],
    labels: []
  };

  public pieChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
      }
    }
  };

  public pieChartType: ChartType = 'pie';

  ngOnInit(): void {
    const data = this.data();
    const query = this.query();
    if (data && data.length === 0 && query) {
      this.dashboardService.getQueryResult2(query).subscribe(res => {
        // Now we can update data since it's a model signal
        if (res.data) {
          this.data.set(res.data);
          this.updateChartData();
        }
      });
    }
  }

  private updateChartData(): void {
    const data = this.data();
    const columns = this.columns();
    const type = this.type();
    const config = this.json_config();

    if (!data || data.length === 0 || !columns || columns.length < 2) {
      return;
    }

    // For pie charts, use first column as labels and second column as values
    const labels = data.map(item => item[columns[0]]);
    const values = data.map(item => {
      const value = item[columns[1]];
      return typeof value === 'number' ? value : parseFloat(value) || 0;
    });

    const colorScheme = config?.chart?.colorScheme || 'default';
    const borderWidth = config?.chart?.borderWidth ?? 2;

    this.pieChartData = {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: this.getColorsByScheme(values.length, colorScheme),
        borderColor: '#ffffff',
        borderWidth: borderWidth
      }]
    };

    // For donut chart
    if (type === 'donut') {
      this.pieChartType = 'doughnut';
    }
    this.cdr.markForCheck();
  }



  handleRemove(): void {
    this.onRemove.emit(this.id());
  }

  handleEdit(): void {
    this.onEdit.emit({ id: this.id(), title: this.title() });
  }

  handleToggleQueryEditable(): void {
    this.onToggleQueryEditable.emit();
  }

  private applyChartConfig(config: any): void {
    this.pieChartOptions = {
      responsive: config.responsive !== false,
      maintainAspectRatio: false,
      animation: config.animationEnabled !== false ? {
        duration: config.animationDuration || 1000,
        easing: config.animationEasing || 'easeOutQuad'
      } : false,
      plugins: {
        legend: {
          display: config.showLegend !== false,
          position: config.legendPosition || 'top',
        },
        tooltip: {
          enabled: config.showTooltip !== false
        }
      }
    };

    // Apply pie/donut specific settings
    if (config.cutout) {
      (this.pieChartOptions as any).cutout = config.cutout;
    }
    if (config.rotation !== undefined) {
      (this.pieChartOptions as any).rotation = config.rotation;
    }
    if (config.circumference !== undefined) {
      (this.pieChartOptions as any).circumference = config.circumference;
    }

    // Update chart data with new config
    this.updateChartData();
  }

  private getColorsByScheme(count: number, scheme: string = 'default'): string[] {
    const schemes: any = {
      default: this.dashboardService.generateColors(count, 0.7),
      pastel: [
        'rgba(255, 179, 186, 0.7)', 'rgba(255, 223, 186, 0.7)', 'rgba(255, 255, 186, 0.7)',
        'rgba(186, 255, 201, 0.7)', 'rgba(186, 225, 255, 0.7)', 'rgba(220, 190, 255, 0.7)'
      ],
      vibrant: [
        'rgba(255, 0, 0, 0.7)', 'rgba(255, 127, 0, 0.7)', 'rgba(255, 255, 0, 0.7)',
        'rgba(0, 255, 0, 0.7)', 'rgba(0, 0, 255, 0.7)', 'rgba(139, 0, 255, 0.7)'
      ],
      monochrome: Array.from({ length: count }, (_, i) => {
        const intensity = 255 - (i * (200 / count));
        return `rgba(${intensity}, ${intensity}, ${intensity}, 0.7)`;
      }),
      cool: [
        'rgba(0, 191, 255, 0.7)', 'rgba(30, 144, 255, 0.7)', 'rgba(65, 105, 225, 0.7)',
        'rgba(0, 255, 255, 0.7)', 'rgba(64, 224, 208, 0.7)', 'rgba(72, 209, 204, 0.7)'
      ],
      warm: [
        'rgba(255, 99, 71, 0.7)', 'rgba(255, 140, 0, 0.7)', 'rgba(255, 215, 0, 0.7)',
        'rgba(255, 69, 0, 0.7)', 'rgba(255, 160, 122, 0.7)', 'rgba(255, 127, 80, 0.7)'
      ]
    };

    const colors = schemes[scheme] || schemes.default;
    // Repeat colors if needed
    return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
  }
}
