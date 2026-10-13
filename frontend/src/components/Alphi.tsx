import React from 'react';

type AlphiMood = 'welcome' | 'excited' | 'cleaning' | 'thinking' | 'happy' | 'error' | 'idle' | 'detective';

interface AlphiProps {
  mood?: AlphiMood;
  size?: 'sm' | 'md' | 'lg';
  message?: string;
  className?: string;
}

const sizeMap = { sm: 48, md: 80, lg: 120 };

export default function Alphi({ mood = 'idle', size = 'md', message, className = '' }: AlphiProps) {
  const s = sizeMap[size];
  
  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <div className={mood === 'idle' ? 'animate-float' : mood === 'excited' ? 'animate-bounce-gentle' : ''}>
        <svg width={s} height={s} viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Body */}
          <ellipse cx="60" cy="72" rx="35" ry="30" fill="#0d9488" />
          
          {/* Head */}
          <circle cx="60" cy="45" r="28" fill="#14b8a6" />
          
          {/* Left ear */}
          <g className={mood === 'excited' ? 'animate-ear-wiggle' : ''} style={{ transformOrigin: '40px 22px' }}>
            <path d="M38 25 L28 8 L48 18 Z" fill="#14b8a6" />
            <path d="M39 23 L32 12 L46 19 Z" fill="#5eead4" />
          </g>
          
          {/* Right ear */}
          <g className={mood === 'excited' ? 'animate-ear-wiggle' : ''} style={{ transformOrigin: '80px 22px', animationDelay: '0.15s' }}>
            <path d="M82 25 L92 8 L72 18 Z" fill="#14b8a6" />
            <path d="M81 23 L88 12 L74 19 Z" fill="#5eead4" />
          </g>
          
          {/* Eyes */}
          {mood === 'happy' || mood === 'excited' ? (
            <>
              {/* Happy squint eyes */}
              <path d="M47 42 Q50 38 53 42" stroke="#042f2e" strokeWidth="2.5" strokeLinecap="round" fill="none" />
              <path d="M67 42 Q70 38 73 42" stroke="#042f2e" strokeWidth="2.5" strokeLinecap="round" fill="none" />
            </>
          ) : mood === 'error' ? (
            <>
              {/* Worried eyes */}
              <circle cx="50" cy="40" r="4" fill="#042f2e" />
              <circle cx="70" cy="40" r="4" fill="#042f2e" />
              <circle cx="51.5" cy="39" r="1.5" fill="white" />
              <circle cx="71.5" cy="39" r="1.5" fill="white" />
            </>
          ) : mood === 'detective' ? (
            <>
              {/* Detective eyes - one with monocle */}
              <circle cx="50" cy="40" r="3.5" fill="#042f2e" />
              <circle cx="51" cy="39" r="1.2" fill="white" />
              <circle cx="70" cy="40" r="5" stroke="#f59e0b" strokeWidth="1.5" fill="none" />
              <circle cx="70" cy="40" r="3" fill="#042f2e" />
              <circle cx="71" cy="39" r="1.2" fill="white" />
              <line x1="75" y1="42" x2="82" y2="52" stroke="#f59e0b" strokeWidth="1.5" />
            </>
          ) : (
            <>
              {/* Normal eyes */}
              <circle cx="50" cy="40" r="4" fill="#042f2e" />
              <circle cx="70" cy="40" r="4" fill="#042f2e" />
              <circle cx="51.5" cy="38.5" r="1.8" fill="white" />
              <circle cx="71.5" cy="38.5" r="1.8" fill="white" />
            </>
          )}
          
          {/* Nose */}
          <ellipse cx="60" cy="48" rx="2.5" ry="1.8" fill="#0f766e" />
          
          {/* Mouth */}
          {mood === 'happy' || mood === 'excited' ? (
            <path d="M54 52 Q60 58 66 52" stroke="#042f2e" strokeWidth="1.8" strokeLinecap="round" fill="none" />
          ) : mood === 'error' ? (
            <path d="M54 55 Q60 51 66 55" stroke="#042f2e" strokeWidth="1.8" strokeLinecap="round" fill="none" />
          ) : (
            <path d="M55 53 Q60 55 65 53" stroke="#042f2e" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          )}
          
          {/* Whiskers */}
          <line x1="35" y1="46" x2="44" y2="48" stroke="#042f2e" strokeWidth="1" opacity="0.5" />
          <line x1="35" y1="50" x2="44" y2="50" stroke="#042f2e" strokeWidth="1" opacity="0.5" />
          <line x1="76" y1="48" x2="85" y2="46" stroke="#042f2e" strokeWidth="1" opacity="0.5" />
          <line x1="76" y1="50" x2="85" y2="50" stroke="#042f2e" strokeWidth="1" opacity="0.5" />
          
          {/* Paws */}
          <ellipse cx="42" cy="92" rx="8" ry="5" fill="#0f766e" />
          <ellipse cx="78" cy="92" rx="8" ry="5" fill="#0f766e" />
          
          {/* Tail */}
          <g className={mood === 'cleaning' ? 'animate-tail-wag' : mood === 'excited' ? 'animate-tail-wag' : ''} style={{ transformOrigin: '90px 80px' }}>
            <path d="M90 75 Q105 65 100 50 Q98 55 95 60 Q92 68 88 73" stroke="#0d9488" strokeWidth="5" strokeLinecap="round" fill="none" />
          </g>
          
          {/* Lightning bolt on chest (EV theme) */}
          <path d="M57 62 L62 55 L60 62 L65 62 L59 72 L61 65 L57 65 Z" fill="#fbbf24" />
        </svg>
      </div>
      {message && (
        <p className="text-sm text-gray-600 font-medium text-center max-w-xs animate-fade-in">
          {message}
        </p>
      )}
    </div>
  );
}
