/**
 * Solar Forecast AI - Main Frontend Component
 * =========================================
 * 
 * System Design:
 * -------------
 * This component implements the main user interface for the Solar Forecast AI system,
 * providing an intuitive chat-based interface for weather queries.
 * 
 * Key Features:
 * - Real-time chat interface
 * - Dynamic weather data visualization
 * - Responsive design for all devices
 * - Seamless API integration
 * 
 * User Experience:
 * --------------
 * The interface is designed for maximum usability:
 * - Clear input/output areas
 * - Loading states and error handling
 * - Intuitive chat history
 * - Rich data visualization
 */

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import '../styles/SolarForecast.css';
import {
  Container,
  Form,
  Button,
  Card,
  Spinner,
  Alert
} from 'react-bootstrap';

export default function SolarForecast() {
  const [message, setMessage] = useState("");
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  
  // Get the API URL from environment variables or use default
  const apiUrl = process.env.REACT_APP_API_URL || '/api';

  /**
   * Auto-scroll chat to bottom on new messages
   * Improves user experience by keeping focus on latest content
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversations]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (conversations.length >= 10) {
      setError("Maximum conversation limit reached. Please refresh to start a new conversation.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Add user message to conversation
      const userMessage = {
        type: 'user',
        content: message,
        timestamp: new Date().toLocaleTimeString()
      };
      
      setConversations(prev => [...prev, userMessage]);
      setMessage("");

      const res = await axios.post(`${apiUrl}/chat/`, { 
        message 
      }, {
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 30000
      });

      // Add assistant's response to conversation
      const assistantMessage = {
        type: 'assistant',
        content: res.data,
        timestamp: new Date().toLocaleTimeString()
      };

      setConversations(prev => [...prev, assistantMessage]);
      
    } catch (err) {
      console.error('Error:', err);
      
      const errorMessage = err.response?.data?.details 
        ? <div>
            <strong>{err.response.data.error}</strong>
            <br />
            {err.response.data.details}
          </div>
        : (err.response?.data?.error || 'Failed to get data. Please try again.');

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const renderHourlyForecast = (content) => {
    return (
      <div className="hourly-forecast mb-3">
        <h5>Hourly Forecast</h5>
        <div className="row">
          {content.hourly_forecast.map((hour, idx) => (
            <div key={idx} className="col-md-4 mb-2">
              <div className="card h-100">
                <div className="card-body">
                  <h6 className="card-title">{hour.hour}</h6>
                  <p className="card-text">
                    <strong>Conditions:</strong> {hour.conditions}<br />
                    <strong>Solar Potential:</strong> {hour.solar_potential}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderDailyForecast = (content) => {
    return (
      <div className="daily-forecast mb-3">
        <h5>Daily Forecast</h5>
        {content.daily_forecast.map((day, idx) => (
          <div key={idx} className="card mb-2">
            <div className="card-body">
              <h6 className="card-title">{day.date}</h6>
              <p className="card-text">
                <strong>Conditions:</strong> {day.conditions}<br />
                <strong>Solar Potential:</strong> {day.solar_potential}
              </p>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderMarineConditions = (content) => {
    return (
      <div className="marine-conditions mb-3">
        <h5>Marine Conditions</h5>
        <div className="card">
          <div className="card-body">
            <p className="card-text">
              <strong>Wave Height:</strong> {content.wave_conditions.wave_height}<br />
              <strong>Wave Direction:</strong> {content.wave_conditions.wave_direction}<br />
              <strong>Sea Temperature:</strong> {content.wave_conditions.sea_temperature}
            </p>
          </div>
        </div>
      </div>
    );
  };

  const renderAirQuality = (content) => {
    return (
      <div className="air-quality mb-3">
        <h5>Air Quality</h5>
        <div className="card">
          <div className="card-body">
            <p className="card-text">
              <strong>AQI Level:</strong> {content.air_quality_metrics.aqi_level}<br />
              <strong>Pollutants:</strong> {content.air_quality_metrics.pollutants}<br />
              <strong>Health Implications:</strong> {content.air_quality_metrics.health_implications}
            </p>
          </div>
        </div>
      </div>
    );
  };

  const renderRecommendations = (content) => {
    if (!content.recommendations?.length) return null;

    return (
      <div className="recommendations-section mb-3">
        <h5>Recommendations</h5>
        <div className="row">
          {content.recommendations.map((rec, idx) => (
            <div key={idx} className="col-md-6 mb-2">
              <div className="card h-100">
                <div className="card-body">
                  <h6 className="card-title">{rec.category}</h6>
                  <p className="card-text">{rec.advice}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderWeatherData = (content) => {
    if (!content.query_type) return JSON.stringify(content);

    return (
      <div className="weather-analysis">
        <div className="location-info mb-3">
          <h4>
            {content.location.city}
            <small className="text-muted ml-2">
              ({content.location.coordinates.lat}, {content.location.coordinates.lon})
            </small>
          </h4>
        </div>

        <div className="summary-section mb-3">
          <p className="lead">{content.summary}</p>
        </div>

        {/* Render specific data based on query type */}
        {content.query_type === 'forecast' && content.time_frame === 'hourly' && renderHourlyForecast(content)}
        {content.query_type === 'forecast' && content.time_frame === 'daily' && renderDailyForecast(content)}
        {content.query_type === 'marine' && renderMarineConditions(content)}
        {content.query_type === 'air_quality' && renderAirQuality(content)}

        {renderRecommendations(content)}
      </div>
    );
  };

  const renderMessage = (msg, index) => {
    const isUser = msg.type === 'user';
    
    return (
      <div 
        key={index} 
        className={`message ${isUser ? 'user-message' : 'assistant-message'} mb-4`}
      >
        <div className="message-header">
          <strong>{isUser ? 'You' : 'Assistant'}</strong>
          <small className="text-muted ml-2">{msg.timestamp}</small>
        </div>
        <div className={`message-content mt-2 p-3 rounded ${isUser ? 'bg-primary text-white' : 'bg-light'}`}>
          {isUser ? msg.content : renderWeatherData(msg.content)}
        </div>
      </div>
    );
  };

  return (
    <Container className="mt-5">
      <div className="chat-container">
        <div className="chat-header mb-4">
          <h2>Weather & Solar Forecast Assistant</h2>
          <p className="text-muted">
            Ask about weather conditions, solar forecasts, marine conditions, air quality, and more.
            <small className="d-block">
              {5 - Math.floor(conversations.length/2)} questions remaining
            </small>
          </p>
        </div>

        <div className="messages-container p-3 mb-4" style={{ 
          height: '60vh', 
          overflowY: 'auto',
          border: '1px solid #dee2e6',
          borderRadius: '0.25rem'
        }}>
          {conversations.map((msg, index) => renderMessage(msg, index))}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <Alert variant="danger" className="mt-3">
            {error}
          </Alert>
        )}

        <Form onSubmit={handleSubmit} className="mt-3">
          <Form.Group className="d-flex">
            <Form.Control
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask about weather conditions..."
              disabled={loading || conversations.length >= 10}
            />
            <Button 
              type="submit" 
              variant="primary" 
              className="ms-2"
              disabled={loading || !message.trim() || conversations.length >= 10}
            >
              {loading ? (
                <Spinner animation="border" size="sm" />
              ) : (
                <span>Send</span>
              )}
            </Button>
          </Form.Group>
        </Form>

        {conversations.length >= 10 && (
          <div className="alert alert-info mt-3">
            <button 
              className="btn btn-outline-primary"
              onClick={() => {
                setConversations([]);
                setError(null);
              }}
            >
              Start New Conversation
            </button>
          </div>
        )}
      </div>
    </Container>
  );
}
