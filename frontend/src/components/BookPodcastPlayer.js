import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Pause, SkipForward, SkipBack, X, ChevronUp, ChevronDown } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

const CHAPTERS = [
  { name: 'Part 1', startPage: 1, endPage: 50 },
  { name: 'Part 2', startPage: 51, endPage: 100 },
  { name: 'Part 3', startPage: 101, endPage: 152 }
];

const PREFETCH_AHEAD = 3;

const BookPodcastPlayer = ({ visible, onClose }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speakablePages, setSpeakablePages] = useState([]);
  const [statusText, setStatusText] = useState('');

  const audioRef = useRef(null);
  const cacheRef = useRef({});      // { pageNum: blobUrl }
  const prefetchingRef = useRef({}); // { pageNum: true } (in-flight)
  const isPlayingRef = useRef(false);
  const { token } = useAuth();

  const speeds = [0.75, 1, 1.25, 1.5, 2];

  // Fetch which pages have speakable content
  useEffect(() => {
    if (!visible) return;
    fetch(`${API}/api/book/audio-status`)
      .then(r => r.json())
      .then(data => {
        setSpeakablePages(data.speakable || []);
      })
      .catch(() => {});
  }, [visible]);

  const getAuthToken = () => token || localStorage.getItem('token') || '';

  // Find next speakable page from given page
  const getNextSpeakable = useCallback((fromPage) => {
    for (let i = fromPage; i <= 152; i++) {
      if (speakablePages.includes(i)) return i;
    }
    return null;
  }, [speakablePages]);

  const getPrevSpeakable = useCallback((fromPage) => {
    for (let i = fromPage; i >= 1; i--) {
      if (speakablePages.includes(i)) return i;
    }
    return null;
  }, [speakablePages]);

  const getCurrentChapter = useCallback(() => {
    for (const ch of CHAPTERS) {
      if (currentPage >= ch.startPage && currentPage <= ch.endPage) return ch;
    }
    return CHAPTERS[0];
  }, [currentPage]);

  // Pre-fetch a single page audio into blob cache
  const prefetchPage = useCallback(async (pageNum) => {
    if (cacheRef.current[pageNum] || prefetchingRef.current[pageNum]) return;
    if (!speakablePages.includes(pageNum)) return;

    prefetchingRef.current[pageNum] = true;
    const authToken = getAuthToken();
    const url = `${API}/api/book/page-audio/${pageNum}?token=${encodeURIComponent(authToken)}`;

    try {
      const res = await fetch(url);
      if (res.ok) {
        const blob = await res.blob();
        cacheRef.current[pageNum] = URL.createObjectURL(blob);
      }
    } catch { /* silent */ }
    delete prefetchingRef.current[pageNum];
  }, [speakablePages]);

  // Pre-fetch next N speakable pages
  const prefetchAhead = useCallback((fromPage) => {
    let count = 0;
    let pg = fromPage;
    while (count < PREFETCH_AHEAD && pg <= 152) {
      if (speakablePages.includes(pg) && !cacheRef.current[pg]) {
        prefetchPage(pg);
        count++;
      }
      pg++;
    }
  }, [speakablePages, prefetchPage]);

  // Play a specific page
  const playPage = useCallback(async (pageNum) => {
    // Stop current audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.onended = null;
      audioRef.current = null;
    }

    // Find the actual speakable page (skip image-only pages)
    const actualPage = getNextSpeakable(pageNum);
    if (!actualPage) {
      setIsPlaying(false);
      isPlayingRef.current = false;
      setStatusText('End of book');
      return;
    }

    setCurrentPage(actualPage);
    setProgress(0);
    setDuration(0);

    // Start prefetching ahead
    prefetchAhead(actualPage + 1);

    // Check cache first
    let audioUrl = cacheRef.current[actualPage];

    if (!audioUrl) {
      setIsLoading(true);
      setStatusText(`Preparing page ${actualPage}...`);

      // Fetch and cache
      const authToken = getAuthToken();
      const url = `${API}/api/book/page-audio/${actualPage}?token=${encodeURIComponent(authToken)}`;
      try {
        const res = await fetch(url);
        if (!res.ok) {
          // Skip this page and try next
          const next = getNextSpeakable(actualPage + 1);
          if (next && isPlayingRef.current) {
            playPage(next);
          } else {
            setIsPlaying(false);
            isPlayingRef.current = false;
            setIsLoading(false);
          }
          return;
        }
        const blob = await res.blob();
        audioUrl = URL.createObjectURL(blob);
        cacheRef.current[actualPage] = audioUrl;
      } catch {
        setIsLoading(false);
        setIsPlaying(false);
        isPlayingRef.current = false;
        return;
      }
    }

    setIsLoading(false);
    setStatusText('');

    const audio = new Audio(audioUrl);
    audio.playbackRate = speed;
    audioRef.current = audio;

    audio.onloadedmetadata = () => setDuration(audio.duration);
    audio.ontimeupdate = () => setProgress(audio.currentTime);

    audio.onended = () => {
      if (isPlayingRef.current) {
        const next = getNextSpeakable(actualPage + 1);
        if (next) {
          playPage(next);
        } else {
          setIsPlaying(false);
          isPlayingRef.current = false;
          setStatusText('Finished');
        }
      }
    };

    audio.onerror = () => {
      // Skip broken page
      if (isPlayingRef.current) {
        const next = getNextSpeakable(actualPage + 1);
        if (next) playPage(next);
        else { setIsPlaying(false); isPlayingRef.current = false; }
      }
    };

    setIsPlaying(true);
    isPlayingRef.current = true;
    audio.play().catch(() => {});
  }, [speed, getNextSpeakable, prefetchAhead]);

  // Toggle play/pause
  const togglePlay = () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
      isPlayingRef.current = false;
    } else if (!isPlaying && audioRef.current && audioRef.current.src) {
      audioRef.current.play().catch(() => {});
      setIsPlaying(true);
      isPlayingRef.current = true;
    } else {
      isPlayingRef.current = true;
      playPage(currentPage);
    }
  };

  const skipNext = () => {
    const next = getNextSpeakable(currentPage + 1);
    if (next) {
      isPlayingRef.current = true;
      playPage(next);
    }
  };

  const skipPrev = () => {
    // If more than 3 seconds in, restart current page
    if (progress > 3 && audioRef.current) {
      audioRef.current.currentTime = 0;
      return;
    }
    const prev = getPrevSpeakable(currentPage - 1);
    if (prev) {
      isPlayingRef.current = true;
      playPage(prev);
    }
  };

  const jumpToChapter = (chapter) => {
    isPlayingRef.current = true;
    playPage(chapter.startPage);
    setExpanded(false);
  };

  const changeSpeed = () => {
    const idx = speeds.indexOf(speed);
    const newSpeed = speeds[(idx + 1) % speeds.length];
    setSpeed(newSpeed);
    if (audioRef.current) audioRef.current.playbackRate = newSpeed;
  };

  const seekTo = (e) => {
    if (!audioRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audioRef.current.currentTime = pct * duration;
  };

  // Cleanup
  useEffect(() => {
    return () => {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
      // Revoke all blob URLs
      Object.values(cacheRef.current).forEach(url => URL.revokeObjectURL(url));
      cacheRef.current = {};
    };
  }, []);

  // Update speed on existing audio
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = speed;
  }, [speed]);

  const formatTime = (s) => {
    if (!s || isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const chapter = getCurrentChapter();
  const pageInChapter = currentPage - chapter.startPage + 1;
  const totalInChapter = chapter.endPage - chapter.startPage + 1;

  if (!visible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        className="fixed bottom-0 left-0 right-0 z-[9998]"
        data-testid="podcast-player"
      >
        {/* Expanded Chapter List */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="bg-[#2a1a10]/95 backdrop-blur-lg border-t border-[#D4AF37]/20 overflow-hidden"
            >
              <div className="max-w-2xl mx-auto p-4 space-y-2">
                <p className="text-[#D4AF37]/60 text-xs font-body uppercase tracking-wider mb-3">Chapters</p>
                {CHAPTERS.map((ch) => (
                  <button
                    key={ch.name}
                    onClick={() => jumpToChapter(ch)}
                    className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-all ${
                      currentPage >= ch.startPage && currentPage <= ch.endPage
                        ? 'bg-[#D4AF37]/15 text-[#D4AF37]'
                        : 'text-[#D4AF37]/50 hover:bg-[#D4AF37]/5 hover:text-[#D4AF37]/80'
                    }`}
                    data-testid={`chapter-${ch.name}`}
                  >
                    <div>
                      <p className="text-sm font-heading">{ch.name}</p>
                      <p className="text-[10px] font-body opacity-60">Pages {ch.startPage}–{ch.endPage}</p>
                    </div>
                    {currentPage >= ch.startPage && currentPage <= ch.endPage && (
                      <span className="text-[10px] font-body bg-[#D4AF37]/20 px-2 py-1 rounded-full">
                        Page {pageInChapter}/{totalInChapter}
                      </span>
                    )}
                  </button>
                ))}

                {/* Speed Control */}
                <div className="flex items-center justify-between pt-3 border-t border-[#D4AF37]/10">
                  <p className="text-[#D4AF37]/60 text-xs font-body">Playback Speed</p>
                  <div className="flex gap-2">
                    {speeds.map(s => (
                      <button
                        key={s}
                        onClick={() => setSpeed(s)}
                        className={`px-3 py-1 rounded-full text-xs font-body font-semibold transition-all ${
                          speed === s ? 'bg-[#D4AF37] text-[#3D2314]' : 'text-[#D4AF37]/50 border border-[#D4AF37]/20 hover:border-[#D4AF37]/50'
                        }`}
                        data-testid={`speed-${s}`}
                      >
                        {s}x
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Mini Player Bar */}
        <div className="bg-[#1a1008]/95 backdrop-blur-lg border-t border-[#D4AF37]/20">
          {/* Progress Bar */}
          <div className="h-1 cursor-pointer group" onClick={seekTo}>
            <div className="h-full bg-[#D4AF37]/20 relative">
              <div
                className="h-full bg-[#D4AF37] transition-all duration-200"
                style={{ width: duration ? `${(progress / duration) * 100}%` : '0%' }}
              />
            </div>
          </div>

          <div className="max-w-2xl mx-auto flex items-center gap-4 px-4 py-3">
            {/* Info */}
            <button onClick={() => setExpanded(!expanded)} className="flex-1 min-w-0 text-left">
              <p className="text-[#D4AF37] text-sm font-heading truncate">
                {chapter.name} — Page {currentPage}
              </p>
              <p className="text-[#D4AF37]/40 text-[10px] font-body">
                {statusText || `${formatTime(progress)} / ${formatTime(duration)}`}
              </p>
            </button>

            {/* Controls */}
            <div className="flex items-center gap-2">
              <button onClick={skipPrev} className="p-2 text-[#D4AF37]/60 hover:text-[#D4AF37] transition-colors">
                <SkipBack className="w-4 h-4" />
              </button>
              <button
                onClick={togglePlay}
                disabled={isLoading}
                className="p-3 rounded-full transition-all"
                style={{ background: 'linear-gradient(145deg, #D4AF37, #B8962E)' }}
                data-testid="podcast-play-btn"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-[#3D2314]/30 border-t-[#3D2314] rounded-full animate-spin" />
                ) : isPlaying ? (
                  <Pause className="w-5 h-5 text-[#3D2314]" />
                ) : (
                  <Play className="w-5 h-5 text-[#3D2314]" />
                )}
              </button>
              <button onClick={skipNext} className="p-2 text-[#D4AF37]/60 hover:text-[#D4AF37] transition-colors">
                <SkipForward className="w-4 h-4" />
              </button>
            </div>

            {/* Speed & Expand */}
            <div className="flex items-center gap-2">
              <button
                onClick={changeSpeed}
                className="px-2 py-1 rounded-full text-[10px] font-body font-bold text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/10"
                data-testid="speed-btn"
              >
                {speed}x
              </button>
              <button onClick={() => setExpanded(!expanded)} className="p-1 text-[#D4AF37]/40 hover:text-[#D4AF37]">
                {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
              </button>
              <button onClick={() => {
                if (audioRef.current) audioRef.current.pause();
                isPlayingRef.current = false;
                setIsPlaying(false);
                onClose();
              }} className="p-1 text-[#D4AF37]/30 hover:text-[#D4AF37]">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default BookPodcastPlayer;
