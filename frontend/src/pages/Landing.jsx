import AnimatedBackground from '@/components/landing/AnimatedBackground';
import HeroSection from '@/components/landing/HeroSection';
import FeaturesSection from '@/components/landing/FeaturesSection';
import TeamSection from '@/components/landing/TeamSection';
import Footer from '@/components/landing/Footer';

const Landing = () => {
  return (
    <div className="relative">
      <AnimatedBackground />
      <HeroSection />
      <FeaturesSection />
      <TeamSection />
      <Footer />
    </div>
  );
};

export default Landing;
