import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChartConfig {
  // Common chart settings
  showLegend?: boolean;
  legendPosition?: 'top' | 'bottom' | 'left' | 'right';
  responsive?: boolean;
  maintainAspectRatio?: boolean;

  // Animation
  animationEnabled?: boolean;
  animationDuration?: number;
  animationEasing?: 'linear' | 'easeInQuad' | 'easeOutQuad' | 'easeInOutQuad' | 'easeInCubic' | 'easeOutCubic' | 'easeInOutCubic';

  // Colors
  colorScheme?: 'default' | 'pastel' | 'vibrant' | 'monochrome' | 'cool' | 'warm';
  backgroundColor?: string;
  borderColor?: string;
  borderWidth?: number;

  // Grid and axes (for line/bar charts)
  showGrid?: boolean;
  gridColor?: string;
  showXAxis?: boolean;
  showYAxis?: boolean;
  beginAtZero?: boolean;

  // Line chart specific
  tension?: number; // Curve smoothness (0 = straight, 1 = very curved)
  fill?: boolean; // Fill area under line
  pointRadius?: number;
  pointStyle?: 'circle' | 'cross' | 'crossRot' | 'dash' | 'line' | 'rect' | 'rectRounded' | 'rectRot' | 'star' | 'triangle';

  // Bar chart specific
  barThickness?: number | 'flex';
  maxBarThickness?: number;

  // Pie/Donut chart specific
  cutout?: string; // For donut charts (e.g., "50%")
  rotation?: number;
  circumference?: number;

  // Tooltip
  showTooltip?: boolean;

  // Title
  showTitle?: boolean;
  titlePosition?: 'top' | 'bottom';
  titleAlign?: 'start' | 'center' | 'end';
}

export interface TableConfig {
  showPagination?: boolean;
  pageSize?: number;
  stripedRows?: boolean;
  showBorders?: boolean;
  hoverEffect?: boolean;
  denseLayout?: boolean;
  headerStyle?: 'default' | 'bold' | 'colored';
  headerColor?: string;
}

export interface SComponent {
  id: any;
  type: 'line' | 'bar' | 'pie' | 'table' | 'donut';
  title: string;
  query: string;
  data: any[];
  columns: string[];
  user_id?: any;
  isQueryEditable?: boolean;
  json_config?: {
    grid?: { x: number; y: number; w: number; h: number };
    chart?: ChartConfig;
    table?: TableConfig;
    createdAt?: string;
    lastModified?: string;
    version?: string;
    source?: string;
    updatedFrom?: string;
  };
}

export interface DashboardState {
  components: SComponent[];
  types: string[];
  data: any[];
  columns: string[];
  query: string;
  error: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private baseUrl = '/api';

  // Convert to Signals
  private dashboardStateSignal = signal<DashboardState>({
    components: [],
    types: [],
    data: [],
    columns: [],
    query: '',
    error: null
  });

  // Public readonly signals
  public readonly dashboardState = this.dashboardStateSignal.asReadonly();

  // Computed signals for specific parts of the state
  public readonly components = computed(() => this.dashboardStateSignal().components);
  public readonly types = computed(() => this.dashboardStateSignal().types);
  public readonly data = computed(() => this.dashboardStateSignal().data);
  public readonly columns = computed(() => this.dashboardStateSignal().columns);
  public readonly query = computed(() => this.dashboardStateSignal().query);
  public readonly error = computed(() => this.dashboardStateSignal().error);

  // Editable component ID as signal
  private editableComponentIdSignal = signal<any>(null);
  public readonly editableComponentId = this.editableComponentIdSignal.asReadonly();

  // Keep observable for backward compatibility (can be removed later)
  public dashboard$ = this.dashboardState;
  public editableComponentId$ = this.editableComponentId;

  constructor(private http: HttpClient) { }

  getDashboard(): DashboardState {
    return this.dashboardStateSignal();
  }

  setDashboardState(newState: Partial<DashboardState>): void {
    this.dashboardStateSignal.update(current => ({ ...current, ...newState }));
  }

  addComponent(component: SComponent): void {
    // Ensure data and columns are always arrays
    const componentWithDefaults = {
      ...component,
      data: component.data || [],
      columns: component.columns || []
    };
    this.dashboardStateSignal.update(current => ({
      ...current,
      components: [componentWithDefaults, ...current.components]
    }));
  }

  removeComponent(id: any): void {
    this.dashboardStateSignal.update(current => ({
      ...current,
      components: current.components.filter(comp => comp.id !== id)
    }));
  }

  updateComponent(updatedComponent: SComponent): void {
    // Ensure data and columns are always arrays
    const componentWithDefaults = {
      ...updatedComponent,
      data: updatedComponent.data || [],
      columns: updatedComponent.columns || []
    };
    this.dashboardStateSignal.update(current => ({
      ...current,
      components: current.components.map(comp =>
        comp.id === componentWithDefaults.id ? componentWithDefaults : comp
      )
    }));
  }

  toggleQueryEditable(componentId: any): void {
    const currentState = this.dashboardStateSignal();
    const isCurrentlyEditable = currentState.components.find(c => c.id === componentId)?.isQueryEditable;

    console.log('Toggle query editable for component:', componentId, 'Current state:', isCurrentlyEditable);

    const updatedComponents = currentState.components.map(comp => ({
      ...comp,
      data: comp.data || [],
      columns: comp.columns || [],
      isQueryEditable: comp.id === componentId ? !isCurrentlyEditable : false
    }));

    this.dashboardStateSignal.update(current => ({
      ...current,
      components: updatedComponents
    }));

    const newEditableId = !isCurrentlyEditable ? componentId : null;
    this.editableComponentIdSignal.set(newEditableId);

    console.log('Updated components:', this.dashboardStateSignal().components.map(c => ({ id: c.id, isQueryEditable: c.isQueryEditable })));
  }

  getEditableComponentId(): any {
    return this.editableComponentIdSignal();
  }

  setTypesAndData(types: string[], data: any[], query: string, columns: string[], error: string | null = null): void {
    this.dashboardStateSignal.update(current => ({
      ...current,
      types,
      data,
      query,
      columns,
      error
    }));
  }

  // API calls
  fetchDashboardData(userId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/dashboards/${userId}`);
  }

  createDashboardComponent(component: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/dashboard`, component);
  }

  deleteDashboardComponent(componentId: any): Observable<any> {
    return this.http.delete(`${this.baseUrl}/dashboard/${componentId}`);
  }

  updateDashboardComponent(componentId: any, updates: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/dashboard/${componentId}`, updates);
  }

  getQueryResult(queryDescription: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/get-query-result`, { queryDescription });
  }

  getQueryResult2(query: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/get-query-result2`, { query });
  }

  takeDecision(response: { data: any[], query: string, error: string | null, detail: string, bot: boolean }): void {
    const { data, query, error, detail, bot } = response;

    // Handle empty data
    if (!data || data.length === 0 || error) {

      let errorMessage = error + ' ' + detail.replace(/\(.+?\)/g, '');
      if (!error) {
        errorMessage = 'No data found for the provided query. Please check your query and try again.';
      }
      if (bot) {
        this.setTypesAndData(['error'], [], errorMessage, [], errorMessage);
      } else {
        this.setTypesAndData([], [], query, [], errorMessage);
      }

      return;
    }

    // Get columns from first object
    let columns = Object.keys(data[0]);
    let namedColumn = '';
    const acc = columns.reduce((acc, col) => {
      if (typeof data[0][col] === 'string' ||
        (data[0][col] instanceof Date ||
          (typeof data[0][col] === 'string' && !isNaN(Date.parse(data[0][col]))))) {
        if (acc['string']) {
          acc['string'] += 1;
        } else {
          acc['string'] = 1;
          namedColumn = col;
        }
      } else if (typeof data[0][col] === 'number') {
        if (acc['number']) {
          acc['number'] += 1;
        } else {
          acc['number'] = 1;
        }
      } else {
        if (acc['unknown']) {
          acc['unknown'] += 1;
        } else {
          acc['unknown'] = 1;
        }
      }
      return acc;
    }, {} as Record<string, any>);

    console.log('Columns:', acc);
    columns = columns.filter(col => col !== namedColumn);
    columns.unshift(namedColumn);
    if (acc['string'] > 1 || acc['unknown'] > 0) {
      this.setTypesAndData(['table'], data, query, columns);
    } else if (acc['number'] > 1) {
      this.setTypesAndData(['line', 'table'], data, query, columns);
    } else if (acc['number'] === 1) {
      this.setTypesAndData(['bar', 'pie', 'donut', 'line', 'table'], data, query, columns);
    } else {
      this.setTypesAndData(['table'], data, query, columns);
    }
  }
  public generateColors(count: number, alpha: number): string[] {
    const baseColors = [
      `rgba(54, 162, 235, ${alpha})`,   // Blue
      `rgba(255, 99, 132, ${alpha})`,   // Red
      `rgba(255, 205, 86, ${alpha})`,   // Yellow
      `rgba(75, 192, 192, ${alpha})`,   // Green
      `rgba(153, 102, 255, ${alpha})`,  // Purple
      `rgba(255, 159, 64, ${alpha})`,   // Orange
      `rgba(255, 20, 147, ${alpha})`,   // Deep Pink
      `rgba(0, 191, 255, ${alpha})`,    // Deep Sky Blue
      `rgba(50, 205, 50, ${alpha})`,    // Lime Green
      `rgba(255, 140, 0, ${alpha})`,    // Dark Orange
      `rgba(147, 112, 219, ${alpha})`,  // Medium Purple
      `rgba(255, 69, 0, ${alpha})`,     // Red Orange
      `rgba(0, 255, 255, ${alpha})`,    // Cyan
      `rgba(255, 192, 203, ${alpha})`,  // Pink
      `rgba(124, 252, 0, ${alpha})`,    // Lawn Green
      `rgba(255, 0, 255, ${alpha})`,    // Magenta
      `rgba(255, 215, 0, ${alpha})`,    // Gold
      `rgba(64, 224, 208, ${alpha})`,   // Turquoise
      `rgba(255, 105, 180, ${alpha})`,  // Hot Pink
      `rgba(32, 178, 170, ${alpha})`,   // Light Sea Green
      `rgba(255, 99, 71, ${alpha})`,    // Tomato
      `rgba(138, 43, 226, ${alpha})`,   // Blue Violet
      `rgba(255, 127, 80, ${alpha})`,   // Coral
      `rgba(0, 128, 128, ${alpha})`,    // Teal
      `rgba(255, 182, 193, ${alpha})`,  // Light Pink
      `rgba(72, 61, 139, ${alpha})`     // Dark Slate Blue
    ];

    const colors = [];
    for (let i = 0; i < count; i++) {
      colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
  }
}
