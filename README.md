# 🌾 AI-Enhanced Crop Monitoring & Anomaly Detection System

![Django](https://img.shields.io/badge/Django-5.0-green)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-orange)
![Machine Learning](https://img.shields.io/badge/ML-Scikit--learn-yellow)
![REST API](https://img.shields.io/badge/API-REST-red)

> **Real-time agricultural monitoring platform with AI-powered anomaly detection**  
> *DS2 Project - Higher Institute of Management of Tunis - 2025/2026*

## Overview

An intelligent crop monitoring system that simulates sensor data, detects anomalies using machine learning, and provides actionable recommendations through an AI agent. The system helps farmers identify irrigation issues, environmental stress, and abnormal patterns in real-time.


## Key Features

### **Smart Monitoring**
- **Real-time sensor simulation** (soil moisture, temperature, humidity)
- **Diurnal cycle patterns** with realistic agricultural variations
- **Multi-plot support** for scalable farm management

###  **AI-Powered Detection**
- **ML anomaly detection** using Isolation Forest and threshold models
- **Real-time anomaly identification** for irrigation failures, heat stress, sensor malfunctions
- **Confidence scoring** for each detected anomaly

###  **Intelligent Agent**
- **Rule-based AI agent** with domain-specific heuristics
- **Explainable recommendations** using template-based explanations
- **Actionable insights** for farmers and agricultural engineers

###  **Modern Dashboard**
- **Interactive visualization** of sensor data streams
- **Real-time anomaly alerts** with severity indicators
- **Historical data analysis** per plot and time period

##  System Architecture

```mermaid
graph TB
    A[ Frontend Dashboard] --> B[ Django REST API]
    C[ AI Agent Module] --> B
    D[ ML Detection Module] --> B
    E[ PostgreSQL Database] --> B
    F[ Sensor Simulator] --> B
    
    B --> G[📈 Real-time Charts]
    B --> H[🚨 Anomaly Alerts]
    B --> I[💡 Recommendations]
