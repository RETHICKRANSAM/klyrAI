import React from 'react';
import { motion } from 'framer-motion';

const AssistantCharacter = ({ state }) => {
  // Glow color based on state
  const glowColor = state === 'Speaking' ? '#ff3b5c' : 
                    state === 'Listening' ? '#00d4ff' : 
                    state === 'Thinking' ? '#ffffff' : '#00d4ff';

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {/* Dynamic Glow Aura */}
      <motion.div
        animate={{
          scale: [1, 1.1, 1],
          opacity: [0.15, 0.3, 0.15],
        }}
        transition={{
          repeat: Infinity,
          duration: 3,
          ease: "easeInOut"
        }}
        style={{
          position: 'absolute',
          width: '400px',
          height: '400px',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${glowColor}55 0%, transparent 70%)`,
          filter: 'blur(40px)',
          zIndex: 0
        }}
      />

      {/* Main Character Image */}
      <motion.img
        src="/klyra_character.png"
        alt="KLYRA AI"
        animate={{
          y: [0, -15, 0],
        }}
        transition={{
          repeat: Infinity,
          duration: 4,
          ease: "easeInOut"
        }}
        style={{
          maxWidth: '450px',
          height: 'auto',
          position: 'relative',
          zIndex: 2,
          filter: `drop-shadow(0 0 20px ${glowColor}44)`,
          mixBlendMode: 'screen'
        }}
      />

      {/* Floating Particles/Elements (Optional, could add more here) */}
    </div>
  );
};

export default AssistantCharacter;
