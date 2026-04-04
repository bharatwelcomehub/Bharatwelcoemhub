import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Video as VideoIcon } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Videos = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const response = await axios.get(`${API}/videos`);
      setVideos(response.data);
    } catch (error) {
      console.error('Failed to fetch videos:', error);
    } finally {
      setLoading(false);
    }
  };

  const getVideoEmbedUrl = (url) => {
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      const videoId = url.includes('youtu.be')
        ? url.split('/').pop()
        : new URL(url).searchParams.get('v');
      return `https://www.youtube.com/embed/${videoId}`;
    }
    if (url.includes('instagram.com')) {
      return url.replace('/reel/', '/embed/');
    }
    return url;
  };

  const reels = videos.filter(v => v.category === 'reels');
  const promotional = videos.filter(v => v.category === 'promotional');

  const VideoCard = ({ video, index }) => (
    <motion.div
      key={video.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="bg-white border border-[#E8DFD0] overflow-hidden hover:border-[#B8962E]/30 transition-all hover:shadow-lg"
      data-testid={`video-${index}`}
    >
      <div className="aspect-video relative">
        <iframe
          src={getVideoEmbedUrl(video.video_url)}
          title={video.title}
          className="w-full h-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
      <div className="p-6">
        <h3 className="font-heading text-lg font-medium text-[#2D1810] mb-2">{video.title}</h3>
        {video.description && (
          <p className="text-sm text-[#5C4A3A] font-body">{video.description}</p>
        )}
      </div>
    </motion.div>
  );

  return (
    <div className="min-h-screen bg-[#FDFBF7]">
      <div className="container mx-auto px-6 lg:px-12 py-16 lg:py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <p className="text-xs tracking-[0.3em] uppercase text-[#B8962E] font-body font-bold mb-4">Media</p>
          <h1 className="font-heading text-5xl md:text-6xl lg:text-7xl font-medium text-[#2D1810] mb-4 tracking-tight" data-testid="videos-title">
            Purnabramha <span className="text-gold-shimmer">Stories</span>
          </h1>
          <p className="text-lg text-[#5C4A3A] font-body max-w-2xl mx-auto">
            Watch our journey, recipes, and celebration of Maharashtrian culture
          </p>
        </motion.div>

        {loading ? (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#B8962E] mx-auto mb-4"></div>
            <p className="text-[#7A6F65] font-body">Loading videos...</p>
          </div>
        ) : videos.length === 0 ? (
          <div className="text-center py-20">
            <VideoIcon className="h-16 w-16 mx-auto text-[#7A6F65]/30 mb-4" />
            <p className="text-[#5C4A3A] font-body">No videos available yet</p>
            <p className="text-sm text-[#7A6F65] font-body mt-2">Check back soon for exciting content!</p>
          </div>
        ) : (
          <Tabs defaultValue="all" className="w-full">
            <TabsList className="grid w-full max-w-md mx-auto grid-cols-3 mb-12 bg-white border border-[#E8DFD0] rounded-none h-12">
              <TabsTrigger value="all" className="rounded-none data-[state=active]:bg-[#B8962E] data-[state=active]:text-white text-[#5C4A3A] font-body text-xs tracking-widest uppercase">All</TabsTrigger>
              <TabsTrigger value="reels" className="rounded-none data-[state=active]:bg-[#B8962E] data-[state=active]:text-white text-[#5C4A3A] font-body text-xs tracking-widest uppercase">Reels</TabsTrigger>
              <TabsTrigger value="promotional" className="rounded-none data-[state=active]:bg-[#B8962E] data-[state=active]:text-white text-[#5C4A3A] font-body text-xs tracking-widest uppercase">Promotional</TabsTrigger>
            </TabsList>

            <TabsContent value="all">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {videos.map((video, index) => <VideoCard key={video.id} video={video} index={index} />)}
              </div>
            </TabsContent>

            <TabsContent value="reels">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {reels.map((video, index) => <VideoCard key={video.id} video={video} index={index} />)}
              </div>
            </TabsContent>

            <TabsContent value="promotional">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {promotional.map((video, index) => <VideoCard key={video.id} video={video} index={index} />)}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
};

export default Videos;
