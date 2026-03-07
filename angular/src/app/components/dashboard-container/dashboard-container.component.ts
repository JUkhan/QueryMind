import { Component, OnInit, OnDestroy, signal, computed, effect, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { KtdGridModule, KtdGridLayout, KtdGridLayoutItem, ktdTrackById } from '@katoid/angular-grid-layout';
import { TableComponentComponent } from '../table-component/table-component.component';
import { LineChartComponent } from '../chart-components/line-chart/line-chart.component';
import { BarChartComponent } from '../chart-components/bar-chart/bar-chart.component';
import { PieChartComponent } from '../chart-components/pie-chart/pie-chart.component';
import { DashboardService, SComponent } from '../../services/dashboard.service';

interface ComponentType {
  type: string;
  name: string;
  icon?: string;
  defaultTitle: string;
}

@Component({
  selector: 'app-dashboard-container',
  standalone: true,
  imports: [CommonModule, FormsModule, KtdGridModule, TableComponentComponent, LineChartComponent, BarChartComponent, PieChartComponent],
  templateUrl: './dashboard-container.component.html',
  styleUrls: ['./dashboard-container.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardContainerComponent implements OnInit, OnDestroy {
  // Use signals for reactive state
  components = computed(() => this.dashboardService.components());
  showAddMenu = signal(false);
  componentTypes = signal<ComponentType[]>([]);
  editingComponent = signal<any>(null);
  editTitle = signal('');
  editChartConfig = signal<any>(null);
  isAdding = computed(() => this.dashboardService.data().length > 0);
  editableComponentId = computed(() => this.dashboardService.editableComponentId());

  // Grid layout configuration
  cols = signal(12);
  rowHeight = signal(100);
  gap = signal(16);
  gridLayout = signal<KtdGridLayout>([]);

  // Track by function for grid items
  trackById = ktdTrackById;

  // Computed signal to map grid layout items to components
  gridComponents = computed(() => {
    const layout = this.gridLayout();
    const components = this.components();
    return layout
      .map(item => {
        const component = components.find(c => String(c.id) === item.id);
        if (!component) return null;
        return { layout: item, component };
      })
      .filter((item): item is { layout: KtdGridLayoutItem; component: SComponent } => item !== null);
  });

  constructor(private dashboardService: DashboardService) {
    // Use effect to react to dashboard state changes
    effect(() => {
      const types = this.dashboardService.types();
      this.updateComponentTypes(types);
    }, { allowSignalWrites: true });

    // Track component changes and sync grid layout only when components are added/removed
    effect(() => {
      const components = this.components();
      const currentLayout = this.gridLayout();

      console.log('Dashboard container - Components updated:', components.length, 'Layout items:', currentLayout.length);

      // Only update grid layout if component count changed or layout is empty
      if (components.length !== currentLayout.length) {
        console.log('Component count changed, updating grid layout');
        this.updateGridLayout(components);
      }
    }, { allowSignalWrites: true });
  }

  ngOnInit(): void {
    // Load existing dashboard data
    this.loadDashboardData();
  }

  /**
   * Migration utility: Migrate grid layout from old columns to json_config
   * Call this method to migrate existing dashboard components
   */
  migrateGridLayoutToJsonConfig(): void {
    const components = this.components();
    let migratedCount = 0;
    let skippedCount = 0;

    console.log('🔄 Starting grid layout migration...');

    components.forEach(component => {
      // Skip if already has grid in json_config
      if (component.json_config?.grid) {
        console.log(`⏭️  Skipping component ${component.id} - already has grid in json_config`);
        skippedCount++;
        return;
      }

      // Check if has old grid columns
      if ((component as any).grid_x !== undefined && (component as any).grid_y !== undefined) {
        const existingConfig = component.json_config || {};

        const updatedConfig = {
          ...existingConfig,
          grid: {
            x: (component as any).grid_x,
            y: (component as any).grid_y,
            w: (component as any).grid_w || 6,
            h: (component as any).grid_h || 4
          },
          migratedAt: new Date().toISOString(),
          version: '1.0'
        };

        this.dashboardService.updateDashboardComponent(component.id, {
          json_config: JSON.stringify(updatedConfig)
        }).subscribe({
          next: () => {
            console.log(`✅ Migrated component ${component.id}`);
            migratedCount++;

            // Update local component
            component.json_config = updatedConfig;
          },
          error: (error) => {
            console.error(`❌ Failed to migrate component ${component.id}:`, error);
          }
        });
      } else {
        console.log(`⏭️  Skipping component ${component.id} - no old grid data`);
        skippedCount++;
      }
    });

    setTimeout(() => {
      console.log(`✅ Migration completed: ${migratedCount} migrated, ${skippedCount} skipped`);
    }, 1000);
  }

  ngOnDestroy(): void {
    // Cleanup if needed (effects are automatically cleaned up)
  }

  private loadDashboardData(): void {
    const userId = sessionStorage.getItem('userId') || '123';
    console.log('Loading dashboard data for user:', userId);
    console.log('Fetching from:', `/api/dashboards/${userId}`);

    this.dashboardService.fetchDashboardData(userId).subscribe({
      next: (response) => {
        console.log('✅ Successfully fetched dashboard data:', response);
        if (response.data && response.data.length > 0) {
          const types = new Set<string>(response.data.map((component: any) => component.type));

          // Build grid layout from saved positions
          const savedLayout: KtdGridLayout = [];

          const processedData = response.data.map((component: any, index: number) => {
            // Ensure columns is an array
            if (typeof component.columns === 'string') {
              component.columns = component.columns.split(',').map((col: string) => col.trim());
            }
            // Ensure data and columns are always arrays
            component.data = component.data || [];
            component.columns = component.columns || [];

            // Parse json_config if it exists
            if (component.json_config) {
              try {
                if (typeof component.json_config === 'string') {
                  component.json_config = JSON.parse(component.json_config);
                }
              } catch (error) {
                console.warn('Failed to parse json_config for component', component.id, error);
                component.json_config = null;
              }
            }

            // Extract grid layout - prioritize json_config, fallback to old columns
            if (component.json_config?.grid) {
              // Use grid layout from json_config
              savedLayout.push({
                id: String(component.id),
                x: component.json_config.grid.x,
                y: component.json_config.grid.y,
                w: component.json_config.grid.w || 6,
                h: component.json_config.grid.h || 4
              });
            } else if (component.grid_x !== undefined && component.grid_y !== undefined) {
              // Fallback to old grid columns for backward compatibility
              savedLayout.push({
                id: String(component.id),
                x: component.grid_x,
                y: component.grid_y,
                w: component.grid_w || 6,
                h: component.grid_h || 4
              });
            }

            return component;
          });

          console.log('Processed components:', processedData.length);
          console.log('Saved layout positions:', savedLayout.length);

          // Set initial grid layout if we have saved positions
          if (savedLayout.length > 0) {
            console.log('Setting grid layout with saved positions');
            this.gridLayout.set(savedLayout);
          }

          console.log('Updating dashboard state...');
          this.dashboardService.setDashboardState({
            components: processedData,
            types: Array.from(types)
          });
          console.log('✅ Dashboard state updated successfully');
        } else {
          console.log('No dashboard data found for user');
        }
      },
      error: (error) => {
        console.error('❌ Error fetching dashboard data:', error);
        console.error('Error details:', {
          status: error.status,
          statusText: error.statusText,
          message: error.message,
          url: error.url
        });
      },
      complete: () => {
        console.log('Dashboard data fetch completed');
      }
    });
  }

  private updateComponentTypes(types: string[]): void {
    const newTypes = types.reduce((acc: ComponentType[], type) => {
      switch (type) {
        case 'line':
          acc.push({ type: 'line', name: 'Line Chart', defaultTitle: 'Line Chart' });
          break;
        case 'bar':
          acc.push({ type: 'bar', name: 'Bar Chart', defaultTitle: 'Bar Chart' });
          break;
        case 'pie':
          acc.push({ type: 'pie', name: 'Pie Chart', defaultTitle: 'Pie Chart' });
          break;
        case 'donut':
          acc.push({ type: 'donut', name: 'Donut Chart', defaultTitle: 'Donut Chart' });
          break;
        case 'table':
          acc.push({ type: 'table', name: 'Table', defaultTitle: 'Table' });
          break;
      }
      return acc;
    }, []);
    this.componentTypes.set(newTypes);
  }

  toggleAddMenu(): void {
    this.showAddMenu.update(value => !value);
  }

  closeAddMenu(): void {
    this.showAddMenu.set(false);
  }

  addComponent(type: string): void {
    const componentType = this.componentTypes().find(ct => ct.type === type);
    const dashboard = this.dashboardService.getDashboard();

    if (componentType && dashboard.columns.length > 0) {
      const newComponent: SComponent = {
        id: Number(new Date().getTime()),
        type: type as any,
        title: componentType.defaultTitle,
        query: dashboard.query || '',
        data: dashboard.data,
        columns: dashboard.columns,
        user_id: sessionStorage.getItem('userId') || ''
      };

      console.log('Adding new component:', newComponent);
      this.dashboardService.addComponent(newComponent);

      // Save to server if user is logged in
      if (newComponent.user_id) {
        const serverComponent = { ...newComponent };
        (serverComponent as any).columns = (serverComponent.columns || []).join(',');
        delete (serverComponent as any).data;

        // Calculate default grid position for new component
        const currentComponents = this.components();
        const index = currentComponents.length;
        const col = index % 2;
        const row = Math.floor(index / 2);

        // Prepare json_config with grid layout and metadata
        (serverComponent as any).json_config = JSON.stringify({
          grid: {
            x: col * 6,
            y: row * 4,
            w: 6,
            h: 4
          },
          createdAt: new Date().toISOString(),
          version: '1.0'
        });

        this.dashboardService.createDashboardComponent(serverComponent).subscribe({
          next: (response) => {
            console.log('Component saved to server:', response);
            // Update the component with server-generated ID and json_config
            const updatedComponent = {
              ...newComponent,
              id: response.dashboard.id,
              json_config: JSON.parse((serverComponent as any).json_config)
            };
            this.dashboardService.removeComponent(newComponent.id);
            this.dashboardService.addComponent(updatedComponent);
          },
          error: (error) => {
            console.error('Error saving component:', error);
          }
        });
      }
    }
    this.closeAddMenu();
  }

  removeComponent(id: any): void {
    console.log('Removing component with ID:', id);
    const component = this.components().find(comp => comp.id === id);

    this.dashboardService.removeComponent(id);

    // Remove from server if it exists
    if (component && component.user_id) {
      this.dashboardService.deleteDashboardComponent(id).subscribe({
        next: () => {
          console.log('Component removed from server');
        },
        error: (error) => {
          console.error('Error removing component from server:', error);
        }
      });
    }
  }

  startEditing(id: any, currentTitle: string): void {
    this.editingComponent.set(id);
    this.editTitle.set(currentTitle);

    // Load current configuration (chart or table)
    const component = this.components().find(comp => comp.id === id);
    if (component) {
      if (component.type === 'table' && component.json_config?.table) {
        this.editChartConfig.set({ ...component.json_config.table });
      } else if (component.type !== 'table' && component.json_config?.chart) {
        this.editChartConfig.set({ ...component.json_config.chart });
      } else {
        // Set default configuration based on component type
        this.editChartConfig.set(this.getDefaultChartConfig(component.type));
      }
    }
  }

  private getDefaultChartConfig(type?: string): any {
    const defaults: any = {
      showLegend: true,
      legendPosition: 'top',
      responsive: true,
      maintainAspectRatio: true,
      animationEnabled: true,
      animationDuration: 1000,
      animationEasing: 'easeOutQuad',
      colorScheme: 'default',
      borderWidth: 2,
      showTooltip: true,
      showTitle: false,
      titlePosition: 'top',
      titleAlign: 'center'
    };

    if (type === 'line') {
      return {
        ...defaults,
        showGrid: true,
        showXAxis: true,
        showYAxis: true,
        beginAtZero: true,
        tension: 0.4,
        fill: false,
        pointRadius: 3,
        pointStyle: 'circle'
      };
    } else if (type === 'bar') {
      return {
        ...defaults,
        showGrid: true,
        showXAxis: true,
        showYAxis: true,
        beginAtZero: true,
        barThickness: 'flex',
        maxBarThickness: 50
      };
    } else if (type === 'pie' || type === 'donut') {
      return {
        ...defaults,
        cutout: type === 'donut' ? '50%' : '0%',
        rotation: 0,
        circumference: 360
      };
    } else if (type === 'table') {
      return {
        showPagination: true,
        pageSize: 10,
        stripedRows: true,
        showBorders: true,
        hoverEffect: true,
        denseLayout: false,
        headerStyle: 'default',
        headerColor: '#3b82f6'
      };
    }

    return defaults;
  }

  saveEdit(): void {
    const component = this.components().find(comp => comp.id === this.editingComponent());
    if (component) {
      // Update component with new title and config (chart or table)
      const updatedConfig = { ...component.json_config };

      if (component.type === 'table') {
        updatedConfig.table = this.editChartConfig();
      } else {
        updatedConfig.chart = this.editChartConfig();
      }
      updatedConfig.lastModified = new Date().toISOString();

      const updatedComponent = {
        ...component,
        title: this.editTitle(),
        json_config: updatedConfig
      };
      this.dashboardService.updateComponent(updatedComponent);

      // Update on server
      if (component.user_id) {
        this.dashboardService.updateDashboardComponent(component.id, {
          title: this.editTitle(),
          json_config: JSON.stringify(updatedComponent.json_config)
        }).subscribe({
          next: (response) => {
            console.log('Component updated:', response);
          },
          error: (error) => {
            console.error('Error updating component:', error);
          }
        });
      }
    }
    this.cancelEdit();
  }

  cancelEdit(): void {
    this.editingComponent.set(null);
    this.editTitle.set('');
    this.editChartConfig.set(null);
  }

  updateChartConfig(key: string, value: any): void {
    this.editChartConfig.update(config => ({
      ...config,
      [key]: value
    }));
  }

  isEditingTable(): boolean {
    const component = this.components().find(comp => comp.id === this.editingComponent());
    return component?.type === 'table';
  }

  handleColumnsChange(id: any, newColumns: string[]): void {
    const component = this.components().find(comp => comp.id === id);
    if (component) {
      const updatedComponent = { ...component, columns: newColumns };
      this.dashboardService.updateComponent(updatedComponent);

      // Update on server
      if (component.user_id) {
        this.dashboardService.updateDashboardComponent(id, { columns: newColumns.join(',') }).subscribe({
          next: (response) => {
            console.log('Component columns updated:', response);
          },
          error: (error) => {
            console.error('Error updating component columns:', error);
          }
        });
      }
    }
  }

  handleConfigChange(id: any, newConfig: any): void {
    const component = this.components().find(comp => comp.id === id);
    if (component) {
      const updatedComponent = {
        ...component,
        json_config: newConfig
      };
      this.dashboardService.updateComponent(updatedComponent);

      // Update on server
      if (component.user_id) {
        this.dashboardService.updateDashboardComponent(id, {
          json_config: JSON.stringify(newConfig)
        }).subscribe({
          next: (response) => {
            console.log('Component config updated:', response);
          },
          error: (error) => {
            console.error('Error updating component config:', error);
          }
        });
      }
    }
  }

  toggleQueryEditable(componentId: any): void {
    this.dashboardService.toggleQueryEditable(componentId);
  }

  // Grid layout methods
  private updateGridLayout(components: SComponent[]): void {
    const currentLayout = this.gridLayout();
    const newLayout: KtdGridLayout = components.map((component, index) => {
      // Check if component already has layout info
      const existingLayout = currentLayout.find(item => item.id === String(component.id));

      if (existingLayout) {
        return existingLayout;
      }

      // Create default layout for new components
      // Place items in a 2-column grid
      const col = index % 2;
      const row = Math.floor(index / 2);

      return {
        id: String(component.id),
        x: col * 6, // 12 columns / 2 = 6 columns per item
        y: row * 4, // 4 rows per item
        w: 6,       // half width
        h: 4,       // 4 rows height
      };
    });

    this.gridLayout.set(newLayout);
  }

  onLayoutUpdated(layout: KtdGridLayout): void {
    console.log('Layout updated:', layout);
    this.gridLayout.set(layout);

    // Save layout to backend for persistence
    this.saveGridLayout(layout);
  }

  private saveGridLayout(layout: KtdGridLayout): void {
    const userId = sessionStorage.getItem('userId');
    if (!userId) return;

    // Save each component's layout position in json_config
    layout.forEach(item => {
      const component = this.components().find(c => String(c.id) === item.id);
      if (component && component.user_id) {
        // Get existing json_config or create new one
        const existingConfig = component.json_config || {};

        // Update grid layout in json_config
        const updatedConfig = {
          ...existingConfig,
          grid: {
            x: item.x,
            y: item.y,
            w: item.w,
            h: item.h
          },
          lastModified: new Date().toISOString()
        };

        const updateData = {
          json_config: JSON.stringify(updatedConfig)
        };

        this.dashboardService.updateDashboardComponent(component.id, updateData).subscribe({
          next: () => console.log(`Layout saved for component ${component.id}`),
          error: (error) => console.error('Error saving layout:', error)
        });
      }
    });
  }
}
