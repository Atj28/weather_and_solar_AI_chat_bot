import React from 'react';
import SolarForecast from './components/SolarForecast';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  return (
    <div>
      <nav className="navbar navbar-dark bg-primary">
        <div className="container">
          <span className="navbar-brand mb-0 h1">Solar Forecast AI</span>
        </div>
      </nav>
      
      <div className="container">
        <SolarForecast />
      </div>
    </div>
  );
}

export default App; 