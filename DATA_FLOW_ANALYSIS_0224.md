# STT Engine Web UI - Complete Data Flow Analysis

## 📋 Executive Summary

This document provides a comprehensive analysis of the data architecture, storage patterns, and API workflows for the STT Engine Web UI system. The system uses a **hybrid storage approach** combining filesystem-based audio storage with SQLite database for metadata tracking.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Web UI Layer                           │
│  (FastAPI + Jinja2 Templates + JavaScript)                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  Services Layer                             │
│  • FileService    • AnalysisService    • STTService         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────┬──────────────────────────────────────┐
│  Filesystem Storage  │     SQLite Database                  │
│  (Audio Files)       │     (Metadata & Results)             │
└──────────────────────┴──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              STT API Backend (Port 8003)                    │
│  • Real Mode: Whisper Model Processing                      │
│  • Dummy Mode: Simulated Responses (when model unavailable) │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 File Storage Structure

### Directory Layout
```
web_ui/data/
├── uploads/                    # User audio files
│   ├── {emp_id}/              # Employee-specific directory
│   │   ├── {folder_path}/     # Date or custom folder name
│   │   │   ├── file1.wav
│   │   │   ├── file2.wav
│   │   │   └── file3.mp3
│   │   ├── 2026-02-24/        # Auto-generated date folders
│   │   └── custom_folder/     # User-defined folders
│   └── 90002/
│       └── ...
└── results/                   # Future: Analysis output files
```

### Path Resolution Rules

**Location**: `web_ui/config.py` (Lines 1-29)

```python
# Priority order:
# 1. DATA_DIR environment variable
# 2. /app/data (Docker mounted volume)
# 3. web_ui/data (Local development)

DATA_DIR = Path(os.getenv("DATA_DIR")) or Path("/app/data") or BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
```

**Key Paths**:
- **Docker Environment**: `/app/data/uploads/{emp_id}/{folder_path}/{filename}`
- **Local Development**: `web_ui/data/uploads/{emp_id}/{folder_path}/{filename}`

---

## 💾 Database Schema

### 5 Core Tables

#### 1. **employees** - User Authentication & Info
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10) UNIQUE NOT NULL,     -- Employee number
    name VARCHAR(100) NOT NULL,
    dept VARCHAR(100),
    created_at DATETIME,
    last_login DATETIME
);
```

#### 2. **file_uploads** - Audio File Metadata
```sql
CREATE TABLE file_uploads (
    id INTEGER PRIMARY KEY,
    emp_id VARCHAR(10) FOREIGN KEY,
    folder_path VARCHAR(500) NOT NULL,      -- "2026-02-24" or "custom_folder"
    filename VARCHAR(500) NOT NULL,         -- "sample.wav"
    file_size_mb FLOAT,
    uploaded_at DATETIME
);
```

**Purpose**: Tracks which files exist, their location, and metadata. Does NOT store audio content.

#### 3. **analysis_jobs** - Analysis Work Tracking
```sql
CREATE TABLE analysis_jobs (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE NOT NULL,     -- "job_abc123def456"
    emp_id VARCHAR(10) FOREIGN KEY,
    folder_path VARCHAR(500),                -- Which folder to analyze
    file_ids JSON,                           -- ["file1.wav", "file2.wav"]
    files_hash VARCHAR(64),                  -- SHA256 hash for change detection
    status VARCHAR(20),                      -- pending|processing|completed|failed
    options JSON,                            -- Analysis options
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME
);
```

**Purpose**: Tracks analysis workflow state. Each job represents one folder analysis request.

#### 4. **analysis_results** - STT & Detection Results
```sql
CREATE TABLE analysis_results (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) FOREIGN KEY,
    file_id VARCHAR(500),                    -- Filename
    stt_text TEXT,                           -- Transcribed text
    stt_metadata JSON,                       -- {duration, language, confidence, backend}
    classification_code VARCHAR(20),
    classification_category VARCHAR(100),
    classification_confidence FLOAT,
    improper_detection_results JSON,
    incomplete_detection_results JSON,
    created_at DATETIME
);
```

**Purpose**: Stores one result per audio file. Contains STT output and analysis results.

#### 5. **analysis_progress** - Real-time Progress Tracking
```sql
CREATE TABLE analysis_progress (
    id INTEGER PRIMARY KEY,
    job_id VARCHAR(50) FOREIGN KEY,
    current_file VARCHAR(500),
    progress_percent INTEGER,
    status VARCHAR(20),
    message TEXT,
    updated_at DATETIME
);
```

---

## 🔄 Data Flow Workflows

### Workflow 1: File Upload

```
┌─────────────┐
│   User      │
│ (Browser)   │
└──────┬──────┘
       │ POST /api/files/upload
       │ FormData: {file, folder_name}
       ↓
┌──────────────────────────────────────┐
│  FileService.upload_file()           │
│  web_ui/app/services/file_service.py │
└──────┬───────────────────────────────┘
       │
       ├─→ 1. Validate user (Employee exists?)
       ├─→ 2. Validate filename (sanitize)
       ├─→ 3. Create folder path
       │      • If folder_name provided: use it
       │      • Else: auto-generate "YYYY-MM-DD"
       ├─→ 4. Save file to disk
       │      Path: data/uploads/{emp_id}/{folder_path}/{filename}
       └─→ 5. Insert metadata to DB
              INSERT INTO file_uploads (emp_id, folder_path, filename, ...)
```

**Code Location**: `web_ui/app/services/file_service.py` (Lines 25-100)

**Key Functions**:
```python
# Filename validation
filename = file_utils.validate_filename(file.filename)

# Folder path creation
folder_path = file_utils.create_folder_path(emp_id, folder_name)
# Returns: "2026-02-24" or custom name

# File storage
full_file_path = user_dir / folder_path / filename
with open(full_file_path, 'wb') as f:
    f.write(file_content)

# DB record
file_record = FileUpload(
    emp_id=emp_id,
    folder_path=folder_path,
    filename=filename,
    file_size_mb=file_size_mb,
    uploaded_at=datetime.utcnow()
)
db.add(file_record)
db.commit()
```

---

### Workflow 2: Analysis Request & Processing

```
┌─────────────┐
│   User      │
│ (Browser)   │
└──────┬──────┘
       │ POST /api/analysis/start
       │ Body: {folder_path, options}
       ↓
┌────────────────────────────────────────────┐
│  AnalysisService.start_analysis()          │
│  web_ui/app/services/analysis_service.py   │
└──────┬─────────────────────────────────────┘
       │
       ├─→ 1. Query files in folder
       │      SELECT * FROM file_uploads 
       │      WHERE emp_id=? AND folder_path=?
       │
       ├─→ 2. Calculate files hash (SHA256)
       │      sorted_files = sorted([f.filename for f in files])
       │      hash = sha256('|'.join(sorted_files))
       │
       ├─→ 3. Check if already analyzed
       │      If hash matches last job: return "unchanged"
       │
       ├─→ 4. Create new analysis job
       │      INSERT INTO analysis_jobs (job_id, emp_id, folder_path, 
       │                                  file_ids, files_hash, status='pending')
       │
       └─→ 5. Launch background task
              background_tasks.add_task(AnalysisService.process_analysis_sync, ...)
```

**Code Location**: `web_ui/app/services/analysis_service.py` (Lines 56-148)

---

### Workflow 3: Background Analysis Processing

```
┌───────────────────────────────────────────┐
│  AnalysisService.process_analysis_sync()  │
│  (Runs in FastAPI BackgroundTasks thread) │
└──────┬────────────────────────────────────┘
       │
       ├─→ 1. Update job status to "processing"
       │
       ├─→ FOR EACH file in file_list:
       │   │
       │   ├─→ Track current file in memory
       │   │   _current_processing[job_id] = filename
       │   │
       │   ├─→ Build file path
       │   │   file_path = data/uploads/{emp_id}/{folder_path}/{filename}
       │   │
       │   ├─→ Call STT API
       │   │   stt_result = await stt_service.transcribe_local_file(file_path)
       │   │
       │   └─→ Save result to DB
       │       INSERT INTO analysis_results (job_id, file_id, stt_text, ...)
       │
       └─→ 2. Update job status to "completed"
```

**Code Location**: `web_ui/app/services/analysis_service.py` (Lines 527-654)

**Dummy Data Implementation** (Current):
```python
# Line 557-564
test_confidence_values = [0.2, 0.45, 0.8]  # danger, warning, safe

for idx, filename in enumerate(files):
    confidence = test_confidence_values[idx % len(test_confidence_values)]
    
    result = AnalysisResult(
        job_id=job_id,
        file_id=filename,
        stt_text=stt_result.get('text', ''),
        stt_metadata={
            "confidence": confidence  # Cycling for testing
        }
    )
```

---

### Workflow 4: STT Service (Real vs Dummy)

```
┌──────────────────────────────────────┐
│  STTService.transcribe_local_file()  │
│  web_ui/app/services/stt_service.py  │
└──────┬───────────────────────────────┘
       │
       ├─→ 1. Path conversion (Docker compatibility)
       │   If "/app/data/..." → "/app/web_ui/data/..."
       │   Elif "/app/web_ui/data/..." → keep as-is
       │
       ├─→ 2. Send HTTP POST to STT API (port 8003)
       │   URL: http://localhost:8003/transcribe
       │   FormData: {file_path, language, options...}
       │
       ├─→ 3. Handle response
       │   ├─ SUCCESS (200) → Return STT result
       │   └─ ERROR (503, timeout, connection error)
       │      └─→ Call _get_dummy_response()
       │
       └─→ 4. Dummy Response Generation
           ├─ Random sleep: 0-30 seconds
           ├─ Select random Korean dialogue (4 versions)
           └─ Return mock result structure
```

**Code Location**: `web_ui/app/services/stt_service.py` (Lines 84-530)

**Real API Response Structure**:
```json
{
  "success": true,
  "text": "상담원: 안녕하세요...",
  "duration_sec": 60.5,
  "backend": "faster-whisper",
  "language": "ko",
  "processing_steps": {
    "stt": true,
    "privacy_removal": false,
    "classification": false,
    "ai_agent": false
  }
}
```

**Dummy Response Structure**:
```json
{
  "success": true,
  "text": "상담원: 안녕하세요...",  // Random dialogue from 4 versions
  "duration_sec": 60,
  "backend": "dummy",
  "language": "ko",
  "processing_steps": {
    "stt": true,
    "privacy_removal": false,
    "classification": false,
    "ai_agent": false
  },
  "_note": "⚠️ STT API 미응답으로 Dummy 응답이 반환되었습니다."
}
```

**Dummy Dialogues** (Lines 437-474):
1. **Basic Sales Dialogue** (~410 chars) - Moderate, professional
2. **Aggressive Sales Dialogue** (~531 chars) - Pressure, guarantees, urgency
3. **Improper Sales Dialogue** (~531 chars) - Rushed, avoiding details
4. **Short Version** (~83 chars) - Fallback

---

## 🔍 Result Fetching Mechanisms

### Real-Time Progress Polling

```
┌─────────────┐
│   Browser   │
│  JavaScript │
└──────┬──────┘
       │ Polling: GET /api/analysis/progress/{job_id}
       │ Interval: Every 2 seconds
       ↓
┌──────────────────────────────────────┐
│  AnalysisService.get_progress()      │
└──────┬───────────────────────────────┘
       │
       ├─→ 1. Query job from DB
       │   SELECT * FROM analysis_jobs WHERE job_id=?
       │
       ├─→ 2. Get completed results
       │   SELECT * FROM analysis_results WHERE job_id=?
       │
       ├─→ 3. Calculate progress
       │   progress = (completed_files / total_files) * 100
       │
       ├─→ 4. Get current processing file (from memory)
       │   current_file = _current_processing[job_id]
       │
       └─→ 5. Build response for ALL files
           For each file in job.file_ids:
             If result exists:
               status = "completed"
               risk_level = calculate_risk(confidence)
             Elif file == current_file:
               status = "processing"
             Else:
               status = "pending"
```

**Code Location**: `web_ui/app/services/analysis_service.py` (Lines 152-268)

**Response Structure**:
```json
{
  "job_id": "job_abc123",
  "folder_path": "2026-02-24",
  "status": "processing",
  "progress": 66,
  "current_file": "file2.wav",
  "total_files": 3,
  "processed_files": 2,
  "results": [
    {
      "filename": "file1.wav",
      "stt_text": "상담원: 안녕하세요...",
      "status": "completed",
      "confidence": 0.2,
      "risk_level": "danger"
    },
    {
      "filename": "file2.wav",
      "status": "processing",
      "confidence": 0,
      "risk_level": "safe"
    },
    {
      "filename": "file3.wav",
      "status": "pending",
      "confidence": 0,
      "risk_level": "safe"
    }
  ]
}
```

---

## 🎯 Risk Level Detection Logic

**Location**: `web_ui/app/services/analysis_service.py` (Lines 215-225)

```python
# Get confidence from STT metadata
confidence = result.stt_metadata.get("confidence", 0.5)

# Determine risk level (lower confidence = higher risk)
if confidence < 0.3:
    risk_level = "danger"      # 부당권유 발견
elif confidence < 0.6:
    risk_level = "warning"     # 의심
else:
    risk_level = "safe"        # 정상
```

**Current Test Mode** (Lines 557-564):
```python
# Cycling confidence values for deterministic testing
test_confidence_values = [0.2, 0.45, 0.8]  # danger, warning, safe

for idx, filename in enumerate(files):
    confidence = test_confidence_values[idx % len(test_confidence_values)]
    # File 1 → 0.2 (danger)
    # File 2 → 0.45 (warning)
    # File 3 → 0.8 (safe)
    # File 4 → 0.2 (danger) ...cycles
```

**Frontend Badge Styling** (`templates/analysis.html`):
```css
.status-danger  { background: #c62828; color: white; }
.status-warning { background: #f57c00; color: white; }
.status-safe    { background: #388e3c; color: white; }
```

---

## 📊 Data Consistency Mechanisms

### 1. File Hash Change Detection
```python
# Calculate hash of file list
current_hash = AnalysisService.calculate_files_hash(file_list)

# Compare with last completed job
if last_job and last_job.files_hash == current_hash:
    return "unchanged"  # Skip re-analysis
```

### 2. In-Memory Tracking
```python
# Track currently processing file
_current_processing: Dict[str, str] = {}  # {job_id: filename}

# Set when file processing starts
_current_processing[job_id] = filename

# Clear when job completes
del _current_processing[job_id]
```

### 3. Status Synchronization
```python
# Progress endpoint shows real-time status for each file
for filename in all_files:
    if result_exists(filename):
        status = "completed"
    elif filename == current_processing_file:
        status = "processing"
    else:
        status = "pending"
```

---

## 🔧 Key Implementation Notes

### Path Conversion (Docker Compatibility)

**Problem**: Different paths between Web UI and STT API
- Web UI stores: `/app/web_ui/data/uploads/...`
- STT API expects: `/app/web_ui/data/...` (mounted volume)

**Solution**: `stt_service.py` (Lines 96-107)
```python
if file_path.startswith("/app/data/"):
    api_file_path = file_path.replace("/app/data/", "/app/web_ui/data/")
elif file_path.startswith("/app/web_ui/data/"):
    api_file_path = file_path  # No conversion needed
else:
    api_file_path = file_path  # Local development
```

### Audio File Serving

**Location**: `web_ui/app/routes/files.py` (Lines 142-193)

```python
@router.get("/audio/{emp_id}/{folder_path}/{filename}")
async def serve_audio_file(emp_id, folder_path, filename, request):
    # Security: Check session matches emp_id
    if session_emp_id != emp_id:
        raise HTTPException(403, "Access denied")
    
    # Build file path
    file_path = f"data/uploads/{emp_id}/{folder_path}/{filename}"
    
    # Serve with proper MIME type
    return FileResponse(
        path=file_path,
        media_type='audio/wav',  # or audio/mpeg for mp3
        filename=filename
    )
```

### CSV Export (Frontend)

**Location**: `templates/analysis.html` (Lines 840-869)

```javascript
function exportResults() {
    // UTF-8 BOM for Korean characters
    let csv = '\uFEFF';
    csv += '파일명,텍스트,분석상태\n';
    
    results.forEach(result => {
        csv += `"${result.filename}","${result.stt_text || ''}","${getRiskLevelText(result.risk_level)}"\n`;
    });
    
    // Download as CSV
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `analysis_results_${Date.now()}.csv`;
    link.click();
}
```

---

## 🚀 Improvement Opportunities

### 1. Dummy Mode Should Mirror Real API More Closely

**Current Issue**: Confidence values are deterministically cycled, not realistic

**Recommendation**:
```python
# Add keyword-based confidence generation
def calculate_realistic_confidence(text):
    """Calculate confidence based on dialogue content"""
    risk_keywords = ["보장", "확실", "원금 보장", "절대", "무조건"]
    risk_count = sum(1 for keyword in risk_keywords if keyword in text)
    
    # Base confidence: 0.6-0.9 (safe range)
    # Reduce by 0.1-0.2 per risk keyword
    confidence = 0.85 - (risk_count * 0.15)
    return max(0.1, min(0.95, confidence))
```

### 2. Better File Status Tracking

**Current**: Uses in-memory dictionary (lost on server restart)

**Recommendation**: Add `status` column to `analysis_results` table
```sql
ALTER TABLE analysis_results ADD COLUMN status VARCHAR(20);
-- Values: pending | processing | completed | failed
```

### 3. Audio File Cleanup

**Missing**: No mechanism to delete orphaned files

**Recommendation**: Add cleanup task
```python
def cleanup_orphaned_files(emp_id):
    """Remove files from disk that are not in DB"""
    db_files = {f.filename for f in db.query(FileUpload).filter_by(emp_id=emp_id)}
    disk_files = set(list_files(user_dir))
    
    orphaned = disk_files - db_files
    for filename in orphaned:
        file_path.unlink()  # Delete
```

### 4. Progress Persistence

**Current**: Progress only calculated from DB queries

**Recommendation**: Use `analysis_progress` table more effectively
```python
# Update progress in DB during processing
progress_record = AnalysisProgress(
    job_id=job_id,
    current_file=filename,
    progress_percent=int((idx / total) * 100),
    status="processing",
    updated_at=datetime.utcnow()
)
db.merge(progress_record)
db.commit()
```

---

## 📝 Summary

### Data Storage Strategy
- **Audio Files**: Filesystem (`data/uploads/{emp_id}/{folder_path}/`)
- **Metadata**: SQLite database (5 tables)
- **Results**: Database with JSON fields for complex data

### Workflow States
1. **Upload**: File → Disk + DB metadata
2. **Analysis Request**: Create job → Background task
3. **Processing**: Sequential file processing → Save results
4. **Progress**: Real-time polling → Frontend updates
5. **Results**: Query DB → Display in UI

### Dummy vs Real API
- **Real**: HTTP POST to port 8003 → Whisper model → JSON response
- **Dummy**: API error → Generate mock dialogue → Same JSON structure
- **Key**: Both return identical data structure for seamless testing

### Critical Files
- `config.py` - Path configuration
- `app/services/stt_service.py` - STT API communication + dummy
- `app/services/analysis_service.py` - Job orchestration + results
- `app/services/file_service.py` - File management
- `app/models/database.py` - Schema definitions
- `templates/analysis.html` - Frontend result display

---

## 🎓 Ready for Changes

You now have complete understanding of:
1. ✅ Where files are stored (filesystem structure)
2. ✅ How metadata is tracked (database schema)
3. ✅ How analysis flows (workflows)
4. ✅ How results are fetched (polling + queries)
5. ✅ How dummy mode works (and should be improved)
6. ✅ Path handling between services (Docker compatibility)

**You are now prepared to make informed changes to the system.**
