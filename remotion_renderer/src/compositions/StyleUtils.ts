export const getStyleProfile = (style: string) => {
  const profiles: Record<string, any> = {
    viral_pop: {
      titleSize: 88,
      hookSize: 40,
      captionBg: '#000000aa',
      accentGlow: '0 0 60px rgba(0,229,168,.35)',
      titleTransform: 'uppercase',
      motionIntensity: 1.12,
    },
    kinetic_bold: {
      titleSize: 82,
      hookSize: 36,
      captionBg: '#07111fcc',
      accentGlow: '0 0 40px rgba(59,130,246,.35)',
      titleTransform: 'uppercase',
      motionIntensity: 1.08,
    },
    premium_minimal: {
      titleSize: 68,
      hookSize: 30,
      captionBg: '#0f172ab8',
      accentGlow: '0 0 20px rgba(255,255,255,.12)',
      titleTransform: 'none',
      motionIntensity: 1.03,
    },
    strong_cta: {
      titleSize: 84,
      hookSize: 38,
      captionBg: '#03141dcc',
      accentGlow: '0 0 46px rgba(245,158,11,.35)',
      titleTransform: 'uppercase',
      motionIntensity: 1.09,
    },
    finance_clean: {
      titleSize: 72,
      hookSize: 32,
      captionBg: '#08111fcc',
      accentGlow: '0 0 22px rgba(0,229,168,.18)',
      titleTransform: 'none',
      motionIntensity: 1.04,
    },
  };
  return profiles[style] || profiles.finance_clean;
};
