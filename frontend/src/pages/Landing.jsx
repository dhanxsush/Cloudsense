import AnimatedBackground from '@/components/landing/AnimatedBackground';
import HeroSection from '@/components/landing/HeroSection';
import FeaturesSection from '@/components/landing/FeaturesSection';
import Footer from '@/components/landing/Footer';

const Landing = () => {
  return (
    <div className="relative">
      <AnimatedBackground />
      <HeroSection />
      <FeaturesSection />
      <Footer />
    </div>
  );
};

export default Landing;
