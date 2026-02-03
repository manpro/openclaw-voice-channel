class VoiceChatClient {
  constructor() {
    this.ws = null;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.userId = null;
    this.isRecording = false;

    this.elements = {
      status: document.getElementById('status'),
      micStatus: document.getElementById('mic-status'),
      recordBtn: document.getElementById('recordBtn'),
      chatContainer: document.getElementById('chatContainer'),
    };

    this.init();
  }

  async init() {
    // Ask for microphone permission FIRST
    this.updateStatus('Begär mikrofon...', 'connecting');
    const audioReady = await this.setupAudio();

    if (!audioReady) {
      this.updateStatus('Mikrofon nekad', 'error');
      return;
    }

    this.updateStatus('Ansluter...', 'connecting');
    await this.connectWebSocket();
    this.setupEventListeners();
  }

  async connectWebSocket() {
    // Use wss:// for HTTPS, ws:// for HTTP
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Connect to the same path as the page (Caddy will proxy to WebSocket server)
    const basePath = window.location.pathname.replace(/\/$/, ''); // Remove trailing slash
    const wsUrl = `${protocol}//${window.location.host}${basePath}`;
    console.log('Connecting to WebSocket:', wsUrl);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.updateStatus('Ansluten', 'connected');
      this.elements.recordBtn.disabled = false;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'connected') {
        this.userId = data.userId;
        console.log('Connected as:', this.userId);
      } else if (data.type === 'assistant_message') {
        this.handleAssistantMessage(data);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.updateStatus('Frånkopplad', 'disconnected');
      this.elements.recordBtn.disabled = true;
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.updateStatus('Fel', 'error');
    };
  }

  async setupAudio() {
    try {
      console.log('Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });

      console.log('Microphone access granted!');

      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 128000,
      });

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);

          // Send chunk to server
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(event.data);
          }
        }
      };

      return true;

    } catch (error) {
      console.error('Microphone access denied:', error);
      alert('❌ Mikrofon åtkomst krävs!\n\nKlicka på lås-ikonen i adressfältet och ge tillåtelse för mikrofon.');
      return false;
    }
  }

  setupEventListeners() {
    // Click to toggle recording
    this.elements.recordBtn.addEventListener('click', () => this.toggleRecording());

    // Touch support for mobile
    this.elements.recordBtn.addEventListener('touchend', (e) => {
      e.preventDefault();
      this.toggleRecording();
    });

    // Keyboard shortcut: Space bar
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !e.repeat) {
        e.preventDefault();
        this.toggleRecording();
      }
    });
  }

  toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  startRecording() {
    if (!this.mediaRecorder || this.mediaRecorder.state === 'recording') return;

    this.audioChunks = [];
    this.isRecording = true;
    this.mediaRecorder.start(100); // 100ms chunks

    this.elements.micStatus.textContent = '🎤 Spelar in...';
    this.elements.micStatus.className = 'mic-recording';
    this.elements.recordBtn.classList.add('recording');
    this.elements.recordBtn.querySelector('.btn-text').textContent = 'Tryck för att stoppa';
  }

  stopRecording() {
    if (!this.mediaRecorder || this.mediaRecorder.state !== 'recording') return;

    this.isRecording = false;
    this.mediaRecorder.stop();

    this.elements.micStatus.textContent = '🎤 Bearbetar...';
    this.elements.micStatus.className = 'mic-processing';
    this.elements.recordBtn.classList.remove('recording');
    this.elements.recordBtn.querySelector('.btn-text').textContent = 'Tryck för att prata';

    // Add user message placeholder
    this.addMessage('user', '(Bearbetar din röst...)', true);
  }

  handleAssistantMessage(data) {
    // Update mic status
    this.elements.micStatus.textContent = '🎤 Redo';
    this.elements.micStatus.className = 'mic-inactive';

    // Reset button text
    if (!this.isRecording) {
      this.elements.recordBtn.querySelector('.btn-text').textContent = 'Tryck för att prata';
    }

    // Remove processing placeholder
    const lastMsg = this.elements.chatContainer.lastElementChild;
    if (lastMsg && lastMsg.classList.contains('processing')) {
      lastMsg.remove();
    }

    // Add assistant message
    this.addMessage('assistant', data.text, false);

    // Play audio response
    if (data.audio) {
      this.playAudio(data.audio);
    }
  }

  addMessage(role, text, processing = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;
    if (processing) messageDiv.classList.add('processing');

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? '👤' : '🦞';

    const content = document.createElement('div');
    content.className = 'message-content';
    content.textContent = text;

    const timestamp = document.createElement('div');
    timestamp.className = 'timestamp';
    timestamp.textContent = new Date().toLocaleTimeString('sv-SE');

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    messageDiv.appendChild(timestamp);

    this.elements.chatContainer.appendChild(messageDiv);
    this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
  }

  playAudio(base64Audio) {
    const audioBlob = this.base64ToBlob(base64Audio, 'audio/wav');
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.play().catch(err => {
      console.error('Audio playback failed:', err);
    });

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
    };
  }

  base64ToBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  }

  updateStatus(text, state) {
    this.elements.status.textContent = text;
    this.elements.status.className = `status-${state}`;
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  new VoiceChatClient();
});
