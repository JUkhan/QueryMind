import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-pager',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div 
      *ngIf="totalPages > 1"
      class="flex items-center justify-between pt-4 bg-white border-t border-gray-200 rounded-bl-lg rounded-br-lg"
    >
      <!-- Mobile view -->
      <div class="flex justify-between flex-1 sm:hidden">
        <button
          (click)="onPageChange.emit(currentPage - 1)"
          [disabled]="currentPage === 1"
          class="relative inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Previous
        </button>
        <span class="text-sm text-gray-700">
          Page {{ currentPage }} of {{ totalPages }}
        </span>
        <button
          (click)="onPageChange.emit(currentPage + 1)"
          [disabled]="currentPage === totalPages"
          class="relative inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Next
        </button>
      </div>
      
      <!-- Desktop view -->
      <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p class="text-sm text-gray-700">
            Showing <span class="font-medium">{{ startIndex }}</span> to
            <span class="font-medium">{{ endIndex }}</span> of
            <span class="font-medium">{{ totalItems }}</span> results
          </p>
        </div>
        
        <div class="flex items-center space-x-2">
          <button
            (click)="onPageChange.emit(currentPage - 1)"
            [disabled]="currentPage === 1"
            class="relative inline-flex items-center px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15,18 9,12 15,6"></polyline>
            </svg>
          </button>
          
          <ng-container *ngFor="let page of pageNumbers; let i = index">
            <span 
              *ngIf="page === '...'"
              class="px-3 py-2 text-sm font-medium text-gray-700"
            >
              ...
            </span>
            <button
              *ngIf="page !== '...'"
              (click)="onPageChange.emit(+page)"
              [class]="getPageButtonClass(page)"
            >
              {{ page }}
            </button>
          </ng-container>
          
          <button
            (click)="onPageChange.emit(currentPage + 1)"
            [disabled]="currentPage === totalPages"
            class="relative inline-flex items-center px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9,18 15,12 9,6"></polyline>
            </svg>
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    /* Additional styles if needed */
  `]
})
export class PagerComponent implements OnInit {
  @Input() currentPage: number = 1;
  @Input() totalPages: number = 1;
  @Input() totalItems: number = 0;
  @Input() itemsPerPage: number = 10;
  @Output() onPageChange = new EventEmitter<number>();

  startIndex: number = 1;
  endIndex: number = 1;
  pageNumbers: (number | string)[] = [];

  ngOnInit() {
    this.calculateIndices();
    this.generatePageNumbers();
  }

  ngOnChanges() {
    this.calculateIndices();
    this.generatePageNumbers();
  }

  private calculateIndices() {
    this.startIndex = (this.currentPage - 1) * this.itemsPerPage + 1;
    this.endIndex = Math.min(this.currentPage * this.itemsPerPage, this.totalItems);
  }

  private generatePageNumbers() {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (this.totalPages <= maxVisible) {
      // Show all pages
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);

      // Calculate start and end of middle section
      let start = Math.max(2, this.currentPage - 1);
      let end = Math.min(this.totalPages - 1, this.currentPage + 1);

      // Add ellipsis if needed
      if (start > 2) {
        pages.push('...');
      }

      // Add middle pages
      for (let i = start; i <= end; i++) {
        if (i !== 1 && i !== this.totalPages) {
          pages.push(i);
        }
      }

      // Add ellipsis if needed
      if (end < this.totalPages - 1) {
        pages.push('...');
      }

      // Always show last page
      if (this.totalPages > 1) {
        pages.push(this.totalPages);
      }
    }

    this.pageNumbers = pages;
  }

  getPageButtonClass(page: number | string): string {
    const baseClass = 'relative inline-flex items-center px-3 py-2 text-sm font-medium rounded-md';

    if (page === this.currentPage) {
      return `${baseClass} bg-blue-600 text-white`;
    } else {
      return `${baseClass} text-gray-500 bg-white border border-gray-300 hover:bg-gray-50`;
    }
  }
}