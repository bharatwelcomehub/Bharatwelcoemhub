import { useState, useEffect, useRef, useCallback, forwardRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import HTMLFlipBook from 'react-pageflip';
import { ChevronLeft, ChevronRight, Bookmark, BookmarkCheck, ArrowLeft, Volume2, VolumeX, X, Home, Headphones, Pause, Play, SkipForward, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';
import BookPodcastPlayer from '@/components/BookPodcastPlayer';

const API = process.env.REACT_APP_BACKEND_URL;

// Page component must use forwardRef for react-pageflip
const PageContent = forwardRef(({ pageNum, authToken }, ref) => {
  const imgSrc = `${API}/api/book/page-image/${pageNum}?token=${encodeURIComponent(authToken || '')}`;
  return (
    <div ref={ref} className="page-content" data-testid={`book-page-${pageNum}`}>
      <div
        className="h-full w-full"
        style={{
          background: '#FFFBF5',
          userSelect: 'none',
          WebkitUserSelect: 'none'
        }}
      >
        <img
          src={imgSrc}
          alt={`Page ${pageNum}`}
          className="w-full h-full object-contain"
          draggable="false"
          onContextMenu={(e) => e.preventDefault()}
          style={{ pointerEvents: 'none' }}
          loading="lazy"
        />
      </div>
    </div>
  );
});
PageContent.displayName = 'PageContent';

const BookReader = () => {
  const { part } = useParams();
  const partNumber = parseInt(part) || 1;
  const [pages, setPages] = useState([]);
  const [partInfo, setPartInfo] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [bookmarks, setBookmarks] = useState([]);
  const [musicOn, setMusicOn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 560 });
  const [showBreak, setShowBreak] = useState(false);
  const [pagesFlipped, setPagesFlipped] = useState(0);
  const [readerSettings, setReaderSettings] = useState({ break_interval: 20, break_shayaris: [], listen_enabled: true });
  const [listenMode, setListenMode] = useState(false);
  const [narrationPlaying, setNarrationPlaying] = useState(false);
  const [narrationLoading, setNarrationLoading] = useState(false);
  const [autoPlay, setAutoPlay] = useState(false);
  const [showPodcast, setShowPodcast] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [isFullPage, setIsFullPage] = useState(false);
  const listenEnabled = readerSettings.listen_enabled !== false;
  const bookRef = useRef(null);
  const audioRef = useRef(null);
  const narrationRef = useRef(null);
  const { user, token } = useAuth();
  const navigate = useNavigate();

  // Default shayaris (used if admin hasn't set custom ones)
  const defaultShayaris = [
    "Thodi der rukkar padhna,\nkabhi kabhi lafzon ko bhi\nsaans lene deni chahiye.",
    "Kitaab koi bhi ho,\nchai ke bina\nmukammal nahi hoti.",
    "Zindagi ki sabse acchi kitaab\nwoh hoti hai jo padhte waqt\nchai thandi ho jaaye.",
    "Alfaaz ruk jaayein toh samjho,\nunhein bhi ek cup chai ki zaroorat hai.",
    "Har ek panna ek safar hai,\naur har safar mein\nek chai break zaroori hai."
  ];
  const shayaris = readerSettings.break_shayaris?.length > 0 ? readerSettings.break_shayaris : defaultShayaris;

  // Fetch reader settings from DB
  useEffect(() => {
    fetch(`${API}/api/book/settings`)
      .then(r => r.json())
      .then(data => setReaderSettings(data))
      .catch(() => {});
  }, []);

  // Reading protection
  useEffect(() => {
    const preventCopy = (e) => e.preventDefault();
    const preventKeys = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 's' || e.key === 'c' || e.key === 'a')) {
        e.preventDefault();
      }
      if (e.key === 'PrintScreen') e.preventDefault();
    };
    document.addEventListener('copy', preventCopy);
    document.addEventListener('cut', preventCopy);
    document.addEventListener('contextmenu', preventCopy);
    document.addEventListener('keydown', preventKeys);
    return () => {
      document.removeEventListener('copy', preventCopy);
      document.removeEventListener('cut', preventCopy);
      document.removeEventListener('contextmenu', preventCopy);
      document.removeEventListener('keydown', preventKeys);
    };
  }, []);

  // Responsive dimensions — maximize reading area
  useEffect(() => {
    const updateDimensions = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const topBar = 52;   // top bar height
      const bottomBar = 60; // bottom controls height
      const padding = 16;
      const availH = h - topBar - bottomBar - padding;
      
      if (w < 640) {
        // Mobile — full width single page
        const pw = w - 16;
        const ph = Math.min(availH, pw * 1.5);
        setDimensions({ width: pw, height: ph });
      } else if (w < 1024) {
        // Tablet — large single page
        const pw = Math.min(w - 40, 600);
        const ph = Math.min(availH, pw * 1.5);
        setDimensions({ width: pw, height: ph });
      } else {
        // Desktop — tall and wide
        const ph = availH;
        const pw = Math.min(Math.floor(ph / 1.5), w - 80, 700);
        setDimensions({ width: pw, height: ph });
      }
    };
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const [isPreview, setIsPreview] = useState(false);

  // Fetch pages
  useEffect(() => {
    fetchPages();
    if (token) fetchBookmarks();
  }, [partNumber, token]);

  const fetchPages = async () => {
    try {
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API}/api/book/pages/${partNumber}`, { headers });
      if (res.status === 403 || res.status === 401) { 
        setError('Please purchase this part to continue reading'); 
        setLoading(false); 
        return; 
      }
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setPartInfo(data.part);
      setPages(data.pages || []);
      setIsPreview(data.is_preview || false);
    } catch { setError('Failed to load book pages'); }
    setLoading(false);
  };

  const fetchBookmarks = async () => {
    try {
      const res = await fetch(`${API}/api/book/bookmarks`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setBookmarks(await res.json());
    } catch { /* ignore */ }
  };

  // Save progress
  const saveProgress = useCallback(async (pageNum) => {
    if (!token) return;
    try {
      await fetch(`${API}/api/book/progress`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ last_page: pageNum, last_part: partNumber })
      });
    } catch { /* ignore */ }
  }, [token, partNumber]);

  const onFlip = useCallback((e) => {
    const pageIdx = e.data;
    setCurrentPage(pageIdx);
    const actualPageNum = (partInfo?.start_page || 1) + pageIdx;
    saveProgress(actualPageNum);
    
    // Tea/coffee break based on admin setting
    setPagesFlipped(prev => {
      const newCount = prev + 1;
      const interval = readerSettings.break_interval || 20;
      if (newCount > 0 && newCount % interval === 0) {
        setTimeout(() => setShowBreak(true), 500);
      }
      return newCount;
    });
  }, [partInfo, saveProgress]);

  const toggleBookmark = async () => {
    const actualPageNum = (partInfo?.start_page || 1) + currentPage;
    const isBookmarked = bookmarks.some(b => b.page_number === actualPageNum);

    try {
      if (isBookmarked) {
        await fetch(`${API}/api/book/bookmark/${actualPageNum}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        toast.success('Bookmark removed');
      } else {
        await fetch(`${API}/api/book/bookmark`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ page_number: actualPageNum })
        });
        toast.success('Page bookmarked');
      }
      fetchBookmarks();
    } catch { toast.error('Failed to update bookmark'); }
  };

  // Music - served from backend (cache-busted)
  const toggleMusic = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio(`${API}/api/book/ambient-music?t=${Date.now()}`);
      audioRef.current.loop = true;
      audioRef.current.volume = 0.15;
    }
    if (musicOn) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch((err) => {
        console.log('Music play failed:', err);
        toast.error('Tap again to play music');
      });
    }
    setMusicOn(!musicOn);
  };

  // Cleanup music on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
      if (narrationRef.current) { narrationRef.current.pause(); narrationRef.current = null; }
    };
  }, []);

  // Narration functions
  const playNarration = async (pageNum) => {
    // Stop any current narration
    if (narrationRef.current) {
      narrationRef.current.pause();
      narrationRef.current = null;
    }

    setNarrationLoading(true);
    setNarrationPlaying(false);

    const authToken = token || '';
    const url = `${API}/api/book/page-audio/${pageNum}?token=${encodeURIComponent(authToken)}&t=${Date.now()}`;

    try {
      const audio = new Audio(url);
      narrationRef.current = audio;

      audio.oncanplaythrough = () => {
        setNarrationLoading(false);
        setNarrationPlaying(true);
        audio.play().catch(() => {});
      };

      audio.onended = () => {
        setNarrationPlaying(false);
        // Auto-advance to next page if autoPlay is on
        if (autoPlay) {
          bookRef.current?.pageFlip()?.flipNext();
          setTimeout(() => {
            const nextPageNum = pageNum + 1;
            playNarration(nextPageNum);
          }, 1000);
        }
      };

      audio.onerror = () => {
        setNarrationLoading(false);
        setNarrationPlaying(false);
        // Silently skip pages without audio (image pages)
      };

      audio.load();
    } catch {
      setNarrationLoading(false);
    }
  };

  const stopNarration = () => {
    if (narrationRef.current) {
      narrationRef.current.pause();
      narrationRef.current = null;
    }
    setNarrationPlaying(false);
    setNarrationLoading(false);
  };

  const toggleListenMode = () => {
    if (listenMode) {
      // Turn off
      stopNarration();
      setAutoPlay(false);
      setListenMode(false);
    } else {
      // Turn on — start narrating current page
      setListenMode(true);
      setAutoPlay(true);
      const pageNum = (partInfo?.start_page || 1) + currentPage;
      playNarration(pageNum);
    }
  };

  const actualPageNum = (partInfo?.start_page || 1) + currentPage;
  const isBookmarked = bookmarks.some(b => b.page_number === actualPageNum);
  const totalPages = pages.length;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#1a1008] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-[#D4AF37]/30 border-t-[#D4AF37] rounded-full animate-spin mx-auto mb-4" />
          <p className="text-[#D4AF37]/60 font-body text-sm">Opening your book...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#1a1008] flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <p className="text-[#D4AF37] font-heading text-xl mb-4">{error}</p>
          <button
            onClick={() => navigate('/book')}
            className="px-6 py-2 text-sm font-body text-[#3D2314] rounded-none"
            style={{ background: 'linear-gradient(145deg, #D4AF37, #B8962E)' }}
          >
            Back to Book
          </button>
        </div>
      </div>
    );
  }

  // Build page array - fill gaps with placeholder pages
  const startPage = partInfo?.start_page || 1;
  const endPage = partInfo?.end_page || 50;
  const allPages = [];
  for (let i = startPage; i <= endPage; i++) {
    const found = pages.find(p => p.page_number === i);
    allPages.push(found || null);
  }

  return (
    <div
      className="min-h-screen flex flex-col select-none"
      style={{ background: 'linear-gradient(180deg, #1a1008, #2a1a10, #1a1008)', userSelect: 'none' }}
      onContextMenu={(e) => e.preventDefault()}
      data-testid="book-reader"
    >
      {/* Top Bar */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#1a1008]/90 border-b border-[#D4AF37]/10 flex-shrink-0">
        <button
          onClick={() => navigate('/book')}
          className="flex items-center gap-2 text-[#D4AF37]/70 hover:text-[#D4AF37] text-sm font-body transition-colors"
          data-testid="back-to-book"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Back</span>
        </button>

        <div className="text-center">
          <p className="text-[#D4AF37] font-heading text-sm tracking-wide">{partInfo?.name || 'Reading'}</p>
          <p className="text-[#D4AF37]/40 text-[10px] font-body">Page {actualPageNum} of {endPage}</p>
        </div>

        <div className="flex items-center gap-2">
          {/* Listen Mode / Podcast */}
          {listenEnabled && (
            <>
              <button
                onClick={toggleListenMode}
                className={`p-2 rounded-full transition-colors flex items-center gap-1 ${listenMode ? 'text-[#D4AF37] bg-[#D4AF37]/10' : 'text-[#D4AF37]/40 hover:text-[#D4AF37]/70'}`}
                data-testid="listen-toggle"
                title="Read aloud this page"
              >
                {narrationLoading ? (
                  <div className="w-4 h-4 border border-[#D4AF37]/50 border-t-[#D4AF37] rounded-full animate-spin" />
                ) : listenMode ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Headphones className="w-4 h-4" />
                )}
                <span className="text-[9px] font-body hidden sm:inline">{listenMode ? 'Stop' : 'Listen'}</span>
              </button>
              <button
                onClick={() => { stopNarration(); setListenMode(false); setShowPodcast(!showPodcast); }}
                className={`p-2 rounded-full transition-colors flex items-center gap-1 ${showPodcast ? 'text-[#D4AF37] bg-[#D4AF37]/10' : 'text-[#D4AF37]/40 hover:text-[#D4AF37]/70'}`}
                data-testid="podcast-toggle"
                title="Podcast mode — listen to the whole book"
              >
                <Play className="w-3.5 h-3.5" />
                <span className="text-[9px] font-body hidden sm:inline">Podcast</span>
              </button>
            </>
          )}
          <button
            onClick={toggleMusic}
            className={`p-2 rounded-full transition-colors ${musicOn ? 'text-[#D4AF37] bg-[#D4AF37]/10' : 'text-[#D4AF37]/40 hover:text-[#D4AF37]/70'}`}
            data-testid="music-toggle"
          >
            {musicOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>
          <button
            onClick={toggleBookmark}
            className={`p-2 rounded-full transition-colors ${isBookmarked ? 'text-[#D4AF37] bg-[#D4AF37]/10' : 'text-[#D4AF37]/40 hover:text-[#D4AF37]/70'}`}
            data-testid="bookmark-toggle"
          >
            {isBookmarked ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
          </button>
          {/* Zoom Controls */}
          <div className="flex items-center gap-0.5 ml-1 border-l border-[#D4AF37]/10 pl-2">
            <button
              onClick={() => setZoom(z => Math.max(0.8, z - 0.2))}
              className="p-1.5 text-[#D4AF37]/40 hover:text-[#D4AF37] rounded-full transition-colors"
              data-testid="zoom-out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[9px] text-[#D4AF37]/50 font-body min-w-[30px] text-center">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom(z => Math.min(2.5, z + 0.2))}
              className="p-1.5 text-[#D4AF37]/40 hover:text-[#D4AF37] rounded-full transition-colors"
              data-testid="zoom-in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => { setIsFullPage(!isFullPage); setZoom(1); }}
              className={`p-1.5 rounded-full transition-colors ${isFullPage ? 'text-[#D4AF37] bg-[#D4AF37]/10' : 'text-[#D4AF37]/40 hover:text-[#D4AF37]'}`}
              data-testid="fullpage-toggle"
              title="Full page view"
            >
              <Maximize className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Listen Mode Banner */}
      {listenEnabled && listenMode && (
        <div className="px-4 py-2 bg-[#D4AF37]/10 border-t border-[#D4AF37]/20 flex-shrink-0">
          <div className="flex items-center justify-center gap-3">
            {narrationLoading ? (
              <p className="text-[#D4AF37] text-xs font-body animate-pulse">Generating narration for page {actualPageNum}...</p>
            ) : narrationPlaying ? (
              <p className="text-[#D4AF37] text-xs font-body flex items-center gap-2">
                <span className="flex gap-0.5">
                  <span className="w-1 h-3 bg-[#D4AF37] rounded-full animate-pulse" />
                  <span className="w-1 h-4 bg-[#D4AF37] rounded-full animate-pulse" style={{animationDelay:'150ms'}} />
                  <span className="w-1 h-2 bg-[#D4AF37] rounded-full animate-pulse" style={{animationDelay:'300ms'}} />
                </span>
                Listening to page {actualPageNum}... Auto-advance ON
              </p>
            ) : (
              <button
                onClick={() => playNarration(actualPageNum)}
                className="text-[#D4AF37] text-xs font-body flex items-center gap-1 hover:underline"
              >
                <Play className="w-3 h-3" /> Play this page
              </button>
            )}
          </div>
        </div>
      )}

      {/* Book Area */}
      <div className="flex-1 flex items-center justify-center px-2 py-1 overflow-auto"
        style={{ touchAction: 'pan-x pan-y pinch-zoom' }}>
        {isFullPage ? (
          /* Full Page Scroll Mode — single page at a time, scrollable, zoomable */
          <div
            className="w-full h-full flex items-center justify-center overflow-auto"
            style={{ touchAction: 'pan-x pan-y pinch-zoom' }}
          >
            <div style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 0.2s' }}>
              <img
                src={`${API}/api/book/page-image/${(partInfo?.start_page || 1) + currentPage}?token=${encodeURIComponent(token || '')}`}
                alt={`Page ${(partInfo?.start_page || 1) + currentPage}`}
                className="max-w-none shadow-2xl"
                style={{ width: dimensions.width, height: 'auto' }}
                draggable="false"
                onContextMenu={(e) => e.preventDefault()}
                data-testid="fullpage-image"
              />
            </div>
          </div>
        ) : allPages.length > 0 ? (
          /* Flipbook Mode */
          <div style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 0.2s' }}>
            <HTMLFlipBook
              ref={bookRef}
              width={dimensions.width}
              height={dimensions.height}
              size="fixed"
              minWidth={280}
              maxWidth={900}
              minHeight={400}
              maxHeight={1200}
              showCover={false}
              maxShadowOpacity={0.3}
              mobileScrollSupport={true}
              onFlip={onFlip}
              className="book-flipbook"
              style={{}}
              flippingTime={600}
              usePortrait={true}
              startZIndex={0}
              autoSize={false}
              drawShadow={true}
              clickEventForward={true}
              swipeDistance={20}
            >
              {allPages.map((page, idx) => (
                <PageContent
                  key={idx}
                  pageNum={startPage + idx}
                  authToken={token}
                />
              ))}
            </HTMLFlipBook>
          </div>
        ) : (
          <p className="text-[#D4AF37]/40 font-body">No pages available yet. Content coming soon.</p>
        )}
      </div>

      {/* Preview Purchase Prompt */}
      {isPreview && (
        <div className="px-4 py-3 bg-gradient-to-r from-[#3D2314] via-[#5A3520] to-[#3D2314] border-t border-[#D4AF37]/20 flex-shrink-0">
          <div className="flex items-center justify-between max-w-lg mx-auto">
            <p className="text-[#D4AF37] text-xs font-body">
              Free preview — Purchase to read all 50 pages
            </p>
            <button
              onClick={() => navigate('/book')}
              className="px-4 py-1.5 text-[10px] font-body font-bold text-[#3D2314] rounded-full tracking-wider uppercase"
              style={{ background: 'linear-gradient(145deg, #D4AF37, #F3D060)' }}
              data-testid="purchase-prompt-btn"
            >
              Purchase Now
            </button>
          </div>
        </div>
      )}

      {/* Bottom Controls */}
      <div className="flex items-center justify-center gap-6 px-4 py-2 bg-[#1a1008]/90 border-t border-[#D4AF37]/10 flex-shrink-0">
        <button
          onClick={() => {
            if (isFullPage) {
              setCurrentPage(p => Math.max(0, p - 1));
              saveProgress((partInfo?.start_page || 1) + Math.max(0, currentPage - 1));
            } else {
              bookRef.current?.pageFlip()?.flipPrev();
            }
          }}
          className="p-3 rounded-full text-[#D4AF37]/60 hover:text-[#D4AF37] hover:bg-[#D4AF37]/10 transition-all"
          data-testid="prev-page"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        {/* Progress bar */}
        <div className="flex-1 max-w-xs">
          <input
            type="range"
            min={0}
            max={Math.max(0, allPages.length - 1)}
            value={currentPage}
            onChange={(e) => {
              const pg = parseInt(e.target.value);
              if (isFullPage) {
                setCurrentPage(pg);
                saveProgress((partInfo?.start_page || 1) + pg);
              } else {
                bookRef.current?.pageFlip()?.turnToPage(pg);
              }
            }}
            className="w-full h-1 appearance-none bg-[#D4AF37]/20 rounded-full cursor-pointer"
            style={{
              background: `linear-gradient(to right, #D4AF37 ${(currentPage / Math.max(1, allPages.length - 1)) * 100}%, rgba(212,175,55,0.2) 0%)`
            }}
            data-testid="page-slider"
          />
        </div>

        <button
          onClick={() => {
            if (isFullPage) {
              setCurrentPage(p => Math.min(allPages.length - 1, p + 1));
              saveProgress((partInfo?.start_page || 1) + Math.min(allPages.length - 1, currentPage + 1));
            } else {
              bookRef.current?.pageFlip()?.flipNext();
            }
          }}
          className="p-3 rounded-full text-[#D4AF37]/60 hover:text-[#D4AF37] hover:bg-[#D4AF37]/10 transition-all"
          data-testid="next-page"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Anti-screenshot overlay */}
      <div
        className="fixed inset-0 pointer-events-none z-[9998]"
        style={{
          background: 'transparent',
          mixBlendMode: 'difference'
        }}
      />

      {/* Tea/Coffee Break Modal */}
      {showBreak && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div
            className="max-w-sm mx-4 rounded-2xl overflow-hidden shadow-2xl"
            style={{ background: 'linear-gradient(135deg, #FFF9F0, #FFF5E8)' }}
            data-testid="coffee-break-modal"
          >
            {/* Steaming cup animation */}
            <div className="text-center pt-8 pb-4">
              <div className="relative inline-block">
                <span className="text-6xl">&#9749;</span>
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 flex gap-1">
                  <span className="block w-1 h-6 bg-[#B8962E]/30 rounded-full animate-pulse" style={{animationDelay: '0ms'}} />
                  <span className="block w-1 h-8 bg-[#B8962E]/20 rounded-full animate-pulse" style={{animationDelay: '200ms'}} />
                  <span className="block w-1 h-5 bg-[#B8962E]/30 rounded-full animate-pulse" style={{animationDelay: '400ms'}} />
                </div>
              </div>
            </div>

            {/* Message */}
            <div className="px-8 pb-4 text-center">
              <p className="font-heading text-lg text-[#3D2314] mb-4">
                Would you like a small tea or coffee break?
              </p>
              <p className="text-sm text-[#5C4A3A] font-body italic leading-relaxed whitespace-pre-line mb-6">
                {shayaris[Math.floor(Math.random() * shayaris.length)]}
              </p>
            </div>

            {/* Buttons */}
            <div className="flex border-t border-[#E8DFD0]">
              <button
                onClick={() => setShowBreak(false)}
                className="flex-1 py-4 text-sm font-body font-semibold text-white tracking-wider uppercase"
                style={{ background: 'linear-gradient(145deg, #D4AF37, #B8962E)' }}
                data-testid="continue-reading"
              >
                Continue Reading
              </button>
              <button
                onClick={() => {
                  setShowBreak(false);
                  toast.success('Enjoy your break! The book will wait for you.');
                }}
                className="flex-1 py-4 text-sm font-body font-semibold text-[#B8962E] bg-white hover:bg-[#F8F5F0] tracking-wider uppercase border-l border-[#E8DFD0]"
                data-testid="take-a-break"
              >
                Take a Break
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Podcast Player */}
      {listenEnabled && (
        <BookPodcastPlayer visible={showPodcast} onClose={() => setShowPodcast(false)} />
      )}
    </div>
  );
};

export default BookReader;
