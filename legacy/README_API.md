# Seed Quality Detection API

FastAPI application that performs seed detection and quality classification using two deep learning models.

## 🚀 Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart
```

Or use the combined requirements:
```bash
pip install -r requirements-api.txt
```

### 2. Ensure Models are Present
Make sure these model files are in the project root:
- `FasterRCNN_ResNet50_Final.pth` (Object Detection)
- `ResNet50_maize_seeds_NEW.pth` (Classification)

### 3. Run the API Server
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## 📡 API Endpoints

### `GET /`
Health check endpoint
```json
{
  "status": "running",
  "message": "Seed Quality Detection API",
  "models_loaded": true,
  "device": "cuda"
}
```

### `POST /api/analyze`
Main endpoint for image analysis

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: Form data with `file` field containing image

**Response:**
```json
{
  "success": true,
  "total_seeds": 45,
  "bounding_boxes": [
    {
      "id": 0,
      "x1": 120,
      "y1": 150,
      "x2": 180,
      "y2": 210,
      "width": 60,
      "height": 60,
      "quality": "Good",
      "detection_confidence": 0.9523,
      "classification_probability": 0.1234,
      "color": "#00FF00"
    }
  ],
  "statistics": {
    "good_seeds": 38,
    "bad_seeds": 7,
    "good_percentage": 84.44,
    "bad_percentage": 15.56
  },
  "image_dimensions": {
    "width": 1920,
    "height": 1080
  },
  "thresholds": {
    "detection_confidence": 0.9,
    "classification_threshold": 0.9
  }
}
```

### `GET /api/config`
Get current configuration
```json
{
  "detection_confidence_threshold": 0.9,
  "classification_threshold": 0.9,
  "nms_threshold": 0.3,
  "image_size": 224,
  "device": "cuda"
}
```

## 🎨 Frontend Integration

### Using HTML5 Canvas (Recommended)
The provided `frontend-example.html` demonstrates drawing bounding boxes using Canvas:

```javascript
// Scale coordinates to displayed image size
const scaleX = displayedWidth / originalWidth;
const scaleY = displayedHeight / originalHeight;

// Draw rectangle
ctx.strokeStyle = box.color;
ctx.lineWidth = 3;
ctx.strokeRect(
  box.x1 * scaleX,
  box.y1 * scaleY,
  box.width * scaleX,
  box.height * scaleY
);
```

### Using CSS/HTML Divs
```javascript
boxes.forEach(box => {
  const div = document.createElement('div');
  div.style.position = 'absolute';
  div.style.left = `${box.x1 * scaleX}px`;
  div.style.top = `${box.y1 * scaleY}px`;
  div.style.width = `${box.width * scaleX}px`;
  div.style.height = `${box.height * scaleY}px`;
  div.style.border = `3px solid ${box.color}`;
  container.appendChild(div);
});
```

### Using SVG
```javascript
const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
boxes.forEach(box => {
  const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
  rect.setAttribute("x", box.x1 * scaleX);
  rect.setAttribute("y", box.y1 * scaleY);
  rect.setAttribute("width", box.width * scaleX);
  rect.setAttribute("height", box.height * scaleY);
  rect.setAttribute("stroke", box.color);
  rect.setAttribute("fill", "none");
  svg.appendChild(rect);
});
```

### React Example
```jsx
function SeedImage({ imageUrl, boxes, dimensions }) {
  const canvasRef = useRef(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
      const scaleX = canvas.width / dimensions.width;
      const scaleY = canvas.height / dimensions.height;
      
      boxes.forEach(box => {
        ctx.strokeStyle = box.color;
        ctx.lineWidth = 3;
        ctx.strokeRect(
          box.x1 * scaleX,
          box.y1 * scaleY,
          box.width * scaleX,
          box.height * scaleY
        );
      });
    };
    
    img.src = imageUrl;
  }, [boxes, dimensions]);
  
  return <canvas ref={canvasRef} />;
}
```

## 🧪 Testing with cURL

```bash
# Test health check
curl http://localhost:8000/

# Analyze an image
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@maize-test/test_image.jpg"

# Get config
curl http://localhost:8000/api/config
```

## 🧪 Testing with Python

```python
import requests

# Analyze image
with open('maize-test/test_image.jpg', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/analyze', files=files)
    data = response.json()
    
    print(f"Total seeds: {data['total_seeds']}")
    print(f"Good: {data['statistics']['good_percentage']}%")
    print(f"Bad: {data['statistics']['bad_percentage']}%")
```

## 📊 Response Data Explanation

### Bounding Box Coordinates
- **x1, y1**: Top-left corner (in original image pixels)
- **x2, y2**: Bottom-right corner (in original image pixels)
- **width, height**: Box dimensions (x2-x1, y2-y1)

### Confidence Scores
- **detection_confidence**: How confident the detector is (0-1)
- **classification_probability**: Raw output from classifier (0-1)
  - Values > 0.9 = "Bad"
  - Values ≤ 0.9 = "Good"

### Colors
- `#00FF00` (Green) = Good seed
- `#FF0000` (Red) = Bad seed

## 🔧 Configuration

Edit these constants in `main.py`:

```python
DETECTION_CONF_THRESHOLD = 0.90  # Min confidence for detection
CLASSIFICATION_THRESHOLD = 0.9   # Threshold for Good/Bad
NMS_THRESHOLD = 0.3              # Non-max suppression
IMAGE_SIZE = 224                 # Input size for models
```

## 📱 CORS Configuration

For production, update the CORS settings:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🚀 Deployment

### Using Docker
Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using systemd
Create `/etc/systemd/system/seed-api.service`:
```ini
[Unit]
Description=Seed Quality Detection API
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/seed-bank
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📝 Notes

- Models load on startup (can take 10-30 seconds)
- GPU recommended for faster inference
- Max image size limited by available memory
- Response time: ~2-5 seconds per image (GPU) or ~10-20 seconds (CPU)
