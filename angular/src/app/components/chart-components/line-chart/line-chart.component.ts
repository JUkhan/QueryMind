import { Component, input, output, model, OnInit, ChangeDetectionStrategy, effect, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgChartsModule } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';
import { DashboardService } from '../../../services/dashboard.service';

@Component({
  selector: 'app-line-chart',
  standalone: true,
  imports: [CommonModule, NgChartsModule],
  templateUrl: './line-chart.component.html',
  styleUrls: ['./line-chart.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LineChartComponent implements OnInit {
  // Model signals for two-way binding
  readonly data = model<any[]>([]);
  readonly columns = model<string[]>([]);

  // Regular inputs
  readonly id = input<any>();
  readonly title = input<string>('Line Chart');
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
      if (data || columns) {
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
  public lineChartData: ChartConfiguration['data'] = {
    datasets: [],
    labels: []
  };

  public lineChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    elements: {
      line: {
        tension: 0.5
      }
    },
    scales: {
      y: {
        position: 'left',
      }
    },
    plugins: {
      legend: { display: true },
    }
  };

  public lineChartType: ChartType = 'line';

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
    const config = this.json_config();

    if (!data || data.length === 0 || !columns || columns.length < 2) {
      return;
    }

    const labels = data.map(item => item[columns[0]]);
    const datasets = [];

    const colorScheme = config?.chart?.colorScheme || 'default';
    const borderWidth = config?.chart?.borderWidth ?? 2;
    const schemeColors = this.getColorsByScheme(columns.length - 1, colorScheme);

    // Create datasets for numeric columns
    for (let i = 1; i < columns.length; i++) {
      const column = columns[i];
      const values = data.map(item => {
        const value = item[column];
        return typeof value === 'number' ? value : parseFloat(value) || 0;
      });

      const baseColor = schemeColors[i - 1];

      datasets.push({
        data: values,
        label: column,
        backgroundColor: baseColor.replace(/[\d.]+\)$/, '0.2)'),
        borderColor: baseColor,
        pointBackgroundColor: baseColor,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: baseColor.replace(/[\d.]+\)$/, '0.8)'),
        borderWidth: borderWidth
      });
    }

    this.lineChartData = {
      labels: labels,
      datasets: datasets
    };
    this.cdr.markForCheck();
  }

  private getColorsByScheme(count: number, scheme: string = 'default'): string[] {
    const schemes: any = {
      default: [
        'rgba(54, 162, 235, 0.7)',   // Blue
        'rgba(255, 99, 132, 0.7)',   // Red
        'rgba(255, 205, 86, 0.7)',   // Yellow
        'rgba(75, 192, 192, 0.7)',   // Green
        'rgba(153, 102, 255, 0.7)',  // Purple
        'rgba(255, 159, 64, 0.7)',   // Orange
      ],
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
    console.log('***Applying chart config:', config);
    // Apply chart configuration options
    this.lineChartOptions = {
      responsive: config.responsive !== false,
      //@ts-ignore
      fill: config.fill || false,
      //@ts-ignore
      pointStyle: config.pointStyle || 'circle',
      pointRadius: config.pointRadius || 3,
      maintainAspectRatio: false,
      animation: config.animationEnabled !== false ? {
        duration: config.animationDuration || 1000,
        easing: config.animationEasing || 'easeOutQuad'
      } : false,
      elements: {
        line: {
          tension: config.tension ?? 0.5
        }
      },
      scales: {
        x: {
          display: config.showXAxis !== false,
          grid: {
            display: config.showGrid !== false,
            color: config.gridColor || 'rgba(0, 0, 0, 0.1)'
          }
        },
        y: {
          display: config.showYAxis !== false,
          position: 'left',
          beginAtZero: config.beginAtZero !== false,
          grid: {
            display: config.showGrid !== false,
            color: config.gridColor || 'rgba(0, 0, 0, 0.1)'
          }
        }
      },
      plugins: {
        legend: {
          display: config.showLegend !== false,
          position: config.legendPosition || 'top'
        },
        tooltip: {
          enabled: config.showTooltip !== false
        }
      }
    };

    this.updateChartData();
  }
}
