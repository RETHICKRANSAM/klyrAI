/* ═══════════════════════════════════════════════════════
   KLYRA AI — Vanilla JS (Converted from React)
   ═══════════════════════════════════════════════════════ */

// --- SOCKET CONNECTION ---
const socket = io('/', { path: '/socket.io' });

// --- STATE ---
let assistantState = 'Idle';
let isInitialized = false;
let isChatOpen = false;
let isContinuous = true;
let mediaRecorder = null;
let audioStream = null;
let lastSpeakTime = 0;

// --- DOM ELEMENTS ---
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot-small');
const chatPanel = document.getElementById('chat-panel');
const chatFab = document.getElementById('chat-fab');
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const btnStart = document.getElementById('btn-start');
const btnHold = document.getElementById('btn-hold');
const contToggle = document.getElementById('cont-toggle');
const characterGlow = document.getElementById('character-glow');
const characterImg = document.getElementById('character-img');

// --- SOCKET EVENTS ---
socket.on('connect', () => {
    console.log('✅ Connected to KLYRA Backend');
});

socket.on('new_message', (data) => {
    addMessage(data.sender, data.text);
});

socket.on('state_change', (data) => {
    setAssistantState(data.state);
});

socket.on('speak_audio', (data) => {
    const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);
    audio.onplay = () => setAssistantState('Speaking');
    audio.onended = () => {
        setAssistantState('Idle');
        lastSpeakTime = Date.now();
        if (isContinuous) setTimeout(() => startRecording(), 1200);
    };
    audio.play().catch(e => console.error('Audio play error:', e));
});

// --- STATE MANAGEMENT ---
function setAssistantState(state) {
    assistantState = state;
    
    // Update status text
    statusText.textContent = state;
    
    // Update status dot
    statusDot.className = 'status-dot-small';
    if (state === 'Listening') statusDot.classList.add('listening');
    else if (state === 'Speaking') statusDot.classList.add('speaking');
    else if (state === 'Thinking') statusDot.classList.add('thinking');
    
    // Update hold button
    if (btnHold && !btnHold.classList.contains('hidden')) {
        btnHold.classList.toggle('listening', state === 'Listening');
        btnHold.textContent = state === 'Listening' ? 'Listening...' : 'Hold to Speak';
    }
    
    // Update character glow color
    const glowColor = state === 'Speaking' ? '#ff3b5c' :
                      state === 'Listening' ? '#00d4ff' :
                      state === 'Thinking' ? '#ffffff' : '#00d4ff';
    
    if (characterGlow) {
        characterGlow.style.background = `radial-gradient(circle, ${glowColor}55 0%, transparent 70%)`;
    }
    if (characterImg) {
        characterImg.style.filter = `drop-shadow(0 0 20px ${glowColor}44)`;
    }
}

// --- CHAT ---
function addMessage(sender, text) {
    const wrapper = document.createElement('div');
    wrapper.className = `msg-wrapper ${sender === 'User' ? 'msg-user' : 'msg-bot'}`;
    
    const senderEl = document.createElement('div');
    senderEl.className = 'msg-sender';
    senderEl.textContent = sender;
    
    const msgEl = document.createElement('div');
    msgEl.className = `msg ${sender === 'User' ? 'user' : 'bot'}`;
    msgEl.textContent = text;
    
    wrapper.appendChild(senderEl);
    wrapper.appendChild(msgEl);
    chatMessages.appendChild(wrapper);
    
    // Auto-scroll
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function handleSendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    socket.emit('text_input', { text });
    userInput.value = '';
}

function toggleChat(open) {
    isChatOpen = open;
    if (open) {
        chatPanel.classList.remove('hidden');
        chatPanel.classList.remove('closing');
        chatFab.classList.add('hidden');
        // Focus input after animation
        setTimeout(() => userInput.focus(), 400);
    } else {
        chatPanel.classList.add('closing');
        setTimeout(() => {
            chatPanel.classList.add('hidden');
            chatPanel.classList.remove('closing');
            chatFab.classList.remove('hidden');
        }, 300);
    }
}

function initAssistant() {
    socket.emit('init_session');
    isInitialized = true;
    btnStart.classList.add('hidden');
    btnHold.classList.remove('hidden');
    
    // Auto-start listening
    setTimeout(() => startRecording(), 1500);
}

function handleGenderChange(gender) {
    socket.emit('set_gender', { gender });
}

// --- NATIVE BROWSER SPEECH RECOGNITION ---
let recognition = null;
if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN';

    recognition.onstart = () => {
        setAssistantState('Listening');
    };

    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        console.log('🗣️ User Said:', transcript);
        if (transcript.trim()) {
            setAssistantState('Thinking');
            socket.emit('text_input', { text: transcript });
        } else {
            setAssistantState('Idle');
        }
    };

    recognition.onerror = (e) => {
        console.error('Microphone error:', e.error);
        if (e.error === 'not-allowed') {
            alert("Microphone access is blocked! Please allow microphone access in Chrome.");
        }
        setAssistantState('Idle');
    };

    recognition.onend = () => {
        if (assistantState === 'Listening') setAssistantState('Idle');
    };
}

function startRecording() {
    if (assistantState === 'Speaking' || assistantState === 'Thinking') return;
    if (recognition) {
        try { recognition.start(); } catch(e) { console.log("Already listening"); }
    } else {
        alert("Speech Recognition is not supported in this browser. Please use Chrome!");
    }
}

function stopRecording() {
    if (recognition) {
        try { recognition.stop(); } catch(e) {}
    }
}

// --- KEYBOARD ---
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSendMessage();
});

contToggle.addEventListener('change', (e) => {
    isContinuous = e.target.checked;
});

console.log('🚀 KLYRA Frontend loaded (Vanilla JS)');
