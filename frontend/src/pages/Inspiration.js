import { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Sparkles, Play } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Inspiration = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const response = await axios.get(`${API}/videos?category=inspiration`);
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
    return url;
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-cream to-white">
      <div className="container mx-auto px-4 lg:px-8 py-12 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <Sparkles className="h-16 w-16 mx-auto text-primary mb-4" />
          <h1 className="font-playfair text-4xl lg:text-6xl font-bold text-foreground mb-4 tracking-tight" data-testid="inspiration-title">
            Words of Inspiration
          </h1>
          <p className="text-lg text-foreground/70 font-manrope max-w-2xl mx-auto">
            Insights, talks, and wisdom from Jayanti Kathale - Founder of Purnabramha
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="max-w-4xl mx-auto mb-16"
        >
          <div className="bg-white rounded-2xl p-8 border border-orange-900/10 shadow-lg">
            <div className="flex flex-col md:flex-row gap-6 items-center">
              <div className="md:w-1/3">
                <div className="h-48 w-48 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 mx-auto flex items-center justify-center">
                  <span className="text-6xl font-playfair font-bold text-primary">JK</span>
                </div>
              </div>
              <div className="md:w-2/3 text-center md:text-left">
                <h2 className="font-playfair text-3xl font-bold text-foreground mb-2">
                  Jayanti Kathale
                </h2>
                <p className="text-primary font-manrope font-semibold mb-4">
                  Founder & Visionary Leader
                </p>
                <p className="text-foreground/70 font-manrope leading-relaxed">
                  A renowned speaker, entrepreneur, and women's leader who has given over 100+ speeches at TEDx, Swayam, engineering colleges, and women-led organizations. Through Purnabramha, she's creating the largest Maharashtrian restaurant chain while empowering women in business.
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {loading ? (
          <div className="text-center py-20">
            <p className="text-foreground/70 font-manrope">Loading videos...</p>
          </div>
        ) : videos.length === 0 ? (
          <div className="text-center py-20">
            <Play className="h-16 w-16 mx-auto text-foreground/20 mb-4" />
            <p className="text-foreground/70 font-manrope mb-2">Inspiration videos coming soon</p>
            <p className="text-sm text-foreground/50 font-manrope">
              We're curating the best talks and insights from Jayanti Kathale
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {videos.map((video, index) => (
              <motion.div
                key={video.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-white rounded-xl overflow-hidden border border-orange-900/10 hover:shadow-lg transition-shadow"
                data-testid={`inspiration-video-${index}`}
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
                  <h3 className="font-playfair text-xl font-semibold text-foreground mb-2">
                    {video.title}
                  </h3>
                  {video.description && (
                    <p className="text-foreground/70 font-manrope">
                      {video.description}
                    </p>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Inspiration;