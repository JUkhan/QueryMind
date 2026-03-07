
import { Injectable, NgZone } from '@angular/core';
import { Subject } from 'rxjs';

interface IWindow extends Window {
  webkitSpeechRecognition: any;
}

@Injectable({
  providedIn: 'root'
})
export class SpeechRecognitionService {
  private speechRecognition: any;
  public isListening = false;
  public transcript$ = new Subject<string>();
  public error$ = new Subject<string>();

  constructor(private ngZone: NgZone) {
    //@ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.speechRecognition = new SpeechRecognition();
      this.speechRecognition.continuous = true;
      this.speechRecognition.interimResults = true;
      this.speechRecognition.lang = 'en-US';
      let finalTranscript = '';

      this.speechRecognition.onstart = () => {
        console.log('Speech recognition started');
        finalTranscript = '';
      };
      this.speechRecognition.onresult = (event: any) => {
        this.ngZone.run(() => {
          let interim = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript + ' ';
              this.transcript$.next(finalTranscript);
            } else {
              interim += transcript;
              this.transcript$.next(finalTranscript + interim);
            }
          }
        });
      };

      this.speechRecognition.onerror = (event: any) => {
        this.ngZone.run(() => {
          this.error$.next(event.error);
        });
      };

      this.speechRecognition.onend = () => {
        this.ngZone.run(() => {
          this.isListening = false;
        });
      };
    } else {
      this.error$.next('Speech recognition not supported in this browser. Please use Chrome or Edge.');
    }
  }


  start() {
    if (!this.speechRecognition) {
      this.error$.next('Speech Recognition is not supported in this browser. Please use Chrome or Edge.');
      return;
    }
    if (!this.isListening) {
      this.isListening = true;
      this.speechRecognition.start();
    }
  }

  stop() {
    if (this.speechRecognition && this.isListening) {
      this.speechRecognition.stop();
      this.isListening = false;
    }
  }
}

