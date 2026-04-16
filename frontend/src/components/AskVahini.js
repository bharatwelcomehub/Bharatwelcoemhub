import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Mic, MicOff, Shuffle, Share2, ShoppingBag, BookOpen, Calendar, MapPin, MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL;

const AskVahini = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const recognitionRef = useRef(null);
  const navigate = useNavigate();

  const getRegion = () => localStorage.getItem('purnabramha_country') || 'India';
  const isAustralia = () => getRegion() === 'Australia';
  const currencySymbol = () => isAustralia() ? '$' : '₹';
  const getPrice = (dish) => isAustralia() ? dish.price_aud : dish.price_inr;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-IN';
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsListening(false);
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);
      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;

    const userMsg = { role: 'user', content: text.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const now = new Date();
      const hours = now.getHours();
      let timeOfDay = 'morning';
      if (hours >= 12 && hours < 17) timeOfDay = 'afternoon';
      else if (hours >= 17 && hours < 21) timeOfDay = 'evening';
      else if (hours >= 21) timeOfDay = 'night';

      const res = await fetch(`${API}/api/vahini/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          session_id: sessionId,
          context: { time_of_day: timeOfDay, region: getRegion() }
        })
      });

      const data = await res.json();

      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message,
        recommended_dishes: data.recommended_dishes || [],
        cultural_note: data.cultural_note || ''
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Vahini is resting right now. Please try again in a moment.',
        recommended_dishes: [],
        cultural_note: ''
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleRandomDish = async () => {
    if (loading) return;
    setLoading(true);

    setMessages(prev => [...prev, { role: 'user', content: 'Let Vahini Choose For Me!' }]);

    try {
      const res = await fetch(`${API}/api/vahini/random-dish?region=${getRegion()}`);
      const data = await res.json();

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message,
        recommended_dishes: data.dish ? [data.dish] : [],
        cultural_note: '',
        isRandomPick: true
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Vahini could not pick a dish right now. Please try again!',
        recommended_dishes: [],
        cultural_note: ''
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleShare = (dish, platform) => {
    const text = `Today Vahini told me to eat ${dish.name} from Purnabramha! Try authentic Maharashtrian food at www.purnabramha.com`;
    const url = 'https://www.purnabramha.com/menu';

    if (platform === 'whatsapp') {
      window.open(`https://wa.me/?text=${encodeURIComponent(text + '\n' + url)}`, '_blank');
    } else if (platform === 'facebook') {
      window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}&quote=${encodeURIComponent(text)}`, '_blank');
    } else if (platform === 'copy') {
      navigator.clipboard.writeText(text + '\n' + url);
    }
    setShowShareMenu(null);
  };

  const quickQuestions = [
    "What should I eat today?",
    "I have acidity, suggest food",
    "Maharashtrian breakfast ideas",
    "Food for summer",
    "Festival dishes"
  ];

  return (
    <>
      {/* Floating Vahini Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-[9999] w-16 h-16 rounded-full shadow-[0_4px_24px_rgba(180,150,46,0.4)] flex items-center justify-center group"
            style={{
              background: 'linear-gradient(145deg, #D4AF37, #B8962E, #9A7B2D)'
            }}
            data-testid="ask-vahini-fab"
          >
            <MessageCircle className="w-7 h-7 text-white" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#3D2314] rounded-full flex items-center justify-center">
              <span className="text-[8px] text-[#D4AF37] font-bold">V</span>
            </span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Tooltip for FAB */}
      {!isOpen && (
        <div className="fixed bottom-[88px] right-6 z-[9999] pointer-events-none">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 2 }}
            className="bg-[#3D2314] text-[#D4AF37] text-xs px-3 py-1.5 rounded-lg shadow-lg font-body whitespace-nowrap"
          >
            Ask Vahini
          </motion.div>
        </div>
      )}

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: 'spring', damping: 25 }}
            className="fixed bottom-4 right-4 z-[9999] w-[380px] max-w-[calc(100vw-32px)] h-[600px] max-h-[calc(100vh-100px)] flex flex-col rounded-2xl overflow-hidden shadow-[0_8px_40px_rgba(0,0,0,0.25)]"
            data-testid="ask-vahini-chat"
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-5 py-4 flex-shrink-0"
              style={{
                background: 'linear-gradient(135deg, #3D2314, #5A3520)'
              }}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full flex items-center justify-center"
                  style={{ background: 'linear-gradient(145deg, #D4AF37, #B8962E)' }}>
                  <span className="text-white font-heading text-lg font-bold">V</span>
                </div>
                <div>
                  <h3 className="text-[#D4AF37] font-heading text-base font-semibold tracking-wide">Ask Vahini</h3>
                  <p className="text-[#D4AF37]/60 text-[10px] font-body tracking-wider">Purnabramha Food Wisdom</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-[#D4AF37]/70 hover:text-[#D4AF37] transition-colors p-1"
                data-testid="close-vahini"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-[#FDFBF7]"
              style={{ scrollbarWidth: 'thin' }}>

              {/* Welcome message if empty */}
              {messages.length === 0 && (
                <div className="text-center py-6">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
                    style={{ background: 'linear-gradient(145deg, #D4AF37, #B8962E)' }}>
                    <span className="text-white font-heading text-2xl font-bold">V</span>
                  </div>
                  <p className="text-[#3D2314] font-heading text-lg mb-1">Confused about what to eat?</p>
                  <p className="text-[#7A6F65] text-sm font-body mb-6">Ask Vahini.</p>

                  {/* Quick Questions */}
                  <div className="flex flex-wrap gap-2 justify-center px-2">
                    {quickQuestions.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(q)}
                        className="text-xs font-body px-3 py-1.5 rounded-full border border-[#D4AF37]/30 text-[#B8962E] hover:bg-[#D4AF37]/10 hover:border-[#D4AF37]/50 transition-all"
                        data-testid={`quick-q-${i}`}
                      >
                        {q}
                      </button>
                    ))}
                  </div>

                  {/* Vahini Decides Button */}
                  <button
                    onClick={handleRandomDish}
                    className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-body font-semibold text-[#3D2314] transition-all hover:shadow-lg"
                    style={{ background: 'linear-gradient(145deg, #D4AF37, #F3D060, #D4AF37)' }}
                    data-testid="vahini-decides-btn"
                  >
                    <Shuffle className="w-4 h-4" />
                    Let Vahini Choose For Me
                  </button>

                  {/* Book Promotion */}
                  <button
                    onClick={() => { setIsOpen(false); navigate('/book'); }}
                    className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-body text-[#B8962E] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/10 transition-all"
                    data-testid="vahini-book-link"
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    Read Our Book — When a Restaurant Becomes Human
                  </button>
                </div>
              )}

              {/* Chat Messages */}
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] ${msg.role === 'user'
                    ? 'bg-[#3D2314] text-[#F3D060] rounded-2xl rounded-br-md px-4 py-3'
                    : 'bg-white border border-[#E8DFD0] rounded-2xl rounded-bl-md px-4 py-3 shadow-sm'
                    }`}>
                    <p className={`text-sm font-body leading-relaxed whitespace-pre-wrap ${msg.role === 'user' ? '' : 'text-[#3D2314]'}`}>
                      {msg.content}
                    </p>

                    {/* Cultural Note */}
                    {msg.cultural_note && (
                      <p className="text-[10px] text-[#B8962E] mt-2 italic font-body border-t border-[#E8DFD0] pt-2">
                        {msg.cultural_note}
                      </p>
                    )}

                    {/* Recommended Dishes */}
                    {msg.recommended_dishes?.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {msg.recommended_dishes.map((dish, j) => (
                          <DishCard
                            key={j}
                            dish={dish}
                            navigate={navigate}
                            setIsOpen={setIsOpen}
                            onShare={() => setShowShareMenu(showShareMenu === `${i}-${j}` ? null : `${i}-${j}`)}
                            showShare={showShareMenu === `${i}-${j}`}
                            handleShare={handleShare}
                            currencySymbol={currencySymbol()}
                            getPrice={getPrice}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Loading */}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-[#E8DFD0] rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                    <div className="flex gap-1.5">
                      <span className="w-2 h-2 bg-[#D4AF37] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-[#D4AF37] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-[#D4AF37] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Vahini Decides - persistent button (only shown when messages exist) */}
            {messages.length > 0 && (
              <div className="px-4 py-2 bg-[#F8F5F0] border-t border-[#E8DFD0] flex-shrink-0">
                <button
                  onClick={handleRandomDish}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-body font-semibold text-[#B8962E] hover:bg-[#D4AF37]/10 transition-all disabled:opacity-50"
                  data-testid="vahini-decides-inline"
                >
                  <Shuffle className="w-3.5 h-3.5" />
                  Let Vahini Choose For Me
                </button>
              </div>
            )}

            {/* Input Area */}
            <div className="px-4 py-3 bg-white border-t border-[#E8DFD0] flex-shrink-0">
              <div className="flex items-center gap-2">
                {recognitionRef.current && (
                  <button
                    onClick={toggleListening}
                    className={`p-2.5 rounded-full transition-all ${isListening
                      ? 'bg-red-500/10 text-red-500'
                      : 'text-[#B8962E] hover:bg-[#D4AF37]/10'
                      }`}
                    data-testid="voice-input-btn"
                  >
                    {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                  </button>
                )}
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
                  placeholder="Ask Vahini about food..."
                  className="flex-1 text-sm font-body bg-[#F8F5F0] border border-[#E8DFD0] rounded-full px-4 py-2.5 focus:outline-none focus:border-[#D4AF37]/50 text-[#3D2314] placeholder:text-[#7A6F65]/50"
                  data-testid="vahini-input"
                  disabled={loading}
                />
                <button
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || loading}
                  className="p-2.5 rounded-full text-white disabled:opacity-40 transition-all"
                  style={{ background: 'linear-gradient(145deg, #D4AF37, #B8962E)' }}
                  data-testid="vahini-send-btn"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
              <p className="text-center text-[8px] text-[#7A6F65]/40 mt-2 font-body tracking-wider">
                Food is not just eating. It is wisdom. — Vahini | Purnabramha
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};


const DishCard = ({ dish, navigate, setIsOpen, onShare, showShare, handleShare, currencySymbol, getPrice }) => {
  const price = getPrice(dish);
  return (
    <div className="bg-[#F8F5F0] rounded-xl p-3 border border-[#E8DFD0]">
      <div className="flex items-start gap-3">
        {dish.image_url && (
          <img
            src={dish.image_url}
            alt={dish.name}
            className="w-14 h-14 rounded-lg object-cover flex-shrink-0"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-heading font-semibold text-[#3D2314] truncate">{dish.name}</p>
          <p className="text-[10px] text-[#7A6F65] font-body">{dish.category}</p>
          <div className="flex items-center gap-2 mt-1">
            {price && (
              <span className="text-xs font-body font-bold text-[#B8962E]">
                {currencySymbol}{price}
              </span>
            )}
            {dish.no_onion_garlic && (
              <span className="text-[8px] px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded-full font-body">Jain</span>
            )}
            {dish.fasting_friendly && (
              <span className="text-[8px] px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded-full font-body">Fasting</span>
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-1.5 mt-3">
        <button
          onClick={() => { setIsOpen(false); navigate('/pickup'); }}
          className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-[10px] font-body font-semibold text-white"
          style={{ background: 'linear-gradient(145deg, #D4AF37, #B8962E)' }}
          data-testid={`order-${dish.id}`}
        >
          <ShoppingBag className="w-3 h-3" />
          Order
        </button>
        <button
          onClick={() => { setIsOpen(false); navigate('/table-booking'); }}
          className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-[10px] font-body font-semibold text-[#B8962E] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/10"
          data-testid={`book-${dish.id}`}
        >
          <Calendar className="w-3 h-3" />
          Book Table
        </button>
        <button
          onClick={() => { setIsOpen(false); navigate('/locations'); }}
          className="p-1.5 rounded-lg text-[#B8962E] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/10"
          data-testid={`locate-${dish.id}`}
        >
          <MapPin className="w-3 h-3" />
        </button>
        <div className="relative">
          <button
            onClick={onShare}
            className="p-1.5 rounded-lg text-[#B8962E] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/10"
            data-testid={`share-${dish.id}`}
          >
            <Share2 className="w-3 h-3" />
          </button>
          {showShare && (
            <div className="absolute bottom-full right-0 mb-1 bg-white border border-[#E8DFD0] rounded-lg shadow-lg p-2 min-w-[120px] z-10">
              <button
                onClick={() => handleShare(dish, 'whatsapp')}
                className="w-full text-left text-[10px] font-body px-2 py-1.5 hover:bg-[#F8F5F0] rounded text-[#3D2314] flex items-center gap-2"
              >
                <span className="text-green-600 text-sm">W</span> WhatsApp
              </button>
              <button
                onClick={() => handleShare(dish, 'facebook')}
                className="w-full text-left text-[10px] font-body px-2 py-1.5 hover:bg-[#F8F5F0] rounded text-[#3D2314] flex items-center gap-2"
              >
                <span className="text-blue-600 text-sm">f</span> Facebook
              </button>
              <button
                onClick={() => handleShare(dish, 'copy')}
                className="w-full text-left text-[10px] font-body px-2 py-1.5 hover:bg-[#F8F5F0] rounded text-[#3D2314] flex items-center gap-2"
              >
                <BookOpen className="w-3 h-3" /> Copy Link
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AskVahini;
