import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';

export interface Message {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  hasSql?: boolean;
}

export interface HelpDesk {
  title: string;
  query_description: string;
  query: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private baseUrl = '/api';
  private helpDesks: HelpDesk[] = [];

  sync(messages: Message[]): Message[] {
    return messages.map(msg => {
      if (msg.sender === 'user') {
        const item = this.helpDesks.find(d => d.query_description === msg.text);
        if (item) {
          msg.text = item.title;
        }
        return msg;
      }
      return msg;
    });
  }
  constructor(private http: HttpClient) {
    this.getAllHelpDesk().subscribe(data => {
      this.helpDesks = data;
    });
  }

  getBotMessages(userId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/get-bot-messages/${userId}`);
  }

  sendMessage(userInput: string, threadId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/get-query-result`, {
      user_input: userInput,
      thread_id: threadId
    });
  }

  executeQuery(query: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/get-query-result2`, {
      query: query
    });
  }

  private getAllHelpDesk(): Observable<HelpDesk[]> {
    return this.http.get<HelpDesk[]>(`${this.baseUrl}/helpdesk`).pipe(
      map((it: any) => it.data || []),
      catchError(error => {
        console.error('Error fetching help desk data:', error);
        return of([]);
      })
    );
  }

  updateHelpDesk(helpDesk: HelpDesk): Observable<HelpDesk[]> {
    return this.http.put<HelpDesk[]>(`${this.baseUrl}/helpdesk/${helpDesk.title}`, helpDesk).pipe(
      catchError(error => {
        console.error('Error updating help desk data:', error);
        return of([]);
      })
    );
  }

  searchHelpDesk(query: string): Observable<HelpDesk[]> {
    if (!query.trim()) {
      return of([]);
    }
    const lowerCaseQuery = query.toLowerCase();
    const filtered = this.helpDesks.filter(desk =>
      desk.title.toLowerCase().includes(lowerCaseQuery)
    );
    return of(filtered);
  }
}
