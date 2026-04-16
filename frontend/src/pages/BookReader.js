import { useState, useEffect, useRef, useCallback, forwardRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import HTMLFlipBook from 'react-pageflip';
import { ChevronLeft, ChevronRight, Bookmark, BookmarkCheck, ArrowLeft, Volume2, VolumeX, X, Home } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

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
  const bookRef = useRef(null);
  const audioRef = useRef(null);
  const { user, token } = useAuth();
  const navigate = useNavigate();

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

  // Responsive dimensions
  useEffect(() => {
    const updateDimensions = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      if (w < 640) {
        setDimensions({ width: w - 40, height: Math.min(h - 160, (w - 40) * 1.4) });
      } else if (w < 1024) {
        setDimensions({ width: Math.min(450, w - 80), height: Math.min(630, h - 160) });
      } else {
        setDimensions({ width: 480, height: 670 });
      }
    };
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Fetch pages
  useEffect(() => {
    if (!token) { setError('Please login to read'); setLoading(false); return; }
    fetchPages();
    fetchBookmarks();
  }, [partNumber, token]);

  const fetchPages = async () => {
    try {
      const res = await fetch(`${API}/api/book/pages/${partNumber}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 403) { setError('Please purchase this part first'); setLoading(false); return; }
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setPartInfo(data.part);
      setPages(data.pages || []);
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

  // Music - use a royalty-free ambient sound
  const toggleMusic = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio('https://cdn.pixabay.com/audio/2024/11/04/audio_4956b4ece1.mp3');
      audioRef.current.loop = true;
      audioRef.current.volume = 0.15;
    }
    if (musicOn) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(() => {});
    }
    setMusicOn(!musicOn);
  };

  // Cleanup music on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    };
  }, []);

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
      <div className="flex items-center justify-between px-4 py-3 bg-[#1a1008]/90 border-b border-[#D4AF37]/10">
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

        <div className="flex items-center gap-3">
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
        </div>
      </div>

      {/* Book Area */}
      <div className="flex-1 flex items-center justify-center px-4 py-6">
        {allPages.length > 0 ? (
          <HTMLFlipBook
            ref={bookRef}
            width={dimensions.width}
            height={dimensions.height}
            size="fixed"
            minWidth={280}
            maxWidth={600}
            minHeight={400}
            maxHeight={800}
            showCover={false}
            maxShadowOpacity={0.3}
            mobileScrollSupport={true}
            onFlip={onFlip}
            className="book-flipbook"
            style={{}}
            flippingTime={800}
            usePortrait={window.innerWidth < 768}
            startZIndex={0}
            autoSize={false}
            drawShadow={true}
            clickEventForward={true}
            swipeDistance={30}
          >
            {allPages.map((page, idx) => (
              <PageContent
                key={idx}
                pageNum={startPage + idx}
                authToken={token}
              />
            ))}
          </HTMLFlipBook>
        ) : (
          <p className="text-[#D4AF37]/40 font-body">No pages available yet. Content coming soon.</p>
        )}
      </div>

      {/* Bottom Controls */}
      <div className="flex items-center justify-center gap-6 px-4 py-4 bg-[#1a1008]/90 border-t border-[#D4AF37]/10">
        <button
          onClick={() => bookRef.current?.pageFlip()?.flipPrev()}
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
              bookRef.current?.pageFlip()?.turnToPage(pg);
            }}
            className="w-full h-1 appearance-none bg-[#D4AF37]/20 rounded-full cursor-pointer"
            style={{
              background: `linear-gradient(to right, #D4AF37 ${(currentPage / Math.max(1, allPages.length - 1)) * 100}%, rgba(212,175,55,0.2) 0%)`
            }}
            data-testid="page-slider"
          />
        </div>

        <button
          onClick={() => bookRef.current?.pageFlip()?.flipNext()}
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
    </div>
  );
};

export default BookReader;
