import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Modal, Animated,
} from 'react-native';
import Voice, { SpeechResultsEvent, SpeechErrorEvent } from '@react-native-voice/voice';
import { colors } from '../theme';

const PAGES: Record<string, string[]> = {
  Home:        ['home', 'main', 'dashboard', 'start'],
  Bookings:    ['book', 'booking', 'space', 'amenity', 'gym', 'pool', 'room', 'hall', 'reserve'],
  Visitors:    ['visitor', 'gate', 'invite', 'guest', 'delivery', 'move', 'entry'],
  Marketplace: ['market', 'buy', 'sell', 'post', 'listing', 'shop'],
  Profile:     ['profile', 'account', 'details', 'vehicles', 'pets', 'family'],
  News:        ['news', 'notice', 'announcement', 'updates'],
  Locks:       ['lock', 'unlock', 'door', 'smart lock'],
};

interface Props {
  visible: boolean;
  onNavigate: (screen: string, prefill?: Record<string, string>) => void;
  onClose: () => void;
}

type Status = 'listening' | 'thinking' | 'done' | 'error';

export default function VoiceAssistant({ visible, onNavigate, onClose }: Props) {
  const [status, setStatus] = useState<Status>('listening');
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!visible) return;
    setStatus('listening');
    setTranscript('');
    setResponse('');
  }, [visible]);

  // Pulse animation when listening
  useEffect(() => {
    if (status === 'listening') {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.2, duration: 600, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulseAnim.stopAnimation();
      pulseAnim.setValue(1);
    }
  }, [status]);

  useEffect(() => {
    Voice.onSpeechResults = (e: SpeechResultsEvent) => {
      const text = e.value?.[0] || '';
      setTranscript(text);
      Voice.stop();
      processWithClaude(text);
    };
    Voice.onSpeechError = (e: SpeechErrorEvent) => {
      setStatus('error');
      setResponse('Could not hear you. Try again.');
      setTimeout(onClose, 2500);
    };
    return () => { Voice.destroy().then(Voice.removeAllListeners); };
  }, []);

  const startListening = async () => {
    try {
      await Voice.start('en-IN');
    } catch (e) {
      setStatus('error');
      setResponse('Microphone not available.');
      setTimeout(onClose, 2000);
    }
  };

  useEffect(() => {
    if (visible) startListening();
    else Voice.stop().catch(() => {});
  }, [visible]);

  const processWithClaude = async (text: string) => {
    setStatus('thinking');
    const today = new Date().toISOString().split('T')[0];
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 200,
          system: `You are a voice assistant for PA Lite, a residential community app. Extract navigation intent AND form prefill data.

Pages: Home, Bookings (space/amenity booking), Visitors (gate pass, invites, move requests), Marketplace (buy/sell posts), Profile (account, vehicles, pets, family), News (announcements), Locks (smart lock).

Respond ONLY with JSON:
{"action":"navigate","page":"Bookings","message":"Booking the gym!","prefill":{"spaceSearch":"gym","date":"2026-03-11","startTime":"06:00","endTime":"07:00"}}

Prefill fields:
- Bookings: spaceSearch, date (YYYY-MM-DD), startTime (HH:MM), endTime (HH:MM)
- Visitors: visitorName, visitorPhone, visitorType (guest/cab/delivery/daily_help), purpose
- Marketplace: postType (buy/sell), title, description, price

Today is ${today}. Resolve relative dates. If unclear: {"action":"unclear","message":"Try: book gym tomorrow at 6pm"}
Keep message under 10 words. Only include prefill fields mentioned.`,
          messages: [{ role: 'user', content: text }],
        }),
      });
      const data = await res.json();
      const raw = data.content?.[0]?.text || '{}';
      const parsed = JSON.parse(raw.replace(/```json|```/g, '').trim());
      setResponse(parsed.message || 'Done!');
      setStatus('done');
      if (parsed.action === 'navigate' && parsed.page) {
        setTimeout(() => { onNavigate(parsed.page, parsed.prefill || {}); onClose(); }, 1200);
      } else {
        setTimeout(onClose, 3000);
      }
    } catch {
      // Keyword fallback
      const lower = text.toLowerCase();
      let matched: string | null = null;
      for (const [page, kw] of Object.entries(PAGES)) {
        if (kw.some(k => lower.includes(k))) { matched = page; break; }
      }
      if (matched) {
        setResponse(`Taking you to ${matched}!`);
        setStatus('done');
        setTimeout(() => { onNavigate(matched!); onClose(); }, 1000);
      } else {
        setStatus('error');
        setResponse("Didn't understand. Try again.");
        setTimeout(onClose, 2500);
      }
    }
  };

  const orbColor = status === 'thinking'
    ? ['#6c5ce7', '#a29bfe']
    : status === 'done' ? ['#00b894', '#00b894']
    : status === 'error' ? ['#e17055', '#e17055']
    : ['#ffffff', '#ffffff'];

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Animated.View style={[styles.orb, { transform: [{ scale: pulseAnim }], backgroundColor: orbColor[0] }]}>
          <Text style={styles.orbIcon}>
            {status === 'listening' ? '🎤' : status === 'thinking' ? '⏳' : status === 'done' ? '✓' : '✕'}
          </Text>
        </Animated.View>

        <Text style={styles.statusText}>
          {status === 'listening' ? 'Listening...'
            : status === 'thinking' ? 'Got it, one sec...'
            : status === 'done' ? 'On it!'
            : 'Oops!'}
        </Text>

        {!!transcript && (
          <Text style={styles.transcript}>"{transcript}"</Text>
        )}
        {!!response && (
          <View style={styles.responseBubble}>
            <Text style={styles.responseText}>{response}</Text>
          </View>
        )}

        <TouchableOpacity style={styles.cancelBtn} onPress={onClose}>
          <Text style={styles.cancelText}>Cancel</Text>
        </TouchableOpacity>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.88)',
    alignItems: 'center', justifyContent: 'center', gap: 24,
  },
  orb: {
    width: 96, height: 96, borderRadius: 48,
    alignItems: 'center', justifyContent: 'center',
    shadowColor: '#fff', shadowOpacity: 0.3, shadowRadius: 20, elevation: 10,
  },
  orbIcon: { fontSize: 36 },
  statusText: { fontSize: 18, fontWeight: '600', color: colors.white },
  transcript: {
    fontSize: 14, color: 'rgba(255,255,255,0.6)',
    textAlign: 'center', maxWidth: 280, fontStyle: 'italic',
  },
  responseBubble: {
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.12)',
    borderRadius: 16, paddingHorizontal: 20, paddingVertical: 12, maxWidth: 300,
  },
  responseText: { fontSize: 15, color: 'rgba(255,255,255,0.9)', textAlign: 'center' },
  cancelBtn: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 28, paddingVertical: 10, borderRadius: 30,
  },
  cancelText: { color: colors.white, fontSize: 14 },
});
