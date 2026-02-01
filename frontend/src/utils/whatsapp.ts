import { Linking } from 'react-native';
import { Center } from '../data/centersData';

/**
 * Opens WhatsApp with a pre-filled message
 * @param phoneNumber - Phone number in international format (without +)
 * @param message - Message to send
 */
export const openWhatsApp = async (phoneNumber: string, message: string) => {
  try {
    const encodedMessage = encodeURIComponent(message);
    const url = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
    
    const supported = await Linking.canOpenURL(url);
    
    if (supported) {
      await Linking.openURL(url);
    } else {
      // Fallback - copy to clipboard or show error
      console.error('WhatsApp is not installed');
      throw new Error('WhatsApp is not available on this device');
    }
  } catch (error) {
    console.error('Error opening WhatsApp:', error);
    throw error;
  }
};

/**
 * Generate table booking WhatsApp message
 */
export const generateTableBookingMessage = (data: {
  name: string;
  phone: string;
  date: string;
  time: string;
  guests: number;
  serviceType: string;
  center: Center;
}) => {
  return `🕉️ Namaskar from Purnabramha!

Table Booking Request:

📍 Location: ${data.center.displayName}
👤 Name: ${data.name}
📱 Phone: ${data.phone}
📅 Date: ${data.date}
⏰ Time: ${data.time}
👥 Number of Guests: ${data.guests}
🍽️ Service Type: ${data.serviceType}

Please confirm the booking. Thank you!`;
};

/**
 * Generate tiffin booking WhatsApp message
 */
export const generateTiffinBookingMessage = (data: {
  name: string;
  phone: string;
  selectedDays: string[];
  totalAmount: number;
  center: Center;
  weeks: any[];
}) => {
  const daysList = data.selectedDays.join(', ');
  
  return `🕉️ Namaskar from Purnabramha!

Tiffin / Lunch Box Booking:

📍 Location: ${data.center.displayName}
👤 Name: ${data.name}
📱 Phone: ${data.phone}
📅 Selected Days: ${daysList}
💰 Total Amount: ${data.center.currencySymbol}${data.totalAmount.toFixed(2)}

Please confirm the tiffin booking. Thank you!`;
};

/**
 * Generate heavy brunch booking WhatsApp message
 */
export const generateHeavyBrunchMessage = (data: {
  name: string;
  phone: string;
  items: any[];
  totalAmount: number;
  center: Center;
}) => {
  let itemsList = '';
  data.items.forEach(item => {
    itemsList += `\n• ${item.name} x${item.quantity} - ${data.center.currencySymbol}${item.total.toFixed(2)}`;
  });
  
  return `🕉️ Namaskar from Purnabramha!

Heavy Brunch Booking:

📍 Location: ${data.center.displayName}
👤 Name: ${data.name}
📱 Phone: ${data.phone}

Items:${itemsList}

💰 Total Amount: ${data.center.currencySymbol}${data.totalAmount.toFixed(2)}

Please confirm the order. Thank you!`;
};

/**
 * Share menu item
 */
export const shareMenuItem = (item: any, center: Center) => {
  const price = center.country === 'Australia' ? item.priceAUD : item.priceINR;
  const message = `Check out this delicious dish from Purnabramha ${center.displayName}!

🍽️ ${item.name}
${item.description}
💰 ${center.currencySymbol}${price}

Visit us or order now!`;
  
  return message;
};