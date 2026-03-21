import { useState } from 'react';
import { MapPin, X, Loader2 } from 'lucide-react';
import { useSEO } from '@/contexts/SEOContext';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';

// "Near Me" Location Banner - positioned below header, not blocking it
const LocationBanner = () => {
  const { 
    showLocationBanner, 
    locationPermission, 
    nearestCenter, 
    currentCity,
    locationLoading,
    requestLocationPermission, 
    dismissLocationBanner 
  } = useSEO();

  // Don't show if permission already granted and we have a center
  if (locationPermission === 'granted' && nearestCenter) {
    return null;
  }

  // Don't show if user dismissed or denied
  if (!showLocationBanner || locationPermission === 'denied') {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -100, opacity: 0 }}
        className="bg-gradient-to-r from-[#5c1e1e] to-[#8b2c2c] text-white py-3 px-4 relative"
        style={{ pointerEvents: 'auto', zIndex: 40 }}
      >
        <div className="container mx-auto flex items-center justify-center gap-3 flex-wrap text-center">
          <MapPin className="h-5 w-5 flex-shrink-0" />
          <span className="text-sm md:text-base">
            Looking for <strong>Maharashtrian food near you</strong>?
          </span>
          <Button
            onClick={requestLocationPermission}
            disabled={locationLoading}
            size="sm"
            className="bg-white text-[#5c1e1e] hover:bg-amber-100 text-xs md:text-sm"
          >
            {locationLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                Detecting...
              </>
            ) : (
              <>
                <MapPin className="h-4 w-4 mr-1" />
                Find Nearest Purnabramha
              </>
            )}
          </Button>
          <button
            onClick={dismissLocationBanner}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2"
            aria-label="Dismiss"
            style={{ pointerEvents: 'auto' }}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

// Nearest Center Display (shown after location is detected)
const NearestCenterBanner = () => {
  const { nearestCenter, locationPermission } = useSEO();
  const [dismissed, setDismissed] = useState(false);

  if (!nearestCenter || locationPermission !== 'granted' || dismissed) {
    return null;
  }

  return (
    <motion.div
      initial={{ y: -50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="bg-gradient-to-r from-green-600 to-green-700 text-white py-2 px-4 relative"
      style={{ pointerEvents: 'auto', zIndex: 40 }}
    >
      <div className="container mx-auto flex items-center justify-center gap-2 text-center">
        <MapPin className="h-4 w-4 flex-shrink-0" />
        <span className="text-sm">
          Your nearest Purnabramha: <strong>{nearestCenter.displayName}</strong>
          {nearestCenter.distance && (
            <span className="text-green-200 ml-1">({nearestCenter.distance} km away)</span>
          )}
        </span>
        <a 
          href={`tel:${nearestCenter.phone}`}
          className="ml-2 bg-white/20 hover:bg-white/30 px-3 py-1 rounded text-xs"
          style={{ pointerEvents: 'auto' }}
        >
          Call Now
        </a>
        <button
          onClick={() => setDismissed(true)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-white/70 hover:text-white p-2"
          aria-label="Dismiss"
          style={{ pointerEvents: 'auto' }}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
};

export { LocationBanner, NearestCenterBanner };
