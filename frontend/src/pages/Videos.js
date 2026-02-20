import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Play, Video as VideoIcon } from 'lucide-react';
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

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <VideoIcon className="h-16 w-16 mx-auto text-primary mb-4" />
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="videos-title">
            Purnabramha Stories
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
            Watch our journey, recipes, and celebration of Maharashtrian culture
          </p>
        </motion.div>

        {loading ? (
          <div className="text-center py-20">
            <p className="text-foreground/70 font-manrope">Loading videos...</p>
          </div>
        ) : videos.length === 0 ? (
          <div className="text-center py-20">
            <VideoIcon className="h-16 w-16 mx-auto text-foreground/20 mb-4" />
            <p className="text-foreground/70 font-manrope">No videos available yet</p>
            <p className="text-sm text-foreground/50 font-manrope mt-2">
              Check back soon for exciting content!
            </p>
          </div>
        ) : (
          <Tabs defaultValue="all" className="w-full">
            <TabsList className="grid w-full max-w-md mx-auto grid-cols-3 mb-8">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="reels">Reels</TabsTrigger>
              <TabsTrigger value="promotional">Promotional</TabsTrigger>
            </TabsList>

            <TabsContent value="all">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {videos.map((video, index) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="bg-white rounded-xl overflow-hidden border border-orange-900/10 hover:shadow-lg transition-shadow"
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
                    <div className="p-4">
                      <h3 className="font-playfair text-lg font-semibold text-foreground mb-2">
                        {video.title}
                      </h3>
                      {video.description && (
                        <p className="text-sm text-foreground/70 font-manrope">
                          {video.description}
                        </p>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="reels">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {reels.map((video, index) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="bg-white rounded-xl overflow-hidden border border-orange-900/10 hover:shadow-lg transition-shadow"
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
                    <div className="p-4">
                      <h3 className="font-playfair text-lg font-semibold text-foreground mb-2">
                        {video.title}
                      </h3>
                    </div>
                  </motion.div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="promotional">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {promotional.map((video, index) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="bg-white rounded-xl overflow-hidden border border-orange-900/10 hover:shadow-lg transition-shadow"
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
                    <div className="p-4">
                      <h3 className="font-playfair text-lg font-semibold text-foreground mb-2">
                        {video.title}
                      </h3>
                    </div>
                  </motion.div>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
};

export default Videos;