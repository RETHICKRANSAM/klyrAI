import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import { Mic, Send, Zap, Ghost, User, Bot, Loader2, Globe, MessageSquare, X, Play, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AssistantCharacter from './AssistantCharacter';

// --- CONFIG ---
const socket = io('/', { path: '/socket.io' });
const SILENCE_THRESHOLD = 30;
const SILENCE_DURATION = 1500;

function App() {
  const [messages, setMessages] = useState([
    { sender: 'Ruby', text: 'KLYRA AI Core Initialized.' }
  ]);
  const [assistantState, setAssistantState] = useState('Idle');
  const [inputText, setInputText] = useState('');
  const [isContinuous, setIsContinuous] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [gender, setGender] = useState('Boy');

  const chatEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);
  const lastSpeakTimeRef = useRef(0);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Socket setup
  useEffect(() => {
    socket.on('connect', () => console.log('Connected to KLYRA Backend'));
    socket.on('new_message', (data) => setMessages(prev => [...prev, data]));
    socket.on('state_change', (data) => setAssistantState(data.state));
    socket.on('speak_audio', (data) => {
      const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);
      audio.onplay = () => setAssistantState('Speaking');
      audio.onended = () => {
        setAssistantState('Idle');
        lastSpeakTimeRef.current = Date.now();
        if (isContinuous) setTimeout(() => startRecording(), 1200);
      };
      audio.play().catch(e => console.error(e));
    });
    return () => { socket.off('new_message'); socket.off('state_change'); socket.off('speak_audio'); };
  }, [isContinuous]);

  // --- RECORDING LOGIC ---
  const startRecording = async () => {
    if (assistantState === 'Speaking' || assistantState === 'Thinking') return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true } });
      streamRef.current = stream;
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      const chunks = [];
      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = () => socket.emit('mobile_audio', { audio: reader.result.split(',')[1] });
        stream.getTracks().forEach(t => t.stop());
      };
      mediaRecorder.start();
      setAssistantState('Listening');
    } catch (err) { console.error(err); }
  };

  const stopRecording = () => mediaRecorderRef.current?.stop();
  const handleSendMessage = () => {
    if (!inputText.trim()) return;
    socket.emit('text_input', { text: inputText });
    setInputText('');
  };
  const initAssistant = () => { socket.emit('init_session'); setIsInitialized(true); };

  return (
    <div className="relative w-screen h-screen bg-[#05060d] text-[#c8d8f0] overflow-hidden font-['Rajdhani']">
      {/* Background Decor */}
      <div className="absolute inset-0 pointer-events-none opacity-20 bg-[linear-gradient(rgba(0,212,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,212,255,0.03)_1px,transparent_1px)] bg-[size:60px_60px]"></div>
      
      {/* Nav */}
      <nav className="absolute top-0 left-0 w-full p-8 flex justify-between items-center z-50">
        <div className="text-2xl font-bold tracking-widest text-white">KLYRA <span className="text-cyan-400 font-light text-sm ml-2">VERSION 3.0</span></div>
        <div className="flex gap-6 text-sm tracking-widest text-[#00d4ff] uppercase">
          <a href="#" className="hover:text-white transition-colors">Documentation</a>
          <a href="#" className="hover:text-white transition-colors">Features</a>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative grid grid-cols-1 lg:grid-cols-2 h-full items-center px-12 lg:px-24">
        {/* Left: Heading & Content */}
        <motion.div 
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex flex-col gap-8"
        >
          <div className="space-y-2">
            <h1 className="text-6xl lg:text-8xl font-black uppercase text-white leading-tight">
              THE FUTURE OF <br /> <span className="text-[#00d4ff]">INTELLIGENCE</span>
            </h1>
            <p className="text-xl text-[#c8d8f0]/60 max-w-lg tracking-wide leading-relaxed">
              Experience KLYRA, the next-generation AI assistant designed for seamless voice interaction and high-performance system orchestration.
            </p>
          </div>

          <div className="flex gap-4">
            {!isInitialized ? (
              <button 
                onClick={initAssistant}
                className="group relative px-8 py-4 bg-[#00d4ff] text-[#05060d] font-bold uppercase tracking-widest rounded-sm overflow-hidden transition-all hover:scale-105"
              >
                <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-0 transition-transform duration-500"></div>
                <span className="relative flex items-center gap-2"><Play fill="currentColor" size={16} /> Start Talking</span>
              </button>
            ) : (
              <button 
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                className={`px-8 py-4 border-2 font-bold uppercase tracking-widest transition-all ${assistantState === 'Listening' ? 'border-[#00d4ff] bg-[#00d4ff]/10 text-[#00d4ff]' : 'border-white/20 text-white hover:border-[#00d4ff]'}`}
              >
                {assistantState === 'Listening' ? 'Listening...' : 'Hold to Speak'}
              </button>
            )}
            <button className="px-8 py-4 border border-white/10 text-white/60 font-medium uppercase tracking-widest hover:bg-white/5 transition-all">Try Demo</button>
          </div>
          
          <div className="flex items-center gap-4 mt-4 text-[#00d4ff]/40 text-xs tracking-widest uppercase">
            <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-green-400"></div> STATUS: {assistantState}</span>
            <span className="w-px h-4 bg-white/10"></span>
            <span>MODEL: GEMINI-2.0-FLASH</span>
          </div>
        </motion.div>

        {/* Right: AI Character */}
        <div className="hidden lg:flex h-full items-center justify-center">
          <AssistantCharacter state={assistantState} />
        </div>
      </main>

      {/* Floating Assistant Button */}
      <AnimatePresence>
        {!isChatOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            onClick={() => setIsChatOpen(true)}
            className="fixed bottom-10 right-10 w-20 h-20 bg-[#00d4ff] rounded-full shadow-[0_0_40px_rgba(0,212,255,0.4)] flex items-center justify-center group overflow-hidden"
          >
            <img src="/klyra_avatar.png" alt="K" className="w-full h-full object-cover transition-transform group-hover:scale-110" />
            <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <MessageSquare className="text-white" />
            </div>
          </motion.button>
        )}

        {/* Chat Interface (Expands from bottom-right) */}
        {isChatOpen && (
          <motion.div
            initial={{ scale: 0, x: 200, y: 300, opacity: 0 }}
            animate={{ scale: 1, x: 0, y: 0, opacity: 1 }}
            exit={{ scale: 0, x: 200, y: 300, opacity: 0 }}
            className="fixed bottom-10 right-10 w-[420px] h-[600px] bg-[#0a0c18] border border-[#00d4ff]/20 shadow-[0_0_100px_rgba(0,0,0,0.8)] flex flex-col z-[100] rounded-lg overflow-hidden backdrop-blur-3xl"
          >
            <div className="p-6 border-b border-white/5 flex justify-between items-center bg-[#00d4ff]/5">
              <div className="flex items-center gap-3">
                <img src="/klyra_avatar.png" className="w-10 h-10 rounded-full border border-[#00d4ff]/50" />
                <div className="text-xs tracking-widest text-[#00d4ff] uppercase font-bold">KLYRA INTERFACE</div>
              </div>
              <button onClick={() => setIsChatOpen(false)} className="text-white/40 hover:text-white"><X size={20} /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex flex-col ${m.sender === 'User' ? 'items-end' : 'items-start'}`}>
                  <div className="text-[10px] uppercase tracking-widest text-white/30 mb-1">{m.sender}</div>
                  <div className={`max-w-[85%] p-4 rounded-lg text-sm leading-relaxed ${m.sender === 'User' ? 'bg-[#00d4ff]/10 border border-[#00d4ff]/20 text-white rounded-tr-none' : 'bg-white/5 border border-white/10 text-[#c8d8f0] rounded-tl-none'}`}>
                    {m.text}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <div className="p-6 border-t border-white/5 space-y-4">
              <div className="flex gap-2">
                <input 
                  autoFocus
                  className="flex-1 bg-white/5 border border-white/10 rounded-sm px-4 py-3 text-sm text-white placeholder:text-white/20 outline-none focus:border-[#00d4ff]/40 transition-colors"
                  placeholder="Ask anything..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <button onClick={handleSendMessage} className="p-3 bg-white/5 border border-white/10 text-white/40 hover:text-[#00d4ff] hover:border-[#00d4ff]/50 transition-all">
                  <Send size={18} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <input type="checkbox" id="cont" checked={isContinuous} onChange={e => setIsContinuous(e.target.checked)} className="accent-[#00d4ff]" />
                    <label htmlFor="cont" className="text-[10px] uppercase tracking-widest text-white/40 cursor-pointer">Live Activation</label>
                </div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-white/40">
                    <span>Voice:</span>
                    <select className="bg-transparent text-[#00d4ff] outline-none cursor-pointer" value={gender} onChange={e => { socket.emit('set_gender', {gender: e.target.value}); setGender(e.target.value); }}>
                        <option value="Boy">Boy</option>
                        <option value="Girl">Girl</option>
                    </select>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Decorative Corner */}
      <div className="fixed top-8 left-8 w-20 h-20 border-t border-l border-white/10 pointer-events-none"></div>
      <div className="fixed bottom-8 right-8 w-20 h-20 border-b border-r border-white/10 pointer-events-none"></div>
    </div>
  );
}

export default App;
