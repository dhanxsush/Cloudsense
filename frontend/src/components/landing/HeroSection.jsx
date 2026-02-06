import { ArrowRight, Satellite, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

const HeroSection = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Status badge */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2">
        <div className="flex items-center gap-2 px-4 py-2 bg-gray-800/80 backdrop-blur-sm rounded-full border border-gray-700">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
          <span className="text-sm font-medium text-gray-300">SYSTEM OPERATIONAL</span>
        </div>
      </div>

      {/* Main heading */}
      <div className="text-center mb-8 relative z-10 mt-16">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Satellite className="h-12 w-12 text-cyan-400" />
          <h1 className="text-5xl md:text-7xl font-bold text-white tracking-tight">
            Cloud<span className="text-cyan-400">Sense</span>
          </h1>
        </div>

        {/* Tagline */}
        <p className="text-2xl md:text-3xl font-medium text-gray-300 mb-6">
          AI-powered tropical cloud intelligence
        </p>

        {/* Description */}
        <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-8">
          Detect, track, and analyze tropical cloud clusters using real-time satellite data.
          Half-hourly infrared brightness temperature analysis for atmospheric research.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/signup">
            <Button size="lg" className="bg-cyan-500 hover:bg-cyan-600 text-black font-semibold">
              Get Started <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
          <Link to="/dashboard">
            <Button size="lg" variant="outline" className="border-gray-600 text-white hover:bg-gray-800">
              Dashboard
            </Button>
          </Link>
          <Link to="/chat">
            <Button size="lg" variant="secondary" className="bg-gray-700 text-white hover:bg-gray-600">
              Chat with AI
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto px-4 relative z-10 mb-16">
        {[
          { value: '48', label: 'Updates/Day', suffix: '' },
          { value: '0.5', label: 'Hour Intervals', suffix: 'hr' },
          { value: '99.9', label: 'Uptime', suffix: '%' },
          { value: '500+', label: 'Satellites', suffix: '' },
        ].map((stat, index) => (
          <div key={index} className="text-center">
            <div className="text-3xl md:text-4xl font-bold text-white mb-1">
              {stat.value}
              <span className="text-cyan-400 text-lg">{stat.suffix}</span>
            </div>
            <div className="text-sm text-gray-500">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
        <div className="w-6 h-10 border-2 border-gray-600 rounded-full flex justify-center pt-2">
          <div className="w-1 h-2 bg-gray-400 rounded-full"></div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;

