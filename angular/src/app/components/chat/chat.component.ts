import { Component, OnInit, ElementRef, ViewChild, AfterViewChecked, OnDestroy, signal, computed, effect, ChangeDetectionStrategy, input } from '@angular/core';
import { CommonModule, formatDate } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ChatService, Message, HelpDesk } from '../../services/chat.service';
import { DashboardService, DashboardState } from '../../services/dashboard.service';
import { SpeechRecognitionService } from '../../services/speech-recognition.service';
import { Subscription, Subject } from 'rxjs';
import { debounceTime, switchMap } from 'rxjs/operators';
import { LucideAngularModule, SignalHighIcon, Loader2Icon, BarChart3, TrendingUp, DonutIcon, PieChart, Grid3X3 } from 'lucide-angular';
import { TableComponentComponent } from '../table-component/table-component.component';
import { LineChartComponent } from '../chart-components/line-chart/line-chart.component';
import { BarChartComponent } from '../chart-components/bar-chart/bar-chart.component';
import { PieChartComponent } from '../chart-components/pie-chart/pie-chart.component';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ChatComponent implements OnInit, AfterViewChecked, OnDestroy {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  isOpen = signal(false);
  messages = signal<Message[]>([
    { id: 1, text: 'Hello! How can I help you today?', sender: 'bot', timestamp: new Date() },
  ]);
  inputValue = signal('');
  isTyping = signal(false);
  isLoading = signal(false);
  preventScroll = false;
  hasEditableComponent = signal(false);
  editableComponentId: any = null;
  hasVirginEditableComponent = false;
  private isComponentUpdated = false;
  private transcriptSubscription: Subscription;
  private errorSubscription: Subscription;
  dashboardState = signal<DashboardState>({
    components: [],
    query: '',
    data: [],
    columns: [],
    types: [],
    error: null
  });
  components = computed(() => {
    return this.dashboardState().types.map((type: string) => {
      switch (type) {
        case 'bar': return { type: 'bar', icon: BarChart3, name: 'Bar Chart', component: BarChartComponent };
        case 'line': return { type: 'line', icon: TrendingUp, name: 'Line Chart', component: LineChartComponent };
        case 'pie': return { type: 'pie', icon: PieChart, name: 'Pie Chart', component: PieChartComponent };
        case 'donut': return { type: 'donut', icon: DonutIcon, name: 'Donut Chart', component: PieChartComponent };
        case 'table': return { type: 'table', icon: Grid3X3, name: 'Table', component: TableComponentComponent };
        default: return { type: 'unknown', icon: BarChart3, name: 'Unknown', component: null };
      }
    })
  });
  error = computed(() => this.dashboardState().error);

  query = signal('');
  helpDeskResults = signal<HelpDesk[]>([]);
  private searchTerms = new Subject<string>();
  private selectedHelpDesk: HelpDesk | null = null;

  constructor(
    private chatService: ChatService,
    private dashboardService: DashboardService,
    private router: Router,
    public speechRecognitionService: SpeechRecognitionService
  ) {
    this.transcriptSubscription = this.speechRecognitionService.transcript$.subscribe(
      transcript => {
        this.inputValue.set(transcript);
        this.searchTerms.next(this.inputValue());
      }
    );
    this.errorSubscription = this.speechRecognitionService.error$.subscribe(
      error => {
        console.error(error);
      }
    );

    // Use effect to react to dashboard state changes (must be in constructor)
    effect(() => {
      const state = this.dashboardService.dashboardState();
      console.log('Dashboard state updated:::::', state);
      this.dashboardState.set(state);
      this.query.set(state.query);

      if (state.types.length > 0 && state.types.includes('error')) {
        const botResponse: Message = {
          id: this.messages().length + 1,
          text: state.error!,
          sender: 'bot',
          hasSql: false,
          timestamp: new Date()
        };
        this.messages.update(msgs => [...msgs, botResponse]);
      }

      if (!state.error && this.hasEditableComponent()) {
        const component = this.dashboardState().components.find(comp => comp.id === this.editableComponentId);
        if (component && !this.isComponentUpdated && this.components().some(com => com.type === component.type)) {
          this.addComponent(component.type);
          this.isComponentUpdated = true;
        }
      }
    }, { allowSignalWrites: true });

    // Use effect to react to editable component changes (must be in constructor)
    effect(() => {
      const id = this.dashboardService.editableComponentId();
      this.hasEditableComponent.set(id !== null);
      this.hasVirginEditableComponent = id !== null;
      this.editableComponentId = id;
      console.log('Editable component ID updated:', id);
    }, { allowSignalWrites: true });
  }

  ngOnInit(): void {
    this.loadChatHistory();

    this.searchTerms.pipe(
      debounceTime(300),
      switchMap((term: string) => this.chatService.searchHelpDesk(term))
    ).subscribe(results => {
      this.helpDeskResults.set(results);
    });
  }

  ngAfterViewChecked(): void {
    if (!this.preventScroll) {
      this.scrollToBottom();
    }
  }

  onInputChange(value: string): void {
    this.inputValue.set(value);
    this.searchTerms.next(value);
  }
  private loadChatHistory(): void {
    console.log('Loading chat history...');
    const userId = sessionStorage.getItem('userId') || '123';
    this.chatService.getBotMessages(userId).subscribe({
      next: (data) => {
        if (data.messages && data.messages.length > 0) {
          if (data.messages.length === 1 && data.messages[0].text === 'New conversation started') return;
          const initialMessages = data.messages.map((msg: any, index: number) => ({
            id: index + 1,
            text: msg.text,
            sender: msg.sender,
            hasSql: msg.sender === 'bot' ? (msg.text.startsWith('SELECT') || msg.text.startsWith('select')) : false,
            timestamp: new Date()
          }));
          this.messages.set(this.chatService.sync(initialMessages));
        }
      },
      error: (error) => {
        console.error('Error loading chat history:', error);
      }
    });
  }

  private scrollToBottom(): void {
    if (this.messagesContainer) {
      const element = this.messagesContainer.nativeElement;
      element.scrollTop = element.scrollHeight;
    }
  }

  toggleChat(): void {
    this.isOpen.update(value => !value);
    if (this.isOpen() && this.router.url !== '/dashboard') {
      console.log('Redirecting to dashboard');
      this.router.navigate(['/dashboard'], { replaceUrl: true });
    }
  }

  closeChat(): void {
    this.isOpen.set(false);
  }

  helpDeskAction(helpDesk: HelpDesk): void {
    console.log('Help Desk Action:', helpDesk);
    this.selectedHelpDesk = helpDesk;
    if (helpDesk.query) {
      const newMessage: Message = {
        id: this.messages().length + 1,
        text: helpDesk.title,
        sender: 'user',
        timestamp: new Date(),
      };
      this.messages.update(msgs => [...msgs, newMessage]);
      const botResponse: Message = {
        id: this.messages().length + 1,
        text: helpDesk.query,
        sender: 'bot',
        hasSql: true,
        timestamp: new Date()
      };
      this.messages.update(msgs => [...msgs, botResponse]);
      this.loadSqlData(helpDesk.query);
      this.inputValue.set('');
    } else {
      this.inputValue.set(helpDesk.query_description);
      this.handleSendMessage();
    }
    this.helpDeskResults.set([]);
  }

  startNewConversation(): void {
    this.inputValue.set('new conversation');
    this.handleSendMessage();
  }
  findSqlByEditableComponentId(id: any): string | null {
    const component = this.dashboardState().components.find(comp => comp.id === id);
    return component ? component.query : null;
  }
  private loadQueryForEditableComponent(sql: string, type: string): void {
    this.chatService.executeQuery(sql).subscribe({
      next: (data) => {
        console.log('SQL execution result:', data);
        this.isLoading.set(false);
        data.query = sql;
        this.dashboardService.takeDecision(data);
        this.selectedHelpDesk = null; // Clear selected help desk after execution
        this.addComponent(type);
        this.isTyping.set(false);
        const botResponse: Message = {
          id: this.messages().length + 1,
          text: sql,
          sender: 'bot',
          hasSql: true,
          timestamp: new Date()
        };
        this.messages.update(msgs => [...msgs, botResponse]);


      },
      error: (error) => {
        this.isLoading.set(false);
      }
    });
  }
  handleSendMessage(): void {
    if (this.inputValue().trim() === '') return;

    const newMessage: Message = {
      id: this.messages().length + 1,
      text: this.selectedHelpDesk ? this.selectedHelpDesk.title : this.inputValue(),
      sender: 'user',
      timestamp: new Date(),
    };

    this.messages.update(msgs => [...msgs, newMessage]);
    let userInput = this.inputValue();
    this.inputValue.set('');
    this.isTyping.set(true);
    this.preventScroll = false;
    this.helpDeskResults.set([]);
    if (this.editableComponentId) {
      const component = this.dashboardState().components.find(comp => comp.id === this.editableComponentId)!;
      const inputLower = userInput.toLowerCase();
      // check inputLower for keywords
      //let keywords = ['make', 'produce', 'generate', 'change', 'update', 'upgrade', 'transform', 'convert', 'turn'];
      if (inputLower.startsWith('make')) {
        let keywords = ['line chart', 'bar chart', 'pie chart', 'donut chart', 'table'];
        if (keywords.some(keyword => inputLower.includes(keyword))) {
          keywords = ['line', 'bar', 'pie', 'donut', 'table'];
          // get first word that matches
          const chartType = keywords.find(keyword => inputLower.includes(keyword))!;
          this.loadQueryForEditableComponent(component.query, chartType);
          return;
        }
      }
      if (component?.query && this.hasVirginEditableComponent) {
        userInput = `Based on the following SQL query: ${component.query}, please regenerate the query adding following statement: ${userInput}`;
        this.hasVirginEditableComponent = false;
      }
      console.log('Using SQL from editable component:', component?.query, userInput);
      this.isComponentUpdated = false;
    }
    // Send message to backend
    const threadId = sessionStorage.getItem('userId') || '123';
    this.chatService.sendMessage(userInput, threadId).subscribe({
      next: (data) => {
        console.log('Bot response:', data);
        if (data.query === 'New conversation started') {
          this.isTyping.set(false);
          this.messages.set([{ id: 1, text: 'Hello! How can I help you today?', sender: 'bot', timestamp: new Date() }]);
          return;
        }
        this.dashboardService.takeDecision(data);

        const botResponse: Message = {
          id: this.messages().length + 1,
          text: data.query ? data.query : 'Your query description is not sufficient to generate a valid query. Please provide more details.',
          sender: 'bot',
          hasSql: data.query ? (data.query.startsWith('SELECT') || data.query.startsWith('select')) : false,
          timestamp: new Date()
        };

        this.messages.update(msgs => [...msgs, botResponse]);
        this.isTyping.set(false);
        if (data.query && this.selectedHelpDesk) {
          this.selectedHelpDesk.query = data.query;
          this.chatService.updateHelpDesk(this.selectedHelpDesk).subscribe({
            next: (updatedHelpDesks) => {
              console.log('Help desk updated:', updatedHelpDesks);
              this.selectedHelpDesk = null; // Clear selected help desk after update
            },
            error: (error) => {
              console.error('Error updating help desk:', error);
              this.selectedHelpDesk = null;
            }
          });
        }
      },
      error: (error) => {
        console.error('Error sending message:', error);
        error.error.bot = true;
        this.dashboardService.takeDecision(error.error);
        this.isTyping.set(false);
        this.selectedHelpDesk = null;
      }
    });
  }

  loadSqlData(sql: string): void {
    if (!sql) return;
    this.isLoading.set(true);
    this.isComponentUpdated = false;
    this.preventScroll = this.selectedHelpDesk === null ? true : false;
    this.chatService.executeQuery(sql).subscribe({
      next: (data) => {
        console.log('SQL execution result:', data);
        this.isLoading.set(false);
        data.query = sql;
        this.dashboardService.takeDecision(data);
        this.selectedHelpDesk = null; // Clear selected help desk after execution
      },
      error: (error) => {
        this.isLoading.set(false);
        error.error.query = sql;
        error.error.bot = false;
        this.dashboardService.takeDecision(error.error);
        console.error('Error executing SQL:', error);
        this.selectedHelpDesk = null; // Clear selected help desk on error
      }
    });
  }

  handleKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.handleSendMessage();
    }
  }

  formatTime(date: Date): string {
    return formatDate(date, 'shortTime', 'en-US');
  }

  toggleListening() {
    if (this.speechRecognitionService.isListening) {
      this.speechRecognitionService.stop();
    } else {
      this.speechRecognitionService.start();
    }
  }

  disableQueryEditMode(): void {
    if (this.editableComponentId) {
      this.dashboardService.toggleQueryEditable(this.editableComponentId);
    }
  }

  addComponent(type: string): void {
    console.log('Adding component of type:', type);
    const componentType = this.components().find((ct: any) => ct.type === type);
    const dashboard = this.dashboardService.getDashboard();
    if (componentType && dashboard.columns.length > 0) {
      const newComponent = {
        id: String(new Date().getTime()),
        type: type as any,
        title: componentType.name,
        query: dashboard.query || '',
        data: dashboard.data,
        columns: dashboard.columns,
        isQueryEditable: false,
        user_id: sessionStorage.getItem('userId') || '',
        json_config: undefined
      };

      console.log('Adding new component:', newComponent);
      if (this.hasEditableComponent()) {
        const oldComponent = this.findSqlByEditableComponentId(this.editableComponentId);
        if (oldComponent) {
          newComponent.id = this.editableComponentId;
          newComponent.isQueryEditable = true;

          // Preserve existing json_config from the old component
          const existingComponent = this.dashboardState().components.find(c => c.id === this.editableComponentId);
          if (existingComponent?.json_config) {
            if (type !== existingComponent.type) {
              existingComponent.json_config.chart = undefined;
              existingComponent.json_config.table = undefined;
            }
            (newComponent as any).json_config = existingComponent.json_config;
          }

          this.dashboardService.updateComponent(newComponent);
          const serverComponent = { ...newComponent };
          (serverComponent as any).columns = (serverComponent.columns || []).join(',');
          delete (serverComponent as any).data;

          // Update json_config with lastModified timestamp
          if (serverComponent.json_config) {
            const config = typeof serverComponent.json_config === 'string'
              ? JSON.parse(serverComponent.json_config)
              : serverComponent.json_config;
            config.lastModified = new Date().toISOString();
            config.updatedFrom = 'chat';
            (serverComponent as any).json_config = JSON.stringify(config);
          }

          this.dashboardService.updateDashboardComponent(serverComponent.id, serverComponent).subscribe({
            next: (response) => {
              console.log('Component updated on server:', response);
            }
          });
          return;
        }
      }
      this.dashboardService.addComponent(newComponent);

      // Save to server if user is logged in
      if (newComponent.user_id) {
        const serverComponent = { ...newComponent };
        (serverComponent as any).columns = (serverComponent.columns || []).join(',');
        delete (serverComponent as any).data;

        // Calculate default grid position for new component
        const currentComponents = this.dashboardService.components();
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
          version: '1.0',
          source: 'chat'
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
            //this.dashboardService.removeComponent(newComponent.id);
            this.dashboardService.updateComponent(updatedComponent);
          },
          error: (error) => {
            console.error('Error saving component:', error);
          }
        });
      }
    }
  }

  ngOnDestroy() {
    this.transcriptSubscription.unsubscribe();
    this.errorSubscription.unsubscribe();
    this.searchTerms.unsubscribe();
    // Effects are automatically cleaned up
  }
}
