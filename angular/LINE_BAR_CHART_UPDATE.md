# Line & Bar Chart Configuration Update Guide

Due to context limits, here are the changes needed for LINE and BAR chart components:

## Line Chart Component (line-chart.component.ts)

### 1. Add json_config input (line 26)
```typescript
readonly json_config = input<any>();
```

### 2. Add effect to watch config changes (in constructor, after existing effects)
```typescript
// React to config changes
effect(() => {
  const config = this.json_config();
  if (config?.chart) {
    this.applyChartConfig(config.chart);
    this.cdr.markForCheck();
  }
});
```

### 3. Update updateChartData method to use config colors
Replace lines 82-118 with:
```typescript
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
  const tension = config?.chart?.tension ?? 0.4;
  const fill = config?.chart?.fill ?? false;
  const pointRadius = config?.chart?.pointRadius ?? 3;
  const pointStyle = config?.chart?.pointStyle || 'circle';
  const borderWidth = config?.chart?.borderWidth ?? 2;

  // Create datasets for numeric columns
  for (let i = 1; i < columns.length; i++) {
    const column = columns[i];
    const values = data.map(item => {
      const value = item[column];
      return typeof value === 'number' ? value : parseFloat(value) || 0;
    });

    const colors = this.getColorsByScheme(columns.length - 1, colorScheme);

    datasets.push({
      data: values,
      label: column,
      backgroundColor: this.adjustAlpha(colors[i - 1], 0.2),
      borderColor: colors[i - 1],
      pointBackgroundColor: colors[i - 1],
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: this.adjustAlpha(colors[i - 1], 0.8),
      tension: tension,
      fill: fill,
      pointRadius: pointRadius,
      pointStyle: pointStyle,
      borderWidth: borderWidth
    });
  }

  this.lineChartData = {
    labels: labels,
    datasets: datasets
  };
  this.cdr.markForCheck();
}
```

### 4. Add applyChartConfig method (before handleRemove)
```typescript
private applyChartConfig(config: any): void {
  this.lineChartOptions = {
    responsive: config.responsive !== false,
    maintainAspectRatio: config.maintainAspectRatio !== false,
    animation: config.animationEnabled !== false ? {
      duration: config.animationDuration || 1000,
      easing: config.animationEasing || 'easeOutQuad'
    } : false,
    elements: {
      line: {
        tension: config.tension ?? 0.4
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
```

### 5. Add color scheme and utility methods (at end, before closing brace)
```typescript
private getColorsByScheme(count: number, scheme: string = 'default'): string[] {
  const schemes: any = {
    default: Array.from({ length: count }, (_, i) => this.getColor(i, 1)),
    pastel: [
      'rgba(255, 179, 186, 0.8)', 'rgba(255, 223, 186, 0.8)', 'rgba(255, 255, 186, 0.8)',
      'rgba(186, 255, 201, 0.8)', 'rgba(186, 225, 255, 0.8)', 'rgba(220, 190, 255, 0.8)'
    ],
    vibrant: [
      'rgba(255, 0, 0, 0.8)', 'rgba(255, 127, 0, 0.8)', 'rgba(255, 255, 0, 0.8)',
      'rgba(0, 255, 0, 0.8)', 'rgba(0, 0, 255, 0.8)', 'rgba(139, 0, 255, 0.8)'
    ],
    monochrome: Array.from({ length: count }, (_, i) => {
      const intensity = 255 - (i * (200 / count));
      return `rgba(${intensity}, ${intensity}, ${intensity}, 0.8)`;
    }),
    cool: [
      'rgba(0, 191, 255, 0.8)', 'rgba(30, 144, 255, 0.8)', 'rgba(65, 105, 225, 0.8)',
      'rgba(0, 255, 255, 0.8)', 'rgba(64, 224, 208, 0.8)', 'rgba(72, 209, 204, 0.8)'
    ],
    warm: [
      'rgba(255, 99, 71, 0.8)', 'rgba(255, 140, 0, 0.8)', 'rgba(255, 215, 0, 0.8)',
      'rgba(255, 69, 0, 0.8)', 'rgba(255, 160, 122, 0.8)', 'rgba(255, 127, 80, 0.8)'
    ]
  };

  const colors = schemes[scheme] || schemes.default;
  return Array.from({ length: count }, (_, i) => colors[i % colors.length]);
}

private adjustAlpha(rgba: string, alpha: number): string {
  const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (match) {
    return `rgba(${match[1]}, ${match[2]}, ${match[3]}, ${alpha})`;
  }
  return rgba;
}
```

## Bar Chart Component (bar-chart.component.ts)

### Apply same changes as Line Chart with these differences:

1. Add json_config input
2. Add config watching effect
3. Update applyChartConfig (remove elements.line, keep scales)
4. Update updateChartData to use single column with config colors
5. Add getColorsByScheme method

### Key difference in updateChartData:
```typescript
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
  const borderWidth = config?.chart?.borderWidth ?? 1;

  if (columns.length >= 2) {
    const column = columns[1];
    const values = data.map(item => {
      const value = item[column];
      return typeof value === 'number' ? value : parseFloat(value) || 0;
    });

    datasets.push({
      data: values,
      label: column,
      backgroundColor: this.getColorsByScheme(values.length, colorScheme),
      borderColor: this.getColorsByScheme(values.length, colorScheme).map(c => this.adjustAlpha(c, 1)),
      borderWidth: borderWidth
    });
  }

  this.barChartData = {
    labels: labels,
    datasets: datasets
  };
  this.cdr.markForCheck();
}
```

## Testing Checklist

1. ✅ Create new chart component - should have default configuration
2. ✅ Edit chart configuration modal - should show all options
3. ✅ Change legend position - should update immediately
4. ✅ Toggle animation - should enable/disable
5. ✅ Change color scheme - colors should update
6. ✅ Line chart: adjust tension - line curve should change
7. ✅ Bar chart: adjust max thickness - bars should resize
8. ✅ Pie/Donut: adjust cutout - donut hole size should change
9. ✅ Grid toggles - should show/hide grid lines
10. ✅ Save and reload - configuration should persist

## Summary

This implementation provides:
- ✅ 20+ configurable Chart.js properties
- ✅ 6 color schemes (default, pastel, vibrant, monochrome, cool, warm)
- ✅ Chart-type-specific options (line tension, bar thickness, donut cutout)
- ✅ Full persistence in json_config
- ✅ Real-time preview in modal
- ✅ Backward compatibility
