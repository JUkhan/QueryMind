import { Component } from '@angular/core';
import { DashboardContainerComponent } from '../dashboard-container/dashboard-container.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [DashboardContainerComponent],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent {

}
