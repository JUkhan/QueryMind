import { Component, input, output, model, OnInit, ChangeDetectionStrategy, effect, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgChartsModule } from 'ng2-charts';
import { ChartConfiguration, ChartType } from 'chart.js';
import { DashboardService } from '../../../services/dashboard.service';

@Component({
  selector: 'app-bar-chart',
  standalone: true,
  imports: [CommonModule, NgChartsModule],
  templateUrl: './bar-chart.component.html',
  styleUrls: ['./bar-chart.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class BarChartComponent implements OnInit {
  // Model signals for two-way binding
  readonly data = model<any[]>([]);
  readonly columns = model<string[]>([]);

  // Regular inputs
  readonly id = input<any>();
  readonly title = input<string>('Bar Chart');
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

    // Track isQueryEditable changes
    effect(() => {
      const editable = this.isQueryEditable();
      console.log(`Bar chart ${this.id()} - isQueryEditable changed to:`, editable);
      this.cdr.markForCheck();
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
  public barChartData: ChartConfiguration['data'] = {
    datasets: [],
    labels: []
  };

  public barChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    scales: {
      y: {
        beginAtZero: true
      }
    },
    plugins: {
      legend: { display: true },
    }
  };

  public barChartType: ChartType = 'bar';

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

    // For bar charts, we typically want to show one numeric column
    if (columns.length >= 2) {
      const column = columns[1]; // Use the second column as the value
      const values = data.map(item => {
        const value = item[column];
        return typeof value === 'number' ? value : parseFloat(value) || 0;
      });

      const colorScheme = config?.chart?.colorScheme || 'default';
      const borderWidth = config?.chart?.borderWidth ?? 1;
      const colors = this.getColorsByScheme(values.length, colorScheme);

      datasets.push({
        data: values,
        label: column,
        backgroundColor: colors.map(c => c.replace(/[\d.]+\)$/, '0.6)')),
        borderColor: colors,
        borderWidth: borderWidth
      });
    }

    this.barChartData = {
      labels: labels,
      datasets: datasets
    };
    console.log('Bar Chart Data:', this.barChartData);
    this.cdr.markForCheck();
  }

  handleRemove(): void {
    this.onRemove.emit(this.id());
  }

  handleEdit(): void {
    this.onEdit.emit({ id: this.id(), title: this.title() });
  }

  handleToggleQueryEditable(): void {
    console.log('Bar chart - Toggle query editable clicked, current state:', this.isQueryEditable());
    this.onToggleQueryEditable.emit();
  }

  private applyChartConfig(config: any): void {
    // Apply chart configuration options
    this.barChartOptions = {
      responsive: config.responsive !== false,
      maintainAspectRatio: config.maintainAspectRatio !== false,
      animation: config.animationEnabled !== false ? {
        duration: config.animationDuration || 1000,
        easing: config.animationEasing || 'easeOutQuad'
      } : false,
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
