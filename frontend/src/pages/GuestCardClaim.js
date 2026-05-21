import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Loader2, AlertTriangle } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { Badge } from '@/components/ui/badge';
import { Mandala } from '@/components/FestiveDecor';
import SEOHead from '@/components/SEOHead';

const API = process.env.REACT_APP_BACKEND_URL;

export default function GuestCardClaim() {
  const { coupon } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    axios.get(`${API}/api/guest-feedback/coupon/${coupon}`)
      .then(r => setData(r.data))
      .catch(() => setErr('Coupon not found or expired'));
  }, [coupon]);

  if (err) return (
    <div className="min-h-screen flex items-center justify-center p-6 text-center">
      <div>
        <AlertTriangle className="h-12 w-12 mx-auto text-[#B8962E] mb-3" />
        <p className="font-heading text-xl text-[#3D2314]">{err}</p>
      </div>
    </div>
  );
  if (!data) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-[#B8962E]" /></div>;

  const couponUrl = window.location.href;
  return (
    <div className="min-h-screen bg-[#FDFBF7] py-10 px-4">
      <SEOHead page="guest-card-claim" title={`Coupon ${data.coupon_code} | Purnabramha`} description="Purnabramha guest discount coupon." />
      <div className="max-w-md mx-auto">
        <div
          className="relative bg-gradient-to-br from-[#3D2314] via-[#5B3923] to-[#3D2314] text-[#F5DEB3] p-6 sm:p-8 shadow-2xl overflow-hidden"
          style={data.background_image_url ? {
            backgroundImage: `linear-gradient(135deg, rgba(61,35,20,0.78), rgba(91,57,35,0.82), rgba(61,35,20,0.82)), url("${data.background_image_url}")`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
          } : undefined}
          data-testid="claim-card"
        >
          <Mandala className="absolute -top-6 -right-6 w-32 h-32 pointer-events-none" opacity={0.12} />
          <Mandala className="absolute -bottom-6 -left-6 w-32 h-32 pointer-events-none" opacity={0.12} />
          <Badge className="bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/40 rounded-none px-2.5 py-0.5 text-[10px] uppercase tracking-widest font-body">
            Purnabramha Guest Card
          </Badge>
          <h2 className="font-heading text-2xl sm:text-3xl text-[#F5DEB3] mt-3 leading-tight">{data.guest_name ? `${data.guest_name.split(' ')[0]}'s ` : ''}Discount Card</h2>
          <p className="font-heading italic text-[#D4AF37] text-sm mt-1">show this at the counter</p>
          {data.discount_pct > 0 && (
            <div className="mt-5 pt-5 border-t border-[#D4AF37]/30">
              <p className="text-[10px] uppercase tracking-widest text-[#D4AF37]/70 font-body">Reward</p>
              <p className="font-heading text-5xl sm:text-6xl text-[#D4AF37] font-light mt-1">{data.discount_pct}% <span className="text-2xl">OFF</span></p>
              <p className="font-heading italic text-[#F5DEB3]/80 text-sm mt-1">{data.offer_title}</p>
            </div>
          )}
          <div className="mt-5 grid grid-cols-2 gap-3 text-xs font-body">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Coupon</p>
              <p className="font-mono text-base text-[#F5DEB3] tracking-widest">{data.coupon_code}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Center</p>
              <p className="text-[#F5DEB3]">{data.center_name}</p>
            </div>
            {data.expiry_date && <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Valid Till</p>
              <p className="text-[#F5DEB3]">{data.expiry_date}</p>
            </div>}
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#D4AF37]/70">Status</p>
              <p className={data.status === 'used' ? 'text-red-300' : data.status === 'expired' ? 'text-orange-300' : 'text-green-300'}>
                {data.status === 'used' ? 'Already used' : data.status === 'expired' ? 'Expired' : 'Valid — show at counter'}
              </p>
            </div>
          </div>
          <div className="mt-5 pt-5 border-t border-[#D4AF37]/30 flex items-end justify-between gap-3">
            <p className="text-[11px] italic text-[#F5DEB3]/70 leading-snug flex-1">{data.terms}</p>
            <div className="bg-white p-2 rounded-md flex-shrink-0">
              <QRCodeCanvas value={`${data.coupon_code}|${couponUrl}`} size={84} bgColor="#FFFFFF" fgColor="#3D2314" level="M" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
