# 🌱 Seed Quality Detection System

AI-powered seed quality assessment using Faster R-CNN for detection and ResNet50 for classification.

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)

## 🎯 Overview

This system performs automated seed quality inspection using a two-stage deep learning pipeline:
1. **Object Detection**: Faster R-CNN detects individual seeds in images
2. **Quality Classification**: ResNet50 classifies each seed as "Good" or "Bad"

Perfect for agricultural quality control, seed banks, and research applications.

## ✨ Features

- 🔍 **Automatic seed detection** with high accuracy (90%+ confidence threshold)
- 🎯 **Binary quality classification** (Good/Bad seeds)
- 📊 **Statistical analysis** with detailed metrics
- 🌐 **REST API** for easy integration
- 🖼️ **Interactive web interface** with visual bounding boxes
- ⚡ **GPU acceleration** support
- 📦 **Batch processing** capability

## 📁 Project Structure

```
seed-bank/
├── main.py                  # FastAPI server
├── requirements.txt         # Python dependencies
├── README.md               # This file
│
├── models/                 # Model weights (not in git)
│   ├── FasterRCNN_ResNet50_Final.pth
│   └── ResNet50_maize_seeds_NEW.pth
│
├── notebooks/              # Jupyter notebooks
│   └── graduation-project-demo-me.ipynb
│
├── frontend/               # Web interface
│   └── index.html
│
├── tests/                  # Test scripts
│   └── test_api.py
│
└── data/                   # Data directory
    └── test-images/        # Sample images
        └── maize-test/
```

## 🚀 Installation

### Prerequisites
- Python 3.10+
- CUDA-capable GPU (optional, but recommended)
- 4GB+ RAM

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd seed-bank
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download model weights**
Place the model files in the `models/` directory:
- `FasterRCNN_ResNet50_Final.pth` (166MB)
- `ResNet50_maize_seeds_NEW.pth` (94MB)

## 💻 Usage

### Start the API Server

```bash
python main.py
```

The server will start at `http://localhost:8000`

### Use the Web Interface

1. Open `frontend/index.html` in a browser
2. Upload a seed image
3. View results with bounding boxes and statistics

### Test the API

```bash
python tests/test_api.py
```

### Example API Call

```python
import requests

with open('image.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/analyze', files=files)
    data = response.json()
    
print(f"Total seeds: {data['total_seeds']}")
print(f"Good: {data['statistics']['good_percentage']}%")
```

## 📡 API Documentation

### `POST /api/analyze`

Analyze an image for seed detection and quality classification.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (image file)

**Response:**
```json
{
  "success": true,
  "total_seeds": 95,
  "bounding_boxes": [
    {
      "id": 0,
      "x1": 811, "y1": 587, "x2": 877, "y2": 672,
      "width": 66, "height": 85,
      "quality": "Good",
      "detection_confidence": 0.9999,
      "classification_probability": 0.8902,
      "color": "#00FF00"
    }
  ],
  "statistics": {
    "good_seeds": 52,
    "bad_seeds": 43,
    "good_percentage": 54.74,
    "bad_percentage": 45.26
  },
  "image_dimensions": {
    "width": 959,
    "height": 930
  },
  "thresholds": {
    "detection_confidence": 0.9,
    "classification_threshold": 0.9
  }
}
```

### `GET /`
Health check endpoint

### `GET /api/config`
Get current configuration parameters

Full API documentation: [README_API.md](README_API.md)

## 🔧 Development

### Configuration

Edit thresholds in `main.py`:

```python
DETECTION_CONF_THRESHOLD = 0.90  # Detection confidence
CLASSIFICATION_THRESHOLD = 0.9   # Good/Bad threshold
NMS_THRESHOLD = 0.3              # Non-max suppression
```

### Training

See `notebooks/graduation-project-demo-me.ipynb` for the complete training pipeline.

### Testing

```bash
# Test API
python tests/test_api.py

# Test with custom image
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@path/to/image.jpg"
```

## 📊 Performance

- **Detection Speed**: ~2-5 seconds per image (GPU) / ~10-20 seconds (CPU)
- **Accuracy**: 90%+ detection confidence threshold
- **Supported Formats**: JPG, PNG, JPEG
- **Max Image Size**: Limited by available memory

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is part of a graduation project.

## 🙏 Acknowledgments

- PyTorch and torchvision teams
- FastAPI framework
- OpenCV community

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Made with ❤️ for agricultural quality control**
