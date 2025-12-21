# Prompt for Antigravity: Seed Quality Detection Frontend

## Project Overview
I'm building an **AI-powered Seed Quality Detection System** for agricultural quality control. The system uses two deep learning models:
1. **Faster R-CNN** - Detects individual seeds in uploaded images
2. **ResNet50** - Classifies each detected seed as "Good" or "Bad"

## What We've Built
- ✅ **FastAPI backend** running at `http://localhost:8000`
- ✅ **Two trained models** for detection and classification
- ✅ **REST API endpoint** that accepts images and returns analysis
- ✅ **Basic HTML frontend** (index.html) as a proof of concept

## What I Need
Create a **modern, professional frontend application** for this seed detection system. The frontend should be production-ready, visually appealing, and provide an excellent user experience for agricultural professionals and seed bank operators.

---

## API Integration Details

### Endpoint
```
POST http://localhost:8000/api/analyze
Content-Type: multipart/form-data
Body: file (image file - JPG, PNG, JPEG)
```

### API Response Structure
```json
{
  "success": true,
  "total_seeds": 95,
  "bounding_boxes": [
    {
      "id": 0,
      "x1": 811,
      "y1": 587,
      "x2": 877,
      "y2": 672,
      "width": 66,
      "height": 85,
      "quality": "Good",
      "detection_confidence": 0.9999,
      "classification_probability": 0.8902,
      "color": "#00FF00"
    }
    // ... more seeds
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

### Important: Bounding Box Coordinates
- Coordinates (`x1`, `y1`, `x2`, `y2`) are in **original image pixels**
- Must be **scaled** to match displayed image size
- Formula: `displayedX = originalX * (displayedWidth / originalWidth)`

---

## Core Features Required

### 1. Image Upload
- Drag & drop support
- File picker button
- Image preview before analysis
- File type validation (JPG, PNG, JPEG only)
- File size indicator

### 2. Visual Analysis Display
- **Original image with bounding boxes** overlaid
- Draw boxes using HTML5 Canvas (recommended) or SVG
- Green boxes (#00FF00) for Good seeds
- Red boxes (#FF0000) for Bad seeds
- Optional: Seed numbering on each box
- Zoom/pan controls for large images
- Toggle to show/hide bounding boxes

### 3. Statistics Dashboard
Display these metrics prominently:
- Total seeds detected
- Good seeds count and percentage
- Bad seeds count and percentage
- Progress bars or pie charts
- Quality score (overall percentage of good seeds)
- Detection confidence threshold used

### 4. Results List/Table
- Scrollable list of all detected seeds
- Each row shows: Seed ID, Quality (Good/Bad), Confidence scores
- Click on a seed to highlight its bounding box
- Filter by quality (show only Good/Bad)
- Sort by confidence scores

### 5. Loading States
- Show loading spinner during API call (~2-5 seconds)
- Progress indicator
- Disable upload during processing

### 6. Error Handling
- Display user-friendly error messages
- Handle network errors
- Handle invalid image formats
- Handle API failures gracefully

### 7. Export/Download Features (Nice to have)
- Download analyzed image with bounding boxes
- Export results as JSON
- Export statistics as CSV
- Generate PDF report

---

## Design Requirements

### Style & Theme
- Modern, clean, professional design
- Agricultural/nature color palette (greens, earth tones)
- Responsive design (desktop, tablet, mobile)
- High contrast for readability
- Professional typography

### Layout Suggestions
1. **Header**: App title, logo area, info button
2. **Upload Section**: Prominent upload area with drag-drop
3. **Main Content** (after analysis):
   - Left: Image with bounding boxes (60-70% width)
   - Right: Statistics cards and seed list (30-40% width)
4. **Footer**: Additional options, export buttons

### UI/UX Considerations
- Clear visual hierarchy
- Intuitive navigation
- Smooth animations/transitions
- Loading states for all async operations
- Success/error notifications (toast/snackbar)
- Accessible (ARIA labels, keyboard navigation)

---

## Technical Requirements

### Canvas Drawing (Critical!)
```javascript
// Scale coordinates to displayed image size
const scaleX = displayedImageWidth / apiResponse.image_dimensions.width;
const scaleY = displayedImageHeight / apiResponse.image_dimensions.height;

// Draw each bounding box
apiResponse.bounding_boxes.forEach(box => {
  ctx.strokeStyle = box.color; // '#00FF00' or '#FF0000'
  ctx.lineWidth = 3;
  ctx.strokeRect(
    box.x1 * scaleX,
    box.y1 * scaleY,
    box.width * scaleX,
    box.height * scaleY
  );
  
  // Optional: Add label
  ctx.fillStyle = box.color;
  ctx.font = 'bold 14px Arial';
  ctx.fillText(`${box.quality} #${box.id}`, box.x1 * scaleX + 5, box.y1 * scaleY - 8);
});
```

### Framework Preference
- Use **React** (preferred) or **Vue.js**
- **Modern JavaScript** (ES6+)
- **CSS Framework**: Tailwind CSS, Material-UI, or Ant Design
- **Charts**: Chart.js or Recharts for statistics visualization
- **Icons**: Lucide, Heroicons, or FontAwesome

### Additional Libraries to Consider
- `react-dropzone` - For file uploads
- `react-chartjs-2` - For charts
- `framer-motion` - For animations
- `react-hot-toast` - For notifications

---

## Reference Implementation
I have a basic working HTML file at `frontend/index.html` with:
- Basic upload functionality
- Canvas-based bounding box drawing
- Statistics display
- Seed list

**Use this as inspiration but create something more modern, polished, and feature-rich.**

---

## Success Criteria
The frontend should:
1. ✅ Successfully upload images and call the API
2. ✅ Correctly draw bounding boxes scaled to the displayed image
3. ✅ Display all statistics clearly and attractively
4. ✅ Handle errors gracefully
5. ✅ Be responsive and work on mobile devices
6. ✅ Have smooth, professional animations
7. ✅ Be intuitive for non-technical users (farmers, lab technicians)

---

## Example User Flow
1. User opens the app → sees attractive landing page with upload area
2. User drags/selects an image → sees preview
3. User clicks "Analyze" → loading spinner appears
4. Results appear → image with boxes, statistics cards animate in
5. User explores → clicks on seeds in list to highlight them
6. User exports → downloads results as PDF/CSV

---

## Notes
- The API typically takes 2-5 seconds on GPU, 10-20 seconds on CPU
- Images can be large (1-4 MB typical)
- Users may analyze multiple images in a session
- Consider adding a "New Analysis" button to reset and analyze another image
- Consider history/session storage to review previous analyses

---

**Please generate a complete, production-ready React application with all the features described above. Focus on creating an excellent user experience for seed quality assessment professionals.**
