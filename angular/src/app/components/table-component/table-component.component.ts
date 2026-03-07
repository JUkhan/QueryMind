import { Component, input, output, model, OnInit, ChangeDetectionStrategy, ChangeDetectorRef, effect, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DashboardService } from '../../services/dashboard.service';
import { PagerComponent } from './pager.component';

@Component({
  selector: 'app-table-component',
  standalone: true,
  imports: [CommonModule, FormsModule, PagerComponent],
  templateUrl: './table-component.component.html',
  styleUrls: ['./table-component.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TableComponentComponent implements OnInit {
  // Model signals for two-way binding (can be modified)
  readonly data = model<any[]>([]);
  readonly columns = model<string[]>([]);

  // Regular inputs (read-only)
  readonly id = input<any>();
  readonly title = input<string>('Table');
  readonly query = input<string>();
  readonly type = input<string>();
  readonly isQueryEditable = input<boolean>();
  readonly json_config = input<any>();

  // Signal outputs
  readonly onRemove = output<any>();
  readonly onEdit = output<{ id: any, title: string }>();
  readonly onColumnsChange = output<string[]>();
  readonly onToggleQueryEditable = output<void>();
  readonly onConfigChange = output<any>();

  // Internal state as signals
  displayColumns = signal<string[]>([]);
  page = signal('');
  // Pagination properties as signals
  currentPage = signal(1);
  pageSize = signal(5);
  pageSizeOptions = [5, 10, 25, 50, 100];
  totalPages = signal(0);
  // Drag and drop properties
  draggedColumnIndex = signal<number | null>(null);
  isDragging = signal(false);

  // Computed values
  paginatedData = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    const end = start + this.pageSize();
    return this.data().slice(start, end);
  });


  constructor(
    private dashboardService: DashboardService,
    private cdr: ChangeDetectorRef
  ) {
    // React to input changes
    effect(() => {
      const data = this.data();
      const columns = this.columns();
      console.log('Table data/columns changed:', data, columns);
      this.updateDisplayColumns();
      this.updatePagination();
    }, { allowSignalWrites: true });

    // Track isQueryEditable changes
    effect(() => {
      const editable = this.isQueryEditable();
      console.log(`Table ${this.id()} - isQueryEditable changed to:`, editable);
    });

    // React to config changes
    effect(() => {
      const config = this.json_config();
      if (config?.table) {
        this.applyTableConfig(config.table);
      }
    }, { allowSignalWrites: true });
  }

  ngOnInit(): void {
    const data = this.data();
    const query = this.query();
    console.log('TableComponent initialized with data::::>', data);
    if (data && data.length === 0 && query) {
      this.dashboardService.getQueryResult2(query).subscribe(res => {
        console.log('Query result for table component:', res);
        // Now we can update data since it's a model signal
        if (res.data) {
          this.data.set(res.data);
          this.updateDisplayColumns();
          this.updatePagination();
        }
      });
    }
  }

  private updateDisplayColumns(): void {
    const columns = this.columns();
    const data = this.data();
    if (columns && columns.length > 0) {
      this.displayColumns.set([...columns]);
    } else if (data && data.length > 0) {
      this.displayColumns.set(Object.keys(data[0]));
    }
    this.updatePagination();
  }

  // Pagination methods
  updatePagination(): void {
    const data = this.data();
    const pageSize = this.pageSize();
    const totalPages = Math.ceil(data.length / pageSize);
    this.totalPages.set(totalPages);
    this.currentPage.update(current => Math.min(current, totalPages || 1));
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  previousPage(): void {
    this.goToPage(this.currentPage() - 1);
  }

  handlePageChange(page: number): void {
    this.goToPage(page);
  }

  nextPage(): void {
    this.goToPage(this.currentPage() + 1);
  }

  onPageSizeChange(newSize: number): void {
    console.log('Page size changing to:', newSize);
    this.pageSize.set(newSize);
    this.currentPage.set(1);
    this.updatePagination();

    // Update json_config and emit to parent for persistence
    const currentConfig = this.json_config() || {};
    const updatedConfig = {
      ...currentConfig,
      table: {
        ...(currentConfig.table || {}),
        pageSize: newSize
      }
    };
    this.onConfigChange.emit(updatedConfig);

    this.cdr.markForCheck();
    console.log('New pageSize:', this.pageSize(), 'paginatedData length:', this.paginatedData().length);
  }

  min(a: number, b: number): number {
    return a < b ? a : b;
  }

  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxPagesToShow = 5;
    const currentPage = this.currentPage();
    const totalPages = this.totalPages();
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

    if (endPage - startPage + 1 < maxPagesToShow) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }
    return pages;
  }

  // Drag and drop methods
  onDragStart(event: DragEvent, columnIndex: number): void {
    // Stop propagation to prevent grid-layout from intercepting
    event.stopPropagation();

    this.draggedColumnIndex.set(columnIndex);
    this.isDragging.set(true);
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/html', event.target?.toString() || '');
    }
  }

  onDragOver(event: DragEvent): void {
    // Stop propagation to prevent grid-layout from intercepting
    event.stopPropagation();
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
  }

  onDrop(event: DragEvent, targetColumnIndex: number): void {
    // Stop propagation to prevent grid-layout from intercepting
    event.stopPropagation();
    event.preventDefault();

    const draggedIndex = this.draggedColumnIndex();

    if (draggedIndex !== null && draggedIndex !== targetColumnIndex) {
      const columns = this.displayColumns();
      const draggedColumn = columns[draggedIndex];
      const newColumns = [...columns];

      // Remove the dragged column
      newColumns.splice(draggedIndex, 1);

      // Insert at new position
      newColumns.splice(targetColumnIndex, 0, draggedColumn);

      this.displayColumns.set(newColumns);
      this.onColumnsChange.emit(newColumns);
    }

    this.draggedColumnIndex.set(null);
    this.isDragging.set(false);
  }

  onDragEnd(event: DragEvent): void {
    // Stop propagation to prevent grid-layout from intercepting
    event.stopPropagation();

    this.draggedColumnIndex.set(null);
    this.isDragging.set(false);
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

  getValueByKey(obj: any, key: string): any {
    return obj[key];
  }

  private applyTableConfig(config: any): void {
    // Apply pagination settings
    if (config.showPagination === false) {
      // User can hide pagination if needed
    }
    if (config.pageSize) {
      this.pageSize.set(config.pageSize);
      this.updatePagination();
    }

    // Other table styling is handled via CSS classes in the template
  }

  // Helper methods for template
  showPagination(): boolean {
    const config = this.json_config();
    return config?.table?.showPagination !== false;
  }

  isStripedRows(): boolean {
    const config = this.json_config();
    return config?.table?.stripedRows !== false;
  }

  showBorders(): boolean {
    const config = this.json_config();
    return config?.table?.showBorders !== false;
  }

  hasHoverEffect(): boolean {
    const config = this.json_config();
    return config?.table?.hoverEffect !== false;
  }

  isDenseLayout(): boolean {
    const config = this.json_config();
    return config?.table?.denseLayout === true;
  }

  getHeaderStyle(): string {
    const config = this.json_config();
    const style = config?.table?.headerStyle || 'default';

    if (style === 'colored') {
      const color = config?.table?.headerColor || '#3b82f6';
      return `background-color: ${color}; color: white;`;
    } else if (style === 'bold') {
      return 'font-weight: 700;';
    }
    return '';
  }
}
