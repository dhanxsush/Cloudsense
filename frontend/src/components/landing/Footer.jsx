import { Satellite, Github, Mail, ExternalLink } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="bg-[#0B0F1A] border-t border-slate-800 text-slate-300 mt-20">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
          {/* Project Info */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Satellite className="h-6 w-6 text-cyan-400" />
              <span className="text-xl font-bold text-white">CloudSense</span>
            </div>
            <p className="text-sm text-slate-400 mb-2">
              Advanced TCC detection using INSAT-3D IRBT data and deep learning architectures.
            </p>
            <p className="text-xs text-slate-500">v1.0.0 • Team CloudSense AI</p>
          </div>

          {/* Tech Stack */}
          <div>
            <h3 className="text-white font-semibold mb-4">Technology Stack</h3>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>• PyTorch & U-Net Architecture</li>
              <li>• cuML DBSCAN Clustering</li>
              <li>• React 18 + Vite</li>
              <li>• FastAPI Backend</li>
              <li>• SQLite Database</li>
            </ul>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-white font-semibold mb-4">Resources</h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a href="/login" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                  Dashboard
                </a>
              </li>
              <li>
                <a href="#" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                  Documentation
                </a>
              </li>
              <li>
                <a href="#" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                  API Reference
                </a>
              </li>
              <li>
                <a href="#" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                  Support
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-slate-700 pt-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <p className="text-sm text-slate-400">
              © {new Date().getFullYear()} CloudSense • Bharatiya Antariksh Hackathon
            </p>
            <div className="flex gap-4 mt-4 md:mt-0">
              <a
                href="https://github.com/dhanush2002/CloudSense"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-cyan-400 transition-colors"
              >
                <Github className="w-5 h-5" />
              </a>
              <button className="text-slate-400 hover:text-cyan-400 transition-colors">
                <Mail className="w-5 h-5" />
              </button>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-4">
            Dr. N.G.P Institute of Technology
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
